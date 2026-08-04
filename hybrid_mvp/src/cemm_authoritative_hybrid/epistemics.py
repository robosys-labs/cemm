"""Epistemic placement, claim occurrence, and policy-derived admission.

Every claim records source, evidence, interval, confidence, modality, scope,
and revision.  :class:`AdmissionDecision` is policy-derived and cannot be
requested by a lexical token.  Corrections supersede exact occurrences without
deleting provenance.  Belief, desire, prediction, quotation, report, and
simulation remain nested placements — they never become world truth directly.

The :class:`EpistemicEngine` classifies a verified program's epistemic
placement from its structural properties (force, modality, provenance) and
applies policy to produce an admission decision.  Only ``observed`` claims
with evidence are admitted as world truth; all other modes remain attributed
to their source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from .authority import LinkedAuthority
from .canonical import stable_ref
from .config import RuntimeConfig

__all__ = [
    "EpistemicPlacement",
    "ClaimOccurrence",
    "AdmissionDecision",
    "EpistemicEngine",
    "PlacementMode",
    "AdmissionStatus",
]

PlacementMode = Literal[
    "reported",
    "believed",
    "desired",
    "predicted",
    "quoted",
    "simulated",
    "observed",
    "corrected",
]

AdmissionStatus = Literal[
    "admitted",
    "attributed",
    "contested",
    "corrected",
    "rejected",
]

# Modes that remain nested placements (never become world truth directly).
_NESTED_MODES = frozenset(
    {"reported", "believed", "desired", "predicted", "quoted", "simulated"}
)


# ---------------------------------------------------------------------------
# Epistemic placement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EpistemicPlacement:
    """The epistemic placement of a claim.

    Attributes:
        source_ref: the entity or channel that is the source of the claim
            (e.g. ``"entity:ada"``, ``"sensor:door-0"``).
        mode: the epistemic mode — how the claim is placed.
        evidence_refs: tuple of evidence refs supporting the placement.
        interval: ``(start, end)`` temporal interval for the placement.
        confidence: confidence in the placement (0.0–1.0).
        modality: modal qualifier (``"actual"``, ``"possible"``, …).
        scope: scope of the claim (``"world"``, ``"nested"``).
        revision: the world revision at which the placement was classified.
    """

    source_ref: str
    mode: PlacementMode
    evidence_refs: tuple[str, ...] = ()
    interval: tuple[int, int] = (0, 0)
    confidence: float = 1.0
    modality: str = "actual"
    scope: str = "world"
    revision: int = 0


# ---------------------------------------------------------------------------
# Claim occurrence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaimOccurrence:
    """A single occurrence of a claim with its epistemic placement.

    Attributes:
        occurrence_ref: stable ref uniquely identifying this occurrence.
        proposition_ref: the proposition being claimed (e.g. a graph root
            application ref).
        placement: the :class:`EpistemicPlacement` of this occurrence.
        claim_ref: the claim this occurrence belongs to (groups corrections
            and re-statements of the same claim).
    """

    occurrence_ref: str
    proposition_ref: str
    placement: EpistemicPlacement
    claim_ref: str = ""


# ---------------------------------------------------------------------------
# Admission decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmissionDecision:
    """A policy-derived admission decision for a claim occurrence.

    The decision is policy-derived and cannot be requested by a lexical token.

    Attributes:
        status: one of ``"admitted"``, ``"attributed"``, ``"contested"``,
            ``"corrected"``, ``"rejected"``.
        policy_ref: the policy ref that produced this decision.
        placement: the epistemic placement that was evaluated.
        proof_refs: tuple of proof refs supporting the decision.
    """

    status: AdmissionStatus
    policy_ref: str
    placement: EpistemicPlacement
    proof_refs: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Epistemic engine
# ---------------------------------------------------------------------------


class EpistemicEngine:
    """Classifies claim occurrences and produces policy-derived admissions.

    The engine classifies a verified program's epistemic placement from its
    structural properties (force, modality, provenance) — never from a lexical
    token.  It then applies admission policy to determine whether the claim
    becomes world truth or remains a nested attribution.
    """

    def __init__(self, authority: LinkedAuthority, config: RuntimeConfig) -> None:
        self._authority = authority
        self._config = config

    def classify(self, program: Any, orientation: Any) -> ClaimOccurrence:
        """Classify a verified program's epistemic placement.

        The epistemic mode is derived from the program's provenance metadata
        (which is set by the proposer from structural evidence, not lexical
        tokens).  Reported speech, belief, desire, prediction, quotation, and
        simulation are classified as nested placements.  Observed claims with
        evidence are candidates for world admission.
        """
        provenance: Mapping[str, Any] = dict(getattr(program.graph, "provenance", {}))
        evidence: Mapping[str, Any] = dict(getattr(program, "evidence", {}))

        # Derive epistemic mode from provenance (set structurally by proposer).
        epistemic_mode = provenance.get("epistemic_mode", "observed")
        source_ref = provenance.get("source_ref", "participant:user")
        evidence_refs = tuple(provenance.get("evidence_refs", ()))
        interval = tuple(provenance.get("interval", (0, 0)))
        confidence = float(provenance.get("confidence", 1.0))
        modality = getattr(program.graph, "modality", "actual")
        scope = provenance.get("scope", "world")
        revision = getattr(orientation, "world_revision", 0)

        placement = EpistemicPlacement(
            source_ref=source_ref,
            mode=epistemic_mode,
            evidence_refs=evidence_refs,
            interval=interval,
            confidence=confidence,
            modality=modality,
            scope=scope,
            revision=revision,
        )

        proposition_ref = getattr(program.graph, "root_application_ref", program.program_ref)
        claim_ref = provenance.get("claim_ref", program.program_ref)
        occurrence_ref = stable_ref(
            "occurrence",
            {
                "proposition": proposition_ref,
                "source": source_ref,
                "mode": epistemic_mode,
                "revision": revision,
            },
        )

        return ClaimOccurrence(
            occurrence_ref=occurrence_ref,
            proposition_ref=proposition_ref,
            placement=placement,
            claim_ref=claim_ref,
        )

    def admit(self, occurrence: ClaimOccurrence) -> AdmissionDecision:
        """Produce a policy-derived admission decision for an occurrence.

        Policy:
        - ``corrected`` → status ``"corrected"`` (supersedes exact occurrences
          without deleting provenance).
        - Nested modes (reported, believed, desired, predicted, quoted,
          simulated) → status ``"attributed"`` (remains a nested placement,
          never world truth).
        - ``observed`` with evidence → status ``"admitted"`` (world truth).
        - ``observed`` without evidence → status ``"contested"``.
        """
        mode = occurrence.placement.mode

        if mode == "corrected":
            status: AdmissionStatus = "corrected"
            policy_ref = "policy:correction_supersede"
        elif mode in _NESTED_MODES:
            status = "attributed"
            policy_ref = "policy:nested_placement"
        elif mode == "observed":
            if occurrence.placement.evidence_refs:
                status = "admitted"
                policy_ref = "policy:observed_with_evidence"
            else:
                status = "contested"
                policy_ref = "policy:observed_without_evidence"
        else:
            status = "rejected"
            policy_ref = "policy:unknown_mode"

        proof_refs = (occurrence.occurrence_ref,)

        return AdmissionDecision(
            status=status,
            policy_ref=policy_ref,
            placement=occurrence.placement,
            proof_refs=proof_refs,
        )
