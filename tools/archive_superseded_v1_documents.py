#!/usr/bin/env python3
"""Archive superseded root repair plans without deleting implementation history."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

CANDIDATES = (
    "v1-fixes.md",
    "PHASES_5_9_IMPLEMENTATION.md",
    "PHASES_10_16_IMPLEMENTATION.md",
    "cemm-v1-final-validation-report.md",
)

BANNER = """> **ARCHIVED — historical evidence only.**\n> This file is not active implementation authority. See root `AGENTS.md`,\n> `ARCHITECTURE.md`, `runtime-core-loop.md`, `CURRENT_RUNTIME_WEAKNESSES.md`,\n> and `V1_ACCEPTANCE.md`.\n\n"""


def archive(repo: Path):
    destination = repo / "docs/archive/v1-repair-history"
    destination.mkdir(parents=True, exist_ok=True)
    moved = []
    for name in CANDIDATES:
        source = repo / name
        if not source.exists():
            continue
        target = destination / name
        content = source.read_text(encoding="utf-8")
        if not content.startswith("> **ARCHIVED"):
            content = BANNER + content
        target.write_text(content, encoding="utf-8")
        source.unlink()
        moved.append({"from": name, "to": str(target.relative_to(repo))})
    manifest = destination / "archive-manifest.json"
    prior = []
    if manifest.exists():
        try:
            prior = json.loads(manifest.read_text(encoding="utf-8")).get("moved", [])
        except Exception:
            prior = []
    combined = {item["from"]: item for item in prior + moved}
    manifest.write_text(
        json.dumps({"moved": [combined[key] for key in sorted(combined)]}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"moved": moved, "manifest": str(manifest.relative_to(repo))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(archive(args.repo.resolve()), indent=2))
