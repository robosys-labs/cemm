#!/usr/bin/env python3
"""Static and artifact-integrity gate for final CEMM v1.

This gate intentionally rejects removed compatibility paths. It does not treat
legacy tests or archived MVP behavior as authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cemm.authority import AuthorityBundleError, load_documents, validate_documents, validate_pack_constants


ACTIVE_SCHEMA_VERSION = 3
ACTIVE_FORM_PACK_VERSION = 7
ACTIVE_FEATURE_ALGEBRA_VERSION = 7


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fail(errors, message):
    errors.append(message)


def check(repo: Path):
    errors: list[str] = []
    cemm = repo / "cemm"
    required = {
        "authority.py", "capability.py", "cognition.py", "curriculum.py", "epistemics.py",
        "evidence.py", "goals.py", "retrieval.py", "stages.py", "transitions.py", "acquisition.py",
    }
    for name in sorted(required):
        if not (cemm / name).exists():
            fail(errors, f"missing final runtime module: cemm/{name}")

    if (cemm / "selfstate.py").exists():
        fail(errors, "removed global SessionSelf module still exists")
    sidecars = sorted((cemm / "language_packs").glob("*.v1.json"))
    if sidecars:
        fail(errors, "runtime language sidecars remain: " + ", ".join(str(x.relative_to(repo)) for x in sidecars))

    forbidden = {
        "SessionSelf": "global semantic self compatibility",
        ".v1.json": "runtime language sidecar",
        "infer_state_dimension": "value-to-dimension semantic inference shim",
        "LEGACY_FORCE": "implicit discourse-force shim",
        "text.rstrip().endswith": "punctuation discourse-force override",
    }
    runtime_files = (
        "runtime.py", "compiler.py", "codec.py", "interpreter.py", "inference.py",
        "retrieval.py", "workspace.py", "realizer.py", "trainer.py", "response.py",
        "transitions.py", "capability.py", "goals.py", "acquisition.py",
    )
    for name in runtime_files:
        path = cemm / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for needle, description in forbidden.items():
            if needle in text:
                fail(errors, f"{path.relative_to(repo)} retains {description}: {needle}")
    acquisition_text = (cemm / "acquisition.py").read_text(encoding="utf-8")
    for needle, description in (
        ("class AutonomousAcquirer", "autonomous unknown-form mutation"),
        ('get("kind", "concept")', "universal concept fallback"),
        ("runtime.process(doc[\"text\"],learn=", "removed learn/teach runtime API"),
    ):
        if needle in acquisition_text:
            fail(errors, f"cemm/acquisition.py retains {description}: {needle}")
    if "def acquire_reviewed" not in acquisition_text:
        fail(errors, "explicit acquire_reviewed workflow is missing")

    runtime_text = (cemm / "runtime.py").read_text(encoding="utf-8")
    for needle in ("base_facts(", "snapshot_hash("):
        if needle in runtime_text:
            fail(errors, f"normal runtime contains forbidden full-store path: {needle}")

    base_path = cemm / "data/base.json"
    authority_refs: set[str] = set()
    data_paths = sorted((cemm / "data").glob("*.json"))
    if not base_path.exists():
        fail(errors, "missing cemm/data/base.json")
    else:
        try:
            bundle_report = validate_documents(load_documents(data_paths), require_foundations=True)
            authority_refs = {
                str(atom["ref"])
                for path in data_paths
                for atom in json.loads(path.read_text(encoding="utf-8")).get("atoms", ())
            }
        except AuthorityBundleError as exc:
            for issue in exc.issues:
                fail(errors, "authority bundle: " + issue)
        base = json.loads(base_path.read_text(encoding="utf-8"))
        atoms = {item["ref"]: item for item in base.get("atoms", ())}
        operators = sorted(ref for ref, item in atoms.items() if item.get("kind") == "operator")
        expected_ops = ["op:designation", "op:event", "op:relation", "op:state", "op:type"]
        if operators != expected_ops:
            fail(errors, f"kernel operator ABI changed: {operators}")
        removed = {
            "dim:response_state", "dim:interpretation_state", "dim:epistemic_state",
            "value:ready", "value:processing", "value:confused",
        }
        leaked = sorted(removed & set(atoms))
        if leaked:
            fail(errors, f"obsolete global self/outcome atoms remain: {leaked}")
        controls = base.get("control_symbols", {})
        for role in controls:
            if role.startswith("self.") and role != "self.ref":
                fail(errors, f"obsolete self control remains: {role}")
        required_controls = {
            "self.ref", "profile.depends_on_relation", "policy.adapter_relation",
            "policy.required_capability_relation", "profile.value_dimension_relation",
            "profile.entitles_dimension_relation",
            "profile.entitles_capability_relation",
        }
        missing = sorted(required_controls - set(controls))
        if missing:
            fail(errors, f"missing final control symbols: {missing}")
        required_atoms = {
            "concept:digital_agent", "rel:handled_by_adapter", "rel:requires_capability",
            "rel:value_of_dimension",
            "dim:runtime_process_support", "dim:semantic_runtime_support",
            "dim:language_realizer_support", "dim:critical_blocker_count",
            "cap:interpret", "cap:realize", "cap:respond",
        }
        missing_atoms = sorted(required_atoms - set(atoms))
        if missing_atoms:
            fail(errors, f"missing final operational-profile atoms: {missing_atoms}")

    # Generic foundations must not be hidden in domain/demo authority.
    generic_rules = {
        "rule:subrelation-inheritance", "rule:relation-subject-type",
        "rule:type-subtype-inheritance", "rule:relation-subject-state",
        "rule:relation-object-state",
    }
    required_meta = {
        "rel:state_dimension", "rel:state_value", "rel:value_of_dimension",
        "rel:subtype_of", "rel:subrelation_of", "rel:subject_type",
        "rel:implies_subject_state", "rel:implies_object_state",
    }
    if base_path.exists():
        base_rule_refs = {str(item.get("rule_ref")) for item in base.get("rules", ())}
        missing = sorted(generic_rules - base_rule_refs)
        if missing:
            fail(errors, f"generic foundation rules missing from base: {missing}")
        missing = sorted(required_meta - set(atoms))
        if missing:
            fail(errors, f"foundational meta-relations missing from base: {missing}")
        if "label:name" not in atoms:
            fail(errors, "foundational designation family label:name is missing")
    for path in data_paths:
        if path == base_path:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        leaked_rules = sorted(generic_rules & {str(item.get("rule_ref")) for item in data.get("rules", ())})
        leaked_atoms = sorted(required_meta & {str(item.get("ref")) for item in data.get("atoms", ())})
        if leaked_rules or leaked_atoms:
            fail(errors, f"domain authority owns generic foundations {path.relative_to(repo)}: atoms={leaked_atoms}, rules={leaked_rules}")

    trainer_text = (cemm / "trainer.py").read_text(encoding="utf-8")
    realization_match = re.search(r"def realization_refs\(example\):(.*?)(?=\ndef )", trainer_text, re.S)
    if not realization_match or ".sort()" not in realization_match.group(1):
        fail(errors, "trainer realization_refs must sort semantic refs exactly like runtime pointerization")

    packs = sorted((cemm / "language_packs").glob("*.json"))
    if not packs:
        fail(errors, "no compiled language packs found")
    for path in packs:
        data = json.loads(path.read_text(encoding="utf-8"))
        material = {key: value for key, value in data.items() if key != "pack_hash"}
        expected = hashlib.sha256(canonical(material).encode()).hexdigest()
        if data.get("pack_hash") != expected:
            fail(errors, f"language pack hash mismatch: {path.relative_to(repo)}")
        if int(data.get("version", 0)) != ACTIVE_FORM_PACK_VERSION:
            fail(errors, f"language pack is not ABI-7 current: {path.relative_to(repo)}")
        sources = set(data.get("source_classes", ()))
        if {"USER", "SYSTEM"} & sources:
            fail(errors, f"lexically fixed participant sources remain: {path.relative_to(repo)}")
        if not {"FRAME_SPEAKER", "FRAME_ADDRESSEE"} <= sources:
            fail(errors, f"participant-frame source classes missing: {path.relative_to(repo)}")
        if not {f"DIM_OF_A{i}" for i in range(8)} <= sources:
            fail(errors, f"explicit value→dimension source classes missing: {path.relative_to(repo)}")
        constant_sources = {
            str(source): str(ref)
            for source, ref in data.get("constant_sources", {}).items()
        }
        undeclared = sorted(set(constant_sources) - sources)
        if undeclared:
            fail(errors, f"undeclared reviewed constant sources in {path.relative_to(repo)}: {undeclared}")
        missing_constants = sorted(set(constant_sources.values()) - authority_refs)
        if missing_constants:
            fail(errors, f"reviewed constant sources escape authority in {path.relative_to(repo)}: {missing_constants}")
        if len(set(constant_sources.values())) != len(constant_sources):
            fail(errors, f"duplicate reviewed constant refs in {path.relative_to(repo)}")
        if not data.get("response_examples"):
            fail(errors, f"Response CSIR realization supervision missing: {path.relative_to(repo)}")
        for example in data.get("structured_examples", ()):
            target = example.get("target", {})
            if "force" not in target:
                fail(errors, f"implicit discourse force in {path.relative_to(repo)}:{example.get('example_ref')}")
            anchor_kinds = {
                f"A{index}": kind
                for index, kind in re.findall(r"@A([0-7])<([^>]+)>", str(example.get("input", "")))
            }
            for application in target.get("apps", ()):
                bindings = application.get("bindings", {})
                if application.get("operator") == "op:state" and "role:dimension" not in bindings:
                    fail(errors, f"state supervision lacks explicit dimension source in {path.relative_to(repo)}:{example.get('example_ref')}")
                if (
                    application.get("operator") == "op:type"
                    and anchor_kinds.get(str(bindings.get("role:instance"))) == "concept"
                    and anchor_kinds.get(str(bindings.get("role:class"))) == "concept"
                ):
                    fail(errors, f"generic concept predication is encoded as instance typing in {path.relative_to(repo)}:{example.get('example_ref')}")
                for source in bindings.values():
                    if isinstance(source, str) and source.startswith("CONST") and source not in constant_sources:
                        fail(errors, f"unresolved reviewed constant source in {path.relative_to(repo)}:{example.get('example_ref')}:{source}")
        if data.get("language") == "es" and "estoy" not in set(data.get("function_forms", ())):
            fail(errors, "Spanish final pack is missing 'estoy'")
    try:
        validate_pack_constants(packs, authority_refs)
    except AuthorityBundleError as exc:
        for issue in exc.issues:
            fail(errors, "language pack: " + issue)

    constants = (cemm / "constants.py").read_text(encoding="utf-8")
    if not re.search(
        rf"SCHEMA_VERSION\s*=\s*[\"']{ACTIVE_SCHEMA_VERSION}[\"']", constants
    ):
        fail(errors, f"active schema version {ACTIVE_SCHEMA_VERSION} is not declared")
    if "rule_index" not in constants or "commit_receipts" not in constants:
        fail(errors, "final indexed-rule/incremental-commit tables are missing")
    if "evidence_count" not in constants or "last_generation" not in constants:
        fail(errors, "canonical accumulating frontier schema is missing")

    form_packs = sorted((cemm / "form_packs").glob("*.json"))
    if not form_packs:
        fail(errors, "no generated form packs found")
    for path in form_packs:
        data = json.loads(path.read_text(encoding="utf-8"))
        if int(data.get("version", 0)) != ACTIVE_FORM_PACK_VERSION:
            fail(errors, f"form pack is not ABI-7 current: {path.relative_to(repo)}")
        if int(data.get("feature_algebra_version", 0)) != ACTIVE_FEATURE_ALGEBRA_VERSION:
            fail(errors, f"form pack feature algebra is not ABI 7: {path.relative_to(repo)}")

    patch_artifacts = sorted(
        path for path in repo.iterdir()
        if path.is_file() and (
            path.name.endswith(".generated.patch")
            or path.name.endswith(".apply-report.json")
            or path.name.startswith("cemm-v1-fixes-phases-")
        )
    )
    if patch_artifacts:
        fail(errors, "generated delivery artifacts remain in repository root: " + ", ".join(x.name for x in patch_artifacts))

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = check(args.repo.resolve())
    if errors:
        print("FINAL V1 CONTRACT: FAILED", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("FINAL V1 CONTRACT: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
