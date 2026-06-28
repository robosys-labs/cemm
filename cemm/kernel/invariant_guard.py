from __future__ import annotations
from ..types.claim import Claim, ClaimStatus
from ..types.model import Model
from ..types.action import Action
from ..types.signal import Signal, SignalKind
from ..types.context_kernel import ContextKernel
from ..types.trace import Trace


class InvariantGuard:
    errors: list[str] = []

    @classmethod
    def reset(cls) -> None:
        cls.errors = []

    @classmethod
    def check_claim_has_evidence(cls, claim: Claim) -> bool:
        if not claim.evidence_signal_ids:
            cls.errors.append(f"Claim {claim.id} has no evidence signals")
            return False
        return True

    @classmethod
    def check_model_has_evidence(cls, model: Model) -> bool:
        if not model.evidence_signal_ids:
            cls.errors.append(f"Model {model.id} has no evidence signals")
            return False
        return True

    @classmethod
    def check_action_has_trace(cls, action: Action) -> bool:
        if action.status.value == "executed" and action.trace is None:
            cls.errors.append(f"Action {action.id} executed without trace")
            return False
        return True

    @classmethod
    def check_private_claim_used_with_permission(cls, claim: Claim, kernel: ContextKernel) -> bool:
        from ..types.permission import PermissionScope
        if claim.permission and claim.permission.scope == PermissionScope.USER_PRIVATE:
            if not kernel.user.known:
                cls.errors.append(f"Private claim {claim.id} used without permission")
                return False
        return True

    @classmethod
    def check_disputed_not_presented_certain(cls, claim: Claim) -> bool:
        if claim.status == ClaimStatus.DISPUTED and claim.confidence > 0.5:
            cls.errors.append(f"Disputed claim {claim.id} has confidence > 0.5")
            return False
        return True

    @classmethod
    def check_prediction_not_fact(cls, signal: Signal) -> bool:
        if signal.kind == SignalKind.SIMULATION_RESULT and signal.salience > 0.9:
            cls.errors.append(f"Simulation signal {signal.id} has excessive salience")
            return False
        return True

    @classmethod
    def check_recursive_budget(cls, kernel: ContextKernel, depth: int) -> bool:
        if depth > kernel.budget.max_recursive_steps:
            cls.errors.append(f"Recursive depth {depth} exceeds budget {kernel.budget.max_recursive_steps}")
            return False
        return True

    @classmethod
    def check_uol_not_bypassing_registry(cls, atoms: list, registry) -> bool:
        for atom in atoms:
            if hasattr(atom, 'state_key') and atom.state_key:
                model = registry.get_uol_semantic(atom.state_key)
                if model is None and atom.confidence > 0.3:
                    cls.errors.append(f"UOL state key '{atom.state_key}' not in registry")
                    return False
            if hasattr(atom, 'frame_key') and atom.frame_key:
                model = registry.get_uol_semantic(atom.frame_key)
                if model is None and atom.confidence > 0.3:
                    cls.errors.append(f"UOL process key '{atom.frame_key}' not in registry")
                    return False
        return True

    @classmethod
    def assert_no_errors(cls) -> list[str]:
        return list(cls.errors)

    @classmethod
    def check_memory_mutation_has_trace(cls, action: Action) -> bool:
        if action.kind.value in ("remember", "update_claim", "create_model_candidate"):
            if action.trace is None:
                cls.errors.append(f"Memory mutation action {action.id} has no trace")
                return False
        return True

    @classmethod
    def check_model_promoted_with_validation(cls, model: Model) -> bool:
        if model.status.value == "active" and model.confidence < 0.6:
            cls.errors.append(f"Model {model.id} promoted with confidence {model.confidence} < 0.6")
            return False
        return True

    @classmethod
    def check_stale_claim_not_used(cls, claim: Claim, kernel: ContextKernel) -> bool:
        if claim.valid_until is not None and kernel.time.now > claim.valid_until:
            if claim.status.value == "active":
                cls.errors.append(f"Stale claim {claim.id} is still active past valid_until")
                return False
        return True

    @classmethod
    def check_synthesis_verification(cls, action: Action, trace: Trace) -> bool:
        if action.kind.value == "answer":
            if not trace.synthesis_verified:
                cls.errors.append(f"Answer action {action.id} bypassed synthesis verification")
                return False
        return True
