#!/usr/bin/env python3
"""Build deterministic v3.5.1 Phase-18 runtime authority manifest v5.

The authority payload is non-circular: activation/closure/signature metadata is excluded from the
payload hash. A preactivation manifest can therefore be hashed and signed, then finalized only after
closure evidence is bound to that payload hash and the detached signature verifies externally.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sqlite3
import subprocess
from pathlib import Path

from cemm.v350.csir.authority import CURRENT_KERNEL_ABI
from cemm.v350.csir.runtime_projection_v351 import CANONICAL_AUTHORITY_SET_REFS
from cemm.v350.finalization.service_authority_v351 import canonical_service_authorities_v351
from cemm.v350.finalization.source_attestation_v351 import runtime_source_root_v351, sha256_file
from cemm.v350.runtime_graph import canonical_stage_descriptors, resolve_adapter_type
from cemm.v350.storage import RecordKind


BOOT_PIN_KINDS = (
    ("allowed_language_packages", RecordKind.LANGUAGE_PACK),
    ("operation_adapter_contracts", RecordKind.OPERATION_ADAPTER_CONTRACT),
    ("semantic_analyzer_contracts", RecordKind.SEMANTIC_ANALYZER_CONTRACT),
    ("channel_adapter_contracts", RecordKind.CHANNEL_ADAPTER_CONTRACT),
    ("argument_frames", RecordKind.ARGUMENT_FRAME),
    ("morphology_rules", RecordKind.MORPHOLOGY_RULE),
    ("linearization_rules", RecordKind.LINEARIZATION_RULE),
)
LEGACY_RECORD_KINDS = {kind.value for kind in RecordKind if kind.value.startswith("migration_")} | {"response_uol"}
RUNTIME_SAFE_RECORD_KINDS = tuple(sorted(kind.value for kind in RecordKind if kind.value not in LEGACY_RECORD_KINDS))
FORBIDDEN_PREFIXES = (
    "cemm.v347", "cemm.migration", "cemm.v350.migration", "cemm.v350.runtime_hardening",
    "cemm.v350.runtime_services", "cemm.v350.activation_services", "cemm.v350.uol",
)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def exact_commit(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def boot_pins(path: Path, kind: RecordKind):
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT record_ref, revision, record_fingerprint FROM record_index WHERE record_kind=? ORDER BY record_ref, revision",
            (kind.value,),
        ).fetchall()
    finally:
        connection.close()
    return tuple(f"{ref}@{int(revision)}#{fingerprint}" for ref, revision, fingerprint in rows)


def language_tags_from_pins(pins):
    tags = set()
    for value in pins:
        record_ref = str(value).split("@", 1)[0]
        prefix = "language-pack:"
        if record_ref.startswith(prefix):
            tag = record_ref[len(prefix):].strip()
            if tag:
                tags.add(tag)
    return tuple(sorted(tags))


def boot_ref_exists(path: Path, kind: RecordKind, ref: str) -> bool:
    if not ref:
        return False
    return any(pin.startswith(f"{ref}@") for pin in boot_pins(path, kind))


def authority_payload(doc):
    excluded = {"activation_ready", "closure_ledger_sha256", "detached_signature", "authority_payload_sha256", "metadata"}
    return {key: doc[key] for key in sorted(doc) if key not in excluded}


def payload_sha(doc):
    raw = json.dumps(authority_payload(doc), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--boot-database", type=Path, required=True)
    parser.add_argument("--verification-report", type=Path, required=True)
    parser.add_argument("--semantic-authority-supplement", type=Path,
                        default=Path("cemm/data/v350/semantic_authority_supplement_v351.json"))
    parser.add_argument("--conversational-seed", type=Path,
                        default=Path("cemm/data/v350/bootstrap/conversational_core_v351.json"))
    parser.add_argument("--conversational-curriculum", type=Path,
                        default=Path("cemm/data/v350/bootstrap/conversational_curriculum_v351.json"))
    parser.add_argument("--closure-ledger", type=Path)
    parser.add_argument("--detached-signature", type=Path)
    parser.add_argument("--signer-identity", default="")
    parser.add_argument("--realization-language-tag", action="append", default=[],
                        help="reviewed realization language to advertise; repeat for multiple")
    parser.add_argument("--base-manifest", type=Path,
                        help="optional prior manifest used only to recover exact output speaker/commitment refs")
    parser.add_argument("--output-speaker-ref", default="")
    parser.add_argument("--output-commitment-kind-ref", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    commit = exact_commit(root)
    boot_sha = sha256_file(args.boot_database)
    source_root, source_inventory = runtime_source_root_v351(root)
    supplement_path = (
        args.semantic_authority_supplement
        if args.semantic_authority_supplement.is_absolute()
        else root / args.semantic_authority_supplement
    ).resolve()
    if not supplement_path.is_file():
        raise ValueError("semantic authority supplement is missing")
    supplement_sha = sha256_file(supplement_path)
    seed_path = (args.conversational_seed if args.conversational_seed.is_absolute() else root / args.conversational_seed).resolve()
    curriculum_path = (args.conversational_curriculum if args.conversational_curriculum.is_absolute() else root / args.conversational_curriculum).resolve()
    if not seed_path.is_file() or not curriculum_path.is_file():
        raise ValueError("conversational seed/curriculum artifact is missing")
    seed_sha = sha256_file(seed_path)
    curriculum_sha = sha256_file(curriculum_path)
    source_manifest = root / "cemm/data/v350/manifest.json"
    denylist = root / "cemm/data/v350/legacy_authority_denylist.json"
    verification_sha = sha256_file(args.verification_report)
    verification_doc = json.loads(args.verification_report.read_text(encoding="utf-8"))
    if verification_doc.get("status") != "pass":
        raise ValueError("verification report is not passing")
    if verification_doc.get("release_commit") != commit:
        raise ValueError("verification report release commit differs from checkout")
    if verification_doc.get("boot_database_sha256") != boot_sha:
        raise ValueError("verification report boot database hash differs from release boot database")
    if verification_doc.get("runtime_source_root_sha256") != source_root:
        raise ValueError("verification report runtime source root differs from checkout")
    if verification_doc.get("semantic_authority_supplement_sha256") != supplement_sha:
        raise ValueError("verification report semantic authority supplement differs from release")
    if verification_doc.get("conversational_seed_sha256") != seed_sha:
        raise ValueError("verification report conversational seed differs from release")
    if int(verification_doc.get("conversational_seed_schema_count", 0)) < 1:
        raise ValueError("verification report contains no installed conversational semantic seed")
    if int(verification_doc.get("semantic_definition_count", 0)) < 1:
        raise ValueError("verification report contains no reconstructed semantic definitions")
    if set(map(str, verification_doc.get("canonical_authority_set_refs", ()))) != set(CANONICAL_AUTHORITY_SET_REFS):
        raise ValueError("verification report lacks exact canonical authority-set inventory")

    boot_authority = {field: list(boot_pins(args.boot_database, kind)) for field, kind in BOOT_PIN_KINDS}
    available_language_tags = set(language_tags_from_pins(boot_authority["allowed_language_packages"]))
    realization_languages = tuple(sorted(set(args.realization_language_tag or ("en",))))
    missing_languages = sorted(set(realization_languages).difference(available_language_tags))
    if missing_languages:
        raise ValueError(f"requested realization language lacks exact boot language-pack authority:{missing_languages}")
    if "en" not in realization_languages:
        raise ValueError("english_conversational_kernel requires reviewed en realization authority")

    base_manifest_path = args.base_manifest or (root / "cemm/data/v350/runtime_authority_manifest.json")
    base_manifest = {}
    if base_manifest_path.is_file():
        base_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    output_speaker_ref = str(args.output_speaker_ref or base_manifest.get("output_speaker_ref") or "")
    output_commitment_kind_ref = str(
        args.output_commitment_kind_ref or base_manifest.get("output_commitment_kind_ref") or ""
    )
    if output_speaker_ref and not boot_ref_exists(args.boot_database, RecordKind.REFERENT, output_speaker_ref):
        raise ValueError("output speaker ref is absent from exact boot database")
    if output_commitment_kind_ref and not boot_ref_exists(args.boot_database, RecordKind.SCHEMA, output_commitment_kind_ref):
        raise ValueError("output commitment kind ref is absent from exact boot database")

    service_docs = [
        {
            "service_kind": item.service_kind,
            "class_path": item.class_path,
            "required_methods": item.required_methods,
            "runtime_abi": item.runtime_abi,
            "implementation_service_kind": item.implementation_service_kind,
            "source_sha256": item.source_sha256,
        }
        for item in canonical_service_authorities_v351()
    ]
    adapters = []
    for descriptor in canonical_stage_descriptors():
        cls = resolve_adapter_type(descriptor)
        source = Path(inspect.getsourcefile(cls) or "")
        adapters.append({
            "stage": int(descriptor.stage), "adapter_ref": descriptor.adapter_ref,
            "adapter_revision": descriptor.adapter_revision, "factory_path": descriptor.adapter_class_path,
            "handler_name": descriptor.handler_name, "source_sha256": sha256_file(source),
            "contract_fingerprint": descriptor.contract.fingerprint,
            "persistence_class": descriptor.contract.persistence.value,
            "allowed_generation_changes": sorted(item.value for item in descriptor.contract.allowed_generation_changes),
            "allowed_effects": sorted(item.value for item in descriptor.contract.allowed_effects),
        })
    doc = {
        "manifest_version": 5,
        "release_version": "3.5.1",
        "release_commit": commit,
        "source_manifest_sha256": sha256_file(source_manifest),
        "boot_database_sha256": boot_sha,
        "schema_version": 351,
        "canonical_orchestrator": "cemm.v350.orchestration:CanonicalOrchestrator",
        "canonical_runtime_factory": "cemm.v350.runtime_v351:build_runtime",
        "public_entrypoints": ["cemm:Runtime", "cemm.app.runtime:Runtime", "python -m cemm", "cemm.web_demo:serve"],
        "forbidden_runtime_import_prefixes": list(FORBIDDEN_PREFIXES),
        "stage_adapters": adapters,
        "canonical_service_authorities": service_docs,
        "runtime_source_root_sha256": source_root,
        "semantic_authority_supplement_sha256": supplement_sha,
        "conversational_seed_sha256": seed_sha,
        "kernel_semantic_abi_fingerprint": CURRENT_KERNEL_ABI.fingerprint,
        "runtime_source_inventory": list(source_inventory),
        "allowed_runtime_modules": ["cemm.v350"],
        "allowed_record_kinds": list(RUNTIME_SAFE_RECORD_KINDS),
        "allowed_boot_data_modules": ["cemm.data.v350"],
        "migration_modules_allowed_at_runtime": [],
        "legacy_denylist_sha256": sha256_file(denylist),
        "verification_report_sha256": verification_sha,
        "runtime_service_bindings": [],
        "release_capabilities": {
            "csir_compilation": True, "recurrent_semantics": True,
            "epistemic_admission": True, "causal_reasoning": True,
            "text_emission": True, "english_conversational_kernel": True,
            "output_discourse": True,
            "realization_languages": list(realization_languages),
            # Additional languages are advertised only when explicitly requested and boot-pinned.
            "shared_semantics_language_equivalence_required": True,
        },
        "realization_language_tags": list(realization_languages),
        "output_speaker_ref": output_speaker_ref or None,
        "output_commitment_kind_ref": output_commitment_kind_ref or None,
        "activation_ready": False,
        "closure_ledger_sha256": "",
        "detached_signature": {},
        "metadata": {
            "phase": "17-18", "state": "preactivation",
            "semantic_authority_supplement_relpath": supplement_path.relative_to(root).as_posix(),
            "conversational_seed_relpath": seed_path.relative_to(root).as_posix(),
            "conversational_curriculum_relpath": curriculum_path.relative_to(root).as_posix(),
            "conversational_curriculum_sha256": curriculum_sha,
        },
    }
    for field, _kind in BOOT_PIN_KINDS:
        doc[field] = boot_authority[field]
    doc["authority_payload_sha256"] = payload_sha(doc)

    if args.closure_ledger is not None:
        ledger = json.loads(args.closure_ledger.read_text(encoding="utf-8"))
        roots_match = (
            ledger.get("complete") is True
            and ledger.get("release_commit") == commit
            and ledger.get("authority_payload_sha256") == doc["authority_payload_sha256"]
            and ledger.get("boot_database_sha256") == boot_sha
            and ledger.get("runtime_source_root_sha256") == source_root
        )
        if not roots_match:
            raise ValueError("closure ledger is incomplete or bound to different release roots")
        if doc["release_capabilities"].get("output_discourse") is True:
            if not output_speaker_ref or not output_commitment_kind_ref:
                raise ValueError("final activation requires exact output speaker and commitment-kind refs")
        doc["closure_ledger_sha256"] = sha256_file(args.closure_ledger)
        if args.detached_signature is None or not args.detached_signature.is_file() or not args.signer_identity:
            raise ValueError("final activation requires detached signature artifact + signer identity")
        # Verification of signature cryptography is intentionally performed by the release process;
        # this builder records the exact detached artifact and closure gate must attest verification.
        doc["detached_signature"] = {
            "sha256": sha256_file(args.detached_signature),
            "signer_identity": args.signer_identity,
        }
        doc["activation_ready"] = True
        if int(verification_doc.get("observation_model_count", 0)) < 1:
            raise ValueError("final activation requires at least one reviewed exact ObservationModel")
        doc["metadata"] = {
            "phase": "17-18", "state": "activation-candidate",
            "semantic_authority_supplement_relpath": supplement_path.relative_to(root).as_posix(),
            "conversational_seed_relpath": seed_path.relative_to(root).as_posix(),
            "conversational_curriculum_relpath": curriculum_path.relative_to(root).as_posix(),
            "conversational_curriculum_sha256": curriculum_sha,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(doc["authority_payload_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
