# Operational Ports And Dynamic Slot Resolution

Purpose: replace hardcoded slot thinking with a recursive atom-based resolution mechanism.

## 1. The Problem With Slots

Traditional slot filling often requires a domain-specific ontology:

```text
destination slot
date slot
hotel slot
account slot
amount slot
```

This does not scale for CEMM.

It creates:

```text
hardcoded domains
duplicated slot definitions
manual schema maintenance
weak cross-domain reuse
bloated memory
```

The better primitive is the **operational port**.

## 2. Slot vs Port

| Slot | Operational Port |
|---|---|
| Domain-specific field | Atom-owned role interface |
| Usually hardcoded | Dynamically resolved through known atoms |
| Often flat | Recursive and typed |
| Filled by entity extraction | Filled by graph matching and constraints |
| Requires custom schema | Reuses atom lattice |

Example:

```text
leader.domain
eat.food
ask.topic
president.time_scope
current.target_relation
```

These are not independent fields. They are ports on executable atoms.

## 3. Research Anchor

Typed feature-structure grammars such as HPSG model linguistic objects using rich typed structures and constraints rather than simple flat fields. This supports the CEMM idea that slots should be resolved through typed structure and constraints, not hardcoded per task. See [Pollard and Sag's HPSG tradition](https://www.cambridge.org/core/journals/language/article/abs/headdriven-phrase-structure-grammar-by-carl-pollard-and-ivan-a-sag-chicago-london-the-university-of-chicago-press-1994-pp-xi-440/DD568392A002418237880F90AC188B02).

Modern task-oriented dialogue research also shows why flat intent/slot approaches struggle with complex compositional requests. Hierarchical semantic parsing addresses this by representing nested structure rather than one intent and token-level slots. See [Gupta et al., 2018](https://arxiv.org/abs/1810.07942).

## 4. Port Definition

```typescript
interface OperationalPort {
  port_id: string
  owner_atom_id: string
  port_key: string
  accepted_atom_kinds: AtomKind[]
  accepted_parent_atoms: string[]
  required_edges: EdgePattern[]
  forbidden_edges: EdgePattern[]
  causal_role?: "cause" | "effect" | "precondition" | "enabler" | "blocker"
  temporal_policy?: TemporalPolicy
  evidence_policy?: EvidencePolicy
  resolver: ResolverPolicy
  confidence: number
}
```

## 5. Dynamic Resolution

Port resolution should be graph-native:

```text
given atom A with open port P
search working graph for candidate atoms
score by type, inherited concept, edge compatibility, context, source, time
bind best candidate if confidence passes threshold
otherwise create placeholder atom or ask repair
```

Resolution algorithm:

```text
1. Read owner atom's port definition.
2. Collect graph candidates from current group.
3. Expand candidates using concept lattice inheritance.
4. Score candidates by accepted kind, parent concept, source, time, and edge fit.
5. Bind with `has_role` or a more specific edge.
6. If no candidate fits, predict likely filler type.
7. If action requires certainty, ask a repair question.
```

## 6. Recursive Resolution

Ports can resolve into atoms that have ports.

Example:

```text
president.domain -> country
country.leader_role -> president
leader.authority_scope -> governance
governance.effects -> policy_state_change
```

This creates recursive causal explanation:

```text
Why can a president govern?
because president is_a leader
leader has authority over domain
authority enables governance actions
governance actions cause policy/state changes
```

No special case is needed for `president`.

The system resolves through existing atoms.

## 7. Port Matching Score

```text
score =
  kind_match
  + inheritance_match
  + edge_pattern_match
  + construction_support
  + source_trust
  + temporal_fit
  + discourse_salience
  - contradiction_penalty
  - freshness_penalty
```

This keeps resolution dynamic and efficient.

## 8. Examples

### President

```text
Atom president
inherits leader
ports:
  holder: person
  domain: country | organization
  time_scope: time
```

Utterance:

```text
Donald Trump is the current president of the USA
```

Resolution:

```text
holder -> Donald Trump
domain -> USA
time_scope -> current/now
evidence_policy -> fresh-world-sensitive
```

### Cold

```text
Atom cold
ports:
  holder: entity | environment
  intensity: quantity
  place: place
  time: time
  possible_effect: discomfort
```

Utterance:

```text
it is very cold where I am
```

Resolution:

```text
holder -> environment_near_user
intensity -> very
place -> user_location_unknown
time -> now
possible_effect -> user discomfort
```

Runtime:

```text
acknowledge, possibly infer need, do not treat as weather query unless user asks
```

## 9. Debloating Effect

Without ports:

```text
many domain-specific slots
many duplicate schemas
many special-case rules
```

With ports:

```text
few atom kinds
many reusable atom-owned interfaces
dynamic binding
recursive explanation
compressed concept lattice
```

## 10. Implementation Direction

Add:

```text
cemm/types/operational_port.py
cemm/kernel/port_resolver.py
cemm/memory/port_lattice.py
```

Core class:

```python
class PortResolver:
    def resolve(graph, atom, port, context) -> PortBinding:
        ...
```

Never implement port filling as:

```text
if atom == "president": fill president slots
```

Always implement:

```text
read atom ports -> resolve through graph and concept lattice
```

## 11. Design Rule

Ports are not fields.

Ports are operational openings in an atom that let the semantic CPU bind, predict, explain, and act.
