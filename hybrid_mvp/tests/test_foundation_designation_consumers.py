"""Actual runtime reuse of independently published alias evidence."""
import pytest
from dataclasses import replace
import secrets

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.r3_artifacts import QueryStatus
from cemm_authoritative_hybrid import persistence
from cemm_authoritative_hybrid.r3_learning import AliasReviewVerifier
from cemm_authoritative_hybrid.r3_effects import R3EffectGateway, AdapterRegistry
from tests.test_foundation_alias_publication import _publication, _signed
from tests.test_foundation_admitted_designations import _physically_corrupt_fact_for_integrity_test
from tests.test_foundation_learning_proposal import ROOT
from tests.test_foundation_semantics import _matrix_expression, _matrix_relation

__cemm_test_inventory__ = {
    "tests/test_foundation_designation_consumers.py::test_publication_reopen_reaches_all_runtime_consumers[relation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:publication-reopen-reaches-all-runtime-consumers-relation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "9e7491756a34df0ace572fff0efbf85feb807ea3a6860667f18a87853b765cf5"
    },
    "tests/test_foundation_designation_consumers.py::test_publication_reopen_reaches_all_runtime_consumers[lexical]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:publication-reopen-reaches-all-runtime-consumers-lexical",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "9e7491756a34df0ace572fff0efbf85feb807ea3a6860667f18a87853b765cf5"
    },
    "tests/test_foundation_designation_consumers.py::test_publication_reopen_reaches_all_runtime_consumers[designation]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:publication-reopen-reaches-all-runtime-consumers-designation",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "9e7491756a34df0ace572fff0efbf85feb807ea3a6860667f18a87853b765cf5"
    },
    "tests/test_foundation_designation_consumers.py::test_runtime_consumers_ignore_naked_and_reject_corrupt_publication[fakeword]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:runtime-consumers-ignore-naked-and-reject-corrupt-publication-fakeword",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "6b85ae561fc352d146784f6e17af1359639c760b2aeeebcd0f8c47cac13e3fae"
    },
    "tests/test_foundation_designation_consumers.py::test_runtime_consumers_ignore_naked_and_reject_corrupt_publication[velnora]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:runtime-consumers-ignore-naked-and-reject-corrupt-publication-velnora",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "6b85ae561fc352d146784f6e17af1359639c760b2aeeebcd0f8c47cac13e3fae"
    },
    "tests/test_foundation_designation_consumers.py::test_orient_consumers_share_one_live_snapshot_and_reader_with_query": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:orient-consumers-share-one-live-snapshot-and-reader-with-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "b95b39ace7a6cd9de2237cce9ba415785f82618507522780b12915bfd811fb84"
    },
    "tests/test_foundation_designation_consumers.py::test_consumer_inputs_reject_foreign_reader_and_batch": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:consumer-inputs-reject-foreign-reader-and-batch",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f7a7543b3619da25e8e043c9325c3ac5452d7ec1cbaa17abe1be71e5ae71514a"
    },
    "tests/test_foundation_designation_consumers.py::test_grounding_aggregate_budget_is_explicit_not_partial_success[at-bound]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:grounding-aggregate-budget-is-explicit-not-partial-success-at-bound",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "99cad0bab5e187b240b694b08f23b76f190f1fb7928340f8ae1efd5ee775ff24"
    },
    "tests/test_foundation_designation_consumers.py::test_grounding_aggregate_budget_is_explicit_not_partial_success[overflow]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:grounding-aggregate-budget-is-explicit-not-partial-success-overflow",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "99cad0bab5e187b240b694b08f23b76f190f1fb7928340f8ae1efd5ee775ff24"
    },
    "tests/test_foundation_designation_consumers.py::test_signed_unicode_multilingual_alias_retains_canonical_surface_and_source_geometry[unicode-expansion]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:signed-unicode-multilingual-alias-retains-canonical-surface-and-source-geometry-unicode-expansion",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "821ea52a1065e3001b4b88b0542a95834e9ebcb8ab61227e75b1885cd2b0c65e"
    },
    "tests/test_foundation_designation_consumers.py::test_signed_unicode_multilingual_alias_retains_canonical_surface_and_source_geometry[spanish]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:signed-unicode-multilingual-alias-retains-canonical-surface-and-source-geometry-spanish",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "821ea52a1065e3001b4b88b0542a95834e9ebcb8ab61227e75b1885cd2b0c65e"
    },
    "tests/test_foundation_designation_consumers.py::test_static_admitted_collisions_keep_exact_precedence_and_canonical_identity": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:static-admitted-collisions-keep-exact-precedence-and-canonical-identity",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "46874f702a103226ee29966c29bf023e0eb91b3e6ccf73da5006b9925fb939a6"
    },
    "tests/test_foundation_designation_consumers.py::test_runtime_lookup_work_is_indexed_under_irrelevant_world_growth[grounding]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:runtime-lookup-work-is-indexed-under-irrelevant-world-growth-grounding",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1491ab9655a612dbcb2cbded97faa1157329614ec0ec208f7ff9540b83d2e949"
    },
    "tests/test_foundation_designation_consumers.py::test_runtime_lookup_work_is_indexed_under_irrelevant_world_growth[query]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:runtime-lookup-work-is-indexed-under-irrelevant-world-growth-query",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1491ab9655a612dbcb2cbded97faa1157329614ec0ec208f7ff9540b83d2e949"
    },
    "tests/test_foundation_designation_consumers.py::test_runtime_lookup_work_is_indexed_under_irrelevant_world_growth[canonical]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:runtime-lookup-work-is-indexed-under-irrelevant-world-growth-canonical",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "1491ab9655a612dbcb2cbded97faa1157329614ec0ec208f7ff9540b83d2e949"
    },
    "tests/test_foundation_designation_consumers.py::test_lexical_query_reads_at_exact_situation_snapshot_not_cached_pin": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:lexical-query-reads-at-exact-situation-snapshot-not-cached-pin",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "708d604bb4f06fe1ce8013c7aa670092abb4761d62b0910d494e0dd5c423d86f"
    },
    "tests/test_foundation_designation_consumers.py::test_public_lexical_query_retains_typed_retrieval_overflow": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:public-lexical-query-retains-typed-retrieval-overflow",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "0825f3fd658c8dfda5661941291d081ee66fddf6737a007b629ebe60708f6962"
    },
    "tests/test_foundation_designation_consumers.py::test_memory_public_consumers_require_explicit_trusted_binding": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:memory-public-consumers-require-explicit-trusted-binding",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "8c8d18cc373dcdb3cd6627519b1b1e004d54ba49aa4768aa687e99f119b57e62"
    }
}


def _publish_alias(runtime, surface, target_surface, target_ref, language="en", session="session:custom-alias"):
    """Signed independent test review over real public query/directive artifacts."""
    source = runtime.process(session, f"What does {surface} mean?")
    assert source.evaluation.query_results[0].status is QueryStatus.UNKNOWN
    snapshot = runtime.stores.r3_obligation_snapshot(session, maximum=16)
    pending, = runtime.stores.pending_dialogue_obligations(session, tuple(snapshot["obligation_refs"]),
        maximum=16, turn_index=source.evaluation.situation.turn_index)
    proposal = runtime.process(session, f"learn {surface} means {target_surface}")
    plan = proposal.response_meaning.learning_plan
    journal = runtime.stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
    secret = secrets.token_bytes(32)
    binding = runtime.stores.learning_store_binding or "trusted-process:test-publication"
    policy = runtime.authority.learning_contract_for_source("op:event", "event:learn_alias").review_policy_ref
    grant = {"proposal_key": proposal.effect_receipt.idempotency_key,
        "proposal_journal_ref": journal["entry"]["journal_ref"],
        "proposal_receipt_ref": proposal.effect_receipt.receipt_ref, "plan_ref": plan.plan_ref,
        "source_obligation_ref": pending.obligation_ref, "source_query_ref": pending.source_query_ref,
        "source_journal_ref": journal["entry"]["request_payload"]["learning_source_journal"]["entry"]["journal_ref"],
        "surface": surface, "target_ref": target_ref, "language": language,
        "reviewer_ref": "reviewer:test", "policy_ref": policy, "key_ref": "key:test-reviewer",
        "store_binding": binding, "nonce": secrets.token_hex(24), "expires_at_turn": pending.expires_turn_index}
    verifier = AliasReviewVerifier(key=secret, key_ref=grant["key_ref"], reviewer_ref=grant["reviewer_ref"],
        policy_ref=policy, store_binding=binding)
    gateway = R3EffectGateway(runtime.stores, AdapterRegistry(), authority=runtime.authority,
        review_verifier=verifier, memory_review_binding=binding if runtime.stores.learning_store_binding is None else None)
    return gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))


@pytest.mark.parametrize("consumer", ("relation", "lexical", "designation"), ids=("relation", "lexical", "designation"))
def test_publication_reopen_reaches_all_runtime_consumers(tmp_path, monkeypatch, consumer):
    runtime, source, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    forms = (ROOT / "data/languages/en/forms.json").read_bytes()
    atoms = dict(runtime.authority.atoms)
    source_history = runtime.stores.r3_effect_journal_get(source.effect_receipt.idempotency_key)
    answer_history = runtime.stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
    before = runtime.stores.revision_pin()
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    after = runtime.stores.revision_pin()
    assert before.world_revision == 0 and after.world_revision == 1
    assert (before.session_revision, before.episode_revision) == (after.session_revision, after.episode_revision)
    runtime.stores.close()
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        text = {"relation": "Bob velnora Alice.", "lexical": "What does velnora mean?", "designation": "VELNORA"}[consumer]
        result = runtime.process("session:reuse", text)
        meaning = result.verification.selected_meaning
        assert meaning is not None
        if consumer == "relation":
            assert meaning.expression == _matrix_expression(_matrix_relation("entity:bob", "entity:alice"))
        elif consumer == "lexical":
            query = result.evaluation.query_results[0]
            assert query.status is QueryStatus.SUPPORTED
            assert query.proof is not None
            assert receipt.committed_fact_refs[0] in tuple(ref for node in query.proof.nodes for ref in node.source_fact_refs)
            assert receipt.receipt_ref in query.proof.source_refs
        else:
            app, = meaning.expression.applications
            assert app.operator == "op:designation" and app.predicate_ref == "label:lexical"
            roles = {row.role_ref: row.filler for row in app.roles}
            assert roles["role:surface"].value == "velnora"
            assert roles["role:target"].target_ref == "rel:likes"
        assert runtime.stores.r3_effect_journal_get(source.effect_receipt.idempotency_key) == source_history
        assert runtime.stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key) == answer_history
        assert runtime.stores.world.revision == 1
        assert dict(runtime.authority.atoms) == atoms
        assert (ROOT / "data/languages/en/forms.json").read_bytes() == forms
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("surface", ("fakeword", "velnora"), ids=("fakeword", "velnora"))
def test_runtime_consumers_ignore_naked_and_reject_corrupt_publication(tmp_path, monkeypatch, surface):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    try:
        fact = runtime.stores.world.get(receipt.committed_fact_refs[0])
        changed = (replace(fact, fact_ref="fact:naked", args={**fact.args, "role:surface": surface},
            proof={"source": "reviewer:trusted", "alias_language": "en"}) if surface == "fakeword" else
            replace(fact, proof={**fact.proof, "publication_key": "missing:publication"}))
        if surface == "fakeword":
            runtime.stores.world.commit((changed,), expected_revision=runtime.stores.world.revision)
        else:
            original_pin = runtime.stores.revision_pin()
            with pytest.raises(ValueError, match="immutable"):
                runtime.stores.world.commit((changed,), expected_revision=runtime.stores.world.revision)
            assert runtime.stores.revision_pin() == original_pin
            assert runtime.stores.world.get(fact.fact_ref) == fact
            # Isolated physical corruption is integrity-test setup, not a
            # supported public mutation or authenticated review authority.
            _physically_corrupt_fact_for_integrity_test(runtime.stores, "sqlite", changed)
        pin = runtime.stores.revision_pin()
        if surface == "fakeword":
            _, context = runtime.orient("session:naked", surface)
            assert not context.designation_slots
            result = runtime.process("session:naked", "What does fakeword mean?")
            assert result.evaluation.query_results[0].status is QueryStatus.UNKNOWN
        else:
            with pytest.raises(ValueError, match="committed journal"):
                runtime.orient("session:corrupt", surface)
            assert runtime.stores.revision_pin() == pin
    finally:
        runtime.stores.close()


def test_orient_consumers_share_one_live_snapshot_and_reader_with_query(tmp_path, monkeypatch):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation)
    try:
        orienter = runtime._owners["orientation"]
        query = runtime._owners["r3"]._evaluator._owners[next(mode for mode in runtime._owners["r3"]._evaluator._owners if mode.value == "QUERY")]
        assert query._designation_reader is orienter._designation_reader
        ground = orienter._grounder.ground_lattice
        build = orienter._context_builder.build
        captured = []
        def ground_then_peer(*args, **kwargs):
            result = ground(*args, **kwargs)
            captured.append(kwargs["designation_batch"])
            peer.world.commit((persistence.Fact("fact:peer", "op:type", {}),), expected_revision=peer.world.revision)
            return result
        def build_same(**kwargs):
            assert kwargs["designation_batch"] is captured[0]
            assert captured[0].active
            return build(**kwargs)
        monkeypatch.setattr(orienter._grounder, "ground_lattice", ground_then_peer)
        monkeypatch.setattr(orienter._context_builder, "build", build_same)
        orientation, context = runtime.orient("session:snapshot", "VELNORA")
        assert orientation.revision_pin.world_revision == context.revision_pin.world_revision == 1
        assert any(row.literal_value == "velnora" for row in context.contribution_slots)
        assert not captured[0].active
        with pytest.raises(persistence.StaleRevisionError):
            runtime.orient("session:snapshot", "VELNORA")
    finally:
        peer.close()
        runtime.stores.close()


def test_consumer_inputs_reject_foreign_reader_and_batch(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.r3_cognition import QueryDecisionOwner
    from cemm_authoritative_hybrid.runtime import RuntimeOrientationOwner
    first = load_runtime(ROOT, profile="development", store_path=tmp_path / "first.db")
    second = load_runtime(ROOT, profile="development", store_path=tmp_path / "second.db")
    try:
        orienter = first._owners["orientation"]
        foreign = second._owners["orientation"]._designation_reader
        with pytest.raises(ValueError, match="reader.*owner"):
            QueryDecisionOwner(first.stores, first._config, first.authority, designation_reader=foreign)
        with pytest.raises(ValueError, match="reader.*owner"):
            RuntimeOrientationOwner(authority=first.authority, stores=first.stores, config=first._config,
                form_resolver=orienter._form_resolver, grounder=orienter._grounder,
                contribution_expander=orienter._contribution_expander, context_builder=orienter._context_builder,
                designation_reader=foreign)
        evidence = orienter.text_evidence("session:batch", "hello")
        lattice = orienter._form_resolver.resolve_evidence(evidence)
        pin = first.stores.revision_pin()
        with foreign.batch(second.stores.revision_pin()) as batch:
            with pytest.raises(ValueError, match="batch.*owner"):
                orienter._grounder.ground_lattice(lattice, pin, designation_batch=batch)
        with orienter._designation_reader.batch(pin) as batch:
            with pytest.raises(ValueError, match="batch.*pin"):
                orienter._grounder.ground_lattice(lattice, replace(pin, world_revision=1), designation_batch=batch)
        captured = {}
        build = orienter._context_builder.build
        def capture(**kwargs):
            captured.update(kwargs)
            return build(**kwargs)
        monkeypatch.setattr(orienter._context_builder, "build", capture)
        first.orient("session:batch", "hello")
        with foreign.batch(second.stores.revision_pin()) as batch:
            with pytest.raises(ValueError, match="batch.*owner"):
                build(**{**captured, "designation_batch": batch})
    finally:
        first.stores.close()
        second.stores.close()


@pytest.mark.parametrize("total", (512, 513), ids=("at-bound", "overflow"))
def test_grounding_aggregate_budget_is_explicit_not_partial_success(form_pack, linked_authority, total):
    from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.gaps import BudgetExhausted
    config = RuntimeConfig.release()
    resolver = FormResolver(form_pack, config)
    # Every contiguous span has valid immutable evidence; the global bound is
    # exceeded although each individual span has only three interpretations.
    words = tuple(f"w{i}" for i in range(32))
    facts = tuple(DesignationFact.create(surface=" ".join(words[start:end]), target_ref=target, language="en")
        for start in range(len(words)) for end in range(start + 1, min(start + 8, len(words)) + 1)
        for target in ("rel:likes", "rel:knows", "concept:mother"))
    linked_authority.designations = DesignationIndex(facts[:total])
    grounder = Grounder(linked_authority, config, form_pack=form_pack)
    pin = persistence.RevisionPin(linked_authority.generation, 0, 0, 0, 0, "bootstrap-proposer")
    if total == 512:
        assert len(grounder.ground_lattice(resolver.resolve(" ".join(words)), pin).designations) == total
    else:
        with pytest.raises(BudgetExhausted):
            grounder.ground_lattice(resolver.resolve(" ".join(words)), pin)


@pytest.mark.parametrize("surface,language,observed", (("Straße", "en", "STRASSE"), ("nuvemóra", "es", "NUVEMÓRA")), ids=("unicode-expansion", "spanish"))
def test_signed_unicode_multilingual_alias_retains_canonical_surface_and_source_geometry(tmp_path, surface, language, observed):
    import json
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    from cemm_authoritative_hybrid.proposal_context import ProposalContextBuilder
    from cemm_authoritative_hybrid.runtime import RuntimeOrientationOwner
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "unicode.db")
    try:
        receipt = _publish_alias(runtime, surface, "mother", "concept:mother", language)
        pack = json.loads((ROOT / f"data/languages/{language}/forms.json").read_text(encoding="utf-8"))
        config = runtime._config
        resolver = FormResolver(pack, config)
        affordances = SemanticAffordanceIndex(runtime.authority, config)
        reader = runtime._owners["orientation"]._designation_reader
        orienter = RuntimeOrientationOwner(authority=runtime.authority, stores=runtime.stores, config=config,
            form_resolver=resolver, grounder=Grounder(runtime.authority, config, form_pack=pack),
            contribution_expander=ContributionExpander(affordances, config),
            context_builder=ProposalContextBuilder(runtime.authority, affordances, config, form_pack=pack),
            designation_reader=reader)
        runtime._owners["orientation"] = orienter
        _, context = runtime.orient("session:unicode", observed)
        slot, = context.designation_slots
        spans = {ref: (start, end) for ref, start, end in context.source_unit_spans}
        start = min(spans[ref][0] for ref in slot.source_unit_refs)
        end = max(spans[ref][1] for ref in slot.source_unit_refs)
        assert observed[start:end] == observed
        assert receipt.committed_fact_refs[0] in slot.provenance_refs
        assert any(row.literal_value == surface for row in context.contribution_slots)
        result = runtime.process("session:unicode", observed)
        app, = result.verification.selected_meaning.expression.applications
        assert app.operator == "op:designation"
        assert {row.role_ref: row.filler for row in app.roles}["role:surface"].value == surface
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()


def test_static_admitted_collisions_keep_exact_precedence_and_canonical_identity(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
    from cemm_authoritative_hybrid.r3_learning import AdmittedDesignationReader
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    try:
        # Explicit static collision fixture: no raw world fact is being granted
        # authority and no checked-in authority or form pack is modified.
        original = tuple(runtime.authority.designations._facts_by_ref.values())
        upper = DesignationFact.create(surface="VELNORA", target_ref="rel:likes", language="en")
        other = DesignationFact.create(surface="velnora", target_ref="concept:mother", language="en")
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((*original, upper, other)))
        reader = AdmittedDesignationReader(runtime.authority, runtime.stores)
        orienter = runtime._owners["orientation"]
        monkeypatch.setattr(orienter, "_designation_reader", reader)
        query_owner = runtime._owners["r3"]._evaluator._owners[next(mode for mode in runtime._owners["r3"]._evaluator._owners if mode.value == "QUERY")]
        monkeypatch.setattr(query_owner, "_designation_reader", reader)
        _, upper_context = runtime.orient("session:collision", "VELNORA")
        assert [row.designation_fact_ref for row in upper_context.designation_slots] == [upper.designation_fact_ref]
        assert [row.literal_value for row in upper_context.contribution_slots if row.kind == "literal"] == ["VELNORA"]
        _, lower_context = runtime.orient("session:collision", "velnora")
        assert {row.target_ref for row in lower_context.designation_slots} == {"rel:likes", "concept:mother"}
        learned = next(row for row in lower_context.designation_slots if row.target_ref == "rel:likes")
        assert receipt.committed_fact_refs[0] in learned.provenance_refs
        assert all(row.literal_value == "velnora" for row in lower_context.contribution_slots if row.kind == "literal")
        _, folded = runtime.orient("session:collision", "Velnora")
        assert len(folded.designation_slots) == 3
        result = runtime.process("session:collision", "What does velnora mean?")
        query = result.evaluation.query_results[0]
        assert query.status is QueryStatus.PARTIAL and query.bindings == () and query.proof is None
        assert receipt.committed_fact_refs[0] in query.retrieval_refs
        assert other.designation_fact_ref in query.retrieval_refs
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("text", ("Bob velnora Alice.", "What does velnora mean?", "VELNORA"), ids=("grounding", "query", "canonical"))
def test_runtime_lookup_work_is_indexed_under_irrelevant_world_growth(tmp_path, monkeypatch, text):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    stores = runtime.stores
    try:
        original = persistence.SemanticStores.r3_designation_facts
        rows_read = []
        def measured(owner, *args, **kwargs):
            result = original(owner, *args, **kwargs)
            rows_read.append(len(result))
            return result
        monkeypatch.setattr(persistence.SemanticStores, "r3_designation_facts", measured)
        measurements = []
        conn = stores._backend._conn
        for count in (0, 128, 2048):
            if count:
                stores.world.commit(tuple(persistence.Fact(f"fact:irrelevant:{count}:{i}", "op:designation",
                    {"role:surface": f"unrelated-{count}-{i}", "role:target": "concept:other"},
                    proof={"alias_language": "fr"}) for i in range(count)), expected_revision=stores.world.revision)
            statements, steps = [], []
            rows_read.clear()
            conn.set_trace_callback(lambda sql: statements.append((len(steps), sql)))
            conn.set_progress_handler(lambda: steps.append(1) or 0, 1)
            result = runtime.process(f"session:work:{count}", text)
            conn.set_trace_callback(None)
            conn.set_progress_handler(None, 0)
            assert result.verification.selected_meaning is not None
            world_steps, world_queries = 0, []
            for index, (start, sql) in enumerate(statements):
                if "FROM world_facts" in sql:
                    finish = statements[index + 1][0] if index + 1 < len(statements) else len(steps)
                    world_steps += finish - start
                    world_queries.append(sql)
                    plan = " ".join(row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql))
                    assert "SEARCH" in plan and "SCAN" not in plan and "TEMP" not in plan, plan
            measurements.append((len(world_queries), sum(rows_read), world_steps))
        assert len({(queries, rows) for queries, rows, _ in measurements}) == 1, measurements
        assert max(row[2] for row in measurements) - min(row[2] for row in measurements) < 80, measurements
        print("runtime designation SQL work", text, measurements)
    finally:
        stores.close()


def test_lexical_query_reads_at_exact_situation_snapshot_not_cached_pin(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.expression_projection import project_expression
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation)
    try:
        orienter = runtime._owners["orientation"]
        turn = orienter.orient_turn("session:query-pin", orienter.text_evidence("session:query-pin", "What does velnora mean?"))
        situation = runtime._owners["r3"]._situation_builder.build(turn.orientation, turn.context, **turn.situation_inputs.as_kwargs())
        from tests.test_foundation_semantics import _matrix_designation_query
        expression = _matrix_designation_query("velnora")
        owner = runtime._owners["r3"]._evaluator._owners[situation.mode]
        positive = owner.evaluate_full(expression, project_expression(expression), situation)
        assert positive.query_results[0].status is QueryStatus.SUPPORTED
        peer.world.commit((persistence.Fact("fact:query-peer", "op:type", {}),), expected_revision=peer.world.revision)
        assert runtime.stores.revision_pin() == situation.revision_pin
        with pytest.raises(persistence.StaleRevisionError):
            owner.evaluate_full(expression, project_expression(expression), situation)
    finally:
        peer.close()
        runtime.stores.close()


def test_public_lexical_query_retains_typed_retrieval_overflow(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
    runtime = load_runtime(ROOT, profile="development", store_path=tmp_path / "overflow.db")
    try:
        original = tuple(runtime.authority.designations._facts_by_ref.values())
        alternatives = tuple(DesignationFact.create(surface="ambigword", target_ref="concept:mother", language=f"lang-{i}") for i in range(17))
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((*original, *alternatives)))
        result = runtime.process("session:overflow", "What does ambigword mean?")
        query = result.evaluation.query_results[0]
        assert query.status is QueryStatus.PARTIAL
        assert query.bindings == () and query.proof is None
        assert "query:designation_retrieval_overflow" in result.evaluation.decision.blocker_refs
        assert runtime.stores.world.revision == 0
    finally:
        runtime.stores.close()


def test_memory_public_consumers_require_explicit_trusted_binding(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.r3_learning import AdmittedDesignationReader
    from cemm_authoritative_hybrid.runtime import RuntimeOrientationOwner
    from cemm_authoritative_hybrid.r3_kernel import R3Kernel
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    try:
        with pytest.raises(ValueError, match="trusted store"):
            runtime.orient("session:untrusted", "velnora")
        old = runtime._owners["orientation"]
        reader = AdmittedDesignationReader(runtime.authority, runtime.stores,
            memory_review_binding="trusted-process:test-publication")
        runtime._owners["orientation"] = RuntimeOrientationOwner(authority=runtime.authority,
            stores=runtime.stores, config=runtime._config, form_resolver=old._form_resolver,
            grounder=old._grounder, contribution_expander=old._contribution_expander,
            context_builder=old._context_builder, designation_reader=reader)
        runtime._owners["r3"] = R3Kernel(authority=runtime.authority, stores=runtime.stores,
            config=runtime._config, designation_reader=reader)
        relation = runtime.process("session:memory", "Bob velnora Alice.")
        assert relation.verification.selected_meaning.expression == _matrix_expression(_matrix_relation("entity:bob", "entity:alice"))
        designation = runtime.process("session:memory", "VELNORA")
        app, = designation.verification.selected_meaning.expression.applications
        assert {row.role_ref: row.filler for row in app.roles}["role:surface"].value == "velnora"
        query = runtime.process("session:memory", "What does velnora mean?").evaluation.query_results[0]
        assert query.status is QueryStatus.SUPPORTED
        assert receipt.committed_fact_refs[0] in query.proof.source_refs
        assert runtime.stores.world.revision == 1
    finally:
        runtime.stores.close()
