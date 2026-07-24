"""Generation-compiled REALIZE eligibility for language/realization authority.

This compatibility-shaped API delegates to CompiledSemanticCapabilityRegistry.  It
contains no independent authorization logic and therefore cannot become a second brain.
"""
from __future__ import annotations

from ..learning.model import PinnedRecord
from ..schema.model import UseOperation
from ..semantic_capability import CompiledSemanticCapabilityRegistry
from ..storage.model import RecordKind


class LanguageUseAuthority:
    LANGUAGE_KINDS = {
        RecordKind.LANGUAGE_PACK, RecordKind.LANGUAGE_FORM, RecordKind.LEXEME,
        RecordKind.FORM_LEXEME_LINK, RecordKind.LEXICAL_SENSE,
        RecordKind.LEXEME_SENSE_LINK, RecordKind.FORM_SENSE_LINK,
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC, RecordKind.CONSTRUCTION,
        RecordKind.CONSTRUCTION_PROGRAM, RecordKind.ARGUMENT_FRAME,
        RecordKind.MORPHOLOGY_RULE, RecordKind.LINEARIZATION_RULE,
    }

    def __init__(self, store, registry: CompiledSemanticCapabilityRegistry | None = None) -> None:
        self.store = store
        self.registry = registry or CompiledSemanticCapabilityRegistry(store)

    @staticmethod
    def _pin(stored):
        return PinnedRecord(stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)

    def authorized(self, stored, operation: UseOperation) -> bool:
        if stored.record_kind not in self.LANGUAGE_KINDS:
            return False
        return self.registry.compile(self._pin(stored), operation).eligible

    def records_for_use(self, kind: RecordKind, operation: UseOperation):
        if kind not in self.LANGUAGE_KINDS:
            return ()
        return self.registry.records_for_use(kind, operation)


__all__ = ["LanguageUseAuthority"]
