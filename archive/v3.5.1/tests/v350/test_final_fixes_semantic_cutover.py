from __future__ import annotations

import json
from pathlib import Path

from cemm.v350.final_activation import decide_turn_language, enumerate_form_paths
from cemm.v350.language.model import FormCandidate, FormObservation, Span
from cemm.v350.schema.model import PortFillerClass, StorageKind
from cemm.v350.uol.equivalence import semantic_graph_fingerprint
from cemm.v350.uol.model import FillerRef, IdentityStatus, Referent, UOLGraph


def _observation(ref: str, start: int, text: str) -> FormObservation:
    return FormObservation(
        observation_ref=ref,
        span=Span(start, start + len(text)),
        original=text,
        canonical=text.casefold(),
        script="Latin",
        category="word",
        evidence_refs=(f"evidence:{ref}",),
    )


def _form(
    ref: str,
    observations: tuple[FormObservation, ...],
    *,
    language_tag: str = "en",
    confidence: float = 1.0,
) -> FormCandidate:
    return FormCandidate(
        candidate_ref=ref,
        observation_refs=tuple(item.observation_ref for item in observations),
        span=Span(observations[0].span.start, observations[-1].span.end),
        form_ref=f"form:{ref}",
        form_revision=1,
        language_tag=language_tag,
        confidence=confidence,
        evidence_refs=(f"evidence:{ref}",),
    )


def test_unknown_same_script_span_does_not_manufacture_multilingual_turn() -> None:
    known = _observation("known", 0, "hello")
    unknown = _observation("unknown", 6, "xylophonicnonce")
    english = _form("hello-en", (known,), language_tag="en")

    decision = decide_turn_language((known, unknown), (english,))

    assert decision.language_tag == "en"
    assert decision.positive_language_tags == ("en",)
    assert decision.code_switching is False
    assert decision.competing_tags == ()


def test_form_paths_make_atomic_and_multiword_coverage_alternatives() -> None:
    left = _observation("left", 0, "za")
    right = _observation("right", 3, "tu")
    atomic_left = _form("atomic-left", (left,))
    atomic_right = _form("atomic-right", (right,))
    multi = _form("multi", (left, right))

    paths = enumerate_form_paths(
        (left, right),
        (atomic_left, atomic_right, multi),
    )
    complete = tuple(path for path in paths if not path.gap_observation_refs)

    assert complete
    selected = {
        frozenset(path.selected_form_candidate_refs)
        for path in complete
    }
    assert frozenset({"multi"}) in selected
    assert frozenset({"atomic-left", "atomic-right"}) in selected
    assert all(
        not (
            "multi" in path.selected_form_candidate_refs
            and (
                "atomic-left" in path.selected_form_candidate_refs
                or "atomic-right" in path.selected_form_candidate_refs
            )
        )
        for path in paths
    )


def test_schema_topic_identity_participates_in_semantic_fingerprint() -> None:
    left = Referent(
        referent_ref="schema-topic:left",
        storage_kind=StorageKind.SCHEMA_TOPIC,
        identity_status=IdentityStatus.RESOLVED,
        context_refs=("actual",),
        permission_ref="public",
        metadata={"schema_ref": "state-value:left", "schema_revision": 1},
    )
    right = Referent(
        referent_ref="schema-topic:right",
        storage_kind=StorageKind.SCHEMA_TOPIC,
        identity_status=IdentityStatus.RESOLVED,
        context_refs=("actual",),
        permission_ref="public",
        metadata={"schema_ref": "state-value:right", "schema_revision": 1},
    )
    left_graph = UOLGraph(
        graph_ref="graph:left",
        referents={left.referent_ref: left},
        root_refs=(FillerRef(PortFillerClass.REFERENT, left.referent_ref),),
        evidence_refs=("evidence:test",),
    )
    right_graph = UOLGraph(
        graph_ref="graph:right",
        referents={right.referent_ref: right},
        root_refs=(FillerRef(PortFillerClass.REFERENT, right.referent_ref),),
        evidence_refs=("evidence:test",),
    )

    assert semantic_graph_fingerprint(left_graph) != semantic_graph_fingerprint(
        right_graph
    )


def _records(repo_root: Path, name: str) -> list[dict]:
    path = repo_root / "cemm" / "data" / "v350" / "final_fixes" / name
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_final_fix_seed_is_atomic_and_generic() -> None:
    root = Path(__file__).resolve().parents[2]
    forms = _records(root, "language_form.jsonl")
    constructions = _records(root, "construction.jsonl")

    surfaces = {item["normalized_form"] for item in forms}
    assert {"name", "is", "are", "do", "what"}.issubset(surfaces)
    assert "what is your name" not in surfaces
    assert "how are you" not in surfaces
    assert "what can you do" not in surfaces

    generic_property = [
        item for item in constructions
        if item["metadata"].get("generic_semantic_family")
        == "property_interrogative"
    ]
    assert {item["pack_ref"] for item in generic_property} == {
        "language-pack:en",
        "language-pack:fr",
        "language-pack:sw",
    }
    assert all(
        item["metadata"].get("predicate_schema_slot") == "predicate"
        for item in generic_property
    )


def test_name_query_uses_structural_identity_adapter_and_durable_value_anchor() -> None:
    root = Path(__file__).resolve().parents[2]
    schemas = _records(root, "schema.jsonl")
    facets = _records(root, "identity_facet.jsonl")

    name = next(
        item for item in schemas
        if item["schema_ref"] == "property:name"
        and item["revision"] == 3
    )
    assert name["metadata"]["query_adapter_kind"] == "identity_facet"
    assert (
        name["metadata"]["identity_facet_selector_ref"]
        == "identity:self:name:value-anchor"
    )
    value = next(
        item for item in facets
        if item["identity_facet_ref"] == "identity:self:name:value-anchor"
    )
    assert value["referent_ref"] == "referent:self"
    assert value["anchor_ref"] == "referent:name:cemm"
    assert value["normalized_value"] == "CEMM"


def test_query_projection_schemas_are_semantic_not_phrase_catalogues() -> None:
    root = Path(__file__).resolve().parents[2]
    schemas = _records(root, "schema.jsonl")
    by_ref = {item["schema_ref"]: item for item in schemas}

    assert (
        by_ref["function:qualitative_state_projection"]["metadata"][
            "query_adapter_kind"
        ]
        == "state_view"
    )
    assert (
        by_ref["function:capability_projection"]["metadata"][
            "query_adapter_kind"
        ]
        == "capability_instance"
    )


def test_is_and_are_share_one_be_lexeme_family() -> None:
    root = Path(__file__).resolve().parents[2]
    links = _records(root, "form_lexeme_link.jsonl")
    be_links = {
        item["form_ref"]: item["lexeme_ref"]
        for item in links
        if item["form_ref"] in {
            "form:en:final:is",
            "form:en:final:are",
        }
    }
    assert be_links == {
        "form:en:final:is": "lexeme:en:final:be",
        "form:en:final:are": "lexeme:en:final:be",
    }


def test_learning_cutover_flag_remains_false_until_restart_matrix_passes() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (root / "cemm" / "data" / "v350" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["metadata"]["learning_runtime_cutover"] is False
