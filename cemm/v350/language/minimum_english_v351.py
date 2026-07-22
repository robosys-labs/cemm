"""Reviewed minimum English composition package contract for CEMM v3.5.1 Phase 9.

English strings live here as data.  Kernel/CSIR code never branches on them.  The package
binds language evidence to exact semantic-authority slots supplied by an
``AuthoritySnapshotV351``-compatible activation step; it does not invent world truth or
hard-code an English ontology.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json
import unicodedata
from typing import Any, Mapping

from ..csir.authority_v351 import AuthoritySnapshotV351
from ..csir.model import ExactAuthorityPin
from .model import ConstructionProgramOperation


class EnglishPackageError(ValueError):
    pass


class CompositionFamily(str, Enum):
    PRONOUNS_DEIXIS = "pronouns_deixis"
    PROPER_NAMES = "proper_names"
    DETERMINERS = "determiners"
    IDENTITY_CLASSIFICATION = "identity_classification"
    PROPERTY_STATE_PREDICATION = "property_state_predication"
    POSSESSION = "possession"
    SIMPLE_RELATIONS = "simple_relations"
    SIMPLE_EVENTS = "simple_events"
    NEGATION = "negation"
    MODALITY_CAPABILITY = "modality_capability"
    WH_QUERY = "wh_query"
    YES_NO_QUERY = "yes_no_query"
    CORRECTIONS = "corrections"
    DEFINITION_TEACHING = "definition_teaching"
    GREETINGS = "greetings"
    REQUESTS_IMPERATIVES = "requests_imperatives"


REQUIRED_COMPOSITION_FAMILIES = tuple(CompositionFamily)


@dataclass(frozen=True, slots=True)
class FormSeed:
    surface: str
    lexical_key: str
    lexical_category: str
    features: tuple[tuple[str, str], ...] = ()
    variants: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SenseSeed:
    lexical_key: str
    semantic_slot: str
    contribution_kind: str
    features: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ProgramStep:
    """Language-package source step over the existing generic composition VM.

    ``semantic_slot`` is a package-local symbolic key that MUST resolve to an exact
    authority pin before activation.  It is not a named kernel concept or raw schema
    lookup.  Phase 10 may lower these source steps to canonical
    ``ConstructionProgramRecord`` values after exact binding.
    """

    operation: ConstructionProgramOperation
    semantic_slot: str = ""
    operands: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.operation, ConstructionProgramOperation):
            raise EnglishPackageError("English construction steps must use generic ConstructionProgramOperation values")
        keys = [key for key, _ in self.operands]
        if len(keys) != len(set(keys)):
            raise EnglishPackageError("English program-step operand keys must be unique")
        if self.semantic_slot and not self.semantic_slot.strip():
            raise EnglishPackageError("English semantic slot must be non-empty when present")


@dataclass(frozen=True, slots=True)
class ConstructionSeed:
    construction_ref: str
    family: CompositionFamily
    trigger_categories: tuple[str, ...]
    required_features: tuple[tuple[str, str], ...]
    program: tuple[ProgramStep, ...]
    competence_cases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MorphologySeed:
    rule_ref: str
    operation: str
    surface_operand: str
    lemma_operand: str
    feature_values: tuple[tuple[str, str], ...]
    reversible: bool = True


@dataclass(frozen=True, slots=True)
class SemanticAuthorityBindings:
    """Exact semantic pins for symbolic package slots.

    Symbolic slot names are package data identifiers only.  Missing bindings are hard
    activation failures, preventing floating semantic lookup by text or "latest" schema.
    """

    pins: Mapping[str, ExactAuthorityPin]

    def require(self, slot: str) -> ExactAuthorityPin:
        try:
            return self.pins[slot]
        except KeyError as exc:
            raise EnglishPackageError(f"missing exact semantic binding for English slot:{slot}") from exc

    def validate_against(self, snapshot: AuthoritySnapshotV351) -> None:
        for slot, pin in sorted(self.pins.items()):
            if not isinstance(slot, str) or not slot.strip():
                raise EnglishPackageError("English semantic binding slots must be non-empty")
            try:
                snapshot.require_known_pin(pin)
            except Exception as exc:
                raise EnglishPackageError(
                    f"English semantic slot is not pinned in the exact AuthorityGeneration:{slot}:{pin.key}"
                ) from exc


FORMS: tuple[FormSeed, ...] = (
    # Participant/deictic evidence. Person/number/possessive are grammatical features;
    # participant-frame grounding supplies actual referent identity.
    FormSeed("I", "pronoun.first.singular.subject", "pronoun", (("person", "1"), ("number", "sg"), ("case", "subject"))),
    FormSeed("me", "pronoun.first.singular.object", "pronoun", (("person", "1"), ("number", "sg"), ("case", "object"))),
    FormSeed("my", "pronoun.first.singular.possessive", "determiner", (("person", "1"), ("possessive", "true"))),
    FormSeed("mine", "pronoun.first.singular.possessive.absolute", "pronoun", (("person", "1"), ("possessive", "true"))),
    FormSeed("you", "pronoun.second", "pronoun", (("person", "2"),)),
    FormSeed("your", "pronoun.second.possessive", "determiner", (("person", "2"), ("possessive", "true"))),
    FormSeed("this", "deictic.proximal", "determiner", (("deixis", "proximal"),)),
    FormSeed("that", "deictic.distal", "determiner", (("deixis", "distal"),)),
    FormSeed("a", "determiner.indefinite", "determiner", (("definiteness", "indefinite"),), ("an",)),
    FormSeed("the", "determiner.definite", "determiner", (("definiteness", "definite"),)),
    # Copular/auxiliary forms are lexical evidence; constructions decide composition.
    FormSeed("be", "copula.be", "verb", (("lemma", "be"),)),
    FormSeed("am", "copula.be", "verb", (("tense", "present"), ("person", "1"), ("number", "sg"))),
    FormSeed("is", "copula.be", "verb", (("tense", "present"), ("number", "sg"))),
    FormSeed("are", "copula.be", "verb", (("tense", "present"),)),
    FormSeed("was", "copula.be", "verb", (("tense", "past"), ("number", "sg"))),
    FormSeed("were", "copula.be", "verb", (("tense", "past"),)),
    FormSeed("have", "relation.possession", "verb", (("tense", "present"),)),
    FormSeed("has", "relation.possession", "verb", (("tense", "present"), ("person", "3"), ("number", "sg"))),
    FormSeed("can", "modal.capability", "modal", (("modality", "capability"),)),
    FormSeed("not", "operator.negation", "particle", (("polarity", "negative"),)),
    FormSeed("no", "ambiguous.no", "particle", (("polarity", "negative"),)),
    # Query evidence.
    FormSeed("who", "wh.person", "wh", (("projection", "referent"),)),
    FormSeed("what", "wh.thing", "wh", (("projection", "referent_or_definition"),)),
    FormSeed("where", "wh.place", "wh", (("projection", "place"),)),
    FormSeed("when", "wh.time", "wh", (("projection", "time"),)),
    FormSeed("why", "wh.reason", "wh", (("projection", "explanation"),)),
    FormSeed("how", "wh.manner_state", "wh", (("projection", "manner_or_state"),)),
    FormSeed("do", "aux.do", "auxiliary", (("tense", "present"),)),
    FormSeed("does", "aux.do", "auxiliary", (("tense", "present"), ("person", "3"), ("number", "sg"))),
    FormSeed("did", "aux.do", "auxiliary", (("tense", "past"),)),
    # Discourse/correction/request evidence.
    FormSeed("actually", "discourse.correction", "discourse_marker"),
    FormSeed("instead", "discourse.replacement", "discourse_marker"),
    FormSeed("means", "discourse.definition", "verb", (("person", "3"), ("number", "sg"))),
    FormSeed("mean", "discourse.definition", "verb"),
    FormSeed("hello", "discourse.greeting", "interjection", variants=("hi", "hey")),
    FormSeed("please", "discourse.request.politeness", "particle", (("politeness", "marked"),)),
)


SENSES: tuple[SenseSeed, ...] = (
    SenseSeed("pronoun.first.singular.subject", "participant_role:speaker", "referential"),
    SenseSeed("pronoun.first.singular.object", "participant_role:speaker", "referential"),
    SenseSeed("pronoun.first.singular.possessive", "participant_role:speaker", "referential", (("relation", "possessor"),)),
    SenseSeed("pronoun.first.singular.possessive.absolute", "participant_role:speaker", "referential", (("relation", "possessor"),)),
    SenseSeed("pronoun.second", "participant_role:addressee", "referential"),
    SenseSeed("pronoun.second.possessive", "participant_role:addressee", "referential", (("relation", "possessor"),)),
    SenseSeed("deictic.proximal", "operator:deixis_proximal", "referential"),
    SenseSeed("deictic.distal", "operator:deixis_distal", "referential"),
    SenseSeed("copula.be", "operator:predication", "construction"),
    SenseSeed("relation.possession", "relation:possession", "target"),
    SenseSeed("modal.capability", "operator:capability", "scope"),
    SenseSeed("operator.negation", "operator:negation", "scope"),
    SenseSeed("ambiguous.no", "operator:negation", "scope", (("sense", "negation"),)),
    SenseSeed("ambiguous.no", "discourse:negative_answer", "construction", (("sense", "answer"),)),
    SenseSeed("ambiguous.no", "determiner:negative", "restriction", (("sense", "determiner"),)),
    SenseSeed("wh.person", "projection:referent_person", "projection"),
    SenseSeed("wh.thing", "projection:referent_or_definition", "projection"),
    SenseSeed("wh.place", "projection:place", "projection"),
    SenseSeed("wh.time", "projection:time", "projection"),
    SenseSeed("wh.reason", "projection:explanation", "projection"),
    SenseSeed("wh.manner_state", "projection:manner_or_state", "projection"),
    SenseSeed("discourse.correction", "discourse:correction", "construction"),
    SenseSeed("discourse.replacement", "discourse:replacement", "construction"),
    SenseSeed("discourse.definition", "discourse:definition", "construction"),
    SenseSeed("discourse.greeting", "discourse:greeting", "construction"),
    SenseSeed("discourse.request.politeness", "discourse:request", "grammatical_feature"),
)


# These are declarative composition programs consumed by the generic Phase-10 solver.
# No program is selected by comparing a raw English phrase in kernel code.
CONSTRUCTIONS: tuple[ConstructionSeed, ...] = (
    ConstructionSeed(
        "construction:en:v351:participant-pronoun", CompositionFamily.PRONOUNS_DEIXIS,
        ("pronoun",), (),
        (ProgramStep(ConstructionProgramOperation.UNIFY),),
        ("case:en:pronoun:speaker", "case:en:pronoun:addressee"),
    ),
    ConstructionSeed(
        "construction:en:v351:proper-name", CompositionFamily.PROPER_NAMES,
        ("proper_name",), (),
        (ProgramStep(ConstructionProgramOperation.ADD_RESTRICTION),),
        ("case:en:name:introduction", "case:en:name:reference"),
    ),
    ConstructionSeed(
        "construction:en:v351:determiner-nominal", CompositionFamily.DETERMINERS,
        ("determiner", "nominal"), (),
        (ProgramStep(ConstructionProgramOperation.ADD_RESTRICTION),),
        ("case:en:det:definite", "case:en:det:indefinite"),
    ),
    ConstructionSeed(
        "construction:en:v351:copular-predication", CompositionFamily.IDENTITY_CLASSIFICATION,
        ("nominal_or_pronoun", "verb", "nominal_or_property"), (("lemma", "be"),),
        (
            ProgramStep(ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES),
            ProgramStep(ConstructionProgramOperation.BIND_PORT_FROM_SLOT),
            ProgramStep(ConstructionProgramOperation.UNIFY),
        ),
        ("case:en:copula:identity", "case:en:copula:classification"),
    ),
    ConstructionSeed(
        "construction:en:v351:state-property-predication", CompositionFamily.PROPERTY_STATE_PREDICATION,
        ("nominal_or_pronoun", "verb", "property_or_state"), (("lemma", "be"),),
        (
            ProgramStep(ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES),
            ProgramStep(ConstructionProgramOperation.BIND_PORT_FROM_SLOT),
            ProgramStep(ConstructionProgramOperation.UNIFY),
        ),
        ("case:en:state:current", "case:en:property:value"),
    ),
    ConstructionSeed(
        "construction:en:v351:possession", CompositionFamily.POSSESSION,
        ("possessor", "possession_marker_or_verb", "possessed"), (),
        (
            ProgramStep(ConstructionProgramOperation.INSTANTIATE_SCHEMA, "relation:possession"),
            ProgramStep(ConstructionProgramOperation.BIND_PORT_FROM_SLOT),
        ),
        ("case:en:possessive:determiner", "case:en:possessive:have"),
    ),
    ConstructionSeed(
        "construction:en:v351:binary-relation", CompositionFamily.SIMPLE_RELATIONS,
        ("argument", "relation", "argument"), (),
        (
            ProgramStep(ConstructionProgramOperation.UNIFY),
            ProgramStep(ConstructionProgramOperation.BIND_PORT_FROM_SLOT),
        ),
        ("case:en:relation:binary",),
    ),
    ConstructionSeed(
        "construction:en:v351:event-clause", CompositionFamily.SIMPLE_EVENTS,
        ("participant", "event_predicate", "arguments"), (),
        (
            ProgramStep(ConstructionProgramOperation.UNIFY),
            ProgramStep(ConstructionProgramOperation.BIND_PORT_FROM_SLOT),
            ProgramStep(ConstructionProgramOperation.PRESERVE_GAP),
        ),
        ("case:en:event:intransitive", "case:en:event:transitive"),
    ),
    ConstructionSeed(
        "construction:en:v351:negation-scope", CompositionFamily.NEGATION,
        ("negative_operator", "scope_target"), (),
        (ProgramStep(ConstructionProgramOperation.ADD_SCOPE, "operator:negation"),),
        ("case:en:negation:clause", "case:en:negation:predicate"),
    ),
    ConstructionSeed(
        "construction:en:v351:capability-modal", CompositionFamily.MODALITY_CAPABILITY,
        ("modal", "predicate"), (("modality", "capability"),),
        (ProgramStep(ConstructionProgramOperation.ADD_MODALITY, "operator:capability"),),
        ("case:en:modal:can",),
    ),
    ConstructionSeed(
        "construction:en:v351:wh-query", CompositionFamily.WH_QUERY,
        ("wh", "clause"), (),
        (
            ProgramStep(ConstructionProgramOperation.INTRODUCE_VARIABLE),
            ProgramStep(ConstructionProgramOperation.ADD_RESTRICTION),
            ProgramStep(ConstructionProgramOperation.SET_PROJECTION),
            ProgramStep(ConstructionProgramOperation.PRESERVE_GAP),
            ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:query"),
        ),
        ("case:en:wh:who", "case:en:wh:what", "case:en:wh:how"),
    ),
    ConstructionSeed(
        "construction:en:v351:yes-no-query", CompositionFamily.YES_NO_QUERY,
        ("auxiliary_or_copula", "clause"), (("clause_type", "interrogative"),),
        (
            ProgramStep(ConstructionProgramOperation.SET_PROJECTION, "projection:truth"),
            ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:query"),
        ),
        ("case:en:yn:copula", "case:en:yn:do", "case:en:yn:modal"),
    ),
    ConstructionSeed(
        "construction:en:v351:correction", CompositionFamily.CORRECTIONS,
        ("correction_marker", "replacement_content"), (),
        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:correction"),),
        ("case:en:correction:name", "case:en:correction:fact"),
    ),
    ConstructionSeed(
        "construction:en:v351:definition-teaching", CompositionFamily.DEFINITION_TEACHING,
        ("term", "definition_predicate", "definition_content"), (),
        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:definition"),),
        ("case:en:definition:means", "case:en:teaching:is"),
    ),
    ConstructionSeed(
        "construction:en:v351:greeting", CompositionFamily.GREETINGS,
        ("interjection",), (),
        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:greeting"),),
        ("case:en:greeting:hello",),
    ),
    ConstructionSeed(
        "construction:en:v351:imperative-request", CompositionFamily.REQUESTS_IMPERATIVES,
        ("predicate", "arguments"), (("mood", "imperative"),),
        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:request"),),
        ("case:en:request:please", "case:en:imperative:bare"),
    ),
)


MORPHOLOGY: tuple[MorphologySeed, ...] = (
    MorphologySeed("morph:en:v351:plural-s", "suffix", "s", "", (("number", "plural"),)),
    MorphologySeed("morph:en:v351:3sg-s", "suffix", "s", "", (("person", "3"), ("number", "sg"), ("tense", "present"))),
    MorphologySeed("morph:en:v351:past-ed", "suffix", "ed", "", (("tense", "past"),)),
    MorphologySeed("morph:en:v351:progressive-ing", "suffix", "ing", "", (("aspect", "progressive"),)),
    MorphologySeed("morph:en:v351:possessive-apostrophe-s", "clitic_suffix", "'s", "", (("possessive", "true"),)),
)


def _stable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _stable(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _stable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_stable(item) for item in value]
    return value


def _package_content_hash(
    language_tag: str,
    revision: int,
    forms: tuple[FormSeed, ...],
    senses: tuple[SenseSeed, ...],
    constructions: tuple[ConstructionSeed, ...],
    morphology: tuple[MorphologySeed, ...],
    reviewed_source_refs: tuple[str, ...],
    competence_case_refs: tuple[str, ...],
) -> str:
    payload = _stable({
        "language_tag": language_tag,
        "revision": revision,
        "forms": forms,
        "senses": senses,
        "constructions": constructions,
        "morphology": morphology,
        "reviewed_source_refs": tuple(sorted(reviewed_source_refs)),
        "competence_case_refs": tuple(sorted(competence_case_refs)),
    })
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewedEnglishPackage:
    language_tag: str
    revision: int
    package_pin: ExactAuthorityPin
    forms: tuple[FormSeed, ...]
    senses: tuple[SenseSeed, ...]
    constructions: tuple[ConstructionSeed, ...]
    morphology: tuple[MorphologySeed, ...]
    reviewed_source_refs: tuple[str, ...]
    competence_case_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.language_tag != "en" or self.revision < 1:
            raise EnglishPackageError("minimum reviewed package must identify exact English revision")
        if (
            self.package_pin.kind != "language_package"
            or self.package_pin.ref != f"language-pack:{self.language_tag}"
            or self.package_pin.revision != self.revision
            or self.package_pin.content_hash != self.content_hash
        ):
            raise EnglishPackageError("English package pin does not exactly address package content")
        surfaces: dict[str, str] = {}
        lexical_keys = {item.lexical_key for item in self.forms}
        for form in self.forms:
            if not form.surface.strip() or not form.lexical_key.strip() or not form.lexical_category.strip():
                raise EnglishPackageError("English form requires surface, lexical key and category")
            for surface in (form.surface, *form.variants):
                normalized = unicodedata.normalize("NFKC", surface).casefold()
                prior = surfaces.get(normalized)
                if prior is not None and prior != form.lexical_key:
                    raise EnglishPackageError(
                        f"ambiguous reviewed English form {surface!r}: {prior} vs {form.lexical_key}"
                    )
                surfaces[normalized] = form.lexical_key
        missing_lexemes = sorted({item.lexical_key for item in self.senses}.difference(lexical_keys))
        if missing_lexemes:
            raise EnglishPackageError(f"English senses reference missing lexical forms:{missing_lexemes}")
        construction_refs = [item.construction_ref for item in self.constructions]
        if len(construction_refs) != len(set(construction_refs)):
            raise EnglishPackageError("English construction refs must be unique")
        morphology_refs = [item.rule_ref for item in self.morphology]
        if len(morphology_refs) != len(set(morphology_refs)):
            raise EnglishPackageError("English morphology rule refs must be unique")
        present = {item.family for item in self.constructions}
        missing = set(REQUIRED_COMPOSITION_FAMILIES).difference(present)
        if missing:
            raise EnglishPackageError(
                f"English package lacks required composition families:{sorted(x.value for x in missing)}"
            )
        if not self.reviewed_source_refs or not self.competence_case_refs:
            raise EnglishPackageError("reviewed package requires source and competence evidence")
        if any(not item.reversible for item in self.morphology):
            raise EnglishPackageError("minimum English analysis morphology must be reversible")

    @property
    def content_hash(self) -> str:
        return _package_content_hash(
            self.language_tag, self.revision, self.forms, self.senses, self.constructions,
            self.morphology, self.reviewed_source_refs, self.competence_case_refs,
        )

    def validate(
        self,
        bindings: SemanticAuthorityBindings,
        *,
        authority_snapshot: AuthoritySnapshotV351 | None = None,
    ) -> None:
        if self.language_tag != "en" or self.revision < 1:
            raise EnglishPackageError("minimum reviewed package must identify exact English revision")
        if (
            self.package_pin.kind != "language_package"
            or self.package_pin.ref != f"language-pack:{self.language_tag}"
            or self.package_pin.revision != self.revision
            or self.package_pin.content_hash != self.content_hash
        ):
            raise EnglishPackageError("English package pin does not exactly address package content")
        surfaces: dict[str, str] = {}
        lexical_keys = {item.lexical_key for item in self.forms}
        for form in self.forms:
            if not form.surface.strip() or not form.lexical_key.strip() or not form.lexical_category.strip():
                raise EnglishPackageError("English form requires surface, lexical key and category")
            for surface in (form.surface, *form.variants):
                normalized = unicodedata.normalize("NFKC", surface).casefold()
                prior = surfaces.get(normalized)
                if prior is not None and prior != form.lexical_key:
                    raise EnglishPackageError(
                        f"ambiguous reviewed English form {surface!r}: {prior} vs {form.lexical_key}"
                    )
                surfaces[normalized] = form.lexical_key
        missing_lexemes = sorted({item.lexical_key for item in self.senses}.difference(lexical_keys))
        if missing_lexemes:
            raise EnglishPackageError(f"English senses reference missing lexical forms:{missing_lexemes}")
        construction_refs = [item.construction_ref for item in self.constructions]
        if len(construction_refs) != len(set(construction_refs)):
            raise EnglishPackageError("English construction refs must be unique")
        morphology_refs = [item.rule_ref for item in self.morphology]
        if len(morphology_refs) != len(set(morphology_refs)):
            raise EnglishPackageError("English morphology rule refs must be unique")
        present = {item.family for item in self.constructions}
        missing = set(REQUIRED_COMPOSITION_FAMILIES).difference(present)
        if missing:
            raise EnglishPackageError(f"English package lacks required composition families:{sorted(x.value for x in missing)}")
        if not self.reviewed_source_refs or not self.competence_case_refs:
            raise EnglishPackageError("reviewed package requires source and competence evidence")
        # Resolve every semantic slot now; no floating lookup remains for runtime.
        # Executable activation additionally proves every package/binding pin belongs to
        # the exact AuthorityGeneration selected at Stage 0.
        if authority_snapshot is not None:
            try:
                authority_snapshot.require_known_pin(self.package_pin)
            except Exception as exc:
                raise EnglishPackageError(
                    "reviewed English package pin is absent from the exact AuthorityGeneration"
                ) from exc
            bindings.validate_against(authority_snapshot)
        for sense in self.senses:
            bindings.require(sense.semantic_slot)
        for construction in self.constructions:
            for step in construction.program:
                if step.semantic_slot:
                    bindings.require(step.semantic_slot)
        if any(not item.reversible for item in self.morphology):
            raise EnglishPackageError("minimum English analysis morphology must be reversible")


_ENGLISH_REVISION = 3
_ENGLISH_REVIEW_REFS = ("review:v351:english-minimum-substrate",)
_ENGLISH_COMPETENCE_CASES = tuple(
    sorted({case for construction in CONSTRUCTIONS for case in construction.competence_cases})
)
_ENGLISH_CONTENT_HASH = _package_content_hash(
    "en", _ENGLISH_REVISION, FORMS, SENSES, CONSTRUCTIONS, MORPHOLOGY,
    _ENGLISH_REVIEW_REFS, _ENGLISH_COMPETENCE_CASES,
)

MINIMUM_REVIEWED_ENGLISH = ReviewedEnglishPackage(
    language_tag="en",
    revision=_ENGLISH_REVISION,
    package_pin=ExactAuthorityPin(
        kind="language_package",
        namespace="cemm",
        ref="language-pack:en",
        revision=_ENGLISH_REVISION,
        content_hash=_ENGLISH_CONTENT_HASH,
        scope_ref="global",
    ),
    forms=FORMS,
    senses=SENSES,
    constructions=CONSTRUCTIONS,
    morphology=MORPHOLOGY,
    reviewed_source_refs=_ENGLISH_REVIEW_REFS,
    competence_case_refs=_ENGLISH_COMPETENCE_CASES,
)


__all__ = [
    "CompositionFamily",
    "ConstructionSeed",
    "EnglishPackageError",
    "FormSeed",
    "MINIMUM_REVIEWED_ENGLISH",
    "MORPHOLOGY",
    "MorphologySeed",
    "ProgramStep",
    "REQUIRED_COMPOSITION_FAMILIES",
    "ReviewedEnglishPackage",
    "SemanticAuthorityBindings",
    "SenseSeed",
]
