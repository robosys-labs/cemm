"""Canonical, fail-closed structured-semantic CLI.

The input is text, but the only admitted output today is a lossless semantic
document, not fabricated conversational prose.  The --root authority bundle
is explicit so an installed CLI cannot silently use stale authority.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .foundation import load_foundation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute one authenticated CEMM semantic foundation turn"
    )
    parser.add_argument("--root", type=Path, required=True,
                        help="Path to the canonical hybrid_mvp authority bundle")
    parser.add_argument("--store", type=Path, required=True,
                        help="SQLite store for session/effect replay")
    parser.add_argument("--session", default="session:foundation-cli")
    parser.add_argument("--text", required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve(strict=True)
    if not (root / "data" / "authority" / "manifest.json").is_file():
        parser.error("--root must contain data/authority/manifest.json")
    runtime = load_foundation(root, store_path=args.store)
    try:
        result = runtime.process(args.session, args.text)
        if not result.verify():
            raise RuntimeError("semantic-output verification failed")
        print(result.semantic_surface)
        return 0
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
