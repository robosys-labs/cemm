#!/usr/bin/env python3
"""End-to-end smoke for the final CEMM v1 authority and Stage 0–22 runtime."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cemm.runtime import MODE_READ_ONLY, Runtime
from cemm.store import Store


def run(repo: Path) -> dict:
    base = repo / "cemm/data/base.json"
    pack = repo / "cemm/language_packs/en.json"
    pack_data = json.loads(pack.read_text(encoding="utf-8"))
    constants = pack_data.get("constant_sources", {})
    for example in pack_data.get("structured_examples", ()):
        target = example.get("target", {})
        for application in target.get("apps", ()):
            bindings = application.get("bindings", {})
            if application.get("operator") == "op:type":
                tags = {
                    token.split("<", 1)[0].lstrip("@"): token.split("<", 1)[1].rstrip(">")
                    for token in str(example.get("input", "")).split()
                    if token.startswith("@A") and "<" in token and token.endswith(">")
                }
                if tags.get(str(bindings.get("role:instance"))) == "concept" and tags.get(str(bindings.get("role:class"))) == "concept":
                    raise RuntimeError(f"generic concept-as-instance supervision remains: {example.get('example_ref')}")
            for source in bindings.values():
                if isinstance(source, str) and source.startswith("CONST") and source not in constants:
                    raise RuntimeError(f"unresolved constant source {source}")

    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / "smoke.sqlite")
        try:
            store.import_data(base)
            runtime = Runtime(store, pack)
            revisions_before = store.revisions()
            result = runtime.process("How are you?", mode=MODE_READ_ONLY)
            stages = [item["stage"] for item in result["stage_trace"]["records"]]
            if stages != list(range(23)):
                raise RuntimeError(f"incomplete stage trace: {stages}")
            if result.get("response_csir", {}).get("action") != "report_capability":
                raise RuntimeError(f"self query did not target capability: {result.get('response_csir')}")
            if not result.get("response"):
                raise RuntimeError("self capability response was empty")
            proof = result.get("realization_proof") or {}
            if not proof.get("verified"):
                raise RuntimeError(f"self capability realization was not verified: {proof}")
            if store.revisions() != revisions_before:
                raise RuntimeError(
                    f"read-only smoke mutated revisions: before={revisions_before} after={store.revisions()}"
                )
            return {
                "status": result.get("status"),
                "response": result.get("response"),
                "response_action": result.get("response_csir", {}).get("action"),
                "stage_count": len(stages),
                "verified": True,
                "pack_hash": pack_data.get("pack_hash"),
            }
        finally:
            store.db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(run(args.repo.resolve()), ensure_ascii=False, indent=2))
