"""R4 all-surface expansion tests."""
from __future__ import annotations

import inspect
import ast
import json
import hashlib
import subprocess
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest

from scripts.expand_r4_cases import _MAX_SCENARIO_BYTES, _read_source
from cemm_authoritative_hybrid.authority import AtomRecord, DesignationIndex
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import (
    ExpectedCycleContractCompiler,
    ReviewedScenario,
)
from cemm_authoritative_hybrid.r4_expansion import (
    CaseExpander,
    ExpandedCase,
    SourceDisposition,
    expand_reviewed_source_universe,
)

__cemm_test_inventory__ = {'tests/test_r4_expansion.py::test_sr1_source_universe_is_model_free_exact_and_disjoint': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-sr1-source-universe-model-free-exact-disjoint',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4.1-SR1',
                                                                                           'owner_ref': 'surface-expansion',
                                                                                           'source_ast_sha256': 'f0e011c8540eee513ee1a25ee6715426b36b8a2af47e2dd6c4504fcc50bc233a'},
 'tests/test_r4_expansion.py::test_sr1_source_disposition_is_closed_and_conflicts_remain_alternatives': {'activation_phase': 'R4',
                                                                                                         'assertion_ref': 'assertion:r4-sr1-source-disposition-closed-conflicts-alternatives',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R4.1-SR1',
                                                                                                         'owner_ref': 'surface-expansion',
                                                                                                         'source_ast_sha256': '29c69d2ee606c464c0f55bb6452a0f56c550a8bf46cc7f77e09e727242f4595b'},
 'tests/test_r4_expansion.py::test_sr1_source_seam_accepts_no_caller_revision_or_model_state': {'activation_phase': 'R4',
                                                                                                'assertion_ref': 'assertion:r4-sr1-source-seam-no-caller-runtime-state',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R4.1-SR1',
                                                                                                'owner_ref': 'surface-expansion',
                                                                                                'source_ast_sha256': 'b2ea1f57797ccb18c4db210023ed683179d968572f4efbb92b60b556c06d7f35'},
 'tests/test_r4_expansion.py::test_sr1_source_seam_bounds_iterators_before_materialization': {'activation_phase': 'R4',
                                                                                              'assertion_ref': 'assertion:r4-sr1-source-seam-bounded-before-materialization',
                                                                                              'diagnostic_role': 'owner',
                                                                                              'introduced_by_task': 'R4.1-SR1',
                                                                                              'owner_ref': 'surface-expansion',
                                                                                              'source_ast_sha256': '49edb8e4d619f416544ac7d27f5d36d3b365272e9251d72defaaa214506eadab'},
 'tests/test_r4_expansion.py::test_sr1_source_seam_operation_counts_are_linear': {'activation_phase': 'R4',
                                                                                  'assertion_ref': 'assertion:r4-sr1-source-seam-linear-operation-counts',
                                                                                  'diagnostic_role': 'owner',
                                                                                  'introduced_by_task': 'R4.1-SR1',
                                                                                  'owner_ref': 'surface-expansion',
                                                                                  'source_ast_sha256': '3efe4114b02d9993facc67ce0f94489dde868905dab236319ff62716ddb5ae78'},
 'tests/test_r4_expansion.py::test_sr1_expansion_cli_is_deterministic_and_source_only': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:r4-sr1-expansion-cli-deterministic-source-only',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R4.1-SR1',
                                                                                         'owner_ref': 'surface-expansion',
                                                                                         'source_ast_sha256': '15404ab60e3665eb6a02435195fef3b10ed8ec2b3b61633ce5670d2862bd466d'},
 'tests/test_r4_expansion.py::test_expander_uses_every_reviewed_surface_and_environment': {'activation_phase': 'R4',
                                                                                           'assertion_ref': 'assertion:r4-expander-uses-every-reviewed-surface-and-environment',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R4-Complete',
                                                                                           'owner_ref': 'surface-expansion',
                                                                                           'source_ast_sha256': '680dd423e3d81a0a44a01d675c3721a6bb9e36b7f3106333502c3b1734308387'},
 'tests/test_r4_expansion.py::test_paraphrase_surfaces_are_isolated_trajectories_by_default': {'activation_phase': 'R4',
                                                                                               'assertion_ref': 'assertion:r4-paraphrase-trajectories-are-isolated',
                                                                                               'diagnostic_role': 'owner',
                                                                                               'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                               'owner_ref': 'surface-expansion',
                                                                                               'source_ast_sha256': 'af4157ebce344c48c8967f8d5d6a8d9f6a1dbb18bdec960cac160850c7fccec0'}}



class _Authority:
    generation = "authority:test"
    atoms = {
        ref: AtomRecord(ref=ref, kind=kind)
        for ref, kind in {
            "rel:mother_in_law": "relation_type",
            "entity:lamp": "entity",
            "dim:power": "state_dimension",
            "value:on": "state_value",
            "value:off": "state_value",
        }.items()
    }
    event_signatures = {}
    value_dimensions = {"value:on": "dim:power", "value:off": "dim:power"}
    designations = DesignationIndex(
        by_surface={("mother-in-law", "en"): ("rel:mother_in_law",)},
        by_target={("rel:mother_in_law", "en"): ("mother-in-law",)},
    )
    capabilities = {}
    permissions = ()
    adapters = ()
    operator_roles = {}
    rules = {}


def _scenario():
    return ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:multi",
            "review_status": "reviewed",
            "competency_category": "designation_definition",
            "semantic_assertions": [
                {
                    "kind": "designates",
                    "surface": "mother-in-law",
                    "target": "rel:mother_in_law",
                }
            ],
            "surface_examples": [
                "mother-in-law",
                "mother in law",
                "spouse's mother",
            ],
            "metadata": {},
        }
    )


def _compiler():
    return ExpectedCycleContractCompiler(_Authority(), abi_registry_ref="abi:test")


def _pin():
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


@lru_cache(maxsize=1)
def _linked_authority():
    from cemm_authoritative_hybrid.authority import AuthorityLinker

    root = Path(__file__).parents[1]
    return AuthorityLinker().link_path(root / "data/authority/manifest.json")


def test_expander_uses_every_reviewed_surface_and_environment() -> None:
    expanded = CaseExpander(_compiler()).expand(
        _scenario(), revision_pin=_pin(), environments=({}, {"permission_refs": []})
    )
    assert len(expanded) == 6
    assert {row.surface for row in expanded} == set(_scenario().surface_examples)
    assert all(ExpandedCase.from_dict(row.as_dict()) == row for row in expanded)


def test_paraphrase_surfaces_are_isolated_trajectories_by_default() -> None:
    expanded = CaseExpander(_compiler()).expand(
        _scenario(), revision_pin=_pin(), environments=({},)
    )
    assert len({row.trajectory_ref for row in expanded}) == len(expanded)
    assert {row.turn_index for row in expanded} == {0}


def test_sr1_source_universe_is_model_free_exact_and_disjoint() -> None:
    root = Path(__file__).parents[1]
    authority = _linked_authority()
    scenarios = tuple(
        ReviewedScenario.from_dict(json.loads(line))
        for line in (root / "data/scenarios/use_cases.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    )
    universe = expand_reviewed_source_universe(scenarios, authority=authority)
    assert universe.scenario_count == 210
    assert universe.expanded_count == 400
    assert universe.disposition_counts == {
        "semantic": 248,
        "explicit_gap": 112,
        "verification_rejection": 20,
        "restart_diagnostic_candidate": 20,
    }
    assert universe.operation_counts == {
        "scenario_next_calls": 211,
        "environment_next_calls": 420,
        "disposition_classifications": 210,
        "aggregate_bound_checks": 210,
        "case_emissions": 400,
    }
    assert Counter(row.source_disposition.value for row in universe.cases) == Counter(
        universe.disposition_counts
    )
    assert universe.case_set_digest == (
        "262e9f6de46ceeb991e3cb8abda2df143b866c2f5c77bccd00c3856a2916764d"
    )
    digest_material = (
        "\n".join(sorted(row.case_ref for row in universe.cases)) + "\n"
    ).encode("utf-8")
    assert len(digest_material) == 16_800
    assert hashlib.sha256(digest_material).hexdigest() == universe.case_set_digest
    assert {row.contract.revision_pin.model_identity for row in universe.cases} == {None}
    assert all(
        row.contract.revision_pin.world_revision
        == row.contract.revision_pin.session_revision
        == row.contract.revision_pin.episode_revision
        == row.contract.revision_pin.effect_revision
        == 0
        for row in universe.cases
    )


def test_sr1_source_disposition_is_closed_and_conflicts_remain_alternatives() -> None:
    from cemm_authoritative_hybrid.r4_supervision import (
        SourceDisposition as SupervisionSourceDisposition,
        source_disposition_is_supervision_eligible,
    )

    assert {row.value for row in SourceDisposition} == {
        "semantic",
        "explicit_gap",
        "verification_rejection",
        "restart_diagnostic_candidate",
    }
    assert SupervisionSourceDisposition is SourceDisposition
    assert all(
        source_disposition_is_supervision_eligible(disposition)
        is (disposition is not SourceDisposition.RESTART_DIAGNOSTIC_CANDIDATE)
        for disposition in SourceDisposition
    )
    with pytest.raises(TypeError, match="exact SourceDisposition"):
        source_disposition_is_supervision_eligible("semantic")  # type: ignore[arg-type]
    conflict = ReviewedScenario.from_dict(
        {
            "scenario_ref": "scenario:conflict",
            "review_status": "reviewed",
            "competency_category": "contradiction",
            "semantic_assertions": [
                {
                    "kind": "contradiction",
                    "subject": "entity:lamp",
                    "dimension": "dim:power",
                    "values": ["value:on", "value:off"],
                }
            ],
            "surface_examples": ["the lamp is on and off"],
            "metadata": {},
        }
    )
    rows = CaseExpander(_compiler()).expand(
        conflict, revision_pin=_pin(), environments=({},)
    )
    assert rows[0].source_disposition is SourceDisposition.SEMANTIC
    assert rows[0].contract.expression_relation.value == "conflict"
    assert len(rows[0].contract.expected_expressions) == 2
    assert all(
        len(expression.root_refs) == 1
        for expression in rows[0].contract.expected_expressions
    )


def test_sr1_source_seam_accepts_no_caller_revision_or_model_state() -> None:
    parameters = inspect.signature(expand_reviewed_source_universe).parameters
    assert "revision_pin" not in parameters
    assert "model_identity" not in parameters
    assert "runtime" not in parameters
    assert "abi_registry_ref" not in parameters
    with pytest.raises(TypeError):
        expand_reviewed_source_universe(  # type: ignore[call-arg]
            (_scenario(),), authority=_linked_authority(), revision_pin=_pin()
        )


class _CountingIterator:
    def __init__(self, value: object) -> None:
        self.calls = 0
        self._value = value

    def __iter__(self):
        return self

    def __next__(self):
        self.calls += 1
        return self._value


def test_sr1_source_seam_bounds_iterators_before_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hostile_scenarios = _CountingIterator(_scenario())
    with pytest.raises(ValueError, match="scenario.*bound"):
        expand_reviewed_source_universe(
            hostile_scenarios, authority=_linked_authority(), max_scenarios=3
        )
    assert hostile_scenarios.calls == 4

    hostile_environments = _CountingIterator({})
    with pytest.raises(ValueError, match="environment.*bound"):
        CaseExpander(_compiler(), max_environments_per_surface=3).expand(
            _scenario(), revision_pin=_pin(), environments=hostile_environments
        )
    assert hostile_environments.calls == 4

    hostile_scenarios = _CountingIterator(_scenario())
    with pytest.raises(ValueError, match="environment map.*bound"):
        expand_reviewed_source_universe(
            hostile_scenarios,
            authority=_linked_authority(),
            reviewed_environments={f"scenario:{index}": ({},) for index in range(4)},
            max_scenarios=3,
        )
    assert hostile_scenarios.calls == 0

    with pytest.raises(ValueError, match="duplicate reviewed environments"):
        expand_reviewed_source_universe(
            (_scenario(),),
            authority=_linked_authority(),
            reviewed_environments={_scenario().scenario_ref: ({}, {})},
        )
    with pytest.raises(TypeError, match="environments must contain mappings"):
        expand_reviewed_source_universe(
            (_scenario(),),
            authority=_linked_authority(),
            reviewed_environments={_scenario().scenario_ref: (object(),)},  # type: ignore[dict-item]
        )

    def forbidden_expand(*_args, **_kwargs):
        raise AssertionError("aggregate bound must fail before CaseExpander materializes")

    monkeypatch.setattr(CaseExpander, "expand", forbidden_expand)
    with pytest.raises(ValueError, match="aggregate expanded case stream"):
        expand_reviewed_source_universe(
            (_scenario(),),
            authority=_linked_authority(),
            max_expanded_cases=2,
        )


def test_sr1_source_seam_operation_counts_are_linear() -> None:
    scenarios = tuple(
        ReviewedScenario.from_dict(
            {**_scenario().as_dict(), "scenario_ref": f"scenario:multi-{index}"}
        )
        for index in range(3)
    )
    universe = expand_reviewed_source_universe(
        iter(scenarios),
        authority=_linked_authority(),
        max_scenarios=3,
        max_expanded_cases=16,
    )
    assert universe.operation_counts == {
        "scenario_next_calls": 4,
        "environment_next_calls": 6,
        "disposition_classifications": 3,
        "aggregate_bound_checks": 3,
        "case_emissions": 9,
    }


def test_sr1_expansion_cli_is_deterministic_and_source_only(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    script = root / "scripts/expand_r4_cases.py"
    left = tmp_path / "left.jsonl"
    right = tmp_path / "right.jsonl"
    summaries = []
    for output in (left, right):
        result = subprocess.run(
            [sys.executable, str(script), "--root", str(root), "--output", str(output)],
            check=True,
            capture_output=True,
            text=True,
        )
        summaries.append(json.loads(result.stdout))
    assert left.read_bytes() == right.read_bytes()
    assert summaries[0] == summaries[1]
    assert summaries[0]["scenario_count"] == 210
    assert summaries[0]["expanded_count"] == 400
    assert summaries[0]["case_set_digest"] == (
        "262e9f6de46ceeb991e3cb8abda2df143b866c2f5c77bccd00c3856a2916764d"
    )
    rows = [json.loads(line) for line in left.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 400
    assert all(row["contract"]["revision_pin"]["model_identity"] is None for row in rows)

    oversized = tmp_path / "oversized.jsonl"
    oversized.write_bytes(b"x" * (_MAX_SCENARIO_BYTES + 1))
    with pytest.raises(ValueError, match="byte bound"):
        _read_source(oversized)
    malformed_rows = {
        "blank": b"\n",
        "duplicate": b'{"a":1,"a":2}\n',
        "noncanonical": b'{"b":1, "a":2}\n',
        "nonfinite": b'{"a":NaN}\n',
        "utf8": b"\xff\n",
    }
    for name, payload in malformed_rows.items():
        source = tmp_path / f"{name}.jsonl"
        source.write_bytes(payload)
        with pytest.raises(ValueError):
            _, source_rows = _read_source(source)
            tuple(source_rows)

    row = _scenario().as_dict()
    bounded_source = tmp_path / "513-scenarios.jsonl"
    bounded_source.write_text(
        "\n".join(
            json.dumps(
                {**row, "scenario_ref": f"scenario:bounded-{index:04d}"},
                sort_keys=True,
                separators=(",", ":"),
            )
            for index in range(513)
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _, source_rows = _read_source(bounded_source)
    with pytest.raises(ValueError, match="reviewed scenario exceeds bound"):
        expand_reviewed_source_universe(source_rows, authority=_linked_authority())

    owner = root / "src/cemm_authoritative_hybrid/r4_expansion.py"
    names: set[str] = set()
    for path in (script, owner):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names |= {
            node.id.lower()
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        } | {
            node.attr.lower()
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        } | {
            alias.name.lower()
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
    forbidden = {
        "propose",
        "verify",
        "evaluate",
        "effect",
        "realize",
        "runtime",
        "bootstrap",
        "model",
        "solver",
        "episode",
    }
    assert not {
        forbidden_name
        for forbidden_name in forbidden
        if any(forbidden_name in name.split(".") for name in names)
    }
