"""Independent genuine projection QUERY and evaluation-lineage contracts."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.decision import Decision, DecisionAction, DecisionStatus
from cemm_authoritative_hybrid.descriptions import DescriptionRequest
from cemm_authoritative_hybrid.expression_projection import project_expression
from cemm_authoritative_hybrid.expressions import SemanticExpression, ScopeOperator
from cemm_authoritative_hybrid.r3_artifacts import EvaluationBundle, QueryResult, QueryStatus
from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
from tests.test_foundation_description_builder import (
    _description_expression, _seed_reviewed_generic_claim, _stores,
)
from tests.test_foundation_description_request_lineage import _query_expression, _situation


def _authority(stores):
    return SimpleNamespace(generation=stores.revision_pin().authority_generation,
        content_hash="authority-content:description-test", atoms={}, capabilities={}, rules={})


def _evaluate(stores, expression=None, *, owner=None, situation=None):
    expression = expression or _query_expression()
    situation = situation or _situation(stores.revision_pin())
    owner = owner or QueryDecisionOwner(stores, RuntimeConfig.release(), _authority(stores))
    return owner.evaluate_full(expression, project_expression(expression), situation)


def _decision(expression, situation, contribution):
    material = Decision._material(verified_meaning_ref="verified_meaning:test",
        expression_ref=expression.expression_ref, program_ref="program:test",
        situation=situation, contribution=contribution, revision_pin=situation.revision_pin)
    return Decision.from_dict({"decision_ref": stable_ref("decision", material), **material})


def _evaluation(expression, situation, mode):
    return EvaluationBundle.create(decision=_decision(expression, situation, mode.contribution),
        expression=expression, situation=situation, mode_evaluation=mode,
        revision_pin=situation.revision_pin)


@pytest.mark.parametrize("backend,stances,status", (
    ("memory", ("support",), "supported"), ("sqlite", ("support",), "supported"),
    ("memory", ("deny",), "supported"), ("sqlite", ("deny",), "supported"),
    ("memory", ("support", "deny"), "conflict"), ("sqlite", ("support", "deny"), "conflict"),
    ("memory", (), "unknown"), ("sqlite", (), "unknown"),
), ids=("positive-memory", "positive-sqlite", "deny-memory", "deny-sqlite",
    "conflict-memory", "conflict-sqlite", "missing-memory", "missing-sqlite"))
def test_projection_query_carries_genuine_signed_result(tmp_path, backend, stances, status):
    stores = _stores(backend, tmp_path)
    try:
        claims = tuple(_seed_reviewed_generic_claim(stores, _description_expression(),
            stance=stance, fact_ref=f"fact:projection-{index}",
            decision_ref=f"decision:projection-{index}", occurrence_ref=f"occurrence:projection-{index}")
            for index, stance in enumerate(stances))
        before = stores.revisions()
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        mode = _evaluate(stores, expression, situation=situation)
        result = mode.query_results[0]
        assert result.result_kind == "projection"
        assert result.abi_version == 3
        assert result.status.value == status
        assert result.proof is None and result.bindings == ()
        proof = result.description_proof
        assert proof.description.request.source_expression_ref == expression.expression_ref
        assert proof.description.request.source_situation_ref == situation.situation_ref
        assert proof.revision_pin == result.revision_pin == situation.revision_pin
        assert {claim.claim_ref for claim in proof.claims} == {claim.claim_ref for claim in claims}
        assert tuple(sorted(claim.stance for claim in proof.claims)) == tuple(sorted(stances))
        assert mode.contribution.proof_refs == (proof.proof_bundle_ref,)
        assert mode.contribution.source_refs == proof.description.source_refs
        assert mode.contribution.query_result_refs == (result.query_result_ref,)
        assert mode.contribution.action is (DecisionAction.ANSWER if status == "supported" else DecisionAction.REQUEST_CLARIFICATION)
        assert mode.contribution.answer_expression_ref == (proof.answer_expression_ref if status == "supported" else None)
        bundle = _evaluation(expression, situation, mode)
        assert EvaluationBundle.from_dict(bundle.as_dict()) == bundle
        assert QueryResult.from_dict(result.as_dict()) == result
        assert result == _evaluate(stores, expression, situation=situation).query_results[0]
        assert stores.revisions() == before
        assert result.query_result_ref not in str(proof.as_dict())
    finally:
        stores.close()


@pytest.mark.parametrize("requested", ("description", "definition"), ids=("description", "definition"))
def test_projection_query_uses_one_read_without_rule_refresh(tmp_path, monkeypatch, requested):
    from contextlib import contextmanager
    from cemm_authoritative_hybrid import r3_cognition
    stores = _stores("memory", tmp_path)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        expression = _query_expression(requested=requested)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), _authority(stores))
        snapshots, postings = [], []
        original_snapshot, original_target = stores.r3_read_snapshot, r3_cognition.active_application_claims_for_target
        @contextmanager
        def snapshot(pin):
            snapshots.append(pin)
            with original_snapshot(pin):
                yield
        def target(*args, **kwargs):
            postings.append((args[1], kwargs["expected_pin"]))
            return original_target(*args, **kwargs)
        def forbidden(*args, **kwargs):
            raise AssertionError("projection query must bypass ordinary rule closure and index refresh")
        monkeypatch.setattr(stores, "r3_read_snapshot", snapshot)
        monkeypatch.setattr(r3_cognition, "active_application_claims_for_target", target)
        monkeypatch.setattr(owner, "_refresh_rule_index", forbidden)
        monkeypatch.setattr(owner, "_relevant_evidence", forbidden)
        result = _evaluate(stores, expression, owner=owner).query_results[0]
        pin = stores.revision_pin()
        assert snapshots == [pin]
        assert postings == ([] if requested == "definition" else [("entity:alice", pin)])
        assert result.status is (QueryStatus.UNKNOWN if requested == "definition" else QueryStatus.SUPPORTED)
        assert result.description_proof is not None
    finally:
        stores.close()


@pytest.mark.parametrize("invalid", ("mixed", "compound", "unresolved", "scoped", "observe", "request", "simulate"),
    ids=("mixed", "compound", "unresolved", "scoped", "observe", "request", "simulate"))
def test_projection_query_rejects_unsupported_source_before_reads(tmp_path, monkeypatch, invalid):
    stores = _stores("memory", tmp_path)
    try:
        expression = _query_expression()
        if invalid == "mixed":
            app = _description_expression().applications[0]
            expression = SemanticExpression.create(applications=(app,),
                root_refs=(app.application_ref, expression.root_refs[0]), query_projections=expression.query_projections)
        if invalid == "compound":
            from cemm_authoritative_hybrid.expressions import ExpressionLink
            app = _description_expression().applications[0]
            link = ExpressionLink("link:compound", "link:conjunction", (app.application_ref, expression.root_refs[0]))
            expression = SemanticExpression.create(applications=(app,), root_refs=(link.link_ref,),
                expression_links=(link,), query_projections=expression.query_projections)
        if invalid == "unresolved":
            from cemm_authoritative_hybrid.expressions import GroundedReference, RoleBinding, SemanticApplication, UnresolvedFiller, UnresolvedValue
            app = SemanticApplication("application:unresolved", "op:type", "concept:mother", (
                RoleBinding("role:instance", UnresolvedValue("unresolved:instance")),
                RoleBinding("role:class", GroundedReference("concept:mother"))))
            residual = UnresolvedFiller("unresolved:instance", app.application_ref, "role:instance", "anchor", ("entity",), True)
            expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref, expression.root_refs[0]),
                unresolved_fillers=(residual,), query_projections=expression.query_projections)
        if invalid == "scoped":
            scope = ScopeOperator("scope:request", "scope:polarity", "value:negative", expression.root_refs[0])
            expression = SemanticExpression.create(applications=(), root_refs=(scope.scope_ref,),
                scope_operators=(scope,), query_projections=expression.query_projections)
        mode = SemanticMode[invalid.upper()] if invalid in {"observe", "request", "simulate"} else SemanticMode.QUERY
        situation = _situation(stores.revision_pin(), mode=mode,
            epistemic_scope_ref={SemanticMode.OBSERVE: "epistemic_scope:observed",
                SemanticMode.REQUEST: "epistemic_scope:requested", SemanticMode.SIMULATE: "epistemic_scope:simulated",
                SemanticMode.QUERY: "epistemic_scope:query"}[mode])
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), _authority(stores))
        def forbidden(*args, **kwargs):
            raise AssertionError("invalid projection source must fail before a store snapshot")
        monkeypatch.setattr(stores, "r3_read_snapshot", forbidden)
        with pytest.raises((ValueError, TypeError)):
            _evaluate(stores, expression, owner=owner, situation=situation)
    finally:
        stores.close()


def _rehash(wire, field, namespace):
    wire[field] = stable_ref(namespace, {key: value for key, value in wire.items() if key != field})
    return wire


@pytest.mark.parametrize("corruption", ("query-refs", "query-source", "query-pin", "request-target",
    "request-content", "request-projection", "request-situation", "answer", "proof", "sources", "bindings", "status"),
    ids=("query-refs", "query-source", "query-pin", "request-target", "request-content", "request-projection",
        "request-situation", "answer", "proof", "sources", "bindings", "status"))
def test_projection_evaluation_rejects_canonical_crossbindings(tmp_path, corruption):
    from cemm_authoritative_hybrid.persistence import RevisionPin
    stores = _stores("memory", tmp_path)
    try:
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        mode = _evaluate(stores, expression, situation=situation)
        result, contribution = mode.query_results[0], mode.contribution
        if corruption.startswith("request-"):
            wire = result.as_dict()
            proof = wire["description_proof"]
            description = proof["description"]
            request = description["request"]
            field, value = {
                "request-target": ("target_ref", "entity:bob"),
                "request-content": ("requested_content", "definition"),
                "request-projection": ("source_projection_ref", "projection:foreign"),
                "request-situation": ("source_situation_ref", _situation(situation.revision_pin, turn_ref="turn:other").situation_ref),
            }[corruption]
            request[field] = value
            _rehash(request, "description_request_ref", "description_request")
            _rehash(description, "description_result_ref", "description_result")
            _rehash(proof, "proof_bundle_ref", "proof_bundle")
            result = QueryResult.from_dict(_rehash(wire, "query_result_ref", "r3_query_result"))
            contribution = replace(contribution, query_result_refs=(result.query_result_ref,),
                proof_refs=(result.description_proof.proof_bundle_ref,))
        elif corruption == "query-source":
            # A structurally genuine result from another exact request is not
            # evidence for the expression included in this evaluation.
            result = _evaluate(stores, _query_expression("entity:bob"), situation=situation).query_results[0]
            contribution = replace(contribution, query_result_refs=(result.query_result_ref,),
                proof_refs=(result.description_proof.proof_bundle_ref,))
        elif corruption == "query-pin":
            pin = RevisionPin(situation.revision_pin.authority_generation, 0, 1, 0, 0, None)
            other = _situation(pin)
            from cemm_authoritative_hybrid.descriptions import DescriptionCompleteness, DescriptionResult
            from cemm_authoritative_hybrid.proof_bundle import ProofBundle
            request = DescriptionRequest.create(source_expression=expression, situation=other, max_depth=1, max_facts=1)
            description = DescriptionResult.create(request=request, answer_expression=None,
                completeness=DescriptionCompleteness.MISSING, fact_refs=(), definition_refs=(), claim_refs=(),
                source_refs=(), proof_refs=(), revision_pin=pin)
            proof = ProofBundle.create(description=description, application_refs=(), claims=(), revision_pin=pin)
            result = QueryResult.create(expression_ref=expression.expression_ref, result_kind="projection",
                status=QueryStatus.UNKNOWN, proof=None, description_proof=proof, bindings=(), retrieval_refs=(), rounds=1, revision_pin=pin)
            contribution = replace(contribution, query_result_refs=(result.query_result_ref,), proof_refs=(proof.proof_bundle_ref,))
        else:
            changes = {
                "query-refs": {"query_result_refs": ("r3_query_result:foreign",)},
                "answer": {"answer_expression_ref": _description_expression().expression_ref},
                "proof": {"proof_refs": ("proof_bundle:foreign",)},
                "sources": {"source_refs": ("source:foreign",)},
                "bindings": {"bindings": (("?foreign", "entity:alice"),)},
                "status": {"status": DecisionStatus.PARTIAL},
            }[corruption]
            contribution = replace(contribution, **changes)
        forged = replace(mode, contribution=contribution, query_results=(result,))
        with pytest.raises(ValueError, match="query|projection|source|pin|answer|proof|status|bindings"):
            _evaluation(expression, situation, forged)
    finally:
        stores.close()


@pytest.mark.parametrize("corruption", ("empty", "proposition", "other-artifacts"),
    ids=("empty", "proposition", "other-artifacts"))
def test_projection_evaluation_requires_sole_projection_result(tmp_path, corruption):
    from cemm_authoritative_hybrid.r3_artifacts import ClaimOccurrence, PlacementMode
    stores = _stores("memory", tmp_path)
    try:
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        mode = _evaluate(stores, expression, situation=situation)
        if corruption == "empty":
            mode = replace(mode, query_results=(), contribution=replace(mode.contribution, query_result_refs=()))
        elif corruption == "proposition":
            result = QueryResult.create(expression_ref=expression.expression_ref, status=QueryStatus.UNKNOWN,
                proof=None, bindings=(), retrieval_refs=(), rounds=1, revision_pin=situation.revision_pin)
            mode = replace(mode, query_results=(result,), contribution=replace(mode.contribution, query_result_refs=(result.query_result_ref,)))
        else:
            claim = ClaimOccurrence.create(expression_ref=expression.expression_ref, root_ref=expression.root_refs[0],
                source_ref="source:unrelated", evidence_refs=(), interval_ref="interval:test", confidence_q=1,
                modality_ref="modality:test", scope_ref="scope:test", placement=PlacementMode.OBSERVED,
                situation_ref=situation.situation_ref, supersedes_ref=None, revision_pin=situation.revision_pin)
            mode = replace(mode, claim_occurrences=(claim,))
        with pytest.raises(ValueError, match="projection|query|unrelated"):
            _evaluation(expression, situation, mode)
    finally:
        stores.close()


@pytest.mark.parametrize("backend,overflow", (
    ("memory", "facts"), ("sqlite", "facts"), ("memory", "proofs"), ("sqlite", "proofs"),
    ("memory", "roots"), ("sqlite", "roots"),
), ids=("facts-memory", "facts-sqlite", "proofs-memory", "proofs-sqlite", "roots-memory", "roots-sqlite"))
def test_projection_budget_keeps_signed_empty_terminal(tmp_path, backend, overflow):
    stores = _stores(backend, tmp_path)
    try:
        from cemm_authoritative_hybrid.expressions import GroundedReference, RoleBinding, SemanticApplication
        for index in range(9 if overflow == "roots" else 2 if overflow == "facts" else 1):
            expression = _description_expression()
            if overflow == "roots":
                app = SemanticApplication("application:root", "op:relation", "relation:attribute", (
                    RoleBinding("role:subject", GroundedReference("entity:alice")),
                    RoleBinding("role:object", GroundedReference(f"entity:other-{index}"))))
                expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
            _seed_reviewed_generic_claim(stores, expression, fact_ref=f"fact:budget-{index}",
                decision_ref=f"decision:budget-{index}", occurrence_ref=f"occurrence:budget-{index}",
                proof_refs=("proof:repeated",) * 65 if overflow == "proofs" else ("proof:normal",))
        config = replace(RuntimeConfig.release(), max_inference_facts=1) if overflow == "facts" else RuntimeConfig.release()
        owner = QueryDecisionOwner(stores, config, _authority(stores))
        before = stores.revisions()
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        mode = _evaluate(stores, expression, owner=owner, situation=situation)
        result = mode.query_results[0]
        assert result.status is QueryStatus.BUDGET_EXHAUSTED
        assert mode.contribution.status is DecisionStatus.BUDGET_EXHAUSTED
        assert mode.contribution.action is DecisionAction.NO_OP
        assert mode.contribution.answer_expression_ref is None
        assert result.description_proof.claims == result.description_proof.applications == ()
        assert result.description_proof.description.fact_refs == result.retrieval_refs == ()
        assert mode.contribution.proof_refs == (result.description_proof.proof_bundle_ref,)
        assert EvaluationBundle.from_dict(_evaluation(expression, situation, mode).as_dict()).query_results == (result,)
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("corruption", ("abi2", "missing-fields", "status", "field-name", "kind", "pin",
    "list", "dict", "nested-string", "nested-list"),
    ids=("abi2", "missing-fields", "status", "field-name", "kind", "pin", "list", "dict", "nested-string", "nested-list"))
def test_projection_query_codec_hardcuts_and_rejects_subclasses(tmp_path, corruption):
    class WireString(str):
        pass
    class WireDict(dict):
        pass
    class WireList(list):
        pass
    stores = _stores("memory", tmp_path)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        wire = _evaluate(stores).query_results[0].as_dict()
        if corruption == "abi2":
            wire["abi_version"] = 2
        elif corruption == "missing-fields":
            del wire["description_proof"]
            del wire["result_kind"]
        elif corruption == "status":
            wire["status"] = WireString(wire["status"])
        elif corruption == "field-name":
            wire[WireString("rounds")] = wire.pop("rounds")
        elif corruption == "kind":
            wire["result_kind"] = WireString(wire["result_kind"])
        elif corruption == "pin":
            wire["revision_pin"] = WireDict(wire["revision_pin"])
        elif corruption == "list":
            wire["bindings"] = WireList(wire["bindings"])
        elif corruption == "dict":
            wire = WireDict(wire)
        elif corruption == "nested-string":
            wire["description_proof"]["claims"][0]["stance"] = WireString("support")
        else:
            wire["description_proof"]["claims"][0]["proof_refs"] = WireList(["proof:reviewed-definition"])
        with pytest.raises((ValueError, TypeError)):
            QueryResult.from_dict(wire)
    finally:
        stores.close()


@pytest.mark.parametrize("invalid", ("unsigned", "contradicted", "bindings", "source", "pin", "proposition-proof"),
    ids=("unsigned", "contradicted", "bindings", "source", "pin", "proposition-proof"))
def test_projection_query_api_rejects_invalid_contract(tmp_path, invalid):
    from cemm_authoritative_hybrid.persistence import RevisionPin
    stores = _stores("memory", tmp_path)
    try:
        result = _evaluate(stores).query_results[0]
        values = dict(expression_ref=result.expression_ref, status=result.status, bindings=(), proof=None,
            retrieval_refs=(), rounds=1, revision_pin=result.revision_pin, result_kind="projection",
            description_proof=result.description_proof)
        changes = {
            "unsigned": {"description_proof": None}, "contradicted": {"status": QueryStatus.CONTRADICTED},
            "bindings": {"bindings": (("?variable", "entity:alice"),)},
            "source": {"expression_ref": _query_expression("entity:bob").expression_ref},
            "pin": {"revision_pin": RevisionPin(result.revision_pin.authority_generation, 0, 1, 0, 0, None)},
            "proposition-proof": {"result_kind": "proposition"},
        }[invalid]
        with pytest.raises((ValueError, TypeError)):
            QueryResult.create(**{**values, **changes})
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_projection_query_maximum_ordered_proof_detaches_wire(tmp_path, backend):
    stores = _stores(backend, tmp_path)
    try:
        proofs = ("proof:z", "proof:a") * 32
        for index in range(64):
            _seed_reviewed_generic_claim(stores, _description_expression(), fact_ref=f"fact:maximum-{index}",
                source_ref=f"source:maximum-{index}", decision_ref=f"decision:maximum-{index}",
                occurrence_ref=f"occurrence:maximum-{index}", proof_refs=proofs)
        result = _evaluate(stores).query_results[0]
        assert result.status is QueryStatus.SUPPORTED
        assert len(result.description_proof.claims) == 64
        assert all(claim.proof_refs == proofs for claim in result.description_proof.claims)
        assert sum(len(claim.proof_refs) for claim in result.description_proof.claims) == 4096
        wire = result.as_dict()
        decoded = QueryResult.from_dict(wire)
        assert decoded == result
        wire["description_proof"]["claims"][0]["proof_refs"].append("proof:foreign")
        assert decoded.as_dict() == result.as_dict()
        assert len(decoded.description_proof.claims[0].proof_refs) == 64
    finally:
        stores.close()


def test_projection_query_partial_signed_codec_preserves_clarification(tmp_path):
    stores = _stores("memory", tmp_path)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        mode = _evaluate(stores, expression, situation=situation)
        wire = mode.query_results[0].as_dict()
        # PARTIAL is a codec/evaluation contract, not an invented store policy:
        # retain real authenticated evidence and change only typed completeness.
        description = wire["description_proof"]["description"]
        description["completeness"] = "partial"
        _rehash(description, "description_result_ref", "description_result")
        _rehash(wire["description_proof"], "proof_bundle_ref", "proof_bundle")
        wire["status"] = "partial"
        result = QueryResult.from_dict(_rehash(wire, "query_result_ref", "r3_query_result"))
        contribution = replace(mode.contribution, status=DecisionStatus.PARTIAL,
            action=DecisionAction.REQUEST_CLARIFICATION, answer_expression_ref=None,
            query_result_refs=(result.query_result_ref,), proof_refs=(result.description_proof.proof_bundle_ref,),
            blocker_refs=("query:partial",))
        partial = replace(mode, query_results=(result,), contribution=contribution)
        assert _evaluation(expression, situation, partial).decision.answer_expression_ref is None
        assert result.description_proof.answer_expression_ref is not None
    finally:
        stores.close()


@pytest.mark.parametrize("timing,field", (("before", "content_hash"), ("during", "content_hash"),
    ("before", "rules"), ("during", "rules"), ("before", "object"), ("during", "object")),
    ids=("before-hash", "during-hash", "before-rules", "during-rules", "before-object", "during-object"))
def test_projection_query_preserves_activation_identity_guards(tmp_path, monkeypatch, timing, field):
    from cemm_authoritative_hybrid.persistence import StaleRevisionError
    stores = _stores("memory", tmp_path)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        authority = _authority(stores)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        cache_state = owner._rule_cache_state
        def change():
            if field == "object":
                owner._authority = SimpleNamespace(**vars(authority))
            else:
                setattr(authority, field, {} if field == "rules" else "authority-content:foreign")
        if timing == "before":
            change()
        else:
            original = owner._description_at_pin
            def read_then_change(request):
                result = original(request)
                change()
                return result
            monkeypatch.setattr(owner, "_description_at_pin", read_then_change)
        with pytest.raises(StaleRevisionError, match="authority"):
            _evaluate(stores, owner=owner)
        assert owner._rule_cache_state is cache_state
    finally:
        stores.close()


@pytest.mark.parametrize("timing", ("before", "during"), ids=("before", "during"))
def test_projection_query_rejects_linked_snapshot_identity_drift(linked_authority, monkeypatch, timing):
    from cemm_authoritative_hybrid.persistence import memory_stores, StaleRevisionError
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        def change():
            generation, content_hash, rules = linked_authority.rule_generation_snapshot()
            object.__setattr__(linked_authority, "_rule_generation_state", (generation, content_hash, rules))
        if timing == "before":
            change()
        else:
            original = owner._description_at_pin
            def read_then_change(request):
                result = original(request)
                change()
                return result
            monkeypatch.setattr(owner, "_description_at_pin", read_then_change)
        with pytest.raises(StaleRevisionError, match="authority"):
            _evaluate(stores, owner=owner)
    finally:
        stores.close()


def test_projection_query_accepts_fresh_generation_without_rule_scan(linked_authority, monkeypatch):
    from cemm_authoritative_hybrid.persistence import memory_stores
    generation = "authority:projection-rollover"
    stores = memory_stores(authority_generation=generation)
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        activated_cache = owner._rule_cache_state
        linked_authority._publish_rule_generation(parent_generation=linked_authority.generation,
            new_generation=generation, new_content_hash="authority-content:projection-rollover", rules=linked_authority.rules)
        def forbidden(*args, **kwargs):
            raise AssertionError("projection rollover must not rebuild ordinary rule indexes")
        monkeypatch.setattr(owner, "_refresh_rule_index", forbidden)
        result = _evaluate(stores, owner=owner).query_results[0]
        assert result.revision_pin.authority_generation == generation
        assert result.status is QueryStatus.UNKNOWN
        assert owner._rule_cache_state is activated_cache
    finally:
        stores.close()


def test_projection_query_sqlite_restart_is_read_only(tmp_path):
    from cemm_authoritative_hybrid.persistence import open_stores
    stores = _stores("sqlite", tmp_path)
    _seed_reviewed_generic_claim(stores, _description_expression(), stance="deny", proof_refs=("proof:z", "proof:a", "proof:z"))
    before = stores.revision_pin()
    expression, situation = _query_expression(), _situation(before)
    first = _evaluation(expression, situation, _evaluate(stores, expression, situation=situation))
    stores.close()
    stores = open_stores(tmp_path / "description-store", authority_generation=before.authority_generation)
    try:
        second = _evaluation(expression, situation, _evaluate(stores, expression, situation=situation))
        assert first == second
        assert second.query_results[0].description_proof.claims[0].proof_refs == ("proof:z", "proof:a", "proof:z")
        assert stores.revision_pin() == before
    finally:
        stores.close()


@pytest.mark.parametrize("mode", (SemanticMode.OBSERVE, SemanticMode.REQUEST, SemanticMode.SIMULATE),
    ids=("observe", "request", "simulate"))
def test_r3_evaluation_rejects_projection_in_nonquery_mode(tmp_path, monkeypatch, mode):
    from cemm_authoritative_hybrid.expressions import VerifiedMeaning
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    stores = _stores("memory", tmp_path)
    try:
        expression, pin = _query_expression(), stores.revision_pin()
        meaning = VerifiedMeaning.create(program_ref="program:query", expression=expression,
            grounding_refs=("grounding:target",), coverage_receipt_ref="coverage:test",
            compilation_proof_ref="compilation_proof:test", verification_receipt_ref="verification_receipt:test",
            revision_pin=pin)
        situation = _situation(pin, mode=mode, epistemic_scope_ref={SemanticMode.OBSERVE: "epistemic_scope:observed",
            SemanticMode.REQUEST: "epistemic_scope:requested", SemanticMode.SIMULATE: "epistemic_scope:simulated"}[mode])
        owner = R3EvaluationOwner(_authority(stores), stores, RuntimeConfig.release())
        def forbidden(*args, **kwargs):
            raise AssertionError("nonquery projection cannot reach a mode owner")
        monkeypatch.setattr(owner._owners[mode], "evaluate_full", forbidden)
        with pytest.raises(ValueError, match="QUERY"):
            owner.evaluate_mode(meaning, situation)
    finally:
        stores.close()


def test_r3_projection_finalize_uses_exact_bundle_boundary(tmp_path, linked_authority):
    from cemm_authoritative_hybrid.expressions import VerifiedMeaning
    from cemm_authoritative_hybrid.r3_cognition import R3EvaluationOwner
    from cemm_authoritative_hybrid.persistence import memory_stores
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        meaning = VerifiedMeaning.create(program_ref="program:query", expression=expression,
            grounding_refs=("grounding:target",), coverage_receipt_ref="coverage:test",
            compilation_proof_ref="compilation_proof:test", verification_receipt_ref="verification_receipt:test",
            revision_pin=situation.revision_pin)
        owner = R3EvaluationOwner(linked_authority, stores, RuntimeConfig.release())
        evaluation = owner.evaluate(meaning, situation)
        assert evaluation.decision.answer_expression_ref == evaluation.query_results[0].description_proof.answer_expression_ref
        mode = owner.evaluate_mode(meaning, situation)
        with pytest.raises(ValueError, match="answer"):
            owner.finalize(meaning, situation, mode, replace(mode.contribution, answer_expression_ref=_description_expression("entity:bob").expression_ref), authority=linked_authority)
        wire = evaluation.as_dict()
        wire["decision"]["proof_refs"] = ["proof_bundle:foreign"]
        _rehash(wire["decision"], "decision_ref", "decision")
        _rehash(wire, "evaluation_ref", "r3_evaluation")
        with pytest.raises(ValueError, match="proof"):
            EvaluationBundle.from_dict(wire)
    finally:
        stores.close()


@pytest.mark.parametrize("field", ("retrieval_refs", "bindings", "status"),
    ids=("retrieval-refs", "bindings", "status"))
def test_query_codec_rejects_cycles_at_typed_field_boundary(field):
    import os
    import subprocess
    import sys
    script = """
from cemm_authoritative_hybrid.r3_artifacts import QueryResult, QueryStatus
from cemm_authoritative_hybrid.persistence import RevisionPin
wire = QueryResult.create(expression_ref='expression:cycle', status=QueryStatus.UNKNOWN,
    proof=None, bindings=(), retrieval_refs=(), rounds=1,
    revision_pin=RevisionPin('authority:cycle', 0, 0, 0, 0, None)).as_dict()
wire[FIELD] = [wire]
try:
    QueryResult.from_dict(wire)
except (ValueError, TypeError):
    pass
else:
    raise AssertionError('cyclic wire must fail closed')
""".replace("FIELD", repr(field))
    completed = subprocess.run([sys.executable, "-c", script], env=os.environ.copy(),
        capture_output=True, text=True, timeout=3)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("corruption", ("field-name", "scalar", "list", "dict"),
    ids=("field-name", "scalar", "list", "dict"))
def test_proposition_query_codec_preserves_nested_strict_wire(tmp_path, corruption):
    class WireString(str):
        pass
    class WireDict(dict):
        pass
    class WireList(list):
        pass
    stores = _stores("memory", tmp_path)
    try:
        expression = _description_expression()
        _seed_reviewed_generic_claim(stores, expression)
        result = _evaluate(stores, expression).query_results[0]
        assert result.result_kind == "proposition" and result.description_proof is None
        assert result.status is QueryStatus.SUPPORTED
        wire = result.as_dict()
        node = wire["proof"]["nodes"][0]
        if corruption == "field-name":
            node[WireString("proof_node_ref")] = node.pop("proof_node_ref")
        elif corruption == "scalar":
            node["proof_node_ref"] = WireString(node["proof_node_ref"])
        elif corruption == "list":
            node["premise_node_refs"] = WireList(node["premise_node_refs"])
        else:
            wire["proof"]["nodes"][0] = WireDict(node)
        with pytest.raises(TypeError):
            QueryResult.from_dict(wire)
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_projection_query_authenticates_nonfocused_postings_before_filter(tmp_path, backend):
    from dataclasses import replace
    from tests.test_foundation_description_builder import _physically_replace_fact
    stores = _stores(backend, tmp_path)
    try:
        seed = _seed_reviewed_generic_claim(stores, _description_expression())
        expression = _query_expression("concept:mother")
        assert _evaluate(stores, expression).query_results[0].status is QueryStatus.UNKNOWN
        fact = stores.world.get(seed.claim_payload["fact_ref"])
        _physically_replace_fact(stores, backend, replace(fact, proof={**fact.proof, "source": "source:foreign"}))
        before = stores.revisions()
        with pytest.raises(ValueError, match="lineage|fact|proof"):
            _evaluate(stores, expression)
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("field", ("retrieval_refs", "bindings"), ids=("retrieval-refs", "bindings"))
def test_query_codec_rejects_overlong_rows_before_child_iteration(field):
    from cemm_authoritative_hybrid.persistence import RevisionPin
    wire = QueryResult.create(expression_ref="expression:overlong", status=QueryStatus.UNKNOWN,
        proof=None, bindings=(), retrieval_refs=(), rounds=1,
        revision_pin=RevisionPin("authority:overlong", 0, 0, 0, 0, None)).as_dict()
    wire[field] = [wire] * 513
    with pytest.raises(ValueError, match="row bound"):
        QueryResult.from_dict(wire)


@pytest.mark.parametrize("entry,level,version,rehashed", (
    ("direct", "graph", 2.0, False), ("direct", "node", 2.0, False),
    ("query", "graph", 2.0, False), ("query", "node", 2.0, False),
    ("direct", "graph", 2.0, True), ("direct", "node", 2.0, True),
    ("query", "graph", 2.0, True), ("query", "node", 2.0, True),
    ("direct", "graph", True, False), ("direct", "node", True, False),
    ("query", "graph", True, False), ("query", "node", True, False),
), ids=("direct-graph-float", "direct-node-float", "query-graph-float", "query-node-float",
    "direct-graph-rehashed-float", "direct-node-rehashed-float", "query-graph-rehashed-float", "query-node-rehashed-float",
    "direct-graph-bool", "direct-node-bool", "query-graph-bool", "query-node-bool"))
def test_query_nested_proof_abi_requires_exact_integer(tmp_path, entry, level, version, rehashed):
    from cemm_authoritative_hybrid.r3_artifacts import ProofGraph, ProofNode
    stores = _stores("memory", tmp_path)
    try:
        expression = _description_expression()
        _seed_reviewed_generic_claim(stores, expression)
        result = _evaluate(stores, expression).query_results[0]
        wire = result.as_dict()
        graph = wire["proof"]
        nested = graph if level == "graph" else graph["nodes"][0]
        nested["abi_version"] = version
        if rehashed:
            if level == "node":
                previous = nested["proof_node_ref"]
                _rehash(nested, "proof_node_ref", "r3_proof_node")
                graph["root_node_refs"] = [nested["proof_node_ref"] if ref == previous else ref for ref in graph["root_node_refs"]]
            _rehash(graph, "proof_ref", "r3_proof_graph")
            _rehash(wire, "query_result_ref", "r3_query_result")
        decoder = QueryResult if entry == "query" else ProofGraph if level == "graph" else ProofNode
        with pytest.raises(ValueError, match="ABI"):
            decoder.from_dict(wire if entry == "query" else nested)
    finally:
        stores.close()


@pytest.mark.parametrize("corruption", ("float", "rehashed-float", "bool", "int-subclass", "old", "future"),
    ids=("float", "rehashed-float", "bool", "int-subclass", "old", "future"))
def test_projection_evaluation_abi_requires_exact_integer(tmp_path, corruption):
    class WireInt(int):
        pass
    stores = _stores("memory", tmp_path)
    try:
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        evaluation = _evaluation(expression, situation, _evaluate(stores, expression, situation=situation))
        versions = (1, 2) if corruption == "old" else ({"float": 3.0,
            "rehashed-float": 3.0, "bool": True, "int-subclass": WireInt(3),
            "future": 4}[corruption],)
        for version in versions:
            wire = evaluation.as_dict()
            wire["abi_version"] = version
            if corruption == "rehashed-float":
                _rehash(wire, "evaluation_ref", "r3_evaluation")
            with pytest.raises(ValueError, match="ABI"):
                EvaluationBundle.from_dict(wire)
    finally:
        stores.close()


@pytest.mark.parametrize("artifact", ("query", "graph", "node", "evaluation"),
    ids=("query", "graph", "node", "evaluation"))
def test_query_proof_envelopes_require_exact_field_names(tmp_path, artifact):
    class WireKey(str):
        pass
    stores = _stores("memory", tmp_path)
    try:
        expression = _description_expression()
        _seed_reviewed_generic_claim(stores, expression)
        mode = _evaluate(stores, expression)
        result = mode.query_results[0]
        if artifact == "evaluation":
            source, situation = _query_expression(), _situation(stores.revision_pin())
            value = _evaluation(source, situation, _evaluate(stores, source, situation=situation))
        else:
            value = result if artifact == "query" else result.proof if artifact == "graph" else result.proof.nodes[0]
        wire = {WireKey(key) if key == "abi_version" else key: item for key, item in value.as_dict().items()}
        with pytest.raises(TypeError, match="field names"):
            type(value).from_dict(wire)
    finally:
        stores.close()


__cemm_test_inventory__ = {
'tests/test_foundation_projection_query.py::test_projection_evaluation_abi_requires_exact_integer[bool]': {'activation_phase': 'R4',
                                                                                                            'assertion_ref': 'assertion:foundation-projection-evaluation-abi-requires-exact-integer-bool',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                            'source_ast_sha256': 'c6a9cbafebd3f57ea61047e313a950cb917b4dd79fd332c75dceebff1528ab81'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_abi_requires_exact_integer[float]': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-projection-evaluation-abi-requires-exact-integer-float',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                             'source_ast_sha256': 'c6a9cbafebd3f57ea61047e313a950cb917b4dd79fd332c75dceebff1528ab81'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_abi_requires_exact_integer[future]': {'activation_phase': 'R4',
                                                                                                              'assertion_ref': 'assertion:foundation-projection-evaluation-abi-requires-exact-integer-future',
                                                                                                              'diagnostic_role': 'owner',
                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                              'source_ast_sha256': 'c6a9cbafebd3f57ea61047e313a950cb917b4dd79fd332c75dceebff1528ab81'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_abi_requires_exact_integer[int-subclass]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-projection-evaluation-abi-requires-exact-integer-int-subclass',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'c6a9cbafebd3f57ea61047e313a950cb917b4dd79fd332c75dceebff1528ab81'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_abi_requires_exact_integer[old]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-projection-evaluation-abi-requires-exact-integer-old',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': 'c6a9cbafebd3f57ea61047e313a950cb917b4dd79fd332c75dceebff1528ab81'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_abi_requires_exact_integer[rehashed-float]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-evaluation-abi-requires-exact-integer-rehashed-float',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'c6a9cbafebd3f57ea61047e313a950cb917b4dd79fd332c75dceebff1528ab81'},
 'tests/test_foundation_projection_query.py::test_query_proof_envelopes_require_exact_field_names[evaluation]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-query-proof-envelopes-require-exact-field-names-evaluation',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'b69cb4832d05d7530b4ff082c750821cd20a66af26e6f7a82f9b0b4c130ed72f'},
 'tests/test_foundation_projection_query.py::test_query_proof_envelopes_require_exact_field_names[graph]': {'activation_phase': 'R4',
                                                                                                            'assertion_ref': 'assertion:foundation-query-proof-envelopes-require-exact-field-names-graph',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                            'source_ast_sha256': 'b69cb4832d05d7530b4ff082c750821cd20a66af26e6f7a82f9b0b4c130ed72f'},
 'tests/test_foundation_projection_query.py::test_query_proof_envelopes_require_exact_field_names[node]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-query-proof-envelopes-require-exact-field-names-node',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': 'b69cb4832d05d7530b4ff082c750821cd20a66af26e6f7a82f9b0b4c130ed72f'},
 'tests/test_foundation_projection_query.py::test_query_proof_envelopes_require_exact_field_names[query]': {'activation_phase': 'R4',
                                                                                                            'assertion_ref': 'assertion:foundation-query-proof-envelopes-require-exact-field-names-query',
                                                                                                            'diagnostic_role': 'owner',
                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                            'source_ast_sha256': 'b69cb4832d05d7530b4ff082c750821cd20a66af26e6f7a82f9b0b4c130ed72f'},
'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[direct-graph-bool]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-direct-graph-bool',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[direct-graph-float]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-direct-graph-float',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[direct-graph-rehashed-float]': {'activation_phase': 'R4',
                                                                                                                                'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-direct-graph-rehashed-float',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                                'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[direct-node-bool]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-direct-node-bool',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[direct-node-float]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-direct-node-float',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[direct-node-rehashed-float]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-direct-node-rehashed-float',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[query-graph-bool]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-query-graph-bool',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[query-graph-float]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-query-graph-float',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[query-graph-rehashed-float]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-query-graph-rehashed-float',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[query-node-bool]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-query-node-bool',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[query-node-float]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-query-node-float',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
 'tests/test_foundation_projection_query.py::test_query_nested_proof_abi_requires_exact_integer[query-node-rehashed-float]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-query-nested-proof-abi-requires-exact-integer-query-node-rehashed-float',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'eb0659f50bdda9caa4b75f07516bc0c9401229a396f8545b2b0a76af5414f615'},
'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[compound]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-compound',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[unresolved]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-unresolved',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
'tests/test_foundation_projection_query.py::test_projection_budget_keeps_signed_empty_terminal[facts-memory]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-budget-keeps-signed-empty-terminal-facts-memory',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '3e8f89fdbd669525006f6ea588751a1e4ca347cbd07230fa1e2583ec53f8db52'},
 'tests/test_foundation_projection_query.py::test_projection_budget_keeps_signed_empty_terminal[facts-sqlite]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-budget-keeps-signed-empty-terminal-facts-sqlite',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '3e8f89fdbd669525006f6ea588751a1e4ca347cbd07230fa1e2583ec53f8db52'},
 'tests/test_foundation_projection_query.py::test_projection_budget_keeps_signed_empty_terminal[proofs-memory]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-budget-keeps-signed-empty-terminal-proofs-memory',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': '3e8f89fdbd669525006f6ea588751a1e4ca347cbd07230fa1e2583ec53f8db52'},
 'tests/test_foundation_projection_query.py::test_projection_budget_keeps_signed_empty_terminal[proofs-sqlite]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-budget-keeps-signed-empty-terminal-proofs-sqlite',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': '3e8f89fdbd669525006f6ea588751a1e4ca347cbd07230fa1e2583ec53f8db52'},
 'tests/test_foundation_projection_query.py::test_projection_budget_keeps_signed_empty_terminal[roots-memory]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-budget-keeps-signed-empty-terminal-roots-memory',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '3e8f89fdbd669525006f6ea588751a1e4ca347cbd07230fa1e2583ec53f8db52'},
 'tests/test_foundation_projection_query.py::test_projection_budget_keeps_signed_empty_terminal[roots-sqlite]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-budget-keeps-signed-empty-terminal-roots-sqlite',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '3e8f89fdbd669525006f6ea588751a1e4ca347cbd07230fa1e2583ec53f8db52'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[answer]': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-answer',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                   'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[bindings]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-bindings',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[proof]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-proof',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[query-pin]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-query-pin',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[query-refs]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-query-refs',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[query-source]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-query-source',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[request-content]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-request-content',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[request-projection]': {'activation_phase': 'R4',
                                                                                                                               'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-request-projection',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-7',
                                                                                                                               'owner_ref': 'decision-query-proof',
                                                                                                                               'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[request-situation]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-request-situation',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[request-target]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-request-target',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[sources]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-sources',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_rejects_canonical_crossbindings[status]': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:foundation-projection-evaluation-rejects-canonical-crossbindings-status',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                   'source_ast_sha256': 'f294e43cf07aedda2364b6c802a21d1ae0774892f69f26fa8808846013c0cd04'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_requires_sole_projection_result[empty]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-evaluation-requires-sole-projection-result-empty',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': '6cb0033b786fb11d7bea95a5663c104b01e9a247fbcf6916cacd4badad36c347'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_requires_sole_projection_result[other-artifacts]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-projection-evaluation-requires-sole-projection-result-other-artifacts',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': '6cb0033b786fb11d7bea95a5663c104b01e9a247fbcf6916cacd4badad36c347'},
 'tests/test_foundation_projection_query.py::test_projection_evaluation_requires_sole_projection_result[proposition]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-evaluation-requires-sole-projection-result-proposition',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '6cb0033b786fb11d7bea95a5663c104b01e9a247fbcf6916cacd4badad36c347'},
 'tests/test_foundation_projection_query.py::test_projection_query_accepts_fresh_generation_without_rule_scan': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-query-accepts-fresh-generation-without-rule-scan',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '830b9e4636d8aa7e2641b7704d0890d33182dbd2ed66f4e3bb7e4258c79ce7fd'},
 'tests/test_foundation_projection_query.py::test_projection_query_api_rejects_invalid_contract[bindings]': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-projection-query-api-rejects-invalid-contract-bindings',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                             'source_ast_sha256': '0454fa4e0d79ac4218f6dae9ef84b0d787ffbba276cb8d294e6f9e81b2cfb48d'},
 'tests/test_foundation_projection_query.py::test_projection_query_api_rejects_invalid_contract[contradicted]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-query-api-rejects-invalid-contract-contradicted',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': '0454fa4e0d79ac4218f6dae9ef84b0d787ffbba276cb8d294e6f9e81b2cfb48d'},
 'tests/test_foundation_projection_query.py::test_projection_query_api_rejects_invalid_contract[pin]': {'activation_phase': 'R4',
                                                                                                        'assertion_ref': 'assertion:foundation-projection-query-api-rejects-invalid-contract-pin',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                        'source_ast_sha256': '0454fa4e0d79ac4218f6dae9ef84b0d787ffbba276cb8d294e6f9e81b2cfb48d'},
 'tests/test_foundation_projection_query.py::test_projection_query_api_rejects_invalid_contract[proposition-proof]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-query-api-rejects-invalid-contract-proposition-proof',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': '0454fa4e0d79ac4218f6dae9ef84b0d787ffbba276cb8d294e6f9e81b2cfb48d'},
 'tests/test_foundation_projection_query.py::test_projection_query_api_rejects_invalid_contract[source]': {'activation_phase': 'R4',
                                                                                                           'assertion_ref': 'assertion:foundation-projection-query-api-rejects-invalid-contract-source',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                           'source_ast_sha256': '0454fa4e0d79ac4218f6dae9ef84b0d787ffbba276cb8d294e6f9e81b2cfb48d'},
 'tests/test_foundation_projection_query.py::test_projection_query_api_rejects_invalid_contract[unsigned]': {'activation_phase': 'R4',
                                                                                                             'assertion_ref': 'assertion:foundation-projection-query-api-rejects-invalid-contract-unsigned',
                                                                                                             'diagnostic_role': 'owner',
                                                                                                             'introduced_by_task': 'Foundation-Task-7',
                                                                                                             'owner_ref': 'decision-query-proof',
                                                                                                             'source_ast_sha256': '0454fa4e0d79ac4218f6dae9ef84b0d787ffbba276cb8d294e6f9e81b2cfb48d'},
 'tests/test_foundation_projection_query.py::test_projection_query_authenticates_nonfocused_postings_before_filter[memory]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-projection-query-authenticates-nonfocused-postings-before-filter-memory',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'b88b2cbdfe6601812058a69ea3e140b244ddb659ffd916657a26fbb5cf4c167a'},
 'tests/test_foundation_projection_query.py::test_projection_query_authenticates_nonfocused_postings_before_filter[sqlite]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-projection-query-authenticates-nonfocused-postings-before-filter-sqlite',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': 'b88b2cbdfe6601812058a69ea3e140b244ddb659ffd916657a26fbb5cf4c167a'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[conflict-memory]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-conflict-memory',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[conflict-sqlite]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-conflict-sqlite',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[deny-memory]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-deny-memory',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[deny-sqlite]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-deny-sqlite',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[missing-memory]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-missing-memory',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[missing-sqlite]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-missing-sqlite',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[positive-memory]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-positive-memory',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_carries_genuine_signed_result[positive-sqlite]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-carries-genuine-signed-result-positive-sqlite',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': 'c1a75448bebd48d478b95ecc06be2107a696060a8b3dfe523f2d5d79dfb481d1'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[abi2]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-abi2',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[dict]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-dict',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[field-name]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-field-name',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[kind]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-kind',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[list]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-list',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[missing-fields]': {'activation_phase': 'R4',
                                                                                                                            'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-missing-fields',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-7',
                                                                                                                            'owner_ref': 'decision-query-proof',
                                                                                                                            'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[nested-list]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-nested-list',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[nested-string]': {'activation_phase': 'R4',
                                                                                                                           'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-nested-string',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-7',
                                                                                                                           'owner_ref': 'decision-query-proof',
                                                                                                                           'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[pin]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-pin',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_codec_hardcuts_and_rejects_subclasses[status]': {'activation_phase': 'R4',
                                                                                                                    'assertion_ref': 'assertion:foundation-projection-query-codec-hardcuts-and-rejects-subclasses-status',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'Foundation-Task-7',
                                                                                                                    'owner_ref': 'decision-query-proof',
                                                                                                                    'source_ast_sha256': 'b7852ccd1129498bd9d7577c0f7514e3e4b3eb5c9e3e721f790d648f39ee0f00'},
 'tests/test_foundation_projection_query.py::test_projection_query_maximum_ordered_proof_detaches_wire[memory]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-maximum-ordered-proof-detaches-wire-memory',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'b65f58e2680ab0f0af14dccb2ff0545e15ea4ac4419c1807c1d8225d39443b99'},
 'tests/test_foundation_projection_query.py::test_projection_query_maximum_ordered_proof_detaches_wire[sqlite]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-maximum-ordered-proof-detaches-wire-sqlite',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': 'b65f58e2680ab0f0af14dccb2ff0545e15ea4ac4419c1807c1d8225d39443b99'},
 'tests/test_foundation_projection_query.py::test_projection_query_partial_signed_codec_preserves_clarification': {'activation_phase': 'R4',
                                                                                                                   'assertion_ref': 'assertion:foundation-projection-query-partial-signed-codec-preserves-clarification',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-7',
                                                                                                                   'owner_ref': 'decision-query-proof',
                                                                                                                   'source_ast_sha256': 'cc8881466cde0060a5fac6d7bf16a44ff1090bca8e16497a98324b364f2bf88b'},
 'tests/test_foundation_projection_query.py::test_projection_query_preserves_activation_identity_guards[before-hash]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-query-preserves-activation-identity-guards-before-hash',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': 'a9f82eabf7c1ac1c15c5474820a29fb46906f5529503b51bb217759e59016090'},
 'tests/test_foundation_projection_query.py::test_projection_query_preserves_activation_identity_guards[before-object]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-query-preserves-activation-identity-guards-before-object',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'a9f82eabf7c1ac1c15c5474820a29fb46906f5529503b51bb217759e59016090'},
 'tests/test_foundation_projection_query.py::test_projection_query_preserves_activation_identity_guards[before-rules]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-projection-query-preserves-activation-identity-guards-before-rules',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'a9f82eabf7c1ac1c15c5474820a29fb46906f5529503b51bb217759e59016090'},
 'tests/test_foundation_projection_query.py::test_projection_query_preserves_activation_identity_guards[during-hash]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-query-preserves-activation-identity-guards-during-hash',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': 'a9f82eabf7c1ac1c15c5474820a29fb46906f5529503b51bb217759e59016090'},
 'tests/test_foundation_projection_query.py::test_projection_query_preserves_activation_identity_guards[during-object]': {'activation_phase': 'R4',
                                                                                                                          'assertion_ref': 'assertion:foundation-projection-query-preserves-activation-identity-guards-during-object',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-7',
                                                                                                                          'owner_ref': 'decision-query-proof',
                                                                                                                          'source_ast_sha256': 'a9f82eabf7c1ac1c15c5474820a29fb46906f5529503b51bb217759e59016090'},
 'tests/test_foundation_projection_query.py::test_projection_query_preserves_activation_identity_guards[during-rules]': {'activation_phase': 'R4',
                                                                                                                         'assertion_ref': 'assertion:foundation-projection-query-preserves-activation-identity-guards-during-rules',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-7',
                                                                                                                         'owner_ref': 'decision-query-proof',
                                                                                                                         'source_ast_sha256': 'a9f82eabf7c1ac1c15c5474820a29fb46906f5529503b51bb217759e59016090'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_linked_snapshot_identity_drift[before]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-rejects-linked-snapshot-identity-drift-before',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': '45c873fd5ed26f0d21e60e2251e079145a0c65b1d772d8d46da57391e5f5b6bf'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_linked_snapshot_identity_drift[during]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-rejects-linked-snapshot-identity-drift-during',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': '45c873fd5ed26f0d21e60e2251e079145a0c65b1d772d8d46da57391e5f5b6bf'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[mixed]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-mixed',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[observe]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-observe',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[request]': {'activation_phase': 'R4',
                                                                                                                       'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-request',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                                       'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[scoped]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-scoped',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
 'tests/test_foundation_projection_query.py::test_projection_query_rejects_unsupported_source_before_reads[simulate]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-projection-query-rejects-unsupported-source-before-reads-simulate',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '17483e71e99b50a907d911836c63cdd5cd12124f38403d08a21fd0b55f3aec57'},
 'tests/test_foundation_projection_query.py::test_projection_query_sqlite_restart_is_read_only': {'activation_phase': 'R4',
                                                                                                  'assertion_ref': 'assertion:foundation-projection-query-sqlite-restart-is-read-only',
                                                                                                  'diagnostic_role': 'owner',
                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                  'source_ast_sha256': '286f74de74d5416cdf815b81397bc6c95bc6a1495e94cc1213bec8f031b2b7af'},
 'tests/test_foundation_projection_query.py::test_projection_query_uses_one_read_without_rule_refresh[definition]': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:foundation-projection-query-uses-one-read-without-rule-refresh-definition',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-7',
                                                                                                                     'owner_ref': 'decision-query-proof',
                                                                                                                     'source_ast_sha256': '265136aeb5b1d8d376810b6e0e4e70ac6b530c08692e8b03c24d2c153f4f79b0'},
 'tests/test_foundation_projection_query.py::test_projection_query_uses_one_read_without_rule_refresh[description]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-projection-query-uses-one-read-without-rule-refresh-description',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': '265136aeb5b1d8d376810b6e0e4e70ac6b530c08692e8b03c24d2c153f4f79b0'},
 'tests/test_foundation_projection_query.py::test_proposition_query_codec_preserves_nested_strict_wire[dict]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-proposition-query-codec-preserves-nested-strict-wire-dict',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': '7330d5eabaa5a2e74400e26d70b7f3de2acb087082a2dcc0a4e4fbf81aefc5fd'},
 'tests/test_foundation_projection_query.py::test_proposition_query_codec_preserves_nested_strict_wire[field-name]': {'activation_phase': 'R4',
                                                                                                                      'assertion_ref': 'assertion:foundation-proposition-query-codec-preserves-nested-strict-wire-field-name',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'Foundation-Task-7',
                                                                                                                      'owner_ref': 'decision-query-proof',
                                                                                                                      'source_ast_sha256': '7330d5eabaa5a2e74400e26d70b7f3de2acb087082a2dcc0a4e4fbf81aefc5fd'},
 'tests/test_foundation_projection_query.py::test_proposition_query_codec_preserves_nested_strict_wire[list]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-proposition-query-codec-preserves-nested-strict-wire-list',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': '7330d5eabaa5a2e74400e26d70b7f3de2acb087082a2dcc0a4e4fbf81aefc5fd'},
 'tests/test_foundation_projection_query.py::test_proposition_query_codec_preserves_nested_strict_wire[scalar]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-proposition-query-codec-preserves-nested-strict-wire-scalar',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': '7330d5eabaa5a2e74400e26d70b7f3de2acb087082a2dcc0a4e4fbf81aefc5fd'},
 'tests/test_foundation_projection_query.py::test_query_codec_rejects_cycles_at_typed_field_boundary[bindings]': {'activation_phase': 'R4',
                                                                                                                  'assertion_ref': 'assertion:foundation-query-codec-rejects-cycles-at-typed-field-boundary-bindings',
                                                                                                                  'diagnostic_role': 'owner',
                                                                                                                  'introduced_by_task': 'Foundation-Task-7',
                                                                                                                  'owner_ref': 'decision-query-proof',
                                                                                                                  'source_ast_sha256': '73d5ac02517a69580093c130ed8ed419bb7fc6c34de49abada2e7be05bb223d7'},
 'tests/test_foundation_projection_query.py::test_query_codec_rejects_cycles_at_typed_field_boundary[retrieval-refs]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-query-codec-rejects-cycles-at-typed-field-boundary-retrieval-refs',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '73d5ac02517a69580093c130ed8ed419bb7fc6c34de49abada2e7be05bb223d7'},
 'tests/test_foundation_projection_query.py::test_query_codec_rejects_cycles_at_typed_field_boundary[status]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-query-codec-rejects-cycles-at-typed-field-boundary-status',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': '73d5ac02517a69580093c130ed8ed419bb7fc6c34de49abada2e7be05bb223d7'},
 'tests/test_foundation_projection_query.py::test_query_codec_rejects_overlong_rows_before_child_iteration[bindings]': {'activation_phase': 'R4',
                                                                                                                        'assertion_ref': 'assertion:foundation-query-codec-rejects-overlong-rows-before-child-iteration-bindings',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-7',
                                                                                                                        'owner_ref': 'decision-query-proof',
                                                                                                                        'source_ast_sha256': '75b4fa975d587c9a6455ab8719724f426112a0d678ea235168f9f67eef6aec10'},
 'tests/test_foundation_projection_query.py::test_query_codec_rejects_overlong_rows_before_child_iteration[retrieval-refs]': {'activation_phase': 'R4',
                                                                                                                              'assertion_ref': 'assertion:foundation-query-codec-rejects-overlong-rows-before-child-iteration-retrieval-refs',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-7',
                                                                                                                              'owner_ref': 'decision-query-proof',
                                                                                                                              'source_ast_sha256': '75b4fa975d587c9a6455ab8719724f426112a0d678ea235168f9f67eef6aec10'},
 'tests/test_foundation_projection_query.py::test_r3_evaluation_rejects_projection_in_nonquery_mode[observe]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-r3-evaluation-rejects-projection-in-nonquery-mode-observe',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': 'ab9612fe453d45caa4b57b479523be8f63a90ceaf28878e2a205e77267f85c5a'},
 'tests/test_foundation_projection_query.py::test_r3_evaluation_rejects_projection_in_nonquery_mode[request]': {'activation_phase': 'R4',
                                                                                                                'assertion_ref': 'assertion:foundation-r3-evaluation-rejects-projection-in-nonquery-mode-request',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'Foundation-Task-7',
                                                                                                                'owner_ref': 'decision-query-proof',
                                                                                                                'source_ast_sha256': 'ab9612fe453d45caa4b57b479523be8f63a90ceaf28878e2a205e77267f85c5a'},
 'tests/test_foundation_projection_query.py::test_r3_evaluation_rejects_projection_in_nonquery_mode[simulate]': {'activation_phase': 'R4',
                                                                                                                 'assertion_ref': 'assertion:foundation-r3-evaluation-rejects-projection-in-nonquery-mode-simulate',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-7',
                                                                                                                 'owner_ref': 'decision-query-proof',
                                                                                                                 'source_ast_sha256': 'ab9612fe453d45caa4b57b479523be8f63a90ceaf28878e2a205e77267f85c5a'},
 'tests/test_foundation_projection_query.py::test_r3_projection_finalize_uses_exact_bundle_boundary': {'activation_phase': 'R4',
                                                                                                       'assertion_ref': 'assertion:foundation-r3-projection-finalize-uses-exact-bundle-boundary',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'Foundation-Task-7',
                                                                                                       'owner_ref': 'decision-query-proof',
                                                                                                       'source_ast_sha256': '2bb9c93a61fdc66f9834ffe53d63a38c0a777b048b51b9907f987a9fbb6b6ef8'}}
