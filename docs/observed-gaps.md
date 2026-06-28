# Observed Gaps & Bugs — ERCA v2.0 Implementation vs Architecture

> Generated: 2026-06-28
> Architecture version: 2.0
> Reference: `cemm/architecture.md` (updated, 1886 lines)
> Implementation: `cemm/` package (pure Python, SQLite-backed)

---

## Part I: Architecture Gaps by Section

### Sec 2: Primitive Units — Boundary Rule Not Enforced
- **Rule**: "If a concept can be derived from the six primitives within budget, it must remain a view or packet. Do not add new persistent primitives without removing or merging an existing one."
- **Status**: No code enforces this. Nothing prevents adding new primitive tables beyond the six.
- **Severity**: Low (design hygiene, no runtime cost)

---

### Sec 3: Signal — Missing Fields & Unenforced Rules

| Gap | Detail | Severity |
|-----|--------|----------|
| `uol_atoms: UOLAtom[]` not in `ObservationSemantics` | Field missing. New in this arch version. | **High** |
| `UOLAtom` union type not defined | `EntityRefUOLAtom`, `ProcessUOLAtom`, `StateUOLAtom` types do not exist | **High** |
| `observation_semantics` never persisted | Schema has no columns for it; set in-memory only | **High** |
| Append-only rule not enforced | `INSERT OR REPLACE` can overwrite existing signals | Low |
| "Every claim must cite at least one signal" | No runtime check — `evidence_signal_ids` is an unvalidated `list[str]` | Medium |
| "Every memory mutation must originate from a signal" | No runtime check | Medium |
| ObservationSemantics fields mismatch arch | `speech_act` is `str` not `Literal` union; `stance` is `str` not `Literal` | Low |

---

### Sec 4: Entity — Missing Meaning Aggregation
- **Arch says**: "Meaning is represented by entity type + aliases + claims about the entity + models involving the entity + actions involving the entity + trusted evidence"
- **Status**: `EntityResolver` does name/alias lookup only. No method to aggregate claims, models, or actions about an entity. No "entity profile" retrieval.
- **Severity**: Medium

---

### Sec 5: Claim — Type Fidelity Bug
- **`object_value` type erasure**: SQLite stores as `TEXT`, reads back as `str | None`. Boolean `False` becomes string `"False"`, integer `42` becomes `"42"`. The arch specifies `object_value?: string | number | boolean | null`.
- **Severity**: Medium

---

### Sec 6: Model — Unused Kinds

| Kind Defined In Arch | Used In Code? | Severity |
|---------------------|---------------|----------|
| `uol_semantic` | **No** (new this version) | **High** |
| `context_rule` | Created in enum, never queried or applied | Medium |
| `ranking_rule` | Created in enum, never queried or applied | Medium |
| `frame_rule` | Created in enum, never queried (FrameEngine uses hardcoded logic) | Medium |

---

### Sec 7: Action — Fake Traces

| Gap | Detail | Severity |
|-----|--------|----------|
| Traces have hardcoded values | `AnswerOperator` (answer.py:38-46) creates Trace with `action_id=""`, no causal/frame info, hardcoded `cost_ms=1.0` | **High** |
| `Action.result_signal_id` rarely set | Most operators create a result signal but don't link it back to the Action | Medium |
| Action scoring never called | `score_action()` exists but is never invoked by the pipeline | Medium |
| `CALL_TOOL` action kind | Defined in enum, no operator implements it | Low |

---

### Sec 8: Self — Frozen State

| Gap | Detail | Severity |
|-----|--------|----------|
| Self state loaded once, never updated | `Pipeline.run()` loads `self_state` once, never writes back | **High** |
| `historical_arc` nesting not implemented | `milestone_signal_ids`, `active_project_ids`, `learned_model_ids` are flat fields, not grouped under `historical_arc` | Low |
| Reflection doesn't update self | `ReflectOperator` reads `SelfState` but never persists changes | Medium |
| `OnlineLearner.update_self_state` never called | Exists but is dead code | Medium |
| `recent_error_rate`, `uncertainty`, `coherence` never mutated | Fields are initialized but never changed by pipeline events | Medium |

---

### Sec 9: Permission — Gates Not Implemented
- **Arch defines 8 gates**: store, retrieval, ranking, response, execution, reflection, model-creation
- **Status**: Individual operators check `may_execute`/`may_store`, but there is no pipeline-level gate infrastructure. No centralized permission checking.
- **`SourceTrustEntry` doesn't match arch's `SourceTrust`**: Arch has `observations`, `confirmations`, `corrections`, `contradictions`, `updated_at`. Implementation has `evidence_count`, `success_count`, `failure_count`, `last_observed_at` — functionally similar but structurally different.
- **Severity**: Medium

---

### Sec 10: Context Kernel — Missing Fields

| Field | Arch Spec | Implementation | Severity |
|-------|-----------|---------------|----------|
| `users: UserState[]` | New in this version | **Missing** | **High** |
| `self: SelfView` | Separate type with specific fields | Uses `self_state: SelfState \| None` directly | Medium |
| `WorldState.assistant_locale` | `{ country?, region?, city?, timezone? }` | Missing | Low |
| `WorldState.world_event_claim_ids` | `string[]` | Missing | Low |
| `WorldState.active_context_rule_model_ids` | `string[]` | Missing | Low |
| `UserState.locale` | `{ country?, region?, city?, timezone? }` | Missing | Low |
| `ConversationState.first_user_signal_id` | `string?` | Missing | Medium |
| `ConversationState.inferred_context_claim_ids` | `string[]` | Missing | Medium |
| `TimeState.session_elapsed_ms` | `number` | Missing | Medium |
| `TimeState.time_since_last_user_signal_ms` | `number?` | Missing | Low |
| `TimeState.time_since_last_assistant_action_ms` | `number?` | Missing | Low |
| `PragmaticState.active_quality_atom_keys` | `string[]` (new) | **Missing** | **High** |
| `PragmaticState.active_process_atom_keys` | `string[]` (new) | **Missing** | **High** |
| `ConversationState.turn_index` | Should increment | Always `0` (hardcoded in `from_signal`) | Medium |

---

### Sec 11: Memory Architecture — 12 Views Not Built
- **Arch defines 12 memory views**: Working, Episodic, Semantic, Causal, Procedural, Registry, UOL, Frame, Context, Self, Trust, Permission
- **Status**: Zero are built as query interfaces. All retrieval goes through `StructuralRetriever` which does flat SQL lookups. The arch says "views over primitives" and "no separate store unless performance requires" — even as logical views, these don't exist.
- **UOL memory** is new in this version.
- **Severity**: High

---

### Sec 12: Registry — Unused Facilities

| Gap | Detail | Severity |
|-----|--------|----------|
| `uol_semantic` registry entries | New kind, no code registers or queries them | **High** |
| Frame rules as `Model(kind="frame_rule")` | Never loaded or applied — `FrameEngine` has hardcoded temporal logic only | Medium |
| "map action intents to operator models" | Not implemented — dispatch is manual `if/elif` in `__main__.py:117-134` | Medium |
| "validate required slots" | `OperatorSpec.required_slots` defined but never checked | Medium |
| "prevent duplicate learned structures" | Not enforced | Medium |

---

### Sec 13: UOL Semantic Layer — ENTIRELY NEW, NOT IMPLEMENTED

This entire section is **new in the updated architecture** and has zero implementation.

| Component | Status |
|-----------|--------|
| `UOLAtom` types (`EntityRefUOLAtom`, `ProcessUOLAtom`, `StateUOLAtom`) | Not defined |
| `ObservationSemantics.uol_atoms` field | Missing |
| `Model(kind = "uol_semantic")` registry entries | Not created |
| UOL mapping runtime (surface form → atom) | Not implemented |
| Training task `uol_mapping` | Not implemented |
| UOL memory view | Not implemented |

**Severity: High** — blocks the new architecture requirement.

---

### Sec 14: Context Inference — Mostly Unimplemented

| Gap | Detail | Severity |
|-----|--------|----------|
| `ContextInference` runtime packet | Not created | **High** |
| Context rules (`Model(kind="context_rule")`) | No code loads or applies them | **High** |
| First-utterance rules | No detection code exists | Medium |
| Location ambiguity detection | Not implemented | Medium |
| "train for context_inference" | No training task | Medium |

---

### Sec 15: Pragmatic Repetition And Affect — 2 Bugs

| Bug/Gap | Detail | Severity |
|---------|--------|----------|
| Stale substring matching | `SemanticClusterRegistry.match()` uses `in` — "dumb" matches "dumbfound" | Medium |
| `last_updated_signal_id` misassigned | `update_pragmatic_state` sets to `semantics.repetition_group_id` instead of signal ID | Medium |
| Cause tracing is rudimentary | Only checks last 5 `working_claim_ids` for causal domain failures, ignores action history | Medium |
| Response policy (frustration→acknowledge, etc.) | Not implemented as actionable policy | Medium |

---

### Sec 16: Causal World Model — 1 Bug

| Bug/Gap | Detail | Severity |
|---------|--------|----------|
| `_preconditions_match` overly permissive | Empty preconditions → all models match everything. Substring matching on model name (causal/inference.py:76-85) | **High** |
| Closure limits `causal horizon`, `confidence floor`, `cycle detection` | Not implemented in transitive_closure | Medium |

---

### Sec 17: Structural Learning — Untriggered

| Gap | Detail | Severity |
|-----|--------|----------|
| Induction **never triggered** in pipeline | `Inductor.maybe_induct()` only called from tests | **High** |
| Candidate model testing against past data | Not implemented — `promote()` checks thresholds but doesn't test against historical signals/claims | Medium |
| `uol_semantic` not creatable by Inductor | New model kind — Inductor doesn't handle it | **High** |

---

### Sec 18: Embodied and Experiential Grounding

| Gap | Detail | Severity |
|-----|--------|----------|
| No grounding mechanism | No operator produces `tool_result` signals; no feedback loop from outcomes to claims | Medium |
| Signal kinds `TOOL_RESULT`, `ENVIRONMENT`, `FEEDBACK` exist but no code creates them | Dead enum values | Low |

---

### Sec 19: Retrieval — Missing UOL Atom Key & Vector Expansion

| Gap | Detail | Severity |
|-----|--------|----------|
| `UOL atom key` in primary retrieval keys | Not implemented (new) | **High** |
| Vector/geometric expansion | `vectors_optional` table exists, nothing writes or queries it | Low |
| "forbidden vector use" rules | Not enforced (no vector system to enforce against) | Low |

---

### Sec 20: Ranking And Confidence — 2 Bugs

| Bug | Detail | Severity |
|-----|--------|----------|
| `score_claim` zeroes out on `salience=0` | Multiplies `relevance * trust * confidence * salience * recency`. If `salience=0.0` (default), score = 0 regardless of other factors. `confidence/scoring.py:31-37` | **High** |
| `update_log_odds` ignores `base_rate` | Takes `base_rate` parameter but never passes to `prior_log_odds(base_rate)`. `confidence/log_odds.py:48-67` | Medium |

---

### Sec 21: Recursive Runtime — Pipeline Is NOT Recursive

| Gap | Detail | Severity |
|-----|--------|----------|
| Internal signals never re-enter pipeline | `Pipeline.run()` outputs result and stops. Signals (memory_update, simulation_result, reflection) stored to DB but never re-fed | **Critical** |
| "maybe_recurse" step | Not implemented | **High** |
| Reflection triggers | Not implemented — `ReflectOperator` is never called automatically | **High** |
| "learn" step | Not implemented — `OnlineLearner` never invoked | **High** |
| Salience threshold check for recursion | Not implemented | Medium |

---

### Sec 22: Typed Operators — Missing Call Tool

| Gap | Detail | Severity |
|-----|--------|----------|
| `CALL_TOOL` action kind | Defined in enum, no operator | Low |
| Operator contract not enforced | Rule says "may only use ContextKernel, input signal, selected claims/models, SelfView" — no runtime check | Medium |

---

### Sec 23: Synthesis And Learning Runtime — Bypassed

| Bug/Gap | Detail | Severity |
|---------|--------|----------|
| **AnswerOperator bypasses synthesis verification** | `answer.py:14-53` generates output from claims without calling `SynthesisVerifier`. Arch invariant: "answer bypasses synthesis verification" is a violation | **High** |
| Neural strategy not implemented | Only template and extractive exist | Low |
| `OnlineLearner.record_outcome` never called | Dead code | **High** |
| `OnlineLearner.update_claim_confidence` never called | Dead code | Medium |
| Self.meta_memory never updated on remember | `RememberOperator` doesn't call `OnlineLearner.update_self_state` | Medium |
| Self.epistemic never updated on update_claim | `UpdateClaimOperator` doesn't update `Self.epistemic` | Medium |

---

### Sec 24: Storage — Index Gap

| Gap | Detail | Severity |
|-----|--------|----------|
| Missing composite index | Arch asks for `models(kind, registry_key, status)` but schema has separate `idx_models_kind_status` and `idx_models_registry_key` | Low |
| Hot cache | Not implemented (arch says implement if profiling proves need) | Low |

---

### Sec 25: Bloat Control
- Design rules only. No specific implementation gaps.
- **Severity**: N/A

---

### Sec 26: MVP Scope — Missing Items

| MVP Item | Implemented? | Severity |
|----------|-------------|----------|
| UOL mapping | **No** (new in this version) | **High** |
| Context inference | No | **High** |
| Recursive internal signals | Signals created but never re-enter pipeline | **High** |
| Background Inductor trigger | No | **High** |
| Self state update through reflection | No | **High** |
| Permission gates | Partial (per-op checks, no pipeline gates) | Medium |

---

### Sec 27: Invariants

| Gap | Detail | Severity |
|-----|--------|----------|
| **Zero runtime invariant enforcement** | 18 invariant test classes exist, but no production code enforces them | **High** |
| New invariant: "language-specific grammar labels bypass UOL process/state registry" | Not testable — UOL not implemented | **High** |
| "claim has no evidence signal" | `Claim` type has `evidence_signal_ids: list[str]` default `[]` — no required enforcement | Medium |
| "model has no evidence signal" | Same as above | Medium |
| "answer bypasses synthesis verification" | Violated by `AnswerOperator` | **High** |

---

### Sec 28: Acceptance Tests
| Test | Implemented? | Severity |
|------|-------------|----------|
| UOL mapping (new) | **No** | **High** |
| "Morning" scheduling context | No | Medium |
| "Good morning" first-utterance | No | Medium |
| "Fix this now" urgency detection | No | Medium |
| Weather location ambiguity | No | Medium |
| Causal model simulation | Test exists but is minimal | Medium |
| Frame validity (supersession) | Partially tested | Medium |

---

## Part II: Bug Inventory

| # | Bug | File | Severity |
|---|-----|------|----------|
| B1 | `score_claim` zeroes out when `salience=0` | `confidence/scoring.py:31-37` | **High** |
| B2 | `update_log_odds` ignores `base_rate` parameter | `confidence/log_odds.py:48-67` | Medium |
| B3 | Claim `object_value` type erasure (all values → `str \| None`) | `store/claim_store.py:59` | Medium |
| B4 | Observation semantics never persisted to DB | `store/signal_store.py` (no schema columns) | **High** |
| B5 | Pragmatic `last_updated_signal_id` set to wrong value (repetition_group_id, not signal id) | `kernel/pragmatic_interpreter.py:104` | Medium |
| B6 | `Pipeline._check_budget` compares signal count against claim budget | `kernel/pipeline.py:101-106` | Medium |
| B7 | `CausalInference._preconditions_match` matches everything when preconditions empty | `causal/inference.py:76-85` | **High** |
| B8 | `ConversationState.turn_index` never increments | `kernel/context_kernel_builder.py:57` | Medium |
| B9 | `AnswerOperator` never calls `SynthesisVerifier` | `operators/answer.py:14-53` | **High** |
| B10 | `OnlineLearner.update_claim_confidence` modifies stale Claim in-memory before `put` — potential lost update | `learning/online.py:35-48` | Medium |
| B11 | SemanticCluster substring matching — false positives ("dumb" in "dumbfound") | `kernel/semantic_clusters.py:53` | Low |

---

## Part III: Summary by Severity

### Critical (1)
1. **Pipeline is not recursive** — internal signals never re-enter, breaking the core architectural promise of Sec 21

### High (14)
1. UOL Semantic Layer entirely missing (Sec 13 — new)
2. `uol_semantic` ModelKind, UOLAtom types, `uol_atoms` field not implemented
3. `users: UserState[]` missing from ContextKernel
4. `active_quality_atom_keys`, `active_process_atom_keys` missing from PragmaticState
5. Learning never triggered — `OnlineLearner` and `Inductor` are dead code
6. Self state frozen — never updated by pipeline
7. Context inference missing entirely (Sec 14)
8. Traces are fake — hardcoded values
9. `score_claim` zeroes on `salience=0`
10. `AnswerOperator` bypasses synthesis verification
11. `_preconditions_match` too loose — matches everything on empty preconditions
12. 12 memory views not built as query interfaces
13. Observation semantics not persisted
14. Zero runtime invariant enforcement

### Medium (12)
- Claim evidence not enforced
- Memory mutation signal origin not enforced
- Entity meaning aggregation missing
- Claim type fidelity issue
- Frame rules/context rules never loaded from registry
- Cause tracing rudimentary
- Candidate testing against history missing
- Grounding mechanism absent
- Permission gates not structural
- Slot validation not implemented
- Induction not wired
- Several ContextKernel sub-fields missing
