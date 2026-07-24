"""Pinned review contract for Phase-9 factor-graph UOL composition."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..data import SourcePackageLoader


@dataclass(frozen=True, slots=True)
class CompositionContract:
    contract_ref: str
    repository_base_commit: str
    required_variable_kinds: tuple[str, ...]
    required_hard_factor_kinds: tuple[str, ...]
    required_competence_case_refs: tuple[str, ...]
    invariants: Mapping[str, bool]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompositionAuditReport:
    contract_ref: str
    valid: bool
    issues: tuple[str, ...]
    manifest_fingerprint: str


def load_composition_contract(path: str | Path) -> CompositionContract:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return CompositionContract(
        contract_ref=str(payload["contract_ref"]),
        repository_base_commit=str(payload["repository_base_commit"]),
        required_variable_kinds=tuple(map(str, payload.get("required_variable_kinds", ()))),
        required_hard_factor_kinds=tuple(map(str, payload.get("required_hard_factor_kinds", ()))),
        required_competence_case_refs=tuple(map(str, payload.get("required_competence_case_refs", ()))),
        invariants={str(key): bool(value) for key, value in payload.get("invariants", {}).items()},
        metadata=dict(payload.get("metadata", {})),
    )


class CompositionPackageAuditor:
    def __init__(self, contract: CompositionContract) -> None:
        self.contract = contract

    def audit(self, package_root: str | Path) -> CompositionAuditReport:
        root = Path(package_root).resolve()
        loader = SourcePackageLoader(root)
        metadata = dict(loader.manifest.metadata)
        issues = []
        try:
            current_phase = int(metadata.get("phase", 0))
        except (TypeError, ValueError):
            current_phase = 0
        if current_phase < 9:
            issues.append(f"manifest:phase:expected>=9:actual={metadata.get('phase')}")
        required = {
            "composition_phase": "9",
            "composition_contract_ref": self.contract.contract_ref,
            "composition_base_commit": self.contract.repository_base_commit,
        }
        for key, value in required.items():
            if str(metadata.get(key)) != value:
                issues.append(f"manifest:{key}:expected={value}:actual={metadata.get(key)}")
        pinned = {
            "composition_contract_sha256": root / "composition_contract.json",
            "meaning_composition_competence_sha256": root / "competence" / "meaning_composition.jsonl",
        }
        for key, path in pinned.items():
            expected = str(metadata.get(key) or "")
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if not expected or expected != actual:
                issues.append(f"manifest_hash:{key}:expected={expected}:actual={actual}")

        case_refs = set()
        path = root / "competence" / "meaning_composition.jsonl"
        if path.is_file():
            for raw in path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    case_refs.add(str(json.loads(raw)["case_ref"]))
        missing = sorted(set(self.contract.required_competence_case_refs) - case_refs)
        if missing:
            issues.append(f"competence_cases:missing={missing}")

        # The contract must explicitly keep all safety boundaries enabled.
        for name, enabled in sorted(self.contract.invariants.items()):
            if not enabled:
                issues.append(f"invariant_disabled:{name}")
        return CompositionAuditReport(
            contract_ref=self.contract.contract_ref,
            valid=not issues,
            issues=tuple(sorted(issues)),
            manifest_fingerprint=loader.manifest.fingerprint,
        )
