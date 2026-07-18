"""Pinned Phase-11 transition-engine review contract."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from ..data import SourceCompilationError, SourcePackageLoader
from ..storage import RecordKind

_NAMED_REF = re.compile(
    r"(?<![A-Za-z0-9_-])(?:type|event|action|state|property|relation|role|function):[A-Za-z][A-Za-z0-9_:-]*"
)


@dataclass(frozen=True, slots=True)
class TransitionContract:
    contract_ref: str
    repository_base_commit: str
    required_competence_case_refs: tuple[str, ...]
    required_record_kinds: tuple[str, ...]
    required_source_modules: tuple[str, ...]
    invariants: Mapping[str, bool]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransitionAuditReport:
    contract_ref: str
    valid: bool
    issues: tuple[str, ...]
    manifest_fingerprint: str


def load_transition_contract(path: str | Path) -> TransitionContract:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return TransitionContract(
        contract_ref=str(data["contract_ref"]),
        repository_base_commit=str(data["repository_base_commit"]),
        required_competence_case_refs=tuple(map(str, data.get("required_competence_case_refs", ()))),
        required_record_kinds=tuple(map(str, data.get("required_record_kinds", ()))),
        required_source_modules=tuple(map(str, data.get("required_source_modules", ()))),
        invariants={str(k): bool(v) for k, v in data.get("invariants", {}).items()},
        metadata=dict(data.get("metadata", {})),
    )


class TransitionPackageAuditor:
    def __init__(self, contract: TransitionContract) -> None:
        self.contract = contract

    def audit(self, package_root: str | Path, *, runtime_root: str | Path | None = None) -> TransitionAuditReport:
        root = Path(package_root).resolve()
        loader = SourcePackageLoader(root)
        metadata = dict(loader.manifest.metadata)
        issues: list[str] = []
        try:
            phase = int(metadata.get("phase", 0))
        except (TypeError, ValueError):
            phase = 0
        if phase < 11:
            issues.append(f"manifest:phase:expected>=11:actual={metadata.get('phase')}")
        for key, expected in {
            "transition_phase": "11",
            "transition_contract_ref": self.contract.contract_ref,
            "transition_base_commit": self.contract.repository_base_commit,
        }.items():
            if str(metadata.get(key)) != expected:
                issues.append(f"manifest:{key}:expected={expected}:actual={metadata.get(key)}")
        for key, path in {
            "transition_contract_sha256": root / "transition_contract.json",
            "transition_competence_sha256": root / "competence" / "transitions.jsonl",
        }.items():
            expected_hash = str(metadata.get(key) or "")
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if not expected_hash or expected_hash != actual:
                issues.append(f"manifest_hash:{key}:expected={expected_hash}:actual={actual}")

        module_map = {item.module_ref: item for item in loader.manifest.modules}
        for module_ref in self.contract.required_source_modules:
            module = module_map.get(module_ref)
            if module is None:
                issues.append(f"source_module:missing={module_ref}")
                continue
            if module.phase != 11 or module.authority_scope != "transition_authority" or not module.allow_empty:
                issues.append(f"source_module:invalid_contract={module_ref}")

        try:
            records = loader.load()
        except SourceCompilationError as exc:
            issues.append(f"source_load_error:{exc}")
            records = ()
        transition_seed = [
            item for item in records
            if item.record_kind in {RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY}
        ]
        if transition_seed:
            issues.append(
                "domain_transition_seed:expected=0:actual="
                + str([(item.record_kind.value, item.record_ref) for item in transition_seed])
            )

        cases: set[str] = set()
        competence_path = root / "competence" / "transitions.jsonl"
        if competence_path.is_file():
            for raw in competence_path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    cases.add(str(json.loads(raw)["case_ref"]))
        missing = sorted(set(self.contract.required_competence_case_refs) - cases)
        extra = sorted(cases - set(self.contract.required_competence_case_refs))
        if missing:
            issues.append(f"competence_cases:missing={missing}")
        if extra:
            issues.append(f"competence_cases:unreviewed={extra}")

        available = {item.value for item in RecordKind}
        missing_kinds = sorted(set(self.contract.required_record_kinds) - available)
        if missing_kinds:
            issues.append(f"record_kinds:missing={missing_kinds}")
        for name, enabled in sorted(self.contract.invariants.items()):
            if not enabled:
                issues.append(f"invariant_disabled:{name}")

        if runtime_root is not None:
            transition_root = Path(runtime_root).resolve() / "transitions"
            for path in sorted(transition_root.rglob("*.py")):
                if path.name == "contract.py":
                    continue
                text = path.read_text(encoding="utf-8")
                matches = sorted(set(_NAMED_REF.findall(text)))
                if matches:
                    issues.append(f"named_kernel_semantic_refs:{path.name}:{matches}")

        return TransitionAuditReport(
            self.contract.contract_ref,
            not issues,
            tuple(sorted(issues)),
            loader.manifest.fingerprint,
        )
