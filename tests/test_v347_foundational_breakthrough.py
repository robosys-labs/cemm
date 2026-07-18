from __future__ import annotations

import pytest

from cemm.migration.v347 import LegacyMigrationError, migrate_legacy_fact
from cemm.v347.goals import CapabilityState, OperationAuthorizer
from cemm.v347.inference import InferenceBudget
from cemm.v347.knowledge import _upsert_predication_op, _upsert_proposition_op
from cemm.v347.model import (
    CommunicativeForce,
    ConsequenceStatus,
    GraphPatch,
    KnowledgeRecord,
    OperationPlan,
    PatchOperation,
    PatchOperationKind,
    Polarity,
    PortBinding,
    PortSchema,
    Predication,
    Referent,
    ReferentKind,
    ResponseClausePlan,
    RuleFunction,
    RulePattern,
    RuleSchema,
    RuleStrength,
    TruthStatus,
    UOLResponsePlan,
    canonical_data,
    semantic_hash,
)
from cemm.v347.runtime import Runtime


def _assertion_patch(runtime: Runtime, *, context: str = "rules") -> GraphPatch:
    predication = Predication(
        predication_id="predication:test:user-president",
        predicate_schema_ref="predicate:occupies_role",
        bindings=(
            PortBinding("holder", referent_refs=("referent:user",)),
            PortBinding("role", referent_refs=("referent:role:president",)),
        ),
        context_ref=context,
        source_evidence_refs=("test:assertion",),
    )
    proposition = Referent(
        referent_id="referent:proposition:test:user-president",
        kind=ReferentKind.PROPOSITION,
        type_refs=("kind:proposition",),
        payload={
            "predication_refs": (predication.predication_id,),
            "context_ref": context,
            "polarity": Polarity.POSITIVE.value,
            "modality_refs": (),
            "attribution_ref": "referent:user",
            "valid_time_ref": None,
            "communicative_force": CommunicativeForce.ASSERT.value,
        },
        scope_ref=context,
        context_ref=context,
    )
    knowledge = KnowledgeRecord(
        knowledge_id="knowledge:test:user-president",
        proposition_ref=proposition.referent_id,
        truth_status=TruthStatus.SUPPORTED,
        context_ref=context,
        source_refs=("referent:user",),
        evidence_refs=("test:assertion",),
        confidence=1.0,
        scope_ref=context,
        permission_ref="conversation",
    )
    return GraphPatch(
        patch_id="patch:test:user-president",
        context_ref=context,
        scope_ref=context,
        source_ref="test",
        evidence_refs=("test:assertion",),
        operations=(
            _upsert_predication_op(predication),
            _upsert_proposition_op(proposition),
            PatchOperation(
                operation_id="op:knowledge:test:user-president",
                kind=PatchOperationKind.UPSERT_KNOWLEDGE,
                target_ref=knowledge.knowledge_id,
                payload=canonical_data(knowledge),
            ),
        ),
        expected_store_revision=runtime.semantic_store.revision,
    )


def test_version_and_public_runtime_are_v347() -> None:
    runtime = Runtime()
    try:
        assert runtime.VERSION == "3.4.7"
        assert runtime.run_text_result("What is your name?").output_text == "My name is CEMM."
    finally:
        runtime.close()


def test_referent_is_the_only_port_filler_family() -> None:
    import cemm.v347.model as model

    assert not hasattr(model, "Value")
    port = PortSchema("value", frozenset({ReferentKind.TEXT}), required=True)
    assert port.accepts(Referent("referent:test", ReferentKind.TEXT, payload={"text": "x"}))
    assert not port.accepts(Referent("referent:test:place", ReferentKind.PLACE))


def test_quantity_and_unit_are_distinct_referents() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("My age is 34 years.", context_id="age")
        predication = next(iter(result.selected_bundle.graph.predications.values()))
        value_ref = predication.binding("value").referent_refs[0]
        unit_ref = predication.binding("unit").referent_refs[0]
        assert value_ref != unit_ref
        assert result.selected_bundle.graph.referents[value_ref].kind == ReferentKind.QUANTITY
        assert result.selected_bundle.graph.referents[unit_ref].kind == ReferentKind.UNIT
    finally:
        runtime.close()


def test_language_detection_is_nbest_and_not_forced_to_english() -> None:
    runtime = Runtime()
    try:
        en = runtime.language.analyze("What is your name?")
        sw = runtime.language.analyze("Jina lako ni nini?")
        assert len(en.language_hypotheses) >= 2
        assert en.language_hypotheses[0].language_tag == "en"
        assert sw.language_hypotheses[0].language_tag == "sw"
    finally:
        runtime.close()


def test_conjunction_and_clause_markers_are_form_evidence() -> None:
    runtime = Runtime()
    try:
        lattice = runtime.language.analyze("My name is Ada and my age is 7 years.")
        assert any(item.relation_kind == "conjunction" for item in lattice.structural_relations)
        assert any(span.candidate_kind == "predicate" for span in lattice.spans)
        assert not any(span.candidate_kind == "predication" for span in lattice.spans)
    finally:
        runtime.close()


def test_seeded_self_name_query() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("What is your name?")
        assert result.output_text == "My name is CEMM."
        assert result.emission_proof and result.emission_proof.authorized
    finally:
        runtime.close()


def test_seeded_cemm_meaning_query() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("what does CEMM mean")
        assert result.output_text == "CEMM means Contextual Event Memory Model."
    finally:
        runtime.close()


def test_user_name_learning_and_retrieval() -> None:
    runtime = Runtime()
    try:
        learned = runtime.run_text("My name is Chibueze Opata.", context_id="profile")
        recalled = runtime.run_text("What is my name?", context_id="profile")
        assert learned.output_text == "Understood."
        assert recalled.output_text == "Your name is Chibueze Opata."
    finally:
        runtime.close()


def test_correction_supersedes_exact_prior_name() -> None:
    runtime = Runtime()
    try:
        runtime.run_text("My name is Chibueze.", context_id="correction")
        correction = runtime.run_text("Correction: my name is Chibu.", context_id="correction")
        recalled = runtime.run_text("What is my name?", context_id="correction")
        assert correction.output_text == "Understood; I corrected it."
        assert recalled.output_text == "Your name is Chibu."
        active_named = runtime.semantic_store.knowledge_for_predicate(
            "predicate:named", context_ref="correction", scope_refs=("global", "correction")
        )
        user_named = [
            pred for _, pred, _ in active_named
            if pred.binding("holder") and pred.binding("holder").referent_refs == ("referent:user",)
        ]
        assert len(user_named) == 1
    finally:
        runtime.close()


def test_age_learning_and_quantity_unit_answer() -> None:
    runtime = Runtime()
    try:
        runtime.run_text("My age is 34 years.", context_id="age-answer")
        result = runtime.run_text("What is my age?", context_id="age-answer")
        assert result.output_text == "Your age is 34 years."
        assert not result.gaps
    finally:
        runtime.close()


def test_two_coordinated_assertions_survive_selection() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("My name is Ada and my age is 7 years.", context_id="coord")
        assert result.selected_bundle is not None
        assert len(result.selected_bundle.proposition_refs) == 2
        assert len(result.selected_bundle.graph.predications) == 2
    finally:
        runtime.close()


def test_two_coordinated_queries_generate_two_answers() -> None:
    runtime = Runtime()
    try:
        runtime.run_text("My name is Ada and my age is 7 years.", context_id="coord-query")
        result = runtime.run_text("What is my name and what is my age?", context_id="coord-query")
        assert "Your name is Ada." in result.output_text
        assert "Your age is 7 years." in result.output_text
    finally:
        runtime.close()


def test_french_uses_same_uol_and_french_realization() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("Quel est votre nom ?", language_hint="fr")
        assert result.target_language == "fr"
        assert result.output_text == "Je m’appelle CEMM."
        pred = next(iter(result.selected_bundle.graph.predications.values()))
        assert pred.predicate_schema_ref == "predicate:named"
    finally:
        runtime.close()


def test_swahili_uses_same_uol_and_swahili_realization() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("Jina lako ni nini?", language_hint="sw")
        assert result.target_language == "sw"
        assert result.output_text == "Jina langu ni CEMM."
        pred = next(iter(result.selected_bundle.graph.predications.values()))
        assert pred.predicate_schema_ref == "predicate:named"
    finally:
        runtime.close()


def test_query_open_port_is_intentional_not_missing_fact_gap() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("What is your name?")
        predication = next(iter(result.selected_bundle.graph.predications.values()))
        name = predication.binding("name")
        assert name.open_variable_ref
        assert not name.referent_refs
        assert not any(gap.kind.value == "port_gap" for gap in result.gaps)
    finally:
        runtime.close()


def test_unknown_input_does_not_default_to_learnable() -> None:
    runtime = Runtime()
    try:
        result = runtime.run_text("dax quux")
        assert result.gaps
        assert all(not gap.learnable for gap in result.gaps)
        assert result.output_text
    finally:
        runtime.close()


def test_explicit_teaching_opens_transaction_but_not_activation() -> None:
    runtime = Runtime()
    try:
        lattice = runtime.language.analyze("Teach dax")
        context = runtime.context.snapshot("learn")
        candidates = runtime.referents.generate(lattice, context)
        understood = runtime.understanding.understand(lattice, candidates, context)
        transaction = runtime.learning.inspect(lattice, understood.bundle, understood.gaps, context_ref="learn")
        assert transaction is not None
        assert transaction.status == "needs_grounding"
        assert runtime.learning.compile_patch(
            transaction, expected_store_revision=runtime.semantic_store.revision
        ) is None
    finally:
        runtime.close()


def test_graph_patch_compare_and_swap_conflict() -> None:
    runtime = Runtime()
    try:
        stale = runtime.semantic_store.revision
        first = GraphPatch(
            patch_id="patch:test:cas:first",
            context_ref="cas", scope_ref="cas", source_ref="test", evidence_refs=(),
            operations=(PatchOperation(
                "op:referent:test:cas", PatchOperationKind.UPSERT_REFERENT,
                "referent:test:cas", canonical_data(Referent("referent:test:cas", ReferentKind.TEXT, payload={"text": "x"}, scope_ref="cas", context_ref="cas")),
            ),),
            expected_store_revision=stale,
        )
        assert runtime.semantic_store.apply_patch(first).committed
        second = GraphPatch(
            patch_id="patch:test:cas:second",
            context_ref="cas", scope_ref="cas", source_ref="test", evidence_refs=(),
            operations=(), expected_store_revision=stale,
        )
        result = runtime.semantic_store.apply_patch(second)
        assert not result.committed
        assert result.errors and result.errors[0].startswith("store_revision_conflict")
    finally:
        runtime.close()


def test_bootstrap_is_idempotent_across_restart(tmp_path: Path) -> None:
    database = tmp_path / "cemm.sqlite"
    first = Runtime(database_path=database)
    revision = first.semantic_store.revision
    first.close()
    second = Runtime(database_path=database)
    try:
        assert second.semantic_store.revision == revision
        assert second.run_text("What is your name?").output_text == "My name is CEMM."
    finally:
        second.close()


def test_discourse_propositions_survive_restart(tmp_path: Path) -> None:
    database = tmp_path / "context.sqlite"
    first = Runtime(database_path=database)
    turn = first.run_text("My name is Ada.", context_id="restart")
    proposition_ref = turn.selected_bundle.proposition_refs[0]
    first.close()
    second = Runtime(database_path=database)
    try:
        recent = second.semantic_store.recent_turns("restart")
        assert proposition_ref in recent[0]["proposition_refs"]
        assert second.semantic_store.get_referent(proposition_ref) is not None
        assert second.run_text("What is my name?", context_id="restart").output_text == "Your name is Ada."
    finally:
        second.close()


def test_world_tracks_are_context_isolated() -> None:
    runtime = Runtime()
    try:
        runtime.run_text(
            "What is your name?",
            context_id="world-a",
            world_observations=({
                "track_id": "track:self:a", "referent_ref": "referent:self",
                "modality": "structured", "state": {"visible": True}, "confidence": 0.9,
            },),
        )
        assert runtime.semantic_store.world_tracks("world-a")
        assert not runtime.semantic_store.world_tracks("world-b")
    finally:
        runtime.close()


def test_strict_rule_produces_entailed_proof() -> None:
    runtime = Runtime()
    try:
        assert runtime.semantic_store.apply_patch(_assertion_patch(runtime)).committed
        inferred = runtime.inference.infer(context_ref="rules")
        assert "rule:president_is_leader" in inferred.outcome.fired_rule_refs
        assert any(step.consequence_status == ConsequenceStatus.ENTAILED for step in inferred.outcome.proof_steps)
    finally:
        runtime.close()


def test_default_rule_is_expected_not_entailed() -> None:
    runtime = Runtime()
    try:
        assert runtime.semantic_store.apply_patch(_assertion_patch(runtime)).committed
        rule = RuleSchema(
            rule_ref="rule:test:default-related",
            antecedents=(RulePattern(
                "predicate:occupies_role", {"holder": "x"}, {"role": "referent:role:president"}
            ),),
            consequent=RulePattern(
                "predicate:related_to", {"left": "x"}, {"right": "referent:self"}
            ),
            function=RuleFunction.DEFAULT,
            strength=RuleStrength.DEFEASIBLE,
            confidence=0.6,
        )
        inferred = runtime.inference.infer(context_ref="rules", rules=(rule,))
        assert inferred.outcome.proof_steps
        assert inferred.outcome.proof_steps[0].consequence_status == ConsequenceStatus.EXPECTED
    finally:
        runtime.close()


def test_sensitive_rule_is_blocked_by_default() -> None:
    runtime = Runtime()
    try:
        assert runtime.semantic_store.apply_patch(_assertion_patch(runtime)).committed
        rule = RuleSchema(
            rule_ref="rule:test:sensitive",
            antecedents=(RulePattern(
                "predicate:occupies_role", {"holder": "x"}, {"role": "referent:role:president"}
            ),),
            consequent=RulePattern(
                "predicate:related_to", {"left": "x"}, {"right": "referent:self"}
            ),
            function=RuleFunction.DEFAULT,
            strength=RuleStrength.DEFEASIBLE,
            sensitivity="restricted",
        )
        inferred = runtime.inference.infer(
            context_ref="rules", rules=(rule,), budget=InferenceBudget(allow_sensitive=False)
        )
        assert rule.rule_ref in inferred.outcome.blocked_rule_refs
        assert not inferred.outcome.proof_steps
    finally:
        runtime.close()


def test_operation_authorization_rechecks_capability_permission_and_risk() -> None:
    runtime = Runtime()
    try:
        plan = OperationPlan(
            plan_id="plan:test:move", operation_ref="operation:move", goal_ref="goal:test",
            bindings=(
                PortBinding("actor", referent_refs=("referent:self",)),
                PortBinding("destination", referent_refs=("referent:place:test",)),
            ),
            precondition_refs=(), expected_effect_patch=None, risk=0.4,
        )
        blocked = OperationAuthorizer(runtime.schema_store).authorize(
            plan,
            CapabilityState(frozenset(), frozenset(), {}, max_risk=0.1),
        )
        assert not blocked.authorized
        assert "capability_unavailable" in blocked.authorization_reason
        assert "permission_missing" in blocked.authorization_reason
        assert "risk_exceeds_limit" in blocked.authorization_reason
    finally:
        runtime.close()


def test_realization_blocks_unknown_semantic_content() -> None:
    runtime = Runtime()
    try:
        clause = ResponseClausePlan(
            clause_id="clause:test", communicative_force=CommunicativeForce.ASSERT,
            proposition_ref=None, semantic_key="answer:not_seeded", port_bindings={}, certainty=1.0,
        )
        plan = UOLResponsePlan(
            plan_id="plan:test:unrealizable", response_goal_refs=("goal:test",),
            target_language="en", clauses=(clause,), discourse_order=(clause.clause_id,),
            reference_plans=(), tone_constraints={}, coverage_requirements=(clause.clause_id,),
            provenance_refs=("test",),
        )
        result = runtime.realizer.realize(plan)
        assert result is not None
        assert not result.text
        assert not result.proof.authorized
        assert any("missing_predicate_realization" in reason for reason in result.proof.reasons)
    finally:
        runtime.close()


def test_legacy_migration_rejects_untyped_raw_fillers() -> None:
    with pytest.raises(LegacyMigrationError):
        migrate_legacy_fact(
            {"fact_id": "legacy:1", "predicate_key": "named", "roles": {"holder": "user", "name": "Ada"}},
            expected_store_revision=0,
        )


def test_multilingual_alias_bootstrap_does_not_collapse_languages() -> None:
    runtime = Runtime()
    try:
        assert "years" in runtime.semantic_store.aliases_for("referent:unit:year", "en")
        assert "ans" in runtime.semantic_store.aliases_for("referent:unit:year", "fr")
        assert "miaka" in runtime.semantic_store.aliases_for("referent:unit:year", "sw")
    finally:
        runtime.close()


def test_foundation_bootstrap_is_one_graph_patch() -> None:
    runtime = Runtime()
    try:
        rows = runtime.semantic_store._connection.execute(
            "SELECT patch_id, operations_json FROM patches WHERE context_ref='boot'"
        ).fetchall()
        assert len(rows) == 1
        assert "upsert_referent" in rows[0]["operations_json"]
        assert "add_alias" in rows[0]["operations_json"]
        assert "upsert_knowledge" in rows[0]["operations_json"]
    finally:
        runtime.close()
