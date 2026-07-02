# Typed Latent Spaces (G26)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Close G26 — the architecture defines 10 typed latent spaces, but no runtime `LatentSpaceSpec`, encoders, or typed latent fields exist. Add a minimal deterministic typed latent encoder and integrate it with the answer graph so `SemanticAnswerGraph.answer_latent` is no longer always empty.

**Architecture:** The architecture defines `TypedLatents` with entity, process, state, claim, model, context, self, memory, action, and answer spaces. The training code (`training/tl1_hash_encoder.py`) already provides deterministic hash encoding. We reuse that for a baseline runtime encoder and add explicit type specs.

**Tech Stack:** Python 3.13, dataclasses, TL1 hash encoder, SemanticAnswerGraph.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/types/latent_space.py` | LatentSpaceSpec and TypedLatents dataclasses | Create |
| `cemm/latent/encoder.py` | Runtime typed latent encoder | Create |
| `cemm/operators/answer.py` | Populate answer_latent on SAG | Modify |
| `cemm/tests/test_typed_latent_spaces.py` | Tests | Create |

---

## Task 1: Add typed latent space types and encoder

**Files:**
- Create: `cemm/types/latent_space.py`
- Create: `cemm/latent/encoder.py`
- Create: `cemm/tests/test_typed_latent_spaces.py`

- [ ] **Step 1: Create LatentSpaceSpec and TypedLatents types**

```python
# cemm/types/latent_space.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LatentSpaceSpec:
    """Specification for a typed latent space."""
    name: str
    dim: int
    description: str = ""
    version: str = "cemm.latent_space.v1"


@dataclass
class TypedLatents:
    """Typed latent embeddings for the major meaning objects in the architecture."""
    entity: list[float] = field(default_factory=list)
    process: list[float] = field(default_factory=list)
    state: list[float] = field(default_factory=list)
    claim: list[float] = field(default_factory=list)
    model: list[float] = field(default_factory=list)
    context: list[float] = field(default_factory=list)
    self: list[float] = field(default_factory=list)
    memory: list[float] = field(default_factory=list)
    action: list[float] = field(default_factory=list)
    answer: list[float] = field(default_factory=list)
```

- [ ] **Step 2: Create LatentEncoder**

```python
# cemm/latent/encoder.py
from __future__ import annotations
from typing import Any

from ..types.latent_space import LatentSpaceSpec, TypedLatents
from ..training.tl1_hash_encoder import Feature, hash_encode, extract_features


_DEFAULT_DIM = 64


_SPACES = [
    LatentSpaceSpec("entity", _DEFAULT_DIM),
    LatentSpaceSpec("process", _DEFAULT_DIM),
    LatentSpaceSpec("state", _DEFAULT_DIM),
    LatentSpaceSpec("claim", _DEFAULT_DIM),
    LatentSpaceSpec("model", _DEFAULT_DIM),
    LatentSpaceSpec("context", _DEFAULT_DIM),
    LatentSpaceSpec("self", _DEFAULT_DIM),
    LatentSpaceSpec("memory", _DEFAULT_DIM),
    LatentSpaceSpec("action", _DEFAULT_DIM),
    LatentSpaceSpec("answer", _DEFAULT_DIM),
]


class LatentEncoder:
    """Deterministic baseline typed latent encoder.

    Produces fixed-size sparse vectors from typed features. Each typed space is
    hashed into its own namespace so entity, process, and state features do not
    collide.
    """

    def __init__(self, dim: int = _DEFAULT_DIM) -> None:
        self.dim = dim
        self.spaces = {s.name: s for s in _SPACES}

    def encode(self, namespace: str, features: list[Any]) -> list[float]:
        """Encode a list of typed features into a dense float vector."""
        typed_features = [
            Feature(namespace=namespace, key=str(f), value=1.0)
            for f in features
        ]
        sparse = hash_encode(typed_features, num_buckets=self.dim)
        dense = [0.0] * self.dim
        for idx, val in sparse.items():
            if 0 <= idx < self.dim:
                dense[idx] = val
        return dense

    def encode_entity(self, entity_id: str, entity_name: str = "") -> list[float]:
        return self.encode("entity", [entity_id, entity_name])

    def encode_process(self, frame_key: str) -> list[float]:
        return self.encode("process", [frame_key])

    def encode_state(self, state_key: str) -> list[float]:
        return self.encode("state", [state_key])

    def encode_claim(self, predicate: str, object_value: str = "") -> list[float]:
        return self.encode("claim", [predicate, object_value])

    def encode_model(self, registry_key: str) -> list[float]:
        return self.encode("model", [registry_key])

    def encode_context(self, context_id: str) -> list[float]:
        return self.encode("context", [context_id])

    def encode_self(self, mode: str, uncertainty: float = 0.0) -> list[float]:
        return self.encode("self", [mode, str(round(uncertainty, 2))])

    def encode_memory(self, selected_claim_ids: list[str]) -> list[float]:
        return self.encode("memory", selected_claim_ids)

    def encode_action(self, action_kind: str) -> list[float]:
        return self.encode("action", [action_kind])

    def encode_answer(
        self,
        intent: str,
        selected_claim_ids: list[str],
        selected_model_ids: list[str],
    ) -> list[float]:
        return self.encode("answer", [intent] + selected_claim_ids + selected_model_ids)

    def encode_typed(
        self,
        entity_ids: list[str] = None,
        process_keys: list[str] = None,
        state_keys: list[str] = None,
        claim_tuples: list[tuple[str, str]] = None,
        model_keys: list[str] = None,
        context_id: str = "",
        self_mode: str = "",
        self_uncertainty: float = 0.0,
        memory_claim_ids: list[str] = None,
        action_kind: str = "",
        answer_intent: str = "",
        answer_claim_ids: list[str] = None,
        answer_model_ids: list[str] = None,
    ) -> TypedLatents:
        """Encode all typed spaces at once."""
        return TypedLatents(
            entity=self.encode("entity", entity_ids or []),
            process=self.encode("process", process_keys or []),
            state=self.encode("state", state_keys or []),
            claim=self.encode("claim", [f"{p}:{o}" for p, o in (claim_tuples or [])]),
            model=self.encode("model", model_keys or []),
            context=self.encode("context", [context_id] if context_id else []),
            self=self.encode("self", [self_mode, str(round(self_uncertainty, 2))] if self_mode else []),
            memory=self.encode("memory", memory_claim_ids or []),
            action=self.encode("action", [action_kind] if action_kind else []),
            answer=self.encode("answer", [answer_intent] + (answer_claim_ids or []) + (answer_model_ids or [])),
        )
```

- [ ] **Step 3: Write tests**

```python
# cemm/tests/test_typed_latent_spaces.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.latent.encoder import LatentEncoder
from cemm.types.latent_space import LatentSpaceSpec, TypedLatents


def test_latent_space_specs_exist():
    encoder = LatentEncoder()
    for name in ("entity", "process", "state", "claim", "model", "context", "self", "memory", "action", "answer"):
        assert name in encoder.spaces
        assert isinstance(encoder.spaces[name], LatentSpaceSpec)


def test_encoder_produces_fixed_dim_vectors():
    encoder = LatentEncoder(dim=64)
    vec = encoder.encode("entity", ["user", "self_main"])
    assert len(vec) == 64
    assert any(v != 0 for v in vec)


def test_encoder_namespaces_are_independent():
    encoder = LatentEncoder(dim=64)
    entity_vec = encoder.encode("entity", ["greeting"])
    process_vec = encoder.encode("process", ["greeting"])
    assert entity_vec != process_vec


def test_encode_typed_returns_all_spaces():
    encoder = LatentEncoder(dim=64)
    latents = encoder.encode_typed(
        entity_ids=["user"],
        process_keys=["greeting"],
        state_keys=["happy"],
        claim_tuples=[("likes", "coffee")],
        model_keys=["uol_0"],
        context_id="ctx",
        self_mode="assistant",
        memory_claim_ids=["c1"],
        action_kind="answer",
        answer_intent="answer",
        answer_claim_ids=["c1"],
    )
    assert isinstance(latents, TypedLatents)
    assert len(latents.entity) == 64
    assert len(latents.answer) == 64
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_typed_latent_spaces.py -v`
Expected: PASS

- [ ] **Step 5: Integrate with answer operator**

In `cemm/operators/answer.py`, import `LatentEncoder` and set `answer_latent` on the SAG.

Find where the SAG is constructed and add:

```python
from ..latent.encoder import LatentEncoder

encoder = LatentEncoder()
answer_latent = encoder.encode_answer(
    intent=sag.intent,
    selected_claim_ids=sag.selected_claim_ids,
    selected_model_ids=sag.selected_model_ids,
)
```

Then pass `answer_latent=answer_latent` to the SAG constructor.

- [ ] **Step 6: Run tests**

Run: `python -m pytest cemm/tests/test_typed_latent_spaces.py cemm/tests/test_answer_operator.py -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 8: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 9: Commit**

```bash
git add cemm/types/latent_space.py cemm/latent/encoder.py cemm/operators/answer.py cemm/tests/test_typed_latent_spaces.py
git commit -m "feat: add typed latent space encoder and populate answer_latent"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G26 No typed latent spaces | LatentSpaceSpec, TypedLatents, and LatentEncoder exist. answer_latent is populated by AnswerOperator. |

### Placeholder Scan

No placeholders.

### Type Consistency

- `LatentSpaceSpec` and `TypedLatents` are dataclasses.
- `LatentEncoder` reuses the existing TL1 hash encoder for deterministic baselines.
- `answer_latent` is a list of floats matching the SAG field.
