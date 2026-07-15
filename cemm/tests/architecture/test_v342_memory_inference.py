def test_semantic_memory_deduplicates_identity():
    from cemm.kernel.memory.semantic import SemanticMemoryStore, SemanticFact, FactRole
    store = SemanticMemoryStore()
    first, created_first = store.add(SemanticFact(
        fact_id="f1",
        predicate_key="instance_of",
        roles=(FactRole("entity", "self"), FactRole("kind", "software_system")),
        evidence_refs=("e1",),
    ))
    second, created_second = store.add(SemanticFact(
        fact_id="f2",
        predicate_key="instance_of",
        roles=(FactRole("entity", "self"), FactRole("kind", "software_system")),
        evidence_refs=("e2",),
    ))
    assert created_first
    assert not created_second
    assert first == second
    assert store.get(first).evidence_refs == ("e1", "e2")

def test_bounded_inference_reaches_fixed_point():
    from cemm.kernel.memory.semantic import SemanticMemoryStore, SemanticFact, FactRole
    from cemm.kernel.schema.rule import RuleSchema, RuleAtom
    from cemm.kernel.inference.engine import BoundedInferenceEngine, InferenceBudget
    store = SemanticMemoryStore()
    store.add(SemanticFact(
        fact_id="instance",
        predicate_key="instance_of",
        roles=(FactRole("entity", "x"), FactRole("kind", "a")),
    ))
    store.add(SemanticFact(
        fact_id="subkind",
        predicate_key="subkind_of",
        roles=(FactRole("child_kind", "a"), FactRole("parent_kind", "b")),
    ))
    rule = RuleSchema(
        semantic_key="rule:test",
        premises=(
            RuleAtom("instance_of", {"entity":"$x","kind":"$a"}),
            RuleAtom("subkind_of", {"child_kind":"$a","parent_kind":"$b"}),
        ),
        conclusions=(RuleAtom("instance_of", {"entity":"$x","kind":"$b"}),),
    )
    result = BoundedInferenceEngine((rule,)).infer(
        store,
        budget=InferenceBudget(max_steps=10, wall_clock_ms=100),
    )
    assert any(fact.role("kind").value_ref == "b" for fact in result.derived_facts)
    assert result.stopped_reason == "fixed_point"
