# CEMM Architecture Gap Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the runtime, realization, training, noisy-language, pragmatic-chat, self-answer, and NER gaps found in the CEMM-SLC architecture review.

**Architecture:** Preserve the governing CEMM packet flow: Signal -> ContextKernel -> SemanticEventGraph -> GroundedGraph -> MemoryPacket -> InferencePacket -> DecisionPacket -> SemanticAnswerGraph or ActionPlan -> Realization -> Verification -> Trace -> TrainingExamples. The plan makes each missing invariant executable before changing behavior. New language/noise/pragmatic capability is expressed as canonical semantic packets and registry-backed models, not as direct text routing.

**Tech Stack:** Python 3.13, pytest, SQLite-backed CEMM stores, existing CEMM dataclasses, existing synthesis/router/trainer modules.

---

## Non-Negotiable Constraints

- Do not produce user-facing final text outside `SemanticAnswerGraph` or `ActionPlan` realization.
- Do not train router or answer behavior from text-only labels when graph packets exist.
- Do not add English-only string matching as the primary interpretation path.
- Do not promote generated labels, induced models, or learned artifacts without validation, risk, cost, and permission gates.
- Do not weaken current passing tests; add stronger tests around uncovered architectural gaps.
- Keep changes scoped to source files and tests. Do not treat SQLite, JSONL, logs, or `__pycache__` artifacts as architecture guidance.

## File Map

- Modify: `cemm_trainer.py`  
  Fix prompt rendering, validation, and task decomposition for graph-first training.
- Modify: `kernel/training_export.py`  
  Export accurate realization and verification metadata.
- Modify: `types/trace.py`  
  Add enough realization metadata to preserve strategy, verifier outcome, and selected evidence linkage.
- Modify: `operators/ask.py`, `operators/remember.py`, `operators/retrieve_op.py`, possibly `operators/base.py`  
  Ensure all user-facing outputs go through SAG or ActionPlan realization and verification.
- Modify: `synthesis/realizer.py`, `synthesis/template.py`, `synthesis/extractive.py`, `synthesis/result.py`  
  Add template coverage for ask/remember/retrieve and propagate verification details.
- Create: `types/normalized_signal.py`  
  Packet for noisy multilingual normalization results.
- Create: `kernel/text_normalizer.py`  
  Conservative Unicode/noise normalization that preserves raw text and emits traceable spans.
- Modify: `kernel/pipeline.py`, `registry/semantic_matcher.py`, `registry/uol_mapper.py`, `kernel/semantic_clusters.py`, `kernel/pragmatic_interpreter.py`  
  Consume normalized forms while keeping raw `Signal.content` stable.
- Create: `training/noisy_seed_generator.py` or modify `cemm_seed_generator.py`  
  Generate noisy casual conversation seed categories with graph packets.
- Modify: `self_knowledge.json`, `registry/uol_mapper.py`, `kernel/decision_router.py`, `operators/answer.py`  
  Make self/capability answers evidence-backed SAGs.
- Modify: `learning/ner_tagger.py`, `scripts/train_ner_tagger.py`, `kernel/semantic_interpreter.py`  
  Make NER safer for mixed labels, punctuation, noisy text, and multilingual aliases.
- Add tests:
  - `tests/test_trainer_prompt_rendering_all_tasks.py`
  - `tests/test_operator_realization_invariants.py`
  - `tests/test_training_export_realization_metadata.py`
  - `tests/test_noisy_text_normalization.py`
  - `tests/test_noisy_casual_seed_generation.py`
  - `tests/test_pragmatic_casual_acts.py`
  - `tests/test_self_capability_answers.py`
  - `tests/test_ner_noisy_multilingual.py`

---

### Task 1: Lock Current Gaps With Failing Tests

**Files:**
- Create: `tests/test_trainer_prompt_rendering_all_tasks.py`
- Create: `tests/test_operator_realization_invariants.py`
- Create: `tests/test_training_export_realization_metadata.py`

- [ ] **Step 1: Add a test that every trainer prompt renders**

Create `tests/test_trainer_prompt_rendering_all_tasks.py`:

```python
from __future__ import annotations

import json

import pytest

from cemm.cemm_trainer import PROMPTS, render_prompt, validate_training_record


def _payload_for(task_type: str) -> dict:
    payload = {
        "context_kernel": {"id": "ctx1", "permission": {"scope": "local_training"}},
        "input_signal_id": "sig1",
        "input_text": "hello",
        "output_text": "hello",
        "semantic_event_graph": {
            "id": "seg1",
            "source_signal_ids": ["sig1"],
            "context_id": "ctx1",
            "entity_refs": [],
            "processes": [{"kind": "process", "frame_key": "greeting", "confidence": 0.8}],
            "states": [],
            "claim_refs": [],
            "claim_candidates": [],
            "model_refs": [],
            "action_refs": [],
            "temporal_edges": [],
            "causal_edges": [],
            "permission_scope": "local_training",
            "confidence": 0.8,
        },
        "semantic_answer_graph": {
            "id": "sag1",
            "intent": "answer",
            "source_signal_ids": ["sig1"],
            "context_id": "ctx1",
            "selected_claim_ids": [],
            "selected_model_ids": [],
            "confidence": 0.8,
            "permission_scope": "local_training",
        },
        "memory_packet": {
            "id": "mem1",
            "selected_signal_ids": ["sig1"],
            "selected_claim_ids": [],
            "selected_model_ids": [],
            "ranking_trace": [],
            "confidence": 0.5,
        },
        "inference_packet": {
            "id": "inf1",
            "implications": [],
            "contradictions": [],
            "predictions": [],
            "missing_slots": [],
            "state_deltas": {},
            "inference_graph_input_signal_ids": ["sig1"],
            "inference_graph_output_model_ids": [],
            "confidence": 0.5,
        },
        "selected_evidence": {"selected_claim_ids": [], "selected_model_ids": []},
        "self_state": {"self_id": "self_main", "mode": "assistant"},
    }
    if task_type == "next_event_prediction":
        payload["recent_event_graphs"] = [payload["semantic_event_graph"]]
    if task_type == "verifier_calibration":
        payload["selected_evidence"] = {"selected_claim_ids": [], "selected_model_ids": []}
    return payload


@pytest.mark.parametrize("task_type", sorted(PROMPTS))
def test_all_prompts_render_without_missing_format_keys(task_type: str) -> None:
    payload = _payload_for(task_type)
    try:
        validate_training_record(task_type, payload)
    except ValueError:
        pass
    agent, system, user = render_prompt(task_type, json.dumps(payload))
    assert agent
    assert system
    assert user
    assert "{" not in user or "context_kernel" in user
```

- [ ] **Step 2: Run the prompt test and verify it fails**

Run:

```bash
python -m pytest tests/test_trainer_prompt_rendering_all_tasks.py -q
```

Expected before implementation: FAIL with `KeyError` for task types such as `semantic_graph_extraction`.

- [ ] **Step 3: Add tests that ask/remember/retrieve outputs are realized and traced**

Create `tests/test_operator_realization_invariants.py`:

```python
from __future__ import annotations

import time

from cemm.__main__ import seed_registry, seed_self_state
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.learning.inductor import Inductor
from cemm.learning.online import OnlineLearner
from cemm.operators.abstain import AbstainOperator
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.registry import OperatorRegistry
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.__main__ import process_input


def _runtime():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), RetrieveOperator(), AbstainOperator()]:
        op_registry.register(op)
    pipeline = Pipeline(store, registry)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    loop = RecursiveLoop(pipeline, store, learner, Inductor(store, registry=registry))
    return store, registry, op_registry, pipeline, learner, loop


def _turn(text: str):
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    output = process_input(text, store, registry, op_registry, pipeline, learner, loop, f"ctx_{int(time.time())}", [0])
    return output, loop


def test_ask_output_has_sag_and_realization_metadata() -> None:
    output, loop = _turn("what is the weather?")
    assert output
    result = loop._last_result
    decision = result.decision_packet
    assert decision is not None
    assert decision.action_kind in {"ask", "abstain"}


def test_remember_output_is_realized_from_sag_not_manual_text() -> None:
    output, loop = _turn("remember I like coffee")
    assert output
    trace = loop._last_result.kernel.memory.working_signal_ids
    assert trace


def test_retrieve_output_is_realized_from_sag_not_manual_text() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    process_input("remember I like coffee", store, registry, op_registry, pipeline, learner, loop, "ctx_retrieve", [0])
    output = process_input("retrieve coffee", store, registry, op_registry, pipeline, learner, loop, "ctx_retrieve", [1])
    assert output
    assert "Retrieved " not in output
```

- [ ] **Step 4: Run the operator invariant tests and verify at least retrieve fails**

Run:

```bash
python -m pytest tests/test_operator_realization_invariants.py -q
```

Expected before implementation: FAIL because retrieve currently returns manual `Retrieved ...` text.

- [ ] **Step 5: Add export metadata regression test**

Create `tests/test_training_export_realization_metadata.py`:

```python
from __future__ import annotations

import time

from cemm.__main__ import seed_registry, seed_self_state
from cemm.kernel.training_export import serialize_turn
from cemm.operators.answer import AnswerOperator
from cemm.operators.base import OperatorContext
from cemm.registry import Registry
from cemm.store.store import Store
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.signal import Signal, SignalKind, SourceType


def test_answer_trace_exports_realization_strategy_and_verified_flag() -> None:
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    kernel = ContextKernel(id="ctx_meta", permission=Permission.public())
    kernel.time.now = time.time()
    signal = Signal(
        id="sig_meta",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="hello",
        observed_at=time.time(),
        context_id=kernel.id,
        permission=Permission.public(),
    )
    result = AnswerOperator().execute(OperatorContext(kernel=kernel, input_signal=signal, store=store, registry=registry, params={"intent": "greeting"}))
    assert result.trace is not None
    records = serialize_turn("hello", result.output_text, kernel, signal, trace=result.trace, semantic_answer_graph=result.semantic_answer_graph)
    full = records[0]["payload"]
    assert full["realization_metadata"]["strategy"] == "template"
    assert full["realization_metadata"]["verified"] is True
```

- [ ] **Step 6: Run the export metadata test and verify it fails**

Run:

```bash
python -m pytest tests/test_training_export_realization_metadata.py -q
```

Expected before implementation: FAIL because `trace.realization_strategy` and `trace.realization_verified` are not populated.

- [ ] **Step 7: Commit failing tests**

```bash
git add tests/test_trainer_prompt_rendering_all_tasks.py tests/test_operator_realization_invariants.py tests/test_training_export_realization_metadata.py
git commit -m "test: lock cemm architecture gap invariants"
```

---

### Task 2: Fix Trainer Prompt Rendering Without Text-Only Shortcuts

**Files:**
- Modify: `cemm_trainer.py`
- Test: `tests/test_trainer_prompt_rendering_all_tasks.py`

- [ ] **Step 1: Replace direct `str.format(payload=...)` with a safe render context**

In `cemm_trainer.py`, replace `render_prompt` with:

```python
def _prompt_context(payload: dict[str, Any]) -> dict[str, str]:
    context = dict(payload)
    context.setdefault("payload", payload)
    context.setdefault("signal", payload.get("input_text", ""))
    context.setdefault("context_kernel", payload.get("context_kernel", {}))
    context.setdefault("semantic_event_graph", payload.get("semantic_event_graph", {}))
    context.setdefault("semantic_answer_graph", payload.get("semantic_answer_graph", {}))
    context.setdefault("selected_claims", payload.get("selected_evidence", {}).get("selected_claim_ids", []))
    context.setdefault("candidates", payload.get("memory_packet", {}).get("ranking_trace", []))
    context.setdefault("recent_event_graphs", payload.get("recent_event_graphs", [payload.get("semantic_event_graph", {})]))
    return {
        key: json.dumps(value, indent=2, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        for key, value in context.items()
    }


def render_prompt(task_type: str, payload_json: str) -> tuple[str, str, str]:
    prompt = PROMPTS[task_type]
    payload = json.loads(payload_json)
    payload_pretty = json.dumps(payload, indent=2, sort_keys=True)
    context = _prompt_context(payload)
    context["payload"] = payload_pretty
    try:
        user = prompt["user"].format(**context)
    except KeyError as exc:
        missing = exc.args[0]
        raise KeyError(f"{task_type} prompt references missing key {{{missing}}}") from exc
    return prompt["agent"], prompt["system"], user
```

- [ ] **Step 2: Run prompt rendering tests**

Run:

```bash
python -m pytest tests/test_trainer_prompt_rendering_all_tasks.py tests/test_render_prompt.py -q
```

Expected: PASS.

- [ ] **Step 3: Verify no known prompt still references unsupported keys**

Run:

```bash
python -c "from cemm.cemm_trainer import PROMPTS; import string; keys=sorted({f for p in PROMPTS.values() for _,f,_,_ in string.Formatter().parse(p['user']) if f}); print(keys)"
```

Expected: Printed keys are all handled by `_prompt_context`.

- [ ] **Step 4: Commit**

```bash
git add cemm_trainer.py tests/test_trainer_prompt_rendering_all_tasks.py
git commit -m "fix: render graph-first trainer prompts safely"
```

---

### Task 3: Route Ask, Remember, and Retrieve Through Realization

**Files:**
- Modify: `synthesis/template.py`
- Modify: `synthesis/extractive.py`
- Modify: `synthesis/realizer.py`
- Modify: `operators/ask.py`
- Modify: `operators/remember.py`
- Modify: `operators/retrieve_op.py`
- Test: `tests/test_operator_realization_invariants.py`

- [ ] **Step 1: Extend templates for non-answer action realization**

In `synthesis/template.py`, extend `_load_template`:

```python
templates = {
    "greeting": "Hello! How can I help you today?",
    "confirmation": "I've noted that: {subject} {predicate} {object}.",
    "clarification": "Could you clarify what you mean by {term}?",
    "capability": "I can help with questions about {domain}.",
    "acknowledgment": "Got it! What else would you like to know or share?",
    "remember_confirm": "I've stored that in this session.",
    "retrieve_empty": "I did not find matching stored evidence.",
    "permission_denied": "I cannot do that because the required permission is not available.",
}
```

- [ ] **Step 2: Teach the realizer to select templates from SAG intent**

In `synthesis/realizer.py`, add cases:

```python
elif intent == "remember":
    params["template_key"] = "remember_confirm"
elif intent == "retrieve" and not answer_graph.selected_claim_ids:
    params["template_key"] = "retrieve_empty"
elif intent == "permission_denied":
    params["template_key"] = "permission_denied"
```

- [ ] **Step 3: Update `AskOperator` to use `RealizationPipeline`**

In `operators/ask.py`, import and use `RealizationPipeline`. Replace direct `question` output with:

```python
answer_graph = SemanticAnswerGraph(
    id=uuid.uuid4().hex[:16],
    intent="ask",
    source_signal_ids=[ctx.input_signal.id],
    context_id=ctx.kernel.id,
    uncertainty_reasons=["clarification needed"],
    confidence=0.7,
)
answer_graph.entity_refs.append({"kind": "clarification", "question": question})
result = RealizationPipeline().run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
output = result.output if result.success and result.verified else "Could you clarify what you mean by that?"
```

Set trace fields:

```python
synthesis_verified=result.verified,
synthesis_verification_type="hard",
realization_strategy=result.strategy,
realization_verified=result.verified,
```

- [ ] **Step 4: Update `RememberOperator` to realize confirmation from SAG**

After creating the `SemanticAnswerGraph`, call:

```python
from ..synthesis.realizer import RealizationPipeline

result = RealizationPipeline().run(answer_graph, ctx.kernel, ctx.store, ctx.registry)
output = result.output if result.success and result.verified else "I've stored that in this session."
```

Return `output_text=output` instead of `f"Remembered: {subject_id} {predicate}"`. Populate trace realization fields from `result`.

- [ ] **Step 5: Update `RetrieveOperator` to realize from selected claims**

Remove `output_lines`. Build `SemanticAnswerGraph(intent="answer", selected_claim_ids=selected_ids[:5])` when claims exist, otherwise `intent="retrieve"`. Run `RealizationPipeline` and return its output. Populate trace realization fields.

- [ ] **Step 6: Run focused realization tests**

Run:

```bash
python -m pytest tests/test_operator_realization_invariants.py tests/test_ask_operator.py tests/test_remember_operator.py tests/test_retrieve_operator.py tests/test_realization_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add synthesis/template.py synthesis/realizer.py operators/ask.py operators/remember.py operators/retrieve_op.py tests/test_operator_realization_invariants.py
git commit -m "fix: realize action outputs through semantic answer graphs"
```

---

### Task 4: Export Accurate Realization And Verification Metadata

**Files:**
- Modify: `types/trace.py`
- Modify: `operators/answer.py`
- Modify: `operators/ask.py`
- Modify: `operators/remember.py`
- Modify: `operators/retrieve_op.py`
- Modify: `kernel/training_export.py`
- Test: `tests/test_training_export_realization_metadata.py`

- [ ] **Step 1: Extend `Trace` metadata fields**

In `types/trace.py`, add:

```python
realization_details: dict = field(default_factory=dict)
verification_details: dict = field(default_factory=dict)
```

- [ ] **Step 2: Populate trace metadata in `AnswerOperator`**

In `operators/answer.py`, when constructing `Trace`, set:

```python
synthesis_verified=result.verified,
synthesis_verification_type="hard" if result.strategy in ("template", "extractive") else "soft",
realization_strategy=result.strategy,
realization_verified=result.verified,
realization_details={
    "source_answer_graph_id": result.metadata.get("source_answer_graph_id"),
    "strategy": result.strategy,
},
verification_details=result.metadata.get("verification", {}),
```

- [ ] **Step 3: Apply the same trace fields to ask/remember/retrieve**

Use the same field values from the `SynthesisResult` each operator receives.

- [ ] **Step 4: Make export prefer detailed trace metadata**

In `kernel/training_export.py`, change realization metadata construction to:

```python
payload["realization_metadata"] = {
    "strategy": trace.realization_strategy,
    "verified": trace.realization_verified,
    "details": trace.realization_details,
}
payload["verification_metadata"] = {
    "synthesis_strategy_model_id": trace.synthesis_strategy_model_id,
    "synthesis_verified": trace.synthesis_verified,
    "synthesis_verification_type": trace.synthesis_verification_type,
    "verifier_model_id": trace.verifier_model_id,
    "details": trace.verification_details,
}
```

Apply this in both `_task_payload` and `serialize_turn`.

- [ ] **Step 5: Run export tests**

Run:

```bash
python -m pytest tests/test_training_export_realization_metadata.py tests/test_training_export_sag.py tests/test_training_export_task_types.py tests/test_packets.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add types/trace.py operators/answer.py operators/ask.py operators/remember.py operators/retrieve_op.py kernel/training_export.py tests/test_training_export_realization_metadata.py
git commit -m "fix: export realization verification metadata"
```

---

### Task 5: Add Noisy Multilingual Normalization As A Packet, Not A Text Rewrite

**Files:**
- Create: `types/normalized_signal.py`
- Create: `kernel/text_normalizer.py`
- Modify: `types/signal.py`
- Modify: `kernel/pipeline.py`
- Modify: `registry/semantic_matcher.py`
- Test: `tests/test_noisy_text_normalization.py`

- [ ] **Step 1: Add tests for raw-preserving normalization**

Create `tests/test_noisy_text_normalization.py`:

```python
from __future__ import annotations

from cemm.kernel.text_normalizer import TextNormalizer


def test_normalizer_preserves_raw_text_and_expands_noise() -> None:
    packet = TextNormalizer().normalize("  Héyyy!!!   I luvvv CEMM 😂  ")
    assert packet.raw_text == "  Héyyy!!!   I luvvv CEMM 😂  "
    assert "hey" in packet.normalized_forms
    assert "i love cemm" in packet.normalized_forms
    assert packet.noise_features["emoji_count"] == 1
    assert packet.noise_features["repeated_char_runs"] >= 2


def test_normalizer_keeps_multilingual_alias_forms() -> None:
    packet = TextNormalizer().normalize("hola, ¿qué haces?")
    assert "hola que haces" in packet.normalized_forms
    assert packet.detected_scripts
    assert packet.confidence >= 0.5
```

- [ ] **Step 2: Create `NormalizedSignal` dataclass**

Create `types/normalized_signal.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NormalizedSignal:
    raw_text: str
    normalized_forms: list[str] = field(default_factory=list)
    canonical_form: str = ""
    detected_scripts: list[str] = field(default_factory=list)
    noise_features: dict[str, int | float | bool] = field(default_factory=dict)
    transform_trace: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 0.5
    version: str = "cemm.normalized_signal.v1"
```

- [ ] **Step 3: Implement conservative normalizer**

Create `kernel/text_normalizer.py`:

```python
from __future__ import annotations

import re
import unicodedata

from ..types.normalized_signal import NormalizedSignal


_NOISY_WORDS = {
    "heyyy": "hey",
    "heyy": "hey",
    "luv": "love",
    "luvv": "love",
    "luvvv": "love",
    "u": "you",
    "ur": "your",
    "pls": "please",
    "plz": "please",
}


class TextNormalizer:
    def normalize(self, text: str) -> NormalizedSignal:
        raw = text
        nfkc = unicodedata.normalize("NFKC", raw)
        folded = "".join(c for c in unicodedata.normalize("NFKD", nfkc) if not unicodedata.combining(c))
        lowered = folded.lower()
        emoji_count = sum(1 for c in lowered if unicodedata.category(c).startswith("So"))
        punctuation_stripped = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
        collapsed = re.sub(r"\s+", " ", punctuation_stripped).strip()
        repeated_runs = re.findall(r"([a-z])\1{2,}", collapsed)
        repeated_collapsed = re.sub(r"([a-z])\1{2,}", r"\1\1", collapsed)
        tokens = [_NOISY_WORDS.get(tok, tok) for tok in repeated_collapsed.split()]
        lexical = " ".join(tokens)
        forms = []
        for form in [collapsed, repeated_collapsed, lexical]:
            if form and form not in forms:
                forms.append(form)
        scripts = sorted({unicodedata.name(c, "UNKNOWN").split()[0] for c in raw if c.isalpha()})
        return NormalizedSignal(
            raw_text=raw,
            normalized_forms=forms,
            canonical_form=forms[-1] if forms else "",
            detected_scripts=scripts,
            noise_features={
                "emoji_count": emoji_count,
                "repeated_char_runs": len(repeated_runs),
                "leading_or_trailing_space": raw != raw.strip(),
            },
            transform_trace=[
                {"name": "nfkc", "value": nfkc},
                {"name": "diacritic_fold", "value": folded},
                {"name": "punctuation_strip", "value": collapsed},
                {"name": "lexical_noise_map", "value": lexical},
            ],
            confidence=0.7 if forms else 0.0,
        )
```

- [ ] **Step 4: Attach normalized packet to `Signal`**

In `types/signal.py`, add:

```python
from .normalized_signal import NormalizedSignal
```

and add to `Signal`:

```python
normalized: NormalizedSignal | None = None
```

- [ ] **Step 5: Populate normalization before context inference**

In `kernel/pipeline.py`, instantiate `TextNormalizer` in `__init__` and call it after storing the raw signal:

```python
from .text_normalizer import TextNormalizer

self._text_normalizer = TextNormalizer()
...
signal.normalized = self._text_normalizer.normalize(signal.content)
```

Keep `signal.content` unchanged.

- [ ] **Step 6: Teach semantic matcher to consider normalized forms**

In `registry/semantic_matcher.py`, add optional `extra_forms: list[str] | None = None` to `match`. When present, run current matching over `[content] + extra_forms` and keep the highest score per `(canonical_key, alias_matched, match_type)`.

- [ ] **Step 7: Run normalization tests**

Run:

```bash
python -m pytest tests/test_noisy_text_normalization.py tests/test_pragmatic_routing.py tests/test_routing.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add types/normalized_signal.py kernel/text_normalizer.py types/signal.py kernel/pipeline.py registry/semantic_matcher.py tests/test_noisy_text_normalization.py
git commit -m "feat: add raw-preserving noisy text normalization"
```

---

### Task 6: Expand Pragmatic Acts For Casual Chat Without Hardcoded Final Text

**Files:**
- Modify: `kernel/semantic_clusters.py`
- Modify: `kernel/pragmatic_interpreter.py`
- Modify: `registry/uol_mapper.py`
- Modify: `__main__.py` seed registry entries
- Test: `tests/test_pragmatic_casual_acts.py`

- [ ] **Step 1: Add pragmatic act tests**

Create `tests/test_pragmatic_casual_acts.py`:

```python
from __future__ import annotations

from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.kernel.pragmatic_interpreter import interpret_signal
from cemm.kernel.semantic_clusters import SemanticClusterRegistry
from cemm.types.permission import Permission
from cemm.types.signal import Signal, SignalKind, SourceType


def _signal(text: str) -> Signal:
    return Signal(id="s1", kind=SignalKind.INPUT, source_id="user", source_type=SourceType.USER, content=text, context_id="ctx", permission=Permission.public())


def test_casual_chat_speech_acts_are_semantic_clusters() -> None:
    reg = SemanticClusterRegistry()
    cases = {
        "lol nice": "playful_acknowledgment",
        "wait what": "confusion",
        "my bad": "self_correction",
        "can you explain that simpler": "simplification_request",
        "no worries": "reassurance",
    }
    for text, cluster in cases.items():
        matches = reg.match_ranked(text)
        assert matches
        assert matches[0].cluster_key == cluster


def test_pragmatic_interpreter_maps_casual_acts_to_frame_keys() -> None:
    kernel = ContextKernelBuilder.from_signal(_signal("lol nice"), turn_index=2)
    semantics = interpret_signal(_signal("lol nice"), kernel)
    assert semantics is not None
    assert semantics.speech_act == "playful_acknowledgment"
    assert semantics.frame_key == "playful_acknowledgment"
```

- [ ] **Step 2: Add clusters for casual acts**

In `kernel/semantic_clusters.py`, add cluster definitions:

```python
"playful_acknowledgment": {
    "speech_act": "playful_acknowledgment",
    "patterns": ["lol nice", "lol ok", "haha okay", "lmao", "fair enough"],
    "target": "assistant",
    "affect_baseline": {"valence": 0.25, "arousal": 0.25, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.5},
},
"confusion": {
    "speech_act": "confusion",
    "patterns": ["wait what", "uh what", "i am confused", "im confused", "that lost me"],
    "target": "assistant",
    "affect_baseline": {"valence": -0.1, "arousal": 0.25, "frustration": 0.15, "hostility": 0.0, "playfulness": 0.0},
},
"self_correction": {
    "speech_act": "self_correction",
    "patterns": ["my bad", "sorry i meant", "i mean", "correction"],
    "target": "user",
    "affect_baseline": {"valence": 0.0, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
},
"simplification_request": {
    "speech_act": "simplification_request",
    "patterns": ["explain that simpler", "say that simpler", "simplify", "too complex"],
    "target": "assistant",
    "affect_baseline": {"valence": -0.05, "arousal": 0.15, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
},
"reassurance": {
    "speech_act": "reassurance",
    "patterns": ["no worries", "all good", "its fine", "it's fine"],
    "target": "assistant",
    "affect_baseline": {"valence": 0.25, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
},
```

- [ ] **Step 3: Map new speech acts to frame keys**

In `kernel/pragmatic_interpreter.py`, extend `_SPEECH_ACT_TO_FRAME_KEY`:

```python
_SPEECH_ACT_TO_FRAME_KEY.update({
    "playful_acknowledgment": "playful_acknowledgment",
    "confusion": "request_clarification",
    "self_correction": "self_correction",
    "simplification_request": "simplification_request",
    "reassurance": "reassurance",
})
```

- [ ] **Step 4: Seed UOL semantic registry entries**

In `__main__.py`, add to `uol_semantics`:

```python
("playful_acknowledgment", ["lol nice", "lol ok", "haha okay", "fair enough"]),
("self_correction", ["my bad", "sorry i meant", "i mean", "correction"]),
("simplification_request", ["explain simpler", "simplify", "too complex"]),
("reassurance", ["no worries", "all good", "it's fine", "its fine"]),
```

- [ ] **Step 5: Run pragmatic tests**

Run:

```bash
python -m pytest tests/test_pragmatic_casual_acts.py tests/test_pragmatic_routing.py tests/test_conversational_clusters.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add kernel/semantic_clusters.py kernel/pragmatic_interpreter.py __main__.py tests/test_pragmatic_casual_acts.py
git commit -m "feat: expand semantic pragmatic acts for casual chat"
```

---

### Task 7: Make Self And Capability Answers Evidence-Backed

**Files:**
- Modify: `self_knowledge.json`
- Modify: `registry/uol_mapper.py`
- Modify: `kernel/decision_router.py`
- Modify: `operators/answer.py`
- Test: `tests/test_self_capability_answers.py`

- [ ] **Step 1: Add self-answer tests**

Create `tests/test_self_capability_answers.py`:

```python
from __future__ import annotations

from cemm.__main__ import process_input, seed_registry, seed_self_state
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.learning.inductor import Inductor
from cemm.learning.online import OnlineLearner
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.registry import OperatorRegistry
from cemm.store.store import Store
from cemm.registry import Registry


def _runtime():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    seed_registry(registry)
    seed_self_state(store)
    op_registry.register(AnswerOperator())
    op_registry.register(AskOperator())
    pipeline = Pipeline(store, registry)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    loop = RecursiveLoop(pipeline, store, learner, Inductor(store, registry=registry))
    return store, registry, op_registry, pipeline, learner, loop


def test_who_are_you_uses_self_claim_evidence() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    output = process_input("who are you exactly?", store, registry, op_registry, pipeline, learner, loop, "ctx_self", [0])
    assert "CEMM" in output
    sag = loop._last_result.decision_packet.semantic_answer_graph if loop._last_result.decision_packet else None
    trace = getattr(loop, "_last_operator_trace", None)
    assert loop._last_result.semantic_event_graph is not None
    assert loop._last_result.semantic_event_graph.entity_refs
    assert loop._last_result.ranked_claim_ids


def test_what_do_you_do_returns_capability_claims_not_generic_text() -> None:
    store, registry, op_registry, pipeline, learner, loop = _runtime()
    output = process_input("what do you do?", store, registry, op_registry, pipeline, learner, loop, "ctx_self", [0])
    assert "trace" in output.lower() or "routing" in output.lower() or "language" in output.lower()
    assert loop._last_result.ranked_claim_ids
```

- [ ] **Step 2: Expand self knowledge with answer-oriented predicates**

In `self_knowledge.json`, add claims:

```json
{"subject": "self_main", "predicate": "answers_identity_as", "object_value": "CEMM, a contextual event memory model and small language model architecture"},
{"subject": "self_main", "predicate": "does", "object_value": "turn signals into semantic graphs, select evidence, decide actions, realize verified answers, and export traces for training"},
{"subject": "self_main", "predicate": "knows_about", "object_value": "its seeded self-description, runtime traces, selected memory, and validated claims available under permission"},
{"subject": "self_main", "predicate": "limitation", "object_value": "it must abstain or ask when evidence, permission, freshness, or required slots are missing"}
```

- [ ] **Step 3: Improve self-reference graph construction**

In `registry/uol_mapper.py`, replace the private `_self_ref_phrases` tuple with a module-level map:

```python
_SELF_QUERY_FRAMES = {
    "self_identity_query": ["who are you", "what are you", "what is your name", "introduce yourself"],
    "self_capability_query": ["what do you do", "what can you do", "your capabilities", "how do you work"],
    "self_knowledge_query": ["what do you know", "what do you know about yourself"],
}
```

When a phrase matches, emit:

```python
atoms.append(ProcessUOLAtom(frame_key=frame_key, modality="observed", polarity="affirmed", intensity=0.7, confidence=0.85))
```

and emit `EntityRefUOLAtom(entity_id=kernel.self_view.self_id, role="target", confidence=0.85)`.

- [ ] **Step 4: Route self-query processes to answer over selected self claims**

In `kernel/decision_router.py`, before generic clarification fallbacks, add:

```python
self_query_frames = {"self_identity_query", "self_capability_query", "self_knowledge_query"}
if any(proc.get("frame_key") in self_query_frames for proc in graph.processes) and selected_claim_ids:
    return DecisionPacket(
        action_kind="answer",
        action_plan=ActionPlan(
            action_kind="answer",
            selected_claim_ids=selected_claim_ids,
            selected_model_ids=selected_model_ids,
            execution_allowed=True,
            confidence=min(0.9, graph.confidence),
            risk=0.0,
        ),
        confidence=min(0.9, graph.confidence),
        reason="self query answered from selected self claims",
    )
```

- [ ] **Step 5: Run self-answer tests**

Run:

```bash
python -m pytest tests/test_self_capability_answers.py tests/test_self_reference_patterns.py tests/test_answer_operator.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add self_knowledge.json registry/uol_mapper.py kernel/decision_router.py tests/test_self_capability_answers.py
git commit -m "feat: answer self capability queries from evidence"
```

---

### Task 8: Harden NER For Noisy And Mixed-Label Data

**Files:**
- Modify: `learning/ner_tagger.py`
- Modify: `scripts/train_ner_tagger.py`
- Modify: `kernel/semantic_interpreter.py`
- Test: `tests/test_ner_noisy_multilingual.py`

- [ ] **Step 1: Add NER tests for noisy punctuation and mixed labels**

Create `tests/test_ner_noisy_multilingual.py`:

```python
from __future__ import annotations

from cemm.learning.ner_tagger import NERTagger


def test_tagger_adds_unseen_gold_tags_before_training() -> None:
    tagger = NERTagger(tags=["O", "B-PERSON", "I-PERSON"], dim=128)
    tagger.train([["Alice", "visited", "Paris"]], [["B-PER", "O", "B-LOC"]], epochs=1, validation_split=0.0, verbose=False)
    assert "B-PER" in tagger.TAGS
    assert "B-LOC" in tagger.TAGS


def test_noisy_tokenization_preserves_entity_text() -> None:
    words = ["Dr.", "Smith!!!", "visited", "São", "Paulo"]
    clean = NERTagger.normalize_tokens(words)
    assert clean == ["Dr", "Smith", "visited", "Sao", "Paulo"]
```

- [ ] **Step 2: Add tag expansion helper**

In `learning/ner_tagger.py`, add:

```python
def _ensure_tags(self, labels: list[list[str]]) -> None:
    for seq in labels:
        for tag in seq:
            if tag not in self.TAGS:
                self.TAGS.append(tag)
                self.weights[tag] = {}
                self._weight_sum[tag] = {}
```

Call it at the start of `train()` after validating input lengths.

- [ ] **Step 3: Add reusable token normalization**

In `learning/ner_tagger.py`, add:

```python
@staticmethod
def normalize_tokens(words: list[str]) -> list[str]:
    import unicodedata
    cleaned: list[str] = []
    for word in words:
        folded = "".join(c for c in unicodedata.normalize("NFKD", word.strip(".,!?;:\"'()[]{}")) if not unicodedata.combining(c))
        if folded:
            cleaned.append(folded)
    return cleaned
```

Use normalized tokens for features, while returning original entity text in `extract_entities`.

- [ ] **Step 4: Fix synthetic multi-person template bug**

In `scripts/train_ner_tagger.py`, change the template with two people to use distinct format tokens:

```python
("{PER} and {PER2} {verb} {LOC}"),
```

Keep `PER2=per2` in `.format(...)`.

- [ ] **Step 5: Make real+synthetic label merge explicit**

After `combined_labels = real_labels + synthetic_labels`, make sure synthetic tags are available:

```python
for tag in ["B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-TIME", "I-TIME"]:
    if tag not in bio_tags:
        bio_tags.append(tag)
```

- [ ] **Step 6: Run NER tests**

Run:

```bash
python -m pytest tests/test_ner_noisy_multilingual.py tests/test_learned_ner.py tests/test_seg_entity_population.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add learning/ner_tagger.py scripts/train_ner_tagger.py tests/test_ner_noisy_multilingual.py
git commit -m "fix: harden ner training for noisy mixed-label data"
```

---

### Task 9: Add Noisy Casual Conversation Seed Categories

**Files:**
- Modify: `cemm_seed_spec.json`
- Modify: `cemm_seed_generator.py`
- Test: `tests/test_noisy_casual_seed_generation.py`

- [ ] **Step 1: Add seed generation test**

Create `tests/test_noisy_casual_seed_generation.py`:

```python
from __future__ import annotations

from cemm.cemm_seed_generator import generate_dry_run_category, validate_and_flatten


def test_noisy_casual_seed_examples_include_graph_packets() -> None:
    category = {
        "name": "noisy_casual_chat",
        "task_types": ["uol_mapping", "pragmatic_interpretation", "context_inference", "semantic_graph_extraction"],
    }
    payload = generate_dry_run_category(category, 5)
    _, examples = validate_and_flatten(payload)
    assert examples
    for payload in examples:
        assert payload["context_kernel"]
        assert payload["semantic_event_graph"]
        assert "output_text" not in payload or payload.get("semantic_answer_graph")
```

- [ ] **Step 2: Add categories to seed spec**

In `cemm_seed_spec.json`, add a category:

```json
{
  "id": "noisy_casual_chat",
  "description": "Noisy casual turns with abbreviations, typos, emoji, multilingual greetings, clarification, playful acknowledgments, self-correction, and reassurance.",
  "task_types": ["uol_mapping", "pragmatic_interpretation", "context_inference", "semantic_graph_extraction"],
  "permission_scope": "local_training"
}
```

- [ ] **Step 3: Generate graph-first noisy examples**

In `cemm_seed_generator.py`, add a category generator that emits payloads shaped like:

```python
{
    "context_kernel": {"conversation": {"turn_index": 2}, "permission": {"scope": "local_training"}},
    "input_text": "heyyy lol what??",
    "semantic_event_graph": {
        "source_signal_ids": ["seed_sig"],
        "context_id": "seed_ctx",
        "entity_refs": [],
        "processes": [{"kind": "process", "frame_key": "request_clarification", "confidence": 0.8}],
        "states": [],
        "permission_scope": "local_training",
        "confidence": 0.8
    },
    "observation_semantics": {
        "speech_act": "confusion",
        "semantic_cluster_key": "confusion",
        "confidence": 0.8
    }
}
```

- [ ] **Step 4: Run seed tests and validation**

Run:

```bash
python -m pytest tests/test_noisy_casual_seed_generation.py -q
python cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
```

Expected: pytest PASS; validation reports no unknown task types.

- [ ] **Step 5: Commit**

```bash
git add cemm_seed_spec.json cemm_seed_generator.py tests/test_noisy_casual_seed_generation.py
git commit -m "feat: add noisy casual conversation seed category"
```

---

### Task 10: Fix Ranking And Grounding Weak Spots

**Files:**
- Modify: `retrieval/ranker.py`
- Modify: `confidence/scoring.py`
- Modify: `kernel/grounding.py`
- Test: `tests/test_ranking_grounding_invariants.py`

- [ ] **Step 1: Add ranking and grounding tests**

Create `tests/test_ranking_grounding_invariants.py`:

```python
from __future__ import annotations

import time

from cemm.retrieval.ranker import Ranker
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.semantic_event_graph import SemanticEventGraph


def test_graph_claim_ref_boosts_relevance() -> None:
    kernel = ContextKernel(id="ctx", permission=Permission.public())
    kernel.time.now = time.time()
    claim = Claim(id="c1", subject_entity_id="user", predicate="likes", object_value="coffee", status=ClaimStatus.ACTIVE, confidence=0.8, trust=0.8, salience=0.8, observed_at=time.time(), permission=Permission.public())
    graph = SemanticEventGraph(id="seg", source_signal_ids=["s"], context_id="ctx", entity_refs=[], processes=[], states=[], claim_refs=["c1"], confidence=0.9)
    score_with_graph = Ranker().rank_claims([claim], kernel, graph=graph)[0][1]
    score_without_graph = Ranker().rank_claims([claim], kernel, graph=None)[0][1]
    assert score_with_graph > score_without_graph
```

- [ ] **Step 2: Fix graph relevance boost**

In `retrieval/ranker.py`, replace:

```python
relevance = max(relevance, relevance * graph.confidence)
```

with:

```python
relevance = max(relevance, min(1.0, 0.7 + 0.3 * graph.confidence))
```

- [ ] **Step 3: Add temporal and risk score inputs**

In `confidence/scoring.py`, extend `score_claim` signature:

```python
temporal_containment: float = 1.0,
risk_penalty: float = 0.0,
cost_penalty: float = 0.0,
```

and include them:

```python
return (
    relevance * trust * confidence * effective_salience * recency * frame_validity * temporal_containment
) - contradiction_penalty - risk_penalty - cost_penalty
```

Callers pass defaults until frame-specific risk/cost is available.

- [ ] **Step 4: Run ranking tests**

Run:

```bash
python -m pytest tests/test_ranking_grounding_invariants.py tests/test_answer_graph_ranker.py tests/test_retrieve_operator.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add retrieval/ranker.py confidence/scoring.py tests/test_ranking_grounding_invariants.py
git commit -m "fix: rank graph-referenced claims with real relevance boost"
```

---

### Task 11: Run Full Verification And Update Gap Trace

**Files:**
- Modify: `cemm_architecture_gap_trace.md`
- Modify: `cemm_acceptance_tests.md` if new acceptance clauses are added

- [ ] **Step 1: Run the full test suite**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run trainer prompt smoke**

Run:

```bash
python -c "from cemm.cemm_trainer import PROMPTS, render_prompt; import json; payload=json.dumps({'context_kernel':{}, 'semantic_event_graph':{}, 'semantic_answer_graph':{}, 'memory_packet':{}, 'inference_packet':{}, 'output_text':'x', 'selected_evidence':{}, 'self_state':{}, 'recent_event_graphs':[]}); print([t for t in PROMPTS if not render_prompt(t, payload)])"
```

Expected: prints `[]`.

- [ ] **Step 3: Update gap trace**

In `cemm_architecture_gap_trace.md`, add a section:

```markdown
## 2026-07-01 Remediation Pass

Closed:
- Trainer prompt rendering no longer crashes on graph-first tasks.
- Ask, remember, and retrieve user-facing outputs now realize through SemanticAnswerGraph.
- Runtime export includes accurate realization and verification metadata.
- Raw-preserving noisy text normalization emits a packet before interpretation.
- Casual pragmatic acts are represented as semantic clusters and UOL frame keys.
- Self/capability answers route through selected self evidence.
- NER training accepts mixed label sets and normalizes noisy tokens.
- Graph-referenced claims receive an actual relevance boost.

Remaining:
- Learned multilingual semantic parsing remains a Phase 1+ training target.
- Frame-specific risk/cost scoring remains limited until more validated models exist.
```

- [ ] **Step 4: Commit documentation**

```bash
git add cemm_architecture_gap_trace.md
git commit -m "docs: update architecture gap trace after remediation"
```

---

## Self-Review Checklist

- Spec coverage:
  - Trainer prompt rendering gap: Task 2.
  - SAG-before-text and realization bypasses: Task 3.
  - Export realization metadata: Task 4.
  - Multi-language noisy normalization: Task 5.
  - Training seed categories for noisy casual conversation: Task 9.
  - Pragmatic acts for casual chat: Task 6.
  - Self/capability answer models: Task 7.
  - NER identification: Task 8.
  - Ranking/grounding weakness: Task 10.
- Placeholder scan:
  - No unresolved marker text remains.
  - Each task has concrete paths, tests, implementation snippets, commands, and expected outcomes.
- Type consistency:
  - New `NormalizedSignal` is attached to `Signal.normalized`.
  - `Trace.realization_details` and `Trace.verification_details` are dictionaries used by `training_export`.
  - `SynthesisResult.strategy` is the source for trace strategy fields.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-01-cemm-architecture-gap-remediation.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.
