"""Expression-only R3 cognition owners.

QUERY evaluates bounded root graphs with explicit unsupported constraints;
flat fact matching is not a complete typed proposition query engine. Some links
still use conjunction-like evidence checks, not full relationship proofs.
OBSERVE separates attributed occurrence from signed simple-state admission.
REQUEST requires an eligible root, reviewed transition and state preconditions;
SIMULATE previews eligible transitions without asserting current executability.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from threading import Lock
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .authority import LinkedAuthority
from .canonical import stable_ref
from .config import RuntimeConfig
from .descriptions import (
    DESCRIPTION_MAX_DEPTH,
    DESCRIPTION_MAX_REFS,
    DescriptionCompleteness,
    DescriptionRequest,
    DescriptionResult,
)
from .cycle import SemanticMode
from .decision import Decision, DecisionAction, DecisionContribution, DecisionStatus
from .expression_projection import ExpressionProjection, project_expression
from .expression_transform import instantiate_bindings, negate_expression
from .gaps import BudgetExhausted
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionBounds,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    UnresolvedValue,
    VariableBinder,
)
from .persistence import (
    Fact,
    NormalizedApplicationClaim,
    RevisionPin,
    SemanticStores,
    StaleRevisionError,
    _normalized_application_payload,
    _normalized_fact_corresponds,
    _normalized_generic_lineage_corresponds,
)
from .r3_artifacts import (
    AdmissionDecision,
    AdmissionStatus,
    CapabilityEvaluation,
    CapabilityStatus,
    ClaimOccurrence,
    EffectIntent,
    EvaluationBundle,
    LearningDraft,
    ModeEvaluation,
    PlacementMode,
    ProofGraph,
    ProofNode,
    QueryResult,
    QueryStatus,
    StateDelta,
    StateQueryResult,
    TransitionEvaluation,
    TransitionStatus,
)
from .r3_persistence import active_application_claims_for_target
from .proof_bundle import ProofBundle, _bundle_for_description
from .situation import SituationContext

__all__ = [
    "QueryDecisionOwner",
    "ObserveDecisionOwner",
    "RequestDecisionOwner",
    "SimulateDecisionOwner",
    "R3EvaluationOwner",
]


@dataclass(frozen=True)
class _FactView:
    fact_ref: str
    operator: str
    predicate_ref: str
    roles: tuple[tuple[str, str], ...]
    stance: str
    placement: str
    source_refs: tuple[str, ...]
    rule_ref: str | None = None
    premise_fact_refs: tuple[str, ...] = ()
    substitutions: tuple[tuple[str, str], ...] = ()


_WORLD_PLACEMENTS = frozenset({PlacementMode.OBSERVED.value, "reviewed"})
_SINGLE_PARENT_DAG_ERROR = "every non-root node must have exactly one parent"
_DESCRIPTION_RESULT_BUDGET_ERRORS = frozenset({
    "answer expression exceeds request max_depth",
    "fact_refs exceeds Description ABI bound",
    "definition_refs exceeds Description ABI bound",
    "claim_refs exceeds Description ABI bound",
    "source_refs exceeds Description ABI bound",
    "proof_refs exceeds Description ABI bound",
})

_DESCRIPTION_METADATA_ROLES = {
    "op:designation": frozenset({"role:label_type", "role:surface"}),
    "op:type": frozenset({"role:class", "role:type"}),
    "op:relation": frozenset({"role:relation"}),
    "op:state": frozenset({"role:dimension", "role:value"}),
    "op:event": frozenset({"role:event", "role:type"}),
}


def _source_selects_description_target(
    expression: SemanticExpression | NormalizedApplicationClaim, target_ref: str
) -> bool:
    """Whether a query or authenticated claim has nonmetadata target focus."""
    return any(
        binding.role_ref not in _DESCRIPTION_METADATA_ROLES[application.operator]
        and isinstance(binding.filler, GroundedReference)
        and binding.filler.target_ref == target_ref
        for application in expression.applications
        for binding in application.roles
    )


def _description_claim_payload(claim: Any) -> dict[str, Any]:
    return {
        "application_ref": claim.application_ref,
        "stance": claim.stance,
        "fact_ref": claim.fact_ref,
        "source_ref": claim.source_ref,
        "decision_ref": claim.decision_ref,
        "occurrence_ref": claim.occurrence_ref,
        "placement": claim.placement,
        "placement_ref": claim.placement_ref,
        "proof_refs": list(claim.proof_refs),
        "authority_generation": claim.authority_generation,
        "confidence_micros": claim.confidence_micros,
        "asserted_world_revision": claim.asserted_world_revision,
        "commit_transaction_ref": claim.commit_transaction_ref,
    }


def _verify_description_claim(
    stores: SemanticStores, claim: Any, pin: RevisionPin
) -> None:
    """Authenticate a generic normalized claim from one keyed pinned read."""
    if (
        claim.active is not True
        or claim.authority_generation != pin.authority_generation
        or not claim.applications
    ):
        raise ValueError("description claim lineage is invalid")
    root = next(
        (
            application
            for application in claim.applications
            if application.application_ref == claim.application_ref
        ),
        None,
    )
    if root is None:
        raise ValueError("description claim root is missing")
    fact, revision, transaction_ref = stores.r3_world_fact_lineage(
        claim.fact_ref, expected_pin=pin
    )
    if not _normalized_fact_corresponds(
        fact, _normalized_application_payload(root), claim.stance
    ):
        raise ValueError("description claim projection is missing or changed")
    # Authenticated alias publications have a distinct, receipt-bound lineage.
    # This generic builder does not yet reconstruct that lineage, so it rejects
    # the claim rather than treating it as a generic reviewed definition.
    if (
        fact.proof.get("publication_key") is not None
        or not _normalized_generic_lineage_corresponds(
            fact, _description_claim_payload(claim)
        )
        or revision != claim.asserted_world_revision
        or transaction_ref != claim.commit_transaction_ref
    ):
        raise ValueError("description claim lineage is invalid")


def _budget_exhausted_description(request: DescriptionRequest) -> DescriptionResult:
    """Return the ABI's lossless terminal outcome for a bounded reconstruction."""
    return DescriptionResult.create(
        request=request,
        answer_expression=None,
        completeness=DescriptionCompleteness.BUDGET_EXHAUSTED,
        fact_refs=(),
        definition_refs=(),
        claim_refs=(),
        source_refs=(),
        proof_refs=(),
        revision_pin=request.revision_pin,
    )


def _query_fact_view(fact: Fact) -> _FactView:
    """QUERY-only projection: do not change the shared transition reader."""
    if type(fact.stance) is not str or fact.stance not in {"support", "deny"}:
        raise BudgetExhausted("query fact stance is invalid", 256)
    proof = fact.proof
    rule = proof.get("rule_ref")
    premises = proof.get("premise_fact_refs", ())
    sources = proof.get("source_refs", ())
    substitutions = proof.get("substitutions", ())
    if (type(premises) not in {tuple, list} or type(sources) not in {tuple, list}
            or type(substitutions) not in {tuple, list}
            or len(premises) > 256 or len(sources) > 256 or len(substitutions) > 256
            or any(type(ref) is not str or not ref for ref in (*premises, *sources))
            or rule is not None and (type(rule) is not str or not rule)
            or any(type(row) not in {tuple, list} or len(row) != 2
                or any(type(v) is not str or not v for v in row) for row in substitutions)
            or (fact.derived or "rule_ref" in proof or "premise_fact_refs" in proof
                or "substitutions" in proof) and (not rule or not premises)):
        raise BudgetExhausted("query fact proof is incomplete or invalid", 256)
    source = proof.get("source")
    if source is not None and (type(source) is not str or not source):
        raise BudgetExhausted("query fact source is invalid", 256)
    return _FactView(fact.fact_ref, fact.operator, str(fact.args.get("predicate_ref", fact.operator)),
        tuple(sorted((str(k), _string_value(v)) for k, v in fact.args.items() if k != "predicate_ref")),
        fact.stance, str(proof.get("placement", PlacementMode.OBSERVED.value)),
        tuple(dict.fromkeys((*sources, *((source,) if source else ())))), rule,
        tuple(premises), tuple(tuple(row) for row in substitutions))


def _premise_placement(parents: tuple[_FactView, ...]) -> str | None:
    placements = {parent.placement for parent in parents}
    if placements and placements <= _WORLD_PLACEMENTS:
        return PlacementMode.OBSERVED.value
    if len(placements) == 1:
        return next(iter(placements))
    return None


@dataclass(frozen=True)
class _Solution:
    bindings: tuple[tuple[str, str], ...]
    fact_refs: tuple[str, ...]


@dataclass(frozen=True)
class _NodeResult:
    status: QueryStatus
    support: tuple[_Solution, ...] = ()
    oppose: tuple[_Solution, ...] = ()
    rounds: int = 1
    truncated: bool = False
    blockers: tuple[str, ...] = ()


def _string_value(value: object) -> str:
    if type(value) is bool:
        return "true" if value else "false"
    return str(value)


def _world_facts(stores: SemanticStores) -> tuple[Fact, ...]:
    method = getattr(stores, "r3_world_facts", None)
    if not callable(method):
        raise TypeError("SemanticStores lacks the public r3_world_facts API")
    rows = method()
    if type(rows) is not tuple or any(type(row) is not Fact for row in rows):
        raise TypeError("r3_world_facts returned non-canonical facts")
    return rows


def _fact_views(stores: SemanticStores) -> tuple[_FactView, ...]:
    result: list[_FactView] = []
    for fact in _world_facts(stores):
        args = dict(fact.args)
        predicate = str(args.pop("predicate_ref", fact.operator))
        proof = dict(fact.proof)
        source = proof.get("source")
        sources = tuple(str(item) for item in proof.get("source_refs", ()) if item)
        if source:
            sources = tuple(dict.fromkeys((*sources, str(source))))
        result.append(
            _FactView(
                fact_ref=fact.fact_ref,
                operator=fact.operator,
                predicate_ref=predicate,
                roles=tuple(sorted((str(key), _string_value(value)) for key, value in args.items())),
                stance=fact.stance,
                placement=str(proof.get("placement", "observed")),
                source_refs=sources,
                rule_ref=proof.get("rule_ref"),
                premise_fact_refs=tuple(proof.get("premise_fact_refs", ())),
                substitutions=tuple(tuple(row) for row in proof.get("substitutions", ())),
            )
        )
    return tuple(result)


def _authority_control_fact_views(
    expression: SemanticExpression,
    authority: Any,
    maximum: int,
) -> tuple[_FactView, ...]:
    """Expose exact reviewed participant-control facts used by control queries."""
    atoms = getattr(authority, "atoms", None)
    capabilities = getattr(authority, "capabilities", None)
    generation = getattr(authority, "generation", None)
    # Reviewed query-only authority fixtures may own rules without owning the
    # independent participant-control plane. Absence of that whole plane
    # contributes no control facts; a partially present plane remains invalid.
    if atoms is None and capabilities is None and generation is None:
        return ()
    if (
        not isinstance(atoms, Mapping)
        or not isinstance(capabilities, Mapping)
        or type(generation) is not str
    ):
        raise TypeError("authority lacks exact control indexes and generation")
    rows: list[_FactView] = []
    for app in expression.applications:
        atom = atoms.get(app.predicate_ref)
        if app.operator != "op:relation" or getattr(atom, "kind", None) != "capability":
            continue
        roles = {binding.role_ref: binding.filler for binding in app.roles}
        subject = roles.get("role:subject")
        if not isinstance(subject, GroundedReference):
            continue
        allowed = capabilities.get(subject.target_ref, ())
        if app.predicate_ref not in allowed:
            continue
        material = {
            "authority_generation": generation,
            "operator": app.operator,
            "predicate_ref": app.predicate_ref,
            "roles": [["role:subject", subject.target_ref]],
        }
        rows.append(
            _FactView(
                fact_ref=stable_ref("r3_authority_control_fact", material),
                operator=app.operator,
                predicate_ref=app.predicate_ref,
                roles=(("role:subject", subject.target_ref),),
                stance="support",
                placement="reviewed",
                source_refs=(generation, app.predicate_ref, subject.target_ref),
            )
        )
        if len(rows) >= maximum:
            break
    return tuple(rows)


def _filler_value(binding: RoleBinding) -> str | None:
    filler = binding.filler
    if isinstance(filler, GroundedReference):
        return filler.target_ref
    if isinstance(filler, LiteralValue):
        return _string_value(filler.value)
    if isinstance(filler, BoundVariable):
        return filler.variable_ref
    if isinstance(filler, ApplicationFiller):
        return filler.node_ref
    return None


def _pattern(app: SemanticApplication) -> tuple[tuple[str, str | BoundVariable], ...]:
    rows: list[tuple[str, str | BoundVariable]] = []
    for binding in (*app.roles, *app.qualifiers):
        value = _filler_value(binding)
        if value is not None:
            rows.append((binding.role_ref, binding.filler if isinstance(binding.filler, BoundVariable) else value))
    return tuple(sorted(rows, key=lambda row: row[0]))


def _merge_bindings(*rows: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...] | None:
    merged: dict[str, str] = {}
    for group in rows:
        for key, value in group:
            existing = merged.get(key)
            if existing is not None and existing != value:
                return None
            merged[key] = value
    return tuple(sorted(merged.items()))


def _match(pattern: tuple[tuple[str, str | BoundVariable], ...], fact: _FactView) -> tuple[tuple[str, str], ...] | None:
    roles = dict(fact.roles)
    bindings: dict[str, str] = {}
    for role, expected in pattern:
        actual = roles.get(role)
        if actual is None:
            return None
        if isinstance(expected, BoundVariable):
            previous = bindings.get(expected.variable_ref)
            if previous is not None and previous != actual:
                return None
            bindings[expected.variable_ref] = actual
        elif expected != actual:
            return None
    return tuple(sorted(bindings.items()))


def _clause_parts(clause: object) -> tuple[str, str, tuple[tuple[str, str], ...], str] | None:
    if not isinstance(clause, Mapping):
        return None
    operator = clause.get("operator")
    args = clause.get("args")
    if type(operator) is not str or not isinstance(args, Mapping):
        return None
    predicate = args.get("predicate_ref", clause.get("predicate", operator))
    if type(predicate) is not str:
        return None
    roles = tuple(sorted((str(k), str(v)) for k, v in args.items() if k != "predicate_ref"))
    stance = clause.get("stance", "support")
    if type(stance) is not str or stance not in {"support", "deny"}:
        return None
    return operator, predicate, roles, stance


def _unify_rule(pattern: tuple[tuple[str, str], ...], fact: _FactView,
                env: Mapping[str, str]) -> dict[str, str] | None:
    roles = dict(fact.roles)
    result = dict(env)
    for role, expected in pattern:
        actual = roles.get(role)
        if actual is None:
            return None
        if expected.startswith("?"):
            prior = result.get(expected)
            if prior is not None and prior != actual:
                return None
            result[expected] = actual
        elif expected != actual:
            return None
    return result


def _rule_closure(
    facts: tuple[_FactView, ...], rules: tuple[Any, ...], config: RuntimeConfig
) -> tuple[tuple[_FactView, ...], tuple[str, ...], int, bool]:
    known = {row.fact_ref: row for row in facts}
    probed: list[str] = []
    rounds = 0
    truncated = False
    added = False
    for round_index in range(config.max_inference_rounds):
        rounds = round_index + 1
        added = False
        current = tuple(known.values())
        for rule in rules:
            probed.append(rule.rule_ref)
            states: list[tuple[dict[str, str], tuple[_FactView, ...]]] = [({}, ())]
            valid = True
            for raw_clause in rule.antecedent:
                parsed = _clause_parts(raw_clause)
                if parsed is None:
                    valid = False
                    break
                operator, predicate, pattern, stance = parsed
                next_states: list[tuple[dict[str, str], tuple[_FactView, ...]]] = []
                for env, parents in states:
                    for fact in current:
                        if fact.operator != operator or fact.predicate_ref != predicate or fact.stance != stance:
                            continue
                        matched = _unify_rule(pattern, fact, env)
                        if matched is not None:
                            if parents and _premise_placement((*parents, fact)) is None:
                                continue
                            next_states.append((matched, (*parents, fact)))
                            if len(next_states) > config.max_inference_facts:
                                truncated = True
                                break
                    if truncated:
                        break
                states = next_states
                if not states or truncated:
                    break
            if not valid or truncated:
                truncated = True
                break
            for env, parents in states:
                for raw_clause in rule.consequent:
                    parsed = _clause_parts(raw_clause)
                    if parsed is None:
                        truncated = True
                        break
                    operator, predicate, role_rows, stance = parsed
                    roles: list[tuple[str, str]] = []
                    for role, raw in role_rows:
                        value = env.get(raw, raw) if raw.startswith("?") else raw
                        if value.startswith("?"):
                            truncated = True
                            break
                        roles.append((role, value))
                    if truncated:
                        break
                    placement = _premise_placement(parents)
                    if placement is None:
                        truncated = True
                        break
                    material = {
                        "operator": operator,
                        "predicate_ref": predicate,
                        "roles": roles,
                        "stance": stance,
                        "rule_ref": rule.rule_ref,
                        "premises": [row.fact_ref for row in parents],
                        "substitutions": sorted(env.items()),
                        "placement": placement,
                    }
                    ref = stable_ref("r3_derived_fact", material)
                    candidate = _FactView(
                            ref, operator, predicate, tuple(sorted(roles)), stance,
                            placement, tuple(dict.fromkeys((rule.source_ref,
                                *(ref for parent in parents for ref in parent.source_refs)
                            ))), rule.rule_ref, tuple(parent.fact_ref for parent in parents),
                            tuple(sorted(env.items())),
                        )
                    if ref not in known:
                        if len(known) >= config.max_inference_facts:
                            truncated = True
                            break
                        known[ref] = candidate
                        added = True
                if truncated:
                    break
            if truncated:
                break
        if truncated or not added:
            break
    if added and rounds == config.max_inference_rounds:
        truncated = True
    return tuple(known[ref] for ref in sorted(known)), tuple(dict.fromkeys(probed)), rounds, truncated


def _proof(selected: tuple[_FactView, ...], all_facts: Mapping[str, _FactView],
           bindings: tuple[tuple[str, str], ...], pin: RevisionPin) -> ProofGraph | None:
    if not selected:
        return None
    nodes: dict[str, ProofNode] = {}
    by_fact: dict[str, str] = {}
    visiting: set[str] = set()

    def build(fact: _FactView) -> str:
        if fact.fact_ref in by_fact:
            return by_fact[fact.fact_ref]
        if fact.fact_ref in visiting:
            raise ValueError("proof fact dependency cycle")
        visiting.add(fact.fact_ref)
        if fact.rule_ref is None:
            node = ProofNode.create(
                conclusion_ref=fact.fact_ref,
                source_fact_refs=(fact.fact_ref,),
                rule_ref=None,
                premise_node_refs=(),
                substitutions=bindings,
                revision_pin=pin,
            )
        else:
            premises = tuple(build(all_facts[ref]) for ref in fact.premise_fact_refs)
            node = ProofNode.create(
                conclusion_ref=fact.fact_ref,
                source_fact_refs=(),
                rule_ref=fact.rule_ref,
                premise_node_refs=premises,
                substitutions=fact.substitutions or bindings,
                revision_pin=pin,
            )
        visiting.remove(fact.fact_ref)
        nodes[node.proof_node_ref] = node
        by_fact[fact.fact_ref] = node.proof_node_ref
        return node.proof_node_ref

    roots = tuple(build(row) for row in selected)
    involved = tuple(all_facts[ref] for ref in by_fact)
    return ProofGraph.create(
        root_node_refs=roots,
        nodes=tuple(nodes[ref] for ref in sorted(nodes)),
        semantic_refs=tuple(sorted({row.predicate_ref for row in involved})),
        source_refs=tuple(sorted({ref for row in involved for ref in row.source_refs})),
        rule_refs=tuple(sorted({row.rule_ref for row in involved if row.rule_ref})),
        transient_witness_refs=tuple(sorted(value for key, value in bindings if key.startswith("?exists"))),
        revision_pin=pin,
    )


def _status(support: tuple[_Solution, ...], oppose: tuple[_Solution, ...], *, truncated: bool = False) -> QueryStatus:
    if truncated:
        return QueryStatus.BUDGET_EXHAUSTED
    if support and oppose:
        return QueryStatus.CONFLICT
    if support:
        return QueryStatus.SUPPORTED
    if oppose:
        return QueryStatus.CONTRADICTED
    return QueryStatus.BUDGET_EXHAUSTED if truncated else QueryStatus.UNKNOWN


def _invert(result: _NodeResult) -> _NodeResult:
    status = {
        QueryStatus.SUPPORTED: QueryStatus.CONTRADICTED,
        QueryStatus.CONTRADICTED: QueryStatus.SUPPORTED,
        QueryStatus.CONFLICT: QueryStatus.CONFLICT,
        QueryStatus.UNKNOWN: QueryStatus.UNKNOWN,
        QueryStatus.PARTIAL: QueryStatus.PARTIAL,
        QueryStatus.BUDGET_EXHAUSTED: QueryStatus.BUDGET_EXHAUSTED,
    }[result.status]
    return _NodeResult(status, result.oppose, result.support, result.rounds, result.truncated, result.blockers)


def _and(results: tuple[_NodeResult, ...], maximum: int) -> _NodeResult:
    if not results:
        return _NodeResult(QueryStatus.UNKNOWN, blockers=("query:empty_conjunction",))
    blockers = tuple(dict.fromkeys(ref for row in results for ref in row.blockers))
    if any(row.truncated or row.status is QueryStatus.BUDGET_EXHAUSTED for row in results):
        return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True, blockers=(*blockers, "query:budget"))
    if any(row.status is QueryStatus.CONFLICT for row in results):
        conflicts = tuple(row for row in results if row.status is QueryStatus.CONFLICT)
        return _NodeResult(
            QueryStatus.CONFLICT,
            support=tuple(solution for row in conflicts for solution in row.support)[:maximum],
            oppose=tuple(solution for row in conflicts for solution in row.oppose)[:maximum],
            blockers=(*blockers, "query:conjunct_conflict"),
        )
    if any(row.status is QueryStatus.BUDGET_EXHAUSTED for row in results):
        return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True, blockers=(*blockers, "query:budget"))
    if any(row.status is QueryStatus.PARTIAL for row in results):
        return _NodeResult(QueryStatus.PARTIAL, blockers=(*blockers, "query:partial_conjunct"))
    if any(row.status is QueryStatus.UNKNOWN for row in results):
        return _NodeResult(QueryStatus.UNKNOWN, blockers=(*blockers, "query:unknown_conjunct"))
    if any(row.status is QueryStatus.CONTRADICTED for row in results):
        oppose = tuple(solution for row in results for solution in row.oppose)[:maximum]
        return _NodeResult(QueryStatus.CONTRADICTED, oppose=oppose)
    solutions: list[_Solution] = [_Solution((), ())]
    for row in results:
        next_rows: list[_Solution] = []
        for left, right in product(solutions, row.support):
            bindings = _merge_bindings(left.bindings, right.bindings)
            if bindings is not None:
                next_rows.append(_Solution(bindings, tuple(dict.fromkeys((*left.fact_refs, *right.fact_refs)))))
                if len(next_rows) > maximum:
                    return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True)
        solutions = next_rows
        if not solutions:
            # No shared witness is not evidence against a proposition. Full
            # multi-answer projection remains separate from conflict proof.
            return _NodeResult(QueryStatus.UNKNOWN, blockers=("query:no_joint_binding",))
    return _NodeResult(QueryStatus.SUPPORTED, support=tuple(solutions))


def _or(results: tuple[_NodeResult, ...], maximum: int) -> _NodeResult:
    if (any(row.truncated or row.status is QueryStatus.BUDGET_EXHAUSTED for row in results)
            or sum(len(row.support) + len(row.oppose) for row in results) > maximum):
        return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True)
    support = tuple(solution for row in results for solution in row.support)[:maximum]
    oppose = tuple(solution for row in results for solution in row.oppose)[:maximum]
    if support:
        # Disjunction is supported when any alternative is supported; opposing
        # alternatives do not make it a conflict.
        return _NodeResult(QueryStatus.SUPPORTED, support=support)
    if results and all(row.status is QueryStatus.CONTRADICTED for row in results):
        return _NodeResult(QueryStatus.CONTRADICTED, oppose=oppose)
    if any(row.status is QueryStatus.BUDGET_EXHAUSTED for row in results):
        return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True)
    if any(row.status is QueryStatus.PARTIAL for row in results):
        return _NodeResult(QueryStatus.PARTIAL)
    return _NodeResult(QueryStatus.UNKNOWN)


_SCOPE_PLACEMENTS = {
    ("scope:simulation", "scope_value:simulation:hypothetical"): PlacementMode.SIMULATED,
    ("scope:simulation", "scope_value:simulation:counterfactual"): PlacementMode.SIMULATED,
    ("scope:quotation", "scope_value:quotation:direct"): PlacementMode.QUOTED,
    ("scope:attribution", "scope_value:attribution:reported"): PlacementMode.REPORTED,
    ("scope:epistemic", "scope_value:epistemic:belief"): PlacementMode.BELIEVED,
    ("scope:epistemic", "scope_value:epistemic:desire"): PlacementMode.DESIRED,
    ("scope:epistemic", "scope_value:epistemic:prediction"): PlacementMode.PREDICTED,
}
_NEGATIVE_POLARITY = frozenset({"scope_value:polarity:negative", "polarity:negative"})
_POSITIVE_POLARITY = frozenset({"scope_value:polarity:positive", "polarity:positive"})


class _RecursiveQueryEvaluator:
    def __init__(self, expression: SemanticExpression, projection: ExpressionProjection,
                 facts: tuple[_FactView, ...], config: RuntimeConfig,
                 allowed_placements: frozenset[str] | None = None,
                 designation_blockers: tuple[str, ...] = ()) -> None:
        self.expression = expression
        self.projection = projection
        self.facts = facts
        self.fact_by_ref = {row.fact_ref: row for row in facts}
        self.config = config
        self.allowed_placements = allowed_placements
        self.designation_blockers = designation_blockers
        self.memo: dict[tuple[str, frozenset[str] | None], _NodeResult] = {}

    def evaluate(self, ref: str, allowed: frozenset[str] | None = None) -> _NodeResult:
        allowed = self.allowed_placements if allowed is None else allowed
        key = (ref, allowed)
        if key in self.memo:
            return self.memo[key]
        node = self.projection.node_by_ref[ref]
        if isinstance(node, SemanticApplication):
            result = self._application(node, allowed)
        elif isinstance(node, ScopeOperator):
            result = self._scope(node, allowed)
        elif isinstance(node, ExpressionLink):
            result = self._link(node, allowed)
        elif isinstance(node, VariableBinder):
            result = self.evaluate(node.body_ref, allowed)
        else:  # pragma: no cover
            raise TypeError("unknown expression node")
        self.memo[key] = result
        return result

    def _application(self, app: SemanticApplication, allowed: frozenset[str] | None) -> _NodeResult:
        blockers: list[str] = []
        if app.operator == "op:designation":
            if any(isinstance(row.filler, BoundVariable) for row in app.roles) and not _lexical_target_application(app):
                blockers.append("query:designation_projection_unsupported")
            blockers.extend(self.designation_blockers)
        for binding in (*app.roles, *app.qualifiers):
            if isinstance(binding.filler, UnresolvedValue):
                blockers.extend(("query:unresolved_constraint", binding.filler.unresolved_ref, binding.role_ref))
            elif isinstance(binding.filler, ApplicationFiller):
                blockers.extend(("query:proposition_constraint", binding.filler.node_ref, binding.role_ref))
        if blockers:
            # Candidate-local application IDs are not persisted proposition
            # identities, and an unresolved role is not a missing constraint.
            return _NodeResult(QueryStatus.PARTIAL, blockers=tuple(dict.fromkeys(blockers)))
        pattern = _pattern(app)
        support: list[_Solution] = []
        oppose: list[_Solution] = []
        for fact in self.facts[: self.config.max_inference_facts]:
            if fact.operator != app.operator or fact.predicate_ref != app.predicate_ref:
                continue
            if allowed is not None and fact.placement not in allowed:
                continue
            bindings = _match(pattern, fact)
            if bindings is None:
                continue
            row = _Solution(bindings, (fact.fact_ref,))
            (support if fact.stance == "support" else oppose).append(row)
        if support and oppose and len({row.bindings for row in (*support, *oppose)}) > 1:
            # The single-result ABI cannot express support and denial for
            # different substitutions as one unqualified conflict.
            return _NodeResult(QueryStatus.PARTIAL, blockers=("query:multi_binding_projection_unsupported",))
        return _NodeResult(_status(tuple(support), tuple(oppose)), tuple(support), tuple(oppose))

    def _scope(self, scope: ScopeOperator, allowed: frozenset[str] | None) -> _NodeResult:
        if scope.operator_type == "scope:polarity":
            result = self.evaluate(scope.operand_ref, allowed)
            if scope.value_ref in _NEGATIVE_POLARITY:
                return _invert(result)
            if scope.value_ref in _POSITIVE_POLARITY:
                return result
            return _NodeResult(QueryStatus.PARTIAL, blockers=("scope:unknown_polarity",))
        placement = _SCOPE_PLACEMENTS.get((scope.operator_type, scope.value_ref))
        if placement is not None:
            if placement is PlacementMode.SIMULATED:
                return _NodeResult(QueryStatus.PARTIAL, blockers=("query:simulated_not_actual",))
            return self.evaluate(scope.operand_ref, frozenset({placement.value}))
        if scope.operator_type == "scope:modality":
            return _NodeResult(QueryStatus.PARTIAL, blockers=("query:modal_not_actual",))
        if scope.operator_type in {"scope:tense", "scope:aspect"}:
            return self.evaluate(scope.operand_ref, allowed)
        return _NodeResult(QueryStatus.PARTIAL, blockers=("scope:unsupported",))

    def _link(self, link: ExpressionLink, allowed: frozenset[str] | None) -> _NodeResult:
        rows = tuple(self.evaluate(ref, allowed) for ref in link.operand_refs)
        if any(row.truncated or row.status is QueryStatus.BUDGET_EXHAUSTED for row in rows):
            return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True)
        if link.link_type in {"link:disjunction"}:
            return _or(rows, self.config.max_inference_facts)
        if link.link_type == "link:condition":
            antecedent, consequent = rows
            if antecedent.status is QueryStatus.SUPPORTED:
                return consequent
            if antecedent.status is QueryStatus.CONTRADICTED:
                return _NodeResult(QueryStatus.SUPPORTED, support=antecedent.oppose)
            if antecedent.status is QueryStatus.CONFLICT:
                return replace(antecedent, blockers=(*antecedent.blockers, "query:condition_conflict"))
            if antecedent.status is QueryStatus.PARTIAL:
                return antecedent
            return _NodeResult(QueryStatus.UNKNOWN, blockers=(*antecedent.blockers, "query:condition_antecedent_unknown"))
        # Coordination, conjunction, cause, purpose, contrast and sequence all
        # require every ordered operand to hold. Their distinct link identity is
        # retained in the expression and proof lineage.
        return _and(rows, self.config.max_inference_facts)


def _lexical_target_application(app: SemanticApplication) -> bool:
    roles = {row.role_ref: row.filler for row in app.roles}
    return (app.operator == "op:designation" and app.predicate_ref == "label:lexical"
            and not app.qualifiers and set(roles) == {"role:label_type", "role:surface", "role:target"}
            and roles["role:label_type"] == GroundedReference(app.predicate_ref)
            and isinstance(roles["role:surface"], LiteralValue)
            and roles["role:surface"].value_type == "string"
            and isinstance(roles["role:target"], BoundVariable))


class QueryDecisionOwner:
    def __init__(self, stores: SemanticStores, config: RuntimeConfig, authority: Any,
                 *, designation_reader: Any = None) -> None:
        self._stores = stores
        self._config = config
        self._authority = authority
        from .r3_learning import AdmittedDesignationReader
        self._designation_reader = designation_reader
        if designation_reader is not None and type(designation_reader) is not AdmittedDesignationReader:
            raise TypeError("designation reader must be exact AdmittedDesignationReader")
        if designation_reader is not None and (designation_reader.authority is not authority or designation_reader.stores is not stores):
            raise ValueError("designation reader differs from query owner")
        empty = MappingProxyType({})
        self._rule_cache_state = (None, empty, empty, False)
        self._rule_index_lock = Lock()
        activation_snapshot = self._rule_generation_snapshot()
        self._refresh_rule_index(activation_snapshot)
        self._description_authority_state = (authority, activation_snapshot)

    @property
    def _rule_index_key(self):
        return self._rule_cache_state[0]

    @property
    def _reviewed_rules(self):
        return self._rule_cache_state[1]

    def _rule_generation_snapshot(self):
        if type(self._authority) is LinkedAuthority:
            return self._authority.rule_generation_snapshot()
        rules = getattr(self._authority, "rules", {})
        return (
            getattr(self._authority, "generation", None),
            getattr(self._authority, "content_hash", None),
            rules,
        )

    def _refresh_rule_index(self, snapshot=None):
        # Linked authority is generation-static. Build once at owner activation,
        # never rescan its complete rule collection in an ordinary query cycle.
        generation, content_hash, rules = (
            self._rule_generation_snapshot() if snapshot is None else snapshot
        )
        key = (generation, content_hash, id(rules))
        state = self._rule_cache_state
        if key == state[0]:
            return state[1], state[2], state[3]
        with self._rule_index_lock:
            state = self._rule_cache_state
            if key == state[0]:
                return state[1], state[2], state[3]
            if (state[0] is not None
                    and key[0] == state[0][0]
                    and key[1:] != state[0][1:]):
                raise BudgetExhausted("same-generation query rule collection drift", 256)
            reviewed_rules: dict[str, Any] = {}
            index: dict[tuple[str, str], list[Any]] = {}
            invalid = False
            for _, rule in sorted(rules.items()):
                if not getattr(rule, "reviewed", False):
                    continue
                reviewed_rules[rule.rule_ref] = rule
                for clause in rule.consequent:
                    parsed = _clause_parts(clause)
                    if parsed is None:
                        invalid = True
                    else:
                        index.setdefault(parsed[:2], []).append(rule)
            reviewed_snapshot = MappingProxyType(reviewed_rules)
            index_snapshot = MappingProxyType({
                index_key: tuple(value) for index_key, value in index.items()
            })
            self._rule_cache_state = (key, reviewed_snapshot, index_snapshot, invalid)
            return reviewed_snapshot, index_snapshot, invalid

    def describe(
        self, request: DescriptionRequest, source_expression: SemanticExpression,
        situation: SituationContext,
    ) -> DescriptionResult:
        """Reconstruct one bounded reviewed description without mutating state."""
        self._validate_description_source(request, source_expression, situation)
        with self._stores.r3_read_snapshot(request.revision_pin):
            authority = self._authority
            authority_snapshot = self._rule_generation_snapshot()
            generation, content_hash, rules = authority_snapshot
            snapshot_key = (generation, content_hash, id(rules))
            if generation != request.revision_pin.authority_generation:
                raise StaleRevisionError("description live authority generation differs from pin")
            if (self._rule_index_key[0] == generation
                    and self._rule_index_key != snapshot_key):
                raise StaleRevisionError("description same-generation authority identity drift")
            with self._rule_index_lock:
                observed_authority, observed_snapshot = self._description_authority_state
                if authority is not observed_authority:
                    raise StaleRevisionError("description authority object identity differs from activation")
                if (generation == observed_snapshot[0]
                        and (content_hash != observed_snapshot[1] or rules is not observed_snapshot[2])):
                    raise StaleRevisionError("description same-generation authority identity drift")
                if (type(authority) is LinkedAuthority and generation == observed_snapshot[0]
                        and authority_snapshot is not observed_snapshot):
                    raise StaleRevisionError("description same-generation authority snapshot identity drift")
                self._description_authority_state = (authority, authority_snapshot)
            result, _ = self._description_at_pin(request)
            current = self._rule_generation_snapshot()
            if (self._authority is not authority
                    or (current[0], current[1], id(current[2])) != snapshot_key
                    or type(authority) is LinkedAuthority and current is not authority_snapshot):
                raise StaleRevisionError("description live authority changed during pinned read")
            return result

    def describe_with_proof(
        self, request: DescriptionRequest, source_expression: SemanticExpression,
        situation: SituationContext,
    ) -> tuple[DescriptionResult, ProofBundle]:
        """Authenticate description evidence during the same indexed pinned read."""
        self._validate_description_source(request, source_expression, situation)
        with self._stores.r3_read_snapshot(request.revision_pin):
            authority = self._authority
            authority_snapshot = self._rule_generation_snapshot()
            generation, content_hash, rules = authority_snapshot
            snapshot_key = (generation, content_hash, id(rules))
            if generation != request.revision_pin.authority_generation:
                raise StaleRevisionError("description live authority generation differs from pin")
            if (self._rule_index_key[0] == generation
                    and self._rule_index_key != snapshot_key):
                raise StaleRevisionError("description same-generation authority identity drift")
            with self._rule_index_lock:
                observed_authority, observed_snapshot = self._description_authority_state
                if authority is not observed_authority:
                    raise StaleRevisionError("description authority object identity differs from activation")
                if (generation == observed_snapshot[0]
                        and (content_hash != observed_snapshot[1] or rules is not observed_snapshot[2])):
                    raise StaleRevisionError("description same-generation authority identity drift")
                if (type(authority) is LinkedAuthority and generation == observed_snapshot[0]
                        and authority_snapshot is not observed_snapshot):
                    raise StaleRevisionError("description same-generation authority snapshot identity drift")
                self._description_authority_state = (authority, authority_snapshot)
            result, claims = self._description_at_pin(request)
            if any(len(claim.proof_refs) > DESCRIPTION_MAX_REFS for claim in claims):
                result, claims = _budget_exhausted_description(request), ()
            bundle = _bundle_for_description(result, claims)
            current = self._rule_generation_snapshot()
            if (self._authority is not authority
                    or (current[0], current[1], id(current[2])) != snapshot_key
                    or type(authority) is LinkedAuthority and current is not authority_snapshot):
                raise StaleRevisionError("description live authority changed during pinned read")
            return result, bundle

    def _validate_description_source(
        self,
        request: DescriptionRequest,
        source_expression: SemanticExpression,
        situation: SituationContext,
    ) -> None:
        """Reconstruct one bounded reviewed description without mutating state."""
        if type(request) is not DescriptionRequest:
            raise TypeError("description request must be exact DescriptionRequest")
        if DescriptionRequest.from_dict(request.as_dict()) != request:
            raise ValueError("description request must be canonical")
        request.validate_source(source_expression, situation)

    def _description_at_pin(
        self, request: DescriptionRequest,
    ) -> tuple[DescriptionResult, tuple[NormalizedApplicationClaim, ...]]:
        """Return the exact result and authenticated reviewed claims at caller pin."""
        if request.requested_content == "definition":
            # No reviewed definition policy is active. A neighborhood, however
            # well supported, cannot supply defining authority.
            return DescriptionResult.create(request=request, answer_expression=None,
                completeness=DescriptionCompleteness.MISSING, fact_refs=(), definition_refs=(),
                claim_refs=(), source_refs=(), proof_refs=(), revision_pin=request.revision_pin), ()
        try:
            claims = active_application_claims_for_target(
                self._stores,
                request.target_ref,
                maximum=min(request.max_facts, DESCRIPTION_MAX_REFS),
                expected_pin=request.revision_pin,
            )
        except BudgetExhausted:
            return _budget_exhausted_description(request), ()
        for claim in claims:
            _verify_description_claim(self._stores, claim, request.revision_pin)
        # A target posting includes predicate/metadata occurrences as well as
        # descriptive roles. Authenticate the complete bounded posting first;
        # only focused reviewed claims own answer graphs and signed evidence.
        reviewed = tuple(
            claim for claim in claims
            if claim.placement == "reviewed"
            and _source_selects_description_target(claim, request.target_ref)
        )
        if not reviewed:
            return DescriptionResult.create(
                request=request,
                answer_expression=None,
                completeness=DescriptionCompleteness.MISSING,
                fact_refs=(),
                definition_refs=(),
                claim_refs=(),
                source_refs=(),
                proof_refs=(),
                revision_pin=request.revision_pin,
            ), ()
        applications_by_ref: dict[str, SemanticApplication] = {}
        for claim in reviewed:
            for application in claim.applications:
                existing = applications_by_ref.setdefault(
                    application.application_ref, application
                )
                if existing != application:
                    raise ValueError("description application identity collision")
        applications = tuple(
            applications_by_ref[ref] for ref in sorted(applications_by_ref)
        )
        roots = tuple(sorted({claim.application_ref for claim in reviewed}))
        limits = ExpressionBounds()
        if len(roots) > limits.max_roots or len(applications) > limits.max_applications:
            return _budget_exhausted_description(request), ()
        # Individually authenticated claims can overlap at a retained root.
        # Their combined answer then has no single-parent forest representation;
        # do not drop a root or weaken its independent signed evidence.
        root_set = frozenset(roots)
        if any(
            isinstance(binding.filler, ApplicationFiller)
            and binding.filler.node_ref in root_set
            for app in applications for binding in (*app.roles, *app.qualifiers)
        ):
            return _budget_exhausted_description(request), ()
        stances_by_application: dict[str, set[str]] = {}
        for claim in reviewed:
            stances_by_application.setdefault(claim.application_ref, set()).add(
                claim.stance
            )
        completeness = (
            DescriptionCompleteness.CONFLICT
            if any(
                {"support", "deny"} <= stances
                for stances in stances_by_application.values()
            )
            else DescriptionCompleteness.SUFFICIENT
        )
        try:
            answer = SemanticExpression.create(
                applications=applications,
                root_refs=roots,
                bounds=limits,
            )
        except ValueError as exc:
            if str(exc) != _SINGLE_PARENT_DAG_ERROR:
                raise
            return _budget_exhausted_description(request), ()
        try:
            return DescriptionResult.create(
                request=request,
                answer_expression=answer,
                completeness=completeness,
                fact_refs=tuple(sorted({claim.fact_ref for claim in reviewed})),
                definition_refs=roots,
                claim_refs=tuple(sorted({claim.claim_ref for claim in reviewed})),
                source_refs=tuple(sorted({claim.source_ref for claim in reviewed})),
                proof_refs=tuple(sorted({
                    proof_ref for claim in reviewed for proof_ref in claim.proof_refs
                })),
                revision_pin=request.revision_pin,
            ), reviewed
        except ValueError as exc:
            if str(exc) not in _DESCRIPTION_RESULT_BUDGET_ERRORS:
                raise
            return _budget_exhausted_description(request), ()

    def _relevant_evidence(self, expression: SemanticExpression, rule_state):
        reviewed_rules, rule_index, index_invalid = rule_state
        if index_invalid:
            raise BudgetExhausted("reviewed query dependency index is incomplete", 256)
        demands: dict[tuple[str, str], set[tuple[tuple[str, str], ...]]] = {}
        for app in expression.applications:
            constraints = tuple((role, value) for role, value in _pattern(app) if type(value) is str)
            demands.setdefault((app.operator, app.predicate_ref), set()).add(constraints)
        pending = list(demands)
        selected = {}
        visited = set()
        while pending:
            key = pending.pop()
            if key in visited:
                continue
            visited.add(key)
            if len(visited) > self._config.max_inference_facts:
                raise BudgetExhausted("query dependency demands exceed bound", 256)
            for rule in rule_index.get(key, ()):
                if rule.rule_ref in selected:
                    continue
                if len(selected) >= self._config.max_inference_rules:
                    raise BudgetExhausted("relevant reviewed rule scan exceeds bound", 256)
                if (not rule.antecedent or not rule.consequent
                        or len(rule.antecedent) > self._config.max_applications
                        or len(rule.consequent) > self._config.max_applications
                        or type(getattr(rule, "source_ref", None)) is not str or not rule.source_ref):
                    raise BudgetExhausted("relevant reviewed rule is incomplete", 256)
                selected[rule.rule_ref] = rule
                for clause in rule.antecedent:
                    parsed = _clause_parts(clause)
                    if parsed is None:
                        raise BudgetExhausted("reviewed rule premise is unsupported", 256)
                    op, pred, roles, _ = parsed
                    # Antecedent constants belong to that clause. Query constants
                    # are NOT copied: joined rules may use intermediate entities.
                    constraints = tuple((role, value) for role, value in roles if not value.startswith("?"))
                    demands.setdefault((op, pred), set()).add(constraints)
                    pending.append((op, pred))
        facts: dict[str, _FactView] = {}
        for (op, pred), constraints in sorted(demands.items()):
            for rows in sorted(constraints):
                retrieved = self._stores.r3_query_facts(op, pred, rows, maximum=self._config.max_inference_facts)
                if len(retrieved) > self._config.max_inference_facts:
                    raise BudgetExhausted("relevant fact retrieval exceeds bound", 256)
                for fact in retrieved:
                    facts[fact.fact_ref] = _query_fact_view(fact)
                    if len(facts) > self._config.max_inference_facts:
                        raise BudgetExhausted("combined relevant facts exceed bound", 256)
        return self._validated_proof_facts(facts, reviewed_rules), tuple(
            selected[ref] for ref in sorted(selected)
        )

    def _validated_proof_facts(
        self, facts: dict[str, _FactView], reviewed_rules: Mapping[str, Any]
    ) -> tuple[_FactView, ...]:
        """Bounded keyed dependencies, including premises outside query demands."""
        visiting: set[str] = set()
        verified: set[str] = set()
        def visit(ref):
            if ref in visiting:
                raise BudgetExhausted("query proof dependency cycle", 256)
            if ref in verified:
                return facts[ref]
            if ref not in facts:
                if len(facts) >= self._config.max_inference_facts:
                    raise BudgetExhausted("query proof dependency bound", 256)
                persisted = self._stores.world.get(ref)
                if persisted is None:
                    raise BudgetExhausted("query proof premise is absent", 256)
                facts[ref] = _query_fact_view(persisted)
            row = facts[ref]
            visiting.add(ref)
            if row.rule_ref is not None:
                rule = reviewed_rules.get(row.rule_ref)
                if (rule is None or len(rule.antecedent) != len(row.premise_fact_refs)
                        or len(rule.antecedent) > self._config.max_applications
                        or len(rule.consequent) > self._config.max_applications
                        or type(getattr(rule, "source_ref", None)) is not str or not rule.source_ref):
                    raise BudgetExhausted("query proof lacks its reviewed rule", 256)
                parents = tuple(visit(parent) for parent in row.premise_fact_refs)
                env = {}
                for clause, parent in zip(rule.antecedent, parents):
                    parsed = _clause_parts(clause)
                    if parsed is None or parsed[:2] != (parent.operator, parent.predicate_ref) or parsed[3] != parent.stance:
                        raise BudgetExhausted("query proof premise differs from reviewed rule", 256)
                    env = _unify_rule(parsed[2], parent, env)
                    if env is None:
                        raise BudgetExhausted("query proof premise substitution is inconsistent", 256)
                conclusions = tuple(_clause_parts(clause) for clause in rule.consequent)
                if not any(clause is not None and clause[:2] == (row.operator, row.predicate_ref)
                        and clause[3] == row.stance
                        and tuple((role, env.get(value, value)) for role, value in clause[2]) == row.roles
                        for clause in conclusions):
                    raise BudgetExhausted("query proof conclusion differs from reviewed rule", 256)
                if row.substitutions and row.substitutions != tuple(sorted(env.items())):
                    raise BudgetExhausted("query proof substitution witness differs", 256)
                placement = _premise_placement(parents)
                if placement is None or (row.placement != "derived" and row.placement != placement
                        and not {row.placement, placement} <= _WORLD_PLACEMENTS):
                    raise BudgetExhausted("query proof placement differs from premises", 256)
                row = replace(row, placement=placement, substitutions=tuple(sorted(env.items())),
                    source_refs=tuple(dict.fromkeys((rule.source_ref,
                        *(source for parent in parents for source in parent.source_refs)))))
                facts[ref] = row
            visiting.remove(ref)
            verified.add(ref)
            return row
        for ref in tuple(facts):
            visit(ref)
        return tuple(facts[ref] for ref in sorted(facts))

    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if expression.query_projections:
            if type(projection) is not ExpressionProjection or projection != project_expression(expression):
                raise ValueError("projection index differs from exact source expression")
            request = DescriptionRequest.create(source_expression=expression, situation=situation,
                max_depth=min(DESCRIPTION_MAX_DEPTH, self._config.max_graph_depth),
                max_facts=min(DESCRIPTION_MAX_REFS, self._config.max_inference_facts))
            # The existing description owner supplies the sole guarded pinned
            # read. Do not refresh proposition rules or nest a query snapshot.
            description, bundle = self.describe_with_proof(request, expression, situation)
            query_status = {
                DescriptionCompleteness.SUFFICIENT: QueryStatus.SUPPORTED,
                DescriptionCompleteness.PARTIAL: QueryStatus.PARTIAL,
                DescriptionCompleteness.CONFLICT: QueryStatus.CONFLICT,
                DescriptionCompleteness.MISSING: QueryStatus.UNKNOWN,
                DescriptionCompleteness.BUDGET_EXHAUSTED: QueryStatus.BUDGET_EXHAUSTED,
            }[description.completeness]
            result = QueryResult.create(expression_ref=expression.expression_ref,
                result_kind="projection", status=query_status, bindings=(), proof=None,
                description_proof=bundle, retrieval_refs=description.fact_refs,
                rounds=1, revision_pin=situation.revision_pin)
            decisive = query_status is QueryStatus.SUPPORTED
            budget = query_status is QueryStatus.BUDGET_EXHAUSTED
            contribution = DecisionContribution(
                status=DecisionStatus(query_status.value),
                action=DecisionAction.ANSWER if decisive else (DecisionAction.NO_OP if budget else DecisionAction.REQUEST_CLARIFICATION),
                answer_expression_ref=bundle.answer_expression_ref if decisive else None,
                bindings=(), query_result_refs=(result.query_result_ref,),
                proof_refs=(bundle.proof_bundle_ref,), source_refs=description.source_refs,
                blocker_refs=() if decisive else (f"query:{query_status.value}",),
                policy_refs=("policy:recursive_expression_query:v1",))
            return ModeEvaluation(contribution=contribution, query_results=(result,))
        # Bind the complete evaluation to one atomic authority snapshot. A
        # publication may not refresh the eager rule index inside an old pinned
        # cycle, even if it lands after this initial generation comparison.
        rule_snapshot = self._rule_generation_snapshot()
        authority_generation = (rule_snapshot[0]
            if rule_snapshot[0] is not None
            else situation.revision_pin.authority_generation)
        if situation.revision_pin.authority_generation != authority_generation:
            raise StaleRevisionError("query authority generation differs from admitted read pin")
        try:
            rule_state = self._refresh_rule_index(rule_snapshot)
        except BudgetExhausted:
            # Preserve the public query contract: malformed or same-generation
            # rule state is an explicit bounded-incompleteness result.
            rule_state = (MappingProxyType({}), MappingProxyType({}), True)
        with self._stores.r3_read_snapshot(situation.revision_pin):
            result = self._evaluate_snapshot(expression, projection, situation, rule_state)
        if (type(self._authority) is LinkedAuthority
                and self._authority.rule_generation_snapshot() is not rule_snapshot):
            raise StaleRevisionError("query authority generation changed during pinned evaluation")
        return result

    def _evaluate_snapshot(self, expression: SemanticExpression, projection: ExpressionProjection,
                           situation: SituationContext, rule_state) -> ModeEvaluation:
        if expression.query_projections:
            raise ValueError("projection requires the guarded description proof read")
        if situation.mode is not SemanticMode.QUERY:
            raise ValueError("QueryDecisionOwner requires QUERY")
        lexical_apps = tuple(app for app in expression.applications if _lexical_target_application(app))
        lexical = len(expression.applications) == 1 and bool(lexical_apps)
        designation_blockers: tuple[str, ...] = ()
        if lexical:
            app = expression.applications[0]
            roles = {row.role_ref: row.filler for row in app.roles}
            from .r3_learning import AdmittedDesignationReader
            overflow = False
            reader = self._designation_reader
            if reader is None:
                # Static nonlexical unit owners need not own a designation
                # authority. Any lexical read still requires the exact reader.
                reader = AdmittedDesignationReader(self._authority, self._stores)
            with reader.batch(situation.revision_pin) as batch:
                try:
                    rows = batch.exact_surface(roles["role:surface"].value,
                        maximum=self._config.max_orientation_alternatives)
                except BudgetExhausted:
                    rows, overflow = (), True
            base = tuple(_FactView(
                fact_ref=row.world_fact_ref or row.authority_designation_ref, operator="op:designation", predicate_ref=app.predicate_ref,
                roles=(("role:label_type", app.predicate_ref), ("role:surface", row.designation.surface), ("role:target", row.designation.target_ref)),
                stance="support", placement="reviewed",
                source_refs=row.provenance_refs,
            ) for row in rows)
            if overflow or len({(row.designation.language, row.designation.target_ref) for row in rows}) > 1:
                designation_blockers = ("query:designation_retrieval_overflow" if overflow else "query:designation_alternatives",)
            if expression.scope_operators or expression.expression_links:
                designation_blockers += ("query:scoped_designation_unsupported",)
            facts, rule_refs, rounds, truncated = base, (), 1, False
        elif lexical_apps:
            # Unsupported compound projection cannot change the admitted
            # designation source into arbitrary world teaching claims.
            facts, rule_refs, rounds, truncated = (), (), 1, False
        else:
            try:
                retrieved, rules = self._relevant_evidence(expression, rule_state)
                base = tuple(dict.fromkeys((*retrieved, *_authority_control_fact_views(
                    expression, self._authority, self._config.max_applications))))
                if len(base) > self._config.max_inference_facts:
                    raise BudgetExhausted("combined query authority and world evidence exceeds bound", 256)
                facts, rule_refs, rounds, truncated = _rule_closure(base, rules, self._config)
            except BudgetExhausted:
                facts, rule_refs, rounds, truncated = (), (), 1, True
        evaluator = _RecursiveQueryEvaluator(expression, projection, facts, self._config,
            allowed_placements=_WORLD_PLACEMENTS, designation_blockers=designation_blockers)
        root_result = _and(
            tuple(evaluator.evaluate(ref) for ref in expression.root_refs),
            self._config.max_inference_facts,
        )
        if lexical_apps and not lexical:
            root_result = _NodeResult(QueryStatus.PARTIAL, blockers=("query:compound_designation_projection_unsupported",))
        if truncated or root_result.truncated:
            root_result = _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True)
        chosen_solutions = root_result.support or root_result.oppose
        chosen = chosen_solutions[0] if chosen_solutions else _Solution((), ())
        if root_result.status is QueryStatus.CONFLICT:
            # Keep actual opposing evidence through conservative compound
            # conflict reporting; never manufacture proof from a blocker.
            substitutions = {solution.bindings for solution in (*root_result.support, *root_result.oppose)}
            chosen = _Solution(next(iter(substitutions)) if len(substitutions) == 1 else (), tuple(dict.fromkeys(
                ref for solution in (*root_result.support, *root_result.oppose)
                for ref in solution.fact_refs
            )))
        selected = tuple(evaluator.fact_by_ref[ref] for ref in chosen.fact_refs)
        try:
            proof = _proof(selected, evaluator.fact_by_ref, chosen.bindings, situation.revision_pin)
        except (ValueError, KeyError, TypeError, RecursionError):
            root_result = _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True)
            chosen, proof = _Solution((), ()), None
        result = QueryResult.create(
            expression_ref=expression.expression_ref,
            status=root_result.status,
            bindings=chosen.bindings,
            proof=proof,
            retrieval_refs=tuple(dict.fromkeys((*tuple(row.fact_ref for row in facts), *rule_refs,
                *((self._authority.content_hash,) if lexical_apps else ()))))[: self._config.max_inference_facts],
            rounds=max(1, rounds),
            revision_pin=situation.revision_pin,
        )
        status = {
            QueryStatus.SUPPORTED: DecisionStatus.SUPPORTED,
            QueryStatus.CONTRADICTED: DecisionStatus.CONTRADICTED,
            QueryStatus.CONFLICT: DecisionStatus.CONFLICT,
            QueryStatus.UNKNOWN: DecisionStatus.UNKNOWN,
            QueryStatus.PARTIAL: DecisionStatus.PARTIAL,
            QueryStatus.BUDGET_EXHAUSTED: DecisionStatus.BUDGET_EXHAUSTED,
        }[root_result.status]
        if root_result.status in {QueryStatus.SUPPORTED, QueryStatus.CONTRADICTED}:
            instantiated = instantiate_bindings(expression, chosen.bindings)
            answer = instantiated if root_result.status is QueryStatus.SUPPORTED else negate_expression(instantiated)
            action = DecisionAction.ANSWER
            answer_ref = answer.expression_ref
            blockers = ()
        elif root_result.status in {QueryStatus.CONFLICT, QueryStatus.UNKNOWN, QueryStatus.PARTIAL}:
            action = DecisionAction.REQUEST_CLARIFICATION
            answer_ref = None
            blockers = tuple(dict.fromkeys(root_result.blockers)) or (f"query:{root_result.status.value}",)
        else:
            action = DecisionAction.NO_OP
            answer_ref = None
            blockers = ("query:budget_exhausted",)
        contribution = DecisionContribution(
            status=status,
            action=action,
            answer_expression_ref=answer_ref,
            bindings=result.bindings,
            query_result_refs=(result.query_result_ref,),
            proof_refs=(proof.proof_ref,) if proof else (),
            source_refs=proof.source_refs if proof else (
                (self._authority.generation, self._authority.content_hash, *(row.fact_ref for row in facts))
                if lexical_apps else ()
            ),
            blocker_refs=blockers,
            policy_refs=("policy:recursive_expression_query:v1",),
        )
        return ModeEvaluation(contribution=contribution, query_results=(result,))

    def evaluate(self, expression: SemanticExpression, projection: ExpressionProjection,
                 situation: SituationContext) -> DecisionContribution:
        return self.evaluate_full(expression, projection, situation).contribution


def _placement_for_root(expression: SemanticExpression, projection: ExpressionProjection,
                        root_ref: str, situation: SituationContext) -> PlacementMode:
    current = root_ref
    seen: set[str] = set()
    while current not in seen:
        seen.add(current)
        node = projection.node_by_ref[current]
        if isinstance(node, ScopeOperator):
            placement = _SCOPE_PLACEMENTS.get((node.operator_type, node.value_ref))
            if placement is not None:
                return placement
            current = node.operand_ref
            continue
        if isinstance(node, VariableBinder):
            current = node.body_ref
            continue
        break
    return PlacementMode.OBSERVED if situation.mode is SemanticMode.OBSERVE else PlacementMode.SIMULATED


def _state_delta(app: SemanticApplication, stance: str, occurrence: ClaimOccurrence, pin: RevisionPin) -> StateDelta:
    roles = tuple(sorted(
        (binding.role_ref, value)
        for binding in (*app.roles, *app.qualifiers)
        if (value := _filler_value(binding)) is not None
    ))
    return StateDelta.create(
        operator_ref=app.operator,
        predicate_ref=app.predicate_ref,
        role_values=roles,
        stance=stance,
        occurrence_ref=occurrence.occurrence_ref,
        proof_refs=(occurrence.occurrence_ref,),
        revision_pin=pin,
    )


def _signed_root_node(projection: ExpressionProjection, root_ref: str) -> tuple[object | None, str]:
    """Follow polarity only; never distribute it through a compound node."""
    node = projection.node_by_ref[root_ref]
    stance = "support"
    while isinstance(node, ScopeOperator):
        if node.operator_type != "scope:polarity":
            return None, stance
        if node.value_ref in _NEGATIVE_POLARITY:
            stance = "deny" if stance == "support" else "support"
        elif node.value_ref not in _POSITIVE_POLARITY:
            return None, stance
        node = projection.node_by_ref[node.operand_ref]
    return node, stance


def _admissible_state(node: object) -> bool:
    return (
        isinstance(node, SemanticApplication)
        and node.operator == "op:state"
        and {"role:subject", "role:value"} <= {binding.role_ref for binding in node.roles}
        and all(isinstance(binding.filler, GroundedReference) for binding in (*node.roles, *node.qualifiers))
    )


def _contains_state_conflict(expression: SemanticExpression, projection: ExpressionProjection) -> bool:
    # Conflict evidence may compare actual conjuncts, but this does not license
    # admitting a compound expression by flattening it into independent facts.
    values_by_state: dict[tuple[object, ...], dict[str, set[GroundedReference]]] = {}
    pending = list(expression.root_refs)
    seen: set[str] = set()
    while pending:
        ref = pending.pop()
        if ref in seen:
            continue
        seen.add(ref)
        node, stance = _signed_root_node(projection, ref)
        if isinstance(node, ExpressionLink):
            if stance == "support" and node.link_type in {"link:conjunction", "link:coordination"}:
                pending.extend(node.operand_refs)
            continue
        if not isinstance(node, SemanticApplication) or node.operator != "op:state":
            continue
        roles = {binding.role_ref: binding.filler for binding in node.roles}
        value = roles.get("role:value")
        if not isinstance(value, GroundedReference) or not isinstance(roles.get("role:subject"), GroundedReference):
            continue
        if any(not isinstance(binding.filler, (GroundedReference, LiteralValue)) for binding in (*node.roles, *node.qualifiers)):
            continue
        # Keep every contextual role/qualifier typed. A literal spelled like a
        # reference cannot put two claims into the same context.
        context = (node.predicate_ref, tuple(binding for binding in node.roles if binding.role_ref != "role:value"), node.qualifiers)
        signed_values = values_by_state.setdefault(context, {"support": set(), "deny": set()})
        signed_values[stance].add(value)
        if len(signed_values["support"]) > 1 or signed_values["support"] & signed_values["deny"]:
            return True
    return False


class ObserveDecisionOwner:
    def __init__(self, authority: LinkedAuthority | None = None) -> None:
        self._authority = authority

    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if situation.mode is not SemanticMode.OBSERVE:
            raise ValueError("ObserveDecisionOwner requires OBSERVE")
        occurrences: list[ClaimOccurrence] = []
        admissions: list[AdmissionDecision] = []
        deltas: list[StateDelta] = []
        blockers: list[str] = []
        occurrence_sources: list[
            tuple[str, str, PlacementMode, tuple[str, ...]]
        ] = [
            (
                root_ref,
                situation.source_refs[0],
                _placement_for_root(expression, projection, root_ref, situation),
                (),
            )
            for root_ref in expression.root_refs
        ]
        if self._authority is not None:
            for application in expression.applications:
                bindings = (*application.roles, *application.qualifiers)
                grounded_by_role: dict[str, list[str]] = {}
                controlled_children: list[tuple[str, Any]] = []
                for binding in bindings:
                    if isinstance(binding.filler, GroundedReference):
                        grounded_by_role.setdefault(binding.role_ref, []).append(
                            binding.filler.target_ref
                        )
                    elif isinstance(binding.filler, ApplicationFiller):
                        control = self._authority.source_attribution_control(
                            application.predicate_ref, binding.role_ref
                        )
                        if control is not None:
                            controlled_children.append((binding.filler.node_ref, control))
                for child_ref, control in controlled_children:
                    sources = grounded_by_role.get(control.source_role_ref, [])
                    if len(sources) != 1:
                        continue
                    occurrence_sources.append((
                        child_ref,
                        sources[0],
                        PlacementMode(control.placement),
                        (application.application_ref, control.control_ref),
                    ))
        for root_ref, source_ref, placement, attribution_proof_refs in occurrence_sources:
            occurrence = ClaimOccurrence.create(
                expression_ref=expression.expression_ref,
                root_ref=root_ref,
                source_ref=source_ref,
                evidence_refs=situation.source_refs,
                interval_ref=situation.temporal_frame_ref,
                confidence_q=1_000_000 if situation.trusted_observation else 500_000,
                modality_ref="modality:actual",
                scope_ref=situation.epistemic_scope_ref,
                placement=placement,
                situation_ref=situation.situation_ref,
                supersedes_ref=None,
                revision_pin=situation.revision_pin,
            )
            occurrences.append(occurrence)
            node, stance = _signed_root_node(projection, root_ref)
            eligible = _admissible_state(node)
            if not eligible:
                blockers.append("observation:unsupported_state_admission")
            can_admit = situation.trusted_observation and placement is PlacementMode.OBSERVED and eligible
            if can_admit:
                root_deltas = (_state_delta(node, stance, occurrence, situation.revision_pin),)
                deltas.extend(root_deltas)
                admission = AdmissionDecision.create(
                    occurrence_ref=occurrence.occurrence_ref,
                    status=AdmissionStatus.ADMITTED,
                    policy_ref="policy:reviewed_adapter_observation:v1",
                    proof_refs=tuple(dict.fromkeys((*situation.adapter_receipt_refs, occurrence.occurrence_ref))),
                    proposed_fact_refs=tuple(row.fact_ref for row in root_deltas),
                    revision_pin=situation.revision_pin,
                )
            else:
                status = AdmissionStatus.ATTRIBUTED if placement is not PlacementMode.OBSERVED else AdmissionStatus.CONTESTED
                policy = "policy:epistemic_attribution:v1" if status is AdmissionStatus.ATTRIBUTED else "policy:conversation_claim_contested:v1"
                admission = AdmissionDecision.create(
                    occurrence_ref=occurrence.occurrence_ref,
                    status=status,
                    policy_ref=policy,
                    proof_refs=(occurrence.occurrence_ref, *attribution_proof_refs),
                    proposed_fact_refs=(),
                    revision_pin=situation.revision_pin,
                )
            admissions.append(admission)
        conflict = _contains_state_conflict(expression, projection)
        if conflict:
            status, action = (
                DecisionStatus.CONFLICT,
                DecisionAction.REQUEST_CLARIFICATION,
            )
        elif admissions and all(row.status is AdmissionStatus.ADMITTED for row in admissions):
            status, action = DecisionStatus.ADMITTED, DecisionAction.ADMIT_CLAIM
        elif any(row.status is AdmissionStatus.CONTESTED for row in admissions):
            status, action = DecisionStatus.CONTESTED, DecisionAction.RETAIN_ATTRIBUTION
        else:
            status, action = DecisionStatus.ATTRIBUTED, DecisionAction.RETAIN_ATTRIBUTION
        contribution = DecisionContribution(
            status=status,
            action=action,
            claim_occurrence_refs=(
                ()
                if conflict
                else tuple(row.occurrence_ref for row in occurrences)
            ),
            admission_decision_refs=(
                ()
                if conflict
                else tuple(row.admission_ref for row in admissions)
            ),
            proof_refs=tuple(
                dict.fromkeys(
                    (
                        *(row.occurrence_ref for row in occurrences),
                        *(
                            ("trusted_evidence",)
                            if situation.trusted_observation
                            else ()
                        ),
                    )
                )
            ),
            source_refs=situation.source_refs,
            policy_refs=tuple(dict.fromkeys(row.policy_ref for row in admissions)),
            blocker_refs=("expected_conflict",) if conflict else tuple(dict.fromkeys(blockers)),
        )
        return ModeEvaluation(
            contribution=contribution,
            claim_occurrences=() if conflict else tuple(occurrences),
            admission_decisions=() if conflict else tuple(admissions),
            state_deltas=() if conflict else tuple(deltas),
        )

    def evaluate(self, expression: SemanticExpression, projection: ExpressionProjection,
                 situation: SituationContext) -> DecisionContribution:
        return self.evaluate_full(expression, projection, situation).contribution


def _role_target(app: SemanticApplication, candidates: tuple[str, ...]) -> str | None:
    for binding in (*app.roles, *app.qualifiers):
        if binding.role_ref in candidates:
            return _filler_value(binding)
    return None


def _transition_mapping(
    authority: Any, event_type_ref: str, dimension_ref: str | None, to_value_ref: str | None
) -> Mapping[str, Any] | None:
    exact_method = getattr(authority, "transition_for", None)
    row = (
        exact_method(event_type_ref, dimension_ref, to_value_ref)
        if callable(exact_method)
        and dimension_ref is not None
        and to_value_ref is not None
        else None
    )
    if row is None:
        legacy_method = getattr(authority, "by_transition", None)
        row = legacy_method(event_type_ref) if callable(legacy_method) else None
    return row if isinstance(row, Mapping) else None


def _state_precondition(stores: SemanticStores, *, target_ref: str, dimension_ref: str,
                        from_value_ref: str) -> tuple[str, tuple[str, ...]]:
    sources: list[str] = []
    seen_values: set[str] = set()
    for fact in _fact_views(stores):
        if fact.operator != "op:state" or fact.predicate_ref != dimension_ref:
            continue
        roles = dict(fact.roles)
        subject = roles.get("role:subject") or roles.get("role:target")
        value = roles.get("role:value")
        if subject == target_ref and value is not None and fact.stance == "support":
            seen_values.add(value)
            sources.extend(fact.source_refs or (fact.fact_ref,))
    if not seen_values:
        return "unknown", tuple(dict.fromkeys(sources))
    if len(seen_values) > 1:
        return "conflict", tuple(dict.fromkeys(sources))
    return ("satisfied" if from_value_ref in seen_values else "contradicted"), tuple(dict.fromkeys(sources))


class _TransitionOwnerBase:
    def __init__(self, authority: Any, stores: SemanticStores, config: RuntimeConfig) -> None:
        self._authority = authority
        self._stores = stores
        self._config = config

    @staticmethod
    def _eligible_root(expression: SemanticExpression, projection: ExpressionProjection) -> tuple[SemanticApplication | None, tuple[str, ...]]:
        if len(expression.root_refs) != 1:
            return None, ("transition:multiple_roots",)
        node = projection.node_by_ref[expression.root_refs[0]]
        while isinstance(node, ScopeOperator):
            if node.operator_type != "scope:polarity" or node.value_ref not in _POSITIVE_POLARITY:
                return None, ("transition:unsupported_scope", node.scope_ref)
            node = projection.node_by_ref[node.operand_ref]
        if not isinstance(node, SemanticApplication) or node.operator not in {"op:event", "op:designation"}:
            return None, ("transition:unsupported_root",)
        if any(isinstance(binding.filler, ApplicationFiller) for binding in (*node.roles, *node.qualifiers)):
            return None, ("transition:proposition_content", node.application_ref)
        return node, ()

    def _transition(self, app: SemanticApplication, situation: SituationContext,
                    *, simulate: bool) -> tuple[TransitionEvaluation, CapabilityEvaluation, EffectIntent | None]:
        event_type = app.predicate_ref
        actor = _role_target(app, ("role:actor",)) or situation.actor_ref or situation.addressee_ref
        target = _role_target(app, ("role:target", "role:subject", "role:object"))
        dimension_ref = _role_target(app, ("role:dimension",))
        to_value_ref = _role_target(app, ("role:value",))
        signature_method = getattr(self._authority, "by_event_signature", None)
        signature = signature_method(event_type) if callable(signature_method) else None
        transition = _transition_mapping(
            self._authority, event_type, dimension_ref, to_value_ref
        )
        if signature is None or transition is None or target is None:
            blockers = tuple(ref for ref, value in (("event_signature:missing", signature), ("transition:missing", transition), ("transition:target_missing", target)) if value is None)
            capability = CapabilityEvaluation.create(
                actor_ref=actor, event_type_ref=event_type, status=CapabilityStatus.UNKNOWN,
                capability_refs=(), permission_refs=(), resource_refs=(), adapter_ref=None,
                proof_refs=(), blocker_refs=blockers, revision_pin=situation.revision_pin,
            )
            evaluation = TransitionEvaluation.create(
                expression_ref=app.application_ref, event_type_ref=event_type,
                transition_ref="transition:unavailable", status=TransitionStatus.UNKNOWN,
                source_application_ref=app.application_ref, actor_ref=actor, target_ref=target,
                predicted_deltas=(), proof_refs=(), blocker_refs=blockers,
                revision_pin=situation.revision_pin,
            )
            return evaluation, capability, None
        required = ("transition_ref", "event_type", "dimension", "to_value")
        if any(type(transition.get(key)) is not str or not transition.get(key) for key in required):
            raise ValueError("reviewed transition record is structurally incomplete")
        transition_ref = transition["transition_ref"]
        dimension = transition["dimension"]
        from_value = transition.get("from_value")
        to_value = transition["to_value"]
        if simulate:
            # Simulation previews the reviewed transition without asserting
            # that its source-state precondition is admitted world truth.
            precondition, state_sources = "satisfied", ()
        elif from_value is None:
            precondition, state_sources = "satisfied", ()
        elif type(from_value) is str and from_value:
            precondition, state_sources = _state_precondition(
                self._stores,
                target_ref=target,
                dimension_ref=dimension,
                from_value_ref=from_value,
            )
        else:
            raise ValueError("reviewed transition from_value must be exact str or null")
        occurrence_ref = stable_ref("transition_occurrence", {"application_ref": app.application_ref, "situation_ref": situation.situation_ref})
        predicted = StateDelta.create(
            operator_ref="op:state", predicate_ref=dimension,
            role_values=(("role:subject", target), ("role:dimension", dimension), ("role:value", to_value)),
            stance="support", occurrence_ref=occurrence_ref,
            proof_refs=(transition_ref, *state_sources), revision_pin=situation.revision_pin,
        )
        if precondition != "satisfied":
            blockers = (f"transition:precondition_{precondition}",)
            capability = CapabilityEvaluation.create(
                actor_ref=actor, event_type_ref=event_type, status=CapabilityStatus.UNKNOWN,
                capability_refs=(), permission_refs=(), resource_refs=(), adapter_ref=None,
                proof_refs=state_sources, blocker_refs=blockers, revision_pin=situation.revision_pin,
            )
            evaluation = TransitionEvaluation.create(
                expression_ref=app.application_ref, event_type_ref=event_type,
                transition_ref=transition_ref, status=TransitionStatus.UNKNOWN,
                source_application_ref=app.application_ref, actor_ref=actor, target_ref=target,
                predicted_deltas=(), proof_refs=state_sources,
                blocker_refs=blockers, revision_pin=situation.revision_pin,
            )
            return evaluation, capability, None
        if simulate:
            capability = CapabilityEvaluation.create(
                actor_ref=actor, event_type_ref=event_type, status=CapabilityStatus.AVAILABLE,
                capability_refs=(), permission_refs=(), resource_refs=(), adapter_ref=None,
                proof_refs=(transition_ref, *state_sources), blocker_refs=(), revision_pin=situation.revision_pin,
            )
            evaluation = TransitionEvaluation.create(
                expression_ref=app.application_ref, event_type_ref=event_type,
                transition_ref=transition_ref, status=TransitionStatus.SIMULATED,
                source_application_ref=app.application_ref, actor_ref=actor, target_ref=target,
                predicted_deltas=(predicted,), proof_refs=(transition_ref, *state_sources),
                blocker_refs=(), revision_pin=situation.revision_pin,
            )
            return evaluation, capability, None
        required_caps = tuple(getattr(signature, "required_capabilities", ()))
        required_permissions = tuple(getattr(signature, "required_permissions", ()))
        required_resources = tuple(transition.get("required_resources", ()))
        adapter_ref = getattr(signature, "adapter_ref", None) or transition.get("adapter_ref")
        missing_caps = tuple(ref for ref in required_caps if ref not in situation.capability_refs)
        missing_permissions = tuple(ref for ref in required_permissions if ref not in situation.permission_refs)
        missing_resources = tuple(ref for ref in required_resources if ref not in situation.resource_refs)
        if missing_caps:
            cap_status, blockers = CapabilityStatus.UNKNOWN, missing_caps
        elif missing_permissions:
            cap_status, blockers = CapabilityStatus.DENIED, missing_permissions
        elif missing_resources:
            cap_status, blockers = CapabilityStatus.RESOURCE_UNAVAILABLE, missing_resources
        elif adapter_ref is None or adapter_ref not in situation.adapter_refs:
            cap_status, blockers = CapabilityStatus.ADAPTER_MISSING, ((adapter_ref or "adapter:missing"),)
        else:
            cap_status, blockers = CapabilityStatus.AVAILABLE, ()
        capability = CapabilityEvaluation.create(
            actor_ref=actor, event_type_ref=event_type, status=cap_status,
            capability_refs=required_caps, permission_refs=required_permissions,
            resource_refs=required_resources, adapter_ref=adapter_ref,
            proof_refs=(transition_ref, *state_sources), blocker_refs=blockers,
            revision_pin=situation.revision_pin,
        )
        transition_eval = TransitionEvaluation.create(
            expression_ref=app.application_ref, event_type_ref=event_type,
            transition_ref=transition_ref,
            status=TransitionStatus.READY if cap_status is CapabilityStatus.AVAILABLE else TransitionStatus.UNKNOWN,
            source_application_ref=app.application_ref, actor_ref=actor, target_ref=target,
            predicted_deltas=(predicted,) if cap_status is CapabilityStatus.AVAILABLE else (),
            proof_refs=(transition_ref, *state_sources, capability.capability_evaluation_ref),
            blocker_refs=blockers, revision_pin=situation.revision_pin,
        )
        intent = None
        if cap_status is CapabilityStatus.AVAILABLE:
            intent = EffectIntent.create(
                event_type_ref=event_type, transition_ref=transition_ref,
                actor_ref=actor, target_ref=target, adapter_ref=adapter_ref,
                capability_evaluation_ref=capability.capability_evaluation_ref,
                proposed_deltas=(predicted,),
                requirement_proof_refs=(transition_eval.transition_evaluation_ref, capability.capability_evaluation_ref),
                revision_pin=situation.revision_pin,
            )
        return transition_eval, capability, intent


class RequestDecisionOwner(_TransitionOwnerBase):
    def _learning_directive(
        self,
        app: SemanticApplication,
        expression: SemanticExpression,
        situation: SituationContext,
    ) -> ModeEvaluation | None:
        from .r3_learning import LearningLoweringError, lower_designation_learning

        contract = self._authority.learning_contract_for_source(app.operator, app.predicate_ref)
        if contract is None:
            return None
        try:
            lowered = lower_designation_learning(self._authority, expression, situation)
        except PermissionError:
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.DENIED, action=DecisionAction.NO_OP,
                blocker_refs=(contract.permission_ref,), policy_refs=(contract.review_policy_ref,),
            ))
        except LearningLoweringError as exc:
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.REQUEST_CLARIFICATION,
                blocker_refs=(exc.blocker_ref,), policy_refs=(contract.review_policy_ref,),
            ))
        except (TypeError, ValueError):
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.REQUEST_CLARIFICATION,
                blocker_refs=("learning:ineligible_directive",), policy_refs=(contract.review_policy_ref,),
            ))
        from .dialogue import bind_learning_answer
        try:
            pending = bind_learning_answer(self._stores, situation, lowered.designation, maximum=self._config.max_orientation_alternatives)
            if pending.expected_answer_contract_ref != contract.answer_contract_ref:
                raise ValueError("learning answer contract differs from the linked source contract")
        except (TypeError, ValueError):
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.REQUEST_CLARIFICATION,
                blocker_refs=("learning:unbound_query_continuation",),
                policy_refs=(contract.review_policy_ref,),
            ))
        roles = {binding.role_ref: binding.filler for binding in lowered.designation.roles}
        surface = roles["role:surface"].value
        target = roles["role:target"].target_ref
        target_kind = self._authority.atoms[target].kind
        draft = LearningDraft.create(
            kind="directive",
            surface_literal=surface,
            target_ref=target,
            expected_target_kinds=(target_kind,),
            source_query_ref=pending.source_query_ref,
            answer_contract_ref=contract.answer_contract_ref,
            proof_refs=(*lowered.proof_refs, pending.obligation_ref),
            revision_pin=situation.revision_pin,
        )
        return ModeEvaluation(
            contribution=DecisionContribution(
                status=DecisionStatus.PENDING,
                action=DecisionAction.CREATE_LEARNING_OBLIGATION,
                learning_draft_refs=(draft.learning_draft_ref,),
                proof_refs=lowered.proof_refs,
                policy_refs=(contract.review_policy_ref,),
            ),
            learning_drafts=(draft,),
        )

    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if situation.mode is not SemanticMode.REQUEST:
            raise ValueError("RequestDecisionOwner requires REQUEST")
        app, blockers = self._eligible_root(expression, projection)
        if app is None:
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,
                blocker_refs=blockers, policy_refs=("policy:request_transition:v2",),
            ))
        learning = self._learning_directive(app, expression, situation)
        if learning is not None:
            return learning
        if any(not isinstance(binding.filler, GroundedReference) for binding in (*app.roles, *app.qualifiers)):
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,
                blocker_refs=("transition:unresolved_or_literal_role",), policy_refs=("policy:request_transition:v2",),
            ))
        transition, capability, intent = self._transition(app, situation, simulate=False)
        if capability.status is CapabilityStatus.AVAILABLE and intent is not None:
            status, action = DecisionStatus.PENDING, DecisionAction.REQUEST_EFFECT
        elif capability.status is CapabilityStatus.DENIED:
            status, action = DecisionStatus.DENIED, DecisionAction.NO_OP
        elif capability.status is CapabilityStatus.RESOURCE_UNAVAILABLE:
            status, action = DecisionStatus.RESOURCE_UNAVAILABLE, DecisionAction.NO_OP
        elif capability.status is CapabilityStatus.ADAPTER_MISSING:
            status, action = DecisionStatus.ADAPTER_MISSING, DecisionAction.NO_OP
        else:
            status, action = DecisionStatus.UNKNOWN, DecisionAction.NO_OP
        contribution = DecisionContribution(
            status=status, action=action,
            transition_preview_refs=(transition.transition_evaluation_ref,),
            effect_intent_ref=intent.effect_intent_ref if intent else None,
            proof_refs=(transition.transition_evaluation_ref, capability.capability_evaluation_ref),
            blocker_refs=capability.blocker_refs,
            policy_refs=("policy:request_transition:v2",),
        )
        return ModeEvaluation(
            contribution=contribution,
            transition_evaluations=(transition,),
            capability_evaluations=(capability,),
            effect_intents=(intent,) if intent else (),
        )

    def evaluate(self, expression: SemanticExpression, projection: ExpressionProjection,
                 situation: SituationContext) -> DecisionContribution:
        return self.evaluate_full(expression, projection, situation).contribution


class SimulateDecisionOwner(_TransitionOwnerBase):
    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if situation.mode is not SemanticMode.SIMULATE:
            raise ValueError("SimulateDecisionOwner requires SIMULATE")
        app, blockers = self._eligible_root(expression, projection)
        if app is not None and any(not isinstance(binding.filler, GroundedReference) for binding in (*app.roles, *app.qualifiers)):
            app, blockers = None, ("transition:unresolved_or_literal_role",)
        if app is None:
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,
                blocker_refs=blockers, policy_refs=("policy:simulation_no_effect:v2",),
            ))
        transition, capability, _ = self._transition(app, situation, simulate=True)
        if transition.status is TransitionStatus.SIMULATED:
            contribution = DecisionContribution(
                status=DecisionStatus.SIMULATION, action=DecisionAction.PREVIEW_TRANSITION,
                transition_preview_refs=(transition.transition_evaluation_ref,),
                proof_refs=(transition.transition_evaluation_ref, capability.capability_evaluation_ref),
                policy_refs=("policy:simulation_no_effect:v2",),
            )
        else:
            contribution = DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,
                transition_preview_refs=(transition.transition_evaluation_ref,),
                proof_refs=(transition.transition_evaluation_ref, capability.capability_evaluation_ref),
                blocker_refs=transition.blocker_refs,
                policy_refs=("policy:simulation_no_effect:v2",),
            )
        return ModeEvaluation(
            contribution=contribution,
            transition_evaluations=(transition,),
            capability_evaluations=(capability,),
        )

    def evaluate(self, expression: SemanticExpression, projection: ExpressionProjection,
                 situation: SituationContext) -> DecisionContribution:
        return self.evaluate_full(expression, projection, situation).contribution


class R3EvaluationOwner:
    """Evaluate one mode and finalize a Decision only after dependent refs exist."""

    def __init__(self, authority: Any, stores: SemanticStores, config: RuntimeConfig,
                 *, designation_reader: Any = None, communicative_owner: Any = None) -> None:
        self._authority = authority
        self._communicative_owner = communicative_owner
        self._owners = {
            SemanticMode.OBSERVE: ObserveDecisionOwner(authority),
            SemanticMode.QUERY: QueryDecisionOwner(stores, config, authority, designation_reader=designation_reader),
            SemanticMode.REQUEST: RequestDecisionOwner(authority, stores, config),
            SemanticMode.SIMULATE: SimulateDecisionOwner(authority, stores, config),
        }

    def evaluate_mode(self, meaning: Any, situation: SituationContext, **source_inputs) -> ModeEvaluation:
        from .expressions import VerifiedMeaning
        if type(meaning) is not VerifiedMeaning or type(situation) is not SituationContext:
            raise TypeError("R3 EVALUATE requires exact meaning and situation")
        if meaning.revision_pin != situation.revision_pin:
            raise ValueError("meaning and situation revision pins differ")
        if meaning.expression.query_projections and situation.mode is not SemanticMode.QUERY:
            raise ValueError("query projections require QUERY mode")
        from .communicative import authenticate_consequence
        authenticate_consequence(self._communicative_owner, authority=self._authority,
            situation=situation, meaning=meaning, **source_inputs)
        if situation.communicative_source is not None:
            source = situation.communicative_source
            if source.force == "performed":
                selection, blockers = self._communicative_owner.selection(source, situation, source_inputs["orientation"])
                return ModeEvaluation(response_selection=selection, contribution=DecisionContribution(
                    status=DecisionStatus.PENDING if selection else DecisionStatus.DENIED,
                    action=DecisionAction.RESPOND if selection else DecisionAction.NO_OP,
                    selection_ref=selection.selection_ref if selection else None,
                    blocker_refs=blockers, source_refs=(source.source_ref,),
                    proof_refs=(source.compilation_proof_ref, source.coverage_receipt_ref),
                    policy_refs=(source.control_ref,)))
        projection = project_expression(meaning.expression)
        result = self._owners[situation.mode].evaluate_full(meaning.expression, projection, situation)
        if type(result) is not ModeEvaluation:
            raise TypeError("mode owner returned non-canonical ModeEvaluation")
        return result

    @staticmethod
    def finalize(meaning: Any, situation: SituationContext,
                 mode_result: ModeEvaluation,
                 contribution: DecisionContribution | None = None,
                 *, communicative_owner=None, authority=None, **source_inputs) -> EvaluationBundle:
        from .expressions import VerifiedMeaning
        if type(meaning) is not VerifiedMeaning:
            raise TypeError("meaning must be exact VerifiedMeaning")
        from .communicative import require_live_authority
        authority = require_live_authority(communicative_owner, authority, meaning.revision_pin)
        contribution = mode_result.contribution if contribution is None else contribution
        exact = {
            "query_result_refs": tuple(row.query_result_ref for row in mode_result.query_results),
            "claim_occurrence_refs": tuple(row.occurrence_ref for row in mode_result.claim_occurrences),
            "admission_decision_refs": tuple(row.admission_ref for row in mode_result.admission_decisions),
            "transition_preview_refs": tuple(row.transition_evaluation_ref for row in mode_result.transition_evaluations),
            "learning_draft_refs": tuple(row.learning_draft_ref for row in mode_result.learning_drafts),
        }
        for name, refs in exact.items():
            if getattr(contribution, name) != refs:
                raise ValueError(f"Decision {name} does not match included artifacts")
        if contribution.effect_intent_ref is not None and tuple(row.effect_intent_ref for row in mode_result.effect_intents) != (contribution.effect_intent_ref,):
            raise ValueError("Decision effect intent does not match included artifact")
        decision = Decision.create(meaning=meaning, situation=situation, contribution=contribution)
        canonical_mode = replace(mode_result, contribution=contribution)
        evaluation = EvaluationBundle.create(
            decision=decision, expression=meaning.expression, situation=situation,
            mode_evaluation=canonical_mode, revision_pin=meaning.revision_pin,
        )
        from .communicative import authenticate_consequence
        authenticate_consequence(communicative_owner, authority=authority, situation=situation, meaning=meaning,
            selection=evaluation.response_selection, evaluation=evaluation, **source_inputs)
        return evaluation

    def evaluate(self, meaning: Any, situation: SituationContext, **source_inputs) -> EvaluationBundle:
        return self.finalize(meaning, situation, self.evaluate_mode(meaning, situation, **source_inputs),
            communicative_owner=self._communicative_owner, authority=self._authority, **source_inputs)
