# Pragmatic Repetition And Affect — CEMM PoC Phase 3

Version: 1.0  
Status: implementation spec  
Based on: ERCA v2.0 architecture §13 (Pragmatic Repetition And Affect), §24 (Invariants), §25 (Acceptance Tests)

## 1. Goal

Add pragmatic-level repetition detection and session affect tracking to the CEMM pipeline. The system must detect repetition **by meaning, not exact text** — "you are dumb", "you are daft", and "you are a fool" share the same `semantic_cluster_key`.

This is NOT sentiment analysis or factual claim storage. It is session-level pragmatic state that decays with time and is used for response policy, cause tracing, and training signal generation.

## 2. Data Types

### 2.1 Signal — add observation_semantics field

```python
@dataclass
class ObservationSemantics:
    speech_act: str = "unknown"  # question, command, claim, correction, insult, complaint, gratitude, joke, unknown
    target_entity_id: str = ""
    semantic_cluster_key: str = ""
    stance: str = "unknown"      # positive, neutral, negative, mixed, unknown
    affect: dict = field(default_factory=lambda: {
        "valence": 0.0, "arousal": 0.0, "frustration": 0.0,
        "hostility": 0.0, "playfulness": 0.0,
    })
    repetition_group_id: str = ""
    repetition_count: int = 0
    cause_hypothesis_claim_ids: list[str] = field(default_factory=list)
    decay_half_life_ms: float = 900000.0  # 15 min default
    confidence: float = 0.0
```

Add as optional field on `Signal`:
```python
observation_semantics: ObservationSemantics | None = None
```

### 2.2 PragmaticState — new dataclass on ContextKernel

```python
@dataclass
class PragmaticState:
    current_stance: str = "unknown"  # cooperative, frustrated, hostile, playful, mischievous, unknown
    target_entity_id: str = ""
    frustration: float = 0.0
    hostility: float = 0.0
    playfulness: float = 0.0
    repetition_pressure: float = 0.0
    likely_cause_claim_ids: list[str] = field(default_factory=list)
    last_updated_signal_id: str = ""
    decay_half_life_ms: float = 900000.0
```

### 2.3 ContextKernel changes

- `UserState` gains `session_affect: PragmaticState`
- `ConversationState` gains `active_repetition_group_ids: list[str]` and `pragmatic_state: PragmaticState`
- `MemoryState` gains `active_repetition_group_ids: list[str]` (mirror for retrieval scope)

### 2.4 Default decay half-lives

| Metric | Half-life |
|---|---|
| Frustration | 15 min (900000 ms) |
| Hostility | 30 min (1800000 ms) |
| Playfulness | 10 min (600000 ms) |
| Repetition pressure | 5 min (300000 ms) |

Decay formula: `value(t) = value(now) * 0.5^(elapsed_ms / half_life_ms)`

## 3. SemanticClusterRegistry

Maps (speech_act, target, semantic pattern) → canonical `semantic_cluster_key`.

### 3.1 Built-in clusters (MVP)

| Pattern | speech_act | semantic_cluster_key |
|---|---|---|
| "dumb", "daft", "stupid", "fool", "idiot" | insult | `assistant_insult_low_competence` |
| "useless", "worthless", "broken" | insult | `assistant_insult_useless` |
| "hate", "cant stand" | complaint | `user_complaint_general` |
| "wrong", "incorrect", "lie" | correction | `user_correction_factual` |
| "thanks", "thank you", "helpful" | gratitude | `user_gratitude` |
| "great", "awesome", "love it" | claim | `user_praise` |

### 3.2 Extension

At runtime, the registry is a `dict[str, dict]` loaded from a JSON contract (`semantic_clusters.v1.json`). The built-in table above is the inline default. New clusters can be added as training artifacts (candidate models) but must be validated before promotion.

## 4. PragmaticInterpreter

Single function that enriches a `Signal` with `ObservationSemantics`:

```python
def interpret_signal(
    signal: Signal,
    kernel: ContextKernel,
    store: Store,
) -> ObservationSemantics | None
```

### 4.1 Flow

1. If `signal.source_type != USER` or `signal.kind != INPUT`: return None (only user input signals get pragmatic interpretation).
2. Run `SemanticClusterRegistry.match(signal.content)` against the cluster table — returns best-matching `(speech_act, semantic_cluster_key, confidence)`.
3. Determine `target_entity_id`: if the cluster targets assistant (insults, complaints about system), set to the self entity ID; otherwise empty.
4. Compute `affect` values from the cluster's predefined valence/arousal/frustration baselines (stored alongside cluster definitions).
5. **Repetition detection**: query `kernel.conversation.active_repetition_group_ids` for the matched `semantic_cluster_key`. If found, increment `repetition_count` (from PragmaticState's tracked counts). If not found, add to active set with count=1.
6. Compute `decay_half_life_ms` from PragmaticState default.
7. **Cause tracing**: if `speech_act` is insult/complaint and `repetition_count > 0`, query recent actions/synthesis verification failures from store. Attach matching claim IDs to `cause_hypothesis_claim_ids`.
8. Return `ObservationSemantics`.

### 4.2 Pipeline integration

In `Pipeline.run()`, after frame rules are applied (line 75), call `interpret_signal(signal, kernel, store)` and set `signal.observation_semantics`. Then update `kernel.user.session_affect` and `kernel.conversation.pragmatic_state` from the new semantics using the decay/merge function.

## 5. PragmaticState Updater

```python
def update_pragmatic_state(
    current: PragmaticState,
    semantics: ObservationSemantics,
    kernel: ContextKernel,
) -> PragmaticState
```

### 5.1 Steps

1. Apply exponential decay to all existing values using `kernel.time.now` as reference.
2. Merge the new `semantics.affect` values:
   - `frustration = max(0, min(1.0, decayed.frustration + affect.frustration))`
   - `hostility = max(0, min(1.0, decayed.hostility + affect.hostility))`
   - `playfulness = max(0, min(1.0, decayed.playfulness + affect.playfulness))`
3. Update `repetition_pressure` based on `repetition_count`:
   - `repetition_pressure = decayed.repetition_pressure + (0.15 * semantics.repetition_count)`
   - Clamp to `[0, 1.0]`
4. Set `current_stance` based on dominant affect:
   - `frustration > 0.5` → "frustrated"
   - `hostility > 0.5` → "hostile"
   - `playfulness > 0.5` → "playful"
   - Otherwise: "cooperative"
5. Merge `cause_hypothesis_claim_ids`.
6. Set `last_updated_signal_id`.

### 5.2 Session initialization

When a new session starts (no existing PragmaticState), initialize to `PragmaticState(current_stance="cooperative")`.

## 6. Response Policy

The `PragmaticState` is available to the ranker and synthesis router for response modulation:

| Stance | Response behavior |
|---|---|
| cooperative | normal response |
| frustrated | acknowledge briefly, reduce verbosity, repair likely cause |
| hostile | set boundary lightly, refocus on task |
| playful | stay calm, do not over-store, continue task if clear |

This is a policy concern — the ranker/synthesis can check `kernel.conversation.pragmatic_state.current_stance` and adjust accordingly. MVP can start with a no-op (log only).

## 7. Invariants (new, architecture §24)

The system must fail tests if:

1. `repeated paraphrased insults are treated as unrelated events` — two signals with the same `semantic_cluster_key` within a decay window must increment `repetition_count`.
2. `temporary frustration is persisted as stable user identity without evidence` — values in `PragmaticState` must never be written to the claims table or user_facts unless there is explicit permission and strong evidence.
3. `insults targeting assistant are stored as factual self claims` — signals with `speech_act=insult` targeting assistant must NOT create claims like "assistant is dumb". They only affect session-scoped PragmaticState.

## 8. Tests (architecture §25)

### 8.1 Pragmatic repetition

```
input sequence: "you are dumb" → "you are daft" → "you are a fool"
expected: same semantic_cluster_key = assistant_insult_low_competence
          repetition_count increases: 1 → 2 → 3
          target is self entity
          session frustration/hostility increases with each repetition
          no factual claim is stored
```

### 8.2 Pragmatic decay

```
event: repeated negative utterances stop
expected: after decay_half_life_ms, repetition_pressure drops by at least 50%
          after 2× half-life, frustration drops by at least 75%
```

### 8.3 Cause tracing

```
event: repeated complaint follows bad answer
expected: likely_cause_claim_ids points to recent failed action or synthesis verification claim
```

### 8.4 Non-insult pass-through

```
input: "What is my favorite database?"
expected: speech_act = question, observation_semantics confidence is low (<0.5)
          no change to frustration/hostility
```

## 9. Files to Create/Modify

| File | Action |
|---|---|
| `cemm/types/signal.py` | Add `ObservationSemantics` dataclass + field on `Signal` |
| `cemm/types/context_kernel.py` | Add `PragmaticState`, update `UserState`, `ConversationState` |
| `cemm/kernel/pragmatic_interpreter.py` | New — `interpret_signal()`, `update_pragmatic_state()` |
| `cemm/kernel/pragmatic_state_updater.py` | New — decay/merge logic (or inline in pragmatic_interpreter) |
| `cemm/kernel/semantic_clusters.py` | New — `SemanticClusterRegistry` with built-in clusters + contract load |
| `cemm/kernel/pipeline.py` | Wire `interpret_signal()` after frame rules |
| `tests/test_pragmatic.py` | New — 15+ tests for the 4 test scenarios above |
| `tests/invariants/test_pragmatic_invariants.py` | New — invariant tests for §7 |

## 10. Alignment With Training Architecture

The runtime pragmatic system and the LLM training pipeline are two tiers of the same cascade (training architecture §8).

### 10.1 Cascade tiers

| Tier | Component | Scope | Runs |
|---|---|---|---|
| Rules (cheapest) | `PragmaticInterpreter` + `SemanticClusterRegistry` | Every input signal | Always, in pipeline |
| Small model | LLM `pragmaticist` agent | High-ambiguity / low-confidence runtime outputs | Training jobs only |

### 10.2 Training inputs (§3) — runtime produces training examples

Training examples come from CEMM primitives — `Signal`, `Entity`, `Claim`, etc. The runtime `PragmaticInterpreter` adds `ObservationSemantics` to each input `Signal`. When confidence is low (<0.4) or the semantic_cluster_key is unknown, the pipeline can emit a `pragmatic_interpretation` training example containing the signal + current PragmaticState. This feeds directly into the training loop's `ingest_examples` step.

Not implemented in MVP — the hook point is captured for future wiring.

### 10.3 Training outputs (§4) — candidate models extend runtime

When the `pragmaticist` agent identifies a new semantic cluster pattern, it becomes a `Model(kind="frame_rule")` candidate entity. After validation and promotion (training architecture §11), the `SemanticClusterRegistry` loads it as a new cluster definition on next startup. The runtime extends without code changes.

### 10.4 Online updates (§10) — match frequency tracking

The training architecture defines safe online updates (`predicate alias counts`, `entity alias counts`). The pragmatic equivalent is `semantic_cluster_match_counts` — tracking how often each cluster fires. This feeds into:
- **Inductor trigger** (§11): when `same unrecognized pragmatic pattern repeats` above threshold, create candidate cluster
- **Confidence calibration**: clusters with high match counts get higher `confidence` in their `ObservationSemantics`

### 10.5 Synthetic PoC extension (§17)

The training architecture's synthetic benchmark uses structured events `{actor, action, object, outcome, timestamp}`. For pragmatic testing, extend the format with ground-truth pragmatic fields:

```text
{"actor":"user","action":"utterance","object":"assistant","content":"you are dumb",
 "speech_act":"insult","semantic_cluster_key":"assistant_insult_low_competence",
 "stance":"negative","affect":{"frustration":0.3,"hostility":0.2},
 "timestamp":1}
```

This allows running the synthetic benchmark against the `PragmaticInterpreter` and measuring classification accuracy, same as the causal PoC measures induction recall.

### 10.6 Training architecture doc updates

The `cemm_training_architecture.md` needs two additions (already applied in this session):

1. **§5 Task Types** — add `pragmatic_interpretation`
2. **§6 Agent Roles** — add row: `pragmaticist` | Detect speech act, target, affect, repetition, and likely cause

These already exist in `cemm_trainer.py` but were missing from the markdown tables.

## 11. Out of Scope

- LLM-based pragmatic interpretation (handled by the `cemm_trainer.py` agent pipeline, not the runtime)
- Persisting pragmatic state to the store (session-scoped only for MVP)
- Complex cause tracing beyond checking recent action claim IDs
- Response policy implementation beyond logging (synthesis/router changes deferred)
