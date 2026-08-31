"""Source-only Task 10A authoring evidence over the full successor universe."""
from __future__ import annotations

from functools import lru_cache
import inspect
import json
from pathlib import Path

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.r4_authoring import build_source_authoring_cache
from cemm_authoritative_hybrid.r4_contracts import ReviewedScenario
from cemm_authoritative_hybrid.r4_expansion import expand_reviewed_source_universe

from scripts.build_r4_1_review_worksheets import _PROPOSALS

ROOT = Path(__file__).parents[1]


@lru_cache(maxsize=1)
def _source_inputs():
    authority = AuthorityLinker().link_path(ROOT / "data/authority/manifest.json")
    current = tuple(
        ReviewedScenario.from_dict(json.loads(line))
        for line in (ROOT / "data/scenarios/use_cases.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    )
    candidates = tuple(
        ReviewedScenario.from_dict(row["scenario"])
        for row in _PROPOSALS
    )
    cases = (
        *expand_reviewed_source_universe(current, authority=authority).cases,
        *expand_reviewed_source_universe(candidates, authority=authority).cases,
    )
    form_pack = json.loads(
        (ROOT / "data/languages/en/forms.json").read_text(encoding="utf-8")
    )
    return authority, cases, form_pack


@lru_cache(maxsize=1)
def _cache():
    authority, cases, form_pack = _source_inputs()
    return build_source_authoring_cache(
        cases=tuple(cases),
        authority=authority,
        form_pack=form_pack,
        config=RuntimeConfig.release(),
    )


def test_source_authoring_cache_covers_every_supervised_successor_once() -> None:
    cache = _cache()
    assert len(cache.cases) == 388
    expected = {case.case_ref for case in cache.cases}
    assert set(cache.cases_by_ref) == expected
    assert set(cache.form_lattices_by_case) == expected
    assert set(cache.grounding_results_by_case) == expected
    assert set(cache.proposal_contexts_by_case) == expected
    assert set(cache.designation_sets_by_case) == expected
    assert set(cache.proposal_recipe_suggestions_by_case) == expected
    assert cache.operation_counts["form_lattice_builds"] == len(expected)
    assert cache.operation_counts["grounding_builds"] == len(expected)
    assert cache.operation_counts["proposal_context_builds"] == len(expected)
    assert cache.operation_counts["proposal_recipe_normalizations"] == len(expected)


def test_proposal_recipe_suggestions_cover_56_source_owned_families() -> None:
    cache = _cache()
    suggestions = tuple(cache.proposal_recipe_suggestions_by_case.values())
    assert len(suggestions) == 388
    families_by_target = {
        target: {
            row.family_ref for row in suggestions if row.target_kind == target
        }
        for target in ("derive", "abstain", "verification_rejection")
    }
    assert {target: len(refs) for target, refs in families_by_target.items()} == {
        "derive": 34,
        "abstain": 21,
        "verification_rejection": 1,
    }
    assert all(row.selectable is False for row in suggestions)
    for row in suggestions:
        rendered_key = json.dumps(
            row.as_dict()["normalized_family_key"], sort_keys=True
        )
        assert row.source_case_ref not in rendered_key
        assert "reviewed_surface:" not in rendered_key
        assert "expected_cycle_contract" not in rendered_key
        assert "expression:" not in rendered_key


def test_designation_sets_are_complete_authority_facts_on_form_geometry() -> None:
    authority, _, _ = _source_inputs()
    cache = _cache()
    nonempty = 0
    empty = 0
    for case_ref, designation_set in cache.designation_sets_by_case.items():
        case = cache.cases_by_ref[case_ref]
        lattice = cache.form_lattices_by_case[case_ref]
        units = tuple(unit for unit in lattice.units if unit.source_text.strip())
        permitted = {
            (
                units[start].source_start,
                units[start + width - 1].source_end,
                tuple(unit.unit_ref for unit in units[start : start + width]),
            )
            for start in range(len(units))
            for width in range(1, min(8, len(units) - start) + 1)
        }
        if designation_set.bindings:
            nonempty += 1
        else:
            empty += 1
            assert case.source_disposition.value in {
                "explicit_gap",
                "verification_rejection",
            }
        for binding in designation_set.bindings:
            assert (binding.source_start, binding.source_end, binding.unit_refs) in permitted
            assert case.surface[binding.source_start : binding.source_end] == binding.source_text
            fact = authority.designations.resolve_fact(binding.designation_fact_ref)
            assert fact is not None
            assert fact.target_ref == binding.target_ref
            assert fact in authority.designations.facts_for_surface(
                binding.source_text.strip(), case.language
            )
    assert (nonempty, empty) == (327, 61)


def test_designation_overlap_and_multi_unit_counts_are_derived_exactly() -> None:
    cache = _cache()
    intersecting_cases = 0
    undirected_pairs = 0
    multi_unit_cases = 0
    for designation_set in cache.designation_sets_by_case.values():
        geometries = {
            (row.source_start, row.source_end)
            for row in designation_set.bindings
        }
        pairs = {
            tuple(sorted((left, right)))
            for left in geometries
            for right in geometries
            if left != right and max(left[0], right[0]) < min(left[1], right[1])
        }
        if pairs:
            intersecting_cases += 1
            undirected_pairs += len(pairs)
        if any(len(row.unit_refs) > 1 for row in designation_set.bindings):
            multi_unit_cases += 1
    assert (intersecting_cases, undirected_pairs, multi_unit_cases) == (12, 13, 21)


def test_designation_authoring_has_no_structural_table_or_ref_name_fallback() -> None:
    source = inspect.getsource(build_source_authoring_cache)
    assert "_PROPOSALS" not in source
    assert "build_r4_1_review_worksheets" not in source
    authority, _, _ = _source_inputs()
    for designation_set in _cache().designation_sets_by_case.values():
        for row in designation_set.bindings:
            fact = authority.designations.resolve_fact(row.designation_fact_ref)
            assert fact is not None
            assert row.target_ref == fact.target_ref


def test_source_authoring_cache_is_deterministic_and_linearly_bounded() -> None:
    authority, cases, form_pack = _source_inputs()
    right = build_source_authoring_cache(
        cases=tuple(cases),
        authority=authority,
        form_pack=form_pack,
        config=RuntimeConfig.release(),
    )
    left = _cache()
    assert right == left
    unit_count = sum(
        len(tuple(unit for unit in lattice.units if unit.source_text.strip()))
        for lattice in left.form_lattices_by_case.values()
    )
    assert left.operation_count <= 4 * len(left.cases) + 8 * unit_count
