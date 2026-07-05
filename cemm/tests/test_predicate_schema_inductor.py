"""Tests for PredicateSchemaInductor."""

from __future__ import annotations

from cemm.learning.predicate_schema_inductor import PredicateSchemaInductor
from cemm.memory.predicate_schema_store import PredicateSchemaStore
from cemm.types.relation_frame import RelationFrame, RelationArgument


class TestPredicateSchemaInductor:
    """Acceptance tests for predicate schema induction from relation frames."""

    def test_unknown_predicate_key_creates_candidate(self) -> None:
        inductor = PredicateSchemaInductor()
        store = PredicateSchemaStore()
        frame = RelationFrame(
            relation_id="r1",
            relation_key="custom_predicate",
            relation_family="definition",
            subject=RelationArgument(role="subject"),
            object=RelationArgument(role="object"),
        )

        result = inductor.induct_from_frames([frame], store)

        assert "custom_predicate" in result
        candidate = store.get_candidate("custom_predicate")
        assert candidate is not None
        assert candidate.support_count == 1
        assert candidate.argument_roles == ["subject", "object"]

    def test_repeated_observation_increments_support_count(self) -> None:
        inductor = PredicateSchemaInductor()
        store = PredicateSchemaStore()
        frame = RelationFrame(
            relation_id="r1",
            relation_key="custom_predicate",
            relation_family="definition",
            subject=RelationArgument(role="subject"),
            object=RelationArgument(role="object"),
        )

        result = inductor.induct_from_frames([frame, frame], store)

        assert "custom_predicate" in result
        promoted = store.get("custom_predicate")
        assert promoted is not None
        assert promoted.support_count == 2

    def test_candidate_auto_promotes_after_threshold(self) -> None:
        inductor = PredicateSchemaInductor()
        store = PredicateSchemaStore()
        frame = RelationFrame(
            relation_id="r1",
            relation_key="custom_predicate",
            relation_family="definition",
            subject=RelationArgument(role="subject"),
            object=RelationArgument(role="object"),
        )

        result = inductor.induct_from_frames([frame, frame], store)

        assert "custom_predicate" in result
        promoted = store.get("custom_predicate")
        assert promoted is not None
        assert promoted.support_count >= 2
        assert promoted.predicate_key == "custom_predicate"
        assert store.get_candidate("custom_predicate") is None

    def test_seed_schemas_are_skipped(self) -> None:
        inductor = PredicateSchemaInductor()
        store = PredicateSchemaStore()
        frame = RelationFrame(
            relation_id="r1",
            relation_key="is_a",
            relation_family="taxonomy",
            subject=RelationArgument(role="child"),
            object=RelationArgument(role="parent"),
        )

        result = inductor.induct_from_frames([frame], store)

        assert "is_a" not in result
        existing = store.get("is_a")
        assert existing is not None
        assert existing.support_count == 1

    def test_multiple_unknown_keys_handled(self) -> None:
        inductor = PredicateSchemaInductor()
        store = PredicateSchemaStore()
        frames = [
            RelationFrame(
                relation_id="r1",
                relation_key="pred_a",
                relation_family="causal",
                subject=RelationArgument(role="cause"),
                object=RelationArgument(role="effect"),
            ),
            RelationFrame(
                relation_id="r2",
                relation_key="pred_b",
                relation_family="definition",
                subject=RelationArgument(role="subject"),
                object=RelationArgument(role="object"),
            ),
        ]

        result = inductor.induct_from_frames(frames, store)

        assert "pred_a" in result
        assert "pred_b" in result
        assert len(result) == 2
        assert store.get_candidate("pred_a") is not None
        assert store.get_candidate("pred_b") is not None

    def test_argument_roles_inferred_from_frames(self) -> None:
        inductor = PredicateSchemaInductor()
        store = PredicateSchemaStore()
        frame = RelationFrame(
            relation_id="r1",
            relation_key="leader_of",
            relation_family="role",
            subject=RelationArgument(role="leader"),
            object=RelationArgument(role="follower"),
            qualifiers={
                "domain": RelationArgument(role="domain"),
            },
        )

        result = inductor.induct_from_frames([frame], store)

        assert "leader_of" in result
        candidate = store.get_candidate("leader_of")
        assert candidate is not None
        assert candidate.argument_roles == ["leader", "follower", "domain"]
