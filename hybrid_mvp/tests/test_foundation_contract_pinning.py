"""Persistent semantic meaning must never be replayed under changed contracts.

A manifest generation string is a human label. The store must also bind the
exact linked authority content, tokenization/forms and proposal model. Any
silent same-generation drift is an activation failure, not a migration.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.canonical import sha256_governed_text
from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import open_stores, StoreActivationError

ROOT = Path(__file__).resolve().parents[1]


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "reviewed-project"
    owners = project / "data" / "authority"
    owners.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "data" / "authority", owners)
    forms = project / "data" / "languages" / "en"
    forms.mkdir(parents=True)
    shutil.copy2(ROOT / "data/languages/en/forms.json", forms / "forms.json")
    return project


def _reopen_and_reject(project: Path, store: Path) -> None:
    with pytest.raises(StoreActivationError, match="semantic execution contract"):
        load_foundation(project, store_path=store)


def test_same_generation_owner_content_drift_fails_closed(tmp_path):
    project = _project(tmp_path)
    store = tmp_path / "world-store"
    runtime = load_foundation(project, store_path=store)
    try:
        assert runtime.process("session:contract", "hello").verify()
    finally:
        runtime.close()

    owner = project / "data/authority/conversation.json"
    manifest = project / "data/authority/manifest.json"
    updated = json.loads(owner.read_text(encoding="utf-8"))
    updated["designations"].append({
        "surface": "novelword", "target": "event:greeting", "language": "en",
    })
    owner.write_text(
        json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    m = json.loads(manifest.read_text(encoding="utf-8"))
    original_generation = m["generation"]
    for row in m["owners"]:
        if row["name"] == "conversation":
            row["sha256"] = sha256_governed_text(owner)
    manifest.write_text(
        json.dumps(m, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    assert json.loads(manifest.read_text())["generation"] == original_generation
    _reopen_and_reject(project, store)


def test_same_generation_language_forms_change_fails_closed(tmp_path):
    project = _project(tmp_path)
    store = tmp_path / "form-store"
    runtime = load_foundation(project, store_path=store)
    runtime.close()

    path = project / "data/languages/en/forms.json"
    forms = json.loads(path.read_text(encoding="utf-8"))
    forms["tokenization"]["lowercase"] = not forms["tokenization"]["lowercase"]
    path.write_text(
        json.dumps(forms, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    _reopen_and_reject(project, store)


def test_unpinned_legacy_store_never_silently_upgrades(tmp_path):
    project = _project(tmp_path)
    generation = AuthorityLinker().link_path(
        project / "data/authority/manifest.json",
    ).generation
    store = tmp_path / "legacy-unpinned"
    old = open_stores(store, authority_generation=generation,
                      model_identity="bootstrap-proposer")
    old.close()
    _reopen_and_reject(project, store)


def test_consistent_contract_restarts_without_resetting_history(tmp_path):
    project = _project(tmp_path)
    store = tmp_path / "stable"
    first = load_foundation(project, store_path=store)
    try:
        assert first.process("session:stable", "hello").verify()
        pin = first.stores.revision_pin()
    finally:
        first.close()
    later = load_foundation(project, store_path=store)
    try:
        assert later.stores.revision_pin() == pin
        assert later.process("session:stable", "hello").verify()
    finally:
        later.close()
