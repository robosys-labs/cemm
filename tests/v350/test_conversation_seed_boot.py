import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOT = ROOT / "cemm/data/v350/release/boot.sqlite"
MANIFEST = ROOT / "cemm/data/v350/manifest.json"


def _payloads(connection: sqlite3.Connection, kind: str) -> list[dict]:
    rows = connection.execute(
        "SELECT payload_json FROM record_index WHERE record_kind=? ORDER BY record_ref,revision",
        (kind,),
    ).fetchall()
    return [json.loads(str(row[0])) for row in rows]


def test_conversation_seed_source_has_no_duplicate_record_identities():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fields = {
        "argument_frame": "frame_ref",
        "channel_adapter_contract": "contract_ref",
        "construction": "construction_ref",
        "evidence": "evidence_ref",
        "form_sense_link": "link_ref",
        "identity_facet": "identity_facet_ref",
        "language_form": "form_ref",
        "language_pack": "pack_ref",
        "lexical_sense": "sense_ref",
        "linearization_rule": "rule_ref",
        "morphology_rule": "rule_ref",
        "referent": "referent_ref",
        "response_policy_rule": "rule_ref",
        "response_transform_rule": "rule_ref",
        "schema": "schema_ref",
        "semantic_analyzer_contract": "contract_ref",
        "semantic_application": "application_ref",
    }
    seen = {}
    duplicates = []
    for module in manifest["modules"]:
        kind = module["record_kind"]
        field = fields.get(kind)
        if field is None:
            continue
        path = ROOT / "cemm/data/v350" / module["path"]
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            document = json.loads(raw)
            key = (kind, document[field], int(document.get("revision", 1)))
            location = f"{module['path']}:{line_number}"
            if key in seen:
                duplicates.append((key, seen[key], location))
            else:
                seen[key] = location
    assert duplicates == []


def test_conversation_seed_boot_authority_is_present_after_full_cutover():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    capabilities = manifest["metadata"]["release_capabilities"]
    assert capabilities["realization_languages"] == ["en", "fr", "sw"]
    assert capabilities["external_operations"] == []
    assert capabilities["epistemic_admission"] is True
    assert capabilities["generic_inference"] is True
    assert manifest["metadata"]["runtime_cutover"] is True

    connection = sqlite3.connect(f"file:{BOOT}?mode=ro", uri=True)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        counts = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT record_kind,COUNT(*) FROM record_index GROUP BY record_kind"
            )
        }
        assert counts["response_policy_rule"] == 43
        assert counts["response_transform_rule"] == 43
        assert counts["argument_frame"] == 48
        assert counts["morphology_rule"] == 3
        assert counts["linearization_rule"] == 48
        assert counts["semantic_analyzer_contract"] == 2
        assert counts["channel_adapter_contract"] == 2
        assert counts.get("operation_adapter_contract", 0) == 0
    finally:
        connection.close()


def test_conversation_seed_policy_transform_mapping_is_exact():
    connection = sqlite3.connect(f"file:{BOOT}?mode=ro", uri=True)
    try:
        policies = [
            item
            for item in _payloads(connection, "response_policy_rule")
            if item["lifecycle_status"] == "active"
            and item["use_decision"] == "allow"
            and item["use_operation"] == "response_policy"
        ]
        transforms = [
            item
            for item in _payloads(connection, "response_transform_rule")
            if item["lifecycle_status"] == "active" and item["use_decision"] == "allow"
        ]
        transform_by_goal = {}
        for transform in transforms:
            for goal in transform["goal_schema_pins"]:
                transform_by_goal.setdefault(tuple(goal), []).append(transform["rule_ref"])
        assert len(policies) == 43
        assert len(transforms) == 43
        assert [
            policy["rule_ref"]
            for policy in policies
            if len(transform_by_goal.get((policy["goal_schema_ref"], policy["goal_schema_revision"]), [])) != 1
        ] == []
    finally:
        connection.close()


def test_conversation_seed_realization_scope_is_en_fr_sw_after_activation_closure():
    connection = sqlite3.connect(f"file:{BOOT}?mode=ro", uri=True)
    try:
        senses = _payloads(connection, "lexical_sense")
        realize_by_pack = {}
        for sense in senses:
            if sense["lifecycle_status"] == "active" and sense["use_operation"] == "realize":
                realize_by_pack[sense["pack_ref"]] = realize_by_pack.get(sense["pack_ref"], 0) + 1
        assert realize_by_pack == {
            "language-pack:en": 45,
            "language-pack:fr": 45,
            "language-pack:sw": 45,
        }
    finally:
        connection.close()


def test_conversation_seed_constructions_do_not_leak_into_interpretation():
    connection = sqlite3.connect(f"file:{BOOT}?mode=ro", uri=True)
    try:
        seed_constructions = [
            item for item in _payloads(connection, "construction")
            if item["metadata"].get("phase") == 20
        ]
        assert seed_constructions
        assert all(item["metadata"].get("interpretation_enabled") is False for item in seed_constructions)
    finally:
        connection.close()
