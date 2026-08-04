"""Tests for deterministic bootstrap episode generation.

The generator script produces a JSONL file with one episode per line. Each
episode records form lattice, orientation projection, action sequence,
rejected legal alternatives, coverage receipt, and authority/action hashes.
Two runs must produce byte-identical output.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
EPISODES_PATH = ROOT / "data" / "bootstrap" / "proposal_episodes.jsonl"
GENERATOR_SCRIPT = ROOT / "scripts" / "build_bootstrap_episodes.py"

# Seed categories that must be covered.
SEED_CATEGORIES = {
    "word-order",
    "synonym",
    "modality",
    "reference",
    "scope",
    "teaching",
    "query",
    "typed-gap",
}

# Required fields in each episode.
REQUIRED_FIELDS = {
    "surface",
    "seed_category",
    "form_lattice",
    "orientation",
    "action_sequence",
    "rejected_alternatives",
    "coverage_receipt",
    "authority_hash",
    "action_encoding_hash",
    "program_ref",
    "accepted",
}


# ---------------------------------------------------------------------------
# JSONL file existence and validity
# ---------------------------------------------------------------------------


def test_episodes_file_exists():
    """The generated JSONL file exists."""
    assert EPISODES_PATH.exists(), f"Missing {EPISODES_PATH}"


def test_episodes_file_is_valid_jsonl():
    """Each line of the JSONL file is valid JSON."""
    assert EPISODES_PATH.exists()
    lines = EPISODES_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0
    for line in lines:
        data = json.loads(line)
        assert isinstance(data, dict)


def test_each_episode_has_required_fields():
    """Each episode has all required fields."""
    assert EPISODES_PATH.exists()
    lines = EPISODES_PATH.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        data = json.loads(line)
        for field in REQUIRED_FIELDS:
            assert field in data, f"Episode missing field '{field}': {data}"


def test_episodes_cover_all_seed_categories():
    """Episodes cover word-order, synonym, modality, reference, scope,
    teaching, query, and typed-gap seeds."""
    assert EPISODES_PATH.exists()
    lines = EPISODES_PATH.read_text(encoding="utf-8").strip().splitlines()
    categories = set()
    for line in lines:
        data = json.loads(line)
        categories.add(data["seed_category"])
    for cat in SEED_CATEGORIES:
        assert cat in categories, f"Missing seed category '{cat}'"


# ---------------------------------------------------------------------------
# Accepted episodes have valid coverage and verification
# ---------------------------------------------------------------------------


def test_accepted_episodes_have_coverage_receipt():
    """Accepted episodes have a non-null coverage receipt."""
    assert EPISODES_PATH.exists()
    lines = EPISODES_PATH.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        data = json.loads(line)
        if data["accepted"]:
            assert data["coverage_receipt"] is not None
            assert data["program_ref"]
            assert data["action_encoding_hash"]


def test_episodes_have_authority_hash():
    """Each episode has a non-empty authority hash."""
    assert EPISODES_PATH.exists()
    lines = EPISODES_PATH.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        data = json.loads(line)
        assert data["authority_hash"]
        assert isinstance(data["authority_hash"], str)


# ---------------------------------------------------------------------------
# Determinism: two runs produce byte-identical output
# ---------------------------------------------------------------------------


def test_two_runs_produce_identical_output(tmp_path):
    """Two runs of the generator produce byte-identical output."""
    out1 = tmp_path / "run1.jsonl"
    out2 = tmp_path / "run2.jsonl"

    for out in [out1, out2]:
        subprocess.run(
            [sys.executable, str(GENERATOR_SCRIPT), "--output", str(out)],
            check=True,
            capture_output=True,
        )

    bytes1 = out1.read_bytes()
    bytes2 = out2.read_bytes()
    assert bytes1 == bytes2, "Two runs produced different output"


def test_generated_output_matches_committed_file(tmp_path):
    """The generator output matches the committed JSONL file."""
    out = tmp_path / "regenerated.jsonl"
    subprocess.run(
        [sys.executable, str(GENERATOR_SCRIPT), "--output", str(out)],
        check=True,
        capture_output=True,
    )
    committed = EPISODES_PATH.read_bytes()
    regenerated = out.read_bytes()
    assert committed == regenerated, "Generated output does not match committed file"
