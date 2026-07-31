from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import cemm_authoritative_hybrid.governance as governance
from cemm_authoritative_hybrid.governance import (
    GovernanceError,
    LedgerAnchor,
    effective_replay_status,
    expected_record_ref,
    load_ledger_anchor,
    read_hash_chain,
    verify_file_invalidation,
)


ROOT = Path(__file__).resolve().parents[1]

GOVERNING_DOCUMENTS = (
    "AGENTS.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md",
    "docs/ARCHITECTURE.md",
    "docs/ABI_REGISTRY.md",
)

SUPERSEDED_EXECUTION_CLAIMS = (
    "docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md",
    "docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md",
    "docs/superpowers/plans/2026-07-29-m1-six-phase-kernel.md",
    "docs/superpowers/plans/2026-07-29-m2-hybrid-proposal-verifier.md",
    "docs/superpowers/plans/2026-07-29-m3-cognition-learning-realization.md",
    "docs/superpowers/plans/2026-07-29-m4-training-failure-competitive-evaluation.md",
    "docs/superpowers/plans/2026-07-29-m5-surfaces-reliable-cutover.md",
    "docs/superpowers/plans/2026-07-30-corrective-replay-plan.md",
)

HISTORICAL_EVIDENCE = (
    "docs/EVALUATION_REPORT.md",
    "docs/NEURAL_MODEL.md",
    "docs/COMPARISON.md",
    "docs/RUNTIME_TRACES.md",
    "docs/WORKTREE_INTEGRATION.md",
    "artifacts/",
)

ACTIVE_POINTERS = (
    "AGENTS.md",
    "README.md",
    "INTEGRATION.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/ABI_REGISTRY.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
)


def _authority() -> dict[str, object]:
    return json.loads(
        (ROOT / "docs/DOCUMENT_AUTHORITY.json").read_text(encoding="utf-8")
    )


def test_document_authority_is_scoped_and_classifications_are_exact() -> None:
    authority = _authority()

    assert authority["schema"] == "cemm-hybrid-document-authority-v1"
    assert authority["scope"] == "hybrid_mvp/"
    assert authority["path_base"] == "hybrid_mvp/"
    assert authority["root_runtime_authority"] == "../AGENTS.md"
    assert authority["governing_documents"] == list(GOVERNING_DOCUMENTS)
    assert authority["superseded_execution_claims"] == list(
        SUPERSEDED_EXECUTION_CLAIMS
    )
    assert authority["historical_evidence"] == list(HISTORICAL_EVIDENCE)
    assert authority["generated_artifacts_are_authority"] is False
    assert authority["root_adoption_requires_separate_review"] is True

    classifications = (
        set(GOVERNING_DOCUMENTS),
        set(SUPERSEDED_EXECUTION_CLAIMS),
        set(HISTORICAL_EVIDENCE),
    )
    for index, current in enumerate(classifications):
        for other in classifications[index + 1 :]:
            assert current.isdisjoint(other)

    for relative in (
        *GOVERNING_DOCUMENTS,
        *SUPERSEDED_EXECUTION_CLAIMS,
        *HISTORICAL_EVIDENCE,
    ):
        assert (ROOT / relative.rstrip("/")).exists(), relative

    root_authority = (ROOT / str(authority["root_runtime_authority"])).resolve()
    assert root_authority == (ROOT.parent / "AGENTS.md").resolve()
    assert root_authority.is_file()


def test_governing_pointers_make_no_old_admission_claim() -> None:
    obsolete_claims = (
        re.compile(r"\bM1\s*[-–]\s*M3\s+are\s+complete\b", re.IGNORECASE),
        re.compile(
            r"\bM4\s+Tasks?\s+(?:1\s*[-–]\s*)?4\s+"
            r"(?:is|are)\s+(?:complete|implemented)\b",
            re.IGNORECASE,
        ),
    )

    for relative in ACTIVE_POINTERS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "proposed for user review" not in text.casefold()
        for pattern in obsolete_claims:
            assert pattern.search(text) is None, relative


STATUS_FIELDS = {
    "schema",
    "sequence",
    "predecessor_ref",
    "source_base",
    "phase",
    "status",
    "admission_gate_result_ref",
    "admission_run_ref",
    "rationale",
    "record_ref",
}

INVALIDATION_FIELDS = {
    "schema",
    "sequence",
    "predecessor_ref",
    "source_base",
    "subject",
    "subject_sha256",
    "disposition",
    "rationale",
    "record_ref",
}

INITIAL_STATUS = {
    "G0": "pending",
    "R1": "red",
    "R2": "red",
    "R3": "red",
    "R4": "red",
    "R5": "red",
    "R6": "red",
    "R7": "red",
    "R8": "red",
}

INVALIDATED_RECEIPTS = {
    "artifacts/validation/MILESTONE_RECEIPT.json":
        "f6df34c05b9cbbdd5b5864ad5fb11bfc7c530105753117e05e80a2da642b6aa7",
    "artifacts/validation/M2_PROPOSAL_RECEIPT.json":
        "c01945cfb2d482f9a43cbf4837284d65a6659914718b2d3c4e5629db4160f5ae",
    "artifacts/validation/M3_MILESTONE_RECEIPT.json":
        "6ab45fa606f7ce9ff99e7d779aacc84a7734abde858e2cff1a96225f91005c5e",
    "artifacts/validation/REPRODUCIBILITY.json":
        "330e214f5fa2cf301dd5d0831645eed0e7c61e4e9eadb1917a16c760b84f9768",
    "artifacts/training_receipt.json":
        "7d03f5151f1750b077f44c975095e9db99510d9b4220e1ae00e010e074066517",
    "artifacts/evaluation/CEMM_EVALUATION.json":
        "4caf7f65fd9d30ddeedf455e81b10194132808d75a274dea49229878ca09dc61",
}


def _ledger(name: str) -> Path:
    return ROOT / "governance" / name


def _canonical_jsonl(records: list[dict[str, object]]) -> bytes:
    return b"".join(
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        for record in records
    )


def _anchor_for(raw: bytes, records: list[dict[str, object]]) -> LedgerAnchor:
    return LedgerAnchor(
        ledger_path="governance/test.jsonl",
        record_schema=str(records[0]["schema"]),
        initial_count=len(records),
        genesis_ref=str(records[0]["record_ref"]),
        initial_head_ref=str(records[-1]["record_ref"]),
        initial_bytes_size=len(raw),
        initial_bytes_sha256=hashlib.sha256(raw).hexdigest(),
        source_base=str(records[0]["source_base"]),
    )


def _append_status(
    records: list[dict[str, object]],
    *,
    phase: str,
    status: object,
    gate_ref: object = None,
    run_ref: object = None,
    source_base: str = "a" * 40,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": "cemm-replay-status-record-v1",
        "sequence": len(records),
        "predecessor_ref": records[-1]["record_ref"],
        "source_base": source_base,
        "phase": phase,
        "status": status,
        "admission_gate_result_ref": gate_ref,
        "admission_run_ref": run_ref,
        "rationale": "test transition",
    }
    record["record_ref"] = expected_record_ref(record)
    records.append(record)
    return record


def _initial_status_records() -> list[dict[str, object]]:
    path = _ledger("replay_status.jsonl")
    records = read_hash_chain(path)
    return [dict(record) for record in records[: load_ledger_anchor(path).initial_count]]


def _order_ancestor(order: dict[str, int]):
    return lambda ancestor, descendant: order[ancestor] <= order[descendant]


def _pure_read(
    path: Path,
    anchor: LedgerAnchor,
    *,
    blobs: dict[str, bytes] | None = None,
    kinds: dict[str, str] | None = None,
    head_ref: str | None = None,
    order: dict[str, int] | None = None,
) -> tuple[dict[str, object], ...]:
    return governance._read_hash_chain_for_test(
        path,
        anchor,
        committed_blobs=blobs or {},
        commit_kinds=kinds or {},
        head_ref=head_ref,
        is_ancestor=_order_ancestor(order) if order is not None else None,
    )


def _load_update_script():
    path = ROOT / "scripts" / "update_replay_status.py"
    spec = importlib.util.spec_from_file_location("task2_update_replay_status", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _receipt(
    *,
    phase: str,
    gate_ref: str,
    run_ref: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        gate_result_ref=gate_ref,
        run_ref=run_ref,
        phase=phase,
        tier="admission",
        fresh=True,
        step_results=(SimpleNamespace(disposition="passed"),),
    )


def test_initial_replay_status_is_truthful_and_receipt_free() -> None:
    records = _initial_status_records()
    assert effective_replay_status(records) == INITIAL_STATUS
    assert len(records) == len(INITIAL_STATUS)
    assert [record["phase"] for record in records] == list(INITIAL_STATUS)
    assert all(set(record) == STATUS_FIELDS for record in records)
    assert all(record["admission_gate_result_ref"] is None for record in records)
    assert all(record["admission_run_ref"] is None for record in records)


def test_invalidations_bind_six_unchanged_historical_files() -> None:
    path = _ledger("receipt_invalidations.jsonl")
    all_records = read_hash_chain(path)
    records = all_records[: load_ledger_anchor(path).initial_count]
    assert len(records) == 6
    assert all(set(record) == INVALIDATION_FIELDS for record in records)
    assert {record["subject"]: record["subject_sha256"] for record in records} == (
        INVALIDATED_RECEIPTS
    )
    for record in records:
        verify_file_invalidation(ROOT, record)


def test_document_authority_cryptographically_pins_ledger_anchors() -> None:
    pin = _authority()["governance_ledger_anchors"]
    assert pin["path"] == "governance/ledger_anchors.json"
    anchor_path = ROOT / pin["path"]
    assert hashlib.sha256(anchor_path.read_bytes()).hexdigest() == pin["sha256"]


def test_document_authority_is_lf_normalized() -> None:
    assert b"\r\n" not in (ROOT / "docs" / "DOCUMENT_AUTHORITY.json").read_bytes()


def test_ledger_anchor_record_schema_must_be_a_strict_string() -> None:
    anchor = load_ledger_anchor(_ledger("replay_status.jsonl"))
    values = dict(vars(anchor))
    values["record_schema"] = []
    with pytest.raises(GovernanceError, match="record_schema"):
        LedgerAnchor(**values)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_type", "content"])
def test_status_records_require_exact_typed_content_addressed_fields(
    tmp_path: Path, mutation: str
) -> None:
    source = _ledger("replay_status.jsonl")
    records = _initial_status_records()
    anchor = load_ledger_anchor(source)
    if mutation == "missing":
        records[0].pop("rationale")
    elif mutation == "extra":
        records[0]["unexpected"] = "not allowed"
    elif mutation == "wrong_type":
        records[0]["sequence"] = False
    else:
        records[0]["rationale"] = "rewritten without updating its content ref"
    tampered = tmp_path / "replay_status.jsonl"
    tampered.write_bytes(_canonical_jsonl(records))
    with pytest.raises(GovernanceError):
        _pure_read(tampered, anchor)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase", []),
        ("status", []),
        ("admission_gate_result_ref", True),
        ("admission_run_ref", 7),
    ],
)
def test_status_enum_and_ref_types_fail_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    source = _ledger("replay_status.jsonl")
    records = _initial_status_records()
    records[0][field] = value
    records[0]["record_ref"] = expected_record_ref(records[0])
    path = tmp_path / "bad-type.jsonl"
    path.write_bytes(_canonical_jsonl(records))
    with pytest.raises(GovernanceError):
        _pure_read(path, load_ledger_anchor(source))


def test_admission_refs_require_exact_gate_and_run_namespaces() -> None:
    records = _initial_status_records()
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref="run:" + "1" * 24,
        run_ref="gate_result:" + "2" * 24,
    )
    with pytest.raises(GovernanceError, match="admission_gate_result_ref"):
        effective_replay_status(records)


def test_hash_chain_rejects_duplicate_blank_noncanonical_and_nonfinite_rows(
    tmp_path: Path,
) -> None:
    source = _ledger("replay_status.jsonl")
    raw = source.read_bytes()
    anchor = load_ledger_anchor(source)
    corruptions = (
        raw.replace(b'"phase":"G0"', b'"phase":"G0","phase":"G0"', 1),
        raw.replace(b"\n", b"\n\n", 1),
        raw.replace(b'{"admission_gate_result_ref"', b'{ "admission_gate_result_ref"', 1),
        raw.replace(b'"sequence":0', b'"sequence":NaN', 1),
    )
    for index, corrupted in enumerate(corruptions):
        path = tmp_path / f"corrupted-{index}.jsonl"
        path.write_bytes(corrupted)
        with pytest.raises(GovernanceError):
            _pure_read(path, anchor)


def test_hash_chain_rejects_broken_predecessor_and_truncation(tmp_path: Path) -> None:
    source = _ledger("replay_status.jsonl")
    anchor = load_ledger_anchor(source)
    records = _initial_status_records()
    records[2]["predecessor_ref"] = records[0]["record_ref"]
    records[2]["record_ref"] = expected_record_ref(records[2])
    broken = tmp_path / "broken.jsonl"
    broken.write_bytes(_canonical_jsonl(records))
    with pytest.raises(GovernanceError, match="predecessor"):
        _pure_read(broken, anchor)
    truncated = tmp_path / "truncated.jsonl"
    truncated.write_bytes(_canonical_jsonl(_initial_status_records()[:-1]))
    with pytest.raises(GovernanceError, match="truncated"):
        _pure_read(truncated, anchor)


def test_anchor_byte_tamper_is_rejected_by_document_authority(tmp_path: Path) -> None:
    root = tmp_path / "hybrid_mvp"
    (root / "docs").mkdir(parents=True)
    (root / "governance").mkdir()
    authority = copy.deepcopy(_authority())
    (root / "docs" / "DOCUMENT_AUTHORITY.json").write_text(
        json.dumps(authority), encoding="utf-8"
    )
    anchor_bytes = _ledger("ledger_anchors.json").read_bytes() + b" "
    (root / "governance" / "ledger_anchors.json").write_bytes(anchor_bytes)
    (root / "governance" / "replay_status.jsonl").write_bytes(
        _ledger("replay_status.jsonl").read_bytes()
    )
    with pytest.raises(GovernanceError, match="document authority"):
        load_ledger_anchor(root / "governance" / "replay_status.jsonl")


def test_invalidation_rejects_traversal_even_with_rehashed_record() -> None:
    record = dict(read_hash_chain(_ledger("receipt_invalidations.jsonl"))[0])
    record["subject"] = "artifacts/../docs/DOCUMENT_AUTHORITY.json"
    record["record_ref"] = expected_record_ref(record)
    with pytest.raises(GovernanceError, match="safe relative path"):
        verify_file_invalidation(ROOT, record)


def test_every_suffix_record_binds_commit_ancestor_monotonic_exact_prefix(
    tmp_path: Path,
) -> None:
    initial = _initial_status_records()
    initial_raw = _canonical_jsonl(initial)
    anchor = _anchor_for(initial_raw, initial)
    first_base, second_base, head = "a" * 40, "b" * 40, "c" * 40
    records = [dict(record) for record in initial]
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref="gate_result:" + "1" * 24,
        run_ref="run:" + "1" * 24,
        source_base=first_base,
    )
    first_prefix = _canonical_jsonl(records)
    _append_status(
        records,
        phase="R1",
        status="externally_blocked",
        gate_ref="gate_result:" + "2" * 24,
        run_ref="run:" + "2" * 24,
        source_base=second_base,
    )
    complete = _canonical_jsonl(records)
    path = tmp_path / "replay_status.jsonl"
    path.write_bytes(complete)
    order = {str(anchor.source_base): 0, first_base: 1, second_base: 2, head: 3}
    assert _pure_read(
        path,
        anchor,
        blobs={first_base: initial_raw, second_base: first_prefix},
        kinds={str(anchor.source_base): "commit", first_base: "commit", second_base: "commit", head: "commit"},
        head_ref=head,
        order=order,
    ) == tuple(records)


@pytest.mark.parametrize("defect", ["non_commit", "not_ancestor", "non_monotonic", "wrong_prefix"])
def test_suffix_git_witness_defects_fail_closed(tmp_path: Path, defect: str) -> None:
    initial = _initial_status_records()
    initial_raw = _canonical_jsonl(initial)
    anchor = _anchor_for(initial_raw, initial)
    base, head = "a" * 40, "c" * 40
    records = [dict(record) for record in initial]
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref="gate_result:" + "3" * 24,
        run_ref="run:" + "3" * 24,
        source_base=base,
    )
    path = tmp_path / "replay_status.jsonl"
    path.write_bytes(_canonical_jsonl(records))
    kinds = {str(anchor.source_base): "commit", base: "commit", head: "commit"}
    order = {str(anchor.source_base): 0, base: 1, head: 2}
    blobs = {base: initial_raw}
    if defect == "non_commit":
        kinds[base] = "tree"
    elif defect == "not_ancestor":
        order[base] = 3
    elif defect == "non_monotonic":
        order[str(anchor.source_base)] = 2
        order[base] = 1
    else:
        blobs[base] = initial_raw + b" "
    with pytest.raises(GovernanceError):
        _pure_read(path, anchor, blobs=blobs, kinds=kinds, head_ref=head, order=order)


def test_hash_chain_has_small_external_bounds(tmp_path: Path) -> None:
    too_many = tmp_path / "too-many.jsonl"
    too_many.write_bytes(b"{}\n" * (governance.MAX_LEDGER_RECORDS + 1))
    with pytest.raises(GovernanceError, match="too many records"):
        governance.parse_and_validate_records(too_many.read_bytes())
    line_too_long = tmp_path / "line-too-long.jsonl"
    line_too_long.write_bytes(b"{" + b" " * governance.MAX_LEDGER_LINE_BYTES + b"}\n")
    with pytest.raises(GovernanceError, match="row exceeds"):
        governance.parse_and_validate_records(line_too_long.read_bytes())


def test_suffix_transitions_reset_descendants_before_applying() -> None:
    records = _initial_status_records()
    _append_status(records, phase="G0", status="green", gate_ref="gate_result:" + "4" * 24, run_ref="run:" + "4" * 24)
    _append_status(records, phase="R1", status="green", gate_ref="gate_result:" + "5" * 24, run_ref="run:" + "5" * 24, source_base="b" * 40)
    assert effective_replay_status(records)["R1"] == "green"
    _append_status(records, phase="G0", status="green", gate_ref="gate_result:" + "6" * 24, run_ref="run:" + "6" * 24, source_base="c" * 40)
    assert effective_replay_status(records) == {"G0": "green", **{f"R{i}": "red" for i in range(1, 9)}}


def test_external_status_requires_green_predecessors_and_unique_dual_refs() -> None:
    records = _initial_status_records()
    _append_status(records, phase="R1", status="externally_blocked", gate_ref="gate_result:" + "7" * 24, run_ref="run:" + "7" * 24)
    with pytest.raises(GovernanceError, match="dependency"):
        effective_replay_status(records)

    records = _initial_status_records()
    gate_ref, run_ref = "gate_result:" + "8" * 24, "run:" + "8" * 24
    _append_status(records, phase="G0", status="externally_blocked", gate_ref=gate_ref, run_ref=run_ref)
    _append_status(records, phase="G0", status="green", gate_ref=gate_ref, run_ref="run:" + "9" * 24, source_base="b" * 40)
    with pytest.raises(GovernanceError, match="gate result.*already consumed"):
        effective_replay_status(records)


def test_red_suffix_resets_green_descendants() -> None:
    records = _initial_status_records()
    _append_status(records, phase="G0", status="green", gate_ref="gate_result:" + "a" * 24, run_ref="run:" + "a" * 24)
    _append_status(records, phase="R1", status="green", gate_ref="gate_result:" + "b" * 24, run_ref="run:" + "b" * 24, source_base="b" * 40)
    _append_status(records, phase="G0", status="red", source_base="c" * 40)
    assert effective_replay_status(records) == INITIAL_STATUS | {"G0": "red"}


def test_governance_ledgers_are_lf_normalized_without_live_git_dependency() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "governance/*.json text eol=lf" in attributes
    assert "governance/*.jsonl text eol=lf" in attributes
    for name in ("replay_status.jsonl", "receipt_invalidations.jsonl", "ledger_anchors.json"):
        assert b"\r\n" not in _ledger(name).read_bytes()


def test_status_cli_derives_current_effective_status() -> None:
    expected = effective_replay_status(read_hash_chain(_ledger("replay_status.jsonl")))
    completed = subprocess.run(
        [sys.executable, "scripts/update_replay_status.py", "--verify-chain"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    for phase, status in expected.items():
        assert f"{phase}={status}" in completed.stdout


def test_unavailable_admission_owner_is_injected_not_filesystem_dependent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    monkeypatch.setattr(
        script,
        "_load_admission_owner",
        lambda **_kwargs: (_ for _ in ()).throw(GovernanceError("validated admission receipt owner is unavailable")),
    )
    with pytest.raises(GovernanceError, match="owner is unavailable"):
        script._validated_admission("G0", "green", run_ref="run:" + "0" * 24)


def test_owner_import_preflight_rejects_dirty_code_before_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    monkeypatch.setattr(
        script, "_dirty_hybrid_paths", lambda: frozenset({"src/runtime.py"})
    )
    with pytest.raises(GovernanceError, match="dirty governed input"):
        script._load_admission_owner(
            phase="G0", run_ref="run:" + "1" * 24
        )


def test_candidate_preflight_allows_exact_run_phase_and_fixed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    run_ref = "run:" + "1" * 24
    dirty = frozenset(
        {
            "artifacts/validation/runs/" + "1" * 24 + ".json",
            "artifacts/validation/G0_ADMISSION_RECEIPT.json",
            "artifacts/validation/BASELINE_REPLAY_FINDINGS.json",
            "artifacts/validation/TEST_INVENTORY_RECEIPT.json",
        }
    )
    monkeypatch.setattr(script, "_dirty_hybrid_paths", lambda: dirty)
    script._preflight_owner_import("G0", run_ref)


def test_owner_loads_exact_reviewed_file_and_rejects_broad_error_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    gate_path = scripts / "validation_gate.py"
    gate_path.write_text(
        "class AdmissionValidationError(Exception):\n"
        "    pass\n"
        "def load_verified_admission_receipt(**kwargs):\n"
        "    return kwargs\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(script, "ROOT", tmp_path)
    monkeypatch.setattr(script, "_dirty_hybrid_paths", lambda: frozenset())
    monkeypatch.setitem(sys.modules, "validation_gate", SimpleNamespace(
        AdmissionValidationError=Exception,
        load_verified_admission_receipt=lambda **_kwargs: None,
    ))
    owner = script._load_admission_owner(
        phase="G0", run_ref="run:" + "1" * 24
    )
    assert Path(owner.loader.__code__.co_filename).resolve() == gate_path.resolve()

    gate_path.write_text(
        "AdmissionValidationError = ValueError\n"
        "def load_verified_admission_receipt(**kwargs):\n"
        "    return kwargs\n",
        encoding="utf-8",
    )
    with pytest.raises(TypeError, match="AdmissionValidationError"):
        script._load_admission_owner(
            phase="G0", run_ref="run:" + "1" * 24
        )


def test_only_typed_admission_errors_are_wrapped() -> None:
    script = _load_update_script()
    run_ref = "run:" + "0" * 24

    class AdmissionValidationError(Exception):
        pass

    def typed_failure(**_kwargs):
        raise AdmissionValidationError("bad receipt")

    owner = script.AdmissionOwner(AdmissionValidationError, typed_failure)
    with pytest.raises(GovernanceError, match="admission receipt was rejected"):
        script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)

    def programming_failure(**_kwargs):
        raise RuntimeError("implementation defect")

    owner = script.AdmissionOwner(AdmissionValidationError, programming_failure)
    with pytest.raises(RuntimeError, match="implementation defect"):
        script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)


@pytest.mark.parametrize("ledger_status", ["green", "externally_blocked"])
def test_admission_requires_passed_technical_steps_and_passes_passed_to_task4(
    ledger_status: str,
) -> None:
    script = _load_update_script()
    gate_ref, run_ref = "gate_result:" + "b" * 24, "run:" + "b" * 24
    receipt = _receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref)
    receipt.step_results = (SimpleNamespace(disposition="failed"),)
    expected_statuses: list[str] = []

    def loader(**kwargs):
        expected_statuses.append(kwargs["expected_status"])
        return receipt, ()

    owner = script.AdmissionOwner(ValueError, loader)
    with pytest.raises(GovernanceError, match="non-passed"):
        script._validated_admission(
            "G0", ledger_status, run_ref=run_ref, owner=owner
        )
    assert expected_statuses == ["passed"]


def test_updater_rejects_swapped_gate_and_run_ref_namespaces() -> None:
    script = _load_update_script()
    receipt = _receipt(
        phase="G0",
        gate_ref="run:" + "b" * 24,
        run_ref="gate_result:" + "b" * 24,
    )
    owner = script.AdmissionOwner(ValueError, lambda **_kwargs: (receipt, ()))
    with pytest.raises(TypeError, match="gate_result_ref"):
        script._validated_admission(
            "G0", "green", run_ref="run:" + "b" * 24, owner=owner
        )


def test_admission_binding_stores_gate_and_exact_run_refs() -> None:
    script = _load_update_script()
    gate_ref, run_ref = "gate_result:" + "c" * 24, "run:" + "c" * 24
    receipt = _receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref)
    owner = script.AdmissionOwner(
        ValueError,
        lambda **_kwargs: (receipt, ("artifacts/validation/runs/current.json",)),
    )
    validated, paths = script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)
    assert validated is receipt
    assert paths == ("artifacts/validation/runs/current.json",)
    record = governance.make_status_record(
        _initial_status_records(),
        source_base="a" * 40,
        phase="G0",
        status="green",
        admission_gate_result_ref=receipt.gate_result_ref,
        admission_run_ref=receipt.run_ref,
        rationale="test",
    )
    assert record["admission_gate_result_ref"] == gate_ref
    assert record["admission_run_ref"] == run_ref


def test_verify_chain_reconstructs_each_admitted_run() -> None:
    script = _load_update_script()
    records = _initial_status_records()
    gate_ref, run_ref = "gate_result:" + "d" * 24, "run:" + "d" * 24
    _append_status(records, phase="G0", status="green", gate_ref=gate_ref, run_ref=run_ref)
    calls: list[str | None] = []

    def loader(**kwargs):
        calls.append(kwargs["run_ref"])
        return (_receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref), ())

    owner = script.AdmissionOwner(ValueError, loader)
    script._verify_admitted_runs(records, owner=owner)
    assert calls == [run_ref]




def test_multi_admission_verify_aggregates_exact_paths_before_dirty_narrowing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    records = _initial_status_records()
    g_gate, g_run = "gate_result:" + "2" * 24, "run:" + "2" * 24
    r_gate, r_run = "gate_result:" + "3" * 24, "run:" + "3" * 24
    _append_status(
        records, phase="G0", status="green", gate_ref=g_gate, run_ref=g_run
    )
    _append_status(
        records,
        phase="R1",
        status="green",
        gate_ref=r_gate,
        run_ref=r_run,
        source_base="b" * 40,
    )
    paths_by_phase = {
        "G0": (
            "artifacts/validation/runs/" + "2" * 24 + ".json",
            "artifacts/validation/G0_ADMISSION_RECEIPT.json",
        ),
        "R1": (
            "artifacts/validation/runs/" + "3" * 24 + ".json",
            "artifacts/validation/R1_ADMISSION_RECEIPT.json",
        ),
    }

    def loader(**kwargs):
        phase = kwargs["phase"]
        gate_ref, run_ref = (
            (g_gate, g_run) if phase == "G0" else (r_gate, r_run)
        )
        return _receipt(phase=phase, gate_ref=gate_ref, run_ref=run_ref), paths_by_phase[phase]

    owner = script.AdmissionOwner(ValueError, loader)
    dirty = frozenset(
        {
            *paths_by_phase["G0"],
            *paths_by_phase["R1"],
            "governance/replay_status.jsonl",
        }
    )
    monkeypatch.setattr(script, "_dirty_hybrid_paths", lambda: dirty)
    script._preflight_owner_import("G0", g_run, authenticated_ledger=True)
    allowed = script._verify_admitted_runs(
        records,
        owner=owner,
        dirty_paths=dirty,
        require_evidence_files=False,
    )
    assert allowed == frozenset((*paths_by_phase["G0"], *paths_by_phase["R1"]))




def test_post_write_reconstructs_all_admitted_rows_and_preserves_path_union() -> None:
    script = _load_update_script()
    records = _initial_status_records()
    g_gate, g_run = "gate_result:" + "6" * 24, "run:" + "6" * 24
    r_gate, r_run = "gate_result:" + "7" * 24, "run:" + "7" * 24
    _append_status(records, phase="G0", status="green", gate_ref=g_gate, run_ref=g_run)
    _append_status(
        records,
        phase="R1",
        status="green",
        gate_ref=r_gate,
        run_ref=r_run,
        source_base="b" * 40,
    )
    paths_by_run = {
        g_run: ("artifacts/validation/runs/" + "6" * 24 + ".json",),
        r_run: ("artifacts/validation/runs/" + "7" * 24 + ".json",),
    }
    calls: list[str] = []

    def loader(**kwargs):
        run_ref = kwargs["run_ref"]
        calls.append(run_ref)
        phase, gate_ref = ("G0", g_gate) if run_ref == g_run else ("R1", r_gate)
        return _receipt(phase=phase, gate_ref=gate_ref, run_ref=run_ref), paths_by_run[run_ref]

    owner = script.AdmissionOwner(ValueError, loader)
    allowed = tuple(sorted((*paths_by_run[g_run], *paths_by_run[r_run])))
    callback = script._make_post_write_validator(
        records=records,
        evidence_paths=allowed,
        source_base="a" * 40,
        prior_bytes=b"prior\n",
        owner=owner,
        dirty_loader=lambda: frozenset({*allowed, "governance/replay_status.jsonl"}),
        head_loader=lambda: "a" * 40,
        committed_loader=lambda _source_base: b"prior\n",
        require_evidence_files=False,
    )

    callback()
    assert calls == [g_run, r_run]


@pytest.mark.parametrize("candidate_status", ["red", "green"])
def test_candidate_reconstructs_prior_admissions_before_any_transition(
    monkeypatch: pytest.MonkeyPatch,
    candidate_status: str,
) -> None:
    script = _load_update_script()
    records = _initial_status_records()
    prior_gate = "gate_result:" + "4" * 24
    prior_run = "run:" + "4" * 24
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref=prior_gate,
        run_ref=prior_run,
    )
    new_run = "run:" + "5" * 24 if candidate_status == "green" else None
    owner_loads = 0

    def load_owner(**_kwargs):
        nonlocal owner_loads
        owner_loads += 1

        def reject_prior(**kwargs):
            if kwargs["run_ref"] == prior_run:
                raise ValueError("prior receipt is no longer valid")
            raise AssertionError("new receipt must not be read after prior rejection")

        return script.AdmissionOwner(ValueError, reject_prior)

    monkeypatch.setattr(script, "read_hash_chain", lambda _path: records)
    monkeypatch.setattr(script, "_dirty_hybrid_paths", frozenset)
    monkeypatch.setattr(script, "_load_admission_owner", load_owner)
    args = SimpleNamespace(phase="R1", status=candidate_status, run_ref=new_run)

    with pytest.raises(GovernanceError, match="receipt was rejected"):
        script._candidate(args)
    assert owner_loads == 1




def test_red_candidate_without_prior_admissions_scans_dirty_status_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_update_script()
    records = _initial_status_records()
    dirty_scans = 0

    def dirty_paths() -> frozenset[str]:
        nonlocal dirty_scans
        dirty_scans += 1
        return frozenset()

    monkeypatch.setattr(script, "read_hash_chain", lambda _path: records)
    monkeypatch.setattr(script, "_dirty_hybrid_paths", dirty_paths)
    monkeypatch.setattr(
        script,
        "_require_committed_current_prefix",
        lambda: ("9" * 40, b"prior\n"),
    )

    script._candidate(SimpleNamespace(phase="G0", status="red", run_ref=None))
    assert dirty_scans == 1
def test_cli_requires_exact_run_ref_and_exposes_no_latest_selector() -> None:
    script = _load_update_script()
    with pytest.raises(SystemExit):
        script._parser().parse_args(["--admit-latest"])
    with pytest.raises(GovernanceError, match="exact --run-ref"):
        script._validate_transition_args(
            SimpleNamespace(phase="G0", status="green", run_ref=None)
        )
    script._validate_transition_args(
        SimpleNamespace(
            phase="G0",
            status="green",
            run_ref="run:" + "1" * 24,
        )
    )
    with pytest.raises(GovernanceError, match="only valid for admission"):
        script._validate_transition_args(
            SimpleNamespace(
                phase="G0",
                status="red",
                run_ref="run:" + "1" * 24,
            )
        )

def test_append_requires_reviewed_candidate_ref() -> None:
    script = _load_update_script()
    record = {"record_ref": "governance_record:" + "e" * 24}
    with pytest.raises(GovernanceError, match="--expect-record-ref is required"):
        script._require_expected_record_ref(record, None)
    with pytest.raises(GovernanceError, match="reviewed candidate changed"):
        script._require_expected_record_ref(record, "governance_record:" + "f" * 24)
    script._require_expected_record_ref(record, str(record["record_ref"]))


def test_dirty_governed_inputs_allow_only_validated_evidence_paths(tmp_path: Path) -> None:
    script = _load_update_script()
    allowed = script._normalize_allowed_evidence_paths(
        ("artifacts/validation/runs/current.json",),
        root=tmp_path,
        require_files=False,
    )
    script._reject_dirty_governed_inputs(
        {"artifacts/validation/runs/current.json"}, allowed
    )
    with pytest.raises(GovernanceError, match="dirty governed input"):
        script._reject_dirty_governed_inputs({"src/runtime.py"}, allowed)
    with pytest.raises(GovernanceError, match="unsafe validated evidence path"):
        script._normalize_allowed_evidence_paths(("../runtime.py",), root=tmp_path, require_files=False)


def test_append_lock_is_exclusive(tmp_path: Path) -> None:
    script = _load_update_script()
    lock = tmp_path / "status.lock"
    lock.write_text("held", encoding="utf-8")
    with pytest.raises(GovernanceError, match="another status update"):
        with script._exclusive_append_lock(lock):
            pass


def test_post_write_failure_rolls_back_exact_prior_bytes(tmp_path: Path) -> None:
    script = _load_update_script()
    ledger = tmp_path / "status.jsonl"
    prior = b'{"prior":true}\n'
    ledger.write_bytes(prior)

    def fail_verification(_path: Path):
        raise RuntimeError("post-write verifier failed")

    with pytest.raises(RuntimeError, match="post-write verifier failed"):
        script._append_exact(
            {"record_ref": "governance_record:" + "1" * 24},
            prior,
            ledger_path=ledger,
            verifier=fail_verification,
            post_write_validate=lambda: None,
        )
    assert ledger.read_bytes() == prior



def test_post_write_callback_cannot_mutate_ledger_before_structural_verification(
    tmp_path: Path,
) -> None:
    script = _load_update_script()
    ledger = tmp_path / "status.jsonl"
    prior = b'{"prior":true}\n'
    ledger.write_bytes(prior)
    verifier_called = False

    def mutate_ledger() -> None:
        with ledger.open("ab") as handle:
            handle.write(b'{"unauthorized":true}\n')

    def verifier(_path: Path) -> None:
        nonlocal verifier_called
        verifier_called = True

    with pytest.raises(GovernanceError, match="exact candidate bytes"):
        script._append_exact(
            {"record_ref": "governance_record:" + "1" * 24},
            prior,
            ledger_path=ledger,
            verifier=verifier,
            post_write_validate=mutate_ledger,
        )
    assert verifier_called is False
    assert ledger.read_bytes() == prior

def test_receipt_mutation_between_candidate_and_write_rolls_back_exact_bytes(
    tmp_path: Path,
) -> None:
    script = _load_update_script()
    ledger = tmp_path / "status.jsonl"
    prior = b'{"prior":true}\n'
    ledger.write_bytes(prior)
    gate_ref, run_ref = "gate_result:" + "f" * 24, "run:" + "f" * 24
    receipt = _receipt(phase="G0", gate_ref=gate_ref, run_ref=run_ref)
    evidence_paths = ("artifacts/validation/runs/" + "f" * 24 + ".json",)
    owner = script.AdmissionOwner(ValueError, lambda **_kwargs: (receipt, evidence_paths))
    records = _initial_status_records()
    _append_status(
        records,
        phase="G0",
        status="green",
        gate_ref=gate_ref,
        run_ref=run_ref,
    )
    script._validated_admission("G0", "green", run_ref=run_ref, owner=owner)
    callback = script._make_post_write_validator(
        records=records,
        evidence_paths=evidence_paths,
        source_base="a" * 40,
        prior_bytes=prior,
        owner=owner,
        dirty_loader=lambda: frozenset({"governance/replay_status.jsonl"}),
        head_loader=lambda: "a" * 40,
        committed_loader=lambda _source_base: prior,
        require_evidence_files=False,
    )
    receipt.step_results = (SimpleNamespace(disposition="failed"),)

    with pytest.raises(GovernanceError, match="non-passed"):
        script._append_exact(
            {"record_ref": "governance_record:" + "1" * 24},
            prior,
            ledger_path=ledger,
            verifier=lambda _path: None,
            post_write_validate=callback,
        )
    assert ledger.read_bytes() == prior




def test_bounded_git_io_cannot_deadlock_on_alternating_large_input_output() -> None:
    chunk_size = 4096
    chunk_count = 256
    payload = bytes(range(256)) * (chunk_size * chunk_count // 256)
    code = (
        "import sys\n"
        f"for _ in range({chunk_count}):\n"
        f"    chunk = sys.stdin.buffer.read({chunk_size})\n"
        "    if not chunk:\n"
        "        break\n"
        "    sys.stdout.buffer.write(chunk)\n"
        "    sys.stdout.buffer.flush()\n"
    )

    output = governance._run_bounded_git_stdout(
        (sys.executable, "-c", code),
        max_bytes=len(payload),
        input_bytes=payload,
    )
    assert output == payload


def test_bounded_git_io_rejects_oversized_input_before_process_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = False

    def popen(*_args, **_kwargs):
        nonlocal started
        started = True
        raise AssertionError("oversized input must be rejected before process start")

    monkeypatch.setattr(governance.subprocess, "Popen", popen)
    with pytest.raises(GovernanceError, match="input exceeds its byte bound"):
        governance._run_bounded_git_stdout(
            ("git", "cat-file", "--batch-check"),
            max_bytes=1,
            input_bytes=b"x" * (governance.MAX_GIT_INPUT_BYTES + 1),
        )
    assert started is False
def test_blob_size_is_checked_before_git_load(monkeypatch: pytest.MonkeyPatch) -> None:
    anchor, revision, head, blob = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    calls: list[tuple[str, ...]] = []

    def bounded(command, *, max_bytes, input_bytes=None):
        calls.append(tuple(command))
        assert "--batch-check=%(objectname) %(objecttype) %(objectsize)" in command
        return (
            f"{head} commit 1\n"
            f"{anchor} commit 1\n"
            f"{revision} commit 1\n"
            f"{blob} blob 11\n"
        ).encode("ascii")

    monkeypatch.setattr(governance, "_run_bounded_git_stdout", bounded)
    with pytest.raises(GovernanceError, match="exact committed prefix size"):
        governance._load_git_witnesses(
            ROOT.parent,
            _ledger("replay_status.jsonl"),
            anchor,
            (governance._PrefixWitness(revision, 10),),
        )
    assert len(calls) == 1


def test_commit_graph_load_is_single_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    head, parent, root = "c" * 40, "b" * 40, "a" * 40
    calls: list[tuple[tuple[str, ...], int]] = []

    def bounded(command, *, max_bytes):
        calls.append((tuple(command), max_bytes))
        return f"{head} {parent}\n{parent} {root}\n{root}\n".encode("ascii")

    monkeypatch.setattr(governance, "_run_bounded_git_stdout", bounded)
    graph = governance._git_load_commit_graph(ROOT.parent, head)
    assert len(calls) == 1
    assert "rev-list" in calls[0][0]
    assert calls[0][1] == governance.MAX_COMMIT_GRAPH_BYTES
    assert governance._graph_is_ancestor(graph, root, head)

    oversized = b"a" * (governance.MAX_COMMIT_GRAPH_BYTES + 1)
    with pytest.raises(GovernanceError, match="byte bound"):
        governance._parse_commit_graph(oversized, head)


def test_commit_graph_enforces_record_bound_and_follows_merge_parents() -> None:
    anchor, left, right, merge, head = (
        "a" * 40,
        "b" * 40,
        "c" * 40,
        "d" * 40,
        "e" * 40,
    )
    graph = governance._CommitGraph(
        anchor,
        head,
        {
            head: (merge,),
            merge: (left, right),
            left: (anchor,),
            right: (anchor,),
        },
    )
    assert governance._graph_is_ancestor(graph, right, head)
    governance._verify_graph_history(
        anchor,
        (
            governance._PrefixWitness(right, 1),
            governance._PrefixWitness(merge, 2),
        ),
        graph,
    )

    too_many = (f"{anchor}\n".encode("ascii")) * (
        governance.MAX_COMMIT_GRAPH_RECORDS + 1
    )
    with pytest.raises(GovernanceError, match="record bound"):
        governance._parse_commit_graph(too_many, head, anchor)


def test_git_witness_process_count_is_constant_for_multiple_suffixes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anchor, first, second, head = ("a" * 40, "b" * 40, "c" * 40, "d" * 40)
    first_blob, second_blob = "e" * 40, "f" * 40
    calls: list[tuple[str, ...]] = []

    def bounded(command, *, max_bytes, input_bytes=None):
        calls.append(tuple(command))
        if any("batch-check=" in part for part in command):
            return (
                f"{head} commit 1\n"
                f"{anchor} commit 1\n"
                f"{first} commit 1\n"
                f"{second} commit 1\n"
                f"{first_blob} blob 3\n"
                f"{second_blob} blob 5\n"
            ).encode("ascii")
        if "rev-list" in command:
            return (
                f"{head} {second}\n"
                f"{second} {first}\n"
                f"{first} {anchor}\n"
            ).encode("ascii")
        assert "--batch" in command
        return (
            f"{first_blob} blob 3\nabc\n"
            f"{second_blob} blob 5\nabcde\n"
        ).encode("ascii")

    monkeypatch.setattr(governance, "_run_bounded_git_stdout", bounded)
    resolved_head, blobs = governance._load_git_witnesses(
        ROOT.parent,
        _ledger("replay_status.jsonl"),
        anchor,
        (
            governance._PrefixWitness(first, 3),
            governance._PrefixWitness(second, 5),
        ),
    )
    assert resolved_head == head
    assert blobs == {first: b"abc", second: b"abcde"}
    assert len(calls) == 3
    assert sum("rev-list" in call for call in calls) == 1
    assert all("merge-base" not in call for call in calls)


def test_governance_import_does_not_load_torch() -> None:
    code = (
        "import sys; import cemm_authoritative_hybrid.governance; "
        "raise SystemExit(1 if 'torch' in sys.modules else 0)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**dict(os.environ), "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr

def test_tensor_type_hints_resolve_without_loading_torch() -> None:
    code = (
        "import sys, typing; "
        "from cemm_authoritative_hybrid.canonical import tensor_identity; "
        "typing.get_type_hints(tensor_identity); "
        "raise SystemExit(1 if 'torch' in sys.modules else 0)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**dict(os.environ), "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr
