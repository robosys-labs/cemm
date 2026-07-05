# Runtime Single-Authority Takeover Design

Status: approved implementation design  
Supersedes: pages 51-54 of the gap-fix plan (Phase 9 details)  
Scope: Phase 9 (Runtime Unification) + remaining Phase 4/7/8 gaps

## 1. Thesis

`SemanticKernelRuntime.run_turn()` is architecturally complete but never called
from production code. `Pipeline.run()` (741 lines) is the real entrypoint, with
the runtime bolted on at line 679 via `run_semantic_stack()`. This design makes
the runtime the single authority for every turn.

## 2. What Changes

### 2a. SemanticKernelRuntime gains `run_text()` — the single entrypoint

```python
def run_text(self, text: str, context_id: str | None = None) -> RuntimeCycleResult:
    signal = self._create_signal(text, context_id)
    kernel = self._build_kernel(signal, context_id)
    self._restore_session(kernel, context_id)
    result = self.run_turn(signal, kernel)
    self._persist_session(kernel, context_id)
    return result
```

Session lifecycle (restore/persist) moves from Pipeline to Runtime.
- `_restore_session()` hydrates kernel from prior session state (stored in Runtime)
- `_persist_session()` saves conversation state, topic, discourse stack

### 2b. `run_turn()` expands to 11 steps

Current → expanded:

| Step | Before | After |
|------|--------|-------|
| 1 | Perceive | Perceive |
| 2 | Build graph | Build graph |
| 3 | Attend | Attend |
| 3a | Compile program | Compile program |
| 3b | Schedule obligation | Schedule obligation |
| 3c | Process teaching | Process teaching |
| 3d | Compile relations | Compile relations + **induce schemas** |
| 3e | Query → bind → contract | Query → bind → contract |
| 3f | Realize | **Realize (authoritative output)** |
| 3g | — | **Lightweight safety check** |
| 4 | Plan | Plan (compat diagnostics) |
| 5 | Extract patches | Extract patches |
| 6 | Validate | Validate (with **fixed temporal + compression checks**) |
| 6a | Commit | Commit |
| 7 | Consolidate | Consolidate |
| 8 | — | **Output state updater + Error attribution** |

New steps absorbed from old Pipeline/`__main__.py`:

- **3d-i: Schema induction** — calls new `PredicateSchemaInductor` after relation compilation
- **3g: Safety check** — lightweight frame check after realization; can override output with abstention
- **8: Output state updater** — updates conversation state from realized output
- **8a: Error attribution** — evaluates output for quality diagnostics

Removed from the authority path:
- **DecisionRouter** — `ObligationScheduler` determines the path
- **AnswerOperator/AskOperator** — `SemanticRealizer` produces output
- **RememberOperator** — graph patch validation + commit is the write path
- **RealizationPipeline fallback** — removed entirely

Kept as legacy diagnostics only:
- `ConversationActClassifier` — runs for diagnostic output
- `EntityFactExtractor` — runs as pre-patch diagnostic, feeds no claims directly
- `SituationFrameBuilder` — runs for compat

### 2c. Pipeline becomes pure adapter

```python
class Pipeline:
    def run(self, input_text, context_id=None):
        signal = self._make_signal(input_text, context_id)
        kernel = self._build_kernel(signal)
        self._restore_session(kernel, context_id)
        cycle = self._runtime.run_turn(signal, kernel)
        self._persist_session(context_id, kernel)
        return PipelineResult.from_cycle(cycle, kernel, signal)

    def _make_signal(self, text, context_id):
        # Same as current Pipeline.run() lines 194-206

    def _build_kernel(self, signal):
        # Same as current lines 209-268 (builder, session restore, self-view, context inference)

    def _restore_session(self, kernel, context_id):
        # Same as current lines 214-257

    def _persist_session(self, context_id, kernel):
        # Same as current lines 696-718
```

`PipelineResult.from_cycle()` derives all backward-compat fields from `RuntimeCycleResult`.

### 2d. `__main__.py` simplified

```python
def process_input(text, store, registry, ...):
    cycle = runtime.run_text(text, context_id)
    output = cycle.realized_output

    # Second attempt: re-realize from contract if output empty
    if not output and cycle.realization_contract:
        output = runtime.realizer.realize(
            cycle.realization_contract,
            cycle.answer_binding,
        )

    # Background: online learning + induction on cycle data
    if cycle.uol_graph and cycle.patch_candidates:
        online_learner.record_turn(...)
        inductor.induct(...)

    return output or "I'm not sure how to respond."
```

Removed from `__main__.py`:
- `RecursiveLoop.run_once()` call and all its result handling
- Mode controller (absorbed into runtime pre-check)
- Simulation engine (causal inference still in runtime, but simulation is optional)
- DecisionRouter call
- Fallback retrieval
- Operator execution chain
- RealizationPipeline fallback (line 710-720)
- Output state updater (absorbed into runtime step 8)
- Discourse stack push (absorbed into runtime step 8)
- Error attribution (absorbed into runtime step 8a)

Kept in `__main__.py`:
- Online learning (background post-processing)
- Induction (background post-processing)
- Signal creation for actionable signals

### 2e. PredicateSchemaInductor (Phase 4 gap)

New file: `cemm/learning/predicate_schema_inductor.py`

```python
class PredicateSchemaInductor:
    def induct_from_frames(
        self, frames: list[RelationFrame], store: PredicateSchemaStore
    ) -> list[str]:
        """Scan relation frames for unknown predicate keys, infer schemas."""
```

For each relation frame:
1. Extract `relation_key` from frame
2. If store doesn't have it → call `store.observe_candidate()`
3. Infer `argument_roles` from subject/object/qualifier roles seen in frames
4. Infer `relation_family` from the most common family among frames with this key
5. Track support count across frames; promote when threshold reached

Called in `run_turn()` after relation frame compilation (step 3d).

### 2f. PatchValidator fixes (Phase 8 stubs)

1. **`_check_temporal()`** (line 280-282): Implement real check
   - Compare patch evidence timestamps against kernel's validity window
   - If `kernel.time.now - evidence_time > temporal_threshold`, flag as stale
   - Threshold configurable via constructor (default: 86400s = 24h)

2. **Compression gain check**: New check #13
   - If patch operations duplicate existing durable relations (same key/subject/object), score low on novelty
   - If patch adds relations that compress previously fragmented knowledge, score high
   - Simple heuristic: count how many operations are novel vs redundant

3. **Source trust**: Use `kernel.permission.source_trust` instead of `patch.confidence` as proxy

### 2g. post-turn hooks

Runtime exposes hooks for background processing after `run_turn()`:
- `on_turn_complete(cycle)` — called by `run_text()` after realization
- Online learner records cycle data
- Inductor runs on relation frames
- Session is persisted

## 3. Acceptance

After implementation:

1. Every user turn produces exactly one `RuntimeCycleResult`
2. `cycle.realized_output` is the authoritative response text
3. No code path produces output that doesn't trace back to `RealizationContract`
4. `Pipeline.run()` is a thin adapter (≤ 50 lines of delegating logic)
5. `__main__.py` calls `runtime.run_text()` directly, not `Pipeline.run()`
6. `RealizationPipeline` is removed from production code
7. `PredicateSchemaInductor` auto-discovers schemas from observed relation frames
8. `_check_temporal()` returns real results (not `True, ""`)
9. All existing v4.2 tests still pass; old Pipeline tests either pass or are replaced
10. No test checks `PipelineResult` fields that don't derive from `RuntimeCycleResult`

## 4. Non-Goals

- Do not rewrite all 16 old Pipeline stages. Adapter wraps runtime; old stages run as needed.
- Do not remove online learning or induction — they become background hooks.
- Do not change the UOL graph, atom kinds, or edge types.
- Do not add new primitive concepts or domain-specific code.
- Do not change the teaching frame, relation frame, or query engine internals.
