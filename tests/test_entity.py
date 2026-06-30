import pytest
from cemm.types.entity import Entity, EntityType


class TestEntity:
    def test_create_basic(self):
        e = Entity(
            id="e1", type=EntityType.PERSON, name="Alice",
            aliases=["alice", "a"], confidence=0.9,
            created_from_signal_id="s1",
            created_at=0.0, updated_at=0.0,
        )
        assert e.id == "e1"
        assert e.type == EntityType.PERSON
        assert e.version == "cemm.entity.v1"

    def test_entity_type_values(self):
        assert EntityType.UNKNOWN.value == "unknown"
        assert EntityType.CONCEPT.value == "concept"
