"""Public-path safety regressions for unreviewed knowledge and attribution.

These are NOT evidence that reviewer-authorized learning or attribution
questions have been fully implemented. They only prohibit unsafe promotion.
"""
from pathlib import Path

from cemm_authoritative_hybrid.foundation import load_foundation

ROOT = Path(__file__).resolve().parents[1]


def test_unreviewed_lexical_claim_does_not_publish_a_new_designation(tmp_path):
    foundation = load_foundation(
        ROOT, store_path=tmp_path / "unreviewed-learning.sqlite3"
    )
    try:
        before = foundation.stores.revision_pin()
        proposal = foundation.process("session:unreviewed", "yoz means hello")
        assert proposal.verify()
        after = foundation.stores.revision_pin()
        assert after.world_revision == before.world_revision
        lookup = foundation.process("session:unreviewed", "What does yoz mean?")
        assert lookup.verify()
        assert lookup.cycle.response_meaning is None or (
            lookup.cycle.response_meaning.discourse_action != "answer"
        )
        assert foundation.stores.revision_pin().world_revision == before.world_revision
    finally:
        foundation.close()


def test_unverified_report_does_not_become_world_event(tmp_path):
    foundation = load_foundation(
        ROOT, store_path=tmp_path / "untrusted-attribution.sqlite3"
    )
    try:
        before = foundation.stores.revision_pin()
        result = foundation.process("session:untrusted-report", "Mary said Bob left.")
        assert result.verify()
        assert foundation.stores.revision_pin().world_revision == before.world_revision
    finally:
        foundation.close()
