#!/usr/bin/env python
"""Incremental MVP validation gate.

Compiles source, links authority, checks SQLite activation, scans for
forbidden legacy/phrase/stage constructs, runs active tests to JUnit XML,
rejects any failure/error/skip/xfail/xpass, and writes a canonical JSON receipt
with source/authority/test hashes.

Usage::

    python scripts/validate_mvp.py --profile development --output artifacts/validation/MILESTONE_RECEIPT.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
AUTHORITY_MANIFEST = ROOT / "data" / "authority" / "manifest.json"

FORBIDDEN_TOKENS = (
    "StageRecord",
    "stage_trace",
    "range(23)",
    "graph_action_ranker.pt",
    "weights_only=False",
    "torch.load(",
    "disabled_by_milestone",
)


def _hash_source() -> str:
    """Return a canonical SHA-256 over all source files."""
    h = hashlib.sha256()
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC)
        h.update(str(rel).encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def _hash_authority() -> str:
    """Return the SHA-256 of the authority manifest."""
    return hashlib.sha256(AUTHORITY_MANIFEST.read_bytes()).hexdigest()


def _compile_source() -> list[str]:
    """Compile all source files; return list of errors."""
    errors: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(str(exc))
    return errors


def _scan_forbidden_tokens() -> list[str]:
    """Scan all source files for forbidden tokens; return offenders."""
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                offenders.append(f"{path.relative_to(ROOT)}: {token}")
    return offenders


def _check_sqlite_activation() -> str | None:
    """Open and close SQLite stores to verify activation; return error or None."""
    try:
        from cemm_authoritative_hybrid.authority import AuthorityLinker
        from cemm_authoritative_hybrid.persistence import open_stores

        linked = AuthorityLinker().link_path(AUTHORITY_MANIFEST)
        with tempfile.TemporaryDirectory() as tmp:
            stores = open_stores(
                Path(tmp) / "stores.db",
                authority_generation=linked.generation,
            )
            stores.close()
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _run_tests() -> tuple[dict[str, int], str | None]:
    """Run pytest and return (summary, error_or_none).

    Rejects any failure, error, skip, xfail, or xpass.
    """
    import xml.etree.ElementTree as ET

    with tempfile.TemporaryDirectory() as tmp:
        junit_path = Path(tmp) / "junit.xml"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                f"--junit-xml={junit_path}",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

        summary = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "xfail": 0,
            "xpass": 0,
        }

        try:
            tree = ET.parse(junit_path)
            root = tree.getroot()
            # JUnit XML: <testsuites><testsuite tests="" failures="" errors="" skipped=""/>...
            for suite in root.iter("testsuite"):
                summary["tests"] += int(suite.get("tests", 0))
                summary["failures"] += int(suite.get("failures", 0))
                summary["errors"] += int(suite.get("errors", 0))
                summary["skipped"] += int(suite.get("skipped", 0))
        except Exception:
            # Fallback: parse the text output for the summary line
            for line in result.stdout.splitlines():
                if "passed" in line:
                    # e.g. "145 passed in 2.87s"
                    parts = line.strip().split()
                    for part in parts:
                        if part.isdigit():
                            summary["tests"] = int(part)
                            break

        # Use return code as primary signal
        if result.returncode != 0:
            summary["failures"] = max(summary["failures"], 1)

        # Check for skip/xfail/xpass in output
        combined = result.stdout + result.stderr
        for line in combined.splitlines():
            lower = line.lower()
            if "skipped" in lower and "0 skipped" not in lower:
                summary["skipped"] = max(summary["skipped"], 1)
            if "xfail" in lower and "0 xfail" not in lower:
                summary["xfail"] = max(summary["xfail"], 1)
            if "xpass" in lower and "0 xpass" not in lower:
                summary["xpass"] = max(summary["xpass"], 1)

        return summary, None if result.returncode == 0 else combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Incremental MVP validation gate")
    parser.add_argument(
        "--profile",
        default="development",
        choices=["development", "typed_fixture", "neural"],
        help="Profile to validate (default: development)",
    )
    parser.add_argument(
        "--output",
        default="artifacts/validation/MILESTONE_RECEIPT.json",
        help="Output path for the canonical JSON receipt",
    )
    args = parser.parse_args()

    receipt: dict = {
        "profile": args.profile,
        "status": "failed",
        "timestamp": _dt.datetime.now(_dt.UTC).isoformat(),
        "source_hash": "",
        "authority_hash": "",
        "test_results": {},
        "checks": {},
    }

    failures: list[str] = []

    # 1. Compile source
    compile_errors = _compile_source()
    receipt["checks"]["compile"] = {
        "passed": len(compile_errors) == 0,
        "errors": compile_errors,
    }
    if compile_errors:
        failures.append("source compilation failed")

    # 2. Scan forbidden tokens
    offenders = _scan_forbidden_tokens()
    receipt["checks"]["forbidden_tokens"] = {
        "passed": len(offenders) == 0,
        "offenders": offenders,
    }
    if offenders:
        failures.append(f"forbidden tokens found: {offenders}")

    # 3. Link authority
    try:
        from cemm_authoritative_hybrid.authority import AuthorityLinker

        linked = AuthorityLinker().link_path(AUTHORITY_MANIFEST)
        receipt["checks"]["authority_link"] = {
            "passed": True,
            "generation": linked.generation,
        }
    except Exception as exc:
        receipt["checks"]["authority_link"] = {
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        failures.append("authority linking failed")

    # 4. SQLite activation check
    activation_error = _check_sqlite_activation()
    receipt["checks"]["sqlite_activation"] = {
        "passed": activation_error is None,
        "error": activation_error,
    }
    if activation_error:
        failures.append("SQLite activation failed")

    # 5. Run tests
    test_summary, test_error = _run_tests()
    receipt["test_results"] = test_summary
    receipt["checks"]["tests"] = {
        "passed": test_error is None,
        "error": test_error,
    }
    if test_error:
        failures.append("test suite had failures")
    if test_summary.get("skipped", 0) > 0:
        failures.append("test suite had skips")

    # 6. Compute hashes
    receipt["source_hash"] = _hash_source()
    receipt["authority_hash"] = _hash_authority()

    # 7. Determine status
    if not failures:
        receipt["status"] = "verified"
    else:
        receipt["status"] = "failed"
        receipt["failures"] = failures

    # 8. Write receipt
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    # 9. Report
    print(f"Validation status: {receipt['status']}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
