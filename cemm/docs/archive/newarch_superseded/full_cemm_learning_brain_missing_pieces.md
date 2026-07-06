# Full CEMM Learning Brain Missing Pieces

Status: implementation plan  
Depends on: `consolidated_architecture.md` v4.2, `core_loop_runtime.md`, `missing_runtime_implementation_plan.md`  
Audience: implementers building beyond the seed runtime loop

## 1. Short Answer

The seed core loop is now runnable.

The earlier seven systems are directionally correct, but not sufficient by
themselves.

They describe the full learning brain at the system level.

There is also a nearer hot-path interpretation layer that must be upgraded
before CEMM can produce high-quality learning traces.

The full CEMM learning brain still needs eight major systems:

```text
1. semantic hot-path interpretation upgrades
2. durable semantic object types
3. persistent lattice storage
4. graph patch validation and trust policy
5. induction engines
6. probabilistic hypothesis evaluation
7. external knowledge ingestion
8. replay/training/evaluation loop
```

These should be added behind the current seams.

They should not be stuffed into `meaning_perceptor.py`, `meaning_graph_builder.py`, or `act_resolution_planner.py`.

## 2. Missing Piece 1: Semantic Hot-Path Interpretation Upgrades

Current state:

```text
MeaningPerceptor emits groups, predicates, hypotheses, and candidate interpretations.
MeaningGraphBuilder preserves candidate sets.
ActResolutionPlanner can see ambiguity.
```

But the hot path is still too deterministic.

This matters because the learning brain can only learn from the graph traces it
receives. If the runtime trace collapses predicates, discourse relations,
anaphora, or interpretation alternatives too early, the induction engines will
learn from impoverished examples.

### 2.1 Predicate Phrase Extraction Is Too Surface-Bound

Current gap:

```text
_build_predicate_phrases creates predicates mainly from action/state atoms whose
surface strings match group tokens.
```

It misses:

```text
implicit predicates
copula relations
zero-relation constructions
multi-word predicate arguments
predicate alternatives from CandidateInterpretation
scope-marked predicates from modality and negation
```

Required files:

| File | Purpose |
|---|---|
| `cemm/kernel/predicate_phrase_extractor.py` | Replace perceptor-local predicate phrase creation with a dedicated extractor |
| `cemm/kernel/predicate_argument_aligner.py` | Align actors, objects, complements, modifiers, time, place, and clause spans |
| `cemm/kernel/implicit_predicate_detector.py` | Detect copula, apposition, zero-copula, definition, possession, and comparative predicates |

Required behavior:

```text
"a president is the leader of a country"
-> predicate: is_a(president, leader)
-> port hint: leader.domain <- country

"cold where I am"
-> predicate: state_holds(cold, user_environment)

"you can look it up"
-> predicate alternatives from candidate act interpretations
```

### 2.2 Hypotheses Need Graph Branches, Not Just Candidate Sets

Current gap:

```text
MeaningHypothesis objects become CandidateSet records, but the builder still
creates one mostly deterministic UOLGraph.
```

Missing object:

```text
AlternativeGraphBranch
InterpretationPath
```

Required files:

| File | Purpose |
|---|---|
| `cemm/types/interpretation_path.py` | Represents a coherent set of selected candidates across groups and spans |
| `cemm/types/alternative_graph_branch.py` | Represents the atoms/edges/predicates/patches belonging to one interpretation branch |
| `cemm/kernel/branching_graph_builder.py` | Forks candidate subgraphs from hypotheses without copying the whole graph unnecessarily |

Required behavior:

```text
one stable base graph
multiple lightweight branch overlays
branch-specific atoms
branch-specific edges
branch-specific predicates
branch-specific patch candidates
branch score
branch rejection reason
```

The base graph should hold shared evidence, source, permission, and stable
surface structure. Branches should hold interpretation choices.

### 2.3 Discourse Relations Must Become Graph Edges

Current gap:

```text
MeaningGroup.relation_to_parent captures labels like cause or condition, but
the builder does not promote them into UOL edges between group predicate atoms.
```

Required files:

| File | Purpose |
|---|---|
| `cemm/kernel/discourse_relation_resolver.py` | Converts group parent/child relations into predicate-level UOL edges |
| `cemm/kernel/group_predicate_index.py` | Finds the best predicate atom(s) representing each meaning group |

Required mapping:

| relation_to_parent | Preferred UOL edge |
|---|---|
| `cause` | `causes` |
| `condition` | `enables` or `prevents` depending on polarity |
| `negative_condition` | `prevents` |
| `concession` | `evaluates` plus contrast metadata |
| `temporal` | `before` / `after` |
| `complement` | `refers_to` or `modifies` |

Example:

```text
"I stayed home because it was cold"
group_0 predicate: stay_home(user)
group_1 predicate: state_holds(cold, environment)
edge: cold_state causes stay_home
```

The edge should connect predicate/process/state atoms, not only group metadata.

### 2.4 Candidate Sets Need Selection, Merge, And Rejection

Current gap:

```text
ActResolutionPlanner._resolve_candidate_sets emits obligations for candidates,
but it does not score candidate sets as competing interpretation paths.
```

Required files:

| File | Purpose |
|---|---|
| `cemm/kernel/candidate_set_resolver.py` | Scores, selects, merges, or rejects candidate interpretations |
| `cemm/kernel/interpretation_path_selector.py` | Chooses coherent candidate combinations across the whole turn |
| `cemm/kernel/planner_branch_adapter.py` | Feeds selected or unresolved branches into planning |

Required behavior:

```text
if one candidate dominates, select it and record rejected alternatives
if candidates are close and response depends on the difference, ask clarification
if candidates are close but response does not depend on the difference, answer generically
if candidates imply different safety/evidence policy, choose the stricter path
```

### 2.5 Cross-Group Anaphora Is Missing

Current gap:

```text
No mechanism resolves pronouns, ellipsis, or repeated mentions across groups.
```

Required files:

| File | Purpose |
|---|---|
| `cemm/kernel/anaphora_resolver.py` | Resolves pronouns and repeated mentions across groups |
| `cemm/kernel/entity_salience_tracker.py` | Maintains discourse salience and recency |
| `cemm/kernel/deictic_resolver.py` | Resolves I, you, here, there, this, that, now, then |

Required behavior:

```text
"I was cold, so I went inside"
second "I" resolves to first speaker/self referent

"can you tell the weather? because it's cold"
"you" resolves to CEMM/self
"it" resolves to weather/environment context, not arbitrary first group atom
```

Anaphora resolution should create `refers_to` edges and should update branch
scores when a candidate interpretation makes references more coherent.

### 2.6 Why This Layer Comes Before Induction

The induction engines need good traces.

Bad trace:

```text
groups have labels
predicate spans are broad
candidate alternatives are isolated atoms
no discourse edges
pronouns unresolved
planner emits several loose obligations
```

Good trace:

```text
each group has predicate candidates
candidate branches preserve alternatives
discourse edges connect predicates
anaphora creates refers_to edges
candidate paths are scored and selected/rejected
planner receives coherent interpretation paths
```

This hot-path layer is the bridge between the seed runtime and the full learning
brain.

## 3. Missing Piece 2: Durable Semantic Object Types

Current state:

```text
UOLAtom is a runtime atom.
ConceptRecord is an in-memory seed concept record.
GraphPatch is the durable learning boundary.
```

Missing:

```text
durable concept atoms
durable operational ports
durable predicate schemas
durable causal affordances
durable construction atoms
durable source policies
```

Required files:

| File | Purpose |
|---|---|
| `cemm/types/concept_atom.py` | Durable concept record with aliases, parents, state, support, counters, fingerprint, and stability |
| `cemm/types/operational_port.py` | Durable port constraints and evidence, separate from seed `OperationalPortSpec` |
| `cemm/types/predicate_schema.py` | Reusable predicate/process/action patterns |
| `cemm/types/causal_affordance.py` | Contextual causal prediction patterns |
| `cemm/types/construction_atom.py` | Learned form-meaning operators |
| `cemm/types/source_policy.py` | Source trust, freshness, permission, and contradiction policy |

Why this matters:

```text
UOLGraph is temporary working memory.
The learning brain needs durable compressed semantic structures.
```

Without these types, consolidation has nowhere rich enough to write long-term learning.

## 4. Missing Piece 3: Persistent Lattice Storage

Current state:

```text
ConceptLattice, ConstructionLattice, and EpisodicTraceStore are in-memory seed stores.
```

Missing:

```text
durable storage
versioned writes
rollback
schema migration
indexed lookup
fingerprint search
confidence decay
counterexample indexing
```

Required files:

| File | Purpose |
|---|---|
| `cemm/memory/persistent_lattice_store.py` | Unified durable read/write layer for concept, construction, predicate, and affordance stores |
| `cemm/memory/concept_store.py` | Persistent concept atom storage and alias lookup |
| `cemm/memory/predicate_schema_store.py` | Persistent predicate schema storage |
| `cemm/memory/causal_affordance_store.py` | Persistent affordance storage |
| `cemm/memory/source_policy_store.py` | Persistent source trust and freshness policy |
| `cemm/memory/fingerprint_index.py` | Approximate semantic fingerprint lookup |

Storage model:

```text
hot in-memory cache
durable append-only patch log
materialized lattice views
fingerprint/vector index
small episodic exemplar store
```

Important rule:

```text
Persist graph patches and compressed semantic records.
Do not persist every working UOL graph as primary memory.
```

## 5. Missing Piece 4: Graph Patch Validation And Trust Policy

Current state:

```text
ConceptConsolidator applies patches above a confidence threshold.
```

Missing:

```text
source reliability
freshness policy
permission checks
contradiction detection
counterexample tracking
multi-source support scoring
rollback and patch versioning
quarantine queue
```

Required files:

| File | Purpose |
|---|---|
| `cemm/learning/patch_validator.py` | Validates patch legality, permission, source trust, and schema compatibility |
| `cemm/learning/contradiction_detector.py` | Detects conflicts with existing concepts, predicates, and source policies |
| `cemm/learning/source_trust_scorer.py` | Scores source reliability and claim class |
| `cemm/learning/consolidation_queue.py` | Async review/merge queue for accepted, rejected, and quarantined patches |
| `cemm/learning/patch_journal.py` | Append-only patch history with rollback metadata |

Patch states:

```text
observed
candidate
accepted
quarantined
rejected
superseded
rolled_back
```

This is the safety layer that prevents CEMM from learning nonsense too confidently.

## 6. Missing Piece 5: Induction Engines

Current state:

```text
GraphPatchExtractor extracts seed patch candidates.
ConceptConsolidator can apply simple concept/construction patches.
```

Missing:

```text
concept induction
construction induction
predicate schema induction
causal affordance induction
port induction
compression and deduplication
```

Required files:

| File | Purpose |
|---|---|
| `cemm/learning/concept_inducer.py` | Merges repeated candidate concepts into stable concept atoms |
| `cemm/learning/port_inducer.py` | Learns operational ports from repeated role/filler patterns |
| `cemm/learning/predicate_schema_inducer.py` | Learns reusable predicate signatures from repeated graph fragments |
| `cemm/learning/causal_affordance_inducer.py` | Learns cause/effect affordances from repeated graph and outcome patterns |
| `cemm/learning/construction_inducer.py` | Learns form-meaning operators from utterance/graph alignments |
| `cemm/learning/semantic_compressor.py` | Collapses redundant graph fragments into compact lattice updates |

The induction engines should study graph fragments like:

```text
X is a Y
X means Y
X is the Y of Z
I am STATE
can you ACTION
if X then Y
because X, Y
```

and produce compressed objects like:

```text
concept relation
predicate schema
construction atom
port constraint
causal affordance
source policy
```

## 7. Missing Piece 6: Probabilistic Hypothesis Evaluation

Current state:

```text
MeaningPerceptor can generate MeaningHypothesis objects.
UOLGraph can preserve candidate sets and candidate subgraphs.
ActResolutionPlanner consumes ambiguity in seed form.
```

Missing:

```text
beam search over candidate subgraphs
structural ambiguity scoring
lexical ambiguity scoring
construction competition
scope resolution
cross-group anaphora resolution
confidence calibration
candidate selection/rejection feedback
```

Required files:

| File | Purpose |
|---|---|
| `cemm/kernel/hypothesis_evaluator.py` | Scores competing candidate interpretations and branch overlays |
| `cemm/kernel/subgraph_beam_search.py` | Maintains top graph interpretations without exploding search |
| `cemm/kernel/anaphora_resolver.py` | Resolves pronouns, ellipsis, and cross-group references |
| `cemm/kernel/scope_resolver.py` | Resolves negation, modality, conditionals, and subordinate clause scope |
| `cemm/kernel/confidence_calibrator.py` | Calibrates confidence against held-out traces and corrections |

This is where CEMM becomes less deterministic and more brain-like.

It should not choose one meaning too early.

It should carry plausible interpretations until planning or evidence forces a choice.

## 8. Missing Piece 7: External Knowledge Ingestion

Current state:

```text
The architecture allows source/evidence atoms and graph patches.
There is no full ingestion pipeline for Wikipedia, dictionaries, tools, or LLM teacher sources.
```

Missing:

```text
lookup planning
source extraction
definition decomposition
claim typing
freshness classification
evidence quoting
cross-source agreement scoring
LLM teacher quarantine
```

Required files:

| File | Purpose |
|---|---|
| `cemm/knowledge/lookup_planner.py` | Decides when and where to look up missing concepts |
| `cemm/knowledge/source_reader.py` | Converts external documents into source/evidence atoms |
| `cemm/knowledge/definition_decomposer.py` | Converts definitions into UOL graph patch candidates |
| `cemm/knowledge/claim_classifier.py` | Separates stable definitions from fresh/current-world claims |
| `cemm/knowledge/llm_teacher_adapter.py` | Treats LLM output as a fallible source, not durable truth |
| `cemm/knowledge/source_agreement.py` | Scores agreement and conflict across sources |

Important rule:

```text
External knowledge must enter as evidence-backed graph patches.
It must never bypass consolidation.
```

Example:

```text
dictionary says "president: elected head of a republic"
-> source atom
-> evidence atom
-> definition graph
-> concept/predicate/port patch candidates
-> validation
-> consolidation
```

## 9. Missing Piece 8: Replay, Training, And Evaluation

Current state:

```text
UOLGraph can export training examples.
Focused regression tests exist.
```

Missing:

```text
replay buffers
human correction capture
self-training from transcripts
gold graph fixtures
architecture-level metrics
learning regression tests
curriculum generator
```

Required files:

| File | Purpose |
|---|---|
| `cemm/training/replay_buffer.py` | Stores selected traces for replay and regression |
| `cemm/training/correction_ingestor.py` | Converts user corrections into graph patches and calibration data |
| `cemm/training/transcript_trainer.py` | Runs transcript batches through perception, graphing, induction, and consolidation |
| `cemm/training/gold_graph_suite.py` | Gold fixtures for expected meaning graphs |
| `cemm/training/evaluation_metrics.py` | Measures graph accuracy, compression, ambiguity handling, and repair quality |
| `cemm/training/curriculum_generator.py` | Generates increasingly complex language learning examples |

Core metrics:

| Metric | Meaning |
|---|---|
| graph fidelity | Does the working graph preserve the intended meaning? |
| ambiguity retention | Does the system preserve plausible alternatives? |
| compression ratio | Does learning reduce storage, or just archive more? |
| concept stability | Do concepts converge under repeated evidence? |
| contradiction handling | Does the system quarantine conflicts? |
| freshness correctness | Does it avoid stale current-world claims? |
| repair quality | Does it ask the right clarification question? |
| transfer | Does learning one construction help new utterances? |

## 10. Priority Build Order

### Phase 0: Fix The Semantic Hot Path

Build:

```text
predicate_phrase_extractor.py
predicate_argument_aligner.py
implicit_predicate_detector.py
interpretation_path.py
alternative_graph_branch.py
branching_graph_builder.py
discourse_relation_resolver.py
group_predicate_index.py
candidate_set_resolver.py
interpretation_path_selector.py
planner_branch_adapter.py
anaphora_resolver.py
entity_salience_tracker.py
deictic_resolver.py
```

Goal:

```text
produce high-quality working graph traces before durable induction begins
```

### Phase 1: Make Learning Durable

Build:

```text
concept_atom.py
operational_port.py
predicate_schema.py
causal_affordance.py
construction_atom.py
source_policy.py
persistent_lattice_store.py
patch_validator.py
patch_journal.py
```

Goal:

```text
graph patches become durable, versioned, inspectable learning records
```

### Phase 2: Make Learning Compressive

Build:

```text
semantic_compressor.py
concept_inducer.py
port_inducer.py
predicate_schema_inducer.py
construction_inducer.py
causal_affordance_inducer.py
```

Goal:

```text
repeated utterance graphs become compact reusable semantic machinery
```

### Phase 3: Make Interpretation Probabilistic

Build:

```text
hypothesis_evaluator.py
subgraph_beam_search.py
anaphora_resolver.py
scope_resolver.py
confidence_calibrator.py
```

Goal:

```text
the system carries multiple plausible meanings until evidence resolves them
```

### Phase 4: Make Knowledge Ingestion Safe

Build:

```text
lookup_planner.py
source_reader.py
definition_decomposer.py
claim_classifier.py
llm_teacher_adapter.py
source_agreement.py
```

Goal:

```text
CEMM learns from dictionaries, Wikipedia, tools, LLMs, and user teaching without swallowing bad facts whole
```

### Phase 5: Make It Trainable

Build:

```text
replay_buffer.py
correction_ingestor.py
transcript_trainer.py
gold_graph_suite.py
evaluation_metrics.py
curriculum_generator.py
```

Goal:

```text
the learning brain improves from transcripts, corrections, and replay instead of only hand-written seed rules
```

## 11. Minimal File Tree For The Full Learning Brain

```text
cemm/
  types/
    interpretation_path.py
    alternative_graph_branch.py
    concept_atom.py
    operational_port.py
    predicate_schema.py
    causal_affordance.py
    construction_atom.py
    source_policy.py

  memory/
    persistent_lattice_store.py
    concept_store.py
    predicate_schema_store.py
    causal_affordance_store.py
    source_policy_store.py
    fingerprint_index.py

  learning/
    patch_validator.py
    contradiction_detector.py
    source_trust_scorer.py
    consolidation_queue.py
    patch_journal.py
    semantic_compressor.py
    concept_inducer.py
    port_inducer.py
    predicate_schema_inducer.py
    causal_affordance_inducer.py
    construction_inducer.py

  kernel/
    predicate_phrase_extractor.py
    predicate_argument_aligner.py
    implicit_predicate_detector.py
    branching_graph_builder.py
    discourse_relation_resolver.py
    group_predicate_index.py
    candidate_set_resolver.py
    interpretation_path_selector.py
    planner_branch_adapter.py
    hypothesis_evaluator.py
    subgraph_beam_search.py
    anaphora_resolver.py
    entity_salience_tracker.py
    deictic_resolver.py
    scope_resolver.py
    confidence_calibrator.py

  knowledge/
    lookup_planner.py
    source_reader.py
    definition_decomposer.py
    claim_classifier.py
    llm_teacher_adapter.py
    source_agreement.py

  training/
    replay_buffer.py
    correction_ingestor.py
    transcript_trainer.py
    gold_graph_suite.py
    evaluation_metrics.py
    curriculum_generator.py
```

## 12. Architectural Guardrails

### 11.1 Do Not Expand The Primitive Set To Solve Domain Problems

Wrong:

```text
add PresidentAtom
add WeatherAtom
add LeaderAtom
```

Correct:

```text
president = ConceptAtom
weather = ConceptAtom
leader = ConceptAtom
```

### 11.2 Do Not Put Learned Knowledge In The Perceptor

Wrong:

```text
if token == "president":
    create holder/domain/current slots
```

Correct:

```text
concept = concept_lattice.resolve(atom)
ports = concept_lattice.ports_for(concept)
bindings = port_resolver.resolve_graph(graph)
```

### 11.3 Do Not Treat External Sources As Truth

Wrong:

```text
Wikipedia says X, therefore store X as fact.
```

Correct:

```text
Wikipedia says X
-> source/evidence atoms
-> graph patch candidate
-> source trust scoring
-> contradiction check
-> consolidation
```

### 11.4 Do Not Store Every Graph Forever

Wrong:

```text
retain all working graphs as permanent memory
```

Correct:

```text
retain compact semantic records
retain only sparse high-value exemplars
```

## 13. Completion Definition

The full learning brain is complete when CEMM can:

```text
read raw human-human transcripts
split utterances into meaning groups and competing interpretations
build working UOL graphs
extract repeated semantic fragments
induce concepts, ports, predicates, constructions, and affordances
validate patches against source trust and contradictions
persist compressed lattice updates
replay traces for training
improve future perception and planning from learned structures
avoid stale current-world claims without fresh evidence
ask useful repair questions when ambiguity matters
```

That is the real threshold.

Everything before that is a seed runtime, however well designed.
