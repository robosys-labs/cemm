from types import SimpleNamespace

from cemm.kernel.proposition_semantics import can_materialize_domain_edge
from cemm.kernel.relation_extractor import RelationExtractor
from cemm.types.meaning_percept import IntentAtom, MeaningGroup


def _group(surface: str, tokens: list[str], *, group_type: str) -> MeaningGroup:
    return MeaningGroup(
        id="g1", group_type=group_type, surface=surface, tokens=tokens,
        confidence=0.75,
        intents=[IntentAtom(
            intent_key="user_profile_query" if group_type == "question" else "statement",
            is_question=group_type == "question", group_id="g1", confidence=0.8,
        )],
    )


def test_profile_query_is_open_not_asserted():
    relation = RelationExtractor().extract([
        _group("what is my email?", ["what", "is", "my", "email"], group_type="question")
    ])[0]
    assert relation.proposition_mode == "queried"
    assert relation.open_roles == ["object"]
    assert relation.target_role == ""
    assert relation.features["object_surface"] == ""
    assert relation.features["property_dimension"] == "identity.email"
    assert not can_materialize_domain_edge(relation)


def test_full_name_uses_longest_slot_alias():
    relation = RelationExtractor().extract([
        _group(
            "my full name is Chibueze Opata",
            ["my", "full", "name", "is", "chibueze", "opata"],
            group_type="clause",
        )
    ])[0]
    assert relation.features["property_dimension"] == "identity.full_name"
    assert relation.features["object_surface"].lower() == "chibueze opata"
    assert relation.features["cardinality"] == "optional_one"
    assert relation.features["update_policy"] == "replace"
