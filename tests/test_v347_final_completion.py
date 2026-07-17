from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

from cemm.v347.context import _world_track_recency
from cemm.v347.inference import InferenceBudget
from cemm.v347.knowledge import _upsert_predication_op, _upsert_proposition_op
from cemm.v347.lifecycle import LifecycleEnvironment
from cemm.v347.model import (
    CommunicativeForce,
    CompetenceResult,
    ConsequenceStatus,
    GraphPatch,
    KnowledgeRecord,
    PatchOperation,
    PatchOperationKind,
    Polarity,
    PortBinding,
    Predication,
    Referent,
    ReferentKind,
    RuleFunction,
    RulePattern,
    RuleSchema,
    RuleStrength,
    SchemaStatus,
    SchemaUseOperation,
    TruthStatus,
    canonical_data,
    semantic_hash,
)
from cemm.v347.relation_algebra import RelationAlgebraCoordinator
from cemm.v347.runtime import Runtime


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _competence(case_ref: str = "case:independent") -> CompetenceResult:
    return CompetenceResult(
        result_ref=f"result:{case_ref}",
        case_ref=case_ref,
        passed=True,
        observed_payload={"structurally_valid": True},
        evidence_refs=(f"evidence:{case_ref}",),
        environment_fingerprint=f"independent_environment:{case_ref}",
    )


def _candidate_patch(runtime: Runtime, candidate_ref: str, payload: dict, *, rule: bool = False, context: str = "learn") -> GraphPatch:
    return GraphPatch(
        patch_id=f"patch:{candidate_ref}",
        context_ref=context,
        scope_ref=context,
        source_ref="test:teacher",
        evidence_refs=("evidence:teacher",),
        operations=(PatchOperation(
            operation_id=f"op:{candidate_ref}",
            kind=(PatchOperationKind.UPSERT_RULE_CANDIDATE if rule else PatchOperationKind.UPSERT_SCHEMA_CANDIDATE),
            target_ref=candidate_ref,
            payload={
                "scope_ref": context,
                "status": SchemaStatus.CANDIDATE.value,
                "payload": payload,
                "evidence_refs": ("evidence:teacher",),
            },
        ),),
        expected_store_revision=runtime.semantic_store.revision,
        permission_ref="private_learning",
    )


def _knowledge_patch(
    runtime: Runtime,
    *,
    patch_suffix: str,
    predicate_ref: str,
    bindings: dict[str, str],
    context: str,
    polarity: Polarity = Polarity.POSITIVE,
    valid_from: str | None = None,
    valid_to: str | None = None,
    source_ref: str = "test:observation",
) -> tuple[GraphPatch, str, str]:
    predication = Predication(
        predication_id=f"predication:{patch_suffix}",
        predicate_schema_ref=predicate_ref,
        bindings=tuple(
            PortBinding(port, referent_refs=(referent_ref,))
            for port, referent_ref in bindings.items()
        ),
        context_ref=context,
        source_evidence_refs=(f"evidence:{patch_suffix}",),
    )
    proposition = Referent(
        referent_id=f"referent:proposition:{patch_suffix}",
        kind=ReferentKind.PROPOSITION,
        type_refs=("kind:proposition",),
        payload={
            "predication_refs": (predication.predication_id,),
            "context_ref": context,
            "polarity": polarity.value,
            "modality_refs": (),
            "attribution_ref": source_ref,
            "valid_time_ref": None,
            "communicative_force": CommunicativeForce.ASSERT.value,
        },
        scope_ref=context,
        context_ref=context,
        metadata={"valid_from": valid_from, "valid_to": valid_to},
    )
    knowledge_ref = f"knowledge:{patch_suffix}"
    knowledge = KnowledgeRecord(
        knowledge_id=knowledge_ref,
        proposition_ref=proposition.referent_id,
        truth_status=TruthStatus.SUPPORTED,
        context_ref=context,
        source_refs=(source_ref,),
        evidence_refs=(f"evidence:{patch_suffix}",),
        confidence=1.0,
        scope_ref=context,
        valid_from=valid_from,
        valid_to=valid_to,
        root_lineage_refs=(f"lineage:{patch_suffix}",),
    )
    patch = GraphPatch(
        patch_id=f"patch:{patch_suffix}",
        context_ref=context,
        scope_ref=context,
        source_ref=source_ref,
        evidence_refs=(f"evidence:{patch_suffix}",),
        operations=(
            _upsert_predication_op(predication),
            _upsert_proposition_op(proposition),
            PatchOperation(
                operation_id=f"op:{knowledge_ref}",
                kind=PatchOperationKind.UPSERT_KNOWLEDGE,
                target_ref=knowledge_ref,
                payload=canonical_data(knowledge),
            ),
        ),
        expected_store_revision=runtime.semantic_store.revision,
    )
    return patch, proposition.referent_id, knowledge_ref


def test_active_schema_promotion_has_stable_use_profile() -> None:
    runtime = Runtime()
    try:
        candidate_ref = "candidate:predicate:admires"
        definition = {
            "contribution_kind": "predicate_schema",
            "target_ref": "predicate:admires",
            "definition": {
                "schema_ref": "predicate:admires",
                "schema_kind": "predicate",
                "semantic_key": "admires",
                "ports": [
                    {"port_id": "experiencer", "accepted_kinds": ["person", "self", "agent"], "required": True},
                    {"port_id": "object", "accepted_kinds": ["person", "agent", "physical_object", "information_object"], "required": True},
                ],
            },
            "grounding_refs": ("referent:self",),
            "frontier_refs": (),
            "confidence": 0.9,
        }
        assert runtime.semantic_store.apply_patch(
            _candidate_patch(runtime, candidate_ref, definition)
        ).committed
        result = runtime.promote_schema_candidate(
            candidate_ref,
            context_id="learn",
            target_status=SchemaStatus.ACTIVE,
            competence_results=(_competence(),),
        )
        assert result and result.committed
        profile = runtime.lifecycle.profile(
            "predicate:admires",
            context_ref="learn",
            operation=SchemaUseOperation.COMPOSE,
            environment=LifecycleEnvironment(
                store_revision=runtime.semantic_store.revision,
                foundation_fingerprint=runtime.schema_store.fingerprint,
                analyzer_fingerprint="different_cycle_observation",
            ),
        )
        assert profile.permits(SchemaUseOperation.COMPOSE)
        assert profile.permits(SchemaUseOperation.INFER)
        assert "environment_fingerprint_stale" not in profile.reasons
        assert {port.port_schema.port_id for port in runtime.lifecycle.project_ports(
            "predicate:admires", context_ref="learn"
        )} == {"experiencer", "object"}
    finally:
        runtime.close()


def test_learned_alias_is_ordinary_grounding_and_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "alias.sqlite"
    first = Runtime(database_path=database)
    candidate_ref = "candidate:alias:core-self"
    definition = {
        "contribution_kind": "lexical_alias",
        "target_ref": "schema:alias:core-self",
        "definition": {
            "schema_ref": "schema:alias:core-self",
            "schema_kind": "lexical_alias",
            "surface": "core-self",
            "referent_ref": "referent:self",
            "language_tag": "en",
        },
        "grounding_refs": ("referent:self",),
        "frontier_refs": (),
        "confidence": 0.95,
    }
    assert first.semantic_store.apply_patch(
        _candidate_patch(first, candidate_ref, definition, context="alias")
    ).committed
    promoted = first.promote_schema_candidate(
        candidate_ref,
        context_id="alias",
        target_status=SchemaStatus.ACTIVE,
        competence_results=(_competence("case:alias"),),
    )
    assert promoted and promoted.committed
    assert first.semantic_store.resolve_alias("core-self", "en")[0][0].referent_id == "referent:self"
    first.close()
    second = Runtime(database_path=database)
    try:
        assert second.semantic_store.resolve_alias("core-self", "en")[0][0].referent_id == "referent:self"
    finally:
        second.close()


def test_learned_rule_promotes_hydrates_and_enters_inference(tmp_path: Path) -> None:
    database = tmp_path / "rule.sqlite"
    runtime = Runtime(database_path=database)
    candidate_ref = "candidate:rule:president-related-self"
    rule_ref = "rule:learned:president-related-self"
    rule = {
        "rule_ref": rule_ref,
        "antecedents": [{
            "predicate_schema_ref": "predicate:occupies_role",
            "port_variables": {"holder": "x"},
            "fixed_referent_refs": {"role": "referent:role:president"},
        }],
        "consequent": {
            "predicate_schema_ref": "predicate:related_to",
            "port_variables": {"left": "x"},
            "fixed_referent_refs": {"right": "referent:self"},
        },
        "function": RuleFunction.STRICT.value,
        "strength": RuleStrength.STRICT.value,
        "status": SchemaStatus.CANDIDATE.value,
        "scope_ref": "rules",
    }
    payload = {
        "contribution_kind": "rule_schema",
        "target_ref": rule_ref,
        "definition": {"rule": rule},
        "rule": rule,
        "grounding_refs": ("referent:role:president",),
        "frontier_refs": (),
        "confidence": 0.9,
    }
    assert runtime.semantic_store.apply_patch(
        _candidate_patch(runtime, candidate_ref, payload, rule=True, context="rules")
    ).committed
    promoted = runtime.promote_rule_candidate(
        candidate_ref,
        context_id="rules",
        target_status=SchemaStatus.ACTIVE,
        competence_results=(_competence("case:rule"),),
    )
    assert promoted and promoted.committed
    fact_patch, _, _ = _knowledge_patch(
        runtime,
        patch_suffix="learned-rule-president",
        predicate_ref="predicate:occupies_role",
        bindings={"holder": "referent:user", "role": "referent:role:president"},
        context="rules",
    )
    assert runtime.semantic_store.apply_patch(fact_patch).committed
    inferred = runtime.inference.infer(context_ref="rules")
    assert rule_ref in inferred.outcome.fired_rule_refs
    runtime.close()
    restarted = Runtime(database_path=database)
    try:
        assert any(item.rule_ref == rule_ref for item in restarted.schema_store.active_rules())
    finally:
        restarted.close()


def test_relation_algebra_compiles_schema_declared_properties() -> None:
    runtime = Runtime()
    try:
        algebra = RelationAlgebraCoordinator(runtime.schema_store)
        assert not algebra.validate()
        rules = algebra.compiled_rules()
        kinds = {(item.metadata.get("algebra"), item.antecedents[0].predicate_schema_ref) for item in rules}
        assert ("symmetric", "predicate:spouse_of") in kinds
        assert ("inverse", "predicate:before") in kinds
        assert ("transitive", "predicate:before") in kinds
    finally:
        runtime.close()


def test_inverse_relation_is_inferred_and_strictly_admissible() -> None:
    runtime = Runtime()
    try:
        for ref in ("referent:time:a", "referent:time:b"):
            patch = GraphPatch(
                patch_id=f"patch:{ref}", context_ref="time", scope_ref="time", source_ref="test",
                evidence_refs=(), expected_store_revision=runtime.semantic_store.revision,
                operations=(PatchOperation(
                    operation_id=f"op:{ref}", kind=PatchOperationKind.UPSERT_REFERENT,
                    target_ref=ref, payload=canonical_data(Referent(
                        ref, ReferentKind.TIME, type_refs=("kind:time",),
                        payload={"granularity": "instant"}, scope_ref="time", context_ref="time",
                    )),
                ),),
            )
            assert runtime.semantic_store.apply_patch(patch).committed
        fact_patch, _, _ = _knowledge_patch(
            runtime,
            patch_suffix="time-before",
            predicate_ref="predicate:before",
            bindings={"earlier": "referent:time:a", "later": "referent:time:b"},
            context="time",
        )
        assert runtime.semantic_store.apply_patch(fact_patch).committed
        inferred = runtime.inference.infer(context_ref="time")
        after_steps = [
            step for step in inferred.outcome.proof_steps
            if inferred.predications[
                next(iter((inferred.referents[step.conclusion_proposition_ref].payload or {})["predication_refs"]))
            ].predicate_schema_ref == "predicate:after"
        ]
        assert after_steps and after_steps[0].consequence_status == ConsequenceStatus.ENTAILED
        patch = runtime.inference.compile_admission_patch(
            inferred, context_ref="time", expected_store_revision=runtime.semantic_store.revision
        )
        assert patch and runtime.semantic_store.apply_patch(patch).committed
        assert runtime.semantic_store.knowledge_for_predicate("predicate:after", context_ref="time")
    finally:
        runtime.close()


def test_multimodal_observation_lattice_preserves_contradiction_and_lineage() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text(
            "What is your name?",
            context_id="vision",
            world_observations=(
                {"track_id": "track:v:1", "referent_ref": "referent:self", "modality": "vision", "state": {"visible": True}, "confidence": 0.8},
                {"track_id": "track:v:2", "referent_ref": "referent:self", "modality": "vision", "state": {"visible": False}, "confidence": 0.7},
            ),
        )
        lattice = result.observation_lattice
        assert lattice is not None
        values = {item.payload["state_value"] for item in lattice.observations if item.payload["state_key"] == "visible"}
        assert values == {True, False}
        assert "vision" in lattice.modality_refs
        for evidence in lattice.fused_evidence:
            assert runtime.semantic_store.evidence_record(evidence.evidence_id) is not None
    finally:
        runtime.close()


def test_world_track_reference_salience_decays_without_deleting_evidence() -> None:
    now = datetime.now(timezone.utc)
    assert _world_track_recency(now.isoformat(), now=now) > 0.99
    assert _world_track_recency((now - timedelta(minutes=10)).isoformat(), now=now) < 0.26
    assert _world_track_recency((now - timedelta(minutes=31)).isoformat(), now=now) == 0.0


def test_four_state_truth_reports_both_for_opposed_polarities() -> None:
    runtime = Runtime()
    try:
        for suffix, polarity in (("relation-positive", Polarity.POSITIVE), ("relation-negative", Polarity.NEGATIVE)):
            patch, _, _ = _knowledge_patch(
                runtime,
                patch_suffix=suffix,
                predicate_ref="predicate:related_to",
                bindings={"left": "referent:user", "right": "referent:self"},
                context="truth",
                polarity=polarity,
            )
            assert runtime.semantic_store.apply_patch(patch).committed
        assessment = runtime.truth.assess_signature(
            "predicate:related_to",
            {"left": "referent:user", "right": "referent:self"},
            context_ref="truth",
        )
        assert assessment.truth_status == TruthStatus.BOTH
        patch = runtime.truth.compile_assessment_patch(
            (assessment,), context_ref="truth", expected_store_revision=runtime.semantic_store.revision
        )
        assert patch and runtime.semantic_store.apply_patch(patch).committed
        assert runtime.semantic_store.latest_truth_assessment(
            assessment.proposition_signature, "truth"
        )["truth_status"] == TruthStatus.BOTH.value
    finally:
        runtime.close()


def test_temporal_validity_controls_truth_without_erasing_record() -> None:
    runtime = Runtime()
    try:
        start = datetime(2030, 1, 1, tzinfo=timezone.utc)
        end = datetime(2031, 1, 1, tzinfo=timezone.utc)
        patch, _, knowledge_ref = _knowledge_patch(
            runtime,
            patch_suffix="future-relation",
            predicate_ref="predicate:related_to",
            bindings={"left": "referent:user", "right": "referent:self"},
            context="temporal",
            valid_from=start.isoformat(),
            valid_to=end.isoformat(),
        )
        assert runtime.semantic_store.apply_patch(patch).committed
        before = runtime.truth.assess_signature(
            "predicate:related_to", {"left": "referent:user", "right": "referent:self"},
            context_ref="temporal", at_time="2029-01-01T00:00:00+00:00",
        )
        during = runtime.truth.assess_signature(
            "predicate:related_to", {"left": "referent:user", "right": "referent:self"},
            context_ref="temporal", at_time="2030-06-01T00:00:00+00:00",
        )
        assert before.truth_status == TruthStatus.UNDETERMINED
        assert during.truth_status == TruthStatus.SUPPORTED
        assert any(item.knowledge_id == knowledge_ref for item in runtime.semantic_store.active_knowledge(context_ref="temporal"))
    finally:
        runtime.close()


def test_default_consequences_never_enter_durable_knowledge() -> None:
    runtime = Runtime()
    try:
        fact_patch, _, _ = _knowledge_patch(
            runtime,
            patch_suffix="default-source",
            predicate_ref="predicate:occupies_role",
            bindings={"holder": "referent:user", "role": "referent:role:president"},
            context="default-proof",
        )
        assert runtime.semantic_store.apply_patch(fact_patch).committed
        default_rule = RuleSchema(
            rule_ref="rule:test:default-not-durable",
            antecedents=(RulePattern(
                "predicate:occupies_role", {"holder": "x"}, {"role": "referent:role:president"}
            ),),
            consequent=RulePattern(
                "predicate:related_to", {"left": "x"}, {"right": "referent:self"}
            ),
            function=RuleFunction.DEFAULT,
            strength=RuleStrength.DEFEASIBLE,
        )
        inferred = runtime.inference.infer(context_ref="default-proof", rules=(default_rule,))
        assert inferred.outcome.proof_steps[0].consequence_status == ConsequenceStatus.EXPECTED
        assert runtime.inference.compile_admission_patch(
            inferred, context_ref="default-proof", expected_store_revision=runtime.semantic_store.revision
        ) is None
    finally:
        runtime.close()


def test_negative_capability_observation_blocks_stale_positive_claim() -> None:
    runtime = Runtime(operation_adapters={"operation:move": lambda plan: None})
    try:
        schema = runtime.schema_store.operation("operation:move")
        patch = GraphPatch(
            patch_id="patch:capability:negative",
            context_ref="actual", scope_ref="actual", source_ref="test:health",
            evidence_refs=("evidence:adapter_down",),
            expected_store_revision=runtime.semantic_store.revision,
            operations=(PatchOperation(
                operation_id="op:capability:negative",
                kind=PatchOperationKind.UPSERT_CAPABILITY_OBSERVATION,
                target_ref="capability_observation:move:down",
                payload={
                    "capability_ref": schema.capability_ref,
                    "available": False,
                    "confidence": 1.0,
                    "source_ref": "test:health",
                    "context_ref": "actual",
                    "resource_state": {},
                    "evidence_refs": ("evidence:adapter_down",),
                },
            ),),
        )
        assert runtime.semantic_store.apply_patch(patch).committed
        state = runtime.capabilities.state("cap", permissions=("external_action",), max_risk=1.0)
        assert schema.capability_ref not in state.available_capabilities
    finally:
        runtime.close()


def test_authorized_adapter_effect_is_rechecked_committed_and_ledgered() -> None:
    holder: dict[str, Runtime] = {}

    def adapter(plan):
        runtime = holder["runtime"]
        referent = Referent(
            "referent:operation:test:completed",
            ReferentKind.STATE,
            type_refs=("kind:state",),
            payload={"dimension_ref": "referent:dimension:operational_status", "value_ref": "referent:state:available"},
            scope_ref="operation", context_ref="operation",
        )
        return {
            "status": "completed",
            "effect_patch": GraphPatch(
                patch_id="patch:adapter:effect",
                context_ref="operation", scope_ref="operation", source_ref="adapter:move",
                evidence_refs=("adapter:move:observed",),
                operations=(PatchOperation(
                    operation_id="op:adapter:effect",
                    kind=PatchOperationKind.UPSERT_REFERENT,
                    target_ref=referent.referent_id,
                    payload=canonical_data(referent),
                ),),
                expected_store_revision=0,
            ),
        }

    runtime = Runtime(
        operation_adapters={"operation:move": adapter},
        granted_permissions=("conversation", "internal", "external_action"),
        max_operation_risk=0.8,
    )
    holder["runtime"] = runtime
    try:
        result = runtime.run_text("Please move you to Lagos.", context_id="operation")
        assert runtime.semantic_store.get_referent("referent:operation:test:completed") is not None
        ledgers = runtime.semantic_store.operation_ledgers()
        assert ledgers and ledgers[-1]["status"] == "completed"
        assert ledgers[-1]["authorization_fingerprint"]
        assert "patch:adapter:effect" in result.committed_patch_refs
    finally:
        runtime.close()


def test_adapter_cannot_commit_schema_authority_as_an_effect() -> None:
    from cemm.v347.goals import OutcomeReconciler
    from cemm.v347.model import OperationOutcome, OperationPlan

    runtime = Runtime()
    try:
        plan = OperationPlan(
            plan_id="plan:unsafe-effect", operation_ref="operation:move", goal_ref="goal:test",
            bindings=(), precondition_refs=(), expected_effect_patch=None, risk=0.1,
            authorized=True, authorization_reason="authorized", authorization_fingerprint="proof:auth",
        )
        unsafe = GraphPatch(
            patch_id="patch:unsafe-effect", context_ref="x", scope_ref="x", source_ref="adapter",
            evidence_refs=(), operations=(PatchOperation(
                operation_id="op:unsafe-schema",
                kind=PatchOperationKind.UPSERT_SCHEMA_REVISION,
                target_ref="predicate:unsafe",
                payload={"revision": 1},
            ),),
        )
        outcome = OperationOutcome(
            outcome_id="outcome:unsafe", plan_ref=plan.plan_id, status="completed", effect_patch=unsafe
        )
        assert OutcomeReconciler().admissible_effect_patch(
            plan, outcome, expected_store_revision=runtime.semantic_store.revision
        ) is None
    finally:
        runtime.close()


def test_emission_proof_roundtrip_and_ledger_are_durable() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("What is your name?", context_id="emission")
        proof = result.emission_proof
        assert proof and proof.authorized and proof.round_trip_checked
        assert proof.round_trip_score == 1.0
        ledgers = runtime.semantic_store.emission_ledgers(plan_ref=proof.plan_ref)
        assert ledgers and ledgers[0]["authorized"]
        assert ledgers[0]["covered_semantic_refs"] == proof.covered_semantic_refs
    finally:
        runtime.close()


def test_three_languages_select_equivalent_uol_predicate_and_participant() -> None:
    runtime = Runtime()
    try:
        results = (
            runtime.run_text("What is your name?", language_hint="en", context_id="lang-en"),
            runtime.run_text("Quel est votre nom ?", language_hint="fr", context_id="lang-fr"),
            runtime.run_text("Jina lako ni nini?", language_hint="sw", context_id="lang-sw"),
        )
        signatures = []
        for result in results:
            predication = next(iter(result.selected_bundle.graph.predications.values()))
            signatures.append((
                predication.predicate_schema_ref,
                predication.binding("holder").referent_refs,
                bool(predication.binding("name").open_variable_ref),
            ))
        assert len(set(signatures)) == 1
    finally:
        runtime.close()


def test_bounded_inference_is_deterministic_and_within_budget() -> None:
    runtime = Runtime()
    try:
        fact_patch, _, _ = _knowledge_patch(
            runtime,
            patch_suffix="budget-source",
            predicate_ref="predicate:occupies_role",
            bindings={"holder": "referent:user", "role": "referent:role:president"},
            context="budget",
        )
        assert runtime.semantic_store.apply_patch(fact_patch).committed
        budget = InferenceBudget(wall_clock_ms=100, max_depth=4, max_firings=128, max_results=64)
        first = runtime.inference.infer(context_ref="budget", budget=budget)
        second = runtime.inference.infer(context_ref="budget", budget=budget)
        assert first.outcome.proposition_refs == second.outcome.proposition_refs
        assert first.outcome.fired_rule_refs == second.outcome.fired_rule_refs
        assert first.outcome.elapsed_ms < 100
        assert second.outcome.elapsed_ms < 100
    finally:
        runtime.close()


def test_storage_audit_views_expose_evidence_truth_operations_and_emissions() -> None:
    runtime = Runtime(
        operation_adapters={"operation:move": lambda plan: {"status": "completed"}},
        granted_permissions=("conversation", "internal", "external_action"),
        max_operation_risk=0.8,
    )
    try:
        runtime.run_text("Please move you to Lagos.", context_id="audit")
        assert runtime.semantic_store.operation_ledgers()
        assert runtime.semantic_store.emission_ledgers()
        assert runtime.semantic_store.truth_assessments("audit")
        lattice = runtime.run_text("What is your name?", context_id="audit-2").observation_lattice
        assert lattice and runtime.semantic_store.evidence_record(lattice.fused_evidence[0].evidence_id)
    finally:
        runtime.close()



def test_contradictory_answers_are_disclosed_not_rendered_as_settled_values() -> None:
    runtime = Runtime()
    try:
        runtime.run_text("My name is Ada.", context_id="contradiction")
        named = runtime.semantic_store.knowledge_for_predicate(
            "predicate:named", context_ref="contradiction", scope_refs=("contradiction", "global")
        )
        user_fact = next(
            (knowledge, predication)
            for knowledge, predication, _ in named
            if predication.binding("holder")
            and predication.binding("holder").referent_refs == ("referent:user",)
        )
        name_ref = user_fact[1].binding("name").referent_refs[0]
        negative, _, _ = _knowledge_patch(
            runtime,
            patch_suffix="negative-user-name",
            predicate_ref="predicate:named",
            bindings={"holder": "referent:user", "name": name_ref},
            context="contradiction",
            polarity=Polarity.NEGATIVE,
        )
        assert runtime.semantic_store.apply_patch(negative).committed
        query = runtime.run_text("What is my name?", context_id="contradiction")
        assert "conflicting versions" in query.output_text
        assert "Your name is Ada" not in query.output_text
    finally:
        runtime.close()


def test_exact_support_retraction_preserves_history_and_invalidates_dependents() -> None:
    runtime = Runtime()
    try:
        fact, _, knowledge_ref = _knowledge_patch(
            runtime,
            patch_suffix="retractable",
            predicate_ref="predicate:related_to",
            bindings={"left": "referent:user", "right": "referent:self"},
            context="retraction",
            source_ref="source:one",
        )
        assert runtime.semantic_store.apply_patch(fact).committed
        dependency_ref = "dependency:cached-answer:retractable"
        dependency = GraphPatch(
            patch_id="patch:dependency:retractable",
            context_ref="retraction", scope_ref="retraction", source_ref="test",
            evidence_refs=(), expected_store_revision=runtime.semantic_store.revision,
            operations=(PatchOperation(
                operation_id=f"op:{dependency_ref}",
                kind=PatchOperationKind.ADD_DEPENDENCY,
                target_ref=dependency_ref,
                payload={
                    "dependent_ref": "cache:answer:retractable",
                    "dependency_ref": knowledge_ref,
                    "dependency_kind": "answer_support",
                    "dependent_revision": 1,
                    "dependency_revision": 1,
                    "active": True,
                    "metadata": {"fingerprint": "before-retraction"},
                },
            ),),
        )
        assert runtime.semantic_store.apply_patch(dependency).committed
        retraction = runtime.epistemics.compile_support_retraction(
            knowledge_ref,
            source_ref="source:one",
            context_ref="retraction",
            expected_store_revision=runtime.semantic_store.revision,
        )
        assert retraction and runtime.semantic_store.apply_patch(retraction).committed
        record = runtime.semantic_store.knowledge_record(knowledge_ref)
        assert record is not None and record.truth_status == TruthStatus.UNDETERMINED
        invalidations = runtime.semantic_store.invalidations_for("cache:answer:retractable")
        assert invalidations and invalidations[0]["reason"] == "premise_support_retracted"
        assert runtime.semantic_store.get_referent(record.proposition_ref) is not None
    finally:
        runtime.close()


def test_expired_capability_observation_does_not_authorize_operation() -> None:
    runtime = Runtime()
    try:
        schema = runtime.schema_store.operation("operation:move")
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        patch = GraphPatch(
            patch_id="patch:capability:expired",
            context_ref="actual", scope_ref="actual", source_ref="test:health",
            evidence_refs=("evidence:expired",), expected_store_revision=runtime.semantic_store.revision,
            operations=(PatchOperation(
                operation_id="op:capability:expired",
                kind=PatchOperationKind.UPSERT_CAPABILITY_OBSERVATION,
                target_ref="capability_observation:expired",
                payload={
                    "capability_ref": schema.capability_ref,
                    "available": True,
                    "confidence": 1.0,
                    "source_ref": "test:health",
                    "context_ref": "actual",
                    "resource_state": {"compute": 1.0},
                    "valid_until": expired,
                    "evidence_refs": ("evidence:expired",),
                },
            ),),
        )
        assert runtime.semantic_store.apply_patch(patch).committed
        state = runtime.capabilities.state("expiry", permissions=("external_action",), max_risk=1.0)
        assert schema.capability_ref not in state.available_capabilities
    finally:
        runtime.close()


def test_sensitive_spouse_default_remains_blocked_without_explicit_policy() -> None:
    runtime = Runtime()
    try:
        fact, _, _ = _knowledge_patch(
            runtime,
            patch_suffix="spouse-sensitive",
            predicate_ref="predicate:spouse_of",
            bindings={"left": "referent:user", "right": "referent:self"},
            context="sensitive",
        )
        assert runtime.semantic_store.apply_patch(fact).committed
        inferred = runtime.inference.infer(
            context_ref="sensitive",
            budget=InferenceBudget(allow_sensitive=False),
        )
        assert "rule:spouses_may_co_reside" in inferred.outcome.blocked_rule_refs
        assert not any(
            predication.predicate_schema_ref == "predicate:co_resides_with"
            for predication in inferred.predications.values()
        )
    finally:
        runtime.close()


def test_tone_changes_surface_not_uol_and_persists_as_session_context() -> None:
    runtime = Runtime()
    try:
        neutral = runtime.run_text(
            "What is your name?", context_id="tone-neutral", language_hint="en"
        )
        warm = runtime.run_text(
            "What is your name?", context_id="tone-warm", language_hint="en",
            tone_constraints={"tone": "warm"},
        )
        assert neutral.output_text == "My name is CEMM."
        assert warm.output_text == "Glad you asked—my name is CEMM."
        neutral_pred = next(iter(neutral.selected_bundle.graph.predications.values()))
        warm_pred = next(iter(warm.selected_bundle.graph.predications.values()))
        assert neutral_pred.predicate_schema_ref == warm_pred.predicate_schema_ref == "predicate:named"
        assert neutral_pred.binding("holder").referent_refs == warm_pred.binding("holder").referent_refs
        inherited = runtime.run_text(
            "What is your name?", context_id="tone-warm", language_hint="en"
        )
        assert inherited.response_plan.tone_constraints["tone"] == "warm"
        assert inherited.output_text == warm.output_text
    finally:
        runtime.close()


def test_case_and_punctuation_variants_preserve_selected_meaning() -> None:
    runtime = Runtime()
    try:
        variants = (
            "What is your name?",
            "what is your name",
            "WHAT IS YOUR NAME???",
            "What, is your name?",
        )
        signatures = []
        for index, text in enumerate(variants):
            result = runtime.run_text(text, context_id=f"metamorphic:{index}")
            predication = next(iter(result.selected_bundle.graph.predications.values()))
            signatures.append((
                predication.predicate_schema_ref,
                predication.binding("holder").referent_refs,
                bool(predication.binding("name").open_variable_ref),
            ))
            assert result.output_text == "My name is CEMM."
        assert len(set(signatures)) == 1
    finally:
        runtime.close()


def test_baby_cemm_greeting_uses_selected_uol_not_clarification() -> None:
    runtime = Runtime()
    try:
        for text in ("hi", "hiii", "hello"):
            result = runtime.run_text(text, context_id=f"greeting:{text}")
            assert result.selected_bundle is not None
            assert result.response_plan is not None
            assert result.emission_proof and result.emission_proof.authorized
            response_details = result.trace.details["RESPONSE_GOALS_AND_UOL"]
            selected_refs = set(response_details["selected"])
            selected_goals = [
                item for item in response_details["candidates"]
                if item["response_goal_id"] in selected_refs
            ]
            assert {item["goal_kind"] for item in selected_goals} == {"rapport_acknowledgement"}
            predication = next(iter(result.selected_bundle.graph.predications.values()))
            assert predication.predicate_schema_ref == "predicate:greets"
            assert predication.binding("speaker").referent_refs == ("referent:user",)
            assert predication.binding("addressee").referent_refs == ("referent:self",)
            assert result.output_text
            assert "clarify" not in result.output_text.casefold()
    finally:
        runtime.close()


def test_baby_cemm_self_state_query_retrieves_grounded_seed_state() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("how are you", context_id="self-state")
        assert result.selected_bundle is not None
        predication = next(iter(result.selected_bundle.graph.predications.values()))
        assert predication.predicate_schema_ref == "predicate:has_state"
        assert predication.binding("holder").referent_refs == ("referent:self",)
        assert predication.binding("dimension").referent_refs == (
            "referent:dimension:operational_status",
        )
        assert predication.binding("value").open_variable_ref
        assert result.trace.details["RETRIEVE_AND_ASSESS"]["answers"]
        assert result.response_plan is not None
        assert result.emission_proof and result.emission_proof.authorized
        assert "referent:state:available" in result.response_plan.clauses[0].port_bindings.values()
        assert "clarify" not in result.output_text.casefold()
    finally:
        runtime.close()


def test_baby_cemm_capability_query_retrieves_grounded_seed_capability() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("what do you do?", context_id="self-capability")
        assert result.selected_bundle is not None
        predication = next(iter(result.selected_bundle.graph.predications.values()))
        assert predication.predicate_schema_ref == "predicate:capable_of"
        assert predication.binding("agent").referent_refs == ("referent:self",)
        assert predication.binding("operation").open_variable_ref
        assert result.trace.details["RETRIEVE_AND_ASSESS"]["answers"]
        assert result.response_plan is not None
        assert result.emission_proof and result.emission_proof.authorized
        assert {
            clause.metadata.get("predicate_schema_ref") for clause in result.response_plan.clauses
        } == {"predicate:capable_of"}
        assert "clarify" not in result.output_text.casefold()
    finally:
        runtime.close()


def test_coordinated_clause_reordering_preserves_semantic_set() -> None:
    runtime = Runtime()
    try:
        first = runtime.run_text(
            "My name is Ada and my age is 7 years.", context_id="reorder:first"
        )
        second = runtime.run_text(
            "My age is 7 years and my name is Ada.", context_id="reorder:second"
        )
        first_set = {item.predicate_schema_ref for item in first.selected_bundle.graph.predications.values()}
        second_set = {item.predicate_schema_ref for item in second.selected_bundle.graph.predications.values()}
        assert first_set == second_set == {"predicate:named", "predicate:has_state"}
        assert len(first.selected_bundle.proposition_refs) == len(second.selected_bundle.proposition_refs) == 2
    finally:
        runtime.close()


def test_context_scopes_prevent_identity_learning_bleed() -> None:
    runtime = Runtime()
    try:
        runtime.run_text("My name is Ada.", context_id="identity:a")
        runtime.run_text("My name is Kato.", context_id="identity:b")
        assert runtime.run_text("What is my name?", context_id="identity:a").output_text == "Your name is Ada."
        assert runtime.run_text("What is my name?", context_id="identity:b").output_text == "Your name is Kato."
    finally:
        runtime.close()


def test_unknown_meaning_uses_target_language_without_english_kernel_fallback() -> None:
    runtime = Runtime()
    try:
        french = runtime.run_text("dax quux", language_hint="fr", context_id="unknown:fr")
        swahili = runtime.run_text("dax quux", language_hint="sw", context_id="unknown:sw")
        assert french.target_language == "fr" and french.output_text.startswith("Pouvez-vous")
        assert swahili.target_language == "sw" and swahili.output_text.startswith("Tafadhali")
        assert french.emission_proof.authorized and swahili.emission_proof.authorized
    finally:
        runtime.close()


def test_foundation_contains_operational_families_without_surface_fields() -> None:
    runtime = Runtime()
    try:
        assert len(runtime.foundation.referents) >= 90
        assert len(runtime.foundation.predicates) >= 35
        assert len(runtime.foundation.operations) >= 3
        assert len(runtime.foundation.rules) >= 5
        predicate_refs = {item.schema_ref for item in runtime.foundation.predicates}
        assert {
            "predicate:named", "predicate:means", "predicate:has_state",
            "predicate:located_at", "predicate:causes", "predicate:enables",
            "predicate:occupies_role", "predicate:before", "predicate:after",
        }.issubset(predicate_refs)
        raw = (_root() / "cemm" / "data" / "v347" / "foundation.json").read_text(encoding="utf-8")
        assert '"surfaces"' not in raw and '"template"' not in raw
    finally:
        runtime.close()


def test_semantic_audit_exposes_selected_meaning_and_durable_counts() -> None:
    from cemm.v347.audit import explain_cycle, runtime_audit

    runtime = Runtime()
    try:
        result = runtime.run_text("What is your name?", context_id="audit-tool")
        explanation = explain_cycle(result)
        audit = runtime_audit(runtime)
        assert explanation["selected_predicate_refs"] == ("predicate:named",)
        assert explanation["emission_proof"]["authorized"] is True
        assert audit["version"] == "3.4.7"
        assert audit["record_counts"]["referents"] >= len(runtime.foundation.referents)
        assert audit["record_counts"]["emission_ledger"] >= 1
    finally:
        runtime.close()


def test_web_demo_chat_handler_uses_canonical_v347_runtime_trace() -> None:
    from cemm.web_demo import handle_chat

    runtime = Runtime()
    try:
        payload = handle_chat(runtime, {
            "text": "how are you",
            "context_id": "web-demo-test",
            "include_trace": True,
        })
        assert payload["ok"] is True
        assert payload["emission_authorized"] is True
        assert payload["output_text"]
        assert "Could you clarify" not in payload["output_text"]
        assert "COMPOSE_AND_SELECT" in payload["trace"]["stages"]
        response = payload["trace"]["details"]["RESPONSE_GOALS_AND_UOL"]
        assert response["plan"]["clauses"][0]["metadata"]["predicate_schema_ref"] == "predicate:has_state"
    finally:
        runtime.close()
