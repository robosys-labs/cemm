"""Runtime-authority manifest and fail-closed cutover guard for CEMM v3.5."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from .orchestration import CoreStage


class RuntimeAuthorityError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class StageAdapterAuthority:
    stage: CoreStage
    adapter_ref: str
    adapter_revision: int
    factory_path: str
    source_sha256: str


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
    legacy_denylist_sha256: str
    verification_report_sha256: str
    activation_ready: bool
    metadata: Mapping[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "RuntimeAuthorityManifest":
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        adapters = tuple(
            StageAdapterAuthority(
                stage=CoreStage(int(item["stage"])),
                adapter_ref=str(item["adapter_ref"]),
                adapter_revision=int(item["adapter_revision"]),
                factory_path=str(item["factory_path"]),
                source_sha256=str(item["source_sha256"]),
            )
            for item in doc.get("stage_adapters", ())
        )
        return cls(
            manifest_version=int(doc["manifest_version"]),
            release_version=str(doc["release_version"]),
            release_commit=str(doc["release_commit"]),
            source_manifest_sha256=str(doc["source_manifest_sha256"]),
            boot_database_sha256=str(doc.get("boot_database_sha256", "")),
            schema_version=int(doc["schema_version"]),
            canonical_orchestrator=str(doc["canonical_orchestrator"]),
            canonical_runtime_factory=str(doc["canonical_runtime_factory"]),
            public_entrypoints=tuple(map(str, doc.get("public_entrypoints", ()))),
            forbidden_runtime_import_prefixes=tuple(map(str, doc.get("forbidden_runtime_import_prefixes", ()))),
            stage_adapters=adapters,
            legacy_denylist_sha256=str(doc["legacy_denylist_sha256"]),
            verification_report_sha256=str(doc["verification_report_sha256"]),
            activation_ready=bool(doc.get("activation_ready", False)),
            metadata=dict(doc.get("metadata", {})),
        )


class RuntimeAuthorityGuard:
    """Validates the exact code/data topology before semantic service."""

    def __init__(self, manifest: RuntimeAuthorityManifest, *, repo_root: Path | None = None) -> None:
        self.manifest = manifest
        self.repo_root = repo_root
        self._by_stage = {item.stage: item for item in manifest.stage_adapters}

    def require_service_authority(self) -> None:
        m = self.manifest
        if not m.activation_ready:
            raise RuntimeAuthorityError("v3.5 runtime authority manifest is not activation-ready")
        if m.release_version != "3.5.0":
            raise RuntimeAuthorityError(f"unexpected release version: {m.release_version}")
        missing = [stage.name for stage in CoreStage if stage not in self._by_stage]
        if missing:
            raise RuntimeAuthorityError("runtime manifest missing stage adapters: " + ",".join(missing))
        loaded = tuple(sys.modules)
        forbidden = tuple(
            name for name in loaded
            if any(name == prefix or name.startswith(prefix + ".") for prefix in m.forbidden_runtime_import_prefixes)
        )
        if forbidden:
            raise RuntimeAuthorityError("forbidden runtime authority modules loaded: " + ",".join(sorted(forbidden)))
        if self.repo_root is not None:
            source_manifest = self.repo_root / "cemm/data/v350/manifest.json"
            denylist = self.repo_root / "cemm/data/v350/legacy_authority_denylist.json"
            if not source_manifest.is_file() or _sha256(source_manifest) != m.source_manifest_sha256:
                raise RuntimeAuthorityError("source manifest fingerprint mismatch")
            if not denylist.is_file() or _sha256(denylist) != m.legacy_denylist_sha256:
                raise RuntimeAuthorityError("legacy denylist fingerprint mismatch")
        for adapter in m.stage_adapters:
            module_name = adapter.factory_path.partition(":")[0]
            if not module_name:
                raise RuntimeAuthorityError(f"missing adapter factory module for {adapter.stage.name}")
            spec = importlib.util.find_spec(module_name)
            origin = None if spec is None else spec.origin
            if not origin or origin in {"built-in", "frozen"}:
                raise RuntimeAuthorityError(f"adapter source cannot be fingerprinted: {module_name}")
            path = Path(origin)
            if not path.is_file() or _sha256(path) != adapter.source_sha256:
                raise RuntimeAuthorityError(f"stage adapter source fingerprint mismatch: {adapter.stage.name}")

    def require_stage_adapter(self, *, stage: CoreStage, adapter_ref: str, adapter_revision: int) -> None:
        expected = self._by_stage.get(stage)
        if expected is None:
            raise RuntimeAuthorityError(f"no authority for stage {stage.name}")
        if (expected.adapter_ref, expected.adapter_revision) != (adapter_ref, int(adapter_revision)):
            raise RuntimeAuthorityError(
                f"stage adapter authority mismatch for {stage.name}: "
                f"{adapter_ref}@{adapter_revision} != {expected.adapter_ref}@{expected.adapter_revision}"
            )

    def load_runtime_factory(self):
        self.require_service_authority()
        module_name, sep, symbol = self.manifest.canonical_runtime_factory.partition(":")
        if not sep or not module_name or not symbol:
            raise RuntimeAuthorityError("canonical_runtime_factory must be module:symbol")
        if any(module_name == p or module_name.startswith(p + ".") for p in self.manifest.forbidden_runtime_import_prefixes):
            raise RuntimeAuthorityError("canonical runtime factory points into forbidden authority namespace")
        module = importlib.import_module(module_name)
        factory = getattr(module, symbol, None)
        if factory is None or not callable(factory):
            raise RuntimeAuthorityError("canonical runtime factory is not callable")
        return factory
