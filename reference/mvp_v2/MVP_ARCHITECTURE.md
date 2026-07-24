# CEMM Minimal Semantic Brain MVP — Consolidated Architecture

## 1. Purpose

This document consolidates the architecture developed through the CEMM MVP design discussion into one implementation-facing reference.

The MVP exists to prove a small set of foundational claims before those claims are re-expanded into the full CEMM v3.5.x runtime:

1. **Meaning is not language.** Language is evidence into and out of a shared semantic substrate.
2. **Exact semantic identity must remain separate from learned/neural ranking.**
3. **New domains should grow atoms, facts, rules, and learned data—not Python branches or database schema.**
4. **Inference should normally be ephemeral.** Thinking more deeply must not automatically materialize an ever-growing closure of redundant facts.
5. **Identity is not a name.** Names, aliases, localized labels, surnames, and descriptions are evidence/designations attached to stable referents.
6. **Responses begin as semantics and only then become language.**
7. **Unknown, false, conflict, prediction, causality, and actual observation must remain distinguishable.**
8. **A learned concept should be reusable in new compositions without custom concept code.**

The MVP is deliberately small. Its Python kernel remains below 1,000 lines and contains no family-, presidency-, temperature-, profession-, or other domain-specific semantic branches.

---

# 2. Architectural thesis

```text
OBSERVATION
language · vision · sound · telemetry · tools
        ↓
EVIDENCE
surface forms · referent candidates · semantic activations
        ↓
MEANING
resolved identities · types · relations · states · events · transitions
        ↓
COGNITION
settle · infer · query · simulate · learn · plan
        ↓
RESPONSE / ACTION MEANING
        ↓
REALIZATION
language · operation · other modality
        ↓
NEW OBSERVATIONS RETURN TO THE SAME LOOP
```

The fundamental separation is:

```text
words / images / sensor readings
            ≠
semantic identity
```

A surface signal is evidence that may activate one or more possible semantic structures.

---

# 3. Overall CEMM architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. OBSERVATION                                              │
│ text · audio · image · telemetry · tool result · self-state │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. EVIDENCE / INTERFACE CODECS                              │
│                                                             │
│ language forms                                              │
│ referent/designation evidence                               │
│ structural evidence                                         │
│ neural/statistical candidate ranking                        │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. GROUNDING                                                │
│                                                             │
│ resolve identity                                            │
│ resolve discourse reference                                 │
│ rank ambiguous entities                                     │
│ preserve unresolved ambiguity                               │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EXACT SEMANTIC CONSTRUCTION                              │
│                                                             │
│ CSIR-compatible atoms / applications / bindings             │
│ validation against exact semantic authority                 │
│ provenance + evidence                                       │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. DYNAMIC SEMANTIC PLANE                                   │
│                                                             │
│ candidate competition                                       │
│ recurrent settling                                          │
│ confidence / salience                                       │
│ bounded inference                                           │
│ learning frontiers                                          │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. WORLD / DISCOURSE / EPISTEMIC MODEL                      │
│                                                             │
│ observations                                                 │
│ active state                                                 │
│ relations                                                    │
│ events                                                       │
│ beliefs / denials / conflicts                               │
│ provenance                                                   │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. REASON / QUERY / SIMULATE / DECIDE                       │
│                                                             │
│ logical closure                                              │
│ causal rules in separate execution mode                     │
│ queries                                                      │
│ goals / operations in full architecture                     │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. RESPONSE CSIR / ACTION SEMANTICS                          │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. LEARNED REALIZATION                                      │
│ semantic structure → language candidates                    │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. SEMANTIC PRESERVATION / AUTHORIZATION                   │
│ inverse semantic check · authority · disclosure             │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
                         EMISSION
```

The MVP implements a compressed subset of this architecture while preserving the same boundaries.

---

# 4. Two planes, one semantic brain

## 4.1 Exact semantic plane

```text
┌────────────────────────────────────────────┐
│ EXACT SEMANTIC PLANE                       │
│ what meaning is                            │
│                                            │
│ exact atoms                                │
│ semantic applications                      │
│ role bindings                              │
│ exact identities                           │
│ observations / claims                      │
│ provenance / rules                         │
│ deterministic snapshot identity            │
└─────────────────────┬──────────────────────┘
                      ↕
┌─────────────────────┴──────────────────────┐
│ DYNAMIC SEMANTIC PLANE                     │
│ how meaning becomes active                 │
│                                            │
│ label usage                                │
│ discourse salience                         │
│ Transformer scores                         │
│ candidate competition                      │
│ bounded closure                            │
│ learning frontiers                         │
└────────────────────────────────────────────┘
```

### Exact-plane rule

Statistical popularity may affect which candidate is considered first.

It must **not** redefine semantic identity.

For example:

```text
"Donald Trump" used 1000 times
"Trump" used 5000 times

DOES NOT imply:
identity = "Trump"
```

Instead:

```text
identity = opaque exact referent
labels   = evidence/designations of that referent
usage    = dynamic ranking evidence
```

The MVP excludes label usage and discourse salience from the deterministic semantic snapshot hash.

---

# 5. Full CSIR and the MVP's compressed semantic algebra

The production CEMM semantic substrate remains CSIR-like:

```text
TERM
VARIABLE
APPLICATION
BINDING
QUALIFIER
SCOPE
COORDINATION
PROOF
```

The MVP intentionally compresses common semantic structures into five universal operator shapes:

```text
op:designation
op:type
op:relation
op:state
op:event
```

These are **not five ontology categories that every future concept must subclass in Python**.

They are compact executable graph shapes used to prove that domain growth can occur through atoms and data rather than code branches.

A production mapping is approximately:

```text
MVP atom                  → CSIR SemanticTerm / authority-pinned semantic definition
MVP application           → CSIR SemanticApplication
MVP role/value binding    → CSIR PortBinding
MVP state time/context    → CSIR Qualifier / scope structure
MVP derived proof         → CSIR ProofLink
MVP open query variable   → CSIR SemanticVariable
```

The MVP must therefore be treated as a compressed executable proof of the semantic architecture, not as a competing replacement for full CSIR.

---

# 6. Universal semantic data architecture

## 6.1 Minimal permanent structures

```text
ATOM
  stable semantic identity

APPLICATION
  occurrence of a universal operator

BINDING
  role → filler

OBSERVATION
  evidence event

CLAIM
  support / denial / validity interval / confidence

PROOF
  lineage from observation or rule

RULE
  reusable semantic transformation
```

Concepts such as:

```text
mother
mother-in-law
wife
husband
spouse
president
doctor
temperature
ownership
arrival
marriage
```

are data atoms and rule structures.

They are not new database tables, Python classes, or execution stages.

---

# 7. Anti-bloat architecture

This is one of the central invariants of the MVP.

```text
                    EXACT ATOMS
                        │
        ┌───────────────┼────────────────┐
        │               │                │
     entity          concept       relation/state/event atoms
        │               │                │
        └───────────────┬────────────────┘
                        ▼
              FIVE UNIVERSAL OPERATORS

                  designation(...)
                  type(...)
                  relation(...)
                  state(...)
                  event(...)

                        │
                        ▼
                 EXACT OBSERVATIONS
                        │
                        ▼
                 REUSABLE RULE GRAPH

              subrelation inheritance
              type constraints
              type transitivity
              relation → state effects
              compositional definitions
              causal/default rules

                        │
                        ▼
              BOUNDED EPHEMERAL CLOSURE

               infer only when required
               deduplicate by semantics
               retain proof lineage
               do not persist by default

                        │
                ┌───────┴────────┐
                ▼                ▼
              QUERY          SIMULATION
        definition/logic     causal mode
```

## 7.1 Growth rule

```text
new vocabulary
    → add designations / language evidence

new entity
    → add atom + identity evidence

new fact
    → add application + claim + provenance

new hierarchy
    → add type/subrelation facts

new common consequence
    → reuse generic rule patterns

new genuinely compositional concept
    → add a compact reusable semantic rule

new causal knowledge
    → add causal rule using same atoms

new domain
    ≠ add schema
    ≠ add Python branch
```

## 7.2 Why inference is ephemeral

A naive knowledge engine may do:

```text
1 observed fact
   ↓
10 inferred facts persisted
   ↓
100 second-order facts persisted
   ↓
new rule added
   ↓
unbounded materialization growth
```

The MVP instead stores:

```text
DURABLE
observations
reviewed/learned claims
rules
provenance

EPHEMERAL
query-time consequences
existential witnesses
derived types
inferred states
proof closure
```

Repeated questioning does not increase the permanent application/binding/claim/proof counts.

---

# 8. Identity and designation architecture

## 8.1 Identity is not a label

```text
                 EXACT IDENTITY
                 opaque atom/ref
                      │
        ┌─────────────┼────────────────┐
        ▼             ▼                ▼
 semantic facts   designations      provenance/state
```

An entity may have:

```text
full legal name
formal name
given name
middle name
surname
maiden name
nickname
alias
stage name
transliteration
localized/exonym label
historical name
```

All can point to one exact identity.

## 8.2 Language-invariant and language-specific labels

```text
entity:country_x
    ├── "United States"   language=en
    ├── "Estados Unidos"  language=es
    └── "États-Unis"      language=fr
```

A personal name may instead be marked language-independent:

```text
"Donald Trump"
language = und
script   = Latn
```

## 8.3 Same-name conflicts

```text
"Alex Kim"
    ├── entity:A
    └── entity:B
```

Resolution must not merge them.

```text
surface label
    ↓
all candidate identities
    ↓
reviewed prior
+ preferred designation evidence
+ language match
+ usage statistics
+ discourse salience
+ semantic type compatibility
    ↓
rank candidates
    ↓
clear margin?
    ├── yes → resolve
    └── no  → clarification frontier
```

## 8.4 Label ranking is contextual

One semantic quantity may have multiple realizations:

```text
quantity:2

count context → "two"
rank context  → "second"
```

Therefore global popularity alone is insufficient.

The architecture supports context-sensitive designation ranking.

---

# 9. Language interface architecture

Language is a codec around meaning.

```text
RAW LANGUAGE
     │
     ▼
lexical / reference evidence
     │
     ▼
known semantic atoms activated
     │
     ▼
DELEXICALIZED STRUCTURE
     │
     ▼
trained Transformer
     │
     ▼
foundational semantic program
     │
     ▼
EXACT VALIDATION
     │
     ▼
semantic applications
```

The learned semantic program may contain only:

```text
foundational operators
foundational roles
placeholders bound to exact atoms
explicitly authorized creatable structural kinds
```

It may not directly invent:

```text
MotherInLawSchema
PresidentSchema
CustomRelationType123
```

### Current MVP safety

Two independently initialized input Transformer models must agree on the semantic program.

The primary program must also round-trip through program → surface → program, and semantic placeholders must be conserved.

This is stronger than the previous single-model self-consistency check, though still not equivalent to production N-best semantic settling.

---

# 10. Document and discourse architecture

```text
DOCUMENT
   ↓
mention candidates
   ↓
label / pronoun / reference evidence
   ↓
ranked referent candidates
   ↓
local discourse salience
   ↓
shared placeholders across sentences
   ↓
Transformer semantic composition
   ↓
multiple applications
   ↓
exact validation
   ↓
commit
```

A crucial invariant:

```text
Donald Trump
He
him
his

may all resolve to:
entity:donald_trump
```

Pronouns are not aliases permanently attached to an entity.

Instead they are reference evidence constrained by semantic features and discourse state.

For example:

```text
"she"
requires:
  entity-like referent
  semantic type compatible with female
```

The current MVP can use **inferred semantic type evidence** for this resolution.

---

# 11. Structural referent reuse

New placeholders are not automatically new identities.

Before minting a new atom, the kernel attempts generic structural reuse:

```text
new placeholder X
       ↓
look at applications containing X
       ↓
use all other grounded roles as constraints
       ↓
search existing semantic facts
       ↓
0 candidates  → mint fresh occurrence-scoped opaque identity
1 candidate   → reuse existing identity
>1 candidates → ambiguity frontier
```

Example:

```text
My mother-in-law arrived today.
```

On first observation, a new unnamed referent may be created.

On a repeated semantically identical observation, the existing relation:

```text
mother_in_law_of(X, user)
```

can identify the same X rather than minting another duplicate referent.

Fresh opaque identity creation is occurrence-scoped, not derived from the surface string.

---

# 12. Family reasoning example

Learned semantic knowledge:

```text
mother_in_law  subrelation_of family_relative
partner        subrelation_of spouse
wife           subrelation_of spouse
husband        subrelation_of spouse

subject_type(mother_of, female)
subject_type(wife, female)
subject_type(husband, male)

female IS_A human
male   IS_A human
human  IS_A living_entity

spouse implies marital_status = married
wife/husband imply marriage_eligibility = eligible
```

The one genuinely compositional family rule is:

```text
mother_in_law_of(M, Y)
    ⇒
exists P:
    mother_of(M, P)
    AND
    partner_of(P, Y)
```

Then generic reusable rules perform the rest.

## Query example

Observation:

```text
My mother in-law arrived today.
```

Durable semantic content:

```text
relation(
    subject  = M,
    relation = mother_in_law,
    object   = user
)

event(
    event = E,
    type  = arrive,
    actor = M,
    time  = today
)
```

Question:

```text
Am I married?
```

Ephemeral proof:

```text
mother_in_law_of(M,user)
        ↓ compositional definition
mother_of(M,P)
partner_of(P,user)
        ↓ generic subrelation inheritance
spouse_of(P,user)
        ↓ generic relation → object-state rule
state(user, marital_status, married)
        ↓
YES
```

The identity of P remains existential/unknown.

The system derives that a spouse must exist without hallucinating who that spouse is.

---

# 13. Generic hierarchy and type reuse

```text
mother_of(M,P)
       ↓ participant-type rule
female(M)
       ↓ type transitivity
human(M)
       ↓ type transitivity
living_entity(M)
```

No stored rules are required for:

```text
mother → human
mother → living_entity
mother-in-law → human
```

Those are consequences of reusable structure.

---

# 14. State architecture

State uses the same fixed operator:

```text
state(
    subject,
    dimension,
    value
)
```

Examples:

```text
marital_status = married
temperature = high
battery_state = charged
network_state = connected
```

A state dimension may declare itself exclusive.

```text
marital_status
exclusive = true
```

Then a new supported state value supersedes the prior active supported value by closing its validity interval.

Important correctness rule:

```text
DENY(new_value)
must not supersede
SUPPORT(old_value)
```

The final MVP fixes this explicitly.

---

# 15. Causality and nonactual reasoning

Rules are typed:

```text
definition
entailment
causal
default
```

Actual-world logical closure executes only authorized definition/entailment rules.

```text
observation
   ↓
grounded world state
   ↓
definition / entailment closure
```

Causal rules are reserved for a separate simulation/prediction mode:

```text
actual state
   ↓
causal model
   ↓
simulated / predicted consequence
```

This prevents:

```text
"X arrived"
```

from silently asserting every causal consequence as current truth.

---

# 16. Query architecture

Current MVP query forms are compressed into:

```text
verify proposition
state lookup / verification
type verification
description target
```

The reasoner distinguishes:

```text
SUPPORTED
CONTRADICTED
UNKNOWN
CONFLICT
```

It does not equate:

```text
not found
=
false
```

Bounded inference has explicit limits.

If closure reaches `max_rounds` or `max_facts`, the runtime emits an `inference_incomplete` frontier instead of pretending the answer is unknown or false.

---

# 17. Response architecture

```text
UNDERSTANDING / QUERY RESULT
           ↓
RESPONSE SEMANTICS
           ↓
trained semantic→language Transformer
           ↓
surface plan
           ↓
insert exact semantic fillers
           ↓
inverse Transformer
           ↓
reconstruct response semantics
           ↓
exact semantic comparison
           ↓
verified?
  ├── no  → block/frontier
  └── yes → emit
```

There is no domain-specific realization template table in the kernel.

The Transformer learns wording while exact semantic structure remains authority.

Internal semantic references such as:

```text
atom:...
existential:...
app:...
fact:...
```

are never authorized for user-visible emission.

If the system lacks a valid referring expression, realization is blocked instead of leaking an internal identifier.

---

# 18. Learning and authority architecture

Target full architecture:

```text
unresolved frontier
      ↓
evidence
      ↓
candidate semantic structure / rule
      ↓
competence tests + counterexamples
      ↓
scoped promotion
      ↓
new authority generation
      ↓
replay / restart
      ↓
reuse in new compositions
```

MVP support:

```text
observations
provisional instance claims
generations
semantic snapshot hashing
reviewed rule imports
rule semantic deduplication
frontiers
```

Executable semantic rules are authority-gated:

```text
reviewed / promoted
    → executable

provisional
    → not executed as semantic authority
```

This was tightened in the final audit.

---

# 19. Deterministic identity, replay, and generations

Semantic identity is intended to be deterministic and replayable.

The MVP snapshot includes exact semantic tables but excludes dynamic ranking state such as:

```text
label usage counts
discourse salience
frontiers
generation timestamps
```

Generation hashes are finalized **after** semantic content has been committed.

Reimporting the same reviewed knowledge is semantically idempotent.

Repeated real-world user observations, however, remain distinct evidence events while structurally grounding to existing referents/applications where appropriate.

This avoids two opposite errors:

```text
ERROR A
same text forever treated as one evidence occurrence

ERROR B
same definite referent minted as a new identity every mention
```

---

# 20. Multilingual architecture

```text
English interface ─┐
Spanish interface ─┼──► same exact atoms / rules / world graph
French interface  ─┘
```

There is no language-specific ontology.

Examples:

```text
"mother in-law"
"suegra"
        ↓
rel:mother_in_law
```

Multilingual designation lookup uses Unicode normalization and casefolding rather than SQLite ASCII-only lowercase matching.

This was fixed in the final audit.

---

# 21. What the current MVP covers

Legend:

```text
✓  implemented and regression-tested
△  partial / proof-level implementation
✗  intentionally not yet implemented
```

| Capability | Status | Notes |
|---|:---:|---|
| Exact opaque semantic identity | ✓ | Identity separated from labels. |
| Multiple labels/names per entity | ✓ | Designation facts + materialized resolver index. |
| Multilingual labels | ✓ | Shared identity, language-specific/invariant designations. |
| Unicode-safe label resolution | ✓ | NFKC + casefold matching. |
| Same-name ambiguity | ✓ | Candidate ranking + ambiguity frontier. |
| Dynamic label usage/salience ranking | ✓ | Excluded from semantic authority hash. |
| Five fixed universal MVP operators | ✓ | Domain import does not grow operator schema. |
| Universal role type validation | ✓ | Wrong semantic filler kinds rejected. |
| Domain knowledge as atoms/rules | ✓ | Family example proves reuse. |
| Subrelation inheritance | ✓ | Generic rule. |
| Type transitivity | ✓ | Generic rule. |
| Relation→state effects | ✓ | Generic meta-rules. |
| Existential witnesses | ✓ | Used for unknown spouse/partner. |
| Bounded ephemeral inference | ✓ | Derived closure not persisted. |
| Inference-limit frontier | ✓ | Resource exhaustion not confused with unknown. |
| Support / deny / unknown / conflict | ✓ | Open-world-safe query result states. |
| Exclusive current-state supersession | ✓ | Positive-state update only. |
| Causal rules separated from actual truth | ✓ | Causal rules not executed in actual closure. |
| Rule authority gating | ✓ | Only reviewed/promoted rules execute. |
| Rule semantic deduplication | ✓ | Duplicate rule IDs do not duplicate semantics. |
| Rule admission validation | ✓ | Unbound variables etc. rejected. |
| Observation vs claim separation | ✓ | Separate tables and proof lineage. |
| Repeated evidence occurrences | ✓ | Repeated user observations remain distinct. |
| Structural referent reuse | ✓ | Existing referents reused when uniquely determined. |
| Multi-sentence pronoun coreference | △ | Demonstrated for small trained topologies/discourse. |
| Inferred semantic type used for pronouns | ✓ | E.g. inferred female supports “she”. |
| Learned input Transformer | ✓ | Delexicalized language→program. |
| Independent input-model agreement | ✓ | Two independently initialized models must agree. |
| Meaning-first learned realization | ✓ | Semantic→surface Transformer. |
| Inverse semantic realization check | ✓ | Surface plan must reconstruct semantics. |
| Internal-ID emission blocking | ✓ | Unresolved referring expressions are not leaked. |
| Semantic generations / replay hash | ✓ | Minimal deterministic generation layer. |
| Full CSIR node model | ✗ | MVP uses compressed operator algebra mapped conceptually to CSIR. |
| N-best recurrent semantic settling | ✗ | Two-model agreement is only a minimal substitute. |
| General arbitrary document composition | ✗ | Only small learned topologies demonstrated. |
| Automatic rule induction from unrestricted teaching language | ✗ | Family rules are learned semantic data, not induced from raw teaching sentences. |
| Competence/counterexample promotion pipeline | ✗ | Reviewed/provisional statuses exist; full promotion does not. |
| Full temporal event/state transition engine | △ | Exclusive state replacement exists; richer fluents/transitions do not. |
| Correction/retraction/replay propagation | ✗ | Not implemented beyond state supersession. |
| Full epistemic belief/source reliability aggregation | △ | Claims/provenance exist; source-calibrated belief fusion does not. |
| Negation/scoped modality in full CSIR | △ | Claim stance exists; full scope/modality algebra does not. |
| Multi-valued role bindings | ✗ | Explicitly rejected in MVP; use repeated applications. |
| Coordination / sets | ✗ | Full CSIR coordination not implemented. |
| General quantifiers | △ | Existential witnesses supported; universal/scoped quantification not. |
| Inequality/distinctness constraints | ✗ | Rule language does not yet express X ≠ Y. |
| Recursive causal simulation/counterfactuals | ✗ | Causal rules stored but no simulator. |
| Goals/significance/planning/actions | ✗ | Outside MVP. |
| Multimodal encoders/fusion | ✗ | Observation model prepared; no vision/audio/telemetry codecs. |
| Learned referring-expression generation | ✗ | Internal IDs are blocked; rich discourse descriptions still missing. |
| Model persistence/versioned weights | ✗ | Tiny models retrain from stored examples in MVP. |
| Signed authority manifests | ✗ | Full repository activation infrastructure not reproduced here. |

---

# 22. Critical bugs found in the final audit and fixed

The final audit found additional correctness problems not covered by the earlier 21-test suite.

## 22.1 Unicode label lookup was not truly multilingual

### Problem

SQLite `LOWER()` is not a complete Unicode casefold implementation.

Accented labels such as:

```text
cónyuge
CÓNYUGE
```

could fail to match reliably.

### Fix

Designation/reference comparison now uses:

```text
Unicode NFKC normalization
+
Python casefold
```

---

## 22.2 Input semantic verification could accept a self-consistent wrong mapping

### Problem

The previous check was:

```text
input
→ program P
→ reconstructed text T'
→ program P
```

A model could theoretically be consistently wrong and still pass.

### Fix

The MVP now requires:

```text
primary Transformer program
=
independently initialized verifier Transformer program
```

plus program round-trip and placeholder conservation.

This still does not replace production N-best settling, but materially reduces single-model self-confirmation.

---

## 22.3 State denial could incorrectly supersede an unrelated current state

### Problem

Asserting:

```text
DENY(single)
```

could close an active:

```text
SUPPORT(married)
```

because state supersession ignored claim stance.

### Fix

Only a new **supported** state can supersede a prior supported value in an exclusive dimension.

---

## 22.4 Repeated observations were collapsed into one evidence event

### Problem

Observation IDs were based only on content.

Two distinct user observations with identical wording could collapse into one row.

### Fix

Reviewed seed imports remain idempotent, while runtime user observations receive occurrence-scoped identities.

Repeated evidence can therefore remain distinct without duplicating semantic applications unnecessarily.

---

## 22.5 New opaque entity/event IDs were seeded from surface text

### Problem

Two identical sentences could mint the same “new” identity simply because the text matched.

### Fix

New atom identities are occurrence-scoped and opaque.

Before minting, generic structural referent reuse attempts to match an existing referent using the other grounded application roles.

---

## 22.6 Provisional rules could execute as semantic authority

### Problem

The inference query loaded all definition/entailment rules regardless of authority status.

### Fix

Only:

```text
reviewed
promoted
```

rules execute in the exact inference closure.

---

## 22.7 Multi-valued role cardinality was declared but silently unsupported

### Problem

The schema had a `cardinality` column, but application arguments are a one-value-per-role dictionary.

A `many` role would therefore be a false capability claim.

### Fix

The MVP now explicitly rejects non-`one` role cardinality.

Multiplicity must be represented by repeated applications until full CSIR coordination/set semantics are added.

---

## 22.8 Bounded inference exhaustion could masquerade as “unknown”

### Problem

If inference hit `max_facts` or `max_rounds`, missing conclusions could incorrectly appear epistemically unknown.

### Fix

The runtime emits:

```text
frontier: inference_incomplete
```

instead of answering false/unknown from an incomplete closure.

---

## 22.9 Internal semantic IDs could leak into descriptive language

### Problem

Unnamed/existential referents could render as:

```text
atom:...
existential:...
```

### Fix

Internal semantic identifiers are blocked from emission.

If no valid referring expression exists, realization must fail/frontier rather than expose implementation identity.

---

# 23. Remaining critical architecture gaps

These are not hidden failures; they are explicit boundaries of the MVP.

## 23.1 Automatic semantic rule induction

The MVP can execute:

```text
mother_in_law_of(M,Y)
⇒
exists P:
  mother_of(M,P)
  partner_of(P,Y)
```

but it does not autonomously derive that formal rule from unrestricted natural language:

```text
"A mother in-law is the mother of a partner."
```

A proper solution requires:

```text
teaching observation
→ candidate rule structures
→ grounding
→ counterexamples
→ competence evaluation
→ scoped promotion
→ reusable semantic authority
```

A regex sentence-to-rule shortcut would violate the architecture.

---

## 23.2 General document-level semantic composition

The MVP demonstrates limited multi-sentence/coreference topologies.

Production needs:

```text
clause semantic candidates
→ N-best partial graphs
→ cross-sentence reference hypotheses
→ recurrent composition
→ competition / inhibition
→ stable or partial document CSIR
```

---

## 23.3 Recurrent semantic dynamics

Current minimal substitute:

```text
two independently initialized models agree
+
exact semantic validation
```

Production target:

```text
multiple candidate graphs
semantic activation
recurrent propagation
inhibition
world-model compatibility
confidence calibration
convergence / unresolved frontier
```

---

## 23.4 Full referring-expression generation

The system must eventually generate discourse-aware references such as:

```text
she
your mother-in-law
the woman who arrived today
that server
its previous owner
```

Current safety behavior blocks internal IDs but does not yet generate rich referring expressions for every unnamed/existential referent.

---

## 23.5 Full temporal transition model

Needed:

```text
before-state
transition/event
after-state
persistence
mutual exclusion
valid intervals
retraction/correction
replay invalidation
```

The MVP only implements generic exclusive-current-state supersession.

---

## 23.6 Rich epistemic/source model

Needed distinctions:

```text
observed
reported
believed
inferred
predicted
simulated
counterfactual
retracted
conflicted
```

with source reliability and evidence aggregation.

---

## 23.7 Full CSIR scope / coordination / quantification

The MVP lacks production-grade:

```text
scope
coordination
sets
ordered bindings
universal quantification
negation scope
modality scope
permission/evidence qualifiers
```

These should map into the existing CSIR kernel rather than create new domain schemas.

---

## 23.8 Model lifecycle

The tiny Transformers retrain from stored examples at runtime.

Production needs versioned model artifacts:

```text
semantic_encoder_<language>@generation
semantic_decoder_<language>@generation
calibration artifact
training provenance
promotion status
content hash/signature
```

The model remains a proposal/ranking component, not semantic authority.

---

# 24. Anti-bloat invariants for the full CEMM implementation

These should become acceptance tests in the main repository.

## Invariant A — domain import cannot grow kernel schema

```text
before domain import:
operator count = N
role schema count = M

after domain import:
operator count = N
role schema count = M
```

unless a deliberate foundational architecture revision occurs.

## Invariant B — repeated reasoning does not persist closure

```text
query same deep inference 1000 times

permanent semantic application count
must remain unchanged
```

unless explicit consolidation/promotion is requested.

## Invariant C — concept learning reuses existing structural atoms

Adding:

```text
stepmother
adoptive mother
CEO
prime minister
battery health
```

should primarily add:

```text
atoms
designations
relations/rules
examples
```

not Python functions/tables/stages.

## Invariant D — model output cannot mint ontology authority

Neural models may propose:

```text
candidate predicate
candidate referent
candidate binding
candidate qualifier
```

but exact authority decides whether those structures are valid/promoted.

## Invariant E — names never define identity

```text
two identical names
≠
same entity
```

## Invariant F — derivation mode must be explicit

```text
definition/entailment
≠
causal prediction
≠
counterfactual simulation
≠
authorized action
```

## Invariant G — incomplete inference never becomes epistemic certainty

Resource limits produce a frontier, not false/unknown certainty.

---

# 25. Current MVP regression coverage

The final audited MVP has **29 passing regression tests** covering:

1. no family/domain hardcoding in Python;
2. domain import does not expand operator schema;
3. surface variants converge without new semantic programs;
4. mother-in-law observation implies marriage through proof;
5. repeated queries do not bloat permanent memory;
6. causal rules do not silently become actual truth;
7. mother role reuses type lattice;
8. wife semantics compose through generic meta-rules;
9. same-name identities remain ambiguous until context helps;
10. designations are semantic facts while dynamic ranking is non-authoritative;
11. multi-sentence coreference reuses one exact referent;
12. learned language programs contain only foundational structure;
13. universal role typing rejects wrong semantic kinds;
14. exclusive state supersession works generically;
15. semantic re-import is replay-stable;
16. inferred role types support follow-up queries without materialization;
17. multilingual interfaces reuse the same semantic rules;
18. pronoun resolution can use inferred semantic type;
19. semantically duplicate rules are deduplicated;
20. unsafe/unbound rules are rejected and creatable kinds are restricted;
21. unknown remains distinct from false;
22. Unicode/casefold multilingual designation resolution;
23. denial does not supersede unrelated positive state;
24. repeated observations remain distinct while grounded referents are reused;
25. provisional rules do not execute as semantic authority;
26. unsupported multi-valued roles fail explicitly;
27. input semantic codec requires independent model agreement;
28. internal semantic IDs are never emitted;
29. inference exhaustion produces a frontier rather than false unknown.

---

# 26. Recommended path from MVP to main CEMM runtime

The MVP should not be copied wholesale into the 23-stage runtime as another subsystem.

Instead, use it as a **conformance oracle** for simplifying the existing architecture.

Recommended migration boundaries:

```text
MVP exact atoms / applications
    → existing CSIR + semantic authority stores

MVP designation facts/index
    → canonical designation semantics + resolver projection

MVP delex/Transformer codec
    → language evidence + ranked CSIR candidate proposal

MVP bounded closure
    → recurrent semantic dynamics + exact inference services

MVP rule kinds
    → definition / entailment / causal / default authority classes

MVP response semantics + Transformer
    → Response CSIR + learned realization + semantic verifier

MVP frontiers
    → canonical Stage 0–22 frontier/effect system
```

The main architectural goal is not to add the MVP beside the current implementation.

It is to remove any current subsystem that violates these simpler invariants.

---

# 27. Final architecture summary

```text
                         OBSERVATION
                             │
                             ▼
                    MULTIMODAL EVIDENCE
                             │
                             ▼
                  REFERENT / LABEL RANKING
                    identity remains exact
                             │
                             ▼
                   LEARNED SEMANTIC CODEC
                    proposes graph structure
                             │
                             ▼
                     EXACT CSIR VALIDATION
                             │
                             ▼
                    GROUNDED WORLD GRAPH
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
         DEFINITION / LOGIC          CAUSAL MODEL
                 │                    simulation only
                 ▼                       │
        BOUNDED EPHEMERAL CLOSURE        │
                 │                       │
                 └───────────┬───────────┘
                             ▼
                      QUERY / DECISION
                             │
                             ▼
                       RESPONSE CSIR
                             │
                             ▼
                 LEARNED LANGUAGE DECODER
                             │
                             ▼
                 INVERSE SEMANTIC VERIFIER
                             │
                             ▼
                          EMISSION
```

And the core anti-bloat principle is:

> **The kernel knows how semantic structure composes. Stored and learned data describe the world. Deeper knowledge reuses atoms, relations, operators, and rules; it does not continuously create new schemas.**

