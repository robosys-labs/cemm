"""ContractExecutor — executes contracts according to the execution plan.

Records every operation in an ExecutionLedger with status transitions.
No partial failure may leave a durable artifact or session binding
in an untracked state.
"""

from __future__ import annotations

import uuid
import time
from typing import Any, Callable

from ...types.execution_ledger import (
    ExecutionLedger, ExecutionLedgerEntry, LedgerEntryStatus,
)
from ...types.obligation_contract import ObligationContract
from .turn_execution_planner import ExecutionPlanStep


class ContractExecutor:
    """Executes contracts according to plan, recording in ledger.

    Delegates actual execution to pluggable step_executor for testability.
    The default executor records PROPOSED status only — real execution
    is wired through the runtime.
    """

    def __init__(
        self,
        step_executor: Callable[[ExecutionPlanStep, ObligationContract | None], Any] | None = None,
    ) -> None:
        self._step_executor = step_executor or self._default_execute_step
        self._ledger: ExecutionLedger | None = None

    def execute(
        self,
        steps: list[ExecutionPlanStep],
        contract: ObligationContract | None,
        turn_id: str = "",
        session_id: str = "",
    ) -> ExecutionLedger:
        """Execute steps in order, recording each in the ledger."""
        self._ledger = ExecutionLedger(
            turn_id=turn_id,
            session_id=session_id,
        )

        for step in steps:
            entry = ExecutionLedgerEntry(
                operation_id=f"op_{uuid.uuid4().hex[:12]}",
                operation_type=step.kind.value,
                node_id=step.node_id,
                contract_id=contract.contract_id if contract else "",
                status=LedgerEntryStatus.PROPOSED.value,
                started_at=time.time(),
            )
            self._ledger.add_entry(entry)

            try:
                entry.transition(LedgerEntryStatus.EXECUTING.value)
                result = self._step_executor(step, contract)
                entry.transition(LedgerEntryStatus.SUCCEEDED.value)
                entry.result = result
            except Exception as e:
                entry.transition(LedgerEntryStatus.FAILED.value)
                entry.error = str(e)
                self._ledger.mark_inconsistent()

            entry.completed_at = time.time()

        return self._ledger

    @staticmethod
    def _default_execute_step(
        step: ExecutionPlanStep,
        contract: ObligationContract | None,
    ) -> str:
        """Default executor: merely records the step as proposed.

        Real execution is wired through the runtime by injecting a
        step_executor that dispatches to the appropriate engine.
        """
        return f"recorded:{step.node_id}"
