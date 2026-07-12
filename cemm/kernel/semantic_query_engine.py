"""Single authoritative semantic query engine.

The engine consumes strict QueryContracts, retrieves durable frames, admits only
asserted current-turn evidence, applies full slot identity constraints, and
produces public-safe evidence-bound AnswerBindings.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Iterable

from ..response.realization.public_values import public_value
from ..types.answer_binding import AnswerBinding, SlotFill
from ..types.obligation_contract import QueryContract
from ..types.obligation_frame import ObligationFrame
from ..types.relation_frame import RelationFrame
from ..types.semantic_program import SemanticProgram
from ..types.semantic_query import QueryConstraint, SemanticQuery
from ..memory.relation_identity import normalize_qualifiers

_NON_QUERY_OBLIGATIONS = frozenset({
    "social_reply", "exit", "abstain_policy", "store_patch",
    "acknowledge_emotional_context",
})

_OBLIGATION_KIND_TO_RELATION_KEY = {
    "answer_self_identity": "answers_identity_as",
    "answer_self_model": "answers_identity_as",
    "answer_self_capability": "capability",
    "answer_self_knowledge": "knows_about",
    "answer_user_profile": "has_property",
}

_OBLIGATION_KIND_TO_SUBJECT = {
    "answer_self_identity": "self", "answer_self_model": "self",
    "answer_self_capability": "self", "answer_self_knowledge": "self",
    "answer_user_profile": "user",
}


class SemanticQueryEngine:
    def __init__(self, relation_algebra: Any | None = None, schema_store: Any | None = None) -> None:
        self._algebra = relation_algebra
        self._schema_store = schema_store

    @staticmethod
    def preferred_relation_key(obligation_kind: str) -> str:
        return _OBLIGATION_KIND_TO_RELATION_KEY.get(obligation_kind, "")

    # ── Canonical QueryContract path ───────────────────────────────

    def execute_contract(
        self,
        contract: QueryContract,
        obligation: ObligationFrame | None,
        *,
        turn_frames: list[RelationFrame],
        durable_store: Any,
    ) -> tuple[SemanticQuery, list[RelationFrame], AnswerBinding]:
        query = self.build_query_from_contract(contract, obligation)
        if not self._contract_has_required_target(contract):
            return query, list(turn_frames), self._empty(query, "unresolved_query_target", contract.evidence_policy)

        relation_keys = list(contract.features.get("allowed_relation_keys", []) or [])
        if not relation_keys:
            relation_keys = [contract.relation_key]
        durable_frames: list[RelationFrame] = []
        for relation_key in relation_keys:
            durable_frames.extend(durable_store.query_relations(
                relation_key=relation_key,
                subject_concept_id=contract.subject_concept_id,
                subject_entity_id=contract.subject_entity_id,
                object_concept_id=contract.object_concept_id,
                object_entity_id=contract.object_entity_id,
                dimension=contract.dimension,
                relation_scope=str(contract.features.get("relation_scope", "") or ""),
                allow_inheritance=False,
                allow_inverse=False,
                active_only=True,
            ))
        admitted_turn_frames = [
            frame for frame in turn_frames
            if self._is_asserted_public_frame(frame)
        ]
        # Durable evidence precedes current-turn evidence. Query scaffolding is
        # never admitted, so current-turn placeholders cannot outrank memory.
        frames = self._dedupe_frames([*durable_frames, *admitted_turn_frames])
        binding = self._execute_contract_frames(contract, query, frames)
        return query, frames, binding

    def build_query_from_contract(
        self,
        contract: QueryContract,
        obligation: ObligationFrame | None,
    ) -> SemanticQuery:
        return SemanticQuery(
            query_id=f"qc_{time.time_ns():x}"[-16:],
            source_obligation_id=getattr(obligation, "primary_instruction_id", "") if obligation else "",
            query_kind=contract.query_kind,
            relation_key=contract.relation_key,
            subject_constraint=QueryConstraint(
                role="subject",
                concept_id=contract.subject_concept_id,
                entity_id=contract.subject_entity_id,
            ),
            object_constraint=QueryConstraint(
                role="object",
                concept_id=contract.object_concept_id,
                entity_id=contract.object_entity_id,
                projection_policy=contract.projection_policy,
            ),
            allow_inheritance=False,
            allow_inverse=False,
            evidence_policy=contract.evidence_policy,
            required_slots=[],
            blocked_by=[],
            confidence=1.0,
        )

    def _execute_contract_frames(
        self,
        contract: QueryContract,
        query: SemanticQuery,
        frames: list[RelationFrame],
    ) -> AnswerBinding:
        matches = [frame for frame in frames if self._matches_contract(frame, contract)]
        if not matches:
            return self._empty(query, "no_matches", contract.evidence_policy)

        matches.sort(key=lambda frame: (
            float(frame.confidence or 0.0),
            len(frame.evidence_refs),
        ), reverse=True)
        fills: list[SlotFill] = []
        seen_values: set[tuple[str, str, str]] = set()
        for frame in matches:
            surface, concept_id, entity_id = self._project(frame, contract.projection_policy)
            safe_surface = public_value(surface, features=frame.features)
            if surface and not safe_surface:
                continue
            if not safe_surface and concept_id.startswith("concept:"):
                # Concept IDs are internal. They require an explicit public
                # surface before they may enter realization.
                concept_id = ""
            if not safe_surface and not concept_id and not entity_id:
                continue
            key = (safe_surface, concept_id, entity_id)
            if key in seen_values:
                continue
            seen_values.add(key)
            fills.append(SlotFill(
                slot_name="answer",
                concept_id=concept_id,
                entity_id=entity_id,
                surface=safe_surface,
                relation_key=frame.relation_key,
                source_frame_ids=[frame.relation_id],
                evidence_refs=list(frame.evidence_refs),
                confidence=frame.confidence,
                is_inherited=bool(frame.inherited_from),
                features={
                    **dict(frame.features or {}),
                    "result_cardinality": contract.result_cardinality,
                },
            ))

        fills = self._apply_cardinality(fills, contract)
        if not fills:
            return self._empty(query, "no_matches", contract.evidence_policy)
        return AnswerBinding(
            binding_id=f"ab_{time.time_ns():x}"[-16:],
            source_query_id=query.query_id,
            query_kind=query.query_kind,
            slot_fills=fills,
            matched_frame_ids=[ref for fill in fills for ref in fill.source_frame_ids],
            explanation_paths=[
                self._algebra.explain_path(frame, frames)
                for frame in matches[:len(fills)]
            ] if self._algebra is not None else [],
            has_answer=True,
            confidence=max(fill.confidence for fill in fills),
            evidence_policy=contract.evidence_policy,
        )

    @staticmethod
    def _apply_cardinality(fills: list[SlotFill], contract: QueryContract) -> list[SlotFill]:
        cardinality = str(getattr(contract, "result_cardinality", "one") or "one")
        limit = max(1, int(getattr(contract, "result_limit", 1) or 1))
        if cardinality in {"one", "optional_one"}:
            return fills[:1]
        return fills[:limit]

    @staticmethod
    def _contract_has_required_target(contract: QueryContract) -> bool:
        if not contract.target_required:
            return True
        if contract.query_kind == "profile_dimension":
            return bool(contract.subject_entity_id and contract.dimension)
        if contract.query_kind == "concept_definition":
            return bool(contract.subject_concept_id)
        return bool(
            contract.subject_entity_id or contract.subject_concept_id
            or contract.object_entity_id or contract.object_concept_id
        )

    @staticmethod
    def _matches_contract(frame: RelationFrame, contract: QueryContract) -> bool:
        if not frame.answerable or frame.structural:
            return False
        features = frame.features or {}
        if str(features.get("proposition_mode", "asserted") or "asserted") == "queried":
            return False
        if features.get("open_roles"):
            return False
        allowed_relation_keys = set(contract.features.get("allowed_relation_keys", []) or [])
        if allowed_relation_keys:
            if frame.relation_key not in allowed_relation_keys:
                return False
        elif contract.relation_key and frame.relation_key != contract.relation_key:
            return False
        if contract.subject_entity_id and frame.subject.entity_id != contract.subject_entity_id:
            return False
        if contract.subject_concept_id and frame.subject.concept_id != contract.subject_concept_id:
            return False
        if contract.object_entity_id and frame.object.entity_id != contract.object_entity_id:
            return False
        if contract.object_concept_id and frame.object.concept_id != contract.object_concept_id:
            return False
        if contract.dimension:
            dimension = str(features.get("dimension", "") or features.get("property_dimension", "") or "")
            if dimension != contract.dimension:
                return False
        scope = str(contract.features.get("relation_scope", "") or "")
        if scope and str(features.get("relation_scope", "") or "") != scope:
            return False
        expected_qualifiers = contract.features.get("qualifiers", {}) or {}
        if expected_qualifiers and normalize_qualifiers(frame.qualifiers) != normalize_qualifiers(expected_qualifiers):
            return False
        return True

    @staticmethod
    def _is_asserted_public_frame(frame: RelationFrame) -> bool:
        features = frame.features or {}
        return (
            frame.answerable
            and not frame.structural
            and str(features.get("proposition_mode", "asserted") or "asserted") != "queried"
            and not features.get("open_roles")
        )

    # ── Compatibility path ────────────────────────────────────────

    def build_query(
        self,
        obligation: ObligationFrame,
        relation_frames: list[RelationFrame],
        program: SemanticProgram | None = None,
        uol_graph: Any | None = None,
    ) -> SemanticQuery:
        relation_key = self.preferred_relation_key(obligation.obligation_kind)
        subject = _OBLIGATION_KIND_TO_SUBJECT.get(obligation.obligation_kind, "")
        return SemanticQuery(
            query_id=uuid.uuid4().hex[:16],
            source_obligation_id=obligation.primary_instruction_id,
            query_kind=self._query_kind_for_obligation(obligation.obligation_kind),
            relation_key=relation_key,
            subject_constraint=QueryConstraint(role="subject", entity_id=subject),
            object_constraint=QueryConstraint(role="object"),
            allow_inheritance=False,
            allow_inverse=False,
            evidence_policy=obligation.evidence_policy,
            required_slots=list(obligation.required_slots),
            blocked_by=list(obligation.blocked_by),
            confidence=obligation.confidence,
        )

    def execute(self, query: SemanticQuery, relation_frames: list[RelationFrame]) -> AnswerBinding:
        if query.blocked_by:
            return self._empty(query, f"blocked:{','.join(query.blocked_by)}", query.evidence_policy)
        if query.query_kind == "none" or not query.relation_key:
            return self._empty(query, "no_relation_key_or_algebra", query.evidence_policy)
        matching = [
            frame for frame in relation_frames
            if self._is_asserted_public_frame(frame)
            and frame.relation_key == query.relation_key
            and (not query.subject_constraint.entity_id or frame.subject.entity_id == query.subject_constraint.entity_id)
            and (not query.subject_constraint.concept_id or frame.subject.concept_id == query.subject_constraint.concept_id)
        ]
        compatibility = QueryContract(
            query_kind="relation_lookup",
            target_scope="compatibility",
            subject_entity_id=query.subject_constraint.entity_id,
            subject_concept_id=query.subject_constraint.concept_id,
            relation_key=query.relation_key,
            object_entity_id=query.object_constraint.entity_id,
            object_concept_id=query.object_constraint.concept_id,
            projection_policy=query.object_constraint.projection_policy or "object",
            target_required=False,
            evidence_policy=query.evidence_policy,
            result_cardinality="one",
            result_limit=1,
        )
        return self._execute_contract_frames(compatibility, query, matching)

    @staticmethod
    def _project(frame: RelationFrame, policy: str) -> tuple[str, str, str]:
        if policy == "subject":
            return frame.subject.surface or "", frame.subject.concept_id or "", frame.subject.entity_id or ""
        return frame.object.surface or "", frame.object.concept_id or "", frame.object.entity_id or ""

    @staticmethod
    def _dedupe_frames(frames: Iterable[RelationFrame]) -> list[RelationFrame]:
        result: list[RelationFrame] = []
        seen: set[tuple[Any, ...]] = set()
        for frame in frames:
            key = (
                frame.relation_key,
                frame.subject.entity_id or frame.subject.concept_id or frame.subject.surface,
                frame.object.entity_id or frame.object.concept_id or frame.object.surface,
                str((frame.features or {}).get("dimension", "") or (frame.features or {}).get("property_dimension", "")),
                normalize_qualifiers(frame.qualifiers),
            )
            if key not in seen:
                seen.add(key)
                result.append(frame)
        return result

    @staticmethod
    def _empty(query: SemanticQuery, reason: str, evidence_policy: str) -> AnswerBinding:
        return AnswerBinding(
            binding_id=f"ab_{time.time_ns():x}"[-16:],
            source_query_id=query.query_id,
            query_kind=query.query_kind,
            has_answer=False,
            abstention_reason=reason,
            evidence_policy=evidence_policy,
        )

    @staticmethod
    def _query_kind_for_obligation(obligation_kind: str) -> str:
        if obligation_kind in _NON_QUERY_OBLIGATIONS:
            return "none"
        return "lookup"
