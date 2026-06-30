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
    def check_recursive_budget(cls, kernel: ContextKernel | None, depth: int) -> bool:
        if kernel is None:
            cls.errors.append("Recursive budget check failed: kernel is None")
            return False
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
    def check_context_not_override_explicit(cls, inferred_claim: Claim, explicit_claim: Claim) -> bool:
        if (inferred_claim.subject_entity_id == explicit_claim.subject_entity_id
                and inferred_claim.predicate == explicit_claim.predicate
                and inferred_claim.object_value != explicit_claim.object_value):
            cls.errors.append(f"Context inference {inferred_claim.id} overrides explicit claim {explicit_claim.id}")
            return False
        return True

    @classmethod
    def check_synthesis_verification(cls, action: Action, trace: Trace) -> bool:
        if action.kind.value == "answer":
            if not trace.synthesis_verified:
                cls.errors.append(f"Answer action {action.id} bypassed synthesis verification")
                return False
        return True

    @classmethod
    def check_context_kernel_before_interpretation(cls, kernel: object) -> bool:
        if kernel is None:
            cls.errors.append("Input interpreted before ContextKernel exists")
            return False
        return True

    @classmethod
    def check_response_has_input_signal(cls, signal: object | None) -> bool:
        if signal is None:
            cls.errors.append("Response has no input signal")
            return False
        return True

    @classmethod
    def check_self_mutation_has_trace(cls, action: Action) -> bool:
        if action.kind.value in ("reflect",):
            if action.trace is None:
                cls.errors.append(f"Self mutation action {action.id} has no trace")
                return False
        return True

    @classmethod
    def check_prediction_not_presented_as_fact(cls, claim: Claim) -> bool:
        confidence_type = getattr(claim, 'confidence_type', None)
        if confidence_type == "simulated" and claim.confidence > 0.99:
            cls.errors.append(f"Prediction {claim.id} exceeds confidence cap 0.99")
            return False
        return True

    @classmethod
    def check_causal_chain_confidence(cls, predictions: list[dict]) -> bool:
        for p in predictions:
            if p.get("confidence", 0) > 0.99:
                cls.errors.append(f"Causal chain confidence {p['confidence']} exceeds cap 0.99")
                return False
        return True

    @classmethod
    def check_self_mode_change_has_trace(cls, old_mode: str, new_mode: str, action: Action | None) -> bool:
        if old_mode != new_mode:
            if action is None or action.kind.value != "reflect":
                cls.errors.append(f"Self mode changed {old_mode}->{new_mode} without reflect action")
                return False
        return True

    @classmethod
    def check_insults_are_not_factual_claims(cls, claim: Claim, self_id: str) -> bool:
        insult_predicates = ("is_dumb", "is_stupid", "is_useless", "is_idiot")
        if claim.subject_entity_id == self_id and claim.predicate in insult_predicates:
            cls.errors.append(f"Insult stored as factual claim {claim.id}")
            return False
        return True

    @classmethod
    def check_temporary_frustration_not_persisted(cls, claim: Claim) -> bool:
        if claim.predicate in ("is_frustrated", "is_hostile"):
            if claim.permission and getattr(claim.permission, 'retention', None) is not None:
                retention = claim.permission.retention.value if hasattr(claim.permission.retention, 'value') else str(claim.permission.retention)
                if retention in ("long_term",):
                    cls.errors.append(f"Temporary frustration persisted as stable identity in claim {claim.id}")
                    return False
        return True
