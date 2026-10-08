"""Unadmitted quantifiers may not masquerade as definite referent identity.

The semantic kernel has no admitted existential/universal binder for these
surface constructions. The safe behavior is a typed unresolved frontier.
"""
from pathlib import Path
import pytest

from cemm_authoritative_hybrid.foundation import load_foundation

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("utterance", (
    "Who owns a book?",
    "Alice owns a book.",
    "Who owns some book?",
    "Who owns every book?",
    "Who owns any book?",
    "Who owns all books?",
))
def test_quantified_nominal_fails_closed_without_scoped_semantics(tmp_path, utterance):
    runtime = load_foundation(ROOT, store_path=tmp_path / "quantified.sqlite3")
    try:
        before = runtime.stores.revision_pin().world_revision
        result = runtime.process("session:unadmitted-quantifier", utterance)
        assert result.verify()
        assert result.cycle.verification.status != "selected", utterance
        assert runtime.stores.revision_pin().world_revision == before
    finally:
        runtime.close()


def test_definite_known_nominal_can_form_reference_binding(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "definite.sqlite3")
    try:
        result = runtime.process("session:definite", "Who owns the book?")
        assert result.verify()
        assert result.cycle.verification.status == "selected"
    finally:
        runtime.close()
