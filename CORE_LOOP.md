# CEMM v3.5 Canonical Learning-First Core Loop

**Status:** sole public Stage-0..22 runtime contract.  
**Depends on:** `ARCHITECTURE.md`, `FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`, `FOUNDATIONAL_SEMANTIC_ALGEBRA.md`, `UOL.md`.  
**Core law:** every stage preserves evidence and uncertainty; no stage manufactures downstream meaning merely to make the system respond.

Execution obeys these ordering constraints:

```text
perceive before answering
working graph before memory write
compression before durable storage
source before belief
time before current-state claims
permission before learning
safety/policy before realization/emission
committed outcome before claiming memory/state changed
meaning before wording
```

The Stage-0..22 loop is paired with a continuous acquisition/consolidation spine. Stages may emit learning evidence/frontiers; candidate induction, competence, promotion, compression, invalidation and rehydration remain bounded and proof-bearing.

---

# 1. Macro loop

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
17 RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS
18 BUILD_RESPONSE_UOL
19 REALIZE_TARGET_LANGUAGE
20 VERIFY_AND_AUTHORIZE_EMISSION
21 COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND
22 INVALIDATE_RECOMPUTE_AND_FINALIZE
```

Learning is cross-cutting. Stages 2–13 may emit typed learning evidence/frontiers.

---

# 2. Stage 0 — ORIENT_AND_PIN

Pin the exact cycle authority:

- semantic store snapshot/revision/fingerprint;
- signed boot and learned overlay;
- language packs;
- lexeme/contribution authority;
- construction authority;
- schema revisions;
- participant frame;
- self referent knowledge view;
- discourse/common-ground revision;
- context and clock;
- permissions;
- capabilities/resources;
- learning/inference/transition/realization budgets;
- operation/channel/analyzer contracts.

Create immutable cycle/pass identity.

### Required invariant

A `ParticipantFrame` is established before language grounding:

```text
system_ref
input_speaker_ref
input_addressee_refs
response_audience_refs
context_ref
permission_ref
identity_evidence_refs
```

No pronoun string decides participant identity.

---

# 3. Stage 1 — OBSERVE

Create evidence envelopes from:

- text;
- audio/prosody;
- vision/tracks;
- sensor data;
- tool/database output;
- operation result;
- timers/system events;
- explicit teaching.

Preserve:

```text
payload identity
source
time
span/track
confidence
permission
lineage
```

No semantic interpretation yet.

---

# 4. Stage 2 — ANALYZE_AND_FUSE_FORM

Produce an N-best evidence lattice.

## 4.1 Text path

```text
raw spans
→ normalized observations
→ language/script evidence
→ form/morpheme candidates
→ lexeme/form-family candidates
→ lexical sense/meaning candidates
→ semantic contributions
→ construction candidates
```

### Required records/evidence

- forms and morphemes;
- lexeme/form-family identity;
- allomorph/inflection relation;
- grammatical features;
- lexical senses;
- semantic contribution specs;
- clause/phrase/construction evidence;
- optional dependency/constituency evidence;
- tense/aspect/modality/polarity cues;
- mentions/deixis;
- question/information-gap contributions;
- ellipsis;
- unresolved spans.

## 4.2 Legacy compatibility

If no active lexeme authority exists for a form, the runtime may read legacy direct form→sense links.

The trace must mark that path as legacy compatibility.

Newly learned/reviewed authority must prefer:

```text
form → lexeme → sense → semantic contribution
```

## 4.3 Stage boundary

Stage 2 may emit semantic constraints/contributions.

It must not select:

- final referent identity;
- final schema application;
- actual-world truth;
- response obligation.

External parsers provide evidence only.

---

# 5. Stage 3 — GENERATE_REFERENT_AND_SCHEMA_CANDIDATES

Use Stage-2 contributions and context to generate candidates.

## 5.1 Referent candidates

From:

- ParticipantFrame/deictic roles;
- identifiers/aliases;
- known referent registry;
- discourse mention chains;
- prior output anchors;
- event/proposition history;
- time/place indexes;
- multimodal tracks;
- provisional mentions.

A referential contribution such as `addressee` closes through evidence, never a surface-word branch.

## 5.2 Schema candidates

From:

- explicit TARGET contributions;
- expected schema classes;
- construction programs;
- referent facet entitlements;
- learned lexical indexes;
- operator/query restrictions.

Candidate families may include:

- types;
- properties;
- states;
- relations/roles;
- actions/eventualities/events;
- operators;
- discourse acts.

Unknown material creates typed frontiers without deleting known contributions.

---

# 6. Stage 4 — PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS

For every durable/provisional referent candidate:

1. compute type closure;
2. project facet entitlements;
3. project properties;
4. project state applicability/timelines/current supported assignments;
5. project defaults separately as expectations;
6. project relations/roles/events;
7. project affordances/functions;
8. compute live capabilities/dependencies;
9. apply context/time/access restrictions;
10. expose conflicts/staleness.

### Critical closure interface

Stage 4 must export candidate-generating compatibility to Stage 5.

Example:

```text
open qualitative predicate
+ holder=self
→ self type/facet projection
→ applicable state/property dimensions
→ candidate schemas/values
```

Do not couple semantic compatibility by surface span equality.

---

# 7. Stage 5 — BUILD_UOL_FACTOR_GRAPH

Build one bounded factor graph.

Variables include:

```text
language/lexeme sense
semantic contribution choice
referent identity
semantic type
schema activation
port filler
open semantic variable
answer projection
restriction
operator scope
time/aspect
eventuality interpretation
event occurrence
context
coordination
discourse act
construction
```

## 7.1 Hard factors

- exact revision/use authorization;
- type/facet entitlement;
- port/filler class;
- referent identity incompatibility;
- ParticipantFrame/deictic constraints;
- context isolation;
- state applicability;
- event participant contract;
- query variable typing;
- projection/restriction compatibility;
- permission/access.

## 7.2 Soft factors

- form/morphology evidence;
- lexical priors;
- construction evidence;
- salience/topic continuity;
- referent knowledge plausibility;
- temporal coherence;
- multimodal coherence;
- defaults as rankers;
- complexity/assumptions.

### Requirement

A recognized contribution must remain traceable into factor values/constraints or an explicit unresolved frontier.

---

# 8. Stage 6 — SOLVE_MEANING_HYPOTHESES

Use bounded constraint propagation plus best-first/beam search.

Must support:

- nested/multi-port operators;
- multiple clauses;
- shared arguments;
- state/process/eventuality alternatives;
- event/state reification;
- proposition/claim embedding;
- typed query variables;
- partial meaning;
- multiple contexts;
- unresolved spans.

Do not prefer a meaning because it is easier to realize.

Pruning is traceable.

---

# 9. Stage 7 — SELECT_MEANING_BUNDLE

Select a compatible semantic subgraph.

Preserve:

- coordinated content;
- close alternatives;
- explicit uncertainty;
- unresolved typed variables;
- contribution lineage;
- context/time consistency.

Output conceptually:

```text
MeaningBundle
SelectionAssessment
Alternatives
PartialUnderstandingMap
```

---

# 10. Stage 8 — CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS

Classify selected meaning into:

- discourse acts;
- information gaps/queries;
- claim occurrences;
- proposition content;
- event occurrences;
- state/property assertions;
- directives/desires;
- corrections/retractions;
- learning contributions;
- typed unresolved gaps.

## Query separation

An information gap is not automatically `ask`.

Matrix/interrogative/discourse structure determines whether an `ask` act exists.

Embedded questions remain embedded semantic structures.

No system acknowledgement is chosen here.

---

# 11. Stage 9 — EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT

Determine placement:

```text
actual
attributed report
belief
hypothetical
planned
desired
counterfactual
fictional/simulated
quoted
```

Assess:

- source;
- evidence;
- confidence;
- contradiction;
- sensitivity;
- permission;
- admission policy.

Understanding does not imply admission as actual truth.

---

# 12. Stage 10 — RETRIEVE_AND_ANSWER_BIND

Bind query restriction graphs against admissible semantic knowledge.

The binder is semantic, not storage-kind specific.

Sources include:

- referent knowledge views;
- semantic applications;
- identity/type assertions;
- properties;
- state assignments/timelines;
- qualified defaults;
- relations/roles;
- capabilities/affordances/functions;
- events;
- propositions/claims/knowledge;
- quantities/measures;
- time/place;
- proof/explanation structures.

Output:

```text
bound semantic values
binding proof/lineage
qualification
remaining open variables
```

No surface text.

### Example

`what can you do?` should bind `?action` against live self capability/affordance semantics.

`how are you?` should bind a qualitative self-state/property projection, qualified by actual known/unknown runtime state.

---

# 13. Stage 11 — BUILD_OR_ADVANCE_LEARNING_FRONTIERS

Create typed frontiers.

Required classes include:

```text
unknown_form
unknown_lexeme
unknown_morphology
unknown_lexical_sense
missing_semantic_contribution
missing_construction
reference_ambiguity
unknown_type
missing_state_dimension
missing_state_value
missing_port_filler
missing_query_projection
missing_transition
missing_capability_dependency
missing_realization
missing_response_competence
policy_block
runtime_capability
```

Frontiers carry:

- exact missing contract;
- target refs;
- expected record kinds/classes;
- accepted anchor/filler types;
- evidence/lineage;
- context/permission;
- competence needed to close.

Generic “schema or application missing” is insufficient when a more precise frontier is known.

---

# 14. Stage 12 — INFER_AND_PREVIEW_TRANSITIONS

Run proof-bearing inference.

For selected admitted-context event candidates:

```text
event
→ transition contract candidates
→ state/relation/role deltas
→ capability/resource deltas
→ secondary events
→ impact candidates
```

Preview only.

Hypothetical/reported/fictional events do not mutate actual state.

Defaults are expectations.

Budget exhaustion remains incomplete.

---

# 15. Stage 13 — COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE

Compile atomic GraphPatches only after the working graph has produced authorized, attributable semantic records. Durable writes must be compressed reusable structure/state/history—not raw transcript substitution.

Compile atomic GraphPatches for:

- claim records;
- epistemic admissions/knowledge;
- property/state assignments;
- event occurrences;
- state/capability deltas;
- learning candidates;
- corrections/retractions;
- discourse updates.

Transition commits require:

- admitted trigger;
- exact transition proof;
- context consistency;
- CAS/dependency validation.

Learning promotion/rehydration must use the same durable record authority path.

---

# 16. Stage 14 — ASSESS_IMPACT_AND_IMPORTANCE

Assess impact and significance from selected/admitted meaning.

Never infer emotional significance from a surface keyword.

Use:

- affected referents/stakeholders;
- goals;
- relationships;
- magnitude;
- irreversibility;
- risk;
- history;
- explicit affective evidence;
- importance policy.

Preserve evidence and privacy scope.

---

# 17. Stage 15 — DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS

Derive semantic obligations/goals from:

- bound queries;
- directives;
- claims;
- learning frontiers;
- impacts;
- commitments;
- policies;
- current self state.

Response policy should be structural.

Avoid predicate catalogues.

Typical generic goals:

```text
answer_query
report_semantic_result
clarify_missing_binding
execute_authorized_action
acknowledge_specific_target
qualify_uncertainty
```

Every selected acknowledgement/response goal is target-bearing.

---

# 18. Stage 16 — PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE

External actions require:

```text
afforded
AND live capability
AND permission
AND resources
AND grounded required ports
AND acceptable risk
```

Plan/authorize/execute/reconcile with exact adapter contracts and journals.

Operations never mutate semantic state directly.

Observed results re-enter as evidence.

---

# 19. Stage 17 — RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS

Operation outcomes re-enter epistemics/transitions.

If semantic state changed, invalidate stale goal decisions and re-run Stage 15.

No second hidden goal family.

No stale pre-operation response may surface.

---

# 20. Stage 18 — BUILD_RESPONSE_UOL

Transform selected goals/bindings into semantic response meaning.

Generic transformations include:

```text
answer_bound_query
report_value
report_state
report_set
report_event
report_capability
describe_referent_projection
aggregate
perspective_shift
qualify_epistemic_status
clarify_missing_binding
```

No final strings.

No predicate-specific sentence authority.

---

# 21. Stage 19 — REALIZE_TARGET_LANGUAGE

```text
Response UOL
→ deep clause plans
→ argument frames/constructions
→ information structure
→ references
→ morphology/agreement
→ linearization
→ surface candidates
```

Language authority may choose grammatical form only.

It may not invent meaning.

---

# 22. Stage 20 — VERIFY_AND_AUTHORIZE_EMISSION

Round-trip analyze generated surface through the canonical semantic analyzer.

Compare:

- schema/application structure;
- referents/bindings;
- query/answer structure;
- polarity/modality;
- time/aspect;
- discourse act;
- qualification;
- unsupported additions/losses.

Semantic round-trip PASS is necessary but does **not** authorize emission.

Independent emission gate verifies:

- exact goal/response/realization lineage;
- audience/permission;
- safety/policy;
- operation-result freshness;
- channel contract;
- qualification preservation.

Journal before external side effect.

---

# 23. Stage 21 — COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND

Only observed emission creates output discourse records.

Commit:

```text
speaker
addressee
goal
discourse act
semantic content refs
acknowledgement target
surface ref
emission proof
common-ground status
```

System output becomes referable.

Delivery does not prove user understanding/agreement.

System speech never becomes world truth merely because it was emitted.

---

# 24. Stage 22 — INVALIDATE_RECOMPUTE_AND_FINALIZE

Invalidate dependencies affected by:

- correction/retraction;
- state/capability changes;
- schema/lexeme/contribution revision;
- learning promotion;
- operation result;
- context closure.

Record:

- final snapshot;
- unresolved frontiers;
- replay requirements;
- incomplete budgets.

A changed semantic substrate requires deterministic recomputation/replay where dependencies demand it.

---

# 25. Worked compositional traces

## 25.1 `how are you?`

Expected architecture:

```text
HOW
  VARIABLE ?answer
  PROJECTION candidates:
    qualitative_condition
    manner
    degree
    means
  target restriction open

ARE
  lexeme BE
  grammatical features:
    finite
    present
    agreement evidence
  construction candidates:
    copular predication
    progressive
    passive
    existential

YOU
  REFERENTIAL addressee
```

Participant grounding:

```text
addressee -> referent:self
```

Construction/knowledge closure:

```text
copular predication(subject=self, predicate=?p)
HOW restricts/project ?p toward qualitative description
Stage-4 self entitlements expose applicable property/state dimensions
Stage-5 ranks compatible closures
```

Stage 8 matrix interrogative may yield `ask`.

Stage 10 binds current supported value or returns qualified unknown.

Stage 18 builds semantic report.

No phrase-specific rule.

## 25.2 `what can you do?`

```text
WHAT
  open projected answer

CAN
  capability/modal contribution

YOU
  addressee -> self

DO
  open action/eventuality slot
```

Compose:

```text
query(
  variable=?action,
  restriction=capability(holder=self, action=?action),
  projection=?action
)
```

Stage 10 binds capabilities/affordances.

No canned capability sentence/list.

---

# 26. Failure invariants

- recognized contributions may not silently disappear;
- no selected meaning -> typed partial map/frontier;
- no referent evidence -> unresolved identity, not guessed binding;
- no epistemic admission -> no actual-world transition;
- no transition rule -> understood event remains without guessed effect;
- no state evidence -> qualified unknown/default expectation, not fabricated state;
- no target -> no generic acknowledgement;
- no response transform -> explicit response competence gap;
- no realization -> realization frontier/silence;
- timeout -> partial/incomplete, never success;
- no parser -> native construction evidence path must still be possible when reviewed grammar is sufficient.
