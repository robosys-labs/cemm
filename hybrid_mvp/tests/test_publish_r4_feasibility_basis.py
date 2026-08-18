from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]
__cemm_test_inventory__ = {'tests/test_publish_r4_feasibility_basis.py::test_publisher_accepts_identical_frozen_identity_and_rejects_changed_identity': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:r4-feasibility-publisher-is-equal-only',
                                                                                                                               'diagnostic_role': 'phase',
                                                                                                                               'introduced_by_task': 'R4-Partition-Corrective-Task-4',
                                                                                                                               'source_ast_sha256': '18d18aac2f83d6d26b993d21b7131f704b06a75b9853022d7a74e9588551aa3b'}}


def test_publisher_accepts_identical_frozen_identity_and_rejects_changed_identity(tmp_path: Path) -> None:
    current = tmp_path / "current.json"
    candidate = tmp_path / "candidate.json"
    config = tmp_path / "config.json"
    current.write_bytes((ROOT / "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json").read_bytes())
    candidate.write_bytes(current.read_bytes())
    config.write_bytes((ROOT / "configs/r4_partitions.json").read_bytes())
    command = [sys.executable, str(ROOT / "scripts/publish_r4_feasibility_basis.py"), "--candidate", str(candidate), "--current", str(current), "--config", str(config)]
    ok = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    before = current.read_bytes()
    row = json.loads(candidate.read_text("utf-8"))
    row["feasibility_basis_ref"] = "r4_partition_feasibility_basis_v1:000000000000000000000000"
    candidate.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n", "utf-8")
    rejected = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert rejected.returncode == 3
    assert current.read_bytes() == before
