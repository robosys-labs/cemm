#!/usr/bin/env python
"""Fail-closed entry point for future authentic R4 episode generation.

R1 admits only diagnostic Semantic Episode ABI 2 records through VERIFY.  It
has no authority to regenerate reviewed gold or replace the quarantined
Program ABI 1 corpus.  This caller activates the one canonical runtime and
then stops at the missing R4 corpus owner before reading scenarios or writing
an output artifact.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.bootstrap import load_runtime  # noqa: E402
from cemm_authoritative_hybrid.gaps import MissingOwner  # noqa: E402
from cemm_authoritative_hybrid.runtime import HybridRuntime  # noqa: E402


R4_AUTHENTIC_EPISODE_GENERATION_OWNER = (
    "r4_authentic_episode_generation_owner"
)


def build_all_episodes(
    scenarios_path: Path,
    *,
    runtime: HybridRuntime,
    seed: int = 1701,
) -> NoReturn:
    """Reject corpus generation until the authentic R4 owner is admitted."""
    if type(runtime) is not HybridRuntime:
        raise TypeError("runtime must be an exact HybridRuntime")
    if not isinstance(scenarios_path, Path):
        raise TypeError("scenarios_path must be an exact Path")
    if type(seed) is not int:
        raise TypeError("seed must be an exact int")
    raise MissingOwner(R4_AUTHENTIC_EPISODE_GENERATION_OWNER)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Activate the canonical runtime and fail closed until authentic "
            "R4 episode generation is admitted."
        )
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=ROOT / "data" / "scenarios" / "use_cases.jsonl",
        help="Future R4 reviewed scenario-contract input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "episodes" / "all.jsonl",
        help="Future R4 output; R1 never creates or overwrites it.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1701,
        help="Future deterministic R4 seed (default: 1701).",
    )
    parser.add_argument(
        "--profile",
        choices=("development", "neural", "release"),
        default="development",
        help="Canonical runtime profile to activate (default: development).",
    )
    parser.add_argument(
        "--store-path",
        type=Path,
        default=None,
        help="Optional canonical runtime store path.",
    )
    args = parser.parse_args()

    runtime = load_runtime(
        ROOT,
        profile=args.profile,
        store_path=args.store_path,
    )
    try:
        build_all_episodes(
            args.scenarios,
            runtime=runtime,
            seed=args.seed,
        )
    finally:
        runtime.stores.close()


if __name__ == "__main__":
    main()
