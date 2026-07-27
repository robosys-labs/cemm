#!/usr/bin/env python3
"""Parse all delivered runtime/test/tool Python without creating bytecode."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    paths = []
    for root_name in ("cemm", "tests", "tools"):
        root = repo / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*.py")
                if "__pycache__" not in path.parts
            )
    issues = []
    for path in sorted(paths):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            issues.append(f"{path.relative_to(repo)}: {exc}")
    if issues:
        raise SystemExit("PYTHON SYNTAX VALIDATION FAILED:\n" + "\n".join(issues))
    print(f"PYTHON SYNTAX VALIDATION PASSED: {len(paths)} files")


if __name__ == "__main__":
    main()
