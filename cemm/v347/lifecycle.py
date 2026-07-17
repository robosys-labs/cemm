"""Schema lifecycle, use-profile projection, promotion and invalidation.

The lifecycle layer is deliberately separate from language analysis and from the
semantic schema registry.  A surface match can identify a schema candidate, but
only a :class:`SchemaUseProfile` can authorize a specific semantic operation for
an exact schema revision in a pinned environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .model import (
    CompetenceResult,
    DependencyRecord,
    GraphPatch,
    InvalidationRecord,
    OperationalPort,
    PatchOperation,
    PatchOperationKind,
    PredicateSchema,
    SchemaRevisionRecord,
    SchemaStatus,
    SchemaUseDecision,
    SchemaUseOperation,
    SchemaUseProfile,
    semantic_hash,
)
from .schema import SemanticSchemaStore
from .storage import SemanticStore


@dataclass(frozen=True, slots=True)
class LifecycleEnvironment:
    store_revision: int
    foundation_fingerprint: str
    analyzer_fingerprint: str = ""
    grounding_policy_version: str = "v347.2"
    inference_version: str = "v347.2"
    context_policy_version: str = "v347.2"

    @property
    def fingerprint(self) -> str:
        """Stable semantic-contract fingerprint.

        The global store revision and a cycle's observation-lattice fingerprint
        pin an assessment snapshot, but neither is itself a schema dependency.
        Including them here would invalidate every learned schema after any
        unrelated commit or every new utterance.  Durable usability therefore
        follows the versions of the foundation and semantic policies only.
        """
        return semantic_hash("environment_contract", (
            self.foundation_fingerprint,
            self.grounding_policy_version,
            self.inference_version,
            self.context_policy_version,
        ), 64)

    @property
    def snapshot_fingerprint(self) -> str:
        """Exact assessment snapshot used for traceability and CAS."""
        return semantic_hash("environment_snapshot", (
            self.fingerprint,
            self.store_revision,
            self.analyzer_fingerprint,
        ), 64)


class SchemaLifecycleCoordinator:
    """Derive operation-specific schema usability without mutating schemas."""

    def __init__(self, schemas: SemanticSchemaStore, store: SemanticStore):
        self._schemas = schemas
        self._store = store
        self._cache: dict[tuple[str, int, str, str, str], SchemaUseProfile] = {}

    def profile(
        self,
        schema_ref: str,
        *,
        context_ref: str,
        operation: SchemaUseOperation = SchemaUseOperation.COMPOSE,
        environment: LifecycleEnvironment | None = None,
    ) -> SchemaUseProfile:
        schema = self._schemas.predicate(schema_ref)
        environment = environment or LifecycleEnvironment(
            store_revision=self._store.revision,
            foundation_fingerprint=self._schemas.fingerprint,
        )
        key = (schema.schema_ref, schema.revision, context_ref, operation.value, environment.fingerprint)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        structural_reasons = self._structural_reasons(schema)
        durable = self._store.latest_schema_revision(schema.schema_ref, context_ref=context_ref)
        status = schema.status
        evidence_refs: tuple[str, ...] = ()
        competence_passed = status == SchemaStatus.ACTIVE
        epistemically_admissible = status == SchemaStatus.ACTIVE
        scope_ref = schema.scope_ref
        dependency_fingerprint = environment.fingerprint
        reasons = list(structural_reasons)
        if durable is not None:
            status = SchemaStatus(str(durable.get("status", status.value)))
            evidence_refs = tuple(durable.get("evidence_refs", ()))
            competence_passed = bool(durable.get("competence_passed", False))
            epistemically_admissible = bool(durable.get("epistemically_admissible", False))
            scope_ref = str(durable.get("scope_ref", scope_ref))
            dependency_fingerprint = str(
                durable.get("environment_fingerprint") or environment.fingerprint
            )
            if dependency_fingerprint != environment.fingerprint:
                reasons.append("environment_fingerprint_stale")

        decisions = self._decisions(
            status=status,
            structurally_complete=not structural_reasons,
            competence_passed=competence_passed,
            epistemically_admissible=epistemically_admissible,
            stale="environment_fingerprint_stale" in reasons,
        )
        profile = SchemaUseProfile(
            profile_id=semantic_hash("schema_use_profile", key),
            schema_ref=schema.schema_ref,
            schema_revision=schema.revision,
            context_ref=context_ref,
            scope_ref=scope_ref,
            operation_decisions=decisions,
            structural_complete=not structural_reasons,
            epistemically_admissible=epistemically_admissible,
            competence_passed=competence_passed,
            dependency_fingerprint=dependency_fingerprint,
            evidence_refs=evidence_refs,
            reasons=tuple(reasons),
        )
        self._cache[key] = profile
        return profile

    def project_ports(
        self,
        schema_ref: str,
        *,
        context_ref: str,
        operation: SchemaUseOperation = SchemaUseOperation.COMPOSE,
        environment: LifecycleEnvironment | None = None,
    ) -> tuple[OperationalPort, ...]:
        schema = self._schemas.predicate(schema_ref)
        profile = self.profile(
            schema_ref,
            context_ref=context_ref,
            operation=operation,
            environment=environment,
        )
        decision = profile.operation_decisions.get(operation.value, SchemaUseDecision.DENY)
        return tuple(
            OperationalPort(
                operational_port_id=semantic_hash("operational_port", (
                    schema.schema_ref, schema.revision, port.port_id,
                    context_ref, operation.value, profile.dependency_fingerprint,
                )),
                predicate_schema_ref=schema.schema_ref,
                predicate_revision=schema.revision,
                port_schema=port,
                context_ref=context_ref,
                use_operation=operation,
                decision=decision,
                accepted_type_closure=port.accepted_type_refs,
                evidence_refs=profile.evidence_refs,
                assessment_fingerprint=profile.dependency_fingerprint,
                reasons=profile.reasons,
            )
            for port in schema.ports
        )

    def invalidate_cache(self, refs: Iterable[str] = ()) -> None:
        refs = set(refs)
        if not refs:
            self._cache.clear()
            return
        self._cache = {
            key: value for key, value in self._cache.items()
            if value.schema_ref not in refs
        }

    @staticmethod
    def _structural_reasons(schema: PredicateSchema) -> tuple[str, ...]:
        reasons: list[str] = []
        ids = [port.port_id for port in schema.ports]
        if not ids:
            reasons.append("no_local_ports")
        if len(ids) != len(set(ids)):
            reasons.append("duplicate_local_port")
        for port in schema.ports:
            if not port.accepted_kinds and not port.accepted_type_refs:
                reasons.append(f"untyped_port:{port.port_id}")
            if port.required and port.multiple and port.query_open:
                reasons.append(f"ambiguous_required_multi_query_port:{port.port_id}")
        return tuple(reasons)

    @staticmethod
    def _decisions(
        *,
        status: SchemaStatus,
        structurally_complete: bool,
        competence_passed: bool,
        epistemically_admissible: bool,
        stale: bool,
    ) -> Mapping[str, SchemaUseDecision]:
        operations = tuple(SchemaUseOperation)
        if not structurally_complete or status in {SchemaStatus.REJECTED, SchemaStatus.SUPERSEDED}:
            return {item.value: SchemaUseDecision.DENY for item in operations}
        if stale:
            return {
                item.value: (
                    SchemaUseDecision.PRESERVE_ONLY
                    if item in {SchemaUseOperation.RECOGNIZE, SchemaUseOperation.REALIZE}
                    else SchemaUseDecision.DENY
                )
                for item in operations
            }
        if status == SchemaStatus.CANDIDATE:
            return {
                item.value: (
                    SchemaUseDecision.PRESERVE_ONLY
                    if item == SchemaUseOperation.RECOGNIZE
                    else SchemaUseDecision.DENY
                )
                for item in operations
            }
        if status == SchemaStatus.PROVISIONAL:
            return {
                item.value: (
                    SchemaUseDecision.PROVISIONAL
                    if item in {
                        SchemaUseOperation.RECOGNIZE,
                        SchemaUseOperation.COMPOSE,
                        SchemaUseOperation.QUERY,
                        SchemaUseOperation.REALIZE,
                    }
                    else SchemaUseDecision.DENY
                )
                for item in operations
            }
        result = {item.value: SchemaUseDecision.ALLOW for item in operations}
        if not competence_passed:
            for item in (
                SchemaUseOperation.INFER,
                SchemaUseOperation.LEARN,
                SchemaUseOperation.PLAN,
                SchemaUseOperation.EXECUTE,
            ):
                result[item.value] = SchemaUseDecision.DENY
        if not epistemically_admissible:
            for item in (SchemaUseOperation.INFER, SchemaUseOperation.PLAN, SchemaUseOperation.EXECUTE):
                result[item.value] = SchemaUseDecision.DENY
        return result


class CandidatePromotionCoordinator:
    """Compile atomic promotion patches after grounding and competence checks."""

    def __init__(self, store: SemanticStore, schemas: SemanticSchemaStore):
        self._store = store
        self._schemas = schemas

    def compile_schema_promotion(
        self,
        candidate_ref: str,
        *,
        context_ref: str,
        competence_results: Iterable[CompetenceResult],
        expected_store_revision: int,
        target_status: SchemaStatus = SchemaStatus.PROVISIONAL,
    ) -> GraphPatch | None:
        candidate = self._store.schema_candidate(candidate_ref)
        if candidate is None:
            return None
        payload = dict(candidate.get("payload", {}))
        definition = dict(payload.get("definition", {}))
        grounding_refs = tuple(payload.get("grounding_refs", ()))
        frontier_refs = tuple(payload.get("frontier_refs", ()))
        results = tuple(competence_results)
        required = tuple(item for item in results if item.case_ref)
        independent = {
            item.environment_fingerprint for item in required if item.passed and item.environment_fingerprint
        }
        if not grounding_refs or frontier_refs:
            return None
        if target_status == SchemaStatus.ACTIVE and (not required or not all(item.passed for item in required)):
            return None
        if target_status == SchemaStatus.ACTIVE and len(independent) < 1:
            return None
        schema_ref = str(definition.get("schema_ref") or payload.get("target_ref") or candidate_ref)
        current = self._store.latest_schema_revision(schema_ref, context_ref=context_ref)
        revision = int(current.get("revision", 0)) + 1 if current else 1
        environment_fingerprint = LifecycleEnvironment(
            store_revision=expected_store_revision + 1,
            foundation_fingerprint=self._schemas.fingerprint,
        ).fingerprint
        record = SchemaRevisionRecord(
            schema_ref=schema_ref,
            schema_kind=str(definition.get("schema_kind", payload.get("contribution_kind", "learned"))),
            revision=revision,
            status=target_status,
            scope_ref=context_ref,
            payload=definition,
            field_provenance={
                str(key): "asserted" for key in definition
            },
            evidence_refs=tuple(candidate.get("evidence_refs", ())),
            support_lineage_refs=tuple(sorted(independent)),
            confidence=min(1.0, float(candidate.get("confidence", 0.6))),
            permission_ref="private_learning",
            dependency_refs=grounding_refs,
            competence_case_refs=tuple(item.case_ref for item in required),
            environment_fingerprint=environment_fingerprint,
        )
        revision_payload = {
            "schema_ref": record.schema_ref,
            "schema_kind": record.schema_kind,
            "revision": record.revision,
            "status": record.status.value,
            "scope_ref": record.scope_ref,
            "payload": record.payload,
            "field_provenance": record.field_provenance,
            "evidence_refs": record.evidence_refs,
            "support_lineage_refs": record.support_lineage_refs,
            "counterevidence_refs": record.counterevidence_refs,
            "confidence": record.confidence,
            "permission_ref": record.permission_ref,
            "dependency_refs": record.dependency_refs,
            "competence_case_refs": record.competence_case_refs,
            "environment_fingerprint": record.environment_fingerprint,
            "competence_passed": bool(required and all(item.passed for item in required)),
            "epistemically_admissible": target_status == SchemaStatus.ACTIVE,
        }
        operations: list[PatchOperation] = [
            PatchOperation(
                operation_id=semantic_hash("op:schema_revision", (schema_ref, revision)),
                kind=PatchOperationKind.UPSERT_SCHEMA_REVISION,
                target_ref=schema_ref,
                payload=revision_payload,
            )
        ]
        for dependency_ref in grounding_refs:
            dep = DependencyRecord(
                dependency_id=semantic_hash("dependency", (schema_ref, revision, dependency_ref)),
                dependent_ref=schema_ref,
                dependency_ref=dependency_ref,
                dependency_kind="grounding",
                dependent_revision=revision,
                dependency_revision=1,
            )
            operations.append(PatchOperation(
                operation_id=f"op:{dep.dependency_id}",
                kind=PatchOperationKind.ADD_DEPENDENCY,
                target_ref=dep.dependency_id,
                payload={
                    "dependent_ref": dep.dependent_ref,
                    "dependency_ref": dep.dependency_ref,
                    "dependency_kind": dep.dependency_kind,
                    "dependent_revision": dep.dependent_revision,
                    "dependency_revision": dep.dependency_revision,
                    "active": dep.active,
                    "metadata": dep.metadata,
                },
            ))
        # A learned lexical alias becomes available to ordinary grounding only
        # when the contribution explicitly identifies a grounded target.
        if record.schema_kind in {"lexical_alias", "lexeme_sense"}:
            surface = str(definition.get("surface", "")).strip()
            target_ref = str(definition.get("referent_ref", "")).strip()
            language_tag = str(definition.get("language_tag", "und"))
            if surface and target_ref and self._store.get_referent(target_ref) is not None:
                operations.append(PatchOperation(
                    operation_id=semantic_hash("op:learned_alias", (language_tag, surface, target_ref)),
                    kind=PatchOperationKind.ADD_ALIAS,
                    target_ref=target_ref,
                    payload={
                        "language_tag": language_tag,
                        "surface": surface,
                        "referent_ref": target_ref,
                        "confidence": record.confidence,
                        "source_ref": schema_ref,
                    },
                ))
        return GraphPatch(
            patch_id=semantic_hash("patch:schema_promotion", (candidate_ref, schema_ref, revision)),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:schema_lifecycle",
            evidence_refs=record.evidence_refs,
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref="private_learning",
            validation_requirements=(
                "grounding_frontier_closed",
                "competence_independent",
                "atomic_schema_revision",
            ),
        )

    def compile_rule_promotion(
        self,
        candidate_ref: str,
        *,
        context_ref: str,
        expected_store_revision: int,
        target_status: SchemaStatus = SchemaStatus.PROVISIONAL,
        competence_results: Iterable[CompetenceResult] = (),
    ) -> GraphPatch | None:
        candidate = self._store.rule_candidate(candidate_ref)
        if candidate is None:
            return None
        payload = dict(candidate.get("payload", {}))
        rule_payload = payload.get("rule") if isinstance(payload.get("rule"), Mapping) else payload.get("definition")
        if not isinstance(rule_payload, Mapping):
            return None
        rule_payload = dict(rule_payload)
        if not rule_payload.get("antecedents") or not rule_payload.get("consequent"):
            return None
        frontier_refs = tuple(payload.get("frontier_refs", ()))
        grounding_refs = tuple(payload.get("grounding_refs", ()))
        if frontier_refs or not grounding_refs:
            return None
        results = tuple(competence_results)
        if target_status == SchemaStatus.ACTIVE and (not results or not all(item.passed for item in results)):
            return None
        rule_ref = str(rule_payload.get("rule_ref") or payload.get("target_ref") or candidate_ref)
        current = next((
            item for item in self._store.latest_rule_revisions(context_ref=context_ref)
            if str(item.get("rule_ref")) == rule_ref
        ), None)
        revision = int(current.get("revision", 0)) + 1 if current else 1
        independent = tuple(sorted({
            item.environment_fingerprint for item in results
            if item.passed and item.environment_fingerprint
        }))
        environment_fingerprint = LifecycleEnvironment(
            store_revision=expected_store_revision + 1,
            foundation_fingerprint=self._schemas.fingerprint,
        ).fingerprint
        operation = PatchOperation(
            operation_id=semantic_hash("op:rule_revision", (rule_ref, revision)),
            kind=PatchOperationKind.UPSERT_RULE_REVISION,
            target_ref=rule_ref,
            payload={
                "revision": revision,
                "status": target_status.value,
                "scope_ref": context_ref,
                "payload": {"rule": {**rule_payload, "rule_ref": rule_ref}},
                "evidence_refs": tuple(candidate.get("evidence_refs", ())),
                "support_lineage_refs": independent,
                "confidence": float(payload.get("confidence", 0.6)),
                "environment_fingerprint": environment_fingerprint,
            },
        )
        dependencies = tuple(
            PatchOperation(
                operation_id=semantic_hash("op:rule_dependency", (rule_ref, revision, ref)),
                kind=PatchOperationKind.ADD_DEPENDENCY,
                target_ref=semantic_hash("dependency", (rule_ref, revision, ref)),
                payload={
                    "dependent_ref": rule_ref,
                    "dependency_ref": ref,
                    "dependency_kind": "grounding",
                    "dependent_revision": revision,
                    "dependency_revision": 1,
                    "active": True,
                    "metadata": {"environment_fingerprint": environment_fingerprint},
                },
            ) for ref in grounding_refs
        )
        return GraphPatch(
            patch_id=semantic_hash("patch:rule_promotion", (candidate_ref, rule_ref, revision)),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:rule_lifecycle",
            evidence_refs=tuple(candidate.get("evidence_refs", ())),
            operations=(operation, *dependencies),
            expected_store_revision=expected_store_revision,
            permission_ref="private_learning",
            validation_requirements=(
                "grounding_frontier_closed",
                "typed_rule_patterns",
                "atomic_rule_revision",
            ),
        )

    def compile_invalidation_patch(
        self,
        changed_ref: str,
        *,
        reason: str,
        context_ref: str,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        dependents = self._store.dependents_of(changed_ref)
        if not dependents:
            return None
        operations: list[PatchOperation] = []
        for item in dependents:
            invalidation = InvalidationRecord(
                invalidation_id=semantic_hash("invalidation", (
                    item["dependent_ref"], changed_ref, expected_store_revision, reason
                )),
                target_ref=str(item["dependent_ref"]),
                reason=reason,
                cause_ref=changed_ref,
                prior_fingerprint=str(item.get("metadata", {}).get("fingerprint", "")),
                invalidated_at_revision=expected_store_revision,
            )
            operations.append(PatchOperation(
                operation_id=f"op:{invalidation.invalidation_id}",
                kind=PatchOperationKind.RECORD_INVALIDATION,
                target_ref=invalidation.invalidation_id,
                payload={
                    "target_ref": invalidation.target_ref,
                    "reason": invalidation.reason,
                    "cause_ref": invalidation.cause_ref,
                    "prior_fingerprint": invalidation.prior_fingerprint,
                    "invalidated_at_revision": invalidation.invalidated_at_revision,
                    "metadata": invalidation.metadata,
                },
            ))
        return GraphPatch(
            patch_id=semantic_hash("patch:invalidation", (changed_ref, reason, expected_store_revision)),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:dependency_invalidator",
            evidence_refs=(changed_ref,),
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref="internal",
        )
