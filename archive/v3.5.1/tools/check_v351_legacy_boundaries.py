#!/usr/bin/env python3
"""Fail canonical builds when legacy v347/UOL runtime authority leaks back in."""
from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = (
    ROOT / "cemm/app",
    ROOT / "cemm/v350/runtime.py",
    ROOT / "cemm/v350/public_runtime.py",
    ROOT / "cemm/v350/cutover.py",
    ROOT / "cemm/v350/runtime_v351.py",
    ROOT / "cemm/v350/service_loader.py",
    ROOT / "cemm/v350/runtime_mechanics.py",
    ROOT / "cemm/v350/orchestration.py",
    ROOT / "cemm/v350/stage_adapters.py",
    ROOT / "cemm/v350/runtime_graph.py",
    ROOT / "cemm/v350/stage_contracts.py",
    ROOT / "cemm/v350/runtime_abi.py",
    ROOT / "cemm/v350/semantic_capability.py",
    ROOT / "cemm/v350/effects",
    ROOT / "cemm/v350/realization/proof.py",
    ROOT / "cemm/v350/realization/policy.py",
)
FORBIDDEN_IMPORT_FRAGMENTS = (
    "cemm.v347", ".v347", "legacy_runtime_v350", "runtime_hardening",
    "cemm.v350.runtime_services", "cemm.v350.activation_services",
    "cemm.v350.uol", ".uol", "cemm.v350.composition", ".composition",
)
FORBIDDEN_STAGE_TOKENS = (
    "BUILD_UOL_FACTOR_GRAPH", "SOLVE_MEANING_HYPOTHESES",
    "SELECT_MEANING_BUNDLE", "BUILD_RESPONSE_UOL",
)
EXPECTED_STAGE_NAMES = {
    "ORIENT_AND_PIN_SEMANTIC_BRAIN", "OBSERVE_MULTIMODAL_EVIDENCE",
    "ENCODE_FORM_AND_SENSOR_EVIDENCE", "ACTIVATE_AND_GROUND_REFERENTS",
    "PROJECT_ENTITLED_STATE_SPACES", "COMPILE_CANDIDATES_TO_CSIR",
    "RUN_RECURRENT_MEANING_DYNAMICS", "STABILIZE_SEMANTIC_ATTRACTORS",
    "BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY_STRUCTURES",
    "PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF",
    "QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL",
    "CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING",
    "SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS",
    "COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS",
    "PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE",
    "DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS",
    "PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE", "ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR",
    "CONSTRUCT_RESPONSE_CSIR", "REALIZE_TARGET_LANGUAGE_OR_MODALITY",
    "VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION",
    "COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND",
    "CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE",
}


def files_under(path: Path):
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(path.rglob("*.py"))


def import_names(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level + (node.module or "")
            yield prefix


def main() -> int:
    failures = []
    for root in CANONICAL:
        for path in files_under(root):
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            for name in import_names(tree):
                if any(fragment in name for fragment in FORBIDDEN_IMPORT_FRAGMENTS):
                    failures.append(f"legacy import:{path.relative_to(ROOT)}:{name}")
            for token in FORBIDDEN_STAGE_TOKENS:
                if token in text:
                    failures.append(f"legacy stage token:{path.relative_to(ROOT)}:{token}")

    # Latest v3.5.1 baseline removes the executable/data v347 tree entirely. Any
    # reappearance in the canonical source tree is a regression; offline migration
    # must use explicit archived/external fixtures rather than importable runtime code.
    for legacy_path in (ROOT / "cemm/v347", ROOT / "cemm/data/v347"):
        if legacy_path.exists():
            failures.append(f"removed v347 legacy tree reappeared:{legacy_path.relative_to(ROOT)}")

    for obsolete in ("PRE_3_5_1_STABILIZATION_PLAN.md", "V3_5_1_IMPLEMENTATION_PLAN.md"):
        if (ROOT / obsolete).exists():
            failures.append(f"superseded root roadmap still active:{obsolete}")

    # Tests are not silently skipped. Any canonical test still depending on v347 or old
    # Stage ABI is reported so it can be rewritten or explicitly moved to migration tests.
    for path in sorted((ROOT / "tests").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        imported_names = tuple(import_names(tree))
        if any(name == "cemm.v347" or name.startswith("cemm.v347.") for name in imported_names):
            failures.append(f"stale canonical test imports v347:{path.relative_to(ROOT)}")
        if any(
            name == "cemm.v350.runtime_services"
            or name.startswith("cemm.v350.runtime_services.")
            or name == "cemm.v350.runtime_hardening"
            or name.startswith("cemm.v350.runtime_hardening.")
            for name in imported_names
        ):
            failures.append(f"stale canonical test imports removed runtime authority:{path.relative_to(ROOT)}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "cemm.v350.orchestration":
                imported = {alias.name for alias in node.names}
                if "CycleState" in imported:
                    failures.append(
                        f"stale canonical test imports removed CycleState ABI:{path.relative_to(ROOT)}"
                    )
            if isinstance(node, ast.ImportFrom) and node.module in {"cemm.v350.runtime", "cemm.v350.runtime_hardening"}:
                imported = {alias.name for alias in node.names}
                stale = imported.intersection({"CanonicalRuntimeCoordinator", "HardenedRuntimeCoordinator"})
                if stale:
                    failures.append(
                        f"stale canonical test imports removed runtime coordinator:{path.relative_to(ROOT)}:{sorted(stale)}"
                    )
        for stale_token in (
            'VERSION = "3.5.0"', 'release_version: str = "3.5.0"',
            'stage0-22-v350-final', 'uol-v350',
        ):
            if stale_token in text:
                failures.append(
                    f"stale canonical test asserts obsolete v3.5.0/UOL authority:{path.relative_to(ROOT)}:{stale_token}"
                )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "CoreStage"
                and node.attr not in EXPECTED_STAGE_NAMES
            ):
                failures.append(
                    f"stale canonical test asserts old/unknown Stage ABI:{path.relative_to(ROOT)}:{node.attr}"
                )
        # Do not reject tests merely for mentioning old tokens in negative-regression
        # assertions. Actual stale CoreStage attribute usage is detected structurally
        # above; migration-only string fixtures may also legitimately mention history.

    if failures:
        print("\n".join(sorted(set(failures))))
        return 1
    print("v3.5.1 legacy-boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
