"""SemanticQueryEngine — build and execute SemanticQuery over relation frames.

The breakthrough module: closes the loop between the v4.2 semantic stack
(SemanticProgram → ObligationFrame → RelationFrames) and the response
pipeline. Instead of keyword-based claim retrieval and hardcoded if/else
template selection, the engine:

1. Builds a SemanticQuery from the ObligationFrame + RelationFrames
2. Executes the query against the RelationAlgebra + PredicateSchemaStore
3. Produces an AnswerBinding with slot fills, evidence, and explanation paths

The AnswerBinding is consumed by the ResponseFormationEngine (v3.1 canonical path).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from ..types.answer_binding import AnswerBinding, SlotFill
from ..types.obligation_frame import ObligationFrame
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

_OBLIGATION_KIND_TO_RELATION_KEY: dict[str, str] = {
    "answer_self_identity": "answers_identity_as",
    "answer_self_model": "answers_identity_as",
    "answer_self_capability": "capability",
    "answer_self_knowledge": "knows_about",
    "answer_user_profile": "has_property",
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
