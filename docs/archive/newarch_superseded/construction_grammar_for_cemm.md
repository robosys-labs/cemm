# Construction Grammar For CEMM

Purpose: explain how Construction Grammar should influence CEMM's meaning runtime without turning the system into a hardcoded grammar.

## 1. Why This Matters

Construction Grammar treats language as a learned network of form-meaning pairings.

This is a strong fit for CEMM because CEMM should learn:

```text
word patterns
phrase patterns
argument structures
idioms
dialogue moves
repair patterns
teaching patterns
```

as reusable structures.

But CEMM should not store every construction as an isolated rule. Constructions should become **operator templates** that help the semantic CPU build, repair, and compress UOL graphs.

## 2. Research Anchor

Fillmore, Kay, and O'Connor's work on the `let alone` construction argued that productive idiomatic patterns can have syntax, semantics, and pragmatics attached to configurations larger than ordinary phrase rules. This is directly relevant to CEMM because a conversational pattern can carry meaning that is not reducible to one word. See [Fillmore, Kay, and O'Connor, 1988](https://www.cambridge.org/core/journals/language/article/abs/regularity-and-idiomaticity-in-grammatical-constructions-the-case-of-let-alone/9E12B7F11C01F4AB5D187F0BFA1C4F73).

Bybee's usage-based view argues that repeated language experience shapes representation. CEMM should use this as a practical compression rule: repeated patterns become stronger constructions, not more stored utterances. See [Bybee, 2006](https://www.cambridge.org/core/journals/language/article/abs/from-usage-to-grammar-the-minds-response-to-repetition/056898EE71EC36FB3A45C1266D1453E2).

Computational construction grammar work also supports the idea that construction constraints can be induced from exposure, including across languages and registers. See [Dunn, 2019](https://arxiv.org/abs/1904.05529), [Dunn and Tayyar Madabushi, 2021](https://arxiv.org/abs/2110.05663), and [Dunn, 2022](https://arxiv.org/abs/2211.14160).

## 3. CEMM Interpretation

In CEMM, a construction is:

```text
a reusable perception/compression operator over surface form and UOL graph shape
```

Not:

```text
a permanent sentence template
a regex
a fixed intent classifier
```

Canonical form:

```typescript
interface ConstructionAtom {
  construction_id: string
  form_signature: FormSignature
  graph_signature: GraphPattern
  pragmatic_signature?: PragmaticPattern
  slot_constraints: PortConstraint[]
  operator_effects: GraphPatchTemplate[]
  confidence: number
  support_count: number
  counterexamples: string[]
}
```

## 4. Examples

### Definition Construction

Surface:

```text
X is a Y
X means Y
X refers to Y
```

Graph effect:

```text
Entity(X) --is_a/same_as--> Entity(Y)
Source(user) --teaches--> Relation(is_a/same_as)
```

Learning effect:

```text
candidate concept relation
possible alias
possible parent concept
```

### Capability Question Construction

Surface:

```text
what can you do?
can you X?
```

Graph effect:

```text
Intent(capability_query) --asks_about--> SelfAtom(self)
Modality(possible) --modifies--> Intent(capability_query)
```

Runtime effect:

```text
answer from SelfModel, not from world retrieval
```

### Casual Disclosure Construction

Surface:

```text
I am cold
I am tired
it is cold here
```

Graph effect:

```text
State(cold/tired) --has_role(holder)--> Entity(user or environment)
Source(user) --teaches/reports--> State(...)
Time(now) --modifies--> State(...)
```

Runtime effect:

```text
acknowledge state
infer possible need
do not demand external verification
```

## 5. Construction Learning

Learning flow:

```text
transcript examples
-> repeated form clusters
-> repeated graph patches
-> construction candidate
-> support/counterexample scoring
-> promote to ConstructionAtom
```

CEMM should induce constructions when:

```text
surface pattern repeats
graph patch repeats
pragmatic effect repeats
repair confirms interpretation
human answer pattern validates expected response
```

It should decay constructions when:

```text
pattern no longer predicts graph effect
pattern is too broad
pattern conflicts with stronger context
pattern has many repairs/corrections
```

## 6. Why This Debloats CEMM

Without constructions:

```text
many sentences -> many graph traces
```

With constructions:

```text
many sentences -> one construction operator + few exemplars
```

This is how CEMM learns language behavior without hoarding transcripts.

## 7. Implementation Direction

Add:

```text
cemm/learning/construction_inducer.py
cemm/types/construction_atom.py
cemm/memory/construction_lattice.py
```

Construction operators should sit before full graph consolidation:

```text
MeaningPerceptor
-> ConstructionMatcher
-> UOLGraphBuilder
-> SemanticCPU
-> ConceptConsolidator
```

## 8. Design Rule

Do not hardcode constructions as final truth.

Use constructions as **probabilistic graph-building operators** with support, confidence, counterexamples, and repair history.
