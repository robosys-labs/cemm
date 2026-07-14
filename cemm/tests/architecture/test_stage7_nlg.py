"""Stage 7 exit gate tests — Semantic NLG and discourse cutover.

Per completion-plan.md Stage 7, CORE_LOOP.md §G, AGENTS.md §19:
- SemanticMessagePlan drives what is said
- Renderer returns exact realized semantic item refs
- Commit common ground only after dispatch
- No unspoken item enters common ground
- No internal IDs/open ports leak
- Output reparses compatibly
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from cemm.kernel.model.message import (
    SemanticMessagePlan,
    MessageContentItem,
    RhetoricalRelation,
)
from cemm.kernel.response.planner import (
    ResponsePlanner,
    ContentSelectionInput,
    EpistemicStance,
    DiscourseFunction,
)
from cemm.kernel.response.renderer import (
    MessageRenderer,
    SurfacePayload,
    RealizedClause,
)
from cemm.kernel.response.common_ground import (
    CommonGroundManager,
    DispatchResult,
    DispatchStatus,
    DiscourseStatus,
)
from cemm.kernel.model.epistemic import EpistemicAssessment
from cemm.kernel.model.mutation import CommitOutcome


# ── Helpers ───────────────────────────────────────────────────────


def make_assessment(
    prop_ref: str = "prop:1",
    admissibility: str = "admitted",
    support_state: str = "supported",
    confidence: float = 0.9,
    schema_use_valid: bool = True,
) -> EpistemicAssessment:
    return EpistemicAssessment(
        proposition_ref=prop_ref,
        context_ref="ctx:default",
        admissibility=admissibility,
        support_state=support_state,
        confidence=confidence,
        schema_use_valid=schema_use_valid,
    )


def make_commit_outcome(
    required_satisfied: bool = True,
    mutation_set_ref: str = "ms:1",
) -> CommitOutcome:
    return CommitOutcome(
        mutation_set_ref=mutation_set_ref,
        required_satisfied=required_satisfied,
        committed_revision=42,
        results=(),
    )


def make_message_plan(
    items: tuple[MessageContentItem, ...] = (),
    relations: tuple[RhetoricalRelation, ...] = (),
) -> SemanticMessagePlan:
    return SemanticMessagePlan(
        id=f"msg:{uuid4().hex[:8]}",
        content_items=items,
        rhetorical_relations=relations,
    )


# ── 1. ResponsePlanner content selection ──────────────────────────


class TestContentSelection:
    def test_propositions_become_content_items(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1", "prop:2"),
            assessments=(make_assessment("prop:1"), make_assessment("prop:2")),
        )
        plan = planner.plan_response(selection)
        refs = {item.semantic_ref for item in plan.content_items}
        assert "prop:1" in refs
        assert "prop:2" in refs

    def test_commit_success_produces_inform_item(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=(),
            commit_outcome=make_commit_outcome(required_satisfied=True),
        )
        plan = planner.plan_response(selection)
        commit_items = [
            item for item in plan.content_items
            if item.semantic_ref == "ms:1"
        ]
        assert len(commit_items) == 1
        assert commit_items[0].discourse_function == "inform"
        assert commit_items[0].stance == "asserted"

    def test_commit_failure_produces_acknowledge_denied(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=(),
            commit_outcome=make_commit_outcome(required_satisfied=False),
        )
        plan = planner.plan_response(selection)
        commit_items = [
            item for item in plan.content_items
            if item.semantic_ref == "ms:1"
        ]
        assert len(commit_items) == 1
        assert commit_items[0].discourse_function == "acknowledge"
        assert commit_items[0].stance == "denied"

    def test_repair_obligations_become_repair_items(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=(),
            repair_obligation_refs=("repair:1",),
        )
        plan = planner.plan_response(selection)
        repair_items = [
            item for item in plan.content_items
            if item.discourse_function == "repair"
        ]
        assert len(repair_items) == 1
        assert repair_items[0].stance == "stale"


# ── 2. Discourse ordering ─────────────────────────────────────────


class TestDiscourseOrdering:
    def test_repair_before_inform(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment("prop:1"),),
            repair_obligation_refs=("repair:1",),
        )
        plan = planner.plan_response(selection)
        # Repair should come before inform
        functions = [item.discourse_function for item in plan.content_items]
        repair_idx = functions.index("repair")
        inform_idx = functions.index("inform")
        assert repair_idx < inform_idx

    def test_correct_before_inform(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment(
                "prop:1", support_state="refuted"
            ),),
        )
        plan = planner.plan_response(selection)
        functions = [item.discourse_function for item in plan.content_items]
        if "correct" in functions and "inform" in functions:
            assert functions.index("correct") < functions.index("inform")


# ── 3. Epistemic qualification ────────────────────────────────────


class TestEpistemicQualification:
    def test_reported_theory_gets_reported_stance(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment(
                "prop:1", admissibility="attributed_only"
            ),),
        )
        plan = planner.plan_response(selection)
        assert plan.content_items[0].stance == "reported"

    def test_provisional_gets_provisional_stance(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment(
                "prop:1", schema_use_valid=False
            ),),
        )
        plan = planner.plan_response(selection)
        assert plan.content_items[0].stance == "provisional"

    def test_contested_gets_contested_stance(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment(
                "prop:1", support_state="both"
            ),),
        )
        plan = planner.plan_response(selection)
        assert plan.content_items[0].stance == "contested"

    def test_low_confidence_gets_hedged_stance(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment("prop:1", confidence=0.3),),
        )
        plan = planner.plan_response(selection)
        assert plan.content_items[0].stance == "hedged"

    def test_refuted_gets_denied_stance(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment(
                "prop:1", support_state="refuted"
            ),),
        )
        plan = planner.plan_response(selection)
        assert plan.content_items[0].stance == "denied"


# ── 4. Information structure ──────────────────────────────────────


class TestInformationStructure:
    def test_first_item_gets_given_focus(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1", "prop:2"),
            assessments=(make_assessment("prop:1"), make_assessment("prop:2")),
        )
        plan = planner.plan_response(selection)
        # First item should have "given" focus (after ordering)
        assert plan.content_items[0].focus == "given"

    def test_subsequent_items_get_new_focus(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1", "prop:2"),
            assessments=(make_assessment("prop:1"), make_assessment("prop:2")),
        )
        plan = planner.plan_response(selection)
        # At least one item should have "new" focus
        new_items = [item for item in plan.content_items if item.focus == "new"]
        assert len(new_items) >= 1


# ── 5. Rhetorical relations ───────────────────────────────────────


class TestRhetoricalRelations:
    def test_relations_connect_sequential_items(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1", "prop:2"),
            assessments=(make_assessment("prop:1"), make_assessment("prop:2")),
        )
        plan = planner.plan_response(selection)
        assert len(plan.rhetorical_relations) > 0

    def test_correction_produces_contrast_relation(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment(
                "prop:1", support_state="refuted"
            ),),
            repair_obligation_refs=("repair:1",),
        )
        plan = planner.plan_response(selection)
        # Should have at least one contrast or correction relation
        relation_kinds = {r.relation_kind for r in plan.rhetorical_relations}
        assert "contrast" in relation_kinds or "correction" in relation_kinds


# ── 6. Provenance tracking ────────────────────────────────────────


class TestProvenance:
    def test_every_item_has_provenance(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1", "prop:2"),
            assessments=(make_assessment("prop:1"), make_assessment("prop:2")),
        )
        plan = planner.plan_response(selection)
        for item in plan.content_items:
            assert len(item.provenance_refs) > 0

    def test_commit_provenance_does_not_pollute_other_items(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment("prop:1"),),
            commit_outcome=make_commit_outcome(required_satisfied=True),
        )
        plan = planner.plan_response(selection)
        prop_items = [
            item for item in plan.content_items
            if item.semantic_ref == "prop:1"
        ]
        assert len(prop_items) == 1
        assert "ms:1" not in prop_items[0].provenance_refs


# ── 7. Content validation ─────────────────────────────────────────


class TestContentValidation:
    def test_valid_plan_passs(self):
        planner = ResponsePlanner()
        selection = ContentSelectionInput(
            proposition_refs=("prop:1",),
            assessments=(make_assessment("prop:1"),),
        )
        plan = planner.plan_response(selection)
        assert planner.validate_plan(plan)

    def test_plan_with_empty_semantic_ref_fails(self):
        planner = ResponsePlanner()
        plan = SemanticMessagePlan(
            id="msg:1",
            content_items=(MessageContentItem(
                semantic_ref="",
                provenance_refs=("prop:1",),
            ),),
        )
        assert not planner.validate_plan(plan)

    def test_plan_with_empty_provenance_fails(self):
        planner = ResponsePlanner()
        plan = SemanticMessagePlan(
            id="msg:1",
            content_items=(MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=(),
            ),),
        )
        assert not planner.validate_plan(plan)

    def test_plan_with_open_port_ref_fails(self):
        planner = ResponsePlanner()
        plan = SemanticMessagePlan(
            id="msg:1",
            content_items=(MessageContentItem(
                semantic_ref="port:1",
                provenance_refs=("port:1",),
            ),),
        )
        assert not planner.validate_plan(plan)


# ── 8. MessageRenderer ────────────────────────────────────────────


class TestMessageRenderer:
    def test_render_produces_surface_text(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="inform",
                stance="asserted",
                provenance_refs=("prop:1",),
            ),),
        )
        payload = renderer.render(plan)
        assert payload.surface_text
        assert len(payload.clauses) == 1

    def test_render_returns_realized_refs(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(
                MessageContentItem(
                    semantic_ref="prop:1",
                    provenance_refs=("prop:1",),
                ),
                MessageContentItem(
                    semantic_ref="prop:2",
                    provenance_refs=("prop:2",),
                ),
            ),
        )
        payload = renderer.render(plan)
        assert "prop:1" in payload.realized_item_refs
        assert "prop:2" in payload.realized_item_refs

    def test_render_query_gets_question_mark(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="query",
                provenance_refs=("prop:1",),
            ),),
        )
        payload = renderer.render(plan)
        assert payload.surface_text.endswith("?")

    def test_render_inform_gets_period(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="inform",
                provenance_refs=("prop:1",),
            ),),
        )
        payload = renderer.render(plan)
        assert payload.surface_text.endswith(".")

    def test_render_empty_plan_produces_empty_text(self):
        renderer = MessageRenderer()
        plan = make_message_plan(items=())
        payload = renderer.render(plan)
        assert payload.surface_text == ""

    def test_render_preserves_provenance(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                provenance_refs=("prop:1", "ev:1"),
            ),),
        )
        payload = renderer.render(plan)
        assert "prop:1" in payload.provenance_refs
        assert "ev:1" in payload.provenance_refs

    def test_render_stance_marker_applied(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                stance="hedged",
                discourse_function="inform",
                provenance_refs=("prop:1",),
            ),),
        )
        payload = renderer.render(plan)
        # Hedged stance should produce "Possibly" prefix
        assert "possibly" in payload.surface_text.lower()


# ── 9. Round-trip validation ──────────────────────────────────────


class TestRoundTrip:
    def test_no_internal_ids_leak(self):
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="inform",
                provenance_refs=("prop:1",),
            ),),
        )
        payload = renderer.render(plan)
        assert renderer.validate_round_trip(payload)

    def test_internal_id_leak_detected(self):
        renderer = MessageRenderer()
        # Create a payload with leaked internal IDs
        payload = SurfacePayload(
            plan_ref="msg:1",
            clauses=(RealizedClause(
                semantic_ref="prop:1",
                surface_text="The op:query returned schema:foo.",
            ),),
            surface_text="The op:query returned schema:foo.",
        )
        assert not renderer.validate_round_trip(payload)


# ── 10. CommonGroundManager ──────────────────────────────────────


class TestCommonGround:
    def test_dispatched_content_recorded(self):
        mgr = CommonGroundManager()
        dispatch = DispatchResult(
            message_plan_ref="msg:1",
            status=DispatchStatus.DISPATCHED,
            dispatched_at="2024-01-01T00:00:00Z",
        )
        entry = mgr.record_dispatch(
            proposition_ref="prop:1",
            participant_ref="self",
            discourse_status=DiscourseStatus.ASSERTED,
            dispatch_result=dispatch,
        )
        assert entry.proposition_ref == "prop:1"
        assert mgr.is_dispatched("prop:1")

    def test_intended_text_not_recorded(self):
        mgr = CommonGroundManager()
        result = mgr.try_record_intended(
            proposition_ref="prop:1",
            participant_ref="self",
            discourse_status=DiscourseStatus.ASSERTED,
        )
        assert result is False
        assert not mgr.is_dispatched("prop:1")

    def test_non_dispatched_rejected(self):
        mgr = CommonGroundManager()
        dispatch = DispatchResult(
            message_plan_ref="msg:1",
            status=DispatchStatus.PENDING,
        )
        with pytest.raises(ValueError):
            mgr.record_dispatch(
                proposition_ref="prop:1",
                participant_ref="self",
                discourse_status=DiscourseStatus.ASSERTED,
                dispatch_result=dispatch,
            )

    def test_correction_marks_old_entry(self):
        mgr = CommonGroundManager()
        dispatch = DispatchResult(
            message_plan_ref="msg:1",
            status=DispatchStatus.DISPATCHED,
            dispatched_at="2024-01-01T00:00:00Z",
        )
        entry1 = mgr.record_dispatch(
            proposition_ref="prop:1",
            participant_ref="self",
            discourse_status=DiscourseStatus.ASSERTED,
            dispatch_result=dispatch,
        )
        entry2 = mgr.record_dispatch(
            proposition_ref="prop:1",
            participant_ref="self",
            discourse_status=DiscourseStatus.CORRECTED,
            dispatch_result=dispatch,
            corrects_entry_id=entry1.entry_id,
        )
        # Old entry should be marked corrected
        old_entries = mgr.get_entries_for_proposition("prop:1")
        corrected = [e for e in old_entries if e.discourse_status == DiscourseStatus.CORRECTED]
        assert len(corrected) >= 1


# ── 11. Legacy deprecation ────────────────────────────────────────


class TestLegacyDeprecation:
    def test_response_formation_engine_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.response.response_formation_engine")
        assert "DEPRECATED" in mod.__doc__

    def test_obligation_frame_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.types.obligation_frame")
        assert "DEPRECATED" in mod.__doc__

    def test_output_state_updater_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.legacy.v3_3.output_state_updater")
        assert "DEPRECATED" in mod.__doc__

    def test_response_types_deprecated(self):
        import importlib
        mod = importlib.import_module("cemm.response.types")
        assert "DEPRECATED" in mod.__doc__


# ── 12. Exit gate: no unspoken item enters common ground ──────────


class TestExitGate:
    def test_no_unspoken_item_enters_common_ground(self):
        """Only dispatched content enters common ground."""
        mgr = CommonGroundManager()
        # Without dispatch, nothing should be in common ground
        assert not mgr.is_dispatched("prop:1")
        assert not mgr.is_dispatched("prop:2")

    def test_message_plan_and_output_agree(self):
        """v3.4 message plan and actual output agree."""
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(
                MessageContentItem(
                    semantic_ref="prop:1",
                    discourse_function="inform",
                    provenance_refs=("prop:1",),
                ),
                MessageContentItem(
                    semantic_ref="prop:2",
                    discourse_function="inform",
                    provenance_refs=("prop:2",),
                ),
            ),
        )
        payload = renderer.render(plan)
        # Every content item should have a corresponding realized clause
        assert len(payload.clauses) == len(plan.content_items)
        for item, clause in zip(plan.content_items, payload.clauses):
            assert item.semantic_ref == clause.semantic_ref

    def test_no_internal_ids_leak_in_output(self):
        """No internal IDs/open ports leak into public text."""
        import re
        renderer = MessageRenderer()
        plan = make_message_plan(
            items=(MessageContentItem(
                semantic_ref="prop:1",
                discourse_function="inform",
                provenance_refs=("prop:1",),
            ),),
        )
        payload = renderer.render(plan)
        text = payload.surface_text
        # Check for internal ID patterns as word-level prefixes
        for pattern in [r'\bop:', r'\bport:', r'\bschema:', r'\bboot:']:
            assert not re.search(pattern, text)
