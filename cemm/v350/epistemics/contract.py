"""Pinned Phase-10 claim/epistemic review contract."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ..data import SourcePackageLoader
from ..storage import RecordKind


@dataclass(frozen=True, slots=True)
class EpistemicContract:
    contract_ref: str
    repository_base_commit: str
    required_competence_case_refs: tuple[str, ...]
    required_record_kinds: tuple[str, ...]
    invariants: Mapping[str, bool]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EpistemicAuditReport:
    contract_ref: str
    valid: bool
    issues: tuple[str, ...]
    manifest_fingerprint: str


def load_epistemic_contract(path: str | Path) -> EpistemicContract:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return EpistemicContract(
        contract_ref=str(data["contract_ref"]),
        repository_base_commit=str(data["repository_base_commit"]),
        required_competence_case_refs=tuple(map(str, data.get("required_competence_case_refs", ()))),
        required_record_kinds=tuple(map(str, data.get("required_record_kinds", ()))),
        invariants={str(key): bool(value) for key, value in data.get("invariants", {}).items()},
        metadata=dict(data.get("metadata", {})),
    )


class EpistemicPackageAuditor:
    def __init__(self, contract: EpistemicContract) -> None:
        self.contract = contract

    def audit(self, package_root: str | Path) -> EpistemicAuditReport:
        root = Path(package_root).resolve()
        loader = SourcePackageLoader(root)
        metadata = dict(loader.manifest.metadata)
        issues: list[str] = []
        try:
            phase = int(metadata.get("phase", 0))
        except (TypeError, ValueError):
            phase = 0
        if phase < 10:
            issues.append(f"manifest:phase:expected>=10:actual={metadata.get('phase')}")
        expected = {
            "epistemic_phase": "10",
            "epistemic_contract_ref": self.contract.contract_ref,
            "epistemic_base_commit": self.contract.repository_base_commit,
        }
        for key, value in expected.items():
            if str(metadata.get(key)) != value:
                issues.append(f"manifest:{key}:expected={value}:actual={metadata.get(key)}")
        pins = {
            "epistemic_contract_sha256": root / "epistemic_contract.json",
            "epistemic_competence_sha256": root / "competence" / "epistemics.jsonl",
        }
        for key, path in pins.items():
            expected_hash = str(metadata.get(key) or "")
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if expected_hash != actual or not expected_hash:
                issues.append(f"manifest_hash:{key}:expected={expected_hash}:actual={actual}")
        cases = set()
        competence_path = root / "competence" / "epistemics.jsonl"
        if competence_path.is_file():
            for raw in competence_path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    cases.add(str(json.loads(raw)["case_ref"]))
        missing = sorted(set(self.contract.required_competence_case_refs) - cases)
        if missing:
            issues.append(f"competence_cases:missing={missing}")
        available_record_kinds = {item.value for item in RecordKind}
        missing_record_kinds = sorted(
            set(self.contract.required_record_kinds) - available_record_kinds
        )
        if missing_record_kinds:
            issues.append(f"record_kinds:missing={missing_record_kinds}")
        for name, enabled in sorted(self.contract.invariants.items()):
            if not enabled:
                issues.append(f"invariant_disabled:{name}")
        return EpistemicAuditReport(
            self.contract.contract_ref, not issues, tuple(sorted(issues)), loader.manifest.fingerprint
        )
