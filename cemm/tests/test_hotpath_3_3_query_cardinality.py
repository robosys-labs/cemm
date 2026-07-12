from types import SimpleNamespace

from cemm.kernel.semantic_query_engine import SemanticQueryEngine
from cemm.memory.durable_semantic_store import DurableSemanticStore
from cemm.types.obligation_contract import QueryContract


def test_capability_query_retains_many_values():
    store = DurableSemanticStore()
    for value in ("learn new things", "basic chat", "process commands"):
        store.add_relation(
            "capability", "affordance", subject_entity_id="self",
            object_surface=value, cardinality="set",
        )
    contract = QueryContract(
        query_kind="self_capability", target_scope="self_model",
        subject_entity_id="self", relation_key="capability",
        projection_policy="self_value", result_cardinality="ranked_many",
        result_limit=8, aggregate_policy="coordinate",
    )
    query, frames, binding = SemanticQueryEngine().execute_contract(
        contract, None, turn_frames=[], durable_store=store,
    )
    assert binding.has_answer
    assert {fill.surface for fill in binding.slot_fills} == {
        "learn new things", "basic chat", "process commands",
    }
