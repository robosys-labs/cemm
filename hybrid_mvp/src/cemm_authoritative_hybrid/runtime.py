"""One canonical Hybrid MVP runtime through the R3 boundary.

The public path is ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT →
ResponseMeaning.  Surface realization remains an exact R5 later-owner gap.
No post-VERIFY owner receives Program structure or source text as meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .config import RuntimeConfig
from .contributions import ContributionExpander
from .cycle import (
    CycleFinalizer as _LegacyCycleFinalizer,
    CycleStatus,
    Orientation,
    PhaseDisposition,
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
from .mode import StructuralModeProjector
from .persistence import SemanticStores
from .proposal import ProposalOwner, ProposalResult
from .proposal_context import ProposalContext, ProposalContextBuilder
from .r3_cycle import CycleFinalizer, CycleResult
from .r3_effects import EffectReceipt, NoEffectReceipt
from .r3_kernel import R3Artifacts, R3Owner
from .r3_persistence import (
    begin_turn,
    focus_snapshot,
    obligation_snapshot,
    session_snapshot,
)
from .situation import SituationInputBundle
from .verifier import VerificationBatch

__all__ = [
    "OrientedTurn",
    "OrientationOwner",
    "RuntimeOrientationOwner",
    "VerificationOwner",
    "HybridRuntime",
]


@dataclass(frozen=True)
class OrientedTurn:
    """Transient exact ORIENT result used by the canonical runtime only."""

    orientation: Orientation
    context: ProposalContext
    situation_inputs: SituationInputBundle

    def __post_init__(self) -> None:
        if type(self.orientation) is not Orientation:
            raise TypeError("orientation must be exact Orientation")
        if type(self.context) is not ProposalContext:
            raise TypeError("context must be exact ProposalContext")
        if type(self.situation_inputs) is not SituationInputBundle:
            raise TypeError("situation_inputs must be exact SituationInputBundle")
        if self.context.orientation_ref != self.orientation.orientation_ref:
            raise ValueError("ProposalContext does not bind Orientation")
        if self.context.revision_pin != self.orientation.revision_pin:
            raise ValueError("ProposalContext and Orientation pins differ")
        if (
            self.context.evidence_packet_ref
            != self.situation_inputs.evidence.packet_ref
        ):
            raise ValueError("Situation inputs do not bind ProposalContext evidence")


@runtime_checkable
class OrientationOwner(Protocol):
    def orient(
        self, session_ref: str, text: str
    ) -> tuple[Orientation, ProposalContext]: ...


@runtime_checkable
class VerificationOwner(Protocol):
    def verify_candidates(
        self, proposal: ProposalResult, context: ProposalContext
    ) -> VerificationBatch: ...


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _snapshot_refs(snapshot: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = snapshot.get(field, ())
    if type(value) not in {tuple, list}:
        raise TypeError(f"{field} snapshot field must be a sequence")
    refs = tuple(value)
    if any(type(ref) is not str or not ref for ref in refs):
        raise TypeError(f"{field} snapshot contains invalid refs")
    return tuple(dict.fromkeys(refs))


class RuntimeOrientationOwner:
    """Bounded evidence-to-context owner with no store-private access."""

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
        mode_projector: StructuralModeProjector | None = None,
        resource_refs: tuple[str, ...] = (),
        adapter_refs: tuple[str, ...] = (),
    ) -> None:
        if type(stores) is not SemanticStores:
            raise TypeError("stores must be exact SemanticStores")
        if type(config) is not RuntimeConfig:
            raise TypeError("config must be exact RuntimeConfig")
        if type(resource_refs) is not tuple or any(
            type(ref) is not str or not ref for ref in resource_refs
        ):
            raise TypeError("resource_refs must be an exact ref tuple")
        if type(adapter_refs) is not tuple or any(
            type(ref) is not str or not ref for ref in adapter_refs
        ):
            raise TypeError("adapter_refs must be an exact ref tuple")
        self._authority = authority
        self._stores = stores
        self._config = config
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._contribution_expander = contribution_expander
        self._context_builder = context_builder
        self._mode_projector = mode_projector or StructuralModeProjector()
        self._resource_refs = tuple(dict.fromkeys(resource_refs))
        self._adapter_refs = tuple(dict.fromkeys(adapter_refs))

    def _text_evidence(self, session_ref: str, text: str) -> EvidencePacket:
        if type(text) is not str:
            raise TypeError("text must be exact str")
        source_ref = stable_ref(
            "text_source", {"session_ref": session_ref, "source_text": text}
        )
        return EvidencePacket.create(
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

    @staticmethod
    def _evidence_policies(evidence: EvidencePacket) -> tuple[str, ...]:
        policies: list[str] = []
        for item in evidence.items:
            if item.source == "text":
                policies.append("policy:evidence:text_attributed")
            elif item.source == "sensor":
                if item.adapter_receipt_ref is None:
                    raise ValueError("sensor evidence requires adapter receipt")
                policies.append("policy:evidence:reviewed_sensor")
            elif item.source == "operation":
                if item.adapter_receipt_ref is None:
                    raise ValueError("operation evidence requires adapter receipt")
                policies.append("policy:evidence:reviewed_operation")
            else:  # Evidence ABI is closed; retain fail-closed defense.
                raise ValueError("unsupported evidence kind")
        return tuple(dict.fromkeys(policies))

    def orient_turn(
        self, session_ref: str, evidence: EvidencePacket
    ) -> OrientedTurn:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        if type(evidence) is not EvidencePacket:
            raise TypeError("evidence must be exact EvidencePacket")
        if EvidencePacket.from_dict(evidence.as_dict()) != evidence:
            raise ValueError("evidence is non-canonical")
        if evidence.form_pack_hash != self._form_resolver.form_pack_hash:
            raise ValueError("evidence form-pack hash differs from active resolver")

        # The turn reservation is read-only.  It is durably finalized by EFFECT,
        # preserving the architecture rule that only EFFECT changes revisions.
        turn = begin_turn(self._stores, session_ref)
        session = session_snapshot(self._stores, session_ref)
        focus = focus_snapshot(
            self._stores,
            session_ref,
            maximum=self._config.max_orientation_alternatives,
        )
        obligations = obligation_snapshot(
            self._stores,
            session_ref,
            maximum=self._config.max_orientation_alternatives,
        )
        pin = self._stores.revision_pin()

        lattice = self._form_resolver.resolve_evidence(evidence)
        mode_projection = self._mode_projector.project(lattice)
        grounding = self._grounder.ground_lattice(lattice, pin)
        contributions = self._contribution_expander.expand(grounding, lattice)

        participants = tuple(sorted(self._authority.by_kind("participant")))
        required = {"participant:user", "participant:system"}
        missing = tuple(sorted(required - set(participants)))
        if missing:
            raise ValueError(
                f"required runtime participants are absent from authority: {missing}"
            )
        capabilities = tuple(
            self._authority.capabilities.get("participant:system", ())
        )
        permissions = tuple(
            row if type(row) is str else f"{row[0]}:{row[1]}:{row[2]}"
            for row in self._authority.permissions
        )
        focus_refs = _snapshot_refs(focus, "focus_refs")
        obligation_refs = _snapshot_refs(obligations, "obligation_refs")
        turn_ref = str(turn["turn_ref"])
        turn_index = int(turn["turn_index"])
        session_phase_ref = str(session["session_phase_ref"])
        event_refs = (
            stable_ref("session_event", {"session_ref": session_ref}),
            turn_ref,
        )
        visited_refs = _unique(
            (
                *participants,
                *event_refs,
                *focus_refs,
                *obligation_refs,
                mode_projection.projection_ref,
            )
        )
        orientation = Orientation.create(
            session_ref=session_ref,
            turn_ref=turn_ref,
            source_text=evidence.source_text,
            mode=mode_projection.mode,
            participant_frame="participant:user",
            temporal_frame="time:now",
            participants=participants,
            active_turn_ref=turn_ref,
            event_refs=event_refs,
            focus_refs=focus_refs,
            obligation_refs=obligation_refs,
            capability_summary=capabilities,
            permission_summary=permissions,
            budgets={"input_tokens": self._config.max_input_tokens},
            scanned_atom_count=0,
            index_probes=(
                "forms:structural_mode_projection",
                "stores:session_snapshot",
                "stores:verified_focus_snapshot",
                "stores:obligation_snapshot",
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
        permission_snapshot_ref = stable_ref(
            "permission_snapshot",
            {
                "permission_refs": list(permissions),
                "revision_pin": pin.as_dict(),
            },
        )
        resource_snapshot_ref = stable_ref(
            "resource_snapshot",
            {
                "resource_refs": list(self._resource_refs),
                "revision_pin": pin.as_dict(),
            },
        )
        adapter_snapshot_ref = stable_ref(
            "adapter_snapshot",
            {
                "adapter_refs": list(self._adapter_refs),
                "revision_pin": pin.as_dict(),
            },
        )
        inputs = SituationInputBundle.create(
            evidence=evidence,
            turn_index=turn_index,
            session_phase_ref=session_phase_ref,
            focus_snapshot_ref=str(focus["snapshot_ref"]),
            focus_refs=focus_refs,
            obligation_snapshot_ref=str(obligations["snapshot_ref"]),
            obligation_refs=obligation_refs,
            permission_snapshot_ref=permission_snapshot_ref,
            resource_snapshot_ref=resource_snapshot_ref,
            resource_refs=self._resource_refs,
            adapter_snapshot_ref=adapter_snapshot_ref,
            adapter_refs=self._adapter_refs,
            evidence_policy_refs=self._evidence_policies(evidence),
        )
        return OrientedTurn(orientation, context, inputs)

    def orient(
        self, session_ref: str, text: str
    ) -> tuple[Orientation, ProposalContext]:
        turn = self.orient_turn(session_ref, self._text_evidence(session_ref, text))
        return turn.orientation, turn.context

    def text_evidence(self, session_ref: str, text: str) -> EvidencePacket:
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        return self._text_evidence(session_ref, text)

    def evidence_packet(
        self,
        session_ref: str,
        text: str,
        *,
        extra_items: tuple[EvidenceItem, ...] = (),
    ) -> EvidencePacket:
        if type(extra_items) is not tuple or any(
            type(item) is not EvidenceItem for item in extra_items
        ):
            raise TypeError("extra_items must be an exact EvidenceItem tuple")
        if any(item.source == "text" for item in extra_items):
            raise ValueError("extra_items cannot contain a second text source")
        base = self._text_evidence(session_ref, text)
        return EvidencePacket.create(
            items=(*base.items, *extra_items),
            source_text=text,
            form_pack_hash=self._form_resolver.form_pack_hash,
        )


class HybridRuntime:
    """Execute exactly one canonical six-phase cognitive path."""

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
            raise TypeError("profile must be exact nonempty str")
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
        for name, contract in requirements.items():
            owner = self._owners.get(name)
            if owner is None:
                raise MissingOwner(f"{name}_owner")
            if not isinstance(owner, contract):
                raise TypeError(f"{name} owner violates its exact protocol")
        r3_owner = self._owners.get("r3")
        if r3_owner is not None and not isinstance(r3_owner, R3Owner):
            raise TypeError("r3 owner violates its exact protocol")

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
        return self._owners["orientation"].orient(session_ref, text)

    def _orient_turn(
        self, session_ref: str, evidence: EvidencePacket
    ) -> OrientedTurn:
        result = self._owners["orientation"].orient_turn(session_ref, evidence)
        if type(result) is not OrientedTurn:
            raise TypeError("ORIENT owner must return exact OrientedTurn")
        return result

    def create_evidence(
        self,
        session_ref: str,
        text: str,
        *,
        extra_items: tuple[EvidenceItem, ...] = (),
    ) -> EvidencePacket:
        return self._owners["orientation"].evidence_packet(
            session_ref, text, extra_items=extra_items
        )

    def process(
        self, session_ref: str, text: str, *, trace: bool = True
    ) -> CycleResult:
        if "r3" in self._owners:
            evidence = self.create_evidence(session_ref, text)
            return self.process_evidence(session_ref, evidence, trace=trace)
        return self._process_legacy(session_ref, text, trace=trace)

    def _process_legacy(
        self, session_ref: str, text: str, *, trace: bool = True
    ) -> CycleResult:
        started = time.perf_counter_ns()
        orientation, context = self.orient(session_ref, text)
        orient_ns = time.perf_counter_ns() - started

        started = time.perf_counter_ns()
        proposal = self._owners["proposal"].propose(context)
        propose_ns = time.perf_counter_ns() - started
        if type(proposal) is not ProposalResult:
            raise TypeError("PROPOSE owner returned non-canonical ProposalResult")

        started = time.perf_counter_ns()
        verification = self._owners["verification"].verify_candidates(
            proposal, context
        )
        verify_ns = time.perf_counter_ns() - started
        if type(verification) is not VerificationBatch:
            raise TypeError("VERIFY owner returned non-canonical VerificationBatch")

        verify_disposition, verify_codes, early_status, early_gap = (
            self._verification_outcome(proposal, verification)
        )
        pin = context.revision_pin
        orient_outputs = (orientation.orientation_ref, context.context_ref)
        verify_outputs = (verification.batch_ref,)
        if verification.status == "selected":
            meaning = verification.selected_meaning
            if meaning is None:
                raise AssertionError("selected verification lacks meaning")
            verify_outputs = (verification.batch_ref, meaning.verified_meaning_ref)
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
                verify_outputs,
                pin,
                pin,
                verify_disposition,
                verify_codes,
                {"candidates": len(verification.candidate_receipts)},
            ),
        )
        if verification.status != "selected":
            assert early_gap is not None
            return _LegacyCycleFinalizer.finalize(
                input_ref=context.evidence_packet_ref,
                status=early_status,
                orientation=orientation,
                proposal=proposal,
                verification=verification,
                evaluation=None,
                effect_receipt=None,
                response_meaning=None,
                realization_receipt=None,
                gap_receipt=early_gap,
                phase_material=materials,
                final_revision_pin=pin,
                capture_trace=trace,
                durations_ns=(orient_ns, propose_ns, verify_ns),
            )

        meaning = verification.selected_meaning
        assert meaning is not None
        if self._owners.get("r3") is None:
            gap = GapClassifier().classify(
                LaterOwnerNotAdmitted(
                    meaning.verified_meaning_ref, "contract:r3:evaluate"
                )
            )
            return _LegacyCycleFinalizer.finalize(
                input_ref=context.evidence_packet_ref,
                status=CycleStatus.PARTIAL,
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
        return self._run_r3(
            session_ref, orientation, context, proposal, verification, meaning,
            materials, orient_ns, propose_ns, verify_ns, trace,
        )

    def process_evidence(
        self,
        session_ref: str,
        evidence: EvidencePacket,
        *,
        trace: bool = True,
    ) -> CycleResult:
        started = time.perf_counter_ns()
        turn = self._orient_turn(session_ref, evidence)
        orientation, context = turn.orientation, turn.context
        orient_ns = time.perf_counter_ns() - started

        started = time.perf_counter_ns()
        proposal = self._owners["proposal"].propose(context)
        propose_ns = time.perf_counter_ns() - started
        if type(proposal) is not ProposalResult:
            raise TypeError("PROPOSE owner returned non-canonical ProposalResult")

        started = time.perf_counter_ns()
        verification = self._owners["verification"].verify_candidates(
            proposal, context
        )
        verify_ns = time.perf_counter_ns() - started
        if type(verification) is not VerificationBatch:
            raise TypeError("VERIFY owner returned non-canonical VerificationBatch")

        verify_disposition, verify_codes, early_status, early_gap = (
            self._verification_outcome(proposal, verification)
        )
        pin = context.revision_pin
        orient_outputs = (orientation.orientation_ref, context.context_ref)
        verify_outputs = (verification.batch_ref,)
        if verification.status == "selected":
            meaning = verification.selected_meaning
            if meaning is None:
                raise AssertionError("selected verification lacks meaning")
            verify_outputs = (verification.batch_ref, meaning.verified_meaning_ref)
        base_materials = (
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
                verify_outputs,
                pin,
                pin,
                verify_disposition,
                verify_codes,
                {"candidates": len(verification.candidate_receipts)},
            ),
        )
        if verification.status != "selected":
            assert early_gap is not None
            return CycleFinalizer.finalize(
                input_ref=context.evidence_packet_ref,
                status=early_status,
                orientation=orientation,
                proposal=proposal,
                verification=verification,
                evaluation=None,
                effect_receipt=None,
                response_meaning=None,
                realization_receipt=None,
                gap_receipt=early_gap,
                phase_material=base_materials,
                final_revision_pin=pin,
                capture_trace=trace,
                durations_ns=(orient_ns, propose_ns, verify_ns),
            )

        meaning = verification.selected_meaning
        assert meaning is not None
        if self._owners.get("r3") is None:
            gap = GapClassifier().classify(
                LaterOwnerNotAdmitted(
                    meaning.verified_meaning_ref, "contract:r3:evaluate"
                )
            )
            return CycleFinalizer.finalize(
                input_ref=context.evidence_packet_ref,
                status=CycleStatus.PARTIAL,
                orientation=orientation,
                proposal=proposal,
                verification=verification,
                evaluation=None,
                effect_receipt=None,
                response_meaning=None,
                realization_receipt=None,
                gap_receipt=gap,
                phase_material=base_materials,
                final_revision_pin=pin,
                capture_trace=trace,
                durations_ns=(orient_ns, propose_ns, verify_ns),
            )
        return self._run_r3(
            session_ref, orientation, context, proposal, verification, meaning,
            base_materials, orient_ns, propose_ns, verify_ns, trace,
            situation_inputs=turn.situation_inputs,
        )

    def _run_r3(
        self,
        session_ref: str,
        orientation: Orientation,
        context: ProposalContext,
        proposal: ProposalResult,
        verification: VerificationBatch,
        meaning: VerifiedMeaning,
        base_materials: tuple[_PhaseMaterial, ...],
        orient_ns: int,
        propose_ns: int,
        verify_ns: int,
        trace: bool,
        *,
        situation_inputs: SituationInputBundle | None = None,
    ) -> CycleResult:
        if situation_inputs is None:
            raise TypeError("R3 requires situation_inputs from OrientedTurn")
        started = time.perf_counter_ns()
        artifacts: R3Artifacts = self._owners["r3"].run(
            meaning=meaning,
            orientation=orientation,
            context=context,
            situation_inputs=situation_inputs,
        )
        r3_ns = time.perf_counter_ns() - started
        evaluation = artifacts.evaluation
        effect = artifacts.effect
        response = artifacts.response_meaning
        effect_disposition = (
            PhaseDisposition.NO_EFFECT
            if type(effect) is NoEffectReceipt
            else PhaseDisposition.COMMITTED
        )
        gap = GapClassifier().classify(
            LaterOwnerNotAdmitted(
                response.response_meaning_ref, "contract:r5:realize_surface"
            )
        )
        materials = (
            *base_materials,
            _PhaseMaterial(
                SemanticPhase.EVALUATE,
                (
                    verification.batch_ref,
                    meaning.verified_meaning_ref,
                    orientation.orientation_ref,
                    context.context_ref,
                ),
                (artifacts.situation.situation_ref, evaluation.evaluation_ref),
                artifacts.input_revision_pin,
                artifacts.input_revision_pin,
                PhaseDisposition.COMPLETED,
                (),
                {"applications": len(meaning.expression.applications)},
            ),
            _PhaseMaterial(
                SemanticPhase.EFFECT,
                (artifacts.situation.situation_ref, evaluation.evaluation_ref),
                (effect.receipt_ref,),
                artifacts.input_revision_pin,
                artifacts.output_revision_pin,
                effect_disposition,
                (),
                {"receipts": 1},
            ),
            _PhaseMaterial(
                SemanticPhase.REALIZE,
                (effect.receipt_ref,),
                (response.response_meaning_ref,),
                artifacts.output_revision_pin,
                artifacts.output_revision_pin,
                PhaseDisposition.GAP,
                ("later_owner_not_admitted",),
                {"response_contracts": 1},
            ),
        )
        return CycleFinalizer.finalize(
            input_ref=context.evidence_packet_ref,
            status=response.cycle_status,
            orientation=orientation,
            proposal=proposal,
            verification=verification,
            evaluation=evaluation,
            effect_receipt=effect,
            response_meaning=response,
            realization_receipt=None,
            gap_receipt=gap,
            phase_material=materials,
            final_revision_pin=artifacts.output_revision_pin,
            capture_trace=trace,
            durations_ns=(orient_ns, propose_ns, verify_ns, r3_ns, 0, 0),
        )

    @staticmethod
    def _verification_outcome(
        proposal: ProposalResult, verification: VerificationBatch
    ) -> tuple[
        PhaseDisposition, tuple[str, ...], CycleStatus, GapReceipt | None
    ]:
        if verification.status == "selected":
            return PhaseDisposition.COMPLETED, (), CycleStatus.PARTIAL, None
        if verification.status == "abstained":
            code = proposal.abstention_code or "proposal:abstained"
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
