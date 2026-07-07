"""Internal action authorization types for CEMM Phase 8.

Internal actions are semantic runtime proposals, not user-facing wording and
not side effects. They are carried to the runtime authority layer for optional
execution by the host system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cemm.response.types import InternalActionProposal


@dataclass(frozen=True)
class ActionPolicy:
    action_type: str
    authority_scope: str
    min_confidence: float = 0.5
    require_source_refs: bool = False
    require_reversible: bool = False
    require_explicit_authority: bool = False
    allowed_without_runtime_executor: bool = True


@dataclass
class ActionAuthorizationDecision:
    proposal: InternalActionProposal
    authorized: bool = False
    reason: str = ""
    policy_scope: str = ""


@dataclass
class ActionAuthorizationResult:
    proposed_actions: list[InternalActionProposal] = field(default_factory=list)
    authorized_actions: list[InternalActionProposal] = field(default_factory=list)
    rejected_actions: list[InternalActionProposal] = field(default_factory=list)
    decisions: list[ActionAuthorizationDecision] = field(default_factory=list)

    def diagnostics(self) -> dict[str, Any]:
        return {
            "proposed_count": len(self.proposed_actions),
            "authorized_count": len(self.authorized_actions),
            "rejected_count": len(self.rejected_actions),
            "decisions": [
                {
                    "action_type": decision.proposal.action_type,
                    "authorized": decision.authorized,
                    "reason": decision.reason,
                    "policy_scope": decision.policy_scope,
                    "confidence": decision.proposal.confidence,
                    "reversible": decision.proposal.reversible,
                }
                for decision in self.decisions
            ],
        }
