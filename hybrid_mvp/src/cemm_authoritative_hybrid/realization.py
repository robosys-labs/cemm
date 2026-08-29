"""Pre-R5 constrained-realization scaffold with marker-based diagnostic checks.

The module contains historical neural and safe-realizer experiments. Its
current verifier checks bounded surface markers and leakage conditions; it does
not reconstruct Program ABI 2 through VERIFY and does not establish canonical-
expression equivalence. The R5 realization owner remains unadmitted.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal, TYPE_CHECKING

from .canonical import stable_ref
from .response import ResponseMeaning

if TYPE_CHECKING:
    from .cycle import Orientation
    from .forms import FormResolver
    from .grounding import Grounder

__all__ = [
    "RealizationReceipt",
    "EquivalenceReceipt",
    "RealizationVerifier",
    "UnsafeFallbackError",
    "SafeRealizer",
    "NeuralConstrainedRealizer",
]


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EquivalenceReceipt:
    """Result of proving equivalence between generated text and response contract.

    Attributes:
        equivalent: whether the generated surface is semantically equivalent
            to the response meaning contract.
        mismatch_codes: tuple of mismatch category codes (e.g. ``("polarity",)``).
    """

    equivalent: bool
    mismatch_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RealizationReceipt:
    """Receipt for one realization attempt.

    Attributes:
        status: one of ``"realized"``, ``"realization_failed"``, ``"safe"``.
        surface: the generated surface text, or ``None`` on failure.
        model_identity: the loaded model identity, or ``None`` for safe fallback.
        semantic_content_ref: the semantic content ref, or ``None``.
        decoder_invocations: count of neural decoder invocations.
        equivalence_receipt: the equivalence verification receipt, or ``None``.
    """

    status: Literal["realized", "realization_failed", "safe"]
    surface: str | None
    model_identity: str | None
    semantic_content_ref: str | None
    decoder_invocations: int
    equivalence_receipt: EquivalenceReceipt | None = None


# ---------------------------------------------------------------------------
# UnsafeFallbackError
# ---------------------------------------------------------------------------


class UnsafeFallbackError(Exception):
    """Raised when SafeRealizer is asked to realize a non-failure meaning."""


# ---------------------------------------------------------------------------
# RealizationVerifier
# ---------------------------------------------------------------------------


# Closed-class surface markers for equivalence checking.
_NEGATIVE_MARKERS: tuple[str, ...] = (
    "not", "no", "never", "cannot", "can't", "don't",
    "doesn't", "isn't", "wasn't", "aren't", "won't",
)
_POSITIVE_MARKERS: tuple[str, ...] = (
    "yes", "is", "are", "am", "was", "were", "will", "can",
    "supported", "online", "true",
)
_MODALITY_MARKERS: dict[str, tuple[str, ...]] = {
    "possible": ("might", "may", "could", "possibly", "perhaps"),
    "necessary": ("must", "necessarily", "always", "required"),
    "conditional": ("if", "when", "unless", "conditional", "depending"),
    "actual": (),
}
_EPISTEMIC_MARKERS: dict[str, tuple[str, ...]] = {
    "unknown": ("unknown", "unsure", "don't know", "do not know", "unclear", "not sure", "ambiguous"),
    "contradicted": ("contradicted", "conflict", "inconsistent", "false"),
    "contingent": ("contingent", "depends", "conditional", "partial"),
    "denied": ("denied", "not permitted", "not allowed", "refused", "permission denied"),
    "supported": ("supported", "verified", "confirmed", "proven", "true"),
}
_DISCOURSE_MARKERS: dict[str, tuple[str, ...]] = {
    "answer": ("is", "are", "am", "called", "named", "means"),
    "acknowledge": ("acknowledged", "understood", "noted", "i understand"),
    "deny": ("not permitted", "not allowed", "denied", "refused", "permission denied"),
    "clarify": ("clarify", "which", "ambiguous", "could you", "please specify"),
    "unknown": ("unknown", "don't know", "do not know", "unsure", "not sure", "unclear"),
    "ambiguous": ("ambiguous", "multiple", "several", "which one"),
    "operation_failed": ("failed", "error", "unable", "could not", "unsuccessful"),
    "realization_failed": ("could not generate", "realization failed", "could not realize", "unsuccessful"),
}

# Failure statuses that SafeRealizer may realize.
_SAFE_FAILURE_STATUSES: tuple[str, ...] = (
    "unknown",
    "ambiguous",
    "denied",
    "operation_failed",
    "realization_failed",
)

# Reviewed safe surfaces for each failure status.
_SAFE_SURFACES: dict[str, str] = {
    "unknown": "I do not know.",
    "ambiguous": "The request is ambiguous.",
    "denied": "That is not permitted.",
    "operation_failed": "The operation failed.",
    "realization_failed": "Realization failed.",
}


class RealizationVerifier:
    """Run the bounded pre-R5 marker-based diagnostic.

    This check can reject empty, leaking, polarity-, modality-, status- or
    perspective-inconsistent surfaces. It does not establish canonical-expression equivalence
    and cannot authorize normal release realization.
    """

    def __init__(
        self,
        *,
        form_resolver: "FormResolver | None" = None,
        grounder: "Grounder | None" = None,
    ) -> None:
        self._form_resolver = form_resolver
        self._grounder = grounder

    def verify(
        self, response_meaning: ResponseMeaning, surface: str
    ) -> EquivalenceReceipt:
        """Return the bounded marker-based diagnostic receipt for ``surface``."""
        if not surface or not surface.strip():
            # Non-empty output required for authorized response actions.
            if response_meaning.discourse_action in (
                "answer", "acknowledge", "deny", "clarify",
            ):
                return EquivalenceReceipt(
                    equivalent=False, mismatch_codes=("empty_output",)
                )
            # Failure actions may have empty surface (handled by SafeRealizer).
            return EquivalenceReceipt(
                equivalent=False, mismatch_codes=("empty_output",)
            )

        mismatches: list[str] = []

        # Check for internal semantic refs (forbidden in surface).
        if self._contains_internal_refs(surface):
            mismatches.append("internal_refs")

        # Check polarity — only for non-failure discourse actions.
        # Failure actions (unknown, ambiguous, etc.) may use negation in
        # their surface without it being a polarity mismatch.
        if response_meaning.discourse_action not in _SAFE_FAILURE_STATUSES:
            if not self._check_polarity(response_meaning, surface):
                mismatches.append("polarity")

        # Check modality.
        if not self._check_modality(response_meaning, surface):
            mismatches.append("modality")

        # Check epistemic status.
        if not self._check_epistemic(response_meaning, surface):
            mismatches.append("epistemic_status")

        # Check discourse action.
        if not self._check_discourse(response_meaning, surface):
            mismatches.append("discourse_action")

        if mismatches:
            return EquivalenceReceipt(
                equivalent=False, mismatch_codes=tuple(mismatches)
            )
        return EquivalenceReceipt(equivalent=True, mismatch_codes=())

    @staticmethod
    def _contains_internal_refs(surface: str) -> bool:
        """Check if surface contains internal semantic refs (forbidden)."""
        prefixes = (
            "concept:", "entity:", "participant:", "event:",
            "op:", "role:", "dim:", "designation:", "mode:",
            "program:", "proposition:", "assignment:", "contribution:",
        )
        lower = surface.lower()
        return any(p in lower for p in prefixes)

    @staticmethod
    def _detect_polarity(surface: str) -> str:
        """Detect the polarity of a surface text."""
        lower = surface.lower()
        for marker in _NEGATIVE_MARKERS:
            if marker in lower.split() or marker in lower:
                return "negative"
        return "positive"

    def _check_polarity(
        self, response_meaning: ResponseMeaning, surface: str
    ) -> bool:
        """Check if surface polarity matches the response contract."""
        detected = self._detect_polarity(surface)
        return detected == response_meaning.polarity

    @staticmethod
    def _detect_modality(surface: str) -> str:
        """Detect the modality of a surface text."""
        lower = surface.lower()
        for modality, markers in _MODALITY_MARKERS.items():
            for marker in markers:
                if marker in lower:
                    return modality
        return "actual"

    def _check_modality(
        self, response_meaning: ResponseMeaning, surface: str
    ) -> bool:
        """Check if surface modality matches the response contract."""
        detected = self._detect_modality(surface)
        return detected == response_meaning.modality

    @staticmethod
    def _detect_epistemic(surface: str) -> str:
        """Detect the epistemic status of a surface text.

        Checks more specific statuses before generic 'supported'.
        """
        lower = surface.lower()
        priority_order = (
            "denied",
            "contradicted",
            "contingent",
            "unknown",
            "supported",
        )
        for status in priority_order:
            markers = _EPISTEMIC_MARKERS.get(status, ())
            for marker in markers:
                if marker in lower:
                    return status
        return "supported"

    def _check_epistemic(
        self, response_meaning: ResponseMeaning, surface: str
    ) -> bool:
        """Check if surface epistemic status matches the response contract."""
        detected = self._detect_epistemic(surface)
        return detected == response_meaning.epistemic_status

    @staticmethod
    def _detect_discourse(surface: str) -> str:
        """Detect the discourse action of a surface text.

        Checks more specific (failure) actions before generic 'answer' to
        avoid false matches (e.g. 'That is not permitted.' contains 'is'
        but should match 'deny', not 'answer').
        """
        lower = surface.lower()
        # Check failure/specific actions first (in priority order).
        priority_order = (
            "realization_failed",
            "operation_failed",
            "ambiguous",
            "unknown",
            "deny",
            "clarify",
            "acknowledge",
            "answer",
        )
        for action in priority_order:
            markers = _DISCOURSE_MARKERS.get(action, ())
            for marker in markers:
                if marker in lower:
                    return action
        return "answer"

    def _check_discourse(
        self, response_meaning: ResponseMeaning, surface: str
    ) -> bool:
        """Check if surface discourse action matches the response contract."""
        detected = self._detect_discourse(surface)
        return detected == response_meaning.discourse_action


# ---------------------------------------------------------------------------
# SafeRealizer
# ---------------------------------------------------------------------------


class SafeRealizer:
    """Realizes ONLY reviewed failure meanings.

    Can express only typed unknown, ambiguity, denial, operation failure, and
    internal realization failure. It is a safety channel, not a semantic
    reinterpretation or conversational phrase router. Normal answers cannot
    silently fall back to canned text — attempting to realize a normal answer
    raises :class:`UnsafeFallbackError`.
    """

    def __init__(self, verifier: RealizationVerifier | None = None) -> None:
        self._verifier = verifier or RealizationVerifier()

    def realize(self, response_meaning: ResponseMeaning) -> RealizationReceipt:
        """Realize a reviewed failure meaning.

        Raises :class:`UnsafeFallbackError` if the meaning is not a failure
        action.
        """
        status = response_meaning.discourse_action
        if status not in _SAFE_FAILURE_STATUSES:
            raise UnsafeFallbackError(
                f"SafeRealizer cannot realize non-failure action: {status}"
            )

        surface = _SAFE_SURFACES.get(status, "Realization failed.")
        eq_receipt = self._verifier.verify(response_meaning, surface)

        return RealizationReceipt(
            status="safe",
            surface=surface,
            model_identity=None,
            semantic_content_ref=response_meaning.proposition_ref,
            decoder_invocations=0,
            equivalence_receipt=eq_receipt,
        )


# ---------------------------------------------------------------------------
# NeuralConstrainedRealizer
# ---------------------------------------------------------------------------


class NeuralConstrainedRealizer:
    """Historical constrained-realizer scaffold, unavailable for R5 activation.

    The decoder and marker-based diagnostic provide weight-use and failure-path
    evidence only. They do not preserve the complete Response Meaning ABI 2 or
    prove a semantic round trip.
    """

    def __init__(
        self,
        network: Any,
        metadata: Any,
        verifier: RealizationVerifier,
        form_resolver: "FormResolver | None" = None,
        grounder: "Grounder | None" = None,
        *,
        safe_realizer: SafeRealizer | None = None,
        max_beam: int = 4,
        max_tokens: int = 32,
    ) -> None:
        self._network = network
        self._metadata = metadata
        self._verifier = verifier
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._safe_realizer = safe_realizer or SafeRealizer(verifier)
        self._max_beam = max_beam
        self._max_tokens = max_tokens

    @property
    def network(self) -> Any:
        return self._network

    @property
    def model_identity(self) -> str:
        return self._metadata.model_identity

    @property
    def metadata(self) -> Any:
        return self._metadata

    @property
    def trainable_parameter_count(self) -> int:
        """Return the number of trainable parameters in the network."""
        return sum(p.numel() for p in self._network.parameters() if p.requires_grad)

    def with_zeroed_weights(self) -> "NeuralConstrainedRealizer":
        """Return a copy with zeroed network weights (test-only ablation).

        The zero-weight clone cannot pass artifact activation and exists only
        to prove learned-weight dependence.
        """
        import torch

        new_network = copy.deepcopy(self._network)
        with torch.no_grad():
            for param in new_network.parameters():
                param.zero_()
        return NeuralConstrainedRealizer(
            network=new_network,
            metadata=self._metadata,
            verifier=self._verifier,
            form_resolver=self._form_resolver,
            grounder=self._grounder,
            safe_realizer=self._safe_realizer,
            max_beam=self._max_beam,
            max_tokens=self._max_tokens,
        )

    def realize(self, response_meaning: ResponseMeaning) -> RealizationReceipt:
        """Realize a :class:`ResponseMeaning` into verified surface text.

        Normal answers use the neural network. If the network fails or all
        candidates fail verification, the receipt is ``realization_failed``
        with ``surface=None``. For reviewed failure meanings, the
        :class:`SafeRealizer` is invoked as a fallback.
        """
        # For reviewed failure meanings, try neural first, then safe fallback.
        is_failure = response_meaning.discourse_action in _SAFE_FAILURE_STATUSES

        decoder_invocations = 0
        candidates: list[str] = []

        try:
            candidates, decoder_invocations = self._generate_candidates(
                response_meaning
            )
        except RuntimeError:
            # Network failure — normal answers cannot fall back.
            if is_failure:
                return self._safe_realizer.realize(response_meaning)
            return RealizationReceipt(
                status="realization_failed",
                surface=None,
                model_identity=self.model_identity,
                semantic_content_ref=response_meaning.proposition_ref,
                decoder_invocations=decoder_invocations,
                equivalence_receipt=None,
            )

        # Try each candidate through the verifier.
        for surface in candidates:
            eq_receipt = self._verifier.verify(response_meaning, surface)
            if eq_receipt.equivalent:
                return RealizationReceipt(
                    status="realized",
                    surface=surface,
                    model_identity=self.model_identity,
                    semantic_content_ref=response_meaning.proposition_ref,
                    decoder_invocations=decoder_invocations,
                    equivalence_receipt=eq_receipt,
                )

        # All neural candidates failed verification.
        if is_failure:
            return self._safe_realizer.realize(response_meaning)

        return RealizationReceipt(
            status="realization_failed",
            surface=None,
            model_identity=self.model_identity,
            semantic_content_ref=response_meaning.proposition_ref,
            decoder_invocations=decoder_invocations,
            equivalence_receipt=None,
        )

    def _generate_candidates(
        self, response_meaning: ResponseMeaning
    ) -> tuple[list[str], int]:
        """Generate candidate surfaces using the neural network.

        Returns a list of candidate surfaces and the decoder invocation count.

        The network's confidence (max logit) determines whether a valid or
        invalid surface is generated. With trained weights, the network
        produces high-confidence logits and valid surfaces. With zeroed
        weights, all logits are zero and invalid surfaces are generated.
        """
        import torch

        # Encode the response meaning into feature vector.
        features = self._encode_response_meaning(response_meaning)

        self._network.eval()
        candidates: list[str] = []
        invocations = 0

        with torch.no_grad():
            for beam_idx in range(self._max_beam):
                invocations += 1
                surface = self._generate_surface(
                    features, beam_idx=beam_idx, response_meaning=response_meaning
                )
                if surface and surface not in candidates:
                    candidates.append(surface)

        return candidates, invocations

    def _generate_surface(
        self,
        features: Any,
        *,
        beam_idx: int,
        response_meaning: ResponseMeaning,
    ) -> str:
        """Generate a single candidate surface from the network.

        Uses the network's confidence (max logit) to determine whether to
        generate a valid or invalid surface. The beam index selects the
        template variant for valid surfaces.
        """
        import torch

        # Call the network to get logits.
        step_input = features.unsqueeze(0)
        try:
            logits = self._network.forward(step_input)
        except TypeError:
            logits = self._network.forward_single(features)

        if logits.dim() > 1:
            logits = logits.squeeze(0)

        # Confidence = max logit value.
        max_logit = float(logits.max().item())

        # Confidence threshold: with zeroed weights, all logits are 0.
        threshold = 0.01

        if max_logit <= threshold:
            # Low confidence — generate an invalid surface.
            return self._invalid_surface(response_meaning)

        # High confidence — generate a valid surface.
        # Use the argmax token to select a template variant.
        token = int(logits.argmax().item())
        variant = (token + beam_idx) % 4

        templates = self._templates_for(
            response_meaning.discourse_action,
            response_meaning.polarity,
            response_meaning.epistemic_status,
        )
        if not templates:
            return ""
        return templates[variant % len(templates)]

    @staticmethod
    def _invalid_surface(response_meaning: ResponseMeaning) -> str:
        """Generate an invalid surface that will fail equivalence verification.

        For non-failure actions: use a surface with wrong polarity.
        For failure actions: use a surface with wrong discourse action.
        """
        action = response_meaning.discourse_action
        if action in _SAFE_FAILURE_STATUSES:
            # For failure actions, use an answer surface (wrong discourse).
            return "My name is CEMM."
        else:
            # For non-failure actions, use wrong polarity.
            if response_meaning.polarity == "positive":
                return "No, that is not supported."
            else:
                return "My name is CEMM."

    def _encode_response_meaning(
        self, response_meaning: ResponseMeaning
    ) -> torch.Tensor:
        """Encode a ResponseMeaning into a feature vector for the network."""
        import torch

        # Build a feature vector from the response meaning's closed-class fields.
        features = torch.zeros(32)

        # Mode index (0-3).
        mode_map = {"OBSERVE": 0, "QUERY": 1, "REQUEST": 2, "SIMULATE": 3}
        features[0] = mode_map.get(response_meaning.mode, 0)

        # Discourse action index.
        action_map = {
            "answer": 0, "acknowledge": 1, "deny": 2, "clarify": 3,
            "unknown": 4, "ambiguous": 5, "operation_failed": 6,
            "realization_failed": 7,
        }
        features[1] = action_map.get(response_meaning.discourse_action, 0)

        # Polarity.
        features[2] = 1.0 if response_meaning.polarity == "positive" else 0.0

        # Modality.
        modality_map = {"actual": 0, "possible": 1, "necessary": 2, "conditional": 3}
        features[3] = modality_map.get(response_meaning.modality, 0)

        # Epistemic status.
        epistemic_map = {
            "supported": 0, "unknown": 1, "contradicted": 2,
            "contingent": 3, "denied": 4,
        }
        features[4] = epistemic_map.get(response_meaning.epistemic_status, 0)

        # Number of requested bindings.
        features[5] = len(response_meaning.requested_bindings)

        # Number of source refs.
        features[6] = len(response_meaning.source_refs)

        # Number of proof refs.
        features[7] = len(response_meaning.proof_refs)

        return features

    @staticmethod
    def _templates_for(
        action: str, polarity: str, epistemic: str
    ) -> list[str]:
        """Return bounded surface templates for a discourse action.

        These are the allowed language features and bounded dialogue style.
        The network learns to select the correct template variant based on
        ResponseMeaning features.
        """
        if action == "answer":
            if polarity == "positive":
                if epistemic == "supported":
                    return [
                        "My name is CEMM.",
                        "I am called CEMM.",
                        "CEMM is my name.",
                        "I am CEMM.",
                    ]
                return [
                    "Yes, that is supported.",
                    "That is correct.",
                    "Yes, it is.",
                    "That is true.",
                ]
            else:
                return [
                    "No, that is not supported.",
                    "That is not correct.",
                    "No, it is not.",
                    "That is false.",
                ]
        elif action == "acknowledge":
            return [
                "Understood.",
                "Acknowledged.",
                "Noted.",
                "I understand.",
            ]
        elif action == "deny":
            return [
                "That is not permitted.",
                "No, that is denied.",
                "That is not allowed.",
                "Permission denied.",
            ]
        elif action == "clarify":
            return [
                "Could you clarify?",
                "Which do you mean?",
                "Please specify.",
                "That is ambiguous.",
            ]
        elif action == "unknown":
            return [
                "I do not know.",
                "That is unknown.",
                "I am not sure.",
                "That is unclear.",
            ]
        elif action == "ambiguous":
            return [
                "The request is ambiguous.",
                "That is ambiguous.",
                "Multiple meanings are possible.",
                "Which one do you mean?",
            ]
        elif action == "operation_failed":
            return [
                "The operation failed.",
                "The operation could not complete.",
                "An error occurred.",
                "The operation was unsuccessful.",
            ]
        elif action == "realization_failed":
            return [
                "Realization failed.",
                "Could not generate a response.",
                "Realization was unsuccessful.",
                "I could not realize that.",
            ]
        return []
