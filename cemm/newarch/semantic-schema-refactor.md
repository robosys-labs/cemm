# Semantic Schema Refactor — Semantic Schema Kernel Architecture

Status: **IMPLEMENTED — all 9 phases complete**
Priority: High — eliminates meaning fragmentation across three overlapping systems
Audience: AI coding agents and maintainers working on CEMM

---

## 1. Central Invariant

```
Verbs do not mean actions; verbs evoke action schemas.
Nouns do not mean entities; nouns evoke entity-kind/concept candidates.
States do not mean strings; states occupy dimensions on entity slots.
Actions are operators over typed slots and produce state/relation deltas.
```

Schema JSON is canonical boot knowledge.
Runtime truth is validated graph-patch memory.

---

## 2. Problem Statement (Historical — Resolved)

CEMM previously split action/state meaning across three partially overlapping
systems that never converged into a single canonical contract. This has been
resolved by the Semantic Schema Kernel implementation:

### System 1: Language Adapter Keyword Maps (flat)
- `cemm/data/languages/en/action_keywords.json` — flat `{"surface_verb": "action_key"}` mapping
- `cemm/data/languages/ig/action_keywords.json` — same, but only 3 entries
- `EnglishLanguageAdapter.ACTIONS` — hardcoded Python dict duplicating the JSON
- `EnglishLanguageAdapter.STATES`, `EnglishLanguageAdapter.NEEDS` — same pattern
- `JSONLanguageAdapter` loads JSON files but produces identical flat `ActionAtom` objects
- **Problem**: Maps surface verb → action label, but does not define slots, preconditions,
  state deltas, entity kind constraints, or affordances. The "meaning" is implicit in code.

### System 2: uol_semantics.json event_schemas (richer but disconnected)
- `uol_semantics.json` contains `event_schemas` with `action_schema`, `state_schema`,
  `need_schema`, `place_affordance`, `object_affordance`, `social_schema`, `safety_schema`
- Loaded by `event_schema_loader.py` into `EventSchemaStore`
- Used by `SituationFrameBuilder`, `FrameBinder`, `SafetyFrameDetector`
- **NOT used by** `MeaningPerceptor`, `MeaningGraphBuilder`, `SemanticKernelRuntime`,
  `AffordancePredictor`, or `RelationFrameCompiler`
- **Problem**: Richer schemas exist but are side-channel — they never reach the main
  perception → graph → obligation → realization pipeline.

### System 3: verb_state/ (external, richest, unintegrated)
- `C:\dev\nameless_vector\verb_state/` — ~500 verb files with:
  - `applicable_subjects` / `applicable_objects` (entity kind constraints)
  - `goals`, `mechanisms`, `tools`
  - `required_subject_states` / `required_object_states` (preconditions)
  - `final_subject_states` / `final_object_states` (state deltas)
  - State families: physical, emotional, mental, positional
- `noun_state/` — noun-to-entity-type mappings
- **Problem**: External to CEMM, not loaded, not referenced.

### The Fixed Chain

```
Architecture implemented:
  surface verb
  → language alias lookup (ActionOperatorRegistry.lookup_alias)
  → canonical action operator schema (slots, preconditions, state deltas, entity kinds)
  → UOL graph atoms with typed slots (using existing 16 atom kinds + 16 edge types)
  → relation frames with projection policies (structural by default, answerable only when query-relevant)
  → state/relation delta predictions → affordance predictions
  → patch candidates with typed operations

What was replaced:
  ✗ flat keyword map → action_key string
  ✗ ActionAtom with only actor_role/target_role (no slot schema)
  ✗ graph builder hardcodes role inference
  ✗ no state delta computation
  ✗ no entity kind validation
  ✗ affordance predictor uses hardcoded rules, not schema-driven
```

---

## 3. Target Architecture — Semantic Schema Kernel

The real missing object is not just `ActionSchemaRegistry`. It is a full
**Semantic Schema Kernel** comprising seven schema types:

```
EntityKindSchema        — entity kinds with native slot families
StateDimensionSchema    — state families and dimensions on entity slots
SlotSchema              — slot definitions (role, entity kind constraints, cardinality)
ActionOperatorSchema    — action operators over typed slots with preconditions + state/relation deltas
AffordanceSchema        — affordance rules derived from action operator schemas
ProjectionPolicySchema  — projection policy per slot/edge (structural vs answerable)
PatchOperationSchema    — typed patch operations (upsert_relation, upsert_state, etc.)
```

### 3.1 New Schema Files

```
cemm/data/semantic_schemas/
  entity_kind_schemas.json     — EntityKindSchema definitions
  state_dimension_schemas.json — StateDimensionSchema definitions
  slot_schemas.json            — SlotSchema definitions
  action_operator_schemas.json — ActionOperatorSchema definitions
  affordance_schemas.json      — AffordanceSchema definitions
  projection_policy_schemas.json — ProjectionPolicySchema definitions
  patch_operation_schemas.json   — PatchOperationSchema definitions
```

### 3.2 Demoted Language Files

```
cemm/data/languages/en/action_keywords.json  → language alias layer only
cemm/data/languages/ig/action_keywords.json  → language alias layer only
```

Each entry becomes:
```json
{
  "surface": "eat",
  "action_key": "consume_food"
}
```

No schema info. The schema lives in `action_operator_schemas.json`.

### 3.3 ActionOperatorSchema Format

```json
{
  "action_key": "consume_food",
  "operator_family": "consume",
  "aliases": {
    "en": ["eat", "consume", "feed"],
    "ig": ["rie"]
  },
  "slots": {
    "actor": {
      "allowed_entity_kinds": ["person", "animal", "self", "autonomous_agent"],
      "required": true
    },
    "object": {
      "allowed_entity_kinds": ["food", "object"],
      "required": true
    }
  },
  "preconditions": [
    {"target": "actor", "slot": "capability.can_consume", "check": "exists"},
    {"target": "object", "slot": "physical.edible", "check": "exists"}
  ],
  "state_deltas": [
    {"target": "actor", "dimension": "vital.hunger", "direction": "decrease", "confidence": 0.85},
    {"target": "object", "dimension": "resource.quantity", "direction": "decrease", "confidence": 0.9}
  ],
  "relation_deltas": [],
  "needs_satisfied": ["food"],
  "risk": "low",
  "permission_policy": "normal",
  "safety_category": "",
  "emotional_valence": "neutral"
}
```

State deltas and relation deltas are **not** new UOL edge types. They are
schema-level declarations that the runtime compiles into:
- `has_property` edges on entity atoms (for state occupancy)
- `causes` edges between action and state atoms (for delta effects)
- Relation atoms with `has_role` edges (for relation deltas)
- `PatchOperation` objects for durable writes

All using the existing 16 atom kinds and 16 edge types defined in AGENTS.md.

### 3.4 EntityKindSchema Format

```json
{
  "entity_kind": "person",
  "native_slots": {
    "identity.name": {"type": "string", "projection": "answerable"},
    "identity.type": {"type": "string", "projection": "structural"},
    "physical.height": {"type": "quantity", "projection": "answerable"},
    "physical.weight": {"type": "quantity", "projection": "answerable"},
    "vital.health": {"type": "state", "projection": "answerable"},
    "vital.hunger": {"type": "state", "projection": "answerable"},
    "affect.mood": {"type": "state", "projection": "answerable"},
    "cognition.knowledge": {"type": "set", "projection": "answerable"},
    "volition.preference": {"type": "relation", "projection": "answerable"},
    "capability.can_speak": {"type": "boolean", "projection": "answerable"},
    "location.current": {"type": "place_ref", "projection": "answerable"},
    "social.relationships": {"type": "relation_set", "projection": "answerable"},
    "permission.allowed_actions": {"type": "set", "projection": "structural"}
  },
  "parent_kind": "biological_body"
}
```

Entity kinds form a hierarchy:
```
biological_body → person, animal
synthetic_agent → autonomous_agent, interactive_app
physical_agent → device, robot
organization → group, company
object → food, tool, virtual_object
concept → theory, plan
place → location, region
```

### 3.5 StateDimensionSchema Format

```json
{
  "state_family": "vital",
  "dimensions": {
    "hunger": {"polarity_negative": "hungry", "polarity_positive": "satisfied", "range": [0, 1]},
    "health": {"polarity_negative": "sick", "polarity_positive": "healthy", "range": [0, 1]},
    "energy": {"polarity_negative": "tired", "polarity_positive": "energetic", "range": [0, 1]}
  },
  "applies_to": ["person", "animal", "self"]
}
```

State families (15 total):
1. `identity` — name, type, species, role, category
2. `physical` — height, size, weight, color, shape, age
3. `vital` — alive, sick, injured, hungry, tired
4. `affective` — happy, sad, angry, afraid, love, hate
5. `cognitive` — knows, believes, confused, certain, attentive
6. `volitional` — wants, needs, prefers, avoids, intends
7. `capability` — can_move, can_speak, can_remember, has_internet
8. `resource` — energy, battery, data, money, time, food, memory
9. `geospatial` — location, distance, orientation, inside/outside
10. `possession` — owns, holds, controls, has_access_to
11. `social` — friend, stranger, authority, trusted, hostile
12. `permission` — allowed, forbidden, obligated, risky, safe
13. `temporal` — before, after, current, stale, pending, completed
14. `informational` — known, unknown, ambiguous, contradicted, verified
15. `operational` — online, offline, available, busy, degraded, blocked

### 3.6 ProjectionPolicySchema Format

```json
{
  "slot_key": "actor",
  "structural": true,
  "answerable": false,
  "projection_policy": "none",
  "rationale": "Action slots are structural by default; only query-explicit slots become answerable"
}
```

**Critical rule**: Action slots are **structural by default**, not answerable.
Making action slots answerable by default would recreate the `has_role` bug
where structural bindings pollute the answerable relation frame space.
Only entity-kind native slots marked `"projection": "answerable"` produce
answerable frames. Action operator slots always start as `structural` with
`projection_policy: "none"` unless a query explicitly asks about them.

### 3.7 PatchOperationSchema Format

```json
{
  "operation": "upsert_state",
  "fields": {
    "entity_ref": "string",
    "dimension": "string",
    "direction": "increase|decrease|set",
    "value": "optional",
    "confidence": "float"
  },
  "validates_against": "ActionOperatorSchema.preconditions"
}
```

Patch operations are **not** new UOL primitives. They are typed instructions
for the patch pipeline (`PatchExtractor → PatchValidator → PatchCommitter`).
Existing operations: `upsert_relation`, `upsert_concept_alias`, `upsert_construction`.
New operations: `upsert_state`, `upsert_entity_kind`.

### 3.8 Compilation Flow (Target)

```
surface verb/noun
  → language alias lookup (action_keywords.json / state_keywords.json)
  → canonical schema lookup (action_operator_schemas.json / state_dimension_schemas.json)
  → slot binding (entity kind validation from entity_kind_schemas.json)
  → UOL graph atoms with typed slots + entity kind metadata
    (using existing 16 atom kinds + 16 edge types only)
  → relation frames (projection policy from ProjectionPolicySchema — structural by default)
  → state/relation delta predictions (from ActionOperatorSchema.state_deltas)
  → affordance predictions (from AffordanceSchema — schema-driven, not hardcoded)
  → patch candidates (typed PatchOperations from PatchOperationSchema)
```

---

## 4. Implementation Phases

### Phase 1: Create Schema Files + Transform verb_state Data — ✅ COMPLETE

**Goal**: Generate canonical schema JSON files from verb_state data.

**Steps**:
1. Create `cemm/data/semantic_schemas/` directory
2. Write Python transform script `cemm/scripts/transform_verb_state.py` that:
   - Reads all `verb_state/*.json` files from `C:\dev\nameless_vector\verb_state\`
   - Reads all `noun_state/*.json` files from `C:\dev\nameless_vector\noun_state\`
   - Transforms each verb entry into canonical `action_operator_schemas.json` format:
     - `applicable_subjects` → `slots.actor.allowed_entity_kinds`
     - `applicable_objects` → `slots.object.allowed_entity_kinds`
     - `required_subject_states` → `preconditions` (subject)
     - `required_object_states` → `preconditions` (object)
     - `final_subject_states` → `state_deltas` (subject)
     - `final_object_states` → `state_deltas` (object)
     - `goals` → `goals`
     - `mechanisms` → `mechanisms`
     - `tools` → `tools`
   - Transforms noun entries into `entity_kind_schemas.json` seed data
   - Maps verb_state entity types to CEMM entity kinds:
     - `biological_body` → `person` / `animal` (split by noun_state data)
     - `synthetic_agent` → `autonomous_agent`
     - `physical_agent` → `device`
     - `organization` → `organization`
     - `object` → `object`
     - `virtual_object` → `virtual_object`
     - `concept` → `concept`
     - `place` → `place`
3. Create `state_dimension_schemas.json` with the 15 state families
4. Create `slot_schemas.json` with slot role definitions
5. Create `entity_kind_schemas.json` with entity kind hierarchy + native slots
6. Create `projection_policy_schemas.json` with default structural policies for action slots
7. Create `patch_operation_schemas.json` with typed patch operation definitions
8. Create `affordance_schemas.json` (seeded from existing affordance rules + emotional valence)
9. Merge existing `uol_semantics.json` `event_schemas` action entries into
   `action_operator_schemas.json` (deduplicate by `action_key`, preserving richer data)

**Output files** (7 schema files):
- `cemm/data/semantic_schemas/action_operator_schemas.json`
- `cemm/data/semantic_schemas/entity_kind_schemas.json`
- `cemm/data/semantic_schemas/state_dimension_schemas.json`
- `cemm/data/semantic_schemas/slot_schemas.json`
- `cemm/data/semantic_schemas/affordance_schemas.json`
- `cemm/data/semantic_schemas/projection_policy_schemas.json`
- `cemm/data/semantic_schemas/patch_operation_schemas.json`

**Verification**: JSON validity, schema count, spot-check 10 verbs for completeness.

---

### Phase 2: Create Semantic Schema Kernel — ✅ COMPLETE

**Goal**: Build the full Semantic Schema Kernel — Python registries for all 7 schema types.

**Steps**:
1. Create `cemm/kernel/semantic_schema_kernel.py` with 7 registries:
   - `EntityKindRegistry` — loads `entity_kind_schemas.json`
     - `lookup_kind(kind) → EntityKindSchema | None`
     - `is_assignable(entity_kind, slot_kind) → bool`
     - `native_slots(entity_kind) → dict[str, SlotDef]`
   - `StateDimensionRegistry` — loads `state_dimension_schemas.json`
     - `lookup_family(family) → StateFamilySchema | None`
     - `lookup_dimension(dimension) → StateDimensionSchema | None`
   - `SlotRegistry` — loads `slot_schemas.json`
     - `lookup_slot(slot_key) → SlotSchema | None`
   - `ActionOperatorRegistry` — loads `action_operator_schemas.json`
     - `lookup_by_action_key(key) → ActionOperatorSchema | None`
     - `lookup_by_surface(surface, lang="en") → ActionOperatorSchema | None`
   - `AffordanceRegistry` — loads `affordance_schemas.json`
     - `lookup_by_action_key(key) → AffordanceSchema | None`
     - `lookup_by_effect_type(effect_type) → list[AffordanceSchema]`
   - `ProjectionPolicyRegistry` — loads `projection_policy_schemas.json`
     - `lookup_policy(slot_key, edge_type) → ProjectionPolicySchema | None`
   - `PatchOperationRegistry` — loads `patch_operation_schemas.json`
     - `lookup_operation(op_name) → PatchOperationSchema | None`
2. Define typed dataclasses for all 7 schema types
3. Create `SemanticSchemaKernel` container holding all 7 registries
4. Wire `SemanticSchemaKernel` into `SemanticCPU.__init__`

**Verification**: Unit test — load all schemas, verify lookup by action_key and by surface alias.

---

### Phase 3: Demote Language Adapter to Alias Layer — ✅ COMPLETE

**Goal**: Language adapter becomes a thin alias resolver, not a meaning definer.

**Steps**:
1. Refactor `EnglishLanguageAdapter`:
   - Remove hardcoded `ACTIONS`, `STATES`, `NEEDS` dicts
   - `map_actions()` → resolve surface token via `ActionOperatorRegistry.lookup_by_surface()`
   - Produce `ActionAtom` with `action_key` from schema, plus slot metadata from schema
   - `map_states()` → resolve via `StateDimensionRegistry`
   - `map_needs()` → resolve via `StateDimensionRegistry` (needs are state deficits)
2. Refactor `JSONLanguageAdapter`:
   - `action_keywords.json` becomes pure alias: `{"surface": "eat", "action_key": "consume_food"}`
   - `map_actions()` → look up `action_key` from JSON, then resolve schema from registry
   - Same for `state_keywords.json`, `need_keywords.json`
3. Add `ActionAtom.schema_slots` field to carry schema-derived slot definitions forward
4. No fallback behavior — if no schema is found, the atom is produced with
   `action_key` from the alias layer but `schema_slots=None`. The runtime handles
   missing schemas explicitly, not via silent fallback.

**Verification**: New test: `map_actions("eat")` produces `ActionAtom`
with `action_key="consume_food"` and `schema_slots={"actor": ..., "object": ...}`.
Update existing tests to expect schema-driven atoms.

---

### Phase 4: Wire Schema Kernel into MeaningGraphBuilder — ✅ COMPLETE

**Goal**: Graph builder uses schema slots for typed atom creation + state/relation deltas.

**Implementation notes**:
- `_add_actions()` attaches `schema_slots` from `ActionOperatorRegistry` to action atoms
- `_connect_action_roles()` creates `has_role` edges with `allowed_entity_kinds` and `kind_valid` validation
- `_compile_state_deltas()` creates `state` atoms + `causes` edges + `has_property` edges from schema `state_deltas`
- `_find_role_atom()` uses O(degree) adjacency index lookup (not O(E) edge scan)
- `_add_emotional_evaluations()` uses schema `emotional_valence` for relation key selection
- `_extract_state_delta_patches()` uses `incoming()` adjacency index for entity lookup
- Entity kind inference maps `user` → `person`, `role_placeholder` → `object`

**Steps**:
1. In `MeaningGraphBuilder._add_actions()`:
   - When creating action atoms, attach schema slot metadata from `ActionOperatorRegistry`
   - Create `has_role` edges with `allowed_entity_kinds` from schema
   - For each `state_delta` in schema, create:
     - A `state` atom on the target entity (using existing `state` atom kind)
     - A `causes` edge from the action atom to the state atom (using existing `causes` edge type)
     - A `has_property` edge from the entity to the state atom (using existing `has_property` edge type)
   - No new edge types are introduced.
2. In `MeaningGraphBuilder._add_emotional_evaluations()`:
   - Use schema `emotional_valence` field instead of hardcoded `_EMOTIONAL_VERB_TO_RELATION`
   - Schema-driven: if `action_schema.emotional_valence == "positive"` → `likes` relation
3. In `MeaningGraphBuilder._predict_affordances()`:
   - Generate affordance predictions from `AffordanceRegistry` instead of hardcoded rules
   - Each schema affordance → `AffordancePrediction` with `effect_type` from schema
4. Add entity kind validation: when binding entities to slots, check `allowed_entity_kinds`
   against `EntityKindRegistry.is_assignable()`

**Verification**: Test "I eat rice" → graph has action atom with schema slots,
`causes` edges to `state` atoms for hunger decrease and quantity decrease.
Test "I love music" → `evaluates` edge from schema emotional_valence, not hardcoded dict.

---

### Phase 5: Wire Schema into RelationFrameCompiler — ✅ COMPLETE

**Goal**: Relation frames derive projection policy from ProjectionPolicySchema,
not hardcoded maps.

**Steps**:
1. In `RelationFrameCompiler`:
   - Replace `_EDGE_TYPE_TO_FAMILY`, `_EDGE_TYPE_TO_KEY` hardcoded dicts with
     schema registry lookups where possible
   - Action-derived relation frames get family from `ActionOperatorSchema.operator_family`
   - State-derived relation frames get family from `StateDimensionRegistry`
2. Schema-driven projection policy from `ProjectionPolicyRegistry`:
   - **Action slots are structural by default** — `structural=true`, `answerable=false`,
     `projection_policy="none"` unless a query explicitly asks about them
   - Entity-kind native slots use their `projection` field from `EntityKindSchema`
     (`"answerable"` or `"structural"`)
   - This prevents recreating the `has_role` bug where structural bindings
     pollute the answerable relation frame space
3. Remove hardcoded fallbacks for edge types — replace with schema lookups

**Verification**: Existing golden tests updated. New test: `consume_food` action
produces **structural** relation frames for actor and object slots (not answerable).
Entity native slots like `identity.name` produce answerable frames.

---

### Phase 6: Wire Schema into AffordancePredictor — ✅ COMPLETE

**Goal**: Affordance predictions are schema-driven from `AffordanceRegistry`,
not hardcoded rules.

**Steps**:
1. In `AffordancePredictor`:
   - Replace hardcoded `_seed_rules` with rules loaded from `AffordanceRegistry`
   - `AffordanceSchema` entries define: trigger action_key, effect_type,
     predicted_patch_template, preconditions
   - Each `ActionOperatorSchema.state_deltas` generates an `AffordanceSchema` entry
     at load time if not explicitly defined
   - Keep `evaluation_shift` for emotional_valence actions (from schema)
2. Schema-driven affordance keys:
   - `user_consume_food` instead of generic `user_action`
   - `evaluation_shift` for emotional_valence actions
   - `state_change` for state_delta actions

**Verification**: Test "I eat rice" → affordance prediction with `effect_type="vital_change"`
and `predicted_patch_template` referencing hunger decrease.

---

### Phase 7: Wire Schema into Patch Extraction — ✅ COMPLETE

**Goal**: Patch candidates carry typed operations from `PatchOperationSchema`.

**Steps**:
1. In `MeaningGraphBuilder._extract_graph_patches()`:
   - For action atoms with schema, extract patch candidates for each `state_delta`
   - Patch operation type: `upsert_state` for state deltas (new PatchOperation type,
     not a new UOL edge type)
   - Patch operation type: `upsert_relation` for relation atoms (existing)
2. In `PatchValidator`:
   - Validate patch operations against `ActionOperatorSchema.preconditions`
   - Reject patches where entity kind doesn't match slot constraints
3. In `PatchCommitter`:
   - Commit `upsert_state` patches to durable store (new patch operation type,
     not a new UOL primitive)

**Verification**: Test "I eat rice" → patch candidate with `upsert_state` for
actor.hunger=decrease. Test patch validation rejects invalid entity kind bindings.

---

### Phase 8: Migrate Existing Consumers + Delete Old Systems — ✅ COMPLETE

**Goal**: Replace all old meaning systems with the Semantic Schema Kernel.
No backward compatibility layers — old systems are replaced, not kept alongside.

**Completed**:
- `event_schema_loader.py` deleted (renamed to `.bak`)
- `event_schemas` section removed from `uol_semantics.json`
- `EnglishLanguageAdapter` and `JSONLanguageAdapter` replaced by `SchemaBackedLanguageAdapter`
- Hardcoded `ACTIONS`/`STATES`/`NEEDS` dicts removed
- Hardcoded `_seed_rules` in `AffordancePredictor` replaced by schema-driven rules
- Hardcoded `_EMOTIONAL_VERB_TO_RELATION` replaced by schema `emotional_valence` lookup
- `MeaningPerceptor` properly wired with `schema_kernel` parameter (no monkey-patching)
- `SemanticKernelRuntime` passes `schema_kernel` to `SemanticCPU`

**Steps**:
1. Migrate `SituationFrameBuilder` to use `ActionOperatorRegistry` instead of `EventSchemaStore`
2. Migrate `FrameBinder` to use `ActionOperatorRegistry`
3. Migrate `SafetyFrameDetector` to use `AffordanceRegistry` for safety categories
4. Delete `event_schema_loader.py` — `EventSchemaStore` is replaced by `SemanticSchemaKernel`
5. Remove `event_schemas` section from `uol_semantics.json` (action/state/need schemas
   now live in `semantic_schemas/` files)
6. Keep `uol_semantics.json` for non-schema entries (uol_semantics frame aliases,
   act_type_metadata, discourse_frames, etc.)
7. Delete hardcoded `ACTIONS`, `STATES`, `NEEDS` dicts from `EnglishLanguageAdapter`
8. Delete hardcoded `_seed_rules` from `AffordancePredictor`
9. Delete hardcoded `_EMOTIONAL_VERB_TO_RELATION` from `MeaningGraphBuilder`
10. Delete hardcoded `_EDGE_TYPE_TO_FAMILY`, `_EDGE_TYPE_TO_KEY` from `RelationFrameCompiler`
    (where replaced by schema lookups)
11. Update all existing tests to expect schema-driven behavior
12. Delete tests that verified old hardcoded behavior — replace with schema-driven tests

**Verification**: Full test suite passes. No old meaning system code remains.

---

### Phase 9: Write Golden Tests for Schema-Driven Pipeline — ✅ COMPLETE

**Goal**: Verify end-to-end schema-driven meaning flow.

**All 10 golden tests implemented and passing** (80 total tests in suite).

**Tests**:
1. `test_schema_lookup` — registry resolves surface → canonical action operator schema
2. `test_schema_slot_binding` — action atom carries schema slots with entity kind constraints
3. `test_schema_state_deltas` — graph has `causes` edges to `state` atoms from schema state_deltas
4. `test_schema_entity_kind_validation` — invalid entity kinds rejected at slot binding
5. `test_schema_affordance_prediction` — affordance from AffordanceRegistry, not hardcoded
6. `test_schema_patch_extraction` — patch with typed `upsert_state` operation
7. `test_schema_emotional_valence` — `evaluates` edge from schema, not hardcoded dict
8. `test_schema_multilingual` — Igbo "rie" resolves to same schema as English "eat"
9. `test_schema_projection_policy` — action slots are structural, entity native slots are answerable
10. `test_schema_full_pipeline` — "I eat rice" end-to-end with schema-driven everything

---

## 5. Non-Drift Principles

- **No** verb-specific Python code — all verb semantics in schema JSON
- **No** hardcoded action_key → meaning mappings in Python
- **No** hardcoded state dimension families in Python
- **No** hardcoded entity kind hierarchies in Python
- **No** new UOL atom kinds or edge types — use the existing 16 + 16
- **Schema JSON is canonical boot knowledge** — runtime truth is validated graph-patch memory
- **Language files are aliases only** — they point to canonical schemas, never define meaning
- **No backward compatibility** — old systems are replaced, not kept alongside
- **Action slots are structural by default** — not answerable, to prevent has_role bug recurrence
- **verb_state data is a seed** — transformed once, then maintained in CEMM schema files
- **State deltas are schema declarations** — compiled into existing UOL primitives
  (`state` atoms + `causes` edges + `has_property` edges), not new edge types

---

## 6. File Inventory

### New Files
```
cemm/data/semantic_schemas/
  action_operator_schemas.json
  entity_kind_schemas.json
  state_dimension_schemas.json
  slot_schemas.json
  affordance_schemas.json
  projection_policy_schemas.json
  patch_operation_schemas.json
cemm/kernel/semantic_schema_kernel.py
cemm/scripts/transform_verb_state.py
cemm/tests/golden/
  test_golden_schema_pipeline.py
```

### Modified Files
```
cemm/kernel/language_adapter.py          — demote to alias resolver, delete hardcoded dicts
cemm/kernel/meaning_graph_builder.py     — schema-driven atom/edge creation
cemm/kernel/meaning_perceptor.py         — pass schema kernel to adapter
cemm/kernel/relation_frame_compiler.py   — schema-driven projection policy
cemm/kernel/affordance_predictor.py      — schema-driven rule generation
cemm/kernel/semantic_cpu.py              — wire SemanticSchemaKernel
cemm/kernel/semantic_kernel_runtime.py   — expose schema kernel
cemm/kernel/situation_frame_builder.py   — migrate to ActionOperatorRegistry
cemm/kernel/frame_binder.py              — migrate to ActionOperatorRegistry
cemm/kernel/safety_frame_detector.py     — migrate to AffordanceRegistry
cemm/types/meaning_percept.py            — add schema_slots to ActionAtom
cemm/data/languages/en/action_keywords.json  — demote to alias layer
cemm/data/languages/ig/action_keywords.json  — demote to alias layer
cemm/data/uol_semantics.json             — remove event_schemas section
```

### Deleted Files
```
cemm/kernel/event_schema_loader.py       — replaced by SemanticSchemaKernel
```

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| verb_state data uses inconsistent entity type names | Normalize during transform script |
| ~500 verbs may produce too many schemas | Filter to verbs already in action_keywords + common verbs |
| Breaking existing tests | Update tests to expect schema-driven behavior; delete tests verifying old hardcoded behavior |
| Schema lookup overhead | Cache lookups, lazy load |
| noun_state data is sparse | Seed entity_kind_schemas from user's table, not just noun_state |
| Emotional verbs not in verb_state | Add manually to action_operator_schemas.json |
| Migrating SituationFrameBuilder/FrameBinder may break frame pipeline | Test frame pipeline after migration |
| Removing event_schemas from uol_semantics.json breaks JSON consumers | All consumers migrated in Phase 8 |

---

## 8. Success Criteria — All Met ✅

1. ✅ `action_keywords.json` contains only `{"surface": "...", "action_key": "..."}` entries
2. ✅ `action_operator_schemas.json` is the canonical boot knowledge for action semantics
3. ✅ `map_actions("eat")` and `map_actions("rie")` (Igbo) resolve to the same `consume_food` schema
4. ✅ Graph builder creates `state` atoms + `causes` edges from schema state_deltas (no new edge types)
5. ✅ Affordance predictor generates rules from `AffordanceRegistry`, not hardcoded `_seed_rules`
6. ✅ Relation frame compiler uses `ProjectionPolicyRegistry` — action slots structural by default
7. ✅ `event_schema_loader.py` is deleted; all consumers use `SemanticSchemaKernel`
8. ✅ No hardcoded `ACTIONS`/`STATES`/`NEEDS` dicts remain in `language_adapter.py`
9. ✅ No hardcoded `_EMOTIONAL_VERB_TO_RELATION` dict remains in `meaning_graph_builder.py`
10. ✅ Full test suite passes (80 tests) with schema-driven behavior
11. ✅ Golden tests verify schema-driven pipeline end-to-end
12. ✅ AGENTS.md updated with Semantic Schema Kernel architecture

### Additional Improvements Beyond Original Plan

- **Adjacency index in UOLGraph**: `_outgoing` and `_incoming` dicts provide O(degree) edge lookups instead of O(E) full edge scans. `_find_role_atom()` and `_extract_state_delta_patches()` use this index.
- **Proper schema kernel wiring**: `MeaningPerceptor` accepts `schema_kernel` and `graph_builder` via constructor parameters, eliminating monkey-patching. `SemanticKernelRuntime` explicitly passes `schema_kernel` to `SemanticCPU`.
- **Entity kind inference**: `_infer_entity_kind()` maps `user` → `person`, `role_placeholder` → `object`, with trace logging for skipped state deltas.
- **Emotional valence fallback**: `_add_emotional_evaluations()` uses schema `emotional_valence` as fallback for relation key selection when relation deltas are absent.
