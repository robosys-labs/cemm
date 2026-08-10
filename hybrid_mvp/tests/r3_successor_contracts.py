"""Behavioral contract helpers for R3 predecessor-lineage successors.

This module deliberately contains no pytest test nodes.  The governed successor
leaves in ``test_r3_closeout_successors.py`` bind historical assertion identities
to these live R3 contracts.  The helpers exercise typed runtime behavior and
canonical artifacts; they do not inspect source for token presence as a proxy for
behavior.
"""
from __future__ import annotations

import ast
import json
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from cemm_authoritative_hybrid.authority import AtomRecord, AuthorityLinker
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import CycleStatus, OrientationProjector
from cemm_authoritative_hybrid.dialogue import (
    DialogueObligation,
    DialogueObligationManager,
    FocusStore,
    GoalArbiter,
    ObligationKind,
    ReferenceConstraints,
    ReferenceResolver,
    VerifiedSemanticFocus,
)
from cemm_authoritative_hybrid.gaps import (
    AbsentIdentity,
    BudgetExhausted,
    CoverageGap,
    GapClassifier,
    MissingOwner,
    PermissionDenied,
    RealizationFailure,
    ReferenceAmbiguity,
    ResourceUnavailable,
    SemanticConflict,
    VerificationFailure,
)
from cemm_authoritative_hybrid.persistence import RevisionPin, memory_stores, open_stores

ROOT = Path(__file__).resolve().parents[1]


def _pin() -> RevisionPin:
    return RevisionPin("authority:test", 0, 0, 0, 0, "model:test")


def _focus(
    *,
    session: str,
    turn: str,
    participant: str,
    revision: int,
    expressions: tuple[str, ...] = (),
    entities: tuple[str, ...] = (),
    events: tuple[str, ...] = (),
) -> VerifiedSemanticFocus:
    proofs = tuple(dict.fromkeys((*expressions, *entities, *events))) or (f"proof:{turn}",)
    return VerifiedSemanticFocus.create(
        expression_refs=expressions,
        entity_refs=entities,
        event_refs=events,
        salience_proof_refs=proofs,
        participant_ref=participant,
        session_ref=session,
        turn_ref=turn,
        revision_pin=RevisionPin("authority:test", 0, revision, 0, 0, "model:test"),
    )


@lru_cache(maxsize=None)
def _focus_contract() -> bool:
    store = FocusStore()
    assert store.refs == frozenset()
    first = _focus(
        session="session:focus",
        turn="turn:1",
        participant="participant:user",
        revision=1,
        expressions=("expression:user:1",),
        entities=("entity:alice",),
    )
    second = _focus(
        session="session:focus",
        turn="turn:2",
        participant="participant:system",
        revision=2,
        expressions=("expression:system:2",),
        events=("event:greeting",),
    )
    store.add(first)
    store.add(second)
    assert store.refs == frozenset(
        {"expression:user:1", "entity:alice", "expression:system:2", "event:greeting"}
    )
    assert store.entries == (first, second)
    assert store.recent_entries(1) == (second,)
    try:
        second.expression_refs = ("expression:forged",)  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:  # pragma: no cover - frozen dataclass contract
        raise AssertionError("VerifiedSemanticFocus must remain immutable")
    try:
        VerifiedSemanticFocus(  # type: ignore[call-arg]
            expression_refs=(), entity_refs=(), event_refs=(),
            salience_proof_refs=(), participant_ref="participant:user",
            session_ref="session:x", turn_ref="turn:x", revision_pin=_pin(),
        )
    except TypeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("direct focus construction must remain closed")
    return True


def _obligation(kind: ObligationKind, *, suffix: str, expiry: int) -> DialogueObligation:
    return DialogueObligation.create(
        kind=kind,
        session_ref="session:obligation",
        source_query_ref=f"query:{suffix}",
        expected_answer_contract_ref=f"contract:{suffix}",
        created_turn_index=1,
        expires_turn_index=expiry,
        source_decision_ref=f"decision:{suffix}",
        completion_receipt_ref=None,
        revision_pin=_pin(),
    )


@lru_cache(maxsize=None)
def _obligation_contract() -> bool:
    manager = DialogueObligationManager()
    rows = {
        kind: _obligation(kind, suffix=kind.value, expiry=5 + i)
        for i, kind in enumerate(ObligationKind)
    }
    # Multiple typed non-learning obligations may coexist with exactly one
    # pending learning obligation.
    for kind, row in rows.items():
        manager.add(row)
        assert manager.get(row.obligation_ref) == row
    assert set(row.kind for row in manager.pending()) == set(ObligationKind)
    assert manager.has_learning_obligation()
    try:
        manager.add(_obligation(ObligationKind.LEARNING_ANSWER, suffix="second", expiry=20))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a second pending learning obligation was accepted")

    clarification = rows[ObligationKind.CLARIFICATION]
    completed_clarification = manager.fulfill(
        clarification.obligation_ref, "completion:clarification"
    )
    assert completed_clarification.completion_receipt_ref == "completion:clarification"
    assert manager.get(clarification.obligation_ref) == completed_clarification
    assert manager.has_learning_obligation()

    learning = rows[ObligationKind.LEARNING_ANSWER]
    completed_learning = manager.fulfill(learning.obligation_ref, "completion:learning")
    assert completed_learning.completion_receipt_ref == "completion:learning"
    assert not manager.has_learning_obligation()
    replacement = _obligation(ObligationKind.LEARNING_ANSWER, suffix="replacement", expiry=30)
    manager.add(replacement)
    assert manager.has_learning_obligation()

    pending = manager.pending()
    selected = GoalArbiter().select(("goal:background",), pending)
    assert selected.selected_obligation_ref == min(
        pending, key=lambda row: (row.expires_turn_index, row.obligation_ref)
    ).obligation_ref
    assert selected.selected_goal_ref is None
    assert selected.ui_intent_label == "obligation:fulfill"
    idle = GoalArbiter().select((), ())
    assert idle.selected_goal_ref is idle.selected_obligation_ref is None
    assert idle.ui_intent_label == "idle"
    goal = GoalArbiter().select(("goal:one",), ())
    assert goal.selected_goal_ref == "goal:one"
    assert goal.ui_intent_label == "goal:pursue"
    try:
        goal.selected_goal_ref = "goal:forged"  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:  # pragma: no cover
        raise AssertionError("GoalSelection must remain immutable")
    try:
        manager.fulfill("obligation:unknown", "completion:none")
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("unknown obligation fulfillment must fail closed")
    assert manager.get("obligation:unknown") is None

    # Store-backed completion must remove the pending ref from the canonical
    # R3 obligation snapshot in one obligation-store revision while retaining
    # both immutable records for verification/audit.
    with tempfile.TemporaryDirectory(prefix="cemm-dialogue-obligation-") as td:
        backends = (
            memory_stores(
                authority_generation="authority:test", model_identity="model:test"
            ),
            open_stores(
                Path(td) / "obligations.sqlite3",
                authority_generation="authority:test",
                model_identity="model:test",
            ),
        )
        for index, stores in enumerate(backends):
            try:
                persisted = DialogueObligationManager(stores)
                persisted_learning = _obligation(
                    ObligationKind.LEARNING_ANSWER,
                    suffix=f"persisted-{index}",
                    expiry=40,
                )
                persisted.add(persisted_learning)
                before = stores.r3_obligation_snapshot(
                    persisted_learning.session_ref, maximum=8
                )
                assert before["obligation_refs"] == [persisted_learning.obligation_ref]
                revision_before = stores.obligations.revision
                completed = persisted.fulfill(
                    persisted_learning.obligation_ref, f"completion:persisted-{index}"
                )
                assert stores.obligations.revision == revision_before + 1
                after = stores.r3_obligation_snapshot(
                    persisted_learning.session_ref, maximum=8
                )
                assert after["obligation_refs"] == []
                assert stores.obligations.get(persisted_learning.obligation_ref)["resolved"] is True
                assert stores.obligations.get(completed.obligation_ref)["resolved"] is True
            finally:
                stores.close()
    return True


class _ReferenceAuthority:
    def __init__(self) -> None:
        self.atoms = {
            "entity:alice": AtomRecord("entity:alice", "entity", metadata={"number": "singular"}),
            "entity:team": AtomRecord("entity:team", "entity", metadata={"number": "plural"}),
        }


@lru_cache(maxsize=None)
def _reference_contract() -> bool:
    store = FocusStore()
    store.add(_focus(
        session="session:reference", turn="turn:1", participant="participant:user",
        revision=1, expressions=("expression:user",), entities=("entity:alice",),
    ))
    store.add(_focus(
        session="session:reference", turn="turn:2", participant="participant:system",
        revision=2, expressions=("expression:system:old",), entities=("entity:team",),
    ))
    store.add(_focus(
        session="session:other", turn="turn:3", participant="participant:system",
        revision=3, expressions=("expression:other-session",),
    ))
    store.add(_focus(
        session="session:reference", turn="turn:4", participant="participant:system",
        revision=4, expressions=("expression:system:new",),
    ))
    resolver = ReferenceResolver(store, _ReferenceAuthority(), margin_q=200_000)

    second = resolver.resolve(
        "reference:you",
        ReferenceConstraints(
            person="second", number=None, kind="content", recency=10,
            scope_ref="session:reference",
        ),
        "turn:current",
    )
    assert second.selected_ref == "expression:system:new"
    assert "expression:user" not in second.alternative_refs
    assert "expression:other-session" not in second.alternative_refs

    first = resolver.resolve(
        "reference:I",
        ReferenceConstraints(
            person="first", number="singular", kind="entity", recency=10,
            scope_ref="session:reference",
        ),
        "turn:current",
    )
    assert first.selected_ref == "entity:alice"

    plural = resolver.resolve(
        "reference:they",
        ReferenceConstraints(
            person="second", number="plural", kind="entity", recency=10,
            scope_ref="session:reference",
        ),
        "turn:current",
    )
    assert plural.selected_ref == "entity:team"

    limited = resolver.resolve(
        "reference:recent",
        ReferenceConstraints(
            person="second", number=None, kind="content", recency=1,
            scope_ref="session:reference",
        ),
        "turn:current",
    )
    assert limited.selected_ref == "expression:system:new"
    assert limited.alternative_refs == ()

    excluded = resolver.resolve(
        "reference:current-turn",
        ReferenceConstraints(person="second", number=None, kind="content", recency=10, scope_ref=None),
        "turn:4",
    )
    assert excluded.selected_ref == "expression:other-session"

    unresolved = resolver.resolve(
        "reference:none",
        ReferenceConstraints(person="first", number="plural", kind="entity", recency=10, scope_ref="session:reference"),
        "turn:current",
    )
    assert unresolved.selected_ref is None and unresolved.alternative_refs == ()

    # Orientation consumes verified focus rather than re-grounding it.
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    stores = memory_stores(authority_generation=authority.generation, model_identity="model:reference")
    try:
        orientation = OrientationProjector(
            authority, stores, RuntimeConfig.release(), focus_store=store
        ).project("session:reference", "unrelated surface")
        assert set(store.refs) <= set(orientation.focus_refs)
    finally:
        stores.close()
    return True


@lru_cache(maxsize=None)
def _gap_contract() -> bool:
    classifier = GapClassifier()
    cases = (
        (CoverageGap("span:test", "missing"), CycleStatus.PARTIAL),
        (ReferenceAmbiguity("ref:test", ("entity:a", "entity:b")), CycleStatus.AMBIGUOUS),
        (AbsentIdentity("entity:unknown", "frame:test"), CycleStatus.UNKNOWN),
        (SemanticConflict("graph:test", "conflict"), CycleStatus.CONFLICT),
        (VerificationFailure("structural", "cycle:test"), CycleStatus.UNSUPPORTED),
        (PermissionDenied("cap:write", "participant:user"), CycleStatus.DENIED),
        (ResourceUnavailable("model:test", "timeout"), CycleStatus.RESOURCE_UNAVAILABLE),
        (BudgetExhausted("tokens", 64), CycleStatus.BUDGET_EXHAUSTED),
        (MissingOwner("realizer"), CycleStatus.OPERATION_FAILED),
        (RealizationFailure("response:test", "no surface"), CycleStatus.REALIZATION_FAILED),
    )
    for error, expected in cases:
        receipt = classifier.classify(error)
        assert CycleStatus.from_gap_receipt(receipt) is expected
    return True


@lru_cache(maxsize=None)
def _canary_rows() -> tuple[dict[str, Any], ...]:
    from scripts.run_r3_canaries import execute_canaries

    with tempfile.TemporaryDirectory(prefix="cemm-r3-successor-") as td:
        rows = execute_canaries(ROOT, Path(td) / "canary", cases_path=None)
        return tuple(dict(row) for row in rows)


@lru_cache(maxsize=None)
def _r3_runtime_contract() -> bool:
    rows = _canary_rows()
    assert {row["semantic_mode"] for row in rows} == {"OBSERVE", "QUERY", "REQUEST", "SIMULATE"}
    assert all(row["effect_revision_delta"] > 0 for row in rows)
    assert all(row["world_revision_delta"] >= 0 for row in rows)
    assert all(row["verified_meaning_ref"] and row["response_meaning_ref"] for row in rows)

    # Every reviewed authority designation must complete the public ORIENT
    # boundary. This catches role-schema drift before R4 expands surfaces.
    surfaces: list[str] = []
    for path in sorted((ROOT / "data" / "authority").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("designations", ()):
            surface = row.get("surface")
            if isinstance(surface, str) and surface and surface not in surfaces:
                surfaces.append(surface)
    with tempfile.TemporaryDirectory(prefix="cemm-r3-public-") as td:
        runtime = load_runtime(
            ROOT, profile="development", store_path=Path(td) / "runtime.sqlite3"
        )
        owner = runtime._owners["orientation"]  # test-only exact owner probe
        try:
            for index, surface in enumerate(surfaces):
                session = f"session:r3-reviewed-surface:{index}"
                evidence = runtime.create_evidence(session, surface)
                turn = owner.orient_turn(session, evidence)
                assert turn.orientation.session_ref == session
                assert turn.context.revision_pin == turn.orientation.revision_pin
        finally:
            runtime.stores.close()

    # Programming defects must not be normalized into semantic gaps.
    runtime_tree = ast.parse((ROOT / "src" / "cemm_authoritative_hybrid" / "runtime.py").read_text(encoding="utf-8"))
    broad_handlers = [
        node for node in ast.walk(runtime_tree)
        if isinstance(node, ast.ExceptHandler)
        and isinstance(node.type, ast.Name)
        and node.type.id in {"Exception", "BaseException"}
    ]
    assert not broad_handlers
    return True


@lru_cache(maxsize=None)
def _episode_contract() -> bool:
    # The R3 boundary must keep derivation lineage distinct from verified
    # semantic meaning and preserve exact revision-bound artifacts.
    rows = _canary_rows()
    for row in rows:
        assert row["verified_meaning_ref"] != row["expression_ref"]
        pin = RevisionPin.from_dict(dict(row["final_revision_pin"]))
        assert pin.authority_generation
        assert pin.model_identity == "r3-boundary-canary"
        assert row["r3_artifacts_ref"]
    return True


@lru_cache(maxsize=None)
def _query_contract() -> bool:
    # Exercise current recursive reviewed-rule inference and proof lineage.
    from tests.test_r3_recursive_query import test_query_owner_applies_reviewed_rules_with_proof_lineage
    test_query_owner_applies_reviewed_rules_with_proof_lineage()
    rows = _canary_rows()
    query = next(row for row in rows if row["semantic_mode"] == "QUERY")
    assert query["decision_ref"] and query["response_meaning_ref"]
    return True


@lru_cache(maxsize=None)
def _learning_contract() -> bool:
    # Exercise the exact evaluated-draft -> plan/obligation path plus fail-closed
    # draft binding and incomplete-designation behavior using current R3 owners.
    from tests.test_r3_learning_transaction import (
        test_incomplete_designation_requests_clarification_without_learning_draft,
        test_learning_decision_materializes_exact_evaluated_draft,
        test_learning_finalization_rejects_unbound_draft_ref,
    )
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    for fn in (
        test_learning_decision_materializes_exact_evaluated_draft,
        test_learning_finalization_rejects_unbound_draft_ref,
        test_incomplete_designation_requests_clarification_without_learning_draft,
    ):
        stores = memory_stores(authority_generation=authority.generation, model_identity="model:r3-learning-successor")
        try:
            fn(authority, stores)
        finally:
            stores.close()
    return True


@lru_cache(maxsize=None)
def _epistemic_contract() -> bool:
    rows = _canary_rows()
    observe = next(row for row in rows if row["semantic_mode"] == "OBSERVE")
    # Text-only evidence remains attributed/contested and does not silently
    # become a trusted world mutation.
    assert observe["decision_status"] in {"contested", "attributed"}
    assert observe["world_revision_delta"] == 0
    assert observe["effect_kind"] == "NoEffectReceipt"
    return True


@lru_cache(maxsize=None)
def _restart_contract() -> bool:
    from scripts.run_r3_canaries import MODEL_IDENTITY, execute_canaries
    authority = AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")
    with tempfile.TemporaryDirectory(prefix="cemm-r3-restart-") as td:
        base = Path(td) / "restart"
        rows = execute_canaries(ROOT, base, cases_path=None)
        for row in rows:
            case = str(row["case_ref"])
            path = base.parent / f"{base.name}-{case}.sqlite3"
            stores = open_stores(
                path,
                authority_generation=authority.generation,
                model_identity=MODEL_IDENTITY,
            )
            try:
                assert stores.revision_pin().as_dict() == row["final_revision_pin"]
            finally:
                stores.close()
    return True


@lru_cache(maxsize=None)
def _response_contract() -> bool:
    """Bind predecessor response assertions to Response Meaning ABI 2."""
    from cemm_authoritative_hybrid.decision import (
        Decision,
        DecisionAction,
        DecisionContribution,
        DecisionStatus,
    )
    from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle, ModeEvaluation
    from cemm_authoritative_hybrid.r3_effects import NoEffectReason, NoEffectReceipt
    from cemm_authoritative_hybrid.r3_persistence import predicted_effect_pin
    from cemm_authoritative_hybrid.r3_response import ResponseBuilder, ResponseMeaning
    from tests.test_r3_decision_abi import _meaning, _situation
    from tests.test_r3_learning_response import (
        test_response_meaning_round_trip_has_no_surface_text,
    )

    test_response_meaning_round_trip_has_no_surface_text()
    meaning = _meaning()
    situation = _situation()
    contribution = DecisionContribution(
        status=DecisionStatus.DENIED,
        action=DecisionAction.NO_OP,
        blocker_refs=("blocker:permission",),
        policy_refs=("policy:deny",),
    )
    decision = Decision.create(
        meaning=meaning, situation=situation, contribution=contribution
    )
    evaluation = EvaluationBundle.create(
        decision=decision,
        expression=meaning.expression,
        situation=situation,
        mode_evaluation=ModeEvaluation(contribution=contribution),
        revision_pin=situation.revision_pin,
    )
    effect = NoEffectReceipt.create(
        reason=NoEffectReason.NO_REQUESTED_EFFECT,
        idempotency_key="effect-key:response-denied",
        journal_origin_ref="journal:origin:response-denied",
        journal_preterminal_ref="journal:preterminal:response-denied",
        decision_ref=decision.decision_ref,
        verified_meaning_ref=meaning.verified_meaning_ref,
        expression_ref=meaning.expression.expression_ref,
        situation_ref=situation.situation_ref,
        program_ref=meaning.program_ref,
        learning_plan_ref=None,
        obligation_ref=None,
        proof_refs=(),
        blocker_refs=("blocker:permission",),
        input_revision_pin=situation.revision_pin,
        output_revision_pin=predicted_effect_pin(
            situation.revision_pin, has_world_delta=False
        ),
    )
    response = ResponseBuilder().build(
        evaluation=evaluation,
        meaning=meaning,
        situation=situation,
        effect=effect,
        learning_plan=None,
        obligation=None,
    )
    assert type(response) is ResponseMeaning
    assert response.cycle_status is CycleStatus.DENIED
    assert response.discourse_action == "deny"
    assert response.polarity_ref == "polarity:negative"
    assert response.epistemic_status_ref == "epistemic_status:denied"
    assert response.response_expression.expression_ref == meaning.expression.expression_ref
    assert "surface" not in response.as_dict()
    assert ResponseMeaning.from_dict(response.as_dict()) == response
    try:
        response.discourse_action = "forged"  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:  # pragma: no cover
        raise AssertionError("ResponseMeaning must remain immutable")
    return True


@lru_cache(maxsize=None)
def _safety_contract() -> bool:
    # Invoke the current governed anti-bypass checks directly so predecessor
    # safety lineages bind to AST-semantic invariants, not token existence.
    from tests.test_r3_no_program_as_meaning import (
        test_r3_owners_do_not_access_program_actions,
        test_r3_owners_do_not_access_program_graph,
        test_r3_owners_do_not_branch_on_raw_words,
        test_r3_owners_do_not_import_semantic_switch_program,
        test_r3_owners_do_not_read_orientation_source_text,
        test_r3_transition_preview_not_effect_authorization,
    )
    for fn in (
        test_r3_owners_do_not_access_program_actions,
        test_r3_owners_do_not_access_program_graph,
        test_r3_owners_do_not_branch_on_raw_words,
        test_r3_owners_do_not_import_semantic_switch_program,
        test_r3_owners_do_not_read_orientation_source_text,
        test_r3_transition_preview_not_effect_authorization,
    ):
        fn()
    return True


_CONTRACTS = {
    "focus": _focus_contract,
    "obligation": _obligation_contract,
    "reference": _reference_contract,
    "gap": _gap_contract,
    "r3_runtime": _r3_runtime_contract,
    "episode": _episode_contract,
    "cycle": _r3_runtime_contract,
    "epistemic": _epistemic_contract,
    "query": _query_contract,
    "learning": _learning_contract,
    "restart": _restart_contract,
    "response": _response_contract,
    "safety": _safety_contract,
}


def assert_successor_contract(contract: str, assertion_ref: str) -> None:
    """Execute the live R3 contract for one preserved assertion identity."""
    if type(assertion_ref) is not str or not assertion_ref.startswith("assertion:"):
        raise TypeError("assertion_ref must be a governed assertion identity")
    try:
        runner = _CONTRACTS[contract]
    except KeyError as exc:
        raise AssertionError(f"unknown R3 successor contract: {contract}") from exc
    assert runner() is True
