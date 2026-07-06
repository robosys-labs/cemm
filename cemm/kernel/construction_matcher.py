"""ConstructionMatcher — §5.3 ConstructionMatch step.

Matches ConstructionAtom form-signatures against surface text and meaning
groups.  Seeded from uol_semantics.json frame aliases — each frame entry
becomes a ConstructionAtom whose surface_pattern is an alias phrase.

This is the missing module from §18 of the consolidated architecture.
It replaces the hardcoded English-specific intent detection that was
inlined in MeaningPerceptor.

Matching is token-based n-gram containment, not regex:
  - Multi-word aliases match as contiguous token subsequences
  - Single-token aliases match as set intersection
  - Longer aliases are checked first (more specific patterns win)
  - Cue-type entries (grammatical_*) are excluded — they are cue sets
    for segmentation, not constructions for intent detection
"""

from __future__ import annotations

import re
from typing import Any

from ..memory.construction_lattice import ConstructionLattice
from ..types.construction_atom import (
    ConstructionAtom,
    FormSignature,
    PortConstraint,
    PragmaticPattern,
)
from ..types.meaning_percept import MeaningGroup, MeaningPerceptPacket
from ..types.uol_graph import ConstructionMatch
from .uol_metadata import FRAME_ALIASES, FRAME_TO_ACT, FRAME_INTENSITY, FRAME_META

_TOKEN_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)?|\d+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Tokenize and normalize — strips apostrophes so "what's" and
    "whats" produce the same token sequence.  Consistent with
    LanguageAdapter.tokenize (§5.1 Normalize)."""
    return [
        m.group(0).lower().replace("'", "")
        for m in _TOKEN_RE.finditer(text or "")
    ]


# Frame entries that are cue sets, not constructions.
# These have cue_type set and canonical_key starting with "grammatical_".
_SKIP_PREFIX = "grammatical_"

# Map frame canonical_key to intent_key used by MeaningPerceptor.
# Most are identity, but a few need translation.
_FRAME_TO_INTENT: dict[str, str] = {
    "self_capability_query": "capability_query",
    "command_remember": "command",
    "command_retrieve": "command",
    "command_reflect": "self_reflect",
    "request_clarification": "repair",
    "confusion_repair": "repair",
    "playful_repair": "repair",
    "teaching_offer": "teaching",
    "teaching_definition": "teaching",
    "concept_query": "question",
    "open_domain_entity_query": "question",
    "weather_query": "fresh_world_query",
    "memory_query": "question",
    "story_request": "command",
    "food_recommendation_request": "command",
    "recommendation_request": "command",
    "user_complaint": "statement",
    "meta_question_intent": "question",
    "teaching_instruction_query": "question",
    "self_category_query": "self_identity_query",
    "user_identity_query": "self_knowledge_query",
    "user_name_query": "self_knowledge_query",
    "assert_evaluation": "statement",
    "state_preference": "statement",
    "low_competence": "statement",
    "useless_assistant": "statement",
    "high_quality": "statement",
    "uncertainty_marker": "statement",
    "discourse_marker": "statement",
    "playful_acknowledgment": "acknowledgment",
    "self_correction": "statement",
    "simplification_request": "repair",
    "reassurance": "statement",
    "temporal_before": "statement",
    "temporal_after": "statement",
    "temporal_during": "statement",
    "temporal_overlaps": "statement",
    "temporal_starts": "statement",
    "temporal_finishes": "statement",
    "causal_causes": "statement",
    "causal_caused_by": "statement",
    "causal_leads_to": "statement",
    "causal_because": "statement",
    "causal_so": "statement",
    "ask_question": "question",
    "unknown_intent": "statement",
    "assistance_request": "capability_query",
}

# Port constraints per intent type — used by the construction to declare
# what ports the downstream graph builder should expect.
_PORT_CONSTRAINTS: dict[str, list[str]] = {
    "self_identity_query": ["subject", "attribute"],
    "self_capability_query": ["subject", "attribute"],
    "self_knowledge_query": ["subject", "attribute"],
    "capability_query": ["subject", "attribute"],
    "phatic_checkin": ["speaker", "listener"],
    "reciprocal_phatic": ["speaker", "listener"],
    "greeting": ["speaker", "listener"],
    "session_exit": ["speaker"],
    "teaching": ["source", "target", "relation"],
    "repair": ["speaker", "repair_target"],
    "command": ["actor", "action", "target"],
    "question": ["speaker", "topic", "evidence"],
    "fresh_world_query": ["speaker", "topic", "evidence"],
    "user_state_report": ["holder", "state", "time"],
    "acknowledgment": ["speaker"],
    "self_reflect": ["subject"],
}


class ConstructionMatcher:
    """Match construction form-signatures against surface text.

    Seeded from uol_semantics.json frame aliases at construction time.
    Each non-grammatical frame entry becomes a ConstructionAtom registered
    in the ConstructionLattice.
    """

    def __init__(self, construction_lattice: ConstructionLattice | None = None) -> None:
        self._lattice = construction_lattice or ConstructionLattice()
        self._seed_from_uol_semantics()

    def _seed_from_uol_semantics(self) -> None:
        """Register ConstructionAtoms from uol_semantics.json frame entries."""
        for canonical_key, aliases in FRAME_ALIASES.items():
            if canonical_key.startswith(_SKIP_PREFIX):
                continue
            if not aliases:
                continue
            act_type = FRAME_TO_ACT.get(canonical_key, "unknown")
            intensity = FRAME_INTENSITY.get(canonical_key, 0.6)
            intent_key = _FRAME_TO_INTENT.get(canonical_key, canonical_key)
            ports = _PORT_CONSTRAINTS.get(intent_key, ["speaker"])
            pragmatic_acts = [act_type] if act_type != "unknown" else [intent_key]

            for alias in aliases:
                construction_id = f"{canonical_key}::{alias}"
                self._lattice.upsert(ConstructionAtom(
                    construction_id=construction_id,
                    form_signature=FormSignature(
                        surface_pattern=alias,
                    ),
                    port_constraints=[PortConstraint(port_key=p) for p in ports],
                    pragmatic_signature=PragmaticPattern(
                        expected_acts=pragmatic_acts,
                    ),
                    confidence=intensity,
                ))

    def match_group(
        self,
        group: MeaningGroup,
        packet: MeaningPerceptPacket,
    ) -> ConstructionMatch | None:
        """Find the best construction match for a meaning group.

        Returns a ConstructionMatch with construction_key set to the
        frame's canonical_key, or None if no construction matches.
        """
        group_tokens = group.tokens
        if not group_tokens:
            return None
        group_token_set = set(group_tokens)
        surface_lower = group.surface.strip().lower()

        best_match: ConstructionMatch | None = None
        best_score: float = 0.0

        for record in self._lattice._records.values():
            pattern = record.form_signature.surface_pattern
            if not pattern:
                continue

            pattern_tokens = _tokenize(pattern)
            if not pattern_tokens:
                continue

            # Multi-word patterns: contiguous token subsequence match
            if len(pattern_tokens) > 1:
                if not self._contiguous_match(pattern_tokens, group_tokens):
                    # Also try surface string containment for patterns
                    # that might span group boundaries
                    if pattern not in surface_lower:
                        continue
                score = (len(pattern_tokens) / len(group_tokens)) * record.confidence
            else:
                # Single-token: set intersection
                if pattern_tokens[0] not in group_token_set:
                    continue
                score = (1.0 / max(len(group_tokens), 1)) * record.confidence

            if score > best_score:
                best_score = score
                # Extract canonical_key from construction_id (before "::")
                canonical_key = record.construction_id.split("::")[0]
                intent_key = _FRAME_TO_INTENT.get(canonical_key, canonical_key)
                best_match = ConstructionMatch(
                    id=f"cm_{group.id}_{record.construction_id}",
                    construction_key=intent_key,
                    group_id=group.id,
                    matched_span_ids=[self._span_id_for_group(packet, group)],
                    expected_ports=[pc.port_key for pc in record.port_constraints],
                    graph_patch_templates=[{
                        "target": "construction_lattice",
                        "operation": "observe_construction_match",
                        "construction_key": record.construction_id,
                    }],
                    pragmatic_hints=list(record.pragmatic_signature.expected_acts) if record.pragmatic_signature else [],
                    confidence=max(group.confidence, record.confidence),
                )

        return best_match

    def match_surface(self, tokens: list[str]) -> str | None:
        """Match a token list against constructions and return intent_key.

        Lightweight version of match_group for use in segmentation
        (_initial_group_type) where a full MeaningGroup is not yet built.
        """
        if not tokens:
            return None
        token_set = set(tokens)

        best_key: str | None = None
        best_score: float = 0.0

        for record in self._lattice._records.values():
            pattern = record.form_signature.surface_pattern
            if not pattern:
                continue
            pattern_tokens = _tokenize(pattern)
            if not pattern_tokens:
                continue

            if len(pattern_tokens) > 1:
                if not self._contiguous_match(pattern_tokens, tokens):
                    continue
                score = (len(pattern_tokens) / len(tokens)) * record.confidence
            else:
                if pattern_tokens[0] not in token_set:
                    continue
                score = (1.0 / max(len(tokens), 1)) * record.confidence

            if score > best_score:
                best_score = score
                canonical_key = record.construction_id.split("::")[0]
                best_key = _FRAME_TO_INTENT.get(canonical_key, canonical_key)

        return best_key

    @staticmethod
    def _contiguous_match(pattern_tokens: list[str], text_tokens: list[str]) -> bool:
        """Check if pattern_tokens appear as a contiguous subsequence."""
        plen = len(pattern_tokens)
        tlen = len(text_tokens)
        if plen > tlen:
            return False
        for i in range(tlen - plen + 1):
            if text_tokens[i:i + plen] == pattern_tokens:
                return True
        return False

    @staticmethod
    def _span_id_for_group(packet: MeaningPerceptPacket, group: Any) -> str:
        for span in packet.spans:
            if span.span_type == "clause" and span.start_token <= group.start_token and span.end_token >= group.end_token:
                return span.id
        return f"group_span:{group.id}"
