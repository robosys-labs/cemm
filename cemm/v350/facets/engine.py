"""Universal type-closure, entitlement, state, and default projection engines."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Iterable

from ..schema.model import (
    EntitlementApplicability,
    EntitlementInheritancePolicy,
    FacetEntitlement,
    ReferentTypeSchema,
    SchemaDependency,
    SchemaLifecycleStatus,
    StateDimensionSchema,
    UseOperation,
    semantic_fingerprint,
)
from ..storage.model import (
    AssertionStatus,
    AssignmentStatus,
    ConditionTruth,
    DefaultRuleRecord,
    RecordKind,
    StoreSnapshot,
)
from ..storage.repositories import interval_contains
from .conditions import ConditionEvaluator, StoreConditionEvaluator
from .model import (
    ConditionAssessment,
    DefaultExpectation,
    ProjectedEntitlement,
    ProjectionStatus,
    StateApplicability,
    TypeClosure,
    TypeClosureMember,
)


_USABLE_LIFECYCLES = frozenset({
    SchemaLifecycleStatus.PROVISIONAL,
    SchemaLifecycleStatus.COMPETENCE_VERIFIED,
    SchemaLifecycleStatus.ACTIVE,
})


class TypeClosureCompiler:
    """Compile supported type membership without propagating opposition."""

    def __init__(self, store) -> None:
        self._store = store

    def compile(
        self,
        referent_ref: str,
        *,
        context_ref: str,
        at_time: str | None = None,
        snapshot: StoreSnapshot,
    ) -> TypeClosure:
        referent_record = self._store.repositories.referents.get(referent_ref, snapshot=snapshot)
        if referent_record is None:
            raise KeyError(referent_ref)
        referent = referent_record.payload
        registry = self._store.repositories.schemas.registry(snapshot=snapshot)
        assertions = self._store.repositories.referents.type_assertions(
            referent_ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot
        )

        support: dict[str, list] = defaultdict(list)
        opposition: dict[str, list] = defaultdict(list)
        disputed: set[str] = set()
        for assertion in assertions:
            if assertion.status == AssertionStatus.SUPPORTED:
                support[assertion.type_schema_ref].append(assertion)
            elif assertion.status == AssertionStatus.OPPOSED:
                opposition[assertion.type_schema_ref].append(assertion)
            elif assertion.status == AssertionStatus.DISPUTED:
                disputed.add(assertion.type_schema_ref)

        declared = set(referent.type_refs)
        contradicted = (set(support).intersection(opposition) | disputed
                        | declared.intersection(opposition) | declared.intersection(disputed))
        direct: list[tuple[ReferentTypeSchema, tuple[str, ...]]] = []
        unresolved: set[str] = set()
        dependency_refs: set[str] = {referent_ref}

        for type_ref in referent.type_refs:
            if type_ref in contradicted:
                continue
            try:
                schema = registry.authoritative_schema(type_ref)
            except KeyError:
                unresolved.add(type_ref)
                continue
            if not isinstance(schema, ReferentTypeSchema):
                unresolved.add(type_ref)
                continue
            direct.append((schema, (referent_ref,)))
            dependency_refs.add(type_ref)

        for type_ref, items in support.items():
            dependency_refs.update(item.assertion_ref for item in items)
            if type_ref in contradicted:
                continue
            revisions = {item.type_revision for item in items}
            if len(revisions) > 1:
                # Multiple supported revisions are retained as a conflict rather
                # than silently selecting the newest assertion.
                contradicted.add(type_ref)
                continue
            revision = next(iter(revisions))
            try:
                schema = registry.schema(type_ref, revision)
            except KeyError:
                unresolved.add(type_ref)
                continue
            if not isinstance(schema, ReferentTypeSchema):
                unresolved.add(type_ref)
                continue
            direct.append((schema, tuple(sorted(item.assertion_ref for item in items))))
            dependency_refs.add(type_ref)

        members: dict[str, TypeClosureMember] = {}
        queue: deque[tuple[ReferentTypeSchema, int, tuple[str, ...], tuple[str, ...]]] = deque()
        for schema, sources in sorted(direct, key=lambda item: (item[0].schema_ref, item[0].revision)):
            queue.append((schema, 0, sources, (schema.schema_ref,)))

        seen_revisions: dict[str, set[int]] = defaultdict(set)
        while queue:
            schema, depth, sources, path = queue.popleft()
            dependency_refs.add(schema.schema_ref)
            seen_revisions[schema.schema_ref].add(schema.revision)
            if len(seen_revisions[schema.schema_ref]) > 1:
                contradicted.add(schema.schema_ref)
                members.pop(schema.schema_ref, None)
            elif schema.schema_ref in opposition or schema.schema_ref in disputed:
                contradicted.add(schema.schema_ref)
                members.pop(schema.schema_ref, None)
            elif schema.schema_ref not in contradicted:
                current = members.get(schema.schema_ref)
                candidate = TypeClosureMember(
                    schema.schema_ref,
                    schema.revision,
                    depth,
                    depth == 0,
                    sources if depth == 0 else (),
                    path,
                )
                if current is None or (depth, -schema.revision) < (current.depth, -current.revision):
                    members[schema.schema_ref] = candidate
            for link in sorted(schema.parent_links, key=lambda item: (-item.priority, item.parent_ref)):
                try:
                    parent = registry.resolve_parent(link)
                except KeyError:
                    unresolved.add(link.parent_ref)
                    continue
                if not isinstance(parent, ReferentTypeSchema):
                    unresolved.add(link.parent_ref)
                    continue
                queue.append((parent, depth + 1, sources, (*path, parent.schema_ref)))

        dependency_fingerprint = self._store.dependency_fingerprint(
            dependency_refs, snapshot=snapshot
        )
        return TypeClosure(
            referent_ref=referent_ref,
            context_ref=context_ref,
            at_time=at_time,
            members=tuple(sorted(members.values(), key=lambda item: (item.depth, item.type_ref))),
            opposed_type_refs=tuple(sorted(opposition)),
            contradicted_type_refs=tuple(sorted(contradicted)),
            unresolved_type_refs=tuple(sorted(unresolved)),
            dependency_refs=tuple(sorted(dependency_refs)),
            dependency_fingerprint=dependency_fingerprint,
        )


class FacetEntitlementProjector:
    """Merge inherited entitlements using explicit inheritance policies."""

    def __init__(self, store, *, condition_evaluator: ConditionEvaluator | None = None) -> None:
        self._store = store
        self._conditions = condition_evaluator or StoreConditionEvaluator(store)

    def project(
        self,
        closure: TypeClosure,
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> tuple[ProjectedEntitlement, ...]:
        registry = self._store.repositories.schemas.registry(snapshot=snapshot)
        depth = {item.type_ref: item.depth for item in closure.members}
        by_facet: dict[str, list[tuple[int, FacetEntitlement]]] = defaultdict(list)
        for type_ref in sorted(closure.type_refs):
            for item in registry.direct_entitlements_for_type(type_ref):
                if item.lifecycle_status not in _USABLE_LIFECYCLES:
                    continue
                if not item.use_profile.permits(UseOperation.GROUND, provisional=True):
                    continue
                by_facet[item.facet_ref].append((depth[type_ref], item))
        result = [
            self._merge(facet_ref, values, context_ref=context_ref, at_time=at_time, snapshot=snapshot)
            for facet_ref, values in sorted(by_facet.items())
        ]
        return tuple(result)

    def _merge(
        self,
        facet_ref: str,
        values: list[tuple[int, FacetEntitlement]],
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> ProjectedEntitlement:
        values = sorted(values, key=lambda pair: (pair[0], pair[1].owner_type_ref, pair[1].entitlement_ref))
        minimum_depth = values[0][0]
        most_specific = [item for item_depth, item in values if item_depth == minimum_depth]
        if any(item.inheritance_policy == EntitlementInheritancePolicy.OVERRIDE for item in most_specific):
            # Override removes only less-specific inherited contracts. Peer
            # contracts from other direct types remain visible and may conflict.
            values = [(minimum_depth, item) for item in most_specific]
        if any(item.inheritance_policy == EntitlementInheritancePolicy.BLOCK for item in most_specific):
            return self._projection(
                facet_ref, values, ProjectionStatus.BLOCKED, None, (), (), (),
                tuple(item.entitlement_ref for item in most_specific),
                ("most_specific_entitlement_blocks_inheritance",), snapshot=snapshot,
            )

        top_applicability = {item.applicability for item in most_specific}
        if top_applicability == {EntitlementApplicability.PROHIBITED}:
            top_values = [(minimum_depth, item) for item in most_specific]
            return self._projection(
                facet_ref, top_values, ProjectionStatus.INAPPLICABLE,
                EntitlementApplicability.PROHIBITED, (), (), (), (),
                ("most_specific_type_prohibits_facet",), snapshot=snapshot,
            )
        applicability_values = {item.applicability for _, item in values}
        has_prohibition = EntitlementApplicability.PROHIBITED in applicability_values
        has_license = bool(applicability_values - {EntitlementApplicability.PROHIBITED})
        if has_prohibition and has_license:
            return self._projection(
                facet_ref, values, ProjectionStatus.CONTRADICTED, None, (), (), (), (),
                ("inherited_applicability_conflict",), snapshot=snapshot,
            )
        if has_prohibition:
            return self._projection(
                facet_ref, values, ProjectionStatus.INAPPLICABLE, EntitlementApplicability.PROHIBITED,
                (), (), (), (), ("facet_prohibited",), snapshot=snapshot,
            )

        selected_applicability = _strongest_applicability(applicability_values)
        status = (
            ProjectionStatus.UNKNOWN
            if selected_applicability == EntitlementApplicability.REQUIRED
            else ProjectionStatus.LATENT
        )
        domains = self._merge_domains(values)
        defaults = tuple(sorted({ref for _, item in values for ref in item.default_rule_refs}))
        conditions: list[ConditionAssessment] = []
        blocking: list[str] = []
        reasons: list[str] = []
        context_mismatch = False

        for _, item in values:
            if item.context_constraints and context_ref not in {*item.context_constraints, "global"}:
                context_mismatch = True
                reasons.append(f"context_not_licensed:{item.entitlement_ref}")
            for condition_ref in item.temporal_constraints:
                assessment = self._conditions.assess(
                    condition_ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot
                )
                conditions.append(assessment)
                if assessment.truth in {ConditionTruth.UNSATISFIED, ConditionTruth.UNKNOWN}:
                    blocking.append(condition_ref)
                elif assessment.truth == ConditionTruth.CONTRADICTED:
                    status = ProjectionStatus.CONTRADICTED
                    reasons.append(f"temporal_constraint_contradicted:{condition_ref}")
            for dependency in item.dependencies:
                assessment = self._assess_dependency(dependency, context_ref, at_time, snapshot)
                conditions.append(assessment)
                governs_projection = (
                    not dependency.required_for or UseOperation.GROUND in dependency.required_for
                )
                if dependency.required and governs_projection and assessment.truth != ConditionTruth.SATISFIED:
                    blocking.append(dependency.dependency_ref)
                if assessment.truth == ConditionTruth.CONTRADICTED:
                    status = ProjectionStatus.CONTRADICTED
                    reasons.append(f"dependency_contradicted:{dependency.dependency_ref}")

        if status != ProjectionStatus.CONTRADICTED and context_mismatch:
            status = ProjectionStatus.INAPPLICABLE
            reasons.append("entitlement_context_inapplicable")
        elif status != ProjectionStatus.CONTRADICTED and blocking:
            status = ProjectionStatus.BLOCKED
            reasons.append("entitlement_conditions_not_satisfied")
        return self._projection(
            facet_ref, values, status, selected_applicability, domains, defaults,
            tuple(conditions), tuple(blocking), tuple(reasons), snapshot=snapshot,
        )

    def _assess_dependency(
        self,
        dependency: SchemaDependency,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> ConditionAssessment:
        records = self._store.resolve_any(dependency.dependency_ref, snapshot=snapshot)
        candidates = [
            item for item in records
            if dependency.exact_revision is None or item.revision == dependency.exact_revision
            if dependency.minimum_revision is None or item.revision >= dependency.minimum_revision
        ]
        if candidates:
            return ConditionAssessment(
                dependency.dependency_ref,
                ConditionTruth.SATISFIED,
                reason="dependency_record_resolved",
            )
        return self._conditions.assess(
            dependency.dependency_ref,
            context_ref=context_ref,
            at_time=at_time,
            snapshot=snapshot,
        )

    @staticmethod
    def _merge_domains(values: list[tuple[int, FacetEntitlement]]) -> tuple[str, ...]:
        domain: set[str] = set()
        for _, item in sorted(values, key=lambda pair: (-pair[0], pair[1].owner_type_ref)):
            incoming = set(item.value_domain_refs)
            if item.inheritance_policy == EntitlementInheritancePolicy.OVERRIDE:
                domain = incoming
            elif item.inheritance_policy == EntitlementInheritancePolicy.NARROW_DOMAIN:
                domain = incoming if not domain else domain.intersection(incoming)
            elif item.inheritance_policy == EntitlementInheritancePolicy.BLOCK:
                domain.clear()
            else:
                domain.update(incoming)
        return tuple(sorted(domain))

    def _projection(
        self,
        facet_ref: str,
        values: list[tuple[int, FacetEntitlement]],
        status: ProjectionStatus,
        applicability: EntitlementApplicability | None,
        domains: tuple[str, ...],
        defaults: tuple[str, ...],
        conditions: tuple[ConditionAssessment, ...],
        blocking_refs: tuple[str, ...],
        reasons: tuple[str, ...],
        *,
        snapshot: StoreSnapshot,
    ) -> ProjectedEntitlement:
        items = [item for _, item in values]
        dependencies = {
            item.entitlement_ref for item in items
        } | {item.owner_type_ref for item in items} | {item.facet_ref for item in items}
        dependencies.update(ref for item in items for ref in item.default_rule_refs)
        dependencies.update(dep.dependency_ref for item in items for dep in item.dependencies)
        return ProjectedEntitlement(
            facet_ref=facet_ref,
            status=status,
            applicability=applicability,
            activation_policy=(
                items[0].activation_policy
                if len({item.activation_policy for item in items}) <= 1
                else "compose"
            ) if items else "none",
            inheritance_policies=tuple(sorted({item.inheritance_policy for item in items}, key=lambda value: value.value)),
            value_domain_refs=domains,
            default_rule_refs=defaults,
            owner_type_refs=tuple(sorted({item.owner_type_ref for item in items})),
            source_entitlement_refs=tuple(sorted(item.entitlement_ref for item in items)),
            source_entitlement_revisions=tuple(sorted((item.entitlement_ref, item.revision) for item in items)),
            condition_assessments=conditions,
            blocking_refs=tuple(sorted(set(blocking_refs))),
            confidence=min((item.confidence for item in items), default=1.0),
            dependency_refs=tuple(sorted(dependencies)),
            dependency_fingerprint=self._store.dependency_fingerprint(dependencies, snapshot=snapshot),
            reasons=tuple(dict.fromkeys(reasons)),
        )


class DefaultExpectationProjector:
    """Project defeasible expectations without creating StateAssignment records."""

    def __init__(self, store, *, condition_evaluator: ConditionEvaluator | None = None) -> None:
        self._store = store
        self._conditions = condition_evaluator or StoreConditionEvaluator(store)

    def project(
        self,
        referent_ref: str,
        closure: TypeClosure,
        entitlements: Iterable[ProjectedEntitlement],
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> tuple[DefaultExpectation, ...]:
        licensed = {item.facet_ref: item for item in entitlements if item.status not in {
            ProjectionStatus.INAPPLICABLE, ProjectionStatus.BLOCKED, ProjectionStatus.CONTRADICTED
        }}
        candidates: dict[str, DefaultRuleRecord] = {}
        for facet in licensed.values():
            for rule_ref in facet.default_rule_refs:
                try:
                    candidates[rule_ref] = self._store.repositories.default_rules.authoritative(
                        rule_ref, snapshot=snapshot
                    )
                except KeyError:
                    pass
            for rule in self._store.repositories.default_rules.for_facet(facet.facet_ref, snapshot=snapshot):
                candidates[rule.rule_ref] = rule
        result: list[DefaultExpectation] = []
        for rule in sorted(candidates.values(), key=lambda item: (-item.priority, item.rule_ref)):
            if rule.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
                continue
            if rule.target_facet_ref not in licensed:
                continue
            if rule.holder_type_refs and not closure.type_refs.intersection(rule.holder_type_refs):
                continue
            if rule.context_constraints and context_ref not in {*rule.context_constraints, "global"}:
                continue
            condition_assessments = tuple(
                self._conditions.assess(ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot)
                for ref in rule.condition_refs
            )
            defeater_assessments = tuple(
                self._conditions.assess(ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot)
                for ref in rule.defeater_refs
            )
            if any(item.truth != ConditionTruth.SATISFIED for item in condition_assessments):
                continue
            if any(item.truth in {ConditionTruth.SATISFIED, ConditionTruth.CONTRADICTED} for item in defeater_assessments):
                continue
            temporal = tuple(
                self._conditions.assess(ref, context_ref=context_ref, at_time=at_time, snapshot=snapshot)
                for ref in rule.temporal_constraints
            )
            if any(item.truth != ConditionTruth.SATISFIED for item in temporal):
                continue
            dependency_refs = {
                referent_ref, rule.rule_ref, rule.target_facet_ref,
                *rule.holder_type_refs, *rule.condition_refs, *rule.defeater_refs,
                *rule.temporal_constraints,
            }
            for ref in (rule.expected_dimension_ref, rule.expected_value_ref):
                if ref:
                    dependency_refs.add(ref)
            result.append(DefaultExpectation(
                expectation_ref=semantic_fingerprint(
                    "default-expectation",
                    (rule.rule_ref, rule.revision, referent_ref, context_ref, at_time),
                    48,
                ),
                rule_ref=rule.rule_ref,
                rule_revision=rule.revision,
                facet_ref=rule.target_facet_ref,
                holder_ref=referent_ref,
                context_ref=context_ref,
                dimension_ref=rule.expected_dimension_ref,
                dimension_revision=rule.expected_dimension_revision,
                value_ref=rule.expected_value_ref,
                value_revision=rule.expected_value_revision,
                confidence=rule.confidence,
                condition_assessments=(*condition_assessments, *temporal),
                defeater_assessments=defeater_assessments,
                dependency_refs=tuple(sorted(dependency_refs)),
                proof_refs=tuple(sorted({*rule.evidence_refs, *(ref for item in condition_assessments for ref in item.evidence_refs)})),
            ))
        return tuple(result)


class StateApplicabilityAssessor:
    def __init__(self, store) -> None:
        self._store = store

    def assess(
        self,
        holder_ref: str,
        dimension_ref: str,
        dimension_revision: int,
        closure: TypeClosure,
        entitlements: Iterable[ProjectedEntitlement],
        defaults: Iterable[DefaultExpectation],
        *,
        context_ref: str,
        at_time: str | None,
        snapshot: StoreSnapshot,
    ) -> StateApplicability:
        registry = self._store.repositories.schemas.registry(snapshot=snapshot)
        schema = registry.schema(dimension_ref, dimension_revision)
        if not isinstance(schema, StateDimensionSchema):
            raise TypeError(f"{dimension_ref}@{dimension_revision} is not a state dimension")
        facet_ref = str(schema.metadata.get("facet_ref") or dimension_ref)
        entitlement = next((item for item in entitlements if item.facet_ref in {facet_ref, dimension_ref}), None)
        dependency_refs = {holder_ref, dimension_ref}
        reasons: list[str] = []
        if schema.holder_type_refs and not closure.type_refs.intersection(schema.holder_type_refs):
            return self._result(holder_ref, schema, facet_ref, ProjectionStatus.INAPPLICABLE, (), (), (), (), (), dependency_refs, ("holder_type_not_licensed",), snapshot)
        if entitlement is None:
            return self._result(holder_ref, schema, facet_ref, ProjectionStatus.INAPPLICABLE, (), (), (), (), (), dependency_refs, ("facet_entitlement_missing",), snapshot)
        dependency_refs.update(entitlement.dependency_refs)
        if entitlement.status in {ProjectionStatus.INAPPLICABLE, ProjectionStatus.BLOCKED, ProjectionStatus.CONTRADICTED}:
            return self._result(holder_ref, schema, facet_ref, entitlement.status, (), (), (), (), (), dependency_refs, entitlement.reasons, snapshot)

        history = tuple(
            stored.payload
            for stored in self._store.repositories.state_assignments.all(snapshot=snapshot)
            if stored.payload.holder_ref == holder_ref
            and stored.payload.dimension_ref == dimension_ref
            and stored.payload.context_ref in {"global", context_ref}
        )
        current = tuple(
            item for item in history
            if interval_contains(item.valid_from, item.valid_to, at_time)
        )
        active = tuple(sorted({
            item.value_ref for item in current if item.status == AssignmentStatus.ACTIVE
        }))
        opposition = tuple(sorted({
            item.value_ref for item in current if item.status == AssignmentStatus.OPPOSED
        }))
        terminated = tuple(sorted({
            item.value_ref for item in history
            if item.status == AssignmentStatus.TERMINATED
            or (item.status == AssignmentStatus.ACTIVE and _ended_before(item.valid_to, at_time))
        }))
        assignment_refs = tuple(sorted(item.assignment_ref for item in history))
        dependency_refs.update(assignment_refs)
        expected = tuple(
            item for item in defaults
            if item.dimension_ref == dimension_ref and item.dimension_revision == dimension_revision
        )
        dependency_refs.update(item.rule_ref for item in expected)

        outside_domain = (
            bool(entitlement.value_domain_refs)
            and bool(set(active).difference(entitlement.value_domain_refs))
        )
        if outside_domain:
            status = ProjectionStatus.CONTRADICTED
            reasons.append("active_value_outside_entitlement_domain")
        elif any(item.status == AssignmentStatus.CONTRADICTED for item in current):
            status = ProjectionStatus.CONTRADICTED
            reasons.append("explicit_state_contradiction")
        elif active and opposition:
            status = ProjectionStatus.CONTRADICTED
            reasons.append("supported_and_opposed_state")
        elif schema.exclusive and len(active) > 1:
            status = ProjectionStatus.CONTRADICTED
            reasons.append("exclusive_dimension_has_multiple_active_values")
        elif active:
            status = ProjectionStatus.ACTIVE
        elif terminated:
            status = ProjectionStatus.TERMINATED
        elif expected:
            status = ProjectionStatus.DEFAULT_EXPECTED
        else:
            status = entitlement.status
        return self._result(
            holder_ref, schema, facet_ref, status, active, opposition, terminated,
            expected, assignment_refs, dependency_refs, tuple(reasons), snapshot,
        )

    def _result(
        self,
        holder_ref: str,
        schema: StateDimensionSchema,
        facet_ref: str,
        status: ProjectionStatus,
        active: tuple[str, ...],
        opposition: tuple[str, ...],
        terminated: tuple[str, ...],
        defaults: tuple[DefaultExpectation, ...],
        assignment_refs: tuple[str, ...],
        dependencies: set[str],
        reasons: tuple[str, ...],
        snapshot: StoreSnapshot,
    ) -> StateApplicability:
        return StateApplicability(
            holder_ref=holder_ref,
            dimension_ref=schema.schema_ref,
            dimension_revision=schema.revision,
            facet_ref=facet_ref,
            status=status,
            active_value_refs=active,
            opposed_value_refs=opposition,
            terminated_value_refs=terminated,
            default_expectations=defaults,
            assignment_refs=assignment_refs,
            dependency_refs=tuple(sorted(dependencies)),
            dependency_fingerprint=self._store.dependency_fingerprint(dependencies, snapshot=snapshot),
            reasons=reasons,
        )


def _ended_before(valid_to: str | None, at_time: str | None) -> bool:
    if not valid_to:
        return False
    try:
        end = datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if at_time is None:
            point = datetime.now(timezone.utc)
        else:
            point = datetime.fromisoformat(at_time.replace("Z", "+00:00"))
            if point.tzinfo is None:
                point = point.replace(tzinfo=timezone.utc)
        return end <= point
    except ValueError:
        return False


def _strongest_applicability(values: set[EntitlementApplicability]) -> EntitlementApplicability:
    order = (
        EntitlementApplicability.REQUIRED,
        EntitlementApplicability.CONDITIONAL,
        EntitlementApplicability.OPTIONAL,
        EntitlementApplicability.INHERITED_ONLY,
    )
    return next(item for item in order if item in values)
