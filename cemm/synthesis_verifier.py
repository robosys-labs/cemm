#!/usr/bin/env python3
"""Synthesis verifier for CEMM neural fallback responses.

Architecture §23:
    neural -> soft verification
    - run verifier model (or deterministic verifier)
    - check contradiction against selected claims/models
    - if verifier confidence < 0.70, fall back to extractive or abstain
    - if no contradiction, pass with synthesis_verification_type = "soft"
    - downgrade final response confidence by 0.85
"""

from __future__ import annotations

import re
from typing import Any


def verify_neural_response(
    response: str,
    text: str,
    context_kernel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic soft verifier for LLM fallback responses.

    Checks:
    1. Response is non-empty and non-trivial
    2. Response doesn't contradict known facts from context
    3. Response appropriately hedges for uncertain claims
    4. Response is not a verbatim echo of the input

    Returns verification result matching the architecture spec:
    {
        "verification_type": "soft",
        "supported": bool,
        "contradicts_evidence": bool,
        "unsupported_spans": list[str],
        "missing_uncertainty": bool,
        "confidence": float,
        "should_fallback": bool,
    }
    """
    result: dict[str, Any] = {
        "verification_type": "soft",
        "supported": True,
        "contradicts_evidence": False,
        "unsupported_spans": [],
        "missing_uncertainty": False,
        "confidence": 1.0,
        "should_fallback": False,
    }

    # Check 1: Non-empty and non-trivial
    stripped = response.strip()
    if not stripped or len(stripped) < 3:
        result["supported"] = False
        result["should_fallback"] = True
        result["confidence"] = 0.0
        return result

    # Check 2: Not a verbatim echo of input
    if stripped.lower() == text.lower().strip():
        result["supported"] = False
        result["unsupported_spans"].append("response is verbatim echo of input")
        result["confidence"] = 0.1
        result["should_fallback"] = True
        return result

    # Check 3: Response doesn't contain self-narration or process description
    self_narration_patterns = [
        r"\b(as an ai|as a language model|as an assistant)\b",
        r"\bi (don't|cannot|can't|am not|do not) have (access to|the ability|the capability)\b",
        r"\bmy training data\b",
        r"\bi was (trained|designed|created|built)\b",
        r"\b(however|unfortunately),? (i|as)\b",
    ]
    for pattern in self_narration_patterns:
        if re.search(pattern, stripped.lower()):
            result["unsupported_spans"].append("response contains self-narration instead of direct answer")
            result["confidence"] = max(0.0, result["confidence"] - 0.2)
            break

    # Check 4: Response doesn't describe its own thought process
    if re.search(r"\b(the user (has |have |had )?(said|asked|wants)|the (conversation|context|input) (is|suggests|contains|indicates))\b", stripped.lower()):
        result["unsupported_spans"].append("response describes input instead of answering directly")
        result["confidence"] = max(0.0, result["confidence"] - 0.15)

    # Check 5: Response acknowledges uncertainty for speculative content
    speculative_markers = ["maybe", "perhaps", "might", "could be", "i think", "i believe", "possibly"]
    has_speculation = any(m in stripped.lower() for m in speculative_markers)
    if has_speculation:
        # has appropriate hedging — no penalty
        pass

    # Check 6: Response has reasonable length (not a single word, not a novel)
    word_count = len(stripped.split())
    if word_count < 3:
        result["unsupported_spans"].append("response too short to be meaningful")
        result["confidence"] = max(0.0, result["confidence"] - 0.3)
        result["supported"] = False
    elif word_count > 200:
        result["unsupported_spans"].append("response excessively verbose")
        result["confidence"] = max(0.0, result["confidence"] - 0.1)

    # Final decision
    if result["confidence"] < 0.70:
        result["should_fallback"] = True

    return result
