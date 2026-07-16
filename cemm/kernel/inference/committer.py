"""Validated critical commit for proof-carrying derived semantic facts."""
from __future__ import annotations

from uuid import uuid4

from ..memory.semantic import FactRole, SemanticFact
from ..model.identity import (
    Permission,
    PermissionScope,
    RetentionPolicy,
    SemanticIdentity,
)
from ..model.mutation import MutationOperation, MutationSet


class InferenceFactCommitter:
    """Convert an inference outcome into a normal guarded mutation set."""

    def __init__(self, payload_registry, commit_coordinator) -> None:
        self._payloads = payload_registry
        self._commit = commit_coordinator

    def commit(self, outcome, *, context_id: str = "default"):
        operations = []
        for derived in tuple(getattr(outcome, "derived_facts", ()) or ()):
            fact = SemanticFact(
                fact_id=str(derived.fact_id),
                predicate_key=str(derived.predicate_key),
                roles=tuple(
                    FactRole(
                        role_key=str(role_key),
                        value_ref=str(value_ref),
                        value_kind=self._value_kind(str(value_ref)),
                        semantic_key=(
                            str(value_ref)
                            if self._is_semantic_constant(str(value_ref))
                            else ""
                        ),
                    )
                    for role_key, value_ref in sorted(derived.roles.items())
                ),
                context_ref=str(derived.context_ref or "actual"),
                polarity=str(derived.polarity),
                confidence=float(derived.confidence),
                evidence_refs=tuple(dict.fromkeys((
                    *tuple(derived.evidence_refs or ()),
                    str(derived.derivation_ref),
                ))),
                source_ref="kernel:bounded_inference",
                valid_from=str(derived.valid_time_ref or ""),
                derivation_rule_ref=str(derived.derivation_ref),
                derivation_depth=int(derived.derivation_depth),
                causal_warrant=str(
                    getattr(derived.causal_warrant, "value", derived.causal_warrant)
                ),
                sensitivity=str(derived.sensitivity),
            )
            payload_ref = f"payload:{fact.fact_id}"
            self._payloads.put(payload_ref, fact)
            operations.append(MutationOperation(
                id=f"mutation:{fact.fact_id}",
                operation_kind="semantic_fact",
                semantic_identity=SemanticIdentity(
                    identity_kind="semantic_fact",
                    key=fact.semantic_identity,
                ),
                action="create",
                payload_ref=payload_ref,
                required=True,
                evidence_refs=fact.evidence_refs,
                permission=Permission(
                    scope=PermissionScope.SESSION_PRIVATE,
                    may_store=True,
                    may_retrieve=True,
                    may_use=True,
                    may_share=False,
                    may_execute=False,
                    retention=RetentionPolicy.SESSION,
                ),
                reason=(
                    "bounded proof-carrying inference in context "
                    f"{context_id}"
                ),
            ))

        if not operations:
            return None
        return self._commit.commit(MutationSet(
            id=f"mutation_set:inference:{uuid4().hex[:12]}",
            phase="critical",
            operations=tuple(operations),
        ))

    @staticmethod
    def _is_semantic_constant(value_ref: str) -> bool:
        return not value_ref.startswith((
            "value:", "entity:mention:", "opaque:", "ref:",
        ))

    @staticmethod
    def _value_kind(value_ref: str) -> str:
        if value_ref.startswith("value:"):
            return "value"
        if value_ref.startswith("entity:mention:"):
            return "entity_anchor"
        return "referent"
