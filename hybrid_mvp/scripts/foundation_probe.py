#!/usr/bin/env python3
"""Diagnostic only: report actual public-path semantic competence, never invent gold.

A green exit code means the probe executed; it does NOT admit a cognitive
capability. Failing/unknown meaning is exposed explicitly in the output.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.foundation import load_foundation

UTTERANCES = (
    "hello",
    "What is your name?",
    "Alice owns a book.",
    "Who owns a book?",
    "Mary said Bob left.",
    "yoz means hello",
    "What does yoz mean?",
    "please turn on the lamp",
)


def probe():
    with tempfile.TemporaryDirectory(prefix="cemm-foundation-probe-") as tmp:
        runtime = load_foundation(ROOT, store_path=Path(tmp) / "probe.sqlite3")
        try:
            rows = []
            for index, utterance in enumerate(UTTERANCES):
                before = runtime.stores.revision_pin()
                try:
                    turn = runtime.process("session:foundation-probe", utterance)
                    cycle = turn.cycle
                    response = cycle.response_meaning
                    rows.append({
                        "turn": index,
                        "utterance": utterance,
                        "outcome": cycle.status.value,
                        "proposal": cycle.proposal.status,
                        "verification": cycle.verification.status,
                        "semantic_output": json.loads(turn.semantic_surface)["kind"],
                        "discourse_action": None if response is None else response.discourse_action,
                        "applications": None if response is None else len(response.response_expression.applications),
                        "decision_status": None if cycle.evaluation is None else cycle.evaluation.decision.status.value,
                        "decision_action": None if cycle.evaluation is None else cycle.evaluation.decision.action.value,
                        "blockers": [] if response is None else list(response.blocker_refs),
                        "input_graph": [] if cycle.verification.selected_meaning is None else [
                            {
                                "op": app.operator,
                                "predicate": app.predicate_ref,
                                "roles": [[role.role_ref, repr(role.filler)[:120]]
                                          for role in app.roles],
                            }
                            for app in cycle.verification.selected_meaning.expression.applications
                        ],
                        "world_revision_delta": cycle.final_revision_pin.world_revision - before.world_revision,
                        "response_verified": turn.verify(),
                    })
                except Exception as exc:
                    rows.append({
                        "turn": index, "utterance": utterance,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:256],
                    })
            return {"schema": "cemm-foundation-diagnostic-v1", "cases": rows}
        finally:
            runtime.close()


if __name__ == "__main__":
    print(json.dumps(probe(), sort_keys=True, separators=(",", ":")))
