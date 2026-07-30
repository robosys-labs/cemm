#!/usr/bin/env python
"""Build deterministic semantic episodes from reviewed scenarios.

For each reviewed scenario in the source JSONL, this script:

1. Loads the scenario and builds a :class:`ScenarioCase`.
2. Uses the :class:`EpisodeBuilder` to run the six-phase runtime and record
   the full six-phase output as a :class:`SemanticEpisode`.
3. Writes all episodes as canonical JSONL (byte-deterministic).

Two runs with the same seed produce byte-identical output.

Usage::

    python scripts/build_episodes.py --scenarios data/scenarios/use_cases.jsonl --output data/episodes/all.jsonl --seed 1701
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the src directory is on the path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.episodes import (
    EpisodeBuilder,
    SemanticEpisode,
    load_scenarios,
    validate_episode,
    write_episodes,
)


def build_all_episodes(
    scenarios_path: Path, *, seed: int = 1701
) -> list[SemanticEpisode]:
    """Build all episodes from scenarios deterministically."""
    cases = load_scenarios(scenarios_path)
    builder = EpisodeBuilder.for_reviewed_scenarios(seed=seed)
    episodes = builder.build_all(cases)
    # Validate every episode.
    for episode in episodes:
        validate_episode(episode.as_dict())
    return episodes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic semantic episodes from reviewed scenarios."
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=ROOT / "data" / "scenarios" / "use_cases.jsonl",
        help="Input scenarios JSONL file path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "episodes" / "all.jsonl",
        help="Output episodes JSONL file path.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1701,
        help="Deterministic seed for episode generation (default: 1701).",
    )
    args = parser.parse_args()

    episodes = build_all_episodes(args.scenarios, seed=args.seed)
    write_episodes(episodes, args.output)

    resolved = sum(1 for e in episodes if e.gap_receipt is None)
    gapped = len(episodes) - resolved
    print(
        f"Generated {len(episodes)} episodes "
        f"({resolved} resolved, {gapped} with gaps) "
        f"-> {args.output}"
    )


if __name__ == "__main__":
    main()
