"""Revision-aware authority and indexing for reviewed language records."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from ..schema.model import SchemaLifecycleStatus
from .model import (
    ConstructionRecord,
    FormSenseLinkRecord,
    LanguageFormRecord,
    LanguagePackRecord,
    LexicalSenseRecord,
)


class LanguageRegistryError(ValueError):
    pass


_ACTIVE = {SchemaLifecycleStatus.ACTIVE}


@dataclass(frozen=True, slots=True)
class LanguageRegistrySnapshot:
    packs: tuple[LanguagePackRecord, ...]
    forms: tuple[LanguageFormRecord, ...]
    senses: tuple[LexicalSenseRecord, ...]
    links: tuple[FormSenseLinkRecord, ...]
    constructions: tuple[ConstructionRecord, ...]


class LanguageRegistry:
    def __init__(
        self,
        packs: Iterable[LanguagePackRecord] = (),
        forms: Iterable[LanguageFormRecord] = (),
        senses: Iterable[LexicalSenseRecord] = (),
        links: Iterable[FormSenseLinkRecord] = (),
        constructions: Iterable[ConstructionRecord] = (),
    ) -> None:
        self._packs = _index(packs, lambda item: item.pack_ref, "language pack")
        self._forms = _index(forms, lambda item: item.form_ref, "language form")
        self._senses = _index(senses, lambda item: item.sense_ref, "lexical sense")
        self._links = _index(links, lambda item: item.link_ref, "form-sense link")
        self._constructions = _index(constructions, lambda item: item.construction_ref, "construction")
        self._validate()
        self._forms_by_key: dict[tuple[str, str], list[LanguageFormRecord]] = defaultdict(list)
        for item in self.active_forms():
            pack = self.require_pack(item.pack_ref, item.pack_revision)
            self._forms_by_key[(pack.language_tag, item.normalized_form)].append(item)
        for values in self._forms_by_key.values():
            values.sort(key=lambda item: (item.token_count, item.form_ref, item.revision))
        self._normalization_index: dict[tuple[str, str], list[LanguageFormRecord]] = defaultdict(list)
        for item in self.active_forms():
            pack = self.require_pack(item.pack_ref, item.pack_revision)
            for key in item.metadata.get("normalization_sources", ()):
                self._normalization_index[(pack.language_tag, str(key))].append(item)
        for values in self._normalization_index.values():
            values.sort(key=lambda item: (item.form_ref, item.revision))
        self._links_by_form: dict[tuple[str, int], list[FormSenseLinkRecord]] = defaultdict(list)
        for item in self.active_links():
            self._links_by_form[(item.form_ref, item.form_revision)].append(item)
        for values in self._links_by_form.values():
            values.sort(key=lambda item: (-item.prior_weight, item.sense_ref, item.revision))

    def _validate(self) -> None:
        for label, index in (
            ("language pack", self._packs), ("language form", self._forms),
            ("lexical sense", self._senses), ("form-sense link", self._links),
            ("construction", self._constructions),
        ):
            for ref, revisions in index.items():
                for item in revisions.values():
                    if item.supersedes_revision is not None and item.supersedes_revision not in revisions:
                        raise LanguageRegistryError(
                            f"{label} {ref}@{item.revision} supersedes missing revision "
                            f"{item.supersedes_revision}"
                        )
                effective = _effective_revisions(revisions)
                if len(effective) > 1:
                    raise LanguageRegistryError(
                        f"{label} has multiple effective active revisions: {ref} "
                        f"{sorted(item.revision for item in effective)}"
                    )
        for pack in self.iter_packs():
            if pack.lifecycle_status in _ACTIVE and not pack.competence_case_refs:
                raise LanguageRegistryError(f"active pack lacks competence: {pack.pack_ref}")
        for form in self.iter_forms():
            pack = self.require_pack(form.pack_ref, form.pack_revision)
            if form.lifecycle_status in _ACTIVE and pack.lifecycle_status not in _ACTIVE:
                raise LanguageRegistryError(f"active form uses inactive pack: {form.form_ref}")
            if form.variant_of_ref is not None:
                variant = self.require_form(form.variant_of_ref)
                if variant.pack_ref != form.pack_ref:
                    raise LanguageRegistryError(f"form variant crosses language packs: {form.form_ref}")
        for sense in self.iter_senses():
            pack = self.require_pack(sense.pack_ref, sense.pack_revision)
            if sense.lifecycle_status in _ACTIVE and pack.lifecycle_status not in _ACTIVE:
                raise LanguageRegistryError(f"active sense uses inactive pack: {sense.sense_ref}")
        for link in self.iter_links():
            form = self.require_form(link.form_ref, link.form_revision)
            sense = self.require_sense(link.sense_ref, link.sense_revision)
            if form.pack_ref != sense.pack_ref:
                raise LanguageRegistryError(f"form-sense link crosses packs: {link.link_ref}")
            if link.lifecycle_status in _ACTIVE and (
                form.lifecycle_status not in _ACTIVE or sense.lifecycle_status not in _ACTIVE
            ):
                raise LanguageRegistryError(f"active link references inactive record: {link.link_ref}")
        for construction in self.iter_constructions():
            pack = self.require_pack(construction.pack_ref, construction.pack_revision)
            if construction.lifecycle_status in _ACTIVE and pack.lifecycle_status not in _ACTIVE:
                raise LanguageRegistryError(f"active construction uses inactive pack: {construction.construction_ref}")
            for ref in construction.trigger_form_refs:
                if self.require_form(ref).pack_ref != construction.pack_ref:
                    raise LanguageRegistryError(f"construction trigger form crosses pack: {construction.construction_ref}")
            for ref in construction.trigger_sense_refs:
                if self.require_sense(ref).pack_ref != construction.pack_ref:
                    raise LanguageRegistryError(f"construction trigger sense crosses pack: {construction.construction_ref}")

    def snapshot(self) -> LanguageRegistrySnapshot:
        return LanguageRegistrySnapshot(
            packs=tuple(self.iter_packs()), forms=tuple(self.iter_forms()), senses=tuple(self.iter_senses()),
            links=tuple(self.iter_links()), constructions=tuple(self.iter_constructions()),
        )

    def iter_packs(self): return _flatten(self._packs)
    def iter_forms(self): return _flatten(self._forms)
    def iter_senses(self): return _flatten(self._senses)
    def iter_links(self): return _flatten(self._links)
    def iter_constructions(self): return _flatten(self._constructions)

    def active_packs(self): return _effective_flatten(self._packs)
    def active_forms(self): return _effective_flatten(self._forms)
    def active_senses(self): return _effective_flatten(self._senses)
    def active_links(self): return _effective_flatten(self._links)
    def active_constructions(self): return _effective_flatten(self._constructions)

    def require_pack(self, ref: str, revision: int | None = None) -> LanguagePackRecord:
        return _require(self._packs, ref, revision, "language pack")
    def require_form(self, ref: str, revision: int | None = None) -> LanguageFormRecord:
        return _require(self._forms, ref, revision, "language form")
    def require_sense(self, ref: str, revision: int | None = None) -> LexicalSenseRecord:
        return _require(self._senses, ref, revision, "lexical sense")
    def require_link(self, ref: str, revision: int | None = None) -> FormSenseLinkRecord:
        return _require(self._links, ref, revision, "form-sense link")
    def require_construction(self, ref: str, revision: int | None = None) -> ConstructionRecord:
        return _require(self._constructions, ref, revision, "construction")

    def pack_for_language(self, language_tag: str) -> LanguagePackRecord | None:
        candidates = [item for item in self.active_packs() if item.language_tag == language_tag]
        return max(candidates, key=lambda item: item.revision) if candidates else None

    def forms_for(self, language_tag: str, normalized_form: str) -> tuple[LanguageFormRecord, ...]:
        return tuple(self._forms_by_key.get((language_tag, normalized_form), ()))

    def normalization_forms_for(self, language_tag: str, observed_key: str) -> tuple[LanguageFormRecord, ...]:
        return tuple(self._normalization_index.get((language_tag, observed_key), ()))

    def links_for_form(self, form_ref: str, revision: int) -> tuple[FormSenseLinkRecord, ...]:
        return tuple(self._links_by_form.get((form_ref, revision), ()))


def _index(items, get_ref, label):
    result = defaultdict(dict)
    for item in items:
        ref = get_ref(item)
        revision = item.revision
        if revision in result[ref]:
            raise LanguageRegistryError(f"duplicate {label}: {ref}@{revision}")
        result[ref][revision] = item
    return dict(result)


def _flatten(index):
    return tuple(index[ref][revision] for ref in sorted(index) for revision in sorted(index[ref]))


def _effective_revisions(revisions):
    superseded = {
        item.supersedes_revision for item in revisions.values()
        if item.supersedes_revision is not None
        and item.lifecycle_status == SchemaLifecycleStatus.ACTIVE
    }
    return tuple(sorted(
        (item for item in revisions.values()
         if item.lifecycle_status in _ACTIVE and item.revision not in superseded),
        key=lambda item: item.revision,
    ))


def _effective_flatten(index):
    return tuple(
        item for ref in sorted(index) for item in _effective_revisions(index[ref])
    )


def _require(index, ref, revision, label):
    values = index.get(ref)
    if not values:
        raise LanguageRegistryError(f"missing {label}: {ref}")
    if revision is None:
        active = _effective_revisions(values)
        if len(active) != 1:
            raise LanguageRegistryError(f"{label} has no singular effective revision: {ref}")
        return active[0]
    try:
        return values[revision]
    except KeyError as exc:
        raise LanguageRegistryError(f"missing {label}: {ref}@{revision}") from exc
