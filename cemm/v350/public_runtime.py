"""Public v3.5 runtime facade.

This facade is intentionally thin: it validates the exact release-authority
manifest and delegates to the one canonical runtime factory.  It contains no
legacy fallback and no semantic interpretation logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .cutover import RuntimeAuthorityGuard, RuntimeAuthorityManifest
from .version import VERSION


class Runtime:
    VERSION = VERSION

    def __init__(self, *args: Any, authority_manifest_path: str | Path | None = None, **kwargs: Any) -> None:
        package_root = Path(__file__).resolve().parents[1]
        repo_root = package_root.parent
        manifest_path = Path(authority_manifest_path) if authority_manifest_path else package_root / "data/v350/runtime_authority_manifest.json"
        manifest = RuntimeAuthorityManifest.load(manifest_path)
        guard = RuntimeAuthorityGuard(manifest, repo_root=repo_root)
        factory = guard.load_runtime_factory()
        runtime = factory(*args, authority_guard=guard, **kwargs)
        if runtime is self or not hasattr(runtime, "run_text") or not hasattr(runtime, "close"):
            raise TypeError("canonical runtime factory must return an object with run_text() and close()")
        self._runtime = runtime
        self.authority_guard = guard

    def run_text(self, text: str, **kwargs: Any):
        self.authority_guard.require_service_authority()
        return self._runtime.run_text(text, **kwargs)

    def run_text_result(self, text: str, **kwargs: Any):
        self.authority_guard.require_service_authority()
        method = getattr(self._runtime, "run_text_result", None)
        return method(text, **kwargs) if callable(method) else self._runtime.run_text(text, **kwargs)

    def close(self) -> None:
        self._runtime.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
