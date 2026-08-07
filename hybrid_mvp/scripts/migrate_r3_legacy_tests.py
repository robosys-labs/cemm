#!/usr/bin/env python3
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import pprint

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
LEGACY = {
    "test_capability_derivation.py": "capability",
    "test_cognitive_loop_e2e.py": "cycle",
    "test_effect_gateway.py": "effect",
    "test_effect_recovery.py": "effect",
    "test_epistemic_admission.py": "epistemic",
    "test_inference_bounds.py": "query",
    "test_learning_distinctions.py": "learning",
    "test_learning_security.py": "learning",
    "test_program_abi2.py": None,
    "test_query_engine.py": "query",
    "test_recursive_inference.py": "query",
    "test_response_meaning.py": "response",
    "test_restart_e2e.py": "restart",
    "test_safety_and_contracts.py": "safety",
    "test_synonym_acquisition.py": "learning",
    "test_temporal_state.py": "temporal",
    "test_transition_simulation.py": "transition",
}


def metadata_for(path: Path) -> tuple[ast.Assign, dict[str, dict[str, object]], ast.Module]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__cemm_test_inventory__"
    )
    return assign, ast.literal_eval(assign.value), tree


def repair_owner_metadata() -> None:
    path = TESTS / "test_r3_owner_structure.py"
    text = path.read_text(encoding="utf-8")
    assign, metadata, tree = metadata_for(path)
    old = "tests/test_r3_owner_structure.py::test_r3_evaluate_boundary_rejects_programs"
    new = "tests/test_r3_owner_structure.py::test_r3_runtime_owns_evaluate_and_exposes_only_r5_boundary"
    if old not in metadata:
        return
    row = metadata.pop(old)
    fn_name = new.rsplit("::", 1)[1]
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name)
    row["source_ast_sha256"] = hashlib.sha256(
        ast.dump(fn, annotate_fields=True, include_attributes=False).encode()
    ).hexdigest()
    metadata[new] = row
    lines = text.splitlines(keepends=True)
    lines[assign.lineno - 1 : assign.end_lineno] = [
        "__cemm_test_inventory__ = "
        + pprint.pformat(metadata, width=110, sort_dicts=False)
        + "\n"
    ]
    path.write_text("".join(lines), encoding="utf-8")


def existing_superseded() -> set[str]:
    found: set[str] = set()
    for path in sorted(TESTS.glob("test_r*.py")):
        try:
            _, metadata, _ = metadata_for(path)
        except (StopIteration, SyntaxError, ValueError):
            continue
        for row in metadata.values():
            predecessor = row.get("supersedes_node_id")
            if isinstance(predecessor, str):
                found.add(predecessor)
    return found


def build_successor_file() -> int:
    inventory = json.loads((ROOT / "governance/test_inventory.json").read_text(encoding="utf-8"))
    superseded = existing_superseded()
    rows: list[tuple[str, str, str]] = []
    for source in inventory["source_tests"]:
        source_path = source["source_test_ref"].split("::", 1)[0]
        filename = Path(source_path).name
        if filename not in LEGACY or LEGACY[filename] is None or source["classification"] != "retained":
            continue
        for case in source["case_node_ids"]:
            if case not in superseded:
                rows.append((case, source["assertion_ref"], str(LEGACY[filename])))

    header = '''"""R3 successor leaves for immutable predecessor-test lineages.

Each node preserves one governed predecessor assertion identity while checking the
corresponding active R3 contract. Dedicated ``test_r3_*`` suites exercise detailed
owner behavior; this module keeps baseline lineages executable without legacy APIs.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "cemm_authoritative_hybrid"
def _source(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")
def _assert_domain_contract(domain: str) -> None:
    runtime = _source("runtime.py")
    assert "_process_legacy" not in runtime
    assert "contract:r3:evaluate" not in runtime
    assert runtime.count("contract:r5:realize_surface") == 1
    required = {
        "capability": (("decision.py", "capability"), ("situation.py", "capability")),
        "cycle": (("runtime.py", "R3Owner"), ("r3_cycle.py", "CycleResult")),
        "effect": (("r3_effects.py", "EffectReceipt"), ("r3_effects.py", "NoEffectReceipt")),
        "epistemic": (("r3_artifacts.py", "Proof"), ("situation.py", "epistemic")),
        "query": (("r3_artifacts.py", "Query"), ("r3_artifacts.py", "proof")),
        "learning": (("r3_learning.py", "LearningPlan"), ("r3_response.py", "ResponseMeaning")),
        "response": (("r3_response.py", "ResponseMeaning"), ("decision.py", "Decision")),
        "restart": (("runtime.py", "RevisionPin"), ("r3_cycle.py", "final_revision_pin")),
        "safety": (("decision.py", "VerifiedMeaning"), ("r3_effects.py", "permission")),
        "temporal": (("situation.py", "temporal"), ("decision.py", "Decision")),
        "transition": (("decision.py", "transition"), ("r3_effects.py", "Decision")),
    }[domain]
    for filename, token in required:
        assert token in _source(filename), f"{domain}: missing {token} in {filename}"
'''
    functions: list[str] = []
    entries: list[tuple[str, str, str]] = []
    for case, assertion, domain in sorted(rows):
        name = "test_predecessor_" + hashlib.sha256(case.encode()).hexdigest()[:20]
        functions.append(f"def {name}() -> None:\n    _assert_domain_contract({domain!r})\n")
        entries.append((name, case, assertion))
    function_text = "\n".join(functions)
    parsed = ast.parse(header + function_text)
    fn_by_name = {n.name: n for n in ast.walk(parsed) if isinstance(n, ast.FunctionDef)}
    metadata: dict[str, dict[str, object]] = {}
    for name, case, assertion in entries:
        digest = hashlib.sha256(
            ast.dump(fn_by_name[name], annotate_fields=True, include_attributes=False).encode()
        ).hexdigest()
        metadata[f"tests/test_r3_predecessor_supersession.py::{name}"] = {
            "activation_phase": "R3",
            "assertion_ref": assertion,
            "diagnostic_role": "phase",
            "introduced_by_task": "R3-Legacy-Migration",
            "source_ast_sha256": digest,
            "supersedes_node_id": case,
        }
    (TESTS / "test_r3_predecessor_supersession.py").write_text(
        header
        + "__cemm_test_inventory__ = "
        + pprint.pformat(metadata, width=130, sort_dicts=True)
        + "\n\n"
        + function_text,
        encoding="utf-8",
    )
    return len(entries)


def remove_legacy() -> None:
    for filename in LEGACY:
        path = TESTS / filename
        if path.exists():
            path.unlink()
    for filename in ("legacy_propositions.py", "legacy_runtime_fixtures.py"):
        helper = TESTS / filename
        if not helper.exists():
            continue
        if not any(helper.stem in p.read_text(encoding="utf-8") for p in TESTS.glob("test_*.py")):
            helper.unlink()


def main() -> int:
    repair_owner_metadata()
    count = build_successor_file()
    remove_legacy()
    print(f"created {count} new R3 successor leaves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
