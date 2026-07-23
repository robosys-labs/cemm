"""Runtime-authority manifest and fail-closed cutover guard for CEMM v3.5.1."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
from types import MappingProxyType
import re
import sqlite3
import sys
from typing import Any, Mapping

from .orchestration import CoreStage
from .csir.authority import CURRENT_KERNEL_ABI
from .runtime_graph import canonical_stage_descriptors, resolve_adapter_type
from .storage import RecordKind


class RuntimeAuthorityError(RuntimeError):
    pass


def _deep_freeze_authority(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _deep_freeze_authority(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze_authority(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze_authority(item) for item in value)
    return value


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _boot_pins(path: Path, kind: RecordKind) -> tuple[str, ...]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT record_ref, revision, record_fingerprint FROM record_index "
            "WHERE record_kind=? ORDER BY record_ref, revision",
            (kind.value,),
        ).fetchall()
    finally:
        connection.close()
    return tuple(f"{ref}@{int(revision)}#{fingerprint}" for ref, revision, fingerprint in rows)


# v3.5.1 authority is the exact AuthoritySnapshot/StageContract closure.
# Special boot-kind requirements are capability-driven below; stale UOL-era
# record-family requirements must never force dummy runtime authority.
REQUIRED_RUNTIME_BOOT_AUTHORITIES: tuple[tuple[str, RecordKind], ...] = ()


@dataclass(frozen=True, slots=True)
class StageAdapterAuthority:
    stage: CoreStage
    adapter_ref: str
    adapter_revision: int
    factory_path: str
    handler_name: str
    source_sha256: str
    contract_fingerprint: str
    persistence_class: str
    allowed_generation_changes: tuple[str, ...] = ()
    allowed_effects: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuntimeAuthorityManifest:
    manifest_version: int
    release_version: str
    release_commit: str
    source_manifest_sha256: str
    boot_database_sha256: str
    schema_version: int
    canonical_orchestrator: str
    canonical_runtime_factory: str
    public_entrypoints: tuple[str, ...]
    forbidden_runtime_import_prefixes: tuple[str, ...]
    stage_adapters: tuple[StageAdapterAuthority, ...]
    allowed_runtime_modules: tuple[str, ...]
    allowed_record_kinds: tuple[str, ...]
    allowed_boot_data_modules: tuple[str, ...]
    allowed_language_packages: tuple[str, ...]
    operation_adapter_contracts: tuple[str, ...]
    semantic_analyzer_contracts: tuple[str, ...]
    channel_adapter_contracts: tuple[str, ...]
    migration_modules_allowed_at_runtime: tuple[str, ...]
    legacy_denylist_sha256: str
    verification_report_sha256: str
    activation_ready: bool
    metadata: Mapping[str, Any]
    argument_frames: tuple[str, ...] = ()
    morphology_rules: tuple[str, ...] = ()
    linearization_rules: tuple[str, ...] = ()
    runtime_service_bindings: tuple[Mapping[str, Any], ...] = ()
    canonical_service_authorities: tuple[Mapping[str, Any], ...] = ()
    runtime_source_root_sha256: str = ""
    semantic_authority_supplement_sha256: str = ""
    conversational_seed_sha256: str = ""
    kernel_semantic_abi_fingerprint: str = ""
    closure_ledger_sha256: str = ""
    detached_signature: Mapping[str, Any] = field(default_factory=dict)
    release_capabilities: Mapping[str, Any] = field(default_factory=dict)
    realization_language_tags: tuple[str, ...] = ()
    output_speaker_ref: str | None = None
    output_commitment_kind_ref: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> "RuntimeAuthorityManifest":
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        adapters = tuple(StageAdapterAuthority(
            stage=CoreStage(int(item["stage"])),
            adapter_ref=str(item["adapter_ref"]),
            adapter_revision=int(item["adapter_revision"]),
            factory_path=str(item["factory_path"]),
            handler_name=str(item.get("handler_name", "")),
            source_sha256=str(item["source_sha256"]),
            contract_fingerprint=str(item.get("contract_fingerprint", "")),
            persistence_class=str(item.get("persistence_class", "")),
            allowed_generation_changes=tuple(sorted(map(str, item.get("allowed_generation_changes", ())))),
            allowed_effects=tuple(sorted(map(str, item.get("allowed_effects", ())))),
        ) for item in doc.get("stage_adapters", ()))
        return cls(
            manifest_version=int(doc["manifest_version"]), release_version=str(doc["release_version"]),
            release_commit=str(doc["release_commit"]), source_manifest_sha256=str(doc["source_manifest_sha256"]),
            boot_database_sha256=str(doc.get("boot_database_sha256", "")), schema_version=int(doc["schema_version"]),
            canonical_orchestrator=str(doc["canonical_orchestrator"]), canonical_runtime_factory=str(doc["canonical_runtime_factory"]),
            public_entrypoints=tuple(map(str, doc.get("public_entrypoints", ()))),
            forbidden_runtime_import_prefixes=tuple(map(str, doc.get("forbidden_runtime_import_prefixes", ()))),
            stage_adapters=adapters, allowed_runtime_modules=tuple(map(str, doc.get("allowed_runtime_modules", ()))),
            allowed_record_kinds=tuple(map(str, doc.get("allowed_record_kinds", ()))),
            allowed_boot_data_modules=tuple(map(str, doc.get("allowed_boot_data_modules", ()))),
            allowed_language_packages=tuple(map(str, doc.get("allowed_language_packages", ()))),
            operation_adapter_contracts=tuple(map(str, doc.get("operation_adapter_contracts", ()))),
            semantic_analyzer_contracts=tuple(map(str, doc.get("semantic_analyzer_contracts", ()))),
            channel_adapter_contracts=tuple(map(str, doc.get("channel_adapter_contracts", ()))),
            migration_modules_allowed_at_runtime=tuple(map(str, doc.get("migration_modules_allowed_at_runtime", ()))),
            legacy_denylist_sha256=str(doc["legacy_denylist_sha256"]), verification_report_sha256=str(doc.get("verification_report_sha256", "")),
            activation_ready=bool(doc.get("activation_ready", False)),
            metadata=_deep_freeze_authority(dict(doc.get("metadata", {}))),
            argument_frames=tuple(map(str, doc.get("argument_frames", ()))),
            morphology_rules=tuple(map(str, doc.get("morphology_rules", ()))),
            linearization_rules=tuple(map(str, doc.get("linearization_rules", ()))),
            runtime_service_bindings=tuple(
                _deep_freeze_authority(dict(item)) for item in doc.get("runtime_service_bindings", ())
                if isinstance(item, Mapping)
            ),
            canonical_service_authorities=tuple(
                _deep_freeze_authority(dict(item)) for item in doc.get("canonical_service_authorities", ())
                if isinstance(item, Mapping)
            ),
            runtime_source_root_sha256=str(doc.get("runtime_source_root_sha256", "")),
            semantic_authority_supplement_sha256=str(doc.get("semantic_authority_supplement_sha256", "")),
            conversational_seed_sha256=str(doc.get("conversational_seed_sha256", "")),
            kernel_semantic_abi_fingerprint=str(doc.get("kernel_semantic_abi_fingerprint", "")),
            closure_ledger_sha256=str(doc.get("closure_ledger_sha256", "")),
            detached_signature=_deep_freeze_authority(dict(doc.get("detached_signature", {}) or {})),
            release_capabilities=_deep_freeze_authority(dict(doc.get("release_capabilities", {}))),
            realization_language_tags=tuple(map(str, doc.get("realization_language_tags", ()))),
            output_speaker_ref=None if doc.get("output_speaker_ref") is None else str(doc.get("output_speaker_ref")),
            output_commitment_kind_ref=None if doc.get("output_commitment_kind_ref") is None else str(doc.get("output_commitment_kind_ref")),
        )


class RuntimeAuthorityGuard:
    """Validate exact code/data/release topology before semantic service."""

    REQUIRED_FORBIDDEN_PREFIXES = (
        "cemm.v347", "cemm.migration", "cemm.v350.migration",
        "cemm.v350.runtime_hardening", "cemm.v350.runtime_services",
        "cemm.v350.activation_services", "cemm.v350.uol",
    )

    def __init__(
        self,
        manifest: RuntimeAuthorityManifest,
        *,
        repo_root: Path | None = None,
        boot_database_path: Path | None = None,
        verification_report_path: Path | None = None,
    ) -> None:
        self.manifest = manifest
        self.repo_root = repo_root
        self.boot_database_path = boot_database_path
        self.verification_report_path = verification_report_path
        self._by_stage = {item.stage: item for item in manifest.stage_adapters}

    def require_service_authority(self) -> None:
        m = self.manifest
        # Reject obsolete manifests before importing any service class. A failed old
        # activation must not contaminate sys.modules with the UOL/composition brain.
        if m.manifest_version < 5:
            raise RuntimeAuthorityError("runtime authority manifest v5 is required for final v3.5.1 cutover")
        if m.release_version != "3.5.1":
            raise RuntimeAuthorityError(f"unexpected release version:{m.release_version}")
        errors: list[str] = []
        if m.kernel_semantic_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            errors.append("kernel semantic ABI fingerprint mismatch")
        if not m.activation_ready:
            errors.append("runtime authority manifest is not activation-ready")
        if not re.fullmatch(r"[0-9a-f]{40}", m.release_commit):
            errors.append("release_commit must be one exact 40-hex git commit")
        if m.canonical_orchestrator != "cemm.v350.orchestration:CanonicalOrchestrator":
            errors.append("canonical orchestrator authority mismatch")
        if m.canonical_runtime_factory != "cemm.v350.runtime_v351:build_runtime":
            errors.append("canonical runtime factory authority mismatch")
        expected_entrypoints = {
            "cemm:Runtime", "cemm.app.runtime:Runtime", "python -m cemm", "cemm.web_demo:serve",
        }
        if set(m.public_entrypoints) != expected_entrypoints:
            errors.append("public runtime entrypoint set mismatch")
        if set(m.allowed_runtime_modules) != {"cemm.v350"}:
            errors.append("runtime module authority must be exactly cemm.v350")
        if set(m.allowed_boot_data_modules) != {"cemm.data.v350"}:
            errors.append("boot-data authority must be exactly cemm.data.v350")
        runtime_safe_record_kinds = {item.value for item in RecordKind if not item.value.startswith("migration_")} - {"response_uol"}
        if set(m.allowed_record_kinds) != runtime_safe_record_kinds:
            errors.append("manifest runtime record-kind authority is not the exact legacy-free v3.5.1 set")
        if m.migration_modules_allowed_at_runtime:
            errors.append("runtime manifest allows migration modules")
        service_kinds = {str(item.get("service_kind", "")) for item in m.runtime_service_bindings}
        canonical_service_kinds = {str(item.get("service_kind", "")) for item in m.canonical_service_authorities}
        service_kinds.update(canonical_service_kinds)
        if m.activation_ready:
            if not m.closure_ledger_sha256 or not re.fullmatch(r"[0-9a-f]{64}", m.closure_ledger_sha256):
                errors.append("activation-ready manifest lacks exact Phase-18 closure ledger")
            signature_sha = str(m.detached_signature.get("sha256", ""))
            if not re.fullmatch(r"[0-9a-f]{64}", signature_sha) or not m.detached_signature.get("signer_identity"):
                errors.append("activation-ready manifest lacks exact detached signature authority")
        for item in m.canonical_service_authorities:
            class_path = str(item.get("class_path", ""))
            module_name, sep, symbol = class_path.partition(":")
            if not sep or not module_name or not symbol:
                errors.append(f"invalid canonical service class path:{class_path}")
                continue
            if any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in self.REQUIRED_FORBIDDEN_PREFIXES):
                errors.append(f"canonical service points into forbidden namespace:{class_path}")
                continue
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, symbol)
                for method in tuple(item.get("required_methods", ()) or ()):
                    if not callable(getattr(cls, str(method), None)):
                        errors.append(f"canonical service lacks required method:{class_path}:{method}")
                runtime_abi = getattr(cls, "RUNTIME_ABI", None)
                if runtime_abi != "v351" or str(item.get("runtime_abi", "")) != "v351":
                    errors.append(f"canonical service lacks final v351 ABI:{class_path}")
                declared_kind = getattr(cls, "SERVICE_KIND", None)
                if not isinstance(declared_kind, str) or not declared_kind.strip():
                    errors.append(f"canonical service lacks explicit SERVICE_KIND:{class_path}")
                    continue
                if declared_kind != str(item.get("implementation_service_kind", "")):
                    errors.append(f"canonical service implementation kind mismatch:{class_path}")
                source_path = inspect.getsourcefile(cls)
                if not source_path or not Path(source_path).is_file() or _sha256(Path(source_path)) != str(item.get("source_sha256", "")):
                    errors.append(f"canonical service source fingerprint mismatch:{class_path}")
            except Exception as exc:
                errors.append(f"canonical service authority cannot resolve:{class_path}:{exc}")
        forbidden_service_prefixes = (
            "cemm.v347", "cemm.migration", "cemm.v350.migration",
            "cemm.v350.runtime_services", "cemm.v350.runtime_hardening",
            "cemm.v350.activation_services", "cemm.v350.uol",
        )
        for item in m.runtime_service_bindings:
            class_path = str(item.get("class_path", ""))
            source_sha = str(item.get("source_sha256", ""))
            binding_module = class_path.partition(":")[0]
            if any(
                binding_module == prefix or binding_module.startswith(prefix + ".")
                for prefix in forbidden_service_prefixes
            ):
                errors.append(f"legacy runtime service binding forbidden:{class_path}")
                continue
            if str(item.get("runtime_abi", "")) != "v351":
                errors.append(f"runtime service binding lacks v351 ABI declaration:{class_path}")
                continue
            if not item.get("implementation_ref") or not re.fullmatch(r"[0-9a-f]{64}", source_sha):
                errors.append("runtime service binding lacks exact implementation/source authority")
                continue
            module_name, sep, symbol = class_path.partition(":")
            if not sep or not module_name or not symbol:
                errors.append(f"runtime service binding has invalid class path:{class_path}")
                continue
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, symbol)
                if getattr(cls, "RUNTIME_ABI", None) != "v351":
                    errors.append(f"runtime service implementation lacks RUNTIME_ABI=v351:{class_path}")
                    continue
                if getattr(cls, "SERVICE_KIND", None) != str(item.get("service_kind", "")):
                    errors.append(f"runtime service implementation SERVICE_KIND mismatch:{class_path}")
                    continue
                source_path = inspect.getsourcefile(cls)
                if not source_path or not Path(source_path).is_file() or _sha256(Path(source_path)) != source_sha:
                    errors.append(f"runtime service source fingerprint mismatch:{class_path}")
            except Exception as exc:
                errors.append(f"runtime service binding cannot resolve:{class_path}:{exc}")
        required_services = {"clock"}
        capabilities = dict(m.release_capabilities)
        if m.activation_ready:
            for required_capability in ("csir_compilation", "recurrent_semantics"):
                if capabilities.get(required_capability) is not True:
                    errors.append(f"activation-ready v3.5.1 release lacks required capability:{required_capability}")
        if capabilities.get("csir_compilation") is True:
            required_services.add("csir_compiler")
        if capabilities.get("recurrent_semantics") is True:
            required_services.update({"recurrent_semantic_solver", "semantic_attractor_stabilizer"})
        if capabilities.get("epistemic_admission") is True:
            required_services.add("epistemic_coordinator")
        if capabilities.get("causal_reasoning") is True:
            required_services.add("causal_simulator")
        if capabilities.get("text_emission") is True:
            required_services.update({"response_csir_builder", "realization_engine", "emission_engine"})
        if capabilities.get("independent_roundtrip") is True:
            required_services.add("independent_semantic_analyzer")
        for required_service in sorted(required_services):
            if required_service not in service_kinds:
                errors.append(f"missing signed runtime service binding:{required_service}")
        realization_languages = set(map(str, capabilities.get("realization_languages", ())))
        if capabilities.get("english_conversational_kernel") is True and "en" not in realization_languages:
            errors.append("English conversational-kernel capability requires reviewed en realization")
        if capabilities.get("text_emission") is True:
            if not realization_languages:
                errors.append("text emission requires at least one reviewed realization language")
            elif not realization_languages.issubset(set(m.realization_language_tags)):
                errors.append("advertised realization language is absent from signed boot language packs")
        if capabilities.get("external_operations") and not m.operation_adapter_contracts:
            errors.append("advertised external operations lack signed adapter contracts")
        if m.activation_ready:
            if m.release_capabilities.get("output_discourse") is True:
                if not m.output_speaker_ref or not m.output_commitment_kind_ref:
                    errors.append("activated output discourse lacks signed speaker/commitment authority")
                elif self.boot_database_path is not None:
                    speaker_pins = _boot_pins(self.boot_database_path, RecordKind.REFERENT)
                    if not any(pin.startswith(f"{m.output_speaker_ref}@") for pin in speaker_pins):
                        errors.append("signed output speaker is absent from boot DB")
                    commitment_pins = _boot_pins(self.boot_database_path, RecordKind.SCHEMA)
                    if not any(pin.startswith(f"{m.output_commitment_kind_ref}@") for pin in commitment_pins):
                        errors.append("signed output commitment kind is absent from boot DB")
        missing_forbidden = [p for p in self.REQUIRED_FORBIDDEN_PREFIXES if p not in m.forbidden_runtime_import_prefixes]
        if missing_forbidden:
            errors.append("runtime manifest omits legacy forbidden prefixes:" + ",".join(missing_forbidden))

        descriptors = canonical_stage_descriptors()
        if len(m.stage_adapters) != len(descriptors) or tuple(item.stage for item in m.stage_adapters) != tuple(CoreStage):
            errors.append("runtime manifest stage graph is not exact CoreStage 0..22 order")
        if len(self._by_stage) != len(descriptors):
            errors.append("runtime manifest contains duplicate/missing stage authorities")
        for descriptor in descriptors:
            authority = self._by_stage.get(descriptor.stage)
            if authority is None:
                errors.append(f"missing stage adapter:{descriptor.stage.name}")
                continue
            observed = (
                authority.adapter_ref, authority.adapter_revision, authority.factory_path,
                authority.handler_name, authority.contract_fingerprint, authority.persistence_class,
                tuple(authority.allowed_generation_changes), tuple(authority.allowed_effects),
            )
            expected = (
                descriptor.adapter_ref, descriptor.adapter_revision, descriptor.adapter_class_path,
                descriptor.handler_name, descriptor.contract.fingerprint, descriptor.contract.persistence.value,
                tuple(sorted(x.value for x in descriptor.contract.allowed_generation_changes)),
                tuple(sorted(x.value for x in descriptor.contract.allowed_effects)),
            )
            if observed != expected:
                errors.append(f"stage authority mismatch:{descriptor.stage.name}")
            if not re.fullmatch(r"[0-9a-f]{64}", authority.source_sha256):
                errors.append(f"invalid stage adapter source fingerprint:{descriptor.stage.name}")
            if not authority.contract_fingerprint.startswith("stage-contract-v351:"):
                errors.append(f"missing/invalid v3.5.1 stage contract fingerprint:{descriptor.stage.name}")

        loaded = tuple(sys.modules)
        forbidden = tuple(name for name in loaded if any(name == prefix or name.startswith(prefix + ".") for prefix in m.forbidden_runtime_import_prefixes))
        if forbidden:
            errors.append("forbidden runtime modules loaded:" + ",".join(sorted(forbidden)))

        if self.repo_root is not None:
            source_manifest = self.repo_root / "cemm/data/v350/manifest.json"
            denylist = self.repo_root / "cemm/data/v350/legacy_authority_denylist.json"
            if not source_manifest.is_file() or _sha256(source_manifest) != m.source_manifest_sha256:
                errors.append("source manifest fingerprint mismatch")
            else:
                try:
                    source_doc = json.loads(source_manifest.read_text(encoding="utf-8"))
                    if source_doc.get("metadata", {}).get("runtime_cutover") is not True:
                        errors.append("source manifest is not runtime_cutover=true")
                except (OSError, ValueError, TypeError) as exc:
                    errors.append(f"source manifest is invalid:{exc}")
            if not denylist.is_file() or _sha256(denylist) != m.legacy_denylist_sha256:
                errors.append("legacy denylist fingerprint mismatch")
            try:
                from .finalization.source_attestation_v351 import runtime_source_root_v351
                observed_root, _inventory = runtime_source_root_v351(self.repo_root)
                if not m.runtime_source_root_sha256 or observed_root != m.runtime_source_root_sha256:
                    errors.append("runtime source-tree root fingerprint mismatch")
            except Exception as exc:
                errors.append(f"cannot attest runtime source-tree root:{exc}")
            supplement_rel = str(m.metadata.get("semantic_authority_supplement_relpath", "") or "")
            supplement_path = self.repo_root / supplement_rel if supplement_rel else None
            if m.activation_ready and (
                not m.semantic_authority_supplement_sha256
                or supplement_path is None
                or not supplement_path.is_file()
            ):
                errors.append("activation-ready release lacks signed semantic authority supplement")
            elif m.semantic_authority_supplement_sha256:
                if supplement_path is None or not supplement_path.is_file():
                    errors.append("semantic authority supplement artifact is unavailable")
                elif _sha256(supplement_path) != m.semantic_authority_supplement_sha256:
                    errors.append("semantic authority supplement fingerprint mismatch")
            seed_rel = str(m.metadata.get("conversational_seed_relpath", "") or "")
            seed_path = self.repo_root / seed_rel if seed_rel else None
            if m.activation_ready and (not m.conversational_seed_sha256 or seed_path is None or not seed_path.is_file()):
                errors.append("activation-ready release lacks signed conversational seed")
            elif m.conversational_seed_sha256:
                if seed_path is None or not seed_path.is_file():
                    errors.append("conversational seed artifact is unavailable")
                elif _sha256(seed_path) != m.conversational_seed_sha256:
                    errors.append("conversational seed fingerprint mismatch")

        if not m.boot_database_sha256:
            errors.append("boot database fingerprint is missing")
        elif self.boot_database_path is None or not self.boot_database_path.is_file():
            errors.append("boot database artifact is unavailable")
        elif _sha256(self.boot_database_path) != m.boot_database_sha256:
            errors.append("boot database fingerprint mismatch")
        else:
            expected_boot_authorities = (
                ("language_packages", m.allowed_language_packages, RecordKind.LANGUAGE_PACK),
                ("operation_adapter_contracts", m.operation_adapter_contracts, RecordKind.OPERATION_ADAPTER_CONTRACT),
                ("semantic_analyzer_contracts", m.semantic_analyzer_contracts, RecordKind.SEMANTIC_ANALYZER_CONTRACT),
                ("channel_adapter_contracts", m.channel_adapter_contracts, RecordKind.CHANNEL_ADAPTER_CONTRACT),
            )
            for label, declared, kind in expected_boot_authorities:
                try:
                    observed = _boot_pins(self.boot_database_path, kind)
                except (sqlite3.Error, OSError, ValueError) as exc:
                    errors.append(f"cannot inspect signed boot authority {label}:{exc}")
                    continue
                if tuple(declared) != observed:
                    errors.append(f"signed boot authority mismatch:{label}")
            required_boot_authorities = list(REQUIRED_RUNTIME_BOOT_AUTHORITIES)
            if m.release_capabilities.get("external_operations"):
                required_boot_authorities.append(
                    ("operation_adapter_contracts", RecordKind.OPERATION_ADAPTER_CONTRACT)
                )
            if m.release_capabilities.get("text_emission"):
                required_boot_authorities.append(
                    ("channel_adapter_contracts", RecordKind.CHANNEL_ADAPTER_CONTRACT)
                )
            if m.release_capabilities.get("independent_roundtrip"):
                required_boot_authorities.append(
                    ("semantic_analyzer_contracts", RecordKind.SEMANTIC_ANALYZER_CONTRACT)
                )
            for label, kind in required_boot_authorities:
                try:
                    if not _boot_pins(self.boot_database_path, kind):
                        errors.append(f"missing active boot authority:{label}")
                except (sqlite3.Error, OSError, ValueError) as exc:
                    errors.append(f"cannot inspect required boot authority {label}:{exc}")

        if not m.verification_report_sha256:
            errors.append("verification report fingerprint is missing")
        elif self.verification_report_path is None or not self.verification_report_path.is_file():
            errors.append("verification report artifact is unavailable")
        elif _sha256(self.verification_report_path) != m.verification_report_sha256:
            errors.append("verification report fingerprint mismatch")
        else:
            try:
                report = json.loads(self.verification_report_path.read_text(encoding="utf-8"))
                if report.get("status") != "pass": errors.append("verification report is not passing")
                if report.get("release_commit") != m.release_commit: errors.append("verification report release commit mismatch")
                if report.get("boot_database_sha256") != m.boot_database_sha256: errors.append("verification report boot fingerprint mismatch")
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"verification report is invalid:{exc}")

        for descriptor in descriptors:
            authority = self._by_stage.get(descriptor.stage)
            if authority is None:
                continue
            try:
                adapter_type = resolve_adapter_type(descriptor)
                if adapter_type.__module__ + ":" + adapter_type.__name__ != authority.factory_path:
                    errors.append(f"resolved adapter symbol mismatch:{descriptor.stage.name}")
                source_path = inspect.getsourcefile(adapter_type)
                if not source_path or not Path(source_path).is_file() or _sha256(Path(source_path)) != authority.source_sha256:
                    errors.append(f"stage adapter source fingerprint mismatch:{descriptor.stage.name}")
                handler = getattr(adapter_type, "HANDLER", None)
                if handler != descriptor.handler_name:
                    errors.append(f"adapter handler declaration mismatch:{descriptor.stage.name}")
            except Exception as exc:
                errors.append(f"stage adapter resolution failed:{descriptor.stage.name}:{exc}")

        if errors:
            raise RuntimeAuthorityError("; ".join(errors))

    def require_stage_adapter(self, *, stage: CoreStage, adapter_ref: str, adapter_revision: int) -> None:
        expected = self._by_stage.get(stage)
        if expected is None:
            raise RuntimeAuthorityError(f"no authority for stage {stage.name}")
        if (expected.adapter_ref, expected.adapter_revision) != (adapter_ref, int(adapter_revision)):
            raise RuntimeAuthorityError(f"stage adapter authority mismatch for {stage.name}: {adapter_ref}@{adapter_revision} != {expected.adapter_ref}@{expected.adapter_revision}")

    def load_runtime_factory(self):
        self.require_service_authority()
        module_name, sep, symbol = self.manifest.canonical_runtime_factory.partition(":")
        if not sep or not module_name or not symbol:
            raise RuntimeAuthorityError("canonical_runtime_factory must be module:symbol")
        if any(module_name == p or module_name.startswith(p + ".") for p in self.manifest.forbidden_runtime_import_prefixes):
            raise RuntimeAuthorityError("canonical runtime factory points into forbidden namespace")
        module = importlib.import_module(module_name)
        factory = getattr(module, symbol, None)
        if factory is None or not callable(factory):
            raise RuntimeAuthorityError("canonical runtime factory is not callable")
        return factory
