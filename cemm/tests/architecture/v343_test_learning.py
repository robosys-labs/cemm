from cemm.kernel.learning.grounded_compiler import (
    AttachmentKind,
    CompetenceCaseProvenance,
    ContributionKind,
    GroundedLearningCompiler,
    GroundingDependency,
    LearningContribution,
    OperationalAttachment,
)


def contribution(field, value):
    return LearningContribution(
        contribution_id=f"contrib:{field}:{value}",
        field_key=field,
        value_ref=value,
        contribution_kind=ContributionKind.ASSERTED,
        evidence_ref="evidence:user_turn",
        source_ref="user",
    )


def test_parent_label_alone_does_not_activate_concept():
    artifact = GroundedLearningCompiler().compile(
        target_semantic_key="opaque:en:machine",
        contributions=(
            contribution("schema_family", "entity_kind"),
            contribution("parent_kind", "digital_entity"),
        ),
        dependencies=(
            GroundingDependency(
                "dependency:digital",
                "digital_entity",
                "definition",
            ),
        ),
        attachments=(),
        competence_cases=(),
        active_anchor_refs=frozenset({"digital_entity"}),
        revision=1,
    )
    assert artifact.status == "staged"
    assert "missing_operational_attachment" in artifact.blocker_refs
    assert "identity_or_membership_pattern" in artifact.unresolved_field_keys


def test_operational_attachment_and_independent_case_enable_structure():
    artifact = GroundedLearningCompiler().compile(
        target_semantic_key="opaque:en:machine",
        contributions=(
            contribution("schema_family", "entity_kind"),
            contribution(
                "identity_or_membership_pattern",
                "pattern:machine:operational_system",
            ),
        ),
        dependencies=(
            GroundingDependency(
                "dependency:software_system",
                "software_system",
                "definition",
            ),
        ),
        attachments=(
            OperationalAttachment(
                attachment_id="attachment:machine:operation",
                attachment_kind=AttachmentKind.OPERATION_PORT,
                semantic_pattern_ref="pattern:machine:performs_designed_operation",
                role_path_refs=("holder","operation"),
                foundation_anchor_refs=(
                    "foundation:predicate:capable_of:v1",
                ),
                evidence_refs=("evidence:user_turn",),
            ),
        ),
        competence_cases=(
            CompetenceCaseProvenance(
                case_id="case:machine:contrast",
                case_source_ref="independent:curated",
                teaching_source_refs=("user",),
                generated_from_teaching_turn=False,
                independent_lineage_ref="independent:curated",
            ),
        ),
        active_anchor_refs=frozenset({
            "software_system",
            "foundation:predicate:capable_of:v1",
        }),
        revision=1,
    )
    assert artifact.status == "structurally_executable"
    assert artifact.blocker_refs == ()


def test_self_generated_competence_does_not_certify_learning():
    artifact = GroundedLearningCompiler().compile(
        target_semantic_key="opaque:en:machine",
        contributions=(
            contribution("schema_family", "entity_kind"),
            contribution(
                "identity_or_membership_pattern",
                "pattern:machine:operational_system",
            ),
        ),
        dependencies=(),
        attachments=(
            OperationalAttachment(
                attachment_id="attachment:machine:state",
                attachment_kind=AttachmentKind.CONSTITUTIVE_STATE,
                semantic_pattern_ref="pattern:machine:operational",
                role_path_refs=("holder","state"),
                foundation_anchor_refs=("foundation:predicate:has_state:v1",),
                evidence_refs=("evidence:user_turn",),
            ),
        ),
        competence_cases=(
            CompetenceCaseProvenance(
                case_id="case:generated_from_same_turn",
                case_source_ref="user",
                teaching_source_refs=("user",),
                generated_from_teaching_turn=True,
                independent_lineage_ref="",
            ),
        ),
        active_anchor_refs=frozenset({
            "foundation:predicate:has_state:v1"
        }),
        revision=1,
    )
    assert "missing_independent_competence_case" in artifact.blocker_refs
