"""Source-only CLI for the immutable corrective-replay test inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from test_inventory_core import (
    InventoryError,
    PHASES,
    load_and_verify,
    verify_document_authority_pin,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=PHASES)
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="required explicit acknowledgement that this command never executes tests",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.source_only:
        _parser().error("--source-only is required")
    root = Path(__file__).resolve().parents[1]
    inventory_path = root / "governance" / "test_inventory.json"
    try:
        inventory_sha256 = verify_document_authority_pin(root, inventory_path)
        result = load_and_verify(
            root,
            inventory_path,
            phase=args.phase,
            enforce_reviewed_counts=True,
            expected_sha256=inventory_sha256,
        )
    except InventoryError as exc:
        print(f"test inventory verification failed: {exc}", file=sys.stderr)
        return 1
    payload: dict[str, object] = {
        "schema": "cemm-test-inventory-check-v1",
        "phase": args.phase,
        "inventory_ref": result.inventory_ref,
        "inventory_sha256": inventory_sha256,
        "literal_metadata_ref": result.literal_metadata_ref,
        "active_node_set_ref": result.active_node_set_ref,
        "active_node_count": len(result.active_node_ids),
        "collectable_node_set_ref": result.collectable_node_set_ref,
        "collectable_node_count": len(result.collectable_node_ids),
        "deferred_rewrite_count": len(result.deferred_rewrite_refs),
        "due_rewrite_count": len(result.due_rewrite_refs),
        "parsed_module_count": result.parsed_module_count,
    }
    if PHASES.index(args.phase) >= PHASES.index("R5"):
        deferred_count = len(result.deferred_r5_assertion_refs)
        retired_count = len(result.retired_r5_assertion_refs)
        r5_predecessor_count = sum(
            record.classification == "retained"
            and record.activation_phase == "R5"
            for record in result.source_tests.values()
        )
        payload.update(
            {
                "r5_disposition_receipt_ref": result.r5_disposition_receipt_ref,
                "r5_successor_count": (
                    r5_predecessor_count - deferred_count - retired_count
                ),
                "r5_deferred_count": deferred_count,
                "r5_retired_count": retired_count,
            }
        )
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
