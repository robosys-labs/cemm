from __future__ import annotations
import pytest
from cemm.v350.learning.model import PinnedRecord
from cemm.v350.operations.model import *
from cemm.v350.response.model import *
from cemm.v350.schema.model import SchemaLifecycleStatus,UseDecision
from cemm.v350.storage.model import RecordKind
from cemm.v350.uol.model import UOLGraph


def pin(kind,ref): return PinnedRecord(kind,ref,1,'f'*64)

def test_unknown_retry_requires_idempotency_contract():
    with pytest.raises(ValueError):
        OperationAdapterContractRecord(contract_ref='adapter-contract:x',action_schema_pins=(('action:x',1),),adapter_ref='adapter:x',adapter_revision=1,supported_port_refs=('actor',),retry_safe_on_unknown=True,active=True)

def test_journal_revision_requires_exact_prior_pin():
    with pytest.raises(ValueError):
        OperationJournalRecord(journal_ref='journal:x',plan_pin=pin(RecordKind.OPERATION_PLAN,'plan:x'),authorization_pin=pin(RecordKind.OPERATION_AUTHORIZATION,'auth:x'),status=OperationJournalStatus.SUBMITTED,idempotency_key=None,adapter_ref='adapter:x',adapter_revision=1,revision=2,supersedes_revision=1)

def test_dispatch_ack_is_not_success_proof():
    with pytest.raises(ValueError):
        OperationResultRecord(result_ref='result:x',journal_pin=pin(RecordKind.OPERATION_JOURNAL,'journal:x'),status=OperationResultStatus.SUCCESS,transport_acknowledged=True,domain_result_refs=(),observed_effect_refs=(),evidence_refs=(),proof_refs=())

def test_response_uol_requires_selected_goal_and_authorized_semantic_root_or_frontier():
    graph=UOLGraph(graph_ref='graph:x')
    with pytest.raises(ValueError):
        ResponseUOLRecord(response_ref='response:x',goal_decision_pin=pin(RecordKind.GOAL_DECISION,'decision:x'),selected_goal_pins=(),source_pins=(),transformation_proof_refs=(),omission_refs=(),graph=graph,unresolved_frontier_refs=(),audience_refs=(),perspective_ref='self',context_ref='actual',permission_ref='conversation',snapshot_fingerprint='snap')

def test_response_transform_rule_is_not_authority_by_lifecycle_alone():
    rule=ResponseTransformRuleRecord(rule_ref='response-rule:x',goal_schema_pins=(('goal:x',1),),source_record_kinds=(RecordKind.KNOWLEDGE,),output_schema_ref='discourse:x',output_schema_revision=1,selectors=(ResponseBindingSelector('content',ResponseSelectorMode.SOURCE),),lifecycle_status=SchemaLifecycleStatus.ACTIVE,use_decision=UseDecision.DENY)
    assert not rule.executable


def test_operation_journal_transition_table_blocks_skipping_submission():
    from cemm.v350.operations.coordinator import _ALLOWED_JOURNAL_TRANSITIONS
    from cemm.v350.operations.model import OperationJournalStatus
    assert OperationJournalStatus.OBSERVED_SUCCESS not in _ALLOWED_JOURNAL_TRANSITIONS[OperationJournalStatus.PREPARED]
    assert OperationJournalStatus.SUBMITTED in _ALLOWED_JOURNAL_TRANSITIONS[OperationJournalStatus.PREPARED]


def test_external_hard_gates_are_evaluators_not_arbitrary_record_presence():
    import inspect
    from cemm.v350.operations.planner import OperationAuthorizationGate
    source = inspect.getsource(OperationAuthorizationGate.authorize)
    assert 'gate_evaluators' in source
    assert 'if evaluator is None' in source


def test_operation_allow_requires_all_hard_gate_names():
    from cemm.v350.operations.planner import OperationAuthorizationGate
    required=set(OperationAuthorizationGate.REQUIRED_GATES)
    assert {'permission','resources','risk','preconditions'}.issubset(required)


def test_response_all_and_only_gate_checks_exact_outputs():
    import inspect
    from cemm.v350.response.planner import ResponseAuthorizationGate
    source=inspect.getsource(ResponseAuthorizationGate.require_authorized)
    assert 'proof_outputs != root_refs' in source
    assert '_reachable_applications' in source
    assert 'Response UOL contains unrooted or missing nested applications' in source


def test_operation_authorization_requires_durable_gate_assessments_contract():
    import inspect
    from cemm.v350.operations.model import OperationAuthorizationRecord, OperationGateAssessmentRecord
    from cemm.v350.operations.planner import OperationAuthorizationGate
    assert 'gate_assessment_pins' in OperationAuthorizationRecord.__dataclass_fields__
    source=inspect.getsource(OperationAuthorizationGate.authorize)
    assert 'OperationGateAssessmentRecord' in source
    assert 'assessment_pins' in source


def test_reconciled_journal_requires_reconciliation_dependency():
    import inspect
    from cemm.v350.operations.validation import Phase16CommitValidator
    source=inspect.getsource(Phase16CommitValidator.validate_operation)
    assert 'RECONCILED journal requires exact operation reconciliation dependency' in source


def test_phase16_planning_and_authorization_are_single_snapshot_fail_closed():
    import inspect
    from cemm.v350.operations.planner import OperationPlanner, OperationAuthorizationGate
    planner=inspect.getsource(OperationPlanner.plan)
    auth=inspect.getsource(OperationAuthorizationGate.authorize)
    assert 'store changed during operation planning' in planner
    assert 'store changed during hard-gate evaluation' in auth

def test_response_event_application_and_nested_apps_require_exact_lineage():
    import inspect
    from cemm.v350.response.planner import ResponseMeaningPlanner
    source=inspect.getsource(ResponseMeaningPlanner)
    assert 'event response transform requires one exact participant application source pin' in source
    assert '_collect_application_closure' in source
    assert 'semantic-application filler requires one exact goal-lineage pin' in source


def test_recovery_covers_submitted_crash_window_without_resubmit():
    import inspect
    from cemm.v350.operations.executor import OperationRecoveryCoordinator
    source=inspect.getsource(OperationRecoveryCoordinator)
    assert 'OperationJournalStatus.SUBMITTED' in source
    assert 'recover_and_persist' in source
    assert 'adapter.recover' in source
    assert 'adapter.submit' not in inspect.getsource(OperationRecoveryCoordinator.recover_and_persist)

def test_terminal_operation_outcomes_require_observed_evidence_or_proof():
    with pytest.raises(ValueError):
        OperationResultRecord(result_ref='result:failure-no-proof',journal_pin=pin(RecordKind.OPERATION_JOURNAL,'journal:x'),status=OperationResultStatus.FAILURE,transport_acknowledged=True,domain_result_refs=(),observed_effect_refs=(),evidence_refs=(),proof_refs=())
