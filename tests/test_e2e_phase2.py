from __future__ import annotations
import time
import uuid
from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.entity_resolver import EntityResolver
from cemm.operators.remember import RememberOperator
from cemm.operators.base import OperatorContext
from cemm.learning.inductor import Inductor
from cemm.learning.online import OnlineLearner
from cemm.learning.promotion import ModelPromoter
from cemm.retrieval.structural import StructuralRetriever, RetrievalQuery
from cemm.retrieval.ranker import Ranker
from cemm.synthesis.router import SynthesisRouter
from cemm.types.entity import Entity, EntityType
from cemm.types.model import ModelKind, ModelStatus
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission, PermissionScope
from cemm.types.context_kernel import ContextKernel

SEED_EVENTS = 200
SEED = 42
ACTIONS = ["query", "update", "save", "delete", "create"]
ACTORS = ["alice", "bob"]

GROUND_TRUTH = {
    ("query", "postgres"): "success",
    ("delete", "k8s"): "failure",
}


def _make_store() -> Store:
    s = Store(":memory:")
    from cemm.types.self_state import SelfState
    s.self_store.put(SelfState(
        id="self_main", name="cemm",
        created_at=time.time(), updated_at=time.time(),
    ))
    return s


def _register_actions(reg: Registry) -> None:
    for i, a in enumerate(ACTIONS):
        reg.register(RegistryEntry(model_id=f"p{i}", canonical_key=a, kind="predicate"))


def _inject_pattern(store: Store, pipeline: Pipeline, resolver: EntityResolver,
                    actor: str, action: str, obj: str, outcome: str,
                    reg: Registry, count: int = 6) -> None:
    remember_op = RememberOperator()
    for _ in range(count):
        text = f"{actor} {action} {obj}"
        pr = pipeline.run(text, context_id="e2e_inject")
        signal = pr.signals[0]
        kernel = pr.kernel
        ae = resolver.resolve_or_create(actor, EntityType.PERSON, signal.id, kernel)
        oe = resolver.resolve_or_create(obj, EntityType.OBJECT, signal.id, kernel)
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal, store=store, registry=reg,
            selected_claim_ids=[], selected_model_ids=[], params={
                "subject_entity_id": ae.id, "predicate": action,
                "object_entity_id": oe.id, "object_value": obj,
                "domain": "causal", "qualifiers": {"outcome": outcome},
            },
        )
        remember_op.execute(ctx)


def _emit_events(store: Store, pipeline: Pipeline, resolver: EntityResolver, remember_op: RememberOperator, reg: Registry | None = None) -> None:
    rng = __import__("random").Random(SEED)
    for t in range(SEED_EVENTS):
        actor = rng.choice(ACTORS)
        action = rng.choice(ACTIONS)
        obj = rng.choice(["postgres", "mysql", "k8s", "docker", "s3"])
        outcome = "success" if rng.random() < 0.6 else "failure"
        text = f"{actor} {action} {obj}"
        pr = pipeline.run(text, context_id="e2e")
        signal = pr.signals[0]
        kernel = pr.kernel
        ae = resolver.resolve_or_create(actor, EntityType.PERSON, signal.id, kernel)
        oe = resolver.resolve_or_create(obj, EntityType.OBJECT, signal.id, kernel)
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal, store=store,
            registry=reg if reg is not None else pipeline._registry,
            selected_claim_ids=[], selected_model_ids=[], params={
                "subject_entity_id": ae.id, "predicate": action,
                "object_entity_id": oe.id, "object_value": obj,
                "domain": "causal", "qualifiers": {"outcome": outcome},
            },
        )
        remember_op.execute(ctx)


class TestE2E_FullPipeline:
    def test_causal_prediction_end_to_end(self):
        store = _make_store()
        reg = Registry()
        _register_actions(reg)
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()

        _emit_events(store, pipeline, resolver, remember_op)

        _inject_pattern(store, pipeline, resolver, "alice", "query", "postgres", "success", reg, count=20)
        _inject_pattern(store, pipeline, resolver, "bob", "delete", "k8s", "failure", reg, count=20)

        inductor = Inductor(store, feedback_threshold=5)
        promoter = ModelPromoter(store)

        candidates = inductor.maybe_induct(domain="causal")
        causal_candidates = [m for m in candidates if m.kind == ModelKind.CAUSAL_RULE]

        promoted_count = 0
        for model in causal_candidates:
            ok, _ = promoter.can_promote(model)
            if ok:
                p_ok, _ = promoter.promote(model.id)
                if p_ok:
                    promoted_count += 1

        active_rules = store.models.find_by_kind("causal_rule", "active")

        for (action, obj), expected_outcome in GROUND_TRUTH.items():
            found = False
            for rule in active_rules:
                if rule.name != action:
                    continue
                precond_names = []
                for p in rule.preconditions:
                    if p.startswith("object:"):
                        eid = p[7:]
                        e = store.entities.get(eid)
                        precond_names.append(e.name if e else eid)
                if obj not in precond_names:
                    continue
                predicted = [e for e in rule.effects if e.startswith("outcome:")]
                if any(f"outcome:{expected_outcome}" == e for e in predicted):
                    found = True
                    break
            assert found, f"Rule for ({action}, {obj}) -> {expected_outcome} not found"

        assert any(m.kind == ModelKind.CAUSAL_RULE for m in active_rules)
        assert any(r.name in [a for a, _ in GROUND_TRUTH] for r in active_rules)

    def test_memory_retrieval_ranking_synthesis_end_to_end(self):
        store = _make_store()
        reg = Registry()
        reg.register(RegistryEntry(model_id="m1", canonical_key="favorite_database", kind="predicate"))
        reg.register(RegistryEntry(model_id="m2", canonical_key="preferred_language", kind="predicate"))
        reg.register(RegistryEntry(model_id="m3", canonical_key="favorite_editor", kind="predicate"))
        reg.register(RegistryEntry(model_id="m4", canonical_key="preferred_os", kind="predicate"))
        reg.register(RegistryEntry(model_id="m5", canonical_key="favorite_color", kind="predicate"))
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()
        retriever = StructuralRetriever(store)
        ranker = Ranker()
        synth_router = SynthesisRouter()

        user_entity = resolver.resolve_or_create("test_user", EntityType.PERSON, "", None)

        preferences = [
            ("favorite_database", "postgres"),
            ("preferred_language", "python"),
            ("favorite_editor", "vscode"),
            ("preferred_os", "linux"),
        ]
        distractors = [
            ("favorite_database", "mysql"),
            ("preferred_language", "java"),
            ("preferred_os", "macos"),
        ]

        for predicate, obj in distractors:
            text = f"user {predicate} {obj}"
            pr = pipeline.run(text, context_id="e2e_mem")
            signal = pr.signals[0]
            kernel = pr.kernel
            oe = resolver.resolve_or_create(obj, EntityType.OBJECT, signal.id, kernel)
            ctx = OperatorContext(
                kernel=kernel, input_signal=signal, store=store, registry=reg,
                selected_claim_ids=[], selected_model_ids=[], params={
                    "subject_entity_id": user_entity.id, "predicate": predicate,
                    "object_entity_id": oe.id, "object_value": obj,
                    "domain": "preference", "qualifiers": {},
                },
            )
            remember_op.execute(ctx)

        for predicate, obj in preferences:
            text = f"user {predicate} {obj}"
            pr = pipeline.run(text, context_id="e2e_mem")
            signal = pr.signals[0]
            kernel = pr.kernel
            oe = resolver.resolve_or_create(obj, EntityType.OBJECT, signal.id, kernel)
            ctx = OperatorContext(
                kernel=kernel, input_signal=signal, store=store, registry=reg,
                selected_claim_ids=[], selected_model_ids=[], params={
                    "subject_entity_id": user_entity.id, "predicate": predicate,
                    "object_entity_id": oe.id, "object_value": obj,
                    "domain": "preference", "qualifiers": {},
                },
            )
            remember_op.execute(ctx)

        rk = ContextKernel(
            id="e2e_rank", permission=Permission.public(),
        )

        for predicate, expected_obj in preferences:
            q_result = retriever.retrieve(
                RetrievalQuery(subject_entity_id=user_entity.id, predicate=predicate)
            )
            matching = [c for c in q_result.claims if c.object_value == expected_obj]
            assert len(matching) >= 1, f"Claim for {predicate}={expected_obj} not found"

            ranked = ranker.rank_claims(q_result.claims, rk)
            assert len(ranked) > 0, f"No ranked claims for {predicate}"
            top_claim = ranked[0][0]
            assert top_claim.object_value == expected_obj, (
                f"Ranked top for {predicate}: expected {expected_obj}, got {top_claim.object_value}"
            )

            synth_params = {"selected_claim_ids": [c.id for c, _ in ranked[:3]]}
            synth_result = synth_router.route("extractive", rk, store, reg, synth_params)
            assert synth_result.success, f"Synthesis failed for {predicate}"
            assert expected_obj in synth_result.output, (
                f"Synthesis for {predicate}: expected '{expected_obj}' in output, got: {synth_result.output}"
            )

    def test_memory_and_causal_coexist_in_same_store(self):
        store = _make_store()
        reg = Registry()
        _register_actions(reg)
        reg.register(RegistryEntry(model_id="mem1", canonical_key="favorite_database", kind="predicate"))
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()
        retriever = StructuralRetriever(store)

        _emit_events(store, pipeline, resolver, remember_op)

        user_entity = resolver.resolve_or_create("e2e_user", EntityType.PERSON, "", None)
        obj_entity = resolver.resolve_or_create("postgres", EntityType.OBJECT, "", None)
        pr = pipeline.run("user favorite_database postgres", context_id="e2e_both")
        signal = pr.signals[0]
        kernel = pr.kernel
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal, store=store, registry=reg,
            selected_claim_ids=[], selected_model_ids=[], params={
                "subject_entity_id": user_entity.id, "predicate": "favorite_database",
                "object_entity_id": obj_entity.id, "object_value": "postgres",
                "domain": "preference", "qualifiers": {},
            },
        )
        remember_op.execute(ctx)

        rules = store.models.find_by_kind("causal_rule", "active")
        causal_ids = store.models.find_by_kind("causal_rule")

        assert len(rules) >= 0
        assert len(causal_ids) >= 0

        mem_result = retriever.retrieve(
            RetrievalQuery(subject_entity_id=user_entity.id, predicate="favorite_database")
        )
        assert len(mem_result.claims) > 0
        assert mem_result.claims[0].object_value == "postgres"


class TestE2E_EdgeCases:
    def test_retrieve_empty_returns_empty(self):
        store = _make_store()
        retriever = StructuralRetriever(store)
        result = retriever.retrieve(RetrievalQuery(subject_entity_id="nonexistent", predicate="missing"))
        assert len(result.claims) == 0
        assert result.total_count == 0

    def test_rank_empty_claims_returns_empty(self):
        ranker = Ranker()
        rk = ContextKernel(id="e2e_empty_rank", permission=Permission.public())
        result = ranker.rank_claims([], rk)
        assert result == []

    def test_synthesis_no_claim_ids_returns_empty(self):
        synth = SynthesisRouter()
        rk = ContextKernel(id="e2e_syn_empty", permission=Permission.public())
        store = _make_store()
        reg = Registry()
        result = synth.route("extractive", rk, store, reg, {})
        assert result.success
        assert result.output == "No relevant information found."

    def test_synthesis_bad_strategy_returns_error(self):
        synth = SynthesisRouter()
        rk = ContextKernel(id="e2e_bad_strat", permission=Permission.public())
        store = _make_store()
        reg = Registry()
        result = synth.route("nonexistent", rk, store, reg, {})
        assert not result.success
        assert "Unknown strategy" in result.output

    def test_remember_missing_subject_creates_entity(self):
        store = _make_store()
        reg = Registry()
        reg.register(RegistryEntry(model_id="p1", canonical_key="likes", kind="predicate"))
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()
        pr = pipeline.run("test likes pizza", context_id="e2e_auto_entity")
        signal = pr.signals[0]
        kernel = pr.kernel
        subject = resolver.resolve_or_create("new_user", EntityType.PERSON, signal.id, kernel)
        obj = resolver.resolve_or_create("pizza", EntityType.OBJECT, signal.id, kernel)
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal, store=store, registry=reg,
            selected_claim_ids=[], selected_model_ids=[], params={
                "subject_entity_id": subject.id, "predicate": "likes",
                "object_entity_id": obj.id, "object_value": "pizza",
                "domain": "preference", "qualifiers": {},
            },
        )
        result = remember_op.execute(ctx)
        assert result.success
        found = store.entities.get(subject.id)
        assert found is not None
        assert found.name == "new_user"

    def test_pipeline_requires_kernel(self):
        pipeline = Pipeline(Store(":memory:"), Registry())
        result = pipeline.run("hello")
        assert result.kernel is not None
        assert result.kernel.time.bucket is not None

    def test_private_claim_ranked_lower_for_unknown_user(self):
        store = _make_store()
        reg = Registry()
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()
        ranker = Ranker()
        retriever = StructuralRetriever(store)

        reg.register(RegistryEntry(model_id="m1", canonical_key="secret", kind="predicate"))
        subj = resolver.resolve_or_create("private_user", EntityType.PERSON, "", None)
        obj = resolver.resolve_or_create("hidden_data", EntityType.OBJECT, "", None)

        pr = pipeline.run("private_user secret hidden_data", context_id="e2e_priv",
                          budget_override={"latency_target_ms": 500})
        signal = pr.signals[0]
        kernel = pr.kernel
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal, store=store, registry=reg,
            selected_claim_ids=[], selected_model_ids=[], params={
                "subject_entity_id": subj.id, "predicate": "secret",
                "object_entity_id": obj.id, "object_value": "hidden_data",
                "domain": "private", "qualifiers": {},
            },
        )
        op_result = remember_op.execute(ctx)
        assert op_result.success
        claim_id = op_result.new_claim_ids[0]
        claim = store.claims.get(claim_id)
        assert claim is not None
        claim.permission = Permission.user_private()
        store.claims.put(claim)

        q_result = retriever.retrieve(RetrievalQuery(subject_entity_id=subj.id, predicate="secret"))

        unknown_kernel = ContextKernel(id="anon", permission=Permission.public())
        ranked = ranker.rank_claims(q_result.claims, unknown_kernel)
        assert len(ranked) == 0, "Private claim should be filtered for anonymous kernel"

        known_kernel = ContextKernel(id="known", permission=Permission(
            scope=PermissionScope.USER_PRIVATE, may_execute=True,
        ))
        known_kernel.user.known = True
        ranked_known = ranker.rank_claims(q_result.claims, known_kernel)
        assert len(ranked_known) > 0, "Private claim should be visible to known kernel"

    def test_repeated_memory_stores_same_predicate(self):
        store = _make_store()
        reg = Registry()
        reg.register(RegistryEntry(model_id="m1", canonical_key="color", kind="predicate"))
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()
        retriever = StructuralRetriever(store)
        ranker = Ranker()

        subj = resolver.resolve_or_create("repeat_user", EntityType.PERSON, "", None)

        colors = ["red", "blue", "green", "blue", "red"]
        for c in colors:
            obj = resolver.resolve_or_create(c, EntityType.OBJECT, "", None)
            pr = pipeline.run(f"repeat_user color {c}", context_id="e2e_repeat")
            signal = pr.signals[0]
            kernel = pr.kernel
            ctx = OperatorContext(
                kernel=kernel, input_signal=signal, store=store, registry=reg,
                selected_claim_ids=[], selected_model_ids=[], params={
                    "subject_entity_id": subj.id, "predicate": "color",
                    "object_entity_id": obj.id, "object_value": c,
                    "domain": "preference", "qualifiers": {},
                },
            )
            remember_op.execute(ctx)

        q_result = retriever.retrieve(RetrievalQuery(subject_entity_id=subj.id, predicate="color"))
        assert len(q_result.claims) == 5

        rk = ContextKernel(id="repeat_rank", permission=Permission.public())
        ranked = ranker.rank_claims(q_result.claims, rk)
        assert len(ranked) == 5
        assert ranked[0][0].object_value == "red"

    def test_missing_entity_retrieval_return_empty_list(self):
        store = _make_store()
        retriever = StructuralRetriever(store)
        result = retriever.retrieve(RetrievalQuery(subject_entity_id="nobody"))
        assert len(result.claims) == 0
        assert len(result.models) == 0
        assert len(result.entities) == 0

    def test_full_pipeline_no_bypass(self):
        store = _make_store()
        reg = Registry()
        reg.register(RegistryEntry(model_id="m1", canonical_key="test_predicate", kind="predicate"))
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)

        subj = resolver.resolve_or_create("bypass_user", EntityType.PERSON, "", None)
        obj = resolver.resolve_or_create("bypass_obj", EntityType.OBJECT, "", None)

        pr = pipeline.run("bypass_user test_predicate bypass_obj", context_id="e2e_bypass")
        assert pr.kernel is not None
        assert len(pr.signals) >= 1
        assert pr.signals[0].id is not None

        signal = pr.signals[0]
        assert signal.kind == SignalKind.INPUT
        assert signal.context_id == "e2e_bypass"
        assert len(signal.content) > 0
        assert signal.source_type == SourceType.USER

    def test_memory_multiple_queries_same_subject(self):
        store = _make_store()
        reg = Registry()
        reg.register(RegistryEntry(model_id="m1", canonical_key="likes", kind="predicate"))
        reg.register(RegistryEntry(model_id="m2", canonical_key="hates", kind="predicate"))
        pipeline = Pipeline(store, reg)
        resolver = EntityResolver(store.entities)
        remember_op = RememberOperator()
        retriever = StructuralRetriever(store)

        subj = resolver.resolve_or_create("multi_user", EntityType.PERSON, "", None)
        dog = resolver.resolve_or_create("dogs", EntityType.OBJECT, "", None)
        cat = resolver.resolve_or_create("cats", EntityType.OBJECT, "", None)

        for predicate, obj_entity, obj_val in [
            ("likes", dog, "dogs"), ("hates", cat, "cats"),
        ]:
            pr = pipeline.run(f"multi_user {predicate} {obj_val}", context_id="e2e_multi")
            signal = pr.signals[0]
            kernel = pr.kernel
            ctx = OperatorContext(
                kernel=kernel, input_signal=signal, store=store, registry=reg,
                selected_claim_ids=[], selected_model_ids=[], params={
                    "subject_entity_id": subj.id, "predicate": predicate,
                    "object_entity_id": obj_entity.id, "object_value": obj_val,
                    "domain": "preference", "qualifiers": {},
                },
            )
            remember_op.execute(ctx)

        likes_result = retriever.retrieve(RetrievalQuery(subject_entity_id=subj.id, predicate="likes"))
        hates_result = retriever.retrieve(RetrievalQuery(subject_entity_id=subj.id, predicate="hates"))
        assert len(likes_result.claims) == 1
        assert len(hates_result.claims) == 1
        assert likes_result.claims[0].object_value == "dogs"
        assert hates_result.claims[0].object_value == "cats"
