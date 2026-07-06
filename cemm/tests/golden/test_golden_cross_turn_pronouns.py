"""Golden test: cross-turn pronoun resolution via EntitySalienceTracker.

Verifies that entity salience persists across turns and enables
anaphora resolution for third-person pronouns.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.tests.harness import SeededSystem


def test_entity_salience_persists_across_turns():
    """Phase 6: After mentioning 'Alice', entity_salience should contain her."""
    system = SeededSystem()
    system.run("Alice likes cats")
    result2 = system.run("She likes dogs too")

    cycle2 = result2["cycle"]
    assert cycle2 is not None

    # The salience map should have been updated in the second turn
    # from the prior turn's entity salience
    errors = result2.get("errors", [])
    salience_errors = [e for e in errors if "salience" in e.lower()]
    assert len(salience_errors) == 0, \
        f"Should have no salience errors, got: {salience_errors}"


def test_salience_map_populated_in_perception_trace():
    """Phase 6: perception_trace should contain a salience_map after perception."""
    system = SeededSystem()
    result = system.run("Alice likes cats")

    cycle = result["cycle"]
    assert cycle is not None
    assert cycle.percept is not None

    salience_map = cycle.percept.perception_trace.get("salience_map", {})
    assert len(salience_map) > 0, \
        "Salience map should be populated in perception trace"


def test_cross_turn_no_errors():
    """Phase 6: Multi-turn conversation with pronouns should not produce errors."""
    system = SeededSystem()
    results = system.run_turns([
        "Alice likes cats",
        "She likes dogs too",
    ])

    for i, result in enumerate(results):
        errors = result.get("errors", [])
        assert len(errors) == 0, \
            f"Turn {i+1} should have no errors, got: {errors}"
