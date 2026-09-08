"""Durable exact unknown-query evidence; not learning authorization."""
from dataclasses import fields, replace
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import Decision, DecisionContribution, DecisionStatus
from cemm_authoritative_hybrid.r3_artifacts import (
    EvaluationBundle, ModeEvaluation, QueryResult, QueryStatus,
)
from cemm_authoritative_hybrid.r3_codec import thaw_json
from cemm_authoritative_hybrid.r3_effects import (
    AdapterRegistry, NoEffectReceipt, R3EffectGateway,
)
from cemm_authoritative_hybrid.r3_persistence import (
    EffectJournalState, effect_journal_get, obligation_snapshot,
)

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_query_witness.py::test_unknown_query_witness_survives_restart_and_terminal_retry": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-unknown-query-witness-survives-restart-and-terminal-retry",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "6aac6f5beceb2d07b3d9284f198171453aa85f4ec2ffe5a4a8e32a4a87460492"
    },
    "tests/test_foundation_query_witness.py::test_noneligible_no_effect_preserves_minimal_journal[known-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-noneligible-no-effect-preserves-minimal-journal-known-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "03d62db78833e76b890c88b84ca516e5d92bfe15b5f013250915aa01a0ac2c2b"
    },
    "tests/test_foundation_query_witness.py::test_noneligible_no_effect_preserves_minimal_journal[nonquery]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-noneligible-no-effect-preserves-minimal-journal-nonquery",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "03d62db78833e76b890c88b84ca516e5d92bfe15b5f013250915aa01a0ac2c2b"
    },
    "tests/test_foundation_query_witness.py::test_unknown_query_witness_rejects_mismatched_result_lineage[expression]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-unknown-query-witness-rejects-mismatched-result-lineage-expression",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "e20bb10e5153b1fa7759b0c45b430561cb452ae59ee3b8870212950f14c4a307"
    },
    "tests/test_foundation_query_witness.py::test_unknown_query_witness_rejects_mismatched_result_lineage[revision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-unknown-query-witness-rejects-mismatched-result-lineage-revision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "e20bb10e5153b1fa7759b0c45b430561cb452ae59ee3b8870212950f14c4a307"
    },
    "tests/test_foundation_query_witness.py::test_unknown_query_witness_rejects_mismatched_result_lineage[decision-result]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-unknown-query-witness-rejects-mismatched-result-lineage-decision-result",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "e20bb10e5153b1fa7759b0c45b430561cb452ae59ee3b8870212950f14c4a307"
    },
    "tests/test_foundation_query_witness.py::test_incomplete_or_ambiguous_queries_do_not_persist_witness[partial-result]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-incomplete-or-ambiguous-queries-do-not-persist-witness-partial-result",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a40572432344560096c6456ef3ac5b2ebeacc9a98384f9ecbd4d3ac41b0a9530"
    },
    "tests/test_foundation_query_witness.py::test_incomplete_or_ambiguous_queries_do_not_persist_witness[zero-results]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-incomplete-or-ambiguous-queries-do-not-persist-witness-zero-results",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a40572432344560096c6456ef3ac5b2ebeacc9a98384f9ecbd4d3ac41b0a9530"
    },
    "tests/test_foundation_query_witness.py::test_incomplete_or_ambiguous_queries_do_not_persist_witness[multiple-results]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-incomplete-or-ambiguous-queries-do-not-persist-witness-multiple-results",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a40572432344560096c6456ef3ac5b2ebeacc9a98384f9ecbd4d3ac41b0a9530"
    },
    "tests/test_foundation_query_witness.py::test_incomplete_or_ambiguous_queries_do_not_persist_witness[partial-decision]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-incomplete-or-ambiguous-queries-do-not-persist-witness-partial-decision",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "a40572432344560096c6456ef3ac5b2ebeacc9a98384f9ecbd4d3ac41b0a9530"
    }
}


def test_unknown_query_witness_survives_restart_and_terminal_retry(tmp_path):
    path = tmp_path / "query-witness.db"
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    try:
        before = runtime.stores.revision_pin()
        result = runtime.process("session:query-witness", "What does zorbulate mean?")
        evaluation = result.evaluation
        meaning = result.verification.selected_meaning
        receipt = result.effect_receipt
        assert evaluation.situation.mode is SemanticMode.QUERY
        assert evaluation.decision.status is DecisionStatus.UNKNOWN
        assert len(evaluation.query_results) == 1
        query = evaluation.query_results[0]
        assert query.status is QueryStatus.UNKNOWN
        assert type(receipt) is NoEffectReceipt
        stored = effect_journal_get(runtime.stores, receipt.idempotency_key)
        assert stored.entry.state is EffectJournalState.NO_EFFECT
        witness = thaw_json(stored.entry.request_payload).get("query_evaluation")
        assert witness == evaluation.as_dict()
        assert EvaluationBundle.from_dict(witness) == evaluation
        assert evaluation.decision.query_result_refs == (query.query_result_ref,)
        assert query.expression_ref == meaning.expression.expression_ref == receipt.expression_ref
        assert query.revision_pin == evaluation.revision_pin == evaluation.situation.revision_pin
        assert receipt.situation_ref == evaluation.situation.situation_ref
        assert receipt.decision_ref == evaluation.decision.decision_ref == stored.entry.decision_ref
        assert receipt.learning_plan_ref is None and receipt.source_obligation_ref is None
        continuation = thaw_json(stored.entry.request_payload)["query_continuation"]
        assert obligation_snapshot(runtime.stores, "session:query-witness", maximum=1)["obligation_refs"] == (continuation["obligation_ref"],)
        assert runtime.stores.world.revision == before.world_revision
        assert receipt.output_revision_pin.effect_revision == receipt.input_revision_pin.effect_revision + 2
        persisted = stored
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=path)
    try:
        stored = effect_journal_get(reopened.stores, receipt.idempotency_key)
        assert stored == persisted
        assert EvaluationBundle.from_dict(thaw_json(stored.entry.request_payload)["query_evaluation"]) == evaluation
        before_retry = reopened.stores.revision_pin()
        replay = R3EffectGateway(reopened.stores, AdapterRegistry()).execute(
            evaluation, meaning, evaluation.situation,
        )
        assert replay == receipt
        assert reopened.stores.revision_pin() == before_retry
        assert effect_journal_get(reopened.stores, receipt.idempotency_key) == stored
    finally:
        reopened.stores.close()


@pytest.mark.parametrize(
    "surface,mode",
    (("What does mother mean?", SemanticMode.QUERY),
     ("Alice is a mother.", SemanticMode.OBSERVE)),
    ids=("known-query", "nonquery"),
)
def test_noneligible_no_effect_preserves_minimal_journal(tmp_path, surface, mode):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "control.db")
    try:
        result = runtime.process("session:query-control", surface)
        assert result.evaluation.situation.mode is mode
        if mode is SemanticMode.QUERY:
            assert result.evaluation.query_results[0].status is QueryStatus.SUPPORTED
        receipt = result.effect_receipt
        assert type(receipt) is NoEffectReceipt
        stored = effect_journal_get(runtime.stores, receipt.idempotency_key)
        assert set(stored.entry.request_payload) == {
            "journal_origin_ref", "kind", "reason", "decision_ref",
            "session_ref", "turn_ref", "turn_index", "session_phase_ref",
        }
        before_retry = runtime.stores.revision_pin()
        assert R3EffectGateway(runtime.stores, AdapterRegistry()).execute(
            result.evaluation, result.verification.selected_meaning, result.evaluation.situation,
        ) == receipt
        assert runtime.stores.revision_pin() == before_retry
        assert effect_journal_get(runtime.stores, receipt.idempotency_key) == stored
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("mismatch", ("expression", "revision", "decision-result"),
                         ids=("expression", "revision", "decision-result"))
def test_unknown_query_witness_rejects_mismatched_result_lineage(tmp_path, mismatch):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "lineage.db")
    try:
        result = runtime.process("session:query-lineage", "What does zorbulate mean?")
        evaluation = result.evaluation
        query = evaluation.query_results[0]
        changed = QueryResult.create(
            expression_ref="expression:other" if mismatch == "expression" else query.expression_ref,
            status=query.status, bindings=query.bindings, proof=query.proof,
            retrieval_refs=("source:other",) if mismatch == "decision-result" else query.retrieval_refs,
            rounds=query.rounds,
            revision_pin=replace(query.revision_pin, world_revision=query.revision_pin.world_revision + 1)
            if mismatch == "revision" else query.revision_pin,
        )
        contribution_values = {row.name: getattr(evaluation.decision, row.name)
                               for row in fields(DecisionContribution)}
        if mismatch != "decision-result":
            contribution_values["query_result_refs"] = (changed.query_result_ref,)
        contribution = DecisionContribution(**contribution_values)
        decision = Decision.create(meaning=result.verification.selected_meaning,
                                   situation=evaluation.situation, contribution=contribution)
        altered = EvaluationBundle.create(
            decision=decision, expression=evaluation.expression,
            situation=evaluation.situation, revision_pin=evaluation.revision_pin,
            mode_evaluation=ModeEvaluation(
                contribution=contribution,
                query_results=(changed,),
            ),
        )
        before = runtime.stores.revision_pin()
        stored = effect_journal_get(runtime.stores, result.effect_receipt.idempotency_key)
        with pytest.raises(ValueError, match="query.*lineage"):
            R3EffectGateway(runtime.stores, AdapterRegistry()).execute(
                altered, result.verification.selected_meaning, evaluation.situation,
            )
        assert runtime.stores.revision_pin() == before
        assert effect_journal_get(runtime.stores, result.effect_receipt.idempotency_key) == stored
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("partial-result", "zero-results", "multiple-results", "partial-decision"),
                         ids=("partial-result", "zero-results", "multiple-results", "partial-decision"))
def test_incomplete_or_ambiguous_queries_do_not_persist_witness(tmp_path, case):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "ineligible.db")
    try:
        result = runtime.process("session:ineligible-query", "What does zorbulate mean?")
        evaluation = result.evaluation
        query = evaluation.query_results[0]
        changed = QueryResult.create(
            expression_ref=query.expression_ref,
            status=QueryStatus.PARTIAL if case == "partial-result" else QueryStatus.UNKNOWN,
            bindings=(), proof=None, retrieval_refs=("source:additional",),
            rounds=query.rounds, revision_pin=query.revision_pin,
        )
        queries = () if case == "zero-results" else (query, changed) if case == "multiple-results" else (changed,)
        contribution_values = {row.name: getattr(evaluation.decision, row.name)
                               for row in fields(DecisionContribution)}
        contribution_values["query_result_refs"] = tuple(row.query_result_ref for row in queries)
        if case == "partial-decision":
            contribution_values["status"] = DecisionStatus.PARTIAL
        contribution = DecisionContribution(**contribution_values)
        decision = Decision.create(meaning=result.verification.selected_meaning,
                                   situation=evaluation.situation, contribution=contribution)
        altered = EvaluationBundle.create(
            decision=decision, expression=evaluation.expression, situation=evaluation.situation,
            revision_pin=evaluation.revision_pin,
            mode_evaluation=ModeEvaluation(contribution=contribution, query_results=queries),
        )
        before_world = runtime.stores.world.revision
        receipt = R3EffectGateway(runtime.stores, AdapterRegistry()).execute(
            altered, result.verification.selected_meaning, evaluation.situation,
        )
        assert type(receipt) is NoEffectReceipt
        stored = effect_journal_get(runtime.stores, receipt.idempotency_key)
        assert "query_evaluation" not in stored.entry.request_payload
        assert runtime.stores.world.revision == before_world
    finally:
        runtime.stores.close()
