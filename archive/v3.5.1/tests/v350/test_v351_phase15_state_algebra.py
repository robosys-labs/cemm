from __future__ import annotations

import pytest

from cemm.v350.csir.model import ExactAuthorityPin
from cemm.v350.state import (
    ProbabilityPointV351, ProcessStatus, RelationStateRoleBindingV351, RelationStateSignatureV351,
    StateAlgebraV351, StateDomainContractV351,
    StateDomainKind, StateModelError, StateOperandV351, StateTransformExpression,
    StateTransformOperator, StateValueV351,
)


def pin(kind: str, ref: str, rev: int = 1) -> ExactAuthorityPin:
    return ExactAuthorityPin(kind, "test", ref, rev, f"sha:{kind}:{ref}:{rev}", "global")


def resolve(operand):
    return operand.constant


def test_all_eight_state_domain_families_are_typed_not_parallel_ontologies():
    low, mid, high = (pin("state_value", x) for x in ("low", "mid", "high"))
    relation = pin("relation", "located_in")
    located = pin("semantic_role", "located")
    container = pin("semantic_role", "container")
    process = pin("process", "transfer")
    domains = (
        StateDomainContractV351("d:cat", 1, StateDomainKind.CATEGORICAL, value_pins=(low, mid, high)),
        StateDomainContractV351("d:ord", 1, StateDomainKind.ORDERED, value_pins=(low, mid, high)),
        StateDomainContractV351("d:cont", 1, StateDomainKind.CONTINUOUS, lower_bound=0, upper_bound=100),
        StateDomainContractV351("d:vec", 1, StateDomainKind.VECTOR, vector_size=3),
        StateDomainContractV351(
            "d:rel", 1, StateDomainKind.RELATIONAL,
            relation_pins=(relation,), relation_role_pins=(located, container),
            relation_signatures=(RelationStateSignatureV351(relation, (located, container)),),
        ),
        StateDomainContractV351("d:set", 1, StateDomainKind.SET, maximum_set_size=4),
        StateDomainContractV351("d:proc", 1, StateDomainKind.PROCESS, process_pins=(process,)),
        StateDomainContractV351(
            "d:prob", 1, StateDomainKind.PROBABILISTIC,
            support_domain_kind=StateDomainKind.CATEGORICAL, value_pins=(low, high),
        ),
    )
    values = (
        StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=low),
        StateValueV351(StateDomainKind.ORDERED, categorical_pin=mid),
        StateValueV351(StateDomainKind.CONTINUOUS, scalar_value=42),
        StateValueV351(StateDomainKind.VECTOR, vector_value=(1, 2, 3)),
        StateValueV351(
            StateDomainKind.RELATIONAL, relation_pin=relation,
            relation_bindings=(
                RelationStateRoleBindingV351(located, "r:a"),
                RelationStateRoleBindingV351(container, "r:b"),
            ),
        ),
        StateValueV351(StateDomainKind.SET, set_members=("r:a", "r:b")),
        StateValueV351(StateDomainKind.PROCESS, process_pin=process, process_status=ProcessStatus.ACTIVE, process_progress=.25),
        StateValueV351(
            StateDomainKind.PROBABILISTIC,
            probability_mass=(
                ProbabilityPointV351(StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=low), .2),
                ProbabilityPointV351(StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=high), .8),
            ),
        ),
    )
    algebra = StateAlgebraV351()
    for domain, value in zip(domains, values):
        algebra.validate_value(domain, value)
        assert value.value_ref.startswith("state-value-occurrence:")


def test_order_shift_uses_exact_reviewed_order_not_guessed_numeric_labels():
    low, mid, high = (pin("state_value", x) for x in ("low", "middle", "high"))
    domain = StateDomainContractV351("dimension:rank", 1, StateDomainKind.ORDERED, value_pins=(low, mid, high))
    current = StateValueV351(StateDomainKind.ORDERED, categorical_pin=mid)
    expr = StateTransformExpression(
        StateTransformOperator.ORDER_SHIFT,
        (StateOperandV351(kind="constant", constant=1.0),),
    )
    result = StateAlgebraV351().apply(domain, current, expr, resolve_operand=resolve)
    assert result.categorical_pin.key == high.key


def test_manifold_forbids_silent_euclidean_math_and_requires_exact_operator_evaluator():
    manifold = pin("manifold", "sphere")
    domain = StateDomainContractV351("dimension:pose", 1, StateDomainKind.VECTOR, vector_size=3, manifold_pin=manifold)
    current = StateValueV351(StateDomainKind.VECTOR, vector_value=(1, 0, 0))
    with pytest.raises(StateModelError, match="not authorized on a manifold"):
        StateAlgebraV351().apply(
            domain, current,
            StateTransformExpression(StateTransformOperator.VECTOR_ADD, (StateOperandV351(kind="constant", constant=(0.0, 1.0, 0.0)),)),
            resolve_operand=resolve,
        )
    op = pin("state_operator", "rotate")
    expr = StateTransformExpression(
        StateTransformOperator.MANIFOLD_MAP,
        (StateOperandV351(kind="constant", constant=(0.0, 1.0, 0.0)),),
        external_operator_pin=op,
    )
    with pytest.raises(StateModelError, match="installed exact evaluator"):
        StateAlgebraV351().apply(domain, current, expr, resolve_operand=resolve)


def test_probability_distribution_is_not_renormalized_from_invalid_mass():
    a, b = pin("state_value", "a"), pin("state_value", "b")
    with pytest.raises(StateModelError, match="sum to 1"):
        StateValueV351(
            StateDomainKind.PROBABILISTIC,
            probability_mass=(
                ProbabilityPointV351(StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=a), .2),
                ProbabilityPointV351(StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=b), .2),
            ),
        )


def test_probability_support_is_typed_by_the_same_underlying_state_algebra():
    allowed = pin("state_value", "allowed")
    forbidden = pin("state_value", "forbidden")
    domain = StateDomainContractV351(
        "dimension:uncertain-category", 1, StateDomainKind.PROBABILISTIC,
        support_domain_kind=StateDomainKind.CATEGORICAL, value_pins=(allowed,),
    )
    distribution = StateValueV351(
        StateDomainKind.PROBABILISTIC,
        probability_mass=(
            ProbabilityPointV351(
                StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=forbidden), 1.0
            ),
        ),
    )
    with pytest.raises(StateModelError, match="outside exact domain value authority"):
        StateAlgebraV351().validate_value(domain, distribution)


def test_unit_bearing_addition_requires_typed_exact_unit_operand():
    unit = pin("unit", "meter")
    domain = StateDomainContractV351(
        "dimension:length", 1, StateDomainKind.CONTINUOUS, unit_pin=unit
    )
    current = StateValueV351(
        StateDomainKind.CONTINUOUS, scalar_value=10.0, unit_pin=unit
    )
    raw = StateTransformExpression(
        StateTransformOperator.ADD,
        (StateOperandV351(kind="constant", constant=2.0),),
    )
    with pytest.raises(StateModelError, match="unit-bearing additive"):
        StateAlgebraV351().apply(domain, current, raw, resolve_operand=resolve)
    typed = StateTransformExpression(
        StateTransformOperator.ADD,
        (StateOperandV351(
            kind="constant",
            constant=StateValueV351(
                StateDomainKind.CONTINUOUS, scalar_value=2.0, unit_pin=unit
            ),
        ),),
    )
    result = StateAlgebraV351().apply(domain, current, typed, resolve_operand=resolve)
    assert result.scalar_value == 12.0
    assert result.unit_pin.key == unit.key


def test_categorical_transition_assignment_requires_exact_value_inventory():
    value = pin("state_value", "candidate")
    domain = StateDomainContractV351("dimension:legacy-cat", 1, StateDomainKind.CATEGORICAL)
    expr = StateTransformExpression(
        StateTransformOperator.ASSIGN,
        (StateOperandV351(
            kind="constant",
            constant=StateValueV351(StateDomainKind.CATEGORICAL, categorical_pin=value),
        ),),
    )
    with pytest.raises(StateModelError, match="exact reviewed value_pins"):
        StateAlgebraV351().apply(domain, None, expr, resolve_operand=resolve)


def test_semantic_state_value_identity_does_not_depend_on_evidence_lineage():
    value_pin = pin("state_value", "same")
    left = StateValueV351(
        StateDomainKind.CATEGORICAL, categorical_pin=value_pin,
        evidence_refs=("evidence:left",),
    )
    right = StateValueV351(
        StateDomainKind.CATEGORICAL, categorical_pin=value_pin,
        evidence_refs=("evidence:right",),
    )
    assert left.value_ref == right.value_ref
    assert left.document() != right.document()


def test_exact_order_comparison_uses_reviewed_order_not_numeric_coercion():
    low, mid, high = (pin("state_value", x) for x in ("low-order", "mid-order", "high-order"))
    domain = StateDomainContractV351(
        "dimension:order-compare", 1, StateDomainKind.ORDERED,
        value_pins=(low, mid, high),
    )
    algebra = StateAlgebraV351()
    assert algebra.compare(
        domain,
        StateValueV351(StateDomainKind.ORDERED, categorical_pin=low),
        StateValueV351(StateDomainKind.ORDERED, categorical_pin=high),
    ) == -1


def test_relational_state_roundtrip_preserves_exact_role_bindings_from_mapping_and_semantic_tuple():
    from dataclasses import asdict
    from cemm.v350.state.entitlement_v351 import state_value_from_document
    from cemm.v350.state.codec_v351 import _state_value

    relation = pin("relation", "contains")
    container = pin("semantic_role", "container")
    content = pin("semantic_role", "content")
    value = StateValueV351(
        StateDomainKind.RELATIONAL, relation_pin=relation,
        relation_bindings=(
            RelationStateRoleBindingV351(container, "r:box"),
            RelationStateRoleBindingV351(content, "r:item"),
        ),
    )
    semantic = state_value_from_document(value.document())
    canonical = _state_value(asdict(value))
    assert semantic.value_ref == value.value_ref
    assert canonical.value_ref == value.value_ref
    assert tuple((b.role_pin.key, b.participant_ref) for b in canonical.relation_bindings) == tuple(
        (b.role_pin.key, b.participant_ref) for b in value.relation_bindings
    )


def test_relational_state_requires_exact_predicate_role_signature_not_role_union_subset():
    relation_a = pin("relation", "r:a")
    relation_b = pin("relation", "r:b")
    left = pin("semantic_role", "left")
    right = pin("semantic_role", "right")
    owner = pin("semantic_role", "owner")
    owned = pin("semantic_role", "owned")
    domain = StateDomainContractV351(
        "dimension:relation", 1, StateDomainKind.RELATIONAL,
        relation_pins=(relation_a, relation_b), relation_role_pins=(left, right, owner, owned),
        relation_signatures=(
            RelationStateSignatureV351(relation_a, (left, right)),
            RelationStateSignatureV351(relation_b, (owner, owned)),
        ),
    )
    malformed = StateValueV351(
        StateDomainKind.RELATIONAL, relation_pin=relation_a,
        relation_bindings=(
            RelationStateRoleBindingV351(left, "r:x"),
            RelationStateRoleBindingV351(owner, "r:y"),
        ),
    )
    with pytest.raises(StateModelError, match="exactly the authorized semantic role signature"):
        StateAlgebraV351().validate_value(domain, malformed)
