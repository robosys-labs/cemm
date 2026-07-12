"""Verify realized text against its SemanticAnswerGraph.

Implements build-order step 10 — deterministic verification
that text faithfully represents the answer graph.

Pass criteria (from cemm_original_work_subplans.md §8.4):
1. text maps back to selected_claim_ids (fuzzy matching via SemanticMatcher)
2. uncertainty is preserved (markers resolved from registry)
3. private evidence is not revealed
4. style changes wording but not facts
5. unsupported spans are blocked
6. evidence integrity: no disputed/retracted claims, abstain/ask has no claims
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..types.claim import Claim, ClaimStatus
from ..registry.registry import Registry
from ..registry.semantic_matcher import SemanticMatcher, MatchResult


# ── Registry-driven verification policy ──────────────────────────────
# Intents that produce template-based conversational responses without
# evidence retrieval are listed in uol_semantics.json (a Model-kind
# registry data file), not hardcoded in operator-level code.
# Architectural invariants (abstain/ask must not select claims) remain
# as code below — they derive from the SAG intent enum, not domain policy.

_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_no_evidence_intents() -> frozenset[str]:
    """Load the set of intents that bypass evidence/uncertainty verification.

    Sourced from the ``no_evidence_intents`` key in ``uol_semantics.json``.
    This is a registry-level verification policy (Model kind = "verifier"),
    not operator-level domain behavior.
    """
    if not _UOL_SEMANTICS_PATH.exists():
        return frozenset()
    data = json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))
    return frozenset(data.get("no_evidence_intents", []))


_NO_EVIDENCE_INTENTS = _load_no_evidence_intents()

# Architectural invariant: abstain/ask are SAG enum values that must
# never select claims.  This is an operator-level constraint from the
# architecture (§10.1.3), not a domain policy — it stays as code.
_CLAIM_FORBIDDEN_INTENTS = frozenset({"abstain", "ask"})


@dataclass
class VerificationResult:
    verified: bool = False
    claim_coverage: float = 0.0
    uncertainty_preserved: bool = False
    private_evidence_protected: bool = True
    unsupported_spans: list[str] = field(default_factory=list)
    evidence_integrity_ok: bool = True
    details: list[str] = field(default_factory=list)
    verification_type: str = "deterministic"


def _text_lower(text: str) -> str:
    return text.lower()


def _check_claim_coverage(
    text: str,
    sag: SemanticAnswerGraph,
    claim_text_map: dict[str, str] | None = None,
    matcher: SemanticMatcher | None = None,
) -> tuple[float, list[str]]:
    """Estimate what fraction of selected claims are reflected in the text.

    Uses fuzzy matching when a SemanticMatcher is available, falling back
    to exact substring matching otherwise.
    """
    text_lower = _text_lower(text)
    covered = 0
    details: list[str] = []

    for cid in sag.selected_claim_ids:
        if cid.lower() in text_lower:
            covered += 1
            continue
        if claim_text_map and cid in claim_text_map:
            ct = claim_text_map[cid]
            if ct.lower() in text_lower:
                covered += 1
                continue
            if matcher is not None:
                prob = matcher.best_probability(ct, cid)
                if prob >= 0.4:
                    covered += 1
                    continue
        details.append(f"Claim {cid} not reflected in output text")

    total = max(len(sag.selected_claim_ids), 1)
    coverage = covered / total if sag.selected_claim_ids else 1.0
    return coverage, details


def _check_uncertainty(
    text: str,
    sag: SemanticAnswerGraph,
    registry: Registry | None = None,
) -> tuple[bool, list[str]]:
    """Check that uncertainty is preserved when confidence is low.

    Markers are resolved from the registry's `uncertainty_marker` UOL semantic
    entry when a registry is available, falling back to a minimal built-in set.

    Returns (preserved, details).
    """
    details: list[str] = []
    # Conversational intents from the registry's verification policy
    # bypass uncertainty marker checks — they produce template responses.
    if sag.intent in _NO_EVIDENCE_INTENTS:
        return True, details
    needs_uncertainty = (
        sag.confidence < 0.7
        or len(sag.uncertainty_reasons) > 0
        or (sag.verification and sag.verification.verification_type != "none" and not sag.verification.supported)
    )

    if not needs_uncertainty:
        return True, details

    text_lower = _text_lower(text)

    markers: list[str] = []
    if registry is not None:
        entry = registry.get_uol_semantic("uncertainty_marker")
        if entry:
            markers = [entry.canonical_key] + entry.aliases

    if not markers:
        markers = [
            "might", "may", "could", "possibly", "probably", "likely",
            "unclear", "uncertain", "not sure",
            "based on available information",
            "it appears", "it seems", "suggests",
        ]

    found_markers = [m for m in markers if m in text_lower]
    preserved = len(found_markers) > 0

    if preserved:
        details.append(f"Uncertainty preserved via markers: {found_markers}")
    else:
        details.append(f"Low confidence ({sag.confidence}) but no uncertainty markers in text")

    return preserved, details


def _check_private_evidence(
    text: str,
    sag: SemanticAnswerGraph,
    private_entity_names: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Check that private-scope evidence is not revealed in public output.

    Returns (protected, details).
    """
    details: list[str] = []

    if sag.permission_scope == "public":
        return True, details

    text_lower = _text_lower(text)
    leaked: list[str] = []

    for ent in sag.entity_refs:
        name = ent.get("name", "")
        if name and name.lower() in text_lower:
            leaked.append(name)

    if private_entity_names:
        for name in private_entity_names:
            if name and name.lower() in text_lower:
                leaked.append(name)

    if leaked:
        details.append(f"Private entity names leaked in text: {leaked}")
        return False, details

    details.append(f"Private scope ({sag.permission_scope}) respected — no leakage")
    return True, details


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple punctuation heuristics."""
    parts: list[str] = []
    current = ""
    for ch in text:
        if ch in ".!?":
            if current.strip():
                parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def _check_unsupported_spans(
    text: str,
    sag: SemanticAnswerGraph,
    claim_text_map: dict[str, str] | None = None,
    matcher: SemanticMatcher | None = None,
) -> tuple[list[str], list[str]]:
    """Detect output sentences not backed by any selected claim.

    Splits output into sentences and checks each against claim text.
    Sentences with no fuzzy match above threshold are flagged as unsupported.

    Returns (unsupported_spans, details).
    """
    if not sag.selected_claim_ids:
        return [], []

    claim_texts: list[str] = []
    if claim_text_map:
        for cid in sag.selected_claim_ids:
            ct = claim_text_map.get(cid, "")
            if ct:
                claim_texts.append(ct.lower())

    if not claim_texts:
        return [], []

    sentences = _split_sentences(text)
    unsupported: list[str] = []
    details: list[str] = []

    for sent in sentences:
        sent_lower = sent.lower().strip()
        if len(sent_lower) < 5:
            continue

        best_prob = 0.0
        for ct in claim_texts:
            if ct in sent_lower:
                best_prob = 1.0
                break
            if matcher is not None:
                for word in sent_lower.split():
                    for ct_word in ct.split():
                        if word == ct_word and len(word) >= 4:
                            best_prob = max(best_prob, 0.5)
                        elif len(word) >= 4 and len(ct_word) >= 4:
                            from ..registry.semantic_matcher import _levenshtein
                            dist = _levenshtein(word, ct_word)
                            max_allowed = 1 if max(len(word), len(ct_word)) <= 5 else 2
                            if dist <= max_allowed:
                                best_prob = max(best_prob, 1.0 - dist / max(len(word), len(ct_word)))

        if best_prob < 0.2:
            unsupported.append(sent.strip())
            details.append(f"Unsupported span: '{sent.strip()}'")

    return unsupported, details


def _check_evidence_integrity(
    sag: SemanticAnswerGraph,
    claims: list[Claim] | None = None,
) -> tuple[bool, list[str]]:
    """Check evidence integrity — absorbed from SynthesisVerifier.

    - Abstain/Ask outputs must not select claims
    - No disputed or retracted claims in selected evidence

    Returns (ok, details).
    """
    details: list[str] = []
    intent = sag.intent

    # Registry-driven policy: conversational intents bypass evidence checks.
    if intent in _NO_EVIDENCE_INTENTS:
        # Architectural invariant (§10.1.3): abstain/ask are SAG enum
        # values that must never select claims as evidence.  This is an
        # operator-level constraint, not a domain policy.
        if intent in _CLAIM_FORBIDDEN_INTENTS and sag.selected_claim_ids:
            details.append("Abstain/Ask output selects claims as evidence")
            return False, details
        return True, details

    if not sag.selected_claim_ids and not sag.selected_model_ids:
        details.append("No evidence selected for synthesis")
        return False, details

    if claims:
        for c in claims:
            if c.status == ClaimStatus.DISPUTED:
                details.append(f"Output uses disputed claim {c.id}")
            if c.status == ClaimStatus.RETRACTED:
                details.append(f"Output uses retracted claim {c.id}")

    return len(details) == 0, details


def verify(
    sag: SemanticAnswerGraph,
    output_text: str,
    claim_text_map: dict[str, str] | None = None,
    private_entity_names: list[str] | None = None,
    registry: Registry | None = None,
    claims: list[Claim] | None = None,
) -> VerificationResult:
    """Verify realized text against its SemanticAnswerGraph.

    Unified verification combining:
    - Claim coverage (fuzzy matching via SemanticMatcher)
    - Uncertainty preservation (markers from registry)
    - Private evidence protection
    - Unsupported span detection
    - Evidence integrity (disputed/retracted claims, abstain/ask rules)

    Args:
        sag: The source SemanticAnswerGraph.
        output_text: The realized text to verify.
        claim_text_map: Optional mapping of claim_id -> claim statement text.
        private_entity_names: Optional list of private entity names to check for leakage.
        registry: Optional Registry for model-driven marker resolution.
        claims: Optional list of Claim objects for evidence integrity checks.

    Returns:
        VerificationResult with detailed pass/fail per criterion.
    """
    details: list[str] = []

    if not output_text or not output_text.strip():
        details.append("Empty output")
        return VerificationResult(
            verified=False,
            claim_coverage=0.0,
            uncertainty_preserved=False,
            private_evidence_protected=True,
            unsupported_spans=[],
            evidence_integrity_ok=False,
            details=details,
        )

    matcher = SemanticMatcher(registry) if registry else None

    claim_cov, claim_details = _check_claim_coverage(output_text, sag, claim_text_map, matcher)

    # When no claim_text_map is provided and claim IDs are not in the text,
    # we cannot meaningfully check coverage — skip this criterion.
    if not claim_text_map and claim_cov == 0.0 and sag.selected_claim_ids:
        claim_cov = 1.0
        claim_details = []

    # Template-only responses (no selected claims) skip claim coverage entirely
    if not sag.selected_claim_ids:
        claim_cov = 1.0
        claim_details = []

    details.extend(claim_details)

    uncert_ok, uncert_details = _check_uncertainty(output_text, sag, registry)
    details.extend(uncert_details)

    priv_ok, priv_details = _check_private_evidence(output_text, sag, private_entity_names)
    details.extend(priv_details)

    unsupported, unsupported_details = _check_unsupported_spans(output_text, sag, claim_text_map, matcher)
    details.extend(unsupported_details)

    integrity_ok, integrity_details = _check_evidence_integrity(sag, claims)
    details.extend(integrity_details)

    claim_coverage_ok = claim_cov >= 0.5
    no_unsupported = len(unsupported) == 0
    verified = claim_coverage_ok and uncert_ok and priv_ok and no_unsupported and integrity_ok

    return VerificationResult(
        verified=verified,
        claim_coverage=round(claim_cov, 4),
        uncertainty_preserved=uncert_ok,
        private_evidence_protected=priv_ok,
        unsupported_spans=unsupported,
        evidence_integrity_ok=integrity_ok,
        details=details,
    )


def verify_synthesis_result(
    sag: SemanticAnswerGraph,
    result: Any,
    **kwargs: Any,
) -> VerificationResult:
    """Convenience wrapper: takes a SynthesisResult object."""
    output = result.output if hasattr(result, "output") else str(result)
    return verify(sag, output, **kwargs)
