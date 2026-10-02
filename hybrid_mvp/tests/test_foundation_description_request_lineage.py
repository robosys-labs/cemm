"""Independent request-first lineage, without public query activation."""
from copy import deepcopy

import pytest

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.descriptions import DescriptionCompleteness, DescriptionRequest, DescriptionResult
from cemm_authoritative_hybrid.expressions import ApplicationFiller, QueryProjection, SemanticExpression, SemanticApplication, RoleBinding, GroundedReference, ScopeOperator
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.cycle import SemanticMode
from cemm_authoritative_hybrid.proof_bundle import ProofBundle
from cemm_authoritative_hybrid.situation import SituationContext


def _query_expression(target="entity:alice", requested="description"):
    return SemanticExpression.create(applications=(), root_refs=("local:request",),
        query_projections=(QueryProjection("local:request", requested, target),))


def _situation(pin=None, **changes):
    values = dict(orientation_ref="orientation:test", proposal_context_ref="proposal_context:test",
        mode=SemanticMode.QUERY, session_ref="session:test", turn_ref="turn:original", turn_index=1,
        session_phase_ref="phase:conversation", participant_refs=("participant:user", "participant:system"),
        speaker_ref="participant:user", addressee_ref="participant:system", actor_ref=None,
        temporal_frame_ref="time:present", active_event_refs=(), focus_snapshot_ref="focus:test", focus_refs=(),
        obligation_snapshot_ref="obligation:test", obligation_refs=(), capability_refs=(),
        permission_snapshot_ref="permission:test", permission_refs=(), resource_snapshot_ref="resource:test",
        resource_refs=(), adapter_snapshot_ref="adapter:test", adapter_refs=(), evidence_kinds=("text",),
        evidence_policy_refs=("policy:text",), adapter_receipt_refs=(), trusted_observation=False,
        source_refs=("evidence:test",), epistemic_scope_ref="epistemic_scope:query",
        revision_pin=pin or RevisionPin("authority:test", 2, 3, 4, 5, "model:test"))
    values.update(changes)
    return SituationContext.create(**values)


def _request(expression=None, situation=None, **changes):
    return DescriptionRequest.create(source_expression=expression or _query_expression(),
        situation=situation or _situation(), max_depth=changes.get("max_depth", 3), max_facts=changes.get("max_facts", 16))


def _terminal(request, completeness=DescriptionCompleteness.MISSING):
    return DescriptionResult.create(request=request, answer_expression=None, completeness=completeness,
        fact_refs=(), definition_refs=(), claim_refs=(), source_refs=(), proof_refs=(), revision_pin=request.revision_pin)


@pytest.mark.parametrize("requested", ("description", "definition"), ids=("description", "definition"))
def test_request_factory_binds_actual_canonical_expression_situation_and_budgets(requested):
    expression, situation = _query_expression(requested=requested), _situation()
    request = _request(expression, situation)
    assert request.abi_version == 2
    assert request.source_expression_ref == expression.expression_ref
    assert request.source_projection_ref == expression.query_projections[0].projection_ref
    assert request.requested_content == requested
    assert request.target_ref == "entity:alice"
    assert request.source_situation_ref == situation.situation_ref
    assert request.revision_pin == situation.revision_pin
    assert (request.max_depth, request.max_facts) == (3, 16)
    assert DescriptionRequest.from_dict(request.as_dict()) == request
    request.validate_source(expression, situation)


def test_request_identity_covers_target_content_situation_pin_and_budgets():
    original = _request()
    variants = (_request(_query_expression("entity:bob")), _request(_query_expression(requested="definition")),
        _request(situation=_situation(turn_ref="turn:other")),
        _request(situation=_situation(RevisionPin("authority:test", 3, 3, 4, 5, "model:test"))),
        _request(max_depth=2), _request(max_facts=15))
    assert len({original.description_request_ref, *(item.description_request_ref for item in variants)}) == 7


@pytest.mark.parametrize("shape", ("membership", "metadata", "mixed"), ids=("membership", "metadata", "mixed"))
def test_request_factory_rejects_proposition_or_mixed_query_sources(shape):
    app = SemanticApplication("local:claim", "op:type", "concept:mother", (
        RoleBinding("role:instance", GroundedReference("entity:alice")),
        RoleBinding("role:class", GroundedReference("concept:mother")),))
    target = "concept:mother" if shape == "metadata" else "entity:alice"
    expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
    if shape == "mixed":
        expression = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref, "local:request"),
            query_projections=(QueryProjection("local:request", "description", target),))
    with pytest.raises(ValueError, match="pure|projection"):
        _request(expression)


def test_request_factory_rejects_nonquery_situation():
    situation = _situation(mode=SemanticMode.OBSERVE, epistemic_scope_ref="epistemic_scope:observed")
    with pytest.raises(ValueError, match="QUERY|query"):
        _request(situation=situation)


def test_request_factory_rejects_scoped_projection():
    projection = QueryProjection("local:request", "description", "entity:alice")
    scope = ScopeOperator("local:scope", "scope:quotation", "scope_value:quoted", projection.projection_ref)
    expression = SemanticExpression.create(applications=(), root_refs=(scope.scope_ref,),
        scope_operators=(scope,), query_projections=(projection,))
    with pytest.raises(ValueError, match="pure query projection"):
        _request(expression)


@pytest.mark.parametrize("record,field", (("request", "field-name"), ("request", "request-ref"),
    ("request", "pin-field-name"), ("result", "field-name"), ("result", "result-ref"), ("result", "completeness")),
    ids=("request-field-name", "request-request-ref", "request-pin-field-name", "result-field-name", "result-result-ref", "result-completeness"))
def test_description_codecs_reject_exact_wire_string_type_violations(record, field):
    class WireString(str):
        pass
    request = _request()
    artifact = request if record == "request" else _terminal(request)
    wire = artifact.as_dict()
    if field == "field-name":
        wire[WireString("abi_version")] = wire.pop("abi_version")
    elif field == "pin-field-name":
        pin = wire["revision_pin"]
        pin[WireString("world_revision")] = pin.pop("world_revision")
    else:
        key = {"request-ref": "description_request_ref", "result-ref": "description_result_ref", "completeness": "completeness"}[field]
        wire[key] = WireString(wire[key])
    with pytest.raises(TypeError):
        type(artifact).from_dict(wire)


@pytest.mark.parametrize("corruption", ("mapping", "list", "string"), ids=("mapping", "list", "string"))
def test_description_result_rejects_nested_answer_wire_subclasses(corruption):
    from tests.test_foundation_descriptions import _result
    class WireDict(dict):
        pass
    class WireList(list):
        pass
    class WireString(str):
        pass
    wire = _result().as_dict()
    answer = wire["answer_expression"]
    if corruption == "mapping":
        answer["applications"][0] = WireDict(answer["applications"][0])
    elif corruption == "list":
        answer["root_refs"] = WireList(answer["root_refs"])
    else:
        answer["expression_ref"] = WireString(answer["expression_ref"])
    with pytest.raises(TypeError):
        DescriptionResult.from_dict(wire)


@pytest.mark.parametrize("record", ("request", "result", "bundle"), ids=("request", "result", "bundle"))
def test_description_and_bundle_explicitly_reject_abi1(record):
    request = _request()
    result = _terminal(request)
    bundle = ProofBundle.create(description=result, claims=(), application_refs=(), revision_pin=request.revision_pin)
    artifact = {"request": request, "result": result, "bundle": bundle}[record]
    wire = artifact.as_dict()
    wire["abi_version"] = 1
    with pytest.raises(ValueError, match="ABI"):
        type(artifact).from_dict(wire)


@pytest.mark.parametrize("field,value", (
    ("source_expression_ref", "query:wrong"), ("source_situation_ref", "situation:wrong"),
    ("source_projection_ref", "projection:wrong reference"), ("target_ref", "bare"),
    ("requested_content", "membership"), ("max_depth", True), ("max_facts", 257),
    ("abi_version", 1), ("revision_pin", []), ("source_query_ref", "r3_query_result:old"),
), ids=("source_expression_ref-query-wrong", "source_situation_ref-situation-wrong",
    "source_projection_ref-projection-wrong-reference", "target_ref-bare", "requested_content-membership",
    "max_depth-True", "max_facts-257", "abi_version-1", "revision_pin-value8", "source_query_ref-r3_query_result-old"))
def test_request_codec_rejects_old_or_invalid_wire(field, value):
    wire = _request().as_dict()
    wire[field] = value
    with pytest.raises((TypeError, ValueError)):
        DescriptionRequest.from_dict(wire)


@pytest.mark.parametrize("change", ("target", "content", "expression", "projection", "situation", "pin"),
    ids=("target", "content", "expression", "projection", "situation", "pin"))
def test_rehashed_request_decoding_does_not_prove_actual_source_origin(change):
    expression, situation = _query_expression(), _situation()
    wire = _request(expression, situation).as_dict()
    field, value = {
        "target": ("target_ref", "entity:bob"), "content": ("requested_content", "definition"),
        "expression": ("source_expression_ref", "expression:forged"),
        "projection": ("source_projection_ref", "projection:1"),
        "situation": ("source_situation_ref", _situation(turn_ref="turn:other").situation_ref),
        "pin": ("revision_pin", _situation(RevisionPin("authority:test", 3, 3, 4, 5, "model:test")).revision_pin.as_dict()),
    }[change]
    wire[field] = value
    wire["description_request_ref"] = stable_ref("description_request", {k: v for k, v in wire.items() if k != "description_request_ref"})
    decoded = DescriptionRequest.from_dict(wire)
    with pytest.raises(ValueError, match="source|pin|match"):
        decoded.validate_source(expression, situation)


def test_terminal_bundle_is_acyclic_request_lineage_without_final_query_backreference():
    request = _request()
    description = _terminal(request)
    bundle = ProofBundle.create(description=description, application_refs=(), claims=(), revision_pin=request.revision_pin)
    wire = bundle.as_dict()
    assert bundle.abi_version == description.abi_version == 2
    assert set(wire) == {"abi_version", "proof_bundle_ref", "description", "application_refs", "claims", "revision_pin"}
    assert bundle.source_expression_ref == request.source_expression_ref
    assert not hasattr(bundle, "source_query_ref")
    assert not hasattr(bundle, "source_query")
    assert ProofBundle.from_dict(wire) == bundle
    for field in ("source_query", "source_expression_ref", "final_result_ref"):
        attacked = deepcopy(wire)
        attacked[field] = "r3_query_result:forged"
        with pytest.raises((TypeError, ValueError)):
            ProofBundle.from_dict(attacked)
    wire["description"]["request"]["target_ref"] = "entity:bob"
    assert bundle.description.request.target_ref == "entity:alice"


def test_definition_result_rejects_neighborhood_as_definition_authority():
    from tests.test_foundation_descriptions import _expression
    request = _request(_query_expression(requested="definition"))
    for completeness in (DescriptionCompleteness.SUFFICIENT, DescriptionCompleteness.PARTIAL, DescriptionCompleteness.CONFLICT):
        with pytest.raises(ValueError, match="definition|policy"):
            DescriptionResult.create(request=request, answer_expression=_expression(), completeness=completeness,
                fact_refs=("fact:test",), definition_refs=("semantic_application:neighborhood",),
                claim_refs=("claim:test",), source_refs=("source:test",), proof_refs=("proof:test",), revision_pin=request.revision_pin)
    assert _terminal(request).completeness is DescriptionCompleteness.MISSING
    assert _terminal(request, DescriptionCompleteness.BUDGET_EXHAUSTED).answer_expression is None


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_definition_is_missing_even_when_same_target_description_is_sufficient(tmp_path, backend):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    from tests.test_foundation_description_builder import _stores, _seed_reviewed_generic_claim, _description_expression
    stores = _stores(backend, tmp_path)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        situation = _situation(stores.revision_pin())
        authority = SimpleNamespace(generation=situation.revision_pin.authority_generation,
            content_hash="authority-content:description-test", atoms={}, capabilities={}, rules={})
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        before = stores.revisions()
        description_source = _query_expression()
        description, proof = owner.describe_with_proof(_request(description_source, situation), description_source, situation)
        assert description.completeness is DescriptionCompleteness.SUFFICIENT
        assert description.definition_refs and proof.claims
        definition_source = _query_expression(requested="definition")
        definition_request = _request(definition_source, situation)
        definition, proof = owner.describe_with_proof(definition_request, definition_source, situation)
        assert definition == owner.describe(definition_request, definition_source, situation)
        assert definition.completeness is DescriptionCompleteness.MISSING
        assert definition.answer_expression is None
        assert proof.claims == proof.application_refs == ()
        assert definition.definition_refs == definition.fact_refs == definition.proof_refs == ()
        assert stores.revisions() == before
    finally:
        stores.close()


def test_component_rejects_old_unknown_queryresult_source_before_read(tmp_path):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.r3_artifacts import QueryResult, QueryStatus
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    from tests.test_foundation_description_builder import _stores
    stores = _stores("memory", tmp_path)
    try:
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        request = _request(expression, situation)
        source = QueryResult.create(expression_ref=expression.expression_ref, status=QueryStatus.UNKNOWN,
            bindings=(), proof=None, retrieval_refs=(), rounds=1, revision_pin=request.revision_pin)
        authority = SimpleNamespace(generation=request.revision_pin.authority_generation,
            content_hash="authority-content:description-test", atoms={}, capabilities={}, rules={})
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        with pytest.raises(TypeError, match="SemanticExpression"):
            owner.describe(request, source, expression)
        with pytest.raises(TypeError):
            DescriptionRequest.create(source_query_ref=source.query_result_ref, target_ref=request.target_ref,
                max_depth=1, max_facts=1, revision_pin=request.revision_pin)
    finally:
        stores.close()


@pytest.mark.parametrize("requested,method_name", (("description", "describe"), ("description", "describe_with_proof"),
    ("definition", "describe"), ("definition", "describe_with_proof")),
    ids=("description-describe", "description-describe_with_proof", "definition-describe", "definition-describe_with_proof"))
def test_component_preserves_single_pinned_read_and_no_preliminary_query(tmp_path, monkeypatch, method_name, requested):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.r3_artifacts import QueryResult
    from cemm_authoritative_hybrid import r3_cognition
    from tests.test_foundation_description_builder import _stores, _seed_reviewed_generic_claim, _description_expression
    stores = _stores("memory", tmp_path)
    try:
        _seed_reviewed_generic_claim(stores, _description_expression())
        expression, situation = _query_expression(requested=requested), _situation(stores.revision_pin())
        request = _request(expression, situation)
        authority = SimpleNamespace(generation=request.revision_pin.authority_generation,
            content_hash="authority-content:description-test", atoms={}, capabilities={}, rules={})
        owner = r3_cognition.QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        snapshots, postings = [], []
        original_snapshot, original_postings = stores.r3_read_snapshot, r3_cognition.active_application_claims_for_target
        @contextmanager
        def snapshot(pin):
            snapshots.append(pin)
            with original_snapshot(pin):
                yield
        def target_read(*args, **kwargs):
            postings.append((args[1], kwargs["expected_pin"]))
            return original_postings(*args, **kwargs)
        def forbidden(*args, **kwargs):
            raise AssertionError("request-first description cannot evaluate or manufacture QueryResult")
        monkeypatch.setattr(stores, "r3_read_snapshot", snapshot)
        monkeypatch.setattr(r3_cognition, "active_application_claims_for_target", target_read)
        monkeypatch.setattr(owner, "evaluate", forbidden)
        monkeypatch.setattr(owner, "evaluate_full", forbidden)
        monkeypatch.setattr(QueryResult, "create", forbidden)
        before = stores.revisions()
        getattr(owner, method_name)(request, expression, situation)
        assert snapshots == [request.revision_pin]
        assert postings == ([] if requested == "definition" else [("entity:alice", request.revision_pin)])
        assert stores.revisions() == before
    finally:
        stores.close()


@pytest.mark.parametrize("timing,field", (("before", "content_hash"), ("before", "rules"),
    ("during", "content_hash"), ("during", "rules")),
    ids=("before-content_hash", "before-rules", "during-content_hash", "during-rules"))
def test_definition_missing_still_rejects_same_generation_authority_drift(tmp_path, monkeypatch, timing, field):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.persistence import StaleRevisionError
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    from tests.test_foundation_description_builder import _stores
    stores = _stores("memory", tmp_path)
    try:
        expression, situation = _query_expression(requested="definition"), _situation(stores.revision_pin())
        request = _request(expression, situation)
        authority = SimpleNamespace(generation=request.revision_pin.authority_generation,
            content_hash="authority-content:description-test", atoms={}, capabilities={}, rules={})
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        def change():
            setattr(authority, field, "authority-content:forged" if field == "content_hash" else {})
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
            owner.describe_with_proof(request, expression, situation)
    finally:
        stores.close()


@pytest.mark.parametrize("requested,method_name", (("description", "describe"), ("description", "describe_with_proof"),
    ("definition", "describe"), ("definition", "describe_with_proof")),
    ids=("description-describe", "description-describe_with_proof", "definition-describe", "definition-describe_with_proof"))
def test_description_rejects_linked_snapshot_identity_replacement_before_read(tmp_path, linked_authority, monkeypatch, requested, method_name):
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.persistence import memory_stores, StaleRevisionError
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        expression, situation = _query_expression(requested=requested), _situation(stores.revision_pin())
        request = _request(expression, situation)
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        original = linked_authority.rule_generation_snapshot()
        generation, content_hash, rules = original
        replacement = (generation, content_hash, rules)
        assert replacement == original and replacement is not original
        object.__setattr__(linked_authority, "_rule_generation_state", replacement)
        def forbidden(*args, **kwargs):
            raise AssertionError("stale activation identity cannot authorize description retrieval")
        monkeypatch.setattr(owner, "_description_at_pin", forbidden)
        with pytest.raises(StaleRevisionError, match="authority.*identity|identity.*authority"):
            getattr(owner, method_name)(request, expression, situation)
    finally:
        stores.close()


@pytest.mark.parametrize("requested,method_name", (("description", "describe"), ("description", "describe_with_proof"),
    ("definition", "describe"), ("definition", "describe_with_proof")),
    ids=("description-describe", "description-describe_with_proof", "definition-describe", "definition-describe_with_proof"))
def test_description_accepts_generation_rollover_without_rule_scan_but_rejects_later_identity_drift(linked_authority, monkeypatch, requested, method_name):
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.persistence import memory_stores, StaleRevisionError
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    new_generation = "authority:description-rollover"
    # Prepare a fresh store for the published generation; do not mutate an old
    # store's activation identity or issue an old-generation read against it.
    stores = memory_stores(authority_generation=new_generation)
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), linked_authority)
        original_key = owner._rule_index_key
        expression = _query_expression(requested=requested)
        old_situation = _situation(RevisionPin(linked_authority.generation, 0, 0, 0, 0, None))
        old_request = _request(expression, old_situation)
        linked_authority._publish_rule_generation(parent_generation=linked_authority.generation,
            new_generation=new_generation, new_content_hash="authority-content:description-rollover", rules=linked_authority.rules)
        def forbidden(*args, **kwargs):
            raise AssertionError("description rollover must not rescan or rebuild the rule index")
        monkeypatch.setattr(owner, "_refresh_rule_index", forbidden)
        with pytest.raises(StaleRevisionError, match="generation|pin"):
            getattr(owner, method_name)(old_request, expression, old_situation)
        situation = _situation(stores.revision_pin())
        request = _request(expression, situation)
        result = getattr(owner, method_name)(request, expression, situation)
        if method_name == "describe_with_proof":
            result = result[0]
        assert result.completeness is DescriptionCompleteness.MISSING
        assert owner._rule_index_key == original_key
        original = linked_authority.rule_generation_snapshot()
        generation, content_hash, rules = original
        replacement = (generation, content_hash, rules)
        assert replacement is not original and replacement == original
        object.__setattr__(linked_authority, "_rule_generation_state", replacement)
        with pytest.raises(StaleRevisionError, match="authority.*identity|identity.*authority"):
            getattr(owner, method_name)(request, expression, situation)
    finally:
        stores.close()


@pytest.mark.parametrize("field,method_name", (("content_hash", "describe"), ("content_hash", "describe_with_proof"),
    ("rules", "describe"), ("rules", "describe_with_proof")),
    ids=("content-hash-describe", "content-hash-describe-with-proof", "rules-describe", "rules-describe-with-proof"))
def test_description_rejects_observed_generation_content_or_rule_identity_drift(tmp_path, monkeypatch, field, method_name):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.persistence import memory_stores, StaleRevisionError
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    new_generation = "authority:description-observed-rollover"
    stores = memory_stores(authority_generation=new_generation)
    try:
        authority = SimpleNamespace(generation="authority:description-initial", content_hash="authority-content:initial",
            rules={}, atoms={}, capabilities={})
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        original_key = owner._rule_index_key
        authority.generation = new_generation
        authority.content_hash = "authority-content:observed-rollover"
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        request = _request(expression, situation)
        def forbidden(*args, **kwargs):
            raise AssertionError("description identity validation cannot rebuild the rule index")
        monkeypatch.setattr(owner, "_refresh_rule_index", forbidden)
        result = getattr(owner, method_name)(request, expression, situation)
        if method_name == "describe_with_proof":
            result = result[0]
        assert result.completeness is DescriptionCompleteness.MISSING
        assert owner._rule_index_key == original_key
        setattr(authority, field, "authority-content:forged" if field == "content_hash" else {})
        with pytest.raises(StaleRevisionError, match="same-generation authority identity drift"):
            getattr(owner, method_name)(request, expression, situation)
    finally:
        stores.close()


def _distinct_claim_expression(index, depth=1):
    leaf = SemanticApplication(f"local:leaf-{index}", "op:type", f"concept:class-{index}", (
        RoleBinding("role:instance", GroundedReference("entity:alice")),
        RoleBinding("role:class", GroundedReference(f"concept:class-{index}")),))
    applications = [leaf]
    for level in range(1, depth):
        applications.append(SemanticApplication(f"local:parent-{index}-{level}", "op:event", "event:assert", (
            RoleBinding("role:actor", GroundedReference("participant:reviewer")),
            RoleBinding("role:content", ApplicationFiller(applications[-1].application_ref)),)))
    return SemanticExpression.create(applications=tuple(applications), root_refs=(applications[-1].application_ref,))


def _seed_distinct_claim(stores, expression, index):
    from tests.test_foundation_description_builder import _seed_reviewed_generic_claim
    return _seed_reviewed_generic_claim(stores, expression, fact_ref=f"fact:bound-{index}",
        source_ref=f"source:bound-{index}", decision_ref=f"decision:bound-{index}",
        occurrence_ref=f"occurrence:bound-{index}", proof_refs=(f"proof:bound-{index}",))


@pytest.mark.parametrize("shape,amount,method_name,backend", (
    ("roots", 8, "describe", "memory"), ("roots", 9, "describe", "memory"),
    ("applications", 24, "describe", "memory"), ("applications", 25, "describe", "memory"),
    ("roots", 8, "describe_with_proof", "memory"), ("roots", 9, "describe_with_proof", "memory"),
    ("applications", 24, "describe_with_proof", "memory"), ("applications", 25, "describe_with_proof", "memory"),
    ("roots", 8, "describe", "sqlite"), ("roots", 9, "describe", "sqlite"),
    ("applications", 24, "describe", "sqlite"), ("applications", 25, "describe", "sqlite"),
    ("roots", 8, "describe_with_proof", "sqlite"), ("roots", 9, "describe_with_proof", "sqlite"),
    ("applications", 24, "describe_with_proof", "sqlite"), ("applications", 25, "describe_with_proof", "sqlite"),
), ids=("roots-8-plain-memory", "roots-9-plain-memory", "apps-24-plain-memory", "apps-25-plain-memory",
    "roots-8-proof-memory", "roots-9-proof-memory", "apps-24-proof-memory", "apps-25-proof-memory",
    "roots-8-plain-sqlite", "roots-9-plain-sqlite", "apps-24-plain-sqlite", "apps-25-plain-sqlite",
    "roots-8-proof-sqlite", "roots-9-proof-sqlite", "apps-24-proof-sqlite", "apps-25-proof-sqlite"))
def test_description_reconstruction_bounds_are_typed_after_all_claim_authentication(tmp_path, monkeypatch, shape, amount, method_name, backend):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid import r3_cognition
    from tests.test_foundation_description_builder import _stores
    stores = _stores(backend, tmp_path)
    try:
        if shape == "roots":
            expressions = tuple(_distinct_claim_expression(index) for index in range(amount))
        else:
            expressions = tuple(_distinct_claim_expression(index, 6) for index in range(4))
            if amount == 25:
                expressions += (_distinct_claim_expression(4),)
            assert len(expressions) <= 8
            assert sum(len(item.applications) for item in expressions) == amount
        claims = tuple(_seed_distinct_claim(stores, item, index) for index, item in enumerate(expressions))
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        request = _request(expression, situation, max_depth=6, max_facts=64)
        authority = SimpleNamespace(generation=request.revision_pin.authority_generation,
            content_hash="authority-content:description-test", rules={}, atoms={}, capabilities={})
        owner = r3_cognition.QueryDecisionOwner(stores, RuntimeConfig.release(), authority)
        authenticated, snapshots, postings = [], [], []
        original_verify, original_snapshot = r3_cognition._verify_description_claim, stores.r3_read_snapshot
        original_postings = r3_cognition.active_application_claims_for_target
        def verify(*args):
            original_verify(*args)
            authenticated.append(args[1].claim_ref)
        @contextmanager
        def snapshot(pin):
            snapshots.append(pin)
            with original_snapshot(pin):
                yield
        def target_read(*args, **kwargs):
            postings.append(args[1])
            return original_postings(*args, **kwargs)
        monkeypatch.setattr(r3_cognition, "_verify_description_claim", verify)
        monkeypatch.setattr(stores, "r3_read_snapshot", snapshot)
        monkeypatch.setattr(r3_cognition, "active_application_claims_for_target", target_read)
        before = stores.revisions()
        returned = getattr(owner, method_name)(request, expression, situation)
        result, bundle = returned if method_name == "describe_with_proof" else (returned, None)
        overflow = amount > (8 if shape == "roots" else 24)
        assert result.completeness is (DescriptionCompleteness.BUDGET_EXHAUSTED if overflow else DescriptionCompleteness.SUFFICIENT)
        assert sorted(authenticated) == sorted(claim.claim_ref for claim in claims)
        assert snapshots == [request.revision_pin] and postings == ["entity:alice"]
        assert stores.revisions() == before
        if overflow:
            assert result.answer_expression is None
            assert result.fact_refs == result.definition_refs == result.claim_refs == result.source_refs == result.proof_refs == ()
            if bundle is not None:
                assert bundle.claims == bundle.applications == bundle.application_refs == ()
        else:
            assert len(result.answer_expression.root_refs) == len(expressions)
            assert len(result.answer_expression.applications) == (amount if shape == "applications" else len(expressions))
        if bundle is not None:
            assert ProofBundle.from_dict(bundle.as_dict()) == bundle
    finally:
        stores.close()


@pytest.mark.parametrize("method_name", ("describe", "describe_with_proof"), ids=("plain", "proof"))
def test_description_root_overflow_does_not_hide_invalid_claim_lineage(tmp_path, method_name):
    from dataclasses import replace
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    from tests.test_foundation_description_builder import _stores, _physically_replace_fact
    stores = _stores("memory", tmp_path)
    try:
        claims = tuple(_seed_distinct_claim(stores, _distinct_claim_expression(index), index) for index in range(9))
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        request = _request(expression, situation, max_facts=64)
        authority = SimpleNamespace(generation=request.revision_pin.authority_generation,
            content_hash="authority-content:description-test", rules={}, atoms={}, capabilities={})
        fact = stores.world.get(claims[-1].claim_payload["fact_ref"])
        _physically_replace_fact(stores, "memory", replace(fact, proof={**fact.proof, "source": "source:forged"}))
        with pytest.raises(ValueError, match="description claim.*lineage"):
            getattr(QueryDecisionOwner(stores, RuntimeConfig.release(), authority), method_name)(request, expression, situation)
    finally:
        stores.close()


@pytest.mark.parametrize("method_name,backend", (("describe", "memory"), ("describe_with_proof", "memory"),
    ("describe", "sqlite"), ("describe_with_proof", "sqlite")),
    ids=("plain-memory", "proof-memory", "plain-sqlite", "proof-sqlite"))
def test_description_authenticated_nested_root_overlap_is_typed_budget(tmp_path, method_name, backend):
    from types import SimpleNamespace
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    from tests.test_foundation_description_builder import _stores
    stores = _stores(backend, tmp_path)
    try:
        _seed_distinct_claim(stores, _distinct_claim_expression(0), 0)
        _seed_distinct_claim(stores, _distinct_claim_expression(0, 2), 1)
        expression, situation = _query_expression(), _situation(stores.revision_pin())
        request = _request(expression, situation, max_depth=6, max_facts=64)
        authority = SimpleNamespace(generation=request.revision_pin.authority_generation,
            content_hash="authority-content:description-test", rules={}, atoms={}, capabilities={})
        returned = getattr(QueryDecisionOwner(stores, RuntimeConfig.release(), authority), method_name)(request, expression, situation)
        result, bundle = returned if method_name == "describe_with_proof" else (returned, None)
        assert result.completeness is DescriptionCompleteness.BUDGET_EXHAUSTED
        assert result.answer_expression is None
        assert result.fact_refs == result.definition_refs == result.claim_refs == result.source_refs == result.proof_refs == ()
        if bundle is not None:
            assert bundle.claims == bundle.applications == bundle.application_refs == ()
    finally:
        stores.close()


__cemm_test_inventory__ = {
    "tests/test_foundation_description_request_lineage.py::test_request_factory_binds_actual_canonical_expression_situation_and_budgets[description]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-binds-actual-canonical-expression-situation-and-budgets-description",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "49aad3a94adddd4fb44461644efc25011bed0c2787abd3838dd837aeafec50b0"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_factory_binds_actual_canonical_expression_situation_and_budgets[definition]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-binds-actual-canonical-expression-situation-and-budgets-definition",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "49aad3a94adddd4fb44461644efc25011bed0c2787abd3838dd837aeafec50b0"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_identity_covers_target_content_situation_pin_and_budgets": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-identity-covers-target-content-situation-pin-and-budgets",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "81de7676b1156c092c55e59a696950ef636358f886893be4729083d903aa1a0f"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_factory_rejects_proposition_or_mixed_query_sources[membership]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-rejects-proposition-or-mixed-query-sources-membership",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d9001b827019d6df27d9b17c8055efd4408d0f87ef4f12d37a15e01631bbe852"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_factory_rejects_proposition_or_mixed_query_sources[metadata]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-rejects-proposition-or-mixed-query-sources-metadata",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d9001b827019d6df27d9b17c8055efd4408d0f87ef4f12d37a15e01631bbe852"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_factory_rejects_proposition_or_mixed_query_sources[mixed]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-rejects-proposition-or-mixed-query-sources-mixed",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d9001b827019d6df27d9b17c8055efd4408d0f87ef4f12d37a15e01631bbe852"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_factory_rejects_nonquery_situation": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-rejects-nonquery-situation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "00f9ba2ef66ae5c96264f92d0c05b4bb0f84cc9ce2fa0e1a4a1d5b72fddd0d63"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_factory_rejects_scoped_projection": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-factory-rejects-scoped-projection",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "102ac4c6e19526d8b4244296c8db32a1c9ad1733859a002bd2bf2ec3a9cee14f"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_codecs_reject_exact_wire_string_type_violations[request-field-name]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-codecs-reject-exact-wire-string-type-violations-request-field-name",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1616e8f41614f9d30d24cf34159ec5f4f50de7eac9fd654fb9d0f87afbb3b4ff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_codecs_reject_exact_wire_string_type_violations[request-request-ref]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-codecs-reject-exact-wire-string-type-violations-request-request-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1616e8f41614f9d30d24cf34159ec5f4f50de7eac9fd654fb9d0f87afbb3b4ff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_codecs_reject_exact_wire_string_type_violations[request-pin-field-name]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-codecs-reject-exact-wire-string-type-violations-request-pin-field-name",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1616e8f41614f9d30d24cf34159ec5f4f50de7eac9fd654fb9d0f87afbb3b4ff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_codecs_reject_exact_wire_string_type_violations[result-field-name]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-codecs-reject-exact-wire-string-type-violations-result-field-name",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1616e8f41614f9d30d24cf34159ec5f4f50de7eac9fd654fb9d0f87afbb3b4ff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_codecs_reject_exact_wire_string_type_violations[result-result-ref]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-codecs-reject-exact-wire-string-type-violations-result-result-ref",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1616e8f41614f9d30d24cf34159ec5f4f50de7eac9fd654fb9d0f87afbb3b4ff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_codecs_reject_exact_wire_string_type_violations[result-completeness]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-codecs-reject-exact-wire-string-type-violations-result-completeness",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1616e8f41614f9d30d24cf34159ec5f4f50de7eac9fd654fb9d0f87afbb3b4ff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_result_rejects_nested_answer_wire_subclasses[mapping]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-result-rejects-nested-answer-wire-subclasses-mapping",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "55e7e20cb2238f5ecf7265156d6f3f34004ae4fa7d0129db1d97aaf5dd7e1be8"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_result_rejects_nested_answer_wire_subclasses[list]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-result-rejects-nested-answer-wire-subclasses-list",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "55e7e20cb2238f5ecf7265156d6f3f34004ae4fa7d0129db1d97aaf5dd7e1be8"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_result_rejects_nested_answer_wire_subclasses[string]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-result-rejects-nested-answer-wire-subclasses-string",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "55e7e20cb2238f5ecf7265156d6f3f34004ae4fa7d0129db1d97aaf5dd7e1be8"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_and_bundle_explicitly_reject_abi1[request]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-and-bundle-explicitly-reject-abi1-request",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "69208684e8bbd8372945abea412e3cea31392528f41064822f77456820c4afff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_and_bundle_explicitly_reject_abi1[result]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-and-bundle-explicitly-reject-abi1-result",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "69208684e8bbd8372945abea412e3cea31392528f41064822f77456820c4afff"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_and_bundle_explicitly_reject_abi1[bundle]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-and-bundle-explicitly-reject-abi1-bundle",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "69208684e8bbd8372945abea412e3cea31392528f41064822f77456820c4afff"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[source_expression_ref-query-wrong]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-source-expression-ref-query-wrong",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[source_situation_ref-situation-wrong]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-source-situation-ref-situation-wrong",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[source_projection_ref-projection-wrong-reference]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-source-projection-ref-projection-wrong-reference",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[target_ref-bare]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-target-ref-bare",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[requested_content-membership]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-requested-content-membership",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[max_depth-True]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-max-depth-true",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[max_facts-257]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-max-facts-257",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[abi_version-1]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-abi-version-1",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[revision_pin-value8]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-revision-pin-value8",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_request_codec_rejects_old_or_invalid_wire[source_query_ref-r3_query_result-old]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-request-codec-rejects-old-or-invalid-wire-source-query-ref-r3-query-result-old",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "46a35d53f622a0041ee1945bf849b3f9a166651040cb7866a8f0077e74930465"
    },
    "tests/test_foundation_description_request_lineage.py::test_rehashed_request_decoding_does_not_prove_actual_source_origin[target]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-rehashed-request-decoding-does-not-prove-actual-source-origin-target",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e01d3020260bc1fe645f4b2f4c3e2b9193cecfcbfe8204b204d1f29dd9b60879"
    },
    "tests/test_foundation_description_request_lineage.py::test_rehashed_request_decoding_does_not_prove_actual_source_origin[content]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-rehashed-request-decoding-does-not-prove-actual-source-origin-content",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e01d3020260bc1fe645f4b2f4c3e2b9193cecfcbfe8204b204d1f29dd9b60879"
    },
    "tests/test_foundation_description_request_lineage.py::test_rehashed_request_decoding_does_not_prove_actual_source_origin[expression]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-rehashed-request-decoding-does-not-prove-actual-source-origin-expression",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e01d3020260bc1fe645f4b2f4c3e2b9193cecfcbfe8204b204d1f29dd9b60879"
    },
    "tests/test_foundation_description_request_lineage.py::test_rehashed_request_decoding_does_not_prove_actual_source_origin[projection]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-rehashed-request-decoding-does-not-prove-actual-source-origin-projection",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e01d3020260bc1fe645f4b2f4c3e2b9193cecfcbfe8204b204d1f29dd9b60879"
    },
    "tests/test_foundation_description_request_lineage.py::test_rehashed_request_decoding_does_not_prove_actual_source_origin[situation]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-rehashed-request-decoding-does-not-prove-actual-source-origin-situation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e01d3020260bc1fe645f4b2f4c3e2b9193cecfcbfe8204b204d1f29dd9b60879"
    },
    "tests/test_foundation_description_request_lineage.py::test_rehashed_request_decoding_does_not_prove_actual_source_origin[pin]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-rehashed-request-decoding-does-not-prove-actual-source-origin-pin",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e01d3020260bc1fe645f4b2f4c3e2b9193cecfcbfe8204b204d1f29dd9b60879"
    },
    "tests/test_foundation_description_request_lineage.py::test_terminal_bundle_is_acyclic_request_lineage_without_final_query_backreference": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-terminal-bundle-is-acyclic-request-lineage-without-final-query-backreference",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "50d95dc7793a2ce7c72614ce7940be71359a82b598558dfd3738be830575653f"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_result_rejects_neighborhood_as_definition_authority": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-result-rejects-neighborhood-as-definition-authority",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c184674b2d9bb3f283ab57ca70c84fbfa4e246032b5296b309acc10e72e195d5"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_is_missing_even_when_same_target_description_is_sufficient[memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-is-missing-even-when-same-target-description-is-sufficient-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a44e104356c55a854f7b4780c1bb426c4745cbdb9a3a0b4903a5314afa706018"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_is_missing_even_when_same_target_description_is_sufficient[sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-is-missing-even-when-same-target-description-is-sufficient-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a44e104356c55a854f7b4780c1bb426c4745cbdb9a3a0b4903a5314afa706018"
    },
    "tests/test_foundation_description_request_lineage.py::test_component_rejects_old_unknown_queryresult_source_before_read": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-component-rejects-old-unknown-queryresult-source-before-read",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "e1f03f0c0ee244d738bf730cacf5c01f6d0aca4d439960f77cc3339d7bf5ae50"
    },
    "tests/test_foundation_description_request_lineage.py::test_component_preserves_single_pinned_read_and_no_preliminary_query[description-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-component-preserves-single-pinned-read-and-no-preliminary-query-description-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d35464dd60c1328e7af758e41961f5e9175454bd3bb08d239f1215b284088101"
    },
    "tests/test_foundation_description_request_lineage.py::test_component_preserves_single_pinned_read_and_no_preliminary_query[description-describe_with_proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-component-preserves-single-pinned-read-and-no-preliminary-query-description-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d35464dd60c1328e7af758e41961f5e9175454bd3bb08d239f1215b284088101"
    },
    "tests/test_foundation_description_request_lineage.py::test_component_preserves_single_pinned_read_and_no_preliminary_query[definition-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-component-preserves-single-pinned-read-and-no-preliminary-query-definition-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d35464dd60c1328e7af758e41961f5e9175454bd3bb08d239f1215b284088101"
    },
    "tests/test_foundation_description_request_lineage.py::test_component_preserves_single_pinned_read_and_no_preliminary_query[definition-describe_with_proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-component-preserves-single-pinned-read-and-no-preliminary-query-definition-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "d35464dd60c1328e7af758e41961f5e9175454bd3bb08d239f1215b284088101"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_missing_still_rejects_same_generation_authority_drift[before-content_hash]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-missing-still-rejects-same-generation-authority-drift-before-content-hash",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c1288ce7199571e876398631955e579d85e7ff544c11b99aac619b28a21229ef"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_missing_still_rejects_same_generation_authority_drift[before-rules]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-missing-still-rejects-same-generation-authority-drift-before-rules",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c1288ce7199571e876398631955e579d85e7ff544c11b99aac619b28a21229ef"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_missing_still_rejects_same_generation_authority_drift[during-content_hash]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-missing-still-rejects-same-generation-authority-drift-during-content-hash",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c1288ce7199571e876398631955e579d85e7ff544c11b99aac619b28a21229ef"
    },
    "tests/test_foundation_description_request_lineage.py::test_definition_missing_still_rejects_same_generation_authority_drift[during-rules]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-definition-missing-still-rejects-same-generation-authority-drift-during-rules",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c1288ce7199571e876398631955e579d85e7ff544c11b99aac619b28a21229ef"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_linked_snapshot_identity_replacement_before_read[description-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-linked-snapshot-identity-replacement-before-read-description-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a47c7366e2761a1dd2a381a276b69629474983b8b471b303ffba2d30dadbe846"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_linked_snapshot_identity_replacement_before_read[description-describe_with_proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-linked-snapshot-identity-replacement-before-read-description-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a47c7366e2761a1dd2a381a276b69629474983b8b471b303ffba2d30dadbe846"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_linked_snapshot_identity_replacement_before_read[definition-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-linked-snapshot-identity-replacement-before-read-definition-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a47c7366e2761a1dd2a381a276b69629474983b8b471b303ffba2d30dadbe846"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_linked_snapshot_identity_replacement_before_read[definition-describe_with_proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-linked-snapshot-identity-replacement-before-read-definition-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "a47c7366e2761a1dd2a381a276b69629474983b8b471b303ffba2d30dadbe846"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_accepts_generation_rollover_without_rule_scan_but_rejects_later_identity_drift[description-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-accepts-generation-rollover-without-rule-scan-but-rejects-later-identity-drift-description-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "208ff2868a14b16063d3c3f7c7627f879933f9fedfaf03418bcbbe35232336fd"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_accepts_generation_rollover_without_rule_scan_but_rejects_later_identity_drift[description-describe_with_proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-accepts-generation-rollover-without-rule-scan-but-rejects-later-identity-drift-description-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "208ff2868a14b16063d3c3f7c7627f879933f9fedfaf03418bcbbe35232336fd"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_accepts_generation_rollover_without_rule_scan_but_rejects_later_identity_drift[definition-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-accepts-generation-rollover-without-rule-scan-but-rejects-later-identity-drift-definition-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "208ff2868a14b16063d3c3f7c7627f879933f9fedfaf03418bcbbe35232336fd"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_accepts_generation_rollover_without_rule_scan_but_rejects_later_identity_drift[definition-describe_with_proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-accepts-generation-rollover-without-rule-scan-but-rejects-later-identity-drift-definition-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "208ff2868a14b16063d3c3f7c7627f879933f9fedfaf03418bcbbe35232336fd"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_observed_generation_content_or_rule_identity_drift[content-hash-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-observed-generation-content-or-rule-identity-drift-content-hash-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c80347f015d1c4426f7223fa7b08c6133e33b0154f2572d0e6f73a4e3be40196"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_observed_generation_content_or_rule_identity_drift[content-hash-describe-with-proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-observed-generation-content-or-rule-identity-drift-content-hash-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c80347f015d1c4426f7223fa7b08c6133e33b0154f2572d0e6f73a4e3be40196"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_observed_generation_content_or_rule_identity_drift[rules-describe]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-observed-generation-content-or-rule-identity-drift-rules-describe",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c80347f015d1c4426f7223fa7b08c6133e33b0154f2572d0e6f73a4e3be40196"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_rejects_observed_generation_content_or_rule_identity_drift[rules-describe-with-proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-rejects-observed-generation-content-or-rule-identity-drift-rules-describe-with-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "c80347f015d1c4426f7223fa7b08c6133e33b0154f2572d0e6f73a4e3be40196"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-8-plain-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-8-plain-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-9-plain-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-9-plain-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-24-plain-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-24-plain-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-25-plain-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-25-plain-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-8-proof-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-8-proof-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-9-proof-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-9-proof-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-24-proof-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-24-proof-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-25-proof-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-25-proof-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-8-plain-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-8-plain-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-9-plain-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-9-plain-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-24-plain-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-24-plain-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-25-plain-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-25-plain-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-8-proof-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-8-proof-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[roots-9-proof-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-roots-9-proof-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-24-proof-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-24-proof-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_reconstruction_bounds_are_typed_after_all_claim_authentication[apps-25-proof-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-reconstruction-bounds-are-typed-after-all-claim-authentication-apps-25-proof-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "3faf94fdddf0d3bdd4a8ce6a2df539913e6c926d460166dba24532eab2cbc37e"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_root_overflow_does_not_hide_invalid_claim_lineage[plain]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-root-overflow-does-not-hide-invalid-claim-lineage-plain",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1e33ef509df787812e81a10baaaa56ead33e93dec6ebebbba796e54b19f9e717"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_root_overflow_does_not_hide_invalid_claim_lineage[proof]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-root-overflow-does-not-hide-invalid-claim-lineage-proof",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "1e33ef509df787812e81a10baaaa56ead33e93dec6ebebbba796e54b19f9e717"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_authenticated_nested_root_overlap_is_typed_budget[plain-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-authenticated-nested-root-overlap-is-typed-budget-plain-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ada26f06e8a78b2d2ffdedeb3623e6ad1d16ad22b32c2234dbe19fcc17691767"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_authenticated_nested_root_overlap_is_typed_budget[proof-memory]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-authenticated-nested-root-overlap-is-typed-budget-proof-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ada26f06e8a78b2d2ffdedeb3623e6ad1d16ad22b32c2234dbe19fcc17691767"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_authenticated_nested_root_overlap_is_typed_budget[plain-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-authenticated-nested-root-overlap-is-typed-budget-plain-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ada26f06e8a78b2d2ffdedeb3623e6ad1d16ad22b32c2234dbe19fcc17691767"
    },
    "tests/test_foundation_description_request_lineage.py::test_description_authenticated_nested_root_overlap_is_typed_budget[proof-sqlite]": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:foundation-test-description-authenticated-nested-root-overlap-is-typed-budget-proof-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-7",
        "owner_ref": "decision-query-proof",
        "source_ast_sha256": "ada26f06e8a78b2d2ffdedeb3623e6ad1d16ad22b32c2234dbe19fcc17691767"
    }
}
