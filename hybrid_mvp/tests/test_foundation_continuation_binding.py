"""Exact query-content continuity from automatic obligations, not acquisition."""
from dataclasses import fields, replace
from pathlib import Path
import json

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import DecisionAction
from cemm_authoritative_hybrid.dialogue import DialogueObligation, DialogueObligationManager, ObligationKind
from cemm_authoritative_hybrid.expressions import GroundedReference, LiteralValue, RoleBinding, SemanticApplication, SemanticExpression
from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
from cemm_authoritative_hybrid.r3_learning import LearningCoordinator
from cemm_authoritative_hybrid.r3_artifacts import LearningDraft
from cemm_authoritative_hybrid.persistence import memory_stores, open_stores
from cemm_authoritative_hybrid.situation import SituationContext
from tests.test_foundation_semantics import _matrix_meaning, _matrix_expression

ROOT = Path(__file__).parents[1]
__cemm_test_inventory__ = {
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_journal_lineage[journal-key]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-journal-lineage-journal-key",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "bd09cf1398f24b21e3fc08e7dcb20ed1b68202e708e7b22bc33e13170b7d5c81"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_journal_lineage[journal-intent]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-journal-lineage-journal-intent",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "bd09cf1398f24b21e3fc08e7dcb20ed1b68202e708e7b22bc33e13170b7d5c81"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_journal_lineage[source-turn]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-journal-lineage-source-turn",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "bd09cf1398f24b21e3fc08e7dcb20ed1b68202e708e7b22bc33e13170b7d5c81"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_journal_lineage[source-phase]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-journal-lineage-source-phase",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "bd09cf1398f24b21e3fc08e7dcb20ed1b68202e708e7b22bc33e13170b7d5c81"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_snapshot_work_and_order_are_session_indexed[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-snapshot-work-and-order-are-session-indexed-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "d5aee350190968b49fbde49340c1c2dd170362319fac2b4046a3f6d0d3be8581"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_snapshot_work_and_order_are_session_indexed[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-snapshot-work-and-order-are-session-indexed-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "d5aee350190968b49fbde49340c1c2dd170362319fac2b4046a3f6d0d3be8581"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_exact_answer_binds_real_query_and_expiry[same-process]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-matrix-alias-directive-binds-actual-prior-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b043e9cbbde96724e19c1d80fa2a5fc63ce374ceba198d54dac9564a2c2adf20",
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_exact_answer_binds_real_query_and_expiry[restart]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-exact-answer-binds-real-query-and-expiry-restart",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "b043e9cbbde96724e19c1d80fa2a5fc63ce374ceba198d54dac9564a2c2adf20"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_plan_preserves_exact_evaluated_draft": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-learning-decision-materializes-exact-evaluated-draft",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "56c4a2d61995e94ce76dd0c400982f6b1fb5eb51859eac276273a33c0c8e8f30",
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_finalization_rejects_unbound_draft_ref": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-learning-finalization-rejects-unbound-draft-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5649bd69e9e2482cda45efb82952fb8d893ec1cc6b133b6da44ee98f2d052b11",
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_positive_directive_remains_eligible_with_bound_query": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-safety-learning-requires-eligible-directive-root-positive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "capability-effect",
        "source_ast_sha256": "5ae1118a483b56aa0c42b79575addb3523c9e53d9b83742d16da65e16e19e8de",
        "supersedes_node_id": "tests/test_foundation_semantics.py::test_foundation_safety_learning_requires_eligible_directive_root[positive]"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[source-query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-source-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[surface]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-surface",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[target]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[target-kind]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-target-kind",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[answer-contract]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-answer-contract",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[proof]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[stale-snapshot]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-stale-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[other-literal]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-other-literal",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[case-sensitive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-case-sensitive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[forged-snapshot]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-forged-snapshot",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[omitted-ref]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-omitted-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[foreign-session]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-foreign-session",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[expired]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-expired",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[missing-witness]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-missing-witness",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_receipt_lineage[program]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-receipt-lineage-program",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "dbd99394f7c7e3ab2eb2d8b18bf1b8dfe28ec65d9b0b66f33130cc724cbaeda8"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_receipt_lineage[proof]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-receipt-lineage-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "dbd99394f7c7e3ab2eb2d8b18bf1b8dfe28ec65d9b0b66f33130cc724cbaeda8"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_rejects_rehashed_foreign_receipt_lineage[blockers]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-rejects-rehashed-foreign-receipt-lineage-blockers",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "dbd99394f7c7e3ab2eb2d8b18bf1b8dfe28ec65d9b0b66f33130cc724cbaeda8"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[same-turn]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-same-turn",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[completed]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-completed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_invalid_answer_cannot_materialize[multiple]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-invalid-answer-cannot-materialize-multiple",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "72ba281a7020f5048ab86273c6f966415cf20fcf97355c49addfee818b5ca5dd"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_memory_index_rejects_invalid_writes_without_partial_change": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-memory-index-rejects-invalid-writes-without-partial-change",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "63c2fa610d8af5fad7ee33b05ab70e7baeda5dd7cb3fc7ff8b2a3639bb879885"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_preserves_query_lineage_across_other_session_effects[before-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-preserves-query-lineage-across-other-session-effects-before-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "5f0661855ec9e7079119d76c5f363bd5affc0ec177be62dd4dcbc269ad7be89f"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_preserves_query_lineage_across_other_session_effects[after-planned]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-preserves-query-lineage-across-other-session-effects-after-planned",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "5f0661855ec9e7079119d76c5f363bd5affc0ec177be62dd4dcbc269ad7be89f"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_materialization_rechecks_bound_content[non-directive]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-materialization-rechecks-bound-content-non-directive",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "38aa80b23d580ccc4d6cbf0ccb3baf5fa734187a9e752b484eb02bcc87d05084"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_storage_keeps_generic_identifier_bounds_separate[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-storage-keeps-generic-identifier-bounds-separate-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "61b5ef9fb2854464bff6947d34cb3fce11468fa0cedc0771e247f2da188815ca"
    },
    "tests/test_foundation_continuation_binding.py::test_continuation_storage_keeps_generic_identifier_bounds_separate[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:continuation-storage-keeps-generic-identifier-bounds-separate-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "learning-response",
        "source_ast_sha256": "61b5ef9fb2854464bff6947d34cb3fce11468fa0cedc0771e247f2da188815ca"
    }
}


@pytest.mark.parametrize("field", ("idempotency_key", "intent_ref", "turn_ref", "session_phase_ref"), ids=("journal-key", "journal-intent", "source-turn", "source-phase"))
def test_continuation_rejects_rehashed_foreign_journal_lineage(tmp_path, field):
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, effect_journal_get
    from cemm_authoritative_hybrid.r3_codec import thaw_json
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway
    from cemm_authoritative_hybrid.persistence import _payload_hash
    runtime, source, pending = _setup(tmp_path)
    try:
        key = R3EffectGateway._effect_key(pending.source_decision_ref, None, "no_effect:unknown")
        original = effect_journal_get(runtime.stores, key).entry
        values = {f.name: getattr(original, f.name) for f in fields(original) if f.name not in {"abi_version", "journal_ref"}}
        if field in {"turn_ref", "session_phase_ref"}:
            values["request_payload"] = {**thaw_json(original.request_payload), field: "foreign"}
        else:
            values[field] = "foreign"
        forged = EffectJournalEntry.create(**values).as_dict()
        runtime.stores._backend._conn.execute("UPDATE r3_effect_journal SET entry_json=?, entry_hash=? WHERE idempotency_key=?",
            (json.dumps(forged), _payload_hash(forged), key))
        runtime.stores._backend._conn.commit()
        meaning, situation = _answer(runtime, source.evaluation.situation)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        result = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert result.learning_drafts == ()
        assert result.decision.action is DecisionAction.REQUEST_CLARIFICATION
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field", ("program_ref", "proof_refs", "blocker_refs"), ids=("program", "proof", "blockers"))
def test_continuation_rejects_rehashed_foreign_receipt_lineage(tmp_path, field):
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, effect_journal_get
    from cemm_authoritative_hybrid.r3_codec import thaw_json
    from cemm_authoritative_hybrid.r3_effects import NoEffectReceipt, R3EffectGateway
    from cemm_authoritative_hybrid.persistence import _payload_hash
    runtime, source, pending = _setup(tmp_path)
    try:
        key = R3EffectGateway._effect_key(pending.source_decision_ref, None, "no_effect:unknown")
        stored = effect_journal_get(runtime.stores, key)
        receipt = NoEffectReceipt.from_dict(thaw_json(stored.receipt_payload))
        values = {f.name: getattr(receipt, f.name) for f in fields(receipt) if f.name not in {"abi_version", "receipt_ref"}}
        values[field] = "program:foreign" if field == "program_ref" else ("foreign",)
        forged_receipt = NoEffectReceipt.create(**values)
        values = {f.name: getattr(stored.entry, f.name) for f in fields(stored.entry) if f.name not in {"abi_version", "journal_ref"}}
        values["outcome_ref"] = forged_receipt.receipt_ref
        forged_entry = EffectJournalEntry.create(**values).as_dict()
        payload = forged_receipt.as_dict()
        runtime.stores._backend._conn.execute("UPDATE r3_effect_journal SET entry_json=?, entry_hash=?, receipt_json=?, receipt_hash=? WHERE idempotency_key=?",
            (json.dumps(forged_entry), _payload_hash(forged_entry), json.dumps(payload), _payload_hash(payload), key))
        runtime.stores._backend._conn.commit()
        meaning, situation = _answer(runtime, source.evaluation.situation)
        result = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert result.learning_drafts == ()
        assert result.decision.action is DecisionAction.REQUEST_CLARIFICATION
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_continuation_snapshot_work_and_order_are_session_indexed(tmp_path, backend):
    stores = memory_stores() if backend == "memory" else open_stores(tmp_path / "index.db", authority_generation="authority:generation-test")
    try:
        for ref in ("obligation:z", "obligation:a"):
            stores.obligations.commit(ref, "session:chosen", {}, expected_revision=stores.obligations.revision)
        for index in range(128):
            stores.obligations.commit(f"obligation:{index}", "session:irrelevant", {}, expected_revision=stores.obligations.revision)
        if backend == "memory":
            class NoEnumeration(dict):
                def __iter__(self): raise AssertionError("whole obligation store enumerated")
                def items(self): raise AssertionError("whole obligation store enumerated")
                def values(self): raise AssertionError("whole obligation store enumerated")
            stores.obligations._obligations = NoEnumeration(stores.obligations._obligations)
        else:
            plan = stores._backend._conn.execute("EXPLAIN QUERY PLAN SELECT obligation_ref FROM obligations WHERE session_ref=? AND resolved=0 ORDER BY revision, obligation_ref LIMIT ?", ("session:chosen", 3)).fetchall()
            assert all("SCAN" not in row[3].upper() and "TEMP" not in row[3].upper() for row in plan)
        assert stores.r3_obligation_snapshot("session:chosen", maximum=2)["obligation_refs"] == ["obligation:z", "obligation:a"]
        with pytest.raises(ValueError, match="bound"):
            stores.r3_obligation_snapshot("session:chosen", maximum=1)
    finally:
        stores.close()


def test_continuation_memory_index_rejects_invalid_writes_without_partial_change():
    stores = memory_stores()
    try:
        stores.obligations.commit("obligation:existing", "session:good", {}, expected_revision=0)
        before = stores.obligations.keyed_row("obligation:existing")
        snapshot = stores.r3_obligation_snapshot("session:good", maximum=1)
        with pytest.raises(TypeError):
            stores.obligations.commit("obligation:existing", [], {}, expected_revision=1)
        assert stores.obligations.revision == 1
        assert stores.obligations.keyed_row("obligation:existing") == before
        assert stores.r3_obligation_snapshot("session:good", maximum=1) == snapshot
        with pytest.raises(TypeError):
            stores.obligations.complete("obligation:existing", [], "session:good", {}, expected_revision=1)
        assert stores.obligations.revision == 1
        assert stores.obligations.keyed_row("obligation:existing") == before
        assert stores.r3_obligation_snapshot("session:good", maximum=1) == snapshot
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_continuation_storage_keeps_generic_identifier_bounds_separate(tmp_path, backend):
    stores = memory_stores() if backend == "memory" else open_stores(tmp_path / "bounds.db", authority_generation="authority:generation-test")
    try:
        ref, session = "obligation:" + "x" * 513, "session:" + "y" * 513
        stores.obligations.commit(ref, session, {}, expected_revision=0)
        assert stores.obligations.revision == 1
        assert stores.r3_obligation_snapshot(session, maximum=1)["obligation_refs"] == [ref]
        with pytest.raises(ValueError, match="characters"):
            stores.pending_dialogue_obligations(session, (ref,), maximum=1, turn_index=2)
    finally:
        stores.close()


def _setup(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "continuation.db")
    query_cycle = runtime.process("session:continuation", "What does velnora mean?")
    query = query_cycle.evaluation.query_results[0]
    pending = DialogueObligation.create(kind=ObligationKind.LEARNING_ANSWER,
        session_ref="session:continuation", source_query_ref=query.query_result_ref,
        expected_answer_contract_ref="contract:designation_answer:v2", created_turn_index=1,
        expires_turn_index=6, source_decision_ref=query_cycle.evaluation.decision.decision_ref,
        completion_receipt_ref=None, revision_pin=query.revision_pin)
    assert runtime.stores.obligations.get(pending.obligation_ref) == {**pending.as_dict(), "resolved": False}
    return runtime, query_cycle, pending


def _answer(runtime, source_situation, *, surface="velnora", **changes):
    snapshot = runtime.stores.r3_obligation_snapshot(source_situation.session_ref, maximum=16)
    values = {f.name: getattr(source_situation, f.name) for f in fields(source_situation)
              if f.name not in {"abi_version", "situation_ref"}}
    values.update(mode=SemanticMode.REQUEST, turn_index=2, turn_ref="turn:answer",
        actor_ref=source_situation.addressee_ref,
        epistemic_scope_ref="epistemic_scope:requested",
        obligation_refs=tuple(snapshot["obligation_refs"]), obligation_snapshot_ref=snapshot["snapshot_ref"],
        revision_pin=runtime.stores.revision_pin())
    values.update(changes)
    situation = SituationContext.create(**values)
    app = SemanticApplication("app:answer", "op:event", "event:learn_alias", (
        RoleBinding("role:actor", GroundedReference(source_situation.addressee_ref)),
        RoleBinding("role:surface", LiteralValue("string", surface)),
        RoleBinding("role:target", GroundedReference("rel:likes"))))
    expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
    return _matrix_meaning(expression, runtime.stores.revision_pin()), situation


@pytest.mark.parametrize("restart", (False, True), ids=("same-process", "restart"))
def test_continuation_exact_answer_binds_real_query_and_expiry(tmp_path, restart):
    runtime, source, pending = _setup(tmp_path)
    try:
        if restart:
            runtime.stores.close()
            runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "continuation.db")
        meaning, situation = _answer(runtime, source.evaluation.situation)
        before = (runtime.stores.revision_pin(), runtime.stores.obligations.revision)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert evaluation.decision.action is DecisionAction.CREATE_LEARNING_OBLIGATION
        assert evaluation.learning_drafts[0].source_query_ref == pending.source_query_ref
        assert pending.obligation_ref in evaluation.learning_drafts[0].proof_refs
        plan, obligation = LearningCoordinator(runtime._authority, runtime.stores).materialize(evaluation, meaning, situation)
        assert plan.source_query_ref == obligation.source_query_ref == pending.source_query_ref
        assert plan.expires_at_turn == pending.expires_turn_index
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


def test_continuation_plan_preserves_exact_evaluated_draft(tmp_path):
    runtime, source, pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        draft = evaluation.learning_drafts[0]
        assert evaluation.decision.learning_draft_refs == (draft.learning_draft_ref,)
        plan, obligation = LearningCoordinator(runtime._authority, runtime.stores).materialize(evaluation, meaning, situation)
        assert plan.decision_ref == evaluation.decision.decision_ref
        assert plan.surface_literal == draft.surface_literal
        assert plan.target_ref == draft.target_ref
        assert plan.expected_target_kinds == draft.expected_target_kinds
        assert plan.answer_contract_ref == draft.answer_contract_ref
        assert draft.learning_draft_ref in plan.provenance_refs
        assert plan.source_obligation_ref == obligation.obligation_ref == pending.obligation_ref
        assert plan.source_query_ref == pending.source_query_ref
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("stage", ("before", "after"), ids=("before-planned", "after-planned"))
def test_continuation_preserves_query_lineage_across_other_session_effects(tmp_path, monkeypatch, stage):
    from cemm_authoritative_hybrid.r3_effects import R3EffectGateway
    original = R3EffectGateway._begin
    def interleaved(gateway, **kwargs):
        def other_session():
            gateway._stores.r3_effect_journal_begin(idempotency_key="key:other-session", intent_ref="intent:other",
                decision_ref="decision:other", request_payload={"session_ref": "session:other", "turn_index": 1},
                expected_effect_revision=gateway._stores.effects.revision)
        if "query_evaluation" in kwargs["request_payload"] and stage == "before":
            other_session()
        journal = original(gateway, **kwargs)
        if "query_evaluation" in kwargs["request_payload"] and stage == "after":
            other_session()
        return journal
    monkeypatch.setattr(R3EffectGateway, "_begin", interleaved)
    runtime, source, pending = _setup(tmp_path)
    try:
        assert source.effect_receipt.output_revision_pin.effect_revision == 3
        meaning, situation = _answer(runtime, source.evaluation.situation)
        result = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert result.learning_drafts[0].source_query_ref == pending.source_query_ref
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_continuation_finalization_rejects_unbound_draft_ref(tmp_path):
    runtime, source, _pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation)
        evaluator = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config)
        result = evaluator.evaluate_mode(meaning, situation)
        tampered = replace(result.contribution, learning_draft_refs=("learning_draft:tampered",))
        with pytest.raises(ValueError, match="Decision learning_draft_refs does not match included artifacts"):
            evaluator.finalize(meaning, situation, result, tampered)
    finally:
        runtime.stores.close()


def test_continuation_positive_directive_remains_eligible_with_bound_query(tmp_path):
    runtime, source, _pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation)
        meaning = _matrix_meaning(_matrix_expression(meaning.expression.applications[0], "positive"), situation.revision_pin)
        before = runtime.stores.revisions(), runtime.stores.r3_world_facts()
        result = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert result.effect_intents == () and len(result.learning_drafts) == 1
        assert result.learning_drafts[0].surface_literal == "velnora"
        assert result.learning_drafts[0].target_ref == "rel:likes"
        assert (runtime.stores.revisions(), runtime.stores.r3_world_facts()) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field", ("source_query_ref", "surface_literal", "target_ref", "expected_target_kinds", "answer_contract_ref", "proof_refs", "stale-snapshot", "kind"),
                         ids=("source-query", "surface", "target", "target-kind", "answer-contract", "proof", "stale-snapshot", "non-directive"))
def test_continuation_materialization_rechecks_bound_content(tmp_path, field):
    runtime, source, _pending = _setup(tmp_path)
    try:
        meaning, situation = _answer(runtime, source.evaluation.situation)
        evaluator = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config)
        mode = evaluator.evaluate_mode(meaning, situation)
        if field == "stale-snapshot":
            runtime.stores.obligations.commit("obligation:new", situation.session_ref, {}, expected_revision=runtime.stores.obligations.revision)
        else:
            draft = mode.learning_drafts[0]
            values = {f.name: getattr(draft, f.name) for f in fields(draft) if f.name not in {"abi_version", "learning_draft_ref"}}
            values[field] = ("entity",) if field == "expected_target_kinds" else () if field == "proof_refs" else "lookup" if field == "kind" else "forged"
            forged = LearningDraft.create(**values)
            mode = replace(mode, learning_drafts=(forged,), contribution=replace(mode.contribution, learning_draft_refs=(forged.learning_draft_ref,)))
        evaluation = evaluator.finalize(meaning, situation, mode, mode.contribution)
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with pytest.raises(ValueError):
            LearningCoordinator(runtime._authority, runtime.stores).materialize(evaluation, meaning, situation)
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("other-literal", "case-sensitive", "forged-snapshot", "omitted-ref", "foreign-session", "expired", "missing-witness", "same-turn", "completed", "multiple"),
                         ids=("other-literal", "case-sensitive", "forged-snapshot", "omitted-ref", "foreign-session", "expired", "missing-witness", "same-turn", "completed", "multiple"))
def test_continuation_invalid_answer_cannot_materialize(tmp_path, case):
    runtime, source, pending = _setup(tmp_path)
    try:
        changes = {}
        if case == "other-literal": changes["surface"] = "different"
        if case == "case-sensitive": changes["surface"] = "Velnora"
        if case == "forged-snapshot": changes["obligation_snapshot_ref"] = "snapshot:forged"
        if case == "omitted-ref": changes["obligation_refs"] = ()
        if case == "foreign-session": changes["session_ref"] = "session:foreign"
        if case == "expired": changes["turn_index"] = 6
        if case == "same-turn": changes["turn_index"] = 1
        if case == "completed":
            runtime.stores.obligations.commit(pending.obligation_ref, pending.session_ref, pending.as_dict(), expected_revision=runtime.stores.obligations.revision, resolved=True)
        if case == "multiple":
            values = {f.name: getattr(pending, f.name) for f in fields(pending) if f.name != "obligation_ref"}
            values["source_decision_ref"] = "decision:other"
            other = DialogueObligation.create(**values)
            runtime.stores.obligations.commit(other.obligation_ref, other.session_ref, other.as_dict(), expected_revision=runtime.stores.obligations.revision)
        if case == "missing-witness":
            runtime.stores._backend._conn.execute("DELETE FROM r3_effect_journal")
            runtime.stores._backend._conn.commit()
        meaning, situation = _answer(runtime, source.evaluation.situation, **changes)
        before = (runtime.stores.revision_pin(), runtime.stores.obligations.revision)
        evaluation = R3EvaluationOwner(runtime._authority, runtime.stores, runtime._config).evaluate(meaning, situation)
        assert evaluation.decision.action is DecisionAction.REQUEST_CLARIFICATION
        assert evaluation.learning_drafts == ()
        assert LearningCoordinator(runtime._authority, runtime.stores).materialize(evaluation, meaning, situation) == (None, None)
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
    finally:
        runtime.stores.close()
