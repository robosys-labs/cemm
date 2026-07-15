"""Stage 7 v3.4.1 exit gates — schema-authorized semantic NLG.

Bare semantic IDs are not realizable content. Every emitted open-class word is
licensed by an active semantic schema and every clause carries predicate,
polarity, role bindings, and provenance.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cemm.kernel.boot.v341 import register_v341_foundations
from cemm.kernel.boot.v341_validation import (
    validate_registered_v341,
    validate_v341_spec,
)
from cemm.kernel.model.epistemic import EpistemicAssessment
from cemm.kernel.model.gap import GapRecord
from cemm.kernel.model.message import (
    LexicalRequirement,
    MessageClauseSpec,
    MessageContentItem,
    MessageRoleValue,
    SemanticMessagePlan,
)
from cemm.kernel.model.mutation import CommitOutcome
from cemm.kernel.response.common_ground import (
    CommonGroundManager,
    DispatchResult,
    DispatchStatus,
    DiscourseStatus,
)
from cemm.kernel.response.lexical_use import LexicalUseGate, LexicalUseStatus
from cemm.kernel.response.planner import ContentSelectionInput, ResponsePlanner
from cemm.kernel.response.renderer import MessageRenderer
from cemm.kernel.schema.store import SemanticSchemaStore


def make_store() -> SemanticSchemaStore:
    store = SemanticSchemaStore()
    validate_v341_spec().require_ok()
    register_v341_foundations(store)
    validate_registered_v341(store).require_ok()
    return store


def make_assessment(
    prop_ref: str = "prop:1",
    *,
    admissibility: str = "admitted",
    support_state: str = "supported",
    confidence: float = 0.9,
    schema_use_valid: bool = True,
) -> EpistemicAssessment:
    return EpistemicAssessment(
        proposition_ref=prop_ref,
        context_ref="ctx:actual",
        admissibility=admissibility,
        support_state=support_state,
        confidence=confidence,
        schema_use_valid=schema_use_valid,
    )


def make_commit(required_satisfied: bool) -> CommitOutcome:
    return CommitOutcome(
        mutation_set_ref="mutation:set:1",
        required_satisfied=required_satisfied,
        committed_revision=7 if required_satisfied else None,
        results=(),
    )


def test_missing_assessment_does_not_become_asserted_content():
    plan = ResponsePlanner().plan_response(ContentSelectionInput(
        proposition_refs=("prop:unassessed",),
        assessments=(),
    ))
    assert all(item.semantic_ref != "prop:unassessed" for item in plan.content_items)
    assert any(item.content_kind == "honest_abstention" for item in plan.content_items)


def test_assessed_bare_proposition_id_is_still_not_surface_content():
    plan = ResponsePlanner().plan_response(ContentSelectionInput(
        proposition_refs=("prop:1",),
        assessments=(make_assessment(),),
    ))
    assert all(item.semantic_ref != "prop:1" for item in plan.content_items)
    assert any(item.content_kind == "honest_abstention" for item in plan.content_items)


def test_learning_probe_is_truth_bearing_and_typed():
    gap = GapRecord(
        id="gap:president",
        gap_kind="missing_semantic_family",
        target_artifact_ref="opaque:en:president",
        missing_fields=("semantic_family", "denotation_role_or_holder"),
        blocked_stage="ground",
        learnable=True,
    )
    plan = ResponsePlanner().plan_response(ContentSelectionInput(gaps=(gap,)))
    item = next(i for i in plan.content_items if i.content_kind == "learning_probe")
    clauses = {clause.predicate_key: clause for clause in item.clauses}
    assert set(clauses) == {"recognizes_form", "has_usable_definition", "means"}
    assert clauses["has_usable_definition"].polarity == "negative"
    assert clauses["means"].communicative_force == "ask"
    assert all(clause.provenance_refs for clause in clauses.values())


def test_mention_is_allowed_without_claiming_word_meaning():
    store = make_store()
    gate = LexicalUseGate(store)
    item = MessageContentItem(
        semantic_ref="mention:item",
        content_kind="mention",
        provenance_refs=("surface:president",),
        lexical_requirements=(
            LexicalRequirement(
                semantic_key="lexical_mention",
                use_mode="mention",
                surface_hint="president",
            ),
        ),
    )
    authorization = gate.authorize_item(item, language="en")
    assert authorization.authorized
    assert authorization.assessments[0].status is LexicalUseStatus.MENTION_ONLY


def test_unknown_assertive_verb_is_blocked():
    store = make_store()
    item = MessageContentItem(
        semantic_ref="claim:item",
        content_kind="semantic_claim",
        provenance_refs=("evidence:1",),
        lexical_requirements=(
            LexicalRequirement("unregistered_action", use_mode="assert"),
        ),
    )
    authorization = LexicalUseGate(store).authorize_item(item, language="en")
    assert not authorization.authorized
    assert authorization.assessments[0].status is LexicalUseStatus.BLOCKED


def test_clause_roles_must_satisfy_predicate_schema():
    store = make_store()
    incomplete_clause = MessageClauseSpec(
        clause_ref="clause:bad",
        predicate_key="means",
        communicative_force="ask",
        polarity="positive",
        role_values=(
            MessageRoleValue(
                role_key="lexical_form",
                surface_hint="president",
                value_kind="lexical_mention",
                use_mode="mention",
            ),
        ),
        lexical_requirements=(
            LexicalRequirement("means", use_mode="probe"),
            LexicalRequirement(
                "lexical_mention", use_mode="mention", surface_hint="president"
            ),
        ),
        provenance_refs=("evidence:1",),
    )
    item = MessageContentItem(
        semantic_ref="item:bad-clause",
        content_kind="learning_probe",
        clauses=(incomplete_clause,),
        provenance_refs=("evidence:1",),
    )
    authorization = LexicalUseGate(store).authorize_item(item, language="en")
    assert not authorization.authorized
    assert any("missing roles" in reason for reason in authorization.failure_reasons)


@pytest.mark.parametrize("required_satisfied,expected_kind", [
    (True, "commit_success"),
    (False, "commit_failure"),
])
def test_commit_wording_tracks_exact_commit_outcome(required_satisfied, expected_kind):
    store = make_store()
    plan = ResponsePlanner().plan_response(ContentSelectionInput(
        commit_outcome=make_commit(required_satisfied),
    ))
    item = next(i for i in plan.content_items if i.content_kind == expected_kind)
    authorization = LexicalUseGate(store).authorize_plan(plan, language="en")
    payload = MessageRenderer(store).render(
        plan, language="en", authorization=authorization
    )
    assert item.semantic_ref in payload.realized_item_refs
    if required_satisfied:
        assert "stored" in payload.surface_text.lower()
    else:
        assert "couldn't" in payload.surface_text.lower()
        assert "stored" not in payload.surface_text.lower()


def test_renderer_never_realizes_bare_internal_identifier():
    store = make_store()
    plan = SemanticMessagePlan(
        id="plan:bare-id",
        content_items=(
            MessageContentItem(
                semantic_ref="prop:1",
                content_kind="proposition",
                provenance_refs=("prop:1",),
            ),
        ),
        language="en",
    )
    payload = MessageRenderer(store).render(plan, language="en")
    assert payload.surface_text == ""
    assert payload.realized_item_refs == ()


def test_common_ground_records_only_realized_dispatched_items():
    manager = CommonGroundManager()
    dispatch = DispatchResult(
        message_plan_ref="plan:1",
        status=DispatchStatus.DISPATCHED,
        dispatched_at=datetime.now(timezone.utc).isoformat(),
    )
    manager.record_dispatch(
        proposition_ref="item:realized",
        participant_ref="self",
        discourse_status=DiscourseStatus.ASSERTED,
        dispatch_result=dispatch,
    )
    assert manager.is_dispatched("item:realized")
    assert not manager.is_dispatched("item:planned-only")


def test_round_trip_requires_equivalence_when_reparser_is_supplied():
    store = make_store()
    renderer = MessageRenderer(store)
    payload = renderer.render(
        ResponsePlanner().plan_response(ContentSelectionInput()),
        language="en",
    )
    assert not renderer.validate_round_trip(
        payload,
        reparse_fn=lambda _text: object(),
        equivalence_fn=lambda _payload, _parsed: False,
    )
