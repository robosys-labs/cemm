"""Public v3.5.1 runtime facade with one-time release attestation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .cutover import RuntimeAuthorityGuard, RuntimeAuthorityManifest
from .runtime_authority import AttestedRuntimeAuthority
from .version import VERSION


def _artifact_path(base: Path, value: object) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else base / path


class Runtime:
    VERSION = VERSION

    def __init__(
        self,
        *args: Any,
        authority_manifest_path: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        package_root = Path(__file__).resolve().parents[1]  # cemm/
        distribution_root = package_root.parent
        manifest_path = (
            Path(authority_manifest_path)
            if authority_manifest_path
            else package_root / "data/v350/runtime_authority_manifest.json"
        )
        manifest = RuntimeAuthorityManifest.load(manifest_path)
        boot_path = _artifact_path(
            distribution_root, manifest.metadata.get("boot_database_relpath")
        )
        report_path = _artifact_path(
            distribution_root,
            manifest.metadata.get("verification_report_relpath"),
        )
        requested_boot = kwargs.pop("boot_database_path", None)
        if requested_boot is not None:
            requested = Path(requested_boot).resolve()
            if boot_path is not None and requested != boot_path.resolve():
                raise ValueError(
                    "public runtime boot_database_path differs from signed "
                    "runtime-authority manifest"
                )
            boot_path = requested

        raw_guard = RuntimeAuthorityGuard(
            manifest,
            repo_root=distribution_root,
            boot_database_path=boot_path,
            verification_report_path=report_path,
        )
        authority = AttestedRuntimeAuthority.verify_reload(raw_guard)
        factory = authority.load_runtime_factory()

        if "services" in kwargs:
            raise ValueError(
                "public v3.5.1 runtime forbids arbitrary service injection; "
                "runtime services come from the signed canonical composition root"
            )

        runtime = factory(
            *args,
            authority_guard=authority,
            boot_database_path=boot_path,
            **kwargs,
        )
        if (
            runtime is self
            or not hasattr(runtime, "run_text")
            or not hasattr(runtime, "close")
        ):
            raise TypeError(
                "canonical runtime factory must return run_text()/close() runtime"
            )

        self._runtime = runtime
        self.authority_guard = authority
        self.runtime_attestation = authority.attestation
        self.runtime_epoch = authority.runtime_epoch

    def run_text(self, text: str, **kwargs: Any):
        # CanonicalOrchestrator performs the O(1) attestation-generation check.
        # Full release/source/boot verification is never repeated per turn.
        return self._runtime.run_text(text, **kwargs)

    def run_text_result(self, text: str, **kwargs: Any):
        return self.run_text(text, **kwargs)

    def close(self) -> None:
        self._runtime.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
