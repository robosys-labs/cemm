import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOT = ROOT / "cemm/data/v350/release/boot.sqlite"
MANIFEST = ROOT / "cemm/data/v350/manifest.json"


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


def test_boot_authority_is_integrity_valid_after_runtime_cutover():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    capabilities = manifest["metadata"]["release_capabilities"]
    assert set(capabilities["realization_languages"]) >= {"en", "fr", "sw"}
    assert capabilities["epistemic_admission"] is True
    assert capabilities["generic_inference"] is True
    assert manifest["metadata"]["runtime_cutover"] is True

    connection = sqlite3.connect(f"file:{BOOT}?mode=ro", uri=True)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        present = {
            row[0]
            for row in connection.execute("SELECT DISTINCT record_kind FROM record_index")
        }
        assert {
            "schema",
            "referent",
            "language_pack",
            "language_form",
            "lexical_sense",
            "construction",
            "semantic_analyzer_contract",
            "channel_adapter_contract",
        } <= present
    finally:
        connection.close()
