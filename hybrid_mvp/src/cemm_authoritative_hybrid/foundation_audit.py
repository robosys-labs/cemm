"""Conservative static import audit for the one admitted foundation path.

The historical modules can exist in Git history, but must not be reachable
from the root-installed semantic foundation. The audit is source based, avoids
import side effects, and expands Python relative imports recursively. It is
not a general Python call graph or a security proof.
"""
from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent
PACKAGE = "cemm_authoritative_hybrid"
ENTRYPOINTS = frozenset({"foundation", "foundation_cli"})
INELIGIBLE_RUNTIME_MODULES = frozenset({
    "model", "training", "realization", "evaluation", "effects",
})


def reachable_modules() -> frozenset[str]:
    available = {
        p.relative_to(SOURCE_ROOT).with_suffix("").as_posix().replace("/", "."): p
        for p in SOURCE_ROOT.rglob("*.py")
    }
    queue = list(sorted(ENTRYPOINTS))
    visited: set[str] = set()
    while queue:
        module = queue.pop()
        if module in visited:
            continue
        path = available.get(module)
        if path is None:
            raise ValueError(f"missing admitted module: {module}")
        visited.add(module)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parts = module.split(".")
        package_parts = parts[:-1]  # __init__.py is represented as pkg.__init__
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "cemm" or name.startswith("cemm."):
                        raise ValueError(f"retired root import in {module}: {name}")
                    if name.startswith(PACKAGE + "."):
                        target = name[len(PACKAGE) + 1:]
                        if target in available:
                            queue.append(target)
            elif isinstance(node, ast.ImportFrom):
                name = node.module or ""
                if node.level == 0:
                    if name == "cemm" or name.startswith("cemm."):
                        raise ValueError(f"retired root import in {module}: {name}")
                    if name.startswith(PACKAGE + "."):
                        target = name[len(PACKAGE) + 1:]
                        if target in available:
                            queue.append(target)
                else:
                    # level=1 uses current package; level=2 moves up once.
                    if node.level > len(package_parts) + 1:
                        raise ValueError(f"out-of-package import: {module}")
                    relative = package_parts[: len(package_parts) - node.level + 1]
                    target = ".".join((*relative, *([name] if name else [])))
                    if target in available:
                        queue.append(target)
                    for alias in node.names:
                        member = target + "." + alias.name
                        if member in available:
                            queue.append(member)
    illegal = sorted(INELIGIBLE_RUNTIME_MODULES.intersection(
        name.partition(".")[0] for name in visited
    ))
    if illegal:
        raise ValueError(f"unadmitted neural/template module reachable: {illegal}")
    return frozenset(visited)


def verify_retirement(repo_root: Path) -> None:
    """Reject working-tree reintroduction of retired historical directories."""
    for path in (
        "cemm", "archive", "tests", "tools", "reference",
        "hybrid_mvp/.lineage-recovery",
    ):
        if (repo_root / path).exists():
            raise ValueError(f"retired executable/history path is back: {path}")
