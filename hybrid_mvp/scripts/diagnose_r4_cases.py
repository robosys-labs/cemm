#!/usr/bin/env python3
"""Run the reviewed R4 corpus through the public runtime and classify mismatches."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.r4_contracts import ExpectedCycleContractCompiler
from cemm_authoritative_hybrid.r4_episodes import (
    AuthenticEpisodeBuilder,
    PublicRuntimeEpisodeOwner,
)
from cemm_authoritative_hybrid.r4_expansion import CaseExpander, ExpandedCase
from cemm_authoritative_hybrid.r4_pipeline import load_reviewed_scenarios


_OWNER_ORDER = (
    "expression",
    "situation",
    "decision",
    "effect",
    "response",
    "gap",
    "environment",
)
_MISMATCH_PREFIX = "comparison:"
_MAX_EXAMPLES = 8


def canonical_report_bytes(report: Mapping[str, object]) -> bytes:
    """Encode a diagnostic report with one deterministic canonical wire shape."""

    if not isinstance(report, Mapping):
        raise TypeError("report must be a mapping")
    return (
        json.dumps(
            dict(report),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _expanded_cases(project_root: Path) -> tuple[ExpandedCase, ...]:
    authority = AuthorityLinker().link_path(
        project_root / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    revision_pin = RevisionPin(
        authority.generation,
        0,
        0,
        0,
        0,
        model_identity,
    )
    compiler = ExpectedCycleContractCompiler(
        authority,
        abi_registry_ref="abi:r4-case-diagnostic",
    )
    expander = CaseExpander(compiler)
    cases = tuple(
        case
        for scenario in load_reviewed_scenarios(
            project_root / "data" / "scenarios" / "use_cases.jsonl"
        )
        for case in expander.expand(
            scenario,
            revision_pin=revision_pin,
            environments=scenario.metadata.get("environments", ({},)),
        )
    )
    return tuple(
        sorted(
            cases,
            key=lambda row: (
                row.trajectory_ref,
                row.turn_index,
                row.surface_index,
                row.environment_index,
                row.case_ref,
            ),
        )
    )


def _example(case: ExpandedCase) -> dict[str, object]:
    return {
        "case_ref": case.case_ref,
        "scenario_ref": case.scenario_ref,
        "trajectory_ref": case.trajectory_ref,
        "turn_index": case.turn_index,
    }


def diagnose_cases(
    project_root: Path,
    *,
    store_root: Path,
    environment_factory: Callable[..., Mapping[str, object]] | None = None,
    source_revision: str | None = None,
) -> dict[str, object]:
    """Execute all reviewed cases and report earliest-owner mismatch families."""

    root = project_root.resolve()
    stores = store_root.resolve()
    stores.mkdir(parents=True, exist_ok=True)
    cases = _expanded_cases(root)
    runtimes: list[Any] = []

    def runtime_factory(_case: ExpandedCase) -> Any:
        store_name = f"runtime-{len(runtimes):03d}"
        runtime = load_runtime(
            root,
            profile="development",
            store_path=stores / store_name,
        )
        runtimes.append(runtime)
        return runtime

    close_environment: Callable[[], object] | None = None
    if environment_factory is None:
        if source_revision is not None:
            raise ValueError("source_revision requires an environment factory")
        owner = PublicRuntimeEpisodeOwner(runtime_factory)
    else:
        if type(source_revision) is not str:
            raise ValueError("source_revision is required with an environment factory")
        environment = environment_factory(
            root,
            stores,
            source_revision=source_revision,
        )
        if not isinstance(environment, Mapping):
            raise TypeError("environment factory must return a mapping")
        supplied_factory = environment.get("runtime_factory")
        if not callable(supplied_factory):
            raise TypeError("environment requires a callable runtime_factory")
        owner = PublicRuntimeEpisodeOwner(
            supplied_factory,
            restart_executor=environment.get("restart_executor"),
        )
        candidate_close = environment.get("close")
        if candidate_close is not None and not callable(candidate_close):
            raise TypeError("environment close owner must be callable")
        close_environment = candidate_close
    builder = AuthenticEpisodeBuilder(owner)
    counts = Counter({"passed": 0, "failed": 0, "errors": 0})
    mismatch_counts: Counter[str] = Counter()
    earliest_owner_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    examples: defaultdict[str, list[dict[str, object]]] = defaultdict(list)

    try:
        for case in cases:
            try:
                comparison = builder.build(case).comparison
            except (RuntimeError, TypeError, ValueError) as exc:
                counts["errors"] += 1
                error_code = f"executor:{type(exc).__name__}:{exc}"
                error_counts[error_code] += 1
                earliest_owner_counts["executor"] += 1
                if len(examples[error_code]) < _MAX_EXAMPLES:
                    examples[error_code].append(_example(case))
                continue

            if comparison.passed:
                counts["passed"] += 1
                continue

            counts["failed"] += 1
            owners: list[str] = []
            for code in comparison.mismatch_codes:
                if not code.startswith(_MISMATCH_PREFIX):
                    raise ValueError(f"unknown comparison mismatch code: {code}")
                owner = code.removeprefix(_MISMATCH_PREFIX)
                if owner not in _OWNER_ORDER:
                    raise ValueError(f"unknown comparison mismatch owner: {owner}")
                owners.append(owner)
                mismatch_counts[owner] += 1
                if len(examples[owner]) < _MAX_EXAMPLES:
                    examples[owner].append(_example(case))
            earliest = next(owner for owner in _OWNER_ORDER if owner in owners)
            earliest_owner_counts[earliest] += 1
    finally:
        for runtime in reversed(runtimes):
            runtime.stores.close()
        if close_environment is not None:
            close_environment()

    return {
        "schema": "cemm-r4-case-diagnostic-v1",
        "case_count": len(cases),
        "counts": dict(sorted(counts.items())),
        "mismatch_counts": dict(sorted(mismatch_counts.items())),
        "earliest_owner_counts": dict(sorted(earliest_owner_counts.items())),
        "error_counts": dict(sorted(error_counts.items())),
        "examples": {
            key: rows
            for key, rows in sorted(examples.items())
        },
    }


def _load_environment_factory(locator: str):
    if type(locator) is not str or locator.count(":") != 1:
        raise ValueError("environment must use module:function syntax")
    module_name, owner_name = locator.split(":", 1)
    if not module_name or not owner_name:
        raise ValueError("environment must use module:function syntax")
    module = importlib.import_module(module_name)
    owner = getattr(module, owner_name, None)
    if not callable(owner):
        raise TypeError("environment locator must name a callable")
    return owner


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment")
    parser.add_argument("--source-revision")
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.environment is not None and args.source_revision is None:
        parser.error("--source-revision is required with --environment")
    if args.environment is None and args.source_revision is not None:
        parser.error("--source-revision requires --environment")

    environment_factory = (
        None
        if args.environment is None
        else _load_environment_factory(args.environment)
    )
    report = diagnose_cases(
        ROOT,
        store_root=args.store_root,
        environment_factory=environment_factory,
        source_revision=args.source_revision,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_report_bytes(report))
    print(canonical_report_bytes(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
