# CEMM v3.4 — Architecture Reliability Revision

## 1. Scope

The v3.4 architecture already has the correct macro shape:

```text
SemanticSchemaStore
→ SemanticComposer
→ GroundingResolver
→ InterpretationResolver
→ EpistemicEvaluator / GapDetector
→ LearningCoordinator + child schema revision + replay
→ CommitCoordinator
→ semantic response planning and NLG
```

The weakness is that `schema resolution` and `grounded understanding` are not separated strongly enough.

The repair is **not** a new ontology engine or a second learning loop. It is a validation contract enforced inside the existing schema, grounding, gap, learning, replay, and activation path.

## 2. The distinction the kernel must preserve

For a term or schema `x`, CEMM must distinguish:

```text
recognized_surface(x)
referentially_available(x)
typed_schema(x)
operationally_understood(x)
epistemically_supported(x)
```

These are not synonyms.

- **Recognized surface**: a lexical form/span was detected.
- **Referentially available**: CEMM can create or retrieve a stable schema/concept reference and preserve assertions about it.
- **Typed schema**: the semantic family and required definition shape are known.
- **Operationally understood**: the exact schema revision has executable definition closure and passes competence checks.
- **Epistemically supported**: evidence aggregation supports the relevant proposition or schema claim at a given confidence/scope.

A statement may be remembered about a referentially available but operationally opaque concept.

### 2.1 Sense individuation and schema identity

Lexemes and schemas are different identity spaces. One lexeme may map to several senses; one schema may be lexicalized several ways.

**Split rule.** When new teaching is structurally incompatible with an existing sense (disjoint semantic family, disjoint bearer/holder constraints, or contradictory strict constitutive patterns), the default is a candidate **new sense**, not a contradiction — unless the source explicitly marks it as a correction. Ambiguous cases produce a sense-individuation probe, not a silent merge or silent fork.

**Merge rule.** Two schema refs may be unified only through an explicit `same_identity` assessment: compatible semantic families, non-conflicting strict patterns, and overlapping constitutive/differentiating structure or an explicit synonym/alias claim. Merging is a journaled, reversible revision that consolidates evidence, deferred relations, and gaps from both refs.

**Provisional ref identity.** A provisional schema ref created for an opaque term is durable and re-resolvable: later mentions of the same lexeme in compatible contexts resolve to the same provisional ref so deferred evidence accumulates instead of fragmenting. Context-incompatible mentions create sense candidates under the split rule.

## 3. Grounded Definition Closure

Every executable schema revision has a `DefinitionShape` determined by its existing schema family.

A revision has Grounded Definition Closure when:

1. its semantic family is resolved;
2. all required roles/fields of that family are present;
3. role and value constraints terminate in kernel value types, executable foundational schemas, adapter-observed schemas, or already grounded active schemas;
4. at least one constitutive condition explains what instances/occurrences must satisfy;
5. where the schema specializes another schema, at least one differentiating condition prevents pure synonymy or empty inheritance;
6. dependency traversal contains no unsupported circular component (see §3.1 for the precise support criteria);
7. its query, recognition, inference, and contradiction behavior can be instantiated;
8. schema-family-specific competence tests pass.

This is a derived assessment for an exact schema revision. It is not another durable ontology and not another resolver.

### 3.1 Jointly anchored definition cycles

Mutual definition is not automatically a closure failure. Natural concept clusters (`buy`/`sell`, `parent`/`child`, `win`/`lose`) are legitimately co-defined.

A strongly connected dependency component is **supported** when:

1. the component, taken as a whole, has at least one dependency path terminating outside the component in grounded foundations;
2. each member schema contributes at least one constitutive condition that is not merely a restatement of another member;
3. the component passes a joint competence suite that discriminates the members from each other.

A component with no external grounded anchor (`leader ↔ chief`) fails closure regardless of assertion count. Supported components activate together or not at all.

## 4. Sole authority

`SemanticSchemaStore` remains the only schema authority.

Before changing a schema revision to `active`, it must call its grounding/validation policy and receive a successful `SchemaGroundingAssessment`.

```text
SemanticSchemaStore.activate(revision)
    → validate structure
    → evaluate definition dependencies
    → check non-circular closure
    → run required competence specifications
    → activate or retain provisional/candidate status
```

A helper such as `SchemaGroundingValidator` may compute the assessment, but it may not resolve schemas, activate revisions, or create a second store.

### 4.1 Assessment validity and downgrade cascade

A `SchemaGroundingAssessment` is valid only for an exact schema revision **and** an exact dependency closure fingerprint — the set of revision IDs of every schema in its dependency closure.

When any dependency is superseded, quarantined, contradicted, or retired:

1. all cached assessments whose closure fingerprint includes the changed revision are invalidated;
2. dependent schemas are re-assessed lazily on next resolution or eagerly per policy;
3. a dependent that loses closure is downgraded to `partial`/`opaque` usability — it is not deleted, and its attributed evidence is preserved;
4. in-flight interpretations that consumed the degraded schema complete against their original snapshot but are marked for re-evaluation;
5. downgrades propagate transitively under the same rules, with a traceable journal entry per hop.

The reverse dependency index required for this cascade is the same index used by deferred relation replay.

## 5. Semantic sufficiency versus evidence confidence

These must remain separate.

### Semantic sufficiency

Answers:

> Is the definition executable and discriminative?

A single complete compositional definition may be sufficient.

### Epistemic confidence

Answers:

> How strongly should CEMM believe or promote this definition, and in what scope?

This depends on source, support, counterevidence, reuse, permission, and policy.

Therefore:

```text
many circular facts ≠ grounded understanding
one complete grounded definition may be semantically sufficient
one untrusted source may still restrict promotion/confidence
```

## 6. Unknown concepts and safe storage

When a user says:

```text
A president is a leader.
```

CEMM may persist the attributed proposition and lexical/schema references even if one or both concepts are opaque.

It may not yet:

- activate subtype/subrole inheritance;
- inherit roles or effects;
- generate a definition as known truth;
- claim `understands(self, president)` or `understands(self, leader)`;
- use the relation to authorize state/action effects.

The assertion remains queryable as reported/user-supplied evidence and can be replayed after its dependencies become grounded.

### 6.1 Permitted operation ladder

`definition_usability` maps to a fixed, monotonic operation ladder. Components consult the ladder; they do not re-derive permissions.

| usability | permitted operations |
|---|---|
| opaque | quote, remember attributed propositions, query as assertion, search, target for learning |
| partial | all opaque operations + typed reference, family-constrained composition, gap-directed probing, provisional contrast |
| executable | all partial operations + recognition, defining queries, licensed inference, inheritance participation |
| executable + effect-authorized | state/action effect projection |

**Executable is not effect-authorized.** A schema whose family carries precondition/effect semantics may project operational effects only after a separate effect-authorization decision considering source trust, scope, permission, and risk class. Structural closure alone never grants effect authority.

### 6.2 Proposition–revision binding

A committed proposition binds to the exact schema revisions under which it was interpreted at assertion time.

When a schema is later revised:

- historical propositions retain their original interpretation and remain queryable under it;
- reinterpretation under the new revision is an explicit, journaled replay that produces a new derived reading — it never silently rewrites the stored proposition;
- contradiction detection across revisions compares readings, not raw stored forms.

Memory meaning is therefore stable under concept drift instead of silently mutating.

### 6.3 Scope shadowing

Schema revisions may be scoped (`session > user > domain > global`). During resolution:

- the narrowest applicable scope shadows wider scopes for interpretation in that context;
- shadowing is per-schema and journaled in the interpretation trace;
- a scoped revision never mutates the wider-scope revision it shadows;
- promotion from a narrow to a wider scope goes through the ordinary promotion policy, including independent-evidence requirements.

## 7. No new top-level stage

The cognitive loop remains unchanged.

The following existing stages are strengthened:

- **Compose** preserves unknown lexical/schema targets and competing semantic-family hypotheses.
- **Ground** resolves reference identity, schema family, definition dependencies, and usable-vs-opaque status.
- **Resolve** may select an opaque interpretation for remembrance/discourse, but may not treat it as executable meaning.
- **Epistemics** distinguishes remembering the assertion from understanding the schema.
- **Gap detection** targets missing definition fields/dependencies that block the selected goal.
- **Learning** supplies typed schema deltas to the same store.
- **Replay** proves the schema is used in the original ordinary path.
- **Schema activation** requires Grounded Definition Closure.

## 8. Minimal definition shapes

### EntityKindSchema

Required for activation:

```text
parent/foundational anchor where applicable
instance criterion
identity/persistence behavior or inherited policy
constitutive/differentiating constraints
```

### Role-like concept

Represent using existing role/predicate schema facilities, not a new object family.

Required:

```text
eligible bearer constraint
context/domain role
occupancy relation or participation pattern
constitutive responsibility/relation/function
temporal/termination behavior where relevant
differentiator from parent role
```

### PredicateSchema

Required:

```text
predication kind
role signature
role constraints
truth/recognition pattern
query projections
polarity/context behavior
precondition/effect semantics when applicable
```

### StateDimensionSchema

Required:

```text
holder constraint
value type/range
cardinality
contradiction/update behavior
temporal policy
```

### Event/process schema

Required:

```text
participant roles
aspect/temporal structure
constitutive process or transition
completion/continuation behavior where applicable
```

## 9. `understands` derivation

`understands(self, schema)` is derived only when:

```text
schema revision is active
AND Grounded Definition Closure passes
AND the ordinary resolver can compose/ground it
AND minimum competence specifications pass
AND required dependencies are accessible
```

The existence of a lexical mapping or durable record is insufficient.

`understands` is graded and competence-relative, not boolean. Every derived claim carries:

```text
competence set demonstrated
scope (session / user / domain / global)
dependency closure fingerprint at assessment time
```

A truthful self-report cites what the schema can currently do, not a binary label.

## 10. Architecture result

This revision gives v3.4 a reliable foundation without adding another ontology layer:

```text
same semantic model
same schema store
same core loop
same learning transaction
same replay mechanism
+ explicit definition closure
+ schema-family completeness
+ non-circular dependencies
+ grounded activation gate
+ honest understanding assessments
+ jointly anchored cycle support
+ assessment invalidation cascade
+ executable/effect-authority separation
```
