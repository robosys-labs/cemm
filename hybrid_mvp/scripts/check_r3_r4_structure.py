#!/usr/bin/env python3
"""Fail-closed structural checks for the R3/R4 owners and R5 data hard cut."""
from __future__ import annotations

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "cemm_authoritative_hybrid"


def _text(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _assert_r5_partition_hard_cut() -> None:
    retired_paths = (
        SRC / "partitions.py",
        ROOT / "scripts" / "partition_episodes.py",
        ROOT / "scripts" / "calibrate_models.py",
        ROOT / "scripts" / "evaluate_cemm.py",
        ROOT / "configs" / "partitions.json",
        ROOT / "data" / "partitions",
        ROOT / "_test_eval.py",
        ROOT / "_test_eval2.py",
        ROOT / "_test_eval3.py",
        ROOT / "_test_train.py",
    )
    survivors = tuple(
        path.relative_to(ROOT).as_posix()
        for path in retired_paths
        if os.path.lexists(path)
    )
    if survivors:
        raise ValueError(f"retired R5 partition authority remains: {survivors}")

    legacy_data_path = "/".join(("data", "partitions"))
    legacy_module = ".".join(("cemm_authoritative_hybrid", "partitions"))
    legacy_imports = (
        legacy_module,
        "from ." + "partitions",
        "from cemm_authoritative_hybrid import " + "partitions",
    )
    allowed_data_mentions = {
        "src/cemm_authoritative_hybrid/r4_partition_access.py": 2,
    }
    offenders: list[str] = []
    checker = Path(__file__).resolve()
    text_suffixes = frozenset(
        {".py", ".json", ".toml", ".yaml", ".yml", ".sh", ".ps1"}
    )
    for base in (SRC, ROOT / "configs", ROOT / "scripts"):
        for path in sorted(base.rglob("*")):
            if (
                not path.is_file()
                or path.resolve() == checker
                or path.suffix.lower() not in text_suffixes
            ):
                continue
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            data_mentions = text.count(legacy_data_path)
            expected_mentions = allowed_data_mentions.get(relative, 0)
            if data_mentions != expected_mentions:
                offenders.append(
                    f"{relative}:{legacy_data_path}:"
                    f"expected={expected_mentions}:actual={data_mentions}"
                )
            for token in legacy_imports:
                if token in text:
                    offenders.append(f"{relative}:{token}")
    if offenders:
        raise ValueError(f"active legacy partition references remain: {offenders}")


def main() -> int:
    downstream = (
        "decision.py", "r3_cognition.py", "r3_kernel.py", "r3_effects.py",
        "r3_learning.py", "r3_response.py",
    )
    forbidden = ("program.graph", ".source_text", "FormResolver(", "Grounder(")
    offenders: list[str] = []
    for name in downstream:
        text = _text(name)
        for token in forbidden:
            if token in text:
                offenders.append(f"{name}:{token}")
    if offenders:
        raise ValueError(f"post-VERIFY semantic bypasses: {offenders}")

    runtime = _text("runtime.py")
    if '"r3": R3Owner' not in runtime or "contract:r5:realize_surface" not in runtime:
        raise ValueError("public runtime lacks the exact R3 owner/R5 boundary")
    cycle = _text("r3_cycle.py")
    if "CYCLE_RESULT_ABI_VERSION = 3" not in cycle:
        raise ValueError("R3 cycle owner does not declare ABI 3")
    if "realization_receipt" not in cycle or "contract:r5:realize_surface" not in cycle:
        raise ValueError("R3 cycle owner lacks the exact R5 boundary")
    expected = _text("r4_contracts.py")
    for token in ("BootstrapProposer", ".propose(", "HybridRuntime"):
        if token in expected:
            raise ValueError(f"expected-contract compiler depends on {token}")
    retired_paths = (
        SRC / "r4_review.py",
        ROOT / "scripts" / "prepare_r4_review_request.py",
        ROOT / "scripts" / "verify_r4_review_manifest.py",
        ROOT / "schemas" / "corpus_review_manifest.schema.json",
        ROOT / "data" / "review" / "R4_REVIEW_MANIFEST.template.json",
    )
    if any(path.exists() for path in retired_paths):
        raise ValueError("retired R4 external-review file remains active")
    retired_tokens = (
        "CorpusReviewManifest", "ApprovedR4Build", "CEMM_R4_REVIEW",
        "R4_REVIEW_MANIFEST", "external_review_required",
    )
    for relative in ("r4_pipeline.py", "r4_admission.py"):
        for token in retired_tokens:
            if token in _text(relative):
                raise ValueError(f"retired R4 external-review token remains: {relative}:{token}")
    validation = (ROOT / "scripts" / "validation_gate.py").read_text(encoding="utf-8")
    for token in retired_tokens:
        if token in validation:
            raise ValueError(f"retired R4 external-review token remains in validation gate: {token}")
    _assert_r5_partition_hard_cut()
    for path in SRC.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print("R3/R4/R5 structural hard-cut checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
