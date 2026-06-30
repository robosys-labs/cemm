# CEMM Implementation Plan — Complete Gap Resolution

**Date:** 2026-01-17  
**Status:** Final  
**Sources:** Gap Analysis, Static Coding Analysis, Pragmatic-Semantic Routing Plan

---

## Executive Summary

CEMM has strong structural scaffolding but executes a **partial, shallow version** of its meaning-first architecture. This document consolidates all identified gaps and provides a complete, phased implementation plan.

**Root cause:** The system has built the component layer but not the semantic execution layer. Kernel components contain static, language-specific code that should live in the model layer.

**10 gaps identified:**
- Gaps 1-6: Strategic semantic execution gaps
- Gap 7: Pragmatic routing missing from DecisionRouter
- Gap 8: Tests validate shallow contracts
- Gap 9: Static coding violations (7 specific S1-S7)
- Gap 10: Concrete runtime failures (R1-R3)

---

## Gap Summary

| Gap | Description | Severity | Phase |
|-----|-------------|----------|-------|
| 1 | Context inference is heuristic, not graph-grounded | High | 2 |
| 2 | SemanticEventGraph is semantically thin | High | 2 |
| 3 | Conversation state weak for multi-turn | High | 2 |
| 4 | SemanticAnswerGraph too skeletal | High | 2 |
| 5 | Training pipeline under-scoped | High | 3 |
| 6 | Retrieval not graph-centered | Medium-High | 2 |
| 7 | Decision router missing pragmatic signals | Medium | 1 |
| 8 | Tests validate shallow contracts | Medium | 4 |
| 9 | Static coding violations in kernel | High | 2 |
| 10 | Concrete runtime failures | Medium | 1-2 |

---

## Static Coding Violations (Gap 9)

**Principle:** All language understanding must live in the model layer (Registry, UOL Mapper). Kernel components operate only on typed semantic structures.

| ID | Location | Problem |
|----|----------|---------|
| S1 | `decision_router.py:32` | `_GREETINGS` hardcoded word list |
| S2 | `decision_router.py:33` | `_EXITS` hardcoded word list |
| S3 | `decision_router.py:34` | `_COMMAND_PREFIXES` hardcoded list |
| S4 | `semantic_interpreter.py:38-50` | `_CLAIM_CANDIDATE_PATTERNS` regex |
| S5 | `semantic_interpreter.py:15-36` | `_TEMPORAL_PATTERNS`, `_CAUSAL_PATTERNS` regex |
| S6 | `semantic_interpreter.py:164-168` | Command prefix stripping |
| S7 | `semantic_interpreter.py:141-143` | Hardcoded `"user"` default subject |

---

## Runtime Failures (Gap 10)

| ID | Problem | Root Cause |
|----|---------|------------|
| R1 | Multi-turn recall failure | UOL mapper doesn't detect question intent |
| R2 | Misspelled input abstention | No fuzzy matching in UOL mapper |
| R3 | Greeting response quality | Greeting routes to answer but no claims exist |

---

## Phase 1: Pragmatic-Semantic Routing (Tactical)

*Addresses Gap 7, partially Gap 1, partially Gap 9 S1-S3, R3*

### Task 1.1: Add Conversational Speech Act Clusters

**File:** `cemm/kernel/semantic_clusters.py`

Add to `_BUILTIN_CLUSTERS`:

```python
"conversational_greeting": {
    "speech_act": "greeting",
    "patterns": ["hello", "hi", "hey", "howdy", "greetings", "sup", "morning", "afternoon", "evening", "hi there", "oh hi", "lol hello"],
    "target": "assistant",
    "affect_baseline": {"valence": 0.3, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
},
"conversational_acknowledgment": {
    "speech_act": "acknowledgment",
    "patterns": ["ok", "sure", "yeah", "cool", "got it", "i see", "right", "understood", "noted", "sounds good", "great", "nice"],
    "target": "assistant",
    "affect_baseline": {"valence": 0.1, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
},
"conversational_clarification": {
    "speech_act": "clarification",
    "patterns": ["what", "huh", "how do you mean", "what do you mean", "what in the world", "what the", "confused", "don't understand", "don't get it", "lost", "not following", "come again", "what?"],
    "target": "assistant",
    "affect_baseline": {"valence": -0.1, "arousal": 0.2, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
},
"conversational_exit": {
    "speech_act": "exit",
    "patterns": ["exit", "quit", "bye", "goodbye", "stop", "done", "see you", "later"],
    "target": "assistant",
    "affect_baseline": {"valence": 0.0, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
},
"conversational_command_remember": {
    "speech_act": "command",
    "patterns": ["remember", "save", "store", "note", "rember", "remembr"],
    "target": "assistant",
    "affect_baseline": {"valence": 0.0, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
},
```

**Test:** `cemm/tests/test_conversational_clusters.py`

---

### Task 1.2: Wire Speech Act into ObservationSemantics

**Files:**
- `cemm/types/signal.py` — add `frame_key: str = ""` to `ObservationSemantics`
- `cemm/kernel/pragmatic_interpreter.py` — map speech acts to frame keys

```python
_SPEECH_ACT_TO_FRAME_KEY = {
    "greeting": "greeting",
    "acknowledgment": "acknowledgment",
    "clarification": "request_clarification",
    "exit": "session_exit",
    "command": "command_remember",
}
frame_key = _SPEECH_ACT_TO_FRAME_KEY.get(speech_act, "")
```

---

### Task 1.3: Enrich Context Inference Rules

**File:** `cemm/kernel/context_inference.py`

Replace Phase 2 fallback with enriched conversational rules:

```python
_GREETING_WORDS = {"hello", "hi", "hey", "howdy", "greetings", "sup", "morning", "afternoon", "evening"}
_ACKNOWLEDGMENT_WORDS = {"ok", "sure", "yeah", "cool", "right", "understood", "noted", "great", "nice"}
_CLARIFICATION_WORDS = {"what", "huh", "confused", "lost", "why", "how"}
_EXIT_WORDS = {"exit", "quit", "bye", "goodbye", "stop", "done"}

words_set = set(content_lower.replace("?", "").split())

if words_set & _EXIT_WORDS:
    inference.frame_id = "session_exit"
elif turn_index == 1 and (words_set & _GREETING_WORDS):
    inference.frame_id = "session_opening"
elif words_set & _GREETING_WORDS:
    inference.frame_id = "greeting"
elif words_set & _ACKNOWLEDGMENT_WORDS:
    inference.frame_id = "acknowledgment"
elif words_set & _CLARIFICATION_WORDS:
    inference.frame_id = "clarification"
```

---

### Task 1.4: Add Speech Act Fallback to Decision Router

**File:** `cemm/kernel/decision_router.py`

1. Add params: `observation_semantics: ObservationSemantics | None = None`
2. Add fallback before final abstain:

```python
if observation_semantics and observation_semantics.confidence >= 0.5:
    sa = observation_semantics.speech_act
    if sa == "greeting":
        return DecisionPacket(action_kind="answer", ...)
    elif sa == "acknowledgment":
        return DecisionPacket(action_kind="answer", ...)
    elif sa == "clarification":
        return DecisionPacket(action_kind="ask", ...)
    elif sa == "exit":
        return DecisionPacket(action_kind="abstain", ...)
```

3. Update `cemm/__main__.py` to pass `observation_semantics` to router

---

### Task 1.5: Add Semantic Similarity Fallback to UOL Mapper

**File:** `cemm/registry/uol_mapper.py`

Add cluster-based fallback when registry matching fails:

```python
def _cluster_fallback(self, content: str, atoms: list) -> list:
    has_process = any(a.kind == "process" for a in atoms)
    if has_process:
        return atoms
    
    ranked = self._cluster_reg.match_ranked(content)
    if not ranked or ranked[0].confidence < 0.5:
        return atoms
    
    _SA_TO_FRAME = {
        "greeting": "greeting",
        "acknowledgment": "acknowledgment",
        "clarification": "request_clarification",
        "exit": "session_exit",
        "command": "command_remember",
    }
    frame_key = _SA_TO_FRAME.get(ranked[0].speech_act, "")
    if frame_key:
        atoms.append(ProcessUOLAtom(frame_key=frame_key, ...))
    return atoms
```

---

### Task 1.6: Wire Inductor to Registry

**File:** `cemm/learning/inductor.py`

1. Add `registry: Registry | None = None` param to `__init__`
2. In `_find_uol_patterns`, register induced semantics:

```python
if self._registry is not None:
    self._registry.register(RegistryEntry(
        model_id=model.id,
        canonical_key=predicate,
        kind="uol_semantic",
        aliases=[predicate],
    ))
```

3. Update `cemm/kernel/recursive_loop.py` to pass registry to Inductor

---

## Phase 2: Semantic Execution + Static Code Removal (Strategic)

*Addresses Gaps 1, 2, 3, 4, 6, 9, 10*

### Task 2.1: Make Context Inference Graph-Grounded

**File:** `cemm/kernel/context_inference.py`

Refactor `infer()` to consume:
- SemanticEventGraph processes/states
- ConversationDynamics
- UserAffectState
- GoalState
- Prior turn's selected claims
- Turn position, time bucket

Replace keyword/regex rules with graph-match rules.

---

### Task 2.2: Remove Static Regex from SemanticInterpreter

**File:** `cemm/kernel/semantic_interpreter.py`

- [ ] Remove `_CLAIM_CANDIDATE_PATTERNS` (S4) — derive from UOL atoms + registry predicates
- [ ] Remove `_TEMPORAL_PATTERNS`, `_CAUSAL_PATTERNS` (S5) — emit via UOL mapper
- [ ] Remove command prefix stripping (S6) — UOL mapper handles
- [ ] Remove hardcoded `"user"` subject (S7) — use UOL entity ref atoms

---

### Task 2.3: Register UOL Semantic Entries

**File:** `cemm/registry/registry.py` or seed data

Register entries for:
- `greeting`, `session_exit`, `command_remember`, `command_reflect`, `command_retrieve`
- `temporal_before`, `temporal_after`, `causal_causes`
- Predicate entries: `likes`, `is_a`, `has`, `used_for`, `belongs_to`, `favorite`, `prefers`

---

### Task 2.4: Add Multi-Turn Discourse State

**File:** `cemm/types/context_kernel.py`

Add `DiscourseState`:
```python
@dataclass
class DiscourseState:
    active_topic: str = ""
    referents: dict[str, str] = field(default_factory=dict)  # pronoun -> entity_id
    unresolved_references: list[str] = field(default_factory=list)
    question_under_discussion: str = ""
    correction_state: dict = field(default_factory=dict)  # original, correction, accepted
```

Populate GoalState from conversation flow. Propagate turn-to-turn causal state.

---

### Task 2.5: Strengthen SemanticAnswerGraph

**File:** `cemm/types/semantic_answer_graph.py`, `cemm/operators/answer.py`

Expand SAG to carry:
- Answer structure (evidence groups, explanation flow)
- Uncertainty placement map
- Missing slot prompts
- Discourse-level intent encoding

---

### Task 2.6: Make Retrieval Graph-Centered

**File:** `cemm/retrieval/structural.py`

- Refactor retrieval to be driven by graph structure
- Add ranking features: process/state match, discourse continuity, goal alignment, correction relevance

---

### Task 2.7: Remove Static Coding from DecisionRouter

**File:** `cemm/kernel/decision_router.py`

- [ ] Remove `_GREETINGS` (S1) — check `graph.processes` for `frame_key == "greeting"`
- [ ] Remove `_EXITS` (S2) — check `graph.processes` for `frame_key == "session_exit"`
- [ ] Remove `_COMMAND_PREFIXES` (S3) — map process frame_keys to action kinds via registry
- [ ] Move Levenshtein to UOL mapper for registry alias resolution

**Prerequisites:** Phase 1 + Task 2.2/2.3 must complete first.

---

## Phase 3: Training Pipeline Alignment (Strategic)

*Addresses Gap 5*

### Task 3.1: Add Training Jobs

**File:** `cemm/cemm_trainer.py`

Add first-class training jobs for:
- `semantic_graph_extraction`
- `uol_mapping`
- `context_inference`
- `pragmatic_interpretation`
- `memory_retrieval_ranking`
- `semantic_answer_composition`
- `semantic_text_realization`

### Task 3.2: Capture Runtime Failures as Training Examples

Structure:
- Input signal
- Prior turns summary
- Full ContextKernel
- Selected claims/models
- SemanticEventGraph
- Chosen action / answer graph
- Realized text
- Verification result
- User correction / failure outcome

---

## Phase 4: Test Coverage (Tactical)

*Addresses Gap 8*

### Task 4.1: Add Scenario Tests

**File:** `tests/test_conversational_scenarios.py`

Add tests for:
- Multi-turn referent tracking ("I bought a laptop." → "It's broken." → bind "it")
- Correction handling ("actually Y" → prefer correction)
- Goal slot filling (ask missing slots, don't hallucinate)
- Context-dependent intent ("sure" means different things)
- Meaning-preserving paraphrase mapping
- Answer graph faithfulness
- Failure capture (low confidence → uncertainty or ask)

---

## Execution Order

```
Phase 1 (Tactical — immediate gains)
├── Task 1.1: Add conversational clusters
├── Task 1.2: Wire speech act to ObservationSemantics
├── Task 1.3: Enrich context inference rules
├── Task 1.4: Add speech act fallback to router
├── Task 1.5: Add cluster fallback to UOL mapper
└── Task 1.6: Wire inductor to registry

Phase 2 (Strategic — complete architecture)
├── Task 2.1: Graph-grounded context inference
├── Task 2.2: Remove static regex from SemanticInterpreter
├── Task 2.3: Register UOL semantic entries
├── Task 2.4: Add multi-turn discourse state
├── Task 2.5: Strengthen SemanticAnswerGraph
├── Task 2.6: Make retrieval graph-centered
└── Task 2.7: Remove static coding from DecisionRouter

Phase 3 (Strategic — enable learning)
├── Task 3.1: Add training jobs
└── Task 3.2: Capture runtime failures

Phase 4 (Tactical — validate capability)
└── Task 4.1: Add scenario tests
```

---

## Verification Commands

```bash
# After each task
python -m pytest cemm/tests/ --tb=short

# After Phase 1
python manual_integration_test.py

# After Phase 2
python -c "from cemm.kernel.decision_router import _GREETINGS" 2>&1 | grep -q "cannot import" && echo "Static code removed"

# After Phase 4
python -m pytest tests/test_conversational_scenarios.py -v
```

---

## Success Criteria

1. **Phase 1 complete:** Greetings, acknowledgments, clarifications route correctly without manual registration
2. **Phase 2 complete:** No static word lists or regex in kernel components; all language understanding in model layer
3. **Phase 3 complete:** Training pipeline covers all 7 core conversational task types
4. **Phase 4 complete:** Multi-turn scenario tests pass

---

*End of Implementation Plan*
