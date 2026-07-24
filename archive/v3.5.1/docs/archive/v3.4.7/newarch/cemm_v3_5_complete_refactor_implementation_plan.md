# CEMM v3.5 Complete Refactor Implementation Plan

**Status:** proposed execution plan  
**Baseline:** commit `855e17d57129bb8a7a601bf7077994c1971e736d`  
**Release character:** breaking authority and data migration  
**Required outcome:** a bounded multilingual baby CEMM whose ordinary runtime composes meaning atoms, queries referent operational profiles, learns grounded extensions, and realizes output through reusable grammar rules.

---

## 1. Release strategy

Do not continue adding fixes inside the existing `cemm/v347` package.

Create a new canonical package, initially:

```text
cemm/v350/
```

During development:

- v3.4.7 remains a behavioral baseline and migration source;
- v3.5 runs behind an explicit runtime flag;
- no compatibility fallback is permitted inside v3.5 interpretation or realization;
- acceptance tests compare semantic behavior, not just surface strings.

At cutover:

- `cemm.app.runtime.Runtime` points only to v3.5;
- old language templates and predicate-shortcut data move to migration fixtures/archive;
- the demo identifies the runtime as v3.5;
- the v3.4.7 package becomes non-authoritative.

---

## 2. Phase 0 — Freeze and forensic baseline

### Work

1. Pin the current repository commit.
2. Capture the failing chat transcript and full traces.
3. Add trace snapshots for:
   - `hii`;
   - `how re u?`;
   - `for what?`;
   - `what can you do?`;
   - `go away`;
   - `My name is Chibu`;
   - `what's my name?`.
4. Inventory:
   - all foundation refs;
   - language lexical entries;
   - fixed bindings;
   - constructions;
   - predicate answer templates;
   - response move templates;
   - hard-coded response goal kinds.
5. Produce an authority map from input surface to emitted text.
6. Record performance and store mutation counts.

### Exit criteria

- every observed failure has a semantic root-cause ticket;
- no fix is proposed as a new transcript phrase;
- the v3.4.7 baseline remains reproducible.

---

## 3. Phase 1 — Governing contract and version boundary

### Work

1. Create:
   - `cemm/ARCHITECTURE_V350.md`;
   - `cemm/newarch/CORE_LOOP_V350.md`;
   - `cemm/newarch/DATA_ARCHITECTURE_V350.md`;
   - `cemm/newarch/NLG_ALGEBRA_V350.md`;
   - `cemm/newarch/V350_IMPLEMENTATION_PLAN.md`.
2. Update `AGENTS.md` to make v3.5 the target while implementation is in progress.
3. Add a version manifest:
   - architecture version;
   - semantic package version;
   - DB schema version;
   - language package versions;
   - grammar engine version;
   - migration version.
4. Add forbidden-pattern checks for:
   - `predicate_answers`;
   - generic `response_moves`;
   - direct surface-to-selected-predicate shortcuts;
   - English word tests in kernel modules.

### Exit criteria

- one version source;
- explicit authority order;
- CI fails on prohibited patterns.

---

## 4. Phase 2 — Meaning-atom metamodel

### New modules

```text
cemm/v350/atoms/model.py
cemm/v350/atoms/classes.py
cemm/v350/atoms/ports.py
cemm/v350/atoms/inheritance.py
cemm/v350/atoms/constraints.py
cemm/v350/atoms/registry.py
```

### Work

1. Implement `MeaningAtomSchema`.
2. Implement specialized atom records:
   - referent type;
   - property;
   - state dimension/value;
   - action;
   - relation;
   - role;
   - unit;
   - operator;
   - discourse.
3. Implement local atom ports and constraints.
4. Implement inheritance closure and cycle classification.
5. Implement lifecycle/revision records.
6. Implement typed atom applications.
7. Implement semantic variables, scope links, and coordination groups.
8. Make the old `PredicateSchema` a migration-only compiled view.

### Tests

- type closure;
- local port validation;
- invalid cycles;
- property cardinality;
- action actor constraints;
- operator scope constraints;
- deterministic atom fingerprints.

### Exit criteria

- all seed semantics can be represented without `PredicateSchema` being the root authority.

---

## 5. Phase 3 — Modular source data and compiler

### New modules

```text
cemm/v350/data/compiler.py
cemm/v350/data/validators.py
cemm/v350/data/sqlite_builder.py
cemm/v350/data/manifest.py
cemm/v350/data/competence.py
```

### Work

1. Establish the modular source tree.
2. Define JSON Schema or equivalent validators.
3. Implement deterministic compilation to SQLite.
4. Generate inheritance, port, affordance, and lexical indexes.
5. Generate content hashes and dependency manifests.
6. Add data-lint CLI.
7. Add source-to-compiled semantic equivalence tests.

### Exit criteria

- rebuilding produces byte-identical logical content;
- no runtime scans the monolithic v3.4.7 foundation file.

---

## 6. Phase 4 — Foundation meaning data

### Seed order

1. broad referent types;
2. properties;
3. state dimensions and values;
4. actions;
5. relations;
6. operators;
7. discourse acts;
8. units/time;
9. type profiles;
10. affordances;
11. self capabilities;
12. rules.

### First vertical seed

#### Referent types

```text
referent
agent
person
animal
organization
software_agent
physical_object
digital_object
place
event
process
state
proposition
quantity
unit
time
collection
information_object
context
schema
```

#### Properties

```text
name
type
meaning
version
age
location
role
capability_set
owner
part_whole
```

#### States

```text
operational_status
availability
connectivity
memory_status
understanding_status
attention
conversational_tone
```

#### Actions

```text
observe
read
write
retrieve
learn
reason
remember
forget
ask
answer
communicate
say
obey
start
stop
move
give
take
see
hear
```

#### Operators

```text
query
ability
permission
obligation
intention
pro_action
negation
past
present
future
ongoing
completed
habitual
still
coordination
comparison
```

### Exit criteria

- the first five acceptance vertical slices can be represented solely from seed atoms.

---

## 7. Phase 5 — Normalized semantic store

### New modules

```text
cemm/v350/store/schema.sql
cemm/v350/store/reader.py
cemm/v350/store/patches.py
cemm/v350/store/snapshots.py
cemm/v350/store/migrations.py
cemm/v350/store/indexes.py
```

### Work

1. Implement normalized tables from the data architecture.
2. Preserve GraphPatch-only mutation.
3. Add pinned multi-store snapshot.
4. Add typed read repositories:
   - atom repository;
   - referent repository;
   - knowledge repository;
   - capability repository;
   - discourse repository.
5. Add scope and valid-time filtering.
6. Add semantic signature indexes.
7. Add restart hydration tests.

### Exit criteria

- core lookup does not depend on decoding large JSON blobs;
- all writes are patch-controlled and reversible.

---

## 8. Phase 6 — Language package redesign

### New package contract

```text
LanguagePack
  lexemes
  senses
  morphology
  paradigms
  argument frames
  syntax rules
  linearization rules
  discourse realization
  idioms
  competence cases
```

### Work

1. Convert English, French, and Swahili.
2. Split lexical form from semantic sense.
3. Remove completed-predicate mappings for:
   - query words;
   - modals;
   - copulas;
   - pro-verbs;
   - tense/aspect markers.
4. Add colloquial normalization as evidence:
   - `hii` → greeting-form candidate;
   - `re` → copular contraction candidate where licensed.
5. Add morphology and agreement.
6. Restrict idioms to genuine non-compositional cases.

### Exit criteria

- “what,” “can,” “you,” and “do” activate distinct atoms;
- no language pack contains a full answer sentence for ordinary semantic atoms.

---

## 9. Phase 7 — Form lattice v2

### New modules

```text
cemm/v350/language/lattice.py
cemm/v350/language/fusion.py
cemm/v350/language/dependency.py
cemm/v350/language/scope.py
cemm/v350/language/coordination.py
cemm/v350/language/ellipsis.py
```

### Work

1. Represent dependency/constituency evidence.
2. Represent operator scope candidates.
3. Represent code switching.
4. Represent relative and complement clauses.
5. Represent coordination/shared argument candidates.
6. Represent query-variable type cues.
7. Preserve unresolved spans and partial structures.
8. Integrate external NER/NLP adapters behind evidence interfaces.

### Exit criteria

- the lattice for the required chat inputs exposes the necessary form alternatives without selected semantics.

---

## 10. Phase 8 — Referent operational profiles

### New modules

```text
cemm/v350/referents/profile.py
cemm/v350/referents/type_closure.py
cemm/v350/referents/affordances.py
cemm/v350/referents/capabilities.py
cemm/v350/referents/multimodal_state.py
```

### Work

1. Compile type profiles.
2. Derive inherited properties and states.
3. Derive structural affordances.
4. merge live capability, permission, resource, and world state;
5. expose one pinned profile per candidate referent.
6. distinguish understanding from executable ability.
7. add explainable profile traces.

### Exit criteria

- self capability queries operate from profile data;
- physical movement is rejected for unembodied self without preventing semantic understanding of movement.

---

## 11. Phase 9 — Atom activation and factor-graph composition

### New modules

```text
cemm/v350/understanding/activation.py
cemm/v350/understanding/factor_graph.py
cemm/v350/understanding/constraints.py
cemm/v350/understanding/solver.py
cemm/v350/understanding/hypotheses.py
cemm/v350/understanding/selector.py
```

### Work

1. Activate atoms from heterogeneous evidence.
2. Build variables for senses, referents, ports, scope, and discourse acts.
3. Implement arc consistency.
4. Implement bounded branching/beam search.
5. Compose nested applications.
6. Compose queries and answer projections.
7. Compose coordination and shared arguments.
8. Compose relative/complement clauses.
9. Preserve partial graphs.
10. Select compatible bundles.

### Deletion gate

The v3.5 runtime must not call v3.4.7 `SchemaActivator`, `JointMeaningAssembler`, or `MeaningBundleSelector`.

### Exit criteria

- “My name is Chibu” and “what can you do?” are composed without full-sentence patterns or direct predicate shortcuts.

---

## 12. Phase 10 — Discourse and system-output semantics

### New modules

```text
cemm/v350/discourse/model.py
cemm/v350/discourse/acts.py
cemm/v350/discourse/common_ground.py
cemm/v350/discourse/output_commit.py
cemm/v350/discourse/ellipsis.py
```

### Work

1. Store both user and system UOL turns.
2. Track discourse acts and content targets.
3. Track output proposition refs.
4. Track acknowledgement targets.
5. Track reasons, purposes, commitments, and alternatives.
6. Resolve elliptical follow-ups.
7. Track repetition and failed repairs.

### Exit criteria

- “for what?”, “why?”, “understood what?”, and “that” can resolve to prior system semantic content.

---

## 13. Phase 11 — Query and epistemic engine v2

### New modules

```text
cemm/v350/knowledge/unification.py
cemm/v350/knowledge/query.py
cemm/v350/knowledge/assessment.py
cemm/v350/knowledge/admission.py
cemm/v350/knowledge/truth.py
```

### Work

1. Match graph restrictions, not only one predicate ref.
2. Bind typed semantic variables.
3. Query atom schemas as values, including action refs.
4. Support collection answers.
5. Support property/state temporal queries.
6. Preserve contradictions and attribution.
7. Generate precise knowledge gaps.

### Exit criteria

- capability queries return action atoms;
- property queries return value referents;
- negative and modal queries preserve scope.

---

## 14. Phase 12 — Grounded learning v2

### New modules

```text
cemm/v350/learning/classifier.py
cemm/v350/learning/frontier.py
cemm/v350/learning/induction.py
cemm/v350/learning/promotion.py
cemm/v350/learning/competence.py
```

### Work

1. Learn atom schemas and type profiles.
2. Learn lexical senses separately.
3. Learn affordances and capability conditions separately.
4. Learn property/state/action/relation definitions.
5. Generate typed frontier questions.
6. Require independent competence before global activation.
7. Rehydrate learned data into normal indexes.
8. Add forgetting/retraction/supersession.

### Exit criteria

- a taught property or action becomes usable across paraphrases and languages once lexicalized;
- unknown words do not cause generic clarification.

---

## 15. Phase 13 — Self capability and operation architecture

### New modules

```text
cemm/v350/self/profile.py
cemm/v350/self/capability_observer.py
cemm/v350/operations/contracts.py
cemm/v350/operations/planner.py
cemm/v350/operations/authorizer.py
cemm/v350/operations/executor.py
cemm/v350/operations/reconciler.py
```

### Work

1. Seed self affordances as semantic action refs.
2. Derive live capabilities from built-ins/adapters.
3. Model permissions, resources, competence, and risk separately.
4. Model `obey(command)` with policy conditions.
5. Model dialogue actions such as stop/pause/respond.
6. Reauthorize before irreversible effect.
7. Expose capability evidence for response.

### Exit criteria

- capability answers change when adapters or permissions change;
- capability output contains no seeded marketing prose.

---

## 16. Phase 14 — Response semantic transducers

### New modules

```text
cemm/v350/response/goals.py
cemm/v350/response/transducers.py
cemm/v350/response/query_answer.py
cemm/v350/response/perspective.py
cemm/v350/response/aggregation.py
cemm/v350/response/repair.py
cemm/v350/response/acknowledgement.py
```

### Work

1. Implement query answer closure.
2. Implement perspective shift.
3. Implement capability expansion.
4. Implement property/state projection.
5. Implement targeted repair synthesis.
6. Implement explicit acknowledgement binding.
7. Implement aggregation and qualification.
8. Attach transform proofs.

### Deletion gate

Remove generic canned clarification and targetless acknowledgement from the canonical path.

### Exit criteria

- every response clause exists as response UOL before language realization.

---

## 17. Phase 15 — Multilingual grammar and morphology

### New modules

```text
cemm/v350/nlg/deep_plan.py
cemm/v350/nlg/unification.py
cemm/v350/nlg/frames.py
cemm/v350/nlg/syntax.py
cemm/v350/nlg/references.py
cemm/v350/nlg/morphology.py
cemm/v350/nlg/linearization.py
cemm/v350/nlg/verification.py
```

### Work

1. Implement deep clause plans.
2. Implement feature unification.
3. Implement argument-frame selection.
4. Implement modal/question/copular/negative rules.
5. Implement coordination with shared arguments.
6. Implement reference generation.
7. Implement morphology.
8. Implement language-specific linearization.
9. Implement semantic round-trip equivalence.
10. Add English, French, and Swahili competence suites.

### Deletion gate

No ordinary response may read `predicate_answers` or `response_moves`.

### Exit criteria

- one semantic capability list is realized in all three languages using grammar rules;
- adding an action lexeme does not require adding a sentence template.

---

## 18. Phase 16 — Migration

### Work

1. Compile the v3.4.7-to-v3.5 reference map.
2. Convert:
   - foundation referents;
   - predicates;
   - ports;
   - operations;
   - rules;
   - learned schema/rule revisions;
   - knowledge;
   - aliases;
   - capabilities;
   - language lexical data.
3. Preserve provenance and revisions.
4. Emit rejected/unresolved records.
5. Add rollback.
6. Run semantic equivalence fixtures.

### Exit criteria

- no silent loss;
- no legacy refs in canonical v3.5 stores;
- old database can be migrated and restarted.

---

## 19. Phase 17 — Acceptance, metamorphic, and performance suite

### Required suites

#### Semantic composition

- property assertion/query;
- state query;
- capability query;
- negation;
- modality;
- tense/aspect;
- coordination;
- relative clause;
- embedded proposition;
- directive.

#### Cross-language

Equivalent UOL for English, French, and Swahili.

#### Paraphrase

Neighboring forms must not require new whole-sentence rules.

#### Discourse

- proposition anaphora;
- event/state anaphora;
- prior system output;
- ellipsis;
- correction;
- acknowledgement target.

#### Learning

- new alias;
- new property;
- new action;
- new affordance;
- new causal rule;
- restart hydration.

#### Safety and epistemics

- sensitive inference blocked;
- defaults qualified;
- contradictions disclosed;
- unsupported output blocked.

#### NLG

- grammar coverage;
- semantic equivalence;
- perspective;
- coordination;
- morphology;
- no added content.

#### Performance

- bounded solver;
- data lookup;
- restart;
- long-session context;
- failure under budget.

### Exit criteria

- all gates pass on a fresh database and migrated database.

---

## 20. Phase 18 — Canonical cutover

### Work

1. Point public runtime to v3.5.
2. Update web demo and CLI.
3. Archive v3.4.7 docs/data/runtime.
4. Remove stale UOL and template authorities.
5. Run repository-wide tests.
6. Generate an authority audit.
7. Publish migration and rollback instructions.

### Final release gates

- specified;
- implemented;
- wired;
- authoritative;
- verified.

All five must be true.

---

## 21. Priority implementation sequence

The first development milestone should not attempt all language phenomena.

### Vertical slice 1 — name property

Must pass:

```text
My name is Chibu.
What is my name?
Actually, my name is Chibueze.
What is my name?
```

Across restart.

### Vertical slice 2 — capability query

Must pass:

```text
What can you do?
Can you read?
Can you move physically?
What are you allowed to do?
What will you do?
```

The last three must distinguish ability, permission, embodiment, and intention.

### Vertical slice 3 — self state

Must pass:

```text
How are you?
What is your status?
Are you connected?
```

No fabricated human emotion.

### Vertical slice 4 — output discourse

Must pass:

```text
<system states a limitation>
For what?
Why?
What did you mean by that?
```

### Vertical slice 5 — acknowledgement truth

The system may not say “Understood” without a target. It must answer:

```text
Understood what?
```

from the prior acknowledgement target.

### Vertical slice 6 — three-language NLG

The name, state, and capability slices must share response UOL across English, French, and Swahili.

---

## 22. Required code removals

At completion, remove from canonical execution:

- v3.4.7 lexical fixed bindings that assert dimensions or participants;
- direct mappings of “how,” “do,” or “can” to completed predicates;
- `UOLResponsePlanner` branches by hard-coded response goal string;
- `RealizationCoordinator` per-predicate answer templates;
- generic “Could you clarify the unresolved meaning?” fallback;
- targetless “Understood.”;
- predicate-presence-only round-trip checking;
- input-only discourse commit;
- capability descriptions stored as surface text.

---

## 23. Risk register

### Risk: atom model becomes another oversized ontology

Mitigation:

- seed only operationally necessary atoms;
- require competence cases;
- use inheritance and profiles;
- do not enumerate world facts as schemas.

### Risk: grammar engine becomes a hidden template engine

Mitigation:

- rules operate on feature structures and semantic classes;
- prohibit predicate-specific full sentences;
- measure rule reuse across atoms;
- require cross-language UOL tests.

### Risk: factor graph becomes too expensive

Mitigation:

- arc consistency;
- profile-based pruning;
- typed variables;
- beam/time budgets;
- incremental discourse priors;
- partial meaning preservation.

### Risk: learning corrupts foundation

Mitigation:

- scoped candidate lifecycle;
- field provenance;
- independent competence;
- reversible promotion;
- dependency invalidation.

### Risk: referent profiles fabricate abilities

Mitigation:

- affordance is not capability;
- live capability requires evidence;
- permission/resource/risk checks remain separate.

---

## 24. Definition of a real baby CEMM

A baby CEMM is not one that knows many phrases.

It is one that can:

1. recognize reusable semantic atoms;
2. bind them to grounded referents;
3. use referent properties, states, affordances, and capabilities to constrain meaning;
4. preserve ambiguity;
5. answer typed queries from stored semantic content;
6. learn a grounded atom or lexical mapping;
7. refer to its own prior output;
8. form a new response UOL through semantic transformations;
9. realize the same meaning in multiple languages through grammar;
10. refuse unsupported output.

That is the release target.
