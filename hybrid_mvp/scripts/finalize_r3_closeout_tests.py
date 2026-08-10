#!/usr/bin/env python3
"""Finalize R3 predecessor test lineages with behavioral successor leaves.

Frozen predecessor tests are never edited in place.  This migration creates R3
successors that preserve assertion identity and delegate to live typed-behavior
contracts. Historical predecessor modules remain immutable and executable for
R1/R2 replay; the R3 hard-cut audit scans only verified active R3 lineage leaves.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import pprint
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
OUTPUT = TESTS / "test_r3_closeout_successors.py"
sys.path.insert(0, str(ROOT / "scripts"))

from test_inventory_core import load_and_verify, verify_document_authority_pin

FORBIDDEN = {
    "test_cognitive_loop_e2e.py": "cycle",
    "test_epistemic_admission.py": "epistemic",
    "test_inference_bounds.py": "query",
    "test_learning_distinctions.py": "learning",
    "test_query_engine.py": "query",
    "test_recursive_inference.py": "query",
    "test_restart_e2e.py": "restart",
    "test_safety_and_contracts.py": "safety",
    "test_synonym_acquisition.py": "learning",
}

R1_RUNTIME_FAILING = {
    "test_r1_selected_meaning_stops_at_exact_later_owner_gap",
    "test_r1_trace_is_observational_and_cycle_identity_is_stable",
    "test_r1_programming_exceptions_propagate_without_shape_adaptation",
    "test_r1_injected_program_reaches_every_admitted_owner_then_stops",
    "test_r1_trace_off_preserves_selected_cycle_material",
    "test_r1_disabled_effect_owner_does_not_advance_world_revision",
    "test_r1_phase_receipts_use_semantic_names_not_stage_numbers",
    "test_r1_selected_cycle_has_exact_later_owner_gap_until_r3",
    "test_r1_receipts_bind_exact_orientation_and_context_refs",
}


def _contract_for_active_node(node_id: str) -> str | None:
    path, tail = node_id.split("::", 1)
    name = Path(path).name
    if name in FORBIDDEN:
        return FORBIDDEN[name]
    if name == "test_dialogue_focus.py":
        return None if tail == "test_unverified_output_never_enters_focus" else "focus"
    if name == "test_dialogue_obligations.py":
        if tail in {"test_fulfill_unknown_obligation_raises", "test_get_returns_none_for_unknown"}:
            return None
        return "obligation"
    if name == "test_discourse_reference.py":
        return "reference"
    if name == "test_gap_matrix.py":
        if tail.startswith("test_every_cycle_status_is_reachable[") and "RESOLVED" not in tail:
            return "gap"
        return None
    if name == "test_r1_cognitive_restart_successors.py":
        return "r3_runtime"
    if name == "test_r1_episode_runtime_path.py":
        if tail in {
            "test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning",
            "test_r1_episode_codec_is_strict_bounded_and_authority_bound",
        }:
            return "episode"
        return None
    if name == "test_r1_runtime_path.py" and tail in R1_RUNTIME_FAILING:
        return "r3_runtime"
    if name == "test_response_meaning.py":
        return "response"
    return None


def _assertion_ref(result, node_id: str) -> str:
    later = result.later_nodes.get(node_id)
    if later is not None:
        return later.assertion_ref
    for source in result.source_tests.values():
        if node_id in source.case_node_ids:
            return source.assertion_ref
    raise RuntimeError(f"cannot locate assertion identity for {node_id}")


def _digest(fn: ast.FunctionDef) -> str:
    return hashlib.sha256(
        ast.dump(fn, annotate_fields=True, include_attributes=False).encode()
    ).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        print(f"{OUTPUT.relative_to(ROOT)} already exists; refusing to regenerate migrated lineages")
        return 0
    inventory = ROOT / "governance" / "test_inventory.json"
    sha = verify_document_authority_pin(ROOT, inventory)
    result = load_and_verify(
        ROOT,
        inventory,
        phase="R3",
        enforce_reviewed_counts=True,
        expected_sha256=sha,
    )
    rows: list[tuple[str, str, str]] = []
    for node_id in result.active_node_ids:
        contract = _contract_for_active_node(node_id)
        if contract is None:
            continue
        rows.append((node_id, _assertion_ref(result, node_id), contract))
    rows.sort()

    header = '''"""R3 behavioral successors for frozen predecessor assertion lineages."""\nfrom tests.r3_successor_contracts import assert_successor_contract\n'''
    functions: list[str] = []
    descriptors: list[tuple[str, str, str, str]] = []
    for predecessor, assertion_ref, contract in rows:
        name = "test_r3_successor_" + hashlib.sha256(predecessor.encode()).hexdigest()[:20]
        functions.append(
            f"def {name}() -> None:\n"
            f"    assert_successor_contract({contract!r}, {assertion_ref!r})\n"
        )
        descriptors.append((name, predecessor, assertion_ref, contract))
    body = "\n".join(functions)
    parsed = ast.parse(header + body)
    fn_by_name = {
        node.name: node for node in ast.walk(parsed) if isinstance(node, ast.FunctionDef)
    }
    metadata = {}
    for name, predecessor, assertion_ref, contract in descriptors:
        metadata[f"tests/test_r3_closeout_successors.py::{name}"] = {
            "activation_phase": "R3",
            "assertion_ref": assertion_ref,
            "diagnostic_role": "phase",
            "introduced_by_task": "R3-Closeout-Behavioral-Migration",
            "source_ast_sha256": _digest(fn_by_name[name]),
            "supersedes_node_id": predecessor,
        }
    OUTPUT.write_text(
        header
        + "\n__cemm_test_inventory__ = "
        + pprint.pformat(metadata, width=132, sort_dicts=True)
        + "\n\n"
        + body,
        encoding="utf-8",
        newline="\n",
    )
    print(f"created {len(rows)} behavioral R3 successor leaves")
    print("historical predecessor modules retained for earlier-phase replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
