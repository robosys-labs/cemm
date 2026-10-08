"""The canonical semantic path must survive a complete store close/reopen."""
from pathlib import Path

from cemm_authoritative_hybrid.foundation import load_foundation

ROOT = Path(__file__).resolve().parents[1]


def test_semantic_turn_survives_store_restart(tmp_path):
    store_path = tmp_path / "foundation-restart.sqlite3"
    first = load_foundation(ROOT, store_path=store_path)
    try:
        first_turn = first.process("session:restart", "hello")
        assert first_turn.verify()
        old_revision = first.stores.revision_pin()
    finally:
        first.close()

    reopened = load_foundation(ROOT, store_path=store_path)
    try:
        assert reopened.stores.revision_pin() == old_revision
        next_turn = reopened.process("session:restart", "hello")
        assert next_turn.verify()
        assert next_turn.cycle.final_revision_pin.session_revision >= old_revision.session_revision
        assert next_turn.cycle.final_revision_pin.effect_revision >= old_revision.effect_revision
    finally:
        reopened.close()
