#!/usr/bin/env python3
"""Capture the Phase-0 CEMM v3.5.1 structural/runtime baseline.

This is intentionally an observational harness. It does not assert that the current
conversation behavior is correct; it records exactly what the current runtime does,
including Stage-0..22 traces, frontiers, errors, latency, store revision movement,
and whether expensive release/boot verification leaked into normal turns.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from typing import Any

import cemm.v350.cutover as cutover
from cemm import Runtime


BASELINE_ORIGIN_COMMIT = "41fc70ab35d72b3d167fef9fb5c16ce3f8c2ecd6"

CASES = (
    ("hello", ("hello",)),
    ("hii", ("hii",)),
    ("how_are_you", ("how are you?",)),
    ("name_memory", ("my name is Chibu", "what's my name?")),
    ("preference_memory", ("I like mangoes", "what do I like?")),
    ("capability", ("what can you do?",)),
    ("why_followup", ("hello", "why?")),
    ("for_what_followup", ("hello", "for what?")),
    ("unknown_word", ("florp",)),
    (
        "correction",
        (
            "my name is Chibu",
            "no, my name is Chibueze",
            "what's my name?",
        ),
    ),
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


@contextmanager
def _instrument_verification():
    counters = {
        "sha256_calls": 0,
        "boot_pin_scans": 0,
        "full_authority_verifications": 0,
    }
    original_sha = cutover._sha256
    original_boot = cutover._boot_pins
    original_require = cutover.RuntimeAuthorityGuard.require_service_authority

    def counted_sha(*args, **kwargs):
        counters["sha256_calls"] += 1
        return original_sha(*args, **kwargs)

    def counted_boot(*args, **kwargs):
        counters["boot_pin_scans"] += 1
        return original_boot(*args, **kwargs)

    def counted_require(self, *args, **kwargs):
        counters["full_authority_verifications"] += 1
        return original_require(self, *args, **kwargs)

    cutover._sha256 = counted_sha
    cutover._boot_pins = counted_boot
    cutover.RuntimeAuthorityGuard.require_service_authority = counted_require
    try:
        yield counters
    finally:
        cutover._sha256 = original_sha
        cutover._boot_pins = original_boot
        cutover.RuntimeAuthorityGuard.require_service_authority = original_require


def _delta(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {key: after[key] - before[key] for key in before}


def capture() -> dict[str, Any]:
    with _instrument_verification() as counters:
        before_startup = dict(counters)
        runtime = Runtime()
        startup_metrics = _delta(dict(counters), before_startup)
        try:
            cases = []
            all_latencies = []
            for case_ref, turns in CASES:
                turn_results = []
                context_id = f"baseline:{case_ref}"
                for index, text in enumerate(turns):
                    before = dict(counters)
                    started = time.perf_counter()
                    result = runtime.run_text_result(text, context_id=context_id)
                    elapsed_ms = (time.perf_counter() - started) * 1000.0
                    all_latencies.append(elapsed_ms)
                    verification_delta = _delta(dict(counters), before)
                    finalization = result.artifacts.get("finalization_summary")
                    turn_results.append(
                        {
                            "turn_index": index,
                            "input": text,
                            "output_text": result.output_text,
                            "elapsed_ms": elapsed_ms,
                            "trace": _jsonable(result.trace),
                            "frontier_refs": list(result.frontier_refs),
                            "errors": list(result.errors),
                            "committed_patch_refs": list(
                                result.committed_patch_refs
                            ),
                            "finalization_summary": _jsonable(finalization),
                            "verification_hot_path": verification_delta,
                        }
                    )
                cases.append({"case_ref": case_ref, "turns": turn_results})

            return {
                "schema_version": 1,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "baseline_origin_commit": BASELINE_ORIGIN_COMMIT,
                "runtime_version": runtime.VERSION,
                "runtime_epoch": _jsonable(
                    getattr(runtime, "runtime_epoch", None)
                ),
                "runtime_attestation": _jsonable(
                    getattr(runtime, "runtime_attestation", None)
                ),
                "startup_verification_metrics": startup_metrics,
                "hot_path_verification_totals": {
                    key: counters[key] - startup_metrics[key]
                    for key in counters
                },
                "latency_ms": {
                    "count": len(all_latencies),
                    "min": min(all_latencies) if all_latencies else None,
                    "median": (
                        statistics.median(all_latencies)
                        if all_latencies
                        else None
                    ),
                    "max": max(all_latencies) if all_latencies else None,
                },
                "cases": cases,
            }
        finally:
            runtime.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="docs/baselines/v351_phase0_trace_corpus.json",
    )
    parser.add_argument(
        "--strict-hot-path",
        action="store_true",
        help="Fail unless normal turns perform zero release hashes/boot scans/full guard verification.",
    )
    args = parser.parse_args()

    payload = capture()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if args.strict_hot_path:
        totals = payload["hot_path_verification_totals"]
        if any(totals.values()):
            raise SystemExit(
                "Phase-1 hot-path verification gate failed: "
                + json.dumps(totals, sort_keys=True)
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
