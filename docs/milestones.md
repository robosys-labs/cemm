# CEMM — Milestones

## M0: Foundation (BLOCKER)
**Gate:** All 18 invariant tests pass.

### Tasks
- [x] Project skeleton (pyproject.toml, directory structure)
- [x] Type definitions (6 primitives, ContextKernel, Permission, Trace, OperatorSpec)
- [x] SQLite schema (10 tables with 16 indexes)
- [x] Store layer (SignalStore, EntityStore, ClaimStore, ModelStore, ActionStore, SelfStore, SourceTrustStore)
- [x] Invariant test suite (18 tests matching ERCA spec §23)
- [ ] **Verify:** `python -m pytest tests/invariants/ -v` — all 18 pass

---

## M1: Kernel + Registry (BLOCKER)
**Gate:** Pipeline accepts input, builds ContextKernel, normalizes predicates.

### Tasks
- [x] Registry (predicate/entity/operator canonicalization + JSON serialization)
- [x] ContextKernelBuilder (from scratch, from signal, time bucket)
- [x] Normalizer (predicate canonicalization)
- [x] EntityResolver (by name, by alias, resolve_or_create, resolve_self)
- [x] FrameEngine (invalidates out-of-frame claims, supersession detection)
- [x] Pipeline skeleton (signal → kernel → store)
- [ ] **Verify:** `python -m pytest tests/test_pipeline.py -v` — 3 pass
- [ ] **Verify:** `python -m pytest tests/test_registry.py -v` — 5 pass

---

## M2: Retrieval + Ranking (BLOCKER)
**Gate:** Structural retrieval returns ranked claims and models.

### Tasks
- [x] StructuralRetriever (index-first retrieval with 6 query modes)
- [x] retrieve_for_kernel (entity-based bulk retrieval)
- [x] Ranker (score_claim, score_model with permission gating)
- [x] Confidence module (log-odds, update_log_odds, scoring formulas)
- [ ] **Verify:** `python -m pytest tests/test_confidence.py -v` — 12 pass

---

## M3: Operators (FUNCTIONAL)
**Gate:** All 10 operators execute and produce results.

### Tasks
- [x] OperatorRegistry (dispatch by ActionKind)
- [x] BaseOperator (abstract class with spec)
- [x] AnswerOperator
- [x] AskOperator
- [x] RememberOperator
- [x] UpdateClaimOperator
- [x] CreateModelOperator
- [x] SynthesizeOperator
- [x] SimulateOperator
- [x] RetrieveOperator
- [x] ReflectOperator
- [x] AbstainOperator
- [ ] **Verify:** `python -m pytest tests/test_store.py -v` — 12+ pass

---

## M4: Synthesis (FUNCTIONAL)
**Gate:** Synthesis router selects cheapest adequate strategy, verifier blocks invalid output.

### Tasks
- [x] SynthesisRouter (strategy selection + dispatch)
- [x] TemplateStrategy (key-based templates with variable substitution)
- [x] ExtractiveStrategy (claim-to-text rendering)
- [x] SynthesisVerifier (empty output, disputed/retracted claims)
- [ ] **Verify:** `python -m pytest tests/invariants/test_synthesis.py -v` — 6 pass

---

## M5: Causal Reasoning (FUNCTIONAL)
**Gate:** Causal inference runs bounded prediction.

### Tasks
- [x] CausalInference (precondition/effect matching, transitive closure)
- [x] SimulationEngine (result signal + predicted claims)
- [ ] **Verify:** `python -m pytest tests/test_causal.py -v` — 3 pass

---

## M6: Learning (FUNCTIONAL)
**Gate:** Online learning updates trust, inductor creates candidates, promotion validates.

### Tasks
- [x] OnlineLearner (outcome recording, claim confidence update)
- [x] Inductor (repeated predicate detection, failed retrieval patterns)
- [x] ModelPromoter (candidate → active with validation gates)
- [ ] **Verify:** Unit tests for inductor + promoter

---

## M7: Acceptance Tests (QUALITY)
**Gate:** All acceptance tests pass, covering ERCA spec §24 scenarios.

### Tasks
- [x] Context interpretation test
- [x] Memory retrieval test
- [x] Permission blocking test
- [x] Synthesis routing test
- [ ] **Verify:** `python -m pytest tests/test_acceptance.py -v` — 5 pass

---

## M8: Integration + CLI (MVP)
**Gate:** Full pipeline from CLI input to synthesized output.

### Tasks
- [x] CLI entry point (cemm/__main__.py)
- [x] Interactive chat loop
- [x] Seeded registry with seed operators
- [x] End-to-end: input → kernel → retrieve → rank → answer → output
- [x] **Verify:** Manual chat session with 3+ turns
- [x] **Verify:** `python -m pytest tests/ -v` — all tests pass

---

## M9: Production Hardening (STABLE)
**Gate:** No regressions, full ERCA compliance.

### Tasks
- [x] WAL-mode persistence with crash recovery
- [x] Budget enforcement in pipeline loop
- [x] Permission gating in all operators
- [x] Causal inference cycle detection
- [x] Inductor threshold configuration
- [ ] Performance benchmarks (latency, memory)
- [ ] **Verify:** `python -m pytest tests/ -v` — all pass, no skips
- [ ] **Verify:** 1000-turn stress test with no leaks
