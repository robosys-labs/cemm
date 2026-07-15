"""Merge audited v3.4.3 semantic language-pack fragments.

The runtime pack and its extension remain data-only authorities.  This module
only merges records by stable schema identity; it does not interpret words or
select dialogue behavior.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from typing import TypeVar

from .semantic_pack import SemanticLanguagePack
from ..kernel.schema.lexicalization import LanguageRealizationPack


T = TypeVar("T")


def _merge_by(
    base: Iterable[T],
    extension: Iterable[T],
    key: Callable[[T], str],
) -> tuple[T, ...]:
    merged: dict[str, T] = {key(item): item for item in base}
    merged.update({key(item): item for item in extension})
    return tuple(merged.values())


def merge_realization_packs(
    base: LanguageRealizationPack,
    extension: LanguageRealizationPack,
) -> LanguageRealizationPack:
    if base.language_tag != extension.language_tag:
        raise ValueError(
            "cannot merge realization packs for different languages: "
            f"{base.language_tag!r} != {extension.language_tag!r}"
        )

    lexicalizations = _merge_by(
        base.lexicalizations.values(),
        extension.lexicalizations.values(),
        lambda item: item.schema_id,
    )
    morphemes = _merge_by(
        base.morphemes.values(),
        extension.morphemes.values(),
        lambda item: item.schema_id,
    )
    constructions = _merge_by(
        base.constructions,
        extension.constructions,
        lambda item: item.schema_id,
    )
    fingerprint = hashlib.sha256(
        f"{base.fingerprint}:{extension.fingerprint}".encode("utf-8")
    ).hexdigest()
    pack = LanguageRealizationPack(
        language_tag=base.language_tag,
        lexicalizations=lexicalizations,
        morphemes=morphemes,
        constructions=constructions,
        referring_expressions={
            **base.referring_expressions,
            **extension.referring_expressions,
        },
        fingerprint=fingerprint,
    )
    failures = pack.validate()
    if failures:
        raise ValueError(
            f"invalid merged realization pack {base.language_tag}: "
            + "; ".join(failures)
        )
    return pack


def merge_semantic_language_packs(
    base: SemanticLanguagePack,
    extension: SemanticLanguagePack,
) -> SemanticLanguagePack:
    if base.language_tag != extension.language_tag:
        raise ValueError(
            "cannot merge semantic packs for different languages: "
            f"{base.language_tag!r} != {extension.language_tag!r}"
        )

    fingerprint = hashlib.sha256(
        f"{base.fingerprint}:{extension.fingerprint}".encode("utf-8")
    ).hexdigest()
    pack = SemanticLanguagePack(
        language_tag=base.language_tag,
        input_lexicon=_merge_by(
            base.input_lexicon,
            extension.input_lexicon,
            lambda item: item.mapping_id,
        ),
        input_constructions=_merge_by(
            base.input_constructions,
            extension.input_constructions,
            lambda item: item.schema_id,
        ),
        token_expansions=_merge_by(
            base.token_expansions,
            extension.token_expansions,
            lambda item: item.expansion_id,
        ),
        realization=merge_realization_packs(
            base.realization,
            extension.realization,
        ),
        fingerprint=fingerprint,
    )
    failures = pack.validate()
    if failures:
        raise ValueError(
            f"invalid merged semantic pack {base.language_tag}: "
            + "; ".join(failures)
        )
    return pack
