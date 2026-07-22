#!/usr/bin/env python3
"""Fail-closed Phase-13/14 activation verifier.

Static implementation presence is not the same as deployed authority. This verifier checks the
reviewed source contract and, when a store/boot database is supplied, requires at least one
ACTIVE exact lowered definition-teaching construction carrying valid Phase-14 learning authority.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from cemm.v350.language.minimum_english_v351 import CompositionFamily, MINIMUM_REVIEWED_ENGLISH
from cemm.v350.language.phase14_learning_authority_v351 import validate_definition_learning_authority_v351
from cemm.v350.schema.model import SchemaLifecycleStatus
from cemm.v350.storage import SemanticStore


def verify_source() -> list[str]:
    errors: list[str] = []
    if MINIMUM_REVIEWED_ENGLISH.revision < 4:
        errors.append("reviewed English source revision does not include Phase-14 learning contract")
    definitions = tuple(
        item for item in MINIMUM_REVIEWED_ENGLISH.constructions
        if item.family is CompositionFamily.DEFINITION_TEACHING
    )
    if len(definitions) != 1 or definitions[0].learning_contract is None:
        errors.append("reviewed English definition-teaching source contract is missing/ambiguous")
    return errors


def verify_store(store: SemanticStore) -> list[str]:
    errors: list[str] = []
    valid = []
    for stored in store.repositories.language.constructions.all(all_revisions=True):
        construction = stored.payload
        if construction.lifecycle_status is not SchemaLifecycleStatus.ACTIVE:
            continue
        if "semantic_definition_projection_v351" not in dict(construction.metadata):
            continue
        try:
            validate_definition_learning_authority_v351(construction)
        except Exception as exc:
            errors.append(
                f"invalid active definition-learning construction:{construction.construction_ref}@{construction.revision}:{type(exc).__name__}"
            )
        else:
            valid.append(f"{construction.construction_ref}@{construction.revision}")
    if not valid:
        errors.append(
            "no ACTIVE exact lowered definition-learning construction; M3 live unseen-concept teaching is not activated"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=":memory:")
    parser.add_argument("--boot-database", type=Path)
    parser.add_argument("--require-live-learning-authority", action="store_true")
    args = parser.parse_args()

    errors = verify_source()
    if args.require_live_learning_authority or args.boot_database is not None or args.database != ":memory:":
        store = SemanticStore(args.database, boot_path=args.boot_database)
        try:
            errors.extend(verify_store(store))
        finally:
            store.close()
    if errors:
        for error in errors:
            print("BLOCKED:", error)
        return 2
    print("PASS: Phase-13/14 reviewed source contract is valid")
    if args.require_live_learning_authority:
        print("PASS: live exact lowered definition-learning authority is active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
