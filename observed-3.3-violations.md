# Observed CEMM 3.3 Violations

**Date**: 2026-07-11  
**Source**: `AGENTS.md`, `ARCHITECTURE.md`, `cemm/newarch/3.3-upgrade-*` plans, live code review of `cemm/kernel`, `cemm/learning`, `cemm/response`.

---

## Executive Summary

The repository is in a **transitional 3.2/3.3 state**. The core `run_turn` pipeline in `semantic_kernel_runtime.py` implements the canonical 3.3 runtime sequence in a **shadow** form — most 3.3 components exist, are instantiated, and populate trace fields on `RuntimeCycleResult`, but the **authoritative v4.2 path still runs unchanged underneath**. The result is a system that looks 3.3-compliant on the surface but does not actually route meaning through the 3.3 authority spine.

| Category | Count |
|----------|-------|
| Forbidden-pattern violations (§5) | **8 distinct code locations** |
| Substrate-law violations (§3) | **6** |
| Shadow-only / unwired 3.3 components | **11** |
| Missing-but-critical 3.3 components | **5** |

---

## 1. Forbidden Pattern Violations (§5)

For each violation, the table gives the **first incorrect artifact** produced by the raw-text/regex check, the **authority it wrongly grants**, the **invariant violated**, and the **proposed correction at the earliest substrate**.

### V1 — `MeaningPerceptor._is_teaching_group` hardcodes English cues

- **File**: `cemm/kernel/meaning_perceptor.py`
- **Lines**: 1113-1119
- **Code**:
  ```python
  if "teach" in token_set:
      return True
  if token_set & {"means", "called", "refers", "equals"}:
      return True
  ```
- **First incorrect artifact**: `group.group_type` or `intent_key` is set to `teaching`.
- **Why it has authority**: `_intent_key_for_group` calls `_is_teaching_group` in its fallback heuristics at line 1074, directly routing a group to an operational intent key based on a surface token.
- **Invariant violated**: §3.1 (surface evidence cannot directly activate an action/state/intent), §3.9 (English-specific rules must stay in language packs).
- **Proposed correction**: Remove `_is_teaching_group`. The `ConstructionMatcher` already seeds `teaching_definition` and `teaching_offer` from `uol_semantics.json`. If `match_group` returns nothing, fall back to `group.group_type` or a minimal data-driven cue (`cue_set("teaching_cue")`) rather than a hardcoded English set.
- **Tests**: `test_meaning_perceptor.py` — assert that `"X means Y"`, `"teach"`, `"called"` are routed by `ConstructionMatcher` and that `_is_teaching_group` is no longer present.

### V2 — `MeaningPerceptor._is_capability_query` hardcodes modal/verb token subsets

- **File**: `cemm/kernel/meaning_perceptor.py`
- **Lines**: 1121-1126
- **Code**:
  ```python
  return bool(
      {"what", "can", "you"} <= token_set
      or {"can", "you"} <= token_set and token_set & {"do", "tell", "remember", "learn"}
  )
  ```
- **First incorrect artifact**: A capability question intent is returned without going through `ConstructionMatcher`.
- **Why it has authority**: Used by `_intent_key_for_group` fallback to return `capability_query`.
- **Invariant violated**: §3.1, §3.9.
- **Proposed correction**: Delete the method. `self_capability_query` is already in `uol_semantics.json` and handled by `ConstructionMatcher`.
- **Tests**: Assert `"what can you do"` and `"what can you tell me"` match `self_capability_query` via `ConstructionMatcher` only.

### V3 — `MeaningPerceptor._is_self_identity_query` hardcodes surface phrases

- **File**: `cemm/kernel/meaning_perceptor.py`
- **Lines**: 1128-1148
- **Code**:
  ```python
  if surface in {"who are you", "what are you", "tell me about yourself", "what is your name"}:
      return True
  if {"who", "are", "you"} <= token_set:
      return True
  ...
  ```
- **First incorrect artifact**: `self_identity_query` intent is emitted directly from surface phrase matching.
- **Why it has authority**: `_intent_key_for_group` calls it in fallback.
- **Invariant violated**: §3.1, §3.9. The `self_identity_query` aliases already exist in `uol_semantics.json:41`.
- **Proposed correction**: Remove `_is_self_identity_query` and `_is_self_knowledge_query`. `ConstructionMatcher.match_group` already covers these frame aliases.
- **Tests**: Assert `self_identity_query` and `self_knowledge_query` frame aliases match the correct intent.

### V4 — `MeaningPerceptor._initial_group_type` hardcodes answer token set

- **File**: `cemm/kernel/meaning_perceptor.py`
- **Line**: 650
- **Code**:
  ```python
  if token_set <= {"yes", "yeah", "yup", "no", "nah", "ok", "okay", "sure", "right"}:
      return "answer"
  ```
- **First incorrect artifact**: A group is classified as `answer` before any semantic construction is considered.
- **Why it has authority**: This is the first group classification; it determines which evidence atoms are emitted and the downstream intent.
- **Invariant violated**: §3.1, §3.9. `uol_semantics.json` already has `acknowledgment` (line 35) and `pure_acknowledgment_phrases` (lines 102-105).
- **Proposed correction**: Use `frame_alias_set("acknowledgment")` or `pure_acknowledgment_phrases` loaded from `uol_semantics.json`.
- **Tests**: Assert pure acknowledgment phrases produce `group_type == "answer"` via data-driven lookup.

### V5 — `EntityFactExtractor` uses English regex for relation extraction

- **File**: `cemm/kernel/entity_fact_extractor.py`
- **Lines**: 176-247
- **Code**: A list of 15 regex patterns of the form `r"^(\w[\w ]*?)\s+is\s+a\s+(?:type|kind)\s+of\s+(\w[\w ]*?)$"`.
- **First incorrect artifact**: `ExtractedClause` objects with `relation_key` and `subject`/`object` are created from surface text.
- **Why it has authority**: These clauses are downstream evidence for `MeaningGraphBuilder` or `PatchExtractor`.
- **Invariant violated**: §3.1, §3.5 (grammar-specific rules in language packs), §5 (raw-text regex in operational meaning).
- **Proposed correction**: Decommission `EntityFactExtractor` for 3.3. Replace it with a **ConstructionMatcher**-driven clause extraction: `uol_semantics.json` frame entries for `is_a`, `has_property`, `shape`, `function`, `source`, `edible`, `affordance` should produce construction matches, and the graph builder should build relation edges from those construction matches and parsed atoms, not regex captures. If a temporary fallback is needed, move the regex to a language pack, label it `fallback_clause_extractor`, and gate it with `confidence < 0.5` and explicit provenance.
- **Tests**: Failing test that `EntityFactExtractor` no longer contains `re.compile` calls for canonical relations.

### V6 — `TeachingInterpreter` parses raw text for teaching events

- **File**: `cemm/kernel/teaching_interpreter.py`
- **Lines**: 97-144
- **Code**:
  ```python
  lower = text.lower().strip()
  words = [w.strip(".,!?;:\"'()[]{}\") for w in lower.split()]
  if "means" in lower:
      ...
  if "when i say" in lower:
      ...
  ```
- **First incorrect artifact**: `TeachingEvent` list is emitted from raw surface string checks.
- **Why it has authority**: `TeachingInterpreter` is called by `MeaningGraphBuilder` or `SemanticCPU` to identify teaching turns.
- **Invariant violated**: §3.1, §3.5, §5. Surface patterns like `"X means Y"` should be recognized by `ConstructionMatcher` and turned into construction matches, not parsed with raw text splitting.
- **Proposed correction**: Replace `TeachingInterpreter` with a `ConstructionMatcher`-driven `TeachingInterpreter` that receives `MeaningPerceptPacket` / `UOLGraph` and checks for `teaching_definition`, `teaching_offer`, `command_alias_teaching` construction matches. The `interpret(text: str)` API should be deprecated or made to call the perceptor first.
- **Tests**: Failing test that `TeachingInterpreter.interpret()` no longer calls `text.lower().split()` or `in` on raw text.

### V7 — `MeaningGraphBuilder._extract_remember_relation_observations` parses raw "remember" text

- **File**: `cemm/kernel/meaning_graph_builder.py`
- **Lines**: 1601-1693
- **Code**:
  ```python
  import re
  tokens = re.findall(r"[^\W_]+", group.surface.lower())
  if "remember" not in tokens:
      continue
  rem_index = tokens.index("remember")
  after_rem = tokens[rem_index + 1:]
  ...
  ```
- **First incorrect artifact**: `StructuralObservation` of type `relation_candidate` is created from regex-tokenized surface text.
- **Why it has authority**: `MeaningGraphBuilder` adds this observation to `UOLGraph`, which is then used by the `RelationFrameCompiler` and patch extractor.
- **Invariant violated**: §3.1, §3.5, §5. The `command_remember` frame is already in `uol_semantics.json` (line 9) and the `ConstructionMatcher` should produce a `command` construction match for "remember" groups. The embedded relation (`"I like coffee"`) should be parsed by the normal perception/graph-building pipeline (predicate verb, subject, object atoms), not by a special surface regex in the graph builder.
- **Proposed correction**: Remove `_extract_remember_relation_observations`. The perceptor should emit a `command` atom for "remember" and the normal graph builder should produce `relation_candidate` observations from the embedded `like`/`has_property` predicate, speaker, and object atoms. Add a `command_remember` construction that supports a `target` port holding the embedded relation.
- **Tests**: Failing test that `MeaningGraphBuilder` no longer contains `re.findall` or `"remember"` token checks.

### V8 — `OutputStateUpdater._detect_question_type` reparses realized output text

- **File**: `cemm/kernel/output_state_updater.py`
- **Lines**: 60-96
- **Code**:
  ```python
  for q_type, patterns in _QUESTION_PATTERNS.items():
      for pattern in patterns:
          if re.search(pattern, text_lower):
              ...
  ```
- **First incorrect artifact**: `pending_question_type` and `expected_answer_type` are set from regex on the assistant's output string.
- **Why it has authority**: This updates `kernel.conversation.pending_question_*`, which affects the next turn's behavior.
- **Invariant violated**: §3.10 (NLG is downstream and blind), §5 (response output reparsing to discover the output act).
- **Proposed correction**: `OutputStateUpdater` should consume `ResponseBundle` and `ResponseContract` from the operational pipeline. `ResponseContract.expected_output_acts` (already produced by `OperationalContractCompiler._expected_acts`) should carry the output act type (`question`, `confirm`, `inform`, etc.). The response realizer should produce act-tagged output. `OutputStateUpdater` then reads `expected_output_acts[0]` and `response_bundle.moves` to determine pending question type, not regex on text.
- **Tests**: `test_output_state_updater.py` — assert `"How are you?"` with `expected_output_acts=["question"]` produces `pending_question_type="social_checkin"` without regex; assert `OutputStateUpdater` does not call `re.search` on output text.

---

## 2. Substrate Law Violations

### S1 — Surface evidence directly activates operational meaning (§3.1)

- **Location**: `cemm/kernel/operational_meaning_compiler.py:208` — `_classify_frame`.
- **Trace**: `instruction.instruction_kind` (`"assertion"`, `"query"`, `"command"`, etc.) + `intent_keys` derived from atom keys (`has_property`, `likes`, `knows`) directly select `frame_type` (`profile_assertion`, `concept_definition_query`, `command`, etc.).
- **Why wrong**: `instruction_kind` is a surface-level label from the `SemanticProgram` (itself produced by the perceptor's group classification). `intent_keys` are atom keys from the graph. Neither has been validated by `PredicateActivationResolver` or scoped through typed ports.
- **Proposed correction**: `OperationalMeaningCompiler` should compile `OperationalMeaningFrame` candidates from the graph. `PredicateActivationResolver` (or a new `PredicateActivationResolver`) must be the gate: it checks typed ports, scope, and permission, and produces a set of **activated** frame IDs. `OperationalMeaningCompiler` then only compiles activated frames. Today `PredicateActivationResolver` is shadow-only and is called after operational frames are already compiled (V-M4).

### S2 — Unknown meaning does not block execution (§3.2)

- **Location**: `cemm/kernel/semantic_kernel_runtime.py:329` and `cemm/learning/semantic_gap_detector.py:122-142`.
- **Trace**: `SemanticGapDetector.classify_blocking(gaps, set())` is called with an empty `selected_branch_ids` set. Because no branch IDs match, **no gap is ever blocking**. The runtime continues to compile and execute operational meaning as if the gap did not exist.
- **Why wrong**: Gaps are typed but not wired into the obligation graph. The `LearningEpisode` is created but its `target_gap_ids` are not used to block the contract.
- **Proposed correction**: `InterpretationResolver` must produce selected branch IDs (Phase 4). `SemanticGapDetector.classify_blocking` must be called with those branch IDs. If a blocking gap exists, `OperationalContractCompiler` must produce a `clarify`/`ask` contract with `response_mode="clarify"` and the `learning_question` must be the primary response. The `ResponseFormationEngine` must consume `learning_questions`.

### S3 — Candidate and activated meaning are the same type (§3.3)

- **Location**: `cemm/types/operational_meaning.py` and `cemm/kernel/operational_meaning_compiler.py`.
- **Trace**: `OperationalMeaningFrame` is used for both candidate frames (all `compile()` outputs) and selected frames (after `arbitrate()`). `arbitrate()` returns `MeaningArbitrationResult.selected_frame_ids` but the selected frames are just a subset of the same objects; no new type distinguishes candidate vs. activated.
- **Proposed correction**: Introduce `CandidateOperationalMeaningFrame` and `ActivatedOperationalMeaningFrame` (or a `status` field that is not mutable in place). `PredicateActivationResolver` returns `ActivatedOperationalMeaningFrame` objects with typed-port validation provenance. `OperationalMeaningCompiler` compiles from activated frames only.

### S4 — No authoritative transmutation authorizer (§3.4, §3.7)

- **Location**: `cemm/kernel/state_transmutation_compiler.py`.
- **Trace**: `StateTransmutationCompiler.compile` directly produces `StateTransmutationFrame` objects with `authority` set by frame type (`user_asserted`, `policy_authorized`, etc.). There is no separate `TransmutationAuthorizer` component.
- **Why wrong**: The authority for state transitions is distributed across `StateTransmutationCompiler` and the frame type heuristics. The `authority` string is derived from surface classification, not from a permission check.
- **Proposed correction**: Add `TransmutationAuthorizer` in `cemm/kernel/transmutation_authorizer.py`. It receives `StateTransmutationFrame` candidates, `StateOccupancyFrame` prior state, and the `ObligationContract`, and returns `authorized`/`quarantined`/`rejected` transmutations with a permission reason. The `StateTransmutationCompiler` should only compile candidates; the authorizer applies permission.

### S5 — State delta is not transactional (§3.7)

- **Location**: `cemm/kernel/semantic_kernel_runtime.py:461-475`.
- **Trace**: `StateDeltaCompiler` → `StateTransmutationCompiler` produces transmutations. `SafetyFrameDetector` consumes them. `PatchExtractor` and `PatchValidator` are called. But the transmutations themselves are not applied through a transaction; if commit fails partway, there is no rollback of session state.
- **Proposed correction**: `ContractExecutor` should execute the `state` step transactionally: `proposed` → `authorized` → `executing` → `succeeded`/`failed` → `committed`/`rolled_back`. `ExecutionLedger` entries for `state` operations must be committed before durable effects are considered final. The `ContractExecutor` default executor must be replaced with a real `StateExecutor` that calls `state_transmutations.apply()` and writes rollback entries.

### S6 — Response NLG is not blind (§3.10)

- **Location**: `cemm/kernel/output_state_updater.py` (V8).
- **Trace**: See V8 above.

---

## 3. Shadow-Only / Unwired 3.3 Components

A component is **shadow** if it is instantiated, produces trace output, but its output is not consumed by the authoritative execution path.

| Component | Location | Shadow evidence | Why it does not drive behavior |
|-----------|----------|-----------------|--------------------------------|
| `SemanticGapDetector` | `cemm/learning/semantic_gap_detector.py` | `result.semantic_gaps`, `result.learning_questions` | `classify_blocking` called with empty selected branch IDs; questions not consumed by `ResponseFormationEngine`. |
| `LearningEpisodeManager` | `cemm/learning/learning_episode_manager.py` | `result.active_learning_episodes` | Episodes created but no answer assimilation loop in `run_turn`. |
| `LearningQuestionPlanner` | `cemm/learning/learning_question_planner.py` | `result.learning_questions` | Output not routed to response. |
| `InterpretationResolver` / `InterpretationLattice` | `cemm/kernel/interpretation_resolver.py`, `interpretation_lattice.py` | `result.interpretation_resolution` | Branches are one-per-group, no alternatives, and result is not used by `OperationalMeaningCompiler` or `SemanticGapDetector`. |
| `EntityGroundingResolver` | `cemm/kernel/entity_grounding_resolver.py` | `result.entity_groundings` | Groundings are plain dicts not consumed by downstream components. |
| `PredicateActivationResolver` | `cemm/kernel/predicate_activation_resolver.py` | `result.predicate_activations` | Called after operational frames are already compiled; no typed-port validation. |
| `ObligationGraphBuilder` | `cemm/kernel/obligation_graph_builder.py` | `result.obligation_graph` | Built after contract compilation; `TurnExecutionPlanner` and `ContractExecutor` default are no-ops. |
| `ContractExecutor` | `cemm/kernel/contract_executor.py` | `result.execution_ledger` | Default executor records `PROPOSED` only; does not execute query/write/state/reaction. |
| `LearningUseObserver` | `cemm/learning/learning_use_observer.py` | `result.learning_use_outcomes` | Not fed back into evidence ledger or knowledge strength. |
| `SessionLearningOverlay` | `cemm/learning/session_learning_overlay.py` | — | Exists but `from_dict` returns empty; not wired into lookup order. |
| `LearningAnswerAssimilator` | `cemm/learning/learning_answer_assimilator.py` | — | Not called in `run_turn`; acquisition spine incomplete. |

---

## 4. Missing Critical 3.3 Components

| Component | Requirement | Impact if missing |
|-----------|-------------|-------------------|
| `TransmutationAuthorizer` | §3.4, §3.7 | State changes have no permission gate; safety and policy checks are not separate from compilation. |
| `GraphPatchValidator` with contradiction/scope checks | §3.6 | Durable mutations are not validated as graph patches before commit. |
| `Consolidation loop` (promote/revise/split/quarantine/retire) | §3.8, §7 | Learned structures never get promoted or revised. |
| `Learning answer assimilation loop` | §2, §7 | Acquisition spine cannot close; user answers don't update hypotheses. |
| `Response act tagging` | §3.10 | `OutputStateUpdater` cannot know the output act without reparsing text. |

---

## 5. Proposed Fix Order (Upstream → Downstream)

Following AGENTS.md §4 (trace first, fix earliest substrate), the order is:

1. **Phase A — Perception substrate cleanup**
   - Remove hardcoded English cue methods from `MeaningPerceptor` (V1-V4).
   - Ensure `ConstructionMatcher` covers all removed cases (add missing frame entries to `uol_semantics.json` if needed).
   - Add `pure_acknowledgment_phrases` / `frame_alias_set` data-driven accessors.

2. **Phase B — Graph builder surface extraction**
   - Remove `MeaningGraphBuilder._extract_remember_relation_observations` (V7).
   - Add `command_remember` construction with embedded-relation port.
   - Verify `"remember I like coffee"` produces a `command` atom + normal `likes` relation observation.

3. **Phase C — Teaching interpreter**
   - Refactor `TeachingInterpreter` to consume `MeaningPerceptPacket`/`UOLGraph` and `ConstructionMatch`es (V6).
   - Deprecate `interpret(text: str)` or make it delegate to perceptor.

4. **Phase D — Entity fact extraction**
   - Replace `EntityFactExtractor` regex clauses with `ConstructionMatcher` entries (V5).
   - This is the largest change; consider a temporary language-pack fallback with explicit provenance and confidence.

5. **Phase E — Authority separation**
   - Implement `PredicateActivationResolver` as a real gate (S3).
   - Implement `TransmutationAuthorizer` (S4).
   - Wire `InterpretationResolver` selected branches into `classify_blocking` and contract compilation (S2).

6. **Phase F — NLG blindness**
   - Add output act tags to `ResponseBundle` and `ResponseContract` (V8).
   - Rewrite `OutputStateUpdater` to consume acts, not regex.

7. **Phase G — Execution spine**
   - Replace `ContractExecutor` default executor with real step dispatchers.
   - Make `ObligationGraph` the driver of execution ordering.

---

## 6. Test Strategy

For each phase, add a **regression test** that fails before the fix and passes after:

- `test_forbidden_pattern_violations.py` — structural tests that grep for `re.compile` / `re.findall` / hardcoded English sets in `MeaningPerceptor`, `MeaningGraphBuilder`, `TeachingInterpreter`, `OutputStateUpdater`.
- `test_construction_match_authority.py` — golden-file comparison of `intent_key` for canonical inputs before/after removing hardcoded methods.
- `test_output_state_updater_acts.py` — assert `OutputStateUpdater` derives question type from `ResponseBundle.moves` and `expected_output_acts`, not `re.search`.
- `test_transmutation_authorization.py` — assert a high-risk state delta is rejected/quarantined by `TransmutationAuthorizer`.
- `test_blocking_gap.py` — assert an unknown lexeme in a selected branch blocks the contract and produces a learning question.

---

*This document is a live trace. Update it as fixes are applied and mark resolved items with the commit/refactor that addressed them.*
