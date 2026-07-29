from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from cemm import web_demo


ROOT = Path(__file__).resolve().parents[1]


def test_final_contract_accepts_active_abi7_artifacts():
    completed = subprocess.run(
        [sys.executable, "tools/check_v1_final_contract.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "FINAL V1 CONTRACT: PASSED" in completed.stdout


def test_web_health_reports_the_active_abi7_contract():
    web_demo._runtime = None
    web_demo._store = None
    web_demo._config = None
    web_demo._activation = None
    web_demo._db_path = ":memory:"
    web_demo._pack_path = str(ROOT / "cemm" / "language_packs" / "en.json")
    web_demo._data_files = [
        str(ROOT / "cemm" / "data" / "base.json"),
        str(ROOT / "cemm" / "data" / "conversation_foundation.json"),
    ]

    health = asyncio.run(web_demo.health())

    assert health["ok"] is True
    assert health["coverage_abi"] == 7
    assert health["feature_algebra_version"] == 7
    assert health["form_pack_version"] == 7


def test_active_tooling_has_no_standalone_v6_migration():
    assert not (ROOT / "tools" / "migrate_en_seed_v6.py").exists()
    assert not (ROOT / "tools" / "generate_en_form_pack.py").exists()


def test_abi7_web_runtime_realizes_core_demo_responses():
    web_demo._runtime = None
    web_demo._store = None
    web_demo._config = None
    web_demo._activation = None
    web_demo._db_path = ":memory:"
    web_demo._pack_path = str(ROOT / "cemm" / "language_packs" / "en.json")
    web_demo._data_files = [
        str(ROOT / "cemm" / "data" / "base.json"),
        str(ROOT / "cemm" / "data" / "conversation_foundation.json"),
    ]

    runtime = web_demo._ensure_runtime()
    outcomes = {
        "hi": runtime.process("hi", mode="read_only"),
        "capabilities": runtime.process("what can you do?", mode="read_only"),
        "designation": runtime.process("my name is Chibueze", mode="read_only"),
        "system_name": runtime.process("what is your name?", mode="read_only"),
    }

    assert outcomes["hi"]["response"]
    assert outcomes["capabilities"]["response"] == "I can use digital agent."
    assert outcomes["designation"]["response"] == "Understood."
    assert outcomes["system_name"]["response"] == "My name is CEMM."
