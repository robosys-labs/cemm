"""Generate proof that the runtime extension passes its executable acceptance suite."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from .v343_runtime import (
    _RUNTIME_EVIDENCE_ENV,
    collect_declared_runtime_extension_evidence,
    load_v343_runtime_package,
    runtime_evidence_path,
    runtime_test_fingerprint,
)
from ..data.loader import default_data_root


def main() -> int:
    data_root = default_data_root()
    repository_root = Path(__file__).resolve().parents[3]
    test_target = "cemm/tests/architecture/test_v343_runtime_regressions.py"
    artifact = runtime_evidence_path(data_root)
    artifact.parent.mkdir(parents=True, exist_ok=True)

    environment = dict(os.environ)
    environment[_RUNTIME_EVIDENCE_ENV] = "1"
    bootstrap = _run_tests(repository_root, test_target, environment)
    if bootstrap != 0:
        return bootstrap

    package = load_v343_runtime_package(data_root)
    evidence = collect_declared_runtime_extension_evidence(
        data_root,
        package,
    )
    payload = {
        "format_version": 1,
        "package_fingerprint": package.fingerprint,
        "acceptance_suite_fingerprint": runtime_test_fingerprint(data_root),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "validation_command": (
            f"{sys.executable} -m pytest -q {test_target}"
        ),
        "active_schema_refs": sorted(evidence.active_schema_refs),
        "competence_case_refs": sorted(evidence.competence_case_refs),
        "round_trip_case_refs": sorted(evidence.round_trip_case_refs),
    }
    temporary = artifact.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(artifact)

    production_environment = dict(os.environ)
    production_environment.pop(_RUNTIME_EVIDENCE_ENV, None)
    production = _run_tests(
        repository_root,
        test_target,
        production_environment,
    )
    if production != 0:
        artifact.unlink(missing_ok=True)
        return production

    print(f"runtime evidence written: {artifact}")
    return 0


def _run_tests(
    repository_root: Path,
    test_target: str,
    environment: dict[str, str],
) -> int:
    environment = dict(environment)
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            test_target,
        ],
        cwd=repository_root,
        env=environment,
        check=False,
    )
    return int(process.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
