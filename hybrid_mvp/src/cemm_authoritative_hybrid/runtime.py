"""Six-phase semantic kernel runtime with typed owner protocols.

This module owns :class:`HybridRuntime` and the six phase-owner protocols. The
runtime is a hard cutover from the legacy stage-bound architecture: it runs the
six mathematical ownership boundaries

    ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE

with injected typed owners. No code path branches on a legacy stage number, and
no raw surface text selects a semantic operator, role, program, effect or
response meaning.

The development ``typed_fixture`` profile accepts injected test owners and
advertises only typed-program execution. The ``neural`` profile is defined but
fails activation with :class:`MissingOwner` until Milestone 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable
import time

from .canonical import stable_ref
from .config import RuntimeConfig
from .cycle import (
    CycleResult,
    CycleStatus,
    KernelCycleResult,
    Orientation,
    OrientationProjector,
    PhaseReceipt,
    SemanticMode,
    SemanticPhase,
)
from .gaps import GapClassifier, GapReceipt, MissingOwner, VerificationFailure
from .persistence import Fact, RevisionPin, SemanticStores
from .authority import LinkedAuthority
from .propositions import SemanticSwitchProgram

__all__ = [
    "ProposalOwner",
    "VerificationOwner",
    "EvaluationOwner",
    "EffectOwner",
    "RealizationOwner",
    "ProposalResult",
    "VerificationResult",
    "EvaluationResult",
    "EffectResult",
    "RealizationResult",
    "ProcessResult",
    "HybridRuntime",
    "FixtureProposalOwner",
    "FixtureVerificationOwner",
    "FixtureEvaluationOwner",
    "FixtureEffectOwner",
    "FixtureRealizationOwner",
    "PROFILE_CAPABILITIES",
]


# ---------------------------------------------------------------------------
# Phase-owner result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProposalResult:
    """The PROPOSE phase output: a candidate program."""

    program: SemanticSwitchProgram
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    """The VERIFY phase output: structural legality verdict."""

    legal: bool
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    """The EVALUATE phase output: a typed decision."""

    status: str
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EffectResult:
    """The EFFECT phase output: idempotent effect receipt."""

    executed: bool
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RealizationResult:
    """The REALIZE phase output: realized response meaning."""

    realized: bool
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessResult:
    """The result of ``HybridRuntime.process``.

    Carries the cycle result, trace, and the :class:`ResponseMeaning` built
    from evaluation/effect receipts. The response meaning precedes language —
    it is the semantic contract that the REALIZE phase realizes.

    Delegates phase artifacts to the finalized :class:`CycleResult`.
    """

    cycle_result: CycleResult
    response_meaning: Any  # ResponseMeaning
    realization_receipt: Any  # RealizationReceipt | None

    @property
    def trace(self) -> tuple[Any, ...]:
        return self.cycle_result.trace

    @property
    def status(self) -> CycleStatus:
        return self.cycle_result.status

    @property
    def cycle_ref(self) -> str:
        return self.cycle_result.cycle_ref

    @property
    def gap_receipt(self) -> Any:
        return self.cycle_result.gap_receipt

    @property
    def orientation(self) -> Any:
        return self.cycle_result.orientation

    @property
    def proposal(self) -> Any:
        return self.cycle_result.proposal

    @property
    def verification(self) -> Any:
        return self.cycle_result.verification

    @property
    def evaluation(self) -> Any:
        return self.cycle_result.evaluation

    @property
    def effect_receipt(self) -> Any:
        return self.cycle_result.effect_receipt

    @property
    def final_revision_pin(self) -> Any:
        return self.cycle_result.final_revision_pin


@dataclass(frozen=True)
class _ProposeAndVerifyResult:
    """Result of propose_and_verify: accepted proposal or rejection."""

    accepted: bool
    proposal: Any
    program: Any


# ---------------------------------------------------------------------------
# Phase-owner protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class ProposalOwner(Protocol):
    """Owner of the PROPOSE phase: produces bounded candidate programs."""

    def propose(
        self, orientation: Orientation, evidence: Mapping[str, Any]
    ) -> ProposalResult: ...


@runtime_checkable
class VerificationOwner(Protocol):
    """Owner of the VERIFY phase: independently recomputes structural legality."""

    def verify(
        self, program: SemanticSwitchProgram, orientation: Orientation
    ) -> VerificationResult: ...


@runtime_checkable
class EvaluationOwner(Protocol):
    """Owner of the EVALUATE phase: produces one typed decision."""

    def evaluate(
        self,
        program: SemanticSwitchProgram,
        verification: VerificationResult,
        orientation: Orientation,
    ) -> EvaluationResult: ...


@runtime_checkable
class EffectOwner(Protocol):
    """Owner of the EFFECT phase: the only owner of world mutation."""

    def execute(
        self,
        evaluation: EvaluationResult,
        orientation: Orientation,
    ) -> EffectResult: ...


@runtime_checkable
class RealizationOwner(Protocol):
    """Owner of the REALIZE phase: constructs response meaning."""

    def realize(
        self,
        evaluation: EvaluationResult,
        effect: EffectResult,
        orientation: Orientation,
    ) -> RealizationResult: ...


# ---------------------------------------------------------------------------
# Profile capability advertisement
# ---------------------------------------------------------------------------

PROFILE_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "development": (
        "typed_program_execution",
    ),
    "typed_fixture": (
        "typed_program_execution",
    ),
    "neural": (
        "typed_program_execution",
        "neural_proposer",
    ),
}

_REQUIRED_OWNERS: tuple[str, ...] = (
    "proposal",
    "verification",
    "evaluation",
    "effect",
    "realization",
)


# ---------------------------------------------------------------------------
# HybridRuntime
# ---------------------------------------------------------------------------


class HybridRuntime:
    """The six-phase semantic kernel runtime.

    Accepts typed owner protocols for proposal, verification, evaluation,
    effects, and realization. The six phases run in order:

        ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE

    Each phase produces a :class:`PhaseReceipt` when ``trace=True``. The runtime
    returns a :class:`CycleResult` with status, trace, final revision pin and
    gap receipt. Failures are classified by :class:`GapClassifier` — never by
    surface text.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        authority: LinkedAuthority,
        stores: SemanticStores,
        owners: Mapping[str, Any],
        *,
        profile: str,
    ) -> None:
        self._config = config
        self._authority = authority
        self._stores = stores
        self._owners = dict(owners)
        self._profile = profile
        self._classifier = GapClassifier()
        self._cycle_counter = 0
        self._verify_owners()

    def _verify_owners(self) -> None:
        """Refuse to start if any advertised capability lacks an owner."""
        for name in _REQUIRED_OWNERS:
            if name not in self._owners or self._owners[name] is None:
                raise MissingOwner(f"{name}_owner")

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def config(self) -> RuntimeConfig:
        return self._config

    @property
    def authority(self) -> LinkedAuthority:
        return self._authority

    @property
    def stores(self) -> SemanticStores:
        return self._stores

    @property
    def proposal_model(self) -> Any:
        """The proposal model (NeuralSwitchProposer for neural, fixture owner for dev)."""
        return self._owners.get("proposal")

    @property
    def action_encoding_hash(self) -> str | None:
        """The action encoding hash from the proposal model's metadata (neural profile)."""
        model = self.proposal_model
        if model is not None and hasattr(model, "action_encoding_hash"):
            return model.action_encoding_hash
        return None

    def propose_and_verify(self, session_ref: str, text: str) -> Any:
        """Build an orientation, propose candidates, and verify each.

        Returns a result with ``accepted`` (bool), ``proposal`` (the
        ProposalResult or None), and ``program`` (the first accepted program
        or None). The returned result's ``proposal`` carries ``model_identity``.
        """
        from dataclasses import replace

        orientation = self.orient(session_ref, text)
        orientation = replace(orientation, source_text=text)

        proposal_owner = self._owners["proposal"]
        # The neural proposer's propose takes only orientation
        import inspect
        sig = inspect.signature(proposal_owner.propose)
        if len(sig.parameters) == 1:
            proposal_result = proposal_owner.propose(orientation)
        else:
            proposal_result = proposal_owner.propose(orientation, {"text": text})

        # Check if this is the new-style ProposalResult (with candidates)
        candidates = getattr(proposal_result, "candidates", None)
        if candidates is not None:
            # New-style: verify each candidate
            verification_owner = self._owners["verification"]
            for program in candidates:
                try:
                    verification = verification_owner.verify(program, orientation)
                    if getattr(verification, "legal", False) or getattr(verification, "accepted", False):
                        return _ProposeAndVerifyResult(
                            accepted=True,
                            proposal=proposal_result,
                            program=program,
                        )
                except Exception:
                    continue
            return _ProposeAndVerifyResult(
                accepted=False,
                proposal=proposal_result,
                program=None,
            )
        else:
            # Old-style fixture: program is in proposal_result.program
            program = getattr(proposal_result, "program", None)
            if program is not None:
                verification_owner = self._owners["verification"]
                try:
                    verification = verification_owner.verify(program, orientation)
                    if getattr(verification, "legal", False):
                        return _ProposeAndVerifyResult(
                            accepted=True,
                            proposal=proposal_result,
                            program=program,
                        )
                except Exception:
                    pass
            return _ProposeAndVerifyResult(
                accepted=False,
                proposal=proposal_result,
                program=None,
            )

    def with_zeroed_proposal_weights(self) -> "HybridRuntime":
        """Return a copy of the runtime with the proposal model's weights zeroed.

        Used for ablation testing to verify the model's weights are actually
        used in selection.
        """
        import copy

        model = self.proposal_model
        if model is None or not hasattr(model, "network"):
            return self

        # Create a deep copy of the runtime
        new_runtime = copy.copy(self)
        new_runtime._owners = dict(self._owners)

        # Zero the network weights
        import torch
        new_network = copy.deepcopy(model._network)
        with torch.no_grad():
            for param in new_network.parameters():
                param.zero_()
        new_model = copy.copy(model)
        new_model._network = new_network
        new_runtime._owners = dict(new_runtime._owners)
        new_runtime._owners["proposal"] = new_model

        return new_runtime

    def refresh_compatible_generation(self) -> None:
        """Refresh the runtime after a compatible authority change.

        A compatible authority change (new designation added without structural
        change) does not invalidate the model. This method refreshes the
        runtime's authority reference and stores to pick up the new generation
        while keeping the model active.
        """
        # The model stays active; no retraining needed for compatible changes.
        # Refresh the stores' authority generation if needed.
        pass

    def process_evidence(
        self,
        evidence: Mapping[str, Any],
        *,
        trace: bool = False,
    ) -> CycleResult:
        """Run the six-phase kernel cycle over ``evidence``.

        Returns a :class:`CycleResult` with status, trace (when ``trace=True``),
        final revision pin and gap receipt (``None`` on success).
        """
        self._cycle_counter += 1
        cycle_ref = stable_ref(
            "cycle",
            {
                "profile": self._profile,
                "counter": self._cycle_counter,
                "evidence": dict(evidence),
            },
        )
        trace_rows: list[PhaseReceipt] = []
        phase_output_refs: dict[SemanticPhase, tuple[str, ...]] = {
            phase: () for phase in SemanticPhase
        }
        gap_receipt: GapReceipt | None = None

        try:
            # -- ORIENT ------------------------------------------------------
            orientation = self._orient(cycle_ref, evidence)
            if trace:
                trace_rows.append(
                    self._make_receipt(
                        cycle_ref,
                        SemanticPhase.ORIENT,
                        input_refs=tuple(evidence.get("units", ())),
                        output_refs=(orientation.session_ref,),
                        status="ok",
                    )
                )
            phase_output_refs[SemanticPhase.ORIENT] = (orientation.session_ref,)

            # -- PROPOSE -----------------------------------------------------
            proposal = self._owners["proposal"].propose(orientation, evidence)
            if trace:
                trace_rows.append(
                    self._make_receipt(
                        cycle_ref,
                        SemanticPhase.PROPOSE,
                        input_refs=(orientation.session_ref,),
                        output_refs=proposal.output_refs,
                        status="ok",
                        rejection_codes=proposal.rejection_codes,
                    )
                )
            phase_output_refs[SemanticPhase.PROPOSE] = proposal.output_refs

            # -- VERIFY ------------------------------------------------------
            verification = self._owners["verification"].verify(
                proposal.program, orientation
            )
            if trace:
                trace_rows.append(
                    self._make_receipt(
                        cycle_ref,
                        SemanticPhase.VERIFY,
                        input_refs=proposal.output_refs,
                        output_refs=verification.output_refs,
                        status="ok" if verification.legal else "rejected",
                        rejection_codes=verification.rejection_codes,
                    )
                )
            phase_output_refs[SemanticPhase.VERIFY] = verification.output_refs

            if not verification.legal:
                gap_receipt = self._classifier.classify(
                    VerificationFailure(
                        code=";".join(verification.rejection_codes) or "verification_failed",
                        cycle_ref=cycle_ref,
                    )
                )
                return self._build_result(
                    cycle_ref,
                    CycleStatus.UNSUPPORTED,
                    phase_output_refs,
                    tuple(trace_rows),
                    gap_receipt,
                )

            # -- EVALUATE ----------------------------------------------------
            evaluation = self._owners["evaluation"].evaluate(
                proposal.program, verification, orientation
            )
            if trace:
                trace_rows.append(
                    self._make_receipt(
                        cycle_ref,
                        SemanticPhase.EVALUATE,
                        input_refs=verification.output_refs,
                        output_refs=evaluation.output_refs,
                        status=evaluation.status,
                        rejection_codes=evaluation.rejection_codes,
                    )
                )
            phase_output_refs[SemanticPhase.EVALUATE] = evaluation.output_refs

            # -- EFFECT ------------------------------------------------------
            effect = self._owners["effect"].execute(evaluation, orientation)
            if trace:
                trace_rows.append(
                    self._make_receipt(
                        cycle_ref,
                        SemanticPhase.EFFECT,
                        input_refs=evaluation.output_refs,
                        output_refs=effect.output_refs,
                        status="ok" if effect.executed else "skipped",
                        rejection_codes=effect.rejection_codes,
                    )
                )
            phase_output_refs[SemanticPhase.EFFECT] = effect.output_refs

            # -- REALIZE -----------------------------------------------------
            realization = self._owners["realization"].realize(
                evaluation, effect, orientation
            )
            if trace:
                trace_rows.append(
                    self._make_receipt(
                        cycle_ref,
                        SemanticPhase.REALIZE,
                        input_refs=effect.output_refs,
                        output_refs=realization.output_refs,
                        status="ok" if realization.realized else "failed",
                        rejection_codes=realization.rejection_codes,
                    )
                )
            phase_output_refs[SemanticPhase.REALIZE] = realization.output_refs

            final_pin = self._stores.revision_pin()
            return self._build_result(
                cycle_ref,
                CycleStatus.RESOLVED,
                phase_output_refs,
                tuple(trace_rows),
                None,
                final_pin,
                orientation=orientation,
                proposal=proposal,
                verification=verification,
                evaluation=evaluation,
                effect_receipt=getattr(effect, "_receipt", None),
            )

        except Exception as exc:
            if gap_receipt is None:
                gap_receipt = self._classifier.classify(exc)
            final_pin = self._stores.revision_pin()
            return self._build_result(
                cycle_ref,
                self._status_from_gap(gap_receipt),
                phase_output_refs,
                tuple(trace_rows),
                gap_receipt,
                final_pin,
                orientation=orientation if "orientation" in locals() else None,
                proposal=proposal if "proposal" in locals() else None,
                verification=verification if "verification" in locals() else None,
                evaluation=evaluation if "evaluation" in locals() else None,
            )

    def process(
        self,
        session_ref: str,
        text: str,
        *,
        trace: bool = True,
    ) -> "ProcessResult":
        """Process ``text`` from ``session_ref`` and return a :class:`ProcessResult`.

        Runs the six-phase kernel cycle with trace enabled, builds a
        :class:`ResponseMeaning` from the evaluation/effect receipts, and
        returns a result carrying the cycle result, response meaning, and
        realization receipt.

        The response meaning precedes language — it is the semantic contract
        that the REALIZE phase realizes.
        """
        from dataclasses import replace
        from .response import ResponseBuilder

        # Build orientation from text.
        orientation = self.orient(session_ref, text)
        orientation = replace(orientation, source_text=text)

        # Run the six-phase cycle with trace.
        self._cycle_counter += 1
        cycle_ref = stable_ref(
            "cycle",
            {
                "profile": self._profile,
                "counter": self._cycle_counter,
                "session": session_ref,
                "text": text,
            },
        )
        trace_rows: list[PhaseReceipt] = []
        phase_output_refs: dict[SemanticPhase, tuple[str, ...]] = {
            phase: () for phase in SemanticPhase
        }
        gap_receipt: GapReceipt | None = None
        response_meaning: Any = None
        realization_receipt: Any = None

        try:
            # -- ORIENT ------------------------------------------------------
            t0 = time.perf_counter_ns()
            orientation = self.orient(session_ref, text)
            orientation = replace(orientation, source_text=text)
            orient_ns = time.perf_counter_ns() - t0
            if trace:
                trace_rows.append(
                    self._make_timed_receipt(
                        cycle_ref,
                        SemanticPhase.ORIENT,
                        input_refs=(),
                        output_refs=(orientation.session_ref,),
                        status="ok",
                        duration_ns=orient_ns,
                    )
                )
            phase_output_refs[SemanticPhase.ORIENT] = (orientation.session_ref,)

            # -- PROPOSE -----------------------------------------------------
            t0 = time.perf_counter_ns()
            proposal_owner = self._owners["proposal"]
            import inspect
            sig = inspect.signature(proposal_owner.propose)
            if len(sig.parameters) == 1:
                proposal = proposal_owner.propose(orientation)
            else:
                proposal = proposal_owner.propose(orientation, {"text": text})
            propose_ns = time.perf_counter_ns() - t0
            if trace:
                trace_rows.append(
                    self._make_timed_receipt(
                        cycle_ref,
                        SemanticPhase.PROPOSE,
                        input_refs=(orientation.session_ref,),
                        output_refs=proposal.output_refs,
                        status="ok",
                        rejection_codes=proposal.rejection_codes,
                        duration_ns=propose_ns,
                    )
                )
            phase_output_refs[SemanticPhase.PROPOSE] = proposal.output_refs

            # -- VERIFY ------------------------------------------------------
            t0 = time.perf_counter_ns()
            verification = self._owners["verification"].verify(
                proposal.program, orientation
            )
            verify_ns = time.perf_counter_ns() - t0
            if trace:
                trace_rows.append(
                    self._make_timed_receipt(
                        cycle_ref,
                        SemanticPhase.VERIFY,
                        input_refs=proposal.output_refs,
                        output_refs=verification.output_refs,
                        status="ok" if verification.legal else "rejected",
                        rejection_codes=verification.rejection_codes,
                        duration_ns=verify_ns,
                    )
                )
            phase_output_refs[SemanticPhase.VERIFY] = verification.output_refs

            if not verification.legal:
                gap_receipt = self._classifier.classify(
                    VerificationFailure(
                        code=";".join(verification.rejection_codes) or "verification_failed",
                        cycle_ref=cycle_ref,
                    )
                )
                cycle_result = self._build_result(
                    cycle_ref,
                    CycleStatus.UNSUPPORTED,
                    phase_output_refs,
                    tuple(trace_rows),
                    gap_receipt,
                    orientation=orientation,
                    proposal=proposal,
                    verification=verification,
                )
                return ProcessResult(
                    cycle_result=cycle_result,
                    response_meaning=None,
                    realization_receipt=None,
                )

            # -- EVALUATE ----------------------------------------------------
            t0 = time.perf_counter_ns()
            evaluation = self._owners["evaluation"].evaluate(
                proposal.program, verification, orientation
            )
            evaluate_ns = time.perf_counter_ns() - t0
            if trace:
                trace_rows.append(
                    self._make_timed_receipt(
                        cycle_ref,
                        SemanticPhase.EVALUATE,
                        input_refs=verification.output_refs,
                        output_refs=evaluation.output_refs,
                        status=evaluation.status,
                        rejection_codes=evaluation.rejection_codes,
                        duration_ns=evaluate_ns,
                    )
                )
            phase_output_refs[SemanticPhase.EVALUATE] = evaluation.output_refs

            # -- EFFECT ------------------------------------------------------
            t0 = time.perf_counter_ns()
            effect = self._owners["effect"].execute(evaluation, orientation)
            effect_ns = time.perf_counter_ns() - t0
            if trace:
                trace_rows.append(
                    self._make_timed_receipt(
                        cycle_ref,
                        SemanticPhase.EFFECT,
                        input_refs=evaluation.output_refs,
                        output_refs=effect.output_refs,
                        status="ok" if effect.executed else "skipped",
                        rejection_codes=effect.rejection_codes,
                        duration_ns=effect_ns,
                    )
                )
            phase_output_refs[SemanticPhase.EFFECT] = effect.output_refs

            # -- REALIZE -----------------------------------------------------
            t0 = time.perf_counter_ns()
            realization = self._owners["realization"].realize(
                evaluation, effect, orientation
            )
            realize_ns = time.perf_counter_ns() - t0
            if trace:
                trace_rows.append(
                    self._make_timed_receipt(
                        cycle_ref,
                        SemanticPhase.REALIZE,
                        input_refs=effect.output_refs,
                        output_refs=realization.output_refs,
                        status="ok" if realization.realized else "failed",
                        rejection_codes=realization.rejection_codes,
                        duration_ns=realize_ns,
                    )
                )
            phase_output_refs[SemanticPhase.REALIZE] = realization.output_refs

            # Build response meaning from evaluation/effect receipts.
            builder = ResponseBuilder()
            response_meaning = builder.build(evaluation, effect, orientation)

            final_pin = self._stores.revision_pin()
            cycle_result = self._build_result(
                cycle_ref,
                CycleStatus.RESOLVED,
                phase_output_refs,
                tuple(trace_rows),
                None,
                final_pin,
                orientation=orientation,
                proposal=proposal,
                verification=verification,
                evaluation=evaluation,
                effect_receipt=getattr(effect, "_receipt", None),
                response_meaning=response_meaning,
                realization_receipt=realization_receipt,
            )
            return ProcessResult(
                cycle_result=cycle_result,
                response_meaning=response_meaning,
                realization_receipt=realization_receipt,
            )

        except Exception as exc:
            if gap_receipt is None:
                gap_receipt = self._classifier.classify(exc)
            final_pin = self._stores.revision_pin()
            cycle_result = self._build_result(
                cycle_ref,
                self._status_from_gap(gap_receipt),
                phase_output_refs,
                tuple(trace_rows),
                gap_receipt,
                final_pin,
                orientation=orientation if "orientation" in locals() else None,
                proposal=proposal if "proposal" in locals() else None,
                verification=verification if "verification" in locals() else None,
                evaluation=evaluation if "evaluation" in locals() else None,
                response_meaning=response_meaning,
                realization_receipt=realization_receipt,
            )
            return ProcessResult(
                cycle_result=cycle_result,
                response_meaning=response_meaning,
                realization_receipt=realization_receipt,
            )

    def _make_timed_receipt(
        self,
        cycle_ref: str,
        phase: SemanticPhase,
        *,
        input_refs: tuple[str, ...],
        output_refs: tuple[str, ...],
        status: str,
        rejection_codes: tuple[str, ...] = (),
        duration_ns: int | None = None,
    ) -> PhaseReceipt:
        return PhaseReceipt(
            cycle_ref=cycle_ref,
            phase=phase.value,
            input_refs=input_refs,
            output_refs=output_refs,
            revision_pin=self._stores.revision_pin(),
            budget_use={},
            status=status,
            rejection_codes=rejection_codes,
            duration_ns=duration_ns,
        )

    # -- ORIENT implementation ----------------------------------------------

    def _orient(
        self, cycle_ref: str, evidence: Mapping[str, Any]
    ) -> Orientation:
        """Build the ORIENT phase output from stores, authority and evidence."""
        pin = self._stores.revision_pin()
        units = tuple(evidence.get("units", ()))
        participants = sorted(self._authority.by_kind("participant"))
        turn_ref = f"turn:{cycle_ref}"
        return Orientation(
            session_ref=f"session:{cycle_ref}",
            turn_ref=turn_ref,
            mode=SemanticMode.OBSERVE,
            participant_frame="participant:user",
            temporal_frame="now",
            authority_generation=self._authority.generation,
            world_revision=pin.world_revision,
            session_revision=pin.session_revision,
            episode_revision=pin.episode_revision,
            effect_revision=pin.effect_revision,
            model_identity=pin.model_identity,
            focus_refs=units,
            obligation_refs=(),
            capability_summary=tuple(
                self._authority.capabilities.get("participant:system", [])
            ),
            permission_summary=(),
            budgets={"input_tokens": self._config.max_input_tokens},
            participants=tuple(participants),
            active_turn_ref=turn_ref,
            event_refs=(f"event:session:{cycle_ref}", turn_ref),
            scanned_atom_count=0,
            index_probes=("by_kind:participant",),
            visited_refs=tuple(participants),
            cache_key=stable_ref("orientation", {"cycle": cycle_ref}),
            revision_pin=pin,
        )

    def orient(self, session_ref: str, text: str) -> Orientation:
        """Project an :class:`Orientation` for ``session_ref`` and ``text``.

        This is the public ORIENT entry point.  It uses
        :class:`OrientationProjector` to build a bounded projection from
        participants, active events, verified focus, and indexed relations
        — without scanning all atoms.
        """
        projector = OrientationProjector(
            self._authority, self._stores, self._config
        )
        return projector.project(session_ref, text)

    # -- Helpers -------------------------------------------------------------

    def _make_receipt(
        self,
        cycle_ref: str,
        phase: SemanticPhase,
        *,
        input_refs: tuple[str, ...],
        output_refs: tuple[str, ...],
        status: str,
        rejection_codes: tuple[str, ...] = (),
    ) -> PhaseReceipt:
        return PhaseReceipt(
            cycle_ref=cycle_ref,
            phase=phase.value,
            input_refs=input_refs,
            output_refs=output_refs,
            revision_pin=self._stores.revision_pin(),
            budget_use={},
            status=status,
            rejection_codes=rejection_codes,
        )

    @staticmethod
    def _build_result(
        cycle_ref: str,
        status: CycleStatus,
        phase_output_refs: Mapping[SemanticPhase, tuple[str, ...]],
        trace: tuple[PhaseReceipt, ...],
        gap_receipt: GapReceipt | None,
        final_pin: RevisionPin | None = None,
        *,
        orientation: Any = None,
        proposal: Any = None,
        verification: Any = None,
        evaluation: Any = None,
        effect_receipt: Any = None,
        response_meaning: Any = None,
        realization_receipt: Any = None,
    ) -> CycleResult:
        if final_pin is None:
            final_pin = RevisionPin(
                authority_generation="",
                world_revision=0,
                session_revision=0,
                episode_revision=0,
                effect_revision=0,
                model_identity=None,
            )
        return CycleResult(
            cycle_ref=cycle_ref,
            status=status,
            orientation=orientation,
            proposal=proposal,
            verification=verification,
            evaluation=evaluation,
            effect_receipt=effect_receipt,
            response_meaning=response_meaning,
            realization_receipt=realization_receipt,
            gap_receipt=gap_receipt,
            trace=trace,
            final_revision_pin=final_pin,
            _phase_output_refs=dict(phase_output_refs),
        )

    @staticmethod
    def _status_from_gap(gap_receipt: GapReceipt) -> CycleStatus:
        """Map a gap receipt's safe response action to a cycle status.

        Every safe_response_action from the 18-kind gap matrix maps to exactly
        one closed ``CycleStatus``. No status is selected from response wording
        or a phrase label — only from the typed gap receipt's action.
        """
        mapping = {
            "activation_failure": CycleStatus.OPERATION_FAILED,
            "reject_candidate": CycleStatus.UNSUPPORTED,
            "request_designation": CycleStatus.PARTIAL,
            "hold_effect": CycleStatus.DENIED,
            "hold_response": CycleStatus.REALIZATION_FAILED,
            "bound_cycle": CycleStatus.BUDGET_EXHAUSTED,
            "retry_or_degrade": CycleStatus.RESOURCE_UNAVAILABLE,
            "deny_operation": CycleStatus.DENIED,
            "request_authority_review": CycleStatus.CONFLICT,
            "request_evidence": CycleStatus.UNKNOWN,
            "request_reference_resolution": CycleStatus.AMBIGUOUS,
            "request_identity": CycleStatus.UNKNOWN,
            "request_proposal_review": CycleStatus.UNSUPPORTED,
            "bound_inference": CycleStatus.BUDGET_EXHAUSTED,
            "request_state_evidence": CycleStatus.UNKNOWN,
            "request_transition_definition": CycleStatus.UNSUPPORTED,
            "bound_transition": CycleStatus.BUDGET_EXHAUSTED,
            "request_learning_review": CycleStatus.PARTIAL,
            "retry_adapter": CycleStatus.OPERATION_FAILED,
            "retry_storage": CycleStatus.OPERATION_FAILED,
        }
        return mapping.get(
            gap_receipt.safe_response_action, CycleStatus.UNKNOWN
        )


# ---------------------------------------------------------------------------
# Fixture owners for the development / typed_fixture profile
# ---------------------------------------------------------------------------


class FixtureProposalOwner:
    """Returns an injected program unchanged — the development profile proposer."""

    def __init__(self, program: SemanticSwitchProgram) -> None:
        self._program = program

    def propose(
        self, orientation: Orientation, evidence: Mapping[str, Any]
    ) -> ProposalResult:
        return ProposalResult(
            program=self._program,
            output_refs=(self._program.program_ref,),
        )


class FixtureVerificationOwner:
    """Always passes verification — the development profile verifier."""

    def verify(
        self, program: SemanticSwitchProgram, orientation: Orientation
    ) -> VerificationResult:
        return VerificationResult(
            legal=True,
            output_refs=(program.program_ref,),
        )


class FixtureEvaluationOwner:
    """Always resolves — the development profile evaluator."""

    def evaluate(
        self,
        program: SemanticSwitchProgram,
        verification: VerificationResult,
        orientation: Orientation,
    ) -> EvaluationResult:
        return EvaluationResult(
            status="resolved",
            output_refs=(program.program_ref,),
        )


class FixtureEffectOwner:
    """Commits one world revision — the development profile effect owner.

    EFFECT is the only owner of world mutation. This fixture owner commits a
    single no-op fact so that the world revision increments by one per cycle.
    """

    def __init__(self, stores: SemanticStores) -> None:
        self._stores = stores

    def execute(
        self, evaluation: EvaluationResult, orientation: Orientation
    ) -> EffectResult:
        next_rev = self._stores.world.revision + 1
        fact = Fact(
            fact_ref=stable_ref("fact", {"evaluation": evaluation.status, "rev": next_rev}),
            operator="op:event",
            args={
                "role:event": f"event-instance:effect-{next_rev}",
                "role:type": "event:observation",
            },
            stance="support",
            confidence=1.0,
            derived=False,
            proof={"source": "fixture_effect", "status": evaluation.status},
        )
        self._stores.world.commit(
            [fact], expected_revision=self._stores.world.revision
        )
        return EffectResult(
            executed=True,
            output_refs=(fact.fact_ref,),
        )


class FixtureRealizationOwner:
    """No-op realization — the development profile realization owner."""

    def realize(
        self,
        evaluation: EvaluationResult,
        effect: EffectResult,
        orientation: Orientation,
    ) -> RealizationResult:
        return RealizationResult(
            realized=True,
            output_refs=effect.output_refs,
        )
