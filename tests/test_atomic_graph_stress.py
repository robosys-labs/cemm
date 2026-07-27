from __future__ import annotations

from itertools import permutations, product
from types import SimpleNamespace

from cemm.atomic_graph import AtomicGraphMatcher, UnitView, deterministic_participant_reference


def unit(ref, kind, token, features, *, semantic_ref=None, atom_kind=None, source_kind=None, score=0.0, pos=0):
    return UnitView(
        ref,
        kind,
        token,
        token.casefold(),
        pos,
        pos + 1,
        pos,
        pos + len(token),
        semantic_ref,
        atom_kind,
        source_kind,
        score,
        features,
    )


def designation_schema():
    return {
        "ref": "en:graph:designation_query",
        "family": "designation_query",
        "steps": [
            {
                "slot": "force",
                "semantic_role": "force",
                "capture": "features",
                "features": {"discourse_force": "query"},
                "ports_provided": ["force:query"],
            },
            {
                "slot": "target",
                "semantic_role": "subject",
                "capture": "ref",
                "kind": "anchor",
                "features": {"category": "reference", "possessive": True},
                "ports_provided": ["argument:subject"],
            },
            {
                "slot": "predicate_head",
                "semantic_role": "predicate_head",
                "capture": "features",
                "features": {"category": "property_marker", "property_kind": "designation"},
                "ports_provided": ["predicate:designation"],
                "ports_required": ["argument:subject"],
            },
            {
                "slot": "binder",
                "semantic_role": "binder",
                "capture": "features",
                "features": {"copular": True, "semantic_port": "predication"},
                "ports_provided": ["binder:predication"],
                "ports_required": ["argument:subject", "predicate:designation"],
            },
        ],
        "packet": {
            "force": "query",
            "apps": [],
            "query": {
                "restrictions": [
                    {
                        "operator": "op:designation",
                        "args": {
                            "role:target": {"$capture": "target"},
                            "role:label_type": {"$feature": "predicate_head.property_ref"},
                            "role:surface": "?q0",
                        },
                        "stance": "support",
                    }
                ],
                "variables": [{"ref": "?q0", "filler_kind": "literal:text", "role_ref": "role:surface"}],
                "projection": ["?q0"],
                "qualifiers": {"query_kind": "designation_property"},
            },
            "directive": None,
            "describe": None,
            "qualifiers": {"construction_family": "designation_query"},
            "modality": "actual",
        },
        "weight": 1.75,
        "graph_contract": {
            "order_preferences": [
                {"before": "force", "after": "binder", "weight": 0.04},
                {"before": "target", "after": "predicate_head", "weight": 0.08},
            ],
            "hard_constraints": [
                {"kind": "max_distance", "slots": ["target", "predicate_head"], "max_distance": 4}
            ],
            "projections": [
                {
                    "slot": "binder",
                    "source": "constant",
                    "value": {"implicit": True, "copular": True, "semantic_port": "predication"},
                    "features": {"implicit": True, "copular": True, "semantic_port": "predication"},
                    "requires_slots": ["force", "target", "predicate_head"],
                    "ports_provided": ["binder:predication"],
                    "penalty": 0.16,
                    "reason": "implicit_copular_binding",
                },
                {
                    "slot": "target",
                    "source": "context",
                    "context_path": "addressee_ref",
                    "features": {"projected": True, "participant_role": "addressee", "possessive": True},
                    "requires_slots": ["force", "predicate_head"],
                    "ports_provided": ["argument:subject"],
                    "penalty": 0.24,
                    "reason": "direct_dialogue_addressee_projection",
                },
            ],
        },
    }


def lattice(units):
    positioned = []
    cursor = 0
    for index, item in enumerate(units):
        positioned.append(
            UnitView(
                item.unit_ref,
                item.kind,
                item.surface,
                item.normalized,
                index,
                index + 1,
                cursor,
                cursor + len(item.surface),
                item.semantic_ref,
                item.atom_kind,
                item.source_kind,
                item.score,
                item.features,
            )
        )
        cursor += len(item.surface) + 1
    hyp = SimpleNamespace(hypothesis_ref="h:test", units=tuple(positioned), score=0.0)
    return SimpleNamespace(grounding_hypotheses=(hyp,))


def atoms(target_ref="participant:system", property_ref="label:name", binder="is", force_kind="word"):
    target = unit(
        "u:target", "anchor", "your",
        {"category": "reference", "participant_role": "addressee", "person": "second", "possessive": True},
        semantic_ref=target_ref, atom_kind="participant", source_kind="reference",
    )
    predicate = unit(
        "u:predicate", "function", "name",
        {"category": "property_marker", "property_ref": property_ref, "property_kind": "designation"},
    )
    copula = unit(
        "u:binder", "function", binder,
        {"category": "verb", "lemma": "be", "predicate": True, "copular": True, "semantic_port": "predication"},
    )
    force = unit(
        "u:force", "punctuation" if force_kind == "punctuation" else "function", "?" if force_kind == "punctuation" else "what",
        {"category": "boundary" if force_kind == "punctuation" else "interrogative", "discourse_force": "query", "force_evidence": "query"},
    )
    return target, predicate, copula, force


def test_echo_query_and_canonical_query_are_same_family():
    matcher = AtomicGraphMatcher((designation_schema(),), max_matches=16)
    target, predicate, binder, force = atoms(force_kind="punctuation")
    echo = matcher.matches(lattice((target, predicate, binder, force)), context={"addressee_ref": "participant:system"})
    assert echo and echo[0].coverage.executable
    assert echo[0].schema_family == "designation_query"
    target, predicate, binder, force = atoms(force_kind="word")
    canonical = matcher.matches(lattice((force, binder, target, predicate)), context={"addressee_ref": "participant:system"})
    assert canonical and canonical[0].coverage.executable
    assert canonical[0].captures["target"] == echo[0].captures["target"]


def test_missing_binder_and_target_are_typed_projections():
    matcher = AtomicGraphMatcher((designation_schema(),), max_matches=16)
    target, predicate, _, force = atoms(force_kind="punctuation")
    no_binder = matcher.matches(lattice((target, predicate, force)), context={"addressee_ref": "participant:system"})
    assert no_binder[0].coverage.executable
    assert "binder" in no_binder[0].projected
    _, predicate, binder, force = atoms(force_kind="punctuation")
    no_target = matcher.matches(lattice((predicate, binder, force)), context={"addressee_ref": "participant:system"})
    assert no_target[0].coverage.executable
    assert no_target[0].captures["target"] == "participant:system"
    assert "target" in no_target[0].projected


def test_grounded_residual_never_becomes_unknown_form():
    matcher = AtomicGraphMatcher((designation_schema(),), max_matches=16)
    target = unit(
        "u:target", "anchor", "you",
        {"category": "reference", "participant_role": "addressee", "person": "second", "possessive": False},
        semantic_ref="participant:system", atom_kind="participant", source_kind="reference",
    )
    result = matcher.matches(lattice((target,)), context={"addressee_ref": "participant:system"})
    assert result
    residuals = result[0].coverage.residuals
    assert residuals
    assert residuals[0].semantic_ref == "participant:system"
    assert residuals[0].grounding_status == "grounded"
    assert residuals[0].residual_class == "grounded_argument_unassigned"


def test_deterministic_participant_reference_dominates_raw_alternative():
    result = deterministic_participant_reference(
        lexical_features={"participant_role": "addressee", "person": "second"},
        semantic_candidates=[("participant:system", 1.0, {"participant_role": "addressee"})],
    )
    assert result and result[0] == "participant:system"
    ambiguous = deterministic_participant_reference(
        lexical_features={"participant_role": "addressee"},
        semantic_candidates=[
            ("participant:system", 1.0, {}),
            ("participant:other", 0.9, {}),
        ],
    )
    assert ambiguous is None


def test_576_positive_compositional_variants():
    matcher = AtomicGraphMatcher((designation_schema(),), max_matches=8, state_budget=20000)
    target_refs = ["participant:system", "participant:user", "entity:alice"]
    properties = ["label:name", "label:name_full", "label:title"]
    binders = ["is", "was", "be", "being"]
    force_kinds = ["word", "punctuation"]
    discourse_counts = [0, 1]
    orders = [
        ("force", "binder", "target", "predicate"),
        ("target", "predicate", "binder", "force"),
        ("force", "target", "predicate", "binder"),
        ("target", "binder", "predicate", "force"),
    ]
    total = 0
    for target_ref, property_ref, binder_text, force_kind, discourse_count, order in product(
        target_refs, properties, binders, force_kinds, discourse_counts, orders
    ):
        target, predicate, binder, force = atoms(target_ref, property_ref, binder_text, force_kind)
        mapping = {"target": target, "predicate": predicate, "binder": binder, "force": force}
        units = [mapping[key] for key in order]
        if discourse_count:
            units.insert(0, unit("u:disc", "discourse", "well", {"discourse_marker": True}))
        matches = matcher.matches(lattice(units), context={"addressee_ref": "participant:system"})
        assert matches and matches[0].coverage.executable, (target_ref, property_ref, binder_text, force_kind, order)
        assert matches[0].captures["target"] == target_ref
        assert matches[0].slot_features["predicate_head"]["property_ref"] == property_ref
        total += 1
    assert total == 576


def test_all_24_core_permutations_remain_bounded_and_executable():
    matcher = AtomicGraphMatcher((designation_schema(),), max_matches=8, state_budget=20000)
    core = atoms(force_kind="punctuation")
    for order in permutations(core):
        matches = matcher.matches(lattice(order), context={"addressee_ref": "participant:system"})
        assert matches and matches[0].coverage.executable
        assert matches[0].diagnostics["search_states"] <= 20000


def test_300_negative_and_partial_cases_do_not_fake_lexical_unknowns():
    matcher = AtomicGraphMatcher((designation_schema(),), max_matches=8)
    target, predicate, binder, force = atoms(force_kind="punctuation")
    cases = []
    for index in range(100):
        wrong_property = unit(
            f"bad:p:{index}", "function", "state",
            {"category": "property_marker", "property_ref": f"dim:{index}", "property_kind": "state"},
        )
        cases.append((target, wrong_property, binder, force))
        cases.append((target, predicate, binder))  # no force
        cases.append((predicate,))  # partial known predicate
    assert len(cases) == 300
    for case in cases:
        matches = matcher.matches(lattice(case), context={"addressee_ref": "participant:system"})
        assert not matches or not matches[0].coverage.executable
        if matches:
            assert all(item.residual_class != "unknown_form" for item in matches[0].coverage.residuals)
