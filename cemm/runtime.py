"""Canonical Stage 0-22 CEMM v1 runtime.

Normal conversation is one pipeline. Modes control durable authority/effect
permissions; they never rewrite discourse force or semantic structure.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import OrderedDict
from typing import Any, Mapping

from cemm.capability import CapabilityEvaluator, RuntimeObservationProvider
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
    QueryBinding,
    QueryResult,
    ScopedEpistemicAssessment,
    build_discourse_act,
)
from cemm.config import Config
from cemm.dialogue import DialogueState
from cemm.context import ContextStack, CycleState, SelfRuntimeView, SessionContext, TemporalFrame
from cemm.epistemics import EpistemicPolicy
from cemm.goals import AdapterRegistry, GoalArbiter, GoalCandidate
from cemm.inference import Inference, InferenceTimeoutError
from cemm.interpreter import Interpreter
from cemm.model import AmbiguousReferent, canonical, now, stable
from cemm.semantic_description import SemanticDescriptionEngine
from cemm.proof import ProofEngine, VerifiedSemanticFocus
from cemm.learning_plans import (
    LearningContractRegistry,
    LearningPlan,
    validate_learning_commit_packet,
)
from cemm.operational import (
    CANONICAL_RUNTIME_RESOURCES,
    OperationalInvariantChecker,
    OperationalProviderContractError,
    OperationalUsageLedger,
    RuntimeServiceRegistry,
    declared_operation_resources,
)
from cemm.realizer import LanguagePack, PointerRealizer
from cemm.response import ResponseBuilder
from cemm.retrieval import SemanticRetriever
from cemm.rules import RuleLearner
from cemm.stages import BudgetSet, Stage, StageTrace
from cemm.state import StateProjector
from cemm.transitions import TransitionEngine
from cemm.workspace import Workspace


MODE_NORMAL = "normal"
MODE_READ_ONLY = "read_only"
MODE_REVIEWED_TEACH = "reviewed_teach"
_VALID_MODES = {MODE_NORMAL, MODE_READ_ONLY, MODE_REVIEWED_TEACH}


class BoundedModelCache:
    def __init__(self, limit=8):
        self._cache = OrderedDict()
        self._limit = int(limit)

    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key, value):
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self._limit:
            self._cache.popitem(last=False)

    def __len__(self):
        return len(self._cache)


class Runtime:
    def __init__(self, store, pack_path, config=None, session_context=None, adapter_registry=None):
        self.s = store
        self.config = config or Config()
        self.pack = LanguagePack(pack_path)
        self.lang = self.pack.language
        self.cache = BoundedModelCache(self.config.model_cache_limit)
        self.session = session_context or SessionContext.default(store.symbol("self.ref"))
        self.adapters = adapter_registry or AdapterRegistry()
        self._cycle_counter = 0
        self.response_builder = ResponseBuilder()
        self.goal_arbiter = GoalArbiter()
        self.epistemic_policy = EpistemicPolicy(store)
        self.dialogue_state = DialogueState(max_verified_focus=self.config.dialogue_max_verified_focus)
        self.runtime_attestation = {
            "authority_generation": store.generation,
            "authority_generation_hash": store.authority_hash(store.generation),
            "language_pack_hash": self.pack.hash,
            "schema_version": self.s.db.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()[0],
        }
        self._bind_authority()

    def _bind_authority(self):
        generation = int(self.runtime_attestation["authority_generation"])
        self.i = Interpreter(self.s, self.pack, generation, self.config)
        self.learning_contracts = LearningContractRegistry(self.s, generation)
        self.inf = Inference(self.s, self.config, authority_generation=generation)
        self.retriever = SemanticRetriever(self.s, self.config, generation)
        self.description_engine = SemanticDescriptionEngine(
            self.s, self.config, int(self.runtime_attestation["authority_generation"])
        )
        self.proof_engine = ProofEngine(
            self.s, self.config, int(self.runtime_attestation["authority_generation"])
        )
        self.state_projector = StateProjector(self.s, self.config, authority_generation=generation)
        self.transition_engine = TransitionEngine(self.s, self.inf, generation)
        self.capability_evaluator = CapabilityEvaluator(
            self.s,
            self.config.capability_dependency_max_depth,
        )
        self.rulelearner = RuleLearner(self.s, self.i, config=self.config)
        self.workspace = Workspace(self.s, self.config, self.cache)
        self.realizer = PointerRealizer(self.s, self.pack, self.cache)
        def semantic_runtime_probe():
            required = (
                "i",
                "inf",
                "retriever",
                "state_projector",
                "transition_engine",
                "capability_evaluator",
                "workspace",
            )
            missing = [name for name in required if not hasattr(self, name)]
            if missing:
                raise OperationalProviderContractError(
                    "semantic runtime registration is incomplete: " + ",".join(missing)
                )
            unavailable = [name for name in required if getattr(self, name) is None]
            if unavailable:
                return {
                    "state": "unavailable",
                    "score": 0.0,
                    "unavailable_components": unavailable,
                }
            return {
                "state": "available",
                "score": 1.0,
                "components": list(required),
            }

        def designation_index_probe():
            interpreter = getattr(self, "i", None)
            public_status = getattr(interpreter, "designation_index_status", None)
            if callable(public_status):
                status = public_status()
                if not isinstance(status, Mapping):
                    raise OperationalProviderContractError(
                        "designation-index status must be a mapping"
                    )
                return dict(status)

            # The resource is a semantic-store index, not a private interpreter
            # implementation detail. Reduced interpreters may omit the optional
            # diagnostic surface, so prove the persistent index directly from
            # the store before falling back to unknown evidence.
            db = getattr(self.s, "db", None)
            if db is None:
                return {
                    "state": "unknown",
                    "score": None,
                    "reason": "designation_index_store_handle_unavailable",
                }
            try:
                present = db.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='designation_index'"
                ).fetchone()
                if present is None:
                    return {
                        "state": "unavailable",
                        "score": 0.0,
                        "present": False,
                        "reason": "designation_index_table_missing",
                    }
                count = int(
                    db.execute("SELECT count(*) FROM designation_index").fetchone()[0]
                )
            except sqlite3.Error as exc:
                return {
                    "state": "unavailable",
                    "score": 0.0,
                    "present": False,
                    "error_type": type(exc).__name__,
                }
            return {
                "state": "available",
                "score": 1.0,
                "present": True,
                "entry_count": count,
                "evidence_source": "semantic_store_table",
            }

        def semantic_store_probe():
            if not hasattr(self.s, "db"):
                raise OperationalProviderContractError(
                    "semantic store provider lacks database handle"
                )
            return (
                self.s.db.execute("SELECT 1").fetchone() is not None,
                {"database_open": True},
            )

        self.service_registry = RuntimeServiceRegistry()
        self.service_registry.register("resource:runtime_process", lambda: True)
        self.service_registry.register(
            "resource:semantic_runtime", semantic_runtime_probe
        )
        self.service_registry.register_object(
            "resource:language_realizer", self, "realizer"
        )
        self.service_registry.register("resource:output_channel", lambda: True)
        self.service_registry.register_object(
            "resource:inference_engine", self, "inf"
        )
        self.service_registry.register(
            "resource:designation_index", designation_index_probe
        )
        self.service_registry.register(
            "resource:semantic_store", semantic_store_probe
        )
        self.service_registry.register_object(
            "resource:common_ground", self.s, "commit_common_ground"
        )
        self.service_registry.validate_resources()

    def reload_authority(self):
        invalidated = self.dialogue_state.invalidate_pending_on_authority_reload()
        generation = self.s.generation
        self.runtime_attestation["authority_generation"] = generation
        self.runtime_attestation["authority_generation_hash"] = self.s.authority_hash(generation)
        self._bind_authority()
        return {
            **dict(self.runtime_attestation),
            "invalidated_pending_learning_plan_ref": (
                invalidated.plan.plan_ref if invalidated is not None else None
            ),
        }

    def _new_cycle(self, participant_frame=None, source="user", channel="text"):
        self._cycle_counter += 1
        revisions = self.s.revisions()
        frame = participant_frame or self.session.input_frame(
            source=source,
            channel=channel,
            dialogue_context=self.dialogue_state.context(self._cycle_counter),
        )
        cycle_ref = stable("cycle", self.session.session_ref, self._cycle_counter, now())
        snapshot = self.service_registry.capture(
            self_ref=self.session.self_ref,
            cycle_ref=cycle_ref,
            authority_generation=int(self.runtime_attestation["authority_generation"]),
            world_revision=revisions["world_revision"],
        )
        view = SelfRuntimeView(
            self.session.self_ref,
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            snapshot,
        )
        cycle = CycleState(
            cycle_ref,
            stable("pass", cycle_ref, 0),
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            frame,
            ContextStack(),
            TemporalFrame(),
            view,
        )
        cycle.workspace.put(
            "operational_usage_ledger", OperationalUsageLedger(snapshot)
        )
        return cycle

    @staticmethod
    def _require_resources(cycle, stage, resources, *, allow_degraded=False):
        ledger = cycle.workspace.get("operational_usage_ledger")
        if ledger is None:
            raise RuntimeError("cycle lacks operational resource-use ledger")
        return OperationalInvariantChecker.check_stage_usage(
            cycle.self_runtime_view.operational_snapshot,
            resources,
            stage=int(stage),
            ledger=ledger,
            allow_degraded=allow_degraded,
        )

    def _interpreter_resources(self, operation):
        return declared_operation_resources(
            self.i,
            str(operation),
            baseline=("resource:semantic_runtime",),
            allowed_resources=CANONICAL_RUNTIME_RESOURCES,
        )

    @staticmethod
    def _packet_applications(packet):
        if not packet:
            return []
        applications = list(packet.get("apps", ()))
        query = packet.get("query")
        if query:
            applications.extend(query.get("restrictions", ()))
        directive = packet.get("directive")
        if directive:
            applications.extend(directive.get("content", ()))
        return applications

    @staticmethod
    def _referents(applications):
        return {
            value
            for application in applications
            for role, value in application.get("args", {}).items()
            if role in {"role:subject", "role:instance", "role:actor", "role:object", "role:event"}
            and isinstance(value, str)
            and not value.startswith(("?", "!"))
        }

    def _project(self, refs):
        output = {}
        for ref in sorted(set(refs)):
            atom = self.s.atom(ref)
            if atom and atom["kind"] in {"entity", "participant", "resource", "source", "existential", "event"}:
                output[ref] = self.state_projector.project(ref).as_dict()
        return output

    @staticmethod
    def _interpretation(trace, packet):
        raw = trace.get("interpretation_assessment", {})
        return InterpretationAssessment(
            raw.get("status") or ("resolved" if packet else "unresolved"),
            packet,
            tuple(raw.get("grounded_refs", trace.get("grounded_anchors", {}).values())),
            tuple(raw.get("open_variables", ())),
            tuple(raw.get("unresolved_evidence", trace.get("unknown_form_evidence", ()))),
            tuple(raw.get("blockers", (trace.get("reason"),) if trace.get("reason") else ())),
            dict(raw.get("coverage", trace.get("interpretation_coverage", {})) or {}),
            dict(raw.get("partial_structure", trace.get("partial_packet", {})) or {}),
        )

    @staticmethod
    def _frontiers(trace, cycle_ref):
        output = []
        seen_gaps = set()
        for item in trace.get("unknown_form_evidence", ()):
            gap = item.get("composition_gap") if isinstance(item, dict) else None
            if isinstance(gap, dict):
                gap_ref = str(gap.get("gap_ref") or "")
                if gap_ref in seen_gaps:
                    continue
                seen_gaps.add(gap_ref)
                kind = str(gap.get("gap_kind") or "known_form_composition_gap")
                unknown_only = bool(gap.get("unknown_unit_refs")) and not gap.get("known_unit_refs")
                blocks = ("interpretation", "answer", "lexical_learning") if unknown_only else ("interpretation", "answer")
                output.append(LearningFrontier.create(
                    "unknown_form" if unknown_only else kind,
                    ({**dict(item), "composition_gap": dict(gap)},),
                    target_ref=item.get("semantic_ref"),
                    blocks=blocks,
                    cycle_ref=cycle_ref,
                ))
                continue
            residual_class = str(item.get("residual_class") or "unknown_form")
            grounding_status = str(item.get("grounding_status") or "unknown")
            semantic_ref = item.get("semantic_ref") or item.get("target_ref")
            if residual_class == "unknown_form":
                kind, blocks = "unknown_form", ("interpretation", "answer", "lexical_learning")
            elif grounding_status == "grounded" and semantic_ref:
                kind, blocks = "grounded_composition_gap", ("interpretation", "answer")
            else:
                kind, blocks = "known_form_composition_gap", ("interpretation", "answer")
            output.append(LearningFrontier.create(
                kind, (dict(item),), target_ref=str(semantic_ref) if semantic_ref else None,
                blocks=blocks, cycle_ref=cycle_ref,
            ))
        for skipped in trace.get("skipped_clauses", ()):
            if skipped.get("reason") != "unknown_form":
                output.append(LearningFrontier.create(
                    skipped.get("reason", "unresolved_clause"), (dict(skipped),),
                    blocks=("interpretation", "answer"), cycle_ref=cycle_ref,
                ))
        if not output and trace.get("reason"):
            output.append(LearningFrontier.create(
                trace["reason"], ({"reason": trace["reason"], "coverage": trace.get("interpretation_coverage"),
                                   "partial_structure": trace.get("partial_packet")},),
                blocks=("interpretation", "answer"), cycle_ref=cycle_ref,
            ))
        return tuple(output)

    def _resolve_candidate_application_refs(self, packet):
        applications = self._packet_applications(packet)
        if not applications:
            return packet
        by_local = {
            str(item.get("application_ref")): item
            for item in applications if item.get("application_ref")
        }
        if not by_local:
            return packet
        if len(by_local) != sum(1 for item in applications if item.get("application_ref")):
            raise ValueError("duplicate candidate-local application refs")
        resolved = {}
        pending = set(by_local)
        while pending:
            progressed = False
            for local_ref in tuple(sorted(pending)):
                application = by_local[local_ref]
                args = {}
                blocked = False
                for role, value in application.get("args", {}).items():
                    if isinstance(value, dict) and set(value) == {"app"}:
                        child = str(value["app"])
                        if child in by_local and child not in resolved:
                            blocked = True
                            break
                        args[role] = {"app": resolved.get(child, child)}
                    else:
                        args[role] = value
                if blocked:
                    continue
                resolved[local_ref] = self.s.app_signature(application["operator"], args)
                application["args"] = args
                application["application_ref"] = resolved[local_ref]
                pending.remove(local_ref)
                progressed = True
            if not progressed:
                raise ValueError("candidate-local application graph is cyclic or incomplete")
        # Parent app bindings now reference exact child app signatures. Child-first
        # order is required so store validation cannot observe a dangling app ref.
        ordered = []
        remaining = list(applications)
        inserted = set()
        while remaining:
            progress = False
            for item in tuple(remaining):
                children = {
                    str(value["app"]) for value in item.get("args", {}).values()
                    if isinstance(value, dict) and set(value) == {"app"}
                }
                local_children = {child for child in children if child in set(resolved.values())}
                external_children = children - local_children
                if all(self.s.db.execute(
                    "SELECT 1 FROM applications WHERE app_ref=?", (child,)
                ).fetchone() for child in external_children) and local_children.issubset(inserted):
                    ordered.append(item); inserted.add(str(item.get("application_ref")))
                    remaining.remove(item); progress = True
            if not progress:
                raise ValueError("materialized application graph is cyclic")
        if packet.get("query"):
            packet["query"]["restrictions"] = ordered
        elif packet.get("directive"):
            packet["directive"]["content"] = ordered
        else:
            packet["apps"] = ordered
        return packet

    def _materialize(self, packet, news, generation, seed):
        mapping = {}
        applications = self._packet_applications(packet)
        for item in news:
            token, kind = item["token"], item["kind"]
            candidate_sets = []
            for application in applications:
                roles = [
                    role for role, value in application.get("args", {}).items()
                    if isinstance(value, dict) and value.get("new") == token
                ]
                if len(roles) != 1:
                    continue
                role = roles[0]
                known_args = {
                    other_role: (mapping[value["new"]] if isinstance(value, dict) and value.get("new") in mapping else value)
                    for other_role, value in application.get("args", {}).items()
                    if other_role != role and not (isinstance(value, dict) and "new" in value)
                }
                if not known_args:
                    continue
                candidates = {
                    fact.args.get(role)
                    for fact in self.s.matching_facts(
                        ({"operator": application["operator"], "args": known_args, "stance": application.get("stance", "support")},),
                        limit=16,
                    )
                    if isinstance(fact.args.get(role), str)
                    and self.s.atom(fact.args.get(role))
                    and self.s.atom(fact.args.get(role))["kind"] == kind
                }
                if candidates:
                    candidate_sets.append(candidates)
            candidates = set.intersection(*candidate_sets) if candidate_sets else set()
            if len(candidates) > 1:
                raise AmbiguousReferent(token, [{"ref": ref, "score": 1.0} for ref in sorted(candidates)])
            mapping[token] = next(iter(candidates)) if candidates else stable("atom", kind, seed, token)
        output = json.loads(canonical(packet))

        def convert(value):
            return mapping[value["new"]] if isinstance(value, dict) and "new" in value else value

        for application in self._packet_applications(output):
            application["args"] = {role: convert(value) for role, value in application["args"].items()}
        output = self._resolve_candidate_application_refs(output)
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
        return output, mapping

    @staticmethod
    def _directive_semantic_targets(act):
        if act is None or act.force != FORCE_DIRECTIVE:
            return ()
        targets = set()
        role_by_operator = {
            "op:event": "role:type",
            "op:relation": "role:relation",
            "op:state": "role:dimension",
        }
        for application in act.content:
            role = role_by_operator.get(application.get("operator"))
            value = application.get("args", {}).get(role) if role else None
            if isinstance(value, str) and not value.startswith(("?", "!")):
                targets.add(value)
        return tuple(sorted(targets))

    def _authority_targets(self, act, control_role):
        try:
            relation = self.s.symbol(control_role)
        except ValueError:
            return ()
        output = set()
        for target in self._directive_semantic_targets(act):
            output.update(
                self.s.relation_objects(
                    target,
                    relation,
                    authority_only=True,
                    upto_generation=int(self.runtime_attestation["authority_generation"]),
                )
            )
        return tuple(sorted(output))

    def _adapter_candidates(self, act):
        """Resolve adapters from semantic authority, never from surface text."""
        return self._authority_targets(act, "policy.adapter_relation")

    def _required_capabilities(self, act):
        """Resolve action-specific capability requirements from semantic authority."""
        return self._authority_targets(act, "policy.required_capability_relation")

    def _commit_stage13(self, *, text, packet, news, uses, trace, act, placement, frontiers, cycle):
        generation = self.s.begin(
            "cycle:" + hashlib.sha256((cycle.cycle_ref + text).encode()).hexdigest()[:16],
            expected_world_revision=cycle.world_revision,
        )
        materialized_packet = packet
        mapping = {}
        if packet and placement is not None and placement.admitted:
            materialized_packet, mapping = self._materialize(packet, news, generation, f"generation:{generation}")
            materialized_act = build_discourse_act(materialized_packet, cycle.participant_frame, trace)
        else:
            materialized_act = act
        observation = self.s.add_observation(
            text,
            {
                "packet": materialized_packet,
                "discourse_act": materialized_act.as_dict() if materialized_act else None,
                "frontier_graph": FrontierGraph(frontiers).as_dict(),
                "context_ref": getattr(materialized_act, "context_ref", None),
            },
            self.lang,
            cycle.participant_frame.speaker_ref,
            generation,
            occurrence_ref=cycle.cycle_ref,
        )
        occurrence_ref = None
        committed_apps = []
        retracted_claims = ()
        refs = []
        if materialized_act is not None:
            target_occurrence = materialized_packet.get("qualifiers", {}).get("target_occurrence_ref") if materialized_packet else None
            if materialized_act.force in {FORCE_CORRECTION, FORCE_RETRACTION} and target_occurrence:
                retracted_claims = self.s.retract_claim_occurrence(
                    target_occurrence, materialized_act.speaker_ref, valid_to=cycle.temporal_frame.observed_at
                )
            occurrence_ref = self.s.add_claim_occurrence(observation, materialized_act, generation)
            if placement is not None:
                self.s.add_epistemic_placement(occurrence_ref, placement, generation)
            if placement is not None and placement.admitted:
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
                    refs.extend(value for value in application["args"].values() if isinstance(value, str))
        frontier_refs = [self.s.frontier(text, frontier.kind, frontier.as_dict(), generation) for frontier in frontiers]
        for surface_value, ref in uses:
            self.s.record_use(surface_value, self.lang, ref)
        if refs:
            self.s.touch(refs)
        receipt = self.s.finish(
            generation,
            cycle_ref=cycle.cycle_ref,
            stage=13,
            expected_world_revision=cycle.world_revision,
            world_delta=bool(committed_apps or retracted_claims),
            observation_delta=True,
            payload={
                "observation_ref": observation,
                "occurrence_ref": occurrence_ref,
                "committed_apps": committed_apps,
                "retracted_claims": list(retracted_claims),
                "frontier_refs": frontier_refs,
                "placement": placement.as_dict() if placement else None,
            },
        )
        return {
            "generation": generation,
            "packet": materialized_packet,
            "act": materialized_act,
            "mapping": mapping,
            "observation_ref": observation,
            "occurrence_ref": occurrence_ref,
            "committed_apps": committed_apps,
            "retracted_claims": list(retracted_claims),
            "frontier_refs": frontier_refs,
            "receipt": receipt,
        }

    def process(self, text, *, mode=MODE_NORMAL, participant_frame=None, source="user", channel="text"):
        if mode not in _VALID_MODES:
            raise ValueError(f"unsupported runtime mode: {mode}")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be non-empty")
        cycle = self._new_cycle(participant_frame, source, channel)
        stages = StageTrace(cycle.cycle_ref)
        budgets = BudgetSet(
            self.config.retrieval_max_seed_facts,
            self.config.retrieval_max_rules,
            self.config.retrieval_max_depth,
            self.config.max_operation_reentry,
        )
        stages.add(Stage.ORIENT, counts={"participants": 3, "budgets": 4}, refs=(cycle.participant_frame.speaker_ref, cycle.participant_frame.addressee_ref))

        if mode == MODE_REVIEWED_TEACH:
            stages.add(Stage.OBSERVE, counts={"evidence": 1})
            stages.add(Stage.ENCODE, counts={"teaching_surface": 1})
            stages.add(Stage.GROUND, counts={"participant_frames": 1})
            stages.add(Stage.PROJECT_STATE, counts={"projections": 0})
            stages.add(Stage.COMPILE, counts={"rule_candidates": 1})
            stages.add(Stage.RECURRENT_DYNAMICS, counts={"candidate_sets": 1})
            stages.add(Stage.STABILIZE, counts={"stable_rules": 1})
            stages.add(Stage.BUILD_STRUCTURES, counts={"teaching_acts": 1})
            stages.add(Stage.EPISTEMIC_PLACEMENT, counts={"reviewed_teaching": 1})
            stages.add(Stage.QUERY_EXPLAIN, counts={})
            stages.add(Stage.PREDICTION_ERROR, counts={})
            stages.add(Stage.TRANSITION_SIMULATION, counts={})
            self._require_resources(
                cycle,
                Stage.ENCODE,
                self._interpreter_resources("delex_for_rule"),
            )
            self._require_resources(
                cycle, Stage.COMMIT, ("resource:semantic_store",)
            )
            result = self.rulelearner.teach(
                text,
                cycle.participant_frame,
                cycle_ref=cycle.cycle_ref,
                expected_world_revision=cycle.world_revision,
            )
            teaching_frontiers = ()
            if result.get("status") == "frontier":
                teaching_frontiers = (LearningFrontier.create(
                    result.get("reason", "rule_induction_unsettled"),
                    ({"surface": text, "details": result},),
                    blocks=("rule_induction",),
                    cycle_ref=cycle.cycle_ref,
                ),)
                stages.add(Stage.COMMIT, counts={"rule_artifacts": 0})
                goal = GoalCandidate(stable("goal", "teaching-clarify", cycle.cycle_ref), "clarify", teaching_frontiers[0].frontier_ref, 1.0, {"frontier": teaching_frontiers[0].as_dict()})
            else:
                stages.add(Stage.COMMIT, counts={"rule_artifacts": 1}, refs=(result.get("candidate_ref", ""),), durable_write=True)
                goal = GoalCandidate(stable("goal", "teaching", cycle.cycle_ref), "acknowledge_claim", result.get("candidate_ref", cycle.cycle_ref), 1.0)
            decision = self.goal_arbiter.decide((goal,))
            stages.add(Stage.CAPABILITY_IMPACT, counts={})
            stages.add(Stage.GOAL_ARBITRATION, counts={"goals": 1})
            stages.add(Stage.PLAN_EXECUTE, counts={"operations": 0})
            stages.add(Stage.ASSIMILATE_OPERATION, counts={})
            response_csir = self.response_builder.build(
                audience_ref=cycle.participant_frame.speaker_ref,
                goal_decision=decision,
                frontiers=teaching_frontiers,
            )
            stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, refs=(response_csir.response_ref,))
            self._require_resources(
                cycle, Stage.REALIZE, ("resource:language_realizer",)
            )
            self._require_resources(
                cycle, Stage.VERIFY, ("resource:output_channel",)
            )
            response, realization_proof = self.realizer.response(
                response_csir,
                self.session.output_frame(
                    addressee_ref=cycle.participant_frame.speaker_ref,
                    channel=cycle.participant_frame.channel,
                    dialogue_context=self.dialogue_state.context(self._cycle_counter),
                ),
            )
            stages.add(Stage.REALIZE, counts={"surfaces": int(bool(response))})
            stages.add(Stage.VERIFY, counts={"verified": int(bool(realization_proof.get("verified")))})
            common_ground = None
            if response and realization_proof.get("verified"):
                self._require_resources(
                    cycle,
                    Stage.COMMON_GROUND,
                    ("resource:common_ground", "resource:semantic_store"),
                )
                with self.s.db:
                    common_ground = self.s.commit_common_ground(
                        cycle.participant_frame.conversation_ref, response_csir.response_ref, {
                        "response_csir": response_csir.as_dict(),
                        "surface_decision": realization_proof.get("surface_decision"),
                        "response_equivalence": realization_proof.get("response_equivalence"),
                        "obligation_ref": response_csir.obligation_ref,
                        "pending_learning": (
                            self.dialogue_state.pending.as_dict()
                            if self.dialogue_state.pending
                            else None
                        ),
                    },
                        expected_discourse_revision=cycle.discourse_revision,
                    )
                self.dialogue_state.observe_response(
                    response_csir,
                    realization_proof,
                    cycle_ref=cycle.cycle_ref,
                    turn_index=self._cycle_counter,
                )
                stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
            else:
                stages.add(Stage.COMMON_GROUND, counts={"entries": 0})
            stages.add(Stage.FINALIZE, counts={"model_cache": len(self.cache)})
            return {
                **result,
                "response": response,
                "response_csir": response_csir.as_dict(),
                "realization_proof": realization_proof,
                "common_ground": common_ground,
                "cycle": cycle.trace(),
                "stage_trace": stages.as_dict(),
                "budgets": budgets.__dict__,
            }

        try:
            self._require_resources(
                cycle,
                Stage.ENCODE,
                self._interpreter_resources("observe"),
            )
            lattice = self.i.observe(text, cycle.participant_frame)
        except AmbiguousReferent as exc:
            stages.add(Stage.OBSERVE, counts={"evidence": 0})
            stages.add(Stage.ENCODE, counts={"clauses": 0, "unknown": 1})
            stages.add(Stage.GROUND, counts={"grounded_referents": 0})
            stages.add(Stage.PROJECT_STATE, counts={"projections": 0})
            stages.add(Stage.COMPILE, counts={"applications": 0})
            stages.add(Stage.RECURRENT_DYNAMICS, counts={"candidate_sets": 0})
            frontiers = (LearningFrontier.create(
                "ambiguous_referent",
                ({"surface": exc.surface, "candidates": exc.candidates},),
                blocks=("interpretation",),
                cycle_ref=cycle.cycle_ref,
            ),)
            stages.add(Stage.STABILIZE, counts={"stable": 0, "frontiers": 1})
            stages.add(Stage.BUILD_STRUCTURES, counts={"discourse_acts": 0, "queries": 0})
            stages.add(Stage.EPISTEMIC_PLACEMENT, counts={"placements": 0, "admitted": 0})
            stages.add(Stage.QUERY_EXPLAIN, counts={"facts": 0, "bindings": 0})
            stages.add(Stage.PREDICTION_ERROR, counts={"errors": 0})
            stages.add(Stage.TRANSITION_SIMULATION, counts={"previews": 0})
            stages.add(Stage.COMMIT, counts={"applications": 0, "frontiers": 0})
            stages.add(Stage.CAPABILITY_IMPACT, counts={"capabilities": 0})
            stages.add(Stage.GOAL_ARBITRATION, counts={"candidates": 1, "selected": 1})
            stages.add(Stage.PLAN_EXECUTE, counts={"operations": 0})
            stages.add(Stage.ASSIMILATE_OPERATION, counts={"operation_evidence": 0})
            clarify_goal = GoalCandidate(
                stable("goal", "clarify-ambiguous", cycle.cycle_ref),
                "clarify",
                frontiers[0].frontier_ref,
                1.0,
                {"frontier": frontiers[0].as_dict()},
            )
            decision = self.goal_arbiter.decide((clarify_goal,))
            response_csir = self.response_builder.build(
                audience_ref=cycle.participant_frame.speaker_ref,
                goal_decision=decision,
                frontiers=frontiers,
            )
            stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, refs=(response_csir.response_ref,))
            self._require_resources(
                cycle, Stage.REALIZE, ("resource:language_realizer",)
            )
            self._require_resources(
                cycle, Stage.VERIFY, ("resource:output_channel",)
            )
            response, realization_proof = self.realizer.response(
                response_csir,
                self.session.output_frame(
                    addressee_ref=cycle.participant_frame.speaker_ref,
                    channel=cycle.participant_frame.channel,
                    dialogue_context=self.dialogue_state.context(self._cycle_counter),
                ),
            )
            stages.add(Stage.REALIZE, counts={"surfaces": int(bool(response))})
            verified = bool(response and realization_proof.get("verified"))
            stages.add(Stage.VERIFY, counts={"verified": int(verified)})
            common_ground = None
            if mode == MODE_NORMAL and verified and self.config.persist_common_ground:
                self._require_resources(
                    cycle,
                    Stage.COMMON_GROUND,
                    ("resource:common_ground", "resource:semantic_store"),
                )
                with self.s.db:
                    common_ground = self.s.commit_common_ground(
                        cycle.participant_frame.conversation_ref,
                        response_csir.response_ref,
                        {
                            "response_csir": response_csir.as_dict(),
                            "surface_decision": realization_proof.get("surface_decision"),
                            "response_equivalence": realization_proof.get("response_equivalence"),
                            "obligation_ref": response_csir.obligation_ref,
                            "pending_learning": None,
                        },
                        expected_discourse_revision=cycle.discourse_revision,
                    )
                self.dialogue_state.observe_response(
                    response_csir,
                    realization_proof,
                    cycle_ref=cycle.cycle_ref,
                    turn_index=self._cycle_counter,
                )
                stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
            else:
                stages.add(Stage.COMMON_GROUND, counts={"entries": 0})
            stages.add(Stage.FINALIZE, counts={"model_cache": len(self.cache), "workspace_slots": 0})
            return {
                "status": "frontier",
                "response": response,
                "mode": mode,
                "packet": None,
                "interpretation": {"status": "unresolved", "blockers": ["ambiguous_referent"]},
                "frontier_graph": FrontierGraph(frontiers).as_dict(),
                "response_csir": response_csir.as_dict(),
                "realization_proof": realization_proof,
                "common_ground": common_ground,
                "dialogue_state": self.dialogue_state.context(self._cycle_counter),
                "operational_usage": cycle.workspace.get("operational_usage_ledger").as_dict(),
                "stage_trace": stages.as_dict(),
                "budgets": budgets.__dict__,
                "side_effect_free": mode == MODE_READ_ONLY,
            }
        stages.add(Stage.OBSERVE, counts={"evidence": len(lattice.envelopes)}, refs=tuple(x.evidence_ref for x in lattice.envelopes))
        stages.add(Stage.ENCODE, counts={"clauses": len(lattice.form_evidence.get("clauses", ())), "unknown": len(lattice.unknown_evidence)})
        resolved_form = lattice.resolved_form_lattice
        grounded_refs_by_hypothesis = {
            hypothesis.hypothesis_ref: {
                unit.semantic_ref
                for unit in hypothesis.units
                if unit.kind == "anchor" and unit.semantic_ref
            }
            for hypothesis in (
                resolved_form.grounding_hypotheses if resolved_form else ()
            )
        }
        grounded_refs = set().union(*grounded_refs_by_hypothesis.values()) if grounded_refs_by_hypothesis else set()
        stages.add(Stage.GROUND, counts={"grounded_referents": len(grounded_refs)}, refs=tuple(sorted(grounded_refs)))
        state_projections = self._project(grounded_refs | {self.session.self_ref})
        cycle.workspace.put("state_space_projections", state_projections)
        cycle.workspace.put("grounded_refs_by_hypothesis", grounded_refs_by_hypothesis)
        stages.add(Stage.PROJECT_STATE, counts={"projections": len(state_projections)}, refs=tuple(sorted(state_projections)))

        try:
            packet, news, uses, trace = self.i.compose(lattice, cycle.participant_frame, state_projections)
        except AmbiguousReferent as exc:
            packet, news, uses = None, [], []
            trace = {
                "reason": "ambiguous_referent",
                "candidates": exc.candidates,
                "unknown_form_evidence": ({
                    "surface": exc.surface,
                    "residual_class": "argument_critical",
                    "semantic_kind_candidates": ["referent"],
                },),
            }
        stages.add(Stage.COMPILE, counts={"applications": len(self._packet_applications(packet))})
        stages.add(Stage.RECURRENT_DYNAMICS, counts={"candidate_sets": len(trace.get("clauses", ()))})
        interpretation = self._interpretation(trace, packet)
        # Retrieval and transition work must follow the selected interpretation,
        # not whichever grounding hypothesis happened to rank first pre-compose.
        if interpretation.grounded_refs:
            grounded_refs = set(interpretation.grounded_refs)
        frontiers = self._frontiers(trace, cycle.cycle_ref)
        if packet is not None and interpretation.status != "resolved":
            raise RuntimeError(
                "partial interpretation attempted to cross the Stage-7 authority boundary"
            )
        cycle.workspace.put("interpretation_assessment", interpretation)
        cycle.workspace.put("frontier_graph", FrontierGraph(frontiers))
        stages.add(
            Stage.STABILIZE,
            counts={
                "stable": int(packet is not None and interpretation.status == "resolved"),
                "frontiers": len(frontiers),
            },
        )

        act = build_discourse_act(packet, cycle.participant_frame, trace) if packet else None
        cycle.workspace.put("discourse_act", act)
        stages.add(Stage.BUILD_STRUCTURES, counts={"discourse_acts": int(act is not None), "queries": int(bool(act and act.query))})
        placement = self.epistemic_policy.place(act) if act is not None else None
        cycle.workspace.put("epistemic_placement", placement)
        stages.add(Stage.EPISTEMIC_PLACEMENT, counts={"placements": int(placement is not None), "admitted": int(bool(placement and placement.admitted))})

        runtime_facts = cycle.self_runtime_view.operational_snapshot.semantic_facts()
        query_result = None
        retrieval = None
        description_result = None
        proof_bundle = None
        facts = list(runtime_facts)
        by_ref = {fact.ref: fact for fact in facts}
        workspace_trace = {"selected": [], "top_k": self.config.workspace_top_k}
        scoped_epistemic = None
        describe_request = getattr(act, "describe_target", None) if act else None
        if act and act.force == FORCE_QUERY and act.query:
            query_kind = str(dict(act.query.qualifiers or {}).get("query_kind") or "")
            if (
                isinstance(describe_request, dict)
                or query_kind == "embedded_proposition_query"
            ):
                self._require_resources(
                    cycle, Stage.QUERY_EXPLAIN, ("resource:semantic_store",)
                )
            if isinstance(describe_request, dict) and describe_request.get("description_kind") == "semantic_target":
                request = self.description_engine.request(
                    str(describe_request["target_ref"]),
                    facets=tuple(describe_request.get("requested_facets", ())) or (),
                    provenance={"query_ref": act.query.query_ref, "act_ref": act.act_ref},
                )
                description_result = self.description_engine.describe(request)
                facts = list(description_result.facts) + list(runtime_facts)
                by_ref = {fact.ref: fact for fact in facts}
                binding = QueryBinding(
                    {"?description_target": request.target_ref},
                    tuple(fact.ref for fact in description_result.facts),
                )
                query_result = QueryResult(
                    act.query.query_ref,
                    "answered" if description_result.target_kind != "unknown" else "unknown",
                    (binding,) if description_result.target_kind != "unknown" else (),
                    1.0 if description_result.target_kind != "unknown" else 0.0,
                    len(description_result.facts), 0, (), (),
                    tuple(x.frontier_ref for x in frontiers),
                    {
                        **dict(act.query.qualifiers or {}),
                        "query_kind": "semantic_description",
                        "target_ref": request.target_ref,
                        "description_result": description_result.as_dict(),
                    },
                )
            elif isinstance(describe_request, dict) and describe_request.get("description_kind") == "epistemic_provenance":
                raw_focus = cycle.participant_frame.dialogue_context.get("verified_semantic_focus")
                focus = VerifiedSemanticFocus.from_dict(raw_focus) if isinstance(raw_focus, dict) else None
                if focus is not None:
                    proof_bundle = self.proof_engine.explain_focus(
                        focus,
                        proof_lookup={focus.proof_ref: self.dialogue_state.proof_bundle(focus.proof_ref)},
                    )
                else:
                    proof_bundle = self.proof_engine.explain_focus(VerifiedSemanticFocus.create(
                        focus_kind="unresolved", response_ref="response:none",
                        authority_generation=int(self.runtime_attestation["authority_generation"]),
                        world_revision=self.s.revisions()["world_revision"],
                    ))
                query_result = QueryResult(
                    act.query.query_ref,
                    "answered" if proof_bundle.completeness not in {"unsupported", "stale"} else "unknown",
                    (), 1.0 if proof_bundle.completeness not in {"unsupported", "stale"} else 0.0,
                    proof_bundle.support_count, proof_bundle.opposition_count, (), (),
                    tuple(x.frontier_ref for x in frontiers),
                    {
                        **dict(act.query.qualifiers or {}),
                        "query_kind": "epistemic_provenance",
                        "proof_bundle": proof_bundle.as_dict(),
                    },
                )
            elif query_kind == "embedded_proposition_query" and dict(act.query.qualifiers or {}).get("evaluation_kind") == "answerability":
                embedded = tuple(dict(act.query.qualifiers or {}).get("embedded_proposition_graphs", ()))
                descriptions = []
                for graph in embedded:
                    request_data = dict(graph.get("provenance", {}).get("describe_request", {}) or {})
                    if request_data.get("target_ref"):
                        req = self.description_engine.request(str(request_data["target_ref"]), provenance={"outer_query_ref": act.query.query_ref})
                        descriptions.append(self.description_engine.describe(req))
                answerable = bool(descriptions) and all(item.target_kind != "unknown" for item in descriptions)
                description_result = descriptions[0] if len(descriptions) == 1 else None
                proof_refs = tuple(fact.ref for item in descriptions for fact in item.facts)
                query_result = QueryResult(
                    act.query.query_ref, "supported" if answerable else "contradicted",
                    (), 1.0, int(answerable), int(not answerable), (), (),
                    tuple(x.frontier_ref for x in frontiers),
                    {**dict(act.query.qualifiers or {}), "answer_mode": "boolean"},
                )
                facts = [fact for item in descriptions for fact in item.facts] + list(runtime_facts)
                by_ref = {fact.ref: fact for fact in facts}
            else:
                self._require_resources(
                    cycle, Stage.QUERY_EXPLAIN,
                    ("resource:inference_engine", "resource:semantic_store"),
                )
                retrieval = self.retriever.retrieve(act.query.restrictions, salient_refs=grounded_refs)
                facts, by_ref = self.inf.closure(seed_facts=retrieval.facts, rules=retrieval.rules, extra=runtime_facts)
                query_result = self.inf.execute_query(
                    act.query, facts, by_ref,
                    blocking_frontiers=tuple(x.frontier_ref for x in frontiers),
                )
                proof_refs = sorted({ref for binding in query_result.bindings for ref in binding.proof_refs})
                _, workspace_trace = self.workspace.build(
                    facts, act.query.as_dict(), proof_refs, cycle_turn=self._cycle_counter,
                )
                scoped_epistemic = ScopedEpistemicAssessment(
                    query_result.query_ref, query_result.status, tuple(proof_refs), (),
                    query_result.unresolved_variables, query_result.coverage,
                )
        elif act and act.force == FORCE_DESCRIPTION and act.describe_target:
            self._require_resources(
                cycle, Stage.QUERY_EXPLAIN, ("resource:semantic_store",)
            )
            target = act.describe_target.get("target_ref") if isinstance(act.describe_target, dict) else act.describe_target
            request = self.description_engine.request(str(target), provenance={"act_ref": act.act_ref})
            description_result = self.description_engine.describe(request)
            facts = list(description_result.facts) + list(runtime_facts)
            by_ref = {fact.ref: fact for fact in facts}
            binding = QueryBinding({"?description_target": request.target_ref}, tuple(fact.ref for fact in description_result.facts))
            query_result = QueryResult(
                stable("description-query", request.target_ref),
                "answered" if description_result.target_kind != "unknown" else "unknown",
                (binding,) if description_result.target_kind != "unknown" else (),
                1.0 if description_result.target_kind != "unknown" else 0.0,
                len(description_result.facts), 0, (), (), tuple(x.frontier_ref for x in frontiers),
                {"query_kind": "semantic_description", "target_ref": request.target_ref,
                 "description_result": description_result.as_dict()},
            )
            scoped_epistemic = ScopedEpistemicAssessment(
                query_result.query_ref, query_result.status,
                tuple(fact.ref for fact in description_result.facts), (), (), query_result.coverage,
            )
        stages.add(Stage.QUERY_EXPLAIN, counts={"facts": len(facts), "bindings": len(query_result.bindings) if query_result else 0}, refs=(query_result.query_ref,) if query_result else ())

        trigger_apps = tuple(act.content if act and act.force in {FORCE_CLAIM, FORCE_DIRECTIVE} else ())
        transition_retrieval = self.retriever.retrieve(trigger_apps, salient_refs=grounded_refs, include_causal=True) if trigger_apps else None
        transition_facts = list(transition_retrieval.facts if transition_retrieval else ()) + list(runtime_facts)
        transition_previews = self.transition_engine.preview(
            trigger_apps,
            transition_facts,
            state_projections,
            context_ref=getattr(act, "context_ref", None),
        ) if trigger_apps else ()
        prediction_errors = self.transition_engine.prediction_errors(
            transition_previews,
            tuple(app for app in trigger_apps if app.get("operator") == "op:state"),
        )
        stages.add(Stage.PREDICTION_ERROR, counts={"errors": len(prediction_errors)})
        stages.add(Stage.TRANSITION_SIMULATION, counts={"previews": len(transition_previews)}, refs=tuple(x.preview_ref for x in transition_previews))

        commit = None
        should_commit = mode == MODE_NORMAL and (
            frontiers or (act and act.force in {FORCE_CLAIM, FORCE_CORRECTION, FORCE_RETRACTION})
        )
        if should_commit:
            packet_qualifiers = dict((packet or {}).get("qualifiers", {}))
            if packet_qualifiers.get("consumes_pending_learning"):
                pending_learning = self.dialogue_state.require(
                    packet_qualifiers.get("pending_learning_obligation_ref")
                )
                validate_learning_commit_packet(
                    packet,
                    pending_learning,
                    self.s,
                    authority_generation=int(
                        self.runtime_attestation["authority_generation"]
                    ),
                )
            commit_resources = {"resource:semantic_store"}
            if any(
                app.get("operator") == "op:designation"
                for app in self._packet_applications(packet)
            ):
                commit_resources.add("resource:designation_index")
            self._require_resources(cycle, Stage.COMMIT, commit_resources)
            with self.s.db:
                commit = self._commit_stage13(
                    text=text,
                    packet=packet,
                    news=news,
                    uses=uses,
                    trace=trace,
                    act=act,
                    placement=placement,
                    frontiers=frontiers,
                    cycle=cycle,
                )
            if commit.get("act") is not None:
                act = commit["act"]
            committed_packet = commit.get("packet") or {}
            committed_qualifiers = dict(committed_packet.get("qualifiers", {}))
            if (
                commit.get("committed_apps")
                and committed_qualifiers.get("consumes_pending_learning")
            ):
                consumed_obligation = self.dialogue_state.consume_after_commit(
                    committed_qualifiers.get("pending_learning_obligation_ref"),
                    commit_receipt_ref=commit["receipt"]["receipt_ref"],
                )
                cycle.workspace.put(
                    "consumed_learning_obligation",
                    consumed_obligation.as_dict(),
                )
            if (
                commit.get("committed_apps")
                and int(commit["generation"])
                != int(self.runtime_attestation["authority_generation"])
            ):
                # Newly admitted semantic authority must become visible to the
                # next cycle through the same generation-pinned designation,
                # affordance and description indexes.  This refreshes runtime
                # bindings only; it never regenerates a language form pack.
                self.reload_authority()
            stages.add(Stage.COMMIT, counts={"applications": len(commit["committed_apps"]), "frontiers": len(commit["frontier_refs"])}, refs=(commit["receipt"]["receipt_ref"],), durable_write=True)
        else:
            stages.add(Stage.COMMIT, counts={"applications": 0, "frontiers": 0})

        self_projection = state_projections.get(self.session.self_ref) or self.state_projector.project(self.session.self_ref).as_dict()
        runtime_observations = RuntimeObservationProvider.observe(cycle.self_runtime_view)
        capability_assessments = self.capability_evaluator.evaluate(self.session.self_ref, self_projection, runtime_observations)
        stages.add(Stage.CAPABILITY_IMPACT, counts={"capabilities": len(capability_assessments)}, refs=tuple(x.assessment_ref for x in capability_assessments))

        required_capability_refs = self._required_capabilities(act)
        learning_probe = []
        if query_result is not None and trace.get("pending_learning_probe"):
            if act is None or act.query is None:
                raise RuntimeError("learning probe survived without an exact query")
            exact_query = act.query.as_dict()
            exact_material = {
                key: exact_query.get(key)
                for key in ("restrictions", "variables", "projection", "qualifiers")
            }
            for raw_probe in trace.get("pending_learning_probe", ()):
                probe = dict(raw_probe)
                raw_query = dict(probe.get("probe_query") or {})
                raw_material = {
                    key: raw_query.get(key, [] if key != "qualifiers" else {})
                    for key in ("restrictions", "variables", "projection", "qualifiers")
                }
                if canonical(raw_material) != canonical(exact_material):
                    raise RuntimeError(
                        "learning probe query differs from the executed QueryStructure"
                    )
                contract_ref = str(probe.get("learning_contract_ref") or "")
                query_kind = str(probe.get("query_kind") or dict(raw_query.get("qualifiers", {}) or {}).get("query_kind") or "")
                contract = self.learning_contracts.license_query(contract_ref, query_kind)
                candidate_target_kinds = tuple(sorted(
                    set(map(str, probe.get("semantic_kind_candidates", ())))
                    & set(contract.expected_target_kinds)
                ))
                if not candidate_target_kinds:
                    raise RuntimeError(
                        "learning probe has no target kind licensed by its contract"
                    )
                plan = LearningPlan.create(
                    contract=contract,
                    source_query_ref=query_result.query_ref,
                    source_query_kind=query_kind,
                    source_query=exact_query,
                    authority_generation=int(
                        self.runtime_attestation["authority_generation"]
                    ),
                    surface_literal=str(probe.get("surface") or ""),
                    language=self.lang,
                    expected_target_kinds=candidate_target_kinds,
                    known_bindings=dict(probe.get("known_bindings", {})),
                    target_ref=probe.get("target_ref"),
                    original_candidate_ref=probe.get("original_candidate_ref"),
                    unresolved_span_ref=probe.get("unresolved_span_ref"),
                    created_turn=self._cycle_counter,
                    expires_after_turn=self.dialogue_state.expiry_turns,
                )
                plan.validate_authority(
                    self.s, authority_generation=int(
                        self.runtime_attestation["authority_generation"]
                    )
                )
                learning_probe.append({
                    **probe,
                    "query_ref": query_result.query_ref,
                    "probe_query": exact_query,
                    "learning_plan": plan.as_dict(),
                })
        candidates = list(self.goal_arbiter.candidates(
            act=act,
            query_result=query_result,
            frontiers=frontiers,
            transition_previews=transition_previews,
            capability_assessments=capability_assessments,
            required_capability_refs=required_capability_refs,
            learning_probe=tuple(learning_probe),
        ))
        # Note: a broad "how are you?" op:state query about the self is a genuine
        # state-of-being question, not a request to report the weakest capability.
        # Capability questions are handled through their own constructions/semantics.
        greeting = False
        if act:
            try:
                greeting_ref = self.s.symbol("event.greeting")
                greeting = any(app.get("operator") == "op:event" and app.get("args", {}).get("role:type") == greeting_ref for app in act.content)
            except ValueError:
                pass
        if greeting:
            candidates.append(GoalCandidate(stable("goal", "greet", act.act_ref), "greet", act.act_ref, 1.1))
        decision = self.goal_arbiter.decide(tuple(candidates))
        stages.add(Stage.GOAL_ARBITRATION, counts={"candidates": len(candidates), "selected": int(decision.selected is not None)}, refs=(decision.decision_ref,))

        operation_plan = operation_result = effect_receipt = None
        if decision.selected and decision.selected.kind == "handle_directive":
            operation_plan = self.adapters.plan(
                decision.selected,
                permission_scope=self.session.permission_scope,
                candidate_adapter_refs=self._adapter_candidates(act),
            )
            if mode == MODE_NORMAL:
                self._require_resources(
                    cycle, Stage.PLAN_EXECUTE, ("resource:semantic_store",)
                )
                operation_result = self.adapters.execute(operation_plan)
                with self.s.db:
                    effect_receipt = self.s.journal_effect(operation_plan, operation_result)
                stages.add(
                    Stage.PLAN_EXECUTE,
                    counts={"operations": 1, "executed": int(operation_result.status != "declined")},
                    refs=(effect_receipt["effect_ref"],),
                    durable_write=True,
                )
            else:
                operation_result = self.adapters.not_executed(
                    operation_plan, reason="runtime_mode_read_only"
                )
                stages.add(
                    Stage.PLAN_EXECUTE,
                    counts={"operations": 1, "executed": 0},
                    refs=(operation_plan.plan_ref,),
                    note="external effect suppressed by runtime mode",
                )
        else:
            stages.add(Stage.PLAN_EXECUTE, counts={"operations": 0})

        operation_evidence = None
        operation_prediction_errors = ()
        operation_observation_receipt = None
        if operation_result is not None:
            semantic_observations = tuple(
                item for item in operation_result.output.get("semantic_observations", ())
                if isinstance(item, dict) and item.get("operator")
            )
            valid_observations = []
            for item in semantic_observations[: self.config.retrieval_max_seed_facts]:
                try:
                    self.s.validate_app(item["operator"], item.get("args", {}))
                    valid_observations.append(item)
                except (KeyError, TypeError, ValueError):
                    continue
            operation_prediction_errors = self.transition_engine.prediction_errors(
                transition_previews, valid_observations
            )
            operation_evidence = {
                "source": "operation_adapter",
                "result": operation_result.as_dict(),
                "semantic_observations": valid_observations,
                "prediction_errors": [item.as_dict() for item in operation_prediction_errors],
                "reentry_count": 1 if valid_observations else 0,
                "max_reentry": self.config.max_operation_reentry,
                "world_admission": "not_automatic",
            }
            if mode == MODE_NORMAL:
                current_world = self.s.revisions()["world_revision"]
                self._require_resources(
                    cycle, Stage.ASSIMILATE_OPERATION, ("resource:semantic_store",)
                )
                with self.s.db:
                    generation = self.s.begin(
                        "operation_observation:" + operation_result.result_ref[-12:],
                        expected_world_revision=current_world,
                    )
                    observation_ref = self.s.add_observation(
                        canonical(operation_result.as_dict()),
                        operation_evidence,
                        self.lang,
                        operation_plan.adapter_ref or "operation_adapter",
                        generation,
                        occurrence_ref=operation_result.result_ref,
                        modality="operation",
                    )
                    operation_observation_receipt = self.s.finish(
                        generation,
                        cycle_ref=cycle.cycle_ref,
                        stage=17,
                        expected_world_revision=current_world,
                        observation_delta=True,
                        payload={"observation_ref": observation_ref, "operation_result": operation_result.as_dict()},
                    )
                stages.add(Stage.ASSIMILATE_OPERATION, counts={"operation_evidence": 1, "semantic_observations": len(valid_observations)}, refs=(operation_observation_receipt["receipt_ref"],), durable_write=True)
            else:
                stages.add(Stage.ASSIMILATE_OPERATION, counts={"operation_evidence": 1, "semantic_observations": len(valid_observations)})
        else:
            stages.add(Stage.ASSIMILATE_OPERATION, counts={"operation_evidence": 0})

        response_csir = self.response_builder.build(
            audience_ref=cycle.participant_frame.speaker_ref,
            goal_decision=decision,
            query_result=query_result,
            facts_by_ref=by_ref,
            frontiers=frontiers,
            capability_assessments=capability_assessments,
            operation_result=operation_result,
            epistemic_placement=placement,
            operational_snapshot=cycle.self_runtime_view.operational_snapshot,
            discourse_act=act,
            dialogue_context=cycle.participant_frame.dialogue_context,
        )
        stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, refs=(response_csir.response_ref,))
        self._require_resources(
            cycle, Stage.REALIZE, ("resource:language_realizer",)
        )
        self._require_resources(
            cycle, Stage.VERIFY, ("resource:output_channel",)
        )
        response, realization_proof = self.realizer.response(
            response_csir,
            self.session.output_frame(
                addressee_ref=cycle.participant_frame.speaker_ref,
                channel=cycle.participant_frame.channel,
                dialogue_context=self.dialogue_state.context(self._cycle_counter),
            ),
        )
        stages.add(Stage.REALIZE, counts={"surfaces": int(bool(response))})
        verified = bool(response and realization_proof.get("verified"))
        stages.add(Stage.VERIFY, counts={"verified": int(verified)}, refs=(response_csir.response_ref,))

        if verified and query_result is not None:
            if proof_bundle is None:
                proof_bundle = self.proof_engine.for_query_result(
                    query_result,
                    operational_snapshot_ref=(
                        cycle.self_runtime_view.operational_snapshot.snapshot_ref
                        if dict(query_result.qualifiers or {}).get("query_kind") == "operational_condition_query"
                        else None
                    ),
                )
            focus_targets = {
                str(value) for binding in query_result.bindings
                for value in binding.values.values()
                if isinstance(value, str) and not value.startswith(("?", "!"))
            }
            focus_targets.update(str(ref) for ref in grounded_refs)
            verified_focus = VerifiedSemanticFocus.create(
                focus_kind="query_result",
                proposition_ref=dict((packet or {}).get("qualifiers", {})).get("proposition_ref"),
                query_ref=query_result.query_ref,
                response_ref=response_csir.response_ref,
                target_refs=tuple(sorted(focus_targets)),
                bindings=(binding.values for binding in query_result.bindings),
                proof_ref=proof_bundle.proof_ref,
                recorded_turn=self._cycle_counter,
                authority_generation=int(self.runtime_attestation["authority_generation"]),
                world_revision=self.s.revisions()["world_revision"],
            )
            self.dialogue_state.record_verified_focus(verified_focus, proof_bundle)
        else:
            verified_focus = None

        common_ground = None
        if mode == MODE_NORMAL and verified and self.config.persist_common_ground:
            self._require_resources(
                cycle,
                Stage.COMMON_GROUND,
                ("resource:common_ground", "resource:semantic_store"),
            )
            with self.s.db:
                common_ground = self.s.commit_common_ground(
                    cycle.participant_frame.conversation_ref,
                    getattr(act, "act_ref", response_csir.response_ref),
                    {
                        "response_csir": response_csir.as_dict(),
                        "surface_decision": realization_proof.get("surface_decision"),
                        "response_equivalence": realization_proof.get("response_equivalence"),
                        "obligation_ref": response_csir.obligation_ref,
                        "verified_semantic_focus": verified_focus.as_dict() if verified_focus else None,
                        "proof_bundle": proof_bundle.as_dict() if proof_bundle else None,
                        "pending_learning": (
                            self.dialogue_state.pending.as_dict()
                            if self.dialogue_state.pending
                            else None
                        ),
                    },
                    expected_discourse_revision=cycle.discourse_revision,
                )
            self.dialogue_state.observe_response(
                response_csir,
                realization_proof,
                cycle_ref=cycle.cycle_ref,
                turn_index=self._cycle_counter,
            )
            stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
        else:
            stages.add(Stage.COMMON_GROUND, counts={"entries": 0})
        stages.add(Stage.FINALIZE, counts={"model_cache": len(self.cache), "workspace_slots": len(workspace_trace.get("selected", ()))})

        status = (
            "frontier" if packet is None
            else "partial" if interpretation.status == "partial"
            else "answered" if query_result is not None
            else "executed" if operation_result and operation_result.status == "succeeded"
            else "declined" if operation_result and operation_result.status == "declined"
            else "learned" if commit and commit["committed_apps"]
            else "recorded" if commit
            else "interpreted"
        )
        result = {
            "status": status,
            "response": response,
            "mode": mode,
            "packet": packet,
            "interpretation": interpretation.as_dict(),
            "discourse_act": act.as_dict() if act else None,
            "epistemic_placement": placement.as_dict() if placement else None,
            "query_result": query_result.as_dict() if query_result else None,
            "description_result": description_result.as_dict() if description_result else None,
            "proof_bundle": proof_bundle.as_dict() if proof_bundle else None,
            "verified_semantic_focus": verified_focus.as_dict() if verified_focus else None,
            "epistemic_assessment": scoped_epistemic.as_dict() if scoped_epistemic else None,
            "frontier_graph": FrontierGraph(frontiers).as_dict(),
            "state_space_projections": state_projections,
            "transition_previews": [x.as_dict() for x in transition_previews],
            "prediction_errors": [x.as_dict() for x in prediction_errors],
            "capability_assessments": [x.as_dict() for x in capability_assessments],
            "goal_decision": decision.as_dict(),
            "operation_plan": operation_plan.as_dict() if operation_plan else None,
            "operation_result": operation_result.as_dict() if operation_result else None,
            "effect_receipt": effect_receipt,
            "commit": commit,
            "response_csir": response_csir.as_dict(),
            "realization_proof": realization_proof,
            "common_ground": common_ground,
            "workspace": workspace_trace,
            "retrieval": retrieval.as_dict() if retrieval else None,
            "operation_evidence": operation_evidence,
            "operation_prediction_errors": [x.as_dict() for x in operation_prediction_errors],
            "operation_observation_receipt": operation_observation_receipt,
            "self_runtime_view": cycle.self_runtime_view.as_dict(),
            "self_state": {},
            "cycle": cycle.trace(),
            "stage_trace": stages.as_dict(),
            "budgets": budgets.__dict__,
            "side_effect_free": mode == MODE_READ_ONLY,
            "dialogue_state": self.dialogue_state.context(self._cycle_counter),
            "operational_usage": cycle.workspace.get("operational_usage_ledger").as_dict(),
            "runtime_invariants": {
                "critical_residuals_block_execution": not (
                    packet is not None and interpretation.status != "resolved"
                ),
                "operational_snapshot_ref": cycle.self_runtime_view.operational_snapshot.snapshot_ref,
                "registered_resources": list(self.service_registry.resources()),
                "response_equivalence_verified": bool(
                    response and realization_proof.get("verified")
                ),
                "surface_absent": not bool(response),
            },
        }
        return result

# CEMM_SOURCE_REWRITE:runtime:v3.1.3
