# CEMM Gap Analysis — Merged Final Document

**Date:** 2026-01-17  
**Status:** Final (merged with `2026-06-30-static-coding-gap-analysis.md`)  
**Purpose:** Identify and prioritize gaps between original architecture goals and current implementation

---

## 1. Executive Summary

The original architecture specifies a **meaning-first system** that operates on typed semantic primitives (UOL atoms, SemanticEventGraph, SemanticAnswerGraph) rather than raw text or embeddings. The goal is a higher-level LLM—operating on meaning atoms instead of matrices.

**Current state:** The system has strong structural scaffolding but executes a **partial, shallow version** of the intended loop. Conversational tests expose this gap not because the system is "untrained," but because the runtime does not yet fully exercise the architecture's meaning-first design.

**Root cause:** The implementation has focused on building the component layer (primitives, types, stores, operators) but has not yet completed the **semantic execution path** that makes those components work together at the meaning level.

**Key finding:** This is not primarily a "needs more training data" problem. It is an **architecture-execution gap** that must be closed before generic training can be effective.

---

## 2. Architecture Goals vs Current Reality

### 2.1 The Target Loop (from architecture.md)

```
Signal + ContextKernel + Memory
-> SemanticEventGraph
-> typed latent computation
-> SemanticAnswerGraph or Action
-> optional text realization
```

With the core loop:
```
Observe
-> Contextualize
-> Interpret
-> Ground
-> Retrieve
-> Infer
-> Decide
-> Realize
-> Update
-> Learn
```

### 2.2 What Actually Runs

The runtime in `cemm/kernel/pipeline.py` executes:

1. Signal creation
2. ContextKernel building
3. SemanticEventGraph generation (via SemanticInterpreter)
4. Pragmatic interpretation (via interpret_signal)
5. Grounding
6. Context inference
7. Retrieval (kernel + graph)
8. Ranking (claims + models)
9. Memory packet creation

**Gap:** Steps 3, 6, and the answer composition step are **semantically thin** relative to what the architecture intends.

### 2.3 Core Law Adherence

| Architecture Principle | Current Adherence |
|---|---|
| context before interpretation | Partial — context inference exists but is mostly heuristic keyword/regex |
| structure before vectors | Partial — SemanticEventGraph exists structurally but is shallow |
| semantic graph before latent compression | Partial — graph is built but not used as primary retrieval key |
| claims before generation | Partial — claims are retrieved but answer composition is thin |
| models before simulation | Partial — models are ranked but simulation is minimal |
| permission before ranking | Implemented |
| ranking before action | Implemented |
| trace before mutation | Implemented |
| signals before recursion | Implemented |
| learning after outcome | Partial — training pipeline exists but is under-scoped |

---

## 3. What's Working

### 3.1 Strong Structural Foundation

- **Six primitives** (Signal, Entity, Claim, Model, Action, Self) are defined and persisted
- **ContextKernel** has all required state types (world, user, time, conversation, goal, memory, self_view, permission, budget)
- **SemanticEventGraph** and **SemanticAnswerGraph** types exist
- **UOL atoms** (EntityRef, Process, State) are defined
- **Pipeline** orchestrates the full flow
- **Operators** (answer, remember, abstain, ask, etc.) are registered and executable
- **Store** and **Registry** patterns are in place
- **Verification** (RealizationVerifier) exists

### 3.2 Implemented Subsystems

- Pragmatic interpretation (speech act, stance, repetition, affect)
- Context inference engine (model-driven + fallback)
- Semantic cluster registry
- Grounding pipeline
- Structural retrieval
- Ranking (claims + models)
- Synthesis/realization pipeline
- Causal inference
- Invariant guard
- Training architecture document

### 3.3 Test Coverage

- Invariant tests (pragmatic, gap, context kernel, synthesis, SLC contracts)
- Acceptance tests (context, memory, permission, synthesis, UOL mapping, recursion, causal)
- Pragmatic tests (repetition, decay, cause tracing)
- Unit tests for components

---

## 4. Gap Analysis

### Gap 1: Context Inference Is Still Mostly Heuristic

**Location:** `cemm/kernel/context_inference.py`

**Current behavior:**
- Phase 1: Model-driven inference using `keyword:`, `regex:`, `turn:` preconditions
- Phase 2: Hardcoded fallback rules (greetings, short first-turn, weather ambiguity)

**Architecture intent:**
- Infer context from: time, location, session position, world, memory, self, semantic graph, grounded entities, conversation dynamics, user affect, goal state

**Gap:**
- Context inference does not consume SemanticEventGraph processes/states
- Does not use conversation dynamics, user affect, or goal state
- Relies on shallow keyword matching instead of meaning-level inference
- Frame IDs are limited to session_opening, urgent_request, greeting, acknowledgment, clarification, exit

**Impact:**
- System cannot infer deeper context (user intent, task stage, correction state, topic shift)
- Routing decisions lack semantic grounding

**Severity:** High

---

### Gap 2: SemanticEventGraph Is Structurally Present but Semantically Thin

**Location:** `cemm/kernel/semantic_interpreter.py`

**Current behavior:**
- Builds graph from `UOLMapper.map_signal()` output
- Extracts claim candidates via heuristic string slicing
- Minimal temporal/causal edge extraction
- Shallow model lookup

**Architecture intent:**
- Graph is the **native higher-order meaning form**
- Binds symbols to typed latent embeddings
- Provides input for trainable semantic operators
- Preserves truth, source, time, permission, confidence outside opaque vectors

**Gap:**
- Graph does not carry rich typed latent information
- Claim candidate extraction is not semantically grounded
- Temporal/causal edges are pattern-based, not inferred
- Graph is not used as primary retrieval key—it enriches retrieval but does not center it

**Impact:**
- Downstream components (retrieval, ranking, answer composition) operate on shallow graph data
- Cannot support advanced reasoning over meaning structure

**Severity:** High

---

### Gap 3: Conversation State Is Weak for Multi-Turn Meaning

**Location:** `cemm/types/context_kernel.py` (ConversationState, GoalState, MemoryState)

**Current state:**
- ConversationState tracks: session_id, turn_index, recent_signal_ids, active_entity_ids, active_claim_ids, active_repetition_group_ids, dynamics, first_user_signal_id, inferred_context_claim_ids
- GoalState tracks: active_goal, required_slots, missing_slots, success_criteria
- MemoryState tracks: working IDs, candidate IDs, active_frame_ids, disputed_claim_ids, source_trust_keys

**Architecture intent:**
- Stable discourse entities across turns
- Topic continuity tracking
- Goal/slot progression from prior turns
- Unresolved reference tracking
- User correction tracking
- Dialogue act transitions
- Grounded turn-to-turn causal state

**Gap:**
- No discourse state (active topic, referents, unresolved references)
- No explicit correction/repair state tracking
- No question-under-discussion tracking
- GoalState exists but is not populated or used by the pipeline
- No turn-to-turn causal state propagation

**Impact:**
- Multi-turn conversations lack continuity at the meaning level
- System cannot track what the user is trying to accomplish across turns
- Corrections are not handled semantically

**Severity:** High

---

### Gap 4: SemanticAnswerGraph Is Too Skeletal

**Location:** `cemm/operators/answer.py`, `cemm/types/semantic_answer_graph.py`

**Current behavior:**
- SAG carries: intent, source_signal_ids, context_id, selected_claim_ids, selected_model_ids, confidence
- Optional: entity_refs, processes, states, causal_edges, temporal_edges, action_candidates, answer_latent

**Architecture intent:**
- SAG is the structured answer plan before text realization
- Carries: answer type, evidence structure, uncertainty placement, missing slot prompts, discourse intent, referenced entities/processes/states, causal/temporal explanation structure, answer-level constraints

**Gap:**
- SAG is mostly a container for selected claim/model IDs
- Does not carry explicit answer structure or plan
- No explicit uncertainty placement mapping
- No missing slot prompt structure
- No discourse-level intent encoding

**Impact:**
- Realization is not a renderer of a rich answer plan—it does most of the thinking
- Answer quality is limited by thin composition

**Severity:** High

---

### Gap 5: Training Pipeline Is Under-Scoped

**Location:** `cemm/cemm_trainer.py`

**Current task types:**
- claim_extraction
- predicate_mapping
- synthesis_verification
- causal_rule_extraction
- structural_induction

**Architecture-defined task types (from cemm_training_architecture.md):**

*Core semantic:*
- semantic_graph_extraction
- semantic_graph_denoising
- semantic_latent_target
- semantic_answer_composition
- semantic_text_realization
- next_event_prediction

*Symbolic grounding:*
- entity_resolution
- uol_mapping
- predicate_mapping
- claim_extraction
- claim_canonicalization
- context_inference
- pragmatic_interpretation
- frame_classification
- contradiction_detection
- temporal_relation_derivation

*Reasoning/routing:*
- memory_retrieval_ranking
- causal_rule_extraction
- causal_effect_prediction
- tool_handoff_planning
- procedure_model_induction
- operator_selection
- ranking_judgment

*Safety/quality/learning:*
- synthesis_verification
- verifier_calibration
- self_state_update
- structural_induction

**Gap:**
- Training runner exposes only 5 of ~30 defined task types
- Missing highest-value conversational tasks: semantic_graph_extraction, uol_mapping, context_inference, pragmatic_interpretation, memory_retrieval_ranking, semantic_answer_composition, semantic_text_realization

**Impact:**
- Cannot train the operators that would improve conversational performance
- Generic training on current tasks will not close the conversational understanding gap

**Severity:** High

---

### Gap 6: Retrieval Is Not Graph-Centered

**Location:** `cemm/retrieval/structural.py`, `cemm/kernel/pipeline.py`

**Current behavior:**
- Retrieval runs twice: `retrieve_for_kernel()` then `retrieve_for_graph()`
- Results are merged (deduplicated by claim ID, graph results preferred)
- Ranking uses graph context but retrieval itself is not fundamentally graph-driven

**Architecture intent:**
- SemanticEventGraph is the primary input for retrieval
- Retrieval is driven by graph processes, states, entity_refs, temporal/causal edges
- Ranking features include: process/state atom match, discourse continuity, goal match, correction relevance, recency + contradiction penalties, frame compatibility, source trust

**Gap:**
- Retrieval is still primarily kernel-driven (claim IDs, model IDs)
- Graph enrichment is additive, not central
- Ranking features do not fully leverage graph structure

**Impact:**
- System cannot retrieve based on meaning-level similarity
- Misses opportunities for graph-grounded relevance

**Severity:** Medium-High

---

### Gap 7: Decision Router Does Not Fully Use Pragmatic Signals

**Location:** `cemm/kernel/decision_router.py`

**Current behavior:**
- Routes based on graph processes/states, memory packet, inference packet
- Has short-input fallback
- Does not consume ObservationSemantics or ContextInference as fallback signals

**Architecture intent (per 2026-06-30-pragmatic-semantic-routing.md plan):**
- Use speech act and frame_key as fallback when graph matching fails
- Wire pragmatic interpretation into routing

**Gap:**
- Router does not accept observation_semantics or context_inference parameters
- No speech act fallback logic

**Impact:**
- System falls back to abstain for conversational inputs that should route to answer/ask
- Requires manual pattern registration for each surface form

**Severity:** Medium (addressed by existing plan)

---

### Gap 8: Tests Validate Shallow Contracts, Not Meaning-Level Understanding

**Location:** `tests/test_acceptance.py`, `tests/test_pragmatic.py`, `tests/invariants/`

**Current test coverage:**
- Greeting detection
- Insult clustering
- Repetition count
- Frustration decay
- Invariant checks (no insult claims, no stale claims, budget limits)

**Missing test coverage:**
- Multi-turn referent tracking ("I bought a laptop yesterday." -> "It's broken." -> bind "it")
- Correction handling (user says X, then "actually Y" -> prefer correction)
- Goal slot filling ("Book me a flight." -> ask missing slots, don't hallucinate)
- Context-dependent intent ("sure" means different things after different assistant acts)
- Meaning-preserving paraphrase mapping
- Answer graph faithfulness (answer only expresses supported evidence)
- Failure capture (low confidence -> uncertainty or ask, not confident synthesis)

**Impact:**
- Current tests pass but do not validate the system's conversational depth
- Cannot detect regressions in meaning-level understanding

**Severity:** Medium

---

### Gap 9: Static Coding Violations in Kernel Components

**Source:** `2026-06-30-static-coding-gap-analysis.md`

**Architectural principle:** CEMM is designed so that **all language understanding lives in the model layer** (Registry, UOL Mapper, trained artifacts). Kernel components (`SemanticInterpreter`, `DecisionRouter`) should only operate on typed semantic structures (UOL atoms, SEG, SAG), never on raw text patterns.

**Current violations:**

#### S1: Hardcoded greeting word list in DecisionRouter
- **Location:** `kernel/decision_router.py:32` — `_GREETINGS = {"hello", "hi", "hey", ...}`
- **Problem:** Greeting detection uses a hardcoded English word list with fuzzy matching directly in the DecisionRouter. This is language-specific, non-trainable, and bypasses the UOL mapper + SEG process detection.
- **Proper path:** UOL mapper should detect greeting intent and emit a `ProcessUOLAtom(frame_key="greeting")`. The SEG should contain this process. The DecisionRouter should check `graph.processes` for `frame_key == "greeting"`, not parse raw text.

#### S2: Hardcoded exit word list in DecisionRouter
- **Location:** `kernel/decision_router.py:33` — `_EXITS = {"exit", "quit", "bye", ...}`
- **Problem:** Same as S1 — language-specific exit detection in the kernel instead of the model layer.
- **Proper path:** UOL mapper should emit `ProcessUOLAtom(frame_key="session_exit")`. DecisionRouter checks graph processes.

#### S3: Hardcoded command prefix list in DecisionRouter
- **Location:** `kernel/decision_router.py:34` — `_COMMAND_PREFIXES = ["remember", "save", "reflect", ...]`
- **Problem:** Command detection uses hardcoded English verb prefixes with fuzzy Levenshtein matching in the DecisionRouter. This bypasses the registry's operator entries and UOL semantic mapping.
- **Proper path:** UOL mapper should detect command intent and emit `ProcessUOLAtom(frame_key="command_remember")` etc. DecisionRouter maps process frame_keys to action kinds via the registry's operator entries.

#### S4: Hardcoded claim candidate regex patterns in SemanticInterpreter
- **Location:** `kernel/semantic_interpreter.py:38-50` — `_CLAIM_CANDIDATE_PATTERNS`
- **Problem:** Claim extraction uses hardcoded English regex patterns (`"i like"`, `"i have"`, `"i am"`, etc.). This is language-specific and non-trainable. The patterns also hardcode subject resolution (`"i" -> "user"`).
- **Proper path:** Claim candidates should be derived from UOL process/state atoms + registry predicates. The UOL mapper identifies the semantic structure; the interpreter maps it to predicate keys via the registry.

#### S5: Hardcoded temporal/causal regex patterns in SemanticInterpreter
- **Location:** `kernel/semantic_interpreter.py:15-36` — `_TEMPORAL_PATTERNS`, `_CAUSAL_PATTERNS`
- **Problem:** Temporal and causal edge extraction uses hardcoded English regex patterns. These should be UOL semantic mappings, not kernel-level regex.
- **Proper path:** UOL mapper should emit process atoms with temporal/causal frame_keys. The interpreter maps these to edges using registry entries, not regex.

#### S6: Command prefix stripping in SemanticInterpreter
- **Location:** `kernel/semantic_interpreter.py:164-168` — strips `"remember "`, `"save "`, `"rember "`, `"store "`
- **Problem:** Hardcoded command prefix stripping including a misspelled variant (`"rember"`). This is a workaround for the UOL mapper not recognizing command intent.
- **Proper path:** UOL mapper should handle command detection and strip/normalize commands as part of mapping.

#### S7: Hardcoded "user" default subject in SemanticInterpreter claim_refs
- **Location:** `kernel/semantic_interpreter.py:141-143` — searches by `"user"` as default subject
- **Problem:** Assumes first-person statements always have `"user"` as subject. This is an English-centric assumption.
- **Proper path:** Subject resolution should come from the UOL mapper's entity ref atoms, which should map first-person pronouns to the kernel's user entity.

**Impact:**
- Kernel components are doing language understanding that should live in the model layer
- System is not model-driven as specified by architecture
- Language-specific code makes the system non-portable
- Static code cannot be learned or improved through training

**Severity:** High

---

### Gap 10: Concrete Runtime Failures from Manual Testing

**Source:** `2026-06-30-static-coding-gap-analysis.md`

These are specific observed failures that demonstrate the gaps above:

#### R1: Multi-turn recall failure
- **Problem:** After storing "I like coffee" via `remember`, asking "what do I like?" does not retrieve the stored claim. The SEG has no claim_refs because the UOL mapper doesn't extract "what do I like?" as a query about the user's preferences.
- **Root cause:** UOL mapper doesn't detect question intent or map it to entity refs that would trigger claim lookup.
- **Related gaps:** Gap 2 (shallow graph), Gap 3 (weak discourse state), Gap 9 S4 (static claim extraction)

#### R2: Misspelled input abstention
- **Problem:** Misspelled queries like "whats the wether?" abstain because the UOL mapper doesn't recognize them.
- **Root cause:** UOL mapper has no fuzzy matching against registry aliases. Fuzzy matching should be in the mapper, not the DecisionRouter.
- **Related gaps:** Gap 2 (shallow graph), Gap 9 S1-S3 (static routing bypasses model layer)

#### R3: Greeting response quality
- **Problem:** Greetings route to `answer` but produce "I don't have enough information to answer." because there are no claims to answer with.
- **Root cause:** Greeting should produce a conversational response, not a knowledge-base answer. This requires a `greeting` synthesis strategy or a dedicated greeting response path in the answer operator.
- **Related gaps:** Gap 4 (thin SAG), Gap 7 (pragmatic routing), Gap 9 S1 (static greeting detection)

**Severity:** Medium (concrete symptoms of deeper gaps)

---

## 5. Root Cause Analysis

### Primary Root Cause

**The system has built the component layer but not the semantic execution layer.**

The architecture specifies a meaning-first system where components work together at the semantic level. The implementation has created the components (primitives, types, stores, operators) but the runtime still operates too close to the text/heuristic level:

- Context inference uses keywords, not graph + kernel state
- SemanticEventGraph exists structurally but carries shallow meaning
- SemanticAnswerGraph is a thin container, not a rich answer plan
- Retrieval is kernel-driven, not graph-centered
- Training does not cover the operators that would improve meaning-level performance
- **Kernel components contain static, language-specific text patterns instead of delegating to the model layer**

### Secondary Root Cause

**Training is scoped to side capabilities, not core conversational operators.**

The training pipeline does not include the task types that would improve:
- Semantic graph extraction quality
- Context inference accuracy
- Pragmatic interpretation depth
- Answer composition richness
- Retrieval ranking quality

Without training on these, the system cannot improve at the meaning level through learning.

### Tertiary Root Cause

**Tests validate invariants, not conversational capability.**

The test suite checks that the system does not violate contracts (no insult claims, no stale claims, budget limits) but does not validate that the system understands conversation at the meaning level.

---

## 6. Prioritized Recommendations

### Phase 1: Complete the Pragmatic-Semantic Routing Path (Tactical)

*Addresses Gap 7, partially Gap 1, partially Gap 9 S1-S3*

This is the work specified in `2026-06-30-pragmatic-semantic-routing.md`:

- [ ] Add conversational speech act clusters (greeting, acknowledgment, clarification, exit, command)
- [ ] Wire speech act into ObservationSemantics with frame_key
- [ ] Enrich context inference with conversational rules
- [ ] Add speech act fallback to DecisionRouter
- [ ] Add semantic similarity fallback to UOLMapper
- [ ] Wire Inductor to register semantics into Registry

**Note:** This phase does **not** remove the static coding violations (Gap 9). It adds fallback paths that reduce their impact. Static code removal is Phase 2.6.

**Expected outcome:** Reduced manual pattern registration, better first-pass conversational coverage.

---

### Phase 2: Strengthen Semantic Execution (Strategic)

*Addresses Gaps 1, 2, 3, 4, 6, 9, 10*

#### 2.1 Make Context Inference Graph-Grounded

- Refactor `ContextInferenceEngine.infer()` to consume:
  - SemanticEventGraph processes/states
  - ConversationDynamics
  - UserAffectState
  - GoalState
  - Prior turn's selected claims
  - Turn position
  - Time bucket
- Replace keyword/regex rules with graph-match rules

#### 2.2 Enrich SemanticEventGraph Semantics + Remove Static Coding

*Addresses Gap 2 and Gap 9 S4-S7*

**Remove static regex from SemanticInterpreter:**
- [ ] Remove `_CLAIM_CANDIDATE_PATTERNS` (S4) — derive claim candidates from UOL process/state atoms + registry predicates
- [ ] Remove `_TEMPORAL_PATTERNS` and `_CAUSAL_PATTERNS` (S5) — emit process atoms with temporal/causal frame_keys via UOL mapper
- [ ] Remove command prefix stripping logic (S6) — UOL mapper should handle command detection and normalization
- [ ] Remove hardcoded `"user"` default subject (S7) — subject resolution should come from UOL entity ref atoms

**Enrich graph semantics:**
- Strengthen claim candidate extraction via registry-backed UOL atoms
- Add inferred temporal/causal edges from graph structure (not regex)
- Carry typed latent information in graph
- Make graph the primary retrieval key, not enrichment

#### 2.3 Add Multi-Turn Discourse State

Add to ContextKernel:
- DiscourseState: active_topic, referents, unresolved_references, question_under_discussion
- Track corrections: correction_state (original, correction, accepted)
- Populate GoalState from conversation flow
- Propagate turn-to-turn causal state

#### 2.4 Strengthen SemanticAnswerGraph

Expand SAG to carry:
- Answer structure (evidence groups, explanation flow)
- Uncertainty placement map
- Missing slot prompts
- Discourse-level intent encoding

#### 2.5 Make Retrieval Graph-Centered

- Refactor retrieval to be driven by graph structure
- Add ranking features: process/state match, discourse continuity, goal alignment, correction relevance

#### 2.6 Remove Static Coding from DecisionRouter

*Addresses Gap 9 S1-S3*

- [ ] Remove `_GREETINGS` hardcoded word list (S1) — UOL mapper should emit `ProcessUOLAtom(frame_key="greeting")`, router checks `graph.processes`
- [ ] Remove `_EXITS` hardcoded word list (S2) — UOL mapper should emit `ProcessUOLAtom(frame_key="session_exit")`, router checks `graph.processes`
- [ ] Remove `_COMMAND_PREFIXES` hardcoded list (S3) — UOL mapper should emit `ProcessUOLAtom(frame_key="command_remember")` etc., router maps frame_keys to action kinds via registry
- [ ] Move Levenshtein fuzzy matching to UOL mapper for registry alias resolution

**Prerequisites:** UOL mapper must first support greeting/exit/command detection (Phase 1 UOLMapper fallback + Phase 2.2 registry entries)

**Expected outcome:** Runtime executes the meaning-first loop as specified.

---

### Phase 3: Align Training Pipeline (Strategic)

*Addresses Gap 5*

Add first-class training jobs for:
- semantic_graph_extraction
- uol_mapping
- context_inference
- pragmatic_interpretation
- memory_retrieval_ranking
- semantic_answer_composition
- semantic_text_realization

Capture runtime failures as structured training examples:
- Input signal
- Prior turns summary
- Full ContextKernel
- Selected claims/models
- SemanticEventGraph
- Chosen action / answer graph
- Realized text
- Verification result
- User correction / failure outcome

**Expected outcome:** System can learn to improve meaning-level performance.

---

### Phase 4: Deepen Test Coverage (Tactical)

*Addresses Gap 8*

Add scenario tests for:
- Multi-turn referent tracking
- Correction handling
- Goal slot filling
- Context-dependent intent
- Meaning-preserving paraphrase
- Answer graph faithfulness
- Failure capture

**Expected outcome:** Tests validate conversational capability, not just invariants.

---

## 7. How This Relates to Existing Plans

### 7.1 Pragmatic-Semantic Routing Plan (`2026-06-30-pragmatic-semantic-routing.md`)

This plan addresses **Gap 7** and **part of Gap 1**.

**Where I agree with that plan:**
- Adding speech act clusters is useful
- Wiring pragmatic signals into routing is a good fallback mechanism
- Cluster fallback for UOL mapper reduces manual registration
- Making inductor semantics visible to registry improves learning

**Where I think it is insufficient:**
- It improves routing but does not create true conversational understanding
- It does not address Gap 2 (shallow graph), Gap 3 (weak discourse state), Gap 4 (thin answer graph), Gap 5 (training scope), or Gap 6 (retrieval not graph-centered)
- It is a tactical patch, not a strategic fix

### 7.2 Static Coding Gap Analysis (`2026-06-30-static-coding-gap-analysis.md`)

This analysis addresses **Gap 9** in exact, code-level detail.

**Where it is stronger than my analysis:**
- Exact file:line references (`kernel/decision_router.py:32`)
- Direct fix plan with specific code changes
- Strong emphasis on model-driven architectural principle
- Concrete runtime failures (R1-R3)

**Where my analysis is broader:**
- Covers training pipeline (Gap 5), test coverage (Gap 8), discourse state (Gap 3), answer graph (Gap 4), retrieval (Gap 6)
- Strategic phasing with dependencies
- System-level root cause: "components built but semantic execution layer incomplete"

**Integration:**
- The static analysis fix plan is integrated into **Phase 2.2** (SemanticInterpreter) and **Phase 2.6** (DecisionRouter)
- R1-R3 runtime failures are captured as **Gap 10**

**Recommendation:** Execute Phase 1 (routing plan) first for immediate improvement, then proceed to Phases 2-4 for strategic closure, using the static analysis as detailed implementation guidance for Phases 2.2 and 2.6.

---

## 8. Conclusion

The CEMM system has strong architectural foundations but has not yet completed the **semantic execution path** that makes the architecture operational. The current runtime is too dependent on heuristics, shallow text-level processing, and **static language-specific code in kernel components**, while the architecture specifies meaning-first, model-driven operation.

This document identifies **10 gaps** across the system:
- **Gaps 1-6:** Strategic semantic execution gaps (context inference, graph semantics, discourse state, answer composition, training scope, retrieval)
- **Gap 7:** Pragmatic routing missing from DecisionRouter
- **Gap 9:** Static coding violations in kernel components (7 specific violations with exact file:line references)
- **Gap 10:** Concrete runtime failures demonstrating the gaps (multi-turn recall, misspelling abstention, greeting quality)

The gap is **not primarily "needs more training."** It is that the system does not yet exercise the meaning-first loop that training would improve, and contains static code that cannot be learned.

**Recommended path:**
1. Execute Phase 1 (routing plan) for immediate tactical gains
2. Execute Phase 2 (semantic execution + static code removal) to complete the architecture
3. Execute Phase 3 (training alignment) to enable learning
4. Execute Phase 4 (test coverage) to validate capability

This will close the architecture-execution gap and position the system for meaningful improvement through training.

---

*End of Gap Analysis*
