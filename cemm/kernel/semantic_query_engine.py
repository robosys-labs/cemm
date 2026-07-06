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


_NON_QUERY_OBLIGATIONS: frozenset = frozenset({
    "social_reply",
    "exit",
    "abstain_policy",
    "store_patch",
    "acknowledge_emotional_context",
})

# Internal concept surface values that must never leak as user-facing answer text.
# These originate from predicate feature extraction (reply_obligation, clarity_required)
# and are semantic scaffolding, not real domain knowledge.
_INTERNAL_SURFACE_VALUES: frozenset = frozenset({
    "reply_obligation",
    "clarity_required",
    "event_candidate",
    "neutral",
})

_NON_ANSWER_TEMPLATES: dict[str, str] = {
    "exit": "session_exit",
    "social_reply": "social_response",
    "store_patch": "store_confirmation",
    "continue_teaching": "teaching_continuation",
    "abstain_policy": "abstain",
    "ask_clarification": "ask_clarification",
    "answer_self_identity": "abstain",
    "answer_self_capability": "abstain",
    "answer_self_knowledge": "abstain",
    "answer_self_model": "abstain",
    "acknowledge_emotional_context": "emotional_response",
}

_OBLIGATION_KIND_TO_RELATION_KEY: dict[str, str] = {
    "answer_self_identity": "answers_identity_as",
    "answer_self_model": "answers_identity_as",
    "answer_self_capability": "capability",
    "answer_self_knowledge": "knows_about",
    "answer_user_profile": "has_name",
}

_OBLIGATION_KIND_TO_SUBJECT_ENTITY: dict[str, str] = {
    "answer_self_identity": "self",
    "answer_self_model": "self",
    "answer_self_capability": "self",
    "answer_self_knowledge": "self",
    "answer_user_profile": "user",
}


class SemanticQueryEngine:
    def __init__(self, relation_algebra: Any | None = None, schema_store: Any | None = None) -> None:
        self._algebra = relation_algebra
        self._schema_store = schema_store

    @staticmethod
    def preferred_relation_key(obligation_kind: str) -> str:
        """Return the preferred relation key for an obligation kind, if any."""
        return _OBLIGATION_KIND_TO_RELATION_KEY.get(obligation_kind, "")

    def build_query(
        self,
        obligation: ObligationFrame,
        relation_frames: list[RelationFrame],
        program: SemanticProgram | None = None,
        uol_graph: Any | None = None,
    ) -> SemanticQuery:
        entry = program.entry_instruction if program is not None else None
        query_kind = self._query_kind_for_obligation(obligation.obligation_kind)

        subject_constraint = QueryConstraint(role="subject")
        object_constraint = QueryConstraint(role="object")
        relation_key = ""

        if entry is not None:
            subject_constraint.surface = entry.surface or ""
            subject_constraint.confidence = entry.confidence

            answerable_frames = [
                f for f in relation_frames
                if f.answerable and not f.structural
            ]

            # For specific self-query obligations, use the obligation kind
            # to determine the relation key directly from the semantic pipeline
            # rather than relying on surface text matching.
            preferred_relation_key = _OBLIGATION_KIND_TO_RELATION_KEY.get(
                obligation.obligation_kind, ""
            )

            if preferred_relation_key:
                subject_entity = _OBLIGATION_KIND_TO_SUBJECT_ENTITY.get(
                    obligation.obligation_kind, "self"
                )
                # Set relation_key and subject entity directly from the mapping.
                # The durable store frames (self-knowledge) are not in turn_frames,
                # so we must not make relation_key dependent on finding matching
                # turn frames. We still try to find matching turn frames to refine
                # object_constraint (e.g. surface text).
                relation_key = preferred_relation_key
                subject_constraint.entity_id = subject_entity

                matching_frames = [
                    f for f in answerable_frames
                    if f.relation_key == preferred_relation_key
                    and f.subject.entity_id == subject_entity
                ]
                if matching_frames:
                    best = self._select_best_frame(matching_frames, entry.surface or "")
                    subject_constraint.concept_id = best.subject.concept_id
                    object_constraint.concept_id = best.object.concept_id
                    object_constraint.entity_id = best.object.entity_id
                    object_constraint.surface = best.object.surface
                    object_constraint.projection_policy = best.projection_policy
            else:
                matching_frames = [
                    f for f in answerable_frames
                    if self._frame_matches_entry(f, entry)
                ]
                if not matching_frames and uol_graph is not None:
                    entry_entity_ids, entry_concept_ids = self._extract_entry_ids(entry, uol_graph)
                    if entry_entity_ids or entry_concept_ids:
                        matching_frames = [
                            f for f in answerable_frames
                            if self._frame_matches_ids(f, entry_entity_ids, entry_concept_ids)
                        ]
                        if obligation.obligation_kind in ("answer_self_model", "answer_self_identity", "answer_self_capability", "answer_self_knowledge"):
                            matching_frames = [
                                f for f in matching_frames
                                if f.subject.entity_id == "self"
                            ]
                            if not matching_frames:
                                matching_frames = [
                                    f for f in answerable_frames
                                    if f.subject.entity_id == "self"
                                ]
                if matching_frames:
                    best = self._select_best_frame(matching_frames, entry.surface or "")
                    relation_key = best.relation_key
                    subject_constraint.concept_id = best.subject.concept_id
                    subject_constraint.entity_id = best.subject.entity_id
                    object_constraint.concept_id = best.object.concept_id
                    object_constraint.entity_id = best.object.entity_id
                    object_constraint.surface = best.object.surface
                    object_constraint.projection_policy = best.projection_policy

        allow_inheritance = True
        allow_inverse = True
        if self._schema_store is not None and relation_key:
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

        if query.query_kind == "none":
            return AnswerBinding(
                binding_id=uuid.uuid4().hex[:16],
                source_query_id=query.query_id,
                query_kind=query.query_kind,
                has_answer=False,
                abstention_reason="",
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
            frames=[f for f in relation_frames if f.answerable and not f.structural],
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
            projection_policy = frame.projection_policy or query.object_constraint.projection_policy
            slot_name, surface, concept_id, entity_id = self._project_frame(
                frame, projection_policy,
            )
            if surface in _INTERNAL_SURFACE_VALUES:
                continue
            if surface == "" and concept_id.replace("concept:", "") in _INTERNAL_SURFACE_VALUES:
                continue
            if surface == "" and concept_id == "" and entity_id in _INTERNAL_SURFACE_VALUES:
                continue
            slot_fill = SlotFill(
                slot_name=slot_name,
                concept_id=concept_id,
                entity_id=entity_id,
                surface=surface,
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

    def _project_frame(
        self,
        frame: RelationFrame,
        projection_policy: str,
    ) -> tuple[str, str, str, str]:
        if projection_policy == "none":
            return "object", "", "", ""
        if projection_policy == "subject":
            return (
                "subject",
                frame.subject.surface or "",
                frame.subject.concept_id or "",
                frame.subject.entity_id or "",
            )
        if projection_policy in ("profile_value", "self_value", "relation_filler"):
            return (
                "object",
                frame.object.surface or "",
                frame.object.concept_id or "",
                frame.object.entity_id or "",
            )
        return (
            "object",
            frame.object.surface or "",
            frame.object.concept_id or "",
            frame.object.entity_id or "",
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
            if len(binding.slot_fills) > 1:
                surfaces = [f.surface for f in binding.slot_fills if f.surface]
                value = "; ".join(surfaces) if surfaces else (best.concept_id or best.entity_id)
            else:
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
                    value=" \u2192 ".join(best.explanation_path),
                    source_binding_id=binding.binding_id,
                    confidence=best.confidence,
                )
        elif obligation.obligation_kind == "store_patch" and program is not None:
            entry = program.entry_instruction
            if entry and entry.surface:
                surface = entry.surface
                lower = surface.lower()
                if lower.startswith("remember "):
                    surface = surface[len("remember "):]
                # Shift first-person pronouns to second-person for system echo
                surface = self._shift_pronouns_for_echo(surface)
                slots["answer"] = RealizationSlot(
                    slot_key="answer",
                    slot_kind="surface",
                    value=surface,
                    source_binding_id=binding.binding_id,
                    confidence=entry.confidence,
                )
                filled = ["answer"]

        if obligation.obligation_kind == "acknowledge_emotional_context":
            preds = obligation.context.get("affordance_predictions", [])
            evaluation_label = "feeling"
            for pred in preds:
                if getattr(pred, "effect_type", "") == "evaluation_shift":
                    patch_tmpl = getattr(pred, "predicted_patch_template", {})
                    shift = patch_tmpl.get("affect_shift", "")
                    if "positive" in shift:
                        evaluation_label = "appreciation"
                    elif "negative" in shift:
                        evaluation_label = "concern"
                    break
            slots["evaluation"] = RealizationSlot(
                slot_key="evaluation",
                slot_kind="surface",
                value=evaluation_label,
                source_binding_id=binding.binding_id,
                confidence=obligation.confidence,
            )
            filled = ["evaluation"]

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
        uol_graph: Any | None = None,
    ) -> tuple[SemanticQuery, AnswerBinding, RealizationContract]:
        query = self.build_query(obligation, relation_frames, program, uol_graph)
        binding = self.execute(query, relation_frames)
        contract = self.build_contract(obligation, binding, program)
        return query, binding, contract

    def _query_kind_for_obligation(self, obligation_kind: str) -> str:
        if obligation_kind in ("answer_concept", "answer_self_model", "answer_self_identity", "answer_self_capability", "answer_self_knowledge", "answer_relation", "answer_user_profile"):
            return "lookup"
        if obligation_kind in ("continue_teaching", "repair"):
            return "lookup"
        if obligation_kind == "store_patch":
            return "none"
        if obligation_kind == "ask_clarification":
            return "clarify"
        if obligation_kind in ("social_reply", "abstain_policy", "exit"):
            return "none"
        return "none"

    @staticmethod
    def _shift_pronouns_for_echo(surface: str) -> str:
        """Shift user's first-person pronouns to second-person for system echo."""
        import re
        replacements = [
            (r'\bI\b', 'you'),
            (r'\bI\'m\b', "you're"),
            (r'\bIm\b', "you're"),
            (r'\bmy\b', 'your'),
            (r'\bme\b', 'you'),
            (r'\bmine\b', 'yours'),
        ]
        result = surface
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def _select_best_frame(frames: list[RelationFrame], question_surface: str) -> RelationFrame:
        """Pick the best frame by confidence. Relation key filtering is handled upstream."""
        return max(frames, key=lambda f: f.confidence)

    def _frame_matches_entry(self, frame: RelationFrame, entry: Any) -> bool:
        if hasattr(entry, "atom_ids"):
            for aid in entry.atom_ids:
                if aid in frame.source_atom_ids:
                    return True
        return False

    def _extract_entry_ids(self, entry: Any, graph: Any) -> tuple[set[str], set[str]]:
        entity_ids: set[str] = set()
        concept_ids: set[str] = set()
        for aid in getattr(entry, "atom_ids", []):
            atom = graph.atoms.get(aid)
            if atom is None:
                continue
            if atom.kind in ("entity", "self"):
                entity_ids.add(atom.key.replace("entity:", "").replace("self:", ""))
            # Look up concept resolution for this atom to get the canonical concept_id
            for cr in getattr(graph, "concept_resolutions", []):
                if cr.atom_id == atom.id:
                    concept_ids.add(cr.concept_id)
                    break
            else:
                # No concept resolution found — derive from atom key
                if atom.kind == "concept":
                    concept_ids.add(atom.key if atom.key.startswith("concept:") else f"concept:{atom.key}")
                elif atom.kind in ("entity", "self") and atom.key not in ("user", "self", "world", "conversation", "memory"):
                    concept_ids.add(f"concept:{atom.key}")
        return entity_ids, concept_ids

    def _frame_matches_ids(
        self,
        frame: RelationFrame,
        entity_ids: set[str],
        concept_ids: set[str],
    ) -> bool:
        for eid in entity_ids:
            if frame.subject.entity_id == eid or frame.object.entity_id == eid:
                return True
        for cid in concept_ids:
            if frame.subject.concept_id == cid or frame.object.concept_id == cid:
                return True
        return False

    def _template_for_obligation(self, obligation: ObligationFrame, binding: AnswerBinding) -> str:
        if not binding.has_answer:
            if binding.abstention_reason.startswith("blocked"):
                return "blocked"
            if binding.abstention_reason:
                return "abstain"
            kind = obligation.obligation_kind
            return _NON_ANSWER_TEMPLATES.get(kind, "general_conversation")

        kind = obligation.obligation_kind
        if kind == "answer_self_identity":
            return "self_identity"
        if kind in ("answer_self_capability", "answer_self_knowledge"):
            return "evidence_answer"
        if kind == "answer_self_model":
            rel_key = binding.best_relation_key if hasattr(binding, "best_relation_key") else ""
            if not rel_key and binding.slot_fills:
                rel_key = binding.slot_fills[0].relation_key
            if rel_key in ("capability", "knows_about", "does", "purpose", "creator", "architecture", "limitation"):
                return "evidence_answer"
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
        if kind == "acknowledge_emotional_context":
            return "emotional_response"
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
        if obligation_kind in ("answer_self_model", "answer_self_identity"):
            if fill.relation_key in ("capability", "knows_about", "does", "purpose", "creator", "architecture", "limitation"):
                return "surface"
            return "self_identity"
        if obligation_kind in ("answer_self_capability", "answer_self_knowledge"):
            return "surface"
        if obligation_kind == "answer_user_profile":
            return "profile"
        if fill.concept_id:
            return "concept"
        if fill.entity_id:
            return "entity"
        return "surface"
