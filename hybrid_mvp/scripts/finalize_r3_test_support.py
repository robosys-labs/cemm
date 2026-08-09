#!/usr/bin/env python3
"""Remove predecessor-only pytest bootstrap support after the R3 hard cut."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFTEST = ROOT / "tests" / "conftest.py"


def main() -> int:
    text = CONFTEST.read_text(encoding="utf-8")
    start_marker = "def _load_legacy_test_support(module_name: str) -> None:\n"
    end_marker = 'AUTHORITY_GENERATION = "authority:generation-1"\n'
    if start_marker in text:
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        text = text[:start] + text[end:]
    text = text.replace("import importlib.util\n", "")
    text = text.replace("import sys\n", "")
    if "_load_legacy_test_support" in text:
        raise RuntimeError("legacy pytest support bootstrap remains after R3 hard cut")
    CONFTEST.write_text(text, encoding="utf-8", newline="\n")
    print("removed predecessor-only pytest support bootstrap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
