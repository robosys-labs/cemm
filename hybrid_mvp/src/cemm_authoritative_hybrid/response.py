"""Exact response meaning: the semantic contract that precedes language.

This module owns :class:`ResponseMeaning` and :class:`ResponseBuilder`.
``ResponseMeaning`` is a frozen semantic contract built from evaluation and
effect receipts — it carries mode, status, proposition refs, bindings, polarity,
modality, epistemic status, source/proof refs, discourse action, and permitted
omissions. It is the input to the REALIZE phase's constrained neural realizer.

``ResponseBuilder`` maps evaluation/effect receipts to a ``ResponseMeaning``.
It **cannot** inspect input words or select canned response text; it works
only from typed receipts and orientation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, TYPE_CHECKING

from .canonical import stable_ref

if TYPE_CHECKING:
    from .cycle import Orientation
    from .runtime import EvaluationResult, EffectResult

__all__ = [
    "ResponseMeaning",
    "ResponseBuilder",
]


# ---------------------------------------------------------------------------
# Closed-class response categories
# ---------------------------------------------------------------------------

# Discourse actions — closed set of authorized response actions.
_DISCOURSE_ACTIONS: tuple[str, ...] = (
    "answer",
    "acknowledge",
    "deny",
    "clarify",
    "unknown",
    "ambiguous",
    "operation_failed",
    "realization_failed",
)

# Polarity values.
_POLARITIES: tuple[str, ...] = ("positive", "negative")

# Modalities.
_MODALITIES: tuple[str, ...] = ("actual", "possible", "necessary", "conditional")

# Epistemic statuses.
_EPISTEMIC_STATUSES: tuple[str, ...] = (
    "supported",
    "unknown",
    "contradicted",
    "contingent",
    "denied",
)


# ---------------------------------------------------------------------------
# ResponseMeaning
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseMeaning:
    """The exact semantic contract for a response, preceding language.

    Built from evaluation/effect receipts — never from input words. Carries
    the verified proposition graph ref, requested bindings, polarity, modality,
    epistemic status, source/proof refs, discourse action, and permitted
    omissions.
    """

    response_ref: str
    mode: str  # SemanticMode value
    status: str  # evaluation status
    proposition_ref: str  # the verified proposition graph ref
    requested_bindings: tuple[tuple[str, str], ...]
    polarity: str  # "positive" or "negative"
    modality: str  # "actual", "possible", "necessary", etc.
    epistemic_status: str  # "supported", "unknown", "contradicted", etc.
    source_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    discourse_action: str  # "answer", "acknowledge", "deny", etc.
    permitted_omissions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "response_ref": self.response_ref,
            "mode": self.mode,
            "status": self.status,
            "proposition_ref": self.proposition_ref,
            "requested_bindings": [list(b) for b in self.requested_bindings],
            "polarity": self.polarity,
            "modality": self.modality,
            "epistemic_status": self.epistemic_status,
            "source_refs": list(self.source_refs),
            "proof_refs": list(self.proof_refs),
            "discourse_action": self.discourse_action,
            "permitted_omissions": list(self.permitted_omissions),
        }


# ---------------------------------------------------------------------------
# ResponseBuilder
# ---------------------------------------------------------------------------


class ResponseBuilder:
    """Maps evaluation/effect receipts to a :class:`ResponseMeaning`.

    Cannot inspect input words or select canned response text. Works only from
    typed receipts (evaluation, effect) and orientation.
    """

    def build(
        self,
        evaluation: "EvaluationResult",
        effect: "EffectResult",
        orientation: "Orientation",
    ) -> ResponseMeaning:
        """Build a :class:`ResponseMeaning` from typed receipts."""
        # Derive discourse action from evaluation status.
        status = getattr(evaluation, "status", "resolved")
        discourse_action = self._discourse_action_for_status(status)

        # Derive polarity, modality, epistemic status from status.
        polarity = self._polarity_for_status(status)
        modality = "actual"
        epistemic_status = self._epistemic_status_for_status(status)

        # Proposition ref from evaluation output refs.
        output_refs = getattr(evaluation, "output_refs", ())
        proposition_ref = output_refs[0] if output_refs else ""

        # Effect proof refs.
        effect_output = getattr(effect, "output_refs", ())
        proof_refs = tuple(effect_output)

        # Mode from orientation.
        mode = orientation.mode
        if hasattr(mode, "value"):
            mode = mode.value

        # Requested bindings — derived from orientation focus refs (structural).
        focus_refs = getattr(orientation, "focus_refs", ())
        requested_bindings = tuple(
            (ref, "query") for ref in focus_refs[:8]
        )

        # Source refs from orientation visited refs (structural).
        source_refs = tuple(getattr(orientation, "focus_refs", ()))[:8]

        # Permitted omissions — empty for normal answers.
        permitted_omissions: tuple[str, ...] = ()

        response_ref = stable_ref(
            "response",
            {
                "mode": mode,
                "status": status,
                "proposition_ref": proposition_ref,
                "polarity": polarity,
                "modality": modality,
                "epistemic_status": epistemic_status,
                "discourse_action": discourse_action,
            },
        )

        return ResponseMeaning(
            response_ref=response_ref,
            mode=mode,
            status=status,
            proposition_ref=proposition_ref,
            requested_bindings=requested_bindings,
            polarity=polarity,
            modality=modality,
            epistemic_status=epistemic_status,
            source_refs=source_refs,
            proof_refs=proof_refs,
            discourse_action=discourse_action,
            permitted_omissions=permitted_omissions,
        )

    @staticmethod
    def _discourse_action_for_status(status: str) -> str:
        """Map an evaluation status to a discourse action."""
        mapping = {
            "resolved": "answer",
            "supported": "answer",
            "unknown": "unknown",
            "ambiguous": "ambiguous",
            "denied": "deny",
            "operation_failed": "operation_failed",
            "realization_failed": "realization_failed",
            "partial": "clarify",
            "conflict": "clarify",
        }
        return mapping.get(status, "answer")

    @staticmethod
    def _polarity_for_status(status: str) -> str:
        """Map an evaluation status to a polarity."""
        if status in ("denied", "operation_failed", "realization_failed"):
            return "negative"
        return "positive"

    @staticmethod
    def _epistemic_status_for_status(status: str) -> str:
        """Map an evaluation status to an epistemic status."""
        mapping = {
            "resolved": "supported",
            "supported": "supported",
            "unknown": "unknown",
            "ambiguous": "unknown",
            "denied": "denied",
            "operation_failed": "unknown",
            "realization_failed": "unknown",
            "partial": "contingent",
            "conflict": "contradicted",
        }
        return mapping.get(status, "supported")
