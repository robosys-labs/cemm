"""SemanticQueryEngine — build and execute SemanticQuery over relation frames.

The breakthrough module: closes the loop between the v4.2 semantic stack
(SemanticProgram → ObligationFrame → RelationFrames) and the response
pipeline. Instead of keyword-based claim retrieval and hardcoded if/else
template selection, the engine:

1. Builds a SemanticQuery from the ObligationFrame + RelationFrames
2. Executes the query against the RelationAlgebra + PredicateSchemaStore
3. Produces an AnswerBinding with slot fills, evidence, and explanation paths
4. Derives a RealizationContract from the ObligationFrame + AnswerBinding

This makes the v4.2 semantic stack actually drive query answering,
not just produce diagnostics.
"""

from __future__ import annotations

import uuid
from typing import Any

from ..types.answer_binding import AnswerBinding, SlotFill
from ..types.obligation_frame import ObligationFrame
from ..types.realization_contract import RealizationContract, RealizationSlot
from ..types.relation_frame import RelationFrame
from ..types.semantic_program import SemanticProgram
from ..types.semantic_query import QueryConstraint, SemanticQuery


class SemanticQueryEngine:
    def __init__(self, relation_algebra: Any | None = None, schema_store: Any | None = None) -> None:
        self._algebra = relation_algebra
        self._schema_store = schema_store

    def build_query(
        self,
        obligation: ObligationFrame,
        relation_frames: list[RelationFrame],
        program: SemanticProgram | None = None,
    ) -> SemanticQuery:
        entry = program.entry_instruction if program is not None else None
        query_kind = self._query_kind_for_obligation(obligation.obligation_kind)

        subject_constraint = QueryConstraint(role="subject")
        object_constraint = QueryConstraint(role="object")
        relation_key = ""

        if entry is not None:
            subject_constraint.surface = entry.surface or ""
            subject_constraint.confidence = entry.confidence

            matching_frames = [
                f for f in relation_frames
                if self._frame_matches_entry(f, entry)
            ]
            if matching_frames:
                best = max(matching_frames, key=lambda f: f.confidence)
                relation_key = best.relation_key
                subject_constraint.concept_id = best.subject.concept_id
                subject_constraint.entity_id = best.subject.entity_id
                object_constraint.concept_id = best.object.concept_id
                object_constraint.entity_id = best.object.entity_id
                object_constraint.surface = best.object.surface

        if not relation_key and relation_frames:
            relation_key = relation_frames[0].relation_key

        allow_inheritance = True
        allow_inverse = True
        if self._schema_store is not None:
            allow_inheritance = self._schema_store.inherits(relation_key)
            inverse_keys = self._schema_store.inverse_of(relation_key)
            allow_inverse = bool(inverse_keys)

        return SemanticQuery(
            query_id=uuid.uuid4().hex[:16],
            source_obligation_id=obligation.primary_instruction_id,
            query_kind=query_kind,
            relation_key=relation_key,
            subject_constraint=subject_constraint,
            object_constraint=object_constraint,
            allow_inheritance=allow_inheritance,
            allow_inverse=allow_inverse,
            evidence_policy=obligation.evidence_policy,
            required_slots=list(obligation.required_slots),
            blocked_by=list(obligation.blocked_by),
            confidence=obligation.confidence,
        )

    def execute(
        self,
        query: SemanticQuery,
        relation_frames: list[RelationFrame],
    ) -> AnswerBinding:
        if query.blocked_by:
            return AnswerBinding(
                binding_id=uuid.uuid4().hex[:16],
                source_query_id=query.query_id,
                query_kind=query.query_kind,
                has_answer=False,
                abstention_reason=f"blocked:{','.join(query.blocked_by)}",
                evidence_policy=query.evidence_policy,
            )

        if not query.relation_key or self._algebra is None:
            return AnswerBinding(
                binding_id=uuid.uuid4().hex[:16],
                source_query_id=query.query_id,
                query_kind=query.query_kind,
                has_answer=False,
                abstention_reason="no_relation_key_or_algebra",
                evidence_policy=query.evidence_policy,
            )

        results = self._algebra.query_subject(
            relation_key=query.relation_key,
            subject_concept_id=query.subject_constraint.concept_id,
            subject_entity_id=query.subject_constraint.entity_id,
            object_concept_id=query.object_constraint.concept_id,
            object_entity_id=query.object_constraint.entity_id,
            frames=relation_frames,
            allow_inheritance=query.allow_inheritance,
            allow_inverse=query.allow_inverse,
        )

        if not results:
            return AnswerBinding(
                binding_id=uuid.uuid4().hex[:16],
                source_query_id=query.query_id,
                query_kind=query.query_kind,
                has_answer=False,
                abstention_reason="no_matches",
                evidence_policy=query.evidence_policy,
            )

        slot_fills: list[SlotFill] = []
        matched_ids: list[str] = []
        explanations: list[list[str]] = []

        for frame in results:
            slot_fill = SlotFill(
                slot_name="object",
                concept_id=frame.object.concept_id,
                entity_id=frame.object.entity_id,
                surface=frame.object.surface,
                relation_key=frame.relation_key,
                source_frame_ids=[frame.relation_id],
                evidence_refs=list(frame.evidence_refs),
                confidence=frame.confidence,
                is_inherited=bool(frame.inherited_from),
            )
            if self._algebra is not None:
                slot_fill.explanation_path = self._algebra.explain_path(frame, relation_frames)
                explanations.append(slot_fill.explanation_path)
            slot_fills.append(slot_fill)
            matched_ids.append(frame.relation_id)

        best_conf = max(f.confidence for f in results) if results else 0.0

        return AnswerBinding(
            binding_id=uuid.uuid4().hex[:16],
            source_query_id=query.query_id,
            query_kind=query.query_kind,
            slot_fills=slot_fills,
            matched_frame_ids=matched_ids,
            explanation_paths=explanations,
            has_answer=bool(slot_fills),
            confidence=best_conf,
            evidence_policy=query.evidence_policy,
        )

    def build_contract(
        self,
        obligation: ObligationFrame,
        binding: AnswerBinding,
        program: SemanticProgram | None = None,
    ) -> RealizationContract:
        response_mode = obligation.response_mode
        intent = obligation.obligation_kind
        template_key = self._template_for_obligation(obligation, binding)

        filled = [f.slot_name for f in binding.slot_fills if f.concept_id or f.entity_id or f.surface]
        unfilled = [s for s in obligation.required_slots if s not in filled]

        explanation_required = obligation.evidence_policy == "required" and binding.has_answer
        abstention_reason = binding.abstention_reason if not binding.has_answer else ""

        slots: dict[str, RealizationSlot] = {}
        if binding.slot_fills:
            best = max(binding.slot_fills, key=lambda f: f.confidence)
            slot_kind = self._slot_kind_for_obligation(obligation.obligation_kind, best)
            value = best.surface or best.concept_id or best.entity_id
            if value:
                slots["answer"] = RealizationSlot(
                    slot_key="answer",
                    slot_kind=slot_kind,
                    value=value,
                    source_binding_id=binding.binding_id,
                    source_relation_id=best.source_frame_ids[0] if best.source_frame_ids else "",
                    confidence=best.confidence,
                )
            if best.explanation_path:
                slots["explanation"] = RealizationSlot(
                    slot_key="explanation",
                    slot_kind="explanation",
                    value=" → ".join(best.explanation_path),
                    source_binding_id=binding.binding_id,
                    confidence=best.confidence,
                )

        return RealizationContract(
            contract_id=uuid.uuid4().hex[:16],
            source_obligation_id=obligation.primary_instruction_id,
            source_binding_id=binding.binding_id,
            response_mode=response_mode,
            intent=intent,
            template_key=template_key,
            evidence_policy=obligation.evidence_policy,
            write_policy=obligation.write_policy,
            verification_level=self._verification_level(obligation, binding),
            required_slots=list(obligation.required_slots),
            filled_slots=filled,
            unfilled_slots=unfilled,
            explanation_required=explanation_required,
            explanation_paths=list(binding.explanation_paths),
            abstention_reason=abstention_reason,
            confidence=binding.confidence,
            slots=slots,
        )

    def run(
        self,
        obligation: ObligationFrame,
        relation_frames: list[RelationFrame],
        program: SemanticProgram | None = None,
    ) -> tuple[SemanticQuery, AnswerBinding, RealizationContract]:
        query = self.build_query(obligation, relation_frames, program)
        binding = self.execute(query, relation_frames)
        contract = self.build_contract(obligation, binding, program)
        return query, binding, contract

    def _query_kind_for_obligation(self, obligation_kind: str) -> str:
        if obligation_kind in ("answer_concept", "answer_self_model", "answer_relation", "answer_user_profile"):
            return "lookup"
        if obligation_kind in ("continue_teaching", "repair"):
            return "lookup"
        if obligation_kind == "store_patch":
            return "assert"
        if obligation_kind == "ask_clarification":
            return "clarify"
        if obligation_kind in ("social_reply", "abstain_policy", "exit"):
            return "none"
        return "none"

    def _frame_matches_entry(self, frame: RelationFrame, entry: Any) -> bool:
        if hasattr(entry, "atom_ids"):
            for aid in entry.atom_ids:
                if aid in frame.source_atom_ids:
                    return True
        return False

    def _template_for_obligation(self, obligation: ObligationFrame, binding: AnswerBinding) -> str:
        if not binding.has_answer:
            if binding.abstention_reason.startswith("blocked"):
                return "blocked"
            return "abstain"
        kind = obligation.obligation_kind
        if kind == "answer_self_model":
            return "self_identity"
        if kind in ("answer_concept", "answer_relation"):
            return "evidence_answer"
        if kind == "answer_user_profile":
            return "user_profile"
        if kind == "continue_teaching":
            return "teaching_continuation"
        if kind == "store_patch":
            return "store_confirmation"
        if kind == "social_reply":
            return "social_response"
        if kind == "ask_clarification":
            return "ask_clarification"
        if kind == "exit":
            return "session_exit"
        return "general_conversation"

    def _verification_level(self, obligation: ObligationFrame, binding: AnswerBinding) -> str:
        if obligation.evidence_policy == "required" and not binding.evidence_refs_present():
            return "strict"
        if obligation.evidence_policy == "required":
            return "normal"
        return "lenient"

    def _slot_kind_for_obligation(self, obligation_kind: str, fill: SlotFill) -> str:
        if obligation_kind == "answer_self_model":
            return "self_identity"
        if obligation_kind == "answer_user_profile":
            return "profile"
        if fill.concept_id:
            return "concept"
        if fill.entity_id:
            return "entity"
        return "surface"
