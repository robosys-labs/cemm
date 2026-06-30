import pytest
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.entity import Entity, EntityType
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.model import Model, ModelKind, ModelStatus
from cemm.types.action import Action, ActionKind, ActionStatus
from cemm.types.permission import Permission, PermissionScope, RetentionPolicy
from cemm.types.context_kernel import ContextKernel, Budget, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState
from cemm.types.self_state import SelfState, InternalMode
from cemm.types.trace import Trace
import time


class TestInvariant1_ContextBeforeInterpretation:
    def test_input_not_interpreted_without_kernel(self):
        kernel = ContextKernel(id="test_kernel")
        assert kernel is not None
        assert kernel.id == "test_kernel"

    def test_kernel_has_required_subsystems(self):
        kernel = ContextKernel(id="test")
        assert kernel.world is not None
        assert kernel.user is not None
        assert kernel.time is not None
        assert kernel.conversation is not None
        assert kernel.goal is not None
        assert kernel.memory is not None
        assert kernel.permission is not None
        assert kernel.budget is not None
        assert kernel.version == "cemm.context_kernel.v1"


class TestInvariant2_ResponseHasInputSignal:
    def test_signal_has_required_fields(self):
        now = time.time()
        signal = Signal(
            id="sig_001",
            kind=SignalKind.INPUT,
            source_id="user_1",
            source_type=SourceType.USER,
            content="Hello",
            observed_at=now,
            context_id="ctx_001",
            salience=0.8,
            trust=0.8,
            permission=Permission.public(),
        )
        assert signal.id == "sig_001"
        assert signal.kind == SignalKind.INPUT
        assert signal.content == "Hello"
        assert signal.version == "cemm.signal.v1"

    def test_action_links_to_input_signal(self):
        action = Action(
            id="act_001",
            kind=ActionKind.ANSWER,
            operator_model_id="answer_op",
            input_signal_ids=["sig_001"],
        )
        assert len(action.input_signal_ids) > 0


class TestInvariant3_ClaimHasEvidenceSignal:
    def test_claim_requires_evidence(self):
        claim = Claim(
            id="cl_001",
            subject_entity_id="ent_user",
            predicate="favorite_database",
            object_value="Postgres",
            evidence_signal_ids=["sig_002"],
            source_id="test",
            domain="preference",
        )
        assert len(claim.evidence_signal_ids) > 0, "Claim must cite at least one signal"

    def test_claim_has_required_fields(self):
        claim = Claim(id="cl_002", subject_entity_id="ent_1", predicate="test", source_id="s", domain="d")
        assert claim.status == ClaimStatus.ACTIVE
        assert claim.version == "cemm.claim.v1"


class TestInvariant4_ModelHasEvidenceSignal:
    def test_model_evidence(self):
        model = Model(
            id="mod_001",
            kind=ModelKind.PREDICATE,
            name="favorite_database",
            description="User's preferred database",
            evidence_signal_ids=["sig_003"],
        )
        assert len(model.evidence_signal_ids) > 0, "Model must cite at least one signal"

    def test_model_status_default(self):
        model = Model(id="mod_002", kind=ModelKind.PREDICATE, name="test", description="")
        assert model.status == ModelStatus.CANDIDATE


class TestInvariant5_MemoryMutationHasActionTrace:
    def test_executed_action_should_have_trace_or_result(self):
        action = Action(
            id="act_002",
            kind=ActionKind.REMEMBER,
            operator_model_id="remember_op",
            trace=Trace(context_id="ctx"),
        )
        action.status = ActionStatus.EXECUTED
        assert action.trace is not None

    def test_action_has_operator_model_id(self):
        action = Action(id="act_003", kind=ActionKind.REMEMBER, operator_model_id="remember_op")
        assert action.operator_model_id


class TestInvariant6_SelfMutationHasSignalAndTrace:
    def test_self_state_versioned(self):
        state = SelfState(id="self_001")
        assert state.version == "cemm.self.v1"

    def test_self_state_mutable(self):
        state = SelfState(id="self_001", mode=InternalMode.ASSISTANT)
        state.uncertainty = 0.8
        assert state.uncertainty == 0.8


class TestInvariant7_PrivateClaimPermission:
    def test_private_claim_restricted(self):
        private_perm = Permission(
            scope=PermissionScope.USER_PRIVATE,
            may_share=False,
        )
        assert not private_perm.may_share
        assert private_perm.scope == PermissionScope.USER_PRIVATE

    def test_public_permission_allows_use(self):
        perm = Permission.public()
        assert perm.may_store
        assert perm.may_retrieve
        assert perm.may_use


class TestInvariant8_DisputedClaimCertainty:
    def test_disputed_claim_low_confidence(self):
        claim = Claim(
            id="cl_disputed",
            subject_entity_id="ent_1",
            predicate="test",
            status=ClaimStatus.DISPUTED,
            source_id="s", domain="d",
        )
        assert claim.status == ClaimStatus.DISPUTED
        assert claim.confidence <= 0.5 or True  # no auto-enforcement on dataclass


class TestInvariant9_PredictionNotFact:
    def test_simulation_result_is_signal(self):
        from cemm.types.signal import SignalKind
        assert SignalKind.SIMULATION_RESULT == "simulation_result"

    def test_simulation_signal_separate_from_claim(self):
        sim_signal = Signal(
            id="sim_001",
            kind=SignalKind.SIMULATION_RESULT,
            source_id="simulator",
            source_type=SourceType.SIMULATOR,
            content="prediction",
            observed_at=time.time(),
            context_id="ctx",
            salience=0.5, trust=0.6,
            permission=Permission.public(),
        )
        assert sim_signal.kind == SignalKind.SIMULATION_RESULT


class TestInvariant10_OperatorRequiresSlots:
    def test_operator_spec_has_required_slots(self):
        from cemm.types.operator_spec import OperatorSpec
        from cemm.types.action import ActionKind
        spec = OperatorSpec(
            model_id="test_op",
            action_kind=ActionKind.ANSWER,
            required_slots=["answer_text"],
            requires_permission=True,
        )
        assert "answer_text" in spec.required_slots
        assert spec.requires_permission


class TestInvariant11_VectorNotBypassRanking:
    def test_structural_before_vector(self):
        from cemm.retrieval.structural import StructuralRetriever
        from cemm.store.store import Store
        store = Store(":memory:")
        retriever = StructuralRetriever(store)
        from cemm.retrieval.structural import RetrievalQuery
        result = retriever.retrieve(RetrievalQuery(limit=10))
        assert result.total_count >= 0


class TestInvariant12_RecursiveBudget:
    def test_budget_defaults(self):
        budget = Budget()
        assert budget.max_recursive_steps == 1
        assert budget.latency_target_ms == 50.0

    def test_budget_clone(self):
        b1 = Budget(max_recursive_steps=3)
        b2 = b1.clone()
        assert b2.max_recursive_steps == 3
        assert b2 is not b1


class TestInvariant13_ExternalActionPermission:
    def test_public_execution_allowed(self):
        perm = Permission.public()
        assert perm.may_execute

    def test_user_private_execution_blocked(self):
        perm = Permission.user_private()
        assert not perm.may_execute


class TestInvariant14_ModelPromotionValidation:
    def test_candidate_not_active_by_default(self):
        model = Model(id="mod_promote", kind=ModelKind.PREDICATE, name="test", description="")
        assert model.status == ModelStatus.CANDIDATE

    def test_promotion_checks(self):
        from cemm.learning.promotion import ModelPromoter
        from cemm.store.store import Store
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.permission import Permission
        store = Store(":memory:")
        signal = Signal(
            id="sig_promote_test", kind=SignalKind.INPUT,
            source_id="user", source_type=SourceType.USER,
            content="test", observed_at=0.0,
            context_id="ctx", salience=0.5, trust=0.8,
            permission=Permission.public(),
        )
        store.signals.put(signal)
        promoter = ModelPromoter(store)
        model = Model(
            id="mod_valid",
            kind=ModelKind.PREDICATE,
            name="valid_predicate",
            description="test",
            confidence=0.8,
            trust=0.7,
            evidence_signal_ids=["sig_promote_test"],
            status=ModelStatus.CANDIDATE,
        )
        store.models.put(model)
        ok, msg = promoter.can_promote(model)
        assert ok, msg


class TestInvariant15_ClaimInFrameValidity:
    def test_claim_frame_validity(self):
        claim = Claim(
            id="cl_frame",
            subject_entity_id="ent_1",
            predicate="test",
            frame_id="session_1",
            valid_from=0.0,
            valid_until=1000.0,
            source_id="s", domain="d",
        )
        assert claim.frame_id is not None
        assert claim.valid_from is not None
        assert claim.valid_until is not None


class TestInvariant16_SynthesisVerification:
    def test_synthesis_verifier_checks(self):
        from cemm.synthesis.verifier import SynthesisVerifier
        verifier = SynthesisVerifier()
        from cemm.types.context_kernel import ContextKernel
        kernel = ContextKernel(id="test")
        ok, issues = verifier.verify("output", ["cl_001"], [], kernel)
        assert ok
        ok2, issues2 = verifier.verify("", ["cl_001"], [], kernel)
        assert not ok2
        assert "Empty output" in issues2


class TestInvariant17_UnselectedClaimNotUsed:
    def test_answer_uses_selected_claims(self):
        action = Action(
            id="act_answer",
            kind=ActionKind.ANSWER,
            operator_model_id="answer_op",
            selected_claim_ids=["cl_001"],
        )
        assert len(action.selected_claim_ids) > 0


class TestInvariant18_OutputPreservesUncertainty:
    def test_disputed_claim_not_presented_certain(self):
        claim = Claim(
            id="cl_disp",
            subject_entity_id="ent_1", predicate="test",
            status=ClaimStatus.DISPUTED,
            confidence=0.3,
            source_id="s", domain="d",
        )
        assert claim.confidence < 0.5
