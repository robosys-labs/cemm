"""CEMM v1 runtime orchestrator for grounded cycles, queries and admission."""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict

from cemm.cognition import (
    FORCE_ACKNOWLEDGMENT,
    FORCE_CLAIM,
    FORCE_CORRECTION,
    FORCE_DESCRIPTION,
    FORCE_DIRECTIVE,
    FORCE_QUERY,
    FORCE_RETRACTION,
    FrontierGraph,
    InterpretationAssessment,
    LearningFrontier,
    ScopedEpistemicAssessment,
    build_discourse_act,
)
from cemm.config import Config
from cemm.context import ContextStack, CycleState, SelfRuntimeView, SessionContext, TemporalFrame
from cemm.epistemics import EpistemicPolicy
from cemm.inference import Inference
from cemm.interpreter import Interpreter
from cemm.model import AmbiguousReferent, canonical, now, stable
from cemm.realizer import LanguagePack, PointerRealizer
from cemm.response import ResponsePlanner
from cemm.rules import RuleLearner
from cemm.state import StateProjector
from cemm.workspace import Workspace


class BoundedModelCache:
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
                self._cache.popitem(last=False)

    def __len__(self):
        return len(self._cache)


class Runtime:
    def __init__(self, store, pack_path: str, config: Config | None = None, session_context: SessionContext | None = None):
        self.s = store
        self.config = config or Config()
        self.pack = LanguagePack(pack_path)
        self.lang = self.pack.language
        self.cache = BoundedModelCache(self.config.model_cache_limit)
        self.session = session_context or SessionContext.default(store.symbol("self.ref"))
        self._cycle_counter = 0
        self.r = PointerRealizer(store, self.pack, self.cache)
        self.planner = ResponsePlanner(store)
        self.epistemic_policy = EpistemicPolicy(store)
        self.runtime_attestation = {
            "authority_generation": store.generation,
            "authority_generation_hash": store.authority_hash(store.generation),
            "language_pack_hash": self.pack.hash,
            "read_generation": store.generation,
        }
        self._bind_authority()

    def _bind_authority(self):
        generation = int(self.runtime_attestation["authority_generation"])
        self.i = Interpreter(self.s, self.pack, generation, self.config)
        self.rulelearner = RuleLearner(self.s, self.i, config=self.config)
        self.inf = Inference(self.s, self.config, authority_generation=generation)
        self.ws = Workspace(self.s, self.config, self.cache)
        self.state_projector = StateProjector(self.s, self.config, authority_generation=generation)

    def reload_authority(self):
        generation = self.s.generation
        self.runtime_attestation["authority_generation"] = generation
        self.runtime_attestation["authority_generation_hash"] = self.s.authority_hash(generation)
        self.runtime_attestation["read_generation"] = generation
        self._bind_authority()
        return dict(self.runtime_attestation)

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

    @staticmethod
    def _packet_applications(packet):
        applications = list(packet.get("apps", []))
        query = packet.get("query")
        if query:
            applications += [query] if query.get("operator") else list(query.get("restrictions", []))
        directive = packet.get("directive")
        if directive:
            applications += list(directive.get("content", []))
        return applications

    def _project_referenced_state_spaces(self, packet, cycle):
        refs = set()
        for application in self._packet_applications(packet):
            for role in ("role:subject", "role:instance", "role:actor", "role:object"):
                value = application.get("args", {}).get(role)
                atom = self.s.atom(value) if isinstance(value, str) and not value.startswith("?") else None
                if atom and atom["kind"] in {"entity", "participant", "resource", "source", "existential"}:
                    refs.add(value)
        projections = {
            ref: self.state_projector.project(ref).as_dict()
            for ref in sorted(refs)
        }
        cycle.workspace.put("state_space_projections", projections)
        return projections

    def _materialize(self, packet, news, generation, seed):
        facts, _ = self.inf.closure()
        mapping = {}
        applications = self._packet_applications(packet)
        for item in news:
            token, kind = item["token"], item["kind"]
            candidates = None
            for application in applications:
                roles = [
                    role
                    for role, value in application.get("args", {}).items()
                    if isinstance(value, dict) and value.get("new") == token
                ]
                if len(roles) != 1:
                    continue
                role = roles[0]
                known = {}
                for other_role, value in application.get("args", {}).items():
                    if other_role == role:
                        continue
                    if isinstance(value, dict) and "new" in value:
                        if value["new"] in mapping:
                            known[other_role] = mapping[value["new"]]
                        continue
                    if not (isinstance(value, str) and value.startswith("?")):
                        known[other_role] = value
                if not known:
                    continue
                values = set()
                for fact in self.inf.match({"operator": application["operator"], "args": known}, facts):
                    candidate = fact.args.get(role)
                    atom = self.s.atom(candidate) if isinstance(candidate, str) else None
                    if atom and atom["kind"] == kind:
                        values.add(candidate)
                if values:
                    candidates = values if candidates is None else candidates & values
            if candidates and len(candidates) > 1:
                raise AmbiguousReferent(token, [{"ref": ref, "score": 1.0} for ref in sorted(candidates)])
            mapping[token] = next(iter(candidates)) if candidates else stable("atom", kind, seed, token)
        for item in news:
            ref = mapping[item["token"]]
            if not self.s.atom(ref):
                self.s.exact(
                    "atoms",
                    ["ref", "kind", "metadata", "generation", "authority_scope"],
                    [ref, item["kind"], "{}", generation, "world"],
                    ["ref"],
                    {"generation"},
                )

        output = json.loads(canonical(packet))

        def convert(value):
            return mapping[value["new"]] if isinstance(value, dict) and "new" in value else value

        for application in self._packet_applications(output):
            application["args"] = {role: convert(value) for role, value in application["args"].items()}
        return output, mapping

    def _outcome(self, key):
        plan = self.planner.plan(key)
        return self.r.plan(plan), plan

    @staticmethod
    def _plan_json(plan):
        if plan is None:
            return None
        return {
            "goal": plan["goal"],
            "value": plan.get("value"),
            "facts": [
                {"operator": fact.operator, "args": fact.args}
                for fact in plan.get("facts", [])
            ],
        }

    def _interpretation_from_trace(self, trace, packet=None):
        raw = trace.get("interpretation_assessment", {})
        status = raw.get("status") or ("resolved" if packet else "unresolved")
        return InterpretationAssessment(
            status=status,
            stable_packet=packet,
            grounded_refs=tuple(raw.get("grounded_refs", trace.get("grounded_anchors", {}).values())),
            open_variables=tuple(raw.get("open_variables", ())),
            unresolved_evidence=tuple(raw.get("unresolved_evidence", trace.get("unknown_form_evidence", ()))),
            blockers=tuple(raw.get("blockers", (trace.get("reason"),) if trace.get("reason") else ())),
        )

    def _frontier(self, text, reason, details, cycle, packet=None):
        interpretation = self._interpretation_from_trace(details, packet)
        evidence = details.get("unknown_form_evidence") or details.get("skipped_clauses") or [{"reason": reason}]
        frontier = LearningFrontier.create(
            details.get("learning_frontier", {}).get("kind", reason),
            evidence,
            blocks=("interpretation",),
            cycle_ref=cycle.cycle_ref,
        )
        graph = FrontierGraph((frontier,))
        cycle.workspace.put("interpretation_assessment", interpretation)
        cycle.workspace.put("frontier_graph", graph)
        (response, proof), plan = self._outcome("frontier")
        return {
            "status": "frontier" if packet is None else "partial",
            "response": response,
            "frontier": frontier.as_dict(),
            "frontier_graph": graph.as_dict(),
            "interpretation": interpretation.as_dict(),
            "response_plan": self._plan_json(plan),
            "realization_proof": proof,
            "self_state": {},
            "self_runtime_view": cycle.self_runtime_view.as_dict(),
            "cycle": cycle.trace(),
        }

    def _query_response(self, query_result, facts_by_ref):
        if query_result.status == "conflict":
            (response, proof), plan = self._outcome("conflict")
            return response, proof, plan
        if query_result.bindings:
            outputs = []
            proofs = []
            used = set()
            for binding in query_result.bindings[:5]:
                for ref in binding.proof_refs:
                    if ref in used or ref not in facts_by_ref:
                        continue
                    used.add(ref)
                    surface, proof = self.r.fact(facts_by_ref[ref])
                    if surface:
                        outputs.append(surface)
                        proofs.append(proof)
            if outputs:
                return " ".join(outputs), {"verified": all(item.get("verified") for item in proofs), "fact_proofs": proofs}, None
        legacy = {
            "answered": "supported",
            "partial": "unknown",
            "supported": "supported",
            "contradicted": "contradicted",
            "conflict": "conflict",
            "unknown": "unknown",
        }[query_result.status]
        (response, proof), plan = self._outcome(legacy)
        return response, proof, plan

    def process(self, text, learn=True, teach=False, participant_frame=None, source="user", channel="text"):
        self.runtime_attestation["read_generation"] = self.s.generation
        cycle = self._new_cycle(participant_frame, source, channel)
        if teach:
            result = self.rulelearner.teach(text, cycle.participant_frame)
            if result.get("status") == "frontier":
                return self._frontier(text, result.get("reason", "rule_learning_frontier"), result, cycle)
            (response, proof), plan = self._outcome("learned")
            return {
                **result,
                "response": response,
                "response_plan": self._plan_json(plan),
                "realization_proof": proof,
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }
        try:
            packet, news, uses, trace = self.i.parse(text, cycle.participant_frame)
        except AmbiguousReferent as exc:
            return self._frontier(
                text,
                "ambiguous_referent",
                {"surface": exc.surface, "candidates": exc.candidates},
                cycle,
            )
        except Exception as exc:
            return self._frontier(text, "interpretation_error", {"error": str(exc)}, cycle)
        if not packet:
            return self._frontier(text, trace.get("reason", "no_candidate"), trace, cycle)

        interpretation = self._interpretation_from_trace(trace, packet)
        cycle.workspace.put("interpretation_assessment", interpretation)
        act = build_discourse_act(packet, cycle.participant_frame, trace)
        cycle.workspace.put("discourse_act", act)
        projections = self._project_referenced_state_spaces(packet, cycle)
        trace["state_space_projections"] = projections
        trace["discourse_act"] = act.as_dict()

        greeting = None
        try:
            greeting = self.s.symbol("event.greeting")
        except ValueError:
            pass
        if greeting and any(
            application["operator"] == "op:event"
            and application["args"].get("role:type") == greeting
            for application in act.content
        ):
            (response, proof), plan = self._outcome("greeting")
            return {
                "status": "ok",
                "response": response,
                "discourse_act": act.as_dict(),
                "interpretation": interpretation.as_dict(),
                "response_plan": self._plan_json(plan),
                "realization_proof": proof,
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }

        if act.force == FORCE_DESCRIPTION and act.describe_target:
            facts, _ = self.inf.closure()
            visible = [
                fact
                for fact in facts
                if fact.stance == "support"
                and self.s.user_visible_fact(fact)
                and act.describe_target in fact.args.values()
            ]
            _, workspace_trace = self.ws.build(
                facts,
                {"restrictions": [{"operator": "describe", "args": {"target": act.describe_target}}]},
                [fact.ref for fact in visible],
                cycle_turn=self._cycle_counter,
            )
            outputs = []
            proofs = []
            for fact in visible[:5]:
                surface, proof = self.r.fact(fact)
                if surface:
                    outputs.append(surface)
                    proofs.append(proof)
            if outputs:
                return {
                    "status": "ok",
                    "response": " ".join(outputs),
                    "facts": [fact.__dict__ for fact in visible[:10]],
                    "workspace": workspace_trace,
                    "discourse_act": act.as_dict(),
                    "interpretation": interpretation.as_dict(),
                    "realization_proofs": proofs,
                    "self_state": {},
                    "self_runtime_view": cycle.self_runtime_view.as_dict(),
                    "cycle": cycle.trace(),
                }
            (response, proof), plan = self._outcome("unknown")
            assessment = ScopedEpistemicAssessment(
                target_ref=act.describe_target,
                status="unknown",
                missing=("description",),
            )
            return {
                "status": "unknown",
                "response": response,
                "workspace": workspace_trace,
                "discourse_act": act.as_dict(),
                "interpretation": interpretation.as_dict(),
                "epistemic_assessment": assessment.as_dict(),
                "response_plan": self._plan_json(plan),
                "realization_proof": proof,
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }

        if act.force == FORCE_QUERY and act.query:
            facts, by_ref = self.inf.closure()
            if self.inf.incomplete:
                return self._frontier(
                    text,
                    "inference_incomplete",
                    {"reason": self.inf.incomplete_reason},
                    cycle,
                    packet,
                )
            query_result = self.inf.execute_query(act.query, facts, by_ref)
            proof_refs = sorted(
                {ref for binding in query_result.bindings for ref in binding.proof_refs}
            )
            _, workspace_trace = self.ws.build(
                facts,
                act.query.as_dict(),
                proof_refs,
                cycle_turn=self._cycle_counter,
            )
            response, realization_proof, plan = self._query_response(query_result, by_ref)
            assessment = ScopedEpistemicAssessment(
                target_ref=query_result.query_ref,
                status=query_result.status,
                support_refs=tuple(proof_refs),
                opposition_refs=(),
                missing=query_result.unresolved_variables,
                coverage=query_result.coverage,
            )
            cycle.workspace.put("query_result", query_result)
            cycle.workspace.put("epistemic_assessment", assessment)
            response_inputs = {
                "query_result": query_result.as_dict(),
                "epistemic_assessment": assessment.as_dict(),
                "state_space_projections": projections,
                "interpretation": interpretation.as_dict(),
                "discourse_act": act.as_dict(),
                "transition_candidates": [],
            }
            return {
                "status": "ok",
                "response": response,
                "result": query_result.status,
                "query": act.query.as_dict(),
                "query_result": query_result.as_dict(),
                "epistemic_assessment": assessment.as_dict(),
                "workspace": workspace_trace,
                "response_plan": self._plan_json(plan),
                "realization_proof": realization_proof,
                "response_inputs": response_inputs,
                "ephemeral_fact_count": sum(fact.derived for fact in facts),
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }

        if act.force == FORCE_DIRECTIVE:
            # Phase 10 will populate role-addressed transition previews.  A
            # directive is neither a claim nor an already executed effect.
            cycle.workspace.put("transition_candidates", [])
            return {
                "status": "interpreted_directive",
                "response": "",
                "discourse_act": act.as_dict(),
                "interpretation": interpretation.as_dict(),
                "goal_candidate": {
                    "source_act_ref": act.act_ref,
                    "requires_capability_check": True,
                    "requires_permission_check": True,
                    "requires_transition_preview": True,
                },
                "transition_candidates": [],
                "blocks_effect": True,
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }

        if act.force not in {FORCE_CLAIM, FORCE_CORRECTION, FORCE_RETRACTION, FORCE_ACKNOWLEDGMENT}:
            return {
                "status": "interpreted",
                "response": "",
                "packet": packet,
                "discourse_act": act.as_dict(),
                "interpretation": interpretation.as_dict(),
                "trace": trace,
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }
        if not learn:
            return {
                "status": "interpreted",
                "response": "",
                "packet": packet,
                "discourse_act": act.as_dict(),
                "interpretation": interpretation.as_dict(),
                "trace": trace,
                "side_effect_free": True,
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }

        try:
            with self.s.db:
                generation = self.s.begin("learn:" + hashlib.sha256(text.encode()).hexdigest()[:12])
                materialized_packet, mapping = self._materialize(packet, news, generation, f"generation:{generation}")
                materialized_act = build_discourse_act(materialized_packet, cycle.participant_frame, trace)
                observation_packet = {
                    "packet": materialized_packet,
                    "discourse_act": materialized_act.as_dict(),
                    "context_ref": materialized_act.context_ref,
                    "qualifiers": materialized_packet.get("qualifiers", {}),
                }
                observation = self.s.add_observation(
                    text,
                    observation_packet,
                    self.lang,
                    materialized_act.speaker_ref,
                    generation,
                    occurrence_ref=f"generation:{generation}",
                )
                occurrence_ref = self.s.add_claim_occurrence(observation, materialized_act, generation)
                placement = self.epistemic_policy.place(materialized_act)
                self.s.add_epistemic_placement(occurrence_ref, placement, generation)
                refs = []
                committed_apps = []
                if placement.admitted:
                    for application in materialized_act.content:
                        committed_apps.append(
                            self.s.insert_app(
                                application["operator"],
                                application["args"],
                                generation,
                                observation,
                                application.get("stance", "support"),
                                self.config.epistemic_default_claim_confidence,
                                "provisional",
                            )
                        )
                        refs += [
                            value
                            for value in application["args"].values()
                            if isinstance(value, str)
                        ]
                for surface_value, ref in uses:
                    self.s.record_use(surface_value, self.lang, ref)
                if placement.admitted:
                    self.s.touch(refs)
                    self.s.rebuild_designations()
                self.s.finish(generation)
            if placement.admitted:
                (response, proof), plan = self._outcome("learned")
            else:
                response, proof, plan = "", None, None
            status = (
                "partially_learned"
                if placement.admitted and interpretation.status == "partial"
                else "learned"
                if placement.admitted
                else "recorded_claim"
            )
            return {
                "status": status,
                "response": response,
                "packet": materialized_packet,
                "generation": generation,
                "new_atoms": mapping,
                "claim_occurrence_ref": occurrence_ref,
                "epistemic_placement": placement.as_dict(),
                "committed_apps": committed_apps,
                "discourse_act": materialized_act.as_dict(),
                "interpretation": interpretation.as_dict(),
                "trace": trace,
                "response_plan": self._plan_json(plan),
                "realization_proof": proof,
                "transition_candidates": [],
                "self_state": {},
                "self_runtime_view": cycle.self_runtime_view.as_dict(),
                "cycle": cycle.trace(),
            }
        except AmbiguousReferent as exc:
            return self._frontier(
                text,
                "ambiguous_referent",
                {"surface": exc.surface, "candidates": exc.candidates},
                cycle,
                packet,
            )
        except Exception as exc:
            return self._frontier(
                text,
                "learning_rejected",
                {"error": str(exc), "packet": packet},
                cycle,
                packet,
            )
