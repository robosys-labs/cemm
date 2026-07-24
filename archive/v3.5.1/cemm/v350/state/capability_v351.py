"""Exact bounded capability dependency graphs over Phase-15 typed state.

Capability is derived from state/resources/other capabilities by an exact dependency DAG.  It is
not a hand-maintained boolean and does not gain authority merely because a record is ACTIVE.
Candidate graphs participate in the ordinary Phase-14 per-use promotion machinery; executable
runtime use additionally requires explicit TRANSITION authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Callable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import StateDimensionSchema, UseOperation, semantic_fingerprint
from ..storage.model import AssertionStatus, AssignmentStatus, CapabilityInstance, CapabilityStatus, RecordKind, StateAssignment
from .algebra_v351 import StateAlgebraV351, StateDomainCompilerV351
from .entitlement_v351 import EntitledStateSpaceCompilerV351, state_value_from_document
from .model_v351 import ConditionOperatorV351, StateModelError, StateValueV351


class CapabilityNodeKind(str, Enum):
    ALL = "all"
    ANY = "any"
    NOT = "not"
    STATE = "state"
    CAPABILITY = "capability"
    RESOURCE = "resource"
    ADAPTER = "adapter"
    PERMISSION = "permission"
    COMPETENCE = "competence"
    STRUCTURAL = "structural"


@dataclass(frozen=True, slots=True)
class CapabilityStateRequirementV351:
    """Typed state predicate for one capability leaf.

    No requirement is encoded by parsing a string key.  Units/frames/domain validity are checked
    by the same StateAlgebra used by causal transition preview.
    """

    requirement_ref: str
    dimension_pin: ExactAuthorityPin
    operator: ConditionOperatorV351
    expected_value: StateValueV351 | None = None
    expected_member_ref: str = ""
    numeric_threshold: float | None = None

    def __post_init__(self) -> None:
        if not self.requirement_ref:
            raise StateModelError("capability state requirement_ref required")
        if self.numeric_threshold is not None and not isfinite(self.numeric_threshold):
            raise StateModelError("capability state threshold must be finite")
        if self.operator in {ConditionOperatorV351.EQUALS, ConditionOperatorV351.NOT_EQUALS}:
            if self.expected_value is None:
                raise StateModelError("state equality capability requirement needs typed expected value")
        if self.operator in {
            ConditionOperatorV351.CONTAINS, ConditionOperatorV351.NOT_CONTAINS
        } and not self.expected_member_ref:
            raise StateModelError("state membership capability requirement needs member identity")
        if self.operator in {
            ConditionOperatorV351.GREATER_THAN,
            ConditionOperatorV351.GREATER_EQUAL,
            ConditionOperatorV351.LESS_THAN,
            ConditionOperatorV351.LESS_EQUAL,
        } and self.numeric_threshold is None and self.expected_value is None:
            raise StateModelError(
                "ordered capability requirement needs a typed expected value or dimensionless numeric threshold"
            )
        if self.operator is ConditionOperatorV351.PROBABILITY_AT_LEAST:
            if self.expected_value is None or self.numeric_threshold is None:
                raise StateModelError(
                    "probability capability requirement needs typed support value and threshold"
                )
            if not 0.0 <= self.numeric_threshold <= 1.0:
                raise StateModelError("probability capability threshold must be in [0,1]")


@dataclass(frozen=True, slots=True)
class CapabilityDependencyNodeV351:
    node_ref: str
    kind: CapabilityNodeKind
    child_refs: tuple[str, ...] = ()
    requirement_ref: str = ""
    requirement_pin: ExactAuthorityPin | None = None
    state_requirement: CapabilityStateRequirementV351 | None = None
    minimum_support: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_ref:
            raise StateModelError("capability dependency node_ref required")
        if not isfinite(self.minimum_support) or not 0.0 <= self.minimum_support <= 1.0:
            raise StateModelError("capability dependency minimum_support must be in [0,1]")
        if self.kind in {CapabilityNodeKind.ALL, CapabilityNodeKind.ANY, CapabilityNodeKind.NOT}:
            if not self.child_refs:
                raise StateModelError("logical capability node requires children")
            if self.kind is CapabilityNodeKind.NOT and len(self.child_refs) != 1:
                raise StateModelError("NOT capability node requires exactly one child")
            if self.requirement_ref or self.requirement_pin is not None or self.state_requirement is not None:
                raise StateModelError("logical capability node cannot smuggle a leaf requirement")
        elif self.kind is CapabilityNodeKind.STATE:
            if self.state_requirement is None:
                raise StateModelError("STATE capability node requires typed state_requirement")
            if self.requirement_pin is not None:
                raise StateModelError("STATE capability node uses exact dimension pin inside state_requirement")
        else:
            if not self.requirement_ref:
                raise StateModelError("leaf capability node requires requirement_ref")
            if self.state_requirement is not None:
                raise StateModelError("non-state capability node cannot carry state_requirement")


@dataclass(frozen=True, slots=True)
class CapabilityDependencyGraph:
    graph_ref: str
    action_schema_pin: ExactAuthorityPin
    holder_type_pins: tuple[ExactAuthorityPin, ...]
    root_ref: str
    nodes: tuple[CapabilityDependencyNodeV351, ...]
    lifecycle_status: str = "candidate"
    competence_case_pins: tuple[ExactAuthorityPin, ...] = ()
    permission_ref: str = "public"
    revision: int = 1
    use_operation: UseOperation = UseOperation.TRANSITION
    authorized_use_operations: tuple[UseOperation, ...] = ()
    use_authority_explicit: bool = False
    context_scopes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.graph_ref or not self.root_ref or not self.permission_ref:
            raise StateModelError("capability graph requires refs and permission")
        if self.revision < 1:
            raise StateModelError("capability graph revision must be positive")
        if self.use_operation is not UseOperation.TRANSITION:
            raise StateModelError("capability dependency graph structural use axis is TRANSITION")
        if len({pin.key for pin in self.holder_type_pins}) != len(self.holder_type_pins):
            raise StateModelError("capability graph holder type pins must be unique")
        if len({pin.key for pin in self.competence_case_pins}) != len(self.competence_case_pins):
            raise StateModelError("capability graph competence pins must be unique")
        if len(self.authorized_use_operations) != len(set(self.authorized_use_operations)):
            raise StateModelError("capability graph authorized uses must be unique")
        allowed_lifecycle = {"candidate", "structurally_closed", "provisional", "competence_verified", "active", "superseded", "rejected"}
        if self.lifecycle_status not in allowed_lifecycle:
            raise StateModelError("capability graph lifecycle status is not recognized")
        if self.authorized_use_operations and not self.use_authority_explicit:
            raise StateModelError("capability graph granted uses require explicit use authority")
        if self.use_authority_explicit and UseOperation.TRANSITION not in self.authorized_use_operations:
            raise StateModelError("explicit capability graph use authority must include TRANSITION")
        if self.lifecycle_status == "active" and not self.evidence_refs:
            raise StateModelError("active capability dependency graph requires reviewed evidence")
        if len(self.context_scopes) != len(set(self.context_scopes)):
            raise StateModelError("capability graph context scopes must be unique")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise StateModelError("capability graph evidence refs must be unique")
        by_ref = {item.node_ref: item for item in self.nodes}
        if len(by_ref) != len(self.nodes) or self.root_ref not in by_ref:
            raise StateModelError("capability graph nodes must be unique and contain root")
        for node in self.nodes:
            unknown = set(node.child_refs).difference(by_ref)
            if unknown:
                raise StateModelError(
                    f"capability graph references unknown children:{sorted(unknown)}"
                )
        self._require_acyclic(by_ref)

    @staticmethod
    def _require_acyclic(by_ref):
        visiting, done = set(), set()

        def walk(ref):
            if ref in done:
                return
            if ref in visiting:
                raise StateModelError("capability dependency graph contains a cycle")
            visiting.add(ref)
            for child in by_ref[ref].child_refs:
                walk(child)
            visiting.remove(ref)
            done.add(ref)

        for ref in sorted(by_ref):
            walk(ref)

    @property
    def dependency_ref(self) -> str:
        """Compatibility identity for RecordKind.CAPABILITY_DEPENDENCY."""
        return self.graph_ref

    @property
    def authority_pin(self) -> ExactAuthorityPin:
        # Lifecycle, competence, permission and granted uses are deliberately excluded from
        # semantic mechanism identity. Promotion rotates operational authority, not meaning.
        payload = (
            self.action_schema_pin.key,
            tuple(pin.key for pin in self.holder_type_pins),
            self.root_ref,
            self.nodes,
        )
        return ExactAuthorityPin(
            "capability_dependency",
            "cemm:v351:capability",
            self.graph_ref,
            self.revision,
            semantic_fingerprint("capability-dependency-authority-v351", payload, 64),
            "global",
        )

    @property
    def executable(self) -> bool:
        return (
            self.lifecycle_status == "active"
            and bool(self.competence_case_pins)
            and self.use_authority_explicit
            and UseOperation.TRANSITION in self.authorized_use_operations
        )


@dataclass(frozen=True, slots=True)
class CapabilityAssessmentV351:
    assessment_ref: str
    graph_ref: str
    holder_ref: str
    action_schema_pin: ExactAuthorityPin
    status: CapabilityStatus
    support: float
    satisfied_node_refs: tuple[str, ...]
    failed_node_refs: tuple[str, ...]
    unknown_node_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    frontier_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityDeltaV351:
    delta_ref: str
    graph_pin: ExactAuthorityPin
    holder_ref: str
    action_schema_pin: ExactAuthorityPin
    prior_status: CapabilityStatus | None
    new_status: CapabilityStatus
    confidence: float
    context_ref: str
    proof_refs: tuple[str, ...] = ()
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.delta_ref or not self.holder_ref or not self.context_ref:
            raise StateModelError("capability delta requires stable refs")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise StateModelError("capability delta confidence must be in [0,1]")


class CapabilityDependencyEvaluatorV351:
    """Evaluate one DAG with tri-valued leaf support.

    `resolve_leaf(node)` returns `(truth, support, proof_refs)`, where truth is
    True/False/None. No requirement names or domain words are interpreted by this kernel.
    """

    def evaluate(
        self,
        graph: CapabilityDependencyGraph,
        *,
        holder_ref: str,
        resolve_leaf: Callable[[CapabilityDependencyNodeV351], tuple[bool | None, float, tuple[str, ...]]],
        maximum_nodes: int = 1024,
    ) -> CapabilityAssessmentV351:
        if not graph.executable:
            raise StateModelError(
                "capability dependency graph is not active/competence/use-authorized"
            )
        if len(graph.nodes) > maximum_nodes:
            raise StateModelError("capability dependency graph exceeds evaluation budget")
        by_ref = {item.node_ref: item for item in graph.nodes}
        memo = {}
        proofs = set()
        satisfied, failed, unknown = set(), set(), set()

        def visit(ref):
            if ref in memo:
                return memo[ref]
            node = by_ref[ref]
            if node.kind not in {
                CapabilityNodeKind.ALL,
                CapabilityNodeKind.ANY,
                CapabilityNodeKind.NOT,
            }:
                truth, support, refs = resolve_leaf(node)
                support = max(0.0, min(1.0, float(support)))
                proofs.update(refs)
                if truth is True and support >= node.minimum_support:
                    result = (True, support)
                    satisfied.add(ref)
                elif truth is False and support >= node.minimum_support:
                    # `support` is confidence in the resolved truth value, not P(True).
                    # Inverting it would make strong evidence for a failed prerequisite look weak.
                    result = (False, support)
                    failed.add(ref)
                else:
                    result = (None, support)
                    unknown.add(ref)
            else:
                children = [visit(child) for child in node.child_refs]
                if node.kind is CapabilityNodeKind.ALL:
                    failed_children = tuple(s for t, s in children if t is False)
                    if failed_children:
                        # One warranted false prerequisite is sufficient to refute ALL.
                        result = (False, max(failed_children))
                    elif any(t is None for t, _ in children):
                        result = (None, min(s for _, s in children))
                    else:
                        result = (True, min(s for _, s in children))
                elif node.kind is CapabilityNodeKind.ANY:
                    true_children = tuple(s for t, s in children if t is True)
                    if true_children:
                        # One warranted true alternative is sufficient to satisfy ANY.
                        result = (True, max(true_children))
                    elif all(t is False for t, _ in children):
                        # Refuting ANY requires every alternative to be false; use the weakest warrant.
                        result = (False, min(s for _, s in children))
                    else:
                        result = (None, max(s for _, s in children))
                else:
                    t, s = children[0]
                    result = (None if t is None else not t, s)
                if result[0] is True:
                    satisfied.add(ref)
                elif result[0] is False:
                    failed.add(ref)
                else:
                    unknown.add(ref)
            memo[ref] = result
            return result

        truth, support = visit(graph.root_ref)
        status = (
            CapabilityStatus.AVAILABLE
            if truth is True
            else CapabilityStatus.BLOCKED
            if truth is False
            else CapabilityStatus.CONDITIONAL
        )
        frontiers = tuple(f"frontier:capability:unknown:{ref}" for ref in sorted(unknown))
        return CapabilityAssessmentV351(
            assessment_ref="capability-assessment:" + semantic_fingerprint(
                "capability-assessment-v351",
                (graph.authority_pin.key, holder_ref, tuple(sorted(memo.items()))),
                32,
            ),
            graph_ref=graph.graph_ref,
            holder_ref=holder_ref,
            action_schema_pin=graph.action_schema_pin,
            status=status,
            support=support,
            satisfied_node_refs=tuple(sorted(satisfied)),
            failed_node_refs=tuple(sorted(failed)),
            unknown_node_refs=tuple(sorted(unknown)),
            proof_refs=tuple(sorted(proofs)),
            frontier_refs=frontiers,
        )


class CapabilityDependencyRuntimeV351:
    """Evaluate exact capability graphs after actual state commit.

    Capability-to-capability leaves recurse through exact action-schema pins with cycle
    protection. STATE leaves read the same typed state algebra used by causal transition
    preview. Other leaf families require an injected exact resolver and remain unknown when
    none is installed.
    """

    def __init__(
        self, *, external_leaf_resolver=None, maximum_graph_depth: int = 32,
        algebra: StateAlgebraV351 | None = None,
    ) -> None:
        if maximum_graph_depth < 1:
            raise ValueError("maximum_graph_depth must be positive")
        self.external_leaf_resolver = external_leaf_resolver
        self.maximum_graph_depth = maximum_graph_depth
        self.algebra = algebra or StateAlgebraV351()
        self.evaluator = CapabilityDependencyEvaluatorV351()

    def evaluate(self, store, *, context_ref: str, permission_ref: str, authority_snapshot=None):
        visible_graphs = {}
        authority_frontiers = []
        for item in store.records(RecordKind.CAPABILITY_DEPENDENCY, all_revisions=True):
            payload = item.payload
            if not isinstance(payload, CapabilityDependencyGraph) or not payload.executable:
                continue
            if store.is_invalidated(RecordKind.CAPABILITY_DEPENDENCY, item.record_ref, item.revision):
                continue
            if payload.permission_ref not in {"public", permission_ref}:
                continue
            if payload.context_scopes and context_ref not in payload.context_scopes and "global" not in payload.context_scopes:
                continue
            if authority_snapshot is not None:
                try:
                    from ..causal.authority_v351 import require_exact_use
                    require_exact_use(
                        authority_snapshot, payload.authority_pin, operation="transition",
                        context_ref=context_ref, permission_ref=permission_ref,
                    )
                except Exception:
                    authority_frontiers.append(
                        "frontier:capability:exact-transition-use-authority-required:" + payload.graph_ref
                    )
                    continue
            current = visible_graphs.get(payload.graph_ref)
            if current is None or payload.revision > current.revision:
                visible_graphs[payload.graph_ref] = payload
        graphs = tuple(visible_graphs[key] for key in sorted(visible_graphs))
        by_action = {}
        for graph in graphs:
            by_action.setdefault(graph.action_schema_pin.key, []).append(graph)
        assessments = []
        deltas = []
        frontiers = list(authority_frontiers)
        memo = {}

        def holders_for(graph):
            if not graph.holder_type_pins:
                frontiers.append(
                    f"frontier:capability:holder-type-authority-required:{graph.graph_ref}"
                )
                return ()
            allowed = {(pin.ref, pin.revision) for pin in graph.holder_type_pins}
            holders = {
                item.payload.referent_ref
                for item in store.records(RecordKind.TYPE_ASSERTION)
                if (
                    getattr(item.payload, "type_schema_ref", ""),
                    getattr(item.payload, "type_revision", 0),
                ) in allowed
                and getattr(item.payload, "status", None) is AssertionStatus.SUPPORTED
                and getattr(item.payload, "context_ref", context_ref) in {"global", context_ref}
                and getattr(item.payload, "permission_ref", permission_ref) in {"public", permission_ref}
            }
            return tuple(sorted(holders))

        def current_capability_instances(holder_ref, action_pin):
            candidates = tuple(
                item.payload
                for item in store.records(RecordKind.CAPABILITY_INSTANCE)
                if isinstance(item.payload, CapabilityInstance)
                and item.payload.holder_ref == holder_ref
                and item.payload.action_schema_ref == action_pin.ref
                and item.payload.action_schema_revision == action_pin.revision
                and item.payload.context_ref in {"global", context_ref}
            )
            exact = tuple(item for item in candidates if item.context_ref == context_ref)
            fallback = tuple(item for item in candidates if item.context_ref == "global")
            return exact if exact else fallback

        def evaluate_graph(graph, holder_ref, stack=()):
            key = (graph.authority_pin.key, holder_ref, context_ref)
            if key in memo:
                return memo[key]
            if len(stack) >= self.maximum_graph_depth or key in stack:
                frontiers.append(
                    "frontier:capability:dependency-cycle-or-depth:" + graph.graph_ref
                )
                return None

            def resolve_leaf(node):
                if node.kind is CapabilityNodeKind.STATE:
                    return self._resolve_state_leaf(
                        store, holder_ref, context_ref, node.state_requirement
                    )
                if node.kind is CapabilityNodeKind.CAPABILITY:
                    if node.requirement_pin is None:
                        return None, 0.0, ()
                    candidates = tuple(by_action.get(node.requirement_pin.key, ()))
                    if len(candidates) > 1:
                        frontiers.append(
                            "frontier:capability:multiple-authoritative-dependencies:"
                            + node.node_ref
                        )
                        return None, 0.0, ()
                    if len(candidates) == 1:
                        nested = evaluate_graph(candidates[0], holder_ref, (*stack, key))
                        if nested is None:
                            return None, 0.0, ()
                        truth = (
                            True if nested.status is CapabilityStatus.AVAILABLE
                            else False if nested.status is CapabilityStatus.BLOCKED
                            else None
                        )
                        return truth, nested.support, (
                            nested.assessment_ref,
                            *nested.proof_refs,
                        )
                    # Existing durable capability instances are permitted as observational
                    # fallback when no exact dependency graph for that action is active.
                    durable = current_capability_instances(holder_ref, node.requirement_pin)
                    if len(durable) != 1:
                        if len(durable) > 1:
                            frontiers.append(
                                "frontier:capability:multiple-active-instances:" + node.node_ref
                            )
                        return None, 0.0, ()
                    item = durable[0]
                    truth = (
                        True if item.status is CapabilityStatus.AVAILABLE
                        else False if item.status is CapabilityStatus.BLOCKED
                        else None
                    )
                    return truth, item.confidence, tuple((*item.proof_refs, *item.evidence_refs))
                if callable(self.external_leaf_resolver):
                    resolved = self.external_leaf_resolver(
                        node=node,
                        holder_ref=holder_ref,
                        context_ref=context_ref,
                        permission_ref=permission_ref,
                        store=store,
                    )
                    if resolved is not None:
                        return resolved
                return None, 0.0, ()

            assessment = self.evaluator.evaluate(
                graph, holder_ref=holder_ref, resolve_leaf=resolve_leaf
            )
            memo[key] = assessment
            return assessment

        for graph in sorted(graphs, key=lambda item: item.authority_pin.key):
            for holder_ref in holders_for(graph):
                assessment = evaluate_graph(graph, holder_ref)
                if assessment is None:
                    continue
                assessments.append(assessment)
                frontiers.extend(assessment.frontier_refs)
                prior = current_capability_instances(holder_ref, graph.action_schema_pin)
                if len(prior) > 1:
                    frontiers.append(
                        "frontier:capability:multiple-active-instances:" + graph.graph_ref + ":" + holder_ref
                    )
                    continue
                prior_status = None if not prior else prior[0].status
                if prior_status is assessment.status:
                    continue
                deltas.append(CapabilityDeltaV351(
                    delta_ref="capability-delta:" + semantic_fingerprint(
                        "capability-delta-v351",
                        (
                            graph.authority_pin.key,
                            holder_ref,
                            None if prior_status is None else prior_status.value,
                            assessment.status.value,
                            assessment.assessment_ref,
                        ),
                        32,
                    ),
                    graph_pin=graph.authority_pin,
                    holder_ref=holder_ref,
                    action_schema_pin=graph.action_schema_pin,
                    prior_status=prior_status,
                    new_status=assessment.status,
                    confidence=assessment.support,
                    context_ref=context_ref,
                    proof_refs=(assessment.assessment_ref, *assessment.proof_refs),
                    frontier_refs=assessment.frontier_refs,
                ))
        return tuple(assessments), tuple(deltas), tuple(sorted(set(frontiers)))

    def _resolve_state_leaf(self, store, holder_ref, context_ref, requirement):
        if requirement is None:
            return None, 0.0, ()
        dimension_stored = store.get_record(
            RecordKind.SCHEMA,
            requirement.dimension_pin.ref,
            requirement.dimension_pin.revision,
        )
        if dimension_stored is None or not isinstance(
            dimension_stored.payload, StateDimensionSchema
        ):
            return None, 0.0, ()
        dimension = dimension_stored.payload
        domain = StateDomainCompilerV351.compile(dimension)
        candidates = tuple(
            item.payload
            for item in store.records(RecordKind.STATE_ASSIGNMENT)
            if isinstance(item.payload, StateAssignment)
            and item.payload.status is AssignmentStatus.ACTIVE
            and item.payload.holder_ref == holder_ref
            and item.payload.dimension_ref == requirement.dimension_pin.ref
            and item.payload.dimension_revision == requirement.dimension_pin.revision
            and item.payload.context_ref in {"global", context_ref}
        )
        # Rich v3.5.1 state represents multi-valued relations/sets inside one typed value.
        # Multiple ACTIVE assignments for the same exact holder/dimension/context are therefore
        # ambiguous regardless of the legacy `exclusive` flag; never pick by storage order.
        exact = tuple(item for item in candidates if item.context_ref == context_ref)
        fallback = tuple(item for item in candidates if item.context_ref == "global")
        selected = exact if exact else fallback
        if len(selected) > 1:
            return None, 0.0, ()
        current = None if not selected else selected[0]
        if requirement.operator is ConditionOperatorV351.KNOWN:
            return current is not None, 1.0 if current is not None else 0.0, (
                () if current is None else tuple((*current.proof_refs, *current.evidence_refs))
            )
        if requirement.operator is ConditionOperatorV351.UNKNOWN:
            return current is None, 1.0 if current is None else 0.0, (
                () if current is None else tuple((*current.proof_refs, *current.evidence_refs))
            )
        if current is None:
            return None, 0.0, ()
        try:
            value = (
                state_value_from_document(current.value_document)
                if getattr(current, "value_document", {})
                else EntitledStateSpaceCompilerV351.assignment_value(
                    current, dimension, store=store
                )
            )
            self.algebra.validate_value(domain, value)
            if requirement.expected_value is not None:
                expected_domain = (
                    self.algebra._support_domain(domain)
                    if requirement.operator is ConditionOperatorV351.PROBABILITY_AT_LEAST
                    else domain
                )
                self.algebra.validate_value(expected_domain, requirement.expected_value)
        except Exception:
            return None, 0.0, ()

        truth = None
        if requirement.operator is ConditionOperatorV351.EQUALS:
            truth = value.value_ref == requirement.expected_value.value_ref
        elif requirement.operator is ConditionOperatorV351.NOT_EQUALS:
            truth = value.value_ref != requirement.expected_value.value_ref
        elif requirement.operator is ConditionOperatorV351.CONTAINS:
            truth = requirement.expected_member_ref in set(value.set_members)
        elif requirement.operator is ConditionOperatorV351.NOT_CONTAINS:
            truth = requirement.expected_member_ref not in set(value.set_members)
        elif requirement.operator is ConditionOperatorV351.PROBABILITY_AT_LEAST:
            if value.domain_kind.value != "probabilistic" or requirement.expected_value is None:
                truth = None
            else:
                mass = sum(
                    item.probability
                    for item in value.probability_mass
                    if item.support_value.value_ref == requirement.expected_value.value_ref
                )
                truth = mass >= float(requirement.numeric_threshold)
        elif requirement.operator in {
            ConditionOperatorV351.GREATER_THAN,
            ConditionOperatorV351.GREATER_EQUAL,
            ConditionOperatorV351.LESS_THAN,
            ConditionOperatorV351.LESS_EQUAL,
        }:
            expected = requirement.expected_value
            if expected is None:
                if domain.kind.value != "continuous" or domain.unit_pin is not None:
                    # Bare numeric thresholds are permitted only for exact dimensionless scalars.
                    truth = None
                else:
                    expected = StateValueV351(
                        domain_kind=domain.kind, scalar_value=float(requirement.numeric_threshold)
                    )
            if expected is not None:
                try:
                    comparison = self.algebra.compare(domain, value, expected)
                except StateModelError:
                    truth = None
                else:
                    checks = {
                        ConditionOperatorV351.GREATER_THAN: comparison > 0,
                        ConditionOperatorV351.GREATER_EQUAL: comparison >= 0,
                        ConditionOperatorV351.LESS_THAN: comparison < 0,
                        ConditionOperatorV351.LESS_EQUAL: comparison <= 0,
                    }
                    truth = checks[requirement.operator]
        return (
            truth,
            current.confidence,
            tuple(sorted(set((*current.proof_refs, *current.evidence_refs)))),
        )


__all__ = [
    "CapabilityAssessmentV351",
    "CapabilityDeltaV351",
    "CapabilityDependencyEvaluatorV351",
    "CapabilityDependencyGraph",
    "CapabilityDependencyNodeV351",
    "CapabilityDependencyRuntimeV351",
    "CapabilityNodeKind",
    "CapabilityStateRequirementV351",
]
