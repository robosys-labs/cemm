from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cemm.authority import (
    AuthorityBundleError,
    GENERIC_FOUNDATION_RULES,
    load_documents,
    validate_documents,
    validate_pack_constants,
)
from cemm.store import Store

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "cemm/data"
PACKS = ROOT / "cemm/language_packs"


class FoundationIntegrityTests(unittest.TestCase):
    def data_paths(self):
        return sorted(DATA.glob("*.json"))

    def write_documents(self, root: Path, payloads):
        paths = []
        for name, payload in payloads:
            path = root / name
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths.append(path)
        return paths

    def test_complete_repository_authority_links(self):
        report = validate_documents(load_documents(self.data_paths()), require_foundations=True)
        self.assertGreater(report.atom_count, 0)
        self.assertGreater(report.fact_count, 0)
        self.assertEqual(len(report.bundle_hash), 64)

    def test_missing_cross_file_relation_fails_before_any_database_write(self):
        payloads = [(path.name, json.loads(path.read_text(encoding="utf-8"))) for path in self.data_paths()]
        for _name, payload in payloads:
            payload["atoms"] = [
                atom for atom in payload.get("atoms", ())
                if atom.get("ref") != "rel:state_dimension"
            ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.write_documents(root, payloads)
            store = Store(root / "broken.sqlite")
            before = {
                "generation": store.generation,
                "atoms": store.db.execute("SELECT count(*) FROM atoms").fetchone()[0],
                "observations": store.db.execute("SELECT count(*) FROM observations").fetchone()[0],
            }
            with self.assertRaises(AuthorityBundleError):
                store.import_bundle(paths)
            after = {
                "generation": store.generation,
                "atoms": store.db.execute("SELECT count(*) FROM atoms").fetchone()[0],
                "observations": store.db.execute("SELECT count(*) FROM observations").fetchone()[0],
            }
            self.assertEqual(before, after)
            store.db.close()

    def test_generic_foundations_live_in_base_only(self):
        base_path = DATA / "base.json"
        base = json.loads(base_path.read_text(encoding="utf-8"))
        base_atoms = {item["ref"] for item in base.get("atoms", ())}
        base_rules = {item["rule_ref"] for item in base.get("rules", ())}
        required = {
            "rel:state_dimension", "rel:state_value", "rel:value_of_dimension",
            "rel:subtype_of", "rel:subrelation_of", "rel:subject_type",
            "rel:implies_subject_state", "rel:implies_object_state",
        }
        self.assertTrue(required <= base_atoms)
        self.assertTrue(GENERIC_FOUNDATION_RULES <= base_rules)
        for path in self.data_paths():
            if path == base_path:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(required & {item["ref"] for item in data.get("atoms", ())})
            self.assertFalse(GENERIC_FOUNDATION_RULES & {item["rule_ref"] for item in data.get("rules", ())})

    def test_concept_hierarchy_is_not_instance_typing(self):
        kinds = {
            item["ref"]: item["kind"]
            for path in self.data_paths()
            for item in json.loads(path.read_text(encoding="utf-8")).get("atoms", ())
        }
        for path in self.data_paths():
            data = json.loads(path.read_text(encoding="utf-8"))
            for fact in data.get("facts", ()):
                if fact.get("operator") != "op:type":
                    continue
                args = fact.get("args", {})
                self.assertFalse(
                    kinds.get(args.get("role:instance")) == "concept"
                    and kinds.get(args.get("role:class")) == "concept",
                    f"{path.name}:{fact.get('fact_ref')} encodes concept hierarchy as instance type",
                )

    def test_every_implied_state_spec_has_exact_dimension_and_value(self):
        dimensions = {}
        values = {}
        implied = set()
        for path in self.data_paths():
            data = json.loads(path.read_text(encoding="utf-8"))
            for fact in data.get("facts", ()):
                if fact.get("operator") != "op:relation":
                    continue
                args = fact.get("args", {})
                subject, relation, obj = (
                    args.get("role:subject"), args.get("role:relation"), args.get("role:object")
                )
                if relation == "rel:state_dimension":
                    dimensions.setdefault(subject, set()).add(obj)
                elif relation == "rel:state_value":
                    values.setdefault(subject, set()).add(obj)
                elif relation in {"rel:implies_subject_state", "rel:implies_object_state"}:
                    implied.add(obj)
        for spec in implied:
            self.assertEqual(len(dimensions.get(spec, ())), 1, spec)
            self.assertEqual(len(values.get(spec, ())), 1, spec)

    def test_name_is_a_designation_family(self):
        base = json.loads((DATA / "base.json").read_text(encoding="utf-8"))
        atoms = {item["ref"]: item for item in base.get("atoms", ())}
        self.assertEqual(atoms["label:name"]["kind"], "label_type")
        subtype_pairs = {
            (fact.get("args", {}).get("role:subject"), fact.get("args", {}).get("role:object"))
            for fact in base.get("facts", ())
            if fact.get("operator") == "op:relation"
            and fact.get("args", {}).get("role:relation") == "rel:subtype_of"
        }
        self.assertIn(("label:name_full", "label:name"), subtype_pairs)
        self.assertIn(("label:name_alias", "label:name"), subtype_pairs)

    def test_pack_constants_link_to_complete_authority(self):
        atom_refs = {
            item["ref"]
            for path in self.data_paths()
            for item in json.loads(path.read_text(encoding="utf-8")).get("atoms", ())
        }
        validate_pack_constants(sorted(PACKS.glob("*.json")), atom_refs)

    def test_pointer_ordering_contract_is_explicit(self):
        text = (ROOT / "cemm/trainer.py").read_text(encoding="utf-8")
        start = text.index("def realization_refs")
        end = text.find("\ndef ", start + 5)
        body = text[start:end if end != -1 else None]
        self.assertIn("refs.sort()", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
