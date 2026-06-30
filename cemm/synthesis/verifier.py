from __future__ import annotations
from ..types.claim import Claim
from ..types.context_kernel import ContextKernel
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..kernel.realization_verifier import verify as _realization_verify


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
        # Build a minimal SAG from the legacy verifier inputs so all verification
        # flows through the single, authoritative RealizationVerifier.
        sag = SemanticAnswerGraph(
            id="synthesis_verifier_sag",
            intent=intent or "answer",
            source_signal_ids=[],
            context_id=kernel.id if kernel else "",
            selected_claim_ids=list(selected_claim_ids),
            selected_model_ids=list(selected_model_ids),
            confidence=(1.0 - kernel.self_view.uncertainty) if kernel and kernel.self_view else 0.5,
            permission_scope=kernel.permission.scope.value if kernel else "public",
        )
        result = _realization_verify(
            sag=sag,
            output_text=output,
            claims=claims,
            registry=None,
        )
        return result.verified, result.details
