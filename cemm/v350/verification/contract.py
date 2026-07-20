"""Pinned Phase-12 cross-domain vertical-slice verification contract."""
from __future__ import annotations

from dataclasses import dataclass, field
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from ..data import SourcePackageLoader
from ..storage import RecordKind


@dataclass(frozen=True, slots=True)
class VerticalSliceContract:
    contract_ref: str
    repository_base_commit: str
    required_competence_case_refs: tuple[str, ...]
    minimum_full_path_packages: int
    invariants: Mapping[str, bool]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerticalSliceAuditReport:
    contract_ref: str
    valid: bool
    issues: tuple[str, ...]
    manifest_fingerprint: str
    full_path_package_count: int


def load_vertical_slice_contract(path: str | Path) -> VerticalSliceContract:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return VerticalSliceContract(
        contract_ref=str(data["contract_ref"]),
        repository_base_commit=str(data["repository_base_commit"]),
        required_competence_case_refs=tuple(map(str, data.get("required_competence_case_refs", ()))),
        minimum_full_path_packages=int(data.get("minimum_full_path_packages", 3)),
        invariants={str(key): bool(value) for key, value in data.get("invariants", {}).items()},
        metadata=dict(data.get("metadata", {})),
    )


class VerticalSlicePackageAuditor:
    """Prove Phase 12 remains verification authority, not hidden ontology authority."""

    KERNEL_DIRS = ("grounding", "composition", "epistemics", "transitions")

    def __init__(self, contract: VerticalSliceContract) -> None:
        self.contract = contract

    def audit(self, package_root: str | Path, *, runtime_root: str | Path | None = None) -> VerticalSliceAuditReport:
        root = Path(package_root).resolve()
        loader = SourcePackageLoader(root)
        metadata = dict(loader.manifest.metadata)
        issues: list[str] = []
        try:
            phase = int(metadata.get("phase", 0))
        except (TypeError, ValueError):
            phase = 0
        if phase < 12:
            issues.append(f"manifest:phase:expected>=12:actual={metadata.get('phase')}")
        expected_metadata = {
            "vertical_slice_phase": "12",
            "vertical_slice_contract_ref": self.contract.contract_ref,
            "vertical_slice_base_commit": self.contract.repository_base_commit,
        }
        for key, expected in expected_metadata.items():
            if str(metadata.get(key)) != expected:
                issues.append(f"manifest:{key}:expected={expected}:actual={metadata.get(key)}")
        for key, path in {
            "vertical_slice_contract_sha256": root / "vertical_slice_contract.json",
            "vertical_slice_competence_sha256": root / "competence" / "transition_vertical_slices.jsonl",
        }.items():
            expected = str(metadata.get(key) or "")
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if not expected or expected != actual:
                issues.append(f"manifest_hash:{key}:expected={expected}:actual={actual}")

        records = loader.load()
        transition_seed = [
            item for item in records
            if item.record_kind in {RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY}
            and item.phase <= 12
        ]
        if transition_seed:
            issues.append(
                "phase12_canonical_transition_seed_must_remain_empty:"
                + str([(item.record_kind.value, item.record_ref) for item in transition_seed])
            )
        phase12_modules = [
            item.module_ref for item in loader.manifest.modules
            if item.phase == 12 and item.authority_scope not in {"verification_only", "competence_only"}
        ]
        if phase12_modules:
            issues.append(f"phase12_semantic_authority_modules_forbidden:{phase12_modules}")

        cases_path = root / "competence" / "transition_vertical_slices.jsonl"
        cases = tuple(
            json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ) if cases_path.is_file() else ()
        case_refs = {str(case["case_ref"]) for case in cases}
        required = set(self.contract.required_competence_case_refs)
        missing = sorted(required - case_refs)
        extra = sorted(case_refs - required)
        if missing:
            issues.append(f"competence_cases:missing={missing}")
        if extra:
            issues.append(f"competence_cases:unreviewed={extra}")
        full_packages = {
            str(case["package_ref"])
            for case in cases
            if case.get("operation") in {"full_slice", "context_isolation"}
            and case.get("package_ref")
        }
        if len(full_packages) < self.contract.minimum_full_path_packages:
            issues.append(
                f"full_path_packages:expected>={self.contract.minimum_full_path_packages}:actual={len(full_packages)}"
            )
        for name, enabled in sorted(self.contract.invariants.items()):
            if not enabled:
                issues.append(f"invariant_disabled:{name}")

        # Synthetic semantic names/forms live in competence data only.  Seeing
        # one in semantic kernel code would prove a fixture leaked into authority.
        if runtime_root is not None:
            runtime = Path(runtime_root).resolve()
            forbidden_tokens: set[str] = set()
            for case in cases:
                if case.get("lexeme"):
                    forbidden_tokens.add(str(case["lexeme"]))
                if case.get("package_ref"):
                    forbidden_tokens.add(str(case["package_ref"]))
                for side in ("left", "right"):
                    item = case.get(side)
                    if isinstance(item, dict):
                        if item.get("lexeme"):
                            forbidden_tokens.add(str(item["lexeme"]))
                        if item.get("package_ref"):
                            forbidden_tokens.add(str(item["package_ref"]))
            for directory in self.KERNEL_DIRS:
                for path in sorted((runtime / directory).rglob("*.py")):
                    literals = _executable_string_literals(path)
                    leaked = sorted(
                        token for token in forbidden_tokens
                        if token and any(_semantic_token_occurs(token, literal) for literal in literals)
                    )
                    if leaked:
                        issues.append(f"competence_fixture_leaked_into_kernel:{directory}/{path.name}:{leaked}")

        return VerticalSliceAuditReport(
            self.contract.contract_ref,
            not issues,
            tuple(sorted(issues)),
            loader.manifest.fingerprint,
            len(full_packages),
        )


def _semantic_token_occurs(token: str, literal: str) -> bool:
    """Detect fixture tokens in executable literals without substring false positives."""
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", literal) is not None


def _executable_string_literals(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docstring_nodes.add(id(first.value))
    return tuple(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstring_nodes
    )
