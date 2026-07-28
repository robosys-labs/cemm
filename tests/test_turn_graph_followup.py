from __future__ import annotations

import json
from types import SimpleNamespace

from cemm.form_algebra import AtomicSchemaMatcher, _expanded_turn_lattice


def unit(ref, kind, surface, features, *, semantic_ref=None, atom_kind=None, pos=0):
    return SimpleNamespace(
        unit_ref=ref,
        kind=kind,
        surface=surface,
        normalized=surface.casefold(),
        token_start=pos,
        token_end=pos + 1,
        char_start=pos,
        char_end=pos + len(surface),
        semantic_ref=semantic_ref,
        atom_kind=atom_kind,
        source_kind="test",
        score=0.0,
        features=dict(features),
        as_dict=lambda: {},
    )


def hypothesis(units, ref="h:0"):
    positioned = []
    for index, item in enumerate(units):
        values = dict(vars(item))
        values.update(
            token_start=index,
            token_end=index + 1,
            char_start=index * 4,
            char_end=index * 4 + len(item.surface),
        )
        values.pop("as_dict", None)
        positioned.append(SimpleNamespace(**values))
    return SimpleNamespace(hypothesis_ref=ref, units=tuple(positioned), score=0.0)


def lattice(units):
    return SimpleNamespace(grounding_hypotheses=(hypothesis(units),))


def designation_schema():
    return {
        "ref": "test:designation-query",
        "family": "designation_query",
        "steps": [
            {
                "slot": "query",
                "semantic_role": "force",
                "capture": "features",
                "features": {"discourse_force": "query"},
                "ports_provided": ["force:query"],
            },
            {
                "slot": "copula",
                "semantic_role": "binder",
                "capture": "features",
                "features": {"copular": True},
                "ports_provided": ["binder:predication"],
                "ports_required": ["argument:subject", "predicate:designation"],
            },
            {
                "slot": "target",
                "semantic_role": "subject",
                "kind": "anchor",
                "capture": "ref",
                "features": {"possessive": True},
                "ports_provided": ["argument:subject"],
            },
            {
                "slot": "property",
                "semantic_role": "predicate_head",
                "capture": "features",
                "features": {
                    "category": "property_marker",
                    "property_kind": "designation",
                },
                "ports_provided": ["predicate:designation"],
                "ports_required": ["argument:subject"],
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
                            "role:label_type": {"$feature": "property.property_ref"},
                            "role:surface": "?q0",
                        },
                        "stance": "support",
                    }
                ],
                "variables": [
                    {
                        "ref": "?q0",
                        "filler_kind": "literal:text",
                        "role_ref": "role:surface",
                    }
                ],
                "projection": ["?q0"],
                "qualifiers": {
                    "query_kind": "designation_property",
                    "property_ref": {"$feature": "property.property_ref"},
                },
            },
            "directive": None,
            "describe": None,
            "qualifiers": {},
            "modality": "actual",
        },
        "coverage_contract": {
            "required_semantic_roles": ["binder", "force", "predicate_head", "subject"],
            "required_slots": ["copula", "property", "query", "target"],
            "role_cardinality": {
                "binder": 1,
                "force": 1,
                "predicate_head": 1,
                "subject": 1,
            },
        },
        "graph_contract": {"projections": []},
        "ignorable_kinds": ["discourse"],
        "weight": 1.0,
    }


def core_query_units():
    return [
        unit("u:q", "function", "what", {"category": "interrogative", "discourse_force": "query"}),
        unit("u:c", "function", "is", {"category": "verb", "copular": True}),
        unit(
            "u:t",
            "anchor",
            "your",
            {"category": "reference", "possessive": True},
            semantic_ref="participant:system",
            atom_kind="participant",
        ),
        unit(
            "u:p",
            "function",
            "name",
            {
                "category": "property_marker",
                "property_kind": "designation",
                "property_ref": "label:name",
            },
        ),
    ]


def frame(dialogue=None):
    return SimpleNamespace(
        speaker_ref="participant:user",
        addressee_ref="participant:system",
        self_ref="participant:system",
        conversation_ref="conversation:test",
        dialogue_context=dict(dialogue or {}),
    )


def test_grounded_preamble_is_retained_as_nonblocking_attachment():
    units = [
        unit(
            "u:lol",
            "anchor",
            "lol",
            {"label_type": "label:abbreviation"},
            semantic_ref="concept:laughing_out_loud",
            atom_kind="concept",
        ),
        unit("u:ok", "discourse", "ok", {"discourse_marker": True}),
        unit("u:comma", "punctuation", ",", {"boundary_only": True}),
        *core_query_units(),
    ]
    expanded = _expanded_turn_lattice(lattice(units))
    assert len(expanded.grounding_hypotheses) == 2
    attached = expanded.grounding_hypotheses[1]
    assert attached.units[0].kind == "discourse"
    assert attached.units[0].semantic_ref == "concept:laughing_out_loud"
    assert attached.units[0].features["turn_attachment"] is True
    matches = AtomicSchemaMatcher((designation_schema(),), max_matches=16).matches(expanded, frame())
    executable = [item for item in matches if item.coverage.executable]
    assert executable
    assert executable[0].captures["target"] == "participant:system"
    assert any(
        residual.features.get("turn_attachment")
        for residual in executable[0].coverage.noncritical_residuals
    )


def test_prior_interjection_clause_does_not_poison_explicit_following_query():
    units = [
        unit("u:huh", "unknown", "huh", {}),
        unit("u:first-q", "punctuation", "?", {"boundary_only": True}),
        *core_query_units(),
        unit("u:last-q", "punctuation", "?", {"boundary_only": True}),
    ]
    matches = AtomicSchemaMatcher((designation_schema(),), max_matches=16).matches(lattice(units), frame())
    assert any(item.coverage.executable for item in matches)


def test_predicate_bearing_prefix_is_never_downgraded_to_preamble():
    units = [
        unit("u:i", "anchor", "I", {"participant_role": "speaker"}, semantic_ref="participant:user", atom_kind="participant"),
        unit("u:am", "function", "am", {"predicate": True, "copular": True}),
        unit("u:sad", "unknown", "sad", {}),
        unit("u:stop", "punctuation", ".", {"boundary_only": True}),
        *core_query_units(),
    ]
    expanded = _expanded_turn_lattice(lattice(units))
    assert len(expanded.grounding_hypotheses) == 1


def test_verified_dialogue_property_projects_ellipsis_predicate_head():
    semantic_signature = json.dumps(
        {
            "action": "answer_bindings",
            "qualifiers": {
                "query_kind": "designation_property",
                "property_ref": "label:name",
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    dialogue = {
        "last_surface_decision": {
            "decision_ref": "decision:1",
            "response_ref": "response:1",
            "semantic_signature": semantic_signature,
        }
    }
    units = [
        unit("u:q", "function", "what", {"discourse_force": "query"}),
        unit("u:c", "function", "is", {"copular": True}),
        unit(
            "u:t",
            "anchor",
            "yours",
            {"possessive": True},
            semantic_ref="participant:system",
            atom_kind="participant",
        ),
    ]
    matches = AtomicSchemaMatcher((designation_schema(),), max_matches=16).matches(
        lattice(units), frame(dialogue)
    )
    executable = [item for item in matches if item.coverage.executable]
    assert executable
    assert executable[0].slot_features["property"]["property_ref"] == "label:name"
    assert executable[0].projected_slots["property"]["reason"] == "verified_dialogue_property_projection"


def test_ellipsis_without_verified_property_focus_remains_unresolved():
    units = [
        unit("u:q", "function", "what", {"discourse_force": "query"}),
        unit("u:c", "function", "is", {"copular": True}),
        unit(
            "u:t",
            "anchor",
            "mine",
            {"possessive": True},
            semantic_ref="participant:user",
            atom_kind="participant",
        ),
    ]
    matches = AtomicSchemaMatcher((designation_schema(),), max_matches=16).matches(
        lattice(units), frame()
    )
    assert not any(item.coverage.executable for item in matches)
