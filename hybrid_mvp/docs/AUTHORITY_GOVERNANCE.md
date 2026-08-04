# Authority and Semantic Governance

## 1. Governing rule

The neural system ranks programs. It does not own semantic truth or semantic vocabulary.

A semantic reference is usable only when it is:

- present in the immutable reviewed `AuthorityStore`;
- an exact learned designation targeting reviewed authority;
- a cycle-local event/session identity;
- a query variable;
- a literal value in an authority-licensed role;
- a transient existential witness created by a reviewed inference rule.

There is no fallback that converts an unknown word into a concept or entity.

## 2. Store separation

### AuthorityStore

Immutable reviewed content:

- atoms and kinds;
- designations;
- relation types;
- state dimensions and value-domain mappings;
- event signatures;
- capabilities;
- permissions;
- adapters;
- inference rules;
- closed-class form evidence.

It has both a revision identifier and a content hash.

### WorldStore

Durable admitted facts and learned aliases. Every reference is validated against authority or an explicitly permitted local/literal namespace.

The world store cannot add an atom, relation type, state dimension, event schema, permission, capability, or adapter.

### SessionStore

Active session event, lifecycle, participants, focus and obligations.

### EpisodeStore

Immutable turn receipts containing selected/rejected candidates, revision pins, response meaning, effects and realization verification.

### ModelRegistry

Checkpoint revision, authority revision, authority content hash and dataset manifest identity.

## 3. Revision pinning

Every cycle can be described by:

```text
authority revision
+ authority content hash
+ world revision
+ session revision
+ episode revision
+ model revision
```

Runtime startup rejects a checkpoint when its authority revision or content hash differs from the loaded authority corpus.

## 4. Unknown content

Evidence processing may produce unknown literal units. Candidate generation is read-only and may not create a semantic ref to absorb them.

A candidate must account for unknown content through one of these exact paths:

- bind it as an allowed literal;
- consume it as the learned surface in a designation program;
- leave it as a residual and be rejected.

Therefore:

```text
do you have a telescope?
```

cannot create `entity:telescope`, `concept:telescope`, or a durable designation. It produces a frontier.

Likewise:

```text
hello telescope
```

cannot discard `telescope` and silently settle as a greeting.

## 5. Alias governance

An alias can be learned only when:

- the target resolves exactly to reviewed authority or a previously valid target;
- the program explicitly binds the new literal surface;
- capability, permission and adapter requirements for the learning effect pass;
- the effect is recorded with proof and revision.

The alias does not copy Python behaviour. It inherits affordances because later retrieval resolves to the same reviewed semantic target.

## 6. Proof-bearing inference

Rules are reviewed authority objects. Bounded forward chaining:

- uses exact unification;
- records parent fact refs;
- records the rule ref;
- preserves support/denial stance;
- bounds rounds and facts;
- creates transient existential witnesses when necessary.

Included inference:

```text
RELATION(Alice, mother_in_law, Bob)
→ RELATION(Bob, has_partner, ∃partner)
→ STATE(Bob, marital_status, married)
```

The witness `∃partner` is valid inside the derivation proof but is not admitted as a durable person or spouse identity.

## 7. Admission boundary

Structural validity is not truth.

- `OBSERVE` may propose admission, subject to exact epistemic/effect rules.
- `QUERY` reads admitted and derived facts without mutation.
- `REQUEST` may cause an effect only after capability, permission and adapter checks.
- `SIMULATE` creates a branch-local preview and cannot mutate world state.
- attributed embedded content retains attribution and is not promoted to direct world truth.
