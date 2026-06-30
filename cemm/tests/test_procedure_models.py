"""Tests for procedure/tool models and skill induction."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cemm.types.procedure_model import ProcedureModel, ToolSchemaModel, ConfirmationPolicy
from cemm.registry.registry import Registry, RegistryEntry
from cemm.models.skill_induction import SkillInductor, InductionRecord, InductionCandidate


class TestProcedureModel:
    def test_procedure_instantiation(self) -> None:
        pm = ProcedureModel(
            model_id="proc_schedule_meeting",
            registry_key="schedule_virtual_meeting",
            required_slots=["participants", "time_window", "duration", "title"],
            tool_sequence=["calendar.availability", "calendar.create_event"],
            confirmation_policy=ConfirmationPolicy.ALWAYS,
        )
        assert pm.model_id == "proc_schedule_meeting"
        assert pm.registry_key == "schedule_virtual_meeting"
        assert "participants" in pm.required_slots
        assert len(pm.tool_sequence) == 2

    def test_tool_schema_instantiation(self) -> None:
        ts = ToolSchemaModel(
            model_id="tool_calculator",
            tool_id="calculator.basic",
            input_schema='{"expression": "string"}',
            output_schema='{"result": "number"}',
            permission_required="public",
            cost_estimate_ms=10.0,
            risk=0.0,
            reliability_log_odds=3.0,
        )
        assert ts.tool_id == "calculator.basic"
        assert ts.cost_estimate_ms == 10.0

    def test_default_policy(self) -> None:
        pm = ProcedureModel(model_id="test", registry_key="test")
        assert pm.confirmation_policy == ConfirmationPolicy.RISKY_ONLY


class TestProcedureRegistry:
    def test_register_procedure(self) -> None:
        reg = Registry()
        entry = RegistryEntry(
            model_id="proc_test",
            canonical_key="test_procedure",
            kind="procedure",
            required_slots=["slot_a", "slot_b"],
        )
        reg.register(entry)
        assert reg.get_procedure("test_procedure") is not None
        assert reg.get_procedure("test_procedure").model_id == "proc_test"

    def test_register_tool(self) -> None:
        reg = Registry()
        entry = RegistryEntry(
            model_id="tool_test",
            canonical_key="calculator.basic",
            kind="tool",
        )
        reg.register(entry)
        assert reg.get_tool("calculator.basic") is not None

    def test_all_by_kind_includes_procedures(self) -> None:
        reg = Registry()
        reg.register(RegistryEntry(model_id="p1", canonical_key="proc1", kind="procedure"))
        reg.register(RegistryEntry(model_id="p2", canonical_key="proc2", kind="procedure"))
        procs = reg.all_by_kind("procedure")
        assert len(procs) == 2

    def test_all_by_kind_includes_tools(self) -> None:
        reg = Registry()
        reg.register(RegistryEntry(model_id="t1", canonical_key="tool1", kind="tool"))
        tools = reg.all_by_kind("tool")
        assert len(tools) == 1

    def test_register_invalid_kind_raises(self) -> None:
        reg = Registry()
        entry = RegistryEntry(model_id="x", canonical_key="x", kind="nonexistent")
        try:
            reg.register(entry)
            assert False, "Expected ValueError"
        except ValueError:
            pass


class TestSkillInduction:
    def test_induction_record(self) -> None:
        rec = InductionRecord(
            goal_key="schedule_meeting",
            slot_pattern=("participants", "time_window"),
            tool_sequence=("calendar.availability",),
            success=True,
            confidence=0.9,
        )
        assert rec.goal_key == "schedule_meeting"
        assert rec.success

    def test_inductor_requires_min_observations(self) -> None:
        inducer = SkillInductor(min_observations=3, min_success_rate=0.5)
        for i in range(2):
            inducer.observe(InductionRecord(
                goal_key="compute_math",
                slot_pattern=("expression",),
                tool_sequence=("calculator.basic",),
                success=True,
                confidence=0.9,
            ))
        assert len(inducer.active_candidates()) == 0
        assert len(inducer.pending_candidates()) == 1

    def test_inductor_validates_after_threshold(self) -> None:
        inducer = SkillInductor(min_observations=3, min_success_rate=0.5)
        for i in range(3):
            inducer.observe(InductionRecord(
                goal_key="compute_math",
                slot_pattern=("expression",),
                tool_sequence=("calculator.basic",),
                success=True,
                confidence=0.9,
            ))
        active = inducer.active_candidates()
        assert len(active) == 1
        assert active[0].goal_key == "compute_math"
        assert active[0].validated

    def test_inductor_respects_success_rate(self) -> None:
        inducer = SkillInductor(min_observations=4, min_success_rate=0.75)
        for i in range(4):
            success = i < 3  # 3 successes, 1 failure = 75%
            inducer.observe(InductionRecord(
                goal_key="query_db",
                slot_pattern=("query",),
                tool_sequence=("database.query",),
                success=success,
                confidence=0.8,
            ))
        active = inducer.active_candidates()
        assert len(active) == 1

    def test_inductor_rejects_low_success_rate(self) -> None:
        inducer = SkillInductor(min_observations=4, min_success_rate=0.75)
        for i in range(4):
            success = i < 2  # 2 successes, 2 failures = 50%
            inducer.observe(InductionRecord(
                goal_key="unreliable_task",
                slot_pattern=("input",),
                tool_sequence=("tool.unreliable",),
                success=success,
                confidence=0.5,
            ))
        active = inducer.active_candidates()
        assert len(active) == 0

    def test_different_patterns_separate_candidates(self) -> None:
        inducer = SkillInductor(min_observations=2)
        for i in range(2):
            inducer.observe(InductionRecord(
                goal_key="task", slot_pattern=("a",), tool_sequence=("t1",),
                success=True, confidence=0.9,
            ))
            inducer.observe(InductionRecord(
                goal_key="task", slot_pattern=("b",), tool_sequence=("t2",),
                success=True, confidence=0.9,
            ))
        # Two separate patterns -> two candidates
        assert len(inducer.active_candidates()) == 2

    def test_export_records(self) -> None:
        import tempfile
        inducer = SkillInductor()
        inducer.observe(InductionRecord(
            goal_key="test", slot_pattern=("x",), tool_sequence=("y",),
            success=True, confidence=0.9,
        ))
        with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
            tmppath = f.name
        inducer.export_records(tmppath)
        with open(tmppath) as f:
            lines = f.readlines()
        assert len(lines) == 1
        Path(tmppath).unlink()

    def test_to_candidate_procedure(self) -> None:
        inducer = SkillInductor(min_observations=1)
        for i in range(1):
            inducer.observe(InductionRecord(
                goal_key="do_stuff",
                slot_pattern=("x", "y"),
                tool_sequence=("tool.a", "tool.b"),
                success=True,
                confidence=0.9,
            ))
        active = inducer.active_candidates()
        assert len(active) == 1
        proc_dict = inducer.to_candidate_procedure(active[0], "proc_do_stuff_001")
        assert proc_dict["model_id"] == "proc_do_stuff_001"
        assert proc_dict["registry_key"] == "do_stuff"
        assert "x" in proc_dict["required_slots"]
        assert "tool.a" in proc_dict["tool_sequence"]
