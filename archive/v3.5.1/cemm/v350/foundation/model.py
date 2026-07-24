"""Phase-6 foundation contracts, audit records, and competence results."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class AuditSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class FoundationContract:
    contract_ref: str
    expected_type_parents: Mapping[str, tuple[str, ...]]
    expected_schema_parents: Mapping[str, tuple[str, ...]]
    required_schema_metadata: Mapping[str, Mapping[str, Any]]
    required_schema_groups: Mapping[str, tuple[str, ...]]
    required_entitlement_refs: tuple[str, ...]
    required_referent_refs: tuple[str, ...]
    required_capability_refs: tuple[str, ...]
    required_competence_case_refs: tuple[str, ...]
    expected_record_counts: Mapping[str, int]
    expected_source_record_fingerprint: str
    forbidden_domain_semantic_keys: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FoundationAuditIssue:
    severity: AuditSeverity
    code: str
    target_ref: str
    message: str


@dataclass(frozen=True, slots=True)
class FoundationAuditReport:
    contract_ref: str
    issues: tuple[FoundationAuditIssue, ...]
    record_count: int
    counts_by_kind: Mapping[str, int]
    manifest_fingerprint: str
    source_record_fingerprint: str

    @property
    def errors(self) -> tuple[FoundationAuditIssue, ...]:
        return tuple(item for item in self.issues if item.severity == AuditSeverity.ERROR)

    @property
    def warnings(self) -> tuple[FoundationAuditIssue, ...]:
        return tuple(item for item in self.issues if item.severity == AuditSeverity.WARNING)

    @property
    def valid(self) -> bool:
        return not self.errors

    def require_valid(self) -> None:
        if self.errors:
            detail = "; ".join(f"{item.code}:{item.target_ref}:{item.message}" for item in self.errors)
            raise FoundationContractError(detail)


class FoundationContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FoundationCompetenceCase:
    case_ref: str
    operation: str
    context_ref: str
    expected: Mapping[str, Any]
    subject_ref: str | None = None
    query: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FoundationCompetenceResult:
    case_ref: str
    operation: str
    passed: bool
    expected: Mapping[str, Any]
    observed: Mapping[str, Any]
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FoundationCompetenceReport:
    results: tuple[FoundationCompetenceResult, ...]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.results)

    @property
    def failed(self) -> tuple[FoundationCompetenceResult, ...]:
        return tuple(item for item in self.results if not item.passed)

    def require_passed(self) -> None:
        if self.failed:
            detail = "; ".join(
                f"{item.case_ref}:{','.join(item.errors) or 'expectation_mismatch'}"
                for item in self.failed
            )
            raise FoundationContractError(detail)
