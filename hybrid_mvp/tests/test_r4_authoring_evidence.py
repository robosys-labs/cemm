"""R4 optional authoring-evidence sidecar tests."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import zipfile

import pytest

from cemm_authoritative_hybrid.r4_authoring_evidence import (
    EvidenceSnapshot,
    EvidenceSource,
    normalize_evidence,
    write_evidence_snapshot,
)

__cemm_test_inventory__ = {'tests/test_r4_authoring_evidence.py::test_empty_snapshot_is_valid_and_network_free': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:r4-closure-test-authority-empty-snapshot-is-valid-and-network-free',
                                                                                        'diagnostic_role': 'admission_only',
                                                                                        'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                        'source_ast_sha256': '06c828d9d2d822545e5b46ecbda20f65ed2be2e70bb01c132f9ad78f6be484c6'},
 'tests/test_r4_authoring_evidence.py::test_unknown_license_cannot_emit_suggestion': {'activation_phase': 'R4',
                                                                                      'assertion_ref': 'assertion:r4-closure-test-authority-unknown-license-cannot-emit-suggestion',
                                                                                      'diagnostic_role': 'admission_only',
                                                                                      'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                      'source_ast_sha256': '806623cd1c0e192c084a36f91d7422a6a2fb7f0f2d597b3684a66e29c8b30c66'},
 'tests/test_r4_authoring_evidence.py::test_evidence_never_mints_cemm_authority': {'activation_phase': 'R4',
                                                                                   'assertion_ref': 'assertion:r4-closure-test-authority-evidence-never-mints-cemm-authority',
                                                                                   'diagnostic_role': 'admission_only',
                                                                                   'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                   'source_ast_sha256': '883fd1bf846e18c2ba5ff02c8dd2c34551cf12798661ca65ea7f03278808467d'},
 'tests/test_r4_authoring_evidence.py::test_source_policy_and_bounds_are_closed': {'activation_phase': 'R4',
                                                                                   'assertion_ref': 'assertion:r4-closure-test-authority-source-policy-and-bounds-are-closed',
                                                                                   'diagnostic_role': 'admission_only',
                                                                                   'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                   'source_ast_sha256': 'a5fde347787d65e10904a0aa8867d58d8afb4b86880c497317732c9bd98baa9c'},
 'tests/test_r4_authoring_evidence.py::test_snapshot_round_trip_verifies_bytes_hash_revision_and_normalizer': {'activation_phase': 'R4',
                                                                                                               'assertion_ref': 'assertion:r4-closure-test-authority-snapshot-round-trip-verifies-bytes-hash-revision-and-normalizer',
                                                                                                               'diagnostic_role': 'admission_only',
                                                                                                               'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                               'source_ast_sha256': 'a8fec66c4e7b6365b24d4e1d7e7e2cfcc9fdd5b8c032d01d32b75b28a1af251a'},
 'tests/test_r4_authoring_evidence.py::test_snapshot_rejects_manifest_path_traversal_and_source_overflow': {'activation_phase': 'R4',
                                                                                                            'assertion_ref': 'assertion:r4-closure-test-authority-snapshot-rejects-manifest-path-traversal-and-source-overflow',
                                                                                                            'diagnostic_role': 'admission_only',
                                                                                                            'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                            'source_ast_sha256': '917919f42c6ba506cb3a81da02981434e832b2f969046df0cac80999db2c4001'},
 'tests/test_r4_authoring_evidence.py::test_fetch_script_rejects_unsafe_urls_redirects_and_archives': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:r4-closure-test-authority-fetch-script-rejects-unsafe-urls-redirects-and-archives',
                                                                                                       'diagnostic_role': 'admission_only',
                                                                                                       'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                       'source_ast_sha256': '4120d0d16de22faa323c6ca63201161efe20770d002961611e369ec0daf61ea4'},
 'tests/test_r4_authoring_evidence.py::test_fetch_publication_is_hash_checked_transactional_and_idempotent': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:r4-closure-test-authority-fetch-publication-is-hash-checked-transactional-and-idempotent',
                                                                                                              'diagnostic_role': 'admission_only',
                                                                                                              'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                                              'source_ast_sha256': '83ead267ae110863dda18232798d0073c3ba91ee9973ac4962613452058bea70'},
 'tests/test_r4_authoring_evidence.py::test_evidence_manifest_schema_is_draft_2020_12': {'activation_phase': 'R4',
                                                                                         'assertion_ref': 'assertion:r4-closure-test-authority-evidence-manifest-schema-is-draft-2020-12',
                                                                                         'diagnostic_role': 'admission_only',
                                                                                         'introduced_by_task': 'R4-Closure-Test-Authority',
                                                                                         'source_ast_sha256': '42f9ab0bf276acc45514134f982c686e93b5a61fed95f00ee02ceb42e7a1f615'}}


ROOT = Path(__file__).parents[1]


def _source(**overrides) -> EvidenceSource:
    values = {
        "source_family": "oewn",
        "revision": "2024-edition",
        "sha256": hashlib.sha256(b"evidence\n").hexdigest(),
        "byte_length": len(b"evidence\n"),
        "license_id": "PDDL-1.0",
        "license_policy": "suggestion_permitted",
        "relative_path": "raw/oewn.txt",
    }
    values.update(overrides)
    return EvidenceSource.create(**values)


def test_empty_snapshot_is_valid_and_network_free() -> None:
    snapshot = EvidenceSnapshot.create(sources=())
    assert snapshot.sources == ()
    assert snapshot.total_bytes == 0
    module_source = (ROOT / "src/cemm_authoritative_hybrid/r4_authoring_evidence.py").read_text(
        encoding="utf-8"
    )
    assert "urllib" not in module_source
    assert "requests" not in module_source
    assert "httpx" not in module_source


def test_unknown_license_cannot_emit_suggestion() -> None:
    source = _source(license_id="LicenseRef-Unknown", license_policy="advisory_only")
    assert normalize_evidence(
        source,
        ({"evidence_kind": "lemma", "observed_form": "learn"},),
    ) == ()


def test_evidence_never_mints_cemm_authority() -> None:
    suggestions = normalize_evidence(
        _source(),
        (
            {
                "evidence_kind": "lemma",
                "observed_form": "learn",
                "observed_sense_key": "oewn:learn-v-1",
                "conflict_refs": [],
            },
        ),
    )
    forbidden = ("op:", "concept:", "event:", "relation:", "designation:")
    assert suggestions
    assert all(not row.suggestion_ref.startswith(forbidden) for row in suggestions)
    assert all(row.selectable is False for row in suggestions)


def test_source_policy_and_bounds_are_closed() -> None:
    with pytest.raises(ValueError, match="source family"):
        _source(source_family="unapproved_source")
    with pytest.raises(ValueError, match="license"):
        _source(license_id="LicenseRef-Unknown")
    with pytest.raises(ValueError, match="relative_path"):
        _source(relative_path="../escape.txt")
    with pytest.raises(ValueError, match="byte_length"):
        _source(byte_length=16 * 1024 * 1024 + 1)


def test_snapshot_round_trip_verifies_bytes_hash_revision_and_normalizer(
    tmp_path: Path,
) -> None:
    source = _source()
    snapshot = write_evidence_snapshot(
        tmp_path / "snapshot",
        ((source, b"evidence\n"),),
    )
    assert EvidenceSnapshot.from_directory(tmp_path / "snapshot") == snapshot

    raw = tmp_path / "snapshot" / source.relative_path
    raw.write_bytes(b"tampered\n")
    with pytest.raises(ValueError, match="byte length|sha256"):
        EvidenceSnapshot.from_directory(tmp_path / "snapshot")


def test_snapshot_rejects_manifest_path_traversal_and_source_overflow(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshot"
    source = _source()
    write_evidence_snapshot(snapshot_dir, ((source, b"evidence\n"),))
    manifest_path = snapshot_dir / "evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["relative_path"] = "../escape.txt"
    manifest_path.write_bytes(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )
    with pytest.raises(ValueError, match="relative_path"):
        EvidenceSnapshot.from_directory(snapshot_dir)

    with pytest.raises(ValueError, match="64 sources"):
        EvidenceSnapshot.create(sources=tuple(_source() for _ in range(65)))


def test_fetch_script_rejects_unsafe_urls_redirects_and_archives() -> None:
    spec = importlib.util.spec_from_file_location(
        "fetch_r4_authoring_evidence",
        ROOT / "scripts/fetch_r4_authoring_evidence.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with pytest.raises(ValueError, match="HTTPS"):
        module.FetchRequest.from_dict(
            {
                "source_family": "oewn",
                "url": "http://127.0.0.1/source.zip",
                "revision": "2024-edition",
                "expected_sha256": "0" * 64,
                "expected_byte_limit": 1024,
                "license_id": "PDDL-1.0",
                "license_policy": "suggestion_permitted",
                "output_directory": "snapshot",
            }
        )
    with pytest.raises(ValueError, match="redirect"):
        module.validate_redirect("https://example.test/a", "http://example.test/b")
    safe_buffer = io.BytesIO()
    with zipfile.ZipFile(safe_buffer, "w") as archive:
        archive.writestr("safe/source.txt", b"source")
    module.validate_zip_bytes(safe_buffer.getvalue())

    unsafe_buffer = io.BytesIO()
    with zipfile.ZipFile(unsafe_buffer, "w") as archive:
        archive.writestr("../escape.txt", b"escape")
    with pytest.raises(ValueError, match="unsafe ZIP path"):
        module.validate_zip_bytes(unsafe_buffer.getvalue())

    link_buffer = io.BytesIO()
    link_info = zipfile.ZipInfo("link")
    link_info.create_system = 3
    link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(link_buffer, "w") as archive:
        archive.writestr(link_info, "target")
    with pytest.raises(ValueError, match="link"):
        module.validate_zip_bytes(link_buffer.getvalue())


def test_fetch_publication_is_hash_checked_transactional_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "fetch_r4_authoring_evidence_publication",
        ROOT / "scripts/fetch_r4_authoring_evidence.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    payload = b"pinned evidence\n"
    request = module.FetchRequest.from_dict(
        {
            "source_family": "oewn",
            "url": "https://example.test/source",
            "revision": "2024-edition",
            "expected_sha256": hashlib.sha256(payload).hexdigest(),
            "expected_byte_limit": len(payload),
            "license_id": "PDDL-1.0",
            "license_policy": "suggestion_permitted",
            "output_directory": str(tmp_path / "snapshot"),
        }
    )
    monkeypatch.setattr(module, "_download", lambda _request: payload)
    source = module.fetch(request)
    assert module.fetch(request) == source

    raw_path = tmp_path / "snapshot" / source.relative_path
    raw_path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="byte length|sha256"):
        module.fetch(request)

    wrong_hash = module.FetchRequest.from_dict(
        {
            **{
                "source_family": request.source_family,
                "url": request.url,
                "revision": request.revision,
                "expected_byte_limit": request.expected_byte_limit,
                "license_id": request.license_id,
                "license_policy": request.license_policy,
                "output_directory": str(tmp_path / "other"),
            },
            "expected_sha256": "0" * 64,
        }
    )
    with pytest.raises(ValueError, match="SHA-256"):
        module.fetch(wrong_hash)


def test_evidence_manifest_schema_is_draft_2020_12() -> None:
    schema = json.loads(
        (ROOT / "schemas/r4_authoring_evidence_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
