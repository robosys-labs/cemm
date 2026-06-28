from __future__ import annotations
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.action import ActionKind
from ..retrieval.structural import StructuralRetriever, RetrievalQuery
from ..retrieval.ranker import Ranker


class RetrieveOperator(BaseOperator):
    @property
    def action_kind(self) -> ActionKind:
        return ActionKind.RETRIEVE

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        if not ctx.kernel.permission.may_execute:
            return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
        if not ctx.kernel.permission.may_retrieve:
            return OperatorResult(success=False, output_text="Permission denied: retrieval not allowed")
        query = RetrievalQuery(
            subject_entity_id=ctx.params.get("subject_entity_id"),
            predicate=ctx.params.get("predicate"),
            object_entity_id=ctx.params.get("object_entity_id"),
            domain=ctx.params.get("domain"),
            source_id=ctx.params.get("source_id"),
            limit=ctx.params.get("limit", 64),
        )
        retriever = StructuralRetriever(ctx.store)
        result = retriever.retrieve(query, ctx.kernel)
        ranker = Ranker()
        ranked = ranker.rank_claims(result.claims, ctx.kernel)
        output_lines = [f"Retrieved {len(ranked)} results"]
        for claim, score in ranked[:5]:
            output_lines.append(
                f"  {claim.subject_entity_id} {claim.predicate} "
                f"{claim.object_value or claim.object_entity_id or ''} "
                f"(score: {score:.3f})"
            )
        return OperatorResult(
            success=True,
            output_text="\n".join(output_lines),
        )
