# CEMM Minimal Semantic Brain MVP v3 — Consolidated Architecture

**Status:** executable architecture proof / migration reference, not a replacement for canonical CEMM CSIR or the Stage 0–22 runtime.

**Canonical repository sources aligned in this document:**

- `ARCHITECTURE.md` — CEMM v3.5.1 Grounded Semantic Brain Architecture, SHA `a9f3b6712f7253422cd5b5f183db29860dd16232`.
- `CORE_LOOP.md` — canonical Stage 0–22 logical cognitive contract, SHA `118332e54d84d6ee98f7780c2fb6ab7fc98b0bd9`.
- `RUNTIME_PLAN.md` — canonical concrete runtime contract, SHA `197360cf0d7ba8b47303b2bf69570d07a592e2c8`.

The v3 MVP incorporates the architectural findings from the earlier MVP iterations while changing one important direction:

> **Exact semantics remain authoritative, but neural computation should operate over a compact active semantic workspace rather than repeatedly translating every generated sentence back through the entire understanding pipeline.**

The MVP therefore demonstrates a small hybrid semantic brain:

```text
exact meaning DB / CSIR-like facts
        ↓
relevance retrieval + semantic closure
        ↓
ACTIVE SEMANTIC WORKSPACE
        ↓
Transformer ranking / learned language projection
        ↓
exact semantic decisions / state transitions
        ↓
Response meaning
        ↓
semantic-pointer NLG
        ↓
cheap proof-carrying verification
        ↓
emission
```

Independent full text round-trip remains useful for training, release competence, novelty, high-risk output, and audit. It is **not** the mandatory per-message runtime path.

---

# 1. Architecture thesis

CEMM is not a language model with a semantic database attached.

It is a semantic cognition architecture in which:

```text
LANGUAGE / VISION / SOUND / TELEMETRY
                │
                ▼
             EVIDENCE
                │
                ▼
      EXACT SEMANTIC CANDIDATES
                │
                ▼
        DYNAMIC SETTLING / RANKING
                │
                ▼
      GROUNDED WORLD + SELF STATE
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
    QUERY     LEARN     SIMULATE
      │         │         │
      └─────────┼─────────┘
                ▼
              GOAL
                │
                ▼
          RESPONSE MEANING
                │
                ▼
     LANGUAGE / ACTION / MODALITY
```

The invariant is:

> **Neural models may rank, activate, compose, retrieve, and realize meaning. They do not become semantic authority.**

Semantic truth and durable identity remain exact, typed, provenance-bearing, versioned structures.

---

# 2. Relationship to canonical CEMM architecture

The canonical architecture defines one cycle-time cognitive state containing, among other things:

```text
CognitiveState_t
  authority_snapshot
  read_generation
  working_csir
  activation_field
  grounded_belief_state
  epistemic_graph
  causal_model
  discourse_common_ground
  goal_impact_field
  frontier_graph
  proof_lineage_graph
  cycle_workspace
```

v3 does **not** introduce a competing cognitive state.

It interprets the MVP's `SemanticWorkspace` as a compact executable subset/projection of canonical:

```text
CycleWorkspace
+ WorkingCSIR
+ ActivationField
+ GroundedBeliefState
+ SelfRuntimeView
+ DiscourseCommonGround
```

for the current question/observation.

The production relationship should be:

```text
CANONICAL COGNITIVE STATE
        │
        ├── exact CSIR candidates
        ├── grounded beliefs
        ├── self/runtime state
        ├── discourse state
        ├── recent transitions
        ├── relevant rules/proofs
        │
        ▼
SEMANTIC WORKSPACE PROJECTION
        │
        ▼
NEURAL DYNAMICS / RANKING
        │
        ▼
results return to canonical stage artifacts
```

The workspace is therefore an optimization and cognition surface, not a new source of truth.

---

# 3. Updated overall CEMM architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│ PROCESS / RELEASE LIFETIME                                           │
│                                                                      │
│ RuntimeAttestation · AuthorityGeneration · ImmutableBootStore        │
│ RuntimeServiceRegistry · pinned language/model artifacts             │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ exact generation pin
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ SESSION / CONTEXT LIFETIME                                           │
│                                                                      │
│ SessionContext · ParticipantFrame · ConversationScope                │
│ SelfSemanticState · DiscourseCommonGround · Retention/Permission     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ CYCLE                                                                │
│                                                                      │
│  raw multimodal observation                                         │
│            ↓                                                         │
│  evidence lattice                                                    │
│            ↓                                                         │
│  referent / identity candidates                                     │
│            ↓                                                         │
│  entitled state-space projection                                    │
│            ↓                                                         │
│  exact CSIR candidate compilation                                   │
│            ↓                                                         │
│  sparse semantic retrieval                                          │
│            ↓                                                         │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ ACTIVE SEMANTIC WORKSPACE                                     │   │
│  │                                                               │   │
│  │ relevant exact/derived facts                                  │   │
│  │ self state                                                    │   │
│  │ recent state transitions                                      │   │
│  │ discourse/referent focus                                      │   │
│  │ query/goal slots                                               │   │
│  │ proof/rule dependencies                                        │   │
│  └──────────────────────┬────────────────────────────────────────┘   │
│                         ↓                                            │
│                neural semantic dynamics                              │
│            rank · attend · inhibit · compose                         │
│                         ↓                                            │
│            stable / partial semantic result                          │
│                         ↓                                            │
│   epistemic placement · query · learning · simulation                │
│                         ↓                                            │
│        authorized exact commit at explicit boundary                  │
│                         ↓                                            │
│          capability / impact / significance / goal                   │
│                         ↓                                            │
│                 Response CSIR semantics                              │
│                         ↓                                            │
│               semantic-pointer realizer                              │
│                         ↓                                            │
│                proof-carrying verification                           │
│                         ↓                                            │
│                    authorized emission                               │
│                         ↓                                            │
│             output discourse/common-ground update                    │
└──────────────────────────────────────────────────────────────────────┘
```

The MVP compresses many of these logical stages into a few Python services. Full CEMM should preserve the Stage 0–22 boundaries and artifact contracts.

---

# 4. Exact semantic plane vs dynamic semantic plane

## 4.1 Exact semantic plane

Authoritative structures include:

```text
CSIR / exact applications
exact referent identities
operator/predicate definitions
role/binding constraints
state dimensions and domains
claims and epistemic stance
semantic rules/mechanisms
evidence/provenance
proof lineage
authority generation pins
language/model artifact pins
```

In the MVP these are compressed into SQLite records and five demonstration operators.

In production they must compile into canonical CSIR:

```text
TERM
VARIABLE
APPLICATION
BINDING
QUALIFIER
SCOPE_EMBEDDING
COORDINATION
PROOF_LINK
```

## 4.2 Dynamic semantic plane

Dynamic state includes:

```text
activation
relevance
uncertainty
salience
recency
query relevance
self relevance
causal/goal relevance
prediction error
competition/inhibition
workspace membership
```

The MVP demonstrates this through a bounded `SemanticWorkspace` and a small Transformer ranker.

Production Stage 6–7 should perform recurrent typed propagation and attractor stabilization over exact CSIR candidates, not merely one-pass ranking.

## 4.3 Hard boundary

```text
neural score ≠ semantic truth
high salience ≠ identity commitment
frequent label ≠ identity
co-activation ≠ equivalence
repeated evidence ≠ causal proof
```

---

# 5. CSIR and the MVP's compressed operator algebra

The MVP deliberately uses five universal operator shapes:

```text
op:designation
op:type
op:relation
op:state
op:event
```

These are **not proposed replacements for CSIR**.

They are a compact executable proof layer that maps into CSIR applications and bindings.

Conceptually:

```text
op:type(instance, class)
        ↓
APPLICATION(type_assertion)
BIND instance → TERM
BIND class    → TERM

op:relation(subject, relation, object)
        ↓
APPLICATION(relation_assertion)
BIND subject  → TERM
BIND relation → TERM
BIND object   → TERM

op:state(subject, dimension, value)
        ↓
APPLICATION(state_assignment)
BIND subject   → TERM
BIND dimension → TERM
BIND value     → TERM / typed value
QUALIFY time/context/source where applicable
```

Production migration rule:

> Domain knowledge may add atoms, definitions, rules, state dimensions, and learned parameters. It must not create a parallel semantic kernel merely because a new concept is learned.

---

# 6. Universal semantic data architecture

```text
ATOM / EXACT IDENTITY
        │
        ├── entity / participant
        ├── concept / type
        ├── relation type
        ├── state dimension
        ├── state value
        ├── event type
        ├── time/context
        ├── goal / operational concept
        └── language designation target

APPLICATION
        │
        └── universal operator + typed role bindings

CLAIM
        │
        ├── support / deny
        ├── confidence
        ├── authority status
        ├── validity interval
        └── source observation

RULE / MECHANISM
        │
        ├── definition
        ├── entailment
        ├── default
        └── causal

DESIGNATION
        │
        ├── target identity
        ├── surface
        ├── language / script
        ├── label type
        ├── semantic context
        ├── reviewed prior
        └── preference

DYNAMIC RANKING
        ├── label use count
        ├── discourse salience
        ├── recency
        └── workspace activation
```

Only exact semantic structures belong to semantic authority.

Dynamic ranking statistics must not alter exact semantic identity hashes.

---

# 7. Identity and multilingual designation architecture

## 7.1 Identity is not a name

```text
entity:opaque_123
    │
    ├── Donald Trump
    ├── Donald J. Trump
    ├── Trump
    └── localized / transliterated forms
```

All labels point toward one identity.

Two identities may share one surface:

```text
"Alex Kim"
   ├── entity:A
   └── entity:B
```

A resolver must produce candidate identities and preserve ambiguity when the score margin is insufficient.

## 7.2 Contextual labels

The same semantic value may realize differently by role/context:

```text
quantity:2
   ├── "two"      when count
   └── "second"   when rank
```

Likewise a type may have:

```text
concept:doctor
   ├── "doctor"    input/lexical designation
   └── "a doctor"  predicative realization context
```

This prevents grammar-specific article hacks in the kernel.

## 7.3 Ranking

Candidate score may use:

```text
reviewed prior
language/script match
context match
usage frequency
discourse salience
recency
semantic type compatibility
session focus
```

But ranking only proposes identity. Exact commitment still requires sufficient evidence/margin.

---

# 8. Self identity and self-aware semantic state

`self` is a normal grounded participant/referent with operational and cognitive state dimensions.

A good model is orthogonal rather than one overloaded `response_state`:

```text
self
├── interpretation_state
│   ├── resolved
│   └── unresolved
├── epistemic_state
│   ├── sufficient
│   ├── insufficient
│   └── uncertain
├── response_state
│   ├── ready
│   ├── processing
│   ├── confused
│   └── clarification_needed
├── operation_state
├── capability state
├── attention target
├── confidence
└── session-scoped transition history
```

Example:

```text
before:
  self.interpretation_state = resolved
  self.response_state       = processing

observation:
  two close incompatible interpretations survive

transition:
  self.interpretation_state = unresolved
  self.response_state       = confused

cause:
  ambiguity_frontier:F7
```

This semantic state can directly drive communication goals.

No special string handler is required for "I am confused" or "I need clarification".

The v3 MVP stores self state session-locally and converts it into ordinary semantic state slots for the workspace.

Production mapping:

```text
SessionContext / ParticipantFrame
        +
SelfRuntimeView
        +
CycleWorkspace
```

Self/session state is not automatically durable global world truth.

---

# 9. State transitions and session deltas

The Transformer should usually attend more strongly to **what changed** than to every historical fact.

Per-turn delta:

```text
new evidence
newly resolved referents
changed entity states
new events
new contradictions
new frontiers
new goals
self-state transitions
operation results
```

Example:

```text
Turn N:
  "My mother in-law arrived today."

Delta:
  + mother_in_law_of(M, self)
  + arrival(E, actor=M, time=today)
  + discourse salience(M)

Turn N+1:
  "Am I married?"

Workspace retrieval favors:
  self
  marital_status
  mother_in_law_of
  mother-in-law decomposition rule
  partner→spouse hierarchy
  spouse→married state effect
  recent delta
```

This is more efficient than re-attending to the whole semantic store.

---

# 10. Active Semantic Workspace

The workspace is the core v3 architectural change.

```text
LONG-TERM EXACT STORE
      │
      │ indexed retrieval / semantic match / proof dependency
      ▼
CANDIDATE SEMANTIC SLOTS
      │
      │ relevance scoring
      ▼
TOP-K ACTIVE WORKSPACE
      │
      ▼
Transformer attention / ranking
```

A generic slot contains conceptually:

```text
SemanticSlot
  exact_ref
  subject/referent
  operator/predicate
  role_bindings
  qualifiers
  source/provenance
  confidence
  epistemic status
  temporal scope

Dynamic features
  query relevance
  self relevance
  discourse salience
  recency
  derived/exact status
  activation
```

v3 currently uses six compact domain-independent features and top-K=24 by default.

Production can extend features without changing semantic identity.

## 10.1 Performance rule

Never feed the entire semantic database into a Transformer.

Preferred path:

```text
millions of exact facts
      ↓ indexed retrieval / ANN / graph lookup
hundreds of candidate slots
      ↓ ranking
32–256 active slots
      ↓ Transformer
```

This aligns with the canonical runtime requirement that hot scans be indexed/bounded/cached/budgeted.

---

# 11. Neural architecture: what Transformers should and should not do

## 11.1 Good uses

Transformers are appropriate for:

```text
language evidence interpretation
candidate program/rule ranking
semantic workspace attention
referent/coreference scoring
document/clause composition
ambiguity ranking
response-content selection
surface-plan selection
morphology/linearization
```

## 11.2 Bad uses

A Transformer output alone must not:

```text
mint semantic authority
commit identity by score alone
create arbitrary ontology kinds
turn hypothesis into actual-world truth
turn causal prediction into observation
override exact type/role constraints
silently mutate durable state
```

## 11.3 MVP neural simplification

For reliability/performance, v3 trains classifiers over learned exact program classes and realization-plan classes rather than autoregressively generating long symbolic programs.

```text
surface evidence
    ↓
Transformer classifier
    ↓
ranked known semantic program class
    ↓
exact filler grounding
    ↓
exact compiler validation
```

For clauses/documents:

```text
clause 1 → short learned program
clause 2 → short learned program
...
       ↓
global referent/coreference map
       ↓
exact structural composition
```

This avoids memorizing long document-level symbolic strings.

Production may use richer generative structured decoders, provided exact Stage-5 closure/validation remains mandatory.

---

# 12. Trainable language acquisition architecture

Foundational meaning data and language competence are separated.

`knowledge/base.json` contains semantic authority.

It does **not** contain hand-authored `language_examples` or `realization_examples` sections.

Language training source contains:

```text
surface text
mention anchors / grounded references
structured universal semantics
```

The trainer derives:

```text
delexicalized interpretation examples
semantic program classes
pointerized realization examples
grammar vocabulary
language-pack hash
```

Pipeline:

```text
reviewed / grounded teaching corpus
        ↓
trainer.py
        ↓
compiled language pack
        ├── interpretation program classes
        ├── realization plan classes
        ├── grammar vocabulary
        └── exact artifact hash
```

The same trainer compiles English and Spanish packs against shared semantics.

## 12.1 Incremental learning target

A future trainer should support:

```text
new explanatory document
        ↓
known lexical/referent anchors
        ↓
existing codec proposes semantic graph/rule
        ↓
exact validation
        ↓
competence + counterexamples
        ↓
promotion into new authority generation
        ↓
new NLU/NLG training pairs
```

The MVP does not yet implement autonomous open-domain semantic rule induction from arbitrary prose.

---

# 13. Document composition and coreference

v3 uses clause-compositional interpretation.

```text
DOCUMENT
   ↓
mention grounding
   ↓
discourse/coreference candidates
   ↓
split into semantic clauses
   ↓
canonicalize each clause placeholders locally
   ↓
Transformer selects short reusable clause program
   ↓
verify exact role/type constraints
   ↓
map local placeholders back to global referents
   ↓
compose document graph
```

Example:

```text
Ada is a doctor. She arrived today.
```

becomes:

```text
type(Ada, doctor)
arrival(event, actor=Ada, time=today)
```

with `she` grounded to the same referent.

This is still an MVP of document semantics, not a general open-domain discourse parser.

---

# 14. Anti-bloat architecture

## 14.1 Permanent memory stores causes/knowledge, not every consequence

```text
DURABLE
  observations
  admitted claims
  definitions
  promoted rules
  exact state
  provenance

TRANSIENT
  derived closure
  candidate interpretations
  existential witnesses
  workspace activation
  simulation branches
  temporary proofs
```

Inference normally creates an ephemeral bounded closure.

Repeated questioning must not materialize all derived facts into permanent storage.

## 14.2 Generic rule factoring

Avoid:

```text
mother → female
mother → human
mother → living
wife → female
wife → human
wife → living
...
```

Prefer:

```text
participant_type(mother_of, female)
female IS_A human
human IS_A living_entity

ONE generic participant-type rule
ONE generic type-transitivity rule
```

Avoid separate schema for every relation.

Prefer:

```text
relation hierarchy facts
+ one generic subrelation inheritance rule
```

## 14.3 Growth rule

```text
new vocabulary     → designation/lexical evidence
new entity         → exact referent atom
new fact           → existing operator/application
new hierarchy      → relation/type facts
new consequence    → generic effect relation where possible
new composition    → compact semantic rule
new causal insight → causal mechanism/rule
new domain         ≠ new kernel schema
```

---

# 15. Family reasoning proof

Learned semantic knowledge:

```text
mother_in_law subrelation family_relative
partner       subrelation spouse
wife          subrelation spouse
husband       subrelation spouse

mother_of subject_type female
wife       subject_type female
husband    subject_type male

female IS_A human
male   IS_A human
human  IS_A living_entity

spouse implies both participants' marital_status = married
```

One irreducibly compositional definition:

```text
mother_in_law_of(M, Person)
    ⇒ exists Partner:
         mother_of(M, Partner)
         partner_of(Partner, Person)
```

Observation:

```text
My mother in-law arrived today.
```

Durable observation meaning:

```text
mother_in_law_of(M, self)
arrival(E, actor=M, time=today)
```

Question:

```text
Am I married?
```

Ephemeral proof:

```text
mother_in_law_of(M,self)
        ↓ definition
mother_of(M,P)
partner_of(P,self)
        ↓ subrelation
spouse_of(P,self)
        ↓ generic relation→state effect
self.marital_status = married
        ↓
YES
```

No `MotherInLawSchema`, `MarriageSchema`, or phrase-specific Python branch is added.

---

# 16. Query and epistemic architecture

Queries are semantic restrictions/projections, not answer templates.

Runtime result classes:

```text
SUPPORTED
CONTRADICTED
UNKNOWN
CONFLICT
INCOMPLETE / FRONTIER
```

Important distinction:

```text
not found ≠ false
budget exhausted ≠ unknown
contradiction ≠ uncertainty
reported fact ≠ actual-world fact
```

The MVP keeps support/deny claims separate and reports inference exhaustion as a frontier.

Full CEMM should preserve source/context/admission classes from canonical runtime policy.

---

# 17. Operational meaning and grounded response vocabulary

CEMM must not emit meaningful concepts it cannot itself represent.

Therefore operational concepts such as:

```text
self
observation
evidence
information
proposition
meaning
knowledge
uncertainty
consistency
conflict
query
response
goal
capability
unknown
```

are ordinary semantic atoms with definitions/relations.

Examples:

```text
evidence IS_A information
conflict IS_A state
meaning IS_A structured_semantic_content
```

Thus the system can both use and answer questions about these concepts:

```text
What is evidence?
→ Evidence is information.

What is conflict?
→ Conflict is a state.

What is meaning?
→ Meaning is structured semantic content.
```

No opaque `resp:conflict` semantic shortcut exists.

---

# 18. Response architecture in v3

Canonical response flow remains:

```text
query / goal / epistemic result
        ↓
communication goal
        ↓
Response CSIR semantics
        ↓
discourse/clause plan
        ↓
semantic-pointer realization
        ↓
cheap proof-carrying semantic verification
        ↓
policy-driven independent round-trip if needed
        ↓
emission
```

## 18.1 Why mandatory per-message re-encoding was removed

Earlier MVP iterations did:

```text
meaning → text → full NL understanding pipeline → meaning → compare
```

for every output.

That was safe but inefficient and unnecessarily forced a symbolic adversarial pattern into a neural architecture.

Canonical runtime explicitly permits cheap proof verification for normal emissions and reserves full independent round-trip for novelty/risk/audit/release competence.

v3 follows that model.

## 18.2 Semantic-pointer NLG

A response realization plan contains exact semantic pointers.

Example:

```text
semantic state:
  subject   = concept:evidence
  dimension = dim:consistency
  value     = value:conflicting

surface plan learned by Transformer:
  @subject is @value .
```

Pointer resolution:

```text
@subject → "Evidence"
@value   → "conflicting"
```

Proof records:

```text
input semantic plan
selected learned transform class
language-pack pin
all semantic pointers
resolved designations
coverage
unknown placeholders
grammar-token authorization
internal-ID leakage check
```

The Transformer chooses wording structure; semantic content remains exact.

## 18.3 Full round-trip policy

Use independent round-trip for:

```text
training and evaluation
release competence tests
novel/out-of-distribution realization
high-risk claims/actions
policy-selected audit/debug
```

Not necessarily every ordinary conversational sentence.

---

# 19. Authority and runtime generation architecture

v3 explicitly separates immutable authority from mutable state.

```text
RuntimeAttestation
   └── startup/reload verification

AuthorityGeneration
   ├── semantic kernel/operator contracts
   ├── reviewed/promoted definitions/rules
   ├── language pack artifact hash
   └── model/parameter artifacts

Mutable state generations
   ├── WorldRevision
   ├── DiscourseRevision
   ├── RuntimeObservationRevision
   ├── AuditRevision
   └── EffectJournalRevision
```

The MVP exposes a runtime attestation with:

```text
authority_generation
authority_generation_hash
language_pack_hash
read_generation
```

Learning a new session fact advances mutable/read generation but must not retroactively change the pinned authority-generation hash.

This mirrors canonical runtime architecture.

---

# 20. Stage 0–22 mapping

The MVP is deliberately compact. The following table shows conceptual alignment, not one-to-one class ownership.

| Canonical stage | Full responsibility | v3 MVP mapping | Status |
|---|---|---|---|
| 0 Orient/pin | authority/read generation, participant/context, budgets | `Runtime.runtime_attestation`, session self, store generation | Partial |
| 1 Observe | source-attributed multimodal evidence | language observations | Partial: text only |
| 2 Encode evidence | language/sensor evidence lattice | generated language pack + mention/designation evidence | Partial |
| 3 Ground referents | identity/coreference solving | designation resolver, discourse salience, pronoun/reference evidence | Implemented MVP subset |
| 4 Project state spaces | entitled dimensions/relations/capabilities | exact state/type/relation retrieval | Partial |
| 5 Compile CSIR | exact candidate compiler/closure proof | universal program parser + exact role/filler validation | Implemented compressed subset |
| 6 Recurrent dynamics | typed recurrent factor/activation graph | semantic workspace Transformer ranking | Partial; not recurrent attractor dynamics |
| 7 Stabilize attractors | stable/partial/alternatives/contradictions | classifier agreement, margins, frontiers | Partial |
| 8 Build structures | propositions/events/queries/discourse | fact/query/event packets | Partial |
| 9 Epistemic/world | admission/context/belief | support/deny + authority status | Partial |
| 10 Query/explain | grounded matches + proof | bounded inference/match/proof extraction | Implemented subset |
| 11 Learning | typed frontiers/candidate induction | frontiers + trainer packs + provisional learned facts | Partial |
| 12 Simulate | causal/counterfactual preview | causal rules kept nonactual | Representation only |
| 13 Commit | authorized CAS/world/learning commits | SQLite explicit generation commit | Partial |
| 14 Impact/significance | capability/impact/affect | not implemented | Gap |
| 15 Goals | obligations/goal arbitration | data-driven response goal mapping | Minimal subset |
| 16 Act | plan/authorize/execute | not implemented | Gap |
| 17 Outcome/re-entry | operation observation/re-entry | not implemented | Gap |
| 18 Response CSIR | semantic response construction | `ResponsePlanner` ordinary semantic facts/goals | Implemented compressed subset |
| 19 Realize | plan/surface/proof | trained surface-plan classifier + pointer realizer | Implemented MVP subset |
| 20 Verify/emit | semantic preservation + authorization | cheap pointer/transform proof | Implemented MVP subset |
| 21 Common ground | output discourse commit | minimal discourse salience only | Partial |
| 22 Finalize | consolidation/invalidation/replay/promotion | deterministic generation hashes; no full lifecycle | Partial |

---

# 21. Persistence architecture

The canonical runtime rule is preserved conceptually:

> `CycleWorkspace` owns transient cognition; persistence is the exception.

MVP persistence:

```text
persistent:
  exact atoms/designations
  observations
  applications/bindings
  admitted/provisional claims
  reviewed/promoted rules
  generations
  frontiers

dynamic/session:
  self state
  self transitions
  semantic workspace
  neural activations/rankings
  derived inference closure
  temporary existential witnesses
```

A repeated query must not grow durable semantic storage merely because inference ran again.

---

# 22. Multilingual architecture

Shared semantic authority:

```text
exact atom / fact / rule graph
```

Separate trainable language projections:

```text
English pack
Spanish pack
future language pack N
```

Each package contains language-specific evidence/grammar/realization competence but not duplicate world truth.

Example:

```text
mother in-law
suegra
        ↓
rel:mother_in_law
```

The same family rules and self/world state answer both:

```text
Am I married?
¿Estoy casado?
```

No English ontology and Spanish ontology are created.

---

# 23. Anti-bloat invariants

## A. One canonical semantic substrate

MVP operator shortcuts compile conceptually to CSIR. Do not grow a second ontology.

## B. Domain import cannot expand the kernel

Learning family, medicine, finance, physics, or politics should add semantic data/rules, not new Python schema classes.

## C. Inference closure is transient by default

Persist source knowledge; derive consequences when needed. Promote/materialize only under explicit policy.

## D. Neural output cannot mint authority

Model proposals require exact role/type/authority validation.

## E. Identity never derives from labels alone

Names are evidence/designations. Same-name entities remain distinct.

## F. State domains are reusable

New state values/dimensions use typed state contracts rather than new object schemas.

## G. Causal, hypothetical, and actual contexts remain distinct

Simulation never becomes world truth by convenience.

## H. Workspace is bounded

No unbounded full-store Transformer attention.

## I. Response semantics precede language

A generated meaningful content token must trace to an exact semantic pointer or authorized semantic transformation.

## J. Expensive verification is policy-driven

Cheap proof every emission; full independent round-trip when risk/novelty/audit requires it.

---

# 24. Performance architecture

Recommended production hot path:

```text
exact semantic DB / graph
      │
      ├── typed indexes
      ├── ref→kind cache
      ├── generation-aware caches
      ├── vector/ANN retrieval where appropriate
      └── proof/rule dependency indexes
      │
      ▼
100s candidate facts
      │
      ▼
rank to 32–256 workspace slots
      │
      ▼
shared semantic Transformer
      │
      ├── interpretation head
      ├── grounding/coreference head
      ├── activation/settling head
      ├── state-update/goal head
      └── NLG decoder / pointer head
```

The current MVP uses small separate Transformer classifiers for simplicity. A production architecture can consolidate them into one shared semantic Transformer with multiple heads to reduce duplicated parameters and improve cross-task learning.

---

# 25. What v3 MVP concretely covers

Implemented/proven in executable form:

```text
✓ exact opaque identities separate from names
✓ multilingual/contextual designations
✓ same-name ambiguity preservation
✓ Unicode-aware label resolution
✓ five stable domain-independent semantic operators
✓ exact typed role/filler validation
✓ deterministic semantic identity/generation hashing
✓ authority-generation pin separate from mutable learning generation
✓ observations separate from claims
✓ support vs deny vs unknown vs conflict
✓ explicit inference-incomplete frontier
✓ bounded ephemeral rule closure
✓ reviewed/promoted rule authority gating
✓ no causal-rule auto-assertion as actual truth
✓ generic family inference without family-specific Python code
✓ schema count does not grow with family import
✓ session self state + transitions
✓ bounded semantic workspace with Transformer ranking
✓ language packs generated by a trainer, not embedded in base meaning DB
✓ English/Spanish packs share semantic authority
✓ clause-compositional multi-sentence/coreference demo
✓ response goals grounded as ordinary meaning
✓ operational words such as evidence/conflict/meaning are queryable concepts
✓ semantic-pointer NLG
✓ learned transform-class authorization for NLG
✓ no mandatory output round-trip
✓ internal exact IDs blocked from user-visible output
✓ repeated observations remain distinct evidence occurrences
✓ repeated reasoning does not bloat durable semantic storage
✓ unsupported multi-valued role semantics fail explicitly rather than silently
```

Kernel + trainer remain below 1,000 source lines combined.

---

# 26. Critical gaps not covered by the MVP

## 26.1 Full CSIR expressiveness

Missing or compressed:

```text
variables as first-class query structures
coordination/set-valued bindings
scope embedding
quantification
ordered multi-valued roles
modality/permission/evidence qualifiers at full fidelity
canonical CSIR normalization/equivalence proofs
```

Production must use the existing CSIR kernel rather than extending the five MVP operators indefinitely.

## 26.2 True recurrent Stage 6–7 semantic dynamics

The workspace ranker is not yet:

```text
recurrent excitation/inhibition
multi-hypothesis factor graph
attractor clustering
certified convergence
partial stable graph posterior
```

This remains a major production gap.

## 26.3 Open-domain semantic rule induction

The system consumes already structured semantic teaching data/rules.

It does not yet reliably transform arbitrary prose such as:

```text
A mother in-law is the mother of a partner.
```

into a promoted quantified semantic rule without reviewed grounding/competence evidence.

## 26.4 Full learning promotion lifecycle

Missing:

```text
counterexample gathering
competence thresholds
review workflow
immutable artifact publication
new AuthorityGeneration switch
restart/replay/invalidation
```

## 26.5 Rich multimodal workspace

Architecture supports multimodal slots conceptually, but executable MVP only consumes text.

## 26.6 Entitled state-space engine

MVP has typed dimensions and exclusivity but not the full canonical state-domain algebra:

```text
continuous/unit-aware
vectors/manifolds
probabilistic distributions
set/process-valued state
facet entitlement closure
```

## 26.7 Causal simulation/counterfactuals

Causal rules are separated from actual truth, but Stage-12 structural simulation, intervention, abduction, isolated counterfactual contexts, and CausalProof DAGs are not implemented.

## 26.8 Capability / significance / goal / action stack

Only minimal response-goal mapping exists.

Stages 14–17 remain largely outside the MVP.

## 26.9 Full discourse/common ground

Missing robust:

```text
open questions
clarification targets
commitments
corrections/retractions
prior output semantics
common-ground proposal/acceptance lifecycle
```

## 26.10 Referring-expression generation

The realizer can use known designations but does not fully synthesize context-sensitive references such as:

```text
she
his mother-in-law
the woman who arrived today
the previously mentioned server
```

Unknown internal IDs are blocked rather than exposed.

## 26.11 N-best semantic realization

Current NLG selects one learned surface-plan class.

Production should generate/rank multiple semantically authorized candidates with style/register/audience constraints.

## 26.12 Production authority/release security

MVP hashes authority and language packs but does not implement full signing, activation manifests, capability tokens, release attestation verification, effect journals, or CAS semantics.

---

# 27. Recommended migration into the current CEMM runtime

Do not replace Stage 0–22.

Integrate the v3 findings into it.

## Phase A — exact alignment

```text
MVP universal applications
    → compile to real CSIR constructors

MVP Store authority pins
    → real AuthorityGeneration / AuthoritySnapshot

MVP mutable generations
    → WorldRevision / DiscourseRevision / ObservationRevision
```

## Phase B — semantic workspace

Add a first-class cycle artifact:

```text
ActiveSemanticWorkspace
  selected CSIR fragments
  self/runtime state slots
  recent transition slots
  discourse/referent slots
  proof/rule dependencies
  activation features
  ranking trace
```

It should live inside `CycleWorkspace`, not in global durable authority.

Stage mapping:

```text
Stages 3–5 produce candidates
        ↓
Stage 6 projects/ranks active workspace + recurrent graph
        ↓
Stage 7 stabilizes semantic classes
```

## Phase C — self semantic state

Make `SelfRuntimeView` semantically explicit and session-scoped:

```text
interpretation state
epistemic state
response state
capability state
attention target
confidence
recent transitions
```

Expose relevant self-state slots to Stage 6 and Stages 14–18.

## Phase D — language trainer / packages

Move language competence growth to generated/versioned language artifacts:

```text
reviewed structured examples
        ↓
trainer
        ↓
versioned language package/model artifact
        ↓
new AuthorityGeneration on promotion
```

Avoid hand-authored phrase-by-phrase runtime repairs.

## Phase E — response and realization

Stage 18:

```text
construct exact Response CSIR
```

Stage 19:

```text
learned discourse/surface plan
+ semantic pointers
+ exact lexical/morphological authority
→ candidate surface + RealizationProof
```

Stage 20:

```text
cheap proof verification always
full independent round-trip selectively
emission authorization
```

This is explicitly consistent with the updated runtime plan.

---

# 28. Minimal production invariants derived from v3

1. **CSIR remains the only canonical semantic substrate.**
2. **The semantic workspace is transient cycle cognition, never a second truth store.**
3. **Self is a grounded participant with typed session/runtime state.**
4. **State transitions are first-class semantic evidence for attention and action.**
5. **Transformers rank and transform semantic candidates; exact closure decides validity.**
6. **Never run full-store attention; retrieve and rank a bounded workspace.**
7. **Language packs are versioned projections over shared semantics, not world knowledge.**
8. **Response meaning must exist before wording.**
9. **Content-bearing surface spans require semantic provenance/pointers.**
10. **Cheap realization proof is mandatory; full round-trip is selective.**
11. **Inference is transient unless explicit policy promotes/materializes a consequence.**
12. **Domain depth must reuse atoms/operators/rules instead of expanding the kernel.**
13. **Mutable world/session changes must not alter pinned authority generation.**
14. **Unknown, contradiction, ambiguity, and budget exhaustion remain distinct.**
15. **Optional missing subsystems must not block a grounded core answer.**
16. **Performance/boundedness are correctness properties.**

---

# 29. v3 regression contract

The bundle currently tests:

```text
32 passing regressions

- foundational DB contains no embedded language/realization example shortcuts
- deterministic generic trainer
- no family/domain/literal-response hardcoding in kernel
- no opaque response atoms
- grounded greeting semantics + semantic-pointer NLG
- evidence/conflict/meaning are queryable concepts
- grounded unknown/conflict response plans
- mother-in-law → marriage inference with proof
- bounded workspace includes self state
- explicit self-state transitions
- no mandatory round-trip flag in normal NLG proof
- language pack independently pinned
- inference/query non-bloat
- same-name ambiguity
- contextual labels do not corrupt input grounding
- multilingual shared semantics
- hidden operational policy edges excluded from descriptions
- domain import does not expand operator schema
- provisional rules do not execute
- structured trainer corpus has no precompiled program strings
- authority attestation stable across mutable learning
- NLG transform class authorization
- internal IDs never emitted
- repeated observations distinct / semantic apps deduplicated
- causal rules do not become actual facts
- semantic replay stable
- Unicode casefold resolution
- multi-valued role unsupported case fails explicitly
- state denial does not supersede supported state
- inference budget exhaustion becomes frontier
- multi-sentence clause composition/coreference
- self epistemic state recovers from insufficient to sufficient after a proven answer
```

---

# 30. Final v3 architecture summary

```text
                IMMUTABLE SEMANTIC AUTHORITY
             CSIR · definitions · rules · language/model pins
                              │
                              ▼
                    MUTABLE GROUNDED WORLD
            referents · claims · state · events · discourse
                              │
                  indexed / bounded retrieval
                              ▼
                ACTIVE SEMANTIC WORKSPACE
         exact facts · self state · transitions · query · proofs
                              │
                    Transformer dynamics
                 rank · attend · compose · select
                              │
                  exact semantic validation
                              │
             ┌────────────────┼──────────────────┐
             ▼                ▼                  ▼
           QUERY            LEARN              SIMULATE
             │                │                  │
             └────────────────┼──────────────────┘
                              ▼
                     GOAL / RESPONSE CSIR
                              │
                              ▼
                 SEMANTIC-POINTER REALIZER
                              │
                              ▼
               CHEAP PROOF-CARRYING VERIFY
                    │                 │
             normal low-risk     novelty/risk/audit
                    │                 │
                    │          independent round-trip
                    └───────────┬─────┘
                                ▼
                         AUTHORIZED EMISSION
                                │
                                ▼
                  DISCOURSE / COMMON-GROUND UPDATE
```

The architectural objective is not to make CEMM anti-neural or anti-Transformer.

It is to put neural computation in the right place:

> **Transformers operate over grounded semantic evidence and a bounded active workspace; exact CSIR/state/authority defines what is true, what may persist, and what semantic commitments an output is allowed to make.**
