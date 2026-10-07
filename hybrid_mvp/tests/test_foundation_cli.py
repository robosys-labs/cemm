"""Root-installed CLI must route to the six-phase foundation, not cemm v1."""
from pathlib import Path
import json
from cemm_authoritative_hybrid.foundation_cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_semantic_cli(capsys, tmp_path):
    result = main([
        "--root", str(ROOT),
        "--store", str(tmp_path / "cli.sqlite3"),
        "--session", "session:foundation-cli-test",
        "--text", "hello",
    ])
    out = capsys.readouterr().out
    doc = json.loads(out)
    assert result == 0
    assert doc["schema"] == "cemm-foundation-semantic-surface-v1"
    assert doc["kind"] == "response_meaning"
