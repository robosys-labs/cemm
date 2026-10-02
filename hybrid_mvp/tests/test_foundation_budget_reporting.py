"""Budget failures retain exact evidence and never become semantic rejection."""
from dataclasses import replace
from pathlib import Path
import builtins

import pytest

import cemm_authoritative_hybrid as public_api
from cemm_authoritative_hybrid import bootstrap, cli, persistence
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import (
    CycleStatus,
    PhaseDisposition,
    SemanticPhase,
)
from cemm_authoritative_hybrid.decision import DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.gaps import (
    BudgetExhausted,
    GapKind,
    GapReceipt,
    RepairOwner,
)
from cemm_authoritative_hybrid.persistence import Fact, RevisionPin
from cemm_authoritative_hybrid.proposal import BootstrapProposer
from cemm_authoritative_hybrid.r3_cycle import (
    CYCLE_RESULT_ABI_VERSION,
    CycleFinalizer,
    CycleResult,
)
from cemm_authoritative_hybrid.r3_effects import NoEffectReason, NoEffectReceipt
from cemm_authoritative_hybrid.r3_response import ResponseBuilder
from cemm_authoritative_hybrid.runtime import HybridRuntime

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_budget_reporting.py::test_public_orient_overflow_returns_exact_readonly_terminal[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-orient-overflow-returns-exact-readonly-terminal-memory",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "cd1a850df03315e124c639998d1de4b37d24fa59834c9ccd730faf3ba8d8e8fb",
    },
    "tests/test_foundation_budget_reporting.py::test_public_orient_overflow_returns_exact_readonly_terminal[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-orient-overflow-returns-exact-readonly-terminal-sqlite",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "cd1a850df03315e124c639998d1de4b37d24fa59834c9ccd730faf3ba8d8e8fb",
    },
    "tests/test_foundation_budget_reporting.py::test_orient_budget_terminal_rejects_every_forged_field": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:orient-budget-terminal-rejects-every-forged-field",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "0df173bf184aae5162820a3c52483a8bf955233bd8e7a0f8435cbec45b646ac3",
    },
    "tests/test_foundation_budget_reporting.py::test_orient_catches_only_budget_exhausted": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:orient-catches-only-budget-exhausted",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "9dd7ebb60f34c3bd6432d9e41112c817fa3e707de5c5391b353eaebb4730f996",
    },
    "tests/test_foundation_budget_reporting.py::test_sqlite_orient_overflow_restarts_deterministically_and_preserves_first_turn": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:sqlite-orient-overflow-restarts-deterministically-and-preserves-first-turn",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "3afea511692246ddafcaf92b6346e2f861e8f48f7088ae5503b99f88961e8242",
    },
    "tests/test_foundation_budget_reporting.py::test_cli_emits_orient_budget_terminal_and_continues": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:cli-emits-orient-budget-terminal-and-continues",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "4c0755c484fda69da8609b70eb2f8e79043d0fb4e1edc58f69101d4b28d7c8e3",
    },
    "tests/test_foundation_budget_reporting.py::test_cycle_result_abi4_preserves_canonical_extension_owner": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-cycle-extension-preserves-canonical-cycle-class-owner",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "40c1121f919268f19f2cbb137121a31fe91ce8993c9a511625f33548b4cf13f9",
        "supersedes_node_id": "tests/test_r3_structure.py::test_cycle_extension_preserves_canonical_cycle_class_owner",
    },
    "tests/test_foundation_budget_reporting.py::test_package_exports_active_cycle_result_owner": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:package-exports-active-cycle-result-owner",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "737aeb4166cb8d9fec7971b46cdbf85583914fab577393a46bc7e213765d1d5e",
    },
    "tests/test_foundation_budget_reporting.py::test_public_query_overflow_preserves_budget_through_response_and_restart": {
    "activation_phase": "R3",
    "assertion_ref": "assertion:public-query-overflow-preserves-budget-through-response-and-restart",
    "diagnostic_role": "phase",
    "introduced_by_task": "Foundation-Task-6",
    "source_ast_sha256": "858d2850fc4eb5e210e59c8a8bd6c3863555a7f0fee27488054e884a403b235e"
},
    "tests/test_foundation_budget_reporting.py::test_public_truncated_search_reports_budget_with_exact_evidence": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:gap-matrix-every-cycle-status-is-reachable",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "cc6e21474d508767f237320cb2f7150ba5f1d659fa9bd665ffe21df157170a7d",
        "supersedes_node_id": "tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.BUDGET_EXHAUSTED]"
    },
    "tests/test_foundation_budget_reporting.py::test_budget_terminal_rejects_forged_status_or_gap[status]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:budget-terminal-rejects-forged-status-or-gap-status",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "bd5afd033ff54e9570bf1fb91204a51db74c8fc704d3eca249363f2e86df27f3"
    },
    "tests/test_foundation_budget_reporting.py::test_budget_terminal_rejects_forged_status_or_gap[source]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:budget-terminal-rejects-forged-status-or-gap-source",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "bd5afd033ff54e9570bf1fb91204a51db74c8fc704d3eca249363f2e86df27f3"
    },
    "tests/test_foundation_budget_reporting.py::test_budget_terminal_rejects_forged_status_or_gap[blocker]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:budget-terminal-rejects-forged-status-or-gap-blocker",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "bd5afd033ff54e9570bf1fb91204a51db74c8fc704d3eca249363f2e86df27f3"
    },
    "tests/test_foundation_budget_reporting.py::test_nontruncated_unknown_does_not_claim_budget_exhaustion": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:nontruncated-unknown-does-not-claim-budget-exhaustion",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "99b35ad4def004367448c9629b0a56917eede9822e3f09973e9979f83e0535bd"
    },
    "tests/test_foundation_budget_reporting.py::test_search_exhaustion_before_first_candidate_is_also_budget": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:search-exhaustion-before-first-candidate-is-also-budget",
        "diagnostic_role": "phase",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "e29d13ef554f757fccc901a76d2228b353a8766840676b248ea29effccbba273"
    },
    "tests/test_foundation_budget_reporting.py::test_budget_decision_remains_budget_response_not_acknowledgement": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:budget-decision-remains-budget-response-not-acknowledgement",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "source_ast_sha256": "d0b55b5d6f328b7f9d14fa52d294062c4f4235585ac37733d846ee900fb4f60c",
        "owner_ref": "learning-response"
    }
}


def _load_orient_overflow_runtime(tmp_path, monkeypatch, backend):
    if backend == "memory":
        monkeypatch.setattr(
            bootstrap,
            "open_stores",
            lambda path, **kwargs: persistence.memory_stores(**kwargs),
        )
    runtime = bootstrap.load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path / f"orient-overflow-{backend}",
    )
    runtime.stores.world.commit(
        tuple(
            Fact(
                f"fact:orient-overflow:{index}",
                "op:designation",
                {"role:surface": "crowded", "role:target": f"ref:{index}"},
                proof={"alias_language": "en"},
            )
            for index in range(17)
        ),
        expected_revision=runtime.stores.world.revision,
    )
    return runtime


def _orient_refinalize(result, **changes):
    values = {
        key: getattr(result, key)
        for key in (
            "input_ref",
            "status",
            "orientation",
            "proposal",
            "verification",
            "evaluation",
            "effect_receipt",
            "response_meaning",
            "realization_receipt",
            "gap_receipt",
            "phase_material",
            "final_revision_pin",
        )
    }
    values.update(changes)
    return CycleFinalizer.finalize(
        **values,
        capture_trace=True,
        durations_ns=(0,) * len(values["phase_material"]),
    )


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_public_orient_overflow_returns_exact_readonly_terminal(
    tmp_path, monkeypatch, backend
):
    runtime = _load_orient_overflow_runtime(tmp_path, monkeypatch, backend)
    session_ref = f"session:orient-overflow:{backend}"
    try:
        class UnexpectedDownstream:
            def propose(self, *args, **kwargs):
                raise AssertionError("PROPOSE ran after ORIENT failed")

            def verify_candidates(self, *args, **kwargs):
                raise AssertionError("VERIFY ran after ORIENT failed")

            def run(self, *args, **kwargs):
                raise AssertionError("R3 ran after ORIENT failed")

        unexpected = UnexpectedDownstream()
        runtime._owners["proposal"] = unexpected
        runtime._owners["verification"] = unexpected
        runtime._owners["r3"] = unexpected
        before_pin = runtime.stores.revision_pin()
        before_session = runtime.stores.r3_session_snapshot(session_ref)
        result = runtime.process(session_ref, "crowded", trace=True)

        assert CYCLE_RESULT_ABI_VERSION == result.abi_version == 4
        assert result.status is CycleStatus.BUDGET_EXHAUSTED
        assert result.input_ref == result.phase_material[0].input_refs[0]
        assert result.orientation is result.proposal is result.verification is None
        assert result.evaluation is result.effect_receipt is None
        assert result.response_meaning is result.realization_receipt is None
        assert result.gap_receipt.kind is GapKind.PERFORMANCE
        assert result.gap_receipt.status == "budget_exhausted"
        assert result.gap_receipt.source_refs == (result.input_ref,)
        assert result.gap_receipt.blockers == (
            "budget exhausted: admitted_designations=8",
        )
        assert result.gap_receipt.missing_contract_refs == ()
        assert result.gap_receipt.rejected_candidate_refs == ()
        assert result.gap_receipt.recommended_owner is RepairOwner.RUNTIME
        assert result.gap_receipt.safe_response_action == "bound_cycle"
        assert len(result.phase_material) == len(result.trace) == 1
        material = result.phase_material[0]
        assert material.phase is SemanticPhase.ORIENT
        assert material.output_refs == (result.gap_receipt.gap_ref,)
        assert material.disposition is PhaseDisposition.FAILED
        assert material.rejection_codes == ("orient:budget_exhausted",)
        assert material.budget_use == {"admitted_designations": 8}
        assert material.input_revision_pin == material.output_revision_pin == before_pin
        assert result.final_revision_pin == before_pin
        assert runtime.stores.revision_pin() == before_pin
        assert runtime.stores.r3_session_snapshot(session_ref) == before_session
        assert CycleResult.from_dict(result.as_dict()) == result
    finally:
        runtime.stores.close()


def test_orient_budget_terminal_rejects_every_forged_field(tmp_path, monkeypatch):
    runtime = _load_orient_overflow_runtime(tmp_path, monkeypatch, "memory")
    try:
        result = runtime.process("session:orient-forgery", "crowded")
        material = result.phase_material[0]
        normal_orientation, _ = runtime.orient("session:orient-control", "hello")
        forged_gap = GapReceipt.create(
            kind=result.gap_receipt.kind,
            status=result.gap_receipt.status,
            source_refs=("evidence:forged",),
            blockers=result.gap_receipt.blockers,
            recommended_owner=result.gap_receipt.recommended_owner,
            safe_response_action=result.gap_receipt.safe_response_action,
        )
        for changes in (
            {"status": CycleStatus.UNSUPPORTED},
            {"input_ref": "evidence:forged"},
            {"gap_receipt": forged_gap},
            {"phase_material": (replace(material, output_refs=("gap:forged",)),)},
            {"phase_material": (replace(material, disposition=PhaseDisposition.GAP),)},
            {"phase_material": (replace(material, rejection_codes=("forged",)),)},
            {"phase_material": (replace(material, budget_use={"forged": 8}),)},
            {
                "final_revision_pin": replace(
                    result.final_revision_pin,
                    world_revision=result.final_revision_pin.world_revision + 1,
                )
            },
            {"orientation": normal_orientation},
        ):
            with pytest.raises((TypeError, ValueError)):
                _orient_refinalize(result, **changes)
        predecessor_wire = result.as_dict()
        predecessor_wire["abi_version"] = 3
        with pytest.raises(ValueError, match="unsupported Cycle Result ABI"):
            CycleResult.from_dict(predecessor_wire)
    finally:
        runtime.stores.close()


def test_orient_catches_only_budget_exhausted(tmp_path, monkeypatch):
    runtime = _load_orient_overflow_runtime(tmp_path, monkeypatch, "memory")
    try:
        def programming_defect(session_ref, evidence, *, revision_pin):
            raise RuntimeError("programming defect")

        monkeypatch.setattr(
            runtime._owners["orientation"], "orient_turn", programming_defect
        )
        with pytest.raises(RuntimeError, match="programming defect"):
            runtime.process("session:orient-defect", "hello")
    finally:
        runtime.stores.close()


def test_sqlite_orient_overflow_restarts_deterministically_and_preserves_first_turn(
    tmp_path, monkeypatch
):
    runtime = _load_orient_overflow_runtime(tmp_path, monkeypatch, "sqlite")
    path = tmp_path / "orient-overflow-sqlite"
    session_ref = "session:orient-overflow:restart"
    try:
        first = runtime.process(session_ref, "crowded", trace=True)
        assert runtime.stores.r3_session_snapshot(session_ref)["turn_index"] == 0
    finally:
        runtime.stores.close()

    reopened = bootstrap.load_runtime(ROOT, profile="development", store_path=path)
    try:
        second = reopened.process(session_ref, "crowded", trace=False)
        assert second.cycle_ref == first.cycle_ref
        assert second.trace == ()
        assert reopened.stores.r3_session_snapshot(session_ref)["turn_index"] == 0
        normal = reopened.process(session_ref, "hello")
        assert normal.orientation.turn_ref
        assert reopened.stores.r3_session_snapshot(session_ref)["turn_index"] == 1
    finally:
        reopened.stores.close()


def test_cli_emits_orient_budget_terminal_and_continues(
    tmp_path, monkeypatch, capsys
):
    runtime = _load_orient_overflow_runtime(tmp_path, monkeypatch, "memory")
    answers = iter(("crowded", "hello", "/quit"))
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))
    try:
        cli.interactive(runtime, trace=False)
        output = capsys.readouterr().out
        assert '"status": "budget_exhausted"' in output
        assert output.count('"abi_version": 4') >= 2
        assert runtime.stores.r3_session_snapshot("session:interactive:0")[
            "turn_index"
        ] == 1
    finally:
        runtime.stores.close()


def test_cycle_result_abi4_preserves_canonical_extension_owner() -> None:
    src = ROOT / "src" / "cemm_authoritative_hybrid"
    extension = (src / "r3_cycle.py").read_text(encoding="utf-8")
    predecessor = (src / "cycle.py").read_text(encoding="utf-8")
    assert "class CycleResult" in extension
    assert "class CycleFinalizer" in extension
    assert "CYCLE_RESULT_ABI_VERSION = 4" in extension
    assert "class CycleResult" in predecessor
    assert "class CycleFinalizer" in predecessor
    assert "CYCLE_RESULT_ABI_VERSION = 2" in predecessor


def test_package_exports_active_cycle_result_owner() -> None:
    assert public_api.CycleResult is CycleResult
    assert public_api.CycleFinalizer is CycleFinalizer


@pytest.fixture(scope="module")
def exhausted_cycle(tmp_path_factory):
    original = load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path_factory.mktemp("budget") / "store",
    )
    try:
        # Exercise a genuinely truncated real search.  The release budget now
        # settles this graph after semantic-state deduplication, so a bounded
        # proposer is required to test the budget terminal rather than pinning
        # the assertion to an obsolete performance defect.
        config = replace(original.config, max_beam_states=4, max_applications=4)
        runtime = HybridRuntime(
            original.config,
            original.authority,
            original.stores,
            {**original._owners, "proposal": BootstrapProposer(config)},
            profile="development",
        )
        result = runtime.process("session:budget", "The server is offline. You said goodbye.")
        assert result.proposal.truncated
        assert result.verification.status == "rejected"
        assert all(any(error.code == "proposal_truncated" for error in row.verification_errors)
                   for row in result.verification.candidate_receipts)
        assert runtime.stores.world.revision == 0
        yield result
    finally:
        original.stores.close()


def _refinalize(result, **changes):
    values = {key: getattr(result, key) for key in (
        "input_ref", "status", "orientation", "proposal", "verification", "evaluation",
        "effect_receipt", "response_meaning", "realization_receipt", "gap_receipt",
        "phase_material", "final_revision_pin")}
    values.update(changes)
    return CycleFinalizer.finalize(**values, capture_trace=True,
                                   durations_ns=(0,) * len(values["phase_material"]))


def test_public_truncated_search_reports_budget_with_exact_evidence(exhausted_cycle):
    result = exhausted_cycle
    assert result.status is CycleStatus.BUDGET_EXHAUSTED
    assert result.gap_receipt.kind is GapKind.PERFORMANCE
    assert result.gap_receipt.status == "budget_exhausted"
    assert result.gap_receipt.source_refs == (result.proposal.proposal_ref, result.verification.batch_ref)
    assert result.gap_receipt.blockers == ("proposal:budget_exhausted",)
    assert result.gap_receipt.recommended_owner is RepairOwner.RUNTIME
    assert result.evaluation is result.effect_receipt is result.response_meaning is None
    assert CycleResult.from_dict(result.as_dict()) == result


@pytest.mark.parametrize("corruption", ("status", "source", "blocker"),
                         ids=("status", "source", "blocker"))
def test_budget_terminal_rejects_forged_status_or_gap(exhausted_cycle, corruption):
    result = exhausted_cycle
    if corruption == "status":
        changes = {"status": CycleStatus.UNSUPPORTED}
    else:
        payload = {key: getattr(result.gap_receipt, key) for key in (
            "kind", "status", "source_refs", "blockers", "missing_contract_refs",
            "rejected_candidate_refs", "recommended_owner", "safe_response_action")}
        payload["source_refs" if corruption == "source" else "blockers"] = ("forged:budget",)
        changes = {"gap_receipt": GapReceipt.create(**payload)}
    with pytest.raises(ValueError):
        _refinalize(result, **changes)


def test_nontruncated_unknown_does_not_claim_budget_exhaustion(tmp_path):
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        result = runtime.process("session:unknown", "zorbulate")
        assert not result.proposal.truncated
        assert result.status is CycleStatus.UNSUPPORTED
        assert result.gap_receipt.kind is not GapKind.PERFORMANCE
        with pytest.raises(ValueError):
            _refinalize(result, status=CycleStatus.BUDGET_EXHAUSTED)
    finally:
        runtime.stores.close()


def test_search_exhaustion_before_first_candidate_is_also_budget(tmp_path):
    original = load_runtime(ROOT, profile="development", store_path=tmp_path / "store")
    try:
        # Exercise the real proposer with a smaller search budget, not a fabricated receipt.
        config = replace(original.config, max_beam_states=1, max_applications=1)
        owners = {**original._owners, "proposal": BootstrapProposer(config)}
        runtime = HybridRuntime(original.config, original.authority, original.stores,
                                owners, profile="development")
        result = runtime.process("session:small-budget", "Alice likes Bob.")
        assert result.proposal.truncated and result.proposal.candidates == ()
        assert result.verification.status == "abstained"
        assert result.status is CycleStatus.BUDGET_EXHAUSTED
        assert result.gap_receipt.source_refs == (result.proposal.proposal_ref, result.verification.batch_ref)
        assert result.gap_receipt.rejected_candidate_refs == ()
        assert CycleResult.from_dict(result.as_dict()) == result
        assert runtime.stores.world.revision == 0
    finally:
        original.stores.close()


def test_budget_decision_remains_budget_response_not_acknowledgement():
    pin = RevisionPin("authority:test", 0, 0, 0, 0, "model:test")
    receipt = NoEffectReceipt.create(reason=NoEffectReason.UNKNOWN,
        idempotency_key="effect:test", journal_origin_ref="journal:origin",
        journal_preterminal_ref="journal:planned", decision_ref="decision:test",
        verified_meaning_ref="meaning:test", expression_ref="expression:test",
        situation_ref="situation:test", program_ref="program:test",
        learning_plan_ref=None, source_obligation_ref=None, proof_refs=(),
        blocker_refs=("query:budget_exhausted",), input_revision_pin=pin,
        output_revision_pin=replace(pin, effect_revision=1))
    assert ResponseBuilder._status(DecisionStatus.BUDGET_EXHAUSTED, receipt) is CycleStatus.BUDGET_EXHAUSTED
    assert ResponseBuilder._discourse(DecisionStatus.BUDGET_EXHAUSTED, DecisionAction.NO_OP, receipt) == "report_gap"


def test_public_query_overflow_preserves_budget_through_response_and_restart(tmp_path):
    path = tmp_path / "store"
    runtime = load_runtime(ROOT, profile="development", store_path=path)
    try:
        runtime.stores.world.commit(tuple(Fact(f"fact:budget-{index}", "op:relation",
            {"predicate_ref": "rel:likes", "role:subject": "entity:alice", "role:object": "entity:bob"})
            for index in range(257)), expected_revision=0)
    finally:
        runtime.stores.close()
    reopened = load_runtime(ROOT, profile="development", store_path=path)
    try:
        result = reopened.process("session:query-budget", "Alice likes Bob?")
        assert result.verification.status == "selected" and not result.proposal.truncated
        decision = result.evaluation.decision
        assert decision.status is DecisionStatus.BUDGET_EXHAUSTED
        assert decision.action is DecisionAction.NO_OP
        assert decision.bindings == decision.proof_refs == ()
        assert decision.answer_expression_ref is None
        assert type(result.effect_receipt) is NoEffectReceipt
        assert result.status is CycleStatus.BUDGET_EXHAUSTED
        assert result.response_meaning.cycle_status is result.status
        assert result.response_meaning.epistemic_status_ref == "epistemic_status:unknown"
        assert result.response_meaning.discourse_action == "report_gap"
        assert reopened.stores.world.revision == 1
        assert CycleResult.from_dict(result.as_dict()) == result
    finally:
        reopened.stores.close()
