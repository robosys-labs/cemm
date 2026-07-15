"""Compatibility redirect to the canonical v3.4.3 data package.

This file must contain no predicates, words, entity kinds, constructions,
realizations, or transcript-specific vocabulary.
"""
from __future__ import annotations

from pathlib import Path

from .v343 import load_v343_package


def load_foundations(data_root: Path):
    return load_v343_package(data_root)


def register_v341_foundations(store, data_root: Path | None = None):
    root = data_root or Path(__file__).resolve().parents[2] / "data"
    package = load_v343_package(root)
    # Schema-store adaptation is intentionally explicit.  The caller must
    # register audited contracts through the canonical store transaction rather
    # than having this compatibility module fabricate active envelopes.
    if not hasattr(store, "register_boot_package"):
        raise TypeError(
            "schema store must implement register_boot_package(package)"
        )
    return store.register_boot_package(package)


def validate_v341_spec(data_root: Path | None = None):
    root = data_root or Path(__file__).resolve().parents[2] / "data"
    return load_v343_package(root)
