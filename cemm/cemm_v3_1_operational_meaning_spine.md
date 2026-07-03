# CEMM v3.1 Operational Meaning Spine

## Purpose

This file is the senior ML/NLP engineering alignment document for the remaining deep CEMM gaps after the v3 foundational atom work.

The current repo now has the right high-level representational direction: `MeaningPerceptPacket`, `SituationFrame`, `OutcomeAtom`, `ValenceAtom`, `SafetyFrame`, `RetrievalPlan`, and `ConversationActPacket` exist. The remaining issue is that these packets are not yet the operational and trainable spine of the system. They are partly populated, partly advisory, and partly invisible to the training loop.

The next milestone is not “add more aliases.” The next milestone is:

```text
CEMM v3.1 = make the foundational atoms operational, trainable, persistent, and authoritative.
```

## Core thesis

CEMM should not primarily learn:

```text
phrase -> intent -> template
```

CEMM should learn:

```text
surface signal + context
-> referents/actions/states/relations/needs
-> bound situation frame
-> expected entity-relative outcomes
-> memory/retrieval/response obligations
-> realized answer/action
-> feedback and structural update
```

This is the difference between a patched symbolic chatbot and a teachable multilingual meaning system.

## Current repo state: what is good

The code has made real progress:

1. `MeaningPerceptPacket` exists before UOL and includes referents, actions, states, relations, needs, unknown lexemes, idioms, affect, and attention target.
2. `SituationFrame` exists and can bind actor/action/object/target/place/needs/outcomes.
3. `OutcomeEvaluator` exists and computes valence from state-change dimensions.
4. `SafetyFrameDetector` exists before final decision.
5. `RetrievalPlan` exists as a first-class object.
6. `ConversationActPacket` supports primary and secondary acts.
7. `OutputStateUpdater` runs after actual response realization.
8. `LexemeMemory` exists for learned word/phrase/command aliases.

These are the right ingredients.

## Current repo state: what is still deeply wrong

The remaining issue is that the ingredients are not yet integrated as a learned control system.

### Gap 1: foundational atoms are containers, not operational variables

`MeaningPerceptPacket` and `SituationFrame` exist, but most binding is still shallow:

```text
first actor-like referent -> actor
first action -> action
first target -> target
first object -> object
```

That is not enough for native language understanding. CEMM needs role binding as a structured prediction problem.

Add:

```text
cemm/kernel/frame_binder.py
```

Target behavior:

```text
Input: "Pear is a type of fruit that you eat and is shaped like a curvy triangle"
Output:
  subject = pear
  predicates:
    is_a -> fruit
    edible -> true
    shape -> curvy_triangle_like
```

```text
Input: "I am fine, you?"
Output:
  act 1: user_state_report(user=fine)
  act 2: reciprocal_phatic_checkin(target=self)
```

```text
Input: "Obidike is looking for my trouble"
Output:
  actor = Obidike/person_candidate
  affected_entity = user
  idiom_candidate = looking_for_my_trouble
  situation = social_conflict_possible
```

### Gap 2: new packets are not first-class training targets

`training_export.py` still mainly exports classic tasks such as semantic graph extraction, claim extraction, entity resolution, UOL mapping, and operator selection.

But the new foundational packets must be exported too:

```text
meaning_percept_extraction
role_binding
situation_frame_construction
outcome_valence_prediction
safety_frame_detection
retrieval_plan_prediction
reply_obligation_prediction
act_resolution_planning
memory_update_planning
response_planning
output_state_update_prediction
```

If these are not exported, the model cannot learn the actual new architecture.

### Gap 3: `ConversationActPacket` is multi-act in type, but decision mostly uses primary act

`ConversationActPacket` supports secondary acts, but `DecisionRouter` still tends to route through `conversation_act.act_type`, which delegates to the primary act.

That collapses turns like:

```text
I'm good, just trying to see what you can do
```

into one route instead of resolving multiple obligations:

```text
1. acknowledge user state
2. answer capability query
```

Add:

```text
cemm/kernel/act_resolution_planner.py
```

Its output should be:

```python
@dataclass
class ActResolutionPlan:
    reply_obligations: list[ReplyObligation]
    memory_update_tasks: list[MemoryUpdatePlan]
    answer_tasks: list[AnswerTask]
    safety_tasks: list[SafetyTask]
    deferred_tasks: list[DeferredTask]
```

The decision layer should route from this plan, not directly from a single act label.

### Gap 4: `RetrievalPlan` is advisory, not executable

The pipeline creates a `RetrievalPlan`, but non-`none` modes still flow into generic structural retrieval.

Add:

```text
cemm/retrieval/retrieval_executor.py
```

It should execute modes differently:

```text
profile -> profile store only
self_knowledge -> self claims + capability models only
lexeme_memory -> lexeme memory / persistent lexeme models only
entity_memory -> claims for target entity + target predicates
world_memory -> world claims, freshness-aware
procedure_model -> executable procedure/capability/tool models
live_tool_required -> abstain/tool handoff, not stale memory
```

### Gap 5: output state should be a state transition, not an optional patch

`OutputStateUpdater.apply()` currently updates fields only when non-null. That can leave stale pending question state.

Replace optional patching with explicit state delta:

```python
@dataclass
class ConversationStateDelta:
    set_fields: dict
    clear_fields: list[str]
    discourse_stack_push: list[ReplyObligation]
    discourse_stack_pop: list[str]
```

Short-term fix:

```python
kernel.conversation.pending_assistant_question = update.pending_assistant_question
kernel.conversation.expected_user_answer_type = update.expected_user_answer_type
```

Then persist the updated state back into `pipeline._session_state` after the output updater runs.

### Gap 6: learned lexemes are in-memory, not structural memory

`LexemeMemory` is useful, but it is an in-memory index. CEMM’s original architecture says reusable learned structure belongs in `Model`, with evidence, scope, status, trust, and promotion.

Correct design:

```text
LexemeMemory = hot cache
ModelStore = source of truth
```

Learned command aliases should become:

```text
Model(kind="tool_schema_model" | "procedure_model" | "uol_semantic" | "predicate")
```

depending on role.

### Gap 7: entity fact extraction is missing as its own learned operator

Current claim extraction is a thin UOL side effect. It is not a robust entity-learning system.

Add:

```text
cemm/kernel/entity_fact_extractor.py
```

It should handle language-specific patterns but emit language-neutral claims:

```text
X is a type/kind of Y -> X is_a Y
X is shaped like Y -> X shape Y
X is usually COLOR -> X typical_color COLOR
X is used for Y -> X function Y
X comes from PLACE -> X source PLACE
X can ACTION -> X affordance ACTION
```

This must work with active topic/coreference:

```text
Pear is a fruit.
It is usually green.
Do you remember the shape?
```

### Gap 8: event schemas are static JSON, not promoted learned structure

`uol_semantics.json` seeds event schemas. That is right for bootstrapping, but repeated learned event schemas should become inactive model candidates, then validated active models.

Correct loop:

```text
example traces
-> candidate EventSchema
-> validation
-> Model(status=candidate)
-> promotion
-> SituationFrameBuilder uses active event models
```

### Gap 9: entity-relative utility is too shallow

`OutcomeEvaluator` currently uses generic favorable dimension lists.

CEMM needs entity-specific utility models:

```text
self/CEMM:
  favorable: knowledge↑, capability↑, data_integrity↑, user_trust↑, coherence↑
  unfavorable: hallucination↑, error_rate↑, privacy_leak↑, permission_violation↑, memory_loss↑

human:
  favorable: health↑, safety↑, hunger↓, pain↓, knowledge↑
  unfavorable: health↓, safety↓, distress↑

world/natural entity:
  favorable/unfavorable should be domain-specific and lower confidence unless configured
```

Add:

```text
cemm/kernel/entity_utility_model.py
```

### Gap 10: capability is not yet a self-affordance ontology

CEMM’s native abilities should not be just self-claims or templates.

Add:

```text
CapabilityModel
```

Each capability should include:

```text
capability_key
supported
requires_tool
input_requirements
output_kind
side_effects
memory_effects
permission_required
examples
limitations
confidence
```

Then questions like:

```text
can you browse the web?
can you play music?
can you learn commands?
can you chain commands?
```

become self-affordance queries, not open-domain entity questions.

## Proposed v3.1 core loop

```text
Signal
-> Normalize
-> MeaningPerceptPacket
-> FrameBinder
-> SituationFrame
-> OutcomeEvaluator + EntityUtilityModel
-> SafetyFrame
-> EntityFactExtractor
-> ConversationActPacket
-> ActResolutionPlan
-> RetrievalPlan
-> RetrievalExecutor
-> MemoryUpdatePlan
-> DecisionPacket
-> ResponsePlan
-> Realizer
-> ConversationStateDelta
-> Trace + TrainingExport
-> Promotion / Learning
```

## Minimal code changes included in this patch set

This patch set focuses on low-risk foundational alignment:

1. Fix safety valence direction bug.
2. Make output-state clearing explicit.
3. Upgrade training export so new v3 packets are visible as ML targets.
4. Provide this canonical v3.1 roadmap.

## Next implementation order

### P0

1. Apply the safety detector bug fix.
2. Apply the output-state clearing fix.
3. Export `MeaningPerceptPacket`, `SituationFrame`, `SafetyFrame`, and `RetrievalPlan` in training records.
4. Persist output-state updater results back into session state after final realization.

### P1

5. Implement `FrameBinder`.
6. Implement `EntityFactExtractor`.
7. Implement `RetrievalExecutor`.
8. Implement `ActResolutionPlanner`.

### P2

9. Persist lexeme learning through `Model` records.
10. Add `CapabilityModel` and self-affordance query handling.
11. Add entity-specific utility models.
12. Train small Pi-friendly models for role binding, claim extraction, capability classification, and response planning.

## Acceptance tests

```text
I am fine, thank you
-> social response, no evidence failure

I am fine, you?
-> acknowledges user state + answers reciprocal check-in

Pear is a type of fruit that is shaped like a curvy triangle
-> stores pear is_a fruit + pear shape curvy_triangle_like

It is usually green
-> resolves it=pear and stores typical_color green

Can you browse the web?
-> self capability/tool availability answer

Can you learn new commands?
-> capability answer describing command-alias learning

When I say moonlight, remember this quietly
-> creates command alias model candidate or active user-scoped model

Should I beat him?
-> safety deescalation, no general conversation template

You keep giving canned responses
-> meta critique/frustration response, no evidence failure
```
