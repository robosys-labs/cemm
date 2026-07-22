"""Process-lifetime runtime attestation for the stabilized v3.5.1 substrate.

The expensive release/source/boot verification owned by ``RuntimeAuthorityGuard`` is
performed exactly once when an attestation is issued. Runtime hot paths receive an
``AttestedRuntimeAuthority`` proxy whose service-authority check is an O(1)
in-memory epoch/generation validation; stage-adapter checks remain exact and
fail-closed.

A reload creates a new epoch/generation and must re-run the full guard before the
new attestation can become active.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import importlib
from types import MappingProxyType
from threading import RLock
from typing import Any
from uuid import uuid4

from .schema.model import semantic_fingerprint


class RuntimeAttestationError(RuntimeError):
    """Raised when a runtime attestation is stale, invalidated, or mismatched."""


@dataclass(frozen=True, slots=True)
class RuntimeEpoch:
    """Occurrence identity for one verified process/reload generation."""

    epoch_ref: str
    generation: int
    started_at: str
    release_version: str
    release_commit: str

    @classmethod
    def create(cls, manifest: Any, *, generation: int = 1) -> "RuntimeEpoch":
        if generation < 1:
            raise ValueError("runtime epoch generation must be positive")
        release_version = str(getattr(manifest, "release_version", "") or "")
        release_commit = str(getattr(manifest, "release_commit", "") or "")
        if not release_version or not release_commit:
            raise ValueError("runtime epoch requires exact release identity")
        nonce = uuid4().hex
        return cls(
            epoch_ref="runtime-epoch:"
            + semantic_fingerprint(
                "runtime-epoch",
                (release_version, release_commit, generation, nonce),
                32,
            ),
            generation=generation,
            started_at=datetime.now(timezone.utc).isoformat(),
            release_version=release_version,
            release_commit=release_commit,
        )


@dataclass(frozen=True, slots=True)
class RuntimeAttestation:
    """Immutable token derived from one successful full release verification."""

    attestation_ref: str
    epoch: RuntimeEpoch
    release_version: str
    release_commit: str
    source_manifest_sha256: str
    boot_database_sha256: str
    verification_report_sha256: str
    legacy_denylist_sha256: str
    canonical_runtime_factory: str
    canonical_orchestrator: str
    kernel_semantic_abi_fingerprint: str
    verified_at: str

    @classmethod
    def verify(cls, guard: Any, *, generation: int = 1) -> "RuntimeAttestation":
        """Run the expensive guard exactly once and issue an immutable token."""

        if guard is None or not hasattr(guard, "require_service_authority"):
            raise TypeError(
                "runtime attestation requires a RuntimeAuthorityGuard-like object"
            )
        guard.require_service_authority()
        manifest = getattr(guard, "manifest", None)
        if manifest is None:
            raise RuntimeAttestationError(
                "verified authority guard exposes no manifest"
            )

        epoch = RuntimeEpoch.create(manifest, generation=generation)
        fields = (
            epoch.epoch_ref,
            epoch.generation,
            str(manifest.release_version),
            str(manifest.release_commit),
            str(manifest.source_manifest_sha256),
            str(manifest.boot_database_sha256),
            str(manifest.verification_report_sha256),
            str(manifest.legacy_denylist_sha256),
            str(manifest.canonical_runtime_factory),
            str(manifest.canonical_orchestrator),
            str(getattr(manifest, "kernel_semantic_abi_fingerprint", "")),
        )
        return cls(
            attestation_ref="runtime-attestation:"
            + semantic_fingerprint("runtime-attestation", fields, 64),
            epoch=epoch,
            release_version=str(manifest.release_version),
            release_commit=str(manifest.release_commit),
            source_manifest_sha256=str(manifest.source_manifest_sha256),
            boot_database_sha256=str(manifest.boot_database_sha256),
            verification_report_sha256=str(
                manifest.verification_report_sha256
            ),
            legacy_denylist_sha256=str(manifest.legacy_denylist_sha256),
            canonical_runtime_factory=str(manifest.canonical_runtime_factory),
            canonical_orchestrator=str(manifest.canonical_orchestrator),
            kernel_semantic_abi_fingerprint=str(
                getattr(manifest, "kernel_semantic_abi_fingerprint", "")
            ),
            verified_at=datetime.now(timezone.utc).isoformat(),
        )


def _deep_freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_deep_freeze(item) for item in value)
    return value


def _sealed_manifest_copy(manifest):
    fields = {}
    for name in ("metadata", "release_capabilities"):
        value = getattr(manifest, name, None)
        if value is not None:
            fields[name] = _deep_freeze(dict(value))
    bindings = getattr(manifest, "runtime_service_bindings", None)
    if bindings is not None:
        fields["runtime_service_bindings"] = tuple(
            _deep_freeze(dict(item)) for item in bindings
        )
    return replace(manifest, **fields) if fields else manifest


class AttestedRuntimeAuthority:
    """Hot-path authority facade backed by one verified attestation.

    ``require_service_authority`` performs no filesystem IO, hashing, boot-database
    reads, loaded-module enumeration, or manifest traversal.
    """

    def __init__(self, guard: Any, attestation: RuntimeAttestation) -> None:
        if guard is None or getattr(guard, "manifest", None) is None:
            raise TypeError("attested authority requires its verified guard")
        self._guard = guard
        self._sealed_manifest = _sealed_manifest_copy(guard.manifest)
        self.attestation = attestation
        self._lock = RLock()
        self._active = True
        self._generation = attestation.epoch.generation
        self._assert_manifest_identity()

    @property
    def manifest(self) -> Any:
        return self._sealed_manifest

    @property
    def runtime_epoch(self) -> RuntimeEpoch:
        return self.attestation.epoch

    @property
    def authority_generation(self) -> int:
        return self._generation

    def _assert_manifest_identity(self) -> None:
        manifest = self._guard.manifest
        observed = (
            str(manifest.release_version),
            str(manifest.release_commit),
            str(manifest.source_manifest_sha256),
            str(manifest.boot_database_sha256),
            str(manifest.verification_report_sha256),
            str(manifest.legacy_denylist_sha256),
            str(manifest.canonical_runtime_factory),
            str(manifest.canonical_orchestrator),
            str(getattr(manifest, "kernel_semantic_abi_fingerprint", "")),
        )
        expected = (
            self.attestation.release_version,
            self.attestation.release_commit,
            self.attestation.source_manifest_sha256,
            self.attestation.boot_database_sha256,
            self.attestation.verification_report_sha256,
            self.attestation.legacy_denylist_sha256,
            self.attestation.canonical_runtime_factory,
            self.attestation.canonical_orchestrator,
            self.attestation.kernel_semantic_abi_fingerprint,
        )
        if observed != expected:
            raise RuntimeAttestationError(
                "runtime authority manifest identity changed after attestation"
            )

    def require_service_authority(self) -> None:
        """O(1) hot-path validity check; never re-runs full release verification."""

        with self._lock:
            if not self._active:
                raise RuntimeAttestationError("runtime attestation is inactive")
            if self._generation != self.attestation.epoch.generation:
                raise RuntimeAttestationError(
                    "runtime attestation generation is stale"
                )
            self._assert_manifest_identity()

    def require_stage_adapter(
        self, *, stage: Any, adapter_ref: str, adapter_revision: int
    ) -> None:
        self.require_service_authority()
        # The underlying guard keeps this in an already-built stage map.
        self._guard.require_stage_adapter(
            stage=stage,
            adapter_ref=adapter_ref,
            adapter_revision=adapter_revision,
        )

    def load_runtime_factory(self):
        """Load the already-attested factory without re-verifying release files."""

        self.require_service_authority()
        module_name, sep, symbol = self.attestation.canonical_runtime_factory.partition(
            ":"
        )
        if not sep or not module_name or not symbol:
            raise RuntimeAttestationError(
                "canonical_runtime_factory must be module:symbol"
            )
        forbidden = tuple(
            getattr(self.manifest, "forbidden_runtime_import_prefixes", ())
        )
        if any(
            module_name == prefix or module_name.startswith(prefix + ".")
            for prefix in forbidden
        ):
            raise RuntimeAttestationError(
                "canonical runtime factory points into forbidden namespace"
            )
        module = importlib.import_module(module_name)
        factory = getattr(module, symbol, None)
        if factory is None or not callable(factory):
            raise RuntimeAttestationError(
                "canonical runtime factory is not callable"
            )
        return factory

    def invalidate(self) -> None:
        """Fail closed before a reload/swap."""

        with self._lock:
            self._active = False
            self._generation += 1

    @classmethod
    def verify_reload(
        cls,
        guard: Any,
        *,
        previous: "AttestedRuntimeAuthority | None" = None,
    ) -> "AttestedRuntimeAuthority":
        """Fully verify a reload and issue the next authority generation."""

        generation = 1 if previous is None else previous.authority_generation + 1
        attestation = RuntimeAttestation.verify(guard, generation=generation)
        replacement = cls(guard, attestation)
        if previous is not None:
            previous.invalidate()
        return replacement


__all__ = [
    "AttestedRuntimeAuthority",
    "RuntimeAttestation",
    "RuntimeAttestationError",
    "RuntimeEpoch",
]
