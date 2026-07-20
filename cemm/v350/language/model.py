"""Language evidence records and runtime form-lattice contracts for CEMM v3.5.

Language forms are observations.  Lexical senses are revisioned mappings from
forms to semantic schemas.  Neither form strings nor language-specific grammar
may become kernel semantic branches.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from ..schema.model import (
    OpenBindingPurpose, PortFillerClass, SchemaClass, SchemaLifecycleStatus,
    UseDecision, UseOperation, semantic_fingerprint,
)


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class FormKind(StrEnum):
    TOKEN = "token"
    MULTIWORD = "multiword"
    PUNCTUATION = "punctuation"
    CLITIC = "clitic"
    AFFIX = "affix"
    ZERO = "zero"
    SYMBOL = "symbol"


class SenseTargetKind(StrEnum):
    SCHEMA = "schema"
    REFERENT_TYPE = "referent_type"
    DISCOURSE = "discourse"
    OPERATOR = "operator"
    STRUCTURAL = "structural"


class SemanticContributionKind(StrEnum):
    TARGET = "target"
    REFERENTIAL = "referential"
    VARIABLE = "variable"
    RESTRICTION = "restriction"
    PROJECTION = "projection"
    SCOPE = "scope"
    ARGUMENT = "argument"
    GRAMMATICAL_FEATURE = "grammatical_feature"
    CONSTRUCTION = "construction"


class FormLexemeRelationKind(StrEnum):
    LEMMA = "lemma"
    INFLECTED = "inflected"
    SUPPLETIVE = "suppletive"
    CLITIC = "clitic"
    DERIVED = "derived"
    ZERO = "zero"


class ConstructionKind(StrEnum):
    COORDINATION = "coordination"
    COMPLEMENT = "complement"
    RELATIVE_CLAUSE = "relative_clause"
    ELLIPSIS = "ellipsis"
    IDIOM = "idiom"
    ARGUMENT_STRUCTURE = "argument_structure"


class SyntaxEvidenceKind(StrEnum):
    DEPENDENCY = "dependency"
    CONSTITUENCY = "constituency"
    ADAPTER = "adapter"


class LatticeNodeKind(StrEnum):
    OBSERVATION = "observation"
    FORM = "form"
    LEXEME = "lexeme"
    SENSE = "sense"
    CONTRIBUTION = "contribution"
    CONSTRUCTION = "construction"
    GAP = "gap"


class LatticeEdgeKind(StrEnum):
    COVERS = "covers"
    TRIGGER = "trigger"
    VARIANT = "variant"
    LEXEME = "lexeme"
    CONTRIBUTION = "contribution"
    NORMALIZATION = "normalization"
    SENSE = "sense"
    COMPOSES = "composes"
    SCOPE = "scope"
    ELLIPSIS = "ellipsis"
    LANGUAGE = "language"


@dataclass(frozen=True, slots=True)
class LanguagePackRecord:
    pack_ref: str
    language_tag: str
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    scripts: tuple[str, ...] = ()
    tokenizer_profile: str = "unicode_default"
    normalization_profile: str = "nfkc_casefold"
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.pack_ref, "pack_ref")
        _language_tag(self.language_tag)
        if self.revision < 1:
            raise ValueError("language-pack revision must be positive")
        _supersession(self.revision, self.supersedes_revision, "language pack")
        _unique(self.scripts, "scripts")
        _unique(self.source_refs, "sources")
        _unique(self.evidence_refs, "evidence")
        _unique(self.competence_case_refs, "competence cases")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.competence_case_refs:
            raise ValueError("active language pack requires competence cases")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "language pack")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("language-pack-content", {
            "language_tag": self.language_tag,
            "scripts": self.scripts,
            "tokenizer_profile": self.tokenizer_profile,
            "normalization_profile": self.normalization_profile,
            "metadata": dict(self.metadata),
        }, 64)

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("language-pack-record", self, 64)


@dataclass(frozen=True, slots=True)
class LanguageFormRecord:
    form_ref: str
    pack_ref: str
    pack_revision: int
    written_form: str
    normalized_form: str
    form_kind: FormKind = FormKind.TOKEN
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    script: str = ""
    token_count: int = 1
    feature_values: tuple[tuple[str, str], ...] = ()
    variant_of_ref: str | None = None
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.form_ref, "form_ref")
        _ref(self.pack_ref, "pack_ref")
        if self.pack_revision < 1 or self.revision < 1:
            raise ValueError("form and pack revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "language form")
        if not self.written_form:
            raise ValueError("language form requires written_form")
        if not self.normalized_form and self.form_kind != FormKind.ZERO:
            raise ValueError("non-zero form requires normalized_form")
        if self.token_count < 0 or (self.form_kind != FormKind.ZERO and self.token_count < 1):
            raise ValueError("invalid form token_count")
        if self.form_kind == FormKind.MULTIWORD and self.token_count < 2:
            raise ValueError("multiword form requires at least two tokens")
        if self.variant_of_ref is not None:
            _ref(self.variant_of_ref, "variant_of_ref")
        _unique(tuple(name for name, _ in self.feature_values), "form feature names")
        _unique(self.source_refs, "form sources")
        _unique(self.evidence_refs, "form evidence")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "language form")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("language-form-content", {
            "pack_ref": self.pack_ref,
            "pack_revision": self.pack_revision,
            "written_form": self.written_form,
            "normalized_form": self.normalized_form,
            "form_kind": self.form_kind.value,
            "script": self.script,
            "token_count": self.token_count,
            "feature_values": self.feature_values,
            "variant_of_ref": self.variant_of_ref,
            "metadata": dict(self.metadata),
        }, 64)

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("language-form-record", self, 64)


@dataclass(frozen=True, slots=True)
class LexemeRecord:
    lexeme_ref: str
    pack_ref: str
    pack_revision: int
    lemma_form_ref: str
    lemma_form_revision: int
    lexical_category: str
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    inflection_class_ref: str = ""
    feature_defaults: tuple[tuple[str, str], ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.lexeme_ref, "lexeme_ref"),
            (self.pack_ref, "pack_ref"),
            (self.lemma_form_ref, "lemma_form_ref"),
            (self.lexical_category, "lexical_category"),
        ):
            _ref(value, label)
        if min(self.pack_revision, self.lemma_form_revision, self.revision) < 1:
            raise ValueError("lexeme revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "lexeme")
        _unique(tuple(name for name, _ in self.feature_defaults), "lexeme feature defaults")
        _unique(self.source_refs, "lexeme sources")
        _unique(self.evidence_refs, "lexeme evidence")
        _unique(self.competence_case_refs, "lexeme competence cases")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.competence_case_refs:
            raise ValueError("active lexeme requires competence cases")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "lexeme")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("lexeme-content", {
            "pack_ref": self.pack_ref,
            "pack_revision": self.pack_revision,
            "lemma_form_ref": self.lemma_form_ref,
            "lemma_form_revision": self.lemma_form_revision,
            "lexical_category": self.lexical_category,
            "inflection_class_ref": self.inflection_class_ref,
            "feature_defaults": self.feature_defaults,
            "metadata": dict(self.metadata),
        }, 64)


@dataclass(frozen=True, slots=True)
class FormLexemeLinkRecord:
    link_ref: str
    form_ref: str
    form_revision: int
    lexeme_ref: str
    lexeme_revision: int
    relation_kind: FormLexemeRelationKind
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    feature_values: tuple[tuple[str, str], ...] = ()
    prior_weight: float = 1.0
    condition_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.link_ref, "form-lexeme link_ref"),
            (self.form_ref, "form_ref"),
            (self.lexeme_ref, "lexeme_ref"),
        ):
            _ref(value, label)
        if min(self.form_revision, self.lexeme_revision, self.revision) < 1:
            raise ValueError("form-lexeme revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "form-lexeme link")
        if not isfinite(self.prior_weight) or self.prior_weight <= 0:
            raise ValueError("form-lexeme prior_weight must be finite and positive")
        _unique(tuple(name for name, _ in self.feature_values), "form-lexeme feature names")
        _unique(self.condition_refs, "form-lexeme conditions")
        _unique(self.source_refs, "form-lexeme sources")
        _unique(self.evidence_refs, "form-lexeme evidence")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "form-lexeme link")


@dataclass(frozen=True, slots=True)
class LexemeSenseLinkRecord:
    link_ref: str
    lexeme_ref: str
    lexeme_revision: int
    sense_ref: str
    sense_revision: int
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    prior_weight: float = 1.0
    condition_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.link_ref, "lexeme-sense link_ref"),
            (self.lexeme_ref, "lexeme_ref"),
            (self.sense_ref, "sense_ref"),
        ):
            _ref(value, label)
        if min(self.lexeme_revision, self.sense_revision, self.revision) < 1:
            raise ValueError("lexeme-sense revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "lexeme-sense link")
        if not isfinite(self.prior_weight) or self.prior_weight <= 0:
            raise ValueError("lexeme-sense prior_weight must be finite and positive")
        _unique(self.condition_refs, "lexeme-sense conditions")
        _unique(self.source_refs, "lexeme-sense sources")
        _unique(self.evidence_refs, "lexeme-sense evidence")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "lexeme-sense link")


@dataclass(frozen=True, slots=True)
class LexicalSenseRecord:
    sense_ref: str
    pack_ref: str
    pack_revision: int
    target_kind: SenseTargetKind | None = None
    target_ref: str | None = None
    target_revision: int | None = None
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    target_schema_class: SchemaClass | None = None
    use_operation: UseOperation = UseOperation.GROUND
    lexical_category: str = ""
    frame_ref: str = ""
    argument_map: tuple[tuple[str, str], ...] = ()
    expected_type_refs: tuple[str, ...] = ()
    scope_behavior: str = "none"
    context_constraints: tuple[str, ...] = ()
    feature_constraints: tuple[tuple[str, str], ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.sense_ref, "sense_ref"), (self.pack_ref, "pack_ref")):
            _ref(value, label)
        if self.target_ref is not None:
            _ref(self.target_ref, "target_ref")
        if (self.target_kind is None) != (self.target_ref is None):
            raise ValueError("lexical sense target kind/ref must be supplied together")
        if self.pack_revision < 1 or self.revision < 1:
            raise ValueError("sense and pack revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "lexical sense")
        if self.target_revision is not None and (self.target_ref is None or self.target_revision < 1):
            raise ValueError("sense target revision must be positive")
        if self.target_kind in {
            SenseTargetKind.SCHEMA, SenseTargetKind.REFERENT_TYPE,
            SenseTargetKind.OPERATOR, SenseTargetKind.DISCOURSE,
        } and self.target_revision is None:
            raise ValueError("schema-backed lexical sense requires exact target revision")
        if self.target_kind == SenseTargetKind.OPERATOR and self.target_schema_class not in {None, SchemaClass.OPERATOR}:
            raise ValueError("operator sense target class must be operator")
        if self.target_kind == SenseTargetKind.REFERENT_TYPE and self.target_schema_class not in {None, SchemaClass.REFERENT_TYPE}:
            raise ValueError("referent-type sense target class must be referent_type")
        _unique(tuple(port for port, _ in self.argument_map), "sense argument source roles")
        _unique(self.expected_type_refs, "sense expected types")
        _unique(self.context_constraints, "sense context constraints")
        _unique(tuple(name for name, _ in self.feature_constraints), "sense feature constraints")
        _unique(self.source_refs, "sense sources")
        _unique(self.evidence_refs, "sense evidence")
        _unique(self.competence_case_refs, "sense competence cases")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.competence_case_refs:
            raise ValueError("active lexical sense requires competence cases")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "lexical sense")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("lexical-sense-content", {
            "pack_ref": self.pack_ref,
            "pack_revision": self.pack_revision,
            "target_kind": None if self.target_kind is None else self.target_kind.value,
            "target_ref": self.target_ref,
            "target_revision": self.target_revision,
            "target_schema_class": None if self.target_schema_class is None else self.target_schema_class.value,
            "use_operation": self.use_operation.value,
            "lexical_category": self.lexical_category,
            "frame_ref": self.frame_ref,
            "argument_map": self.argument_map,
            "expected_type_refs": self.expected_type_refs,
            "scope_behavior": self.scope_behavior,
            "context_constraints": self.context_constraints,
            "feature_constraints": self.feature_constraints,
            "metadata": dict(self.metadata),
        }, 64)

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("lexical-sense-record", self, 64)


@dataclass(frozen=True, slots=True)
class SemanticContributionSpecRecord:
    spec_ref: str
    pack_ref: str
    pack_revision: int
    sense_ref: str
    sense_revision: int
    contribution_kind: SemanticContributionKind
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    target_kind: SenseTargetKind | None = None
    target_ref: str | None = None
    target_revision: int | None = None
    target_schema_class: SchemaClass | None = None
    expected_filler_classes: tuple[PortFillerClass, ...] = ()
    expected_schema_classes: tuple[SchemaClass, ...] = ()
    expected_type_refs: tuple[str, ...] = ()
    open_binding_purpose: OpenBindingPurpose | None = None
    restriction_refs: tuple[str, ...] = ()
    projection_ref: str | None = None
    projection_revision: int | None = None
    role_ref: str = ""
    source_role_ref: str = ""
    scope_behavior: str = "none"
    feature_constraints: tuple[tuple[str, str], ...] = ()
    use_operation: UseOperation = UseOperation.COMPOSE
    use_decision: UseDecision = UseDecision.DENY
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.spec_ref, "semantic contribution spec_ref"),
            (self.pack_ref, "pack_ref"),
            (self.sense_ref, "sense_ref"),
        ):
            _ref(value, label)
        if min(self.pack_revision, self.sense_revision, self.revision) < 1:
            raise ValueError("semantic contribution revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "semantic contribution spec")
        if self.target_ref is not None:
            _ref(self.target_ref, "contribution target_ref")
        if (self.target_kind is None) != (self.target_ref is None):
            raise ValueError("contribution target kind/ref must be supplied together")
        if self.target_revision is not None and (self.target_ref is None or self.target_revision < 1):
            raise ValueError("contribution target revision requires a target")
        if self.contribution_kind == SemanticContributionKind.TARGET and self.target_ref is None:
            raise ValueError("TARGET contribution requires a target")
        if self.contribution_kind == SemanticContributionKind.PROJECTION and self.projection_ref is None:
            raise ValueError("PROJECTION contribution requires projection_ref")
        if (self.projection_ref is None) != (self.projection_revision is None):
            raise ValueError("projection ref/revision must be supplied together")
        if self.projection_ref is not None:
            _ref(self.projection_ref, "projection_ref")
            if self.projection_revision is None or self.projection_revision < 1:
                raise ValueError("projection revision must be positive")
        if self.contribution_kind == SemanticContributionKind.ARGUMENT and (
            not self.role_ref or not self.source_role_ref
        ):
            raise ValueError("ARGUMENT contribution requires source_role_ref and role_ref")
        if self.role_ref:
            _ref(self.role_ref, "role_ref")
        if self.source_role_ref:
            _ref(self.source_role_ref, "source_role_ref")
        _unique(self.expected_filler_classes, "contribution filler classes")
        _unique(self.expected_schema_classes, "contribution schema classes")
        _unique(self.expected_type_refs, "contribution expected types")
        _unique(self.restriction_refs, "contribution restrictions")
        _unique(tuple(name for name, _ in self.feature_constraints), "contribution feature constraints")
        _unique(self.source_refs, "contribution sources")
        _unique(self.evidence_refs, "contribution evidence")
        _unique(self.competence_case_refs, "contribution competence cases")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.competence_case_refs:
            raise ValueError("active semantic contribution requires competence cases")
        _reviewed_authority(
            self.lifecycle_status, self.source_refs, self.evidence_refs,
            "semantic contribution spec",
        )

    @property
    def executable(self) -> bool:
        return (
            self.lifecycle_status == SchemaLifecycleStatus.ACTIVE
            and self.use_decision == UseDecision.ALLOW
        )


@dataclass(frozen=True, slots=True)
class FormSenseLinkRecord:
    link_ref: str
    form_ref: str
    form_revision: int
    sense_ref: str
    sense_revision: int
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    prior_weight: float = 1.0
    register_refs: tuple[str, ...] = ()
    condition_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in ((self.link_ref, "link_ref"), (self.form_ref, "form_ref"), (self.sense_ref, "sense_ref")):
            _ref(value, label)
        if min(self.form_revision, self.sense_revision, self.revision) < 1:
            raise ValueError("form-sense revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "form-sense link")
        if not isfinite(self.prior_weight) or self.prior_weight <= 0:
            raise ValueError("form-sense prior_weight must be finite and positive")
        _unique(self.register_refs, "link registers")
        _unique(self.condition_refs, "link conditions")
        _unique(self.source_refs, "link sources")
        _unique(self.evidence_refs, "link evidence")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "form-sense link")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("form-sense-link-content", {
            "form_ref": self.form_ref,
            "form_revision": self.form_revision,
            "sense_ref": self.sense_ref,
            "sense_revision": self.sense_revision,
            "prior_weight": self.prior_weight,
            "register_refs": self.register_refs,
            "condition_refs": self.condition_refs,
            "metadata": dict(self.metadata),
        }, 64)

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("form-sense-link-record", self, 64)


@dataclass(frozen=True, slots=True)
class ConstructionSlot:
    slot_ref: str
    minimum: int = 1
    maximum: int | None = 1
    accepted_categories: tuple[str, ...] = ()
    accepted_target_classes: tuple[SchemaClass, ...] = ()
    dependency_relations: tuple[str, ...] = ()
    dependency_position: str = "either"
    anchor_to_trigger: bool = True
    constituency_labels: tuple[str, ...] = ()
    optional_when_licensed: bool = False
    semantic_port_ref: str = ""

    def __post_init__(self) -> None:
        _ref(self.slot_ref, "construction slot_ref")
        if self.minimum < 0 or (self.maximum is not None and self.maximum < self.minimum):
            raise ValueError("invalid construction slot cardinality")
        _unique(self.accepted_categories, "slot categories")
        _unique(self.accepted_target_classes, "slot target classes")
        _unique(self.dependency_relations, "slot dependency relations")
        if self.dependency_position not in {"head", "dependent", "either"}:
            raise ValueError("dependency_position must be head, dependent, or either")
        _unique(self.constituency_labels, "slot constituency labels")


@dataclass(frozen=True, slots=True)
class ConstructionRecord:
    construction_ref: str
    pack_ref: str
    pack_revision: int
    construction_kind: ConstructionKind
    slots: tuple[ConstructionSlot, ...]
    revision: int = 1
    supersedes_revision: int | None = None
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    trigger_form_refs: tuple[str, ...] = ()
    trigger_sense_refs: tuple[str, ...] = ()
    output_schema_ref: str | None = None
    output_schema_revision: int | None = None
    output_schema_class: SchemaClass | None = None
    full_sentence_pattern: bool = False
    genuine_idiom: bool = False
    preserves_gap: bool = False
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    permission_ref: str = "public"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.construction_ref, "construction_ref")
        _ref(self.pack_ref, "pack_ref")
        if min(self.pack_revision, self.revision) < 1:
            raise ValueError("construction and pack revisions must be positive")
        _supersession(self.revision, self.supersedes_revision, "construction")
        if not self.slots:
            raise ValueError("construction requires slots")
        _unique(tuple(item.slot_ref for item in self.slots), "construction slots")
        _unique(self.trigger_form_refs, "construction forms")
        _unique(self.trigger_sense_refs, "construction senses")
        if (self.output_schema_ref is None) != (self.output_schema_revision is None):
            raise ValueError("construction output schema and revision must be supplied together")
        if self.output_schema_ref is not None:
            _ref(self.output_schema_ref, "output_schema_ref")
            if self.output_schema_revision is None or self.output_schema_revision < 1:
                raise ValueError("construction output revision must be positive")
        if self.full_sentence_pattern and not (self.construction_kind == ConstructionKind.IDIOM and self.genuine_idiom):
            raise ValueError("full-sentence patterns are permitted only for genuine idioms")
        if self.genuine_idiom and self.construction_kind != ConstructionKind.IDIOM:
            raise ValueError("genuine_idiom requires idiom construction kind")
        if self.construction_kind == ConstructionKind.ELLIPSIS and not self.preserves_gap:
            raise ValueError("ellipsis construction must preserve an explicit semantic gap")
        _unique(self.source_refs, "construction sources")
        _unique(self.evidence_refs, "construction evidence")
        _unique(self.competence_case_refs, "construction competence cases")
        if self.lifecycle_status == SchemaLifecycleStatus.ACTIVE and not self.competence_case_refs:
            raise ValueError("active construction requires competence cases")
        _reviewed_authority(self.lifecycle_status, self.source_refs, self.evidence_refs, "construction")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("construction-content", {
            "pack_ref": self.pack_ref,
            "pack_revision": self.pack_revision,
            "construction_kind": self.construction_kind.value,
            "slots": self.slots,
            "trigger_form_refs": self.trigger_form_refs,
            "trigger_sense_refs": self.trigger_sense_refs,
            "output_schema_ref": self.output_schema_ref,
            "output_schema_revision": self.output_schema_revision,
            "output_schema_class": None if self.output_schema_class is None else self.output_schema_class.value,
            "full_sentence_pattern": self.full_sentence_pattern,
            "genuine_idiom": self.genuine_idiom,
            "preserves_gap": self.preserves_gap,
            "metadata": dict(self.metadata),
        }, 64)

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("construction-record", self, 64)


@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("invalid span")

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class FormObservation:
    observation_ref: str
    span: Span
    original: str
    canonical: str
    script: str
    category: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.observation_ref, "observation_ref")
        if self.span.length != len(self.original):
            raise ValueError("observation span length must equal original codepoint length")
        if not self.evidence_refs:
            raise ValueError("form observation requires evidence")


@dataclass(frozen=True, slots=True)
class LanguageEvidence:
    language_tag: str
    span: Span
    confidence: float
    source_refs: tuple[str, ...]
    competing_language_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _language_tag(self.language_tag)
        _confidence(self.confidence)
        if not self.source_refs:
            raise ValueError("language evidence requires sources")
        _unique(self.competing_language_tags, "competing languages")


@dataclass(frozen=True, slots=True)
class NormalizationEvidence:
    evidence_ref: str
    span: Span
    original: str
    proposed: str
    rule_ref: str
    confidence: float
    reversible: bool = True

    def __post_init__(self) -> None:
        _ref(self.evidence_ref, "normalization evidence_ref")
        _ref(self.rule_ref, "normalization rule_ref")
        _confidence(self.confidence)
        if not self.original:
            raise ValueError("normalization evidence requires original form")
        if not self.reversible:
            raise ValueError("colloquial normalization must remain reversible evidence")


@dataclass(frozen=True, slots=True)
class LexemeCandidate:
    candidate_ref: str
    form_candidate_ref: str
    lexeme_ref: str
    lexeme_revision: int
    language_tag: str
    confidence: float
    feature_values: tuple[tuple[str, str], ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.candidate_ref, "lexeme candidate_ref"),
            (self.form_candidate_ref, "form_candidate_ref"),
            (self.lexeme_ref, "lexeme_ref"),
        ):
            _ref(value, label)
        if self.lexeme_revision < 1:
            raise ValueError("lexeme candidate revision must be positive")
        _language_tag(self.language_tag)
        _confidence(self.confidence)
        _unique(tuple(name for name, _ in self.feature_values), "lexeme candidate feature names")
        if not self.evidence_refs:
            raise ValueError("lexeme candidate requires evidence")


@dataclass(frozen=True, slots=True)
class SemanticContribution:
    contribution_ref: str
    contribution_kind: SemanticContributionKind
    spec_ref: str | None = None
    target_kind: SenseTargetKind | None = None
    target_ref: str | None = None
    target_revision: int | None = None
    target_schema_class: SchemaClass | None = None
    expected_filler_classes: tuple[PortFillerClass, ...] = ()
    expected_schema_classes: tuple[SchemaClass, ...] = ()
    expected_type_refs: tuple[str, ...] = ()
    open_binding_purpose: OpenBindingPurpose | None = None
    restriction_refs: tuple[str, ...] = ()
    projection_ref: str | None = None
    projection_revision: int | None = None
    role_ref: str = ""
    scope_behavior: str = "none"
    feature_values: tuple[tuple[str, str], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.contribution_ref, "semantic contribution_ref")
        if self.spec_ref is not None:
            _ref(self.spec_ref, "semantic contribution spec_ref")
        if self.target_ref is not None:
            _ref(self.target_ref, "semantic contribution target_ref")
        if self.projection_ref is not None:
            _ref(self.projection_ref, "semantic contribution projection_ref")
        if self.projection_revision is not None and self.projection_revision < 1:
            raise ValueError("semantic contribution projection revision must be positive")
        if self.role_ref:
            _ref(self.role_ref, "semantic contribution role_ref")
        _unique(self.expected_filler_classes, "semantic contribution filler classes")
        _unique(self.expected_schema_classes, "semantic contribution schema classes")
        _unique(self.expected_type_refs, "semantic contribution expected types")
        _unique(self.restriction_refs, "semantic contribution restrictions")
        _unique(tuple(name for name, _ in self.feature_values), "semantic contribution feature names")
        _unique(self.evidence_refs, "semantic contribution evidence")


@dataclass(frozen=True, slots=True)
class FormCandidate:
    candidate_ref: str
    observation_refs: tuple[str, ...]
    span: Span
    form_ref: str
    form_revision: int
    language_tag: str
    confidence: float
    evidence_refs: tuple[str, ...]
    via_variant: bool = False
    via_normalization: bool = False

    def __post_init__(self) -> None:
        _ref(self.candidate_ref, "form candidate_ref")
        _ref(self.form_ref, "form_ref")
        _language_tag(self.language_tag)
        if self.form_revision < 1:
            raise ValueError("form candidate revision must be positive")
        _confidence(self.confidence)
        if not self.observation_refs or not self.evidence_refs:
            raise ValueError("form candidate requires observations and evidence")


@dataclass(frozen=True, slots=True)
class SenseCandidate:
    candidate_ref: str
    form_candidate_ref: str
    sense_ref: str
    sense_revision: int
    target_kind: SenseTargetKind | None
    target_ref: str | None
    target_revision: int | None
    target_schema_class: SchemaClass | None
    confidence: float
    evidence_refs: tuple[str, ...]
    use_operation: UseOperation = UseOperation.GROUND
    scope_behavior: str = "none"
    expected_type_refs: tuple[str, ...] = ()
    lexical_category: str = ""
    argument_map: tuple[tuple[str, str], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    contributions: tuple[SemanticContribution, ...] = ()
    lexeme_ref: str | None = None
    authority_path: str = "legacy_form_sense"

    def __post_init__(self) -> None:
        for value, label in ((self.candidate_ref, "sense candidate_ref"), (self.form_candidate_ref, "form_candidate_ref"), (self.sense_ref, "sense_ref")):
            _ref(value, label)
        if self.target_ref is not None:
            _ref(self.target_ref, "target_ref")
        if self.lexeme_ref is not None:
            _ref(self.lexeme_ref, "lexeme_ref")
        if self.sense_revision < 1:
            raise ValueError("sense candidate revision must be positive")
        _confidence(self.confidence)
        _unique(tuple(item.contribution_ref for item in self.contributions), "sense candidate contributions")
        _unique(self.expected_type_refs, "sense candidate expected types")
        if not self.evidence_refs:
            raise ValueError("sense candidate requires evidence")


@dataclass(frozen=True, slots=True)
class DependencyArc:
    head_observation_ref: str
    dependent_observation_ref: str
    relation: str
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.head_observation_ref, "dependency head")
        _ref(self.dependent_observation_ref, "dependency dependent")
        if self.head_observation_ref == self.dependent_observation_ref:
            raise ValueError("dependency self-loop is invalid")
        _ref(self.relation, "dependency relation")
        _confidence(self.confidence)
        if not self.evidence_refs:
            raise ValueError("dependency arc requires evidence")


@dataclass(frozen=True, slots=True)
class DependencyParseEvidence:
    parse_ref: str
    observation_refs: tuple[str, ...]
    arcs: tuple[DependencyArc, ...]
    root_observation_refs: tuple[str, ...]
    adapter_ref: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        _ref(self.parse_ref, "parse_ref")
        _ref(self.adapter_ref, "adapter_ref")
        _confidence(self.confidence)
        known = set(self.observation_refs)
        if not known:
            raise ValueError("dependency parse requires observations")
        if not set(self.root_observation_refs).issubset(known):
            raise ValueError("dependency roots must be observations")
        for arc in self.arcs:
            if arc.head_observation_ref not in known or arc.dependent_observation_ref not in known:
                raise ValueError("dependency arc references unknown observation")
        _require_acyclic(self.observation_refs, tuple((arc.head_observation_ref, arc.dependent_observation_ref) for arc in self.arcs))


@dataclass(frozen=True, slots=True)
class ConstituencyNode:
    node_ref: str
    label: str
    span: Span
    child_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.node_ref, "constituency node_ref")
        _ref(self.label, "constituency label")
        _unique(self.child_refs, "constituency children")
        if not self.evidence_refs:
            raise ValueError("constituency node requires evidence")


@dataclass(frozen=True, slots=True)
class ConstituencyParseEvidence:
    parse_ref: str
    root_ref: str
    nodes: tuple[ConstituencyNode, ...]
    adapter_ref: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        _ref(self.parse_ref, "parse_ref")
        _ref(self.root_ref, "root_ref")
        _ref(self.adapter_ref, "adapter_ref")
        _confidence(self.confidence)
        by_ref = {item.node_ref: item for item in self.nodes}
        if len(by_ref) != len(self.nodes) or self.root_ref not in by_ref:
            raise ValueError("constituency parse requires unique nodes and a known root")
        for node in self.nodes:
            for child_ref in node.child_refs:
                child = by_ref.get(child_ref)
                if child is None:
                    raise ValueError("constituency child is unknown")
                if child.span.start < node.span.start or child.span.end > node.span.end:
                    raise ValueError("constituency child span must be contained by parent")
        _require_acyclic(tuple(by_ref), tuple((node.node_ref, child) for node in self.nodes for child in node.child_refs))


@dataclass(frozen=True, slots=True)
class ConstructionCandidate:
    candidate_ref: str
    construction_ref: str
    construction_revision: int
    trigger_refs: tuple[str, ...]
    slot_fillers: tuple[tuple[str, tuple[str, ...]], ...]
    span: Span
    confidence: float
    evidence_refs: tuple[str, ...]
    gap_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ref(self.candidate_ref, "construction candidate_ref")
        _ref(self.construction_ref, "construction_ref")
        if self.construction_revision < 1:
            raise ValueError("construction revision must be positive")
        _confidence(self.confidence)
        _unique(self.trigger_refs, "construction candidate triggers")
        _unique(tuple(name for name, _ in self.slot_fillers), "construction candidate slots")
        if not self.evidence_refs:
            raise ValueError("construction candidate requires evidence")


@dataclass(frozen=True, slots=True)
class LatticeNode:
    node_ref: str
    node_kind: LatticeNodeKind
    span: Span
    payload_ref: str
    confidence: float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ref(self.node_ref, "lattice node_ref")
        _ref(self.payload_ref, "lattice payload_ref")
        _confidence(self.confidence)
        if not self.evidence_refs:
            raise ValueError("lattice node requires evidence")


@dataclass(frozen=True, slots=True)
class LatticeEdge:
    edge_ref: str
    source_ref: str
    target_ref: str
    edge_kind: LatticeEdgeKind
    confidence: float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in ((self.edge_ref, "lattice edge_ref"), (self.source_ref, "source_ref"), (self.target_ref, "target_ref")):
            _ref(value, label)
        _confidence(self.confidence)
        if not self.evidence_refs:
            raise ValueError("lattice edge requires evidence")


@dataclass(frozen=True, slots=True)
class FormLattice:
    lattice_ref: str
    source_ref: str
    source_content: str
    observations: tuple[FormObservation, ...]
    language_evidence: tuple[LanguageEvidence, ...]
    normalization_evidence: tuple[NormalizationEvidence, ...]
    form_candidates: tuple[FormCandidate, ...]
    sense_candidates: tuple[SenseCandidate, ...]
    construction_candidates: tuple[ConstructionCandidate, ...]
    nodes: tuple[LatticeNode, ...]
    edges: tuple[LatticeEdge, ...]
    lexeme_candidates: tuple[LexemeCandidate, ...] = ()
    unresolved_spans: tuple[Span, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ref(self.lattice_ref, "lattice_ref")
        _ref(self.source_ref, "source_ref")
        _unique(tuple(item.observation_ref for item in self.observations), "observation refs")
        _unique(tuple(item.candidate_ref for item in self.form_candidates), "form candidate refs")
        _unique(tuple(item.candidate_ref for item in self.lexeme_candidates), "lexeme candidate refs")
        _unique(tuple(item.candidate_ref for item in self.sense_candidates), "sense candidate refs")
        _unique(tuple(item.candidate_ref for item in self.construction_candidates), "construction candidate refs")
        node_refs = tuple(item.node_ref for item in self.nodes)
        _unique(node_refs, "lattice node refs")
        _unique(tuple(item.edge_ref for item in self.edges), "lattice edge refs")
        known = set(node_refs)
        for edge in self.edges:
            if edge.source_ref not in known or edge.target_ref not in known:
                raise ValueError("lattice edge references unknown node")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint("form-lattice", self, 64)


def _reviewed_authority(
    lifecycle_status: SchemaLifecycleStatus,
    source_refs: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    label: str,
) -> None:
    if lifecycle_status in {SchemaLifecycleStatus.ACTIVE, SchemaLifecycleStatus.COMPETENCE_VERIFIED}:
        if not source_refs or not evidence_refs:
            raise ValueError(f"active {label} requires reviewed source and evidence")


def _supersession(revision: int, supersedes_revision: int | None, label: str) -> None:
    if supersedes_revision is not None and (supersedes_revision < 1 or supersedes_revision >= revision):
        raise ValueError(f"{label} supersedes_revision must be positive and older")


def _ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty reference")


def _language_tag(value: str) -> None:
    _ref(value, "language_tag")
    if " " in value or "_" in value:
        raise ValueError("language_tag must use BCP-47 style hyphens")


def _unique(values: tuple[Any, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


def _confidence(value: float) -> None:
    if not isfinite(value) or value < 0 or value > 1:
        raise ValueError("confidence must be finite and within [0, 1]")


def _require_acyclic(nodes: tuple[str, ...], edges: tuple[tuple[str, str], ...]) -> None:
    adjacency = {node: [] for node in nodes}
    for source, target in edges:
        adjacency.setdefault(source, []).append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("parse graph contains a cycle")
        if node in visited:
            return
        visiting.add(node)
        for target in adjacency.get(node, ()):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in nodes:
        visit(node)
