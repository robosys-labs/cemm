#!/usr/bin/env python3
"""Run a real public CEMM v3.5.1 web-demo/runtime smoke corpus and capture Stage 0-22 traces."""
from __future__ import annotations
import argparse, json
from pathlib import Path

from cemm.app.runtime import Runtime
from cemm.v350.cutover import RuntimeAuthorityError

CORPUS = (
    "hello",
    "how are you?",
    "what is my name?",
    "my name is Chibueze",
    "what is my name?",
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--database", default=":memory:")
    p.add_argument("--manifest", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    kwargs = {"database_path": a.database}
    if a.manifest is not None:
        kwargs["authority_manifest_path"] = a.manifest
    report = {"status": "fail", "turns": [], "activation_error": ""}
    runtime = None
    try:
        runtime = Runtime(**kwargs)
        context = "activation-smoke"
        for text in CORPUS:
            result = runtime.run_text(text, context_id=context, language_hint="en", target_language="en")
            stages = [dict(item) for item in result.stage_trace]
            report["turns"].append({
                "input": text,
                "output": result.output_text,
                "frontiers": list(result.frontier_refs),
                "errors": list(result.errors),
                "stage_trace": stages,
            })
        report["status"] = "pass" if all(not item["errors"] for item in report["turns"]) else "fail"
    except RuntimeAuthorityError as exc:
        report["activation_error"] = str(exc)
    finally:
        if runtime is not None:
            runtime.close()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] == "pass" else 2

if __name__ == "__main__":
    raise SystemExit(main())
