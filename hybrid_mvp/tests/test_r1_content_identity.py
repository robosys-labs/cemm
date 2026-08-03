from __future__ import annotations

import json
import runpy
from dataclasses import replace
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.canonical import sha256_file, sha256_governed_text
from cemm_authoritative_hybrid.persistence import RevisionPin


def _pin() -> RevisionPin:
    return RevisionPin(
        authority_generation="authority:g1",
        world_revision=1,
        session_revision=2,
        episode_revision=3,
        effect_revision=4,
        model_identity="model:m1",
    )


def test_revision_pin_round_trip_preserves_every_field() -> None:
    pin = _pin()
    restored = RevisionPin.from_dict(pin.as_dict())
    assert restored == pin
    assert restored.revision_ref == pin.revision_ref


@pytest.mark.parametrize(
    "mutation",
    (
        pytest.param(
            lambda data: {key: value for key, value in data.items() if key != "world_revision"},
            id="missing-field",
        ),
        pytest.param(lambda data: {**data, "unknown": "value"}, id="unknown-field"),
        pytest.param(lambda data: {**data, "world_revision": True}, id="bool-revision"),
        pytest.param(lambda data: {**data, "authority_generation": 1}, id="generation-type"),
        pytest.param(lambda data: {**data, "model_identity": 7}, id="model-type"),
    ),
)
def test_revision_pin_deserializer_rejects_noncanonical_payload(mutation) -> None:
    with pytest.raises((TypeError, ValueError)):
        RevisionPin.from_dict(mutation(_pin().as_dict()))


def test_revision_pin_identity_covers_all_six_fields() -> None:
    pin = _pin()
    variants = (
        replace(pin, authority_generation="authority:g2"),
        replace(pin, world_revision=9),
        replace(pin, session_revision=9),
        replace(pin, episode_revision=9),
        replace(pin, effect_revision=9),
        replace(pin, model_identity="model:m2"),
    )
    assert all(candidate.revision_ref != pin.revision_ref for candidate in variants)


def test_governed_text_hash_is_bom_and_eol_portable(tmp_path: Path) -> None:
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    bom_cr = tmp_path / "bom-cr.json"
    lf.write_bytes(b'{"a":1}\n')
    crlf.write_bytes(b'{"a":1}\r\n')
    bom_cr.write_bytes(b'\xef\xbb\xbf{"a":1}\r')

    assert sha256_governed_text(lf) == sha256_governed_text(crlf)
    assert sha256_governed_text(lf) == sha256_governed_text(bom_cr)
    assert sha256_file(lf) != sha256_file(crlf)


def test_governed_text_hash_rejects_invalid_utf8(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        sha256_governed_text(invalid)


def test_authority_split_generator_hashes_portable_governed_owner_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = Path(__file__).parents[1]
    generated_root = tmp_path / "generated"
    scripts_dir = generated_root / "scripts"
    data_dir = generated_root / "data"
    authority_dir = data_dir / "authority"
    scripts_dir.mkdir(parents=True)
    authority_dir.mkdir(parents=True)

    generator_path = scripts_dir / "gen_authority_split.py"
    generator_path.write_bytes(
        (project_root / "scripts" / "gen_authority_split.py").read_bytes()
    )
    owner_names = {"kernel.json", "conversation.json", "state_operations.json"}
    current_authority_dir = project_root / "data" / "authority"
    owner_documents = [
        json.loads((current_authority_dir / name).read_text(encoding="utf-8"))
        for name in sorted(owner_names)
    ]
    legacy = {
        "atoms": [],
        "designations": [],
        "event_signatures": [],
        "rules": [],
        "capabilities": {},
        "permissions": [],
        "adapters": [],
        "operator_roles": {},
        "value_dimensions": {},
    }
    for document in owner_documents:
        for field in (
            "atoms",
            "designations",
            "event_signatures",
            "rules",
            "permissions",
            "adapters",
        ):
            legacy[field].extend(document[field])
        for field in ("capabilities", "operator_roles", "value_dimensions"):
            legacy[field].update(document[field])
    (data_dir / "authority.json").write_bytes(
        json.dumps(legacy, sort_keys=True).encode("utf-8")
    )

    original_write_text = Path.write_text

    def write_text_with_reviewed_checkout_variants(
        path: Path, text: str, *args: object, **kwargs: object
    ) -> int:
        if path.parent == authority_dir and path.name in owner_names:
            lf_text = text.replace("\r\n", "\n").replace("\r", "\n")
            path.write_bytes(
                b"\xef\xbb\xbf" + lf_text.replace("\n", "\r\n").encode("utf-8")
            )
            return len(text)
        return original_write_text(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write_text_with_reviewed_checkout_variants)
    runpy.run_path(str(generator_path), run_name="__main__")

    manifest_path = authority_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for owner in manifest["owners"]:
        owner_path = authority_dir / owner["path"]
        raw = owner_path.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")
        assert b"\r\n" in raw
        assert owner["sha256"] == sha256_governed_text(owner_path)
        assert owner["sha256"] != sha256_file(owner_path)

    crlf_bom_link = AuthorityLinker().link_path(manifest_path)

    for owner in manifest["owners"]:
        owner_path = authority_dir / owner["path"]
        raw = owner_path.read_bytes()[3:]
        owner_path.write_bytes(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))

    lf_link = AuthorityLinker().link_path(manifest_path)
    assert lf_link.generation == crlf_bom_link.generation


__cemm_test_inventory__ = {
    "tests/test_r1_content_identity.py::test_revision_pin_round_trip_preserves_every_field": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-round-trip-complete",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "061801f27216492ee2bf109fbb495d809243f4ed085fa0dc6a49d8b95b740af5",
    },
    "tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[missing-field]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-rejects-missing-field",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "356b19e10c7042931173a027d9dabbd52ed80ade3be2e20ffc748bfd1100ce07",
    },
    "tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[unknown-field]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-rejects-unknown-field",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "356b19e10c7042931173a027d9dabbd52ed80ade3be2e20ffc748bfd1100ce07",
    },
    "tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[bool-revision]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-rejects-bool-revision",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "356b19e10c7042931173a027d9dabbd52ed80ade3be2e20ffc748bfd1100ce07",
    },
    "tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[generation-type]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-rejects-generation-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "356b19e10c7042931173a027d9dabbd52ed80ade3be2e20ffc748bfd1100ce07",
    },
    "tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[model-type]": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-rejects-model-type",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "356b19e10c7042931173a027d9dabbd52ed80ade3be2e20ffc748bfd1100ce07",
    },
    "tests/test_r1_content_identity.py::test_revision_pin_identity_covers_all_six_fields": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-revision-pin-identity-covers-all-fields",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "5c745871b97829e9dbc9c24cc9302463e887e6c2c6c9ba933ccc9c454e01370b",
    },
    "tests/test_r1_content_identity.py::test_governed_text_hash_is_bom_and_eol_portable": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-governed-text-hash-portable",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "01867ac709c829dc340e5ac8dbc9fb2b81d2bc0235d6827d4bbd97acb93df96f",
    },
    "tests/test_r1_content_identity.py::test_governed_text_hash_rejects_invalid_utf8": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-governed-text-hash-rejects-invalid-utf8",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "71908b2a5961bc1b931da8ed45f3ecc3a6365e8d0e89ed7cd0b131c060f3f59f",
    },
    "tests/test_r1_content_identity.py::test_authority_split_generator_hashes_portable_governed_owner_text": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-authority-generator-governed-hash-portable",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-6",
        "owner_ref": "content-identity",
        "source_ast_sha256": "a7c388d69932b51026edb290156c0321e3d02fc225beaea654e1bf5d670ccdd3",
    },
}
