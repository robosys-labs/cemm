"""Canonical v3.4.3 runtime package with audited extension composition."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .v343 import V343BootPackage, load_v343_package
from ...language.merge import merge_semantic_language_packs
from ...language.semantic_pack import SemanticLanguagePack
from ..schema.foundation_contract import FoundationRegistry


class CompositeFoundationRegistry:
    """Read-only composition of canonical and extension foundation contracts."""

    def __init__(
        self,
        base: FoundationRegistry,
        extension: FoundationRegistry,
    ) -> None:
        self._base = base
        self._extension = extension
        self.fingerprint = hashlib.sha256(
            f"{base.fingerprint}:{extension.fingerprint}".encode("utf-8")
        ).hexdigest()

    def predicate(self, key: str):
        return self._extension.predicate(key) or self._base.predicate(key)

    def boot_schema(self, key: str):
        return self._extension.boot_schema(key) or self._base.boot_schema(key)

    def validate(self) -> tuple[str, ...]:
        return (*self._base.validate(), *self._extension.validate())


@dataclass(frozen=True, slots=True)
class RuntimeEmissionEvidence:
    active_schema_refs: frozenset[str]
    competence_case_refs: frozenset[str]
    round_trip_case_refs: frozenset[str]


def load_v343_runtime_package(data_root: Path) -> V343BootPackage:
    base = load_v343_package(data_root)
    extension_root = data_root / "foundations" / "v343_runtime"
    foundation_extension = FoundationRegistry.load(extension_root)
    foundations = CompositeFoundationRegistry(
        base.foundations,
        foundation_extension,
    )
    failures = foundations.validate()
    if failures:
        raise RuntimeError(
            "runtime foundation validation failed: " + ";".join(failures)
        )

    packs: dict[str, SemanticLanguagePack] = {}
    for language_tag, pack in base.language_packs.items():
        runtime_root = data_root / "languages" / language_tag / "v343_runtime"
        if not runtime_root.exists():
            packs[language_tag] = pack
            continue
        packs[language_tag] = merge_semantic_language_packs(
            pack,
            SemanticLanguagePack.load(runtime_root),
        )

    fingerprint = (
        f"foundations={foundations.fingerprint};"
        + ";".join(
            f"{tag}={pack.fingerprint}"
            for tag, pack in sorted(packs.items())
        )
    )
    return V343BootPackage(
        foundations=foundations,  # structural registry protocol
        self_claim_authorizer=base.self_claim_authorizer,
        language_packs=packs,
        fingerprint=fingerprint,
    )


def collect_runtime_emission_evidence(
    data_root: Path,
    package: V343BootPackage,
) -> RuntimeEmissionEvidence:
    active: set[str] = set()
    for root in (
        data_root / "foundations" / "v343",
        data_root / "foundations" / "v343_runtime",
    ):
        for filename in ("predicates.json", "boot_schemas.json"):
            path = root / filename
            if not path.exists():
                continue
            for item in json.loads(path.read_text(encoding="utf-8")):
                contract_id = str(item.get("contract_id", ""))
                if contract_id:
                    active.add(contract_id)

    competence: set[str] = set()
    round_trip: set[str] = set()
    for semantic_pack in package.language_packs.values():
        for lexical in semantic_pack.input_lexicon:
            competence.update(lexical.competence_case_refs)
        for construction in semantic_pack.input_constructions:
            competence.update(construction.competence_case_refs)
            round_trip.update(construction.round_trip_case_refs)
        realization = semantic_pack.realization
        for lexical in realization.lexicalizations.values():
            active.add(lexical.grounding_contract_ref)
            competence.update(lexical.competence_case_refs)
            round_trip.update(lexical.round_trip_case_refs)
        for morpheme in realization.morphemes.values():
            competence.update(morpheme.competence_case_refs)
            round_trip.update(morpheme.round_trip_case_refs)
        for construction in realization.constructions:
            competence.update(construction.competence_case_refs)
            round_trip.update(construction.round_trip_case_refs)

    return RuntimeEmissionEvidence(
        active_schema_refs=frozenset(active),
        competence_case_refs=frozenset(competence),
        round_trip_case_refs=frozenset(round_trip),
    )


def load_runtime_policies(data_root: Path) -> dict[str, Any]:
    path = data_root / "foundations" / "v343_runtime" / "runtime_policies.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return dict(raw)
