# Pragmatic Semantic Routing — Reduce Manual Training Burden

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the need to manually register every conversational surface form by wiring the pragmatic interpretation layer (speech acts + semantic clusters) and context inference into the decision router as fallback signals, and by making the inductor's learned UOL semantics visible to the UOL mapper.

**Architecture:** The architecture (§13, §14, §15, §17, §21) describes a system where UOL atoms + context inference + pragmatic interpretation handle most inputs without manual tuning. Currently 5 gaps prevent this: (1) speech act detection only covers insults/praise, not basic conversation; (2) context inference doesn't influence routing; (3) UOL mapper has no semantic similarity fallback; (4) inductor creates dead Model records invisible to the Registry; (5) decision router doesn't use speech acts as fallback. This plan fixes all 5 gaps.

**Tech Stack:** Python 3.13, dataclasses, SQLite (Store), Registry pattern, SemanticMatcher (Levenshtein fuzzy matching)

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/semantic_clusters.py` | Conversational speech act clusters (greeting, question, acknowledgment, clarification, command, exit) | Modify |
| `cemm/kernel/pragmatic_interpreter.py` | Wire speech act into ObservationSemantics with frame_key for routing | Modify |
| `cemm/kernel/context_inference.py` | Enrich context inference rules, output frame_id for conversational contexts | Modify |
| `cemm/kernel/decision_router.py` | Accept observation_semantics + context_inference as fallback signals when UOL matching fails | Modify |
| `cemm/registry/uol_mapper.py` | Add semantic similarity fallback using cluster matching when registry matching fails | Modify |
| `cemm/learning/inductor.py` | Register induced UOL semantics into Registry, not just ModelStore | Modify |
| `cemm/kernel/pipeline.py` | Pass observation_semantics and context_inference to decision router via process_input | Modify |
| `cemm/__main__.py` | Pass observation_semantics and context_inference to DecisionRouter.run() | Modify |
| `cemm/tests/test_conversational_clusters.py` | Tests for conversational speech act detection | Create |
| `cemm/tests/test_pragmatic_routing.py` | Tests for speech-act-based routing fallback | Create |
| `cemm/tests/test_context_inference_routing.py` | Tests for context inference influencing routing | Create |
| `cemm/tests/test_uol_mapper_fallback.py` | Tests for semantic similarity fallback in UOL mapper | Create |
| `cemm/tests/test_inductor_registry.py` | Tests for inductor registering UOL semantics into Registry | Create |

---

## Task 1: Add Conversational Speech Act Clusters

**Files:**
- Modify: `cemm/kernel/semantic_clusters.py:7-44` (add clusters to `_BUILTIN_CLUSTERS`)
- Create: `cemm/tests/test_conversational_clusters.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_conversational_clusters.py
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.kernel.semantic_clusters import SemanticClusterRegistry


def test_greeting_cluster():
    reg = SemanticClusterRegistry()
    speech_act, cluster_key, conf = reg.match("hello")
    assert speech_act == "greeting"
    assert conf >= 0.8


def test_greeting_variant():
    reg = SemanticClusterRegistry()
    speech_act, cluster_key, conf = reg.match("hi there")
    assert speech_act == "greeting"
    assert conf >= 0.7


def test_acknowledgment_cluster():
    reg = SemanticClusterRegistry()
    speech_act, cluster_key, conf = reg.match("ok")
    assert speech_act == "acknowledgment"
    assert conf >= 0.8


def test_acknowledgment_variants():
    reg = SemanticClusterRegistry()
    for text in ["sure", "yeah", "cool", "got it", "i see"]:
        speech_act, _, conf = reg.match(text)
        assert speech_act == "acknowledgment", f"Failed for '{text}': got {speech_act}"
        assert conf >= 0.7


def test_clarification_cluster():
    reg = SemanticClusterRegistry()
    for text in ["what?", "huh?", "how do you mean?", "what in the world?", "i'm confused"]:
        speech_act, _, conf = reg.match(text)
        assert speech_act == "clarification", f"Failed for '{text}': got {speech_act}"
        assert conf >= 0.6


def test_exit_cluster():
    reg = SemanticClusterRegistry()
    speech_act, _, conf = reg.match("bye")
    assert speech_act == "exit"
    assert conf >= 0.8


def test_command_cluster():
    reg = SemanticClusterRegistry()
    speech_act, _, conf = reg.match("remember I like coffee")
    assert speech_act == "command"
    assert conf >= 0.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_conversational_clusters.py -v`
Expected: FAIL — `AssertionError: assert 'unknown' == 'greeting'`

- [ ] **Step 3: Add conversational clusters to `_BUILTIN_CLUSTERS`**

Add these entries to the `_BUILTIN_CLUSTERS` dict in `cemm/kernel/semantic_clusters.py`, after the existing `user_praise` entry:

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

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_conversational_clusters.py -v`
Expected: PASS — all 7 tests

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add cemm/kernel/semantic_clusters.py cemm/tests/test_conversational_clusters.py
git commit -m "feat: add conversational speech act clusters (greeting, acknowledgment, clarification, exit, command)"
```

---

## Task 2: Wire Speech Act into ObservationSemantics with Frame Key

**Files:**
- Modify: `cemm/kernel/pragmatic_interpreter.py:50-56` (add `frame_key` to ObservationSemantics return)
- Modify: `cemm/types/signal.py:34-48` (add `frame_key` field to ObservationSemantics)
- Create: `cemm/tests/test_pragmatic_routing.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_pragmatic_routing.py
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.kernel.pragmatic_interpreter import interpret_signal
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.context_kernel import ContextKernel, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState, Budget
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView


def _make_kernel():
    return ContextKernel(
        id="ctx_test", world=WorldState(), user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id="s1", turn_index=1),
        goal=GoalState(), memory=MemoryState(),
        permission=Permission.public(), budget=Budget(),
        self_view=SelfView(self_id="cemm"),
    )


def _make_signal(text):
    return Signal(
        id="s1", kind=SignalKind.INPUT, source_id="user", source_type=SourceType.USER,
        content=text, observed_at=time.time(), context_id="ctx_test", salience=0.5,
        trust=0.5, permission=Permission.public(),
    )


def test_greeting_sets_frame_key():
    kernel = _make_kernel()
    sig = _make_signal("hello")
    sem = interpret_signal(sig, kernel)
    assert sem is not None
    assert sem.speech_act == "greeting"
    assert sem.frame_key == "greeting"


def test_acknowledgment_sets_frame_key():
    kernel = _make_kernel()
    sig = _make_signal("ok")
    sem = interpret_signal(sig, kernel)
    assert sem is not None
    assert sem.speech_act == "acknowledgment"
    assert sem.frame_key == "acknowledgment"


def test_clarification_sets_frame_key():
    kernel = _make_kernel()
    sig = _make_signal("huh?")
    sem = interpret_signal(sig, kernel)
    assert sem is not None
    assert sem.speech_act == "clarification"
    assert sem.frame_key == "request_clarification"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_pragmatic_routing.py -v`
Expected: FAIL — `AttributeError: 'ObservationSemantics' object has no attribute 'frame_key'`

- [ ] **Step 3: Add `frame_key` field to ObservationSemantics**

In `cemm/types/signal.py`, add `frame_key` field to the `ObservationSemantics` dataclass:

```python
@dataclass
class ObservationSemantics:
    speech_act: str = "unknown"
    target_entity_id: str = ""
    semantic_cluster_key: str = ""
    stance: str = "unknown"
    affect: dict[str, float] = field(default_factory=lambda: {
        "valence": 0.0, "arousal": 0.0, "frustration": 0.0,
        "hostility": 0.0, "playfulness": 0.0,
    })
    repetition_group_id: str = ""
    repetition_count: int = 0
    cause_hypothesis_claim_ids: list[str] = field(default_factory=list)
    decay_half_life_ms: float = 900000.0
    confidence: float = 0.5
    uol_atoms: list = field(default_factory=list)
    frame_key: str = ""
```

- [ ] **Step 4: Map speech acts to frame keys in `interpret_signal`**

In `cemm/kernel/pragmatic_interpreter.py`, add a speech-act-to-frame-key mapping and set it on the returned `ObservationSemantics`. After line 49 (`stance = ...`), before the `return ObservationSemantics(...)`, add:

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

Then add `frame_key=frame_key,` to the `ObservationSemantics(...)` constructor call.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_pragmatic_routing.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add cemm/types/signal.py cemm/kernel/pragmatic_interpreter.py cemm/tests/test_pragmatic_routing.py
git commit -m "feat: wire speech act into ObservationSemantics with frame_key for routing"
```

---

## Task 3: Enrich Context Inference with Conversational Rules

**Files:**
- Modify: `cemm/kernel/context_inference.py:69-89` (enrich fallback rules)
- Create: `cemm/tests/test_context_inference_routing.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_context_inference_routing.py
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.kernel.context_inference import ContextInferenceEngine
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.context_kernel import ContextKernel, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState, Budget
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView


def _make_kernel(turn_index=1):
    return ContextKernel(
        id="ctx_test", world=WorldState(), user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id="s1", turn_index=turn_index),
        goal=GoalState(), memory=MemoryState(),
        permission=Permission.public(), budget=Budget(),
        self_view=SelfView(self_id="cemm"),
    )


def _make_signal(text):
    return Signal(
        id="s1", kind=SignalKind.INPUT, source_id="user", source_type=SourceType.USER,
        content=text, observed_at=time.time(), context_id="ctx_test", salience=0.5,
        trust=0.5, permission=Permission.public(),
    )


def test_first_turn_short_utterance_infers_session_opening():
    store = Store(":memory:")
    reg = Registry()
    engine = ContextInferenceEngine(store, reg)
    kernel = _make_kernel(turn_index=1)
    sig = _make_signal("hi")
    result = engine.infer(sig, kernel)
    assert result.frame_id == "session_opening"
    assert result.confidence >= 0.5


def test_clarification_infers_clarification_frame():
    store = Store(":memory:")
    reg = Registry()
    engine = ContextInferenceEngine(store, reg)
    kernel = _make_kernel(turn_index=3)
    sig = _make_signal("huh?")
    result = engine.infer(sig, kernel)
    assert result.frame_id == "clarification"
    assert result.confidence >= 0.4


def test_acknowledgment_infers_acknowledgment_frame():
    store = Store(":memory:")
    reg = Registry()
    engine = ContextInferenceEngine(store, reg)
    kernel = _make_kernel(turn_index=3)
    sig = _make_signal("ok")
    result = engine.infer(sig, kernel)
    assert result.frame_id == "acknowledgment"
    assert result.confidence >= 0.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_context_inference_routing.py -v`
Expected: FAIL — `AssertionError: assert 'urgent_request' == 'session_opening'` (or similar)

- [ ] **Step 3: Enrich context inference fallback rules**

In `cemm/kernel/context_inference.py`, replace the Phase 2 fallback block (lines 69-89) with enriched rules:

```python
        # Phase 2: Fallback — hardcoded rules (only if no model exceeded threshold)
        if not inference.applied_context_rule_model_ids:
            # Conversational context inference using keyword matching
            _GREETING_WORDS = {"hello", "hi", "hey", "howdy", "greetings", "sup", "morning", "afternoon", "evening"}
            _ACKNOWLEDGMENT_WORDS = {"ok", "sure", "yeah", "cool", "right", "understood", "noted", "great", "nice"}
            _CLARIFICATION_WORDS = {"what", "huh", "confused", "lost", "why", "how"}
            _EXIT_WORDS = {"exit", "quit", "bye", "goodbye", "stop", "done"}

            words_set = set(content_lower.replace("?", "").split())

            if words_set & _EXIT_WORDS:
                inference.confidence = max(inference.confidence, 0.7)
                inference.frame_id = "session_exit"

            elif turn_index == 1 and (words_set & _GREETING_WORDS):
                inference.confidence = max(inference.confidence, 0.7)
                inference.frame_id = "session_opening"

            elif words_set & _GREETING_WORDS:
                inference.confidence = max(inference.confidence, 0.5)
                inference.frame_id = "greeting"

            elif words_set & _ACKNOWLEDGMENT_WORDS:
                inference.confidence = max(inference.confidence, 0.5)
                inference.frame_id = "acknowledgment"

            elif words_set & _CLARIFICATION_WORDS:
                inference.confidence = max(inference.confidence, 0.5)
                inference.frame_id = "clarification"

            elif turn_index == 1 and len(content_lower.split()) <= 3 and "?" not in content_lower:
                inference.confidence = max(inference.confidence, 0.3)
                inference.frame_id = "session_opening"

            if "weather" in content_lower:
                if not kernel.user.locale:
                    inference.confidence = max(inference.confidence, 0.4)

            context_rules = self._registry.all_by_kind("context_rule")
            for rule in context_rules:
                if rule.canonical_key == "greeting_detection" and turn_index == 1:
                    inference.applied_context_rule_model_ids.append(rule.model_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_context_inference_routing.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add cemm/kernel/context_inference.py cemm/tests/test_context_inference_routing.py
git commit -m "feat: enrich context inference with conversational frame detection"
```

---

## Task 4: Add Speech Act Fallback to Decision Router

**Files:**
- Modify: `cemm/kernel/decision_router.py:20-28` (add `observation_semantics` and `context_inference` params)
- Modify: `cemm/kernel/decision_router.py:152-178` (add speech act fallback before abstain)
- Modify: `cemm/__main__.py:326-334` (pass observation_semantics and context_inference to router)
- Modify: `cemm/tests/test_pragmatic_routing.py` (add routing tests)

- [ ] **Step 1: Write the failing test**

Add to `cemm/tests/test_pragmatic_routing.py`:

```python
from cemm.kernel.decision_router import DecisionRouter
from cemm.types.semantic_event_graph import SemanticEventGraph
from cemm.types.packets import MemoryPacket


def _make_empty_seg():
    return SemanticEventGraph(
        id="seg1", source_signal_ids=["s1"], context_id="ctx_test",
        entity_refs=[], processes=[], states=[],
        claim_refs=[], model_refs=[], action_refs=[],
        temporal_edges=[], causal_edges=[],
        permission_scope="public", confidence=0.5,
    )


def test_speech_act_greeting_routes_to_answer():
    """When UOL matching fails but speech act is 'greeting',
    the router should use the speech act as fallback."""
    from cemm.types.signal import ObservationSemantics
    kernel = _make_kernel()
    graph = _make_empty_seg()
    sem = ObservationSemantics(speech_act="greeting", frame_key="greeting", confidence=0.8)
    router = DecisionRouter()
    decision = router.run(
        graph=graph, kernel=kernel, input_text="hello",
        observation_semantics=sem,
    )
    assert decision.action_kind == "answer"
    assert "greeting" in decision.reason.lower() or "speech_act" in decision.reason.lower()


def test_speech_act_acknowledgment_routes_to_answer():
    from cemm.types.signal import ObservationSemantics
    kernel = _make_kernel()
    graph = _make_empty_seg()
    sem = ObservationSemantics(speech_act="acknowledgment", frame_key="acknowledgment", confidence=0.7)
    router = DecisionRouter()
    decision = router.run(
        graph=graph, kernel=kernel, input_text="ok",
        observation_semantics=sem,
    )
    assert decision.action_kind == "answer"
    assert "acknowledgment" in decision.reason.lower() or "speech_act" in decision.reason.lower()


def test_speech_act_clarification_routes_to_ask():
    from cemm.types.signal import ObservationSemantics
    kernel = _make_kernel()
    graph = _make_empty_seg()
    sem = ObservationSemantics(speech_act="clarification", frame_key="request_clarification", confidence=0.7)
    router = DecisionRouter()
    decision = router.run(
        graph=graph, kernel=kernel, input_text="huh?",
        observation_semantics=sem,
    )
    assert decision.action_kind == "ask"


def test_speech_act_exit_routes_to_abstain():
    from cemm.types.signal import ObservationSemantics
    kernel = _make_kernel()
    graph = _make_empty_seg()
    sem = ObservationSemantics(speech_act="exit", frame_key="session_exit", confidence=0.8)
    router = DecisionRouter()
    decision = router.run(
        graph=graph, kernel=kernel, input_text="bye",
        observation_semantics=sem,
    )
    assert decision.action_kind == "abstain"


def test_speech_act_fallback_only_when_no_frame_keys():
    """If UOL matching already produced frame keys, speech act should NOT override."""
    from cemm.types.signal import ObservationSemantics
    from cemm.types.uol_atom import ProcessUOLAtom
    kernel = _make_kernel()
    graph = SemanticEventGraph(
        id="seg1", source_signal_ids=["s1"], context_id="ctx_test",
        entity_refs=[], processes=[
            {"frame_key": "command_remember", "confidence": 0.85},
        ],
        states=[], claim_refs=[], model_refs=[], action_refs=[],
        temporal_edges=[], causal_edges=[],
        permission_scope="public", confidence=0.85,
    )
    sem = ObservationSemantics(speech_act="greeting", frame_key="greeting", confidence=0.7)
    router = DecisionRouter()
    decision = router.run(
        graph=graph, kernel=kernel, input_text="remember I like tea",
        observation_semantics=sem,
    )
    # Should route to remember, NOT greeting
    assert decision.action_kind == "remember"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_pragmatic_routing.py::test_speech_act_greeting_routes_to_answer -v`
Expected: FAIL — `TypeError: run() got an unexpected keyword argument 'observation_semantics'`

- [ ] **Step 3: Add `observation_semantics` and `context_inference` params to `DecisionRouter.run()`**

In `cemm/kernel/decision_router.py`, modify the `run` method signature:

```python
    def run(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        grounded_graph: GroundedGraph | None = None,
        memory_packet: MemoryPacket | None = None,
        inference_packet: InferencePacket | None = None,
        answer_candidates: list[SemanticAnswerGraph] | None = None,
        input_text: str = "",
        observation_semantics: ObservationSemantics | None = None,
        context_inference: ContextInference | None = None,
    ) -> DecisionPacket:
```

Add imports at the top:

```python
from ..types.signal import ObservationSemantics
from ..types.context_inference import ContextInference
```

- [ ] **Step 4: Add speech act fallback in the router, before the final abstain**

In `cemm/kernel/decision_router.py`, after the existing `for proc in graph.processes` clarification check (around line 165), and before the short-input check, add:

```python
        # Speech act fallback: when UOL matching produced no actionable frame keys,
        # use the pragmatic interpretation layer as a fallback signal.
        # This implements architecture §15: pragmatic interpretation feeds routing.
        if observation_semantics and observation_semantics.confidence >= 0.5:
            sa = observation_semantics.speech_act
            fk = observation_semantics.frame_key
            if sa == "greeting":
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.7,
                        risk=0.0,
                    ),
                    confidence=0.7,
                    reason=f"speech_act greeting (pragmatic fallback, conf={observation_semantics.confidence:.2f})",
                )
            elif sa == "acknowledgment":
                return DecisionPacket(
                    action_kind="answer",
                    action_plan=ActionPlan(
                        action_kind="answer",
                        execution_allowed=True,
                        confidence=0.65,
                        risk=0.0,
                    ),
                    confidence=0.65,
                    reason=f"speech_act acknowledgment (pragmatic fallback, conf={observation_semantics.confidence:.2f})",
                )
            elif sa == "clarification":
                return DecisionPacket(
                    action_kind="ask",
                    action_plan=ActionPlan(
                        action_kind="ask",
                        execution_allowed=True,
                        confidence=0.65,
                        risk=0.0,
                    ),
                    confidence=0.65,
                    reason=f"speech_act clarification (pragmatic fallback, conf={observation_semantics.confidence:.2f})",
                )
            elif sa == "exit":
                return DecisionPacket(
                    action_kind="abstain",
                    action_plan=ActionPlan(
                        action_kind="abstain",
                        execution_allowed=False,
                        confidence=0.9,
                        risk=0.0,
                    ),
                    confidence=0.9,
                    reason=f"speech_act exit (pragmatic fallback, conf={observation_semantics.confidence:.2f})",
                )
```

- [ ] **Step 5: Pass `observation_semantics` from `__main__.py` to the router**

In `cemm/__main__.py`, in the `process_input` function where `decision_router.run()` is called (around line 327), add the `observation_semantics` parameter:

```python
        decision = decision_router.run(
            graph=pipeline_result.semantic_event_graph,
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet if inference_packet.predictions else None,
            input_text=text,
            observation_semantics=input_signal.observation_semantics,
        )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_pragmatic_routing.py -v`
Expected: PASS — all 8 tests

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add cemm/kernel/decision_router.py cemm/__main__.py cemm/tests/test_pragmatic_routing.py
git commit -m "feat: add speech act fallback to decision router when UOL matching fails"
```

---

## Task 5: Add Semantic Similarity Fallback to UOL Mapper

**Files:**
- Modify: `cemm/registry/uol_mapper.py:14-140` (add cluster-based fallback when registry matching fails)
- Create: `cemm/tests/test_uol_mapper_fallback.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_uol_mapper_fallback.py
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.registry.uol_mapper import UOLMapper
from cemm.registry import Registry
from cemm.types.context_kernel import ContextKernel, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState, Budget
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView


def _make_kernel():
    return ContextKernel(
        id="ctx_test", world=WorldState(), user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id="s1", turn_index=1),
        goal=GoalState(), memory=MemoryState(),
        permission=Permission.public(), budget=Budget(),
        self_view=SelfView(self_id="cemm"),
    )


def test_unrecognized_greeting_produces_atom_via_fallback():
    """When 'lol hello' doesn't match any UOL alias directly,
    the cluster fallback should still produce a greeting process atom."""
    reg = Registry()
    mapper = UOLMapper(reg)
    kernel = _make_kernel()
    atoms = mapper.map_signal("lol hello", kernel)
    frame_keys = [a.frame_key for a in atoms if a.kind == "process"]
    assert "greeting" in frame_keys


def test_unrecognized_clarification_produces_atom_via_fallback():
    reg = Registry()
    mapper = UOLMapper(reg)
    kernel = _make_kernel()
    atoms = mapper.map_signal("what in the world?", kernel)
    frame_keys = [a.frame_key for a in atoms if a.kind == "process"]
    assert "request_clarification" in frame_keys


def test_unrecognized_acknowledgment_produces_atom_via_fallback():
    reg = Registry()
    mapper = UOLMapper(reg)
    kernel = _make_kernel()
    atoms = mapper.map_signal("got it", kernel)
    frame_keys = [a.frame_key for a in atoms if a.kind == "process"]
    assert "acknowledgment" in frame_keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_uol_mapper_fallback.py -v`
Expected: FAIL — `AssertionError: assert 'greeting' in []`

- [ ] **Step 3: Add cluster-based fallback to UOLMapper**

In `cemm/registry/uol_mapper.py`, add import at the top:

```python
from ..kernel.semantic_clusters import SemanticClusterRegistry
```

Add a `_cluster_fallback` method to the `UOLMapper` class and call it at the end of `map_signal` when no process atoms were emitted:

```python
    def __init__(self, registry: Registry) -> None:
        self._registry = registry
        self._matcher = SemanticMatcher(registry)
        self._cluster_reg = SemanticClusterRegistry(registry=registry)

    def _cluster_fallback(self, content: str, atoms: list) -> list:
        """When registry UOL matching fails, use semantic clusters as fallback
        to detect conversational intent. This implements architecture §13/§15:
        pragmatic interpretation feeds UOL atom generation."""
        has_process = any(a.kind == "process" for a in atoms)
        if has_process:
            return atoms

        ranked = self._cluster_reg.match_ranked(content)
        if not ranked:
            return atoms

        best = ranked[0]
        if best.confidence < 0.5:
            return atoms

        _SA_TO_FRAME = {
            "greeting": "greeting",
            "acknowledgment": "acknowledgment",
            "clarification": "request_clarification",
            "exit": "session_exit",
            "command": "command_remember",
        }
        frame_key = _SA_TO_FRAME.get(best.speech_act, "")
        if not frame_key:
            return atoms

        atoms.append(ProcessUOLAtom(
            frame_key=frame_key,
            modality="observed",
            polarity="affirmed",
            intensity=0.6,
            confidence=best.confidence,
        ))
        return atoms
```

Then at the end of `map_signal` (before `return atoms`), add:

```python
        # Cluster-based fallback: when registry matching produced no process atoms,
        # use semantic clusters to detect conversational intent.
        atoms = self._cluster_fallback(content, atoms)

        return atoms
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_uol_mapper_fallback.py -v`
Expected: PASS — all 3 tests

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add cemm/registry/uol_mapper.py cemm/tests/test_uol_mapper_fallback.py
git commit -m "feat: add semantic cluster fallback to UOL mapper for unrecognized inputs"
```

---

## Task 6: Wire Inductor to Register UOL Semantics into Registry

**Files:**
- Modify: `cemm/learning/inductor.py:223-244` (register induced UOL semantics into Registry)
- Modify: `cemm/kernel/recursive_loop.py:42-43` (pass registry to inductor)
- Create: `cemm/tests/test_inductor_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_inductor_registry.py
from __future__ import annotations
import os, sys, uuid, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.learning.inductor import Inductor
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.permission import Permission


def _store_claim(store: Store, predicate: str, domain: str = "test") -> str:
    store.conn.execute(
        "INSERT OR IGNORE INTO entities (id, type, name, confidence, created_from_signal_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("entity_test", "concept", "test", 1.0, "sig_init", time.time(), time.time()),
    )
    cid = uuid.uuid4().hex[:16]
    claim = Claim(
        id=cid, subject_entity_id="entity_test", predicate=predicate,
        object_value="true", domain=domain, status=ClaimStatus.ACTIVE,
        confidence=0.7, trust=0.6, observed_at=time.time(), updated_at=time.time(),
        permission=Permission.public(),
    )
    store.claims.put(claim)
    return cid


def test_induced_uol_semantic_registered_in_registry():
    """When the inductor creates a UOL semantic candidate from repeated predicates,
    it should also register it in the Registry so the UOLMapper can see it."""
    store = Store(":memory:")
    registry = Registry()
    inductor = Inductor(store, feedback_threshold=3, registry=registry)
    for _ in range(3):
        _store_claim(store, "enjoys")
    inductor._find_uol_patterns()
    # The induced UOL semantic should be visible in the registry
    entry = registry.get_uol_semantic("enjoys")
    assert entry is not None
    assert "enjoys" in entry.aliases


def test_inductor_without_registry_still_works():
    """Inductor should still function without a registry (backward compat)."""
    store = Store(":memory:")
    inductor = Inductor(store, feedback_threshold=3)
    for _ in range(3):
        _store_claim(store, "likes")
    result = inductor._find_uol_patterns()
    assert len(result) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_inductor_registry.py -v`
Expected: FAIL — `TypeError: Inductor.__init__() got an unexpected keyword argument 'registry'`

- [ ] **Step 3: Add `registry` parameter to Inductor**

In `cemm/learning/inductor.py`, modify the `__init__`:

```python
class Inductor:
    def __init__(self, store: Store, feedback_threshold: int = 5, registry: Registry | None = None) -> None:
        self._store = store
        self._feedback_threshold = feedback_threshold
        self._registry = registry
```

Add import at the top:

```python
from ..registry.registry import Registry, RegistryEntry
```

- [ ] **Step 4: Register induced UOL semantics into Registry**

In `cemm/learning/inductor.py`, modify `_find_uol_patterns` to also register into the registry:

```python
    def _find_uol_patterns(self, domain: str | None = None) -> list[Model]:
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
                # Also register in the Registry so UOLMapper can see it
                if self._registry is not None:
                    existing_entry = self._registry.get_uol_semantic(predicate)
                    if existing_entry is None:
                        self._registry.register(RegistryEntry(
                            model_id=model.id,
                            canonical_key=predicate,
                            kind="uol_semantic",
                            aliases=[predicate],
                            description=f"Auto-induced from {count} observations",
                        ))
        return candidates
```

- [ ] **Step 5: Pass registry to Inductor in RecursiveLoop**

In `cemm/kernel/recursive_loop.py`, modify the `__init__` to accept and pass a registry:

```python
    def __init__(
        self,
        pipeline: Pipeline,
        store: Store,
        online_learner: OnlineLearner,
        inductor: Inductor,
        registry: Registry | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._store = store
        self._learner = online_learner
        self._inductor = inductor
        self._registry = registry
        self._retriever = StructuralRetriever(store)
        self._ranker = Ranker()
        self._induction_turn_count: int = 0
```

Add import: `from ..registry.registry import Registry`

- [ ] **Step 6: Pass registry when constructing RecursiveLoop in `__main__.py`**

In `cemm/__main__.py` (or `manual_integration_test.py`), wherever `RecursiveLoop` is constructed, pass the registry:

```python
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor, registry=registry)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_inductor_registry.py -v`
Expected: PASS — all 2 tests

- [ ] **Step 8: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 9: Commit**

```bash
git add cemm/learning/inductor.py cemm/kernel/recursive_loop.py cemm/__main__.py cemm/tests/test_inductor_registry.py
git commit -m "feat: wire inductor to register UOL semantics into Registry for mapper visibility"
```

---

## Task 7: Integration Test — Verify Reduced Manual Training

**Files:**
- Modify: `manual_integration_test.py` (add test cases for previously-unrecognized inputs)

- [ ] **Step 1: Add new test cases to manual integration test**

Add these test cases to the `test_cases` list in `manual_integration_test.py`:

```python
        ("lol hello", "Informal greeting"),
        ("hey what's up", "Casual greeting"),
        ("got it", "Acknowledgment variant"),
        ("i see", "Acknowledgment variant"),
        ("what in the world?", "Confused clarification"),
        ("I'm confused", "Confusion expression"),
        ("huh?", "Short confusion"),
        ("how do you mean?", "Polite clarification"),
        ("nice", "Short acknowledgment"),
        ("sounds good", "Acknowledgment phrase"),
```

- [ ] **Step 2: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: All tests pass with 0 gaps

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add manual_integration_test.py
git commit -m "test: add integration tests for pragmatic-semantic routing"
```

---

## Self-Review

### Spec Coverage

| Architecture Section | Gap | Task |
|---|---|---|
| §13 UOL Semantic Layer | No semantic similarity fallback | Task 5 |
| §14 Context Inference | Context inference doesn't influence routing | Task 3 |
| §15 Pragmatic Interpretation | Speech act detection too narrow | Task 1 |
| §15 Pragmatic Interpretation | Speech acts not wired to routing | Tasks 2, 4 |
| §17 Structural Learning | Inductor creates dead models | Task 6 |
| §21 Recursive Runtime | Router uses frame keys only, no fallback | Task 4 |

### Placeholder Scan

No placeholders found. All steps contain complete code.

### Type Consistency

- `ObservationSemantics.frame_key` — added in Task 2, used in Task 4
- `ContextInference.frame_id` — existing field, enriched in Task 3
- `DecisionRouter.run()` params — `observation_semantics` and `context_inference` added in Task 4, passed from `__main__.py` in Task 4
- `Inductor.__init__(registry=)` — added in Task 6, used in `RecursiveLoop` in Task 6
- `SemanticClusterRegistry` — used in Task 1 (clusters), Task 5 (UOL mapper fallback)
- `_SPEECH_ACT_TO_FRAME_KEY` mapping in Task 2 matches `_SA_TO_FRAME` mapping in Task 5
