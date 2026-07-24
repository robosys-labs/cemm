"""Reviewed activation-bound semantic services for canonical CEMM v3.5.

These services are intentionally conservative:
- conversation-context claims may be admitted only into that conversation context;
- actual-world admission remains explicitly authorized/fail-closed;
- generic inference is proof-bearing and data-driven from active DefaultRule records;
- inference previews never invent unproved semantic assertions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .epistemic_runtime import EpistemicAdmissionProposal
from .epistemics.model import (
    AdmissionPolicy,
    AdmissionRequest,
    AdmissionThresholds,
    SourceAssessment,
)
from .learning.model import PinnedRecord
from .schema.model import semantic_fingerprint
from .storage import KnowledgeStatus, RecordKind


class ContextLocalEpistemicPolicyProvider:
    """Admit attributed claims only to their bounded conversation context by default.

    This provider never treats grammar as actual-world truth authority.  Claims in
    ``actual`` remain authorization-gated.  In a non-actual conversation context,
    direct attributed input may become context-local supported knowledge with exact
    claim/evidence lineage, allowing conversational learning without globalizing it.
    """

    provider_ref = "epistemic-policy-provider:context-local-v350"
    provider_revision = "1"
    policy_ref = "epistemic-policy:context-local-attributed:v1"

    def proposals(
        self,
        *,
        attributed_claims: tuple[object, ...],
        context_ref: str,
        permission_ref: str,
        store,
    ) -> tuple[EpistemicAdmissionProposal, ...]:
        result: list[EpistemicAdmissionProposal] = []
        actual_world = context_ref == "actual"
        thresholds = AdmissionThresholds(
            minimum_authority=0.50,
            minimum_reliability=0.50,
            minimum_access_quality=0.50,
            maximum_bias_risk=0.75,
            minimum_evidence_confidence=0.50,
            minimum_independent_sources=1,
        )
        policy = AdmissionPolicy(
            policy_ref=self.policy_ref,
            default_thresholds=thresholds,
            require_explicit_authorization=actual_world,
            permission_ref=permission_ref,
        )
        for compiled in attributed_claims:
            claim = compiled.claim_record
            occurrence = compiled.claim_occurrence
            evidence_refs = tuple(sorted(set(compiled.evidence_refs)))
            if not evidence_refs:
                continue

            evidence_confidences = []
            for evidence_ref in evidence_refs:
                stored = store.get_record(RecordKind.EVIDENCE, evidence_ref)
                confidence = (
                    float(getattr(stored.payload, "confidence", 1.0))
                    if stored is not None
                    else 1.0
                )
                evidence_confidences.append((evidence_ref, confidence))

            source = SourceAssessment(
                source_ref=claim.source_ref,
                authority=0.60,
                reliability=0.60,
                access_quality=1.0,
                bias_risk=0.50,
                evidence_refs=evidence_refs,
                metadata={
                    "scope": "attributed_conversation_source",
                    "actual_world_authority": False,
                },
            )
            proof_refs = tuple(
                sorted(
                    {
                        occurrence.claim_ref,
                        claim.claim_record_ref,
                        compiled.history_record.history_ref,
                    }
                )
            )
            request = AdmissionRequest(
                request_ref="admission-request:"
                + semantic_fingerprint(
                    "context-local-admission-request",
                    (
                        claim.claim_record_ref,
                        claim.proposition_ref,
                        occurrence.source_context_ref,
                        context_ref,
                        evidence_refs,
                    ),
                    24,
                ),
                proposition_ref=claim.proposition_ref,
                source_context_ref=occurrence.source_context_ref,
                target_context_ref=context_ref,
                requested_truth_status=KnowledgeStatus.SUPPORTED,
                source_refs=(claim.source_ref,),
                evidence_confidences=tuple(evidence_confidences),
                proof_refs=proof_refs,
                source_assessments=(source,),
                policy_ref=self.policy_ref,
                authorization_ref=None,
                permission_ref=permission_ref,
                sensitivity="normal",
                metadata={
                    "context_local_only": not actual_world,
                    "actual_world_admission": False,
                    "attribution_preserved": True,
                },
            )
            result.append(EpistemicAdmissionProposal(request=request, policy=policy))
        return tuple(result)


@dataclass(frozen=True, slots=True)
class RuntimeInferencePreview:
    preview_ref: str
    proof_refs: tuple[str, ...]
    rule_pins: tuple[PinnedRecord, ...]
    conclusions: tuple[tuple[str, str, str], ...] = ()
    frontier_refs: tuple[str, ...] = ()


class ReviewedDefaultInferenceEngine:
    """Generic proof-bearing inference over reviewed DefaultRule authority.

    The engine derives only default *previews*.  It does not mutate the semantic
    store and does not upgrade an undetermined default into factual truth.
    """

    engine_ref = "inference-engine:reviewed-defaults-v350"
    engine_revision = "1"

    def preview(
        self,
        *,
        graph,
        context_ref: str,
        permission_ref: str,
        snapshot,
        budget: Any,
    ) -> RuntimeInferencePreview:
        del budget
        records = tuple(
            item
            for item in self._records(snapshot=snapshot)
            if getattr(getattr(item.payload, "lifecycle_status", None), "value", None)
            == "active"
            and (item.permission_ref in {None, "public", permission_ref})
        )
        if not records:
            raise ValueError("generic inference requires at least one active reviewed default rule")

        pins = tuple(
            PinnedRecord(
                item.record_kind,
                item.record_ref,
                item.revision,
                item.record_fingerprint,
            )
            for item in records
        )
        conclusions: list[tuple[str, str, str]] = []
        proof_refs: list[str] = []
        propositions = tuple(sorted((getattr(graph, "propositions", {}) or {}).keys()))
        referents = dict(getattr(graph, "referents", {}) or {})
        explicit_state = {
            (str(item.payload.holder_ref), str(item.payload.dimension_ref))
            for item in self._store.records(RecordKind.STATE_ASSIGNMENT, snapshot=snapshot)
            if str(getattr(item.payload, "context_ref", "")) == context_ref
            and getattr(getattr(item.payload, "status", None), "value", None) == "active"
        }

        for item, pin in zip(records, pins):
            rule = item.payload
            holder_types = set(map(str, getattr(rule, "holder_type_refs", ())))

            # Proposition defaults apply to explicit proposition nodes.
            holder_refs: set[str] = set()
            if "type:proposition" in holder_types:
                holder_refs.update(propositions)

            # ``type:referent`` is the universal structural holder for UOL referents.
            # More specific defaults require an explicit compatible type on the UOL
            # referent; the inference engine never guesses a hidden type.
            for referent_ref, referent in referents.items():
                declared_types = set(map(str, getattr(referent, "type_refs", ())))
                if "type:referent" in holder_types or holder_types.intersection(declared_types):
                    holder_refs.add(str(referent_ref))

            for holder_ref in sorted(holder_refs):
                if not rule.expected_dimension_ref or not rule.expected_value_ref:
                    continue
                if (holder_ref, str(rule.expected_dimension_ref)) in explicit_state:
                    continue
                conclusion = (
                    holder_ref,
                    str(rule.expected_dimension_ref),
                    str(rule.expected_value_ref),
                )
                conclusions.append(conclusion)
                proof_refs.append(
                    "inference-proof:"
                    + semantic_fingerprint(
                        "reviewed-default-inference",
                        (pin.key, conclusion, context_ref),
                        24,
                    )
                )

        if not proof_refs:
            # A negative applicability proof is still proof-bearing inference: the
            # reviewed rule set was evaluated and produced no semantic assertion.
            proof_refs.append(
                "inference-proof:"
                + semantic_fingerprint(
                    "reviewed-default-no-applicable-conclusion",
                    (
                        tuple(pin.key for pin in pins),
                        tuple(getattr(graph, "root_refs", ()) or ()),
                        context_ref,
                    ),
                    24,
                )
            )
        return RuntimeInferencePreview(
            preview_ref="inference-preview:"
            + semantic_fingerprint(
                "reviewed-default-preview",
                (
                    tuple(pin.key for pin in pins),
                    tuple(sorted(proof_refs)),
                    tuple(conclusions),
                    context_ref,
                ),
                24,
            ),
            proof_refs=tuple(sorted(set(proof_refs))),
            rule_pins=pins,
            conclusions=tuple(sorted(set(conclusions))),
            frontier_refs=(),
        )

    def _records(self, *, snapshot):
        # ``SemanticStore.records`` is the canonical snapshot-aware generic read.
        # It avoids a language/domain-specific repository branch.
        return self._store.records(RecordKind.DEFAULT_RULE, snapshot=snapshot)

    def __init__(self, store) -> None:
        self._store = store
