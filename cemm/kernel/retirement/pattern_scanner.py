"""ForbiddenPatternScanner — detects forbidden implementation patterns.

Import boundary: standard library only.

Architectural guardrails (AGENTS.md §23, IMPLEMENTATION_PLAN.md Phase 12):
Forbidden patterns to detect in canonical kernel modules:
- ActionOperatorSchema as competing verb authority
- SessionLearningOverlay
- graph-build-time effects (executing predicted effects while building graph)
- runtime-local query/write authorities
- static capability responder
- hard-coded role loops (hard-code universal role names in graph builder)
- run old and new pipelines in parallel
- call shadow code complete
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Forbidden patterns to scan for in canonical kernel source
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    # ActionOperatorSchema as competing verb authority
    ("ActionOperatorSchema", "action_operator_competing_authority"),
    ("ActionOperatorRegistry", "action_operator_competing_authority"),
    ("action_operators", "action_operator_competing_authority"),

    # SessionLearningOverlay
    ("SessionLearningOverlay", "session_learning_overlay"),
    ("session_learning_overlay", "session_learning_overlay"),

    # graph-build-time effects
    ("execute.*effect.*build", "graph_build_time_effect"),
    ("fire.*effect.*graph", "graph_build_time_effect"),
    ("_fire_effect", "graph_build_time_effect"),

    # runtime-local query/write authorities
    ("runtime.*query.*authority", "runtime_local_authority"),
    ("runtime.*write.*authority", "runtime_local_authority"),

    # static capability responder
    ("static.*capability.*responder", "static_capability_responder"),
    ("_canned_response", "static_capability_responder"),
    ("canned.*responder", "static_capability_responder"),

    # hard-coded universal role names
    ('"actor"', "hardcoded_role_names"),
    ('"object"', "hardcoded_role_names"),
    ('"target"', "hardcoded_role_names"),
    ("'actor'", "hardcoded_role_names"),
    ("'object'", "hardcoded_role_names"),
    ("'target'", "hardcoded_role_names"),

    # parallel pipelines
    ("old.*pipeline.*new.*pipeline", "parallel_pipeline"),
    ("run.*parallel.*authoritative", "parallel_pipeline"),

    # shadow code
    ("shadow.*code.*complete", "shadow_code"),
)


@dataclass(frozen=True, slots=True)
class PatternViolation:
    """A forbidden pattern violation found in source code."""
    file_path: str
    line_number: int
    matched_pattern: str
    violation_kind: str
    line_content: str = ""


@dataclass(frozen=True, slots=True)
class PatternScanResult:
    """Result of scanning for forbidden patterns."""
    is_clean: bool
    violations: tuple[PatternViolation, ...] = ()
    files_scanned: int = 0


class ForbiddenPatternScanner:
    """Scans canonical kernel modules for forbidden implementation patterns.

    Do not:
    - add transcript phrases to query, write, capability, or response executors
    - learn into an overlay the ordinary schema resolver does not use
    - retain action and predicate schema stores as separate semantic authorities
    - execute predicted effects while building or interpreting a graph
    - hard-code universal role names in a graph builder
    - run the old and new pipelines in parallel
    - call shadow code complete
    """

    def scan_directory(self, directory: Path) -> PatternScanResult:
        """Scan canonical kernel modules for forbidden patterns.

        Scans both canonical kernel subdirectories and root-level kernel/*.py
        files, matching the coverage of ``LegacyImportGuard.scan_directory``.
        """
        from .legacy_guard import CANONICAL_KERNEL_PACKAGES

        violations: list[PatternViolation] = []
        files_scanned = 0

        # Scan canonical subpackages
        for pkg in CANONICAL_KERNEL_PACKAGES:
            pkg_dir = directory / pkg
            if not pkg_dir.is_dir():
                continue
            for py_file in pkg_dir.rglob("*.py"):
                if py_file.name.startswith("_debug") or py_file.name.startswith("_test"):
                    continue
                files_scanned += 1
                file_violations = self.scan_file(py_file)
                violations.extend(file_violations)

        # Scan root-level kernel/*.py files (not subdirectories)
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_debug") or py_file.name.startswith("_test"):
                continue
            files_scanned += 1
            file_violations = self.scan_file(py_file)
            violations.extend(file_violations)

        return PatternScanResult(
            is_clean=len(violations) == 0,
            violations=tuple(violations),
            files_scanned=files_scanned,
        )

    def scan_file(self, file_path: Path) -> tuple[PatternViolation, ...]:
        """Scan a single file for forbidden patterns."""
        violations: list[PatternViolation] = []

        try:
            source = file_path.read_text(encoding="utf-8")
        except Exception:
            return tuple()

        lines = source.splitlines()
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for pattern, kind in FORBIDDEN_PATTERNS:
                if re.search(pattern, stripped, re.IGNORECASE):
                    violations.append(PatternViolation(
                        file_path=str(file_path),
                        line_number=line_num,
                        matched_pattern=pattern,
                        violation_kind=kind,
                        line_content=stripped,
                    ))
                    break  # One violation per line

        return tuple(violations)

    def check_clean(self, directory: Path) -> bool:
        """Check that no forbidden patterns exist in canonical kernel."""
        result = self.scan_directory(directory)
        return result.is_clean
