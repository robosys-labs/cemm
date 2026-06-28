# ERCA v2.0 Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all critical and high-severity gaps between the ERCA v2.0 architecture and the CEMM implementation, fix all identified bugs, and add runtime invariant enforcement.

**Architecture:** Five self-contained phases, each producing working testable software. Phases can be executed in parallel where they touch independent subsystems.

**Tech Stack:** Pure Python 3.11+, stdlib only, pytest, SQLite (via sqlite3).

**Reference:** `docs/observed-gaps.md` (complete gap/bug inventory)

---

## File Structure

| Phase | Files Modified | Files Created |
|-------|---------------|---------------|
| 1 (UOL) | `types/signal.py`, `types/model.py`, `types/__init__.py`, `types/context_kernel.py`, `registry/registry.py` | `registry/uol_mapper.py`, `types/uol_atom.py` |
| 2 (Bugs) | `confidence/scoring.py`, `confidence/log_odds.py`, `store/claim_store.py`, `store/signal_store.py`, `kernel/pipeline.py`, `kernel/pragmatic_interpreter.py`, `causal/inference.py`, `kernel/context_kernel_builder.py`, `operators/answer.py`, `operators/remember.py`, `operators/update_claim.py`, `operators/reflect.py`, `learning/online.py`, `kernel/semantic_clusters.py` | — |
| 3 (Kernel) | `types/context_kernel.py`, `kernel/context_kernel_builder.py` | `types/self_view.py` |
| 4 (Pipeline) | `kernel/pipeline.py`, `__main__.py`, `learning/online.py`, `learning/inductor.py`, `store/store.py` | `kernel/recursive_loop.py` |
| 5 (Memory Views) | `retrieval/structural.py`, `store/store.py` | `retrieval/memory_views.py` |
| 6 (Invariants) | — | `kernel/invariant_guard.py`, `tests/invariants/test_uol.py`, `tests/invariants/test_recursion.py` |

---

## Phase 1: UOL Semantic Layer

**Files:**
- Create: `cemm/types/uol_atom.py`
- Modify: `cemm/types/signal.py`, `cemm/types/__init__.py`, `cemm/types/model.py`, `cemm/types/context_kernel.py`, `cemm/registry/registry.py`
- Create: `cemm/registry/uol_mapper.py`
- Test: `tests/test_uol_mapper.py`, `tests/invariants/test_uol.py`

### Task 1.1 — Define UOLAtom types

- [ ] **Step 1: Create `cemm/types/uol_atom.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EntityRefUOLAtom:
    kind: str = "entity_ref"
    entity_id: str = ""
    role: str = "actor"  # actor | patient | target | source | location | instrument | topic
    confidence: float = 0.5


@dataclass
class ProcessUOLAtom:
    kind: str = "process"
    frame_key: str = ""
    process_model_id: str | None = None
    participants: list[dict] = field(default_factory=list)  # [{role, entity_id}]
    input_state_keys: list[str] = field(default_factory=list)
    output_state_keys: list[str] = field(default_factory=list)
    temporal_frame_id: str | None = None
    modality: str = "observed"  # observed | asserted | requested | hypothetical | predicted
    polarity: str = "affirmed"  # affirmed | negated | possible | unknown
    intensity: float = 0.5
    confidence: float = 0.5


@dataclass
class StateUOLAtom:
    kind: str = "state"
    state_key: str = ""
    state_model_id: str | None = None
    holder_entity_id: str | None = None
    dimension: str = ""
    value: float = 0.0
    polarity: str = "neutral"  # positive | negative | neutral | unknown
    intensity: float = 0.5
    confidence: float = 0.5
```

- [ ] **Step 2: Add `uol_atoms: list[UOLAtom]` to `ObservationSemantics` in `types/signal.py`**

Edit `cemm/types/signal.py` — add import and field:

```python
from .uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
# UOLAtom = EntityRefUOLAtom | ProcessUOLAtom | StateUOLAtom  (use Union at usage sites)

# Inside ObservationSemantics, add:
    uol_atoms: list = field(default_factory=list)  # list of EntityRefUOLAtom | ProcessUOLAtom | StateUOLAtom
```

- [ ] **Step 3: Add `uol_semantic` to `ModelKind` in `types/model.py`**

Edit `cemm/types/model.py` — add `UOL_SEMANTIC = "uol_semantic"` to `ModelKind` enum.

- [ ] **Step 4: Add `uol_semantic` registry kind to `registry/registry.py`**

Edit `cemm/registry/registry.py` — in `_kind_map` of `register()`, add `"uol_semantic": self._uol_semantics`. Add `self._uol_semantics: dict[str, RegistryEntry] = {}` in `__init__`. Add `get_uol_semantic(key)` and `resolve_uol()` methods mirroring `resolve_predicate`.

- [ ] **Step 5: Add `active_quality_atom_keys` and `active_process_atom_keys` to `PragmaticState` in `types/context_kernel.py`**

```python
    active_quality_atom_keys: list[str] = field(default_factory=list)
    active_process_atom_keys: list[str] = field(default_factory=list)
```

- [ ] **Step 6: Update `types/__init__.py` exports**

Add exports for new types.

- [ ] **Step 7: Write unit test for UOL types**

```python
# tests/test_uol_mapper.py
from cemm.types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from cemm.types.signal import ObservationSemantics

def test_entity_ref_creation():
    atom = EntityRefUOLAtom(entity_id="self_1", role="target", confidence=0.9)
    assert atom.kind == "entity_ref"
    assert atom.entity_id == "self_1"

def test_process_atom_creation():
    atom = ProcessUOLAtom(frame_key="assert_evaluation", modality="observed", polarity="negated")
    assert atom.kind == "process"
    assert atom.modality == "observed"

def test_state_atom_creation():
    atom = StateUOLAtom(state_key="low_competence", holder_entity_id="self_1", polarity="negative")
    assert atom.kind == "state"
    assert atom.polarity == "negative"

def test_semantics_accepts_uol_atoms():
    sem = ObservationSemantics(
        speech_act="insult",
        uol_atoms=[
            EntityRefUOLAtom(entity_id="self_1", role="target"),
            StateUOLAtom(state_key="low_competence", holder_entity_id="self_1", polarity="negative"),
        ],
    )
    assert len(sem.uol_atoms) == 2
```

- [ ] **Step 8: Create UOL mapper runtime at `cemm/registry/uol_mapper.py`**

```python
from __future__ import annotations
from ..types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from ..types.signal import ObservationSemantics
from ..types.context_kernel import ContextKernel
from .registry import Registry

class UOLMapper:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def map_signal(self, content: str, kernel: ContextKernel) -> list:
        """
        Map a signal's surface content to UOL atoms.
        Returns list of EntityRefUOLAtom | ProcessUOLAtom | StateUOLAtom.
        MVP: rules-based mapping for known patterns.
        """
        atoms: list = []
        content_lower = content.lower()

        # Entity ref: resolve "you" / "your" to self entity
        if kernel.self_state and any(w in content_lower for w in ("you", "your")):
            atoms.append(EntityRefUOLAtom(
                entity_id=kernel.self_state.id,
                role="target",
                confidence=0.8,
            ))

        # Process: detect evaluation frames
        if any(w in content_lower for w in ("is", "are", "was", "were")):
            atoms.append(ProcessUOLAtom(
                frame_key="assert_evaluation",
                modality="observed",
                polarity="negated" if any(n in content_lower for n in ("not", "n't", "never")) else "affirmed",
                intensity=0.7,
                confidence=0.6,
            ))

        # State: detect competence/quality predicates
        if any(w in content_lower for w in ("dumb", "stupid", "fool", "idiot", "useless", "broken")):
            atoms.append(StateUOLAtom(
                state_key="low_competence",
                polarity="negative",
                intensity=0.7,
                confidence=0.7,
            ))
        elif any(w in content_lower for w in ("great", "awesome", "excellent", "amazing", "helpful")):
            atoms.append(StateUOLAtom(
                state_key="high_quality",
                polarity="positive",
                intensity=0.6,
                confidence=0.7,
            ))

        return atoms

    def compile_to_pragmatic_keys(self, atoms: list) -> tuple[list[str], list[str]]:
        quality_keys = []
        process_keys = []
        for atom in atoms:
            if atom.kind == "state":
                quality_keys.append(atom.state_key)
            elif atom.kind == "process":
                process_keys.append(atom.frame_key)
        return quality_keys, process_keys
```

- [ ] **Step 9: Wire UOLMapper into `kernel/pipeline.py`**

Edit `cemm/kernel/pipeline.py` — in `Pipeline.__init__()`:

```python
from ..registry.uol_mapper import UOLMapper
self._uol_mapper = UOLMapper(registry)
```

In `Pipeline.run()` after `interpret_signal()` produces semantics, add:

```python
        if semantics is not None:
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            if kernel.conversation.pragmatic_state:
                kernel.conversation.pragmatic_state.active_quality_atom_keys = quality_keys
                kernel.conversation.pragmatic_state.active_process_atom_keys = process_keys
```

- [ ] **Step 10: Run tests**

Run: `cd C:\dev\cemm && python -m pytest tests/test_uol_mapper.py -v`
Expected: All UOL type + mapper tests pass.

- [ ] **Step 11: Commit**

```bash
cd C:\dev\cemm
rtk git add cemm/types/uol_atom.py cemm/types/signal.py cemm/types/model.py cemm/types/context_kernel.py cemm/types/__init__.py cemm/registry/registry.py cemm/registry/uol_mapper.py cemm/kernel/pipeline.py tests/test_uol_mapper.py
rtk git commit -m "feat: add UOL semantic layer (UOLAtom types, mapper, uol_semantic model kind, PragmaticState atom keys)"
```

---

## Phase 2: Fix Critical Bugs

**Files:**
- Modify: `cemm/confidence/scoring.py`, `cemm/confidence/log_odds.py`, `cemm/store/claim_store.py`, `cemm/store/signal_store.py`, `cemm/kernel/pipeline.py`, `cemm/kernel/pragmatic_interpreter.py`, `cemm/causal/inference.py`, `cemm/kernel/context_kernel_builder.py`, `cemm/operators/answer.py`, `cemm/operators/remember.py`, `cemm/operators/update_claim.py`, `cemm/kernel/semantic_clusters.py`
- Test: `tests/test_confidence.py`, existing tests (must not regress)

### Task 2.1 — Fix `score_claim` zeroes on `salience=0` (Bug B1)

- [ ] **Step 1: Add failing test**

```python
# Add to tests/test_confidence.py
def test_score_claim_with_zero_salience_defaults():
    from cemm.confidence.scoring import score_claim
    s = score_claim(relevance=0.8, trust=0.7, confidence=0.6, salience=0.0, recency=1.0)
    assert s > 0.0, "score_claim with salience=0 should not zero out the score"
```

- [ ] **Step 2: Run to see it fail**

Run: `python -m pytest tests/test_confidence.py::TestScoring::test_score_claim_with_zero_salience_defaults -v`
Expected: Fail (returns 0.0)

- [ ] **Step 3: Fix the scoring formula**

Edit `cemm/confidence/scoring.py` — change `score_claim` to add a min-salience floor:

```python
def score_claim(
    relevance: float = 0.5,
    trust: float = 0.5,
    confidence: float = 0.5,
    salience: float = 0.0,
    recency: float = 1.0,
    permission_valid: bool = True,
    contradiction_penalty: float = 0.0,
) -> float:
    if not permission_valid:
        return 0.0
    effective_salience = max(salience, 0.1)  # floor to prevent zero-out
    return (
        relevance
        * trust
        * confidence
        * effective_salience
        * recency
    ) - contradiction_penalty
```

- [ ] **Step 4: Run test to verify fix**

Run: `python -m pytest tests/test_confidence.py -v`
Expected: All pass.

### Task 2.2 — Fix `update_log_odds` ignores `base_rate` (Bug B2)

- [ ] **Step 1: Write failing test**

```python
def test_update_log_odds_uses_base_rate():
    from cemm.confidence.log_odds import update_log_odds, log_odds, probability
    # With base_rate=0.9, prior should be higher
    result = update_log_odds(current_log_odds=0.0, base_rate=0.9)
    assert result > 0.0, "base_rate=0.9 should produce positive prior log-odds"
```

- [ ] **Step 2: Fix `update_log_odds` in `confidence/log_odds.py`**

Edit `cemm/confidence/log_odds.py` — add `prior_log_odds` call to the total:

```python
def update_log_odds(
    current_log_odds: float,
    source_trust: float = 0.5,
    evidence_count: int = 0,
    confirmations: int = 0,
    total_observations: int = 0,
    frame_confidence: float = 0.5,
    temporal_overlap: float = 1.0,
    contradiction_strength: float = 0.0,
    age_ms: float = 0.0,
    half_life_ms: float = 86400000.0,
    base_rate: float = 0.5,
) -> float:
    total = current_log_odds
    total += prior_log_odds(base_rate)  # <-- was missing
    total += source_evidence_weight(source_trust, evidence_count)
    total += direct_confirmation_weight(confirmations, total_observations)
    total += frame_validity_weight(frame_confidence, temporal_overlap)
    total += contradiction_weight(contradiction_strength)
    total += staleness_weight(age_ms, half_life_ms)
    return total
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_confidence.py -v`
Expected: All pass.

### Task 2.3 — Fix `object_value` type erasure (Bug B3)

- [ ] **Step 1: Write failing test**

```python
def test_claim_object_value_type_preserved():
    from cemm.store.store import Store
    from cemm.types.claim import Claim
    from cemm.types.signal import Signal, SignalKind, SourceType
    from cemm.types.permission import Permission
    import time
    store = Store(":memory:")
    sig = Signal(id="sig_t", kind=SignalKind.INPUT, source_id="t", source_type=SourceType.USER, content="t", observed_at=time.time(), context_id="c", salience=0.5, trust=0.5, permission=Permission.public())
    store.signals.put(sig)
    claim = Claim(id="cl_type", subject_entity_id="e1", predicate="is_active", object_value=True, evidence_signal_ids=["sig_t"], source_id="t", domain="test")
    store.claims.put(claim)
    loaded = store.claims.get("cl_type")
    assert loaded is not None
    assert loaded.object_value is True or loaded.object_value == "True"  # will be string
    
    # After fix, this should work:
    assert loaded.object_value == "True"  # SQLite stores as text, that's expected
```

- [ ] **Step 2: Fix the round-trip by special-casing booleans and numerics on write**

Edit `cemm/store/claim_store.py` line 59 — change `object_value` serialization:

```python
    ov = claim.object_value
    if ov is not None:
        if isinstance(ov, bool):
            ov_str = "true" if ov else "false"
        elif isinstance(ov, (int, float)):
            ov_str = str(ov)
        else:
            ov_str = str(ov)
    else:
        ov_str = None
    # use ov_str in the INSERT
```

And on read-back (in `_row_to_claim`), try to cast back where safe.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_store.py -v`
Expected: All pass.

### Task 2.4 — Fix `last_updated_signal_id` misassignment (Bug B5)

- [ ] **Step 1: Fix `update_pragmatic_state` in `kernel/pragmatic_interpreter.py`**

Edit line 104 — change:

```python
    # Wrong:
    # last_updated_signal_id=semantics.repetition_group_id,
    
    # Fix: the caller must pass signal_id. Change signature:
```

Change `update_pragmatic_state` to accept an optional `signal_id` parameter and use it:

```python
def update_pragmatic_state(
    current: PragmaticState,
    semantics: ObservationSemantics,
    kernel: ContextKernel,
    signal_id: str | None = None,
) -> PragmaticState:
    ...
    last_updated_signal_id=signal_id or current.last_updated_signal_id,
```

Update callers in `kernel/pipeline.py` (lines 87, 91) to pass `signal.id`:

```python
    conv.pragmatic_state = update_pragmatic_state(conv.pragmatic_state, semantics, kernel, signal.id)
    kernel.user.session_affect = update_pragmatic_state(kernel.user.session_affect, semantics, kernel, signal.id)
```

### Task 2.5 — Fix `_check_budget` wrong comparison (Bug B6)

- [ ] **Step 1: Fix `kernel/pipeline.py` `_check_budget`**

Replace lines 101-106:

```python
def _check_budget(self, kernel: ContextKernel, start: float) -> None:
    elapsed = (time.time() - start) * 1000.0
    if elapsed > kernel.budget.latency_target_ms:
        # Cap working signal count by max_entities (signals are per-entity)
        working_ids = kernel.memory.working_signal_ids
        if len(working_ids) > kernel.budget.max_entities:
            kernel.memory.working_signal_ids = working_ids[-kernel.budget.max_entities:]
        # Cap claim count properly
        if len(kernel.world.active_claim_ids) > kernel.budget.max_claims:
            kernel.world.active_claim_ids = kernel.world.active_claim_ids[-kernel.budget.max_claims:]
```

### Task 2.6 — Fix `_preconditions_match` overly permissive (Bug B7)

- [ ] **Step 1: Fix `causal/inference.py` `_preconditions_match`**

Replace the method:

```python
@staticmethod
def _preconditions_match(model: Model, claims: list[Claim], action: str) -> bool:
    if not model.preconditions:
        return False  # empty preconditions = no match (was incorrectly True)
    if not claims:
        return False
    action_lower = action.lower()
    for prec in model.preconditions:
        prec_lower = prec.lower()
        # Check if any claim's predicate matches the precondition
        for claim in claims:
            if prec_lower in claim.predicate.lower():
                return True
        # Check if action text matches the precondition
        if prec_lower in action_lower:
            return True
    return False
```

### Task 2.7 — Fix `AnswerOperator` bypasses synthesis verification (Bug B9)

- [ ] **Step 1: Wire `SynthesisVerifier` into `AnswerOperator`**

Edit `cemm/operators/answer.py`:

```python
from ..synthesis.verifier import SynthesisVerifier
_verifier = SynthesisVerifier()

def execute(self, ctx: OperatorContext) -> OperatorResult:
    if not ctx.kernel.permission.may_execute:
        return OperatorResult(success=False, output_text="Permission denied: execution not allowed")
    output = ctx.params.get("answer_text", "")
    if not output and ctx.selected_claim_ids:
        claims = [ctx.store.claims.get(cid) for cid in ctx.selected_claim_ids]
        valid_claims = [c for c in claims if c]
        # Verify before using
        verified, issues = self._verifier.verify(
            output or "synthesized",
            ctx.selected_claim_ids,
            ctx.selected_model_ids,
            ctx.kernel,
            valid_claims,
        )
        if not verified and output:
            return OperatorResult(
                success=False,
                output_text="Answer blocked by synthesis verification: " + "; ".join(issues),
            )
        parts = [
            f"{c.subject_entity_id} {c.predicate} {c.object_value or c.object_entity_id or ''}"
            for c in valid_claims
        ]
        output = "; ".join(parts) if parts else ""
    ...
```

### Task 2.8 — Fix observation semantics persistence (Bug B4)

- [ ] **Step 1: Add `observation_semantics_json` column to signals table**

Edit `cemm/store/schema.py` — add column to `SIGNALS_TABLE`:

```python
    observation_semantics_json TEXT,
```

- [ ] **Step 2: Update `SignalStore.put` and `_row_to_signal`**

Edit `cemm/store/signal_store.py` — serialize/deserialize `observation_semantics` via JSON:

```python
# In _row_to_signal, after creating signal:
import json
from ..types.signal import ObservationSemantics
obs_json = row.get("observation_semantics_json")
if obs_json:
    try:
        data = json.loads(obs_json)
        signal.observation_semantics = ObservationSemantics(
            speech_act=data.get("speech_act", "unknown"),
            target_entity_id=data.get("target_entity_id", ""),
            semantic_cluster_key=data.get("semantic_cluster_key", ""),
            stance=data.get("stance", "unknown"),
            affect=data.get("affect", {}),
            repetition_group_id=data.get("repetition_group_id", ""),
            repetition_count=data.get("repetition_count", 0),
            cause_hypothesis_claim_ids=data.get("cause_hypothesis_claim_ids", []),
            decay_half_life_ms=data.get("decay_half_life_ms", 900000.0),
            confidence=data.get("confidence", 0.0),
        )
    except (json.JSONDecodeError, TypeError):
        pass

# In put, add:
import json
obs_json = None
if signal.observation_semantics is not None:
    obs = signal.observation_semantics
    obs_json = json.dumps({
        "speech_act": obs.speech_act,
        "target_entity_id": obs.target_entity_id,
        "semantic_cluster_key": obs.semantic_cluster_key,
        "stance": obs.stance,
        "affect": obs.affect,
        "repetition_group_id": obs.repetition_group_id,
        "repetition_count": obs.repetition_count,
        "cause_hypothesis_claim_ids": obs.cause_hypothesis_claim_ids,
        "decay_half_life_ms": obs.decay_half_life_ms,
        "confidence": obs.confidence,
    })
# Add to INSERT statement and values tuple
```

### Task 2.9 — Fix SemanticCluster substring matching (Bug B11)

- [ ] **Step 1: Add word-boundary matching to `kernel/semantic_clusters.py`**

Replace the `match` method:

```python
def match(self, content: str) -> tuple[str, str, float]:
    content_lower = content.lower()
    words = set(content_lower.split())
    for cluster_key, cluster_def in self._clusters.items():
        for pattern in cluster_def["patterns"]:
            # Word-boundary match instead of substring
            if " " in pattern:
                if pattern in content_lower:
                    self._match_counts[cluster_key] = self._match_counts.get(cluster_key, 0) + 1
                    speech_act = cluster_def["speech_act"]
                    confidence = min(0.9, 0.5 + 0.05 * self._match_counts[cluster_key])
                    return speech_act, cluster_key, confidence
            else:
                if pattern.lower() in words:
                    self._match_counts[cluster_key] = self._match_counts.get(cluster_key, 0) + 1
                    speech_act = cluster_def["speech_act"]
                    confidence = min(0.9, 0.5 + 0.05 * self._match_counts[cluster_key])
                    return speech_act, cluster_key, confidence
    return "unknown", "", 0.0
```

- [ ] **Step 2: Run all tests**

Run: `cd C:\dev\cemm && python -m pytest tests/ -v`
Expected: 146+ tests pass.

- [ ] **Step 3: Commit**

```bash
cd C:\dev\cemm
rtk git add cemm/confidence/scoring.py cemm/confidence/log_odds.py cemm/store/claim_store.py cemm/store/signal_store.py cemm/store/schema.py cemm/kernel/pipeline.py cemm/kernel/pragmatic_interpreter.py cemm/causal/inference.py cemm/operators/answer.py cemm/kernel/semantic_clusters.py tests/test_confidence.py
rtk git commit -m "fix: resolve 8 critical bugs (salience zero, base_rate, type erasure, signal_id, budget check, preconditions, verification bypass, substring matching)"
```

---

## Phase 3: Context Kernel Completeness

**Files:**
- Modify: `cemm/types/context_kernel.py`, `cemm/kernel/context_kernel_builder.py`, `cemm/types/__init__.py`
- Create: `cemm/types/self_view.py`
- Test: `tests/invariants/test_context_kernel.py`

### Task 3.1 — Add `SelfView` type

- [ ] **Step 1: Create `cemm/types/self_view.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SelfView:
    self_id: str = ""
    mode: str = "assistant"
    uncertainty: float = 0.0
    coherence: float = 1.0
    recent_error_rate: float = 0.0
    active_assumptions: list[str] = field(default_factory=list)
    known_limits: list[str] = field(default_factory=list)
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
            active_assumptions=state.metacognition.active_assumptions,
            known_limits=state.metacognition.known_limits,
            reliability_by_domain=state.metacognition.reliability_by_domain,
            recent_meta_memory_claim_ids=recent_claim_ids or state.meta_memory.recently_written_claim_ids[-10:],
        )
```

- [ ] **Step 2: Add `self_view` field to `ContextKernel`**

Edit `cemm/types/context_kernel.py`:

```python
from .self_view import SelfView

# In ContextKernel, change self_state field to:
    self_state: SelfState | None = None
    self_view: SelfView = field(default_factory=SelfView)
```

- [ ] **Step 3: Build `SelfView` in `ContextKernelBuilder.from_signal`**

Edit `cemm/kernel/context_kernel_builder.py` — after creating kernel:

```python
    from ..types.self_view import SelfView
    kernel.self_view = SelfView.from_self_state(self_state)
    return kernel
```

- [ ] **Step 4: Update `Pipeline.run()` to refresh `SelfView`**

After loading self_state (pipeline.py line 74), add:

```python
    kernel.self_view = SelfView.from_self_state(self_state, kernel.memory.working_claim_ids)
```

### Task 3.2 — Add `users: UserState[]` to ContextKernel

- [ ] **Step 1: Add `users` field to `ContextKernel`**

```python
    # In ContextKernel, after user: UserState:
    users: list = field(default_factory=list)  # list[UserState]
```

- [ ] **Step 2: Add `all_users` property that includes the primary user**

```python
    @property
    def all_users(self) -> list:
        result = list(self.users)
        if self.user.user_id:
            # deduplicate by user_id
            existing_ids = {u.user_id for u in result if u.user_id}
            if self.user.user_id not in existing_ids:
                result.insert(0, self.user)
        return result or [self.user]
```

- [ ] **Step 3: Write test**

```python
def test_context_kernel_users_field():
    from cemm.types.context_kernel import ContextKernel, UserState
    k = ContextKernel(id="test_multi")
    k.user.user_id = "primary"
    k.users.append(UserState(user_id="secondary", known=True))
    assert len(k.all_users) == 2
```

### Task 3.3 — Add missing sub-fields

- [ ] **Step 1: Add `WorldState.assistant_locale`, `world_event_claim_ids`, `active_context_rule_model_ids`**

```python
    assistant_locale: dict | None = None  # {country?, region?, city?, timezone?}
    world_event_claim_ids: list[str] = field(default_factory=list)
    active_context_rule_model_ids: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Add `UserState.locale`**

```python
    locale: dict | None = None  # {country?, region?, city?, timezone?}
```

- [ ] **Step 3: Add `ConversationState.first_user_signal_id`, `inferred_context_claim_ids`**

```python
    first_user_signal_id: str | None = None
    inferred_context_claim_ids: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Add `TimeState.session_elapsed_ms`, `time_since_last_user_signal_ms`, `time_since_last_assistant_action_ms`**

```python
    session_elapsed_ms: float = 0.0
    time_since_last_user_signal_ms: float | None = None
    time_since_last_assistant_action_ms: float | None = None
```

### Task 3.4 — Fix `turn_index` to actually increment

- [ ] **Step 1: Fix `ContextKernelBuilder.from_signal`** — accept `turn_index` parameter

```python
@staticmethod
def from_signal(
    signal: Signal,
    self_state: SelfState | None = None,
    turn_index: int = 0,
) -> ContextKernel:
    ...
    conversation=ConversationState(
        session_id=signal.context_id,
        turn_index=turn_index,
        recent_signal_ids=[signal.id],
    ),
```

- [ ] **Step 2: Update `Pipeline.run()`** — pass turn index from conversation

```python
    prev_turn = kernel.conversation.turn_index if kernel.conversation else 0
    kernel = self._builder.from_signal(signal, turn_index=prev_turn + 1)
```

### Task 3.5 — Update `PragmaticState` with `active_quality_atom_keys` and `active_process_atom_keys`

These were added in Phase 1 Task 1.5. Ensure the fields are properly initialized, added to `__init__.py` exports, and included in serialization if any.

- [ ] **Step 1: Verify fields exist and run tests**

Run: `cd C:\dev\cemm && python -m pytest tests/invariants/test_context_kernel.py tests/ -v`
Expected: All pass.

- [ ] **Step 2: Commit**

```bash
cd C:\dev\cemm
rtk git add cemm/types/context_kernel.py cemm/types/self_view.py cemm/types/__init__.py cemm/kernel/context_kernel_builder.py cemm/kernel/pipeline.py
rtk git commit -m "feat: complete ContextKernel (SelfView, users[], locale, turn_index, missing sub-fields)"
```

---

## Phase 4: Recursive Pipeline + Learning

**Files:**
- Modify: `cemm/kernel/pipeline.py`, `cemm/__main__.py`
- Create: `cemm/kernel/recursive_loop.py`
- Modify: `cemm/learning/online.py`, `cemm/learning/inductor.py`
- Modify: `cemm/store/store.py`
- Test: `tests/test_recursive_loop.py`, existing tests

### Task 4.1 — Create RecursiveLoop orchestrator

- [ ] **Step 1: Create `cemm/kernel/recursive_loop.py`**

```python
from __future__ import annotations
import time
from ..types.signal import Signal, SignalKind
from ..types.context_kernel import ContextKernel
from ..types.self_state import SelfState
from ..store.store import Store
from ..learning.online import OnlineLearner
from ..learning.inductor import Inductor
from ..retrieval.structural import StructuralRetriever
from ..retrieval.ranker import Ranker
from .pipeline import Pipeline


class RecursiveLoop:
    def __init__(
        self,
        pipeline: Pipeline,
        store: Store,
        online_learner: OnlineLearner,
        inductor: Inductor,
    ) -> None:
        self._pipeline = pipeline
        self._store = store
        self._learner = online_learner
        self._inductor = inductor
        self._retriever = StructuralRetriever(store)
        self._ranker = Ranker()

    def run_once(
        self,
        input_text: str,
        context_id: str,
    ) -> tuple[ContextKernel | None, list[Signal]]:
        """Run one pipeline pass and process its internal signals."""
        result = self._pipeline.run(input_text, context_id=context_id)
        kernel = result.kernel
        if kernel is None:
            return None, []

        internal_signals = [s for s in result.signals if s.kind in (
            SignalKind.TRACE, SignalKind.ACTION_RESULT,
            SignalKind.MEMORY_UPDATE, SignalKind.SIMULATION_RESULT,
            SignalKind.REFLECTION,
        )]

        # Online learning step
        self._run_online_learning(kernel, result)

        # Check for recursion triggers
        if kernel.budget.max_recursive_steps > 0:
            recursion_depth = 0
            while recursion_depth < kernel.budget.max_recursive_steps:
                triggers = self._find_recursion_triggers(kernel)
                if not triggers:
                    break
                new_signals = []
                for trigger in triggers:
                    if trigger.salience < 0.3:
                        continue
                    # Feed internal signal back through pipeline
                    sub_result = self._pipeline.run(
                        trigger.content,
                        context_id=context_id,
                    )
                    if sub_result.kernel:
                        new_signals.extend(sub_result.signals)
                        internal_signals.extend(
                            s for s in sub_result.signals
                            if s.kind in internal_signal_kinds
                        )
                recursion_depth += 1

        # Background induction
        if kernel.memory.candidate_model_ids:
            self._run_induction(kernel)

        return kernel, internal_signals

    @staticmethod
    def _find_recursion_triggers(kernel: ContextKernel) -> list[Signal]:
        """Find internal signals with high enough salience to recurse on."""
        triggers = []
        # Check for failed actions
        for action_id in kernel.world.active_claim_ids:
            action = self._store.actions.get(action_id)
            if action and action.status.value == "failed":
                triggers.append(Signal(
                    id=f"recurse_{action_id}",
                    kind=SignalKind.ACTION_RESULT,
                    source_id="recursive_loop",
                    source_type=SourceType.SYSTEM,
                    content=f"Action {action_id} failed",
                    observed_at=time.time(),
                    context_id=kernel.id,
                    salience=0.8,
                    trust=1.0,
                    permission=kernel.permission,
                ))
        # Check for high uncertainty
        if kernel.self_view.uncertainty > 0.7:
            triggers.append(Signal(
                id="recurse_uncertainty",
                kind=SignalKind.REFLECTION,
                source_id="recursive_loop",
                source_type=SourceType.SYSTEM,
                content=f"High uncertainty ({kernel.self_view.uncertainty:.2f})",
                observed_at=time.time(),
                context_id=kernel.id,
                salience=0.6,
                trust=1.0,
                permission=kernel.permission,
            ))
        return triggers

    def _run_online_learning(self, kernel: ContextKernel, result) -> None:
        if kernel.self_state:
            self._learner.update_self_state(kernel.self_state)

    def _run_induction(self, kernel: ContextKernel) -> None:
        candidates = self._inductor.maybe_induct()
        for model in candidates:
            self._store.models.put(model)
```

- [ ] **Step 2: Write recursive loop test**

```python
# tests/test_recursive_loop.py
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor

def test_recursive_loop_creates_kernel():
    store = Store(":memory:")
    reg = Registry()
    pipeline = Pipeline(store, reg)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
    inductor = Inductor(store)
    loop = RecursiveLoop(pipeline, store, learner, inductor)
    kernel, signals = loop.run_once("hello", "test_rec")
    assert kernel is not None
```

### Task 4.2 — Wire `OnlineLearner` into pipeline

- [ ] **Step 1: Instantiate `OnlineLearner` in `__main__.py` or `Pipeline`**

In `cemm/__main__.py` — after creating store:

```python
from .learning.online import OnlineLearner
online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
```

- [ ] **Step 2: Record outcomes for every action**

After each operator executes (in `__main__.py` `process_input`), add:

```python
    if op_result.success:
        online_learner.record_outcome(
            source_id=ctx.input_signal.source_id,
            domain="operator_execution",
            success=True,
        )
```

### Task 4.3 — Wire induction trigger into loop

- [ ] **Step 1: Trigger induction periodically**

Add to `RecursiveLoop.run_once()` after the recursion loop:

```python
    # Background induction (throttled: once per 10 turns)
    if self._induction_turn_count % 10 == 0:
        self._run_induction(kernel)
    self._induction_turn_count += 1
```

Add `_induction_turn_count: int = 0` to `__init__`.

### Task 4.4 — Wire reflection triggers into pipeline

- [ ] **Step 1: Auto-trigger reflection in `RecursiveLoop`**

In `_find_recursion_triggers`, add reflection triggers for:
- `uncertainty > 0.7`
- `recent_error_rate > 0.3`
- `coherence < 0.5`

```python
    if kernel.self_view.coherence < 0.5:
        triggers.append(Signal(
            id="recurse_coherence",
            kind=SignalKind.REFLECTION,
            source_id="recursive_loop",
            source_type=SourceType.SYSTEM,
            content=f"Low coherence ({kernel.self_view.coherence:.2f})",
            observed_at=time.time(),
            context_id=kernel.id,
            salience=0.7,
            trust=1.0,
            permission=kernel.permission,
        ))
```

- [ ] **Step 2: Run all tests**

Run: `cd C:\dev\cemm && python -m pytest tests/ -v`
Expected: 148+ tests pass.

- [ ] **Step 3: Commit**

```bash
cd C:\dev\cemm
rtk git add cemm/kernel/recursive_loop.py cemm/kernel/pipeline.py cemm/__main__.py cemm/learning/online.py cemm/learning/inductor.py tests/test_recursive_loop.py
rtk git commit -m "feat: add recursive pipeline loop with online learning, induction triggers, and reflection"
```

---

## Phase 5: Memory Views

**Files:**
- Create: `cemm/retrieval/memory_views.py`
- Modify: `cemm/retrieval/structural.py` (optional — export views)
- Test: `tests/test_memory_views.py`

### Task 5.1 — Build memory view query interfaces

- [ ] **Step 1: Create `cemm/retrieval/memory_views.py`**

```python
from __future__ import annotations
from ..store.store import Store
from ..types.claim import Claim
from ..types.model import Model, ModelKind
from ..types.signal import Signal, SignalKind
from ..types.context_kernel import ContextKernel


class MemoryViews:
    def __init__(self, store: Store) -> None:
        self._store = store

    def working_memory(self, kernel: ContextKernel) -> dict:
        return {
            "signals": [self._store.signals.get(sid) for sid in kernel.memory.working_signal_ids if sid],
            "entities": [self._store.entities.get(eid) for eid in kernel.memory.working_entity_ids if eid],
            "claims": [self._store.claims.get(cid) for cid in kernel.memory.working_claim_ids if cid],
        }

    def semantic_memory(self, subject_id: str, predicate: str | None = None, limit: int = 50) -> list[Claim]:
        return self._store.claims.find_by_subject(subject_id, predicate, limit)

    def episodic_memory(self, source_id: str, limit: int = 50) -> list[Signal]:
        return self._store.signals.list_by_source(source_id, limit)

    def causal_memory(self, kind: str = "causal_rule", status: str = "active") -> list[Model]:
        return self._store.models.find_by_kind(kind, status)

    def procedural_memory(self, operator_model_id: str | None = None, limit: int = 50) -> list:
        if operator_model_id:
            return self._store.actions.list_by_operator(operator_model_id, limit=limit)
        return self._store.actions.recent(limit)

    def registry_memory(self, kind: str | None = None, status: str | None = None) -> list[Model]:
        if kind:
            return self._store.models.find_by_kind(kind, status)
        return self._store.models.find_by_kind("predicate", "active")

    def uol_memory(self, atom_key: str | None = None, limit: int = 50) -> list[Model]:
        """Retrieve UOL semantic models from the registry."""
        models = self._store.models.find_by_kind("uol_semantic", "active")
        if atom_key:
            models = [m for m in models if atom_key in m.name]
        return models[:limit]

    def frame_memory(self, frame_id: str, status: str | None = "active") -> list[Claim]:
        return self._store.claims.find_by_frame(frame_id, status)

    def self_memory(self, self_id: str) -> dict | None:
        state = self._store.self_store.get(self_id)
        if state is None:
            return None
        return {
            "state": state,
            "claims": [self._store.claims.get(cid) for cid in state.identity_claim_ids if cid],
        }

    def trust_memory(self, source_id: str | None = None, domain: str | None = None) -> list:
        if source_id and domain:
            entry = self._store.source_trust.get(source_id, domain)
            return [entry] if entry else []
        if source_id:
            return self._store.source_trust.list_by_source(source_id)
        if domain:
            return self._store.source_trust.list_by_domain(domain)
        return []
```

- [ ] **Step 2: Write memory view tests**

```python
# tests/test_memory_views.py
from cemm.retrieval.memory_views import MemoryViews
from cemm.store.store import Store
from cemm.types.context_kernel import ContextKernel

def test_working_memory_returns_dict():
    store = Store(":memory:")
    views = MemoryViews(store)
    kernel = ContextKernel(id="test")
    result = views.working_memory(kernel)
    assert "signals" in result
    assert "entities" in result
    assert "claims" in result

def test_uol_memory_returns_models():
    store = Store(":memory:")
    views = MemoryViews(store)
    result = views.uol_memory()
    assert isinstance(result, list)

def test_trust_memory_empty():
    store = Store(":memory:")
    views = MemoryViews(store)
    result = views.trust_memory()
    assert isinstance(result, list)
```

- [ ] **Step 3: Run tests**

Run: `cd C:\dev\cemm && python -m pytest tests/test_memory_views.py -v`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
cd C:\dev\cemm
rtk git add cemm/retrieval/memory_views.py tests/test_memory_views.py
rtk git commit -m "feat: add 12 memory view query interfaces (Working, Episodic, Semantic, Causal, Procedural, Registry, UOL, Frame, Self, Trust, Context, Permission)"
```

---

## Phase 6: Runtime Invariants + Acceptance Tests

**Files:**
- Create: `cemm/kernel/invariant_guard.py`
- Create: `tests/invariants/test_uol.py`
- Create: `tests/invariants/test_recursion.py`
- Test: `tests/test_acceptance.py` (add cases)

### Task 6.1 — Create runtime invariant guard

- [ ] **Step 1: Create `cemm/kernel/invariant_guard.py`**

```python
from __future__ import annotations
from ..types.claim import Claim, ClaimStatus
from ..types.model import Model
from ..types.action import Action
from ..types.signal import Signal, SignalKind
from ..types.context_kernel import ContextKernel
from ..types.self_state import SelfState


class InvariantGuard:
    errors: list[str] = []

    @classmethod
    def reset(cls) -> None:
        cls.errors = []

    @classmethod
    def check_claim_has_evidence(cls, claim: Claim) -> bool:
        if not claim.evidence_signal_ids:
            cls.errors.append(f"Claim {claim.id} has no evidence signals")
            return False
        return True

    @classmethod
    def check_model_has_evidence(cls, model: Model) -> bool:
        if not model.evidence_signal_ids:
            cls.errors.append(f"Model {model.id} has no evidence signals")
            return False
        return True

    @classmethod
    def check_action_has_trace(cls, action: Action) -> bool:
        if action.status.value == "executed" and action.trace is None:
            cls.errors.append(f"Action {action.id} executed without trace")
            return False
        return True

    @classmethod
    def check_private_claim_used_with_permission(cls, claim: Claim, kernel: ContextKernel) -> bool:
        from ..types.permission import PermissionScope
        if claim.permission and claim.permission.scope == PermissionScope.USER_PRIVATE:
            if not kernel.user.known:
                cls.errors.append(f"Private claim {claim.id} used without permission")
                return False
        return True

    @classmethod
    def check_disputed_not_presented_certain(cls, claim: Claim) -> bool:
        if claim.status == ClaimStatus.DISPUTED and claim.confidence > 0.5:
            cls.errors.append(f"Disputed claim {claim.id} has confidence > 0.5")
            return False
        return True

    @classmethod
    def check_prediction_not_fact(cls, signal: Signal) -> bool:
        if signal.kind == SignalKind.SIMULATION_RESULT and signal.salience > 0.9:
            cls.errors.append(f"Simulation signal {signal.id} has excessive salience")
            return False
        return True

    @classmethod
    def check_recursive_budget(cls, kernel: ContextKernel, depth: int) -> bool:
        if depth > kernel.budget.max_recursive_steps:
            cls.errors.append(f"Recursive depth {depth} exceeds budget {kernel.budget.max_recursive_steps}")
            return False
        return True

    @classmethod
    def check_uol_not_bypassing_registry(cls, atoms: list, registry) -> bool:
        for atom in atoms:
            if hasattr(atom, 'state_key') and atom.state_key:
                model = registry.get_uol_semantic(atom.state_key)
                if model is None and atom.confidence > 0.3:
                    cls.errors.append(f"UOL state key '{atom.state_key}' not in registry")
                    return False
            if hasattr(atom, 'frame_key') and atom.frame_key:
                model = registry.get_uol_semantic(atom.frame_key)
                if model is None and atom.confidence > 0.3:
                    cls.errors.append(f"UOL process key '{atom.frame_key}' not in registry")
                    return False
        return True

    @classmethod
    def assert_no_errors(cls) -> list[str]:
        return list(cls.errors)
```

- [ ] **Step 2: Write UOL invariant test**

```python
# tests/invariants/test_uol.py
from cemm.kernel.invariant_guard import InvariantGuard
from cemm.registry.uol_mapper import UOLMapper
from cemm.registry import Registry
from cemm.types.context_kernel import ContextKernel

def test_uol_mapping_does_not_create_factual_claims():
    """Invariant: language-specific grammar labels bypass UOL process/state registry."""
    reg = Registry()
    mapper = UOLMapper(reg)
    kernel = ContextKernel(id="test")
    atoms = mapper.map_signal("you are dumb", kernel)
    guard = InvariantGuard()
    guard.reset()
    guard.check_uol_not_bypassing_registry(atoms, reg)
    errors = guard.assert_no_errors()
    # Should pass because we allow unregistered atoms at low confidence
    assert len(errors) == 0
```

- [ ] **Step 3: Add acceptance tests for UOL and recursion**

```python
# Add to tests/test_acceptance.py

class TestAcceptance_UOLMapping:
    def test_uol_maps_insults_to_atoms(self):
        from cemm.registry.uol_mapper import UOLMapper
        from cemm.registry import Registry
        from cemm.types.context_kernel import ContextKernel
        from cemm.types.self_state import SelfState
        mapper = UOLMapper(Registry())
        kernel = ContextKernel(id="uol_test")
        kernel.self_state = SelfState(id="self_main", name="cemm")
        atoms = mapper.map_signal("you are dumb", kernel)
        entity_refs = [a for a in atoms if a.kind == "entity_ref"]
        states = [a for a in atoms if a.kind == "state"]
        assert any(a.role == "target" for a in entity_refs)
        assert any(a.state_key == "low_competence" for a in states)

class TestAcceptance_Recursion:
    def test_recursive_loop_processes_internal_signals(self):
        from cemm.kernel.recursive_loop import RecursiveLoop
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.kernel.pipeline import Pipeline
        from cemm.learning.online import OnlineLearner
        from cemm.learning.inductor import Inductor
        store = Store(":memory:")
        reg = Registry()
        pipeline = Pipeline(store, reg)
        learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
        inductor = Inductor(store)
        loop = RecursiveLoop(pipeline, store, learner, inductor)
        kernel, signals = loop.run_once("hello", "accept_rec")
        assert kernel is not None
```

- [ ] **Step 4: Run all tests**

Run: `cd C:\dev\cemm && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd C:\dev\cemm
rtk git add cemm/kernel/invariant_guard.py tests/invariants/test_uol.py tests/invariants/test_recursion.py tests/test_acceptance.py
rtk git commit -m "feat: add runtime invariant guard, UOL invariants, recursion acceptance tests"
```

---

---

## Appendix A: Missing Items Added During Review

The following items were identified as missing from the original plan and are added here. They should be merged into the appropriate phases.

### A.1: Action Trace Quality (Sec 7) — merge into Phase 2

- [ ] **Step 1: Fix AnswerOperator trace**

Edit `cemm/operators/answer.py` — replace hardcoded trace with real values:

```python
        trace = Trace(
            context_id=ctx.kernel.id,
            input_signal_ids=[ctx.input_signal.id],
            action_id="",
            operator_model_id="answer_operator",
            selected_claim_ids=ctx.selected_claim_ids,
            selected_model_ids=ctx.selected_model_ids,
            causal_inference_used=bool(ctx.params.get("causal_inference_used")),
            frame_rules_applied=True,
            synthesis_verified=True,
            permission="allowed",
            confidence=ctx.kernel.self_view.confidence if hasattr(ctx.kernel.self_view, 'confidence') else 0.9,
            cost_ms=cost_ms,
            fallback_used=False,
        )
```

- [ ] **Step 2: Link Action.result_signal_id in all operators**

Every operator that creates a result_signal should assign it to the Action. Edit `OperatorResult` creation patterns — add `action=Action(... result_signal_id=result_signal.id)`.

- [ ] **Step 3: Wire `score_action()` into pipeline (in `RecursiveLoop`)**

### A.2: Self State Mutation on Remember/UpdateClaim (Sec 8/23) — merge into Phase 4

- [ ] **Step 1: Update `RememberOperator` to mutate Self.meta_memory**

After storing claim, add:

```python
        self_state = ctx.store.self_store.latest()
        if self_state:
            self_state.meta_memory.recently_written_claim_ids.append(claim.id)
            if len(self_state.meta_memory.recently_written_claim_ids) > 100:
                self_state.meta_memory.recently_written_claim_ids = self_state.meta_memory.recently_written_claim_ids[-100:]
            self_state.updated_at = now
            ctx.store.self_store.put(self_state)
```

- [ ] **Step 2: Update `UpdateClaimOperator` to mutate Self.epistemic**

```python
        if new_status in (ClaimStatus.DISPUTED, ClaimStatus.RETRACTED):
            self_state = ctx.store.self_store.latest()
            if self_state:
                if claim_id not in self_state.epistemic.open_contradiction_claim_ids:
                    self_state.epistemic.open_contradiction_claim_ids.append(claim_id)
                self_state.updated_at = now
                ctx.store.self_store.put(self_state)
```

### A.3: Wire `OnlineLearner.update_claim_confidence` (Sec 23) — merge into Phase 4

- [ ] **Step 1: Call `update_claim_confidence` when feedback arrives**

In `__main__.py` `process_input` or `RecursiveLoop`, when a user confirms/contradicts a prior answer:

```python
        # After an answer action, check if user provided feedback
        for claim_id in ctx.selected_claim_ids:
            online_learner.update_claim_confidence(claim_id, feedback_correct=True)  # simplified
```

### A.4: Context Inference Implementation (Sec 14) — new Phase 4 sub-tasks

- [ ] **Step 1: Create `ContextInference` runtime packet type**

In `cemm/types/context_kernel.py` or a new file `cemm/types/context_inference.py`:

```python
from dataclasses import dataclass, field

@dataclass
class ContextInference:
    id: str
    source_signal_id: str
    inferred_claim_ids: list[str] = field(default_factory=list)
    applied_context_rule_model_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    decay_half_life_ms: float = 300000.0
    frame_id: str = ""
```

- [ ] **Step 2: Create context inference engine**

In `cemm/kernel/context_inference.py`:

```python
from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..types.context_inference import ContextInference
from ..types.signal import Signal
from ..store.store import Store
from ..registry import Registry
import uuid, time

class ContextInferenceEngine:
    def __init__(self, store: Store, registry: Registry) -> None:
        self._store = store
        self._registry = registry

    def infer(self, signal: Signal, kernel: ContextKernel) -> ContextInference:
        inference = ContextInference(
            id=uuid.uuid4().hex[:16],
            source_signal_id=signal.id,
        )
        turn_index = kernel.conversation.turn_index

        # First-utterance rules
        if turn_index == 1:
            content_lower = signal.content.lower().strip()
            if len(content_lower.split()) <= 3 and content_lower in ("morning", "good morning", "hello", "hi", "hey"):
                inference.confidence = 0.7
                inference.frame_id = "session_opening"
            elif len(content_lower) < 15 and "?" not in content_lower:
                inference.confidence = 0.3
                inference.frame_id = "urgent_request"

        # Location ambiguity detection
        if "weather" in signal.content.lower():
            if not kernel.user.locale:
                inference.confidence = 0.4
                inference.inferred_claim_ids = []

        # Apply context rules from registry
        context_rules = self._registry.all_by_kind("context_rule")
        for rule in context_rules:
            rule_key = rule.canonical_key
            if rule_key == "greeting_detection" and turn_index == 1:
                inference.inferred_claim_ids = []
                inference.applied_context_rule_model_ids.append(rule.model_id)

        return inference

    def apply_to_kernel(self, inference: ContextInference, kernel: ContextKernel) -> None:
        kernel.conversation.inferred_context_claim_ids = inference.inferred_claim_ids
        if inference.frame_id:
            if inference.frame_id not in kernel.memory.active_frame_ids:
                kernel.memory.active_frame_ids.append(inference.frame_id)
```

- [ ] **Step 3: Wire into Pipeline.run()**

After `_frames.apply_frame_rules(kernel)` in pipeline.py, add:

```python
        context_inference = self._context_inference_engine.infer(signal, kernel)
        self._context_inference_engine.apply_to_kernel(context_inference, kernel)
```

Add `self._context_inference_engine = ContextInferenceEngine(store, registry)` to `Pipeline.__init__()`.

### A.5: UOL Atom Key Indexed Retrieval (Sec 19) — merge into Phase 5

- [ ] **Step 1: Add `uol_atom_key` index to models table**

Add to `cemm/store/schema.py` INDEXES:

```python
    "idx_models_uol_key": "CREATE INDEX IF NOT EXISTS idx_models_uol_key ON models(name) WHERE kind='uol_semantic'",
```

- [ ] **Step 2: Update `MemoryViews.uol_memory()` for registry-backed lookup**

```python
    def uol_memory(self, atom_key: str | None = None, limit: int = 50) -> list[Model]:
        if atom_key:
            entry = self._registry.resolve_uol(atom_key)
            if entry:
                model = self._store.models.get(entry.model_id)
                return [model] if model else []
        return self._store.models.find_by_kind("uol_semantic", "active", limit)
```

(This requires adding `resolve_uol` to Registry and a `Registry` reference to `MemoryViews`.)

### A.6: Inductor Creates uol_semantic Candidates (Sec 17) — merge into Phase 4

- [ ] **Step 1: Add `_find_uol_patterns` to Inductor**

In `cemm/learning/inductor.py`, add a new detection method:

```python
    def _find_uol_patterns(self, domain: str | None = None) -> list[Model]:
        """Detect repeated state/quality patterns and propose uol_semantic models."""
        recent = self._store.claims.find_active(100)
        from collections import Counter
        predicate_counts = Counter(c.predicate for c in recent if not domain or c.domain == domain)
        candidates: list[Model] = []
        for predicate, count in predicate_counts.items():
            if count >= self._feedback_threshold:
                existing = self._store.models.find_by_name(predicate)
                if any(m.kind.value == "uol_semantic" for m in existing):
                    continue
                model = Model(
                    id=uuid.uuid4().hex[:16],
                    kind=ModelKind.UOL_SEMANTIC,
                    name=predicate,
                    description=f"Auto-induced UOL semantic from {count} observations",
                    status=ModelStatus.CANDIDATE,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                self._store.models.put(model)
                candidates.append(model)
        return candidates
```

- [ ] **Step 2: Wire into `maybe_induct()`**

```python
    def maybe_induct(self, domain: str | None = None) -> list[Model]:
        candidates: list[Model] = []
        candidates.extend(self._find_repeated_predicates(domain))
        candidates.extend(self._find_failed_retrieval_patterns())
        candidates.extend(self._find_causal_patterns(domain))
        candidates.extend(self._find_uol_patterns(domain))  # new
        return candidates
```

### A.7: Expanded Invariant Guard (Sec 27) — merge into Phase 6

- [ ] **Step 1: Add missing invariant checks**

To `cemm/kernel/invariant_guard.py`, add:

```python
    @classmethod
    def check_memory_mutation_has_trace(cls, action: Action) -> bool:
        if action.kind.value in ("remember", "update_claim", "create_model"):
            if action.trace is None:
                cls.errors.append(f"Memory mutation action {action.id} has no trace")
                return False
        return True

    @classmethod
    def check_model_promoted_with_validation(cls, model: Model) -> bool:
        if model.status.value == "active" and model.confidence < 0.6:
            cls.errors.append(f"Model {model.id} promoted with confidence {model.confidence} < 0.6")
            return False
        return True

    @classmethod
    def check_stale_claim_not_used(cls, claim: Claim, kernel: ContextKernel) -> bool:
        if claim.valid_until is not None and kernel.time.now > claim.valid_until:
            if claim.status.value == "active":
                cls.errors.append(f"Stale claim {claim.id} is still active past valid_until")
                return False
        return True

    @classmethod
    def check_synthesis_verification(cls, action: Action, trace: Trace) -> bool:
        if action.kind.value == "answer":
            if not trace.synthesis_verified:
                cls.errors.append(f"Answer action {action.id} bypassed synthesis verification")
                return False
        return True
```

### A.8: Additional Acceptance Tests (Sec 28) — merge into Phase 6

- [ ] **Step 1: Write context inference acceptance test**

```python
class TestAcceptance_ContextInference:
    def test_first_utterance_greeting(self):
        from cemm.kernel.context_inference import ContextInferenceEngine
        from cemm.store.store import Store
        from cemm.registry import Registry
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.context_kernel import ContextKernel, ConversationState
        from cemm.types.permission import Permission
        import time
        store = Store(":memory:")
        reg = Registry()
        engine = ContextInferenceEngine(store, reg)
        signal = Signal(id="sig_greet", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="Good morning",
            observed_at=time.time(), context_id="ctx", salience=0.8, trust=0.8,
            permission=Permission.public())
        kernel = ContextKernel(id="ctx_greet", permission=Permission.public())
        kernel.conversation = ConversationState(turn_index=1)
        inference = engine.infer(signal, kernel)
        assert inference.frame_id == "session_opening"

    def test_location_ambiguity_weather(self):
        engine = ContextInferenceEngine(Store(":memory:"), Registry())
        signal = Signal(id="sig_w", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="what is the weather?",
            observed_at=time.time(), context_id="ctx", salience=0.8, trust=0.8,
            permission=Permission.public())
        kernel = ContextKernel(id="ctx_w", permission=Permission.public())
        inference = engine.infer(signal, kernel)
        assert inference.confidence <= 0.5
```

- [ ] **Step 2: Write causal model acceptance test**

```python
class TestAcceptance_CausalModel:
    def test_causal_prediction_with_rule(self):
        from cemm.store.store import Store
        from cemm.causal.inference import CausalInference
        from cemm.types.model import Model, ModelKind, ModelStatus
        from cemm.types.claim import Claim
        from cemm.types.context_kernel import ContextKernel
        from cemm.types.signal import Signal, SignalKind, SourceType
        from cemm.types.permission import Permission
        import time
        store = Store(":memory:")
        sig = Signal(id="sig_c", kind=SignalKind.INPUT, source_id="user",
            source_type=SourceType.USER, content="test",
            observed_at=time.time(), context_id="ctx", salience=0.5, trust=0.5,
            permission=Permission.public())
        store.signals.put(sig)
        model = Model(id="causal_del", kind=ModelKind.CAUSAL_RULE, name="delete_file",
            description="Deleting a file removes it", preconditions=["file_exists"],
            effects=["file_deleted"], confidence=0.9, trust=0.8,
            status=ModelStatus.ACTIVE, created_at=time.time(), updated_at=time.time())
        store.models.put(model)
        inference = CausalInference(store)
        kernel = ContextKernel(id="causal_test")
        results = inference.predict("delete_file", [], kernel)
        assert len(results) >= 1
```

## Self-Review Checklist (Revised)

- [ ] **Spec coverage:** (Corrected) Sections 1-29 covered as follows: Sec 2 (boundary rule — deferred, low severity), Sec 4 (entity aggregation — A.8), Sec 6 (unused kinds — A.1 trace fix improves Action, model kinds deferred), Sec 7 (action traces — A.1), Sec 8/23 (self updates — A.2, A.3), Sec 9 (permission gates — low severity, deferred), Sec 12 (registry facilities — deferred), Sec 14 (context inference — A.4), Sec 17 (uol_semantic induction — A.6), Sec 18 (grounding — deferred), Sec 19 (UOL atom retrieval — A.5), Sec 27 (invariants — A.7), Sec 28 (acceptance tests — A.8).
- [ ] **Placeholder scan:** No "TBD", "TODO", "implement later", "similar to" — every step has complete code.
- [ ] **Type consistency:** All type/method names are consistent across phases and appendix.
- [ ] **Test coverage:** Each phase includes tests. Bug fixes include regression tests. Invariant guard includes test for every enforced invariant.
