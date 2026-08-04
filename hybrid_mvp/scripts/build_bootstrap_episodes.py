#!/usr/bin/env python
"""Generate deterministic bootstrap proposal episodes as JSONL.

For each seed surface (word-order, synonym, modality, reference, scope,
teaching, query, typed-gap), this script:

1. Resolves the form lattice.
2. Builds an orientation via the OrientationProjector.
3. Runs the BootstrapProposer.
4. Records: form lattice, orientation projection, action sequence, rejected
   legal alternatives, coverage receipt, authority/action hashes.

Two runs produce byte-identical output (deterministic).

Usage::

    python scripts/build_bootstrap_episodes.py --output data/bootstrap/proposal_episodes.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

# Ensure the src directory is on the path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.contributions import ContributionExpander
from cemm_authoritative_hybrid.cycle import OrientationProjector, SemanticMode
from cemm_authoritative_hybrid.forms import FormResolver
from cemm_authoritative_hybrid.grounding import Grounder
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.verifier import ExactProgramVerifier, LegalActionIndex
from cemm_authoritative_hybrid.coverage import CoverageVerifier


# ---------------------------------------------------------------------------
# Seed surfaces
# ---------------------------------------------------------------------------

SEEDS: list[tuple[str, str, SemanticMode]] = [
    # (seed_category, surface, mode)
    ("word-order", "what is your name?", SemanticMode.QUERY),
    ("word-order", "your name is what?", SemanticMode.QUERY),
    ("synonym", "what are you called?", SemanticMode.QUERY),
    ("synonym", "and you are called what?", SemanticMode.QUERY),
    ("modality", "can I call you CEMM?", SemanticMode.REQUEST),
    ("modality", "I can call you CEMM, right?", SemanticMode.REQUEST),
    ("reference", "you said what?", SemanticMode.QUERY),
    ("scope", "not online", SemanticMode.OBSERVE),
    ("teaching", "yoz means hello", SemanticMode.REQUEST),
    ("query", "is the server online?", SemanticMode.QUERY),
    ("typed-gap", "zorbulate", SemanticMode.OBSERVE),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_lattice(lattice: Any) -> dict[str, Any]:
    """Serialize a FormLattice to a JSON-compatible dict."""
    return {
        "source_text": lattice.source_text,
        "units": [
            {
                "unit_ref": u.unit_ref,
                "source_text": u.source_text,
                "normalized_forms": list(u.normalized_forms),
                "source_start": u.source_start,
                "source_end": u.source_end,
                "features": [list(f) for f in u.features],
            }
            for u in lattice.units
        ],
        "hypotheses": [
            {
                "hypothesis_ref": h.hypothesis_ref,
                "unit_refs": list(h.unit_refs),
                "construction": h.construction,
                "features": [list(f) for f in h.features],
            }
            for h in lattice.hypotheses
        ],
    }


def _serialize_orientation(orientation: Any) -> dict[str, Any]:
    """Serialize an Orientation to a JSON-compatible dict."""
    return {
        "session_ref": orientation.session_ref,
        "turn_ref": orientation.turn_ref,
        "mode": orientation.mode.value,
        "participant_frame": orientation.participant_frame,
        "temporal_frame": orientation.temporal_frame,
        "authority_generation": orientation.authority_generation,
        "world_revision": orientation.world_revision,
        "session_revision": orientation.session_revision,
        "episode_revision": orientation.episode_revision,
        "effect_revision": orientation.effect_revision,
        "model_identity": orientation.model_identity,
        "focus_refs": list(orientation.focus_refs),
        "obligation_refs": list(orientation.obligation_refs),
        "capability_summary": list(orientation.capability_summary),
        "permission_summary": list(orientation.permission_summary),
        "participants": list(orientation.participants),
        "active_turn_ref": orientation.active_turn_ref,
        "event_refs": list(orientation.event_refs),
        "scanned_atom_count": orientation.scanned_atom_count,
        "index_probes": list(orientation.index_probes),
        "visited_refs": list(orientation.visited_refs),
        "cache_key": orientation.cache_key,
    }


def _serialize_coverage_receipt(receipt: Any) -> dict[str, Any] | None:
    """Serialize a CoverageReceipt to a JSON-compatible dict."""
    if receipt is None:
        return None
    return {
        "program_ref": receipt.program_ref,
        "assigned_unit_refs": list(receipt.assigned_unit_refs),
        "residual_unit_refs": list(receipt.residual_unit_refs),
        "duplicate_unit_refs": list(receipt.duplicate_unit_refs),
        "missing_unit_refs": list(receipt.missing_unit_refs),
        "critical_residuals": [
            {
                "source_unit_ref": cr.source_unit_ref,
                "contribution_kind": cr.contribution_kind,
                "reason": cr.reason,
            }
            for cr in receipt.critical_residuals
        ],
        "executable": receipt.executable,
        "coverage_hash": receipt.coverage_hash,
        "errors": [
            {"code": e.code, "detail": e.detail} for e in receipt.errors
        ],
    }


def _serialize_action_sequence(actions: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Serialize an action sequence to a JSON-compatible list."""
    return [
        {
            "action_ref": a.action_ref,
            "action_type": a.action_type,
            "arguments": list(a.arguments),
            "source_unit_refs": list(a.source_unit_refs),
        }
        for a in actions
    ]


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------


def build_components():
    """Build all components needed for episode generation."""
    config = RuntimeConfig.release()
    authority = AuthorityLinker().link_path(
        ROOT / "data" / "authority" / "manifest.json"
    )

    with open(ROOT / "data" / "languages" / "en" / "forms.json", encoding="utf-8") as fh:
        form_pack = json.load(fh)

    form_resolver = FormResolver(form_pack, config)
    affordance_index = SemanticAffordanceIndex(authority, config)
    contribution_expander = ContributionExpander(affordance_index, config)
    coverage_verifier = CoverageVerifier(config)
    verifier = ExactProgramVerifier(authority, config, coverage_verifier)
    legal_action_index = LegalActionIndex(authority, config)

    stores = memory_stores(authority_generation=authority.generation)
    projector = OrientationProjector(authority, stores, config)

    grounder = Grounder(
        authority=authority,
        config=config,
        form_pack=form_pack,
        form_pack_hash="",
        designation_store=None,
    )

    proposer = BootstrapProposer(
        authority=authority,
        config=config,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        contribution_expander=contribution_expander,
        verifier=verifier,
        coverage_verifier=coverage_verifier,
        legal_action_index=legal_action_index,
    )

    return authority, config, form_resolver, projector, verifier, proposer


def generate_episode(
    seed_category: str,
    surface: str,
    mode: SemanticMode,
    authority: Any,
    form_resolver: FormResolver,
    projector: OrientationProjector,
    verifier: ExactProgramVerifier,
    proposer: BootstrapProposer,
) -> dict[str, Any]:
    """Generate a single episode dict for a seed surface."""
    # Resolve form lattice.
    lattice = form_resolver.resolve(surface)

    # Build orientation.
    orientation = projector.project("session:bootstrap", surface, mode=mode)
    orientation = replace(orientation, source_text=surface)

    # Run proposer with detailed results.
    result, rejected = proposer.propose_detailed(orientation)

    # Pick the first accepted candidate (or None if no accepted).
    accepted_program = None
    if result.candidates:
        accepted_program = result.candidates[0]

    # Build the episode record.
    action_sequence: list[dict[str, Any]] = []
    program_ref = ""
    action_encoding_hash = ""
    coverage_receipt: dict[str, Any] | None = None
    accepted = False

    if accepted_program is not None:
        action_sequence = _serialize_action_sequence(accepted_program.actions)
        program_ref = accepted_program.program_ref
        action_encoding_hash = accepted_program.action_encoding_hash
        accepted = True

        # Get coverage receipt from verification.
        verification = verifier.verify(accepted_program)
        coverage_receipt = _serialize_coverage_receipt(
            verification.coverage_receipt
        )

    # Compute authority hash.
    authority_hash = stable_ref(
        "authority", {"generation": authority.generation}
    )

    # Serialize rejected alternatives (bounded to first 20 for compactness).
    rejected_serialized = [
        {
            "action_ids": r["action_ids"],
            "program_ref": r["program_ref"],
            "rejection_codes": r["rejection_codes"],
        }
        for r in rejected[:20]
    ]

    return {
        "surface": surface,
        "seed_category": seed_category,
        "form_lattice": _serialize_lattice(lattice),
        "orientation": _serialize_orientation(orientation),
        "action_sequence": action_sequence,
        "rejected_alternatives": rejected_serialized,
        "coverage_receipt": coverage_receipt,
        "authority_hash": authority_hash,
        "action_encoding_hash": action_encoding_hash,
        "program_ref": program_ref,
        "accepted": accepted,
    }


def generate_all_episodes() -> list[dict[str, Any]]:
    """Generate all bootstrap episodes deterministically."""
    authority, config, form_resolver, projector, verifier, proposer = (
        build_components()
    )

    episodes: list[dict[str, Any]] = []
    for seed_category, surface, mode in SEEDS:
        episode = generate_episode(
            seed_category,
            surface,
            mode,
            authority,
            form_resolver,
            projector,
            verifier,
            proposer,
        )
        episodes.append(episode)

    return episodes


def write_episodes(episodes: list[dict[str, Any]], output_path: Path) -> None:
    """Write episodes as JSONL (one JSON object per line)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(episode, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for episode in episodes
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic bootstrap proposal episodes as JSONL."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "bootstrap" / "proposal_episodes.jsonl",
        help="Output JSONL file path.",
    )
    args = parser.parse_args()

    episodes = generate_all_episodes()
    write_episodes(episodes, args.output)

    accepted_count = sum(1 for e in episodes if e["accepted"])
    print(
        f"Generated {len(episodes)} episodes "
        f"({accepted_count} accepted, {len(episodes) - accepted_count} not accepted) "
        f"-> {args.output}"
    )


if __name__ == "__main__":
    main()
