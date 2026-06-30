from __future__ import annotations
from ..types.claim import Claim, ClaimStatus
from ..types.context_kernel import ContextKernel
from ..types.signal import SignalKind


class SynthesisVerifier:
    def verify(
        self,
        output: str,
        selected_claim_ids: list[str],
        selected_model_ids: list[str],
        kernel: ContextKernel,
        claims: list[Claim] | None = None,
        intent: str = "",
    ) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if not output.strip():
            issues.append("Empty output")
            return False, issues

        if intent in ("abstain", "ask"):
            if selected_claim_ids:
                issues.append("Abstain/Ask output selects claims as evidence")
                return False, issues
            return True, []
        if not selected_claim_ids and not selected_model_ids:
            issues.append("No evidence selected for synthesis")
            return False, issues

        if claims:
            for c in claims:
                if c.status == ClaimStatus.DISPUTED:
                    issues.append(f"Output uses disputed claim {c.id}")
                if c.status == ClaimStatus.RETRACTED:
                    issues.append(f"Output uses retracted claim {c.id}")

        return len(issues) == 0, issues
