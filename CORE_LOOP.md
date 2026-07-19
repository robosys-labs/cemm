# CEMM v3.5 Canonical Learning-First Core Loop

**Status:** replacement runtime contract  
**Depends on:** `ARCHITECTURE.md`, `FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`, and `UOL.md`  
**Core law:** no stage may manufacture a downstream artifact, and every cycle must preserve a reusable learning frontier even when full understanding fails.

---

## 1. Macro loop

```text
0  ORIENT_AND_PIN
1  OBSERVE
2  ANALYZE_AND_FUSE_FORM
3  GENERATE_REFERENT_AND_SCHEMA_CANDIDATES
4  PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS
5  BUILD_UOL_FACTOR_GRAPH
6  SOLVE_MEANING_HYPOTHESES
7  SELECT_MEANING_BUNDLE
8  CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS
9  EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT
10 RETRIEVE_AND_ANSWER_BIND
11 BUILD_OR_ADVANCE_LEARNING_FRONTIERS
12 INFER_AND_PREVIEW_TRANSITIONS
13 COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE
14 ASSESS_IMPACT_AND_IMPORTANCE
15 DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS
16 PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE
17 GENERATE_RESPONSE_GOALS
18 BUILD_RESPONSE_UOL
19 REALIZE_TARGET_LANGUAGE
20 VERIFY_AND_AUTHORIZE_EMISSION
21 COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND
22 INVALIDATE_RECOMPUTE_AND_FINALIZE
```

Learning is not one isolated phase. Stages 3–13 all emit learning evidence, unresolved dependencies, competence cases, or counterevidence.

---

## 2. Stage 0 — ORIENT_AND_PIN

Pin:

- semantic-schema revision;
- referent/knowledge store revisions;
- learned overlay revisions;
- discourse and world-model revisions;
- language/analyzer/realizer versions;
- self knowledge view;
- clock and locale;
- permissions, capabilities, resources, and risk;
- inference, transition, learning, and realization budgets.

Create a `CognitiveCycle` with immutable stage outputs.

---

## 3. Stage 1 — OBSERVE

Create evidence from:

- text;
- audio and prosody;
- vision and tracked regions;
- sensor readings;
- tool/database outputs;
- operation results;
- timer/system events;
- explicit teaching actions.

Preserve raw payload identity, source, time, confidence, permission, and lineage.

---

## 4. Stage 2 — ANALYZE_AND_FUSE_FORM

Produce N-best:

- language/script spans;
- tokens and morphemes;
- lexical senses;
- clause and phrase structures;
- dependency/constituency edges;
- conjunction and scope;
- relative/complement clauses;
- tense/aspect/modality/negation cues;
- question variables;
- mentions and deictics;
- ellipsis;
- discourse markers;
- unresolved spans.

Form analysis emits no selected referent or proposition.

---

## 5. Stage 3 — GENERATE_REFERENT_AND_SCHEMA_CANDIDATES

### 5.1 Referent candidates

Use:

- direct participant frame;
- aliases and identifiers;
- known referent registry;
- discourse mention chains;
- event/proposition history;
- geospatial/time indexes;
- multimodal tracks;
- provisional typed mentions;
- learned lexical indexes.

### 5.2 Schema candidates

Activate possible:

- referent types;
- properties;
- states;
- actions/events;
- relations/roles;
- operators;
- discourse acts.

Unknown forms create typed lexical or schema candidates, not immediate clarification.

---

## 6. Stage 4 — PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS

For every referent candidate:

1. compute type closure;
2. project facet entitlements;
3. retrieve active/default/latent/unknown state;
4. retrieve properties, relations, roles, event history;
5. project affordances and functions;
6. compute live capabilities from dependencies;
7. apply context/time/access restrictions;
8. expose conflicts and stale projections.

This stage supplies semantic compatibility. It does not choose final identity.

---

## 7. Stage 5 — BUILD_UOL_FACTOR_GRAPH

Variables include:

```text
language sense
referent identity
semantic type
schema activation
port filler
operator scope
event occurrence
claim/proposition relation
context
time
coordination
discourse act
```

Hard factors include:

- type/facet entitlement;
- port constraints;
- identity incompatibility;
- scope and modality;
- state applicability;
- event participant constraints;
- query variable typing;
- access/permission;
- context isolation.

Soft factors include:

- form evidence;
- salience;
- topic continuity;
- event/state plausibility;
- multimodal coherence;
- defaults;
- importance priors;
- assumptions and complexity.

Defaults rank; they do not become facts.

---

## 8. Stage 6 — SOLVE_MEANING_HYPOTHESES

Use bounded constraint propagation and best-first/beam search.

The solver must support:

- nested operators;
- multiple clauses;
- shared arguments;
- event and state reification;
- proposition and claim embedding;
- partial meaning;
- typed open variables;
- multiple contexts;
- unresolved spans.

Pruning is traceable.

---

## 9. Stage 7 — SELECT_MEANING_BUNDLE

Choose a compatible semantic subgraph for the turn.

Selection requirements:

- preserve coordinated content;
- retain close alternatives;
- avoid double-consuming evidence;
- maintain context/time consistency;
- preserve explicit uncertainty;
- never select a meaning solely because it is easiest to realize.

Output:

```text
MeaningBundle
SelectionAssessment
Alternatives
PartialUnderstandingMap
```

---

## 10. Stage 8 — CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS

Identify:

- discourse act occurrences;
- claim occurrences and proposition content;
- event occurrence candidates;
- state/property assertions;
- queries;
- directives and desired states;
- corrections/retractions;
- learning contributions;
- typed gaps.

“Understood” or “acknowledge” is not selected here for the system; this stage classifies input acts.

---

## 11. Stage 9 — EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT

Determine whether content belongs to:

- actual;
- attributed report;
- belief;
- hypothetical;
- planned;
- desired;
- counterfactual;
- fictional/simulated;
- quoted context.

Assess source, evidence, confidence, sensitivity, contradiction, and permission.

An event can be semantically understood without being admitted as actual.

---

## 12. Stage 10 — RETRIEVE_AND_ANSWER_BIND

Unify query restriction graphs against admissible knowledge.

Support answers containing:

- referents;
- quantities;
- times;
- places;
- events;
- propositions;
- schema/action references;
- collections;
- truth-status results;
- explanations/proofs.

Do not return a text answer at this stage.

---

## 13. Stage 11 — BUILD_OR_ADVANCE_LEARNING_FRONTIERS

### 13.1 Learning inputs

- explicit teaching;
- unknown lexical senses;
- provisional types;
- incomplete event/property/state schemas;
- corrections;
- repeated evidence;
- counterexamples;
- failed competence cases;
- unresolved transition dependencies.

### 13.2 Frontier behavior

Generate exact questions such as:

```text
Is “glorp” a property, action, state, or type?
What kind of referent can perform this action?
Does this event always end the state, or only usually?
Which capability depends on this state?
Is this consequence harmful to the user or only to the affected referent?
```

Generic rephrasing is last resort.

---

## 14. Stage 12 — INFER_AND_PREVIEW_TRANSITIONS

### 14.1 Inference

Run bounded proof-bearing rules in the selected contexts.

### 14.2 Event transition preview

For selected event occurrences:

```text
event
→ state delta candidates
→ relation/role deltas
→ capability/resource deltas
→ secondary event candidates
→ impact candidates
```

### 14.3 Safety

- hypothetical events never mutate actual state;
- defaults remain expectations;
- sensitive consequences are blocked by policy;
- transitions can be incomplete under budget.

---

## 15. Stage 13 — COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE

Compile separate patches for:

- claim records;
- admitted proposition knowledge;
- property/state assignments;
- event occurrences;
- state/capability deltas;
- learning candidates;
- corrections/retractions;
- discourse updates.

State transition commits require an admitted trigger event and a valid proof.

---

## 16. Stage 14 — ASSESS_IMPACT_AND_IMPORTANCE

### 16.1 Impact

Assess event/state changes for affected referents and stakeholders.

### 16.2 Importance

Use:

- explicit importance;
- relationship;
- user goals;
- history;
- focus;
- emotional evidence;
- magnitude;
- irreversibility;
- risk.

This stage may search bounded session/history summaries for significance evidence. It must preserve the evidence and privacy scope.

---

## 17. Stage 15 — DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS

Derive target-bearing semantic obligations from active response-policy rules, then generate semantic goals from:

- queries;
- directives;
- claims;
- learning frontiers;
- impacts;
- commitments;
- policies;
- self state.

Arbitrate conflicts by urgency, importance, permission, risk, user intent, and resource cost.

---

## 18. Stage 16 — PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE

Operations bind action schemas and referents.

Execution requires:

```text
afforded
AND live capability
AND permission
AND resources
AND grounded required ports
AND accepted risk
```

Reconciliation compares predicted and observed outcomes and emits evidence/patches.

---

## 19. Stage 17 — GENERATE_RESPONSE_GOALS

Generate candidates such as:

```text
answer_query
answer_capability_query
report_state
acknowledge_claim
acknowledge_commit
console
warn
qualify
ask_reference_repair
ask_schema_repair
continue_learning
confirm_operation
report_operation_result
refuse_or_limit
follow_response_policy
remain_silent
```

Every goal has a semantic target.

A targetless acknowledgement candidate is invalid.

---

## 20. Stage 18 — BUILD_RESPONSE_UOL

Apply proof-carrying semantic transformations:

- query answer closure;
- perspective shift;
- capability expansion;
- state/property projection;
- aggregation;
- qualification;
- impact-sensitive discourse act selection;
- explicit acknowledgement binding;
- repair question synthesis.

No final strings exist yet.

---

## 21. Stage 19 — REALIZE_TARGET_LANGUAGE

Transform:

```text
Response UOL
→ deep clause plans
→ argument frames
→ syntax and information structure
→ references
→ morphology/agreement
→ linearization
→ surface
```

Language packages cannot invent facts, impacts, relationships, certainty, or emotion.

---

## 22. Stage 20 — VERIFY_AND_AUTHORIZE_EMISSION

Round-trip analyze the surface and compare recovered meaning with response UOL.

Verify:

- semantic schemas;
- referents and bindings;
- polarity;
- modality;
- time/aspect;
- discourse act;
- impact qualification;
- no unsupported additions.

Explicit literal response policies are verified against the policy record and semantic trigger.

---

## 23. Stage 21 — COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND

Commit system output as semantic discourse:

```text
speaker
addressee
response goal
discourse act
content proposition/event refs
acknowledgement target
surface ref
emission proof
common-ground status
```

This enables “why?”, “for what?”, “understood what?”, and anaphora to system output.

---

## 24. Stage 22 — INVALIDATE_RECOMPUTE_AND_FINALIZE

Invalidate projections affected by:

- corrections;
- state changes;
- capability changes;
- schema revisions;
- retractions;
- operation results;
- context closure.

Record incomplete budgets and replay requirements.

---

## 25. Death-event walkthrough

Input:

```text
“My fox died.”
```

The loop should:

1. detect a claim act;
2. resolve `my` to user and `fox` to a fox referent or provisional owned fox;
3. select biological death using living-type compatibility;
4. place the proposition as a user claim;
5. assess whether it is admitted as conversational actual/report;
6. create a death event occurrence in the chosen context;
7. preview/commit life-status transition;
8. recompute life-dependent capabilities;
9. assess harmful, irreversible impact;
10. retrieve ownership/mention/emotional significance;
11. generate response candidates such as console, specific acknowledgement, or clarification;
12. choose according to certainty, importance, and user stance;
13. build response UOL;
14. realize without inventing a name, relationship, or feeling.

---

## 26. Failure invariants

- no selected meaning → typed partial map and repair;
- no epistemic admission → no actual state transition;
- no transition rule → event remains understood without guessed effects;
- no significance evidence → avoid over-personalized consolation;
- no target → no acknowledgement;
- no realizable response → silence or explicit realization gap;
- timeout → partial proof and incompleteness, never success.
