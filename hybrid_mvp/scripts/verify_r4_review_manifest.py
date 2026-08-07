#!/usr/bin/env python3
"""Verify an R4 review manifest with an externally supplied verifier owner.

``--verifier`` names either an object implementing ``verify_signature`` or a
zero-argument factory/class returning such an object.  Plain boolean callback
functions are intentionally not accepted by the canonical verifier.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from cemm_authoritative_hybrid.r4_review import (
    CorpusReviewManifest,
    ReviewManifestVerifier,
)


def _load_verifier(spec: str):
    if spec.count(":") != 1:
        raise ValueError("verifier must use module:attribute syntax")
    module_name, attribute_name = spec.split(":", 1)
    candidate = getattr(importlib.import_module(module_name), attribute_name)
    if not hasattr(candidate, "verify_signature"):
        if not callable(candidate):
            raise TypeError("verifier attribute must be an owner or zero-argument factory")
        candidate = candidate()
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--verifier",
        required=True,
        help="module:attribute external verifier owner or zero-argument factory",
    )
    args = parser.parse_args()
    value = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest = CorpusReviewManifest.from_dict(value)
    ReviewManifestVerifier(_load_verifier(args.verifier)).verify(manifest)
    print(manifest.manifest_ref)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
