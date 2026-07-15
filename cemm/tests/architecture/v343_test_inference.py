from cemm.kernel.inference.engine import BoundedInferenceEngine
from cemm.kernel.inference.rule_model import (
    CausalWarrant,
    CycleClass,
    ExistentialDeclaration,
    InferenceBudget,
    RuleAtom,
    RuleStrength,
    SemanticFact,
    SemanticRule,
)


def test_subkind_inheritance_reaches_fixed_point():
    facts = (
        SemanticFact(
            "fact:instance", "instance_of",
            {"entity":"self","kind":"software_system"},
            "actual",
        ),
        SemanticFact(
            "fact:subkind", "subkind_of",
            {"child_kind":"software_system","parent_kind":"agent"},
            "actual",
        ),
    )
    rule = SemanticRule(
        rule_id="rule:instance_subkind",
        premises=(
            RuleAtom("instance_of", {"entity":"$x","kind":"$a"}),
            RuleAtom("subkind_of", {"child_kind":"$a","parent_kind":"$b"}),
        ),
        conclusions=(
            RuleAtom("instance_of", {"entity":"$x","kind":"$b"}),
        ),
        strength=RuleStrength.STRICT,
        cycle_class=CycleClass.POSITIVE_MONOTONE,
    )
    outcome = BoundedInferenceEngine().infer(
        seed_facts=facts,
        rules=(rule,),
        budget=InferenceBudget(wall_clock_ms=100),
        dependency_fingerprint="deps:1",
    )
    assert outcome.status == "fixed_point"
    assert any(
        fact.roles == {"entity":"self","kind":"agent"}
        for fact in outcome.derived_facts
    )


def test_kinship_rule_creates_existential_constraint_not_a_person():
    fact = SemanticFact(
        "fact:affinal",
        "mother_in_law_of",
        {"parent":"person:m","relative":"person:x"},
        "actual",
        evidence_refs=("user:claim",),
    )
    rule = SemanticRule(
        rule_id="rule:affinal_spouse_exists",
        premises=(
            RuleAtom(
                "mother_in_law_of",
                {"parent":"$m","relative":"$x"},
            ),
        ),
        conclusions=(
            RuleAtom(
                "spouse_or_partner_of",
                {"partner":"?p","relative":"$x"},
            ),
        ),
        existential_declarations=(
            ExistentialDeclaration("?p", entity_kind_ref="person"),
        ),
        strength=RuleStrength.DEFEASIBLE,
        cycle_class=CycleClass.STRATIFIED_DEFEASIBLE,
        confidence=0.8,
    )
    outcome = BoundedInferenceEngine().infer(
        seed_facts=(fact,),
        rules=(rule,),
        budget=InferenceBudget(wall_clock_ms=100),
        dependency_fingerprint="deps:kinship",
    )
    assert outcome.derived_facts == ()
    assert len(outcome.existential_constraints) == 1
    assert outcome.existential_constraints[0].variable == "?p"


def test_cohabitation_is_defeasible_not_strict():
    fact = SemanticFact(
        "fact:spouse",
        "spouse_or_partner_of",
        {"partner":"person:p","relative":"person:x"},
        "actual",
    )
    rule = SemanticRule(
        rule_id="rule:spouse_cohabitation_default",
        premises=(
            RuleAtom(
                "spouse_or_partner_of",
                {"partner":"$p","relative":"$x"},
            ),
        ),
        conclusions=(
            RuleAtom(
                "cohabits_with",
                {"left":"$p","right":"$x"},
            ),
        ),
        strength=RuleStrength.DEFEASIBLE,
        cycle_class=CycleClass.STRATIFIED_DEFEASIBLE,
        confidence=0.7,
    )
    outcome = BoundedInferenceEngine().infer(
        seed_facts=(fact,),
        rules=(rule,),
        budget=InferenceBudget(wall_clock_ms=100),
        dependency_fingerprint="deps:cohabitation",
    )
    assert outcome.derived_facts[0].strength is RuleStrength.DEFEASIBLE
    assert outcome.derived_facts[0].confidence < 0.7


def test_sensitive_probabilistic_rule_is_disabled_by_policy():
    fact = SemanticFact(
        "fact:relationship",
        "spouse_or_partner_of",
        {"partner":"person:p","relative":"person:x"},
        "actual",
    )
    rule = SemanticRule(
        rule_id="rule:sensitive_association",
        premises=(
            RuleAtom(
                "spouse_or_partner_of",
                {"partner":"$p","relative":"$x"},
            ),
        ),
        conclusions=(
            RuleAtom(
                "sensitive_relationship_state",
                {"left":"$p","right":"$x"},
            ),
        ),
        strength=RuleStrength.PROBABILISTIC,
        cycle_class=CycleClass.STRATIFIED_DEFEASIBLE,
        causal_warrant=CausalWarrant.PREDICTIVE_ASSOCIATION,
        sensitivity="sensitive",
        enabled_by_default=True,
    )
    outcome = BoundedInferenceEngine().infer(
        seed_facts=(fact,),
        rules=(rule,),
        budget=InferenceBudget(
            wall_clock_ms=100,
            allow_sensitive=False,
        ),
        dependency_fingerprint="deps:sensitive",
    )
    assert outcome.derived_facts == ()
