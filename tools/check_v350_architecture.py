#!/usr/bin/env python3
"""Run v3.5 prohibitions and the v3.4.7 authority-debt ratchet."""
from __future__ import annotations

from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cemm.v350.architecture_lint import (
    render_violations,
    scan_legacy_debt,
    scan_tree,
)


def main() -> int:
    repository_root = REPOSITORY_ROOT
    package_root = repository_root / "cemm" / "v350"
    failed = False
    violations = scan_tree(package_root)
    if violations:
        print(render_violations(violations, root=repository_root), file=sys.stderr)
        failed = True
    full_checkout = (repository_root / "pyproject.toml").is_file() and (
        repository_root / "cemm" / "v347"
    ).is_dir()
    if full_checkout:
        debt = scan_legacy_debt(repository_root)
        for item in debt:
            print(
                f"{item.path.relative_to(repository_root)}: {item.debt_id}: {item.message}",
                file=sys.stderr,
            )
            failed = True
    if failed:
        return 1
    if full_checkout:
        print("v3.5 architecture lint passed; v3.4.7 authority debt did not increase")
    else:
        print(
            "v3.5 architecture lint passed; legacy-debt ratchet requires a complete repository checkout"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
