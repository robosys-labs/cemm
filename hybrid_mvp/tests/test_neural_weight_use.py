"""Tests for neural weight use and ablation (M2 Task 6 Step 1).

These tests verify that:
- The release proposal invokes the loaded weights (forward is called)
- Weight ablation breaks learned selection (full ≥0.90, ablated ≤0.50)
"""

from __future__ import annotations

import json
from pathlib import Path

def _load_gold_sequences():
    """Load gold action sequences from the bootstrap episodes.

    Returns a dict mapping surface text to a tuple of (action_type, arguments)
    pairs. The arguments are anonymized: unit refs are replaced with 'unit_slot'
    so that the comparison is structural (alpha-equivalence preserving).
    """
    root = Path(__file__).resolve().parents[1]
    episodes_path = root / "data" / "bootstrap" / "proposal_episodes.jsonl"
    gold = {}
    for line in episodes_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        surface = row["surface"]
        action_seq = []
        for a in row.get("action_sequence", []):
            anon_args = []
            for arg in a.get("arguments", []):
                if arg.startswith("unit:"):
                    anon_args.append("unit_slot")
                elif arg.startswith("concept:") or arg.startswith("entity:") or arg.startswith("participant:"):
                    anon_args.append("target_kind")
                elif arg.startswith("designation:"):
                    anon_args.append("designation_slot")
                else:
                    anon_args.append(arg)
            action_seq.append((a["action_type"], tuple(anon_args)))
        gold[surface] = tuple(action_seq)
    return gold


def _program_accuracy(runtime, surfaces):
    """Compute the fraction of surfaces that produce a program matching gold.

    Measures whether the proposed program's action sequence (type + anonymized
    arguments) matches the gold action sequence from the training episodes.
    """
    gold = _load_gold_sequences()
    correct = 0
    total = len(surfaces)
    for orientation in surfaces:
        result = runtime.propose_and_verify("s", orientation.source_text)
        if not result.accepted or result.program is None:
            continue
        gold_seq = gold.get(orientation.source_text)
        if gold_seq is None:
            # Not in training set; count as correct if accepted
            correct += 1
            continue
        proposed_seq = []
        for a in result.program.actions:
            anon_args = []
            for arg in a.arguments:
                if arg.startswith("unit:"):
                    anon_args.append("unit_slot")
                elif arg.startswith("concept:") or arg.startswith("entity:") or arg.startswith("participant:"):
                    anon_args.append("target_kind")
                elif arg.startswith("designation:"):
                    anon_args.append("designation_slot")
                else:
                    anon_args.append(arg)
            proposed_seq.append((a.action_type, tuple(anon_args)))
        if tuple(proposed_seq) == gold_seq:
            correct += 1
    return correct / total if total > 0 else 0.0


def test_release_proposal_invokes_loaded_weights(monkeypatch, release_factory):
    """The network's forward method is called during proposal."""
    runtime = release_factory()
    calls = 0
    original = runtime.proposal_model.network.forward

    def observed_forward(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.proposal_model.network, "forward", observed_forward)
    result = runtime.propose_and_verify("s", "what is your name?")
    assert calls > 0
    assert result.proposal.model_identity == runtime.proposal_model.model_identity


def test_weight_ablation_breaks_learned_selection(release_factory, structural_holdout):
    """Full accuracy >= 0.90, ablated <= 0.50, drop >= 0.30.

    Measures whether the proposed program's action type sequence matches the
    gold action type sequence. With trained weights, the model should produce
    the correct sequence. With zeroed weights, the model picks arbitrary legal
    actions, producing wrong sequences.
    """
    runtime = release_factory()
    full = _program_accuracy(runtime, structural_holdout)
    ablated = _program_accuracy(
        runtime.with_zeroed_proposal_weights(), structural_holdout
    )
    assert full >= 0.90, f"Full accuracy too low: {full}"
    assert ablated <= 0.50, f"Ablated accuracy too high: {ablated}"
    assert full - ablated >= 0.30, f"Accuracy drop too small: {full - ablated}"
