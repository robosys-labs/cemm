# Meaning-Based Safety Detection Refactor Plan

## Problem

The current safety detection implementation (even after the compositional refactor) is **not truly meaning-based**. It operates as a **separate pre-emption gate** that runs *before* the operational meaning and state transmutation pipeline. It inspects raw graph atoms and schema aliases directly, bypassing the core CEMM semantic primitives that were designed for exactly this purpose.

### Architectural Violations

1. **Safety detection runs at step 3b — before operational meaning compilation (step 3c).**
   The 3.2 improvement plan specifies the pipeline order:
   ```
   5. compile state occupancy and state-delta candidates
   6. compile OperationalMeaningFrames
   7. arbitrate meaning frames
   8. compile StateTransmutationFrames
   9. run causal/effect router  ← safety creates refusal/risk effect HERE
   ```
   Safety should be an **effect of the causal router** (step 9), not a pre-emption gate before step 6.

2. **`StateOccupancyFrame` is defined but never instantiated.**
   The system has no concept of "current entity state." Safety cannot reason about state transitions because it doesn't know the prior state. A harm action that would move an already-injured entity further toward death is more severe than one on a healthy entity.

3. **`StateDeltaFrame` is defined but never instantiated.**
   Proposed state changes exist only as raw graph atoms (`source="schema_state_delta"`). They are never compiled into `StateDeltaFrame`s — the authoritative type for proposed changes. Safety reads raw graph atoms instead of the compiled authority units.

4. **`StateTransmutationCompiler` doesn't compile safety-relevant transmutations from schema state deltas.**
   It only handles `profile_assertion`, `style_feedback`, `session_exit`, `user_state_report`, and `safety_candidate` (a placeholder). It never compiles transmutations from the graph's `schema_state_delta` atoms — the actual state changes that actions would cause.

5. **`_has_safety()` in `OperationalMeaningCompiler` duplicates safety detection logic.**
   It re-derives safety from graph atoms instead of using the `SafetyFrame` that was already detected. And `_classify_frame()` calls `_has_safety()` *before* arbitration, creating a circular dependency.

6. **Tier 3 (token-based alias lookup) is still surface-level keyword matching.**
   It's moved from hardcoded dicts to schema aliases, but it's still matching surface tokens. A true meaning-based approach would never need token matching — the graph and transmutation pipeline should carry all semantic information.

7. **`OperationalCausalRouter` creates a generic `activate_safety_refusal` effect.**
   It doesn't use the `SafetyFrame`'s category, severity, or response mode. The 3.2 plan says "safety creates refusal/risk effect" — this should be a typed effect with full safety context.

8. **`_classify_safety()` is too shallow.**
   It only considers: `state_family`, `target_kind`, `permission_policy`, `risk`.
   It doesn't consider:
   - Current entity state (is the entity already injured?)
   - Magnitude of the state change
   - Multiple state deltas from the same action
   - Relation deltas (e.g., destroying a trust relationship)
   - The authority of the speaker (can they command this action?)
   - Whether the action is being requested, reported, or commanded
   - Social context (is this a game? a hypothetical? a report about past events?)

## Solution: True Meaning-Based Safety Through the Transmutation Pipeline

### Core Insight

Safety is a **property of state transmutations**, not a property of input text or graph atoms. A `SafetyFrame` should be derived from `StateTransmutationFrame`s — the authority units that describe resolved state transitions with prior state, proposed state, direction, authority, and persistence policy.

### Pipeline Reordering

```
Current (broken):
  2b. Build situation frame
  3b. Safety detection (pre-emption gate)  ← WRONG: before meaning compilation
  3c. Compile operational meaning
  3c. Compile state transmutations
  3c. Route effects
  8. Safety override (post-hoc patch)

Proposed (correct):
  2b. Build situation frame
  3a. Compile semantic program
  3b. Compile operational meaning frames
  3c. Arbitrate meaning frames
  3d. Compile state occupancy frames (NEW — from graph state atoms + context kernel)
  3e. Compile state delta frames (NEW — from graph schema_state_delta atoms)
  3f. Compile state transmutation frames (EXTENDED — from deltas + occupancy + authority)
  3g. Safety detection from transmutations (MOVED — after transmutation compilation)
  3h. Route effects (EXTENDED — safety effect from SafetyFrame)
  3i. Build obligation contract (with safety_frame)
```

### Implementation Phases

#### Phase A: Activate `StateOccupancyFrame` — Entity State Tracking

**File:** `kernel/state_occupancy_compiler.py` (NEW)

Compile `StateOccupancyFrame`s from:
- Graph state atoms (`kind="state"`, `source="schema_state_delta"` or `"reported"`)
- `ContextKernel` entity state (user affect, self operational status)
- Prior turn's transmutations that were applied (session state)

Each occupancy frame records:
```python
StateOccupancyFrame(
    target_ref="entity:user",
    state_family="vital",
    dimension="health",
    current_value=0.8,  # from prior transmutations or defaults
    confidence=0.7,
    temporal_scope="session",
)
```

**Registry:** Add `EntityStateRegistry` to `ContextKernel` (or a lightweight dict) that tracks current state values per entity per dimension. Updated by `OutputStateUpdater` after each turn.

#### Phase B: Activate `StateDeltaFrame` — Proposed Change Compilation

**File:** `kernel/state_delta_compiler.py` (NEW)

Compile `StateDeltaFrame`s from the graph's `schema_state_delta` atoms. Each delta frame records:
```python
StateDeltaFrame(
    target_ref="entity:user",
    state_family="vital",
    dimension="health",
    proposed_value=None,  # direction-based, not value-based
    direction="decrease",
    source_frame_id="omf_xxx",
    confidence=0.9,
    features={"action_key": "physically_harm_target", "target_role": "target"},
)
```

The compiler traverses the graph:
1. Find all `state` atoms with `source="schema_state_delta"`
2. For each, find the `causes` edge to get the source action atom
3. For each, find the `has_property` edge to get the target entity
4. Determine `target_ref` from the entity atom's key
5. Create a `StateDeltaFrame` with the dimension, direction, and action context

#### Phase C: Extend `StateTransmutationCompiler` — Compile from State Deltas

**File:** `kernel/state_transmutation_compiler.py` (MODIFY)

Add a new compilation path: when an `OperationalMeaningFrame` has associated `StateDeltaFrame`s (from Phase B), compile them into `StateTransmutationFrame`s with:
- `prior_value` from the corresponding `StateOccupancyFrame` (Phase A)
- `proposed_value` derived from direction + prior_value
- `transmutation_kind` from the frame type:
  - `command` → `"commanded"`
  - `assertion` → `"reported"`
  - `question` → `"desired"` (hypothetical)
  - `safety_candidate` → `"inferred"`
- `authority` from the frame's source:
  - User command → `"user_asserted"`
  - Safety candidate → `"policy_authorized"`
  - Inferred → `"inferred"`
- `persistence_policy` from the frame type + safety evaluation:
  - Safety-relevant transmutation → `"quarantine"` (never persist harmful state changes)
  - Normal command → `"session_state"`
  - Writable assertion → `"graph_patch_candidate"`

The safety_candidate path is replaced: instead of creating a placeholder "candidate" transmutation, it compiles real transmutations from the graph's state delta atoms.

#### Phase D: Rewrite `SafetyFrameDetector` — Transmutation-Based Detection

**File:** `kernel/safety_frame_detector.py` (REWRITE)

The detector now consumes `StateTransmutationFrame`s, not raw graph atoms or tokens:

```python
def detect(
    self,
    transmutations: list[StateTransmutationFrame],
    occupancy_frames: list[StateOccupancyFrame],
    situation: SituationFrame | None = None,
) -> SafetyFrame | None:
```

**Detection logic:**

For each transmutation:
1. Check if the state family + dimension is safety-relevant (`StateDimensionRegistry.is_safety_relevant`)
2. Check if the direction is harmful (`StateDimensionRegistry.is_harmful_direction`)
3. If harmful, classify based on:
   - `target_ref` → entity kind (self vs person vs animal)
   - `features.get("permission_policy")` → restricted vs normal
   - `features.get("risk")` → severity
   - `prior_value` from occupancy → magnitude assessment
   - `transmutation_kind` → intent classification:
     - `"commanded"` → user is requesting this → high concern
     - `"reported"` → user is reporting past event → context-dependent
     - `"desired"` → hypothetical → moderate concern
     - `"inferred"` → system inferred → high concern

4. Classify into category:
   - `self_harm`: vital harmful direction, target=self, transmutation_kind=commanded/desired
   - `interpersonal_violence`: vital harmful direction, target=person, permission_policy=restricted
   - `illegal_activity`: permission_policy=restricted (any state family)
   - `medical_risk`: vital harmful direction, permission_policy=normal, risk=high, target=person/self

5. Assess severity from:
   - `risk` level from schema
   - Magnitude of change (direction + prior_value)
   - Number of harmful deltas in the same action
   - Whether multiple vital dimensions are affected simultaneously

6. Build `SafetyFrame` with:
   - `harmful_outcomes` from the harmful transmutations
   - `must_not_do` from category-specific policy
   - `allowed_response_mode` from category
   - `actor_entity_id` and `target_entity_id` from transmutation refs
   - `requested_action` from transmutation features

**Fallback removed:** No token-based alias lookup. If the graph and transmutation pipeline don't produce safety-relevant transmutations, there is no safety concern. The pipeline is the single source of truth.

#### Phase E: Extend `OperationalCausalRouter` — Typed Safety Effects

**File:** `kernel/operational_causal_router.py` (MODIFY)

Replace the generic `activate_safety_refusal` with typed safety effects:

```python
if frame.frame_type == "safety_candidate" and safety_frame is not None:
    effects.append(OperationalEffect(
        effect_type="safety_refusal",
        target="conversation:safety",
        delta={
            "category": safety_frame.category,
            "severity": safety_frame.severity,
            "response_mode": safety_frame.allowed_response_mode,
            "must_not_do": safety_frame.must_not_do,
            "harmful_outcomes": [o.changed_dimension for o in safety_frame.harmful_outcomes],
        },
        strength=1.0,
        reversible=False,
    ))
```

The router needs `safety_frame` passed to `route()` — add it as a parameter.

#### Phase F: Reorder Runtime Pipeline

**File:** `kernel/semantic_kernel_runtime.py` (MODIFY)

Move safety detection from step 3b to after state transmutation compilation:

```python
# 3b. Compile operational meaning (was 3c)
operational_frames = self._operational_meaning_compiler.compile(...)
meaning_arbitration = self._operational_meaning_compiler.arbitrate(...)
selected_frames = [...]

# 3c. Compile state occupancy (NEW)
occupancy_frames = self._state_occupancy_compiler.compile(uol_graph, kernel)

# 3d. Compile state deltas (NEW)
delta_frames = self._state_delta_compiler.compile(uol_graph, selected_frames)

# 3e. Compile state transmutations (EXTENDED)
state_transmutations = self._state_transmutation_compiler.compile(
    uol_graph, selected_frames, delta_frames, occupancy_frames,
)

# 3f. Safety detection from transmutations (MOVED from 3b)
safety_frame = self._safety_detector.detect(
    transmutations=state_transmutations,
    occupancy_frames=occupancy_frames,
    situation=situation_frame,
)

# 3g. Route effects (with safety_frame)
operational_effects = self._operational_causal_router.route(
    selected_frames, state_transmutations, safety_frame=safety_frame, ...
)

# 3h. Build obligation contract (with safety_frame)
obligation_contract = self._obligation_contract_builder.build(
    ..., safety_frame=safety_frame,
)
```

Remove:
- Step 3b safety detection (moved to 3f)
- Step 8 safety override (no longer needed — safety is integrated into the contract)

#### Phase G: Fix `OperationalMeaningCompiler._has_safety()`

**File:** `kernel/operational_meaning_compiler.py` (MODIFY)

`_has_safety()` should no longer re-derive safety from graph atoms. Instead:
1. Remove `_has_safety()` from `_classify_frame()` — safety classification happens after transmutation compilation
2. `_classify_frame()` should not produce `safety_candidate` frame type from graph inspection
3. Instead, after safety detection (step 3f), if a `SafetyFrame` is detected, the corresponding `OperationalMeaningFrame` is *upgraded* to `safety_candidate` type by the runtime, or the `MeaningArbitrationResult` is rebuilt with safety preemption

Alternative (simpler): Keep `_has_safety()` but make it check for `schema_state_delta` atoms with harmful vital directions (current implementation) — this is a *hint* for frame classification, not the authoritative safety detection. The authoritative detection happens at step 3f from transmutations.

#### Phase H: Update `StateTransmutationPolicy` — Safety Quarantine

**File:** `types/state_transmutation.py` (MODIFY)

Add a policy for safety-relevant transmutations:

```python
@dataclass
class SafetyTransmutationPolicy:
    """Policy for safety-relevant state transmutations."""
    requires_authority: bool = True
    requires_confirmation: bool = False
    persistence_policy: str = "quarantine"  # Never persist harmful state changes
    allows_ephemeral: bool = True
    allows_session_state: bool = False
    allows_patch_candidate: bool = False
    allows_durable_candidate: bool = False
    quarantine_on_conflict: bool = True
    must_report_safety: bool = True
```

Safety-relevant transmutations are always quarantined — they are never persisted as state changes. They exist only to trigger safety effects.

#### Phase I: Entity State Registry in ContextKernel

**File:** `types/context_kernel.py` (MODIFY)

Add a lightweight entity state registry:

```python
@dataclass
class EntityStateEntry:
    entity_ref: str  # "entity:user", "entity:self", etc.
    state_family: str
    dimension: str
    current_value: float
    confidence: float
    last_updated_signal_id: str
    last_updated_at: float

@dataclass
class ContextKernel:
    ...
    entity_states: dict[str, EntityStateEntry] = field(default_factory=dict)
    # Key: f"{entity_ref}:{state_family}.{dimension}"
```

Updated by `OutputStateUpdater` after each turn from applied transmutations.

#### Phase J: Update Tests

**File:** `tests/golden/test_golden_schema_kernel.py` (MODIFY)

Update safety test to verify transmutation-based detection:
- Test that `StateTransmutationFrame`s are compiled from `schema_state_delta` atoms
- Test that `SafetyFrameDetector.detect()` consumes transmutations
- Test that safety categories are correctly derived from transmutation properties
- Test that severity accounts for prior state magnitude
- Test that `OperationalCausalRouter` produces typed safety effects

**File:** `tests/test_deep_stress.py` (VERIFY)

All 18 scenarios should continue to pass.

## Affected Files

| File | Change |
|------|--------|
| `kernel/state_occupancy_compiler.py` | NEW — compile StateOccupancyFrames from graph + kernel |
| `kernel/state_delta_compiler.py` | NEW — compile StateDeltaFrames from graph state atoms |
| `kernel/state_transmutation_compiler.py` | MODIFY — accept delta + occupancy frames, compile from schema state deltas |
| `kernel/safety_frame_detector.py` | REWRITE — consume transmutations, not graph atoms or tokens |
| `kernel/operational_causal_router.py` | MODIFY — accept safety_frame, produce typed safety effects |
| `kernel/operational_meaning_compiler.py` | MODIFY — remove _has_safety() from _classify_frame() or make it a hint only |
| `kernel/semantic_kernel_runtime.py` | MODIFY — reorder pipeline, add new compilation steps, remove step 8 override |
| `types/context_kernel.py` | MODIFY — add entity_states registry |
| `types/state_transmutation.py` | MODIFY — add SafetyTransmutationPolicy |
| `kernel/output_state_updater.py` | MODIFY — update entity_states from applied transmutations |
| `tests/golden/test_golden_schema_kernel.py` | MODIFY — update safety tests for transmutation-based detection |
| `docs/compositional_safety_refactor.md` | UPDATE — reflect meaning-based approach |
| `docs/archive/cemm_foundational_fixes.md` | UPDATE — section 8.5 |

## Non-Negotiable Invariants

```
1. Safety is derived from StateTransmutationFrames, not from raw graph atoms or token matching.
2. StateOccupancyFrame and StateDeltaFrame are live types used by the pipeline.
3. Safety detection runs AFTER state transmutation compilation, not before.
4. Safety-relevant transmutations are quarantined — never persisted as state changes.
5. The OperationalCausalRouter produces typed safety effects with full category context.
6. No token-based alias lookup as a fallback — the pipeline is the single source of truth.
7. No duplicate safety detection calls in the runtime.
8. _has_safety() in OperationalMeaningCompiler is a classification hint, not authoritative detection.
9. Entity state registry tracks current state values for magnitude assessment.
10. Safety severity accounts for prior state, not just schema risk level.
```

## Migration Strategy

1. **Phase A-B** (new compilers): Add `StateOccupancyCompiler` and `StateDeltaCompiler` as new modules. No existing code changes — purely additive.
2. **Phase C** (extend transmutation compiler): Add new compilation path for schema state deltas. Existing paths unchanged.
3. **Phase D** (rewrite detector): New `detect()` signature. Old signature removed. All callers updated.
4. **Phase E** (extend router): Add `safety_frame` parameter. Existing effects unchanged.
5. **Phase F** (reorder runtime): Move safety detection call. Remove step 8 override. Add new compilation calls.
6. **Phase G** (fix meaning compiler): Remove or downgrade `_has_safety()`.
7. **Phase H-I** (types): Add new types. Existing types unchanged.
8. **Phase J** (tests): Update tests to verify new pipeline.

Each phase is independently testable. The full test suite should pass after each phase.
