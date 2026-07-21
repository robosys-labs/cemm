"""Realize cycle-local bound query values through reviewed language authority.

Bound query values are not durable semantic facts.  The lexicalizer therefore
accepts only proof-bearing answer referents created by the universal binder and
never falls back to transcript text, schema semantic keys, or Python concept
names.
"""
from __future__ import annotations

from ..learning.model import PinnedRecord
from ..schema.model import UseOperation
from ..storage.model import RecordKind
from .authority import LanguageUseAuthority
from .engine import RealizationFrontier


class BoundValueLexicalizer:
    def __init__(self, store) -> None:
        self.store = store
        self.authority = LanguageUseAuthority(store)

    def realize_schema_topic(self, referent, request):
        schema_ref = str(
            referent.metadata.get("schema_ref")
            or referent.metadata.get("schema_topic_ref")
            or ""
        )
        schema_revision = int(
            referent.metadata.get("schema_revision")
            or referent.metadata.get("schema_topic_revision")
            or 0
        )
        if not schema_ref or schema_revision < 1:
            raise RealizationFrontier(
                "bound_schema_topic_missing_exact_pin",
                (referent.referent_ref,),
            )
        return self._lexicalize_exact_schema(
            schema_ref, schema_revision, request
        )

    def realize_literal(self, referent, response, request):
        surface = referent.metadata.get("literal_surface")
        if not isinstance(surface, str) or not surface:
            raise RealizationFrontier(
                "bound_literal_missing_authorized_surface",
                (referent.referent_ref,),
            )
        raw_kind = referent.metadata.get("source_record_kind")
        source_ref = str(referent.metadata.get("source_record_ref") or "")
        source_revision = int(referent.metadata.get("source_revision") or 0)
        source_fingerprint = str(
            referent.metadata.get("source_fingerprint") or ""
        )
        try:
            source_kind = RecordKind(str(raw_kind))
        except (TypeError, ValueError) as exc:
            raise RealizationFrontier(
                "bound_literal_missing_source_pin",
                (referent.referent_ref,),
            ) from exc
        if not source_ref or source_revision < 1 or not source_fingerprint:
            raise RealizationFrontier(
                "bound_literal_missing_source_pin",
                (referent.referent_ref,),
            )
        pin = PinnedRecord(
            source_kind,
            source_ref,
            source_revision,
            source_fingerprint,
        )
        if pin not in response.source_pins:
            raise RealizationFrontier(
                "bound_literal_not_in_response_lineage",
                (source_ref,),
            )
        stored = self.store.get_record(
            source_kind, source_ref, source_revision
        )
        if (
            stored is None
            or stored.record_fingerprint != source_fingerprint
            or self.store.is_invalidated(
                source_kind, source_ref, source_revision
            )
        ):
            raise RealizationFrontier(
                "bound_literal_source_stale_or_invalidated",
                (source_ref,),
            )
        permission = stored.permission_ref or getattr(
            stored.payload, "permission_ref", None
        )
        if permission not in {None, "public", request.permission_ref}:
            raise RealizationFrontier(
                "bound_literal_permission_blocked", (source_ref,)
            )
        return surface, (pin,)

    def _lexicalize_exact_schema(
        self, schema_ref: str, schema_revision: int, request
    ):
        allowed_packs = {
            (pin.record_ref, pin.revision)
            for pin in request.language_pack_pins
            if pin.record_kind == RecordKind.LANGUAGE_PACK
        }
        registry = self.store.repositories.language.registry()
        candidates = []
        for sense in registry.active_senses():
            if (
                sense.target_ref != schema_ref
                or sense.target_revision != schema_revision
                or not sense.supports_use(UseOperation.REALIZE)
                or (sense.pack_ref, sense.pack_revision) not in allowed_packs
            ):
                continue
            sense_stored = self.store.get_record(
                RecordKind.LEXICAL_SENSE, sense.sense_ref, sense.revision
            )
            pack_stored = self.store.get_record(
                RecordKind.LANGUAGE_PACK,
                sense.pack_ref,
                sense.pack_revision,
            )
            if (
                sense_stored is None
                or pack_stored is None
                or pack_stored.payload.language_tag != request.language_tag
                or pack_stored.permission_ref not in {None, "public", request.permission_ref}
                or not self.authority.authorized(pack_stored, UseOperation.REALIZE)
                or not self.authority.authorized(
                    sense_stored, UseOperation.REALIZE
                )
            ):
                continue
            for link in registry.lexeme_links_for_sense(
                sense.sense_ref, sense.revision
            ):
                lexeme_stored = self.store.get_record(
                    RecordKind.LEXEME,
                    link.lexeme_ref,
                    link.lexeme_revision,
                )
                if (
                    lexeme_stored is None
                    or not self.authority.authorized(
                        lexeme_stored, UseOperation.REALIZE
                    )
                ):
                    continue
                lexeme = lexeme_stored.payload
                form_stored = self.store.get_record(
                    RecordKind.LANGUAGE_FORM,
                    lexeme.lemma_form_ref,
                    lexeme.lemma_form_revision,
                )
                if (
                    form_stored is None
                    or not self.authority.authorized(
                        form_stored, UseOperation.REALIZE
                    )
                    or (
                        request.script
                        and form_stored.payload.script
                        and form_stored.payload.script != request.script
                    )
                ):
                    continue
                link_stored = self.store.get_record(
                    RecordKind.LEXEME_SENSE_LINK,
                    link.link_ref,
                    link.revision,
                )
                if (
                    link_stored is None
                    or link_stored.permission_ref not in {None, "public", request.permission_ref}
                    or not self.authority.authorized(link_stored, UseOperation.REALIZE)
                ):
                    continue
                candidates.append(
                    (
                        -float(link.prior_weight),
                        form_stored.record_ref,
                        sense_stored,
                        lexeme_stored,
                        link_stored,
                        form_stored,
                    )
                )

        # Bound query values require the canonical Phase-9 lexeme path.
        # Legacy direct form-sense links remain available only to predicate
        # realization until their own reviewed migration is complete.

        candidates.sort(key=lambda item: (item[0], item[1], item[2].record_ref))
        if not candidates:
            raise RealizationFrontier(
                "missing_bound_value_lexicalization",
                (schema_ref, str(schema_revision), request.language_tag),
            )
        best = candidates[0]
        # Equal-priority different surfaces are true lexical ambiguity.
        if (
            len(candidates) > 1
            and candidates[1][0] == best[0]
            and candidates[1][5].payload.written_form
            != best[5].payload.written_form
        ):
            raise RealizationFrontier(
                "ambiguous_bound_value_lexicalization",
                (schema_ref, str(schema_revision), request.language_tag),
            )
        _, _, sense_stored, lexeme_stored, link_stored, form_stored = best
        return (
            form_stored.payload.written_form,
            (
                _pin_record(sense_stored),
                _pin_record(lexeme_stored),
                _pin_record(link_stored),
                _pin_record(form_stored),
            ),
        )


def _pin_record(stored):
    return PinnedRecord(stored.record_kind, stored.record_ref, stored.revision, stored.record_fingerprint)
