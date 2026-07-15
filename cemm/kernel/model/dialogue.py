"""Dialogue-control records for grounded multi-turn learning."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DialogueObligation:
    """A question that was actually dispatched and awaits typed evidence."""

    obligation_id: str
    context_ref: str
    transaction_ref: str
    question_semantic_ref: str
    target_artifact_ref: str
    expected_evidence_schema_refs: tuple[str, ...] = ()
    unresolved_field_refs: tuple[str, ...] = ()
    accepted_contribution_refs: tuple[str, ...] = ()
    asked_probe_key: str = ""
    output_event_ref: str = ""
    status: str = "pending"  # pending | answered | superseded | cancelled


@dataclass(frozen=True, slots=True)
class DialogueTurnResolution:
    """How the current turn relates to a pending learning dialogue."""

    context_ref: str
    resolution_kind: str = "none"  # none | evidence | meta_question | correction
    obligation_ref: str = ""
    transaction_ref: str = ""
    target_artifact_ref: str = ""
    accepted_contribution_refs: tuple[str, ...] = ()
    accepted_surface_forms: tuple[str, ...] = ()
    remaining_field_refs: tuple[str, ...] = ()
    explanation_key: str = ""
    evidence_refs: tuple[str, ...] = ()
    suppress_fresh_lexical_gaps: bool = False
