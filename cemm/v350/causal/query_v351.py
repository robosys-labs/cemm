"""Exact Stage-10 causal-query projection over ordinary grounded Query artifacts."""
from __future__ import annotations

from dataclasses import dataclass

from ..csir.model import ExactAuthorityPin
from ..orchestration import StageOutcome
from ..query.engine_v351 import GroundedQueryEngineV351
from .model_v351 import CausalQueryRequestV351
from .authority_v351 import require_exact_use


@dataclass(frozen=True, slots=True)
class CausalQueryProjectionContractV351:
    """Reviewed mapping from an exact answer-projection meaning to a causal query kind."""

    contract_pin: ExactAuthorityPin
    projection_pin: ExactAuthorityPin
    query_kind: str

    def __post_init__(self) -> None:
        if self.query_kind not in {"why", "why_not", "what_if", "cause_of", "effect_of"}:
            raise ValueError("unsupported causal query kind")


class Phase16QueryEngineV351(GroundedQueryEngineV351):
    """Preserve ordinary query binding while emitting exact causal-query work.

    No English word or question template is inspected. A query becomes causal only when its
    exact `AnswerProjection.projection_pin` is covered by a reviewed contract and the query
    carries an already-grounded causal target variable identity.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "query_engine"

    def __init__(self, session_memory, *, causal_query_contracts=(), maximum_beliefs_per_query=512):
        super().__init__(session_memory, maximum_beliefs_per_query=maximum_beliefs_per_query)
        self.causal_query_contracts = tuple(causal_query_contracts)
        keys = tuple(item.projection_pin.key for item in self.causal_query_contracts)
        if len(keys) != len(set(keys)):
            raise ValueError("causal query projection contracts must be singular per exact projection")

    def query(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        ordinary = super().query(
            cycle=cycle,
            capability=capability,
            store=store,
            effect_store=effect_store,
            semantic_capabilities=semantic_capabilities,
        )
        semantic_authority = cycle.artifacts.get("semantic_authority_snapshot_v351")
        by_projection = {}
        frontiers = list(ordinary.frontier_refs)
        for contract in self.causal_query_contracts:
            try:
                semantic_authority.require_known_pin(contract.projection_pin)
                require_exact_use(
                    semantic_authority, contract.contract_pin, operation="query",
                    context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                )
            except Exception:
                frontiers.append(
                    "frontier:causal-query:projection-authority-not-in-generation:"
                    + contract.projection_pin.ref
                )
                continue
            by_projection[contract.projection_pin.key] = contract

        requests = []
        for query in tuple(cycle.artifacts.get("queries", ()) or ()):
            projection = query.answer_projection
            pin = getattr(projection, "projection_pin", None)
            if pin is None:
                continue
            contract = by_projection.get(pin.key)
            if contract is None:
                continue
            target_ref = str(getattr(projection, "causal_target_variable_ref", "") or "")
            if not target_ref:
                frontiers.append(
                    "frontier:causal-query:grounded-target-variable-required:" + query.query_ref
                )
                continue
            intervention_ref = str(getattr(projection, "causal_intervention_context_ref", "") or "")
            intervention = None
            if intervention_ref:
                direct = tuple(cycle.artifacts.get("intervention_contexts", ()) or ())
                counterfactual = tuple(cycle.artifacts.get("counterfactual_contexts", ()) or ())
                matches = [item for item in direct if getattr(item, "context_ref", "") == intervention_ref]
                matches.extend(
                    item.intervention for item in counterfactual
                    if getattr(item, "context_ref", "") == intervention_ref
                )
                if len(matches) != 1:
                    frontiers.append(
                        "frontier:causal-query:exact-intervention-context-required:" + query.query_ref
                    )
                    continue
                intervention = matches[0]
            source_ref = str(getattr(projection, "causal_source_variable_ref", "") or "")
            contrast_ref = str(getattr(projection, "causal_contrast_value_ref", "") or "")
            if contract.query_kind in {"what_if", "why_not"} and intervention is None:
                frontiers.append(
                    "frontier:causal-query:intervention-required:" + query.query_ref
                )
                continue
            if contract.query_kind == "effect_of" and not source_ref:
                frontiers.append(
                    "frontier:causal-query:source-variable-required:" + query.query_ref
                )
                continue
            if contract.query_kind == "why_not" and not contrast_ref:
                frontiers.append(
                    "frontier:causal-query:contrast-value-required:" + query.query_ref
                )
                continue
            requests.append(CausalQueryRequestV351(
                query_ref=query.query_ref,
                target_variable_ref=target_ref,
                query_kind=contract.query_kind,
                source_variable_ref=source_ref,
                contrast_value_key=contrast_ref,
                intervention=intervention,
            ))

        artifacts = dict(ordinary.artifacts)
        artifacts["causal_query_requests"] = tuple(requests)
        artifacts["causal_query_projection_contract_refs"] = tuple(
            item.contract_pin.ref for item in self.causal_query_contracts
        )
        return StageOutcome(
            ordinary.status,
            artifacts=artifacts,
            frontier_refs=tuple(sorted(set(frontiers))),
            errors=ordinary.errors,
            reentry_request=ordinary.reentry_request,
            terminal=ordinary.terminal,
        )


__all__ = ["CausalQueryProjectionContractV351", "Phase16QueryEngineV351"]
