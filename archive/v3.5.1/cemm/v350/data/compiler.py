"""Deterministic compiler from reviewed source modules to immutable SQLite."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Iterable, Mapping

from ..schema.model import semantic_fingerprint
from ..storage.codec import decode_record, encode_record, record_ref, record_revision
from ..storage.model import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
)
from ..storage.persistence import write_record
from ..storage.sqlite_schema import (
    configure_connection,
    initialize_schema,
    set_meta,
)
from ..storage.store import SemanticStore
from .manifest import SourceManifest, SourceModule, load_manifest


class SourceCompilationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceRecord:
    module_ref: str
    path: str
    ordinal: int
    record_kind: RecordKind
    phase: int
    authority_scope: str
    record: Any
    revision: int

    @property
    def record_ref(self) -> str:
        return record_ref(self.record_kind, self.record)


@dataclass(frozen=True, slots=True)
class CompilationResult:
    output_path: Path
    manifest_fingerprint: str
    record_set_fingerprint: str
    boot_fingerprint: str
    record_count: int
    module_counts: Mapping[str, int]
    byte_size: int


class SourcePackageLoader:
    def __init__(self, package_root: str | Path):
        self.package_root = Path(package_root).resolve()
        self.manifest_path = self.package_root / "manifest.json"
        self.manifest = load_manifest(self.manifest_path)

    def load(self) -> tuple[SourceRecord, ...]:
        result: list[SourceRecord] = []
        identities: set[tuple[RecordKind, str, int]] = set()
        for module in self.manifest.modules:
            module_path = (self.package_root / module.path).resolve()
            try:
                module_path.relative_to(self.package_root)
            except ValueError as exc:
                raise SourceCompilationError(
                    f"module escapes source package: {module.path}"
                ) from exc
            if not module_path.is_file():
                if module.required:
                    raise SourceCompilationError(f"required source module is missing: {module.path}")
                continue
            documents = tuple(_read_documents(module_path))
            if not documents and not module.allow_empty:
                raise SourceCompilationError(f"source module may not be empty: {module.path}")
            for ordinal, document in enumerate(documents, start=1):
                try:
                    record = decode_record(module.record_kind, document)
                    revision = record_revision(module.record_kind, record)
                    identity = (module.record_kind, record_ref(module.record_kind, record), revision)
                    if identity in identities:
                        raise SourceCompilationError(
                            f"duplicate source record {identity[0].value}:{identity[1]}@{identity[2]}"
                        )
                    identities.add(identity)
                    result.append(SourceRecord(
                        module_ref=module.module_ref,
                        path=module.path,
                        ordinal=ordinal,
                        record_kind=module.record_kind,
                        phase=module.phase,
                        authority_scope=module.authority_scope,
                        record=record,
                        revision=revision,
                    ))
                except (TypeError, ValueError) as exc:
                    if isinstance(exc, SourceCompilationError):
                        raise
                    raise SourceCompilationError(
                        f"{module.path}:{ordinal}: {exc}"
                    ) from exc
        result.sort(key=lambda item: (
            item.record_kind.value,
            item.record_ref,
            item.revision,
            item.module_ref,
            item.ordinal,
        ))
        return tuple(result)


class DeterministicSQLiteCompiler:
    def compile(
        self,
        package_root: str | Path,
        output_path: str | Path,
        *,
        make_read_only: bool = True,
    ) -> CompilationResult:
        loader = SourcePackageLoader(package_root)
        records = loader.load()
        self._validate(records)
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        try:
            connection = sqlite3.connect(temporary)
            connection.row_factory = sqlite3.Row
            configure_connection(connection, deterministic_build=True)
            connection.execute("BEGIN IMMEDIATE")
            try:
                initialize_schema(connection)
                for item in records:
                    write_record(
                        connection,
                        item.record_kind,
                        item.record,
                        revision=item.revision,
                        store_revision=0,
                    )
                record_set_fingerprint = semantic_fingerprint(
                    "compiled-record-set",
                    tuple(
                        (
                            item.record_kind.value,
                            item.record_ref,
                            item.revision,
                            encode_record(item.record_kind, item.record),
                        )
                        for item in records
                    ),
                    64,
                )
                boot_fingerprint = semantic_fingerprint(
                    "boot-database",
                    (
                        loader.manifest.fingerprint,
                        record_set_fingerprint,
                    ),
                    64,
                )
                set_meta(connection, "compiled_manifest_fingerprint", loader.manifest.fingerprint)
                set_meta(connection, "record_set_fingerprint", record_set_fingerprint)
                set_meta(connection, "boot_fingerprint", boot_fingerprint)
                set_meta(connection, "store_revision", "0")
                connection.commit()
                connection.execute("VACUUM")
                connection.execute("PRAGMA optimize")
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            os.replace(temporary, output)
            if make_read_only:
                output.chmod(0o444)
            counts: dict[str, int] = {module.module_ref: 0 for module in loader.manifest.modules}
            for item in records:
                counts[item.module_ref] += 1
            return CompilationResult(
                output_path=output,
                manifest_fingerprint=loader.manifest.fingerprint,
                record_set_fingerprint=record_set_fingerprint,
                boot_fingerprint=boot_fingerprint,
                record_count=len(records),
                module_counts=counts,
                byte_size=output.stat().st_size,
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _validate(records: tuple[SourceRecord, ...]) -> None:
        if not records:
            return
        store = SemanticStore(":memory:")
        try:
            operations = tuple(
                PatchOperation(
                    operation_ref=f"compile:{item.module_ref}:{item.ordinal}",
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=item.record_kind,
                    target_ref=item.record_ref,
                    record_revision=item.revision,
                    payload=encode_record(item.record_kind, item.record),
                )
                for item in records
            )
            patch = GraphPatch(
                patch_ref="patch:compile-source-package",
                context_ref="boot",
                scope_ref="global",
                source_ref="compiler:reviewed-source",
                permission_ref="internal",
                operations=operations,
                expected_store_revision=0,
                validation_requirements=("complete_cross_record_validation",),
            )
            result = store.apply_patch(patch)
            if not result.committed:
                raise SourceCompilationError("; ".join(result.errors))
        finally:
            store.close()


def _read_documents(path: Path) -> Iterable[Mapping[str, Any]]:
    suffix = path.suffix.casefold()
    if suffix == ".jsonl":
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SourceCompilationError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(value, Mapping):
                raise SourceCompilationError(f"{path}:{line_number}: JSONL record must be an object")
            yield value
        return
    if suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        values = value if isinstance(value, list) else (value,)
        for index, item in enumerate(values, start=1):
            if not isinstance(item, Mapping):
                raise SourceCompilationError(f"{path}:{index}: JSON record must be an object")
            yield item
        return
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SourceCompilationError(
            f"YAML source requires PyYAML: {path}"
        ) from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = value if isinstance(value, list) else (value,)
    for index, item in enumerate(values, start=1):
        if not isinstance(item, Mapping):
            raise SourceCompilationError(f"{path}:{index}: YAML record must be an object")
        yield item
