"""Canonical Stage 0-22 CEMM v1 runtime.

Normal conversation is one pipeline. Modes control durable authority/effect
permissions; they never rewrite discourse force or semantic structure.
"""
from __future__ import annotations

import hashlib
import json
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
from cemm.context import ContextStack, CycleState, SelfRuntimeView, SessionContext, TemporalFrame
from cemm.epistemics import EpistemicPolicy
from cemm.goals import AdapterRegistry, GoalArbiter, GoalCandidate
from cemm.inference import Inference, InferenceTimeoutError
from cemm.interpreter import Interpreter
from cemm.model import AmbiguousReferent, canonical, now, stable
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
        self.inf = Inference(self.s, self.config, authority_generation=generation)
        self.retriever = SemanticRetriever(self.s, self.config, generation)
        self.state_projector = StateProjector(self.s, self.config, authority_generation=generation)
        self.transition_engine = TransitionEngine(self.s, self.inf, generation)
        self.capability_evaluator = CapabilityEvaluator(
            self.s,
            self.config.capability_dependency_max_depth,
            self.config.capability_unknown_score,
        )
        self.rulelearner = RuleLearner(self.s, self.i, config=self.config)
        self.workspace = Workspace(self.s, self.config, self.cache)
        self.realizer = PointerRealizer(self.s, self.pack, self.cache)

    def reload_authority(self):
        generation = self.s.generation
        self.runtime_attestation["authority_generation"] = generation
        self.runtime_attestation["authority_generation_hash"] = self.s.authority_hash(generation)
        self._bind_authority()
        return dict(self.runtime_attestation)

    def _new_cycle(self, participant_frame=None, source="user", channel="text"):
        self._cycle_counter += 1
        revisions = self.s.revisions()
        frame = participant_frame or self.session.input_frame(source=source, channel=channel)
        cycle_ref = stable("cycle", self.session.session_ref, self._cycle_counter, now())
        view = SelfRuntimeView(
            self.session.self_ref,
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            process_available=True,
            language_realizer_support=1.0,
            semantic_runtime_support=1.0,
            critical_blockers=(),
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
        return cycle

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
        )

    @staticmethod
    def _frontiers(trace, cycle_ref):
        output = []
        unknown = trace.get("unknown_form_evidence", ())
        if unknown:
            for item in unknown:
                output.append(
                    LearningFrontier.create(
                        "unknown_form",
                        (item,),
                        target_ref=None,
                        blocks=("interpretation",),
                        cycle_ref=cycle_ref,
                    )
                )
        for skipped in trace.get("skipped_clauses", ()):
            if skipped.get("reason") == "unknown_form":
                continue
            output.append(
                LearningFrontier.create(
                    skipped.get("reason", "unresolved_clause"),
                    (skipped,),
                    blocks=("interpretation",),
                    cycle_ref=cycle_ref,
                )
            )
        if not output and trace.get("reason"):
            output.append(
                LearningFrontier.create(
                    trace["reason"],
                    ({"reason": trace["reason"]},),
                    blocks=("interpretation",),
                    cycle_ref=cycle_ref,
                )
            )
        return tuple(output)

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
    def _broad_self_state_query(query, self_ref):
        return any(
            restriction.get("operator") == "op:state"
            and restriction.get("args", {}).get("role:subject") == self_ref
            and isinstance(restriction.get("args", {}).get("role:dimension"), str)
            and restriction["args"]["role:dimension"].startswith("?")
            for restriction in query.restrictions
        )

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

    @staticmethod
    def _top_level_capability_refs(projection, assessments):
        capabilities = {item.capability_ref for item in assessments}
        depended_capabilities = {
            edge.get("depends_on")
            for edge in projection.get("dependency_edges", ())
            if edge.get("subject") in capabilities and edge.get("depends_on") in capabilities
        }
        roots = tuple(sorted(capabilities - depended_capabilities))
        return roots or tuple(sorted(capabilities))

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
            response, realization_proof = self.realizer.response(response_csir)
            stages.add(Stage.REALIZE, counts={"surfaces": int(bool(response))})
            stages.add(Stage.VERIFY, counts={"verified": int(bool(realization_proof.get("verified")))})
            common_ground = None
            if response and realization_proof.get("verified"):
                with self.s.db:
                    common_ground = self.s.commit_common_ground(
                        cycle.participant_frame.conversation_ref, response_csir.response_ref, response_csir.as_dict(),
                        expected_discourse_revision=cycle.discourse_revision,
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

        lattice = self.i.observe(text, cycle.participant_frame)
        stages.add(Stage.OBSERVE, counts={"evidence": len(lattice.envelopes)}, refs=tuple(x.evidence_ref for x in lattice.envelopes))
        stages.add(Stage.ENCODE, counts={"clauses": len(lattice.form_evidence.get("clauses", ())), "unknown": len(lattice.unknown_evidence)})
        grounded_refs = set(lattice.form_evidence.get("grounded_anchors", {}).values())
        stages.add(Stage.GROUND, counts={"grounded_referents": len(grounded_refs)}, refs=tuple(sorted(grounded_refs)))
        state_projections = self._project(grounded_refs | {self.session.self_ref})
        cycle.workspace.put("state_space_projections", state_projections)
        stages.add(Stage.PROJECT_STATE, counts={"projections": len(state_projections)}, refs=tuple(sorted(state_projections)))

        try:
            packet, news, uses, trace = self.i.compose(lattice, cycle.participant_frame, state_projections)
        except AmbiguousReferent as exc:
            packet, news, uses = None, [], []
            trace = {"reason": "ambiguous_referent", "candidates": exc.candidates, "unknown_form_evidence": ({"surface": exc.surface},)}
        except Exception as exc:
            packet, news, uses = None, [], []
            trace = {"reason": "interpretation_error", "error": str(exc)}
        stages.add(Stage.COMPILE, counts={"applications": len(self._packet_applications(packet))})
        stages.add(Stage.RECURRENT_DYNAMICS, counts={"candidate_sets": len(trace.get("clauses", ()))})
        interpretation = self._interpretation(trace, packet)
        frontiers = self._frontiers(trace, cycle.cycle_ref)
        cycle.workspace.put("interpretation_assessment", interpretation)
        cycle.workspace.put("frontier_graph", FrontierGraph(frontiers))
        stages.add(Stage.STABILIZE, counts={"stable": int(packet is not None), "frontiers": len(frontiers)})

        act = build_discourse_act(packet, cycle.participant_frame, trace) if packet else None
        cycle.workspace.put("discourse_act", act)
        stages.add(Stage.BUILD_STRUCTURES, counts={"discourse_acts": int(act is not None), "queries": int(bool(act and act.query))})
        placement = self.epistemic_policy.place(act) if act is not None else None
        cycle.workspace.put("epistemic_placement", placement)
        stages.add(Stage.EPISTEMIC_PLACEMENT, counts={"placements": int(placement is not None), "admitted": int(bool(placement and placement.admitted))})

        runtime_facts = RuntimeObservationProvider.semantic_facts(cycle.self_runtime_view)
        query_result = None
        retrieval = None
        facts = list(runtime_facts)
        by_ref = {fact.ref: fact for fact in facts}
        workspace_trace = {"selected": [], "top_k": self.config.workspace_top_k}
        scoped_epistemic = None
        if act and act.force == FORCE_QUERY and act.query:
            retrieval = self.retriever.retrieve(act.query.restrictions, salient_refs=grounded_refs)
            facts, by_ref = self.inf.closure(seed_facts=retrieval.facts, rules=retrieval.rules, extra=runtime_facts)
            query_result = self.inf.execute_query(
                act.query,
                facts,
                by_ref,
                blocking_frontiers=tuple(x.frontier_ref for x in frontiers),
            )
            proof_refs = sorted({ref for binding in query_result.bindings for ref in binding.proof_refs})
            _, workspace_trace = self.workspace.build(
                facts,
                act.query.as_dict(),
                proof_refs,
                cycle_turn=self._cycle_counter,
            )
            scoped_epistemic = ScopedEpistemicAssessment(
                query_result.query_ref,
                query_result.status,
                tuple(proof_refs),
                (),
                query_result.unresolved_variables,
                query_result.coverage,
            )
        elif act and act.force == FORCE_DESCRIPTION and act.describe_target:
            direct = tuple(self.s.facts_mentioning((act.describe_target,), limit=self.config.retrieval_max_seed_facts))
            facts = list(direct) + list(runtime_facts)
            by_ref = {fact.ref: fact for fact in facts}
            bindings = tuple(QueryBinding({}, (fact.ref,)) for fact in direct if self.s.user_visible_fact(fact))
            query_result = QueryResult(
                stable("description-query", act.describe_target),
                "answered" if bindings else "unknown",
                bindings,
                1.0 if bindings else 0.0,
                len(bindings),
                0,
                (),
                tuple(self.inf.explain(fact, by_ref) for fact in direct),
                tuple(x.frontier_ref for x in frontiers),
            )
            scoped_epistemic = ScopedEpistemicAssessment(query_result.query_ref, query_result.status, tuple(fact.ref for fact in direct), (), (), query_result.coverage)
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
            stages.add(Stage.COMMIT, counts={"applications": len(commit["committed_apps"]), "frontiers": len(commit["frontier_refs"])}, refs=(commit["receipt"]["receipt_ref"],), durable_write=True)
        else:
            stages.add(Stage.COMMIT, counts={"applications": 0, "frontiers": 0})

        self_projection = state_projections.get(self.session.self_ref) or self.state_projector.project(self.session.self_ref).as_dict()
        runtime_observations = RuntimeObservationProvider.observe(cycle.self_runtime_view)
        capability_assessments = self.capability_evaluator.evaluate(self.session.self_ref, self_projection, runtime_observations)
        stages.add(Stage.CAPABILITY_IMPACT, counts={"capabilities": len(capability_assessments)}, refs=tuple(x.assessment_ref for x in capability_assessments))

        required_capability_refs = self._required_capabilities(act)
        candidates = list(self.goal_arbiter.candidates(
            act=act,
            query_result=query_result,
            frontiers=frontiers,
            transition_previews=transition_previews,
            capability_assessments=capability_assessments,
            required_capability_refs=required_capability_refs,
        ))
        if act and act.force == FORCE_QUERY and act.query and self._broad_self_state_query(act.query, self.session.self_ref):
            candidates.append(
                GoalCandidate(
                    stable("goal", "self-capability", act.query.query_ref),
                    "report_self_capability",
                    act.query.query_ref,
                    1.2,
                    {
                        "preferred_capability_refs": list(
                            self._top_level_capability_refs(
                                self_projection, capability_assessments
                            )
                        )
                    },
                )
            )
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
                except Exception:
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
        )
        stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, refs=(response_csir.response_ref,))
        response, realization_proof = self.realizer.response(response_csir)
        stages.add(Stage.REALIZE, counts={"surfaces": int(bool(response))})
        verified = bool(response and realization_proof.get("verified"))
        stages.add(Stage.VERIFY, counts={"verified": int(verified)}, refs=(response_csir.response_ref,))

        common_ground = None
        if mode == MODE_NORMAL and verified and self.config.persist_common_ground:
            with self.s.db:
                common_ground = self.s.commit_common_ground(
                    cycle.participant_frame.conversation_ref,
                    getattr(act, "act_ref", response_csir.response_ref),
                    response_csir.as_dict(),
                    expected_discourse_revision=cycle.discourse_revision,
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
        }
        return result
