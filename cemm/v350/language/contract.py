"""Review contract and audit for Phase-7 language evidence.

The audit freezes reviewed forms, senses, and constructions independently from
Phase-6 semantic foundation authority.  Phase-8 grounding competence is pinned
by the same package contract but does not create durable truth records.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..data import SourcePackageLoader
from ..schema.model import SchemaLifecycleStatus, canonical_data, semantic_fingerprint
from ..storage import RecordKind
from .model import ConstructionKind, ConstructionRecord, LexicalSenseRecord
from .registry import LanguageRegistry


@dataclass(frozen=True, slots=True)
class LanguageGroundingContract:
    contract_ref: str
    base_commit: str
    expected_record_counts: Mapping[str, int]
    expected_source_record_fingerprint: str
    required_language_tags: tuple[str, ...]
    required_construction_kinds: Mapping[str, tuple[str, ...]]
    required_semantic_targets: Mapping[str, tuple[str, ...]]
    required_competence_case_refs: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LanguageGroundingAuditReport:
    contract_ref: str
    valid: bool
    issues: tuple[str, ...]
    counts_by_kind: Mapping[str, int]
    source_record_fingerprint: str
    manifest_fingerprint: str


def load_language_grounding_contract(path: str | Path) -> LanguageGroundingContract:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("language-grounding contract must be a JSON object")
    return LanguageGroundingContract(
        contract_ref=str(payload["contract_ref"]),
        base_commit=str(payload["base_commit"]),
        expected_record_counts={str(key): int(value) for key, value in payload.get("expected_record_counts", {}).items()},
        expected_source_record_fingerprint=str(payload.get("expected_source_record_fingerprint", "")),
        required_language_tags=tuple(map(str, payload.get("required_language_tags", ()))),
        required_construction_kinds={
            str(key): tuple(map(str, values))
            for key, values in payload.get("required_construction_kinds", {}).items()
        },
        required_semantic_targets={
            str(key): tuple(map(str, values))
            for key, values in payload.get("required_semantic_targets", {}).items()
        },
        required_competence_case_refs=tuple(map(str, payload.get("required_competence_case_refs", ()))),
        metadata=dict(payload.get("metadata", {})),
    )


class LanguageGroundingPackageAuditor:
    def __init__(self, contract: LanguageGroundingContract):
        self.contract = contract

    def audit(self, package_root: str | Path) -> LanguageGroundingAuditReport:
        root = Path(package_root).resolve()
        loader = SourcePackageLoader(root)
        records = tuple(item for item in loader.load() if item.phase == 7)
        issues: list[str] = []
        counts = Counter(item.record_kind.value for item in records)
        expected = dict(self.contract.expected_record_counts)
        for kind in sorted(set(counts) | set(expected)):
            if counts.get(kind, 0) != expected.get(kind, 0):
                issues.append(f"record_count:{kind}:expected={expected.get(kind, 0)}:actual={counts.get(kind, 0)}")

        language_modules = tuple(item for item in loader.manifest.modules if item.phase == 7)
        if not language_modules:
            issues.append("manifest:no_phase7_modules")
        for module in language_modules:
            if module.authority_scope != "language_evidence":
                issues.append(f"manifest:scope:{module.module_ref}:{module.authority_scope}")

        metadata = dict(loader.manifest.metadata)
        required_metadata = {
            "language_phase": "7",
            "grounding_phase": "8",
            "language_grounding_contract_ref": self.contract.contract_ref,
            "language_grounding_base_commit": self.contract.base_commit,
        }
        try:
            current_phase = int(metadata.get("phase", 0))
        except (TypeError, ValueError):
            current_phase = 0
        if current_phase < 8:
            issues.append(f"manifest:phase:expected>=8:actual={metadata.get('phase')}")
        for key, value in required_metadata.items():
            if str(metadata.get(key)) != value:
                issues.append(f"manifest:{key}:expected={value}:actual={metadata.get(key)}")

        pinned = {
            "language_grounding_contract_sha256": root / "language_grounding_contract.json",
            "composition_competence_sha256": root / "competence" / "composition.jsonl",
            "multilingual_competence_sha256": root / "competence" / "multilingual.jsonl",
            "grounding_competence_sha256": root / "competence" / "grounding.jsonl",
        }
        for key, path in pinned.items():
            expected_hash = str(metadata.get(key) or "")
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if not expected_hash or expected_hash != actual_hash:
                issues.append(f"manifest_hash:{key}:expected={expected_hash}:actual={actual_hash}")

        packs = tuple(item.record for item in records if item.record_kind == RecordKind.LANGUAGE_PACK)
        forms = tuple(item.record for item in records if item.record_kind == RecordKind.LANGUAGE_FORM)
        senses = tuple(item.record for item in records if item.record_kind == RecordKind.LEXICAL_SENSE)
        links = tuple(item.record for item in records if item.record_kind == RecordKind.FORM_SENSE_LINK)
        constructions = tuple(item.record for item in records if item.record_kind == RecordKind.CONSTRUCTION)
        try:
            registry = LanguageRegistry(packs, forms, senses, links, constructions)
        except Exception as exc:
            issues.append(f"language_registry:{exc}")
            registry = None

        if registry is not None:
            actual_tags = {item.language_tag for item in registry.active_packs()}
            missing_tags = sorted(set(self.contract.required_language_tags) - actual_tags)
            if missing_tags:
                issues.append(f"language_tags:missing={missing_tags}")
            for tag, expected_kinds in sorted(self.contract.required_construction_kinds.items()):
                pack = registry.pack_for_language(tag)
                actual_kinds = {
                    item.construction_kind.value
                    for item in registry.active_constructions()
                    if pack is not None and item.pack_ref == pack.pack_ref
                }
                missing = sorted(set(expected_kinds) - actual_kinds)
                if missing:
                    issues.append(f"construction_kinds:{tag}:missing={missing}")
            for tag, expected_targets in sorted(self.contract.required_semantic_targets.items()):
                pack = registry.pack_for_language(tag)
                actual_targets = {
                    item.target_ref for item in registry.active_senses()
                    if pack is not None and item.pack_ref == pack.pack_ref
                }
                missing = sorted(set(expected_targets) - actual_targets)
                if missing:
                    issues.append(f"semantic_targets:{tag}:missing={missing}")
            for construction in registry.active_constructions():
                if construction.full_sentence_pattern and not (
                    construction.construction_kind == ConstructionKind.IDIOM and construction.genuine_idiom
                ):
                    issues.append(f"sentence_template:{construction.construction_ref}")
                if construction.construction_kind == ConstructionKind.ELLIPSIS and not construction.preserves_gap:
                    issues.append(f"ellipsis_without_gap:{construction.construction_ref}")
            for sense in registry.active_senses():
                if sense.target_kind.value != "structural" and sense.target_revision is None:
                    issues.append(f"unpinned_sense_target:{sense.sense_ref}")
                if sense.lifecycle_status not in {SchemaLifecycleStatus.ACTIVE, SchemaLifecycleStatus.COMPETENCE_VERIFIED}:
                    issues.append(f"inactive_effective_sense:{sense.sense_ref}")

        competence_refs = set()
        for relative in (
            "competence/composition.jsonl",
            "competence/multilingual.jsonl",
            "competence/grounding.jsonl",
        ):
            for raw in (root / relative).read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    competence_refs.add(str(json.loads(raw)["case_ref"]))
        missing_cases = sorted(set(self.contract.required_competence_case_refs) - competence_refs)
        if missing_cases:
            issues.append(f"competence_cases:missing={missing_cases}")

        source_fingerprint = semantic_fingerprint(
            "phase7-language-source-records",
            tuple(
                (item.record_kind.value, item.record_ref, item.revision, canonical_data(item.record))
                for item in records
            ),
            64,
        )
        if source_fingerprint != self.contract.expected_source_record_fingerprint:
            issues.append(
                "source_fingerprint:expected="
                f"{self.contract.expected_source_record_fingerprint}:actual={source_fingerprint}"
            )
        return LanguageGroundingAuditReport(
            contract_ref=self.contract.contract_ref,
            valid=not issues,
            issues=tuple(sorted(issues)),
            counts_by_kind=dict(sorted(counts.items())),
            source_record_fingerprint=source_fingerprint,
            manifest_fingerprint=loader.manifest.fingerprint,
        )
