# Atomic Learned Definitions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compose and derive from reviewed learned definition graphs without lexical special cases or independently authoritative rule bags.

**Architecture:** Persist reviewed composite definitions as linked, nested ordinary applications; validate and index a bounded executable projection at activation. Extend the recursive chart with generic state-query and possessive relation/event graphlets. Use the definition graph ref as the proof authority for every projected inference result.

**Tech Stack:** Python 3.13, SQLite semantic store, pytest, JSON authority bundles, deterministic language-pack generator.

---

### Task 1: Establish end-to-end failing acceptance cases

**Files:**
- Modify: `C:\dev\cemm\tests\test_native_semantic_spine.py`

- [ ] **Step 1: Add a reviewed composite-definition fixture and failing state-query test**

```python
def test_composite_definition_derives_state_for_possessive_relation(tmp_path):
    runtime = build_runtime_with_reviewed_composite_definition(tmp_path)
    runtime.process("My kinbridge arrived today.")
    result = runtime.process("Am I married?", mode="read_only")
    assert result["query_result"]["status"] == "supported"
    assert result["proof_bundle"]["inference_receipt_refs"]
```

- [ ] **Step 2: Run the test to verify the current semantic gap**

Run: `python -m pytest tests/test_native_semantic_spine.py::test_composite_definition_derives_state_for_possessive_relation -q`

Expected: FAIL because the possessive relation/event graph and state query do not settle.

- [ ] **Step 3: Add an unseen-alias and a no-definition negative test**

```python
def test_composite_relation_alias_inherits_definition_without_pack_rebuild(tmp_path):
    runtime = build_runtime_with_reviewed_composite_definition(tmp_path)
    publish_alias(runtime, "kinbridge", "rel:synthetic_in_law")
    assert runtime.process("My kinbridge arrived today.")["interpretation"]["status"] == "resolved"

def test_designation_without_definition_does_not_entail_state(tmp_path):
    runtime = build_runtime_with_designation_only(tmp_path)
    result = runtime.process("Am I married?", mode="read_only")
    assert result["query_result"]["status"] == "unknown"
```

- [ ] **Step 4: Run the new tests and verify both fail for the intended missing behavior**

Run: `python -m pytest tests/test_native_semantic_spine.py -k "composite_definition or composite_relation_alias or designation_without_definition" -q`

Expected: FAIL only on the new assertions.

### Task 2: Represent and validate reviewed definition graphs

**Files:**
- Modify: `C:\dev\cemm\propositions.py`
- Modify: `C:\dev\cemm\store.py`
- Modify: `C:\dev\cemm\native_semantic_validation.py`
- Modify: `C:\dev\cemm\activation.py`
- Test: `C:\dev\cemm\tests\test_native_semantic_spine.py`

- [ ] **Step 1: Define a canonical definition graph receipt**

```python
@dataclass(frozen=True)
class ReviewedDefinitionGraph:
    definition_ref: str
    target_ref: str
    proposition: PropositionGraph
    executable_projection: tuple[Mapping[str, Any], ...]
```

It must reject unbound consequent variables, missing target atoms, unsupported
operators, duplicate graph identity, and definition graphs whose target is not
explicitly linked by reviewed authority.

- [ ] **Step 2: Persist the graph through existing application/binding storage**

```python
store.publish_definition_graph(
    target_ref=target_ref,
    proposition=proposition,
    authority_status="reviewed",
)
```

The method must materialize children first and store app-valued roles through
the existing binding ABI; it must not add a lexical dictionary or a transient
graph table.

- [ ] **Step 3: Validate activation and deterministic projection**

```python
definition = store.definition_graph(target_ref, generation)
assert definition.definition_ref
assert definition.target_ref == target_ref
assert all(rule["definition_ref"] == definition.definition_ref for rule in definition.executable_projection)
```

- [ ] **Step 4: Run definition-graph focused tests**

Run: `python -m pytest tests/test_native_semantic_spine.py -k "definition_graph or composite_definition" -q`

Expected: PASS.

### Task 3: Add generic state query and possessive relation/event composition

**Files:**
- Modify: `C:\dev\cemm\composition.py`
- Modify: `C:\dev\cemm\runtime.py`
- Modify: `C:\dev\cemm\config.py`
- Modify: `C:\dev\cemm\training\en_form_schema_seed.json`
- Modify: `C:\dev\cemm\form_packs\en.json`
- Modify: `C:\dev\cemm\language_packs\en.json`
- Modify: `C:\dev\cemm\tools\generate_en_form_pack_v7.py`
- Test: `C:\dev\cemm\tests\test_native_semantic_spine.py`

- [ ] **Step 1: Add a failing test for an unknown-but-valid state dimension query**

```python
def test_valid_state_query_is_not_rejected_for_missing_projection(tmp_path):
    runtime = build_runtime_with_reviewed_composite_definition(tmp_path)
    result = runtime.process("Am I married?", mode="read_only")
    assert result["packet"]["query"]["restrictions"][0]["operator"] == "op:state"
```

- [ ] **Step 2: Lower state-value contribution graphs by force**

```python
if force == "query":
    packet = state_graph.as_query(answer_mode="boolean")
else:
    packet = state_graph.as_claim()
```

The implementation must select force from form evidence and semantic ports,
not from the spelling or ref of the state value.

- [ ] **Step 3: Permit missing state observations during query composition**

```python
if packet_is_state_query and dimension_is_authoritative(dimension):
    factors.append({"status": "unobserved", "factor": 1.0})
else:
    hard_blockers.append(...)
```

- [ ] **Step 4: Compose possessive relation and event graphlets through typed ports**

```python
relative = existential_for(relation_predicate, participant_ref)
relation_app = relation_predicate.bind(
    relation_subject=relative,
    participant_object=participant_ref,
)
event_app = event_predicate.bind(actor=relative, time=time_ref)
```

`relation_subject`, `participant_object`, and `actor` must come from reviewed
frame role metadata. The code may not name a domain relation or a surface form.

- [ ] **Step 5: Regenerate language artifacts and run focused composition tests**

Run: `python tools/generate_en_form_pack_v7.py`

Run: `python -m pytest tests/test_native_semantic_spine.py -k "state_query or composite_definition or possessive" -q`

Expected: PASS.

### Task 4: Project definition graphs for bounded inference and proof

**Files:**
- Modify: `C:\dev\cemm\inference.py`
- Modify: `C:\dev\cemm\proof.py`
- Modify: `C:\dev\cemm\runtime.py`
- Modify: `C:\dev\cemm\semantic_description.py`
- Test: `C:\dev\cemm\tests\test_native_semantic_spine.py`

- [ ] **Step 1: Retrieve only projections linked to the selected definition graph**

```python
rules = store.definition_rule_projections(
    salient_refs=salient_refs,
    generation=authority_generation,
    limit=config.inference_rule_limit,
)
```

- [ ] **Step 2: Preserve graph lineage when deriving a fact**

```python
proof = {
    "rule_ref": rule["rule_ref"],
    "definition_ref": rule["definition_ref"],
    "definition_application_refs": rule["definition_application_refs"],
    "parents": parent_refs,
}
```

- [ ] **Step 3: Expose the definition graph in proof and description results**

```python
assert result["proof_bundle"]["claims"][0]["definition_ref"] == expected_definition_ref
```

- [ ] **Step 4: Run the complete new acceptance set**

Run: `python -m pytest tests/test_native_semantic_spine.py -k "composite_definition or state_query or possessive" -q`

Expected: PASS.

### Task 5: Contract, anti-bloat, and full verification

**Files:**
- Modify: `C:\dev\cemm\CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md`
- Modify: `C:\dev\cemm\RUNTIME_ARCHITECTURE.md`
- Modify: `C:\dev\cemm\DATA_ARCHITECTURE.md`
- Modify: `C:\dev\cemm\V1_ACCEPTANCE.md`
- Test: `C:\dev\cemm\tests\test_native_semantic_spine.py`

- [ ] **Step 1: Record the definition-graph authority rule**

```text
A rule projection is executable derivative data. It is valid only when it
retains a reviewed definition-graph source and cannot outlive that graph's
generation.
```

- [ ] **Step 2: Add an anti-bloat assertion**

```python
assert "mother_in_law" not in production_source_literal_dispatches()
assert "kinbridge" not in production_source_literal_dispatches()
```

- [ ] **Step 3: Run activation and deterministic generation validation**

Run: `python tools/validate_semantic_operational_contract.py`

Run: `python -m pytest -q`

Expected: both exit 0 with all tests passing.

- [ ] **Step 4: Commit the reviewed repair**

```powershell
git add cemm tests tools *.md docs/superpowers
git commit -m "Compose learned definition graphs atomically"
```
