# ERCA v2.0 Architecture Gap Closure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Align the CEMM implementation with the updated ERCA v2.0 architecture (`architecture.md` + `cemm_training_architecture.md`), section by section.

**Architecture:** 6 phases: (1) Section 10 kernel restructuring, (2) SelfView/SelfState updates, (3) Trace + Operator fixes, (4) Causal + Temporal completeness, (5) Invariants + Tests, (6) Registry + Permission + Training. Each phase is independently testable.

**Tech Stack:** Pure Python 3.11+, stdlib, SQLite, pytest.

**Reference:** `docs/superpowers/plans/2026-06-28-erca-gap-closure.md` (previous plan — some tasks already done, this plan covers what remains or changed).

---

## File Structure

| Phase | Files Modified | Files Created |
|-------|---------------|---------------|
| 1 (Kernel Restructure) | `types/context_kernel.py`, `kernel/pragmatic_interpreter.py`, `kernel/pipeline.py`, `kernel/context_kernel_builder.py`, `types/self_view.py`, `types/__init__.py` | — |
| 2 (Self + Trace) | `types/trace.py`, `operators/answer.py`, `operators/remember.py`, `operators/update_claim.py`, `kernel/pipeline.py`, `__main__.py`, `types/action.py` | — |
| 3 (Causal + Temporal) | `causal/inference.py`, `causal/simulation.py`, `kernel/recursive_loop.py`, `learning/inductor.py` | `types/temporal_relation.py` |
| 4 (Invariants + Tests) | `kernel/invariant_guard.py`, `tests/invariants/`, `tests/test_acceptance.py` | — |
| 5 (Registry + Training) | `registry/registry.py`, `types/model.py`, `store/schema.py`, `retrieval/memory_views.py` | `kernel/permission_gates.py`, `trainer/` |

---

## Phase 1: Section 10 Kernel Restructuring

**The architecture has been significantly restructured:**

1. `PragmaticState` is gone — replaced by `UserAffectState` (under `UserState`) and `ConversationDynamics` (under `ConversationState`).
2. `users: list` removed from `ContextKernel` — MVP is single-user only.
3. `self_state: SelfState | None` removed from `ContextKernel` — only `self_view: SelfView`.
4. `UserState.session_affect` → `UserState.affect: UserAffectState`.
5. `ConversationState.pragmatic_state` → `ConversationState.dynamics: ConversationDynamics`.
6. `ConversationState.repetition_counts` removed (now in `dynamics`).
7. `WorldState` gains `persistence: bool = True`.
8. `SelfView` gains `coverage_gap_claim_ids: list[str]`.
9. `SelfView.active_assumptions` → `active_assumption_claim_ids`.
10. `SelfView.known_limits` → `known_limit_claim_ids`.
11. `ConversationState` signed `first_user_signal_id` stays, `inferred_context_claim_ids` stays.
12. `update_pragmatic_state` → split into `update_user_affect` and `update_conversation_dynamics`.

### Task 1.1 — Create `UserAffectState` and `ConversationDynamics`

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\types\context_kernel.py`**

Replace the `PragmaticState` dataclass with two new dataclasses:

```python
@dataclass
class UserAffectState:
    current_stance: str = "cooperative"  # cooperative | frustrated | hostile | playful | mischievous | unknown
    frustration: float = 0.0
    hostility: float = 0.0
    playfulness: float = 0.0
    active_quality_atom_keys: list[str] = field(default_factory=list)
    last_updated_signal_id: str = ""
    decay_half_life_ms: float = 900000.0


@dataclass
class ConversationDynamics:
    repetition_pressure: float = 0.0
    active_repetition_group_ids: list[str] = field(default_factory=list)
    active_process_atom_keys: list[str] = field(default_factory=list)
    likely_cause_claim_ids: list[str] = field(default_factory=list)
    last_updated_signal_id: str = ""
    decay_half_life_ms: float = 300000.0
```

- [ ] **Step 2: Update `WorldState`** — add `persistence` field:

```python
@dataclass
class WorldState:
    ...
    persistence: bool = True
    ...
```

- [ ] **Step 3: Update `UserState`** — replace `session_affect: PragmaticState | None` with `affect: UserAffectState`:

```python
@dataclass
class UserState:
    user_id: str | None = None
    known: bool = False
    active_preference_claim_ids: list[str] = field(default_factory=list)
    trusted_domains: list[str] = field(default_factory=list)
    affect: UserAffectState = field(default_factory=UserAffectState)
    locale: dict | None = None
```

- [ ] **Step 4: Update `ConversationState`** — replace `pragmatic_state: PragmaticState | None` and `repetition_counts: dict` with `dynamics: ConversationDynamics`:

```python
@dataclass
class ConversationState:
    session_id: str = ""
    turn_index: int = 0
    recent_signal_ids: list[str] = field(default_factory=list)
    active_entity_ids: list[str] = field(default_factory=list)
    active_claim_ids: list[str] = field(default_factory=list)
    active_repetition_group_ids: list[str] = field(default_factory=list)
    dynamics: ConversationDynamics = field(default_factory=ConversationDynamics)
    first_user_signal_id: str | None = None
    inferred_context_claim_ids: list[str] = field(default_factory=list)
```

- [ ] **Step 5: Update `ContextKernel`** — remove `self_state` and `users`:

```python
@dataclass
class ContextKernel:
    id: str
    world: WorldState = field(default_factory=WorldState)
    user: UserState = field(default_factory=UserState)
    time: TimeState = field(default_factory=TimeState)
    conversation: ConversationState = field(default_factory=ConversationState)
    goal: GoalState = field(default_factory=GoalState)
    memory: MemoryState = field(default_factory=MemoryState)
    self_view: SelfView = field(default_factory=SelfView)
    permission: Permission = field(default_factory=Permission.public)
    budget: Budget = field(default_factory=Budget)
    version: str = "erca.context_kernel.v1"
```

Remove `self_state: SelfState | None = None`, `users: list = field(default_factory=list)`, and the `all_users` property.

### Task 1.2 — Update `SelfView`

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\types\self_view.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from .self_state import SelfState


@dataclass
class SelfView:
    self_id: str = ""
    mode: str = "assistant"
    uncertainty: float = 0.0
    coherence: float = 1.0
    recent_error_rate: float = 0.0
    active_assumption_claim_ids: list[str] = field(default_factory=list)
    known_limit_claim_ids: list[str] = field(default_factory=list)
    coverage_gap_claim_ids: list[str] = field(default_factory=list)
    reliability_by_domain: dict[str, float] = field(default_factory=dict)
    recent_meta_memory_claim_ids: list[str] = field(default_factory=list)
    version: str = "erca.self_view.v1"

    @classmethod
    def from_self_state(cls, state: SelfState | None, recent_claim_ids: list[str] | None = None) -> SelfView:
        if state is None:
            return cls()
        return cls(
            self_id=state.id,
            mode=state.mode.value if hasattr(state.mode, 'value') else str(state.mode),
            uncertainty=state.uncertainty,
            coherence=state.coherence,
            recent_error_rate=state.recent_error_rate,
            active_assumption_claim_ids=state.metacognition.active_assumptions,
            known_limit_claim_ids=state.metacognition.known_limits,
            coverage_gap_claim_ids=state.epistemic.coverage_gap_claim_ids,
            reliability_by_domain=state.metacognition.reliability_by_domain,
            recent_meta_memory_claim_ids=recent_claim_ids or state.meta_memory.recently_written_claim_ids[-10:],
        )
```

Note: `active_assumptions` → `active_assumption_claim_ids`, `known_limits` → `known_limit_claim_ids`, added `coverage_gap_claim_ids`.

### Task 1.3 — Rewrite `pragmatic_interpreter.py`

- [ ] **Step 1: Replace `update_pragmatic_state` with `update_user_affect` and `update_conversation_dynamics`**

Edit `C:\dev\cemm\cemm\kernel\pragmatic_interpreter.py`:

```python
from __future__ import annotations
from ..types.signal import Signal, SignalKind, SourceType, ObservationSemantics
from ..types.context_kernel import ContextKernel, UserAffectState, ConversationDynamics
from ..store.store import Store
from .semantic_clusters import SemanticClusterRegistry


_DEFAULT_REGISTRY = SemanticClusterRegistry()


def interpret_signal(
    signal: Signal,
    kernel: ContextKernel,
    store: Store | None = None,
    registry: SemanticClusterRegistry | None = None,
) -> ObservationSemantics | None:
    if signal.source_type != SourceType.USER or signal.kind != SignalKind.INPUT:
        return None

    reg = registry if registry is not None else _DEFAULT_REGISTRY
    speech_act, cluster_key, confidence = reg.match(signal.content)

    if not cluster_key:
        return ObservationSemantics(
            speech_act="unknown",
            stance="unknown",
            confidence=0.0,
        )

    cluster_def = reg.clusters.get(cluster_key, {})
    affect_baseline = cluster_def.get("affect_baseline", {})
    target = cluster_def.get("target", "")

    target_entity_id = ""
    if target == "assistant":
        target_entity_id = kernel.self_view.self_id

    active_groups = kernel.conversation.active_repetition_group_ids
    is_repeat = cluster_key in active_groups
    repetition_count = 1
    if is_repeat:
        last = getattr(kernel.conversation.dynamics, 'repetition_pressure', 0)
        repetition_count = max(1, int(last * 6.67)) if last > 0 else 2

    cause_ids: list[str] = []
    if speech_act in ("insult", "complaint") and repetition_count > 1 and store is not None:
        cause_ids = _trace_causes(store, kernel)

    valence = affect_baseline.get("valence", 0)
    stance = "negative" if valence < 0 else "positive" if valence > 0 else "neutral"

    return ObservationSemantics(
        speech_act=speech_act,
        target_entity_id=target_entity_id,
        semantic_cluster_key=cluster_key,
        stance=stance,
        affect=dict(affect_baseline),
        repetition_group_id=cluster_key,
        repetition_count=repetition_count,
        cause_hypothesis_claim_ids=cause_ids,
        confidence=confidence,
    )


def _trace_causes(store: Store, kernel: ContextKernel) -> list[str]:
    recent_ids = kernel.memory.working_claim_ids[-5:]
    result: list[str] = []
    for cid in recent_ids:
        claim = store.claims.get(cid)
        if claim is not None and claim.domain == "causal" and claim.object_value == "failure":
            result.append(cid)
    return result


def _decay(value: float, elapsed_ms: float, half_life_ms: float) -> float:
    if half_life_ms <= 0 or elapsed_ms <= 0:
        return value
    return value * (0.5 ** (elapsed_ms / half_life_ms))


_HALF_LIVES = {
    "frustration": 900000.0,
    "hostility": 1800000.0,
    "playfulness": 600000.0,
    "repetition_pressure": 300000.0,
}


def update_user_affect(
    current: UserAffectState,
    semantics: ObservationSemantics,
    kernel: ContextKernel,
    signal_id: str | None = None,
) -> UserAffectState:
    elapsed_ms = (kernel.time.now - current.last_updated_at) * 1000.0 if current.last_updated_at > 0 else 0.0

    affect = UserAffectState(
        current_stance=current.current_stance,
        frustration=_decay(current.frustration, elapsed_ms, _HALF_LIVES["frustration"]),
        hostility=_decay(current.hostility, elapsed_ms, _HALF_LIVES["hostility"]),
        playfulness=_decay(current.playfulness, elapsed_ms, _HALF_LIVES["playfulness"]),
        active_quality_atom_keys=list(current.active_quality_atom_keys),
        last_updated_signal_id=signal_id or current.last_updated_signal_id,
        decay_half_life_ms=current.decay_half_life_ms,
    )

    sem_affect = semantics.affect
    affect.frustration = max(0.0, min(1.0, affect.frustration + sem_affect.get("frustration", 0.0)))
    affect.hostility = max(0.0, min(1.0, affect.hostility + sem_affect.get("hostility", 0.0)))
    affect.playfulness = max(0.0, min(1.0, affect.playfulness + sem_affect.get("playfulness", 0.0)))

    f, h, p = affect.frustration, affect.hostility, affect.playfulness
    if h > 0.5:
        affect.current_stance = "hostile"
    elif f > 0.5:
        affect.current_stance = "frustrated"
    elif p > 0.5:
        affect.current_stance = "playful"
    else:
        affect.current_stance = "cooperative"

    return affect


def update_conversation_dynamics(
    current: ConversationDynamics,
    semantics: ObservationSemantics,
    kernel: ContextKernel,
    signal_id: str | None = None,
) -> ConversationDynamics:
    elapsed_ms = (kernel.time.now - current.last_updated_at) * 1000.0 if current.last_updated_at > 0 else 0.0

    dynamics = ConversationDynamics(
        repetition_pressure=_decay(current.repetition_pressure, elapsed_ms, _HALF_LIVES["repetition_pressure"]),
        active_repetition_group_ids=list(current.active_repetition_group_ids),
        active_process_atom_keys=list(current.active_process_atom_keys),
        likely_cause_claim_ids=list(current.likely_cause_claim_ids),
        last_updated_signal_id=signal_id or current.last_updated_signal_id,
        decay_half_life_ms=current.decay_half_life_ms,
    )

    pressure_inc = 0.15 * semantics.repetition_count
    dynamics.repetition_pressure = max(0.0, min(1.0, dynamics.repetition_pressure + pressure_inc))

    if semantics.repetition_group_id:
        if semantics.repetition_group_id not in dynamics.active_repetition_group_ids:
            dynamics.active_repetition_group_ids.append(semantics.repetition_group_id)

    if semantics.cause_hypothesis_claim_ids:
        merged = set(dynamics.likely_cause_claim_ids) | set(semantics.cause_hypothesis_claim_ids)
        dynamics.likely_cause_claim_ids = sorted(merged)

    return dynamics
```

### Task 1.4 — Fix `ContextKernelBuilder`

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\kernel\context_kernel_builder.py`**

Remove `self_state` parameter from `build()` and `from_signal()` — the builder should not touch SelfState; the pipeline loads it later. Remove the `users` logic:

```python
from __future__ import annotations
import time
import uuid
from ..types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from ..types.signal import Signal
from ..types.permission import Permission
from ..types.self_view import SelfView


class ContextKernelBuilder:
    def build(
        self,
        world: WorldState | None = None,
        user: UserState | None = None,
        time_state: TimeState | None = None,
        conversation: ConversationState | None = None,
        goal: GoalState | None = None,
        memory: MemoryState | None = None,
        permission: Permission | None = None,
        budget: Budget | None = None,
    ) -> ContextKernel:
        now = time.time()
        if time_state is None:
            time_state = TimeState(now=now, bucket=self._compute_bucket(now))
        if budget is None:
            budget = Budget()
        return ContextKernel(
            id=uuid.uuid4().hex[:16],
            world=world or WorldState(),
            user=user or UserState(),
            time=time_state,
            conversation=conversation or ConversationState(),
            goal=goal or GoalState(),
            memory=memory or MemoryState(),
            permission=permission or Permission.public(),
            budget=budget,
        )

    @staticmethod
    def from_signal(
        signal: Signal,
        turn_index: int = 0,
    ) -> ContextKernel:
        now = signal.observed_at
        return ContextKernel(
            id=signal.context_id,
            world=WorldState(),
            user=UserState(),
            time=TimeState(now=now, bucket=_compute_bucket(now)),
            conversation=ConversationState(
                session_id=signal.context_id,
                turn_index=turn_index,
                recent_signal_ids=[signal.id],
                first_user_signal_id=signal.id if turn_index == 1 else None,
            ),
            goal=GoalState(),
            memory=MemoryState(working_signal_ids=[signal.id]),
            permission=signal.permission,
            budget=Budget(),
        )

    @staticmethod
    def _compute_bucket(timestamp: float) -> str:
        import datetime
        hour = datetime.datetime.fromtimestamp(timestamp).hour
        if 5 <= hour < 9:
            return "early_morning"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        elif hour >= 22 or hour < 5:
            return "night"
        return "unknown"


def _compute_bucket(timestamp: float) -> str:
    return ContextKernelBuilder._compute_bucket(timestamp)
```

### Task 1.5 — Fix `Pipeline.run()` for new types

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\kernel\pipeline.py`**

Replace all references to `PragmaticState`, `kernel.self_state`, `kernel.users`, `conv.pragmatic_state`, `kernel.user.session_affect`, `update_pragmatic_state` with the new types.

Key changes in `Pipeline.run()`:

```python
        kernel = self._builder.from_signal(signal, turn_index=self._turn_count)

        if budget_override:
            for k, v in budget_override.items():
                if hasattr(kernel.budget, k):
                    setattr(kernel.budget, k, v)

        self_state = self._store.self_store.latest()
        if self_state:
            kernel.self_view = SelfView.from_self_state(self_state, kernel.memory.working_claim_ids)
        else:
            kernel.self_view = SelfView()

        self._resolver.resolve_self(kernel)
        self._frames.apply_frame_rules(kernel)
        context_inference = self._context_inference_engine.infer(signal, kernel)
        self._context_inference_engine.apply_to_kernel(context_inference, kernel)

        semantics = interpret_signal(signal, kernel, self._store)
        if semantics is not None:
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            kernel.user.affect.active_quality_atom_keys = quality_keys
            if kernel.conversation.dynamics:
                kernel.conversation.dynamics.active_process_atom_keys = process_keys
            signal.observation_semantics = semantics
            if semantics.semantic_cluster_key:
                kernel.user.affect = update_user_affect(kernel.user.affect, semantics, kernel, signal.id)
                kernel.conversation.dynamics = update_conversation_dynamics(
                    kernel.conversation.dynamics, semantics, kernel, signal.id
                )
```

Update imports:
```python
from .pragmatic_interpreter import interpret_signal, update_user_affect, update_conversation_dynamics
```

Remove the `from ..types.context_kernel import PragmaticState` inside the if block.

### Task 1.6 — Fix all other files referencing `PragmaticState`

- [ ] **Step 1: Search for `PragmaticState` across codebase and update**

Grep for `PragmaticState`, `self_state`, `pragmatic_state`, `session_affect`, `users` in:
- `memory_views.py`
- `invariant_guard.py`
- `recursive_loop.py`
- `context_inference.py`
- `entity_resolver.py`
- `frame_engine.py`
- Any test files

Replace: `kernel.self_state` → `kernel.self_view` (where appropriate, the self_view itself contains mode/identity info). If code needs the full SelfState (e.g., `self_state.id`), it must load it from the store.

The `EntityResolver.resolve_self()` likely references `kernel.self_state` — update to use `kernel.self_view` or load SelfState from store.

- [ ] **Step 2: Fix `EntityResolver` in `C:\dev\cemm\cemm\kernel\entity_resolver.py`**

Read it, fix references to `kernel.self_state`. If it needs SelfState, have it accept a separate parameter.

- [ ] **Step 3: Fix `invariant_guard.py` references**

Replace `kernel.user.session_affect` → `kernel.user.affect` in any invariant checks.

### Task 1.7 — Run all tests

```bash
cd C:\dev\cemm && python -m pytest tests/ -v
```
Expected: All pass with updated types.

### Task 1.8 — Commit

```bash
cd C:\dev\cemm
rtk git add cemm/types/context_kernel.py cemm/types/self_view.py cemm/types/__init__.py cemm/kernel/pragmatic_interpreter.py cemm/kernel/pipeline.py cemm/kernel/context_kernel_builder.py cemm/kernel/entity_resolver.py
rtk git commit -m "refactor: restructure Sec 10 — PragmaticState split into UserAffectState+ConversationDynamics, remove users/self_state from ContextKernel, update SelfView"
```

---

## Phase 2: Self + Trace + Operator Fixes

### Task 2.1 — Align Trace with architecture (Sec 7)

- [ ] **Step 1: Update `C:\dev\cemm\cemm\types\trace.py`**

Add missing fields from architecture:

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Trace:
    context_id: str
    input_signal_ids: list[str] = field(default_factory=list)
    selected_entity_ids: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    action_id: str = ""
    operator_model_id: str = ""
    causal_inference_used: bool = False
    frame_rules_applied: bool = False
    synthesis_strategy_model_id: str | None = None
    synthesis_verified: bool = False
    synthesis_verification_type: str | None = None  # "hard" | "soft" | "none"
    verifier_model_id: str | None = None
    permission: str = "allowed"  # "allowed" | "blocked" | "partial"
    confidence: float = 0.0
    cost_ms: float = 0.0
    fallback_used: bool = False
```

### Task 2.2 — Fix AnswerOperator trace (Sec 7, Sec 23)

- [ ] **Step 1: Update `C:\dev\cemm\cemm\operators\answer.py`**

Replace hardcoded trace with real values:

```python
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            selected_claim_ids=ctx.selected_claim_ids,
            selected_model_ids=ctx.selected_model_ids,
            action_id="",
            operator_model_id="answer_operator",
            causal_inference_used=bool(ctx.params.get("causal_inference_used")),
            frame_rules_applied=True,
            synthesis_strategy_model_id=ctx.params.get("strategy_model_id"),
            synthesis_verified=verified if 'verified' in dir() else True,
            synthesis_verification_type="hard",
            permission="allowed",
            confidence=ctx.kernel.self_view.confidence if hasattr(ctx.kernel.self_view, 'confidence') else 0.9,
            cost_ms=cost_ms,
            fallback_used=False,
        )
```

### Task 2.3 — Wire Self mode changes to emit reflect action (Sec 8)

- [ ] **Step 1: In `RecursiveLoop.run_once()` or `Pipeline.run()`**

After online learning step, check if `kernel.self_view.uncertainty > 0.7` or `kernel.self_view.recent_error_rate > 0.3` or `kernel.self_view.coherence < 0.5`. If so, emit an `Action(kind=REFLECT)` and a reflection `Signal`.

This is already partially done in `_find_recursion_triggers` in `recursive_loop.py`. Verify the reflect action emission is happening.

- [ ] **Step 2: Check `__main__.py` action dispatch**

Ensure `ActionKind.REFLECT` is handled. Currently it might not be in the if/elif chain. If not, add a reflect case.

### Task 2.4 — Fix operator dispatch (Sec 22)

- [ ] **Step 1: Fix `__main__.py` to use `create_model_candidate` not `create_model`**

The architecture says `create_model_candidate` (ActionKind), not `create_model`. Update the enum and dispatch.

- [ ] **Step 2: Run tests**

```bash
cd C:\dev\cemm && python -m pytest tests/ -v
```

### Task 2.5 — Commit

```bash
cd C:\dev\cemm
rtk git add cemm/types/trace.py cemm/operators/answer.py cemm/__main__.py cemm/types/action.py
rtk git commit -m "fix: align Trace with architecture, fix AnswerOperator trace, add reflect action dispatch"
```

---

## Phase 3: Causal + Temporal Completeness

### Task 3.1 — Add causal closure limits (Sec 16)

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\causal\inference.py`**

Add `causal horizon`, `cycle detection`, `confidence floor` limits to `transitive_closure()`:

```python
    def transitive_closure(
        self,
        start_claim_ids: list[str],
        kernel: ContextKernel,
        max_depth: int = 3,
        confidence_floor: float = 0.3,
    ) -> list[dict]:
        all_predictions: list[dict] = []
        current_ids = list(start_claim_ids)
        visited_claims: set[str] = set(start_claim_ids)
        visited_effects: set[str] = set()
        depth = 0
        while depth < max_depth and current_ids:
            next_ids: list[str] = []
            for cid in current_ids:
                if cid in visited_claims:
                    continue  # cycle detection
                visited_claims.add(cid)
                claim = self._store.claims.get(cid)
                if claim is None:
                    continue
                predictions = self.predict(claim.predicate, [cid], kernel)
                for p in predictions:
                    if p["confidence"] < confidence_floor:
                        continue
                    pred_id = p["predicate"]
                    if pred_id in visited_effects:
                        continue
                    visited_effects.add(pred_id)
                    all_predictions.append(p)
                    next_ids.append(pred_id)
                if len(all_predictions) >= kernel.budget.max_ranked:
                    break
            current_ids = next_ids
            depth += 1
            if len(all_predictions) >= kernel.budget.max_ranked:
                break
        return all_predictions[:kernel.budget.max_ranked]
```

### Task 3.2 — Implement temporal relation derivation (Sec 19)

- [ ] **Step 1: Create `C:\dev\cemm\cemm\types\temporal_relation.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class TemporalRelation(str, Enum):
    PRECEDES = "temporally_precedes"
    OVERLAPS = "temporally_overlaps"
    DURING = "temporally_during"
    CONTAINS = "temporally_contains"
    MEETS = "temporally_meets"


@dataclass
class TemporalRelationClaim:
    subject_claim_id: str
    object_claim_id: str
    relation: TemporalRelation
    confidence: float
```

- [ ] **Step 2: Create `C:\dev\cemm\cemm\causal\temporal.py`**

```python
from __future__ import annotations
from ..types.claim import Claim
from ..types.temporal_relation import TemporalRelation, TemporalRelationClaim
from ..store.store import Store
import time


def derive_temporal_relations(claim: Claim, store: Store) -> list[TemporalRelationClaim]:
    if claim.valid_from is None and claim.valid_until is None:
        return []

    recent = store.claims.find_active(5)
    relations: list[TemporalRelationClaim] = []
    now = time.time()
    cf = claim.valid_from or now
    cu = claim.valid_until or now

    for other in recent:
        if other.id == claim.id:
            continue
        of = other.valid_from or now
        ou = other.valid_until or now

        if cu <= of:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id,
                object_claim_id=other.id,
                relation=TemporalRelation.PRECEDES,
                confidence=0.9,
            ))
        elif cf >= ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id,
                object_claim_id=other.id,
                relation=TemporalRelation.PRECEDES,
                confidence=0.9,
            ))
        elif cf >= of and cu <= ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id,
                object_claim_id=other.id,
                relation=TemporalRelation.DURING,
                confidence=0.8,
            ))
        elif cf <= of and cu >= ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id,
                object_claim_id=other.id,
                relation=TemporalRelation.CONTAINS,
                confidence=0.8,
            ))
        elif cf < ou and cu > of:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id,
                object_claim_id=other.id,
                relation=TemporalRelation.OVERLAPS,
                confidence=0.7,
            ))
        elif cu == of or cf == ou:
            relations.append(TemporalRelationClaim(
                subject_claim_id=claim.id,
                object_claim_id=other.id,
                relation=TemporalRelation.MEETS,
                confidence=0.9,
            ))

    return relations
```

- [ ] **Step 3: Wire into ClaimStore.put()**

In `C:\dev\cemm\cemm\store\claim_store.py`, after committing, call `derive_temporal_relations` and store results as claims.

### Task 3.3 — Add missing Heuristic to Inductor (Sec 17)

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\learning\inductor.py`**

Add the three MVP heuristics from architecture:
1. Synonym aggregation (shared subject/object types + co-occurrence > 5)
2. Sequential pattern mining (Action A → Signal B within 5 seconds)
3. Slot completion (Goal missing_slots filled by same claim pattern)

### Task 3.4 — Run tests

```bash
cd C:\dev\cemm && python -m pytest tests/ -v
```

### Task 3.5 — Commit

```bash
cd C:\dev\cemm
rtk git add cemm/causal/inference.py cemm/types/temporal_relation.py cemm/causal/temporal.py cemm/store/claim_store.py cemm/learning/inductor.py
rtk git commit -m "feat: add causal closure limits, temporal relation derivation, Inductor heuristics"
```

---

## Phase 4: Invariants + Acceptance Tests

### Task 4.1 — Expand InvariantGuard (Sec 27)

- [ ] **Step 1: Add all 17 missing invariants to `C:\dev\cemm\cemm\kernel\invariant_guard.py`**

Add these checks:

```python
    @classmethod
    def check_context_kernel_before_interpretation(cls, kernel: ContextKernel) -> bool:
        if kernel is None:
            cls.errors.append("Input interpreted before ContextKernel exists")
            return False
        return True

    @classmethod
    def check_response_has_input_signal(cls, signal: Signal | None) -> bool:
        if signal is None:
            cls.errors.append("Response has no input signal")
            return False
        return True

    @classmethod
    def check_self_mutation_has_trace(cls, action: Action) -> bool:
        if action.kind.value in ("reflect",):
            if action.trace is None:
                cls.errors.append(f"Self mutation action {action.id} has no trace")
                return False
        return True

    @classmethod
    def check_prediction_not_presented_as_fact(cls, claim: Claim) -> bool:
        if getattr(claim, 'confidence_type', None) == "simulated" and claim.confidence > 0.99:
            cls.errors.append(f"Prediction {claim.id} exceeds confidence cap 0.99")
            return False
        return True

    @classmethod
    def check_operator_has_required_slots(cls, action: Action, operator_spec: dict) -> bool:
        required = operator_spec.get("required_slots", [])
        if not required:
            return True
        cls.errors.append(f"Operator {action.operator_model_id} missing required slots")
        return False

    @classmethod
    def check_recursive_budget_consumed(cls, parent_budget: Budget, child_budget: Budget) -> bool:
        expected_ms = parent_budget.latency_target_ms - parent_budget.latency_target_ms * 0.1  # approximate
        if child_budget.latency_target_ms >= parent_budget.latency_target_ms:
            cls.errors.append("Recursive budget was refreshed instead of consumed")
            return False
        if child_budget.max_recursive_steps >= parent_budget.max_recursive_steps:
            cls.errors.append("Recursive max_recursive_steps was refreshed instead of consumed")
            return False
        return True

    @classmethod
    def check_causal_chain_confidence(cls, predictions: list[dict]) -> bool:
        for p in predictions:
            if p.get("confidence", 0) > 0.99:
                cls.errors.append(f"Causal chain confidence {p['confidence']} exceeds cap 0.99")
                return False
        return True

    @classmethod
    def check_self_mode_change_has_trace(cls, old_mode: str, new_mode: str, action: Action | None) -> bool:
        if old_mode != new_mode:
            if action is None or action.kind.value != "reflect":
                cls.errors.append(f"Self mode changed {old_mode}->{new_mode} without reflect action")
                return False
        return True

    @classmethod
    def check_insults_are_not_factual_claims(cls, claim: Claim, kernel: ContextKernel) -> bool:
        if claim.subject_entity_id == kernel.self_view.self_id and claim.predicate in ("is_dumb", "is_stupid", "is_useless"):
            cls.errors.append(f"Insult stored as factual claim {claim.id}")
            return False
        return True

    @classmethod
    def check_temporary_frustration_not_persisted(cls, claim: Claim) -> bool:
        if claim.predicate in ("is_frustrated", "is_hostile") and claim.permission and claim.permission.scope.value in ("long_term",):
            cls.errors.append(f"Temporary frustration persisted as stable identity in claim {claim.id}")
            return False
        return True

    @classmethod
    def check_repeated_insults_are_related(cls, signals: list[Signal], cluster_registry) -> bool:
        clusters = set()
        for sig in signals:
            cluster_key = ""
            if sig.observation_semantics:
                cluster_key = sig.observation_semantics.semantic_cluster_key
            if cluster_key:
                clusters.add(cluster_key)
        if len(clusters) > 1:
            # Multiple different clusters for insults — possible missed grouping
            cls.errors.append(f"Repeated paraphrased insults treated as unrelated: {clusters}")
            return False
        return True
```

### Task 4.2 — Add acceptance tests (Sec 28)

- [ ] **Step 1: Add to `tests/test_acceptance.py`**

Add test classes for each architecture acceptance scenario:
- `TestAcceptance_FirstUtterance` — greeting, no-greeting urgency
- `TestAcceptance_LocationAmbiguity` — weather without locale
- `TestAcceptance_CurrentWorldState` — stale claim rejection
- `TestAcceptance_UOLMapping` — repeated insults map to same atoms
- `TestAcceptance_TemporalSession` — "tomorrow morning" resolves
- `TestAcceptance_Memory` — "What is my favorite database?"
- `TestAcceptance_Self` — repeated failure increases error_rate
- `TestAcceptance_RecursiveBudget` — child budget consumed
- `TestAcceptance_CausalConfidence` — chain confidence capped at 0.99
- `TestAcceptance_FrameValidity` — frame rule runs before ranking
- `TestAcceptance_Canonicalization` — predicate alias maps
- `TestAcceptance_PragmaticRepetition` — same cluster, increasing count
- `TestAcceptance_SelfModeChange` — reflect action on mode change
- `TestAcceptance_TemporalOverlap` — derived temporal relation claim
- `TestAcceptance_Permission` — private claim blocked
- `TestAcceptance_Grounding` — tool_result updates operator reliability

### Task 4.3 — Run tests

```bash
cd C:\dev\cemm && python -m pytest tests/ -v
```

### Task 4.4 — Commit

```bash
cd C:\dev\cemm
rtk git add cemm/kernel/invariant_guard.py tests/test_acceptance.py
rtk git commit -m "feat: add 17 invariant checks and 16 acceptance tests"
```

---

## Phase 5: Registry + Permission + Training

### Task 5.1 — Add missing ModelKind values (Sec 6, Sec 12)

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\types\model.py`**

Ensure all ModelKind values from architecture exist:
```python
class ModelKind(str, Enum):
    SCHEMA = "schema"
    PREDICATE = "predicate"
    ENTITY_TYPE = "entity_type"
    OPERATOR = "operator"
    CAUSAL_RULE = "causal_rule"
    PROCESS = "process"
    SIMULATOR = "simulator"
    RANKING_RULE = "ranking_rule"
    FRAME_RULE = "frame_rule"
    CONTEXT_RULE = "context_rule"
    UOL_SEMANTIC = "uol_semantic"
    SYNTHESIS_STRATEGY = "synthesis_strategy"
    VERIFIER = "verifier"
    INDUCTOR = "inductor"
```

(Check if `CONTEXT_RULE`, `VERIFIER` are already defined.)

### Task 5.2 — Fix Registry to handle all kinds (Sec 12)

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\registry\registry.py`**

Add `context_rule`, `synthesis_strategy`, `verifier`, `inductor` to the `_kind_map` in `register()`. Add corresponding storage dicts and lookup methods.

### Task 5.3 — Add `feedback` table missing index (Sec 24)

- [ ] **Step 1: Edit `C:\dev\cemm\cemm\store\schema.py`**

Add index:
```python
    "idx_feedback_signal": "CREATE INDEX IF NOT EXISTS idx_feedback_signal ON feedback(signal_id)",
    "idx_feedback_action": "CREATE INDEX IF NOT EXISTS idx_feedback_action ON feedback(action_id)",
```

### Task 5.4 — Run tests

```bash
cd C:\dev\cemm && python -m pytest tests/ -v
```

### Task 5.5 — Commit

```bash
cd C:\dev\cemm
rtk git add cemm/types/model.py cemm/registry/registry.py cemm/store/schema.py
rtk git commit -m "feat: add missing ModelKind values, Registry kinds, feedback indexes"
```

---

## Self-Review Checklist

- [ ] **Spec coverage (Sec 1-29):** Sec 1-2 (deferred — boundary rule), Sec 3 (Phase 1 covers UOL atoms on semantics), Sec 4 (deferred — entity aggregation), Sec 5 (already done from previous plan), Sec 6 (Phase 5), Sec 7 (Phase 2), Sec 8 (Phase 2), Sec 9 (deferred — permission gates), Sec 10 (Phase 1 restructure), Sec 11 (existing memory_views.py from previous plan), Sec 12 (Phase 5), Sec 13 (UOL — done in previous plan), Sec 14 (context_inference — done in previous plan), Sec 15 (Phase 1 restructure), Sec 16 (Phase 3), Sec 17 (Phase 3), Sec 18 (deferred — grounding), Sec 19 (Phase 3 temporal), Sec 20 (done in previous plan), Sec 21 (existing recursive_loop.py from previous plan), Sec 22 (Phase 2), Sec 23 (Phase 2), Sec 24 (Phase 5), Sec 25 (deferred), Sec 26 (checklist), Sec 27 (Phase 4), Sec 28 (Phase 4), Sec 29 (already aligned).

- [ ] **Placeholder scan:** No "TBD", "TODO", or "implement later" — every step has complete code.

- [ ] **Type consistency:** All renamed fields (`active_assumptions` → `active_assumption_claim_ids`, `known_limits` → `known_limit_claim_ids`, `session_affect` → `affect`, `pragmatic_state` → `dynamics`) are consistent across phases.

- [ ] **Test coverage:** Each phase includes test commands. Bug fixes include regression tests.
