# CEMM Architecture Gap Trace - Deep Audit

Date: 2026-06-29
Scope: current implementation in `C:\dev\cemm\cemm`, canonical root SLC docs, archived SLC snapshot under `docs\archive\new-slc-snapshot-2026-06-29`, and tests in `C:\dev\cemm\tests`.

This audit follows the new architecture section by section. The earlier trace was only a triage list; this version treats `architecture.md`, `cemm_training_architecture.md`, `cemm_pipeline.md`, `cemm_implementation_plan.md`, and `cemm_acceptance_tests.md` as the contract.

## Evidence Commands

- Demo transcript: `output.log`
- Demo DB: `demo_runtime.sqlite3`
- Demo training export: `generated\codex_demo_runtime_training.jsonl`
- Final verification: `python -m pytest tests --tb=short -q`
- Final result: `221 passed in 1.22s`
- Source map commands:
  - `rg -n "^#{1,4} " architecture.md cemm_training_architecture.md cemm_pipeline.md cemm_implementation_plan.md cemm_acceptance_tests.md`
  - `rg -n "SemanticEventGraph|SemanticAnswerGraph|DecisionPacket|Realize|Decide|Ground|Interpret|permission_validity|frame|budget|trace|training|fallback|call_llm" -S .`
  - `rg -n "class |def |@dataclass|Enum|CREATE TABLE|interface |type " types kernel retrieval synthesis operators training learning causal store registry confidence cemm_runtime_router.py cemm_trainer.py cemm_seed_generator.py __main__.py`

## Executive Summary

The codebase has a good ERCA-shaped substrate: Signal, Claim, Model, Action, ContextKernel, UOL atoms, storage, retrieval, ranker, pipeline, recursive loop, synthesis strategies, trainer queue, seed generator, and tests. However, the new CEMM-SLC architecture is a semantic-core architecture, and the current runtime is still mostly a deterministic text router with architecture-shaped metadata.

The highest-impact gap is not a missing feature; it is an ordering and representation mismatch:

```text
Required:
Signal + ContextKernel + Memory
-> SemanticEventGraph
-> typed latent / Decide
-> SemanticAnswerGraph or ActionPlan
-> Realize
-> Verify
-> Trace
-> Export

Current package runtime:
Signal
-> ContextKernel
-> normalize text
-> context inference
-> frame rules
-> retrieve/rank
-> pragmatic UOL-ish semantics
-> hardcoded route
-> operator returns text
-> optional SynthesisRouter fallback

Current basic router:
build_context
-> observe
-> normalize text
-> infer_context(text)
-> map_uol(text)
-> route(text)
-> synthesize(text)
-> trace/export
```

The archived SLC snapshot at `docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py` is closer because it builds lightweight `semantic_event_graph` and `semantic_answer_graph` dictionaries, but even there final text is produced before `compose_semantic_answer_graph()` (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:871-872`). So the root docs are the target; the archived code is a partial bootstrap, not a compliant endpoint.

## Current Vs Proposed Runtime Files

### Current `cemm_runtime_router.py`

- Has SQLite runtime tables, ContextKernel dict, UOL-ish atoms, direct claim extraction, direct routing, direct synthesis, trace export, and an unused runtime `call_llm()`.
- Does not have `build_semantic_event_graph()`.
- Does not have `compose_semantic_answer_graph()`.
- Training export does not emit semantic graph task types.
- Static fallback remains: `return "I am here."` (`cemm_runtime_router.py:1132`).

### Proposed `docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py`

- Adds `build_semantic_event_graph()` (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:528-558`).
- Adds `compose_semantic_answer_graph()` (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:726-764`).
- Adds graph fields to traces (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:805-849`).
- Adds graph/latent/answer/text-realization exports (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:911-963`).
- Still produces text before composing the answer graph (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:871-872`).
- Still routes and synthesizes with English regex/text matching (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:561-723`).

Conclusion: copy-forward from the archived snapshot is not enough. It is useful migration material, but the implementation must invert answer flow so graph comes before text.

## Architecture Section Audit

### Section 1 - Core Law (`architecture.md:7`)

Requirement: CEMM is a language model / MOE-SLM over semantic representations, not a wrapper or deterministic rule engine.

Current evidence:
- `cemm_runtime_router.py:686-871` uses English text, regexes, and hand-coded branches for context/routing.
- `__main__.py:181-238` does the same for self reference and action selection before consulting operator models.

Gap:
- Current code is still rule-first and text-first. Rules are acceptable as the cheapest layer, but not as the primary open-domain semantics layer.

Fix:
- Introduce a `DecisionRouter` that consumes `SemanticEventGraph`, selected memory, ContextKernel, and active operator models. Keep deterministic rules only as high-precision graph/action resolvers.

### Section 2 - Primitive Units (`architecture.md:45`)

Requirement: primitive units include Signal, Entity, Claim, Model, Action, Self, Permission, ContextKernel, Trace.

Current evidence:
- Present: `types\signal.py`, `types\entity.py`, `types\claim.py`, `types\model.py`, `types\action.py`, `types\self_state.py`, `types\permission.py`, `types\context_kernel.py`, `types\trace.py`.
- Store schema persists most primitives in `store\schema.py`.

Gap:
- Primitive layer is strong but incomplete for SLC because SemanticEventGraph and SemanticAnswerGraph are not first-class types.
- Trace is shallow: it has selected ids and synthesis flags, but no graph packet fields (`types\trace.py`).

Fix:
- Add `types\semantic_event_graph.py` and `types\semantic_answer_graph.py`.
- Extend `Trace` to reference serialized graph ids or embedded graph packets.

### Section 3 - Signal (`architecture.md:70`) and Section 3.1 - Semantic Event Graph (`architecture.md:208`)

Requirement: Signal is observed input; SemanticEventGraph is the native higher-order meaning form.

Current evidence:
- `Signal` has `observation_semantics` only (`types\signal.py:33-65`).
- `ObservationSemantics` contains speech act, target, semantic cluster, affect, repetition, and raw `uol_atoms`, but not graph edges, claim/model refs, action refs, permissions, or typed graph identity.
- Basic router stores `semantics_json` on signals, not a graph (`cemm_runtime_router.py:672-683`, `cemm_runtime_router.py:1227-1229`).

Gap:
- Semantics are annotations, not a `SemanticEventGraph`.
- Causal/temporal edges are absent from runtime graph packets.
- Claim candidates are stored separately and not always attached to the meaning packet.

Fix:
- Interpret stage must output `SemanticEventGraph`.
- Store `semantic_event_graph_json` on traces and optionally signals.
- Make claim extraction consume graph processes/states instead of raw text.

### Sections 4-6 - Entity, Claim, Model (`architecture.md:318`, `359`, `411`)

Requirement: entities/claims/models are typed, evidence-backed, frame-aware, permission-aware, and promotion-gated.

Current evidence:
- Entities, claims, and models exist and have evidence/permission/frame fields (`types\claim.py`, `types\model.py`, `store\schema.py`).
- Claims have `frame_id`, `valid_from`, `valid_until`, evidence ids, confidence, trust.
- Models have kind/status/evidence/permission/risk/cost.

Gaps:
- `ModelKind` lacks the new `semantic_encoder` and `text_realizer` kinds (`types\model.py:7-21`; new architecture lists these at `cemm_training_architecture.md:472`).
- Promotion can approve a model directly by setting active with no validation/eval/risk gate (`training\promoter.py:29-46`).
- Basic runtime `models` table is separate and simpler than package store schema (`cemm_runtime_router.py:129-153`).

Fix:
- Extend `ModelKind` and schema for semantic encoder/text realizer/model eval metadata.
- Replace `Promoter.approve()` with validation-gated promotion: eval pass, risk pass, permission pass, cost pass, regression pass.
- Unify or clearly deprecate basic-router model schema.

### Section 7 - Action (`architecture.md:479`)

Requirement: action is produced by Decide and includes selected claims/models/signals, permission, confidence, trace, fallback.

Current evidence:
- Package `Action` supports selected ids and trace (`types\action.py`).
- Basic runtime `RouteDecision` is not an Action and stores only selected claim ids (`cemm_runtime_router.py:197-205`).
- Basic runtime writes actions after route/synthesis, with no operator model id or selected model ids (`cemm_runtime_router.py:1179-1219`).

Gap:
- Basic runtime action trace is not a full architectural action.
- Package runtime bypasses a formal DecisionPacket; `process_input()` picks `ActionKind` directly (`__main__.py:218-275`).

Fix:
- Add `types\decision_packet.py`.
- `DecisionRouter.run()` must produce `DecisionPacket`.
- `ActionStore` write should happen from DecisionPacket after permission/budget gates.

### Section 8 - Self (`architecture.md:546`)

Requirement: Self state and SelfView are context inputs, not ungrounded persona text.

Current evidence:
- Package has `SelfState` and `SelfView` dataclasses.
- Basic runtime has dict-based self state and self view builder.
- Demo "who are you" response is self-state grounded.

Gaps:
- Basic and package self models differ.
- Full package injects self entity through text pattern matching (`__main__.py:181-194`).
- Self updates are not always tied to explicit action traces in basic runtime beyond recent trace id mutation.

Fix:
- Route self-reference through SemanticEventGraph target/entity refs.
- Emit self mutation actions/traces and enforce in tests.

### Section 9 - Permission (`architecture.md:628`)

Requirement: permission gates memory use, execution, sharing, retention, and training use.

Current evidence:
- Package `Permission` has scope/storage/retrieval/use/share/execute/retention (`types\permission.py`).
- Basic runtime uses dict permission with `can_use_user_memory`, `can_write_user_memory`, `can_call_external_tools` (`cemm_runtime_router.py:631-636`).

Gaps:
- Two permission systems exist.
- Runtime training export uses `local_training` or context scope but does not enforce private-data training law deeply (`cemm_runtime_router.py:1278-1301`, `cemm_runtime_router.py:1355-1358`).
- Ranker filters by permission but passes `permission_valid=True` to scoring (`retrieval\ranker.py:37-45`, `60-68`).

Fix:
- Normalize basic runtime onto `Permission`.
- Add `permission_validity(claim/model, kernel)` and pass real value to scoring.
- Add export-time privacy tests for user-private/session-private data.

### Section 10 - Context Kernel (`architecture.md:682`)

Requirement: 9-section ContextKernel is the input for every decision.

Current evidence:
- Package `ContextKernel` has world/user/time/conversation/goal/memory/self_view/permission/budget, but not an explicit `self_state` field (`types\context_kernel.py`).
- Basic runtime dict ContextKernel includes both self_state and self_view (`cemm_runtime_router.py:656-669`).

Gaps:
- Package and basic runtime kernels diverge.
- Package kernel lacks `self_state` even though docs and AGENTS call for 9 sections including `self_state`.
- Package pipeline builds kernel before normalization and then mutates signal content (`kernel\pipeline.py:64-82`).

Fix:
- Add `self_state` or explicit `self_state_id` to package ContextKernel.
- Keep raw signal immutable; add normalized content / graph fields separately.
- Create a single kernel contract used by both CLIs.

### Section 10.1 - Semantic Latent Core and Foundational Operators (`architecture.md:849-1064`)

Requirement: typed latent representation; operators Interpret/Ground/Retrieve/Infer/Decide/Realize; dense generation only as realization fallback.

Current evidence:
- No typed latent representation type.
- No `SemanticInterpreter`, `GroundingPipeline`, `DecisionRouter`, or `RealizationPipeline` modules.
- `OperatorRegistry` registers domain-ish actions (`answer`, `ask`, `remember`, etc.) rather than foundational operators (`operators\registry.py`, `__main__.py:43-83`).

Gaps:
- Current operators are action handlers, not foundational transformations.
- No typed latent supervision or runtime component loading.
- Dense/neural path exists as a synthesis strategy but not as graph-bounded realization.

Fix:
- Create foundational operator modules under `kernel/` or `slc/`: observe, contextualize, interpret, ground, retrieve, infer, decide, realize, update, learn.
- Keep legacy action operators behind `ActionExecutor`, after Decide.

### Section 10.1.3 - Semantic Answer Graph (`architecture.md:1064`)

Requirement: answer meaning exists before text.

Current evidence:
- Current runtime has no answer graph.
- `docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py` composes an answer graph after `synthesize()` returns final text (`docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py:871-872`).
- Package `AnswerOperator` can directly return `answer_text` (`operators\answer.py`, called from `__main__.py:236-238`, `272-275`).

Gap:
- Both current and proposed bootstrap code violate the order "answer -> SemanticAnswerGraph -> Realize -> Verify."

Fix:
- `AnswerOperator` must return an `OperatorResult` carrying `semantic_answer_graph`, not final text.
- Realizer chooses template/extractive/neural/abstain from graph + evidence.

### Section 10.1.4 - Universal Core Loop (`architecture.md:1126`) and Section 21 - Recursive Runtime (`architecture.md:1925`)

Requirement: Observe -> Contextualize -> Interpret -> Ground -> Retrieve -> Infer -> Decide -> Realize -> Update -> Learn -> maybe recurse.

Current evidence:
- Package pipeline: signal -> kernel -> normalize -> context inference -> resolve self -> frame -> retrieve/rank -> semantics (`kernel\pipeline.py:64-123`).
- Basic runtime: context -> observe -> normalize -> infer_context -> map_uol -> route -> synthesize -> trace/export (`cemm_runtime_router.py:1222-1243`).
- Recursive loop subtracts parent `result.cost_ms` before children and not child `sub_result.cost_ms` after (`kernel\recursive_loop.py:62-103`).

Gaps:
- Interpret happens after retrieval/ranking in package pipeline.
- Ground is not a distinct stage.
- Decide is hardcoded route.
- Realize is direct synthesis.
- Recursive budget is under-accounted.

Fix:
- Refactor `Pipeline.run()` around explicit stage result packets.
- Update `RecursiveLoop` to decrement child budget by child actual cost and return budget telemetry.
- Add stage-order tests.

### Section 11 - Memory Architecture (`architecture.md:1210`)

Requirement: semantic, episodic, procedural, registry, causal, self, trust, permission memory are views over primitives.

Current evidence:
- `retrieval\memory_views.py` implements memory views.
- Store schema has source trust, actions, models, claims, signals.

Gaps:
- Memory views do not expose semantic graph memory or answer graph memory.
- Retrieval does not consume SemanticEventGraph.
- Vector table exists as optional storage but no explicit dense fallback guard around retrieval (`store\schema.py:316-327`).

Fix:
- Add graph packet memory views.
- Use graph-grounded retrieval query fields.
- Add no-dense-fallback regression tests.

### Section 12 - Registry And Frames (`architecture.md:1231`)

Requirement: registry holds canonical predicates/operators/UOL/frame rules; frame validity must reject out-of-frame claims.

Current evidence:
- Registry supports predicates, operators, synthesis strategies, context rules, frame rules, UOL semantics (`registry\registry.py`).
- Frame engine exists (`kernel\frame_engine.py`).
- Basic router has no real frame engine.

Gaps:
- UOL semantic registry is not seeded enough in runtime.
- `FrameEngine.apply_frame_rules()` only appends model registry keys; it does not reject/rerank claims by temporal/frame containment before ranking.
- Frame rules are not clearly before permission/ranking in the basic runtime.

Fix:
- Seed UOL/frame models.
- Make retrieval return frame-valid and frame-rejected sets.
- Add tests where stale/out-of-frame claim is present but not ranked.

### Section 13 - UOL Semantic Layer (`architecture.md:1282`)

Requirement: UOL atoms are language-agnostic process/state/entity structures, not English grammar labels.

Current evidence:
- UOL dataclasses exist.
- `registry\uol_mapper.py` and `cemm_runtime_router.py:729-775` map from `text.lower()` with English keywords.

Gaps:
- UOL mapping is still surface-language heuristic.
- UOL process/state keys are not validated at runtime except via invariant guard if called.

Fix:
- Add model-backed `SemanticInterpreter` with deterministic UOL fallback.
- Reject unregistered process/state keys in runtime traces.

### Section 14 - Context Inference (`architecture.md:1350`)

Requirement: infer context without overriding explicit statements; temporary, decayed, evidence-bound.

Current evidence:
- Package context inference supports model-driven context rules then fallback (`kernel\context_inference.py`).
- Basic inference uses English keyword rules (`cemm_runtime_router.py:686-726`).

Gaps:
- Context inference runs before semantic graph interpretation.
- Basic inference not model-backed.
- Tests cover only "does not crash" for urgency (`tests\test_acceptance.py:226-242`).

Fix:
- Context inference should consume Signal + ContextKernel + SemanticEventGraph.
- Add tests for explicit statement override, decay, ambiguity, stale-world requirement.

### Section 15 - Pragmatic Repetition And Affect (`architecture.md:1419`)

Requirement: repeated negative evaluations become temporary pragmatic state, not facts.

Current evidence:
- Package pragmatic interpreter exists.
- Basic runtime detects semantic clusters via text pattern lists.
- Tests cover pragmatic repetition.

Gaps:
- Semantic clusters are still English pattern matched (`kernel\semantic_clusters.py`).
- Basic self/social affect persists counters in self_state, which can become identity-like if not bounded.

Fix:
- Move repetition into graph/process keys and session frame.
- Add retention/decay tests for affect fields.

### Section 16 - Causal World Model (`architecture.md:1522`)

Requirement: causal predictions are predictions, not observed facts; run causal inference only when goal requires it.

Current evidence:
- Package causal inference and simulation exist.
- Full package `process_input()` runs causal prediction and simulation on every turn and discards results (`__main__.py:209-213`).

Gaps:
- Causal work is eager, not goal-gated.
- Causal predictions are not represented in answer graph.

Fix:
- Gate causal stage by graph process/action intent.
- Put causal predictions into SemanticAnswerGraph with `confidence_type="predicted"`.

### Section 17 - Structural Learning (`architecture.md:1626`)

Requirement: repeated patterns create candidate models; promotion requires validation.

Current evidence:
- `learning\inductor.py` can propose predicate/causal/UOL/slot models.
- Training has `structural_induction` prompts.
- Promotion direct-activates models (`training\promoter.py:29-46`).

Gaps:
- No full promotion gate.
- Candidate evidence is not always tied to semantic graphs.

Fix:
- Add promotion gate with eval/risk/cost/permission checks.
- Require `semantic_event_graph_ids` or source trace ids for candidate promotion.

### Section 18 - Embodied And Experiential Grounding (`architecture.md:1728`)

Requirement: external/tool/sensor experience enters as signals with permissions and source trust.

Current evidence:
- Signal source types include tool/web/file/sensor/simulator.
- Runtime has external tools disabled in basic context.

Gaps:
- No ObservationPipeline for tools/web/files in current runtime.
- Fresh-world questions abstain correctly, but there is no tool-backed retrieval path.

Fix:
- Keep abstain for Phase 0.
- Later add external tool signals through Observe/Ground, never direct answer text.

### Section 19 - Retrieval And Representation (`architecture.md:1767`)

Requirement: structural retrieval first; optional dense expansion cannot bypass ranking/permission/frame.

Current evidence:
- `StructuralRetriever` exists and is used.
- Basic recall query goes direct predicate lookup (`cemm_runtime_router.py:813-851`).

Gaps:
- Retrieval query is not built from SemanticEventGraph.
- Frame and temporal containment are partial.
- Dense fallback controls are not tested.

Fix:
- Build `RetrievalQuery` from graph intents/entities/predicates/time/frame.
- Return ranked + rejected diagnostics.

### Section 20 - Ranking And Confidence (`architecture.md:1842`)

Requirement: scoring includes relevance, trust, confidence, salience, recency, frame validity, permission validity, risk/cost.

Current evidence:
- Scoring functions include permission multiplier (`confidence\scoring.py`).
- Ranker always passes `permission_valid=True` after prefilter (`retrieval\ranker.py:37-45`, `60-68`).
- Frame validity is not fed into score.

Gaps:
- Formula signature is compliant-ish, but runtime inputs are not.
- Permission invalidity disappears from diagnostics.
- Frame validity not integrated.

Fix:
- Add `ScoreContext` or diagnostics struct.
- Pass `permission_valid`, `frame_validity`, `temporal_overlap`.
- Add tests that fail if permission multiplier is skipped.

### Section 22 - Foundational Operators (`architecture.md:2084`)

Requirement: foundational operator metadata chooses resolver; no action executes unless Decide produced it.

Current evidence:
- `OperatorRegistry` maps `ActionKind` to action operator classes.
- `seed_registry()` registers action-like operators, not foundational operators (`__main__.py:43-83`).

Gaps:
- Foundational operators are missing as runtime components.
- Actions execute from hardcoded kind selection, not DecisionPacket.

Fix:
- Create operator specs for observe/contextualize/interpret/ground/retrieve/infer/decide/realize/update/learn.
- Route through resolver modules, not domain action handlers.

### Section 23 - Synthesis And Learning Runtime (`architecture.md:2162`)

Requirement: answer -> SemanticAnswerGraph -> Realize; cheapest strategy template -> extractive -> neural -> abstain; verification by strategy.

Current evidence:
- `SynthesisRouter.select_strategy()` orders template -> extractive -> neural -> abstain (`synthesis\router.py:47-56`).
- `route(strategy_name, ...)` renders exactly the supplied strategy and does not enforce cheapest-first when caller passes one (`synthesis\router.py:24-38`).
- `__main__.py:297-300` hardcodes template fallback.
- Basic `synthesize()` directly emits strings (`cemm_runtime_router.py:905-1132`).

Gaps:
- SynthesisRouter is not the realization gate for all answers.
- Strategy selection is optional and caller-controlled.
- No first-class hard/soft verifier pipeline over SemanticAnswerGraph.

Fix:
- Replace `route(strategy_name, ...)` calls with `realize(answer_graph, evidence, kernel)`.
- Make direct strategy execution private or test-only.
- Add verifier result onto answer graph.

### Section 24 - Storage (`architecture.md:2314`)

Requirement: storage supports primitives, frame/time indexes, graph packets, traces, training labels.

Current evidence:
- Package schema is broad and indexed.
- Basic router schema is simpler and separate.

Gaps:
- No semantic graph tables/columns in package schema.
- Basic schema and package schema diverge.
- Training schema in standalone `cemm_trainer.py` is separate from package `store\schema.py`.

Fix:
- Add semantic graph packet columns/tables.
- Decide whether `cemm_runtime_router.py` remains bootstrap-only or migrates to package stores.

### Section 25 - Bloat Control (`architecture.md:2367`)

Requirement: no unnecessary causal/neural/recursive work; no dense when structural enough.

Current evidence:
- Full package always runs causal inference and simulation before routing (`__main__.py:209-213`).
- Basic runtime only calls LLM if API key exists; but static fallback remains.

Gaps:
- Eager causal/simulation violates cost control.
- Tests do not assert no neural when template/extractive sufficient.

Fix:
- Gate causal/neural stages by DecisionPacket and graph requirements.
- Add counters/trace flags and no-unneeded-stage tests.

### Section 26 - Implementation Boundary (`architecture.md:2392`)

Requirement: day-one surface includes Signal, ContextKernel, UOL mapping, SemanticEventGraph packet, claim retrieval, SemanticAnswerGraph packet, template realization, trace, export, self update.

Current evidence:
- Current code has all except SemanticEventGraph and SemanticAnswerGraph.
- `docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py` adds lightweight graph packets, but with wrong answer ordering.

Gap:
- Current runtime is behind the Phase 0 boundary.

Fix:
- Use the archived snapshot's graph packet generation as a reference, but correct ordering before landing.

### Section 27 - Invariants (`architecture.md:2423`)

Requirement: tests fail on missing context, missing evidence, unselected claim use, text-only routing/training, graph bypass, stale world state, frame rules after ranking, budget refresh.

Current evidence:
- 221 tests pass.
- Some tests are smoke tests or weak invariants:
  - Direct `answer_text="Postgres"` is accepted without selected claim/answer graph (`tests\test_acceptance.py:47-55`).
  - Unselected evidence test allows success (`tests\invariants\test_gap_invariants.py:131-143`).
  - Recursive tests check depth guard, not child cost consumption (`tests\invariants\test_recursion.py:5-24`).

Gap:
- Tests do not enforce the new invariant contract.

Fix:
- Create contract tests for every invariant in `architecture.md:2423-2456`.

### Section 28 - Acceptance Test Boundary (`architecture.md:2464`) and `cemm_acceptance_tests.md`

Requirement: acceptance tests cover Phase 0 through efficiency.

Current evidence:
- Existing tests cover many primitives and old acceptance cases.
- New acceptance tests are only markdown, not executable.

Gap:
- `cemm_acceptance_tests.md` is not implemented as executable tests.

Fix:
- Translate it into `tests/test_slc_acceptance.py` and targeted invariant files.

### Section 29 - Final Shape (`architecture.md:2474`)

Requirement: CEMM is a semantic latent core with graph-backed memory, answer/action meaning before text, and traceable learning.

Current status:
- Current implementation is a useful bootstrap, not the final shape.
- The archived SLC snapshot implementation is a partial migration, not a final shape.

## Training Architecture Audit

### Training Sections 1-2 - Goal And Law (`cemm_training_architecture.md:6-72`)

Requirement: training target is graph -> typed latent -> answer/action -> optional text; invalid shortcuts include text->action and text->answer.

Current evidence:
- Current trainer has `operator_selection` outputting `action_kind` from payload (`cemm_trainer.py:206-217`).
- Current trainer has no semantic graph/answer/text-realizer task prompts.
- Current seed spec v1 lacks graph/latent global rules (`cemm_seed_spec.json:3-9`).

Gap:
- Current training can still train text-to-action and answer verification against final text.

Fix:
- Migrate to `docs\archive\new-slc-snapshot-2026-06-29\cemm_trainer.py` task set, but enforce payload validation so examples lacking graphs are rejected.

### Training Sections 3-5 - Inputs, Outputs, Task Types (`cemm_training_architecture.md:74-203`)

Requirement: inputs include traces, semantic graphs, answer graphs, selected memory, verifier outcomes; task types include semantic graph extraction, semantic answer composition, text realization, latent targets, memory ranking, causal effect prediction.

Current evidence:
- Current trainer prompts end at 17 task types, missing the graph/latent/answer tasks in new files (`cemm_seed_generator.py:45-62`).
- New seed generator has 26 task types including graph/latent/answer/text realization (`docs\archive\new-slc-snapshot-2026-06-29\cemm_seed_generator.py:42-68`).

Gap:
- Current trainer and seed spec are old generation.

Fix:
- Adopt new task names and add strict schema validators.
- Add ingest tests for new seed spec categories.

### Training Section 6 - Agent Roles (`cemm_training_architecture.md:205-230`)

Requirement: cheap parallel agents first; semantic_graph_builder, latent_teacher, semantic_answerer, text_realizer, memory_ranker, etc.

Current evidence:
- Current prompts have contextualist, uol_mapper, extractor, canonicalizer, critic, pragmaticist, causalist, temporalist, synthesis_judge, inductor, ranker_judge.
- Missing semantic_graph_builder, semantic_graph_denoiser, latent_teacher, semantic_answerer, text_realizer, event_predictor.

Fix:
- Merge new prompts and add arbiter comparisons for graph/answer outputs.

### Training Section 7 - Continuous Loop (`cemm_training_architecture.md:241-281`)

Requirement: runtime supports rules, model-backed graph parsing, typed latent loading, model-backed Decide, template/extractive realization, soft neural fallback, trace writing, feedback export.

Current evidence:
- Runtime export exists.
- Continuous queue only emits LLM fallback turns (`cemm_runtime_router.py:1332-1362`).
- Current export lacks graph tasks.

Gap:
- Runtime does not feed all semantic-core tasks.

Fix:
- Export graph/answer/text realization tasks for every turn.
- Use LLM fallback queue as one source, not the only continuous source.

### Training Sections 8-10 - Efficiency, Latents, Disagreement (`cemm_training_architecture.md:283-420`)

Requirement: structural-first, disagreement as signal, latent target supervision, verifier calibration.

Current evidence:
- Arbiter/evaluator exist but are minimal.
- No typed latent target persistence.
- Ranking judgement exists as task prompt, not runtime/eval integration.

Fix:
- Add training label schema fields for graph target, answer target, latent target, disagreement score, arbiter decision.

### Training Sections 11-13 - Online Updates, Structural Induction, Storage (`cemm_training_architecture.md:421-544`)

Requirement: online updates calibrate confidence; structural induction proposes candidates; storage ties labels, evals, promotion, privacy.

Current evidence:
- Online learner and inductor exist.
- Promoter is too permissive.
- Store schema includes training labels/eval/promotion, but standalone trainer uses separate schema.

Fix:
- Consolidate or bridge trainer DB and runtime store.
- Promotion candidates require eval results and permission checks.

### Training Sections 14-18 - API Policy, Day-One, Seed Generation, Metrics, Final Shape (`cemm_training_architecture.md:545-709`)

Requirement: env-only keys, day-one semantic graph/answer/text tasks, seed generation with graph targets, success metrics.

Current evidence:
- Env-only keys are respected.
- Current seed spec is v1; new seed spec is v2.
- No metrics dashboard or metric enforcement.

Fix:
- Replace current seed spec with v2.
- Add metrics collection tests for graph extraction accuracy, answer faithfulness, frame-rule stale prevention, low-confidence abstention, budget, and export completeness.

## Pipeline And Acceptance Audit

### `cemm_pipeline.md`

Important improvements:
- Target model shape requires graph before answer/text (`cemm_pipeline.md:26-34`).
- Router training target is `signal + ContextKernel + SemanticEventGraph + selected memory -> typed action or SemanticAnswerGraph` (`cemm_pipeline.md:152-156`).
- Bootstrap "what works now" expects graph trace objects and answer graph trace objects (`cemm_pipeline.md:195-208`).
- Regression gates fail if training lacks ContextKernel, trains text-only actions, bypasses SemanticAnswerGraph, uses unselected claims, overrides permission/frame, or promotes generated labels without eval (`cemm_pipeline.md:265-275`).

Current gaps:
- Current runtime export lacks graph tasks and graph fields.
- Existing tests do not fail on text-only action labels.

### `cemm_implementation_plan.md`

Important improvements:
- Phase 0 requires SemanticEventGraph packet and SemanticAnswerGraph packet (`cemm_implementation_plan.md:60-73`).
- Not Phase 0: vector search, custom embedding training, neural text generation, external tool execution (`cemm_implementation_plan.md:89-99`).
- Current known gaps in the new plan explicitly admit deterministic parsing/routing, metadata-only latents, LLM prompt labels, no artifact promotion registry, no evaluator/promotion gate (`cemm_implementation_plan.md:360-367`).

Current gaps:
- Current code is older than this plan: it lacks the Phase 0 graph packets now present in `docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py`.
- The proposed new code still violates answer-before-text ordering.

### `cemm_acceptance_tests.md`

Unimplemented executable tests:
- SemanticEventGraph for memory write.
- SemanticAnswerGraph before text realization.
- Runtime export emits ContextKernel + SemanticEventGraph + SemanticAnswerGraph + selected evidence + synthesis trace.
- Trainer rejects text-only operator labels.
- Trainer rejects direct text answer target when SemanticAnswerGraph is available.
- Memory ranker orders relevant claims.
- Verifier blocks unsupported additions.
- Recursive budget decrements child kernel.
- Promotion gate blocks candidates until validation/risk/cost/permission pass.
- No dense fallback when disabled.

## Additional Observed Runtime Weaknesses

1. `exit` is treated as an ordinary turn in basic chat and returns `I am here.` The chat loop does not intercept exit commands (`cemm_runtime_router.py:1445-1453`), and the fallback fires (`cemm_runtime_router.py:1132`).
2. Full package `process_input()` has an exit branch (`__main__.py:215-216`), so behavior differs across CLIs.
3. `call_llm()` in runtime is dead code (`cemm_runtime_router.py:1365` has no call sites); neural fallback uses direct `urllib` inside `synthesize()` (`cemm_runtime_router.py:1092-1129`).
4. `docs\archive\new-slc-snapshot-2026-06-29\cemm_runtime_router.py` also defines `call_llm()` but does not use it.
5. Basic runtime and package runtime have divergent schemas, permissions, kernels, and operator semantics.

## Gap Severity Ranking

Critical:
- No first-class SemanticEventGraph/SemanticAnswerGraph in current runtime.
- Answer text is produced before answer graph.
- Decide is text route, not graph + memory + kernel route.
- Current training target can still be text-only.

High:
- Core loop ordering mismatch.
- Permission multiplier bypassed in ranker inputs.
- Recursive budget under-accounted.
- Promotion gate missing.
- Tests do not enforce new invariants.

Medium:
- Runtime `call_llm()` dead.
- Causal inference runs eagerly in package entrypoint.
- Basic/package runtime divergence.
- UOL registry validation not enforced at runtime.
- Static fallback leaks into chat.

Lower but important:
- Metrics and dashboards absent.
- No typed latent persistence.
- No graph memory views.
- No executable version of new acceptance tests.

## 2026-07-01 Remediation Pass

Closed in this pass:
- Trainer prompt rendering no longer crashes on graph-first tasks; all prompts render with a safe context.
- Ask, remember, and retrieve user-facing outputs now realize through `SemanticAnswerGraph` and carry verification metadata.
- Runtime export includes accurate `realization_metadata` and `verification_metadata` with detailed trace dictionaries.
- Raw-preserving noisy text normalization emits a `NormalizedSignal` packet before interpretation without mutating `Signal.content`.
- Casual pragmatic acts (`playful_acknowledgment`, `confusion`, `self_correction`, `simplification_request`, `reassurance`) are represented as semantic clusters and UOL frame keys.
- Self and capability answers route through selected self evidence (`self_identity_query`, `self_capability_query`, `self_knowledge_query`).
- NER training accepts mixed label sets, normalizes noisy tags, and reports per-entity confidence.
- Graph-referenced claims receive an entity-overlap relevance boost and grounded location roles are captured in `GroundedGraph`.
- Full test suite now passes (271 passed, 6.58s).

Remaining / Phase 1+:
- Learned multilingual semantic parsing remains a training target.
- Frame-specific risk/cost scoring remains limited until more validated models exist.
- Typed latent persistence and graph memory views are not yet implemented.
- Promotion gate and evaluator integration remain open.
- No executable version of the full `cemm_acceptance_tests.md` checklist yet.

## Fix Strategy

Do not attempt to "make current deterministic code smarter" first. The right sequence is:

1. Add executable contract tests from `cemm_acceptance_tests.md`.
2. Add first-class graph packet types and schema support.
3. Correct runtime order so graphs precede retrieval/decision/realization.
4. Move text output behind RealizationPipeline.
5. Update training to graph/answer/text-realization tasks.
6. Add ranker/frame/permission/budget/promotion invariants.
7. Only then add learned components and neural fallback.

The detailed implementation plan is in `docs\superpowers\plans\2026-06-29-cemm-slc-architecture-alignment.md`.
