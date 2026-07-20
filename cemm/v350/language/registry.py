"""Revision-aware authority and indexing for reviewed language records."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from ..schema.model import SchemaLifecycleStatus, UseOperation
from .model import (
    ConstructionRecord,
    FormLexemeLinkRecord,
    FormSenseLinkRecord,
    LanguageFormRecord,
    LanguagePackRecord,
    LexemeRecord,
    LexemeSenseLinkRecord,
    LexicalSenseRecord,
    SemanticContributionSpecRecord,
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
    lexemes: tuple[LexemeRecord, ...]
    form_lexeme_links: tuple[FormLexemeLinkRecord, ...]
    lexeme_sense_links: tuple[LexemeSenseLinkRecord, ...]
    contribution_specs: tuple[SemanticContributionSpecRecord, ...]


class LanguageRegistry:
    def __init__(
        self,
        packs: Iterable[LanguagePackRecord] = (),
        forms: Iterable[LanguageFormRecord] = (),
        senses: Iterable[LexicalSenseRecord] = (),
        links: Iterable[FormSenseLinkRecord] = (),
        constructions: Iterable[ConstructionRecord] = (),
        lexemes: Iterable[LexemeRecord] = (),
        form_lexeme_links: Iterable[FormLexemeLinkRecord] = (),
        lexeme_sense_links: Iterable[LexemeSenseLinkRecord] = (),
        contribution_specs: Iterable[SemanticContributionSpecRecord] = (),
    ) -> None:
        self._packs = _index(packs, lambda item: item.pack_ref, "language pack")
        self._forms = _index(forms, lambda item: item.form_ref, "language form")
        self._senses = _index(senses, lambda item: item.sense_ref, "lexical sense")
        self._links = _index(links, lambda item: item.link_ref, "form-sense link")
        self._constructions = _index(constructions, lambda item: item.construction_ref, "construction")
        self._lexemes = _index(lexemes, lambda item: item.lexeme_ref, "lexeme")
        self._form_lexeme_links = _index(form_lexeme_links, lambda item: item.link_ref, "form-lexeme link")
        self._lexeme_sense_links = _index(lexeme_sense_links, lambda item: item.link_ref, "lexeme-sense link")
        self._contribution_specs = _index(contribution_specs, lambda item: item.spec_ref, "semantic contribution spec")
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
        self._lexeme_links_by_form: dict[tuple[str, int], list[FormLexemeLinkRecord]] = defaultdict(list)
        for item in self.active_form_lexeme_links():
            self._lexeme_links_by_form[(item.form_ref, item.form_revision)].append(item)
        for values in self._lexeme_links_by_form.values():
            values.sort(key=lambda item: (-item.prior_weight, item.lexeme_ref, item.revision))
        self._sense_links_by_lexeme: dict[tuple[str, int], list[LexemeSenseLinkRecord]] = defaultdict(list)
        for item in self.active_lexeme_sense_links():
            self._sense_links_by_lexeme[(item.lexeme_ref, item.lexeme_revision)].append(item)
        for values in self._sense_links_by_lexeme.values():
            values.sort(key=lambda item: (-item.prior_weight, item.sense_ref, item.revision))
        self._contributions_by_sense: dict[tuple[str, int], list[SemanticContributionSpecRecord]] = defaultdict(list)
        for item in self.active_contribution_specs():
            if item.executable:
                self._contributions_by_sense[(item.sense_ref, item.sense_revision)].append(item)
        for values in self._contributions_by_sense.values():
            values.sort(key=lambda item: (item.contribution_kind.value, item.spec_ref, item.revision))

    def _validate(self) -> None:
        for label, index in (
            ("language pack", self._packs), ("language form", self._forms),
            ("lexical sense", self._senses), ("form-sense link", self._links),
            ("construction", self._constructions),
            ("lexeme", self._lexemes),
            ("form-lexeme link", self._form_lexeme_links),
            ("lexeme-sense link", self._lexeme_sense_links),
            ("semantic contribution spec", self._contribution_specs),
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
            if sense.lifecycle_status in _ACTIVE and sense.target_ref is None:
                executable = [
                    item for item in self.iter_contribution_specs()
                    if item.sense_ref == sense.sense_ref and item.sense_revision == sense.revision
                    and item.executable
                    and item.use_operation in {UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY}
                ]
                if not executable:
                    raise LanguageRegistryError(f"active targetless sense lacks contribution authority: {sense.sense_ref}")
        for link in self.iter_links():
            form = self.require_form(link.form_ref, link.form_revision)
            sense = self.require_sense(link.sense_ref, link.sense_revision)
            if form.pack_ref != sense.pack_ref:
                raise LanguageRegistryError(f"form-sense link crosses packs: {link.link_ref}")
            if link.lifecycle_status in _ACTIVE and (
                form.lifecycle_status not in _ACTIVE or sense.lifecycle_status not in _ACTIVE
            ):
                raise LanguageRegistryError(f"active link references inactive record: {link.link_ref}")
        for lexeme in self.iter_lexemes():
            pack = self.require_pack(lexeme.pack_ref, lexeme.pack_revision)
            lemma = self.require_form(lexeme.lemma_form_ref, lexeme.lemma_form_revision)
            if lemma.pack_ref != lexeme.pack_ref:
                raise LanguageRegistryError(f"lexeme lemma crosses language packs: {lexeme.lexeme_ref}")
            if lexeme.lifecycle_status in _ACTIVE and pack.lifecycle_status not in _ACTIVE:
                raise LanguageRegistryError(f"active lexeme uses inactive pack: {lexeme.lexeme_ref}")
        for link in self.iter_form_lexeme_links():
            form = self.require_form(link.form_ref, link.form_revision)
            lexeme = self.require_lexeme(link.lexeme_ref, link.lexeme_revision)
            if form.pack_ref != lexeme.pack_ref:
                raise LanguageRegistryError(f"form-lexeme link crosses packs: {link.link_ref}")
            if link.lifecycle_status in _ACTIVE and (
                form.lifecycle_status not in _ACTIVE or lexeme.lifecycle_status not in _ACTIVE
            ):
                raise LanguageRegistryError(f"active form-lexeme link references inactive record: {link.link_ref}")
        for link in self.iter_lexeme_sense_links():
            lexeme = self.require_lexeme(link.lexeme_ref, link.lexeme_revision)
            sense = self.require_sense(link.sense_ref, link.sense_revision)
            if lexeme.pack_ref != sense.pack_ref:
                raise LanguageRegistryError(f"lexeme-sense link crosses packs: {link.link_ref}")
            if link.lifecycle_status in _ACTIVE and (
                lexeme.lifecycle_status not in _ACTIVE or sense.lifecycle_status not in _ACTIVE
            ):
                raise LanguageRegistryError(f"active lexeme-sense link references inactive record: {link.link_ref}")
        for spec in self.iter_contribution_specs():
            pack = self.require_pack(spec.pack_ref, spec.pack_revision)
            sense = self.require_sense(spec.sense_ref, spec.sense_revision)
            if sense.pack_ref != spec.pack_ref:
                raise LanguageRegistryError(f"contribution spec crosses packs: {spec.spec_ref}")
            if spec.lifecycle_status in _ACTIVE and (
                pack.lifecycle_status not in _ACTIVE or sense.lifecycle_status not in _ACTIVE
            ):
                raise LanguageRegistryError(f"active contribution spec references inactive authority: {spec.spec_ref}")
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
            lexemes=tuple(self.iter_lexemes()),
            form_lexeme_links=tuple(self.iter_form_lexeme_links()),
            lexeme_sense_links=tuple(self.iter_lexeme_sense_links()),
            contribution_specs=tuple(self.iter_contribution_specs()),
        )

    def iter_packs(self): return _flatten(self._packs)
    def iter_forms(self): return _flatten(self._forms)
    def iter_senses(self): return _flatten(self._senses)
    def iter_links(self): return _flatten(self._links)
    def iter_constructions(self): return _flatten(self._constructions)
    def iter_lexemes(self): return _flatten(self._lexemes)
    def iter_form_lexeme_links(self): return _flatten(self._form_lexeme_links)
    def iter_lexeme_sense_links(self): return _flatten(self._lexeme_sense_links)
    def iter_contribution_specs(self): return _flatten(self._contribution_specs)

    def active_packs(self): return _effective_flatten(self._packs)
    def active_forms(self): return _effective_flatten(self._forms)
    def active_senses(self): return _effective_flatten(self._senses)
    def active_links(self): return _effective_flatten(self._links)
    def active_constructions(self): return _effective_flatten(self._constructions)
    def active_lexemes(self): return _effective_flatten(self._lexemes)
    def active_form_lexeme_links(self): return _effective_flatten(self._form_lexeme_links)
    def active_lexeme_sense_links(self): return _effective_flatten(self._lexeme_sense_links)
    def active_contribution_specs(self): return _effective_flatten(self._contribution_specs)

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
    def require_lexeme(self, ref: str, revision: int | None = None) -> LexemeRecord:
        return _require(self._lexemes, ref, revision, "lexeme")
    def require_form_lexeme_link(self, ref: str, revision: int | None = None) -> FormLexemeLinkRecord:
        return _require(self._form_lexeme_links, ref, revision, "form-lexeme link")
    def require_lexeme_sense_link(self, ref: str, revision: int | None = None) -> LexemeSenseLinkRecord:
        return _require(self._lexeme_sense_links, ref, revision, "lexeme-sense link")
    def require_contribution_spec(self, ref: str, revision: int | None = None) -> SemanticContributionSpecRecord:
        return _require(self._contribution_specs, ref, revision, "semantic contribution spec")

    def pack_for_language(self, language_tag: str) -> LanguagePackRecord | None:
        candidates = [item for item in self.active_packs() if item.language_tag == language_tag]
        return max(candidates, key=lambda item: item.revision) if candidates else None

    def forms_for(self, language_tag: str, normalized_form: str) -> tuple[LanguageFormRecord, ...]:
        return tuple(self._forms_by_key.get((language_tag, normalized_form), ()))

    def normalization_forms_for(self, language_tag: str, observed_key: str) -> tuple[LanguageFormRecord, ...]:
        return tuple(self._normalization_index.get((language_tag, observed_key), ()))

    def links_for_form(self, form_ref: str, revision: int) -> tuple[FormSenseLinkRecord, ...]:
        return tuple(self._links_by_form.get((form_ref, revision), ()))

    def lexeme_links_for_form(self, form_ref: str, revision: int) -> tuple[FormLexemeLinkRecord, ...]:
        return tuple(self._lexeme_links_by_form.get((form_ref, revision), ()))

    def sense_links_for_lexeme(self, lexeme_ref: str, revision: int) -> tuple[LexemeSenseLinkRecord, ...]:
        return tuple(self._sense_links_by_lexeme.get((lexeme_ref, revision), ()))

    def contribution_specs_for_sense(self, sense_ref: str, revision: int) -> tuple[SemanticContributionSpecRecord, ...]:
        return tuple(self._contributions_by_sense.get((sense_ref, revision), ()))


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
