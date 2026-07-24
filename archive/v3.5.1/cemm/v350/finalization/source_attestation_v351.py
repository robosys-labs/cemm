"""Deterministic runtime source-tree attestation."""
from __future__ import annotations

import hashlib
from pathlib import Path


PUBLIC_ENTRYPOINT_PATHS = (
    "cemm/__init__.py",
    "cemm/__main__.py",
    "cemm/app/runtime.py",
    "cemm/web_demo.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_source_inventory_v351(repo_root: str | Path):
    root = Path(repo_root).resolve()
    files = {path for path in (root / "cemm/v350").rglob("*.py") if path.is_file()}
    files.update(root / item for item in PUBLIC_ENTRYPOINT_PATHS if (root / item).is_file())
    return tuple(sorted(files, key=lambda path: path.relative_to(root).as_posix()))


def runtime_source_root_v351(repo_root: str | Path):
    root = Path(repo_root).resolve()
    inventory = runtime_source_inventory_v351(root)
    lines = tuple(
        f"{path.relative_to(root).as_posix()}\0{sha256_file(path)}"
        for path in inventory
    )
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return digest, tuple(lines)


__all__ = ["PUBLIC_ENTRYPOINT_PATHS", "runtime_source_inventory_v351", "runtime_source_root_v351", "sha256_file"]
