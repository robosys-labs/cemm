"""Communicative builder — builds communicative force candidates from evidence.

Import boundary: model + language submodules only.

Communicative force is independent from polarity, context, and modality
(AGENTS.md §5). The communicative builder extracts force candidates
from surface evidence without conflating them with content.

A question is a communicative predication over a proposition pattern
with open ports. A command is a directive predication whose content
denotes a desired operation or state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...language.interfaces import SurfaceEvidence, CommunicativeCandidate
from ...language.stream import Token, TokenKind, TokenStream


def extract_communicative_forces(
    evidence: SurfaceEvidence,
) -> tuple[CommunicativeCandidate, ...]:
    """Extract communicative force candidates from surface evidence.

    Force candidates come from:
    1. Explicit communicative candidates from the adapter
    2. Syntactic evidence (interrogative, imperative, declarative)
    3. Construction candidates that imply force

    Multiple forces may be detected — composition preserves alternatives.
    """
    forces: list[CommunicativeCandidate] = list(evidence.communicative_candidates)

    # Detect force from syntactic evidence if no explicit candidates
    if not forces:
        stream = evidence.token_stream
        force = _detect_force_from_syntax(stream)
        if force is not None:
            forces.append(CommunicativeCandidate(
                force=force,
                confidence=0.7,
                evidence_kind="syntactic",
            ))

    return tuple(forces)


def _detect_force_from_syntax(stream: TokenStream) -> str | None:
    """Detect communicative force from syntactic evidence.

    - Question: sentence starts with wh-word or auxiliary inversion
    - Command: imperative verb at start, no subject
    - Assert: default declarative
    """
    if not stream.tokens:
        return None

    # Check for question marks
    has_question_mark = any(
        t.raw_form == "?" for t in stream.tokens
        if t.kind == TokenKind.PUNCTUATION
    )
    if has_question_mark:
        return "ask"

    # Check for imperative (first token is a verb, no subject)
    first_word = next(
        (t for t in stream.tokens if t.kind == TokenKind.WORD),
        None,
    )
    if first_word:
        # Check if it's a base-form verb (lemma == normalized, no tense features)
        is_base_verb = (
            first_word.lemma_candidates
            and first_word.normalized_form.lower() == first_word.lemma_candidates[0].lower()
            and not any(
                f.feature == "tense" and f.value != "base"
                for f in first_word.morphological_features
            )
        )
        if is_base_verb:
            return "request"  # Could be request or direct

    return "assert"  # Default


def force_to_open_ports(force: str) -> tuple[str, ...]:
    """Determine which open ports a communicative force requires.

    Questions have open ports for the unknown role.
    Commands have open ports for the desired state/operation.
    """
    if force == "ask":
        return ("role:unknown",)
    elif force in ("request", "direct"):
        return ("role:desired_state",)
    return ()
