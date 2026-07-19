#!/usr/bin/env python3
"""Build a signed-input verification report for one exact v3.5 release commit.

The report is a release artifact, not a substitute for tests. ``status=pass`` is
emitted only when every required command succeeds and deterministic boot output
matches the supplied boot database byte-for-byte by SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def run(root: Path, argv: list[str]) -> dict:
    proc=subprocess.run(argv,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return {"argv":argv,"returncode":proc.returncode,"output":proc.stdout[-20000:]}


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,default=Path("."))
    p.add_argument("--release-commit",required=True)
    p.add_argument("--boot-db",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); root=args.repo_root.resolve(); boot=args.boot_db.resolve()
    if len(args.release_commit)!=40 or any(c not in "0123456789abcdef" for c in args.release_commit):
        raise SystemExit("release commit must be exact lowercase 40-hex SHA")
    if not boot.is_file(): raise SystemExit(f"missing boot database:{boot}")
    commands=[
        [sys.executable,"tools/check_v350_architecture.py"],
        [sys.executable,"-m","pytest","-q","tests/v350"],
        [sys.executable,"tools/verify_v350_foundation.py"],
        [sys.executable,"tools/verify_v350_language_grounding.py"],
        [sys.executable,"tools/verify_v350_composition.py"],
        [sys.executable,"tools/verify_v350_epistemics.py"],
        [sys.executable,"tools/verify_v350_transitions.py"],
        [sys.executable,"tools/verify_v350_vertical_slices.py"],
        [sys.executable,"tools/verify_v350_phase20.py","--preactivation"],
        [sys.executable,"-m","pytest","-q"],
    ]
    results=[]; passed=True
    for command in commands:
        item=run(root,command); results.append(item)
        if item["returncode"]!=0: passed=False; break

    deterministic={"checked":False}
    wheel_check={"checked":False}
    if passed:
        with tempfile.TemporaryDirectory(prefix="cemm-v350-release-") as tmp:
            tmp=Path(tmp); a=tmp/"boot-a.sqlite"; b=tmp/"boot-b.sqlite"
            ra=run(root,[sys.executable,"tools/compile_v350_data.py","--output",str(a),"--writable"])
            rb=run(root,[sys.executable,"tools/compile_v350_data.py","--output",str(b),"--writable"])
            results.extend((ra,rb))
            passed=ra["returncode"]==0 and rb["returncode"]==0 and a.is_file() and b.is_file()
            if passed:
                sha_a,sha_b,sha_boot=sha256(a),sha256(b),sha256(boot)
                deterministic={"checked":True,"compile_a_sha256":sha_a,"compile_b_sha256":sha_b,"boot_database_sha256":sha_boot,"match":sha_a==sha_b==sha_boot}
                passed=bool(deterministic["match"])
            if passed:
                wheel_dir=tmp/"wheel"; wheel_dir.mkdir()
                rw=run(root,[sys.executable,"-m","pip","wheel",".","--no-deps","--no-build-isolation","-w",str(wheel_dir)])
                results.append(rw); wheels=tuple(wheel_dir.glob("*.whl"))
                if rw["returncode"]!=0 or len(wheels)!=1: passed=False
                else:
                    rv=run(root,[sys.executable,"tools/verify_v350_phase20.py","--preactivation","--wheel",str(wheels[0])])
                    results.append(rv); passed=rv["returncode"]==0
                    wheel_check={"checked":True,"wheel_name":wheels[0].name,"wheel_sha256":sha256(wheels[0]),"passed":passed}
    report={
        "status":"pass" if passed else "fail",
        "release_commit":args.release_commit,
        "boot_database_sha256":sha256(boot),
        "deterministic_boot":deterministic,
        "wheel_quarantine":wheel_check,
        "checks":results,
    }
    out=args.output if args.output.is_absolute() else root/args.output
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(out)
    return 0 if passed else 1

if __name__=="__main__": raise SystemExit(main())
