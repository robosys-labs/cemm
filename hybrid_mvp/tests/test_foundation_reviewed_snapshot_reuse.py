"""Novel designation reuse across authority publication and process restart.

This uses a *reviewed source snapshot* change, not a runtime conversation write
or a simulated user authorization. It independently proves the foundation's
most important open-class invariant: an unseen synonym inherits the existing
target's semantic affordances with NO code or form-pack regeneration.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import pytest

from cemm_authoritative_hybrid.canonical import sha256_governed_text
from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact, StoreActivationError
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


def _authority_snapshot(root: Path) -> Path:
    dest = root / "data" / "authority"
    shutil.copytree(ROOT / "data" / "authority", dest)
    forms = root / "data" / "languages" / "en"
    forms.mkdir(parents=True)
    shutil.copy2(ROOT / "data" / "languages" / "en" / "forms.json", forms / "forms.json")
    return dest


def _publish_reviewed_alias(dest: Path, *, surface: str, target: str) -> None:
    # The source publication deliberately remains out-of-band and reviewed.
    # This is NOT an API that permits arbitrary chat to modify authority.
    conversation_path = dest / "conversation.json"
    owner = json.loads(conversation_path.read_text(encoding="utf-8"))
    owner["designations"].append({
        "language": "en", "surface": surface, "target": target,
    })
    conversation_path.write_text(
        json.dumps(owner, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    manifest_path = dest / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generation"] = "authority-reviewed-alias-20261008"
    for row in manifest["owners"]:
        if row["name"] == "conversation":
            row["sha256"] = sha256_governed_text(conversation_path)
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )


def _reviewed_ownership():
    return Fact(
        fact_ref="fact:reviewed-owner-of-book",
        operator="op:relation",
        args={
            "predicate_ref": "rel:owns",
            "role:subject": "entity:alice",
            "role:object": "entity:book",
        },
        proof={"source": "source:reviewed-ownership", "placement": "observed"},
    )


def _assert_query_uses_reviewed_alias(runtime, utterance):
    turn = runtime.process("session:reviewed-alias", utterance)
    assert turn.verify()
    assert turn.cycle.verification.status == "selected"
    response = turn.cycle.response_meaning
    assert response is not None and response.discourse_action == "answer"
    assert ("?v0", "entity:alice") in response.bindings
    assert "source:reviewed-ownership" in response.source_refs


def test_new_reviewed_designation_inherits_semantics_without_pack_rebuild(tmp_path):
    project = tmp_path / "authority-release"
    authority_dir = _authority_snapshot(project)
    fixed_pack = (project / "data/languages/en/forms.json").read_bytes()

    baseline_store = tmp_path / "baseline.sqlite3"
    baseline = load_foundation(project, store_path=baseline_store)
    try:
        before = baseline.stores.revision_pin().world_revision
        unknown = baseline.process("session:baseline-unknown", "Who owns the tome?")
        assert unknown.verify()
        assert unknown.cycle.verification.status != "selected"
        assert baseline.stores.revision_pin().world_revision == before
    finally:
        baseline.close()

    _publish_reviewed_alias(authority_dir, surface="tome", target="entity:book")
    _publish_reviewed_alias(authority_dir, surface="possesses", target="rel:owns")
    assert (project / "data/languages/en/forms.json").read_bytes() == fixed_pack
    # A generation change must invalidate stores pinned to the old bundle.
    with pytest.raises(StoreActivationError):
        load_foundation(project, store_path=baseline_store)

    stored = tmp_path / "reviewed.sqlite3"
    admitted = load_foundation(project, store_path=stored)
    try:
        install_reviewed_world_facts(admitted.stores, facts=(_reviewed_ownership(),))
        _assert_query_uses_reviewed_alias(admitted, "Who owns the tome?")
        _assert_query_uses_reviewed_alias(admitted, "Who possesses the tome?")
    finally:
        admitted.close()

    restarted = load_foundation(project, store_path=stored)
    try:
        _assert_query_uses_reviewed_alias(restarted, "Who owns the tome?")
        _assert_query_uses_reviewed_alias(restarted, "Who possesses the tome?")
    finally:
        restarted.close()
