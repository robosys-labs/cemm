from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_active_contract_is_six_phase_and_hard_cutover():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for phase in ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"):
        assert phase in text
    assert "Stage 0–22 ordering is not an activation invariant" in text
    assert "Runtime cutover: hard" in text


def test_exactly_five_persistent_operators_are_declared():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count("op:designation") == 1
    for operator in ("op:type", "op:relation", "op:state", "op:event"):
        assert operator in text
