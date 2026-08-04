from __future__ import annotations

import json
import inspect
import runpy
from dataclasses import fields, replace
from pathlib import Path
from types import MappingProxyType

import pytest

import cemm_authoritative_hybrid.cycle as cycle_module
from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.canonical import sha256_file, sha256_governed_text, stable_ref
from cemm_authoritative_hybrid.cycle import (
    CycleResult,
    CycleStatus,
    Orientation,
    SemanticMode,
)
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


def _orientation(**changes: object) -> Orientation:
    values = {
        "session_ref": "session:one", "turn_ref": "turn:one",
        "source_text": "hello", "mode": SemanticMode.QUERY,
        "participant_frame": "participant-frame:one",
        "temporal_frame": "temporal-frame:one",
        "participants": ("participant:user", "participant:system"),
        "active_turn_ref": "turn:one",
        "event_refs": ("event:session:one", "turn:one"),
        "focus_refs": ("event:greeting",),
        "obligation_refs": ("obligation:one",),
        "capability_summary": ("cap:answer",),
        "permission_summary": ("permission:answer",),
        "budgets": {"input_tokens": 64}, "scanned_atom_count": 0,
        "index_probes": ("designations:for_surface",),
        "visited_refs": ("event:greeting",), "revision_pin": _pin(),
        "cache_key": "orientation-cache:one",
    }
    values.update(changes)
    return Orientation.create(**values)


def test_orientation_abi1_round_trip_is_strict_and_omits_cache_metadata() -> None:
    orientation = _orientation()
    payload = orientation.as_dict()
    assert Orientation.from_dict(payload) == replace(orientation, cache_key=None)
    assert tuple(payload) == (
        "abi_version", "orientation_ref", "session_ref", "turn_ref",
        "source_text", "mode", "participant_frame", "temporal_frame",
        "participants", "active_turn_ref", "event_refs", "focus_refs",
        "obligation_refs", "capability_summary", "permission_summary",
        "budgets", "scanned_atom_count", "index_probes", "visited_refs",
        "revision_pin",
    )
    assert "cache_key" not in payload
    assert "authority_generation" not in payload
    assert Orientation.from_dict(payload).cache_key is None


@pytest.mark.parametrize(
    "mutation",
    (
        pytest.param(lambda data: {key: value for key, value in data.items() if key != "turn_ref"}, id="missing"),
        pytest.param(lambda data: {**data, "unknown": 1}, id="extra"),
        pytest.param(lambda data: {**data, "participants": tuple(data["participants"])}, id="tuple-wire"),
        pytest.param(lambda data: {**data, "budgets": MappingProxyType(data["budgets"])}, id="mapping-wire"),
        pytest.param(lambda data: {**data, "abi_version": True}, id="bool-abi"),
        pytest.param(lambda data: {**data, "scanned_atom_count": False}, id="bool-count"),
        pytest.param(lambda data: {**data, "mode": SemanticMode.QUERY}, id="enum-wire"),
        pytest.param(lambda data: {**data, "revision_pin": _pin()}, id="pin-wire"),
        pytest.param(lambda data: {**data, "orientation_ref": "orientation:forged"}, id="forged-ref"),
    ),
    ids=("missing", "extra", "tuple-wire", "mapping-wire", "bool-abi", "bool-count", "enum-wire", "pin-wire", "forged-ref"),
)
def test_orientation_abi1_rejects_noncanonical_wire_payload(mutation) -> None:
    with pytest.raises((TypeError, ValueError)):
        Orientation.from_dict(mutation(_orientation().as_dict()))


def test_orientation_identity_covers_every_serialized_identity_field() -> None:
    original = _orientation()
    variants = (
        _orientation(session_ref="session:two"), _orientation(turn_ref="turn:two"),
        _orientation(source_text="hello!"), _orientation(mode=SemanticMode.OBSERVE),
        _orientation(participant_frame="participant-frame:two"),
        _orientation(temporal_frame="temporal-frame:two"),
        _orientation(participants=("participant:user",)),
        _orientation(active_turn_ref="turn:two"),
        _orientation(event_refs=("event:session:two",)),
        _orientation(focus_refs=("event:other",)),
        _orientation(obligation_refs=("obligation:two",)),
        _orientation(capability_summary=("cap:other",)),
        _orientation(permission_summary=("permission:other",)),
        _orientation(budgets={"input_tokens": 63}),
        _orientation(scanned_atom_count=1),
        _orientation(index_probes=("focus_store:refs",)),
        _orientation(visited_refs=("event:other",)),
        _orientation(revision_pin=replace(_pin(), world_revision=9)),
    )
    assert len({original.orientation_ref, *(row.orientation_ref for row in variants)}) == len(variants) + 1


def test_orientation_cache_key_is_transient_and_identity_independent() -> None:
    first = _orientation(cache_key="cache:first")
    second = _orientation(cache_key="cache:second")
    absent = _orientation(cache_key=None)
    assert first.orientation_ref == second.orientation_ref == absent.orientation_ref
    assert first.as_dict() == second.as_dict() == absent.as_dict()


def test_orientation_budgets_are_defensively_deep_frozen_and_bounded() -> None:
    source = {"input_tokens": 64}
    orientation = _orientation(budgets=source)
    source["input_tokens"] = 1
    assert orientation.budgets == {"input_tokens": 64}
    assert isinstance(orientation.budgets, MappingProxyType)
    with pytest.raises(TypeError):
        orientation.budgets["input_tokens"] = 2  # type: ignore[index]
    for invalid in (
        {"": 1}, {"k" * 257: 1}, {"tokens": True}, {"tokens": -1},
        {"tokens": 2**63}, {f"budget:{index}": index for index in range(65)},
    ):
        with pytest.raises((TypeError, ValueError)):
            _orientation(budgets=invalid)


def test_orientation_create_rejects_hostile_content_before_hashing(monkeypatch) -> None:
    def forbidden_hash(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("hostile Orientation content reached stable_ref")

    monkeypatch.setattr(cycle_module, "stable_ref", forbidden_hash)
    invalid = (
        {"source_text": "x" * 16_385},
        {"participants": tuple(f"participant:{index}" for index in range(1_025))},
        {"participants": ["participant:user"]},
        {"scanned_atom_count": 257},
    )
    for changes in invalid:
        with pytest.raises((TypeError, ValueError)):
            _orientation(**changes)


def test_orientation_from_dict_rejects_hostile_wire_list_before_hashing(monkeypatch) -> None:
    payload = _orientation().as_dict()
    payload["participants"] = [f"participant:{index}" for index in range(1_025)]

    def forbidden_hash(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("hostile Orientation wire content reached stable_ref")

    monkeypatch.setattr(cycle_module, "stable_ref", forbidden_hash)
    with pytest.raises(ValueError, match="bound"):
        Orientation.from_dict(payload)

def test_orientation_projection_and_decode_hash_complete_content_once(monkeypatch) -> None:
    real_stable_ref = cycle_module.stable_ref
    calls: list[str] = []

    def recording_hash(namespace: str, payload: object) -> str:
        calls.append(namespace)
        return real_stable_ref(namespace, payload)

    monkeypatch.setattr(cycle_module, "stable_ref", recording_hash)
    created = _orientation()
    assert calls == ["orientation"]

    payload = created.as_dict()
    calls.clear()
    Orientation.from_dict(payload)
    assert calls == ["orientation"]

def test_orientation_has_no_lineage_or_meaning_defaults() -> None:
    parameters = inspect.signature(Orientation).parameters
    assert tuple(field.name for field in fields(Orientation)) == (
        "abi_version", "orientation_ref", "session_ref", "turn_ref",
        "source_text", "mode", "participant_frame", "temporal_frame",
        "participants", "active_turn_ref", "event_refs", "focus_refs",
        "obligation_refs", "capability_summary", "permission_summary",
        "budgets", "scanned_atom_count", "index_probes", "visited_refs",
        "revision_pin", "cache_key",
    )
    assert all(
        parameter.default is inspect.Parameter.empty
        for name, parameter in parameters.items()
        if name != "cache_key"
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
    ids=("missing-field", "unknown-field", "bool-revision", "generation-type", "model-type"),
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


class _RevisionStr(str):
    pass


class _RevisionInt(int):
    pass


class _RevisionDict(dict):
    pass


def test_revision_pin_constructor_rejects_invalid_exact_content() -> None:
    maximum = 2**63 - 1
    invalid_fields = (
        ("authority_generation", ""),
        ("authority_generation", "g" * 257),
        ("authority_generation", _RevisionStr("authority:g1")),
        ("model_identity", ""),
        ("model_identity", "m" * 257),
        ("model_identity", _RevisionStr("model:m1")),
    ) + tuple(
        (field_name, invalid_value)
        for field_name in (
            "world_revision",
            "session_revision",
            "episode_revision",
            "effect_revision",
        )
        for invalid_value in (-1, maximum + 1, True, 1.0, _RevisionInt(1))
    )

    for field_name, invalid_value in invalid_fields:
        with pytest.raises((TypeError, ValueError)):
            replace(_pin(), **{field_name: invalid_value})


def test_revision_pin_from_dict_requires_exact_canonical_payload() -> None:
    payload = _pin().as_dict()
    invalid_payloads = (
        _RevisionDict(payload),
        MappingProxyType(payload),
        tuple(payload.items()),
        {key: value for key, value in payload.items() if key != "world_revision"},
        {**payload, "abi_version": 1},
        {**payload, "authority_generation": 1},
        {**payload, "world_revision": "1"},
        {**payload, "session_revision": False},
        {**payload, "model_identity": 7},
    )

    for invalid_payload in invalid_payloads:
        with pytest.raises((TypeError, ValueError)):
            RevisionPin.from_dict(invalid_payload)


def test_cycle_result_requires_authentic_final_revision_pin() -> None:
    with pytest.raises(TypeError):
        CycleResult(cycle_ref="cycle:test", status=CycleStatus.PARTIAL)


def test_revision_pin_from_dict_rejects_nonexact_string_keys() -> None:
    payload = _pin().as_dict()
    payload[_RevisionStr("world_revision")] = payload.pop("world_revision")

    with pytest.raises(TypeError):
        RevisionPin.from_dict(payload)


def test_revision_pin_from_dict_rejects_oversized_dict_before_key_validation() -> None:
    payload = _pin().as_dict()
    payload.update({f"extra_{index}": index for index in range(1_000)})

    with pytest.raises(ValueError, match="exactly six fields"):
        RevisionPin.from_dict(payload)


def test_revision_pin_wire_contract_and_inclusive_boundaries() -> None:
    pin = RevisionPin(
        authority_generation="a" * 256,
        world_revision=0,
        session_revision=2**63 - 1,
        episode_revision=0,
        effect_revision=2**63 - 1,
        model_identity="m" * 256,
    )
    expected_fields = (
        "authority_generation",
        "world_revision",
        "session_revision",
        "episode_revision",
        "effect_revision",
        "model_identity",
    )

    assert tuple(field.name for field in fields(pin)) == expected_fields
    assert tuple(pin.as_dict()) == expected_fields
    assert pin.revision_ref == stable_ref("revision_pin", pin.as_dict())


def _forged_orientation_revision_pins() -> tuple[RevisionPin, RevisionPin]:
    values = _pin().as_dict()
    missing = object.__new__(RevisionPin)
    invalid = object.__new__(RevisionPin)
    for name, value in values.items():
        if name != "effect_revision":
            object.__setattr__(missing, name, value)
        object.__setattr__(invalid, name, True if name == "world_revision" else value)
    return missing, invalid


def _forbid_orientation_hash(monkeypatch) -> None:
    def forbidden_hash(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("forged revision pin reached Orientation stable_ref")

    monkeypatch.setattr(cycle_module, "stable_ref", forbidden_hash)


def test_orientation_create_rejects_forged_exact_revision_pins_before_hash(
    monkeypatch,
) -> None:
    pins = _forged_orientation_revision_pins()
    _forbid_orientation_hash(monkeypatch)

    for pin in pins:
        with pytest.raises((TypeError, ValueError), match="revision_pin"):
            _orientation(revision_pin=pin)


def test_orientation_direct_constructor_rejects_forged_exact_revision_pins_before_hash(
    monkeypatch,
) -> None:
    original = _orientation()
    pins = _forged_orientation_revision_pins()
    _forbid_orientation_hash(monkeypatch)

    for pin in pins:
        with pytest.raises((TypeError, ValueError), match="revision_pin"):
            replace(original, revision_pin=pin)

class _OrientationSubclass(Orientation):
    pass


def test_orientation_factories_reject_subclasses() -> None:
    original = _orientation()
    fields = {
        "session_ref": original.session_ref,
        "turn_ref": original.turn_ref,
        "source_text": original.source_text,
        "mode": original.mode,
        "participant_frame": original.participant_frame,
        "temporal_frame": original.temporal_frame,
        "participants": original.participants,
        "active_turn_ref": original.active_turn_ref,
        "event_refs": original.event_refs,
        "focus_refs": original.focus_refs,
        "obligation_refs": original.obligation_refs,
        "capability_summary": original.capability_summary,
        "permission_summary": original.permission_summary,
        "budgets": original.budgets,
        "scanned_atom_count": original.scanned_atom_count,
        "index_probes": original.index_probes,
        "visited_refs": original.visited_refs,
        "revision_pin": original.revision_pin,
    }
    with pytest.raises(TypeError, match="exact Orientation"):
        _OrientationSubclass.create(**fields)
    with pytest.raises(TypeError, match="exact Orientation"):
        _OrientationSubclass.from_dict(original.as_dict())


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


__cemm_test_inventory__ = {'tests/test_r1_content_identity.py::test_authority_split_generator_hashes_portable_governed_owner_text': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-authority-generator-governed-hash-portable',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-6',
                                                                                                           'owner_ref': 'program-verifier',
                                                                                                           'source_ast_sha256': 'a7c388d69932b51026edb290156c0321e3d02fc225beaea654e1bf5d670ccdd3'},
 'tests/test_r1_content_identity.py::test_c1_cycle_receipt_and_result_have_exact_required_abi2_fields': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-c1-cycle-result-required-fields',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Slice-C1',
                                                                                                         'owner_ref': 'program-verifier',
                                                                                                         'source_ast_sha256': '48c2920ae5513043664325565a44daf4004e68ce7f6f4edc82aae7a78d035433'},
 'tests/test_r1_content_identity.py::test_cycle_result_requires_authentic_final_revision_pin': {'activation_phase': 'R1',
                                                                                                'assertion_ref': 'assertion:r1-cycle-result-requires-final-pin',
                                                                                                'diagnostic_role': 'owner',
                                                                                                'introduced_by_task': 'R1-Slice-A',
                                                                                                'owner_ref': 'program-verifier',
                                                                                                'source_ast_sha256': '375c2ff3bee5e291608e2b78e5e1073bdfb0c4898cfcac12a942c6163bf54bb2'},
 'tests/test_r1_content_identity.py::test_governed_text_hash_is_bom_and_eol_portable': {'activation_phase': 'R1',
                                                                                        'assertion_ref': 'assertion:r1-governed-text-hash-portable',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R1-Task-6',
                                                                                        'owner_ref': 'program-verifier',
                                                                                        'source_ast_sha256': '01867ac709c829dc340e5ac8dbc9fb2b81d2bc0235d6827d4bbd97acb93df96f'},
 'tests/test_r1_content_identity.py::test_governed_text_hash_rejects_invalid_utf8': {'activation_phase': 'R1',
                                                                                     'assertion_ref': 'assertion:r1-governed-text-hash-rejects-invalid-utf8',
                                                                                     'diagnostic_role': 'owner',
                                                                                     'introduced_by_task': 'R1-Task-6',
                                                                                     'owner_ref': 'program-verifier',
                                                                                     'source_ast_sha256': '71908b2a5961bc1b931da8ed45f3ecc3a6365e8d0e89ed7cd0b131c060f3f59f'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[bool-abi]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-bool-abi',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Slice-B',
                                                                                                          'owner_ref': 'runtime-path',
                                                                                                          'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[bool-count]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-bool-count',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Slice-B',
                                                                                                            'owner_ref': 'runtime-path',
                                                                                                            'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[enum-wire]': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-enum-wire',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Slice-B',
                                                                                                           'owner_ref': 'runtime-path',
                                                                                                           'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[extra]': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-extra',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Slice-B',
                                                                                                       'owner_ref': 'runtime-path',
                                                                                                       'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[forged-ref]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-forged-ref',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Slice-B',
                                                                                                            'owner_ref': 'runtime-path',
                                                                                                            'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[mapping-wire]': {'activation_phase': 'R1',
                                                                                                              'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-mapping-wire',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'R1-Slice-B',
                                                                                                              'owner_ref': 'runtime-path',
                                                                                                              'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[missing]': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-missing',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Slice-B',
                                                                                                         'owner_ref': 'runtime-path',
                                                                                                         'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[pin-wire]': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-pin-wire',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Slice-B',
                                                                                                          'owner_ref': 'runtime-path',
                                                                                                          'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_rejects_noncanonical_wire_payload[tuple-wire]': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-slice-b-orientation-rejects-tuple-wire',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Slice-B',
                                                                                                            'owner_ref': 'runtime-path',
                                                                                                            'source_ast_sha256': '211a763c592f869a22efe560440ef815f7b3e41f5953f2949d3bcdd4066e1792'},
 'tests/test_r1_content_identity.py::test_orientation_abi1_round_trip_is_strict_and_omits_cache_metadata': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-slice-b-orientation-roundtrip',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Slice-B',
                                                                                                            'owner_ref': 'runtime-path',
                                                                                                            'source_ast_sha256': 'de115e1fa3c31ab6bc1e37559eaeb0dadff8d65b71665340a126361ff673421d'},
 'tests/test_r1_content_identity.py::test_orientation_budgets_are_defensively_deep_frozen_and_bounded': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-slice-b-orientation-budgets-frozen-bounded',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Slice-B',
                                                                                                         'owner_ref': 'runtime-path',
                                                                                                         'source_ast_sha256': '2267eb1b629686dc3c6db7f7984a871c5ad577d336f1488df52259e3c77286c1'},
 'tests/test_r1_content_identity.py::test_orientation_cache_key_is_transient_and_identity_independent': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-slice-b-orientation-cache-independent',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Slice-B',
                                                                                                         'owner_ref': 'runtime-path',
                                                                                                         'source_ast_sha256': 'a76fc2b153d3c63ffa26b350bd7c1e5bc438671c2661181a48f59b47ee871556'},
 'tests/test_r1_content_identity.py::test_orientation_create_rejects_forged_exact_revision_pins_before_hash': {'activation_phase': 'R1',
                                                                                                               'assertion_ref': 'assertion:r1-orientation-create-revalidates-revision-pin',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'R1-Slice-B',
                                                                                                               'owner_ref': 'runtime-path',
                                                                                                               'source_ast_sha256': 'cd7bbc5cf5b344baeea529cd5f05e81de5a20e0fba78d8bf9c2e535c4333b9f4'},
 'tests/test_r1_content_identity.py::test_orientation_create_rejects_hostile_content_before_hashing': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:r1-slice-b-orientation-prehash-create-bounds',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Slice-B',
                                                                                                       'owner_ref': 'runtime-path',
                                                                                                       'source_ast_sha256': '139b600861005d20449fd90217453cea424e1e76c80a14d5e08d1a8104dee85a'},
 'tests/test_r1_content_identity.py::test_orientation_direct_constructor_rejects_forged_exact_revision_pins_before_hash': {'activation_phase': 'R1',
                                                                                                                           'assertion_ref': 'assertion:r1-orientation-direct-revalidates-revision-pin',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'R1-Slice-B',
                                                                                                                           'owner_ref': 'runtime-path',
                                                                                                                           'source_ast_sha256': '6bf9c27bc24c0ee847a989cdf62ba8ae9bd056189d1e3e97bedd168380b5569b'},
 'tests/test_r1_content_identity.py::test_orientation_factories_reject_subclasses': {'activation_phase': 'R1',
                                                                                     'assertion_ref': 'assertion:r1-orientation-factories-reject-subclasses',
                                                                                     'diagnostic_role': 'owner',
                                                                                     'introduced_by_task': 'R1-Slice-B',
                                                                                     'owner_ref': 'runtime-path',
                                                                                     'source_ast_sha256': '399eb74bd884fab1aaee93e318f5be07c7023cfae39e3b787253d01e414ac908'},
 'tests/test_r1_content_identity.py::test_orientation_from_dict_rejects_hostile_wire_list_before_hashing': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-slice-b-orientation-prehash-wire-bounds',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'R1-Slice-B',
                                                                                                            'owner_ref': 'runtime-path',
                                                                                                            'source_ast_sha256': '6327d6108aeb80bfb0e4fa2215a0e47ce219645f35a6c6402f3d0a0d2c785bf3'},
 'tests/test_r1_content_identity.py::test_orientation_has_no_lineage_or_meaning_defaults': {'activation_phase': 'R1',
                                                                                            'assertion_ref': 'assertion:r1-slice-b-orientation-no-default-lineage',
                                                                                            'diagnostic_role': 'owner',
                                                                                            'introduced_by_task': 'R1-Slice-B',
                                                                                            'owner_ref': 'runtime-path',
                                                                                            'source_ast_sha256': 'f0422e45e0d0b7c575629b726cd02065642544d1d1c4ae6476f86185b016af83'},
 'tests/test_r1_content_identity.py::test_orientation_identity_covers_every_serialized_identity_field': {'activation_phase': 'R1',
                                                                                                         'assertion_ref': 'assertion:r1-slice-b-orientation-identity-fields',
                                                                                                         'diagnostic_role': 'owner',
                                                                                                         'introduced_by_task': 'R1-Slice-B',
                                                                                                         'owner_ref': 'runtime-path',
                                                                                                         'source_ast_sha256': '118c0b85b62793142f3a71e8fedcd06ab4c95a004fe77ad469077436d0f918f3'},
 'tests/test_r1_content_identity.py::test_orientation_projection_and_decode_hash_complete_content_once': {'activation_phase': 'R1',
                                                                                                          'assertion_ref': 'assertion:r1-slice-b-orientation-single-content-hash',
                                                                                                          'diagnostic_role': 'owner',
                                                                                                          'introduced_by_task': 'R1-Slice-B',
                                                                                                          'owner_ref': 'runtime-path',
                                                                                                          'source_ast_sha256': '3a7fe51495c0886306ee7e1728e5c7da696098d8e5db03ccbe79b59738558571'},
 'tests/test_r1_content_identity.py::test_revision_pin_constructor_rejects_invalid_exact_content': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:r1-revision-pin-rejects-invalid-constructor-content',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Slice-A',
                                                                                                    'owner_ref': 'program-verifier',
                                                                                                    'source_ast_sha256': '77e7cd729412458cdcb5f99fe02568a6fefd173451da0ee927f0cf471cf087ef'},
 'tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[bool-revision]': {'activation_phase': 'R1',
                                                                                                                   'assertion_ref': 'assertion:r1-revision-pin-rejects-bool-revision',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R1-Task-6',
                                                                                                                   'owner_ref': 'program-verifier',
                                                                                                                   'source_ast_sha256': '81253fa36d01b885d138b0361144afe1a44f23a446f669fda75f52baea95aa73'},
 'tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[generation-type]': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:r1-revision-pin-rejects-generation-type',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-6',
                                                                                                                     'owner_ref': 'program-verifier',
                                                                                                                     'source_ast_sha256': '81253fa36d01b885d138b0361144afe1a44f23a446f669fda75f52baea95aa73'},
 'tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[missing-field]': {'activation_phase': 'R1',
                                                                                                                   'assertion_ref': 'assertion:r1-revision-pin-rejects-missing-field',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R1-Task-6',
                                                                                                                   'owner_ref': 'program-verifier',
                                                                                                                   'source_ast_sha256': '81253fa36d01b885d138b0361144afe1a44f23a446f669fda75f52baea95aa73'},
 'tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[model-type]': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:r1-revision-pin-rejects-model-type',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-6',
                                                                                                                'owner_ref': 'program-verifier',
                                                                                                                'source_ast_sha256': '81253fa36d01b885d138b0361144afe1a44f23a446f669fda75f52baea95aa73'},
 'tests/test_r1_content_identity.py::test_revision_pin_deserializer_rejects_noncanonical_payload[unknown-field]': {'activation_phase': 'R1',
                                                                                                                   'assertion_ref': 'assertion:r1-revision-pin-rejects-unknown-field',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'R1-Task-6',
                                                                                                                   'owner_ref': 'program-verifier',
                                                                                                                   'source_ast_sha256': '81253fa36d01b885d138b0361144afe1a44f23a446f669fda75f52baea95aa73'},
 'tests/test_r1_content_identity.py::test_revision_pin_from_dict_rejects_nonexact_string_keys': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-revision-pin-codec-rejects-nonexact-keys',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Slice-A',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': '94287517b38d41b45434194f4c25d5d688441af1d4b32880589c18aa26c6c2e1'},
 'tests/test_r1_content_identity.py::test_revision_pin_from_dict_rejects_oversized_dict_before_key_validation': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:r1-revision-pin-codec-bounds-payload-before-key-scan',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Slice-A',
                                                                                                                 'owner_ref': 'program-verifier',
                                                                                                                 'source_ast_sha256': '729c0005da739f6312326518802b8b521f88f9afa30b0b7a39affd3893ca82a6'},
 'tests/test_r1_content_identity.py::test_revision_pin_from_dict_requires_exact_canonical_payload': {'activation_phase': 'R1',
                                                                                                     'assertion_ref': 'assertion:r1-revision-pin-codec-requires-exact-dict',
                                                                                                     'diagnostic_role': 'owner',
                                                                                                     'introduced_by_task': 'R1-Slice-A',
                                                                                                     'owner_ref': 'program-verifier',
                                                                                                     'source_ast_sha256': '584b6dcb894c9fa0a0b65fa8b35848bad2a4e5a9b5636a565fb7abc7c97f3e6d'},
 'tests/test_r1_content_identity.py::test_revision_pin_identity_covers_all_six_fields': {'activation_phase': 'R1',
                                                                                         'assertion_ref': 'assertion:r1-revision-pin-identity-covers-all-fields',
                                                                                         'diagnostic_role': 'owner',
                                                                                         'introduced_by_task': 'R1-Task-6',
                                                                                         'owner_ref': 'program-verifier',
                                                                                         'source_ast_sha256': '5c745871b97829e9dbc9c24cc9302463e887e6c2c6c9ba933ccc9c454e01370b'},
 'tests/test_r1_content_identity.py::test_revision_pin_round_trip_preserves_every_field': {'activation_phase': 'R1',
                                                                                           'assertion_ref': 'assertion:r1-revision-pin-round-trip-complete',
                                                                                           'diagnostic_role': 'owner',
                                                                                           'introduced_by_task': 'R1-Task-6',
                                                                                           'owner_ref': 'program-verifier',
                                                                                           'source_ast_sha256': '061801f27216492ee2bf109fbb495d809243f4ed085fa0dc6a49d8b95b740af5'},
 'tests/test_r1_content_identity.py::test_revision_pin_wire_contract_and_inclusive_boundaries': {'activation_phase': 'R1',
                                                                                                 'assertion_ref': 'assertion:r1-revision-pin-wire-contract-boundaries',
                                                                                                 'diagnostic_role': 'owner',
                                                                                                 'introduced_by_task': 'R1-Slice-A',
                                                                                                 'owner_ref': 'program-verifier',
                                                                                                 'source_ast_sha256': '0972ba04d54ab3508665f684c769a14c8a2e885faa4df178ddcb8c55273ac02d'}}


def test_c1_cycle_receipt_and_result_have_exact_required_abi2_fields() -> None:
    assert tuple(field.name for field in fields(cycle_module.PhaseReceipt)) == (
        "abi_version", "receipt_ref", "cycle_ref", "phase", "input_refs",
        "output_refs", "input_revision_pin", "output_revision_pin",
        "disposition", "rejection_codes", "budget_use", "duration_ns",
    )
    assert tuple(field.name for field in fields(cycle_module.CycleResult)) == (
        "abi_version", "cycle_ref", "input_ref", "status", "orientation",
        "proposal", "verification", "evaluation", "effect_receipt",
        "response_meaning", "realization_receipt", "gap_receipt",
        "phase_material", "trace", "final_revision_pin",
    )
    for owner in (cycle_module.PhaseReceipt, cycle_module.CycleResult):
        assert all(
            parameter.default is inspect.Parameter.empty
            for parameter in inspect.signature(owner).parameters.values()
        )
