"""Candidate graph — competing predication/proposition candidates with alternatives.

Import boundary: model + schema + language submodules only. No engine imports.

Architectural guardrails (UNDERSTANDING_PIPELINE.md §3):
- SemanticComposer creates separate candidates for:
    lexical sense, schema family, predication/proposition structure,
    communicative force, role bindings and open ports, embedded propositions,
    context/world, source evidence.
- Whole-turn construction and pragmatic cues may ADD candidates or
  discourse relations. They may NOT replace compositional content.
- For an opaque lexeme, composition creates a lexical reference and
  one or more provisional candidate sense clusters. It does not assume
  that identical spellings share one schema.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.predication import Predication, RoleBinding, OpenPort
from ..model.proposition import Proposition, ModalQualifier
from ..model.context_frame import ContextFrame
from ..model.evidence import EvidenceRecord
from ..model.refs import FrozenMap


@dataclass(frozen=True, slots=True)
class CandidatePredication:
    """A candidate predication from composition.

    Multiple candidates may exist for the same surface evidence —
    composition preserves alternatives, it does not select one.
    """
    predication: Predication
    candidate_source: str = "lexical"  # lexical, construction, pragmatic
    confidence: float = 0.0
    source_evidence_refs: tuple[str, ...] = ()
    source_token_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateProposition:
    """A candidate proposition from composition.

    A proposition wraps a predication with context, polarity, modality,
    attribution, and valid time. Multiple candidates may exist.
    """
    proposition: Proposition
    candidate_source: str = "compositional"
    confidence: float = 0.0
    embedded_proposition_refs: tuple[str, ...] = ()
    source_evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateCommunicativeForce:
    """A candidate communicative force for a turn or clause.

    Communicative force is independent from polarity, context, and modality.
    """
    force: str  # assert, ask, request, direct, acknowledge, correct, promise, refuse
    target_proposition_ref: str = ""
    confidence: float = 0.0
    source_evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateContext:
    """A candidate context frame for propositions."""
    context_frame: ContextFrame
    confidence: float = 0.0
    source_evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscourseRelation:
    """A discourse relation between candidates or groups.

    Pragmatic cues may add discourse relations — they may not
    replace compositional content.
    """
    source_ref: str
    target_ref: str
    relation_kind: str  # elaboration, contrast, cause, condition, topic_shift, etc.
    confidence: float = 0.0
    from_pragmatic_cue: bool = False


@dataclass(frozen=True, slots=True)
class CandidateGraph:
    """A graph of competing candidates from composition.

    Preserves alternatives — does not select one interpretation.
    The InterpretationResolver selects among candidates later.
    """
    candidate_predications: tuple[CandidatePredication, ...] = ()
    candidate_propositions: tuple[CandidateProposition, ...] = ()
    candidate_communicative_forces: tuple[CandidateCommunicativeForce, ...] = ()
    candidate_contexts: tuple[CandidateContext, ...] = ()
    discourse_relations: tuple[DiscourseRelation, ...] = ()
    open_ports: tuple[OpenPort, ...] = ()
    opaque_lexeme_refs: tuple[str, ...] = ()
    source_evidence_refs: tuple[str, ...] = ()

    @property
    def has_alternatives(self) -> bool:
        """Whether there are competing alternatives."""
        return (
            len(self.candidate_predications) > 1
            or len(self.candidate_propositions) > 1
            or len(self.candidate_communicative_forces) > 1
        )

    @property
    def has_embedded_propositions(self) -> bool:
        """Whether there are embedded (nested) propositions."""
        return any(
            len(c.embedded_proposition_refs) > 0
            for c in self.candidate_propositions
        )

    @property
    def has_opaque_lexemes(self) -> bool:
        """Whether there are opaque (unknown) lexemes."""
        return len(self.opaque_lexeme_refs) > 0

    def predications_for_token(self, token_index: int) -> tuple[CandidatePredication, ...]:
        """Get candidate predications that involve a specific token."""
        return tuple(
            cp for cp in self.candidate_predications
            if token_index in cp.source_token_indices
        )
