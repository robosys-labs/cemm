from __future__ import annotations

from dataclasses import fields
import inspect

from cemm.v350.operations.model import OperationReconciliationRecord
from cemm.v350.realization.authority import LanguageUseAuthority
from cemm.v350.realization.model import SemanticRoundTripRecord


def test_operation_reconciliation_pins_exact_observed_journal_revision():
    names={item.name for item in fields(OperationReconciliationRecord)}
    assert "observed_journal_pin" in names


def test_roundtrip_pins_reviewed_semantic_analyzer_contract():
    names={item.name for item in fields(SemanticRoundTripRecord)}
    assert "analyzer_contract_pin" in names


def test_overlay_language_records_do_not_self_authorize_by_active_status():
    source=inspect.getsource(LanguageUseAuthority.authorized)
    assert "self.registry.compile" in source
    assert "LANGUAGE_KINDS" in source


def test_language_authority_requires_singular_effective_revision():
    source=inspect.getsource(LanguageUseAuthority)
    assert "self.registry.compile(self._pin(stored), operation).eligible" in source
