"""One canonical R1 runtime path from evidence to verified meaning.

R1 admits ORIENT, PROPOSE and VERIFY. A selected ``VerifiedMeaning`` stops at
the exact ``LaterOwnerNotAdmitted`` boundary for ``contract:r3:evaluate``.
Programs remain construction lineage; they are never passed to a later
semantic owner as meaning.
"""

from __future__ import annotations

import time
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .config import RuntimeConfig
from .contributions import ContributionExpander
from .cycle import (
    CycleFinalizer,
    CycleResult,
    CycleStatus,
    Orientation,
    PhaseDisposition,
    SemanticMode,
    SemanticPhase,
    _PhaseMaterial,
)
from .forms import EvidenceItem, EvidencePacket, FormResolver
from .gaps import (
    GapClassifier,
    GapKind,
    GapReceipt,
    LaterOwnerNotAdmitted,
    MissingOwner,
    RepairOwner,
)
from .grounding import Grounder
from .persistence import SemanticStores
from .proposal import ProposalOwner, ProposalResult
from .proposal_context import ProposalContext, ProposalContextBuilder
from .verifier import VerificationBatch

__all__ = [
    "OrientationOwner",
    "RuntimeOrientationOwner",
    "VerificationOwner",
    "HybridRuntime",
]


@runtime_checkable
class OrientationOwner(Protocol):
    """Own one exact evidence-to-``ProposalContext`` ORIENT pass."""

    def orient(
        self, session_ref: str, text: str
    ) -> tuple[Orientation, ProposalContext]:
        raise NotImplementedError


@runtime_checkable
class VerificationOwner(Protocol):
    """Independently verify one proposal against the same exact context."""

    def verify_candidates(
        self, proposal: ProposalResult, context: ProposalContext
    ) -> VerificationBatch:
        raise NotImplementedError


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


class RuntimeOrientationOwner:
    """Bounded canonical ORIENT composition without resolver re-entry."""

    def __init__(
        self,
        *,
        authority: Any,
        stores: SemanticStores,
        config: RuntimeConfig,
        form_resolver: FormResolver,
        grounder: Grounder,
        contribution_expander: ContributionExpander,
        context_builder: ProposalContextBuilder,
    ) -> None:
        if type(stores) is not SemanticStores:
            raise TypeError("stores must be exact SemanticStores")
        if type(config) is not RuntimeConfig:
            raise TypeError("config must be exact RuntimeConfig")
        if type(form_resolver) is not FormResolver:
            raise TypeError("form_resolver must be exact FormResolver")
        if type(grounder) is not Grounder:
            raise TypeError("grounder must be exact Grounder")
        if type(contribution_expander) is not ContributionExpander:
            raise TypeError(
                "contribution_expander must be exact ContributionExpander"
            )
        if type(context_builder) is not ProposalContextBuilder:
            raise TypeError("context_builder must be exact ProposalContextBuilder")
        self._authority = authority
        self._stores = stores
        self._config = config
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._contribution_expander = contribution_expander
        self._context_builder = context_builder

    def orient(
        self, session_ref: str, text: str
    ) -> tuple[Orientation, ProposalContext]:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be an exact nonempty str")
        if type(text) is not str:
            raise TypeError("text must be an exact str")

        source_ref = stable_ref(
            "text_source", {"session_ref": session_ref, "source_text": text}
        )
        evidence = EvidencePacket.create(
            items=(
                EvidenceItem.create(
                    source="text",
                    content=text,
                    source_ref=source_ref,
                    provenance_refs=(),
                    adapter_receipt_ref=None,
                ),
            ),
            source_text=text,
            form_pack_hash=self._form_resolver.form_pack_hash,
        )
        lattice = self._form_resolver.resolve_evidence(evidence)
        pin = self._stores.revision_pin()
        grounding = self._grounder.ground_lattice(lattice, pin)
        contributions = self._contribution_expander.expand(grounding, lattice)

        participants = tuple(sorted(self._authority.by_kind("participant")))
        focus_refs = _unique(tuple(row.target_ref for row in grounding.designations))
        turn_ref = f"turn:{session_ref}"
        event_refs = (f"event:session:{session_ref}", turn_ref)
        capabilities = tuple(
            self._authority.capabilities.get("participant:system", ())
        )
        permissions = tuple(
            f"{subject}:{capability}:{resource}"
            for subject, capability, resource in self._authority.permissions
        )
        visited_refs = _unique((*participants, *event_refs, *focus_refs))
        orientation = Orientation.create(
            session_ref=session_ref,
            turn_ref=turn_ref,
            source_text=text,
            mode=SemanticMode.OBSERVE,
            participant_frame="participant:user",
            temporal_frame="now",
            participants=participants,
            active_turn_ref=turn_ref,
            event_refs=event_refs,
            focus_refs=focus_refs,
            obligation_refs=(),
            capability_summary=capabilities,
            permission_summary=permissions,
            budgets={"input_tokens": self._config.max_input_tokens},
            scanned_atom_count=0,
            index_probes=(
                "by_kind:participant",
                "grounding:exact_designations",
                "capabilities:participant:system",
                "permissions:activation_index",
            ),
            visited_refs=visited_refs,
            revision_pin=pin,
        )
        context = self._context_builder.build(
            orientation=orientation,
            evidence=evidence,
            form_lattice=lattice,
            grounding_result=grounding,
            contributions=contributions,
        )
        return orientation, context


class HybridRuntime:
    """Execute the single admitted ORIENT -> PROPOSE -> VERIFY path."""

    def __init__(
        self,
        config: RuntimeConfig,
        authority: Any,
        stores: SemanticStores,
        owners: Mapping[str, Any],
        *,
        profile: str,
    ) -> None:
        if type(config) is not RuntimeConfig:
            raise TypeError("config must be exact RuntimeConfig")
        if type(stores) is not SemanticStores:
            raise TypeError("stores must be exact SemanticStores")
        if type(profile) is not str or not profile:
            raise TypeError("profile must be an exact nonempty str")
        if not isinstance(owners, Mapping):
            raise TypeError("owners must be a mapping")
        self._config = config
        self._authority = authority
        self._stores = stores
        self._owners = dict(owners)
        self._profile = profile
        self._verify_owners()

    def _verify_owners(self) -> None:
        requirements = {
            "orientation": OrientationOwner,
            "proposal": ProposalOwner,
            "verification": VerificationOwner,
        }
        for owner_name, owner_contract in requirements.items():
            owner = self._owners.get(owner_name)
            if owner is None:
                raise MissingOwner(f"{owner_name}_owner")
            if not isinstance(owner, owner_contract):
                raise TypeError(f"{owner_name} owner violates its exact protocol")

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def config(self) -> RuntimeConfig:
        return self._config

    @property
    def authority(self) -> Any:
        return self._authority

    @property
    def stores(self) -> SemanticStores:
        return self._stores

    @property
    def proposal_model(self) -> ProposalOwner:
        return self._owners["proposal"]

    def orient(
        self, session_ref: str, text: str
    ) -> tuple[Orientation, ProposalContext]:
        result = self._owners["orientation"].orient(session_ref, text)
        if type(result) is not tuple or len(result) != 2:
            raise TypeError("ORIENT owner must return one exact artifact pair")
        orientation, context = result
        if type(orientation) is not Orientation:
            raise TypeError("ORIENT owner returned a non-canonical Orientation")
        if type(context) is not ProposalContext:
            raise TypeError("ORIENT owner returned a non-canonical ProposalContext")
        if context.orientation_ref != orientation.orientation_ref:
            raise ValueError("ProposalContext does not bind the exact Orientation")
        if context.revision_pin != orientation.revision_pin:
            raise ValueError("ProposalContext and Orientation revision pins differ")
        return orientation, context

    def process(
        self,
        session_ref: str,
        text: str,
        *,
        trace: bool = True,
    ) -> CycleResult:
        started = time.perf_counter_ns()
        orientation, context = self.orient(session_ref, text)
        orient_ns = time.perf_counter_ns() - started

        started = time.perf_counter_ns()
        proposal = self._owners["proposal"].propose(context)
        propose_ns = time.perf_counter_ns() - started
        if type(proposal) is not ProposalResult:
            raise TypeError("PROPOSE owner returned a non-canonical ProposalResult")

        started = time.perf_counter_ns()
        verification = self._owners["verification"].verify_candidates(
            proposal, context
        )
        verify_ns = time.perf_counter_ns() - started
        if type(verification) is not VerificationBatch:
            raise TypeError("VERIFY owner returned a non-canonical VerificationBatch")

        disposition, rejection_codes, status, gap = self._terminal_outcome(
            proposal, verification
        )
        pin = context.revision_pin
        orient_outputs = (orientation.orientation_ref, context.context_ref)
        materials = (
            _PhaseMaterial(
                SemanticPhase.ORIENT,
                (context.evidence_packet_ref,),
                orient_outputs,
                pin,
                pin,
                PhaseDisposition.COMPLETED,
                (),
                {"input_tokens": len(context.source_unit_refs)},
            ),
            _PhaseMaterial(
                SemanticPhase.PROPOSE,
                orient_outputs,
                (proposal.proposal_ref,),
                pin,
                pin,
                PhaseDisposition.COMPLETED,
                (),
                {"search_states": proposal.explored_states},
            ),
            _PhaseMaterial(
                SemanticPhase.VERIFY,
                (proposal.proposal_ref, context.context_ref),
                (verification.batch_ref,),
                pin,
                pin,
                disposition,
                rejection_codes,
                {"candidates": len(verification.candidate_receipts)},
            ),
        )
        return CycleFinalizer.finalize(
            input_ref=context.evidence_packet_ref,
            status=status,
            orientation=orientation,
            proposal=proposal,
            verification=verification,
            evaluation=None,
            effect_receipt=None,
            response_meaning=None,
            realization_receipt=None,
            gap_receipt=gap,
            phase_material=materials,
            final_revision_pin=pin,
            capture_trace=trace,
            durations_ns=(orient_ns, propose_ns, verify_ns),
        )

    @staticmethod
    def _terminal_outcome(
        proposal: ProposalResult,
        verification: VerificationBatch,
    ) -> tuple[PhaseDisposition, tuple[str, ...], CycleStatus, GapReceipt]:
        if verification.status == "selected":
            meaning = verification.selected_meaning
            if meaning is None:
                raise AssertionError("selected verification has no VerifiedMeaning")
            return (
                PhaseDisposition.COMPLETED,
                (),
                CycleStatus.PARTIAL,
                GapClassifier().classify(
                    LaterOwnerNotAdmitted(
                        meaning.verified_meaning_ref,
                        "contract:r3:evaluate",
                    )
                ),
            )
        if verification.status == "abstained":
            code = proposal.abstention_code
            if code is None:
                raise AssertionError("abstained verification lacks proposal code")
            return (
                PhaseDisposition.ABSTAINED,
                (code,),
                CycleStatus.UNSUPPORTED,
                GapReceipt.create(
                    kind=GapKind.PROPOSAL,
                    status="proposal_abstained",
                    source_refs=(proposal.proposal_ref, verification.batch_ref),
                    blockers=(code,),
                    recommended_owner=RepairOwner.TRAINING,
                    safe_response_action="request_proposal_review",
                ),
            )
        if verification.status == "rejected":
            return (
                PhaseDisposition.REJECTED,
                ("verification:rejected",),
                CycleStatus.UNSUPPORTED,
                GapReceipt.create(
                    kind=GapKind.VERIFICATION,
                    status="verification_rejected",
                    source_refs=(verification.batch_ref,),
                    blockers=("verification:rejected",),
                    rejected_candidate_refs=tuple(
                        row.candidate_ref for row in verification.candidate_receipts
                    ),
                    recommended_owner=RepairOwner.RUNTIME,
                    safe_response_action="reject_candidate",
                ),
            )
        if verification.status == "ambiguous":
            return (
                PhaseDisposition.GAP,
                ("verification:ambiguous",),
                CycleStatus.AMBIGUOUS,
                GapReceipt.create(
                    kind=GapKind.VERIFICATION,
                    status="verification_ambiguous",
                    source_refs=(verification.batch_ref,),
                    blockers=("verification:ambiguous",),
                    recommended_owner=RepairOwner.TRAINING,
                    safe_response_action="request_reference_resolution",
                ),
            )
        raise AssertionError("unknown closed VerificationBatch status")