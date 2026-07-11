"""Tests for 3.3 Transactional Runtime and Use Outcomes (Phase 11)."""

from __future__ import annotations

import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.types.execution_ledger import (
    ExecutionLedger, ExecutionLedgerEntry, LedgerEntryStatus,
)
from cemm.types.obligation_graph import ObligationGraph, ObligationNode, ObligationNodeKind


class TestExecutionLedger:
    def test_create_entry(self):
        entry = ExecutionLedgerEntry(
            operation_id="op1",
            operation_type="query",
            node_id="n1",
            status=LedgerEntryStatus.PROPOSED.value,
        )
        assert entry.operation_id == "op1"
        assert entry.status == "proposed"

    def test_transition_status(self):
        entry = ExecutionLedgerEntry(
            operation_id="op1",
            operation_type="query",
            node_id="n1",
        )
        entry.transition("authorized")
        assert entry.status == "authorized"
        entry.transition("executing")
        assert entry.status == "executing"
        entry.transition("succeeded")
        assert entry.status == "succeeded"

    def test_add_entry_to_ledger(self):
        ledger = ExecutionLedger(turn_id="turn1", session_id="session1")
        entry = ExecutionLedgerEntry(
            operation_id="op1", operation_type="query", node_id="n1",
        )
        ledger.add_entry(entry)
        assert len(ledger.entries) == 1
        assert ledger.entry_by_id("op1") is entry

    def test_entry_by_type_filter(self):
        ledger = ExecutionLedger()
        ledger.add_entry(ExecutionLedgerEntry(
            operation_id="q1", operation_type="query", node_id="n1",
        ))
        ledger.add_entry(ExecutionLedgerEntry(
            operation_id="w1", operation_type="write", node_id="n2",
        ))
        queries = ledger.entries_by_type("query")
        assert len(queries) == 1
        assert queries[0].operation_id == "q1"

    def test_succeeded_and_failed(self):
        ledger = ExecutionLedger()
        ledger.add_entry(ExecutionLedgerEntry(
            operation_id="q1", operation_type="query", node_id="n1",
            status=LedgerEntryStatus.SUCCEEDED.value,
        ))
        ledger.add_entry(ExecutionLedgerEntry(
            operation_id="w1", operation_type="write", node_id="n2",
            status=LedgerEntryStatus.FAILED.value,
        ))
        assert len(ledger.succeeded()) == 1
        assert len(ledger.failed()) == 1
        assert ledger.has_failures

    def test_consistent_when_no_failures(self):
        ledger = ExecutionLedger()
        ledger.add_entry(ExecutionLedgerEntry(
            operation_id="q1", operation_type="query", node_id="n1",
            status=LedgerEntryStatus.SUCCEEDED.value,
        ))
        assert ledger.is_consistent
        assert not ledger.has_failures

    def test_mark_inconsistent(self):
        ledger = ExecutionLedger()
        ledger.mark_inconsistent()
        assert not ledger.is_consistent

    def test_failure_makes_inconsistent(self):
        ledger = ExecutionLedger()
        ledger.add_entry(ExecutionLedgerEntry(
            operation_id="w1", operation_type="write", node_id="n1",
            status=LedgerEntryStatus.FAILED.value,
        ))
        assert ledger.has_failures


class TestTurnExecutionPlanner:
    def test_plan_from_empty_graph(self):
        from cemm.kernel.turn_execution_planner import TurnExecutionPlanner
        planner = TurnExecutionPlanner()
        graph = ObligationGraph()
        steps = planner.plan(graph, None)
        assert steps == []

    def test_plan_execution_order(self):
        from cemm.kernel.turn_execution_planner import TurnExecutionPlanner
        planner = TurnExecutionPlanner()
        graph = ObligationGraph()
        graph.add_node(ObligationNode(
            node_id="write1", kind=ObligationNodeKind.WRITE,
        ))
        graph.add_node(ObligationNode(
            node_id="query1", kind=ObligationNodeKind.QUERY,
            depends_on=("write1",),
        ))
        steps = planner.plan(graph, None)
        assert len(steps) == 2
        assert steps[0].node_id == "write1"
        assert steps[1].node_id == "query1"

    def test_plan_learning_question(self):
        from cemm.kernel.turn_execution_planner import TurnExecutionPlanner
        planner = TurnExecutionPlanner()
        graph = ObligationGraph()
        graph.add_node(ObligationNode(
            node_id="lq1", kind=ObligationNodeKind.LEARNING_QUESTION,
            is_required=False, budget_cost=0.5,
        ))
        graph.add_node(ObligationNode(
            node_id="q1", kind=ObligationNodeKind.QUERY,
            depends_on=("lq1",),
        ))
        steps = planner.plan(graph, None)
        assert len(steps) == 2
        assert steps[0].kind == ObligationNodeKind.LEARNING_QUESTION
        assert steps[1].kind == ObligationNodeKind.QUERY

    def test_plan_skips_blocked(self):
        from cemm.kernel.turn_execution_planner import TurnExecutionPlanner
        planner = TurnExecutionPlanner()
        graph = ObligationGraph()
        graph.add_node(ObligationNode(
            node_id="write1", kind=ObligationNodeKind.WRITE,
            blocked_by=("safety1",),
        ))
        order = graph.execution_order()
        assert "write1" not in order


class TestLearningUseObserver:
    def test_observe_binding_selection(self):
        from cemm.learning.learning_use_observer import LearningUseObserver
        observer = LearningUseObserver()
        outcomes = observer.observe_binding_selected(
            hypothesis_id="hyp1",
            surface_form="zibble",
            resolved_target="entity:unknown",
            confidence=0.7,
        )
        assert len(outcomes) == 1
        assert outcomes[0].outcome_kind.value == "binding_selected"

    def test_observe_query_success(self):
        from cemm.learning.learning_use_observer import LearningUseObserver
        observer = LearningUseObserver()
        outcomes = observer.observe_use_success(
            hypothesis_id="hyp1",
            use_type="query",
            confidence=0.8,
        )
        assert len(outcomes) >= 1

    def test_observe_repair(self):
        from cemm.learning.learning_use_observer import LearningUseObserver
        observer = LearningUseObserver()
        outcomes = observer.observe_repair(
            hypothesis_id="hyp1",
            repair_type="correction",
        )
        assert len(outcomes) >= 1


class TestContractExecutor:
    def test_execute_empty_plan(self):
        from cemm.kernel.contract_executor import ContractExecutor
        executor = ContractExecutor()
        ledger = executor.execute([], None)
        assert ledger is not None
        assert len(ledger.entries) == 0

    def test_execute_records_entry(self):
        from cemm.kernel.contract_executor import ContractExecutor
        from cemm.kernel.turn_execution_planner import ExecutionPlanStep
        executor = ContractExecutor()
        step = ExecutionPlanStep(
            node_id="q1",
            kind=ObligationNodeKind.QUERY,
            is_required=True,
        )
        ledger = executor.execute([step], None)
        assert len(ledger.entries) == 1
        entry = ledger.entries[0]
        assert entry.node_id == "q1"
        assert entry.operation_type == "query"
        assert entry.status == LedgerEntryStatus.SUCCEEDED.value

    def test_execute_with_error(self):
        from cemm.kernel.contract_executor import ContractExecutor
        from cemm.kernel.turn_execution_planner import ExecutionPlanStep

        def failing_executor(step, contracts):
            raise RuntimeError("execution failed")

        executor = ContractExecutor(step_executor=failing_executor)
        step = ExecutionPlanStep(
            node_id="w1",
            kind=ObligationNodeKind.WRITE,
            is_required=True,
        )
        ledger = executor.execute([step], None)
        entry = ledger.entries[0]
        assert entry.status == LedgerEntryStatus.FAILED.value
        assert "execution failed" in entry.error
        assert ledger.has_failures
        assert not ledger.is_consistent
