from cemm.v350.discourse.minimum_authority_v351 import compile_minimum_discourse_authority
from cemm.v350.discourse.model import DiscourseActKind


def test_minimum_discourse_authority_covers_exact_phase9_wrapper_slots_without_floating_lookup():
    artifacts = compile_minimum_discourse_authority()
    bindings = artifacts.binding_map
    assert set(bindings) == {
        "discourse:query", "discourse:correction", "discourse:definition",
        "discourse:greeting", "discourse:request", "discourse:retraction",
    }
    assert {item.act_kind for item in artifacts.authority_map.authorities} == {
        DiscourseActKind.QUERY, DiscourseActKind.CORRECTION, DiscourseActKind.DEFINITION,
        DiscourseActKind.GREETING, DiscourseActKind.REQUEST, DiscourseActKind.RETRACTION,
    }
    assert all(pin.content_hash for pin in bindings.values())
    assert len({pin.key for pin in bindings.values()}) == len(bindings)


def test_discourse_authority_compile_is_deterministic_and_content_addressed():
    first = compile_minimum_discourse_authority()
    second = compile_minimum_discourse_authority()
    assert tuple(pin.key for _, pin in first.semantic_slot_pins) == tuple(pin.key for _, pin in second.semantic_slot_pins)
    assert first.authority_map == second.authority_map


def test_one_promoted_discourse_wrapper_does_not_require_unrelated_wrappers():
    from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351
    from cemm.v350.conversation.session_memory import SessionDiscourseMemory
    from cemm.v350.discourse.builder_v351 import DiscourseStructureBuilderV351

    artifacts = compile_minimum_discourse_authority()
    query_authority = next(item for item in artifacts.authority_map.authorities if item.act_kind is DiscourseActKind.QUERY)
    query_definition = next(
        item for item in artifacts.semantic_definitions
        if item.definition_pin.key == query_authority.definition_pin.key
    )
    snapshot = AuthoritySnapshotV351(1, "authority:query-wrapper-only", semantic_definitions=(query_definition,))
    builder = DiscourseStructureBuilderV351(SessionDiscourseMemory())
    effective = builder._effective_authority_map(snapshot)
    assert tuple(item.act_kind for item in effective.authorities) == (DiscourseActKind.QUERY,)
