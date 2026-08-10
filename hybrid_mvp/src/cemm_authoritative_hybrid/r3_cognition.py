"""Expression-only R3 cognition owners.

The QUERY owner evaluates the canonical root graph recursively, preserving link
and scope semantics.  OBSERVE separates claim occurrence from admission and
never turns ordinary text into world truth.  REQUEST/SIMULATE require exact
reviewed transitions and independently verify state preconditions.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .config import RuntimeConfig
from .cycle import SemanticMode
from .decision import Decision, DecisionAction, DecisionContribution, DecisionStatus
from .expression_projection import ExpressionProjection, project_expression
from .expression_transform import instantiate_bindings, negate_expression
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    VariableBinder,
)
from .persistence import Fact, RevisionPin, SemanticStores
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


def _pattern(app: SemanticApplication) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for binding in (*app.roles, *app.qualifiers):
        value = _filler_value(binding)
        if value is not None:
            rows.append((binding.role_ref, value))
    return tuple(sorted(rows))


def _merge_bindings(*rows: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...] | None:
    merged: dict[str, str] = {}
    for group in rows:
        for key, value in group:
            existing = merged.get(key)
            if existing is not None and existing != value:
                return None
            merged[key] = value
    return tuple(sorted(merged.items()))


def _match(pattern: tuple[tuple[str, str], ...], fact: _FactView) -> tuple[tuple[str, str], ...] | None:
    roles = dict(fact.roles)
    bindings: dict[str, str] = {}
    for role, expected in pattern:
        actual = roles.get(role)
        if actual is None:
            return None
        if expected.startswith("?"):
            previous = bindings.get(expected)
            if previous is not None and previous != actual:
                return None
            bindings[expected] = actual
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
    stance = str(clause.get("stance", "support"))
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
    facts: tuple[_FactView, ...], authority: Any, config: RuntimeConfig
) -> tuple[tuple[_FactView, ...], tuple[str, ...], int, bool]:
    rules = tuple(
        row for _, row in sorted(getattr(authority, "rules", {}).items())
        if getattr(row, "reviewed", False)
    )[: config.max_inference_rules]
    known = {row.fact_ref: row for row in facts}
    probed: list[str] = []
    rounds = 0
    truncated = False
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
                            next_states.append((matched, (*parents, fact)))
                            if len(next_states) >= config.max_inference_facts:
                                truncated = True
                                break
                    if truncated:
                        break
                states = next_states
                if not states or truncated:
                    break
            if not valid or truncated:
                break
            for env, parents in states:
                for raw_clause in rule.consequent:
                    parsed = _clause_parts(raw_clause)
                    if parsed is None:
                        continue
                    operator, predicate, role_rows, stance = parsed
                    roles: list[tuple[str, str]] = []
                    for role, raw in role_rows:
                        value = env.get(raw, raw) if raw.startswith("?") else raw
                        roles.append((role, value))
                    material = {
                        "operator": operator,
                        "predicate_ref": predicate,
                        "roles": roles,
                        "stance": stance,
                        "rule_ref": rule.rule_ref,
                        "premises": [row.fact_ref for row in parents],
                        "substitutions": sorted(env.items()),
                    }
                    ref = stable_ref("r3_derived_fact", material)
                    if ref not in known:
                        known[ref] = _FactView(
                            ref, operator, predicate, tuple(sorted(roles)), stance,
                            "derived", tuple(dict.fromkeys(
                                ref for parent in parents for ref in parent.source_refs
                            )), rule.rule_ref, tuple(parent.fact_ref for parent in parents),
                            tuple(sorted(env.items())),
                        )
                        added = True
                        if len(known) >= config.max_inference_facts:
                            truncated = True
                            break
                if truncated:
                    break
            if truncated:
                break
        if truncated or not added:
            break
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
    if any(row.status is QueryStatus.CONFLICT for row in results):
        return _NodeResult(QueryStatus.CONFLICT, blockers=("query:conjunct_conflict",))
    if any(row.status is QueryStatus.BUDGET_EXHAUSTED for row in results):
        return _NodeResult(QueryStatus.BUDGET_EXHAUSTED, truncated=True, blockers=("query:budget",))
    if any(row.status is QueryStatus.UNKNOWN for row in results):
        return _NodeResult(QueryStatus.UNKNOWN, blockers=("query:unknown_conjunct",))
    if any(row.status is QueryStatus.PARTIAL for row in results):
        return _NodeResult(QueryStatus.PARTIAL, blockers=("query:partial_conjunct",))
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
                if len(next_rows) >= maximum:
                    break
        solutions = next_rows
        if not solutions:
            return _NodeResult(QueryStatus.CONFLICT, blockers=("query:binding_conflict",))
    return _NodeResult(QueryStatus.SUPPORTED, support=tuple(solutions))


def _or(results: tuple[_NodeResult, ...], maximum: int) -> _NodeResult:
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
                 allowed_placements: frozenset[str] | None = None) -> None:
        self.expression = expression
        self.projection = projection
        self.facts = facts
        self.fact_by_ref = {row.fact_ref: row for row in facts}
        self.config = config
        self.allowed_placements = allowed_placements
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
        if link.link_type in {"link:disjunction"}:
            return _or(rows, self.config.max_inference_facts)
        if link.link_type == "link:condition":
            antecedent, consequent = rows
            if antecedent.status is QueryStatus.SUPPORTED:
                return consequent
            if antecedent.status is QueryStatus.CONTRADICTED:
                return _NodeResult(QueryStatus.SUPPORTED, support=antecedent.oppose)
            if antecedent.status is QueryStatus.CONFLICT:
                return _NodeResult(QueryStatus.CONFLICT, blockers=("query:condition_conflict",))
            return _NodeResult(QueryStatus.UNKNOWN, blockers=("query:condition_antecedent_unknown",))
        # Coordination, conjunction, cause, purpose, contrast and sequence all
        # require every ordered operand to hold. Their distinct link identity is
        # retained in the expression and proof lineage.
        return _and(rows, self.config.max_inference_facts)


class QueryDecisionOwner:
    def __init__(self, stores: SemanticStores, config: RuntimeConfig, authority: Any) -> None:
        self._stores = stores
        self._config = config
        self._authority = authority

    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if situation.mode is not SemanticMode.QUERY:
            raise ValueError("QueryDecisionOwner requires QUERY")
        base = _fact_views(self._stores)
        facts, rule_refs, rounds, truncated = _rule_closure(base, self._authority, self._config)
        evaluator = _RecursiveQueryEvaluator(expression, projection, facts, self._config)
        root_result = _and(
            tuple(evaluator.evaluate(ref) for ref in expression.root_refs),
            self._config.max_inference_facts,
        )
        if truncated and root_result.status is QueryStatus.UNKNOWN:
            root_result = replace(root_result, status=QueryStatus.BUDGET_EXHAUSTED, truncated=True)
        chosen_solutions = root_result.support or root_result.oppose
        chosen = chosen_solutions[0] if chosen_solutions else _Solution((), ())
        selected = tuple(evaluator.fact_by_ref[ref] for ref in chosen.fact_refs)
        proof = _proof(selected, evaluator.fact_by_ref, chosen.bindings, situation.revision_pin)
        result = QueryResult.create(
            expression_ref=expression.expression_ref,
            status=root_result.status,
            bindings=chosen.bindings,
            proof=proof,
            retrieval_refs=tuple(dict.fromkeys((*tuple(row.fact_ref for row in facts), *rule_refs)))[: self._config.max_inference_facts],
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
            blockers = root_result.blockers or (f"query:{root_result.status.value}",)
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
            source_refs=proof.source_refs if proof else (),
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


def _state_delta(app: SemanticApplication, occurrence: ClaimOccurrence, pin: RevisionPin) -> StateDelta:
    roles = tuple(sorted(
        (binding.role_ref, value)
        for binding in (*app.roles, *app.qualifiers)
        if (value := _filler_value(binding)) is not None
    ))
    return StateDelta.create(
        operator_ref=app.operator,
        predicate_ref=app.predicate_ref,
        role_values=roles,
        stance="support",
        occurrence_ref=occurrence.occurrence_ref,
        proof_refs=(occurrence.occurrence_ref,),
        revision_pin=pin,
    )


class ObserveDecisionOwner:
    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if situation.mode is not SemanticMode.OBSERVE:
            raise ValueError("ObserveDecisionOwner requires OBSERVE")
        occurrences: list[ClaimOccurrence] = []
        admissions: list[AdmissionDecision] = []
        deltas: list[StateDelta] = []
        for root_ref in expression.root_refs:
            placement = _placement_for_root(expression, projection, root_ref, situation)
            occurrence = ClaimOccurrence.create(
                expression_ref=expression.expression_ref,
                root_ref=root_ref,
                source_ref=situation.source_refs[0],
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
            can_admit = situation.trusted_observation and placement is PlacementMode.OBSERVED
            if can_admit:
                root_apps = projection.descendant_applications(root_ref)
                root_deltas = tuple(_state_delta(app, occurrence, situation.revision_pin) for app in root_apps)
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
                    proof_refs=(occurrence.occurrence_ref,),
                    proposed_fact_refs=(),
                    revision_pin=situation.revision_pin,
                )
            admissions.append(admission)
        if admissions and all(row.status is AdmissionStatus.ADMITTED for row in admissions):
            status, action = DecisionStatus.ADMITTED, DecisionAction.ADMIT_CLAIM
        elif any(row.status is AdmissionStatus.CONTESTED for row in admissions):
            status, action = DecisionStatus.CONTESTED, DecisionAction.RETAIN_ATTRIBUTION
        else:
            status, action = DecisionStatus.ATTRIBUTED, DecisionAction.RETAIN_ATTRIBUTION
        contribution = DecisionContribution(
            status=status,
            action=action,
            claim_occurrence_refs=tuple(row.occurrence_ref for row in occurrences),
            admission_decision_refs=tuple(row.admission_ref for row in admissions),
            proof_refs=tuple(dict.fromkeys(row.occurrence_ref for row in occurrences)),
            source_refs=situation.source_refs,
            policy_refs=tuple(dict.fromkeys(row.policy_ref for row in admissions)),
        )
        return ModeEvaluation(
            contribution=contribution,
            claim_occurrences=tuple(occurrences),
            admission_decisions=tuple(admissions),
            state_deltas=tuple(deltas),
        )

    def evaluate(self, expression: SemanticExpression, projection: ExpressionProjection,
                 situation: SituationContext) -> DecisionContribution:
        return self.evaluate_full(expression, projection, situation).contribution


def _role_target(app: SemanticApplication, candidates: tuple[str, ...]) -> str | None:
    for binding in (*app.roles, *app.qualifiers):
        if binding.role_ref in candidates:
            return _filler_value(binding)
    return None


def _transition_mapping(authority: Any, event_type_ref: str) -> Mapping[str, Any] | None:
    method = getattr(authority, "by_transition", None)
    row = method(event_type_ref) if callable(method) else None
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

    def _transition(self, app: SemanticApplication, situation: SituationContext,
                    *, simulate: bool) -> tuple[TransitionEvaluation, CapabilityEvaluation, EffectIntent | None]:
        event_type = app.predicate_ref
        actor = _role_target(app, ("role:actor",)) or situation.actor_ref or situation.addressee_ref
        target = _role_target(app, ("role:target", "role:subject", "role:object"))
        signature_method = getattr(self._authority, "by_event_signature", None)
        signature = signature_method(event_type) if callable(signature_method) else None
        transition = _transition_mapping(self._authority, event_type)
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
        required = ("transition_ref", "dimension", "from_value", "to_value")
        if any(type(transition.get(key)) is not str or not transition.get(key) for key in required):
            raise ValueError("reviewed transition record is structurally incomplete")
        transition_ref = transition["transition_ref"]
        dimension = transition["dimension"]
        from_value = transition["from_value"]
        to_value = transition["to_value"]
        precondition, state_sources = _state_precondition(
            self._stores, target_ref=target, dimension_ref=dimension, from_value_ref=from_value
        )
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
    def evaluate_full(self, expression: SemanticExpression, projection: ExpressionProjection,
                      situation: SituationContext) -> ModeEvaluation:
        if situation.mode is not SemanticMode.REQUEST:
            raise ValueError("RequestDecisionOwner requires REQUEST")
        app = next(iter(projection.event_applications()), None) or next(iter(expression.applications), None)
        if app is None:
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,
                blocker_refs=("request:no_application",), policy_refs=("policy:request_transition:v2",),
            ))
        if app.operator == "op:designation":
            roles = {row.role_ref: _filler_value(row) for row in (*app.roles, *app.qualifiers)}
            surface = roles.get("role:surface")
            target = roles.get("role:target") or roles.get("role:object") or roles.get("role:meaning")
            missing = tuple(
                blocker for blocker, value in (
                    ("learning:surface_missing", surface),
                    ("learning:target_missing", target),
                ) if value is None
            )
            if missing:
                return ModeEvaluation(contribution=DecisionContribution(
                    status=DecisionStatus.UNKNOWN,
                    action=DecisionAction.REQUEST_CLARIFICATION,
                    blocker_refs=missing,
                    policy_refs=("policy:learning_directive_requires_review:v2",),
                ))
            atom = getattr(self._authority, "atoms", {}).get(target)
            target_kind = getattr(atom, "kind", "unknown")
            draft = LearningDraft.create(
                kind="directive",
                surface_literal=surface,
                target_ref=target,
                expected_target_kinds=(target_kind,),
                source_query_ref=None,
                answer_contract_ref="contract:designation_answer:v2",
                proof_refs=(app.application_ref,),
                revision_pin=situation.revision_pin,
            )
            return ModeEvaluation(
                contribution=DecisionContribution(
                    status=DecisionStatus.PENDING,
                    action=DecisionAction.CREATE_LEARNING_OBLIGATION,
                    learning_draft_refs=(draft.learning_draft_ref,),
                    proof_refs=(app.application_ref,),
                    policy_refs=("policy:learning_directive_requires_review:v2",),
                ),
                learning_drafts=(draft,),
            )
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
        app = next(iter(projection.event_applications()), None) or next(iter(expression.applications), None)
        if app is None:
            return ModeEvaluation(contribution=DecisionContribution(
                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,
                blocker_refs=("simulation:no_application",), policy_refs=("policy:simulation_no_effect:v2",),
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

    def __init__(self, authority: Any, stores: SemanticStores, config: RuntimeConfig) -> None:
        self._owners = {
            SemanticMode.OBSERVE: ObserveDecisionOwner(),
            SemanticMode.QUERY: QueryDecisionOwner(stores, config, authority),
            SemanticMode.REQUEST: RequestDecisionOwner(authority, stores, config),
            SemanticMode.SIMULATE: SimulateDecisionOwner(authority, stores, config),
        }

    def evaluate_mode(self, meaning: Any, situation: SituationContext) -> ModeEvaluation:
        from .expressions import VerifiedMeaning
        if type(meaning) is not VerifiedMeaning or type(situation) is not SituationContext:
            raise TypeError("R3 EVALUATE requires exact meaning and situation")
        if meaning.revision_pin != situation.revision_pin:
            raise ValueError("meaning and situation revision pins differ")
        projection = project_expression(meaning.expression)
        result = self._owners[situation.mode].evaluate_full(meaning.expression, projection, situation)
        if type(result) is not ModeEvaluation:
            raise TypeError("mode owner returned non-canonical ModeEvaluation")
        return result

    @staticmethod
    def finalize(meaning: Any, situation: SituationContext,
                 mode_result: ModeEvaluation,
                 contribution: DecisionContribution | None = None) -> EvaluationBundle:
        from .expressions import VerifiedMeaning
        if type(meaning) is not VerifiedMeaning:
            raise TypeError("meaning must be exact VerifiedMeaning")
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
        return EvaluationBundle.create(
            decision=decision, expression=meaning.expression, situation=situation,
            mode_evaluation=canonical_mode, revision_pin=meaning.revision_pin,
        )

    def evaluate(self, meaning: Any, situation: SituationContext) -> EvaluationBundle:
        return self.finalize(meaning, situation, self.evaluate_mode(meaning, situation))
