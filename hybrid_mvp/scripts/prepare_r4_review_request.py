#!/usr/bin/env python3
"""Create an unsigned external-review request for exact R4 build artifacts.

This command cannot approve or sign a corpus.  It calculates the immutable
material an independent reviewer must bind when issuing CorpusReviewManifest
ABI 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


def _sha(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required regular artifact is absent: {path}")
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _assertion_registry_sha(path: Path) -> str:
    kinds: dict[str, tuple[str, ...]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        assertions = value.get("semantic_assertions") if isinstance(value, dict) else None
        if type(assertions) is not list:
            raise TypeError(f"scenario line {number} has no assertion list")
        for assertion in assertions:
            if type(assertion) is not dict or type(assertion.get("kind")) is not str:
                raise TypeError(f"scenario line {number} has invalid assertion")
            kind = assertion["kind"]
            fields = tuple(sorted(assertion))
            previous = kinds.get(kind)
            if previous is not None and previous != fields:
                # Multiple reviewed schemas for one kind must be reviewed explicitly.
                fields = tuple(sorted(set(previous) | set(fields)))
            kinds[kind] = fields
    raw = json.dumps(kinds, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer-ref", required=True)
    parser.add_argument("--reviewer-policy-ref", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--issued-at", required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    build = json.loads((root / "BUILD_RECEIPT.json").read_text(encoding="utf-8"))
    partitions = tuple(sorted((root / "partitions").glob("*.json")))
    if len(partitions) != 7:
        raise ValueError("R4 review requires all seven independent partition axes")
    request = {
        "schema": "cemm-r4-external-review-request-v1",
        "scenario_source_sha256": _sha(args.scenarios.resolve()),
        "assertion_registry_sha256": _assertion_registry_sha(args.scenarios.resolve()),
        "expected_contract_set_sha256": _sha(root / "expected_contracts.jsonl"),
        "derivation_contract_set_sha256": _sha(root / "expected_derivations.jsonl"),
        "structural_sufficiency_sha256": _sha(root / "structural_sufficiency.json"),
        "episode_set_sha256": _sha(root / "episodes.jsonl"),
        "mutation_set_sha256": _sha(root / "mutations.jsonl"),
        "partition_manifest_sha256s": [_sha(path) for path in partitions],
        "authority_generation": build["authority_generation"],
        "abi_registry_ref": build["abi_registry_ref"],
        "source_revision": build["source_revision"],
        "reviewer_ref": args.reviewer_ref,
        "reviewer_policy_ref": args.reviewer_policy_ref,
        "requested_decision": "approve",
        "nonce": args.nonce,
        "issued_at": args.issued_at,
        "signature_algorithm": "REQUIRES_EXTERNAL_SIGNER",
        "signature": "REQUIRES_EXTERNAL_SIGNATURE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(request, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
