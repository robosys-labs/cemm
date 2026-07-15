from pathlib import Path

from cemm.kernel.boot.v343 import load_v343_package
from cemm.kernel.model.requirements import (
    EvidenceField,
    EvidenceSpecification,
    GoalDependency,
    GoalRecord,
    GoalStatus,
    RequirementEngine,
)
from cemm.kernel.response.emission_closure import (
    EmissionEnvironment,
    SemanticEmissionGate,
)
from cemm.kernel.response.realizer import SemanticRealizer
from cemm.kernel.response.semantic_planner import (
    InformationRequestIntent,
    SemanticResponsePlanner,
)


DATA_ROOT = Path("cemm/data")


def all_competence_refs(pack):
    refs = set()
    for item in pack.lexicalizations.values():
        refs.update(item.competence_case_refs)
    for item in pack.morphemes.values():
        refs.update(item.competence_case_refs)
    for item in pack.constructions:
        refs.update(item.competence_case_refs)
    return frozenset(refs)


def all_round_trip_refs(pack):
    refs = set()
    for item in pack.lexicalizations.values():
        refs.update(item.round_trip_case_refs)
    for item in pack.morphemes.values():
        refs.update(item.round_trip_case_refs)
    for item in pack.constructions:
        refs.update(item.round_trip_case_refs)
    return frozenset(refs)


def requirement_assessment():
    goal = GoalRecord(
        goal_id="goal:learn:x",
        holder_ref="self",
        desired_proposition_ref="prop:definition_active:x",
        context_ref="dialogue:1",
        status=GoalStatus.ACTIVE,
        provenance_refs=("gap:x",),
    )
    spec = EvidenceSpecification(
        specification_id="spec:x",
        target_ref="opaque:en:x",
        fields=(EvidenceField("schema_family", "identifier"),),
        context_ref="dialogue:1",
        provenance_refs=("gap:x",),
    )
    dependency = GoalDependency(
        dependency_id="dependency:goal_x:spec_x",
        goal_ref=goal.goal_id,
        requirement_ref=spec.specification_id,
        context_ref="dialogue:1",
        provenance_refs=("planner:learning",),
    )
    return RequirementEngine().assess(
        goals=(goal,),
        dependencies=(dependency,),
        specifications=(spec,),
        evidence=(),
        revision_fingerprint="revision:1",
    )[0]


def plan(language):
    assessment = requirement_assessment()
    return SemanticResponsePlanner().plan_requirement_request(
        InformationRequestIntent(
            intent_id="intent:request:x",
            requester_ref="self",
            addressee_ref="user",
            requirement_assessment_ref=assessment.assessment_id,
            requirement_ref=assessment.requirement_ref,
            goal_ref=assessment.goal_ref,
            target_ref="opaque:en:x",
            target_surface="x",
            context_ref="dialogue:1",
            provenance_refs=("gap:x",),
        ),
        (assessment,),
        language_tag=language,
    ), assessment


def environment(package, pack, assessment, *, include_round_trip=True):
    return EmissionEnvironment(
        environment_fingerprint="env:1",
        grounding_refs=frozenset({"gap:x", assessment.assessment_id}),
        active_schema_refs=frozenset({
            "foundation:predicate:requires_for_goal:v1",
            "boot:schema:information_object:v1",
            "boot:schema:evidence_specification:v1",
            "boot:schema:goal:v1",
        }),
        passed_competence_case_refs=all_competence_refs(pack),
        passed_round_trip_case_refs=(
            all_round_trip_refs(pack) if include_round_trip else frozenset()
        ),
        requirement_assessments=(assessment,),
    )


def test_need_statement_is_impossible_without_live_assessment():
    package = load_v343_package(DATA_ROOT)
    semantic_pack = package.language_packs["en"]
    plan_value, assessment = plan("en")
    env = environment(package, semantic_pack.realization, assessment)
    env = EmissionEnvironment(
        environment_fingerprint=env.environment_fingerprint,
        grounding_refs=env.grounding_refs,
        active_schema_refs=env.active_schema_refs,
        passed_competence_case_refs=env.passed_competence_case_refs,
        passed_round_trip_case_refs=env.passed_round_trip_case_refs,
        requirement_assessments=(),
    )
    proof = SemanticEmissionGate(
        package.foundations,
        package.self_claim_authorizer,
    ).authorize(plan_value, semantic_pack.realization, env)
    assert not proof.authorized
    assert "missing_live_goal_requirement_assessment" in proof.blocker_refs


def test_missing_information_grounding_blocks_surface():
    package = load_v343_package(DATA_ROOT)
    semantic_pack = package.language_packs["en"]
    plan_value, assessment = plan("en")
    env = environment(package, semantic_pack.realization, assessment)
    env = EmissionEnvironment(
        environment_fingerprint=env.environment_fingerprint,
        grounding_refs=env.grounding_refs,
        active_schema_refs=frozenset({
            "foundation:predicate:requires_for_goal:v1"
        }),
        passed_competence_case_refs=env.passed_competence_case_refs,
        passed_round_trip_case_refs=env.passed_round_trip_case_refs,
        requirement_assessments=env.requirement_assessments,
    )
    proof = SemanticEmissionGate(
        package.foundations,
        package.self_claim_authorizer,
    ).authorize(plan_value, semantic_pack.realization, env)
    assert not proof.authorized
    assert any(
        blocker.startswith("lexicalization_ungrounded:lex:en:information")
        for blocker in proof.blocker_refs
    )


def test_round_trip_competence_is_mandatory():
    package = load_v343_package(DATA_ROOT)
    semantic_pack = package.language_packs["en"]
    plan_value, assessment = plan("en")
    env = environment(
        package, semantic_pack.realization, assessment,
        include_round_trip=False,
    )
    proof = SemanticEmissionGate(
        package.foundations,
        package.self_claim_authorizer,
    ).authorize(plan_value, semantic_pack.realization, env)
    assert not proof.authorized
    assert any("round_trip_unproven" in blocker for blocker in proof.blocker_refs)


def test_english_and_french_realize_same_semantic_plan_shape():
    package = load_v343_package(DATA_ROOT)
    gate = SemanticEmissionGate(
        package.foundations,
        package.self_claim_authorizer,
    )
    outputs = {}
    predicate_roles = {}
    for language in ("en", "fr"):
        plan_value, assessment = plan(language)
        realization_pack = package.language_packs[language].realization
        proof = gate.authorize(
            plan_value,
            realization_pack,
            environment(package, realization_pack, assessment),
        )
        assert proof.authorized, proof.blocker_refs
        message = SemanticRealizer().realize(
            plan_value, proof, realization_pack
        )
        assert message.surface_text
        assert sum(len(span.surface) for span in message.coverage) == len(
            message.surface_text
        )
        outputs[language] = message.surface_text
        predicate_roles[language] = (
            plan_value.clauses[0].predicate_key,
            tuple(role.role_key for role in plan_value.clauses[0].roles),
        )
    assert predicate_roles["en"] == predicate_roles["fr"]
    assert outputs["en"] != outputs["fr"]
