"""Compatibility validation API backed by data-package validation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .v341 import _load

@dataclass(frozen=True, slots=True)
class V341FoundationValidationReport:
    ok: bool
    failures: tuple[str, ...] = ()
    fingerprint: str = ""

    def require_ok(self):
        if not self.ok:
            raise RuntimeError(
                "foundation validation failed: "
                + "; ".join(self.failures)
            )

def validate_v341_spec():
    loader, languages = _load()
    report = loader.validate(languages)
    return V341FoundationValidationReport(
        report.ok, report.failures, report.fingerprint
    )

def validate_registered_v341(store: Any):
    loader, languages = _load()
    report = loader.validate(languages)
    failures = list(report.failures)
    if report.ok:
        for item in (
            *loader.predicates,
            *loader.entity_kinds,
            *loader.state_dimensions,
        ):
            active = store.find_active(item["semantic_key"])
            if active is None:
                failures.append(
                    f"missing active schema: {item['semantic_key']}"
                )
            elif (
                not active.grounding_assessment_ref
                or not active.competence_assessment_ref
            ):
                failures.append(
                    f"schema lacks assessments: {item['semantic_key']}"
                )
    return V341FoundationValidationReport(
        not failures, tuple(failures), report.fingerprint
    )
