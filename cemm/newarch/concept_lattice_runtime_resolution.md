# Concept Lattice Runtime Resolution

Purpose: describe how CEMM resolves unknown concepts, port fillers, and predicates through the concept lattice at runtime.

## 1. The Core Idea

CEMM should not know all concepts upfront.

It should know how to grow concepts.

The concept lattice is a living network of:

```text
concept atoms
parent links
aliases
ports
predicate schemas
causal affordances
source support
counterexamples
semantic fingerprints
```

Runtime resolution means:

```text
when a word, role, or predicate is unknown, find or build its nearest operational place in the lattice
```

## 2. Resolution States

Every concept can exist in one of these states:

| State | Meaning |
|---|---|
| `unknown_surface` | Seen but not interpreted. |
| `candidate_atom` | Tentative concept created from surface/context. |
| `typed_candidate` | Has probable atom kind and parent. |
| `operational_atom` | Has enough ports/predicates to use. |
| `consolidated_atom` | Stable, supported, compressed concept. |
| `contested_atom` | Has contradictions or source disagreement. |
| `stale_atom` | May need source/time refresh. |

## 3. Runtime Algorithm

```text
resolve(surface, context_graph):
  1. normalize surface
  2. exact alias lookup
  3. construction/context lookup
  4. semantic fingerprint nearest-neighbor lookup
  5. source-backed lookup if needed
  6. create candidate atom if unresolved
  7. infer likely parent atoms
  8. open parent ports
  9. bind graph evidence
  10. return operational confidence
```

## 4. Unknown Concept Example

Input:

```text
a zorbal is a kind of container used for storing water
```

CEMM should create:

```text
zorbal:
  state: typed_candidate
  kind: entity_concept
  parents:
    container
  predicates:
    used_for(storing_water)
  ports inherited from container:
    content
    material
    capacity
    use
```

No hardcoded `zorbal` entry needed.

## 5. Unknown Predicate Example

Input:

```text
the device flarns the signal
```

If `flarn` is unknown:

```text
flarn:
  state: candidate_process
  ports:
    actor/device
    object/signal
  parent candidates:
    transform
    transmit
    process
  evidence:
    surface pattern: X verb Y
```

If later examples say:

```text
flarn means encrypt
flarned signal cannot be read
```

Then:

```text
flarn same_as encrypt
flarn causes readability_decrease_without_key
```

## 6. Recursive Explanation

Every operational atom should answer:

```text
What is this?
What can it bind to?
What can it do?
What can happen because of it?
What evidence supports this?
When does this stop being true?
```

Example:

```text
president
-> office_role
-> social_role
-> relation between holder and institution
-> authority enables actions
-> actions can cause domain state changes
```

This gives CEMM deeper reasoning as the lattice grows.

## 7. Semantic Fingerprints

Explicit graph structure remains primary.

But each concept can maintain a compact fingerprint:

```text
aliases
parents
ports
predicates
affordances
typical contexts
source distribution
```

Use fingerprint for:

```text
fast lookup
duplicate detection
candidate parent search
construction clustering
transcript pattern mining
```

Do not use fingerprint as truth.

## 8. Consolidation

A candidate atom becomes consolidated when:

```text
it compresses many graph traces
it predicts future bindings well
it reduces repairs
it has source support
it has low contradiction pressure
it has useful operational ports
```

Consolidation output:

```text
update aliases
update parents
update ports
update predicate schemas
update causal affordances
discard redundant traces
keep high-value exemplars
```

## 9. Design Rule

CEMM should not ask:

```text
Do I have a hardcoded type for this?
```

CEMM should ask:

```text
Where does this fit in the current concept lattice,
and what operational structure can be inherited or learned?
```
