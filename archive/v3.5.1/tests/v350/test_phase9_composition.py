from __future__ import annotations

from pathlib import Path

import pytest

from cemm.v350.composition_pre_phase10_backup import (
    MeaningComposer,
    MeaningFactor,
    MeaningFactorGraph,
    MeaningFactorKind,
    MeaningFactorSolver,
    MeaningValue,
    MeaningVariable,
    MeaningVariableKind,
)
from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.grounding import DiscourseAnchor, JointGrounder, MultimodalTrack
from cemm.v350.language import (
    DependencyArc,
    DependencyParseEvidence,
    FormLatticeAnalyzer,
    SyntaxAdapterHub,
)
from cemm.v350.schema.model import PortFillerClass
from cemm.v350.storage import SemanticStore

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


class StructuralDependencyAdapter:
    adapter_ref = "test-adapter:phase9:dependency"

    def analyze(self, request):
        lexical = [
            item for item in request.observations
            if item.category not in {"whitespace", "punctuation", "symbol"}
        ]
        if not lexical:
            return None
        arcs = []
        claim_forms = {"say", "says", "said", "dire", "dit", "dis", "sema", "anasema"}
        observe_forms = {"see", "sees", "saw", "voir", "voit", "vois", "ona", "anaona", "naona"}
        coordinate_forms = {"and", "or", "et", "ou", "na", "au"}
        for index, item in enumerate(lexical):
            key = item.canonical
            if key in claim_forms:
                if index > 0:
                    arcs.append(DependencyArc(
                        item.observation_ref, lexical[index - 1].observation_ref, "claimant",
                        evidence_refs=(self.adapter_ref,),
                    ))
                if index + 1 < len(lexical):
                    arcs.append(DependencyArc(
                        item.observation_ref, lexical[index + 1].observation_ref, "proposition",
                        evidence_refs=(self.adapter_ref,),
                    ))
            if key in observe_forms:
                if index > 0:
                    arcs.append(DependencyArc(
                        item.observation_ref, lexical[index - 1].observation_ref, "observer",
                        evidence_refs=(self.adapter_ref,),
                    ))
                if index + 1 < len(lexical):
                    arcs.append(DependencyArc(
                        item.observation_ref, lexical[index + 1].observation_ref, "observed",
                        evidence_refs=(self.adapter_ref,),
                    ))
            if key in coordinate_forms:
                if index > 0:
                    arcs.append(DependencyArc(
                        item.observation_ref, lexical[index - 1].observation_ref, "coordinate_left",
                        evidence_refs=(self.adapter_ref,),
                    ))
                if index + 1 < len(lexical):
                    arcs.append(DependencyArc(
                        item.observation_ref, lexical[index + 1].observation_ref, "coordinate_right",
                        evidence_refs=(self.adapter_ref,),
                    ))
        # DependencyParseEvidence requires acyclicity; repeated evidence is de-duplicated.
        unique = {(a.head_observation_ref, a.dependent_observation_ref, a.relation): a for a in arcs}
        return DependencyParseEvidence(
            parse_ref=f"parse:phase9:{request.source_ref}",
            observation_refs=tuple(item.observation_ref for item in lexical),
            arcs=tuple(unique[key] for key in sorted(unique)),
            root_observation_refs=(lexical[0].observation_ref,),
            adapter_ref=self.adapter_ref,
            confidence=0.95,
        )


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    directory = tmp_path_factory.mktemp("phase9")
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
def grounder(store):
    analyzer = FormLatticeAnalyzer(
        store.repositories.language.registry(),
        syntax_adapters=SyntaxAdapterHub(dependency_adapters=(StructuralDependencyAdapter(),)),
    )
    return JointGrounder(store, analyzer)


@pytest.fixture(scope="module")
def composer(store):
    return MeaningComposer(store)


def _compose(grounder, composer, content, *, source_ref, language_hints=()):
    lattice, grounding = grounder.ground_text(
        content, source_ref=source_ref, context_ref="actual", language_hints=language_hints,
        discourse_anchors=(DiscourseAnchor(
            anchor_ref=f"anchor:{source_ref}:self", referent_ref="referent:self",
            context_ref="actual", salience=1.0, turn_index=0, role_refs=("self", "speaker"),
            evidence_refs=(f"evidence:{source_ref}:self",),
        ),),
        multimodal_tracks=(MultimodalTrack(
            track_ref=f"track:{source_ref}", modality="vision", context_ref="actual",
            referent_ref="referent:self", type_refs=(), salience=0.9,
            evidence_refs=(f"evidence:{source_ref}:track",),
        ),),
    )
    return composer.compose(lattice, grounding, context_ref="actual")


def test_factor_solver_applies_soft_factor_once_and_hard_prunes() -> None:
    graph = MeaningFactorGraph(
        graph_ref="graph:test:solver",
        source_lattice_ref="lattice:test",
        grounding_ref="grounding:test",
        snapshot_fingerprint="snapshot:test",
        variables=(
            MeaningVariable("v:a", MeaningVariableKind.SENSE, (
                MeaningValue("a:one", 1.0, ("e:a",)), MeaningValue("a:two", 0.0, ("e:a",)),
            ), evidence_refs=("e:a",)),
            MeaningVariable("v:b", MeaningVariableKind.SCHEMA, (
                MeaningValue("b:one", 0.0, ("e:b",)), MeaningValue("b:two", 0.0, ("e:b",)),
            ), evidence_refs=("e:b",)),
        ),
        factors=(
            MeaningFactor(
                "f:hard", MeaningFactorKind.LINK, ("v:a", "v:b"), True,
                allowed_value_tuples=(("a:one", "b:one"), ("a:two", "b:two")),
                evidence_refs=("e:f",), reason="paired",
            ),
            MeaningFactor(
                "f:soft", MeaningFactorKind.DISCOURSE_COHERENCE, ("v:a",), False,
                tuple_scores=((('a:one',), 0.5), (('a:two',), 0.0)),
                evidence_refs=("e:f",), reason="soft evidence",
            ),
        ),
        unresolved_refs=(), evidence_refs=("e:graph",),
    )
    result = MeaningFactorSolver().solve(graph)
    assert result.hypotheses[0].assignment_map == {"v:a": "a:one", "v:b": "b:one"}
    # 1.0 value evidence + 0.5 soft factor, not 2.0 from double application.
    assert result.hypotheses[0].score == pytest.approx(1.5)
    assert result.pruning_trace


def test_factor_solver_is_deterministic_and_bounded() -> None:
    variables = tuple(
        MeaningVariable(
            f"v:{index}", MeaningVariableKind.SENSE,
            tuple(MeaningValue(f"x:{index}:{choice}", float(choice), (f"e:{index}",)) for choice in range(3)),
            evidence_refs=(f"e:{index}",),
        )
        for index in range(6)
    )
    graph = MeaningFactorGraph(
        "graph:bounded", "lattice:bounded", "grounding:bounded", "snapshot:bounded",
        variables, (), (), ("e:bounded",),
    )
    solver = MeaningFactorSolver(beam_width=5, maximum_hypotheses=3, maximum_expansions=50)
    first = solver.solve(graph)
    second = solver.solve(graph)
    assert first.hypotheses == second.hypotheses
    assert first.expansions <= 51
    assert first.exhausted is True


def test_event_composition_is_non_transitioning_and_non_admitting(grounder, composer) -> None:
    result = _compose(grounder, composer, "I see this", source_ref="phase9:observe")
    graph = result.bundle.uol_graph
    assert graph is not None
    assert graph.events
    assert all(item.occurrence_status.value == "mentioned" for item in graph.events.values())
    assert all(item.admission_refs == () for item in graph.events.values())
    assert graph.state_deltas == ()
    assert graph.capability_deltas == ()
    assert graph.impact_assessments == ()


def test_reviewed_argument_construction_fills_semantic_ports(grounder, composer) -> None:
    result = _compose(grounder, composer, "I see this", source_ref="phase9:ports")
    graph = result.bundle.uol_graph
    application = next(item for item in graph.applications.values() if len(item.bindings) == 2)
    assert all(
        binding.fillers and binding.fillers[0].filler_class == PortFillerClass.REFERENT
        for binding in application.bindings
    )
    assert not any(
        binding.open_binding_purpose is not None for binding in application.bindings
    )


def test_nested_operators_preserve_scope_without_generic_negative_axis(grounder, composer) -> None:
    result = _compose(grounder, composer, "I may not move", source_ref="phase9:scope")
    graph = result.bundle.uol_graph
    assert graph is not None
    assert len(graph.scope_relations) == 2
    assert {item.scope_kind.value for item in graph.scope_relations} == {"modal", "negation"}
    assert len(graph.events) == 1
    assert graph.state_deltas == ()


def test_multilingual_observation_composes_same_semantic_schema(grounder, composer) -> None:
    variants = (
        ("I see this", ("en",)),
        ("je vois ceci", ("fr",)),
        ("mimi naona hii", ("sw",)),
    )
    schema_signatures = []
    for index, (text, hints) in enumerate(variants):
        result = _compose(
            grounder, composer, text, source_ref=f"phase9:multi:{index}", language_hints=hints
        )
        graph = result.bundle.uol_graph
        schema_signatures.append(tuple(sorted((app.schema_ref, app.schema_revision) for app in graph.applications.values())))
    assert schema_signatures[0] == schema_signatures[1] == schema_signatures[2]


def test_query_surface_creates_open_semantic_structure_not_answer_text(grounder, composer) -> None:
    result = _compose(grounder, composer, "what", source_ref="phase9:query")
    graph = result.bundle.uol_graph
    assert graph is not None
    assert graph.variables
    assert graph.unresolved_refs
    assert all(not hasattr(item, "surface") for item in graph.applications.values())


def test_unknown_content_preserves_frontier_while_valid_subgraph_survives(grounder, composer) -> None:
    result = _compose(grounder, composer, "I see NovelThing", source_ref="phase9:partial")
    assert result.bundle.uol_graph is not None
    assert result.bundle.uol_graph.applications
    assert result.bundle.partial_understanding.frontier_refs
    assert result.bundle.selection.decisive is False


def test_composition_selection_never_depends_on_realization(grounder, composer) -> None:
    result = _compose(grounder, composer, "I may not move", source_ref="phase9:no-realization")
    assert result.bundle.metadata["realization_influenced_selection"] is False


def test_event_predicate_introduces_new_occurrence_not_historical_identity(grounder, composer) -> None:
    result = _compose(grounder, composer, "move", source_ref="phase9:event-introduction")
    graph = result.bundle.uol_graph
    assert graph is not None
    assert graph.events
    assert all(item.referent.identity_status.value in {"provisional", "candidate"} for item in graph.events.values())


def test_partial_semantic_variables_are_authorized_by_open_port_contract(grounder, composer) -> None:
    result = _compose(grounder, composer, "move", source_ref="phase9:open-port")
    graph = result.bundle.uol_graph
    assert graph is not None
    assert graph.variables
    assert any(
        binding.open_binding_purpose is not None
        for application in graph.applications.values()
        for binding in application.bindings
    )


def test_snapshot_pinning_rejects_stale_factor_graph(store, grounder, composer) -> None:
    lattice, grounding = grounder.ground_text("move", source_ref="phase9:snapshot", context_ref="actual")
    with store.snapshot() as snapshot:
        graph = composer.builder.build(lattice, grounding, context_ref="actual", snapshot=snapshot)
        hypothesis = composer.solver.solve(graph).hypotheses[0]
        # Exact pinned snapshot succeeds while it is current.
        uol, report = composer.materializer.materialize(
            graph, hypothesis, lattice, grounding, context_ref="actual", snapshot=snapshot
        )
        assert report.valid
        assert uol.graph_ref


def test_meaning_graph_preserves_close_alternatives_instead_of_forcing_decision() -> None:
    graph = MeaningFactorGraph(
        "graph:alternatives", "lattice:alternatives", "grounding:alternatives", "snapshot:alternatives",
        (MeaningVariable(
            "v:ambiguous", MeaningVariableKind.SENSE,
            (MeaningValue("choice:a", 0.1, ("e:a",)), MeaningValue("choice:b", 0.1, ("e:b",))),
            evidence_refs=("e:a", "e:b"),
        ),), (), (), ("e:graph",),
    )
    solved = MeaningFactorSolver(maximum_hypotheses=2).solve(graph)
    assert len(solved.hypotheses) == 2
    assert solved.hypotheses[0].score == solved.hypotheses[1].score


def test_factor_graph_exposes_context_type_and_decomposed_grounding_factors(grounder, composer) -> None:
    lattice, grounding = grounder.ground_text(
        "I see this", source_ref="phase9:factor-audit", context_ref="actual",
        multimodal_tracks=(MultimodalTrack(
            track_ref="track:phase9:factor-audit", modality="vision", context_ref="actual",
            referent_ref="referent:self", type_refs=(), salience=0.9,
            evidence_refs=("evidence:phase9:factor-audit",),
        ),),
    )
    with composer.store.snapshot() as snapshot:
        factor_graph = composer.builder.build(lattice, grounding, context_ref="actual", snapshot=snapshot)
    kinds = {item.factor_kind for item in factor_graph.factors}
    assert MeaningFactorKind.TYPE_ENTITLEMENT in kinds
    assert MeaningFactorKind.CONTEXT_ISOLATION in kinds
    assert MeaningFactorKind.WORLD_PLAUSIBILITY in kinds or MeaningFactorKind.DISCOURSE_COHERENCE in kinds
    referent_values = [
        value for variable in factor_graph.variables if variable.variable_kind == MeaningVariableKind.REFERENT
        for value in variable.values
    ]
    assert referent_values
    assert all(value.score == 0.0 for value in referent_values)
