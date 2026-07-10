"""Diagnostic probe — runs deep stress scenarios with full output logging.

This is not a pass/fail test. It runs each scenario and logs every turn's
obligation_kind, has_answer, durable_count, output, and errors so we can
spot silent bugs: wrong obligation routing, empty outputs on teaching,
safety not triggering, durable store not growing, etc.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("CEMM_EXPORT_PATH", "")

from cemm.tests.harness import SeededSystem, seed_durable_from_config


def run_diagnostic(label: str, turns: list[tuple[str, dict]], seed: bool = True) -> list[dict]:
    sys = SeededSystem(context_id=f"diag_{label}")
    if seed:
        seed_durable_from_config(sys)

    prev_durable = sys.durable_store.relation_count()
    results = []

    for i, (text, checks) in enumerate(turns):
        r = sys.run(text)
        entry = {
            "turn": i,
            "input": text[:80],
            "obligation": r["obligation_kind"],
            "has_answer": r["has_answer"],
            "abstention": r["abstention_reason"],
            "durable": r["durable_count"],
            "durable_delta": r["durable_count"] - prev_durable,
            "patches": r["patch_candidates"],
            "committed": r["patch_committed"],
            "output_len": len(r["output"]),
            "output": r["output"][:120],
            "errors": r["errors"],
            "relation_key": r["relation_key"],
            "slot_fills": r["slot_fills"][:3],
        }
        results.append(entry)
        prev_durable = r["durable_count"]

    return results


def print_diagnostic(label: str, results: list[dict]) -> None:
    print(f"\n{'='*120}")
    print(f"SCENARIO: {label} ({len(results)} turns)")
    print(f"{'='*120}")
    print(f"{'T':>3} {'Obligation':<35} {'Ans':<5} {'Durable':>8} {'dDur':>4} {'Patches':>7} {'Committed':>9} {'OutLen':>6} {'RelKey':<25} {'Input'}")
    print(f"{'-'*120}")
    for r in results:
        print(
            f"{r['turn']:>3} {r['obligation']:<35} {str(r['has_answer']):<5} "
            f"{r['durable']:>8} {r['durable_delta']:>+4} {r['patches']:>7} {r['committed']:>9} "
            f"{r['output_len']:>6} {str(r['relation_key']):<25} {r['input']}"
        )
        if r["errors"]:
            print(f"    ERRORS: {r['errors']}")
        if r["abstention"]:
            print(f"    ABSTENTION: {r['abstention']}")


def analyze_anomalies(label: str, results: list[dict]) -> list[str]:
    """Flag potential bugs or surprising behavior."""
    anomalies = []

    for r in results:
        turn = r["turn"]
        inp = r["input"]
        obl = r["obligation"]
        out_len = r["output_len"]

        # Teaching that didn't grow durable store
        if "remember" in inp.lower() and r["durable_delta"] == 0 and r["patches"] == 0:
            anomalies.append(f"  T{turn} ({inp!r}): teaching input but no patch candidate AND no durable growth")

        # Teaching that produced patches but none committed
        if r["patches"] > 0 and r["committed"] == 0:
            anomalies.append(f"  T{turn} ({inp!r}): {r['patches']} patch candidates but 0 committed")

        # Safety input that didn't produce safety obligation
        if any(w in inp.lower() for w in ["hit", "hurt", "kill", "hack", "steal", "beat", "stab", "shoot"]):
            if "safety" not in str(obl) and obl not in ("abstain_policy", "ask_clarification"):
                if obl and obl != "acknowledge_emotional_context":
                    anomalies.append(f"  T{turn} ({inp!r}): harm-related input but obligation={obl!r} (expected safety/abstain/clarification)")

        # Self-query that didn't answer
        if r["has_answer"] is False and any(w in inp.lower() for w in ["your name", "who are you", "what can you do", "what do you know"]):
            anomalies.append(f"  T{turn} ({inp!r}): self-query but has_answer=False, abstention={r['abstention']!r}")

        # Empty output on non-empty input
        if out_len == 0 and inp.strip() and not r["errors"]:
            anomalies.append(f"  T{turn} ({inp!r}): empty output on non-empty input, obligation={obl!r}")

        # Durable count decreased
        if r["durable_delta"] < -1:
            anomalies.append(f"  T{turn} ({inp!r}): durable count dropped by {r['durable_delta']}")

        # Exit obligation but not a dismissal phrase
        if obl == "exit" and not any(w in inp.lower() for w in ["bye", "go away", "shut up", "stop", "goodbye", "leave"]):
            anomalies.append(f"  T{turn} ({inp!r}): exit obligation but no dismissal phrase detected")

        # Social reply on what should be a query
        if obl == "social_reply" and "?" in inp and "your name" in inp.lower():
            anomalies.append(f"  T{turn} ({inp!r}): social_reply on a self-query input")

        # Acknowledge_emotional_context on non-emotional input
        if obl == "acknowledge_emotional_context":
            if not any(w in inp.lower() for w in ["too ", "verbose", "long", "robotic", "wordy", "feeling", "down", "rough", "sad", "happy", "great", "appreciate"]):
                anomalies.append(f"  T{turn} ({inp!r}): acknowledge_emotional_context but no emotional/style cue in input")

    return anomalies


# Import scenario data from the deep stress test
from cemm.tests.test_deep_stress import (
    TEENAGER_BREAKER,
    MULTI_LEARNING,
    DEEP_SOCIAL,
    DEDUCTION_EXPLORER,
    COMEDY_BANTER,
)

ALL_SCENARIOS = [
    ("teenager_breaker", TEENAGER_BREAKER),
    ("multi_learning_researcher", MULTI_LEARNING),
    ("deep_social_companion", DEEP_SOCIAL),
    ("deduction_explorer", DEDUCTION_EXPLORER),
    ("comedy_banter", COMEDY_BANTER),
]


def test_diagnostic_run():
    """Run all scenarios and print diagnostics. This test always passes — it's for inspection."""
    all_anomalies = []

    for label, turns in ALL_SCENARIOS:
        results = run_diagnostic(label, turns)
        print_diagnostic(label, results)
        anomalies = analyze_anomalies(label, results)
        if anomalies:
            print(f"\n  [!] ANOMALIES in {label}:")
            for a in anomalies:
                print(a)
            all_anomalies.extend([(label, a) for a in anomalies])
        else:
            print(f"\n  [OK] No anomalies detected in {label}")

    print(f"\n{'='*120}")
    print(f"TOTAL ANOMALIES: {len(all_anomalies)}")
    for label, a in all_anomalies:
        print(f"  [{label}] {a}")
    print(f"{'='*120}")

    # This test always passes — it's diagnostic only
    assert True
