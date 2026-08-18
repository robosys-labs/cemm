from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path.cwd()
ROOT = REPO / ".github" / "r4-task5-recovery"
TEMP_ENVELOPE = Path("/tmp/r4-task5-envelope")
EXPECTED_AGGREGATE_SHA256 = "a4eabfd5480ce9df928aff3218c83583b4e87634a785ce9d3770808db470e73d"
EXPECTED_AGGREGATE_BYTES = 30384
EXPECTED_BASIS_REF = "r4_partition_feasibility_basis_v1:8d7b96e61cd31e98bbc9de46"
EXPECTED_GRAPH_REF = "r4_partition_graph_v3:c80724e6107d010c724ad341"
EXPECTED_WITNESS_REF = "r4_partition_minima_witness_v1:7283c55335905b1dba4e6c67"
EXPECTED_CONFIG_REF = "r4_partition_config_v1:0647f2402b0b942044c243ec"
EXPECTED_FINAL_REF = "r4_partition_feasibility_v1:654878fb2b7e874d07ff31e4"

TASK4_CHUNKS = (
    ("task4.00.0", "0768010ef82d3f3289383d8f20a598f2ce3d9380e1899a904af43cdd4710d2a2"),
    ("task4.00.1", "32ec659c3a6f3a80324061f302f5b4a0bfce83b761d24b1be078ba3f0f832ee7"),
    ("task4.00.2", "71f475a90e49537e497cb13f742265fdefa48e9fd998bfe95103bb9102f31896"),
    ("task4.00.3a", "a5d6e3d3fc0ca71af79488b830db20dc1b99ec486c0264ddc25e678e3cc2ffa0"),
    ("task4.00.3b", "4a71e4eb14a606a9f12f8c20c868349c82d97605726626795ce050c5b0ba93ba"),
    ("task4.part.01", "cc247d9143d5e79f786c20fd8f020e091ed0e97b94a7022399897e119e8e6134"),
    ("task4.02.0", "9c5f3caad8042aa4130ddb3b5eee5d0ef90389ee289f5a38de60eba44f3fd116"),
    ("task4.02.1a", "1cc6c77c419b6b8eeaf7d2bac0969d72686e49154c24ad41d6649409f64c5bc5"),
    ("task4.02.1b", "3f785a3317bc6a1b107ce338b43a2d61e1f845a07a8ffc9f7a437b1affb19940"),
    ("task4.02.2", "9e00c806c38f80f631910deb0ee6a29ebd5212f1046d229860a403015f8cbbde"),
    ("task4.02.3", "041a2f353438880c010add43f383303df668535f350073333cd3daf26c9d5641"),
    ("task4.03.0", "e58847995ba8bcd8013ad7aec05d42a31ec1685362fa29d7a4fdf59e6e806140"),
    ("task4.03.1", "a76f002a98df16976228ff5624641ffcea8d017732f129908a7c68413f270ace"),
    ("task4.03.2", "1f91ac221be45e98080319d48a372b535f51931f7271c5e4839b3ccc7af03f5c"),
    ("task4.03.3", "5a8eef0a078119004ffec372a7c1673affb12109cd172d283532c7e149eeaae0"),
)


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
    return completed.stdout.rstrip("\r\n") if capture else ""


def stage_envelopes() -> None:
    chunks: list[bytes] = []
    for name, expected in TASK4_CHUNKS:
        payload = (ROOT / name).read_bytes()
        observed = hashlib.sha256(payload).hexdigest()
        if observed != expected:
            raise RuntimeError(f"{name} SHA mismatch: {observed} != {expected}")
        chunks.append(payload)
    task4 = b"".join(chunks)
    observed = hashlib.sha256(task4).hexdigest()
    if len(task4) != EXPECTED_AGGREGATE_BYTES or observed != EXPECTED_AGGREGATE_SHA256:
        raise RuntimeError(
            f"Task 4 aggregate mismatch: bytes={len(task4)} sha256={observed}"
        )
    TEMP_ENVELOPE.mkdir(parents=True, exist_ok=True)
    (TEMP_ENVELOPE / "task4.xz.b64").write_bytes(task4)
    (TEMP_ENVELOPE / "task5.xz.b64").write_bytes((ROOT / "task5.xz.b64").read_bytes())
    print(f"authenticated Task 4 transport: bytes={len(task4)} sha256={observed}")


def load_publisher():
    script = ROOT / "publish_task5.py"
    spec = importlib.util.spec_from_file_location("r4_task5_publisher", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Task 5 publisher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ENVELOPE = TEMP_ENVELOPE
    module.run = run
    return module


def install_test_deps() -> None:
    run(
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "pytest==8.4.0",
        "jsonschema==4.25.1",
    )


def configure_git(module) -> None:
    module.git("config", "user.name", "github-actions[bot]")
    module.git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")


def checkout_target(module, local_branch: str) -> None:
    module.git("fetch", "origin", module.TARGET_BRANCH)
    remote = module.git("rev-parse", f"origin/{module.TARGET_BRANCH}", capture=True)
    if remote != module.EXPECTED_HEAD:
        raise RuntimeError(f"target moved before {local_branch}: {remote}")
    module.git("checkout", "-B", local_branch, f"origin/{module.TARGET_BRANCH}")
    if module.git("rev-parse", "HEAD", capture=True) != module.EXPECTED_HEAD:
        raise RuntimeError("target checkout SHA mismatch")
    module.assert_clean()


def normalize_task4_host_independent(module) -> tuple[dict, dict]:
    analyzer = module.HYBRID / "scripts/analyze_r4_partition_feasibility.py"
    text = analyzer.read_text("utf-8")
    old = '        "solver": feasibility.solver_stats.as_dict(),\n'
    new = (
        '        "solver": {\n'
        '            key: value\n'
        '            for key, value in feasibility.solver_stats.as_dict().items()\n'
        '            if key != "wall_seconds_millis"\n'
        '        },\n'
    )
    if text.count(old) != 1:
        raise RuntimeError("Task 4 solver identity anchor is not exact")
    analyzer.write_text(text.replace(old, new, 1), encoding="utf-8")

    module.py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--basis",
        "--output",
        "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    )
    basis_path = module.HYBRID / "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json"
    basis = json.loads(basis_path.read_text("utf-8"))
    if basis["feasibility_basis_ref"] != EXPECTED_BASIS_REF:
        raise RuntimeError(f"unexpected basis ref: {basis['feasibility_basis_ref']}")
    if basis["graph_ref"] != EXPECTED_GRAPH_REF:
        raise RuntimeError(f"unexpected graph ref: {basis['graph_ref']}")
    if basis["minima_witness_ref"] != EXPECTED_WITNESS_REF:
        raise RuntimeError(f"unexpected witness ref: {basis['minima_witness_ref']}")
    if basis["solver"] != {
        "estimated_memory_bytes": 252960,
        "key_width_ints": 93,
        "state_count": 85,
    }:
        raise RuntimeError(f"unexpected deterministic solver material: {basis['solver']}")

    src = str(module.HYBRID / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from cemm_authoritative_hybrid.canonical import stable_ref

    config_path = module.HYBRID / "configs/r4_partitions.json"
    config = json.loads(config_path.read_text("utf-8"))
    config["feasibility_basis_ref"] = basis["feasibility_basis_ref"]
    config["config_ref"] = stable_ref(
        "r4_partition_config_v1",
        {key: value for key, value in config.items() if key != "config_ref"},
    )
    if config["config_ref"] != EXPECTED_CONFIG_REF:
        raise RuntimeError(f"unexpected config ref: {config['config_ref']}")
    config_path.write_text(
        json.dumps(config, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    module.py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--final",
        "--output",
        "artifacts/validation/R4_PARTITION_FEASIBILITY.json",
    )
    final_path = module.HYBRID / "artifacts/validation/R4_PARTITION_FEASIBILITY.json"
    final = json.loads(final_path.read_text("utf-8"))
    if final["receipt_ref"] != EXPECTED_FINAL_REF:
        raise RuntimeError(f"unexpected final ref: {final['receipt_ref']}")
    if final["config_ref"] != EXPECTED_CONFIG_REF:
        raise RuntimeError(f"unexpected final config ref: {final['config_ref']}")
    return basis, final


def apply_task4(module, patch: Path) -> None:
    module.git("apply", "--check", str(patch))
    module.git("apply", str(patch))
    normalize_task4_host_independent(module)
    module.assert_scope(module.TASK4_PATHS, "Task 4")


def apply_task5(module, patch: Path) -> None:
    module.git("apply", "--check", str(patch))
    module.git("apply", str(patch))
    module.assert_scope(module.TASK5_PATHS, "Task 5")


def verify_task4() -> int:
    stage_envelopes()
    module = load_publisher()
    install_test_deps()
    task4_patch = module.reconstruct("task4", module.TASK4_PATCH_SHA256)
    checkout_target(module, "r4-task4-verify")
    apply_task4(module, task4_patch)
    module.validate_task4()
    print("Task 4 cross-host verification passed")
    return 0


def verify_task5() -> int:
    stage_envelopes()
    module = load_publisher()
    install_test_deps()
    configure_git(module)
    task4_patch = module.reconstruct("task4", module.TASK4_PATCH_SHA256)
    task5_patch = module.reconstruct("task5", module.TASK5_PATCH_SHA256)
    checkout_target(module, "r4-task5-verify")
    apply_task4(module, task4_patch)
    module.commit_paths(module.TASK4_PATHS, "verify(r4): prepare Task 4 prerequisite")
    apply_task5(module, task5_patch)
    module.validate_task5()
    print("Task 5 deterministic allocator/verifier verification passed")
    return 0


def publish_verified() -> int:
    stage_envelopes()
    module = load_publisher()
    configure_git(module)
    task4_patch = module.reconstruct("task4", module.TASK4_PATCH_SHA256)
    task5_patch = module.reconstruct("task5", module.TASK5_PATCH_SHA256)
    checkout_target(module, "r4-task5-publish-candidate")

    apply_task4(module, task4_patch)
    module.py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--basis",
        "--check",
        "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json",
    )
    module.py(
        "scripts/analyze_r4_partition_feasibility.py",
        "--final",
        "--check",
        "artifacts/validation/R4_PARTITION_FEASIBILITY.json",
    )
    task4_sha = module.commit_paths(module.TASK4_PATHS, "feat(r4): reconstruct leakage feasibility")

    apply_task5(module, task5_patch)
    task5_sha = module.commit_paths(module.TASK5_PATHS, "feat(r4): assign globally sealed data classes")

    docs_sha = module.update_tracker(task4_sha, task5_sha)
    module.final_verify(task4_sha, task5_sha, docs_sha)
    module.publish(task4_sha, task5_sha, docs_sha)
    print(json.dumps({"task4": task4_sha, "task5": task5_sha, "docs": docs_sha}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("verify-task4", "verify-task5", "publish"))
    args = parser.parse_args()
    if args.mode == "verify-task4":
        return verify_task4()
    if args.mode == "verify-task5":
        return verify_task5()
    return publish_verified()


if __name__ == "__main__":
    raise SystemExit(main())
