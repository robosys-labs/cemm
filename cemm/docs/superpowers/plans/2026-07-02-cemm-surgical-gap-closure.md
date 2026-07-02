# CEMM Surgical Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the highest-impact deterministic gaps that violate the CEMM architecture's SLC routing and SAG-first realization rules: memory-query/command confusion, self-intent loss, operator hardcoded text, and missing user-profile memory lane.

**Architecture:** Anchor every fix to the canonical runtime shape:

```text
Signal -> ContextKernel -> SEG -> Decide -> SAG/ActionPlan -> Realize -> Verify -> Trace
```

No operator emits user-facing text without first constructing a `SemanticAnswerGraph` and running it through `RealizationPipeline`. Routing decisions use graph packets and selected evidence, not raw-text string matching.

**Tech Stack:** Python 3, existing CEMM types, pytest, `RealizationPipeline`, `SemanticAnswerGraph`, `DecisionRouter`, `AnswerOperator`, `RememberOperator`, `LearnOperator`, `AskOperator`, `Claim`, `Store`.

---

## File Structure Map

| File | Responsibility |
|------|----------------|
| `cemm/kernel/decision_router.py` | Decides `action_kind` and intent from SEG + selected claims. Fix: guard `remember` command against memory-query interrogatives. Route user identity/name queries to profile lane first. |
| `cemm/operators/answer.py` | Builds SAG for answer actions. Fix: propagate `self_*_query` intents from decision router. |
| `cemm/operators/remember.py` | Stores claims. Fix: build SAG with intent `remember` and selected claim, run realizer, remove hardcoded output. Detect user-profile statements and store them in profile lane. |
| `cemm/operators/learn.py` | Stores lexeme mappings. Fix: build SAG with intent `learn_*` and run realizer instead of returning a hardcoded string. |
| `cemm/operators/ask.py` | Builds SAG for clarification. Fix: ensure the question is in SAG `entity_refs` and realization handles the template. |
| `cemm/synthesis/template.py` | Template dictionary. Add templates for `learn_command_alias`, `learn_lexeme`, `learn_correction`. |
| `cemm/store/profile_store.py` | New lightweight profile lane on top of `ClaimStore`. |
| `cemm/store/store.py` | Wire `profile` property. |
| `cemm/tests/test_surgical_gap_closure.py` | New regression tests for all four gaps. |

---

## Task 1: Guard `remember` command against memory-query interrogatives

**Files:**
- Modify: `cemm/kernel/decision_router.py:571-594`
- Test: `cemm/tests/test_surgical_gap_closure.py`

- [ ] **Step 1: Write the failing test**

```python
def test_memory_query_not_remember_command(decision_router: DecisionRouter, kernel: ContextKernel, store: Store) -> None:
    seg = SemanticEventGraph(
        id="1",
        source_signal_ids=["s1"],
        context_id=kernel.id,
        processes=[{"frame_key": "command_remember"}],
        confidence=0.7,
    )
    packet = decision_router.decide(
        graph=seg,
        kernel=kernel,
        store=store,
        input_text="do you remember me?",
        selected_claim_ids=[],
    )
    assert packet.action_kind != "remember"
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py::test_memory_query_not_remember_command -v
```

Expected: `AssertionError` because `action_kind == "remember"`.

- [ ] **Step 3: Implement the guard**

In `DecisionRouter.run`, compute a language-agnostic `is_question` flag from the terminal `?` and from question frames in the SEG (`ask_question`, `request_clarification`, `unknown_intent`). Pass this flag into `_detect_command_intent`. The remember command only fires when `command_remember` is in the SEG and `is_question` is False. This avoids all English-specific string matching in routing.

```python
# In run()
question_frames = {"ask_question", "request_clarification", "unknown_intent"}
is_question = input_lower.endswith("?") or bool(graph_frame_keys & question_frames)

# In _detect_command_intent(..., is_question: bool = False)
if "command_remember" in frame_keys and not is_question:
    return DecisionPacket(action_kind="remember", ...)
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py::test_memory_query_not_remember_command -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cemm/kernel/decision_router.py cemm/tests/test_surgical_gap_closure.py
git commit -m "fix(router): guard remember command against memory-query interrogatives"
```

---

## Task 2: Propagate self-query intents through AnswerOperator

**Files:**
- Modify: `cemm/operators/answer.py:31-43`
- Test: `cemm/tests/test_surgical_gap_closure.py`

- [ ] **Step 1: Write the failing test**

```python
def test_self_capability_intent_preserved(answer_operator: AnswerOperator, operator_context: OperatorContext) -> None:
    operator_context.params["decision_reason"] = "self query (self_capability_query) answered from verified claims"
    operator_context.params["intent"] = "self_capability"
    operator_context.params["selected_claim_ids"] = ["c1"]
    result = answer_operator.execute(operator_context)
    assert result.semantic_answer_graph.intent == "self_capability"
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py::test_self_capability_intent_preserved -v
```

Expected: `AssertionError` because the intent is overwritten to `answer`.

- [ ] **Step 3: Implement the fix**

In `AnswerOperator.execute`, before the fallback intent logic, preserve an explicit `self_*_query` intent that is already in `ctx.params` or infer it from `decision_reason`:

```python
intent = ctx.params.get("intent", "")
decision_reason = ctx.params.get("decision_reason", "")
reason_lower = decision_reason.lower()
if not intent:
    if "self_identity_query" in reason_lower:
        intent = "self_identity_query"
    elif "self_capability_query" in reason_lower:
        intent = "self_capability_query"
    elif "self_knowledge_query" in reason_lower:
        intent = "self_knowledge_query"
    elif "greeting" in reason_lower and not selected_claims:
        intent = "greeting"
    elif "acknowledgment" in reason_lower and not selected_claims:
        intent = "acknowledgment"
```

Also ensure `self_capability_query` is mapped to the `self_capability` realization intent in the SAG:

```python
sag_intent = intent.replace("_query", "") if intent.startswith("self_") else intent
answer_graph = SemanticAnswerGraph(..., intent=sag_intent, ...)
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py::test_self_capability_intent_preserved -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cemm/operators/answer.py cemm/tests/test_surgical_gap_closure.py
git commit -m "fix(answer): propagate self-query intents to SAG"
```

---

## Task 3: Move operator hardcoded text into SAG-driven realization

**Files:**
- Modify: `cemm/operators/learn.py`, `cemm/operators/remember.py`, `cemm/operators/ask.py`
- Modify: `cemm/synthesis/template.py:35-61`
- Test: `cemm/tests/test_surgical_gap_closure.py`

- [ ] **Step 1: Write failing tests**

```python
def test_learn_operator_uses_sag_realization(learn_operator: LearnOperator, operator_context: OperatorContext) -> None:
    operator_context.params["teaching_event"] = {
        "kind": "command_alias",
        "surface": "zibble",
        "meaning": "remember this",
        "role": "command_alias",
        "confidence": 0.7,
    }
    result = learn_operator.execute(operator_context)
    assert result.semantic_answer_graph is not None
    assert result.semantic_answer_graph.intent == "learn_command_alias"


def test_remember_operator_uses_sag_realization(remember_operator: RememberOperator, operator_context: OperatorContext) -> None:
    operator_context.params["text"] = "my friend nathan likes mangoes"
    result = remember_operator.execute(operator_context)
    assert result.semantic_answer_graph is not None
    assert result.semantic_answer_graph.intent == "remember"
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py::test_learn_operator_uses_sag_realization cemm/tests/test_surgical_gap_closure.py::test_remember_operator_uses_sag_realization -v
```

Expected: `AttributeError` because `semantic_answer_graph` is `None`.

- [ ] **Step 3: Create language-indexed response templates**

Create `cemm/data/response_templates.json` with a top-level language key and UOL-intent sub-keys. The variables must be SAG-derived (`surface`, `meaning`). English is the default seed; other languages are added as data, not code.

```json
{
  "meta": { "default_language": "en" },
  "en": {
    "learn_command_alias": "Got it. When you say '{surface}', I'll remember that.",
    "learn_lexeme": "Got it. '{surface}' means '{meaning}'.",
    "learn_correction": "Thanks. I've updated '{surface}' to mean '{meaning}'."
  }
}
```

In `cemm/synthesis/template.py`, load templates from this file and select the language from `kernel.user.locale` or `kernel.world.assistant_locale`.

- [ ] **Step 4: Implement SAG-driven realization in LearnOperator**

Replace the hardcoded `output` strings with a `SemanticAnswerGraph` whose intent matches the teaching event kind, and run it through `RealizationPipeline`:

```python
from ..synthesis.realizer import RealizationPipeline
from ..types.semantic_answer_graph import SemanticAnswerGraph
import uuid

class LearnOperator(BaseOperator):
    def __init__(
        self,
        lexeme_memory: LexemeMemory | None = None,
        action_kind: ActionKind = ActionKind.LEARN_LEXEME,
    ) -> None:
        self._lexeme_memory = lexeme_memory
        self._action_kind = action_kind
        self._pipeline = RealizationPipeline()

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        # ... existing validation ...
        kind = event.get("kind", "definition")
        surface = event.get("surface", "").lower()
        meaning = event.get("meaning", "").lower()
        role = event.get("role", "unknown")
        confidence = event.get("confidence", 0.6)

        # Learn into lexeme memory (unchanged)
        if kind == "command_alias":
            lexeme_memory.learn(...)
        elif kind == "correction":
            lexeme_memory.learn(...)
            lexeme_memory.reinforce(...)
        else:
            lexeme_memory.learn(...)

        # Build SAG and realize
        sag_intent = "learn_command_alias" if kind == "command_alias" else "learn_correction" if kind == "correction" else "learn_lexeme"
        answer_graph = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent=sag_intent,
            source_signal_ids=[ctx.input_signal.id],
            context_id=ctx.kernel.id,
            selected_claim_ids=[],
            confidence=confidence,
            entity_refs=[{"kind": "teaching_event", "surface": surface, "meaning": meaning, "role": role}],
        )
        result = self._pipeline.run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
        output = result.output if result.success and result.verified else "I've noted that."

        # ... existing action/result_signal creation, but set semantic_answer_graph=answer_graph ...
```

- [ ] **Step 5: Implement SAG-driven realization in RememberOperator**

After creating the `Claim`, build a `SemanticAnswerGraph` with intent `remember` and selected claim, run the realizer, and use its output. Remove the fallback `I've stored that in this session.` string.

```python
answer_graph = SemanticAnswerGraph(
    id=uuid.uuid4().hex[:16],
    intent="remember",
    source_signal_ids=[ctx.input_signal.id],
    context_id=ctx.kernel.id,
    selected_claim_ids=[claim.id],
    confidence=0.7,
)
result = RealizationPipeline().run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
output = result.output if result.success and result.verified else "I've noted that."
```

- [ ] **Step 6: Ensure AskOperator uses a SAG with clarification entity**

`AskOperator` already builds a SAG; verify it places the question in `entity_refs` with `"kind": "clarification"` so `RealizationPipeline` can render the `ask_meaning` template or the explicit clarification template. No hardcoded `Could you clarify?` should remain in the success path; keep it only as a fallback for realization failure.

- [ ] **Step 7: Run the tests and confirm they pass**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add cemm/operators/learn.py cemm/operators/remember.py cemm/operators/ask.py cemm/synthesis/template.py cemm/tests/test_surgical_gap_closure.py
git commit -m "fix(operators): route all operator output through SAG + RealizationPipeline"
```

---

## Task 4: Add a lightweight user-profile memory lane

**Files:**
- Create: `cemm/store/profile_store.py`
- Modify: `cemm/store/store.py`
- Modify: `cemm/operators/remember.py`
- Modify: `cemm/kernel/decision_router.py`
- Test: `cemm/tests/test_surgical_gap_closure.py`

- [ ] **Step 1: Write the failing test**

```python
def test_profile_lane_stores_user_name(remember_operator: RememberOperator, operator_context: OperatorContext) -> None:
    operator_context.params.update({
        "subject_entity_id": "user",
        "predicate": "user.name",
        "object_value": "chibueze",
    })
    remember_operator.execute(operator_context)
    profile = operator_context.store.profile
    assert profile.get("name") == "chibueze"
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py::test_profile_lane_stores_user_name -v
```

Expected: `AttributeError` because `store.profile` does not exist.

- [ ] **Step 3: Create the profile lane**

Create `cemm/store/profile_store.py` as a thin wrapper over the existing `ClaimStore` (no new SQL schema). Profile facts are stored as claims with `domain="profile"`, `subject_entity_id="user"`, and a predicate in a controlled namespace (`user.name`, `user.alias`, `user.preference.*`).

```python
from __future__ import annotations
from ..types.claim import Claim, ClaimStatus
from ..types.permission import Permission

class ProfileStore:
    def __init__(self, claim_store):
        self._claim_store = claim_store

    def put(self, slot: str, value: str, source_id: str, permission: Permission | None = None, trust: float = 0.7) -> Claim:
        import uuid
        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id="user",
            predicate=f"user.{slot}",
            object_value=value,
            domain="profile",
            source_id=source_id,
            confidence=0.8,
            trust=trust,
            status=ClaimStatus.ACTIVE,
        )
        if permission is not None:
            claim.permission = permission
        self._claim_store.put(claim)
        return claim

    def get(self, slot: str) -> str | None:
        for claim in self._claim_store.find_by_subject("user"):
            if claim.domain == "profile" and claim.predicate == f"user.{slot}":
                return str(claim.object_value)
        return None
```

- [ ] **Step 4: Wire the profile lane into Store**

In `cemm/store/store.py`, expose `self.profile = ProfileStore(self.claims)` after `self.claims` is created.

- [ ] **Step 5: Detect user-profile statements in RememberOperator**

A fact is routed to the profile lane when the SEG/grounding layer has already identified the subject as the user entity (`subject_entity_id == "user"`) or the predicate is in the user namespace (`predicate.startswith("user.")`). No English string matching is used in the operator. The operator ensures the `user` entity exists in the entity store to satisfy the foreign-key constraint, then writes the profile claim.

```python
is_profile_fact = subject_id == "user" or predicate.startswith("user.")
if is_profile_fact:
    slot = predicate.removeprefix("user.") if predicate.startswith("user.") else predicate
    entity = ctx.store.entities.get("user")
    if entity is None:
        entity = Entity(id="user", type=EntityType.PERSON, name="user", ...)
        ctx.store.entities.put(entity)
    claim = ctx.store.profile.put(slot, raw_text, ctx.input_signal.source_id, ctx.kernel.permission)
    # ... build SAG with selected_claim_ids=[claim.id] ...
```

- [ ] **Step 6: Route user identity/name queries to the profile lane first**

In `DecisionRouter._matching_evidence_ids`, when `frame` is `user_identity_query` or `user_name_query`, first check `store.profile.get("name")`. If it exists, return a synthetic claim ID or use a dedicated profile claim. If the profile lane is empty, fall back to the existing identity-predicate search.

- [ ] **Step 7: Run the tests and confirm they pass**

```bash
python -m pytest cemm/tests/test_surgical_gap_closure.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add cemm/store/profile_store.py cemm/store/store.py cemm/operators/remember.py cemm/kernel/decision_router.py cemm/tests/test_surgical_gap_closure.py
git commit -m "feat(memory): add lightweight user-profile lane"
```

---

## Task 5: Invariant regression tests and full suite verification

**Files:**
- Test: `cemm/tests/test_surgical_gap_closure.py`

- [ ] **Step 1: Add invariant tests**

- No operator returns an `output_text` whose `semantic_answer_graph` is `None` for a successful operator action.
- No answer path drops a `self_*_query` intent when selected claims exist.
- No `remember` action is chosen for a memory-query interrogative.
- User profile facts are retrievable by the profile lane API.

- [ ] **Step 2: Run the full test suite**

```bash
python -m pytest cemm/tests -q --tb=short
```

Expected: all PASS (target: 80+ tests).

- [ ] **Step 3: Commit**

```bash
git add cemm/tests/test_surgical_gap_closure.py
git commit -m "test(gap-closure): invariant regression tests for surgical gap closure"
```

---

## Spec Coverage Check

| Gap | Task |
|-----|------|
| Memory-query misrouted as `remember` command | Task 1 |
| Self-query intent lost before realization | Task 2 |
| Operator hardcoded output text | Task 3 |
| Missing user-profile memory lane | Task 4 |
| No invariant tests for the above | Task 5 |

Remaining architectural gaps (closed in a follow-up pass):
- Hardcoded UOL semantic aliases in `__main__.py` and `registry/uol_mapper.py` → moved to `cemm/data/uol_semantics.json` and `cemm/data/predicates.json`; `UOLMapper` now loads query frames, pronouns, insult aliases, and question aliases from JSON.
- Hardcoded word lists in `surface_tagger.py` → moved to `cemm/data/surface_role_words.json`.
- Hardcoded word lists in `teaching_interpreter.py` → moved to `cemm/data/teaching_patterns.json` (triggers, stop words, role cues, meaning stop words).
- Hardcoded realization templates in `synthesis/template.py` → moved to `cemm/data/response_templates.json` (language-indexed, UOL-intent-keyed).
- Hardcoded canonical operator registration in `__main__.py` → metadata moved to `cemm/data/operators.json`.
- SAG-less training export paths → `__main__.py` passes `semantic_answer_graph` to `serialize_turn`; `training_export.py` includes SAG-derived records and trace metadata.
- Hardcoded English stop words, command words, causal/temporal relation markers, target prepositions, and named-entity extraction lists in `kernel/semantic_interpreter.py` → moved to `cemm/data/semantic_interpreter_words.json`.
- Hardcoded English causal connectors and phrase-extraction stop words in `learning/inductor.py` → moved to `cemm/data/semantic_interpreter_words.json`.
- Hardcoded English open-domain conversational intent phrases in `kernel/decision_router.py` (`_classify_general_question`) → replaced with data-driven SEG/UOL frame detection; new frames `story_request`, `food_recommendation_request`, and `recommendation_request` added to `cemm/data/uol_semantics.json`.

Tests: `cemm/tests/test_data_driven_semantic_layer.py` covers all of the above.

All identified deterministic shortcut gaps in this pass are now closed. The remaining architectural work is expanding the data files with non-English language seeds and generalizing the last English-specific stop-word heuristics (e.g., `teaching_interpreter._extract_command_alias`) when a language-agnostic pattern is available.
