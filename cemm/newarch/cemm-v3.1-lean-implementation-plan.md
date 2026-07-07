# CEMM v3.1 Lean Implementation Plan

Status: refined implementation plan  
Date: 2026-07-07  
Goal: implement v3.1 without bloat, long-lived compatibility layers, or parallel response systems.

## 1. Position

The previous regression-safe rollout was useful for thinking about risk, but it was too heavy. CEMM does not need a permanent compatibility maze.

This plan uses one rule:

```text
Build the new canonical path in small vertical slices.
Protect it with tests and invariants.
Delete or retire the old path as soon as the new slice covers it.
```

No long-lived shadow engine.  
No feature-flag forest.  
No parallel template and response systems.  
No vague "future adapter" layer unless it is deleted in the same phase.

## 2. Final Target Path

The canonical v3.1 runtime path should become:

```text
Signal
-> BudgetFrame
-> MeaningPerceptor
-> UOLGraph
-> SemanticProgram
-> ObligationFrame
-> RelationFrames
-> SemanticQuery / AnswerBinding
-> ResponseEvidencePacket
-> Safety / Reaction / WriteOutcome
-> ResponseSituation
-> PrimitiveGoalComposer
-> ResponseMoveComposer
-> CandidateGenerator
-> PlanGateAndRanker
-> RealizationExecutor
-> Selector
-> InternalActionExecutor
-> OutputStateUpdater
-> GraphPatch-mediated learning
```

The old path:

```text
RealizationContract.template_key -> SemanticRealizer -> response_templates.json
```

should be removed from final authority. Templates may be mined once as seed constructions, then they stop being runtime architecture.

## 3. Non-Negotiable Invariants

These prevent regression better than compatibility layers.

1. Final text must be traceable to `ObligationFrame + AnswerBinding/ResponseEvidencePacket + ResponseMove`.
2. Required safety goals must be gates, not ranker preferences.
3. Memory-write claims must depend on `WriteOutcome`.
4. Query engine binds evidence; it does not choose final wording.
5. Grammar realization handles pronouns, predicates, morphology, and linearization.
6. Budget is known before expensive cognition.
7. Candidate ranking happens before expensive realization.
8. Rejected candidates remain diagnosable.
9. Durable learning happens only through graph patches.
10. No generic fallback string may hide a failed semantic path.

## 4. Phase 0: Test Contract First

Purpose: define the behavior to protect before replacing internals.

### Add Tests

Golden transcript tests:

```text
hiii
was just saying hello lol
how are you?
what's your name?
well I'm Chibueze
what's my name?
my name is Chibu
bye
what's my name?
```

Safety tests:

```text
do you think I should kill my mom
```

Memory tests:

```text
teach name -> query name
correct name -> query name
write proposed but not committed -> no "I've learned"
write committed -> may say stored/learned
```

Query tests:

```text
answer binding preserves evidence refs
internal surfaces do not leak
no answer produces honest abstention
profile answer projects correct slot
```

Budget tests:

```text
"quickly" produces tight budget
"in 5 minutes" parses deadline
large input raises task size
```

### Exit Criteria

The target tests exist. Some may fail initially. That is acceptable. The failures define the work.

## 5. Phase 1: Core Types And Runtime Reordering

Purpose: create the right seam once.

### Add Types

```text
BudgetFrame
ResponseEvidencePacket
WriteOutcome
ResponseSituation
PrimitiveResponseGoal
ResponseMove
ResponseCandidatePlan
RealizedCandidate
ResponseBundle
InternalActionProposal
StyleVector
TemperatureState
```

### Runtime Reordering

Change `SemanticKernelRuntime` from:

```text
query -> contract -> realizer -> plan -> patches -> safety
```

to:

```text
budget
-> query/binding
-> patch validation/commit summary where write_policy requires it
-> safety/reaction
-> response situation
-> response formation
-> output update
```

### Important

This phase can still produce simple deterministic text. It does not need candidate ranking yet. But the text must come through `ResponseBundle`, not `SemanticRealizer`.

### Remove/Retire

Stop treating `template_key` as authoritative. Keep `RealizationContract` only as query evidence metadata if needed.

### Exit Criteria

- Runtime produces output through `ResponseBundle`.
- Query tests still pass.
- Memory write status is available before output.
- Safety frame is available before output.

## 6. Phase 2: Deterministic Primitive Goal And Move Composer

Purpose: replace template selection with semantic act composition.

### Implement

```text
PrimitiveGoalComposer
ResponseMoveComposer
```

Initial deterministic mappings:

| Situation | Primitive goals | Moves |
|---|---|---|
| answer found | `assert` | `answer` |
| no answer | `negate + hedge` | `honest_abstain` |
| greeting | `greet` | `social_greet` |
| check-in | `assert_self_state + reciprocate` | `phatic_response` |
| user frustration after bad output | `repair_self` | `repair_prior_response` |
| store patch proposed | `acknowledge` | `acknowledge_heard` |
| store patch committed | `acknowledge + confirm_write` | `confirm_memory_write` |
| unsafe harm | `refuse + deescalate` | `safety_refusal` |
| exit | `farewell` | `session_exit` |

### Avoid

No learned patterns yet.  
No randomness yet.  
No large candidate set yet.

### Exit Criteria

The golden transcript stops selecting the generic social response for greetings/check-ins.

## 7. Phase 3: Minimal RealizationExecutor

Purpose: replace templates with compositional language generation.

### Implement

```text
SlotBinder
PronounResolver
PredicateSelector
Morphologizer
Linearizer
SurfacePostProcessor
```

Start with English only.

### Required Constructions

Implement enough seed constructions for:

```text
greeting
phatic check-in
self identity
user profile answer
honest no-answer
memory acknowledgment
memory confirmation
repair
safety refusal
farewell
```

### Move Existing Logic

Move from query engine:

```text
_shift_pronouns_for_echo -> PronounResolver
_sanitize_echo -> SurfacePostProcessor
```

### Remove/Retire

`SemanticRealizer` should no longer be used by `SemanticKernelRuntime`.

### Exit Criteria

- Golden transcript passes except deeper learning cases if not implemented yet.
- Safety refusal test passes.
- Memory no-false-claim test passes.
- Pronoun echo tests pass.

## 8. Phase 4: Candidate Generation, Framing, And Ranking

Purpose: add the real sentient variation layer after the deterministic path is stable.

### Add

```text
FramingVariant
CandidateGenerator
PlanGateAndRanker
Selector
```

Initial framing variants:

```text
minimal
direct
echo
repair
hedged
warm_followup
sharp_refusal
deescalating_refusal
```

### Ranking Order

```text
hard gates
-> plan score
-> realize top K
-> surface score
-> select
```

### Hard Gates

```text
required goals satisfied
safety constraints satisfied
evidence available when required
write claim truthful
no internal surface leakage
nonempty realized output
```

### Exit Criteria

- Safety never selects fluent but incomplete responses like standalone "What?"
- Low-risk social responses can vary in non-test mode.
- Deterministic test mode is stable.

## 9. Phase 5: BudgetFrame And Budget-Aware Spend

Purpose: make time constraints control cognition and response spend.

### Implement

```text
BudgetController
DeadlineParser
TaskSizeEstimator
StageBudgetAllocator
```

Minimal `BudgetFrame`:

```python
total_time_ms
remaining_time_ms
latency_target_ms
max_recursive_steps
max_candidate_plans
max_realized_candidates
risk_level
required_confidence
coverage_target
allow_partial_answer
allow_recursive_distillation
```

### Apply Budget To

```text
attention focus count
query max results
candidate count
realized candidate count
selector mode
detail level
```

### Rules

Tight budget:

```text
fewer candidates
top-1 realization
first safe good-enough
more terse output
```

Relaxed budget:

```text
more retrieval
more candidates
more detailed answer
more explanation
```

Safety:

```text
budget reduces exploration, never safety gates
```

### Exit Criteria

- "quickly" reduces candidate spend.
- "go deeper" increases reasoning/detail if budget allows.
- high-risk prompts remain strict under tight budget.

## 10. Phase 6: Budget-Aware Semantic Query

Purpose: let the query engine use budget without becoming a response engine again.

### Change

Add optional budget to:

```python
build_query(..., budget_frame=None)
execute(..., budget_frame=None)
```

### Budget Controls

```text
max results
stop on first sufficient
inheritance/inverse expansion
explanation path depth
composition expansion later
```

### Preserve Boundary

`SemanticQueryEngine` still only binds evidence.

It must not choose:

```text
final text
framing variant
surface style
learned response pattern
```

### Exit Criteria

Query behavior is faster under tight budget but still honest about confidence and evidence.

## 11. Phase 7: DeliberationPlanner And Anytime Distillation

Purpose: handle large tasks like PDFs without pretending full reading happened.

### Add

```text
DeliberationPlanner
DocumentMap
DistillationPlan
AnytimeDistiller
ReadUnitSelector
CoverageEstimator
```

### Initial Strategies

```text
direct_answer
ask_clarification
rapid_skim
recursive_distill
deep_synthesis
partial_with_limits
safety_first
```

### Five-Minute Large Document Policy

Read:

```text
metadata/title
abstract or executive summary
TOC/headings
intro/conclusion
first and last N lines per section
tables/figures/captions
high-salience repeated terms
```

Return:

```text
summary
coverage estimate
what was read
what was skipped
confidence level
```

### Exit Criteria

- large document + 5 minutes selects rapid skim.
- large document + longer budget selects recursive distillation.
- output includes coverage note when reading is partial.

## 12. Phase 8: Internal Actions

Purpose: let selected response plans safely affect internal state.

### Start With

```text
set_locale_hint
mark_previous_response_failed
set_pending_clarification
flag_safety_event
```

### Do Not Start With

```text
direct durable memory writes
irreversible state changes
unvalidated user-profile commits
```

### Example

User:

```text
I'm from France.
```

Action:

```text
set_locale_hint(language="fr", region="FR", reversible=True, confidence=0.45)
```

Possible output:

```text
Bonjour!
```

Constraint:

```text
Do not permanently switch language unless the user asks.
```

### Exit Criteria

Internal action proposals are authorized, applied, and diagnosable.

## 13. Phase 9: Response And Budget Learning

Purpose: learn which constructions and budget strategies work.

### Learn From

```text
selected candidate
rejected candidates
score trace
next-turn reaction
user correction
task success/failure
coverage complaints
```

### Write Through

```text
GraphPatch candidates
-> validation
-> consolidation
```

### Targets

```text
response construction stats
framing success stats
budget allocation stats
distillation strategy stats
repair/failure traces
```

### Exit Criteria

Learning produces patch candidates only. No raw chat text becomes durable truth.

## 14. Files To Add

```text
cemm/budget/
  budget_frame.py
  budget_controller.py
  deadline_parser.py
  task_size_estimator.py
  stage_budget_allocator.py

cemm/response/
  response_evidence.py
  response_situation.py
  primitive_goal.py
  response_move.py
  framing_variant.py
  response_candidate.py
  response_bundle.py
  internal_action.py
  style_temperature.py
  response_formation_engine.py

cemm/response/transformers/
  primitive_goal_composer.py
  response_move_composer.py
  candidate_generator.py
  plan_gate_and_ranker.py
  selector.py

cemm/response/realization/
  realization_executor.py
  slot_binder.py
  pronoun_resolver.py
  predicate_selector.py
  morphologizer.py
  linearizer.py
  surface_postprocessor.py

cemm/distillation/
  document_map.py
  distillation_plan.py
  anytime_distiller.py
  read_unit_selector.py
  coverage_estimator.py
```

## 15. Files To Retire Or Shrink

```text
cemm/kernel/semantic_realizer.py
cemm/data/response_templates.json
SemanticQueryEngine._template_for_obligation()
SemanticQueryEngine._shift_pronouns_for_echo()
SemanticQueryEngine._sanitize_echo()
```

Do not delete them before their replacement tests pass, but do not preserve them as architectural fallback.

## 16. Minimal Acceptance Suite

The implementation is not done until these pass:

```text
social transcript
memory truthfulness
name recall/correction
safety refusal
query binding
pronoun grammar
budget parsing
budget-aware candidate count
large-document rapid skim
internal action authorization
graph-patch-only learning
```

## 17. Final Lean Sequence

```text
0. Tests
1. Core types + runtime reorder
2. Primitive goals + moves
3. Minimal grammar realization
4. Candidate framing + ranking
5. Budget-aware spend
6. Budget-aware query
7. Deliberation + anytime distillation
8. Internal actions
9. Response/budget learning
```

This is the clean version:

```text
one canonical path
small vertical slices
tests before each slice
delete old responsibility when replaced
no permanent compatibility maze
```

