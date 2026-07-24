from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from cemm.v350.data import DeterministicSQLiteCompiler, SourcePackageLoader
from cemm.v350.language import (
    ConstituencyNode,
    ConstituencyParseEvidence,
    ConstructionKind,
    ConstructionRecord,
    DependencyArc,
    DependencyParseEvidence,
    FormKind,
    FormLatticeAnalyzer,
    LanguageFormRecord,
    LanguageRegistry,
    LanguageRegistryError,
    Span,
    SyntaxAdapterHub,
)
from cemm.v350.grounding import MentionCompiler, MentionTargetClass
from cemm.v350.schema.model import SchemaLifecycleStatus
from cemm.v350.storage import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


class ReviewedDependencyAdapter:
    adapter_ref = "test-adapter:dependency"

    def analyze(self, request):
        lexical = [item for item in request.observations if item.category not in {"whitespace", "punctuation", "symbol"}]
        if not lexical:
            return None
        by_key = {item.canonical: item for item in lexical}
        arcs = []

        def add(trigger_keys, left_relation, right_relation):
            for index, item in enumerate(lexical):
                if item.canonical not in trigger_keys:
                    continue
                if index > 0:
                    arcs.append(DependencyArc(item.observation_ref, lexical[index - 1].observation_ref, left_relation,
                                              evidence_refs=(self.adapter_ref,)))
                if index + 1 < len(lexical):
                    arcs.append(DependencyArc(item.observation_ref, lexical[index + 1].observation_ref, right_relation,
                                              evidence_refs=(self.adapter_ref,)))

        add({"and", "or", "et", "ou", "na", "au"}, "coordinate_left", "coordinate_right")
        add({"that", "que", "kwamba"}, "complement_matrix", "complement_content")
        add({"who", "which", "qui", "ambaye", "ambayo"}, "relative_head", "relative_clause")
        add({"also", "aussi", "pia"}, "ellipsis_antecedent", "ellipsis_remainder")

        for index, item in enumerate(lexical):
            if item.canonical in {"say", "says", "said", "dire", "dit", "sema", "anasema"}:
                if index > 0:
                    arcs.append(DependencyArc(item.observation_ref, lexical[index - 1].observation_ref, "claimant",
                                              evidence_refs=(self.adapter_ref,)))
                if index + 1 < len(lexical) and lexical[index + 1].canonical not in {"that", "que", "kwamba"}:
                    arcs.append(DependencyArc(item.observation_ref, lexical[index + 1].observation_ref, "proposition",
                                              evidence_refs=(self.adapter_ref,)))
            if item.canonical in {"see", "sees", "saw", "voir", "voit", "vois", "ona", "anaona"}:
                if index > 0:
                    arcs.append(DependencyArc(item.observation_ref, lexical[index - 1].observation_ref, "observer",
                                              evidence_refs=(self.adapter_ref,)))
                if index + 1 < len(lexical):
                    arcs.append(DependencyArc(item.observation_ref, lexical[index + 1].observation_ref, "observed",
                                              evidence_refs=(self.adapter_ref,)))

        # Deterministic de-duplication in case a test phrase triggers overlapping rules.
        unique = {(a.head_observation_ref, a.dependent_observation_ref, a.relation): a for a in arcs}
        return DependencyParseEvidence(
            parse_ref=f"parse:dependency:{request.source_ref}",
            observation_refs=tuple(item.observation_ref for item in lexical),
            arcs=tuple(unique[key] for key in sorted(unique)),
            root_observation_refs=(lexical[0].observation_ref,),
            adapter_ref=self.adapter_ref,
            confidence=0.95,
        )


class ReviewedConstituencyAdapter:
    adapter_ref = "test-adapter:constituency"

    def analyze(self, request):
        lexical = [item for item in request.observations if item.category not in {"whitespace", "punctuation", "symbol"}]
        if not lexical:
            return None
        children = tuple(
            ConstituencyNode(
                node_ref=f"constituent:{request.source_ref}:{index}",
                label="TOKEN",
                span=item.span,
                evidence_refs=(self.adapter_ref,),
            )
            for index, item in enumerate(lexical)
        )
        root = ConstituencyNode(
            node_ref=f"constituent:{request.source_ref}:root",
            label="CLAUSE",
            span=Span(lexical[0].span.start, lexical[-1].span.end),
            child_refs=tuple(item.node_ref for item in children),
            evidence_refs=(self.adapter_ref,),
        )
        return ConstituencyParseEvidence(
            parse_ref=f"parse:constituency:{request.source_ref}",
            root_ref=root.node_ref,
            nodes=(root, *children),
            adapter_ref=self.adapter_ref,
            confidence=0.9,
        )


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    directory = tmp_path_factory.mktemp("phase7")
    first = DeterministicSQLiteCompiler().compile(SOURCE, directory / "a.sqlite", make_read_only=False)
    second = DeterministicSQLiteCompiler().compile(SOURCE, directory / "b.sqlite", make_read_only=False)
    assert first.output_path.read_bytes() == second.output_path.read_bytes()
    return first


@pytest.fixture(scope="module")
def store(compiled):
    value = SemanticStore(":memory:", boot_path=compiled.output_path)
    yield value
    value.close()


@pytest.fixture(scope="module")
def analyzer(store):
    return FormLatticeAnalyzer(
        store.repositories.language.registry(),
        syntax_adapters=SyntaxAdapterHub(
            dependency_adapters=(ReviewedDependencyAdapter(),),
            constituency_adapters=(ReviewedConstituencyAdapter(),),
        ),
    )


def test_manifest_separates_foundation_and_language_authority() -> None:
    manifest = SourcePackageLoader(SOURCE).manifest
    language = tuple(item for item in manifest.modules if item.phase == 7)
    foundation = tuple(item for item in manifest.modules if item.phase <= 6)
    assert foundation and language
    assert all(item.authority_scope == "foundation" for item in foundation)
    assert all(item.authority_scope == "language_evidence" for item in language)
    assert {item.record_kind for item in language} == {
        RecordKind.EVIDENCE,
        RecordKind.LANGUAGE_PACK,
        RecordKind.LANGUAGE_FORM,
        RecordKind.LEXICAL_SENSE,
        RecordKind.FORM_SENSE_LINK,
        RecordKind.CONSTRUCTION,
    }


def test_compiled_language_tables_and_typed_repositories_are_populated(store) -> None:
    repos = store.repositories.language
    phase7_forms = tuple(item for item in repos.forms.all() if item.payload.metadata.get("phase") == 7)
    phase7_senses = tuple(item for item in repos.senses.all() if item.payload.metadata.get("phase") == 7)
    phase7_links = tuple(item for item in repos.links.all() if item.payload.metadata.get("phase") == 7)
    phase7_constructions = tuple(
        item for item in repos.constructions.all() if item.payload.metadata.get("phase") == 7
    )
    assert repos.packs.all()
    assert phase7_forms
    assert phase7_senses
    assert phase7_links
    assert phase7_constructions
    assert {item.payload.language_tag for item in repos.packs.all()} == {"en", "fr", "sw"}


def test_forms_senses_and_schemas_remain_separate(store) -> None:
    registry = store.repositories.language.registry()
    form = registry.require_form("form:en:see", 1)
    sense = registry.require_sense("sense:en:observe", 1)
    assert form.normalized_form == "see"
    assert not hasattr(form, "target_ref")
    assert sense.target_ref == "event:observe"
    assert sense.target_revision == 1
    assert store.repositories.schemas.authoritative("event:observe").schema_ref == sense.target_ref


def test_code_switching_is_span_local_and_preserves_unresolved_evidence(analyzer) -> None:
    lattice = analyzer.analyze("I vois ceci", source_ref="utterance:code-switch")
    assert {(item.language_tag, lattice.source_content[item.span.start:item.span.end]) for item in lattice.language_evidence} >= {
        ("en", "I"), ("fr", "vois"), ("fr", "ceci")
    }
    assert {item.form_ref for item in lattice.form_candidates} >= {
        "form:en:i", "form:fr:vois", "form:fr:ceci"
    }
    assert "sense:fr:observe" in {item.sense_ref for item in lattice.sense_candidates}
    assert lattice.unresolved_spans == ()


def test_colloquial_normalization_is_reversible_evidence(analyzer) -> None:
    lattice = analyzer.analyze("ya see this", source_ref="utterance:colloquial", language_hints=("en",))
    normalized = lattice.normalization_evidence
    assert len(normalized) == 1
    assert normalized[0].original == "ya"
    assert normalized[0].proposed == "you"
    assert normalized[0].reversible is True
    candidate = next(item for item in lattice.form_candidates if item.form_ref == "form:en:you")
    assert candidate.via_normalization is True
    assert normalized[0].evidence_ref in candidate.evidence_refs


def test_syntax_adapters_contribute_evidence_not_semantic_selection(analyzer) -> None:
    lattice = analyzer.analyze("I see this", source_ref="utterance:adapter-boundary")
    assert all(not item.target_ref.startswith("test-adapter:") for item in lattice.sense_candidates)
    assert any(ref.startswith("parse:dependency:") for item in lattice.construction_candidates for ref in item.evidence_refs)


def test_full_sentence_pattern_is_rejected_unless_genuine_idiom(store) -> None:
    pack = store.repositories.language.registry().require_pack("language-pack:en", 1)
    with pytest.raises(ValueError, match="genuine idioms"):
        ConstructionRecord(
            construction_ref="construction:test:sentence",
            pack_ref=pack.pack_ref,
            pack_revision=pack.revision,
            construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
            slots=(store.repositories.language.registry().require_construction("construction:en:claim-frame", 1).slots[0],),
            full_sentence_pattern=True,
        )


def test_language_revision_supersession_selects_one_effective_revision(store) -> None:
    snapshot = store.repositories.language.registry().snapshot()
    old = next(item for item in snapshot.forms if item.form_ref == "form:en:see")
    newer = replace(old, revision=2, supersedes_revision=1, written_form="SEE")
    registry = LanguageRegistry(snapshot.packs, (*snapshot.forms, newer), snapshot.senses, snapshot.links, snapshot.constructions, contribution_specs=snapshot.contribution_specs)
    assert registry.require_form(old.form_ref).revision == 2
    with pytest.raises(LanguageRegistryError, match="multiple effective active revisions"):
        LanguageRegistry(snapshot.packs, (*snapshot.forms, replace(old, revision=2)), snapshot.senses, snapshot.links, snapshot.constructions, contribution_specs=snapshot.contribution_specs)


def test_language_revision_commits_through_graph_patch_and_typed_repository(store) -> None:
    old = store.repositories.language.registry().require_form("form:en:see", 1)
    newer = replace(old, revision=2, supersedes_revision=1, written_form="SEE")
    operation = PatchOperation(
        operation_ref="operation:language-form:see:2",
        operation_kind=PatchOperationKind.UPSERT,
        record_kind=RecordKind.LANGUAGE_FORM,
        target_ref=newer.form_ref,
        record_revision=2,
        expected_record_revision=1,
        payload=encode_record(RecordKind.LANGUAGE_FORM, newer),
        reason="test reviewed form revision",
    )
    result = store.apply_patch(GraphPatch(
        patch_ref="patch:language-form:see:2",
        context_ref="actual",
        scope_ref="language-test",
        source_ref="test",
        permission_ref="internal",
        operations=(operation,),
        expected_store_revision=store.revision,
    ))
    assert result.committed, result.errors
    assert store.repositories.language.registry().require_form("form:en:see").revision == 2
    assert store.repositories.language.forms.require("form:en:see", 1).layer == "boot"
    assert store.repositories.language.forms.require("form:en:see", 2).layer == "overlay"


def test_form_lattice_is_deterministic(analyzer) -> None:
    first = analyzer.analyze("mimi na wewe", source_ref="utterance:determinism")
    second = analyzer.analyze("mimi na wewe", source_ref="utterance:determinism")
    assert first == second
    assert first.fingerprint == second.fingerprint
    assert {item.language_tag for item in first.language_evidence} == {"sw"}


def test_active_language_authority_requires_reviewed_source_and_evidence() -> None:
    with pytest.raises(ValueError, match="reviewed source and evidence"):
        LanguageFormRecord(
            form_ref="form:test:unreviewed-active",
            pack_ref="language-pack:en",
            pack_revision=1,
            written_form="test",
            normalized_form="test",
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        )


def test_observation_script_ties_and_normalization_source_are_deterministic(analyzer) -> None:
    first = analyzer.analyze("aа", source_ref="utterance:mixed-script")
    second = analyzer.analyze("aа", source_ref="utterance:mixed-script")
    assert first.observations == second.observations
    assert first.observations[0].script == "Cyrillic"

    normalized = analyzer.analyze("YA   see this", source_ref="utterance:exact-normalization", language_hints=("en",))
    evidence = next(item for item in normalized.normalization_evidence if item.proposed == "you")
    assert evidence.original == "YA"
    assert normalized.source_content[evidence.span.start:evidence.span.end] == evidence.original


def test_construction_ports_flow_into_grounding_mentions(analyzer, store) -> None:
    lattice = analyzer.analyze("I say this", source_ref="utterance:claim-role-bridge")
    mentions = MentionCompiler(store.repositories.language.registry()).compile(lattice, context_ref="actual")
    claimant = next(item for item in mentions if item.surface == "I")
    claim_event = next(item for item in mentions if item.surface == "say")
    # Construction role evidence must not mutate the mention into a hidden ontology class.
    # Compatibility is derived later from the exact output-schema port contract.
    assert claimant.target_class == MentionTargetClass.REFERENT
    assert claimant.syntactic_role == "claimant"
    assert claimant.source_role == ""
    claim_candidates = {
        item.candidate_ref for item in lattice.construction_candidates
        if item.construction_ref == "construction:en:claim-frame"
    }
    assert set(claimant.construction_candidate_refs).intersection(claim_candidates)
    assert set(claim_event.construction_candidate_refs).intersection(claim_candidates)
    assert claim_event.syntactic_role == "predicate"
    assert any(ref.startswith("parse:dependency:") for ref in claimant.evidence_refs)
    assert any(ref.startswith("parse:dependency:") for ref in claim_event.evidence_refs)

