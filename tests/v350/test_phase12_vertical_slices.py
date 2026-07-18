from __future__ import annotations

import json
from pathlib import Path

from cemm.v350.data import DeterministicSQLiteCompiler, SourcePackageLoader
from cemm.v350.storage import RecordKind
from cemm.v350.verification import (
    TransitionSliceHarness, TransitionSliceResult, VerticalSlicePackageAuditor,
    load_vertical_slice_contract,
)
from cemm.v350.verification.contract import _executable_string_literals, _semantic_token_occurs

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"
RUNTIME = ROOT / "cemm" / "v350"


def _cases():
    return tuple(
        json.loads(line)
        for line in (SOURCE / "competence" / "transition_vertical_slices.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def test_phase12_contract_is_pinned_to_phase11_remote_base_and_audits_cleanly() -> None:
    contract = load_vertical_slice_contract(SOURCE / "vertical_slice_contract.json")
    assert contract.repository_base_commit == "735d13d11f112d0062972a9a66d59100fa8a406c"
    assert contract.minimum_full_path_packages >= 3
    report = VerticalSlicePackageAuditor(contract).audit(SOURCE, runtime_root=RUNTIME)
    assert report.valid, report.issues
    assert report.full_path_package_count >= contract.minimum_full_path_packages


def test_phase12_canonical_source_does_not_promote_competence_packages_to_boot_authority() -> None:
    records = SourcePackageLoader(SOURCE).load()
    assert not [
        item for item in records
        if item.record_kind in {RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY}
    ]
    assert all("phase12" not in item.record_ref for item in records)


def test_phase12_all_declarative_vertical_slice_cases_execute(tmp_path: Path) -> None:
    compiled = DeterministicSQLiteCompiler().compile(SOURCE, tmp_path / "phase12.sqlite", make_read_only=False)
    harness = TransitionSliceHarness(compiled.output_path)
    full_packages = set()
    for case in _cases():
        result = harness.run(case)
        if isinstance(result, TransitionSliceResult):
            if case["operation"] in {"full_slice", "context_isolation"}:
                full_packages.add(result.package_ref)
                assert result.grounding_selected
                assert result.composed_schema_ref is not None
            if result.committed:
                assert result.restart_verified
                assert result.proof_event_revision == 1
                assert result.proof_application_revision == 1
        elif case["operation"] == "rename_equivalence":
            assert result["equivalent"] is True
        elif case["operation"] == "polysemy_type_selection":
            assert result["sense_candidate_count"] >= 2
            assert result["selected_schema_ref"] != result["rejected_schema_ref"]
    assert len(full_packages) >= 4


def test_phase12_competence_names_never_appear_in_semantic_kernel() -> None:
    tokens = set()
    for case in _cases():
        if case.get("lexeme"):
            tokens.add(case["lexeme"])
        for side in ("left", "right"):
            item = case.get(side)
            if isinstance(item, dict) and item.get("lexeme"):
                tokens.add(item["lexeme"])
    for directory in ("grounding", "composition", "epistemics", "transitions"):
        for path in (RUNTIME / directory).rglob("*.py"):
            literals = _executable_string_literals(path)
            assert not [
                token for token in tokens
                if any(_semantic_token_occurs(token, literal) for literal in literals)
            ], path
