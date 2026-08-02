"""Execute one bounded corrective-replay validation tier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Sequence


_MAX_BOOTSTRAP_SOURCE_BYTES = 4 * 1024 * 1024


def _is_link_or_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        junction = getattr(path, "is_junction", None)
        if callable(junction) and junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError as exc:
        raise RuntimeError(f"cannot inspect reviewed source: {path.name}") from exc
    return bool(attributes & 0x400)


def _resolve_reviewed_source_path(path: Path) -> Path:
    scripts = Path(__file__).absolute().parent
    root = scripts.parent
    candidate = path if path.is_absolute() else scripts / path
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("reviewed validation source escapes its root") from exc
    current = root
    if _is_link_or_reparse(root):
        raise RuntimeError("Hybrid MVP root is a redirected path")
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            raise RuntimeError(
                f"reviewed validation source is redirected: {path.name}"
            )
        resolved = current.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("reviewed validation source escapes its root") from exc
        if resolved != current:
            raise RuntimeError(
                f"reviewed validation source is redirected: {path.name}"
            )
    return current

def _load_reviewed_source(path: Path, name: str) -> ModuleType:
    resolved = _resolve_reviewed_source_path(path)
    if not resolved.is_file():
        raise RuntimeError(f"reviewed validation source is unavailable: {path.name}")
    with resolved.open("rb") as stream:
        raw = stream.read(_MAX_BOOTSTRAP_SOURCE_BYTES + 1)
    if not raw or len(raw) > _MAX_BOOTSTRAP_SOURCE_BYTES:
        raise RuntimeError(f"reviewed validation source is invalid: {path.name}")
    code = compile(raw, str(resolved), "exec", dont_inherit=True, optimize=0)
    module = ModuleType(name)
    module.__file__ = str(resolved)
    module.__package__ = ""
    module.__cached__ = None
    module.__loader__ = None
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except BaseException:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    return module


_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
_load_reviewed_source(
    _ROOT / "src" / "cemm_authoritative_hybrid" / "process_control.py",
    "process_control",
)
_validation_gate = _load_reviewed_source(
    _SCRIPTS / "validation_gate.py", "_cemm_reviewed_validation_gate_cli"
)
AdmissionValidationError = _validation_gate.AdmissionValidationError
GateConfigError = _validation_gate.GateConfigError
PHASES = _validation_gate.PHASES
run_validation = _validation_gate.run_validation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("owner", "phase", "admission"))
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--owner")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args, unknown = parser.parse_known_args(list(argv) if argv is not None else None)
    if unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    if args.tier is None:
        parser.error("--tier is required")
    if args.phase is None:
        parser.error("--phase is required")
    if args.tier == "owner" and args.owner is None:
        parser.error("--owner is required for the owner tier")
    if args.tier != "owner" and args.owner is not None:
        parser.error("--owner is valid only for the owner tier")
    root = Path(__file__).resolve().parents[1]
    try:
        outcome = run_validation(
            root,
            phase=args.phase,
            tier=args.tier,
            owner=args.owner,
        )
        payload = outcome.to_dict()
        exit_code = outcome.exit_code
    except (GateConfigError, AdmissionValidationError) as exc:
        payload = {
            "disposition": "error",
            "error": str(exc),
            "owner": args.owner,
            "phase": args.phase,
            "schema": "cemm-validation-outcome-v1",
            "tier": args.tier,
        }
        exit_code = 2
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
