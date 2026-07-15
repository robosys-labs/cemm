"""Canonical v3.4 runtime package and verified competence evidence loading.

The base v3.4.3 package is treated as the already-audited canonical authority.
Runtime extensions are not authorized merely because they declare competence or
round-trip references.  Their references are enabled only by a verification
artifact tied to both the package fingerprint and the executable acceptance
suite.  A narrowly scoped bootstrap mode exists solely for generating that
artifact in an isolated test subprocess.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .v343 import V343BootPackage, load_v343_package
from ...language.merge import merge_semantic_language_packs
from ...language.semantic_pack import SemanticLanguagePack
from ..schema.foundation_contract import FoundationRegistry


_RUNTIME_EVIDENCE_ENV = "CEMM_VERIFY_RUNTIME_EVIDENCE"
_RUNTIME_EVIDENCE_RELATIVE_PATH = Path(
    "runtime_evidence/v343_runtime_verified.json"
)
_RUNTIME_TEST_RELATIVE_PATH = Path(
    "tests/architecture/test_v343_runtime_regressions.py"
)


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
    """Return audited base evidence plus verified runtime-extension evidence."""
    base = load_v343_package(data_root)
    base_evidence = _collect_package_evidence(base)
    declared_runtime = collect_declared_runtime_extension_evidence(
        data_root,
        package,
    )

    if os.environ.get(_RUNTIME_EVIDENCE_ENV) == "1":
        # This mode is consumed only by verify_runtime_cases.py in a subprocess.
        # It must never be used as a production configuration.
        runtime_evidence = declared_runtime
    else:
        runtime_evidence = _load_verified_runtime_evidence(
            data_root,
            package,
            declared_runtime,
        )

    foundation_active = _foundation_contract_refs(data_root)
    return RuntimeEmissionEvidence(
        active_schema_refs=frozenset((
            *foundation_active,
            *base_evidence.active_schema_refs,
            *runtime_evidence.active_schema_refs,
        )),
        competence_case_refs=frozenset((
            *base_evidence.competence_case_refs,
            *runtime_evidence.competence_case_refs,
        )),
        round_trip_case_refs=frozenset((
            *base_evidence.round_trip_case_refs,
            *runtime_evidence.round_trip_case_refs,
        )),
    )


def collect_declared_runtime_extension_evidence(
    data_root: Path,
    package: V343BootPackage | None = None,
) -> RuntimeEmissionEvidence:
    """Collect candidate refs from extension files for isolated verification.

    Returning these refs is not authorization. Production loading consumes only
    the subset recorded by a matching verification artifact.
    """
    del package  # the extension files themselves are the candidate authority
    active: set[str] = set()
    competence: set[str] = set()
    round_trip: set[str] = set()
    language_root = data_root / "languages"
    for runtime_root in sorted(language_root.glob("*/v343_runtime")):
        semantic_pack = SemanticLanguagePack.load(runtime_root)
        evidence = _collect_semantic_pack_evidence(semantic_pack)
        active.update(evidence.active_schema_refs)
        competence.update(evidence.competence_case_refs)
        round_trip.update(evidence.round_trip_case_refs)
    return RuntimeEmissionEvidence(
        active_schema_refs=frozenset(active),
        competence_case_refs=frozenset(competence),
        round_trip_case_refs=frozenset(round_trip),
    )


def runtime_evidence_path(data_root: Path) -> Path:
    return data_root / _RUNTIME_EVIDENCE_RELATIVE_PATH


def runtime_test_path(data_root: Path) -> Path:
    return data_root.parent / _RUNTIME_TEST_RELATIVE_PATH


def runtime_test_fingerprint(data_root: Path) -> str:
    path = runtime_test_path(data_root)
    if not path.exists():
        raise RuntimeError(f"runtime acceptance suite missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_runtime_policies(data_root: Path) -> dict[str, Any]:
    path = data_root / "foundations" / "v343_runtime" / "runtime_policies.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return dict(raw)


def _load_verified_runtime_evidence(
    data_root: Path,
    package: V343BootPackage,
    declared: RuntimeEmissionEvidence,
) -> RuntimeEmissionEvidence:
    path = runtime_evidence_path(data_root)
    if not path.exists():
        raise RuntimeError(
            "runtime extension competence is unverified; run "
            "`python -m cemm.kernel.boot.verify_runtime_cases`"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("package_fingerprint") != package.fingerprint:
        raise RuntimeError(
            "runtime evidence is stale for the current package; rerun "
            "`python -m cemm.kernel.boot.verify_runtime_cases`"
        )
    if raw.get("acceptance_suite_fingerprint") != runtime_test_fingerprint(
        data_root
    ):
        raise RuntimeError(
            "runtime evidence was produced by a different acceptance suite; "
            "rerun `python -m cemm.kernel.boot.verify_runtime_cases`"
        )

    evidence = RuntimeEmissionEvidence(
        active_schema_refs=frozenset(raw.get("active_schema_refs", ())),
        competence_case_refs=frozenset(raw.get("competence_case_refs", ())),
        round_trip_case_refs=frozenset(raw.get("round_trip_case_refs", ())),
    )
    for label, values, candidates in (
        ("active", evidence.active_schema_refs, declared.active_schema_refs),
        (
            "competence",
            evidence.competence_case_refs,
            declared.competence_case_refs,
        ),
        (
            "round_trip",
            evidence.round_trip_case_refs,
            declared.round_trip_case_refs,
        ),
    ):
        unexpected = values - candidates
        if unexpected:
            raise RuntimeError(
                f"runtime evidence contains undeclared {label} refs: "
                + ", ".join(sorted(unexpected))
            )
    return evidence


def _collect_package_evidence(
    package: V343BootPackage,
) -> RuntimeEmissionEvidence:
    active: set[str] = set()
    competence: set[str] = set()
    round_trip: set[str] = set()
    for semantic_pack in package.language_packs.values():
        evidence = _collect_semantic_pack_evidence(semantic_pack)
        active.update(evidence.active_schema_refs)
        competence.update(evidence.competence_case_refs)
        round_trip.update(evidence.round_trip_case_refs)
    return RuntimeEmissionEvidence(
        active_schema_refs=frozenset(active),
        competence_case_refs=frozenset(competence),
        round_trip_case_refs=frozenset(round_trip),
    )


def _collect_semantic_pack_evidence(
    semantic_pack: SemanticLanguagePack,
) -> RuntimeEmissionEvidence:
    active: set[str] = set()
    competence: set[str] = set()
    round_trip: set[str] = set()
    for lexical in semantic_pack.input_lexicon:
        active.add(lexical.grounding_contract_ref)
        competence.update(lexical.competence_case_refs)
    for expansion in semantic_pack.token_expansions:
        competence.update(expansion.competence_case_refs)
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
        active_schema_refs=frozenset(value for value in active if value),
        competence_case_refs=frozenset(value for value in competence if value),
        round_trip_case_refs=frozenset(value for value in round_trip if value),
    )


def _foundation_contract_refs(data_root: Path) -> frozenset[str]:
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
    return frozenset(active)
