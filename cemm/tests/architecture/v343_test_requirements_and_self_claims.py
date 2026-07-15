from pathlib import Path

from cemm.kernel.boot.v343 import load_v343_package
from cemm.kernel.model.emission import (
    PlannedClause,
    SemanticRoleValue,
    UseMode,
)
from cemm.kernel.model.requirements import (
    EvidenceField,
    EvidenceSpecification,
    GoalDependency,
    GoalRecord,
    GoalStatus,
    RequirementEngine,
    RequirementEvidence,
    RequirementStatus,
)


DATA_ROOT = Path("cemm/data")


def fixtures():
    goal = GoalRecord(
        goal_id="goal:learn:x",
        holder_ref="self",
        desired_proposition_ref="prop:definition_active:x",
        context_ref="dialogue:1",
        status=GoalStatus.ACTIVE,
        provenance_refs=("gap:x",),
    )
    specification = EvidenceSpecification(
        specification_id="spec:x",
        target_ref="opaque:en:x",
        fields=(
            EvidenceField("schema_family", "identifier"),
            EvidenceField("constitutive_pattern", "semantic_pattern"),
        ),
        context_ref="dialogue:1",
        provenance_refs=("gap:x",),
    )
    dependency = GoalDependency(
        dependency_id="dependency:goal_x:spec_x",
        goal_ref=goal.goal_id,
        requirement_ref=specification.specification_id,
        context_ref="dialogue:1",
        provenance_refs=("planner:learn_definition",),
    )
    return goal, specification, dependency


def test_no_live_goal_means_no_requirement():
    _, specification, dependency = fixtures()
    assessments = RequirementEngine().assess(
        goals=(),
        dependencies=(dependency,),
        specifications=(specification,),
        evidence=(),
        revision_fingerprint="r1",
    )
    assert assessments == ()


def test_unsatisfied_goal_dependency_licenses_requirement_claim():
    goal, specification, dependency = fixtures()
    assessment = RequirementEngine().assess(
        goals=(goal,),
        dependencies=(dependency,),
        specifications=(specification,),
        evidence=(),
        revision_fingerprint="r1",
    )[0]
    assert assessment.status is RequirementStatus.UNSATISFIED
    assert assessment.licenses_requirement_claim


def test_satisfied_specification_removes_requirement_claim():
    goal, specification, dependency = fixtures()
    evidence = RequirementEvidence(
        evidence_id="evidence:x",
        specification_ref=specification.specification_id,
        supplied_field_keys=frozenset(
            {"schema_family", "constitutive_pattern"}
        ),
        context_ref="dialogue:1",
        source_ref="independent:test",
    )
    assessment = RequirementEngine().assess(
        goals=(goal,),
        dependencies=(dependency,),
        specifications=(specification,),
        evidence=(evidence,),
        revision_fingerprint="r2",
    )[0]
    assert assessment.status is RequirementStatus.SATISFIED
    assert not assessment.licenses_requirement_claim


def test_self_need_claim_fails_without_requirement_assessment():
    package = load_v343_package(DATA_ROOT)
    clause = PlannedClause(
        clause_id="clause:need",
        predicate_key="requires_for_goal",
        roles=(
            SemanticRoleValue(
                "requirer", "self", "referent",
                provenance_refs=("goal:x",),
            ),
            SemanticRoleValue(
                "requirement", "spec:x", "referent",
                semantic_key="evidence_specification",
                provenance_refs=("spec:x",),
            ),
            SemanticRoleValue(
                "goal", "goal:x", "referent",
                semantic_key="goal",
                provenance_refs=("goal:x",),
            ),
            SemanticRoleValue(
                "target", "opaque:en:x", "referent",
                surface_hint="x", use_mode=UseMode.MENTION,
                provenance_refs=("surface:x",),
            ),
            SemanticRoleValue(
                "context", "dialogue:1", "context",
                provenance_refs=("context:1",),
            ),
        ),
        communicative_force="request",
        context_ref="dialogue:1",
        provenance_refs=("gap:x",),
    )
    proof = package.self_claim_authorizer.authorize(
        clause,
        evidence=(),
        requirement_assessments=(),
    )
    assert proof is not None
    assert not proof.authorized
    assert "missing_live_goal_requirement_assessment" in proof.blocker_refs
