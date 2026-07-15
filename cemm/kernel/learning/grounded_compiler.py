"""Schema-family-aware recursive learning with operational attachment."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable
from uuid import uuid4


class SchemaFamily(str, Enum):
    ENTITY_KIND = "entity_kind"
    ROLE = "role"
    PREDICATE = "predicate"
    STATE_DIMENSION = "state_dimension"
    EVENT_KIND = "event_kind"
    OPERATION = "operation"
    RULE = "rule"
    LEXICALIZATION = "lexicalization"
    CONSTRUCTION = "construction"
    REALIZATION = "realization"


class ContributionKind(str, Enum):
    ASSERTED = "asserted"
    OBSERVED = "observed"
    ENTAILED = "entailed"
    INHERITED = "inherited"
    HYPOTHESIZED = "hypothesized"
    DEFAULTED = "defaulted"
    INDUCED = "induced"
    ADAPTER_SUPPLIED = "adapter_supplied"
    BOOT_SUPPLIED = "boot_supplied"


class AttachmentKind(str, Enum):
    CONSTITUTIVE_STATE = "constitutive_state"
    CONSTITUTIVE_RELATION = "constitutive_relation"
    CONSTITUTIVE_EVENT = "constitutive_event"
    IDENTITY_CRITERION = "identity_criterion"
    OPERATION_PORT = "operation_port"
    OBSERVATION_DISCRIMINATOR = "observation_discriminator"


@dataclass(frozen=True, slots=True)
class LearningContribution:
    contribution_id: str
    field_key: str
    value_ref: str
    contribution_kind: ContributionKind
    evidence_ref: str
    source_ref: str
    confidence: float = 1.0
    context_ref: str = ""
    valid_time_ref: str = ""


@dataclass(frozen=True, slots=True)
class GroundingDependency:
    dependency_id: str
    target_schema_ref: str
    dependency_kind: str
    required: bool = True
    dependency_revision_fingerprint: str = ""


@dataclass(frozen=True, slots=True)
class OperationalAttachment:
    attachment_id: str
    attachment_kind: AttachmentKind
    semantic_pattern_ref: str
    role_path_refs: tuple[str, ...]
    foundation_anchor_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    required: bool = True


@dataclass(frozen=True, slots=True)
class CompetenceCaseProvenance:
    case_id: str
    case_source_ref: str
    teaching_source_refs: tuple[str, ...]
    generated_from_teaching_turn: bool
    independent_lineage_ref: str = ""

    @property
    def independent(self) -> bool:
        return (
            not self.generated_from_teaching_turn
            and bool(self.independent_lineage_ref)
            and self.independent_lineage_ref not in self.teaching_source_refs
        )


@dataclass(frozen=True, slots=True)
class CompiledSchemaArtifact:
    artifact_id: str
    target_semantic_key: str
    schema_family: SchemaFamily | None
    fields: dict[str, tuple[str, ...]]
    dependencies: tuple[GroundingDependency, ...]
    operational_attachments: tuple[OperationalAttachment, ...]
    unresolved_field_keys: tuple[str, ...]
    blocker_refs: tuple[str, ...]
    status: str
    provenance_refs: tuple[str, ...]
    revision: int


class GroundedLearningCompiler:
    FAMILY_REQUIRED_FIELDS = {
        SchemaFamily.ENTITY_KIND: frozenset({"identity_or_membership_pattern"}),
        SchemaFamily.ROLE: frozenset({"holder_constraint", "context_pattern"}),
        SchemaFamily.PREDICATE: frozenset({"role_signatures", "query_behavior"}),
        SchemaFamily.STATE_DIMENSION: frozenset({"holder_kinds", "value_type"}),
        SchemaFamily.EVENT_KIND: frozenset({"participant_roles", "occurrence_pattern"}),
        SchemaFamily.OPERATION: frozenset({"input_ports", "output_ports", "failure_modes"}),
        SchemaFamily.RULE: frozenset({"premises", "conclusions", "strength"}),
        SchemaFamily.LEXICALIZATION: frozenset({"language_tag", "semantic_schema_ref"}),
        SchemaFamily.CONSTRUCTION: frozenset({"language_tag", "semantic_projection"}),
        SchemaFamily.REALIZATION: frozenset({"language_tag", "coverage_contract"}),
    }

    def compile(
        self,
        *,
        target_semantic_key: str,
        contributions: Iterable[LearningContribution],
        dependencies: Iterable[GroundingDependency],
        attachments: Iterable[OperationalAttachment],
        competence_cases: Iterable[CompetenceCaseProvenance],
        active_anchor_refs: frozenset[str],
        revision: int,
    ) -> CompiledSchemaArtifact:
        contribution_values: dict[str, list[str]] = {}
        provenance: list[str] = []
        for item in contributions:
            contribution_values.setdefault(item.field_key, []).append(item.value_ref)
            provenance.extend((item.contribution_id, item.evidence_ref, item.source_ref))

        family_values = contribution_values.get("schema_family", ())
        family = None
        blockers: list[str] = []
        if len(set(family_values)) == 1:
            try:
                family = SchemaFamily(family_values[0])
            except ValueError:
                blockers.append(f"unsupported_schema_family:{family_values[0]}")
        elif not family_values:
            blockers.append("missing_schema_family")
        else:
            blockers.append("conflicting_schema_family")

        dependency_tuple = tuple(dependencies)
        attachment_tuple = tuple(attachments)
        fields = {
            key: tuple(dict.fromkeys(values))
            for key, values in contribution_values.items()
        }

        required_fields = self.FAMILY_REQUIRED_FIELDS.get(family, frozenset())
        missing_fields = tuple(
            sorted(field for field in required_fields if not fields.get(field))
        )

        if not attachment_tuple:
            blockers.append("missing_operational_attachment")
        elif not any(
            attachment.foundation_anchor_refs
            and set(attachment.foundation_anchor_refs) <= active_anchor_refs
            for attachment in attachment_tuple
        ):
            blockers.append("operational_attachment_not_foundation_anchored")

        for dependency in dependency_tuple:
            if dependency.required and dependency.target_schema_ref not in active_anchor_refs:
                blockers.append(
                    f"unresolved_required_dependency:{dependency.target_schema_ref}"
                )

        independent_cases = tuple(case for case in competence_cases if case.independent)
        if not independent_cases:
            blockers.append("missing_independent_competence_case")

        status = (
            "candidate"
            if family is None
            else "staged"
            if missing_fields or blockers
            else "structurally_executable"
        )
        return CompiledSchemaArtifact(
            artifact_id=f"learned:{target_semantic_key}:{uuid4().hex[:12]}:v{revision}",
            target_semantic_key=target_semantic_key,
            schema_family=family,
            fields=fields,
            dependencies=dependency_tuple,
            operational_attachments=attachment_tuple,
            unresolved_field_keys=missing_fields,
            blocker_refs=tuple(dict.fromkeys(blockers)),
            status=status,
            provenance_refs=tuple(dict.fromkeys(provenance)),
            revision=revision,
        )
