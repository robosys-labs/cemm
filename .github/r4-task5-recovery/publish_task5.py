from __future__ import annotations

import base64
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path.cwd()
HYBRID = REPO / "hybrid_mvp"
TARGET_BRANCH = "agent/r4-task4-batch-publisher-20260816"
EXPECTED_HEAD = "56d233a63be57d9ef611d617a4cf7430826b2324"
TASK4_PATCH_SHA256 = "4b419a98f651149a6e6c7c1dded1c8f538527540ac622661ac2efd78a4e38ed4"
TASK5_PATCH_SHA256 = "a90bab2d330cb84da5d460fcff85a2b16257768a8b25cea8fc1579bea79a078c"
ENVELOPE = REPO / ".github" / "r4-task5-recovery"

TASK4_PATHS = {
    "hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY.json",
    "hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    "hybrid_mvp/configs/r4_partitions.json",
    "hybrid_mvp/scripts/analyze_r4_partition_feasibility.py",
    "hybrid_mvp/scripts/publish_r4_feasibility_basis.py",
    "hybrid_mvp/src/cemm_authoritative_hybrid/r4_partitions.py",
    "hybrid_mvp/tests/test_publish_r4_feasibility_basis.py",
    "hybrid_mvp/tests/test_r4_partition_global_assignment.py",
}
TASK5_PATHS = {
    "hybrid_mvp/src/cemm_authoritative_hybrid/r4_partitions.py",
    "hybrid_mvp/src/cemm_authoritative_hybrid/r4_partition_verify.py",
    "hybrid_mvp/tests/test_r4_partition_global_assignment.py",
    "hybrid_mvp/tests/test_r4_mutations_and_partitions.py",
}
TRACKER = "hybrid_mvp/docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md"


def run(*args: str, cwd: Path = REPO, env: dict[str, str] | None = None, capture: bool = False) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print("+", " ".join(args), flush=True)
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=merged,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return completed.stdout.strip() if capture else ""


def git(*args: str, capture: bool = False) -> str:
    return run("git", *args, capture=capture)


def py(*args: str, cwd: Path = HYBRID, capture: bool = False) -> str:
    return run(sys.executable, *args, cwd=cwd, env={"PYTHONPATH": "src"}, capture=capture)


def reconstruct(name: str, expected: str) -> Path:
    source = ENVELOPE / f"{name}.xz.b64"
    encoded = b"".join(source.read_bytes().split())
    packed = base64.b64decode(encoded, validate=True)
    patch = lzma.decompress(packed, format=lzma.FORMAT_XZ)
    observed = hashlib.sha256(patch).hexdigest()
    if observed != expected:
        raise RuntimeError(f"{name} patch SHA-256 mismatch: {observed} != {expected}")
    if not patch.startswith(b"diff --git ") or b"\r" in patch:
        raise RuntimeError(f"{name} patch is not a normalized Git patch")
    output = Path("/tmp") / f"r4-{name}.patch"
    output.write_bytes(patch)
    print(f"authenticated {name}: bytes={len(patch)} sha256={observed}")
    return output


def status_paths() -> set[str]:
    raw = git("status", "--porcelain=v1", capture=True)
    if not raw:
        return set()
    return {row[3:].split(" -> ", 1)[-1] for row in raw.splitlines()}


def assert_scope(expected: set[str], label: str) -> None:
    observed = status_paths()
    if observed != expected:
        raise RuntimeError(f"{label} scope mismatch: observed={sorted(observed)} expected={sorted(expected)}")


def assert_clean() -> None:
    observed = status_paths()
    if observed:
        raise RuntimeError(f"working tree is not clean: {sorted(observed)}")


def validate_inventory() -> None:
    py("scripts/check_test_inventory.py", "--phase", "R4", "--source-only")
    py("scripts/check_test_inventory.py", "--phase", "R5", "--source-only")


def validate_task4() -> None:
    py(
        "-m", "pytest",
        "tests/test_r4_partition_contracts.py",
        "tests/test_r4_partition_global_assignment.py",
        "tests/test_publish_r4_feasibility_basis.py",
        "-q", "-p", "no:cacheprovider",
    )
    py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--basis", "--check", "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    )
    py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--final", "--check", "artifacts/validation/R4_PARTITION_FEASIBILITY.json",
    )
    validate_inventory()
    git("diff", "--check")


def validate_task5() -> None:
    py(
        "-m", "pytest",
        "tests/test_r4_partition_global_assignment.py",
        "tests/test_r4_mutations_and_partitions.py",
        "-q", "-p", "no:cacheprovider",
    )
    candidate = "/tmp/R4_PARTITION_FEASIBILITY_BASIS_TASK5.json"
    py("scripts/analyze_r4_partition_feasibility.py", "--basis", "--output", candidate)
    py(
        "scripts/publish_r4_feasibility_basis.py",
        "--candidate", candidate,
        "--config", "configs/r4_partitions.json",
        "--current", "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    )
    py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--basis", "--check", "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    )
    py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--final", "--check", "artifacts/validation/R4_PARTITION_FEASIBILITY.json",
    )
    py("-m", "pytest", "tests/test_r4_partition_contracts.py", "-q", "-p", "no:cacheprovider")
    validate_inventory()
    git("diff", "--check")
    protected = {
        "hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
        "hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY.json",
        "hybrid_mvp/configs/r4_partitions.json",
    }
    dirty_protected = status_paths() & protected
    if dirty_protected:
        raise RuntimeError(f"Task 5 changed frozen feasibility authority: {sorted(dirty_protected)}")


def commit_paths(paths: set[str], message: str) -> str:
    run("git", "add", "--", *sorted(paths))
    git("diff", "--cached", "--check")
    git("commit", "-m", message)
    sha = git("rev-parse", "HEAD", capture=True)
    assert_clean()
    return sha


def update_tracker(task4_sha: str, task5_sha: str) -> str:
    tracker = REPO / TRACKER
    text = tracker.read_text("utf-8")
    if not re.fullmatch(r"[0-9a-f]{40}", task4_sha) or not re.fullmatch(r"[0-9a-f]{40}", task5_sha):
        raise RuntimeError("invalid implementation SHA")
    basis = json.loads((HYBRID / "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json").read_text("utf-8"))
    final = json.loads((HYBRID / "artifacts/validation/R4_PARTITION_FEASIBILITY.json").read_text("utf-8"))

    replacements = {
        "- [ ] Preserve every exact protected identity across all seven axes as a\n  namespaced leakage hyperedge.": "- [x] Preserve every exact protected identity across all seven axes as a\n  namespaced leakage hyperedge.",
        "- [ ] Reject sentinel/coarse categorical union keys.": "- [x] Reject sentinel/coarse categorical union keys.",
        "- [ ] Implement deterministic global component assignment.": "- [x] Implement deterministic global component assignment.",
        "- [ ] Implement independent verifier reconstruction.": "- [x] Implement independent verifier reconstruction.",
        "- [ ] Generate feasibility report before freezing thresholds.": "- [x] Generate feasibility report before freezing thresholds.",
        "- [ ] Preserve the acyclic basis → config → final receipt identity graph; changed basis refs stop for amended review.": "- [x] Preserve the acyclic basis → config → final receipt identity graph; changed basis refs stop for amended review.",
        "- [ ] Review exact positive minimum counts.": "- [x] Review exact positive minimum counts.",
        "- [ ] Require support and feasible-component denominators.": "- [x] Require support and feasible-component denominators.",
        "- [ ] Require held-out coverage across configured dimensions.": "- [x] Require held-out coverage across configured dimensions.",
    }
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"missing tracker checklist line: {old}")
        text = text.replace(old, new, 1)

    anchor = "| 2026-08-14 | `codex/r4-partition-corrective-replay@b9efaba3a05dea0006b74d882671a98fd5f1547e` | Strict R4 partition, sufficiency, config, capability, and authorization contracts registered | Contract/schema/inventory suites passed; owner and phase tiers remained correctly governance-blocked by the deliberate R4-red ledger state |"
    if anchor not in text:
        raise RuntimeError("publication log anchor missing")
    rows = (
        f"\n| 2026-08-17 | `agent/r4-task4-batch-publisher-20260816@{task4_sha}` | Read-only seven-axis leakage feasibility checkpoint reconstructed | 400 sources; {basis['hyperedge_count']} exact hyperedges; {basis['label_count']} labels; {basis['component_count']} components; largest {basis['largest_component_count']}; basis/config/final identities check |"
        f"\n| 2026-08-17 | `agent/r4-task4-batch-publisher-20260816@{task5_sha}` | Deterministic four-class assignment and independent reconstruction completed | Whole-component assignment, permutation determinism, split-tamper rejection, giant-component infeasibility, equal-only feasibility publisher, R4/R5 inventory checks passed |"
    )
    text = text.replace(anchor, anchor + rows, 1)

    checkpoint = re.compile(r"## 11\. Current checkpoint\n\n.*?\n\n## 12\. Exact invalidation evidence", re.S)
    replacement = f"""## 11. Current checkpoint

**Current work:** P5 in progress; Task 5 deterministic four-class assignment and independent verification are complete at `{task5_sha}`.
**Task 4 feasibility identities:** graph `{basis['graph_ref']}`; basis `{basis['feasibility_basis_ref']}`; witness `{basis['minima_witness_ref']}`; config `{final['config_ref']}`; final `{final['receipt_ref']}`.
**Next required action:** Task 6 cuts Build Receipt ABI 4 and prepares deterministic temporary four-class generated fixtures.
**Implementation authorization:** Task 6 source/schema/test work is authorized; checked-in replacement R4 artifacts, re-admission, and neural training remain blocked.
**R5 neural work:** blocked on authentic R4 re-admission.

## 12. Exact invalidation evidence"""
    text, count = checkpoint.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError("current checkpoint replacement failed")
    tracker.write_text(text, encoding="utf-8")

    validate_inventory()
    git("diff", "--check")
    return commit_paths({TRACKER}, "docs(r4): record global assignment checkpoint")


def final_verify(task4_sha: str, task5_sha: str, docs_sha: str) -> None:
    if git("rev-parse", "HEAD^^", capture=True) != task4_sha:
        raise RuntimeError("Task 4 ancestry mismatch")
    if git("rev-parse", "HEAD^", capture=True) != task5_sha:
        raise RuntimeError("Task 5 ancestry mismatch")
    if git("rev-parse", "HEAD", capture=True) != docs_sha:
        raise RuntimeError("docs ancestry mismatch")
    if git("merge-base", EXPECTED_HEAD, "HEAD", capture=True) != EXPECTED_HEAD:
        raise RuntimeError("candidate is not a fast-forward from the expected target")
    assert_clean()
    git("diff", "--check", f"{EXPECTED_HEAD}..HEAD")
    py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--basis", "--check", "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    )
    py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--final", "--check", "artifacts/validation/R4_PARTITION_FEASIBILITY.json",
    )
    chain = py("scripts/update_replay_status.py", "--verify-chain", capture=True)
    print(chain)
    if "R4=red" not in chain:
        raise RuntimeError("R4 replay state is not deliberately red after Task 5")
    if git("rev-parse", f"{EXPECTED_HEAD}:hybrid_mvp/governance/replay_status.jsonl", capture=True) != git(
        "rev-parse", "HEAD:hybrid_mvp/governance/replay_status.jsonl", capture=True
    ):
        raise RuntimeError("Task 4/5 unexpectedly changed replay ledger")
    if git("rev-parse", f"{EXPECTED_HEAD}:hybrid_mvp/artifacts/r4", capture=True) != git(
        "rev-parse", "HEAD:hybrid_mvp/artifacts/r4", capture=True
    ):
        raise RuntimeError("Task 4/5 unexpectedly changed checked-in R4 artifact tree")


def publish(task4_sha: str, task5_sha: str, docs_sha: str) -> None:
    git("fetch", "origin", TARGET_BRANCH)
    remote = git("rev-parse", f"origin/{TARGET_BRANCH}", capture=True)
    if remote != EXPECTED_HEAD:
        raise RuntimeError(f"target moved before publication: {remote}")
    for expected_parent, sha, label in (
        (EXPECTED_HEAD, task4_sha, "Task 4"),
        (task4_sha, task5_sha, "Task 5"),
        (task5_sha, docs_sha, "docs"),
    ):
        remote = git("rev-parse", f"origin/{TARGET_BRANCH}", capture=True)
        if remote != expected_parent:
            raise RuntimeError(f"{label} publication parent mismatch: {remote} != {expected_parent}")
        git("push", "origin", f"{sha}:refs/heads/{TARGET_BRANCH}")
        git("fetch", "origin", TARGET_BRANCH)
        remote = git("rev-parse", f"origin/{TARGET_BRANCH}", capture=True)
        if remote != sha:
            raise RuntimeError(f"{label} remote verification failed: {remote} != {sha}")
        print(f"published {label}: {sha}")


def main() -> int:
    task4_patch = reconstruct("task4", TASK4_PATCH_SHA256)
    task5_patch = reconstruct("task5", TASK5_PATCH_SHA256)

    run(sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "pytest==8.4.0", "jsonschema==4.25.1")

    git("fetch", "origin", TARGET_BRANCH)
    remote = git("rev-parse", f"origin/{TARGET_BRANCH}", capture=True)
    if remote != EXPECTED_HEAD:
        raise RuntimeError(f"target moved before build: {remote}")
    git("checkout", "-B", "r4-task5-publish-candidate", f"origin/{TARGET_BRANCH}")
    if git("rev-parse", "HEAD", capture=True) != EXPECTED_HEAD:
        raise RuntimeError("target checkout SHA mismatch")
    assert_clean()

    git("apply", "--check", str(task4_patch))
    git("apply", str(task4_patch))
    assert_scope(TASK4_PATHS, "Task 4")
    validate_task4()
    task4_sha = commit_paths(TASK4_PATHS, "feat(r4): reconstruct leakage feasibility")

    git("apply", "--check", str(task5_patch))
    git("apply", str(task5_patch))
    assert_scope(TASK5_PATHS, "Task 5")
    validate_task5()
    task5_sha = commit_paths(TASK5_PATHS, "feat(r4): assign globally sealed data classes")

    docs_sha = update_tracker(task4_sha, task5_sha)
    final_verify(task4_sha, task5_sha, docs_sha)
    publish(task4_sha, task5_sha, docs_sha)

    print(json.dumps({"task4": task4_sha, "task5": task5_sha, "docs": docs_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
