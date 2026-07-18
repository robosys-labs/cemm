"""Reviewed source-package manifest for deterministic v3.5 compilation."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from ..schema.model import semantic_fingerprint
from ..storage.model import RecordKind


@dataclass(frozen=True, slots=True)
class SourceModule:
    module_ref: str
    path: str
    record_kind: RecordKind
    required: bool = True
    allow_empty: bool = True
    phase: int = 6
    authority_scope: str = "semantic"

    def __post_init__(self) -> None:
        if not self.module_ref.strip() or not self.path.strip():
            raise ValueError("source module requires module_ref and path")
        relative = Path(self.path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"source module path must remain inside the package: {self.path}")
        if self.phase < 0:
            raise ValueError("source module phase must be non-negative")
        if not self.authority_scope.strip():
            raise ValueError("source module authority_scope is required")
        if relative.suffix.casefold() not in {".jsonl", ".json", ".yaml", ".yml"}:
            raise ValueError(f"unsupported source module extension: {self.path}")


@dataclass(frozen=True, slots=True)
class SourceManifest:
    package_ref: str
    version: str
    modules: tuple[SourceModule, ...]
    schema_version: int = 1
    metadata: Mapping[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})
        if not self.package_ref.strip() or not self.version.strip():
            raise ValueError("manifest requires package_ref and version")
        if self.schema_version != 1:
            raise ValueError(f"unsupported source manifest schema version: {self.schema_version}")
        refs = tuple(item.module_ref for item in self.modules)
        paths = tuple(item.path for item in self.modules)
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate source module_ref")
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate source module path")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            "source-manifest",
            {
                "package_ref": self.package_ref,
                "version": self.version,
                "schema_version": self.schema_version,
                "modules": [
                    {
                        "module_ref": item.module_ref,
                        "path": item.path,
                        "record_kind": item.record_kind.value,
                        "required": item.required,
                        "allow_empty": item.allow_empty,
                        "phase": item.phase,
                        "authority_scope": item.authority_scope,
                    }
                    for item in self.modules
                ],
                "metadata": dict(self.metadata),
            },
            64,
        )


def load_manifest(path: str | Path) -> SourceManifest:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("source manifest must be a JSON object")
    modules = []
    for item in payload.get("modules", ()):
        if not isinstance(item, Mapping):
            raise ValueError("manifest modules must be objects")
        modules.append(SourceModule(
            module_ref=str(item["module_ref"]),
            path=str(item["path"]),
            record_kind=RecordKind(item["record_kind"]),
            required=bool(item.get("required", True)),
            allow_empty=bool(item.get("allow_empty", True)),
            phase=int(item.get("phase", 6)),
            authority_scope=str(item.get("authority_scope", "semantic")),
        ))
    return SourceManifest(
        package_ref=str(payload["package_ref"]),
        version=str(payload["version"]),
        modules=tuple(modules),
        schema_version=int(payload.get("schema_version", 1)),
        metadata=dict(payload.get("metadata", {})),
    )
