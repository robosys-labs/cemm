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

import re
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
    "feeling",
    "appreciation",
    "concern",
    "unknown",
    "none",
    "null",
})

# Pattern for state delta surfaces produced by _compile_state_deltas in
# meaning_graph_builder.py: "dimension:direction" (e.g. "preference:increase",
# "energy:decreased"). These are internal state representation, not answers.
_STATE_DELTA_SURFACE_RE = re.compile(r"^[a-z_]+(:\.[a-z_]+)*:[a-z_]+$")


def _is_internal_surface(value: str) -> bool:
    """Check if a surface value is internal scaffolding that must not leak as an answer."""
    if not value:
        return False
    if value in _INTERNAL_SURFACE_VALUES:
        return True
    return bool(_STATE_DELTA_SURFACE_RE.match(value))

_NON_ANSWER_TEMPLATES: dict[str, str] = {
    "exit": "session_exit",
    "social_reply": "social_response",
    "store_patch": "store_confirmation",
    "continue_teaching": "teaching_continuation",
    "abstain_policy": "abstain",
    "ask_clarification": "ask_clarification",
    "repair": "confusion_repair",
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
    "answer_user_profile": "has_property",
}

_RELATION_KEY_LABELS: dict[str, str] = {
    "has_name": "name",
    "has_age": "age",
    "has_alias": "alias",
    "has_role": "role",
    "has_property": "value",
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

            # Known structural relation types that should never be used
            # as answerable frames, even if the structural flag isn't set
            # (e.g., durable store frames don't preserve the flag).
            _NON_ANSWERABLE_KEYS = frozenset({
                "has_role", "causes", "enables", "prevents",
                "before", "after", "refers_to", "modifies",
                "teaches", "asks_about",
                "is_a", "same_as", "part_of", "used_for",
            })
            answerable_frames = [
                f for f in relation_frames
                if f.answerable and not f.structural
                and f.relation_key not in _NON_ANSWERABLE_KEYS
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
                # For user_profile queries, determine relation key from surface
                # text — role/job/title → has_role, everything else → has_property
                if obligation.obligation_kind == "answer_user_profile" and entry is not None:
                    surface_lower = (entry.surface or "").lower()
                    if "job" in surface_lower or "occupation" in surface_lower or "work" in surface_lower or "role" in surface_lower or "title" in surface_lower:
                        preferred_relation_key = "has_role"
                    else:
                        preferred_relation_key = "has_property"
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
                    # Surface-based fallback: match entry surface tokens
                    # against frame subject/object surfaces and concept_ids.
                    # This catches concept queries like "who is the president?"
                    # where the durable store has is_a(president_of_nigeria, tinubu)
                    # but the current turn's atoms don't share IDs with the
                    # original teaching turn's atoms.
                    if not matching_frames and entry is not None:
                        matching_frames = self._match_frames_by_surface(
                            answerable_frames, entry, uol_graph
                        )
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
            if _is_internal_surface(surface):
                continue
            if surface == "" and _is_internal_surface(concept_id.replace("concept:", "")):
                continue
            if surface == "" and concept_id == "" and _is_internal_surface(entity_id):
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
                features=dict(frame.features) if frame.features else {},
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
        template_key = self._template_for_obligation(obligation, binding, program)

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
                if obligation.obligation_kind == "answer_user_profile" and best.relation_key:
                    prop_dim = best.features.get("property_dimension", "")
                    if prop_dim:
                        label = prop_dim
                    else:
                        label = _RELATION_KEY_LABELS.get(best.relation_key, best.relation_key)
                    slots["label"] = RealizationSlot(
                        slot_key="label",
                        slot_kind="profile",
                        value=label,
                        source_binding_id=binding.binding_id,
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
                # Shift pronouns for system echo
                surface = self._shift_pronouns_for_echo(surface)
                # Sanitize before echoing to user
                surface = self._sanitize_echo(surface)
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
        """Shift pronouns bidirectionally for system echo.

        User's first-person pronouns (I, my, me, mine) → second-person (you, your, yours).
        User's second-person pronouns (you, your, yourself) referring to the AI → first-person (I, my, myself).
        Uses placeholder tokens to avoid double-replacement.
        """
        import re
        # Phase 1: first-person → placeholders (user talking about themselves)
        replacements_phase1 = [
            (r'\bI\b', '\x00YOU\x00'),
            (r"\bI'm\b", "\x00YOURE\x00"),
            (r'\bIm\b', "\x00YOURE\x00"),
            (r'\bmy\b', '\x00YOUR\x00'),
            (r'\bme\b', '\x00YOU2\x00'),
            (r'\bmine\b', '\x00YOURS\x00'),
            (r'\bmyself\b', '\x00YOURSELF\x00'),
            (r'\bours\b', '\x00YOURS\x00'),
            (r'\bour\b', '\x00YOUR\x00'),
        ]
        # Phase 2: second-person → first-person (user talking about the AI)
        replacements_phase2 = [
            (r"\byou're\b", "\x00IM\x00"),
            (r"\byoure\b", "\x00IM\x00"),
            (r'\byourself\b', '\x00MYSELF\x00'),
            (r'\byourselves\b', '\x00OURSELVES\x00'),
            (r'\byours\b', '\x00MINE\x00'),
            (r'\byour\b', '\x00MY\x00'),
            (r'\byou\b', '\x00I\x00'),
        ]
        # Phase 3: resolve placeholders to final text
        placeholder_resolves = [
            ('\x00YOU\x00', 'you'),
            ('\x00YOURE\x00', "you're"),
            ('\x00YOUR\x00', 'your'),
            ('\x00YOU2\x00', 'you'),
            ('\x00YOURS\x00', 'yours'),
            ('\x00YOURSELF\x00', 'yourself'),
            ('\x00I\x00', 'I'),
            ('\x00IM\x00', "I'm"),
            ('\x00MY\x00', 'my'),
            ('\x00MYSELF\x00', 'myself'),
            ('\x00MINE\x00', 'mine'),
            ('\x00OURSELVES\x00', 'ourselves'),
        ]
        result = surface
        for pattern, replacement in replacements_phase1:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        for pattern, replacement in replacements_phase2:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        for placeholder, final in placeholder_resolves:
            result = result.replace(placeholder, final)
        return result

    @staticmethod
    def _sanitize_echo(surface: str) -> str:
        """Sanitize user surface before echoing in store confirmation.

        - Strips HTML tags to prevent XSS
        - Removes control characters
        - Limits length to 200 characters
        - Collapses whitespace
        """
        import re
        # Strip HTML tags
        surface = re.sub(r'<[^>]+>', '', surface)
        # Remove control characters (except normal whitespace)
        surface = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', surface)
        # Collapse whitespace
        surface = re.sub(r'\s+', ' ', surface).strip()
        # Limit length
        if len(surface) > 200:
            surface = surface[:197] + '...'
        return surface

    @staticmethod
    def _select_best_frame(frames: list[RelationFrame], question_surface: str) -> RelationFrame:
        """Pick the best frame by token overlap with question, then confidence."""
        import re
        _STOP = frozenset({
            "who", "what", "where", "when", "why", "how", "which",
            "do", "does", "did", "is", "are", "am", "was", "were",
            "can", "could", "would", "should", "will", "might",
            "the", "a", "an", "of", "in", "on", "at", "to", "for",
            "and", "or", "but", "not", "no", "yes",
            "i", "me", "my", "mine", "we", "us", "our",
            "you", "your", "yours", "it", "its", "they", "them",
            "that", "this", "these", "those",
            "self", "user", "world", "conversation", "memory",
        })
        token_re = re.compile(r"[^\W_]+", re.UNICODE)
        q_tokens = {t for t in token_re.findall((question_surface or "").lower()) if t not in _STOP}

        def _frame_score(f: RelationFrame) -> tuple[int, float]:
            if not q_tokens:
                return (0, f.confidence)
            subj = (f.subject.surface or "").lower()
            obj = (f.object.surface or "").lower()
            subj_c = (f.subject.concept_id or "").lower().replace("concept:", "").replace("_", " ")
            obj_c = (f.object.concept_id or "").lower().replace("concept:", "").replace("_", " ")
            frame_tokens: set[str] = set()
            for text in (subj, obj, subj_c, obj_c):
                frame_tokens |= {t for t in token_re.findall(text) if t not in _STOP}
            overlap = len(q_tokens & frame_tokens)
            return (overlap, f.confidence)

        return max(frames, key=_frame_score)

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

    def _match_frames_by_surface(
        self,
        frames: list[RelationFrame],
        entry: Any,
        uol_graph: Any | None = None,
    ) -> list[RelationFrame]:
        """Match frames by surface token overlap with the entry.

        Extracts content tokens from the entry's atom surfaces and the
        entry surface itself, then matches them against frame subject/object
        surfaces and concept_ids. Excludes structural frames (self-knowledge,
        enables, causes, has_role) to avoid false matches.
        """
        import re
        _STOP = frozenset({
            "who", "what", "where", "when", "why", "how", "which",
            "do", "does", "did", "is", "are", "am", "was", "were",
            "can", "could", "would", "should", "will", "might",
            "the", "a", "an", "of", "in", "on", "at", "to", "for",
            "and", "or", "but", "not", "no", "yes",
            "i", "me", "my", "mine", "we", "us", "our",
            "you", "your", "yours", "it", "its", "they", "them",
            "that", "this", "these", "those",
            "self", "user", "world", "conversation", "memory",
        })
        token_re = re.compile(r"[^\W_]+", re.UNICODE)

        # Collect content tokens from entry surface and graph atoms
        entry_surface = (entry.surface or "").lower()
        entry_tokens = {t for t in token_re.findall(entry_surface) if t not in _STOP}

        if uol_graph is not None:
            for aid in getattr(entry, "atom_ids", []):
                atom = uol_graph.atoms.get(aid)
                if atom is None:
                    continue
                if atom.kind in ("entity", "concept", "self", "relation", "quality", "state"):
                    atom_surface = (atom.surface or "").lower()
                    atom_tokens = {t for t in token_re.findall(atom_surface) if t not in _STOP}
                    entry_tokens |= atom_tokens

        if not entry_tokens:
            return []

        # Match against frames — check if any content token appears in
        # the frame's subject or object surface/concept_id
        _STRUCTURAL_RELATIONS = frozenset({
            "has_role", "causes", "enables", "prevents",
            "before", "after", "refers_to", "modifies",
            "teaches", "asks_about",
            "is_a", "same_as", "part_of", "used_for",
        })
        matches: list[RelationFrame] = []
        for f in frames:
            if f.structural:
                continue
            if f.relation_key in _STRUCTURAL_RELATIONS:
                continue
            subj_surface = (f.subject.surface or "").lower()
            obj_surface = (f.object.surface or "").lower()
            subj_concept = (f.subject.concept_id or "").lower()
            obj_concept = (f.object.concept_id or "").lower()

            # Extract tokens from frame surfaces and concept_ids
            frame_tokens: set[str] = set()
            for text in (subj_surface, obj_surface):
                frame_tokens |= {t for t in token_re.findall(text) if t not in _STOP}
            for text in (subj_concept, obj_concept):
                # concept_id is like "concept:president_of_nigeria"
                for part in text.replace("concept:", "").replace("_", " ").split():
                    if part and part not in _STOP:
                        frame_tokens.add(part)

            if entry_tokens & frame_tokens:
                overlap = len(entry_tokens & frame_tokens)
                min_overlap = max(1, len(entry_tokens) // 3)
                if overlap >= min_overlap:
                    matches.append(f)

        return matches

    def _template_for_obligation(
        self,
        obligation: ObligationFrame,
        binding: AnswerBinding,
        program: Any | None = None,
    ) -> str:
        if not binding.has_answer:
            if binding.abstention_reason.startswith("blocked"):
                return "blocked"
            if binding.abstention_reason:
                return "abstain"
            kind = obligation.obligation_kind
            if kind == "social_reply" and program is not None:
                entry = program.entry_instruction
                if entry is not None:
                    entry_surface = (entry.surface or "").lower()
                    frustration_cues = ("dumb", "stupid", "useless", "broken",
                                        "suck", "worthless", "worse")
                    if any(cue in entry_surface for cue in frustration_cues):
                        return "frustration_response"
                    checkin_cues = ("how are you", "how do you do", "how's it going",
                                    "hows it going", "how are things", "how you doing",
                                    "how's your day", "hows your day")
                    if any(cue in entry_surface for cue in checkin_cues):
                        return "phatic_checkin"
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
            # Distinguish greeting from phatic check-in or frustration
            # by examining the entry instruction's intent atoms.
            if program is not None:
                entry = program.entry_instruction
                if entry is not None:
                    entry_surface = (entry.surface or "").lower()
                    # Check for frustration/banter signals
                    frustration_cues = ("dumb", "stupid", "useless", "broken",
                                        "suck", "worthless", "worse")
                    if any(cue in entry_surface for cue in frustration_cues):
                        return "frustration_response"
                    # Check for phatic check-in
                    checkin_cues = ("how are you", "how do you do", "how's it going",
                                    "hows it going", "how are things", "how you doing",
                                    "how's your day", "hows your day")
                    if any(cue in entry_surface for cue in checkin_cues):
                        return "phatic_checkin"
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
