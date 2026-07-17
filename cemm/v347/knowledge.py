"""Epistemic admission, retrieval, correction and foundation bootstrap."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .model import (
    CommunicativeForce,
    GraphPatch,
    KnowledgeRecord,
    MeaningBundle,
    PatchOperation,
    PatchOperationKind,
    Polarity,
    PortBinding,
    Predication,
    Referent,
    ReferentKind,
    TruthStatus,
    canonical_data,
    semantic_hash,
)
from .schema import FoundationPackage, LanguagePack, SemanticSchemaStore
from .storage import SemanticStore


@dataclass(frozen=True, slots=True)
class AnswerBinding:
    query_proposition_ref: str
    matched_knowledge_ref: str
    matched_proposition_ref: str
    variable_bindings: Mapping[str, str]
    confidence: float
    evidence_refs: tuple[str, ...]
    polarity: Polarity = Polarity.POSITIVE


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    answers: tuple[AnswerBinding, ...]
    knowledge_gap: bool
    contradicted: bool = False
    reason: str = ""


class EpistemicCoordinator:
    def __init__(self, store: SemanticStore, schemas: SemanticSchemaStore):
        self._store = store
        self._schemas = schemas

    def compile_admission_patch(
        self,
        bundle: MeaningBundle | None,
        *,
        context_ref: str,
        source_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        if bundle is None:
            return None
        operations: list[PatchOperation] = []
        admitted_props: list[str] = []
        for proposition_ref in bundle.proposition_refs:
            proposition = bundle.graph.referents.get(proposition_ref)
            if proposition is None or proposition.kind != ReferentKind.PROPOSITION:
                continue
            payload = proposition.payload or {}
            force = CommunicativeForce(str(payload.get("communicative_force", "assert")))
            if force not in {CommunicativeForce.ASSERT, CommunicativeForce.CORRECT}:
                continue
            predication_refs = tuple(map(str, payload.get("predication_refs", ())))
            if not predication_refs:
                continue
            for predication_ref in predication_refs:
                predication = bundle.graph.predications.get(predication_ref)
                if predication is None:
                    continue
                if any(binding.open_variable_ref for binding in predication.bindings):
                    continue
                for binding in predication.bindings:
                    for referent_ref in binding.referent_refs:
                        referent = bundle.graph.referents.get(referent_ref)
                        if referent is not None:
                            operations.append(_upsert_referent_op(referent))
                operations.append(_upsert_predication_op(predication))
            operations.append(_upsert_proposition_op(proposition))
            knowledge_ref = semantic_hash("knowledge", (proposition_ref, source_ref, context_ref))
            schema = self._schemas.predicate(
                bundle.graph.predications[predication_refs[0]].predicate_schema_ref
            )
            supersession_ports = schema.supersedes_same_ports
            if supersession_ports:
                predication = bundle.graph.predications[predication_refs[0]]
                fixed = {
                    binding.port_id: binding.referent_refs[0]
                    for binding in predication.bindings
                    if binding.port_id in supersession_ports and len(binding.referent_refs) == 1
                }
                for prior in self._store.latest_active_for_signature(
                    schema.schema_ref,
                    fixed,
                    context_ref=context_ref,
                    scope_refs=("global", context_ref),
                ):
                    if prior.proposition_ref == proposition_ref:
                        continue
                    operations.append(PatchOperation(
                        operation_id=semantic_hash("op:supersede", (prior.knowledge_id, knowledge_ref)),
                        kind=PatchOperationKind.SUPERSEDE_KNOWLEDGE,
                        target_ref=prior.knowledge_id,
                        payload={"superseded_by": knowledge_ref},
                        expected_revision=prior.revision,
                    ))
                    for dependent in self._store.dependents_of(prior.knowledge_id):
                        invalidation_ref = semantic_hash("invalidation", (
                            dependent["dependent_ref"], prior.knowledge_id, knowledge_ref
                        ))
                        operations.append(PatchOperation(
                            operation_id=f"op:{invalidation_ref}",
                            kind=PatchOperationKind.RECORD_INVALIDATION,
                            target_ref=invalidation_ref,
                            payload={
                                "target_ref": dependent["dependent_ref"],
                                "reason": "premise_superseded",
                                "cause_ref": prior.knowledge_id,
                                "prior_fingerprint": dependent.get("metadata", {}).get("fingerprint", ""),
                                "invalidated_at_revision": expected_store_revision,
                                "metadata": {"replacement_ref": knowledge_ref},
                            },
                        ))
            operations.append(PatchOperation(
                operation_id=f"op:{knowledge_ref}",
                kind=PatchOperationKind.UPSERT_KNOWLEDGE,
                target_ref=knowledge_ref,
                payload=canonical_data(KnowledgeRecord(
                    knowledge_id=knowledge_ref,
                    proposition_ref=proposition_ref,
                    truth_status=TruthStatus.SUPPORTED,
                    context_ref=context_ref,
                    source_refs=(source_ref,),
                    evidence_refs=bundle.graph.evidence_refs,
                    confidence=0.9,
                    scope_ref=context_ref,
                    permission_ref="conversation",
                    valid_time_ref=payload.get("valid_time_ref"),
                    root_lineage_refs=tuple(dict.fromkeys(bundle.graph.evidence_refs)),
                    valid_from=(proposition.metadata.get("valid_from") if proposition.metadata else None),
                    valid_to=(proposition.metadata.get("valid_to") if proposition.metadata else None),
                    metadata={
                        "bundle_ref": bundle.bundle_id,
                        "polarity": payload.get("polarity", "positive"),
                        "attribution_ref": payload.get("attribution_ref"),
                    },
                )),
            ))
            admitted_props.append(proposition_ref)
            operations.extend(self._alias_operations(bundle, predication_refs, source_ref))
        if not admitted_props:
            return None
        return GraphPatch(
            patch_id=semantic_hash("patch:admission", (bundle.bundle_id, source_ref, context_ref)),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref=source_ref,
            evidence_refs=bundle.graph.evidence_refs,
            operations=tuple(_dedupe_operations(operations)),
            expected_store_revision=expected_store_revision,
            permission_ref="conversation",
            validation_requirements=("complete_required_ports", "source_attribution", "referent_integrity"),
            rollback_hint="supersede newly admitted knowledge and retract aliases",
        )

    def _alias_operations(
        self,
        bundle: MeaningBundle,
        predication_refs: Iterable[str],
        source_ref: str,
    ) -> list[PatchOperation]:
        operations: list[PatchOperation] = []
        for predication_ref in predication_refs:
            predication = bundle.graph.predications[predication_ref]
            schema = self._schemas.predicate(predication.predicate_schema_ref)
            alias_port = str(schema.metadata.get("alias_value_port", ""))
            if not alias_port:
                continue
            binding = predication.binding(alias_port)
            if binding is None:
                continue
            language_tag = str(schema.metadata.get("alias_language", "und"))
            for referent_ref in binding.referent_refs:
                referent = bundle.graph.referents.get(referent_ref)
                text = _referent_text(referent)
                if not text:
                    continue
                operations.append(PatchOperation(
                    operation_id=semantic_hash("op:alias", (language_tag, text, referent_ref)),
                    kind=PatchOperationKind.ADD_ALIAS,
                    target_ref=referent_ref,
                    payload={
                        "language_tag": language_tag,
                        "surface": text,
                        "referent_ref": referent_ref,
                        "confidence": 0.9,
                        "source_ref": source_ref,
                    },
                ))
        return operations

    def compile_support_retraction(
        self,
        knowledge_ref: str,
        *,
        source_ref: str,
        context_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        """Retract one exact source contribution and invalidate dependents.

        Retraction is not deletion and does not erase unrelated evidence.  If
        the removed source was the last support, storage marks the proposition
        undetermined while preserving provenance and historical identity.
        """
        knowledge = self._store.knowledge_record(knowledge_ref)
        if knowledge is None or source_ref not in knowledge.source_refs:
            return None
        operations: list[PatchOperation] = [PatchOperation(
            operation_id=semantic_hash("op:retract_support", (knowledge_ref, source_ref)),
            kind=PatchOperationKind.RETRACT_SUPPORT,
            target_ref=knowledge_ref,
            payload={"source_ref": source_ref},
            expected_revision=knowledge.revision,
        )]
        for dependent in self._store.dependents_of(knowledge_ref):
            invalidation_ref = semantic_hash("invalidation", (
                dependent["dependent_ref"], knowledge_ref, "support_retracted", source_ref
            ))
            operations.append(PatchOperation(
                operation_id=f"op:{invalidation_ref}",
                kind=PatchOperationKind.RECORD_INVALIDATION,
                target_ref=invalidation_ref,
                payload={
                    "target_ref": dependent["dependent_ref"],
                    "reason": "premise_support_retracted",
                    "cause_ref": knowledge_ref,
                    "prior_fingerprint": dependent.get("metadata", {}).get("fingerprint", ""),
                    "invalidated_at_revision": expected_store_revision + 1,
                    "metadata": {"source_ref": source_ref},
                },
            ))
        return GraphPatch(
            patch_id=semantic_hash("patch:retract_support", (knowledge_ref, source_ref, context_ref)),
            context_ref=context_ref,
            scope_ref=knowledge.scope_ref,
            source_ref="runtime:epistemic_retraction",
            evidence_refs=knowledge.evidence_refs,
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref=knowledge.permission_ref,
            validation_requirements=("exact_source_retraction", "dependent_invalidation"),
            rollback_hint="restore source support through a new attributed admission",
        )

    def retrieve(self, bundle: MeaningBundle | None, *, context_ref: str) -> RetrievalResult:
        if bundle is None:
            return RetrievalResult(answers=(), knowledge_gap=True, reason="no_selected_meaning")
        answers: list[AnswerBinding] = []
        for query_prop_ref in bundle.proposition_refs:
            proposition = bundle.graph.referents.get(query_prop_ref)
            payload = proposition.payload or {} if proposition else {}
            force = CommunicativeForce(str(payload.get("communicative_force", "assert")))
            if force != CommunicativeForce.ASK:
                continue
            for predication_ref in payload.get("predication_refs", ()):
                query = bundle.graph.predications.get(str(predication_ref))
                if query is None:
                    continue
                answers.extend(self._retrieve_predication(query_prop_ref, query, context_ref))
        by_binding: dict[tuple[tuple[str, str], ...], set[Polarity]] = {}
        for answer in answers:
            signature = tuple(sorted((str(key), str(value)) for key, value in answer.variable_bindings.items()))
            by_binding.setdefault(signature, set()).add(answer.polarity)
        contradicted = any(
            Polarity.POSITIVE in polarities and Polarity.NEGATIVE in polarities
            for polarities in by_binding.values()
        )
        # A negative proposition constrains or opposes an answer; it must never
        # be verbalized through an affirmative value template.  It remains
        # available to truth maintenance and contradiction disclosure.
        positive_answers = [item for item in answers if item.polarity == Polarity.POSITIVE]
        ranked = sorted(positive_answers, key=lambda item: item.confidence, reverse=True)
        return RetrievalResult(
            answers=tuple(ranked),
            knowledge_gap=not ranked and not contradicted,
            contradicted=contradicted,
            reason=(
                "contradictory_admissible_knowledge" if contradicted
                else "matched_open_ports" if ranked
                else "no_admissible_knowledge_match"
            ),
        )

    def _retrieve_predication(
        self, query_prop_ref: str, query: Predication, context_ref: str
    ) -> list[AnswerBinding]:
        results = []
        scopes = ("global", context_ref)
        fixed = {
            binding.port_id: binding.referent_refs
            for binding in query.bindings if binding.referent_refs
        }
        open_bindings = {
            binding.port_id: binding.open_variable_ref
            for binding in query.bindings if binding.open_variable_ref
        }
        for knowledge, candidate, proposition in self._store.knowledge_for_predicate(
            query.predicate_schema_ref, context_ref=context_ref, scope_refs=scopes
        ):
            candidate_bindings = {
                binding.port_id: binding.referent_refs for binding in candidate.bindings
            }
            if any(candidate_bindings.get(port) != refs for port, refs in fixed.items()):
                continue
            variable_bindings = {}
            complete = True
            for port, variable_ref in open_bindings.items():
                refs = candidate_bindings.get(port, ())
                if len(refs) != 1 or not variable_ref:
                    complete = False
                    break
                variable_bindings[variable_ref] = refs[0]
            if not complete:
                continue
            polarity = Polarity(str((proposition.payload or {}).get("polarity", Polarity.POSITIVE.value)))
            results.append(AnswerBinding(
                query_proposition_ref=query_prop_ref,
                matched_knowledge_ref=knowledge.knowledge_id,
                matched_proposition_ref=knowledge.proposition_ref,
                variable_bindings=variable_bindings,
                confidence=knowledge.confidence * candidate.confidence,
                evidence_refs=knowledge.evidence_refs,
                polarity=polarity,
            ))
        return results


def build_foundation_patch(
    foundation: FoundationPackage,
    languages: Mapping[str, LanguagePack],
    *,
    expected_store_revision: int,
) -> GraphPatch:
    operations: list[PatchOperation] = []
    referent_map = {item.referent_id: item for item in foundation.referents}
    for referent in foundation.referents:
        operations.append(_upsert_referent_op(referent))
    # Surface aliases are owned exclusively by language packages.
    for language_tag, pack in languages.items():
        for entry in pack.lexical_entries:
            semantic_ref = str(entry.get("semantic_ref", ""))
            if semantic_ref not in referent_map:
                continue
            for surface in entry.get("surfaces", ()):
                operations.append(PatchOperation(
                    operation_id=semantic_hash("op:boot-alias", (language_tag, surface, semantic_ref)),
                    kind=PatchOperationKind.ADD_ALIAS,
                    target_ref=semantic_ref,
                    payload={
                        "language_tag": language_tag,
                        "surface": str(surface),
                        "referent_ref": semantic_ref,
                        "confidence": float(entry.get("confidence", 0.95)),
                        "source_ref": f"language_pack:{language_tag}:{pack.version}",
                    },
                ))
    for assertion in foundation.seed_assertions:
        predicate_ref = str(assertion["predicate_schema_ref"])
        bindings = tuple(
            PortBinding(port_id=str(port), referent_refs=(str(ref),))
            for port, ref in assertion["bindings"].items()
        )
        predication = Predication(
            predication_id=semantic_hash("predication", (predicate_ref, assertion["bindings"], "foundation")),
            predicate_schema_ref=predicate_ref,
            bindings=bindings,
            context_ref=str(assertion.get("context_ref", "actual")),
            source_evidence_refs=("foundation:seed_assertion",),
            confidence=float(assertion.get("confidence", 1.0)),
        )
        proposition = Referent(
            referent_id=semantic_hash("referent:proposition", (
                predication.predication_id,
                assertion.get("context_ref", "actual"),
                assertion.get("polarity", "positive"),
            )),
            kind=ReferentKind.PROPOSITION,
            type_refs=("kind:proposition",),
            payload={
                "predication_refs": (predication.predication_id,),
                "context_ref": str(assertion.get("context_ref", "actual")),
                "polarity": str(assertion.get("polarity", "positive")),
                "modality_refs": (),
                "attribution_ref": str(assertion.get("source_ref", "foundation")),
                "valid_time_ref": assertion.get("valid_time_ref"),
                "communicative_force": "assert",
            },
            scope_ref=str(assertion.get("scope_ref", "global")),
            context_ref=str(assertion.get("context_ref", "actual")),
            metadata={"foundation": True},
        )
        knowledge_ref = semantic_hash("knowledge", (proposition.referent_id, "foundation"))
        operations.extend((
            _upsert_predication_op(predication),
            _upsert_proposition_op(proposition),
            PatchOperation(
                operation_id=f"op:{knowledge_ref}",
                kind=PatchOperationKind.UPSERT_KNOWLEDGE,
                target_ref=knowledge_ref,
                payload=canonical_data(KnowledgeRecord(
                    knowledge_id=knowledge_ref,
                    proposition_ref=proposition.referent_id,
                    truth_status=TruthStatus.SUPPORTED,
                    context_ref=str(assertion.get("context_ref", "actual")),
                    source_refs=(str(assertion.get("source_ref", "foundation")),),
                    evidence_refs=("foundation:seed_assertion",),
                    confidence=float(assertion.get("confidence", 1.0)),
                    scope_ref=str(assertion.get("scope_ref", "global")),
                    permission_ref="public",
                    metadata={"foundation": True},
                )),
            ),
        ))
    language_fingerprint = semantic_hash(
        "language_boot",
        {
            tag: {
                "version": pack.version,
                "lexical_entries": pack.lexical_entries,
            }
            for tag, pack in sorted(languages.items())
        },
        32,
    )
    return GraphPatch(
        patch_id=semantic_hash("patch:foundation", (foundation.fingerprint, language_fingerprint), 32),
        context_ref="boot",
        scope_ref="global",
        source_ref=foundation.package_ref,
        evidence_refs=(foundation.fingerprint, language_fingerprint),
        operations=tuple(_dedupe_operations(operations)),
        expected_store_revision=expected_store_revision,
        permission_ref="system_boot",
        validation_requirements=("foundation_schema_integrity", "language_surface_separation"),
        rollback_hint="restore pre-bootstrap database",
        metadata={
            "version": foundation.version,
            "fingerprint": foundation.fingerprint,
            "language_fingerprint": language_fingerprint,
        },
    )


def _upsert_referent_op(referent: Referent) -> PatchOperation:
    return PatchOperation(
        operation_id=f"op:{referent.referent_id}",
        kind=PatchOperationKind.UPSERT_REFERENT,
        target_ref=referent.referent_id,
        payload=canonical_data(referent),
    )


def _upsert_predication_op(predication: Predication) -> PatchOperation:
    return PatchOperation(
        operation_id=f"op:{predication.predication_id}",
        kind=PatchOperationKind.UPSERT_PREDICATION,
        target_ref=predication.predication_id,
        payload=canonical_data(predication),
    )


def _upsert_proposition_op(proposition: Referent) -> PatchOperation:
    return PatchOperation(
        operation_id=f"op:{proposition.referent_id}",
        kind=PatchOperationKind.UPSERT_PROPOSITION,
        target_ref=proposition.referent_id,
        payload=canonical_data(proposition),
    )


def _referent_text(referent: Referent | None) -> str:
    if referent is None:
        return ""
    payload = referent.payload or {}
    if isinstance(payload, Mapping):
        for key in ("text", "name", "label"):
            value = payload.get(key)
            if value:
                return str(value)
    return ""


def _dedupe_operations(items: Iterable[PatchOperation]) -> list[PatchOperation]:
    # Operation identity, not target identity, is the deduplication boundary.
    # Multiple aliases intentionally share a referent target, and collapsing by
    # target silently destroys multilingual bootstrap data.
    result: dict[str, PatchOperation] = {}
    for item in items:
        result[item.operation_id] = item
    return list(result.values())
