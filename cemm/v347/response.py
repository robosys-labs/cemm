"""Semantic response-goal generation, UOL response planning and realization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .knowledge import RetrievalResult
from .learning import LearningTransaction
from .model import (
    CommunicativeForce,
    DiscourseRelation,
    EmissionProof,
    GraphPatch,
    GapRecord,
    MeaningBundle,
    OperationOutcome,
    PatchCommitResult,
    PatchOperation,
    PatchOperationKind,
    RealizedMessage,
    ReferencePlan,
    Referent,
    ReferentKind,
    ResponseClausePlan,
    ResponseGoalCandidate,
    RoundTripAssessment,
    TruthAssessment,
    TruthStatus,
    UOLResponsePlan,
    semantic_hash,
)
from .language import LanguageAnalysisCoordinator
from .schema import LanguagePack, SemanticSchemaStore
from .storage import SemanticStore


class ConversationalTonePlanner:
    """Derive realization tone from explicit policy, discourse and self state.

    Tone is a realization constraint only.  It cannot add, remove or replace a
    semantic clause, and the selected UOL content remains identical across tone
    variants.
    """

    def __init__(self, store: SemanticStore):
        self._store = store

    def derive(
        self,
        context_ref: str,
        explicit: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        explicit = dict(explicit or {})
        requested = str(explicit.get("tone", "")).strip()
        if requested:
            return {**explicit, "tone": requested, "tone_source": "explicit"}

        state_tones: list[tuple[str, str]] = []
        for _, predication, _ in self._store.knowledge_for_predicate(
            "predicate:has_state",
            context_ref=context_ref,
            scope_refs=("global", context_ref),
        ):
            holder = predication.binding("holder")
            dimension = predication.binding("dimension")
            value = predication.binding("value")
            if not holder or holder.referent_refs != ("referent:self",):
                continue
            if not dimension or not value or len(value.referent_refs) != 1:
                continue
            dimension_ref = dimension.referent_refs[0] if dimension.referent_refs else ""
            if dimension_ref not in {
                "referent:dimension:conversational_tone",
                "referent:dimension:emotive_state",
            }:
                continue
            state = self._store.get_referent(value.referent_refs[0])
            payload = state.payload if state and isinstance(state.payload, Mapping) else {}
            tone = str(payload.get("tone_hint", "")).strip()
            if not tone:
                semantic_key = str(payload.get("semantic_key", ""))
                tone = semantic_key.rsplit(":", 1)[-1] if semantic_key else ""
            if tone:
                state_tones.append((tone, value.referent_refs[0]))

        non_neutral = next((item for item in state_tones if item[0] != "neutral"), None)
        if non_neutral:
            return {**explicit, "tone": non_neutral[0], "tone_source": non_neutral[1]}

        for turn in self._store.recent_turns(context_ref, limit=5):
            tone = str(turn.get("metadata", {}).get("conversational_tone", "")).strip()
            if tone:
                return {**explicit, "tone": tone, "tone_source": f"turn:{turn['turn_id']}"}

        if state_tones:
            return {**explicit, "tone": state_tones[0][0], "tone_source": state_tones[0][1]}
        return {**explicit, "tone": "neutral", "tone_source": "default"}


class ResponseGoalGenerator:
    def generate(
        self,
        *,
        bundle: MeaningBundle | None,
        retrieval: RetrievalResult,
        gaps: Iterable[GapRecord],
        commit_results: Iterable[PatchCommitResult],
        learning: LearningTransaction | None,
        operation_outcomes: Iterable[OperationOutcome],
        truth_assessments: Iterable[TruthAssessment] = (),
    ) -> tuple[ResponseGoalCandidate, ...]:
        candidates: list[ResponseGoalCandidate] = []
        commit_results = tuple(commit_results)
        operation_outcomes = tuple(operation_outcomes)
        truth_assessments = tuple(truth_assessments)
        contradictory = tuple(
            item for item in truth_assessments if item.truth_status == TruthStatus.BOTH
        )
        if retrieval.contradicted and not contradictory:
            candidates.append(ResponseGoalCandidate(
                response_goal_id=semantic_hash("response_goal", ("retrieval_contradiction", retrieval.reason)),
                goal_kind="contradiction_disclosure",
                target_proposition_refs=(),
                score=2.2,
                required=True,
                constraints={"reason": retrieval.reason},
            ))
        if contradictory:
            candidates.append(ResponseGoalCandidate(
                response_goal_id=semantic_hash("response_goal", (
                    "contradiction", tuple(item.assessment_id for item in contradictory)
                )),
                goal_kind="contradiction_disclosure",
                target_proposition_refs=(),
                score=2.2,
                required=True,
                constraints={
                    "assessment_refs": tuple(item.assessment_id for item in contradictory),
                    "support_count": sum(len(item.support_knowledge_refs) for item in contradictory),
                    "opposition_count": sum(len(item.opposition_knowledge_refs) for item in contradictory),
                },
                evidence_refs=tuple(dict.fromkeys(
                    ref for item in contradictory for ref in item.evidence_refs
                )),
            ))
        if retrieval.answers and not retrieval.contradicted:
            for answer in retrieval.answers:
                candidates.append(ResponseGoalCandidate(
                    response_goal_id=semantic_hash("response_goal", (
                        "answer", answer.query_proposition_ref, answer.matched_knowledge_ref
                    )),
                    goal_kind="answer",
                    target_proposition_refs=(answer.matched_proposition_ref,),
                    score=1.0 + answer.confidence,
                    required=True,
                    constraints={
                        "query_proposition_ref": answer.query_proposition_ref,
                        "knowledge_ref": answer.matched_knowledge_ref,
                        "variable_bindings": dict(answer.variable_bindings),
                    },
                    evidence_refs=answer.evidence_refs,
                ))
        elif retrieval.knowledge_gap and bundle is not None and self._has_question(bundle):
            candidates.append(ResponseGoalCandidate(
                response_goal_id=semantic_hash("response_goal", (bundle.bundle_id, "knowledge_gap")),
                goal_kind="knowledge_limitation",
                target_proposition_refs=bundle.proposition_refs,
                score=1.3,
                required=True,
                constraints={"reason": retrieval.reason},
                evidence_refs=bundle.graph.evidence_refs,
            ))

        committed = tuple(item for item in commit_results if item.committed)
        failed = tuple(item for item in commit_results if not item.committed)
        if bundle is not None and self._has_assertion(bundle):
            if committed:
                goal_kind = "correction_acknowledgement" if self._has_correction(bundle) else "acknowledgement"
                candidates.append(ResponseGoalCandidate(
                    response_goal_id=semantic_hash("response_goal", (bundle.bundle_id, goal_kind)),
                    goal_kind=goal_kind,
                    target_proposition_refs=bundle.proposition_refs,
                    score=0.95,
                    constraints={"committed_patch_refs": tuple(item.patch_id for item in committed)},
                    evidence_refs=bundle.graph.evidence_refs,
                ))
            elif failed:
                candidates.append(ResponseGoalCandidate(
                    response_goal_id=semantic_hash("response_goal", (bundle.bundle_id, "admission_failed")),
                    goal_kind="admission_failed",
                    target_proposition_refs=bundle.proposition_refs,
                    score=1.1,
                    constraints={"errors": tuple(error for item in failed for error in item.errors)},
                    evidence_refs=bundle.graph.evidence_refs,
                ))

        if learning is not None and learning.frontier:
            candidates.append(ResponseGoalCandidate(
                response_goal_id=semantic_hash("response_goal", (learning.transaction_id, "learning_probe")),
                goal_kind="learning_probe",
                target_proposition_refs=(),
                score=1.15,
                constraints={
                    "dependency_ref": learning.frontier[0].dependency_ref,
                    "expected_kind": learning.frontier[0].expected_kind,
                    "reason": learning.frontier[0].reason,
                },
                evidence_refs=learning.evidence_refs,
            ))

        for outcome in operation_outcomes:
            candidates.append(ResponseGoalCandidate(
                response_goal_id=semantic_hash("response_goal", (outcome.outcome_id, "operation_result")),
                goal_kind="operation_result",
                target_proposition_refs=outcome.observed_proposition_refs,
                score=1.0 if outcome.status != "completed" else 0.85,
                constraints={"status": outcome.status, "errors": outcome.errors},
            ))

        if not candidates:
            gap = next(iter(gaps), None)
            candidates.append(ResponseGoalCandidate(
                response_goal_id=semantic_hash("response_goal", (
                    "clarification", gap.gap_id if gap else "unknown"
                )),
                goal_kind="clarification",
                target_proposition_refs=(),
                score=0.8,
                required=True,
                constraints={
                    "gap_kind": gap.kind.value if gap else "analysis_gap",
                    "target_ref": gap.target_ref if gap else "",
                    "reason": gap.reason if gap else "no_selected_meaning",
                },
                evidence_refs=gap.evidence_refs if gap else (),
            ))
        return tuple(candidates)

    @staticmethod
    def _has_question(bundle: MeaningBundle) -> bool:
        return any(
            str((bundle.graph.referents[ref].payload or {}).get("communicative_force")) == "ask"
            for ref in bundle.proposition_refs
            if ref in bundle.graph.referents
        )

    @staticmethod
    def _has_assertion(bundle: MeaningBundle) -> bool:
        return any(
            str((bundle.graph.referents[ref].payload or {}).get("communicative_force")) in {"assert", "correct"}
            for ref in bundle.proposition_refs
            if ref in bundle.graph.referents
        )

    @staticmethod
    def _has_correction(bundle: MeaningBundle) -> bool:
        return any(
            str((bundle.graph.referents[ref].payload or {}).get("communicative_force")) == "correct"
            for ref in bundle.proposition_refs
            if ref in bundle.graph.referents
        )


class ResponseRanker:
    def select(self, candidates: Iterable[ResponseGoalCandidate]) -> tuple[ResponseGoalCandidate, ...]:
        ranked = sorted(candidates, key=lambda item: (item.required, item.score), reverse=True)
        selected: list[ResponseGoalCandidate] = []
        seen_kinds = set()
        for candidate in ranked:
            if candidate.goal_kind == "answer":
                selected.append(candidate)
                continue
            if candidate.goal_kind in seen_kinds:
                continue
            if candidate.goal_kind == "acknowledgement" and any(item.goal_kind == "answer" for item in selected):
                continue
            selected.append(candidate)
            seen_kinds.add(candidate.goal_kind)
            if len(selected) >= 3:
                break
        return tuple(selected)


class ReferencePlanner:
    """Choose semantic reference strategies before language realization."""

    def __init__(self, store: SemanticStore):
        self._store = store

    def plan(
        self, clauses: Iterable[ResponseClausePlan], *, language_tag: str
    ) -> tuple[ReferencePlan, ...]:
        result: list[ReferencePlan] = []
        seen: set[str] = set()
        for clause in clauses:
            for referent_ref in clause.port_bindings.values():
                if not referent_ref.startswith("referent:") or referent_ref in seen:
                    continue
                seen.add(referent_ref)
                referent = self._store.get_referent(referent_ref)
                aliases = self._store.aliases_for(referent_ref, language_tag)
                if referent_ref in {"referent:self", "referent:user"}:
                    strategy = "participant_pronoun"
                elif referent and referent.kind in {ReferentKind.QUANTITY, ReferentKind.TIME, ReferentKind.UNIT}:
                    strategy = "semantic_value"
                elif aliases:
                    strategy = "preferred_alias"
                else:
                    strategy = "descriptive"
                result.append(ReferencePlan(
                    referent_ref=referent_ref,
                    strategy=strategy,
                    preferred_alias=aliases[0] if aliases else "",
                    grammatical_features={},
                ))
        return tuple(result)


class SemanticRoundTripChecker:
    """Verify that realized predicate content is recoverable by the analyzer."""

    def assess(
        self,
        plan: UOLResponsePlan,
        realized_text: str,
        clause_texts: Mapping[str, str],
        pack: LanguagePack,
    ) -> RoundTripAssessment:
        source: list[str] = []
        recovered: list[str] = []
        analyzer = LanguageAnalysisCoordinator({pack.language_tag: pack})
        for clause in plan.clauses:
            text = clause_texts.get(clause.clause_id, "")
            if not text:
                continue
            predicate_ref = str(clause.metadata.get("predicate_schema_ref", ""))
            expected = predicate_ref or clause.semantic_key
            source.append(expected)
            if predicate_ref:
                lattice = analyzer.analyze(text, hint=pack.language_tag)
                semantic_refs = {
                    ref for span in lattice.spans for ref in span.semantic_refs
                }
                if predicate_ref in semantic_refs:
                    recovered.append(predicate_ref)
            else:
                # Response moves are closed semantic templates selected by key;
                # successful formatting recovers that exact move contract.
                recovered.append(clause.semantic_key)
        source_refs = tuple(dict.fromkeys(source))
        recovered_refs = tuple(dict.fromkeys(recovered))
        score = len(set(source_refs).intersection(recovered_refs)) / max(1, len(source_refs))
        authorized = bool(realized_text) and score == 1.0
        reasons = () if authorized else ("semantic_round_trip_incomplete",)
        return RoundTripAssessment(
            assessment_id=semantic_hash("round_trip", (
                plan.plan_id, realized_text, source_refs, recovered_refs
            )),
            plan_ref=plan.plan_id,
            realized_text=realized_text,
            source_semantic_refs=source_refs,
            recovered_semantic_refs=recovered_refs,
            semantic_score=score,
            authorized=authorized,
            reasons=reasons,
        )


class EmissionLedgerCompiler:
    def compile(
        self,
        message: RealizedMessage | None,
        *,
        context_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        if message is None:
            return None
        proof = message.proof
        ledger_ref = semantic_hash("emission_ledger", (proof.proof_id, message.language_tag))
        operation = PatchOperation(
            operation_id=f"op:{ledger_ref}",
            kind=PatchOperationKind.UPSERT_EMISSION_LEDGER,
            target_ref=ledger_ref,
            payload={
                "plan_ref": proof.plan_ref,
                "proof_ref": proof.proof_id,
                "language_tag": message.language_tag,
                "surface_hash": semantic_hash("surface", message.text, 64),
                "authorized": proof.authorized,
                "covered_semantic_refs": proof.covered_semantic_refs,
                "schema_revisions": dict(proof.active_schema_revisions),
                "reasons": proof.reasons,
            },
        )
        return GraphPatch(
            patch_id=semantic_hash("patch:emission_ledger", ledger_ref),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:emission_gate",
            evidence_refs=proof.evidence_refs,
            operations=(operation,),
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
        )


class UOLResponsePlanner:
    def __init__(self, store: SemanticStore, schemas: SemanticSchemaStore):
        self._store = store
        self._schemas = schemas
        self._references = ReferencePlanner(store)

    def plan(
        self,
        selected: Iterable[ResponseGoalCandidate],
        *,
        target_language: str,
        tone_constraints: Mapping[str, Any] | None = None,
    ) -> UOLResponsePlan | None:
        selected = tuple(selected)
        if not selected:
            return None
        clauses: list[ResponseClausePlan] = []
        reference_refs: set[str] = set()
        provenance: list[str] = []
        for index, goal in enumerate(selected):
            if goal.goal_kind == "answer":
                clause = self._answer_clause(goal, index)
            else:
                clause = ResponseClausePlan(
                    clause_id=f"response_clause:{index}",
                    communicative_force=(
                        CommunicativeForce.ASK if goal.goal_kind in {"clarification", "learning_probe"}
                        else CommunicativeForce.ACKNOWLEDGE
                    ),
                    proposition_ref=goal.target_proposition_refs[0] if goal.target_proposition_refs else None,
                    semantic_key=goal.goal_kind,
                    port_bindings={
                        str(key): str(value)
                        for key, value in goal.constraints.items()
                        if isinstance(value, (str, int, float))
                    },
                    certainty=min(1.0, max(0.0, goal.score / 2.0)),
                    metadata=dict(goal.constraints),
                )
            if clause is None:
                continue
            clauses.append(clause)
            reference_refs.update(
                value for value in clause.port_bindings.values() if value.startswith("referent:")
            )
            provenance.extend(goal.evidence_refs)
        if not clauses:
            return None
        references = self._references.plan(clauses, language_tag=target_language)
        coherence = tuple(
            DiscourseRelation(
                relation_id=semantic_hash("response:coherence", (left.clause_id, right.clause_id)),
                relation_kind="coordination",
                source_ref=left.clause_id,
                target_ref=right.clause_id,
                confidence=1.0,
            )
            for left, right in zip(clauses, clauses[1:])
        )
        information_structure = {
            clause.clause_id: ("focus" if index == 0 else "continuation")
            for index, clause in enumerate(clauses)
        }
        return UOLResponsePlan(
            plan_id=semantic_hash("response_plan", (
                tuple(item.response_goal_id for item in selected), target_language
            )),
            response_goal_refs=tuple(item.response_goal_id for item in selected),
            target_language=target_language,
            clauses=tuple(clauses),
            discourse_order=tuple(clause.clause_id for clause in clauses),
            reference_plans=references,
            tone_constraints=dict(tone_constraints or {}),
            coverage_requirements=tuple(clause.clause_id for clause in clauses if not clause.optional),
            provenance_refs=tuple(dict.fromkeys(provenance)),
            information_structure=information_structure,
            coherence_relations=coherence,
            response_context_ref="actual",
        )

    def _answer_clause(self, goal: ResponseGoalCandidate, index: int) -> ResponseClausePlan | None:
        proposition_ref = goal.target_proposition_refs[0]
        proposition = self._store.get_referent(proposition_ref)
        if proposition is None:
            return None
        payload = proposition.payload or {}
        predication_refs = tuple(payload.get("predication_refs", ()))
        if not predication_refs:
            return None
        predication = self._store.get_predication(str(predication_refs[0]))
        if predication is None:
            return None
        schema = self._schemas.predicate(predication.predicate_schema_ref)
        bindings: dict[str, str] = {}
        for binding in predication.bindings:
            if len(binding.referent_refs) == 1:
                bindings[binding.port_id] = binding.referent_refs[0]
        return ResponseClausePlan(
            clause_id=f"response_clause:{index}",
            communicative_force=CommunicativeForce.ASSERT,
            proposition_ref=proposition_ref,
            semantic_key=f"answer:{schema.semantic_key}",
            port_bindings=bindings,
            certainty=goal.score / (goal.score + 1.0),
            attribution_ref=str(payload.get("attribution_ref") or ""),
            metadata={
                "predicate_schema_ref": predication.predicate_schema_ref,
                "knowledge_ref": goal.constraints.get("knowledge_ref", ""),
                "query_proposition_ref": goal.constraints.get("query_proposition_ref", ""),
            },
        )


class RealizationCoordinator:
    """Language-pack-only realization with semantic coverage proof."""

    def __init__(
        self,
        store: SemanticStore,
        schemas: SemanticSchemaStore,
        language_packs: Mapping[str, LanguagePack],
    ):
        self._store = store
        self._schemas = schemas
        self._packs = dict(language_packs)
        self._round_trip = SemanticRoundTripChecker()

    def realize(self, plan: UOLResponsePlan | None) -> RealizedMessage | None:
        if plan is None:
            return None
        pack = self._packs.get(plan.target_language)
        if pack is None:
            return self._blocked(plan, "unsupported_target_language")
        clause_texts: dict[str, str] = {}
        covered: list[str] = []
        blocked: list[str] = []
        reasons: list[str] = []
        schema_revisions: dict[str, int] = {}
        for clause_id in plan.discourse_order:
            clause = next((item for item in plan.clauses if item.clause_id == clause_id), None)
            if clause is None:
                blocked.append(clause_id)
                reasons.append(f"missing_clause:{clause_id}")
                continue
            text, clause_covered, clause_reason, schema_revision = self._realize_clause(
                clause, pack, plan.tone_constraints, plan.reference_plans
            )
            if text:
                clause_texts[clause.clause_id] = text
                covered.extend(clause_covered)
                if schema_revision:
                    schema_revisions.update(schema_revision)
            else:
                blocked.append(clause.clause_id)
                reasons.append(clause_reason or f"unrealized:{clause.clause_id}")
        missing_required = [ref for ref in plan.coverage_requirements if ref not in clause_texts]
        text = " ".join(clause_texts[item] for item in plan.discourse_order if item in clause_texts)
        preliminary_authorized = not missing_required and not blocked
        round_trip = self._round_trip.assess(plan, text, clause_texts, pack)
        authorized = preliminary_authorized and round_trip.authorized
        if not round_trip.authorized:
            reasons.extend(round_trip.reasons)
        plan_fingerprint = semantic_hash("response_plan_fingerprint", plan, 64)
        proof = EmissionProof(
            proof_id=semantic_hash("emission_proof", (
                plan.plan_id, tuple(clause_texts), tuple(blocked), tuple(covered), round_trip.assessment_id
            )),
            plan_ref=plan.plan_id,
            realized_clause_refs=tuple(clause_texts),
            covered_semantic_refs=tuple(dict.fromkeys(covered)),
            blocked_semantic_refs=tuple(blocked),
            active_schema_revisions=schema_revisions,
            evidence_refs=plan.provenance_refs,
            authorized=authorized,
            reasons=tuple(dict.fromkeys(reasons)),
            round_trip_checked=True,
            round_trip_score=round_trip.semantic_score,
            plan_fingerprint=plan_fingerprint,
            store_revision=self._store.revision,
        )
        if not authorized:
            text = ""
        return RealizedMessage(
            text=text,
            language_tag=plan.target_language,
            clause_texts=clause_texts,
            proof=proof,
        )

    def _realize_clause(
        self,
        clause: ResponseClausePlan,
        pack: LanguagePack,
        tone_constraints: Mapping[str, Any],
        reference_plans: tuple[ReferencePlan, ...],
    ) -> tuple[str, tuple[str, ...], str, dict[str, int]]:
        realization = pack.realization
        if clause.semantic_key.startswith("answer:"):
            predicate_key = clause.semantic_key.split(":", 1)[1]
            templates = realization.get("predicate_answers", {})
            tone = str(tone_constraints.get("tone", "neutral"))
            tone_template = (
                realization.get("tone_variants", {}).get(tone, {}).get(clause.semantic_key)
            )
            template = tone_template or templates.get(predicate_key)
            if not template:
                return "", (), f"missing_predicate_realization:{predicate_key}", {}
            predicate_ref = str(clause.metadata.get("predicate_schema_ref", f"predicate:{predicate_key}"))
            try:
                schema = self._schemas.predicate(predicate_ref)
            except KeyError:
                return "", (), f"inactive_predicate:{predicate_ref}", {}
            slots: dict[str, str] = {}
            covered = [clause.proposition_ref] if clause.proposition_ref else []
            for port_id, referent_ref in clause.port_bindings.items():
                referent = self._store.get_referent(referent_ref)
                if referent is None:
                    return "", tuple(covered), f"missing_referent:{referent_ref}", {}
                slots[port_id] = self._reference(
                    referent, pack, grammatical_role=port_id, reference_plans=reference_plans
                )
                if not slots[port_id]:
                    return "", tuple(covered), f"unrealizable_referent:{referent_ref}", {}
                covered.append(referent_ref)
            variant = self._select_template_variant(template, clause.port_bindings)
            try:
                text = str(variant).format(**slots)
            except KeyError as exc:
                return "", tuple(covered), f"uncovered_template_slot:{exc.args[0]}", {}
            return text.strip(), tuple(covered), "", {schema.schema_ref: schema.revision}
        tone = str(tone_constraints.get("tone", "neutral"))
        tone_template = (
            pack.realization.get("tone_variants", {}).get(tone, {}).get(clause.semantic_key)
        )
        template = tone_template or pack.realization.get("response_moves", {}).get(clause.semantic_key)
        if not template:
            return "", (), f"missing_response_move:{clause.semantic_key}", {}
        slots = {key: str(value) for key, value in clause.port_bindings.items()}
        try:
            text = str(template).format(**slots)
        except KeyError as exc:
            return "", (), f"uncovered_response_slot:{exc.args[0]}", {}
        covered = (clause.proposition_ref,) if clause.proposition_ref else (clause.clause_id,)
        return text.strip(), covered, "", {}

    @staticmethod
    def _select_template_variant(template: Any, bindings: Mapping[str, str]) -> str:
        if isinstance(template, str):
            return template
        if not isinstance(template, Mapping):
            return ""
        holder = bindings.get("holder") or bindings.get("subject") or ""
        if holder == "referent:self" and "self" in template:
            return str(template["self"])
        if holder == "referent:user" and "user" in template:
            return str(template["user"])
        return str(template.get("default", next(iter(template.values()), "")))

    def _reference(
        self, referent: Referent, pack: LanguagePack, *, grammatical_role: str,
        reference_plans: tuple[ReferencePlan, ...] = (),
    ) -> str:
        references = pack.realization.get("references", {})
        if referent.referent_id == "referent:self":
            forms = references.get("self", {})
            return str(forms.get(grammatical_role) or forms.get("default") or "")
        if referent.referent_id == "referent:user":
            forms = references.get("user", {})
            return str(forms.get(grammatical_role) or forms.get("default") or "")
        payload = referent.payload or {}
        if isinstance(payload, Mapping):
            if referent.kind == ReferentKind.QUANTITY:
                magnitude = str(payload.get("magnitude", ""))
                unit_ref = payload.get("unit_ref")
                if unit_ref:
                    unit = self._store.get_referent(str(unit_ref))
                    unit_text = self._reference(
                        unit, pack, grammatical_role="unit", reference_plans=reference_plans
                    ) if unit else ""
                    return " ".join(item for item in (magnitude, unit_text) if item)
                return magnitude
            if referent.kind == ReferentKind.TEXT:
                for key in ("text", "name", "label"):
                    if payload.get(key):
                        return str(payload[key])
        reference_plan = next((
            item for item in reference_plans if item.referent_ref == referent.referent_id
        ), None)
        if reference_plan and reference_plan.preferred_alias:
            return reference_plan.preferred_alias
        aliases = self._store.aliases_for(referent.referent_id, pack.language_tag)
        if aliases:
            return aliases[0]
        if isinstance(payload, Mapping):
            for key in ("name", "label", "semantic_key", "text"):
                if payload.get(key):
                    return str(payload[key])
        return ""

    def _blocked(self, plan: UOLResponsePlan, reason: str) -> RealizedMessage:
        proof = EmissionProof(
            proof_id=semantic_hash("emission_proof", (plan.plan_id, reason)),
            plan_ref=plan.plan_id,
            realized_clause_refs=(),
            covered_semantic_refs=(),
            blocked_semantic_refs=plan.coverage_requirements,
            active_schema_revisions={},
            evidence_refs=plan.provenance_refs,
            authorized=False,
            reasons=(reason,),
            round_trip_checked=False,
            round_trip_score=0.0,
            plan_fingerprint=semantic_hash("response_plan_fingerprint", plan, 64),
            store_revision=self._store.revision,
        )
        return RealizedMessage(text="", language_tag=plan.target_language, clause_texts={}, proof=proof)
