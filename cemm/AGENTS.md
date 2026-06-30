# CEMM SLC Architecture - Governing Instructions

This file is the highest-priority local implementation guide for CEMM work. If any older plan, archived document, generated artifact, or bootstrap script conflicts with this file, follow this file and the canonical root architecture documents.

## Canonical Documents

Use these root files as the active contract:

- `architecture.md` - stable CEMM-SLC architecture.
- `cemm_training_architecture.md` - continuous training architecture.
- `cemm_pipeline.md` - active end-to-end pipeline.
- `cemm_acceptance_tests.md` - acceptance contract to convert into executable tests.
- `cemm_implementation_plan.md` - proposed implementation phases.
- `cemm_architecture_gap_trace.md` - current gap analysis.
- `docs/superpowers/plans/2026-06-29-cemm-slc-architecture-alignment.md` - active implementation plan.

Historical or deprecated material under `docs/archive/` is not implementation guidance. Do not follow old plans that describe CEMM as a basic deterministic conversational MVP, or plans that say to copy files from `new/` directly into root.

## Core Identity

- CEMM itself is a language model, not a wrapper around prompts.
- CEMM is a MOE/SLM: it routes semantic packets through expert modules and learned components.
- UOL and graph packets are the semantic representation; English text is only one input/output surface.
- The knowledge compression pipeline is runtime -> trace -> extract -> train -> compress -> deploy.
- The training pipeline feeds the runtime. Deterministic code is a temporary cheapest-first fallback, not the architecture.

## Non-Negotiable Runtime Shape

The active target is:

```text
Signal + ContextKernel + Memory
-> SemanticEventGraph
-> typed latent / Decide
-> SemanticAnswerGraph or ActionPlan
-> Realize
-> Verify
-> Trace
-> Export
```

Final user-facing answer text must not be produced before a `SemanticAnswerGraph` or valid `ActionPlan` exists.

## Core Loop Ordering

Every runtime change must preserve the SLC loop:

```text
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
-> maybe_recurse_from_internal_signals
```

Implementation names may differ, but the data dependency must not. In particular:

- Build the ContextKernel before interpretation.
- Interpret into `SemanticEventGraph` before retrieval, ranking, or decision.
- Ground entities, time, location, frame, and permission before ranking.
- Retrieve structurally before any dense or neural path.
- Decide over ContextKernel + SemanticEventGraph + selected memory, not raw text.
- Realize from SemanticAnswerGraph or ActionPlan only.
- Export traces with ContextKernel, SemanticEventGraph, SemanticAnswerGraph or ActionPlan, selected evidence, realization metadata, and verification metadata.

## Inference Cascade

Use cheapest valid computation first:

```text
deterministic structural rules
-> small model / SLC component
-> parallel small agents
-> stronger arbiter
-> background induction
```

No layer may be a dead end. Low confidence, insufficient evidence, missing slots, stale world state, or permission failure must route to ask/abstain/escalate according to budget and permission.

## Synthesis And Realization

Answer actions do not directly generate final text.

Required flow:

```text
answer decision
-> SemanticAnswerGraph
-> RealizationPipeline
-> template | extractive | neural | abstain
-> verification
-> final output or abstain
```

Strategy selection must be cheapest-first:

```text
template -> extractive -> neural -> abstain
```

Rules:

- Do not run neural synthesis when template or extractive realization is sufficient.
- Neural realization must use soft verification and bounded selected evidence.
- Template/extractive realization must use hard verification where possible.
- Text is invalid if it cannot be mapped back to the SemanticAnswerGraph and selected evidence.

## Training Law

Training must improve semantic computation, not text-only behavior.

Valid training target:

```text
text/context/memory
-> SemanticEventGraph
-> semantic answer/action
-> realized text
```

Invalid shortcuts:

- text -> action
- text -> answer
- embedding -> text answer without SemanticAnswerGraph
- generated label -> active truth
- private trace -> public training example

Runtime export and trainer ingest must preserve permission scope, source ids, confidence, time, selected evidence, SemanticEventGraph, SemanticAnswerGraph or ActionPlan, realization, and verification metadata.

## Required Graph Packets

Phase 0 runtime and traces must include:

- `Signal`
- `ContextKernel`
- UOL atoms
- `SemanticEventGraph`
- selected claims/models
- `SemanticAnswerGraph` or `ActionPlan`
- realization metadata
- verification metadata
- action trace
- runtime training export

Do not close implementation work that touches answer, routing, training, retrieval, synthesis, or traces until affected graph-packet invariants are executable tests.

## No Rules

- No English-specific string matching as the primary routing mechanism.
- No hardcoded response strings for open-domain inputs.
- No static fallback such as `I am here.`
- No dead `call_llm`; model-call abstractions must be wired or removed.
- No answer text before SemanticAnswerGraph.
- No text-only operator-selection training when graph data is available.
- No text-only answer training when SemanticAnswerGraph is available.
- No neural/dense output bypassing permission, frame validity, ranking, selected evidence, or verification.
- No promoting generated labels or candidate models without validation, risk, cost, and permission gates.
- No running causal inference unless the goal or graph requires prediction, planning, or consequence reasoning.
- No refreshing recursive budget in child loops; child budget equals parent remaining budget minus actual cost.
- **No hiding limitations to make a demo look good.** Run honest evaluations. Let failures and gaps guide the next training pathway, not ad-hoc patches to the legacy router.

## Scoring And Ranking

Scoring formulas must include actual permission validity, not a hardcoded `True`.

Ranking must consider:

- relevance
- trust
- confidence
- salience
- recency
- frame validity
- temporal containment
- permission validity
- risk and cost where applicable

Frame rules and permission gates must run before ranking. Rejected candidates should be observable in diagnostics or tests where practical.

## Storage And Source Of Truth

The root docs are current. The `new/` directory must not be used as a second active source of truth. If a snapshot of old or proposed files is needed, archive it under `docs/archive/`.

Generated runtime artifacts such as `.sqlite3`, `output.log`, generated JSONL, and `__pycache__` files are not architecture guidance.

## Code Review Checklist

Before closing a PR or task, verify:

- [ ] Runtime ordering follows Observe -> Contextualize -> Interpret -> Ground -> Retrieve -> Infer -> Decide -> Realize -> Update -> Learn.
- [ ] ContextKernel exists before interpretation.
- [ ] SemanticEventGraph exists before retrieval/ranking/decision.
- [ ] Answer decisions produce SemanticAnswerGraph before text.
- [ ] Realization uses cheapest-first template -> extractive -> neural -> abstain.
- [ ] Output verification is recorded and appropriate to strategy.
- [ ] Ranking uses real permission validity and frame validity.
- [ ] Recursive child budget is consumed by actual child cost.
- [ ] Causal inference is goal/graph-gated.
- [ ] Runtime export includes ContextKernel, SemanticEventGraph, SemanticAnswerGraph or ActionPlan, selected evidence, realization, and verification.
- [ ] Training examples reject text-only action/answer targets when graph packets are available.
- [ ] Promotion requires validation, risk, cost, and permission gates.
- [ ] All affected invariants from `architecture.md` section 27 and `cemm_acceptance_tests.md` are covered by executable tests.
