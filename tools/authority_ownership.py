#!/usr/bin/env python3
"""Authority ownership and migration preflight for CEMM bundles.

An atom is defined by exactly one authority document.  Other documents may refer
across that boundary but may never redefine the atom, even with identical kind or
metadata.  This module is deliberately usable before a bundle mutates the checkout.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class AuthorityOwnershipError(ValueError):
    pass


@dataclass(frozen=True)
class AuthorityOwnershipIndex:
    atom_owner: Mapping[str, str]
    atom_definition: Mapping[str, Mapping[str, Any]]
    document_atoms: Mapping[str, tuple[str, ...]]

    @classmethod
    def build(cls, paths: Iterable[Path]) -> "AuthorityOwnershipIndex":
        owner: dict[str, str] = {}
        definitions: dict[str, Mapping[str, Any]] = {}
        by_document: dict[str, tuple[str, ...]] = {}
        issues: list[str] = []
        for path in sorted(Path(item) for item in paths):
            data = json.loads(path.read_text(encoding="utf-8"))
            refs: list[str] = []
            local: set[str] = set()
            for index, atom in enumerate(data.get("atoms", ())):
                ref = str(atom.get("ref") or "")
                if not ref:
                    issues.append(f"{path}: atom {index} has no ref")
                    continue
                if ref in local:
                    issues.append(f"{path}: duplicate local atom definition: {ref}")
                    continue
                local.add(ref)
                refs.append(ref)
                previous = owner.get(ref)
                if previous is not None:
                    issues.append(
                        f"cross-document atom ownership conflict: {ref} is defined by "
                        f"{previous} and {path}"
                    )
                    continue
                owner[ref] = str(path)
                definitions[ref] = dict(atom)
            by_document[str(path)] = tuple(sorted(refs))
        if issues:
            raise AuthorityOwnershipError("\n".join(issues))
        return cls(owner, definitions, by_document)

    def require_owner(self, ref: str, path: Path) -> None:
        actual = self.atom_owner.get(ref)
        expected = str(path)
        if actual != expected:
            raise AuthorityOwnershipError(
                f"authority owner mismatch for {ref}: expected {expected}, found {actual}"
            )

    def reject_runtime_metadata(self) -> None:
        issues = []
        for ref, atom in self.atom_definition.items():
            metadata = dict(atom.get("metadata", {}) or {})
            leaked = sorted(
                key
                for key in metadata
                if key in {
                    "runtime_derived",
                    "runtime_observed",
                    "cycle_local",
                    "ephemeral",
                }
                and metadata.get(key)
            )
            if leaked:
                issues.append(
                    f"authority atom {ref} contains transient runtime metadata: {leaked}"
                )
        if issues:
            raise AuthorityOwnershipError("\n".join(issues))


def validate_repository_authority(repo: Path) -> AuthorityOwnershipIndex:
    repo = Path(repo).resolve()
    paths = sorted((repo / "cemm/data").glob("*.json"))
    if not paths:
        raise AuthorityOwnershipError("no cemm/data/*.json authority documents found")
    index = AuthorityOwnershipIndex.build(paths)
    index.reject_runtime_metadata()

    # Use the repository's canonical semantic validator as a second, independent
    # check. Import happens only after repository identity has been established.
    import sys

    sys.path.insert(0, str(repo))
    imported_before = set(sys.modules)
    try:
        from cemm.authority import load_documents, validate_documents

        validate_documents(load_documents(paths), require_foundations=True)
    finally:
        try:
            sys.path.remove(str(repo))
        except ValueError:
            pass
        # This tool can validate multiple temporary repositories in one process.
        # Never retain modules imported from a prior checkout.
        for name in sorted(set(sys.modules) - imported_before, reverse=True):
            if name == "cemm" or name.startswith("cemm."):
                sys.modules.pop(name, None)

    base = repo / "cemm/data/base.json"
    conversation = repo / "cemm/data/conversation_foundation.json"
    if not base.exists() or not conversation.exists():
        raise AuthorityOwnershipError("base.json and conversation_foundation.json are required")
    for ref in (
        "value:unknown",
        "dim:runtime_process_support",
        "dim:semantic_runtime_support",
        "dim:language_realizer_support",
        "dim:critical_blocker_count",
        "rel:subtype_of",
        "rel:value_of_dimension",
    ):
        index.require_owner(ref, base)
    for ref in (
        "rel:knows",
        "resource:inference_engine",
        "resource:designation_index",
        "resource:semantic_store",
        "resource:common_ground",
    ):
        index.require_owner(ref, conversation)
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    index = validate_repository_authority(Path(args.repo))
    print(
        json.dumps(
            {
                "status": "authority_ownership_valid",
                "atom_count": len(index.atom_owner),
                "document_count": len(index.document_atoms),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
