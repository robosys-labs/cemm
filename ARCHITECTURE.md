# CEMM Active Architecture — Native Semantic Spine

## 1. Thesis

CEMM models a semantic cognition substrate rather than a language-first response engine. Signals provide evidence; evidence proposes semantic candidates; exact graphs settle into meaning; epistemic policy controls admission; goals and operations act on settled semantics; realization projects response semantics back into language.

The core distinction introduced by this revision is:

```text
semantic identity != semantic contribution
```

Knowing that `hii` denotes `event:greeting` is identity grounding. Knowing that `event:greeting` may participate as a greeting discourse act or an event predicate is compositional affordance. Both are necessary for learned language to become usable.

## 2. Fixed semantic kernel

The kernel retains five operators:

```text
DESIGNATION target ↔ surface/language/label evidence
TYPE        instance → class
RELATION    subject → relation → object
STATE       subject → dimension → value
EVENT       event → event type + roles
```

Everything else is represented through semantic atoms, typed roles, frame contracts, state profiles, capabilities, goals, rules and evidence.

## 3. Architectural planes

### 3.1 Evidence plane

Contains immutable observations and reversible form evidence. It may preserve multiple normalizations, spans, morphology analyses, quotations, entity proposals, references and designations.

### 3.2 Semantic authority plane

Contains atoms, five-operator applications, semantic frames, capabilities, dimensions, rules, designations, learning contracts and proof-bearing admitted knowledge.

### 3.3 Candidate cognition plane

Contains transient grounding hypotheses, semantic contributions, atomic matches, partial graphs, state factors and recurrent settling state.

### 3.4 Epistemic/world plane

Contains attributed claims, admission decisions, active world claims, state timelines and revisioned commit receipts.

### 3.5 Operation plane

Contains goals, authorized plans, adapters, idempotency/effect receipts and returned operation evidence.

### 3.6 Response plane

Contains exact Response CSIR, reference planning, language realization and semantic-equivalence verification.

## 4. Semantic Contribution ABI

A `SemanticContribution` is a transient proposal that connects one observed form unit to one way a semantic target can participate in a graph.

```text
SemanticContribution
  contribution_ref
  source unit/span refs
  semantic_ref
  semantic_kind
  contribution_kind
  affordance/frame ref
  ports provided
  ports required
  role contract
  score
  provenance
```

Closed contribution kinds:

```text
ANCHOR
PREDICATE
BINDER
REFERENCE
SCOPE
DISCOURSE
CONNECTOR
QUALIFIER
LITERAL
OPEN_VARIABLE
```

This ABI is not persisted as world truth. It is regenerated from the pinned form lattice and semantic authority each cycle.

## 5. Semantic affordance architecture

### 5.1 Defaults by semantic kind

The runtime derives a small default profile set from the target atom kind. It never examines the word surface or parses the semantic ref name.

### 5.2 Sparse explicit frames

A target may link to reviewed frame atoms:

```text
target
  -- rel:has_semantic_frame -->
semantic_frame
```

Frame metadata defines contribution kind, ports, role expectations, kernel lowering hint, proposition-taking behaviour, discourse behaviour and bounded score adjustment.

Explicit frames may augment defaults. They may replace defaults only when `replace_defaults=true` is reviewed and validation proves at least one usable profile remains.

### 5.3 Event-capability separation

Action/event identity is not the same as capability identity.

```text
can + event:learn
→ capability modality over learning event
→ assess cap:learn through semantic dependency
```

The surface `learn` should not be permanently designated with equal priority to both `event:learn` and `cap:learn` merely to answer capability questions.

## 6. Form and semantic grounding

```text
raw text
→ reversible normalization
→ token/morphology/span alternatives
→ reference and designation candidates
→ target affordance expansion
→ grounding hypotheses containing semantic contributions
→ atomic graph candidates
```

A newly committed designation becomes available after authority reload. No language-pack rebuild is required for ordinary synonym acquisition.

Closed-class forms remain language-pack features. Open-class meaning is primarily designation-driven.

## 7. Composition

Atomic graph schemas express semantic-role and port compatibility, not phrase templates.

A candidate is executable only when:

- all required roles are satisfied;
- all required contribution ports are provided;
- operator and filler kinds validate;
- state/domain constraints pass;
- every input unit is consumed or typed as residual;
- no critical residual remains;
- coverage and provenance receipts verify.

Dynamic ports from semantic contributions are merged with schema-declared ports.

## 8. Predication

Copular forms provide a binder, not a fixed operator.

```text
subject + binder + concept predicate      → TYPE
subject + binder + state value/dimension  → STATE
subject + binder + label property/value   → DESIGNATION
subject + binder + relation phrase        → RELATION
subject + binder + event/process phrase   → EVENT/process state where licensed
```

The binder never chooses among these alone.

## 9. Polysemy and settling

One surface can expand across:

- multiple designation targets;
- multiple explicit/default affordances per target;
- multiple reference/coreference hypotheses;
- multiple graph structures;
- multiple discourse scopes.

Exact kind and role incompatibility clamp candidates. State, context, discourse and usage evidence adjust bounded scores. A top candidate is selected only through an explicit convergence/margin rule.

## 10. Native learning architecture

Learning is a semantic capability and goal-directed operation, not a hidden parser mode.

A `LearningPlan` binds:

```text
learning contract
source QueryResult and exact QueryStructure
pinned authority generation
semantic goal
required capability
commit operator
unresolved surface
expected target kinds
answer contract
provenance and expiry
```

Designation resolution uses:

```text
contract: contract:designation_learning
goal:     goal:acquire_designation
capability: cap:learn
commit:   op:designation
```

The plan does not execute merely because a word equivalent to “mean” or “learn” was observed. Exact query/claim/directive structure determines the operation.

## 11. Dialogue continuation

One session may contain at most one bounded pending learning obligation. It is created only after an exact unanswered query and a verified learning-request response. The plan identity includes the authority generation that licensed its contract and frame graph. A later answer must resolve the same obligation, generation and expected answer contract. Authority reload invalidates the obligation; consumption occurs only after a successful Stage-13 commit receipt.

## 12. Proposition architecture

Proposition-taking frames can bind an embedded graph or, where decomposition is unavailable, a typed literal/open proposition.

Examples:

```text
want(actor=self, proposition=know(...))
know(subject=self, object=designation(...))
say(actor=user, content=claim(...), addressee=self)
learn(actor=self, content=designation(...))
```

Embedding uses the same five-operator substrate and application references. It does not introduce opaque intent payloads.

## 13. Data and persistence

Persistent authority includes frame and learning-contract atoms, but not cycle-local contribution instances. Designations remain ordinary facts. Internal refs never automatically become language designations.

Revisions remain separated:

```text
world_revision
observation_revision
discourse_revision
effect_revision
```

## 14. Runtime bounds

Recommended initial bounds:

```text
designation candidates per span       8
affordance profiles per target        4
grounding hypotheses                 16
atomic matches                       32
semantic candidates                  48
proposition nesting depth             6
pending learning obligations          1
operation re-entry                     1
```

Bounds are configuration and receipt data, not silent truncation.

## 15. Activation invariants

Startup fails if:

- ABI versions disagree;
- a frame link targets a missing/malformed frame;
- a frame has an unsupported contribution kind;
- dynamic ports are not bounded sequences;
- a learning contract references a missing operator/capability/goal/answer contract;
- a designation target has no valid bounded affordance;
- internal refs were auto-published as user-visible designations;
- generated authority or packs differ from checked-in artifacts.


Realization grammar tokens are output-only and must never be fed back into pre-core form classification.
