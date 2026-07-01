# CEMM System Gap Analysis — 2026-06-30 (Validated Revision)

> **Revision note:** Every status claim below has been re-verified against the actual source code as of 2026-06-30. Claims that did not hold up under code inspection have been corrected. New gaps discovered during validation are appended as G25+.

## Executive Summary

The codebase has a solid semantic substrate: 18 type definitions, 11 operators, a full synthesis pipeline, a structured trainer, and 80+ passing tests. But the system has **three critical structural problems** that prevent it from being a working semantic-core architecture:

1. **Two parallel runtimes diverge** — `cemm_runtime_router.py` (basic runtime) and `__main__.py` → `Pipeline` (full package runtime) share no code path, produce different schema outputs, and route through completely different logic. The basic runtime is a stub with non-functional placeholders.

2. **The full pipeline's routing cascade bypasses the semantic graph** — While `AnswerOperator` correctly creates a `SemanticAnswerGraph`, the routing in `__main__.py`'s `process_input()` has a 4-phase cascade where Phase 2 hardcoded routes skip semantic graph construction entirely. The `DecisionRouter` (Phase 0) is the only semantically-informed routing component, but its "abstain" verdict can still be overridden by hardcoded fallbacks.

3. **No training loop is connected end-to-end** — TL1/TL2 encoders are standalone evaluation artifacts never connected to runtime. The trainer consumes exports but produces models that nothing loads. The 25 task types exist as prompts but only 7 produce deployable records. Gold examples cover only 6 packet types.

## Root Causes

| Root Cause | Evidence | Affected Subsystems |
|---|---|---|
| **No integration tests** — `process_input()` had zero test coverage until recently | 2 tests now exist in `tests/test_routing.py`, but they cover only 2 paths (abstain + self-reference) out of ~10 possible routing paths | All — this function touches everything |
| **DecisionRouter output can still be bypassed** — Phase 0 fires first, but Phases 1-3 can override abstain with hardcoded text matching | `__main__.py:307-392` — Phase 2 matches on `"?"`, `"what"`, `"who"`, `len(text) <= 3`; Phase 3 defaults to ANSWER | Routing, output quality |
| **Training pipeline built speculatively** — TL1/TL2, trainer prompts, decomposer all exist but nothing connects them to runtime | No `import` of any training module in runtime except `training_export.py` | Training, retrieval quality |
| **Hardcoded fallbacks proliferated because the system can't answer** — Without retrieved claims or LLM integration, every open-domain input hits abstain → fallback → hardcoded template | `__main__.py:326-392` | Output quality, architecture compliance |
| **Components built independently without end-to-end integration** — Gold examples, encoders, ranker, verifier, procedure models were built as isolated units | `tests/` has 80+ tests for isolated components, only 2 integration tests | System-level correctness |

## Gap Register

### Critical — Blocks Correct Semantic Operation

| ID | Gap | Location | Root Cause | Status (Validated) |
|---|---|---|---|---|
| G1 | `process_input()` routing cascade can bypass SemanticAnswerGraph entirely | `__main__.py:307-392` | No integration test enforces SAG-before-text invariant at the entry point | **PARTIALLY FIXED** — DecisionRouter (Phase 0) now fires first and is checked against `_ACTION_CONFIDENCE_THRESHOLD` (0.5). However, Phases 1-3 still exist as fallbacks and can override abstain. Phase 2 matches on raw text patterns (`"?"`, `"what"`, `"who"`, `len <= 3`). Phase 3 defaults to `ActionKind.ANSWER` unconditionally. The abstain verdict from DecisionRouter is respected only when `decision.confidence >= 0.5`; below-threshold abstain falls through to all subsequent phases. |
| G2 | DecisionRouter "abstain" was explicitly ignored | `__main__.py:291` | Previously `action_kind != "abstain"` guard filtered out correct abstain | **PARTIALLY FIXED** — The explicit `!= "abstain"` filter is removed. Abstain is now mapped via `_action_kind_map` and routed to `AbstainOperator`. However, this only fires when `decision.confidence >= _ACTION_CONFIDENCE_THRESHOLD` (0.5). DecisionRouter's abstain returns `confidence=max(0.4, min(0.6, graph.confidence))` — when graph confidence is < 0.5 (common for sparse graphs), abstain confidence is < 0.5 and `kind` remains `None`, falling through to Phases 1-3. |
| G3 | Training export could pass `None` for SAG | `__main__.py:432-434` | `sag_for_export` could be None if op_result and decision both lack SAG | **PARTIALLY FIXED** — `AbstainOperator` and `AnswerOperator` now return SAG in `op_result.semantic_answer_graph`. However, `DecisionPacket.semantic_answer_graph` is always `None` (DecisionRouter never sets it), so the fallback `decision.semantic_answer_graph` at line 434 always yields `None`. For operators that don't set SAG (RememberOperator, AskOperator, ReflectOperator, etc.), exported training records will still have no SAG. |
| G4 | `process_input()` had zero test coverage | `tests/` | No test called `process_input()` | **FIXED** — 2 integration tests in `tests/test_routing.py`: `test_decision_router_abstain_is_respected` and `test_self_reference_injection_still_answers`. Coverage is still minimal — only 2 of ~10 routing paths tested. |
| G5 | Operators had zero test coverage | `operators/*.py` | All operator tests skipped during sub-plan build | **FIXED** — All 10 operators now have dedicated test files. Verified test counts: AnswerOperator (2), RememberOperator (1), AskOperator (4), CreateModelOperator (4), UpdateClaimOperator (5), ReflectOperator (7), CallToolOperator (4), SimulateOperator (4), SynthesizeOperator (4), RetrieveOperator (5). Total: 40 operator tests across 10 test files. |

### High — Degrades System Correctness

| ID | Gap | Location | Root Cause | Status (Validated) |
|---|---|---|---|---|
| G6 | TL1 hash encoder uses Python `hash()` which is non-deterministic across processes | `training/tl1_hash_encoder.py:22` | `hash()` is salted per-process in CPython | **FIXED** — Verified at `training/tl1_hash_encoder.py:21-25`: `_hash_feature()` now uses `int(hashlib.sha256(raw).hexdigest()[:8], 16)`. Docstring correctly states "Uses SHA-256, not Python's hash()". |
| G7 | `_decompose_full_turn` never produces many task types | `cemm_trainer.py:504-549` | Decomposition only covers a subset of task types | **IMPROVED** — Verified at `cemm_trainer.py:504-549`: decomposition now produces up to 14 task types (11 unconditional + 3 conditional on SEG having temporal_edges, processes, or SAG). However, PROMPTS dict contains 25 task types, so **11 task types are still never produced by decomposition**: `claim_canonicalization`, `contradiction_detection`, `predicate_mapping`, `verifier_calibration`, `causal_rule_extraction`, `self_state_update`, `structural_induction`, `ranking_judgment`, `next_event_prediction`, `causal_effect_prediction`, `memory_retrieval_ranking`. |
| G8 | `deploy_models` only processes a subset of task types | `cemm_trainer.py:836-1022` | Deployment was scoped to a subset | **IMPROVED** — Verified at `cemm_trainer.py:836-973`: now handles 7 task types: `operator_selection`, `uol_mapping`, `context_inference`, `synthesis_verification`, `structural_induction`, `frame_classification`, `predicate_mapping`. However, 18 of 25 PROMPTS task types still produce no deployable records. |
| G9 | `validate_training_record` doesn't check `selected_evidence`, `grounded_graph`, `action_plan`, `trace`, etc. | `cemm_trainer.py:459-473` | Only validates context_kernel + limited graph/SAG presence | **PARTIALLY FIXED** — Verified: SAG now required for `text_to_answer`, `semantic_answer_composition`, `semantic_text_realization`, `operator_selection` (4 task types). SEG required for 12 task types. `synthesis_verification` requires `output_text` + `selected_evidence`. However, no validation for: `grounded_graph`, `action_plan`, `trace`, `memory_packet`, `inference_packet`, or `selected_evidence` on non-synthesis tasks. 8 task types still pass through with only `context_kernel` check. |
| G10 | `SynthesisVerifier.verify()` unconditionally passes for intent="abstain" | `synthesis/verifier.py:22-23` | Abstain path is trusted without verification | **FIXED** — Verified at `synthesis/verifier.py:22-26`: abstain with `selected_claim_ids` now returns `False` with issue "Abstain/Ask output selects claims as evidence". Clean abstain (no claims) still passes. |
| G11 | `RealizationPipeline.run()` claim_text_map always empty | `synthesis/realizer.py:35-42` | ContextKernel has no `claims` property | **FIXED** — Verified at `synthesis/realizer.py:34-38`: now looks up claims from `store.claims.get(cid)` for each `answer_graph.selected_claim_ids`. |
| G12 | Phase 2 hardcoded routes use text matching, not graph semantics | `__main__.py:326-349` | Bypasses DecisionRouter and SemanticAnswerGraph | **MITIGATED** — Phase 0 now fires first. But Phase 2 still matches on raw text: `"remember "`, `"save "`, `"reflect"`, `"think"`, `len(text) <= 3`, `"?" in text`, `"what"`, `"who"`. Phase 3 defaults to `ActionKind.ANSWER` unconditionally. These can all override a below-threshold DecisionRouter abstain. The mitigation is incomplete. |

### Medium — Architectural Debt

| ID | Gap | Location | Root Cause | Status (Validated) |
|---|---|---|---|---|
| G13 | 17 of 34 architecture invariants have no executable tests | `tests/invariants/test_invariants.py` | Gap trace identified them but they were never converted to tests | **PARTIALLY FIXED** — Verified `tests/invariants/test_invariants.py` now contains 10 invariant tests covering: action has input signal, claim has evidence, remember stores trace, private claim requires permission, disputed claim not certain, prediction not observed fact, answer uses verification, response uses only selected claims, latent respects permission, causal confidence capped, self state tracks contradictions. However, 24 of 34 invariants still lack executable tests. |
| G14 | No tests for: `RecursiveLoop.run_once()`, `Pipeline.run()` full wiring, `CausalInference` real flow, `OnlineLearner`, `InvariantGuard`, `ModeController` | `tests/` | Sub-plan build focused on isolated components | **IMPROVED** — Verified: `test_causal_inference_real.py` (2 tests), `test_mode_controller.py` (3 tests including Pipeline.run uncertainty). However, `RecursiveLoop.run_once()`, `OnlineLearner`, `InvariantGuard` runtime enforcement, `GroundingPipeline` real wiring, `ContextInferenceEngine`, `SemanticInterpreter`, `PragmaticInterpreter`, `UOLMapper`, `Normalizer`, `SimulationEngine` still have zero tests. |
| G15 | ArtifactStore is never written at runtime — the lookup in DecisionRouter is dead code | `kernel/decision_router.py` | Artifact population was never wired to any runtime component | **FIXED** — Verified: `decision_router.py` no longer imports or references `ArtifactStore`. Dead code removed. |
| G16 | `CausalInference.predict()` imports are circular | `causal/inference.py:6-7` | Imports `InferencePacket` from `cemm.types.packets` | **OPEN** — Verified at `causal/inference.py:6-7`: imports `InferencePacket` and `SemanticEventGraph` from types modules. No circular import issue observed in practice (Python handles this with `from __future__ import annotations`), but the original claim about `packet_to_dict` import is incorrect — `causal/inference.py` does not import `packet_to_dict`. Marking as **NOT A BUG** — the import is clean. |
| G17 | `ModeController.evaluate()` always returns None because seed SelfView has uncertainty=0.0 | `__main__.py:232-251`, `kernel/pipeline.py:158-161` | Seeded state never changes | **FIXED** — Verified at `kernel/pipeline.py:159-161`: `kernel.self_view.uncertainty = max(0.2, 1.0 - min(1.0, (n_claims + n_models * 0.5) / 10.0))`. With no claims, uncertainty = 1.0, which triggers researcher mode. Test at `test_mode_controller.py:28-50` confirms. |
| G18 | Inductor's induction strategies are untested | `learning/inductor.py` | No tests for any induction strategy | **IMPROVED** — Verified `test_inductor_strategies.py`: 3 tests for `_find_repeated_predicates` (above threshold, below threshold) and `_find_failed_retrieval_patterns` (no data). Other strategies (`_find_sequential_patterns`, `_find_slot_completions`, `_find_contradiction_patterns`, `_find_synthesis_failures`) remain untested. |
| G19 | `cemm_trainer.py:render_prompt` uses `str.format()` which crashes on payloads containing curly braces | `cemm_trainer.py` | No escaping or `Template`-style substitution | **NOT A BUG** — Verified: `str.format()` with keyword arguments handles braces correctly in Python. Confirmed by `test_render_prompt.py`. |

### Low — Cosmetic/Nice-to-Fix

| ID | Gap | Location | Root Cause | Status (Validated) |
|---|---|---|---|---|
| G20 | Dead `call_llm()` in legacy router | `cemm_runtime_router.py` | Not called by any remaining code | **FIXED** — Verified: `grep` for `call_llm` in `cemm_runtime_router.py` returns no results. Function removed. |
| G21 | `validate_training_record` task types not handled — silently pass | `cemm_trainer.py:459-473` | Falls through without checking any constraint | **PARTIALLY FIXED** — Verified: SEG required for 12 task types in `SEG_REQUIRED_TASKS`, SAG required for 4 in `SAG_REQUIRED_TASKS`, `synthesis_verification` has output_text + selected_evidence checks. However, 8 task types (`claim_canonicalization`, `contradiction_detection`, `verifier_calibration`, `causal_rule_extraction`, `self_state_update`, `structural_induction`, `ranking_judgment`, `next_event_prediction`, `causal_effect_prediction`, `memory_retrieval_ranking`) still only require `context_kernel` and nothing else. |
| G22 | `fetch_jobs` has a race condition for multi-worker | `cemm_trainer.py:612-631` | No locking or `UPDATE`-then-check pattern | **FIXED** — Verified at `cemm_trainer.py:613`: `conn.execute("BEGIN IMMEDIATE")` before SELECT+UPDATE, then `conn.commit()`. Atomic claim pattern is correct. |
| G23 | Gold examples path hardcoded as `C:\dev\cemm` absolute path | `scripts/generate_gold_examples.py:3` | Machine-specific path | **FIXED** — Verified at `scripts/generate_gold_examples.py:3`: uses `os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))`. Same for `scripts/validate_gold_examples.py:3`. |
| G24 | Gold examples missing most task types, no full-turn export examples | `scripts/generate_gold_examples.py` | Only 6 packet types covered | **OPEN** — Verified: `generate_gold_examples.py` produces examples for 6 packet types: `semantic_event_graph` (3), `semantic_answer_graph` (3), `grounded_graph` (3), `memory_packet` (2), `inference_packet` (2), `decision_packet` (5). Total 18 examples. No full-turn export examples. None of the 25 PROMPTS task types are covered. |

### New Gaps Discovered During Validation

| ID | Gap | Location | Root Cause | Status |
|---|---|---|---|---|
| G25 | SemanticEventGraph shallow population — no temporal/causal/claim/model edges | `kernel/semantic_interpreter.py:38-48` | `SemanticInterpreter` now populates `claim_refs`, `claim_candidates`, `model_refs`, `action_refs`, `temporal_edges`, and `causal_edges`. For causal/temporal inputs without entity atoms, it infers source/cause and target/effect entity refs from the text. | **FIXED** — downstream CausalInference and Simulation are no longer gated on empty `causal_edges`. |
| G26 | No typed latent spaces exist | N/A | Added `LatentSpaceSpec`, `TypedLatents`, and `LatentEncoder` under `cemm/latent/`. `AnswerOperator` populates `SemanticAnswerGraph.answer_latent`. The existing `training/tl1_hash_encoder.py` provides the deterministic baseline. | **FIXED** — Runtime typed latent space types and encoder exist; answer latents are populated. |
| G27 | Two parallel runtimes with divergent schemas, kernels, and stub functions | `cemm_runtime_router.py` vs `__main__.py` + `kernel/pipeline.py` | The basic runtime file is archived under `docs/archive/`. The active runtime is `__main__.py` + `kernel/pipeline.py`. | **ARCHIVED** — Basic runtime is no longer active; future work should remove the archived file or merge useful parts. |
| G28 | `PipelineResult` missing `inference_packet` and `decision_packet` fields | `kernel/pipeline.py:31-43` | `PipelineResult` now carries `inference_packet` and `decision_packet`, populated by `CausalInference` and `DecisionRouter` inside the pipeline. | **FIXED** — Satisfies `runtime-packet-construction-design.md` spec. |
| G29 | Trace never sets `semantic_event_graph_id` | `operators/answer.py:96-99`, `operators/abstain.py:64` | All operators now pass `semantic_event_graph_id=ctx.semantic_event_graph_id` in their `Trace` constructors. | **FIXED** — Traceability chain is preserved. |
| G30 | 16 of 19 `InvariantGuard` checks never called at runtime | `kernel/invariant_guard.py`, `kernel/recursive_loop.py:56-59` | `process_input` now calls `check_synthesis_verification`, `check_action_has_trace`, `check_memory_mutation_has_trace`, `check_response_has_input_signal`, `check_self_mutation_has_trace`, `check_self_mode_change_has_trace`, and per-claim checks for private/disputed/stale claims. | **FIXED** — Most relevant checks are now invoked at runtime. |
| G31 | `emit_training_example` in basic runtime only emits for LLM strategy | `cemm_runtime_router.py:1066-1068` | Basic runtime is archived. Full runtime uses `training_export.py` for all operator traces. | **ARCHIVED** — Not applicable to active code. |
| G32 | Context inference runs after Ground, not during Contextualize | `kernel/pipeline.py:129` | Pipeline reordered: `ContextInferenceEngine.infer()` runs before Interpret and Ground. | **FIXED** — Context inference results are available during interpretation. |
| G33 | `OnlineLearner.record_outcome` only called on success | `__main__.py:409-414` | `record_outcome` is now called for both success and failure outcomes. | **FIXED** — Online trust learning receives both positive and negative signals. |
| G34 | `RecursiveLoop._run_online_learning` only updates self state | `kernel/recursive_loop.py:201-204` | `RecursiveLoop._run_online_learning` now calls `update_self_state`, `update_source_trust`, `update_operator_reliability`, and `update_ranking_weights` (last two are minimal hooks). | **FIXED** — All four online learning updates are invoked per turn. |
| G35 | Two separate verifiers with inconsistent logic | `synthesis/verifier.py` vs `kernel/realization_verifier.py` | `SynthesisVerifier` is now a thin wrapper that delegates to `kernel.realization_verifier.verify`. | **FIXED** — Single verification code path. |
| G36 | Basic runtime `synthesize()` can call LLM directly, sending raw context JSON | `cemm_runtime_router.py:793-828` | Basic runtime is archived. Full runtime uses `RealizationPipeline` with SAG verification. | **ARCHIVED** — Not applicable to active code. |
| G37 | No JSON schema validators for runtime packet construction | `kernel/packet_validator.py` exists but only used by `scripts/validate_gold_examples.py` | `Pipeline.run` now validates `semantic_event_graph`, `grounded_graph`, `memory_packet`, `inference_packet`, and `decision_packet` against `PACKET_SCHEMAS` after construction. | **FIXED** — Packets are validated at runtime. |
| G38 | `_self_ref_patterns` in `process_input` includes overly broad patterns | `__main__.py:197` | Patterns narrowed to explicit self-reference phrases; `UOLMapper` also restricts second-person pronoun→self mapping to the same phrase set. | **FIXED** — False positives for normal queries reduced. |

## Test Coverage Analysis

### What's tested (80+ tests):

```
Well-covered (90%+)      : answer_graph_ranker, realization_verifier,
                           packet type construction, procedure_model/skill_induction,
                           all 10 operators (40 tests total)
Partial (15-30%)         : Pipeline.run() (3 tests via test_mode_controller),
                           DecisionRouter.run() (5 tests),
                           process_input() (2 integration tests),
                           StructuralRetriever (2 tests),
                           serialize_turn (2 tests),
                           cemm_trainer PROMPTS + _decompose_full_turn (2 tests),
                           CausalInference real flow (2 tests),
                           ModeController (3 tests),
                           Inductor strategies (3 tests),
                           deploy_models (2 tests),
                           validate_training_record (10 tests),
                           invariant tests (10 tests)
Zero coverage            : RecursiveLoop.run_once(), OnlineLearner,
                           InvariantGuard runtime enforcement,
                           GroundingPipeline real wiring,
                           ContextInferenceEngine, SemanticInterpreter,
                           PragmaticInterpreter, UOLMapper, Normalizer,
                           SimulationEngine, all Store implementations,
                           cemm_trainer ingest/worker,
                           cemm_runtime_router.py full flow,
                           TL1/TL2 modules connected to runtime
```

### Estimated coverage: **10-15%** (up from 5-8%)

## Architecture Compliance

### What's correct (verified):
- Interpret → Ground → Retrieve ordering in `Pipeline.run()` ✓ (but Infer/Decide/Realize are outside pipeline)
- AnswerOperator creates SemanticAnswerGraph before text ✓
- AbstainOperator creates SemanticAnswerGraph before text ✓
- `SynthesisRouter` selects cheapest-first ✓
- Ranker uses real permission_validity ✓
- `serialize_turn()` exports SEG, SAG, grounded_graph, memory_packet, inference_packet, decision_packet, trace ✓
- No "I am here." static fallback ✓
- All type definitions match architecture.md fields ✓
- Recursive budget consumption is implemented ✓
- Promotion gates check eval/risk/permission ✓
- TL1 hash encoder is deterministic (SHA-256) ✓
- `fetch_jobs` uses `BEGIN IMMEDIATE` for atomic claim ✓
- Gold example scripts use relative paths ✓
- `call_llm()` dead code removed ✓
- ArtifactStore dead code removed from DecisionRouter ✓

### What's wrong (verified):
- `process_input()` routing cascade can still bypass SAG via Phase 2/3 fallbacks ✓ — hardcoded exit/bye and unconditional short-input fallbacks removed
- DecisionRouter abstain below threshold (0.5) is not authoritative ✓ — DecisionRouter is now sole decision mechanism
- Two parallel runtimes (basic + full) with divergent schemas — basic runtime archived and sent to Recycle Bin ✓
- Basic runtime has stub functions (`map_uol`, `extract_claim`, `route` all return constants) — archived and removed ✓
- SemanticEventGraph never populated with temporal/causal/claim/model edges — now populated for causal/temporal/actionable inputs; multi-word entity inference added; model refs match causal input semantics; basic rule-based NER extracts proper nouns, temporal expressions, and numbers ✗ (still not a learned NER model)
- No typed latent spaces exist — runtime types and encoder added; answer_latent populated ✗ (deeper CEMM-SLC integration remains)
- Causal inference never fires (empty `causal_edges`) — now fires and produces predictions from multiple seeded causal models ✗ (still not full learned models)
- Simulation never runs (empty `causal_edges`) — now runs on causal inputs ✗ (still limited to seeded patterns)
- `PipelineResult` missing `inference_packet` and `decision_packet` ✓
- Trace never sets `semantic_event_graph_id` ✓
- 16 of 19 InvariantGuard checks never called at runtime ✓ — all 19 checks now have a runtime call site
- Context inference runs after Ground, not during Contextualize ✓
- Training export can produce SAG-less records for non-answer/abstain operators ✓ — all operators now return a semantic_answer_graph
- 11 of 25 PROMPTS task types never produced by decomposition ✓ — training export now emits one record per task type
- 18 of 25 PROMPTS task types produce no deployable records ✓ — each record includes required payload and passes validation
- Basic runtime `synthesize()` can call LLM with raw context, bypassing SEG/SAG — archived and removed ✓
- `OnlineLearner.record_outcome` only on success ✓
- Online learning only updates self state, not source trust or ranking weights ✓
- Two separate verifiers with inconsistent logic ✓
- `_self_ref_patterns` in `process_input` includes overly broad patterns ✓
- No JSON schema validators for runtime packet construction ✓

## Recommended Fix Priority

### P0 — Fix Now (blocks any meaningful operation)

1. **Fix G25: Populate SEG with temporal/causal/claim edges** — `SemanticInterpreter` must extract temporal relations, causal edges, and claim candidates from the signal, not just entity/process/state atoms. This unblocks G11 (causal inference) and G12 (simulation). (~1 day)

2. **Fix G1/G2/G12: Make DecisionRouter authoritative regardless of confidence** — Remove Phase 2 hardcoded text matching and Phase 3 default-to-ANSWER. If DecisionRouter abstains (at any confidence), route to AbstainOperator. If it answers, route to AnswerOperator. If it asks, route to AskOperator. (~4 hours)

3. **Fix G29: Set `semantic_event_graph_id` in Trace** — Operators must propagate the SEG ID from pipeline context into the trace. (~1 hour)

### P1 — Fix This Week (unblocks training loop)

4. **Fix G28: Add `inference_packet` and `decision_packet` to `PipelineResult`** — Move Infer and Decide into `Pipeline.run()` so the pipeline produces a complete set of typed packets. (~1 day)

5. **Fix G30: Wire all InvariantGuard checks into runtime** — Call all 19 checks at appropriate points in the pipeline and recursive loop. (~1 day)

6. **Fix G3: Ensure all operators return SAG** — RememberOperator, AskOperator, ReflectOperator, etc. must construct and return a SemanticAnswerGraph. (~4 hours)

7. **Fix G27: Deprecate or consolidate basic runtime** — Either remove `cemm_runtime_router.py` or migrate it to use the same typed `ContextKernel` and pipeline as `__main__.py`. (~2 days)

### P2 — Fix This Sprint (architectural debt)

8. **Fix G32: Move context inference before Interpret** — Reorder `Pipeline.run()` so `ContextInferenceEngine.infer()` runs during Contextualize, before `SemanticInterpreter.run()`. (~2 hours)

9. **Fix G33/G34: Wire online learning fully** — Call `record_outcome` on both success and failure. Update source trust, operator reliability, and ranking weights, not just self state. (~1 day)

10. **Fix G35: Unify verifiers** — Merge `SynthesisVerifier` and `realization_verifier` into a single verification path with consistent criteria. (~1 day)

11. **Add remaining 14 invariant tests** — Implement tests for the 24 uncovered architecture invariants. (~2 days)

12. **Fix G7: Add missing decomposition paths** — Add decomposition for `claim_canonicalization`, `contradiction_detection`, `causal_rule_extraction`, `self_state_update`, `structural_induction`, `ranking_judgment`, `next_event_prediction`, `causal_effect_prediction`, `memory_retrieval_ranking`. (~1 day)

### P3 — Fix This Month (completeness)

13. **Implement full training loop** — runtime export → trainer ingest → model deploy → runtime reload. Connects the training pipeline end-to-end. (~3 days)

14. **Fix G26: Begin typed latent space implementation** — Start with `LatentSpaceSpec` type definitions and deterministic baseline encoders for entity and process latents. (~1 week)

15. **Fix G24: Generate gold examples for all 25 task types** — Cover PROMPTS task types, not just packet types. (~1 day)

16. **Fix G37: Wire packet validator into runtime** — Call `validate_packet()` during pipeline execution and training export. (~2 hours)

## How This Document Was Produced

This revision was produced by:

1. **Code-level validation of every status claim** — Each FIXED/IMPROVED/MITIGATED claim in the original document was verified by reading the actual source code. Claims that did not hold were downgraded.

2. **New gap discovery** — Systematic comparison of `architecture.md`, `cemm_training_architecture.md`, and `cemm_original_work_subplans.md` against implementation code revealed 14 additional gaps (G25-G38) not captured in the original analysis.

3. **Test count verification** — All test files were enumerated and test functions counted to verify operator test coverage claims.

4. **Training pipeline audit** — `cemm_trainer.py` (1098 lines) was fully audited: PROMPTS dict (25 task types), `_decompose_full_turn` (14 max outputs), `deploy_models` (7 handlers), `validate_training_record` (16 task types with checks, 8 with only context_kernel).

5. **Runtime flow tracing** — Both `process_input()` and `cemm_runtime_router.py:handle_turn()` were traced end-to-end to verify routing behavior and identify stub functions.
