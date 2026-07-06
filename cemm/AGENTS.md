# CEMM Agent Instructions

Status: governing implementation guide  
Audience: AI coding agents, reviewers, and maintainers working on CEMM  
Supersedes: older v3.0/SLC-only local plans when they conflict with the current architecture

## 0. CRITICAL — Causal-Runtime Wiring Gap (Blocker #1)

**Priority: BLOCKER. All other work is secondary until this is fixed.**

The causal and recursive foundational architecture was designed to handle
cross-turn semantic understanding, emotional context persistence, and
entity salience tracking. The modules exist but are **island components** —
built but never wired into the runtime pipeline.

### The Broken Chain

```
Architecture intended:
  Construction → evaluates edge → affordance prediction (evaluation_shift)
  → planner (empathetic response + patch) → durable store → cross-turn retrieval

What's implemented:
  Construction → intent label only (no relation patch)
  ✗ no evaluates edge for emotional predicates
  ✗ no evaluation_shift affordance rule
  ✗ affordance predictions never consumed by scheduler/realizer
  ✗ patch extractor filters out likes/evaluates
  ✗ causal inference engine disconnected from semantic runtime
  ✗ update_user_affect never called — affect state never updated during turns
  ✗ anaphora resolver doesn't resolve third-person pronouns cross-turn
  ✓ durable store can store/retrieve (but nothing to store)
```

### 12 Specific Culprits

1. **ConstructionMatcher** — No emotional predicate constructions. `graph_patch_templates` only emits metadata.
2. **MeaningGraphBuilder** — `_parse_surface_relation` only handles definitional cues. No `evaluates` edge for emotional predicates.
3. **AffordancePredictor** — Only 3 seed rules. No `evaluation_shift` rule.
4. **SemanticKernelRuntime.run_turn()** — Computes affordance predictions but never passes them to obligation scheduler, query engine, or realizer.
5. **CausalInference** — Operates on old Store/Claim/Model system. Never called from runtime.
6. **PragmaticInterpreter.update_user_affect** — Function exists but never called.
7. **Patch extraction filter** — Excludes `likes`, `dislikes`, `evaluates` from durable patches.
8. **RelationFrameCompiler** — `evaluates` has `projection_policy: "none"`.
9. **SemanticObligationScheduler** — No obligation kind for emotional context or affect follow-up.
10. **SemanticRealizer** — No templates for proactive emotional follow-up.
11. **AnaphoraResolver** — Third-person pronouns record candidates but don't assign entity_id.
12. **SemanticAttentionController** — Doesn't process `AffordancePrediction` objects from the graph.

### Master Fix Plan

See: `newarch/causal-runtime-wiring-fix.md` — the single authoritative fix plan.

All other implementation plans are superseded. Do not follow them.

## 1. Canonical Source Of Truth

Use these files as the active implementation contract, in this order:

1. `AGENTS.md` (this file)
2. `newarch/causal-runtime-wiring-fix.md` (master fix plan — BLOCKER #1)
3. `newarch/consolidated_architecture.md`
4. `newarch/3.3-uol-graph-architecture.md`
5. `newarch/core_loop_runtime.md`

Superseded design docs and plans are archived at `docs/archive/newarch_superseded/`.
Use them as background reference only — they are not active architecture contracts.

The following newarch docs are **deprecated** and have been moved to archive:
- `semantic-graph-brain-gap-fix-implementation-plan.md`
- `semantic-graph-brain-implementation.md`
- `semantic-graph-brain.design.md`
- `runtime-single-authority-takeover-design.md`
- `cemm-v4.2-exact-root-cause-gap-fix-proposal.md`
- `missing_runtime_implementation_plan.md`
- `full_cemm_learning_brain_missing_pieces.md`
- `construction-matcher-refactor-plan.md`

Do not follow any superseded plan. Follow `causal-runtime-wiring-fix.md` instead.

Older generated artifacts, patch files, archived docs, bootstrap scripts,
runtime databases, logs, `__pycache__`, JSONL exports, and files under old
proposal/archive directories are not active architecture guidance.

If any document says CEMM is only a deterministic conversational MVP, an
English-first router, or a text-answer generator, ignore that instruction.

Also ensure that old tests don't derail new implementation or cause drift. Delete and create new ones instead if necessary.

## 2. Core Identity

CEMM is a meaning-first language architecture.

It is not:

```text
a prompt wrapper
a plain intent classifier
a text-only chatbot
a giant sentence database
```

It is:

```text
a semantic runtime
a UOL working-graph system
a graph-patch learning system
a compression-oriented concept/construction/predicate/affordance learner
```

English text is one input/output surface. UOL graph structure is the internal
semantic workbench.

## 3. Current Runtime Contract

The active seed runtime loop is:

```text
Signal
-> MeaningPerceptor
-> MeaningPerceptPacket
-> MeaningGraphBuilder
-> UOLGraph
-> runtime resolution (concept/port/affordance)
-> ActResolutionPlanner
-> GraphPatchExtractor
-> ConceptConsolidator
-> durable semantic structures
```

Status: **pipeline unified but causal-runtime wiring is broken (BLOCKER #1)**
- `Pipeline.run()` delegates to `SemanticKernelRuntime.run_turn()` — single authority achieved
- `UOLGraph` is the sole working graph
- `SemanticKernelRuntime.run_turn()` has 11 steps: perceive, build, attend, compile, schedule, teach, compile relations, query, realize, plan, extract/validate/commit patches
- `PatchValidator` and `PatchCommitter` enforce graph-patch-only durable writes
- `SessionStore` restores/persists conversation, user affect, topic, discourse state across turns
- `EntitySalienceTracker` tracks entity salience across turns
- `DurableSemanticStore` stores and retrieves relation frames

**CRITICAL GAP — Causal-Runtime Wiring (see Section 0 and `causal-runtime-wiring-fix.md`):**
- Affordance predictions computed but never consumed by scheduler/realizer
- `CausalInference` engine completely disconnected from runtime
- `update_user_affect` never called — affect state never updated during turns
- No `evaluates` edge creation for emotional predicates
- No `evaluation_shift` affordance rules
- Patch extractor filters out `likes`/`dislikes`/`evaluates`
- AnaphoraResolver doesn't resolve third-person pronouns cross-turn
- No obligation kind for emotional context or affect follow-up
- No realization templates for proactive emotional follow-up

**Other remaining gaps:**
- 5 durable architecture types replaced by simpler records (acceptable for now)
- Remaining 10 Phase 0 hot-path modules still embedded in `MeaningPerceptor`
- Dynamic self-knowledge (still static `self_knowledge.json`)
- Knowledge ingestion, training infrastructure, adapters, synthesis modules

Do not overclaim that the full learning brain is done. The causal-runtime wiring is the #1 blocker.

## 4. Compatibility Names

Some older docs use SLC names. Use this mapping:

| Older Term | Current Active Equivalent |
|---|---|
| `SemanticEventGraph` | `UOLGraph` plus meaning groups, predicates, candidate sets, concept resolutions, port bindings, affordances, and patch candidates |
| graph packet | `MeaningPerceptPacket` and/or `UOLGraph` depending on stage |
| semantic packet | `MeaningPerceptPacket` |
| typed latent / Decide | runtime resolution plus `ActResolutionPlanner` |
| `SemanticAnswerGraph` | not yet implemented as a first-class type; use `ActResolutionPlan` and future answer-graph type only when added |
| training export | `UOLGraph.to_training_example()` plus graph patch and realization metadata |

Do not invent a fake `SemanticAnswerGraph` just to satisfy old wording.

If answer-graph work is needed, add an explicit type behind the current
planner/realizer seam.

## 5. Non-Negotiable Ordering

Runtime changes must preserve this dependency order:

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
```

Current implementation mapping:

| Stage | Current Implementation |
|---|---|
| Observe | `Signal`, source metadata, raw text |
| Contextualize | context/kernel objects, source, permission, self/user atoms |
| Interpret | `MeaningPerceptor`, meaning groups, predicates, hypotheses |
| Ground | `MeaningGraphBuilder`, `UOLGraph`, concept/port/source/time/place grounding |
| Retrieve | retrieval plan and selected evidence, when available |
| Infer | concept resolution, construction matches, port bindings, affordance predictions, candidate paths |
| Decide | `ActResolutionPlanner` |
| Realize | response realization layer, currently outside the core seed modules |
| Update | graph patch extraction |
| Learn | consolidation into durable semantic structures |

## 6. Phase 0 Hot-Path Rule

Before building heavy durable learning, fix the semantic hot path.

Do not feed weak traces into the learning brain.

Phase 0 completion status (4 of 14 extracted from MeaningPerceptor):

| File | Status |
|---|---|
| `predicate_phrase_extractor.py` | ✓ Extracted (`cemm/kernel/predicate_phrase_extractor.py`) |
| `predicate_argument_aligner.py` | ❌ Still embedded in MeaningPerceptor |
| `implicit_predicate_detector.py` | ✓ Extracted (`cemm/kernel/implicit_predicate_detector.py`) |
| `interpretation_path.py` | ❌ Not yet created |
| `alternative_graph_branch.py` | ❌ Not yet created |
| `branching_graph_builder.py` | ❌ Not yet created |
| `discourse_relation_resolver.py` | ❌ Not yet created |
| `group_predicate_index.py` | ❌ Not yet created |
| `candidate_set_resolver.py` | ❌ Not yet created |
| `interpretation_path_selector.py` | ❌ Not yet created |
| `planner_branch_adapter.py` | ❌ Not yet created |
| `anaphora_resolver.py` | ✓ Extracted (`cemm/kernel/anaphora_resolver.py`) |
| `entity_salience_tracker.py` | ✓ Extracted (`cemm/kernel/entity_salience_tracker.py`) |
| `deictic_resolver.py` | ❌ Not yet created |

These must improve:

```text
predicate extraction
implicit predicates
candidate graph branching
discourse relation edges
candidate selection/rejection
cross-group anaphora and deixis
```

## 7. Foundational Primitive Rule

The UOL graph has exactly 16 canonical atom kinds:

```text
entity
process
state
relation
quality
quantity
time
place
intent
need
modality
evidence
source
permission
action
self
```

The UOL graph has exactly 16 canonical edge types:

```text
has_role
modifies
refers_to
asks_about
teaches
evaluates
causes
enables
prevents
before
after
same_as
is_a
part_of
used_for
has_property
```

Do not create domain primitives such as:

```text
PresidentAtom
WeatherAtom
LeaderAtom
CountryAtom
PersonAtom
```

Represent those as dynamic concept atoms or concept records.

## 8. Learning Law

CEMM learns by semantic compression.

Correct:

```text
working UOL graph
-> graph patch candidates
-> validation/scoring
-> consolidation
-> concept/construction/predicate/affordance/source-policy updates
```

Incorrect:

```text
raw text -> answer
raw text -> durable fact
embedding -> final answer
generated label -> active truth
external lookup -> direct memory write
```

All durable learning must pass through graph patches.

## 9. External Knowledge Rule

Dictionaries, Wikipedia, tools, and LLM teacher outputs are sources, not
truth-oracles.

They must enter as:

```text
source atoms
evidence atoms
working graph structure
graph patch candidates
validation
consolidation
```

Never bypass source, permission, freshness, contradiction, or trust policy.

## 10. Inference Cascade

Use the cheapest valid computation first:

```text
deterministic structural operator
-> small learned component
-> parallel small agents
-> stronger arbiter
-> background induction
```

No layer may be a dead end.

Low confidence, insufficient evidence, missing required ports, stale world
state, contradiction, or permission failure must route to:

```text
ask
abstain
retrieve
escalate
quarantine
```

according to budget, risk, and permission.

## 11. Realization Rule

Final text should be realized from a response/action plan and selected evidence,
not directly from raw input text.

Current seed implementation has `ActResolutionPlan`.

Future implementation should add a first-class answer graph or realization
contract.

Realization strategy should be cheapest-first:

```text
template
-> extractive
-> neural
-> abstain
```

Text is invalid if it cannot be traced back to the working graph, selected
evidence, and response/action plan.

## 12. No Rules

Do not:

```text
use English-specific string matching as the primary architecture
hardcode open-domain fallback strings to hide model failure
produce final answer text before interpretation and planning
write durable memory directly from perception or retrieval
promote generated labels without validation
let dense/neural output bypass permission and evidence
store every working graph forever as primary memory
add new primitive atom kinds for ordinary domain concepts
bury learned knowledge inside meaning_perceptor.py
collapse candidate meanings too early
ignore candidate sets, graph branches, anaphora, or discourse edges
hide limitations to make a demo look good
```

Seed heuristics are allowed only as explicit fallback scaffolding.

## 13. Scoring And Ranking

Ranking must consider:

```text
relevance
trust
confidence
salience
recency
frame validity
temporal containment
permission validity
risk
cost
contradiction
freshness requirements
```

Permission validity must be real, not hardcoded `True`.

Rejected candidates should remain observable in diagnostics, candidate sets,
branch metadata, or tests where practical.

## 14. Storage And Source Of Truth

Working graphs are temporary.

Durable memory should store:

```text
compressed semantic records
concept atoms
operational ports
predicate schemas
construction operators
causal affordances
source policies
patch journal entries
sparse high-value exemplars
```

Do not use runtime artifacts as architecture guidance:

```text
*.sqlite3
*.log
__pycache__/
generated JSONL
old patch files
```

## 15. Code Review Checklist

Before closing a task, verify:

- [ ] The change follows the current v4.2 architecture, not older v3-only instructions.
- [ ] `MeaningPerceptPacket` exists before graph construction.
- [ ] `UOLGraph` exists before runtime resolution, planning, patch extraction, or learning.
- [ ] Candidate meanings are preserved instead of collapsed prematurely.
- [ ] Predicate extraction is not limited to action/state surface matches when the task touches interpretation.
- [ ] Discourse relations create graph structure when the task touches group relations.
- [ ] Anaphora/deixis are handled or explicitly marked unresolved when the task touches cross-group reference.
- [ ] Durable learning happens only through `GraphPatch`.
- [ ] Concept, construction, port, and affordance behavior lives behind the proper lattice/resolver/predictor seams.
- [ ] Domain concepts are not added as new primitive atom kinds.
- [ ] External knowledge enters through source/evidence/graph-patch flow.
- [ ] Planning uses graph structure, candidate sets, and evidence policy, not raw text alone.
- [ ] Realization is traceable to a plan, selected evidence, and graph state.
- [ ] Tests cover affected graph-packet invariants.
- [ ] Known limitations are documented honestly instead of hidden behind fallback strings.

