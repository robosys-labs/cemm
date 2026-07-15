"""ResponsePlanner — sole public-content authority.

This replacement fails closed on missing epistemic assessments and produces
language-neutral teaching/dialogue items instead of vague response labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable
from uuid import uuid4

from ..model.message import (
    LexicalRequirement,
    MessageClauseSpec,
    MessageContentItem,
    MessageRoleValue,
    RhetoricalRelation,
    SemanticMessagePlan,
)
from ..model.epistemic import EpistemicAssessment
from ..model.execution import ExecutionLedger
from ..model.mutation import CommitOutcome


class EpistemicStance(str, Enum):
    ASSERTED = "asserted"
    REPORTED = "reported"
    PROVISIONAL = "provisional"
    CONTESTED = "contested"
    HEDGED = "hedged"
    STALE = "stale"
    DENIED = "denied"


class DiscourseFunction(str, Enum):
    INFORM = "inform"
    QUERY = "query"
    REQUEST = "request"
    ACKNOWLEDGE = "acknowledge"
    CORRECT = "corrects"
    PROMISE = "promise"
    REFUSE = "refuse"
    REPAIR = "repair"


@dataclass(frozen=True, slots=True)
class ContentSelectionInput:
    proposition_refs: tuple[str, ...] = ()
    assessments: tuple[EpistemicAssessment, ...] = ()
    commit_outcome: CommitOutcome | None = None
    execution_ledger: ExecutionLedger | None = None
    goal_refs: tuple[str, ...] = ()
    discourse_state_refs: tuple[str, ...] = ()
    repair_obligation_refs: tuple[str, ...] = ()
    addressee_ref: str = ""
    language: str = "und"
    channel: str = "text"

    # v3.4.1 canonical context
    selected_interpretations: tuple[Any, ...] = ()
    grounding_assessments: tuple[Any, ...] = ()
    retrieval_results: tuple[Any, ...] = ()
    knowledge_assessments: tuple[Any, ...] = ()
    capability_assessments: tuple[Any, ...] = ()
    gaps: tuple[Any, ...] = ()
    learning_transactions: tuple[Any, ...] = ()
    dialogue_resolution: Any | None = None
    dialogue_obligations: tuple[Any, ...] = ()
    surface_evidence: tuple[Any, ...] = ()


class ResponsePlanner:
    """Select only content justified by semantic/epistemic control records."""

    def plan_response(self, selection: ContentSelectionInput) -> SemanticMessagePlan:
        items: list[MessageContentItem] = []

        items.extend(self._plan_repairs(selection))

        dialogue_item = self._plan_dialogue_resolution(selection)
        if dialogue_item is not None:
            items.append(dialogue_item)

        if dialogue_item is None:
            probe = self._plan_learning_probe(selection)
            if probe is not None:
                items.append(probe)

        capability_item = self._plan_self_capability_status(selection)
        if capability_item is not None and not items:
            items.append(capability_item)

        social = self._plan_social_surface(selection)
        if social is not None and not items:
            items.append(social)

        # Only propositions with an assessment may become public proposition
        # content. Missing assessment is not equivalent to asserted truth.
        items.extend(self._plan_assessed_propositions(selection))

        if selection.commit_outcome is not None:
            commit_item = self._plan_commit_content(selection.commit_outcome)
            if commit_item is not None:
                items.append(commit_item)

        if not items:
            items.append(self._honest_abstention(selection))

        items = self._order_by_discourse(self._dedupe(items))
        relations = self._build_rhetorical_relations(items)

        return SemanticMessagePlan(
            id=f"msg_plan:{uuid4().hex[:12]}",
            communicative_goal_refs=selection.goal_refs,
            content_items=tuple(items),
            rhetorical_relations=tuple(relations),
            addressee_refs=(selection.addressee_ref,) if selection.addressee_ref else (),
            language=selection.language,
            channel=selection.channel,
        )

    def _plan_dialogue_resolution(
        self, selection: ContentSelectionInput,
    ) -> MessageContentItem | None:
        resolution = selection.dialogue_resolution
        if resolution is None:
            return None
        kind = getattr(resolution, "resolution_kind", "none")
        if kind == "meta_question":
            remaining = tuple(getattr(resolution, "remaining_field_refs", ()) or ())
            target = self._public_surface(getattr(resolution, "target_artifact_ref", ""))
            return MessageContentItem(
                semantic_ref=f"dialogue_explain:{getattr(resolution, 'obligation_ref', '')}",
                discourse_function=DiscourseFunction.QUERY.value,
                stance=EpistemicStance.ASSERTED.value,
                content_kind="dialogue_gap_explanation",
                predicate_key="requires_information",
                clauses=self._gap_explanation_clauses(
                    target, tuple(getattr(resolution, "evidence_refs", ()) or ())
                    or (getattr(resolution, "obligation_ref", ""),),
                ),
                role_values=(
                    MessageRoleValue(
                        role_key="target",
                        value_kind="lexical_mention",
                        surface_hint=target,
                        use_mode="mention",
                        provenance_refs=tuple(getattr(resolution, "evidence_refs", ()) or ()),
                    ),
                    MessageRoleValue(
                        role_key="remaining_fields",
                        value_kind="semantic_keys",
                        semantic_ref="|".join(remaining),
                        use_mode="assert",
                    ),
                ),
                lexical_requirements=(
                    self._lex("requires_information"),
                    self._lex("semantic_distinction"),
                    self._lex("role"),
                    self._lex("person"),
                    self._lex("grammar:quantifier_both"),
                    self._lex("means"),
                    self._mention(target),
                ),
                provenance_refs=tuple(getattr(resolution, "evidence_refs", ()) or ())
                or (getattr(resolution, "obligation_ref", ""),),
            )

        if kind in {"evidence", "correction"}:
            accepted = tuple(getattr(resolution, "accepted_surface_forms", ()) or ())
            remaining = tuple(getattr(resolution, "remaining_field_refs", ()) or ())
            target = self._public_surface(getattr(resolution, "target_artifact_ref", ""))
            requirements = [
                self._lex("explanation"), self._lex("associates"), self._lex("is_incomplete"),
            ]
            if "denotation_role_or_holder" in remaining:
                requirements.extend((
                    self._lex("requires_information"), self._lex("semantic_distinction"),
                    self._lex("role"), self._lex("person"),
                    self._lex("grammar:quantifier_both"), self._lex("means"),
                ))
            elif any(field in remaining for field in ("example", "non_example", "differentiator")):
                requirements.extend((
                    self._lex("requires_information"), self._lex("requests"),
                    self._lex("example"), self._lex("non_example"),
                ))
            if target:
                requirements.append(self._mention(target))
            requirements.extend(self._mention(value) for value in accepted if value)
            return MessageContentItem(
                semantic_ref=f"learning_progress:{getattr(resolution, 'transaction_ref', '')}",
                discourse_function=DiscourseFunction.QUERY.value,
                stance=EpistemicStance.PROVISIONAL.value,
                content_kind="learning_progress",
                predicate_key="requires_information",
                clauses=self._learning_progress_clauses(
                    target, accepted, remaining,
                    tuple(getattr(resolution, "evidence_refs", ()) or ())
                    or (getattr(resolution, "transaction_ref", ""),),
                ),
                role_values=(
                    MessageRoleValue(
                        role_key="target", value_kind="lexical_mention",
                        surface_hint=target, use_mode="mention",
                    ),
                    MessageRoleValue(
                        role_key="accepted", value_kind="surface_mentions",
                        semantic_ref="|".join(accepted), use_mode="mention",
                    ),
                    MessageRoleValue(
                        role_key="remaining_fields", value_kind="semantic_keys",
                        semantic_ref="|".join(remaining), use_mode="assert",
                    ),
                ),
                lexical_requirements=tuple(requirements),
                provenance_refs=tuple(getattr(resolution, "evidence_refs", ()) or ())
                or (getattr(resolution, "transaction_ref", ""),),
            )
        return None

    def _plan_self_capability_status(
        self, selection: ContentSelectionInput,
    ) -> MessageContentItem | None:
        asks_self_condition = False
        for item in selection.selected_interpretations:
            if getattr(item, "communicative_force", "") != "ask":
                continue
            grounding = self._find_predication_grounding(
                getattr(item, "predication_ref", ""),
                selection.grounding_assessments,
            )
            if self._is_self_query_projection(grounding):
                asks_self_condition = True
                break
        if not asks_self_condition:
            return None
        capable = next(
            (
                assessment for assessment in selection.capability_assessments
                if getattr(assessment, "subject_ref", "") == "self"
                and getattr(assessment, "status", "") in {"capable", "degraded"}
                and getattr(assessment, "operation_schema_ref", "")
            ),
            None,
        )
        if capable is None:
            return None
        operation_ref = getattr(capable, "operation_schema_ref", "")
        provenance = tuple(getattr(capable, "evidence_refs", ()) or ()) or (
            f"capability:{operation_ref}",
        )
        return MessageContentItem(
            semantic_ref="self:capability_status",
            discourse_function=DiscourseFunction.INFORM.value,
            stance=(
                EpistemicStance.HEDGED.value
                if getattr(capable, "status", "") == "degraded"
                else EpistemicStance.ASSERTED.value
            ),
            content_kind="self_capability_status",
            predicate_key="capable_of",
            clauses=(self._clause(
                "self:can_answer", "capable_of", "assert", "positive",
                (
                    self._role("agent", "self"),
                    self._role("operation", operation_ref),
                ),
                (self._lex("capable_of"), self._lex("answer_record")),
                provenance,
            ),),
            role_values=(
                MessageRoleValue(
                    role_key="operation",
                    value_kind="semantic_ref",
                    semantic_ref=operation_ref,
                    semantic_key="answer_record",
                    use_mode="assert",
                    provenance_refs=provenance,
                ),
            ),
            lexical_requirements=(self._lex("capable_of"), self._lex("answer_record")),
            provenance_refs=provenance,
        )

    def _plan_learning_probe(
        self, selection: ContentSelectionInput,
    ) -> MessageContentItem | None:
        gap = next(
            (
                gap for gap in selection.gaps
                if getattr(gap, "learnable", False)
                and getattr(gap, "blocked_stage", "") in {"compose", "ground", "know"}
            ),
            None,
        )
        if gap is None:
            return None

        target_ref = getattr(gap, "target_artifact_ref", "")
        target = self._public_surface(target_ref)
        gap_kind = getattr(gap, "gap_kind", "missing_semantic_family")
        missing = tuple(getattr(gap, "missing_fields", ()) or ())
        probe_key = ""
        options = tuple(getattr(gap, "probe_options", ()) or ())
        if options:
            probe_key = getattr(options[0], "idempotency_key", "") or (
                f"probe:{gap.id}:{gap_kind}"
            )

        requirements = [
            self._lex("recognizes_form"),
            self._lex("lexical_form"),
            self._lex("semantic_definition"),
            self._lex("has_usable_definition"),
            self._lex("means"),
            self._lex("person"),
            self._lex("role"),
            self._lex("grammar:quantifier_both"),
        ]
        if target:
            requirements.append(self._mention(target))

        return MessageContentItem(
            semantic_ref=f"learning_probe:{gap.id}",
            discourse_function=DiscourseFunction.QUERY.value,
            stance=EpistemicStance.HEDGED.value,
            content_kind="learning_probe",
            predicate_key="recognizes_form",
            clauses=self._learning_probe_clauses(target, (gap.id,)),
            role_values=(
                MessageRoleValue(
                    role_key="gap_ref", semantic_ref=gap.id,
                    value_kind="gap_ref", use_mode="assert",
                ),
                MessageRoleValue(
                    role_key="target", value_kind="lexical_mention",
                    surface_hint=target, use_mode="mention",
                ),
                MessageRoleValue(
                    role_key="gap_kind", semantic_key=gap_kind,
                    value_kind="semantic_key", use_mode="probe",
                ),
                MessageRoleValue(
                    role_key="missing_fields", semantic_ref="|".join(missing),
                    value_kind="semantic_keys", use_mode="probe",
                ),
                MessageRoleValue(
                    role_key="probe_key", semantic_ref=probe_key,
                    value_kind="control_ref", use_mode="probe",
                ),
            ),
            lexical_requirements=tuple(requirements),
            provenance_refs=(gap.id,),
        )

    def _plan_social_surface(
        self, selection: ContentSelectionInput,
    ) -> MessageContentItem | None:
        cues = []
        for evidence in selection.surface_evidence:
            cues.extend(getattr(evidence, "pragmatic_cues", ()) or ())
        cue_kinds = {getattr(cue, "cue_kind", "") for cue in cues}
        if "greeting" in cue_kinds:
            return MessageContentItem(
                semantic_ref="social:greeting",
                discourse_function=DiscourseFunction.INFORM.value,
                stance=EpistemicStance.ASSERTED.value,
                content_kind="social_greeting",
                predicate_key="greet",
                clauses=self._social_clauses(("surface:greeting",)),
                lexical_requirements=(self._lex("greet"),),
                provenance_refs=tuple(
                    ref
                    for evidence in selection.surface_evidence
                    for ref in getattr(evidence, "source_evidence_refs", ())
                ) or ("surface:greeting",),
            )
        return None

    def _plan_assessed_propositions(
        self, selection: ContentSelectionInput,
    ) -> list[MessageContentItem]:
        result: list[MessageContentItem] = []
        for prop_ref in selection.proposition_refs:
            assessment = self._find_assessment(prop_ref, selection.assessments)
            if assessment is None:
                continue
            if assessment.admissibility not in {"admitted", "attributed_only", "contested"}:
                continue
            # Bare proposition IDs are not realizable semantics. Preserve them
            # only when a caller supplied a semantic realization item through
            # dialogue/commit/self-report paths. Do not emit "regarding prop:...".
        return result

    def _plan_commit_content(self, outcome: CommitOutcome) -> MessageContentItem:
        if not outcome.required_satisfied:
            return MessageContentItem(
                semantic_ref=outcome.mutation_set_ref,
                discourse_function=DiscourseFunction.INFORM.value,
                stance=EpistemicStance.DENIED.value,
                content_kind="commit_failure",
                predicate_key="completes",
                clauses=(self._clause(
                    "commit:failure", "completes", "assert", "negative",
                    (self._role("agent", "self"), self._role("operation", outcome.mutation_set_ref)),
                    (self._lex("completes"),), (outcome.mutation_set_ref,),
                ),),
                lexical_requirements=(self._lex("completes"),),
                provenance_refs=(outcome.mutation_set_ref,),
            )
        return MessageContentItem(
            semantic_ref=outcome.mutation_set_ref,
            discourse_function=DiscourseFunction.INFORM.value,
            stance=EpistemicStance.ASSERTED.value,
            content_kind="commit_success",
            predicate_key="stores",
            clauses=(self._clause(
                "commit:success", "stores", "assert", "positive",
                (self._role("agent", "self"), self._role("artifact", outcome.mutation_set_ref)),
                (self._lex("stores"),), (outcome.mutation_set_ref,),
            ),),
            lexical_requirements=(self._lex("stores"),),
            provenance_refs=(outcome.mutation_set_ref,),
        )

    def _plan_repairs(self, selection: ContentSelectionInput) -> list[MessageContentItem]:
        return [
            MessageContentItem(
                semantic_ref=repair_ref,
                discourse_function=DiscourseFunction.REPAIR.value,
                stance=EpistemicStance.STALE.value,
                content_kind="repair",
                predicate_key="corrects",
                clauses=(self._clause(
                    f"repair:{repair_ref}", "corrects", "assert", "positive",
                    (self._role("agent", "self"), self._role("proposition", repair_ref)),
                    (self._lex("corrects"), self._lex("answer_record")),
                    (repair_ref,),
                ),),
                lexical_requirements=(self._lex("corrects"), self._lex("answer_record")),
                provenance_refs=(repair_ref,),
            )
            for repair_ref in selection.repair_obligation_refs
        ]

    def _honest_abstention(self, selection: ContentSelectionInput) -> MessageContentItem:
        provenance = tuple(
            getattr(gap, "id", "") for gap in selection.gaps if getattr(gap, "id", "")
        ) or ("response:no_admissible_content",)
        return MessageContentItem(
            semantic_ref="response:no_admissible_content",
            discourse_function=DiscourseFunction.INFORM.value,
            stance=EpistemicStance.HEDGED.value,
            content_kind="honest_abstention",
            predicate_key="has_sufficient_information",
            clauses=(self._clause(
                "response:insufficient_information",
                "has_sufficient_information", "assert", "negative",
                (self._role("agent", "self"), self._role("content", "answer_record")),
                (self._lex("information_object"), self._lex("grammar:quantifier_sufficiency")),
                provenance,
            ),),
            lexical_requirements=(
                self._lex("information_object"), self._lex("grammar:quantifier_sufficiency"),
            ),
            provenance_refs=provenance,
        )

    def _learning_probe_clauses(
        self, target: str, provenance: tuple[str, ...],
    ) -> tuple[MessageClauseSpec, ...]:
        mention = self._mention(target)
        return (
            self._clause(
                "probe:recognized_form", "recognizes_form", "assert", "positive",
                (self._role("recognizer", "self"), self._mention_role("lexical_form", target)),
                (self._lex("recognizes_form"), self._lex("lexical_form"), mention),
                provenance,
            ),
            self._clause(
                "probe:missing_definition", "has_usable_definition", "assert", "negative",
                (self._role("holder", "self"), self._mention_role("schema_sense", target)),
                (self._lex("has_usable_definition"), self._lex("semantic_definition"), mention),
                provenance,
            ),
            self._clause(
                "probe:meaning_choice", "means", "ask", "positive",
                (
                    self._mention_role("lexical_form", target),
                    MessageRoleValue(
                        role_key="schema_sense", value_kind="semantic_alternatives",
                        semantic_ref="person|role|grammar:quantifier_both",
                        use_mode="probe", provenance_refs=provenance,
                    ),
                ),
                (
                    self._lex("means", "probe"), self._lex("person", "probe"),
                    self._lex("role", "probe"),
                    self._lex("grammar:quantifier_both", "probe"), mention,
                ),
                provenance,
            ),
        )

    def _gap_explanation_clauses(
        self, target: str, provenance: tuple[str, ...],
    ) -> tuple[MessageClauseSpec, ...]:
        mention = self._mention(target)
        return (
            self._clause(
                "dialogue:need_distinction", "requires_information", "assert", "positive",
                (
                    self._role("agent", "self"),
                    self._role("requirement", "semantic_distinction"),
                ),
                (
                    self._lex("requires_information"),
                    self._lex("semantic_distinction"),
                    self._lex("role"), self._lex("person"), mention,
                ),
                provenance,
            ),
            self._clause(
                "dialogue:meaning_choice", "means", "ask", "positive",
                (
                    self._mention_role("lexical_form", target),
                    self._role("schema_sense", "person|role|grammar:quantifier_both"),
                ),
                (
                    self._lex("means", "probe"), self._lex("role", "probe"),
                    self._lex("person", "probe"),
                    self._lex("grammar:quantifier_both", "probe"), mention,
                ),
                provenance,
            ),
        )

    def _learning_progress_clauses(
        self, target: str, accepted: tuple[str, ...], remaining: tuple[str, ...],
        provenance: tuple[str, ...],
    ) -> tuple[MessageClauseSpec, ...]:
        clauses: list[MessageClauseSpec] = []
        mention = self._mention(target)
        if accepted:
            clauses.append(self._clause(
                "learning:accepted_association", "associates", "assert", "positive",
                (
                    self._role("source", "user"),
                    self._mention_role("left", target),
                    self._role("right", "|".join(accepted)),
                ),
                (self._lex("associates", "qualified"), mention,
                 *(self._mention(value) for value in accepted)),
                provenance, qualification_key="user_asserted",
            ))
        clauses.append(self._clause(
            "learning:incomplete", "is_incomplete", "assert", "positive",
            (self._role("artifact", "semantic_definition"),),
            (self._lex("is_incomplete", "qualified"), self._lex("explanation")),
            provenance, qualification_key="provisional",
        ))
        remaining_set = set(remaining)
        if "denotation_role_or_holder" in remaining_set:
            clauses.extend(self._gap_explanation_clauses(target, provenance))
        elif remaining_set & {"example", "non_example", "differentiator"}:
            clauses.append(self._clause(
                "learning:request_contrast", "requests", "ask", "positive",
                (
                    self._role("speaker", "self"), self._role("addressee", "user"),
                    self._role("content", "example|non_example"),
                ),
                (
                    self._lex("requests", "probe"), self._lex("example", "probe"),
                    self._lex("non_example", "probe"),
                ),
                provenance,
            ))
        return tuple(clauses)

    def _social_clauses(
        self, provenance: tuple[str, ...],
    ) -> tuple[MessageClauseSpec, ...]:
        return (self._clause(
            "social:greet", "greet", "assert", "positive",
            (self._role("source", "self"), self._role("addressee", "user")),
            (self._lex("greet"),), provenance,
        ),)

    @staticmethod
    def _role(key: str, semantic_ref: str) -> MessageRoleValue:
        return MessageRoleValue(
            role_key=key, semantic_ref=semantic_ref, value_kind="semantic_ref",
            provenance_refs=(semantic_ref,) if semantic_ref else (),
        )

    @staticmethod
    def _mention_role(key: str, surface: str) -> MessageRoleValue:
        return MessageRoleValue(
            role_key=key, value_kind="lexical_mention", surface_hint=surface,
            use_mode="mention", provenance_refs=(f"surface:{surface}",) if surface else (),
        )

    @staticmethod
    def _clause(
        clause_ref: str, predicate_key: str, force: str, polarity: str,
        role_values: tuple[MessageRoleValue, ...],
        lexical_requirements: tuple[LexicalRequirement, ...],
        provenance_refs: tuple[str, ...],
        qualification_key: str = "",
    ) -> MessageClauseSpec:
        return MessageClauseSpec(
            clause_ref=clause_ref, predicate_key=predicate_key,
            communicative_force=force, polarity=polarity,
            role_values=role_values, lexical_requirements=lexical_requirements,
            provenance_refs=tuple(ref for ref in provenance_refs if ref),
            qualification_key=qualification_key,
        )

    @staticmethod
    def _lex(key: str, use_mode: str = "assert") -> LexicalRequirement:
        return LexicalRequirement(semantic_key=key, use_mode=use_mode)

    @staticmethod
    def _mention(surface: str) -> LexicalRequirement:
        return LexicalRequirement(
            semantic_key="lexical_mention",
            use_mode="mention",
            surface_hint=surface,
            required=bool(surface),
        )

    @staticmethod
    def _public_surface(ref: str) -> str:
        if not ref:
            return ""
        parts = ref.split(":")
        if parts[0] == "opaque":
            # stable form: opaque:<lang>:<surface>; legacy form:
            # opaque:<surface>:<uuid>
            if len(parts) >= 3 and len(parts[1]) <= 5:
                return parts[2].replace("_", " ")
            if len(parts) >= 2:
                return parts[1].replace("_", " ")
        if ref.startswith("ref:unknown:"):
            return ref.removeprefix("ref:unknown:").replace("_", " ")
        return ""

    @staticmethod
    def _find_assessment(
        prop_ref: str, assessments: tuple[EpistemicAssessment, ...],
    ) -> EpistemicAssessment | None:
        return next((item for item in assessments if item.proposition_ref == prop_ref), None)

    @staticmethod
    def _find_predication_grounding(
        predication_ref: str, grounding_assessments: tuple[Any, ...],
    ) -> Any | None:
        for graph_grounding in grounding_assessments:
            if hasattr(graph_grounding, "for_predication"):
                found = graph_grounding.for_predication(predication_ref)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _is_self_query_projection(grounding: Any | None) -> bool:
        if grounding is None:
            return False
        unresolved = set(getattr(grounding, "unresolved_role_refs", ()) or ())
        query_roles = set(getattr(grounding, "query_role_refs", ()) or ())
        if not unresolved.intersection(query_roles):
            return False
        return any(
            getattr(binding, "grounded_filler_ref", "") == "self"
            for binding in getattr(grounding, "role_bindings", ())
        )

    @staticmethod
    def _dedupe(items: list[MessageContentItem]) -> list[MessageContentItem]:
        seen: set[tuple[str, str]] = set()
        result: list[MessageContentItem] = []
        for item in items:
            key = (item.semantic_ref, item.content_kind)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    _ORDER = {
        DiscourseFunction.REPAIR.value: 0,
        DiscourseFunction.CORRECT.value: 1,
        DiscourseFunction.REFUSE.value: 2,
        DiscourseFunction.INFORM.value: 3,
        DiscourseFunction.QUERY.value: 4,
        DiscourseFunction.REQUEST.value: 5,
        DiscourseFunction.PROMISE.value: 6,
        DiscourseFunction.ACKNOWLEDGE.value: 7,
    }

    def _order_by_discourse(self, items: list[MessageContentItem]) -> list[MessageContentItem]:
        return sorted(items, key=lambda item: self._ORDER.get(item.discourse_function, 99))

    @staticmethod
    def _build_rhetorical_relations(
        items: list[MessageContentItem],
    ) -> list[RhetoricalRelation]:
        relations: list[RhetoricalRelation] = []
        for left, right in zip(items, items[1:]):
            kind = "contrast" if left.stance in {"stale", "denied"} else "elaboration"
            relations.append(RhetoricalRelation(left.semantic_ref, right.semantic_ref, kind))
        return relations

    def validate_plan(self, plan: SemanticMessagePlan) -> bool:
        if plan is None:
            return False
        for item in plan.content_items:
            if not item.semantic_ref or not item.provenance_refs:
                return False
            if item.semantic_ref.startswith(("port:", "placeholder:")):
                return False
            if item.required and not item.all_lexical_requirements():
                return False
        return True
