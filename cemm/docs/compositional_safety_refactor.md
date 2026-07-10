# Compositional Safety Derivation Refactor

**Version:** 1.0
**Purpose:** Replace hardcoded keyword/alias matching in SafetyFrameDetector with compositional derivation from primitive atoms, relational edges, and state architecture.
**Date:** 2026-07-10

---

## Problem

SafetyFrameDetector currently uses hardcoded alias-to-category dicts (`_SELF_HARM_ACTIONS`, `_ILLEGAL_ACTIONS`, `_HARM_ACTIONS`) and keyword matching on `input_text`. This bypasses the system's compositional architecture:

- `SituationFrameBuilder` exists but is **never called** in the runtime pipeline
- `RuntimeCycleResult` has no `situation_frame` field — `getattr(result, 'situation_frame', None)` always returns `None`
- `ActionOperatorSchema.permission_policy` and `.risk` are **never read** by any code
- `StateDimensionSchema.polarity_negative/polarity_positive` are **never used** for safety
- Graph `state` atoms with `source="schema_state_delta"` contain dimension/direction/target_role but are **never inspected** by safety detection
- Safety detection runs twice (step 3b and step 8) with identical broken calls
- `OperationalMeaningCompiler._has_safety()` checks for `permission` atoms with `deny`/`restrict` that are never created

## Compositional Derivation Rules

Safety is derived from primitive atoms, not hardcoded phrases:

1. **Self-harm**: action causes state delta on `vital.*` dimension in harmful direction, target entity kind is `self`
2. **Interpersonal violence**: action causes state delta on `vital.*` dimension in harmful direction, target entity kind is `person` (not self)
3. **Illegal activity**: action has `permission_policy == "restricted"` (regardless of state deltas)
4. **Medical risk**: action causes state delta on `vital.*` dimension in harmful direction, `permission_policy == "normal"`, `risk == "high"`

Priority: self_harm > interpersonal_violence > illegal_activity > medical_risk

### Harmful Direction Derivation

A state delta's direction is "harmful" if it moves toward the negative polarity of a vital dimension:
- `vital.health`: decrease → toward "sick" → harmful
- `vital.injured`: decrease → toward "injured" → harmful
- `vital.alive`: decrease → toward "dead" → harmful

This is data-driven via `harmful_polarity` field in `state_dimension_schemas.json`:
- `harmful_polarity: "negative"` means `decrease` is harmful (toward polarity_negative)
- `harmful_polarity: "positive"` means `increase` is harmful (toward polarity_positive)

Dimensions without `harmful_polarity` are not safety-relevant.

## Implementation Phases

### Phase 1: Wire SituationFrameBuilder into runtime
- Add `situation_frame` field to `RuntimeCycleResult`
- Instantiate `SituationFrameBuilder` in `SemanticKernelRuntime.__init__`
- Call `situation_frame_builder.build(percept, kernel)` after step 2 (graph build)
- Store result in `result.situation_frame`
- Pass to `SafetyFrameDetector.detect()` instead of `None`

### Phase 2: Add compositional safety derivation to SafetyFrameDetector
- New method `_detect_from_graph(uol_graph)` — inspects state atoms with `source="schema_state_delta"` and their `causes` edges
- For each harmful state delta, find the action atom via `causes` edge
- Find target entity via `has_role` edge → check `entity_kind` feature
- Look up `ActionOperatorSchema` for `permission_policy` and `risk`
- Derive category from primitives (vital decrease + target=self → self_harm, etc.)
- Fallback: `_detect_from_situation(situation)` — use `expected_outcomes` from SituationFrame
- Last resort: `_detect_from_tokens(input_text)` — use `lookup_alias()` to find action_key, then derive from schema

### Phase 3: Add accessors to ActionOperatorRegistry
- `permission_policy_for(action_key) -> str`
- `risk_for(action_key) -> str`

### Phase 4: Add harmful_polarity to StateDimensionRegistry
- Add `harmful_polarity` field to vital and permission dimensions in `state_dimension_schemas.json`
- Add `is_harmful_direction(state_family, dimension, direction) -> bool` to `StateDimensionRegistry`
- Add `is_safety_relevant(state_family, dimension) -> bool` to `StateDimensionRegistry`

### Phase 5: Remove hardcoded dicts and keyword matching
- Remove `_SELF_HARM_ACTIONS`, `_ILLEGAL_ACTIONS`, `_HARM_ACTIONS`
- Remove `_MODAL_VERBS`, `_ILLEGAL_INTENT_CUES`, `_TARGET_PRONOUNS`
- Remove `safety_category` field from action operator schemas (derived, not stored)
- Remove schema alias loading in `SafetyFrameDetector.__init__`
- Fix `vital.injured` direction in `harm_person` and `self_harm_injury` schemas (increase → decrease)

### Phase 6: Remove duplicate safety detection call
- Remove step 8 safety detection in `SemanticKernelRuntime.run_turn()`
- Keep step 3b safety detection (now with proper situation_frame)
- Move safety override (step 8a) to after step 3b

### Phase 7: Wire safety into OperationalMeaningCompiler._has_safety()
- Check for `state` atoms with `source="schema_state_delta"` that have harmful vital dimensions
- Instead of checking for `permission` atoms with `deny`/`restrict` (never created)

## Files Modified

| File | Change |
|------|--------|
| `types/runtime_cycle.py` | Add `situation_frame` field |
| `kernel/semantic_kernel_runtime.py` | Wire SituationFrameBuilder, remove dup safety call |
| `kernel/safety_frame_detector.py` | Full rewrite of detect() to compositional derivation |
| `kernel/semantic_schema_kernel.py` | Add accessors to ActionOperatorRegistry and StateDimensionRegistry |
| `data/semantic_schemas/state_dimension_schemas.json` | Add `harmful_polarity` to vital/permission dimensions |
| `data/semantic_schemas/action_operator_schemas.json` | Fix vital.injured direction, remove safety_category |
| `kernel/operational_meaning_compiler.py` | Update _has_safety() to check state delta atoms |
| `tests/golden/test_golden_schema_kernel.py` | Update safety test for compositional derivation |
