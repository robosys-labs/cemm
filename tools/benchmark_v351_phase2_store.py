#!/usr/bin/env python3
"""Phase-2 storage/concurrency benchmark and query-plan gate.

Run after applying the Phase 2-3 patch.  It measures scaling properties rather than
hardcoding machine-specific latency thresholds.  CI may layer environment-specific
budgets on the emitted JSON.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import statistics
import tempfile
import time

from cemm.v350.schema.model import semantic_fingerprint
from cemm.v350.storage import (
    EvidenceRecord,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
)


def evidence(index: int) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_ref=f"evidence:phase2-bench:{index}",
        source_ref="source:phase2-bench",
        confidence=1.0,
        lineage_ref=f"source-lineage:phase2-bench:{index}",
        context_ref="bench",
        permission_ref="internal",
        metadata={"index": index},
    )


def write_one(store: SemanticStore, index: int) -> float:
    item = evidence(index)
    with store.snapshot() as snapshot:
        patch = GraphPatch(
            patch_ref="patch:phase2-bench:"
            + semantic_fingerprint(
                "phase2-bench-patch",
                (index, snapshot.store_revision),
                20,
            ),
            context_ref="bench",
            scope_ref="bench:phase2",
            source_ref="source:phase2-bench",
            permission_ref="internal",
            operations=(
                PatchOperation(
                    operation_ref=f"op:phase2-bench:{index}",
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.EVIDENCE,
                    target_ref=item.evidence_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.EVIDENCE, item),
                ),
            ),
            expected_store_revision=snapshot.store_revision,
        )
    started = time.perf_counter()
    result = store.apply_patch(patch)
    elapsed = (time.perf_counter() - started) * 1000.0
    if not result.committed:
        raise RuntimeError(result.errors)
    return elapsed


def read_worker(store: SemanticStore, refs: tuple[str, ...], rounds: int) -> float:
    started = time.perf_counter()
    for _ in range(rounds):
        with store.snapshot() as snapshot:
            for ref in refs:
                found = store.resolve_any(ref, snapshot=snapshot)
                if not found:
                    raise AssertionError(f"missing benchmark ref:{ref}")
    return (time.perf_counter() - started) * 1000.0


def query_plan(database_path: Path) -> list[str]:
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            "EXPLAIN QUERY PLAN "
            "SELECT DISTINCT record_kind FROM record_index WHERE record_ref=?",
            ("evidence:phase2-bench:0",),
        ).fetchall()
        return [" | ".join(map(str, row)) for row in rows]
    finally:
        connection.close()


def run(scale: int, read_rounds: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="cemm-phase2-bench-") as directory:
        db_path = Path(directory) / "overlay.sqlite"
        store = SemanticStore(db_path)
        try:
            write_latencies = [write_one(store, index) for index in range(scale)]
            sample_refs = tuple(
                f"evidence:phase2-bench:{index}"
                for index in sorted(
                    {
                        0,
                        max(0, scale // 4),
                        max(0, scale // 2),
                        max(0, scale - 1),
                    }
                )
            )
            concurrency = {}
            for workers in (1, 4, 16, 64):
                started = time.perf_counter()
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [
                        pool.submit(read_worker, store, sample_refs, read_rounds)
                        for _ in range(workers)
                    ]
                    worker_ms = [future.result() for future in futures]
                wall_ms = (time.perf_counter() - started) * 1000.0
                concurrency[str(workers)] = {
                    "wall_ms": wall_ms,
                    "worker_median_ms": statistics.median(worker_ms),
                    "worker_max_ms": max(worker_ms),
                }

            plan = query_plan(db_path)
            if not any(
                "record_index_ref_idx" in line
                or "PRIMARY KEY" in line
                or "COVERING INDEX" in line
                for line in plan
            ):
                raise AssertionError(
                    "record-ref lookup query plan does not prove indexed lookup: "
                    + repr(plan)
                )

            generation = store.current_read_generation()
            return {
                "scale": scale,
                "write_ms": {
                    "median": statistics.median(write_latencies),
                    "p95_approx": sorted(write_latencies)[
                        min(len(write_latencies) - 1, int(len(write_latencies) * 0.95))
                    ],
                    "max": max(write_latencies),
                    "first_100_median": statistics.median(
                        write_latencies[: min(100, len(write_latencies))]
                    ),
                    "last_100_median": statistics.median(
                        write_latencies[-min(100, len(write_latencies)) :]
                    ),
                },
                "concurrency": concurrency,
                "query_plan": plan,
                "generation": {
                    "store_revision": generation.store_revision,
                    "authority_generation": generation.authority_generation,
                    "world_revision": generation.world_revision,
                    "audit_revision": generation.audit_revision,
                },
            }
        finally:
            store.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scales",
        default="1000,10000,100000",
        help="Comma-separated overlay record counts.",
    )
    parser.add_argument("--read-rounds", type=int, default=5)
    parser.add_argument(
        "--output",
        default="docs/baselines/v351_phase2_storage_benchmark.json",
    )
    args = parser.parse_args()

    results = [
        run(int(raw), args.read_rounds)
        for raw in args.scales.split(",")
        if raw.strip()
    ]

    # Structural asymptotic guard: median write latency near the end of a scale must
    # not explode relative to its first 100 writes. This is deliberately generous to
    # avoid machine noise while still catching accidental O(total-history) rescans.
    for item in results:
        first = max(item["write_ms"]["first_100_median"], 0.001)
        last = item["write_ms"]["last_100_median"]
        if last / first > 20.0:
            raise AssertionError(
                f"write scaling regression at scale={item['scale']}: "
                f"last/first median={last / first:.2f}"
            )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"schema_version": 1, "results": results}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
