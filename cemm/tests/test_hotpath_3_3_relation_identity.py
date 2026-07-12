from cemm.memory.durable_semantic_store import DurableSemanticStore
from cemm.memory.relation_identity import RelationIdentity


def test_profile_dimensions_are_distinct_relation_slots():
    name = RelationIdentity.from_fields({
        "relation_key": "has_property", "subject_entity_id": "user",
        "dimension": "identity.name",
    })
    email = RelationIdentity.from_fields({
        "relation_key": "has_property", "subject_entity_id": "user",
        "dimension": "identity.email",
    })
    assert name != email
    assert name.as_key() != email.as_key()


def test_single_slot_supersedes_only_same_dimension():
    store = DurableSemanticStore()
    first = store.add_relation(
        "has_property", "property", subject_entity_id="user",
        object_surface="Chibueze", dimension="identity.name",
        cardinality="optional_one", features={"update_policy": "replace"},
    )
    email = store.add_relation(
        "has_property", "property", subject_entity_id="user",
        object_surface="opata@gmail.com", dimension="identity.email",
        cardinality="optional_one", features={"update_policy": "replace"},
    )
    full = store.add_relation(
        "has_property", "property", subject_entity_id="user",
        object_surface="Chibueze Opata", dimension="identity.name",
        cardinality="optional_one", features={"update_policy": "replace"},
    )
    assert not first.active
    assert full.active and email.active
    assert first.superseded_by_record_id == full.record_id
    assert [f.object.surface for f in store.query_relations(
        relation_key="has_property", subject_entity_id="user",
        dimension="identity.email",
    )] == ["opata@gmail.com"]
