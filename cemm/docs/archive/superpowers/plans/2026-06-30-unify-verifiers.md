# Unify SynthesisVerifier and RealizationVerifier

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Close G35 — Two separate verifiers with inconsistent logic. Make `SynthesisVerifier` a thin compatibility wrapper around the more complete `RealizationVerifier` so all verification follows one code path.

**Architecture:** `RealizationVerifier` already absorbed the `SynthesisVerifier` evidence-integrity rules (`_check_evidence_integrity`). Keeping both classes means fixes to verification logic must be duplicated or diverge. The fix is to have `SynthesisVerifier.verify` build a minimal `SemanticAnswerGraph` from its arguments and delegate to `kernel.realization_verifier.verify`.

**Tech Stack:** Python 3.13, SynthesisVerifier, RealizationVerifier, SemanticAnswerGraph.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/synthesis/verifier.py` | Legacy high-level verifier | Modify |
| `cemm/kernel/realization_verifier.py` | Deterministic verifier | Read-only |
| `cemm/tests/test_synthesis_verifier.py` | SynthesisVerifier tests | Read-only / verify |

---

## Task 1: Make SynthesisVerifier delegate to RealizationVerifier

**Files:**
- Modify: `cemm/synthesis/verifier.py`

- [ ] **Step 1: Read both verifier APIs**

Run: `python -c "from cemm.synthesis.verifier import SynthesisVerifier; import inspect; print(inspect.signature(SynthesisVerifier.verify))"`
Run: `python -c "from cemm.kernel.realization_verifier import verify; import inspect; print(inspect.signature(verify))"`

- [ ] **Step 2: Implement delegation**

Replace the body of `SynthesisVerifier.verify` with:

```python
from ..types.semantic_answer_graph import SemanticAnswerGraph
from ..kernel.realization_verifier import verify as _realization_verify


class SynthesisVerifier:
    def verify(
        self,
        output: str,
        selected_claim_ids: list[str],
        selected_model_ids: list[str],
        kernel: ContextKernel,
        claims: list[Claim] | None = None,
        intent: str = "",
    ) -> tuple[bool, list[str]]:
        # Build a minimal SAG from the legacy verifier inputs so we can use
        # the single, authoritative realization verifier.
        sag = SemanticAnswerGraph(
            id="synthesis_verifier_sag",
            intent=intent or "answer",
            source_signal_ids=[],
            context_id=kernel.id if kernel else "",
            selected_claim_ids=list(selected_claim_ids),
            selected_model_ids=list(selected_model_ids),
            confidence=1.0 - kernel.self_view.uncertainty if kernel and kernel.self_view else 0.5,
            permission_scope=kernel.permission.scope.value if kernel else "public",
        )
        result = _realization_verify(
            sag=sag,
            output_text=output,
            claims=claims,
            registry=None,
        )
        return result.verified, result.details
```

Keep the existing imports (Claim, ClaimStatus, ContextKernel, SignalKind) unless they become unused.

- [ ] **Step 3: Run SynthesisVerifier tests**

Run: `python -m pytest cemm/tests/test_synthesis_verifier.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 5: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 6: Commit**

```bash
git add cemm/synthesis/verifier.py
git commit -m "refactor: unify SynthesisVerifier with RealizationVerifier"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G35 Two verifiers with inconsistent logic | SynthesisVerifier now delegates to RealizationVerifier, so all verification logic lives in one place. |

### Placeholder Scan

No placeholders. Code is complete.

### Type Consistency

- `SynthesisVerifier.verify` returns `tuple[bool, list[str]]` as before.
- `SemanticAnswerGraph` fields match the constructor signature.
