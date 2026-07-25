"""Runtime orchestrator for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 614-705).

The Runtime wires together every subsystem (interpreter, inference, workspace,
response planner, pointer realizer, rule learner) and exposes a single
``process`` entry point that turns natural language into learned knowledge,
answered queries, or frontier reports.

Weakness #10 fix: v4 used an unbounded global ``MODEL_CACHE = {}`` that grew
without limit for the lifetime of the process.  This module replaces it with a
bounded LRU cache (``BoundedModelCache``) that is owned by the Runtime instance
and shared with the subsystems that need it (surface codec, workspace net).
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict

from cemm.config import Config
from cemm.store import Store
from cemm.interpreter import Interpreter
from cemm.inference import Inference
from cemm.workspace import Workspace
from cemm.selfstate import SessionSelf
from cemm.context import SessionContext, CycleState, ContextStack, TemporalFrame, SelfRuntimeView
from cemm.state import StateProjector
from cemm.response import ResponsePlanner
from cemm.realizer import PointerRealizer, LanguagePack
from cemm.rules import RuleLearner
from cemm.model import Fact, stable, canonical, now, AmbiguousReferent


class BoundedModelCache:
    """LRU cache for neural models.  Bounded by ``config.model_cache_limit``.

    Uses :class:`collections.OrderedDict` so that the least-recently-used entry
    is evicted when the cache exceeds its limit.  This replaces v4's unbounded
    global ``MODEL_CACHE`` dict (weakness #10).
    """

    def __init__(self, limit: int = 8):
        self._cache: OrderedDict = OrderedDict()
        self._limit = limit

    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            self._cache[key] = value
            if len(self._cache) > self._limit:
                self._cache.popitem(last=False)  # evict oldest

    def __len__(self):
        return len(self._cache)


class Runtime:
    """Top-level orchestrator that ties all CEMM subsystems together."""

    def __init__(self, s: Store, pack_path: str, config: Config | None = None, session_context: SessionContext | None = None):
        self.s = s
        self.config = config or Config()
        self.pack = LanguagePack(pack_path)
        self.lang = self.pack.language
        self.cache = BoundedModelCache(self.config.model_cache_limit)
        self.session = session_context or SessionContext.default(s.symbol("self.ref"))
        self._cycle_counter = 0
        self.selfstate = SessionSelf(s)
        self.r = PointerRealizer(s, self.pack, self.cache)
        self.planner = ResponsePlanner(s)
        self.runtime_attestation = {
            "authority_generation": s.generation,
            "authority_generation_hash": s.authority_hash(s.generation),
            "language_pack_hash": self.pack.hash,
            "read_generation": s.generation,
        }
        self._bind_authority()

    def _bind_authority(self):
        g = int(self.runtime_attestation["authority_generation"])
        self.i = Interpreter(self.s, self.pack, g, self.config)
        self.rulelearner = RuleLearner(self.s, self.i, config=self.config)
        self.inf = Inference(self.s, self.config, authority_generation=g)
        self.ws = Workspace(self.s, self.selfstate, self.config, self.cache)
        self.state_projector = StateProjector(self.s, self.config, authority_generation=g)

    def _new_cycle(self, participant_frame=None, source="user", channel="text"):
        self._cycle_counter += 1
        frame = participant_frame or self.session.input_frame(source=source, channel=channel)
        cycle_ref = stable("cycle", self.session.session_ref, self._cycle_counter, now())
        return CycleState(
            cycle_ref=cycle_ref,
            pass_ref=stable("pass", cycle_ref, 0),
            authority_generation=int(self.runtime_attestation["authority_generation"]),
            read_generation=int(self.s.generation),
            participant_frame=frame,
            context_stack=ContextStack(),
            temporal_frame=TemporalFrame(),
            self_runtime_view=SelfRuntimeView(
                self_ref=self.session.self_ref,
                authority_generation=int(self.runtime_attestation["authority_generation"]),
                read_generation=int(self.s.generation),
            ),
        )

    def _project_referenced_state_spaces(self, packet, cycle):
        refs = set()
        apps = list(packet.get("apps", [])) + ([packet["query"]] if packet.get("query") else [])
        for app in apps:
            for role in ("role:subject", "role:instance", "role:actor", "role:object"):
                v = app.get("args", {}).get(role)
                atom = self.s.atom(v) if isinstance(v, str) else None
                if atom and atom["kind"] in {"entity", "participant", "resource", "source", "existential"}:
                    refs.add(v)
        projections = {ref: self.state_projector.project(ref).as_dict() for ref in sorted(refs)}
        cycle.workspace.put("state_space_projections", projections)
        return projections

    def reload_authority(self):
        g = self.s.generation
        self.runtime_attestation["authority_generation"] = g
        self.runtime_attestation["authority_generation_hash"] = self.s.authority_hash(g)
        self.runtime_attestation["read_generation"] = g
        self._bind_authority()
        return dict(self.runtime_attestation)

    def _materialize(self, packet, news, g, seed):
        facts, _ = self.inf.closure()
        mapping = {}
        for x in news:
            tok, kind = x["token"], x["kind"]
            candidates = None
            for a in packet.get("apps", []):
                roles = [
                    r
                    for r, v in a.get("args", {}).items()
                    if isinstance(v, dict) and v.get("new") == tok
                ]
                if len(roles) != 1:
                    continue
                role = roles[0]
                known = {}
                for r, v in a.get("args", {}).items():
                    if r == role:
                        continue
                    if isinstance(v, dict) and "new" in v:
                        if v["new"] in mapping:
                            known[r] = mapping[v["new"]]
                        continue
                    known[r] = v
                if not known:
                    continue
                vals = set()
                for f in self.inf.match({"operator": a["operator"], "args": known}, facts):
                    v = f.args.get(role)
                    atom = self.s.atom(v) if isinstance(v, str) else None
                    if atom and atom["kind"] == kind:
                        vals.add(v)
                if vals:
                    candidates = vals if candidates is None else candidates & vals
            if candidates and len(candidates) > 1:
                raise AmbiguousReferent(
                    tok, [{"ref": r, "score": 1.0} for r in sorted(candidates)]
                )
            mapping[tok] = next(iter(candidates)) if candidates else stable("atom", kind, seed, tok)
        for x in news:
            ref = mapping[x["token"]]
            if not self.s.atom(ref):
                self.s.exact(
                    "atoms",
                    ["ref", "kind", "metadata", "generation", "authority_scope"],
                    [ref, x["kind"], "{}", g, "world"],
                    ["ref"],
                    {"generation"},
                )
        p = json.loads(canonical(packet))
        cv = lambda v: mapping[v["new"]] if isinstance(v, dict) and "new" in v else v
        for a in p.get("apps", []):
            a["args"] = {k: cv(v) for k, v in a["args"].items()}
        if p.get("query"):
            p["query"]["args"] = {k: cv(v) for k, v in p["query"]["args"].items()}
        return p, mapping

    def _outcome(self, key, cause):
        if key in {"frontier"}:
            self.selfstate.set(
                self.s.symbol("self.interpretation_state_dimension"),
                self.s.symbol("self.unresolved"),
                cause,
            )
            self.selfstate.set(
                self.s.symbol("self.response_state_dimension"),
                self.s.symbol("self.confused"),
                cause,
            )
        elif key in {"unknown", "conflict"}:
            self.selfstate.set(
                self.s.symbol("self.epistemic_state_dimension"),
                self.s.symbol("self.insufficient" if key == "unknown" else "self.uncertain"),
                cause,
            )
            self.selfstate.set(
                self.s.symbol("self.response_state_dimension"),
                self.s.symbol("self.ready"),
                cause,
            )
        else:
            self.selfstate.set(
                self.s.symbol("self.interpretation_state_dimension"),
                self.s.symbol("self.resolved"),
                cause,
            )
            self.selfstate.set(
                self.s.symbol("self.epistemic_state_dimension"),
                self.s.symbol("self.sufficient"),
                cause,
            )
            self.selfstate.set(
                self.s.symbol("self.response_state_dimension"),
                self.s.symbol("self.ready"),
                cause,
            )
        plan = self.planner.plan(key)
        return self.r.plan(plan), plan

    def _plan_json(self, p):
        return {
            "goal": p["goal"],
            "value": p.get("value"),
            "facts": [{"operator": f.operator, "args": f.args} for f in p.get("facts", [])],
        }

    def _frontier(self, text, reason, details, *, persist=False, cycle=None):
        ref = self.s.frontier(text, reason, details) if persist else stable("frontier", getattr(cycle, "cycle_ref", "ephemeral"), text, reason, details)
        (out, p), plan = self._outcome("frontier", reason)
        return {
            "status": "frontier",
            "response": out,
            "frontier": {"ref": ref, "reason": reason, "details": details},
            "response_plan": self._plan_json(plan),
            "realization_proof": p,
            "self_state": dict(self.selfstate.state),
            "cycle": cycle.trace() if cycle else None,
        }

    def process(self, text, learn=True, teach=False, participant_frame=None, source="user", channel="text"):
        self.runtime_attestation["read_generation"] = self.s.generation
        cycle = self._new_cycle(participant_frame, source, channel)
        if teach:
            rr = self.rulelearner.teach(text, cycle.participant_frame)
            if rr.get("status") == "frontier":
                return self._frontier(text, rr.get("reason", "rule_learning_frontier"), rr, persist=True, cycle=cycle)
            (out, rp), plan = self._outcome("learned", "rule_learning")
            return {
                **rr,
                "response": out,
                "response_plan": self._plan_json(plan),
                "realization_proof": rp,
                "self_state": dict(self.selfstate.state),
            }
        self.selfstate.set(
            self.s.symbol("self.response_state_dimension"),
            self.s.symbol("self.processing"),
            "new_observation",
        )
        try:
            packet, news, uses, trace = self.i.parse(text, cycle.participant_frame)
        except AmbiguousReferent as e:
            return self._frontier(
                text, "ambiguous_referent", {"surface": e.surface, "candidates": e.candidates}, persist=bool(learn), cycle=cycle
            )
        except Exception as e:
            return self._frontier(text, "interpretation_error", {"error": str(e)}, cycle=cycle)
        if not packet:
            return self._frontier(text, trace.get("reason", "no_candidate"), trace, persist=bool(learn), cycle=cycle)
        # Pragmatic intent override: when learn=True and the input has no
        # question punctuation, the user is explicitly asserting a fact. If
        # the codec mispredicted query intent, convert the query packet to an
        # assert packet so the fact gets stored. Question marks are a
        # universal pragmatic signal — this uses surface form as evidence
        # about intent, not as semantic ontology.
        if learn and packet.get("query") and not packet.get("describe"):
            if not text.rstrip().endswith(("?", "？")):
                q = packet["query"]
                packet["apps"] = [{
                    "operator": q.get("operator", "op:type"),
                    "args": q.get("args", {}),
                    "stance": q.get("stance", "support"),
                }]
                packet["query"] = None
        trace["state_space_projections"] = self._project_referenced_state_spaces(packet, cycle)
        # Greeting is an ordinary event recognized through a pinned semantic ref.
        greet = (
            self.s.symbol("event.greeting")
            if self.s.db.execute(
                "SELECT 1 FROM control_symbols WHERE role='event.greeting'"
            ).fetchone()
            else None
        )
        if greet and any(
            a["operator"] == "op:event" and a["args"].get("role:type") == greet
            for a in packet.get("apps", [])
        ):
            (out, proof), plan = self._outcome("greeting", "greeting_event")
            return {
                "status": "ok",
                "response": out,
                "response_plan": self._plan_json(plan),
                "realization_proof": proof,
                "self_state": dict(self.selfstate.state),
            }
        if packet.get("query") or packet.get("describe"):
            facts, byref = self.inf.closure()
            if self.inf.incomplete:
                return self._frontier(
                    text, "inference_incomplete", {"reason": self.inf.incomplete_reason}, persist=bool(learn), cycle=cycle
                )
            if packet.get("describe"):
                target = packet["describe"]
                des = self.s.symbol("operator.designation")
                xs = [
                    f
                    for f in facts
                    if f.stance == "support"
                    and self.s.user_visible_fact(f)
                    and target in f.args.values()
                ]
                workspace, wtrace = self.ws.build(
                    facts, {"operator": "describe", "args": {"target": target}}, [f.ref for f in xs]
                )
                outs = []
                proofs = []
                for f in xs[:5]:
                    x, p = self.r.fact(f)
                    if x:
                        outs.append(x)
                        proofs.append(p)
                if outs:
                    self.selfstate.set(
                        self.s.symbol("self.interpretation_state_dimension"),
                        self.s.symbol("self.resolved"),
                        "describe_resolved",
                    )
                    self.selfstate.set(
                        self.s.symbol("self.response_state_dimension"),
                        self.s.symbol("self.ready"),
                        "describe_resolved",
                    )
                    return {
                        "status": "ok",
                        "response": " ".join(outs),
                        "facts": [f.__dict__ for f in xs[:10]],
                        "workspace": wtrace,
                        "realization_proofs": proofs,
                        "self_state": dict(self.selfstate.state),
                    }
                (out, p), plan = self._outcome("unknown", "describe_no_fact")
                return {
                    "status": "unknown",
                    "response": out,
                    "workspace": wtrace,
                    "response_plan": self._plan_json(plan),
                    "realization_proof": p,
                    "self_state": dict(self.selfstate.state),
                }
            pos = self.inf.match(packet["query"], facts)
            neg = self.inf.match({**packet["query"], "stance": "deny"}, facts)
            result = (
                "conflict" if pos and neg else "supported" if pos else "contradicted" if neg else "unknown"
            )
            chosen = pos or neg
            proof_refs = []
            if chosen:

                def collect(n):
                    proof_refs.append(n.ref)
                    if n.derived:
                        for r in n.proof["parents"]:
                            if r in byref:
                                collect(byref[r])

                collect(chosen[0])
            workspace, wtrace = self.ws.build(facts, packet["query"], proof_refs)
            (out, rp), plan = self._outcome(result, f"query:{result}")
            exp = self.inf.explain(chosen[0], byref) if chosen else None
            return {
                "status": "ok",
                "response": out,
                "result": result,
                "query": packet["query"],
                "proof": exp,
                "workspace": wtrace,
                "response_plan": self._plan_json(plan),
                "realization_proof": rp,
                "ephemeral_fact_count": sum(f.derived for f in facts),
                "self_state": dict(self.selfstate.state),
                "self_transitions": [t.__dict__ for t in self.selfstate.transitions[-6:]],
            }
        if not learn:
            return {"status": "interpreted", "packet": packet, "trace": trace}
        try:
            with self.s.db:
                g = self.s.begin("learn:" + hashlib.sha256(text.encode()).hexdigest()[:12])
                p, m = self._materialize(packet, news, g, f"generation:{g}")
                obs = self.s.add_observation(text, p, self.lang, "user", g, occurrence_ref=f"generation:{g}")
                refs = []
                for a in p.get("apps", []):
                    self.s.insert_app(a["operator"], a["args"], g, obs, a.get("stance", "support"), 0.95, "provisional")
                    refs += [v for v in a["args"].values() if isinstance(v, str)]
                for surf_, ref in uses:
                    self.s.record_use(surf_, self.lang, ref)
                self.s.touch(refs)
                self.s.rebuild_designations()
                self.s.finish(g)
            (out, rp), plan = self._outcome("learned", "knowledge_committed")
            return {
                "status": "learned",
                "response": out,
                "packet": p,
                "generation": g,
                "new_atoms": m,
                "trace": trace,
                "response_plan": self._plan_json(plan),
                "realization_proof": rp,
                "self_state": dict(self.selfstate.state),
            }
        except AmbiguousReferent as e:
            return self._frontier(
                text, "ambiguous_referent", {"surface": e.surface, "candidates": e.candidates}, persist=bool(learn), cycle=cycle
            )
        except Exception as e:
            return self._frontier(text, "learning_rejected", {"error": str(e), "packet": packet}, persist=bool(learn), cycle=cycle)

