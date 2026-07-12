# Canonical Grounded Trace — “A President Is a Leader”

This trace illustrates preservation, provisional structural learning, independent validation, context admission, and final differentiation without inventing user claims.

## Initial state

English lexical forms `president` and `leader` are recognized, but no executable sense is assumed.

The actual context, user-attribution context, boot foundation revisions, and environment fingerprint are pinned.

## Turn 1

```text
User: A president is a leader.
```

### Compose

Create lexical refs and separate candidate sense clusters:

```text
president → P?
leader → L?
```

Relation hypotheses remain separate:

```text
subtype(P, L)
role_specialization(P, L)
role-bearer implication
prototype/generalization
synonym/paraphrase
```

English `is` does not decide the relation.

### Ground and resolve

```text
P usability = opaque
L usability = opaque
semantic families unresolved
exact relation unresolved
```

Select only the attributed communicative meaning:

```text
asserts(user, relation_hypothesis(P?, L?))
```

### Commit

Permitted:

```text
lexical references
candidate sense refs/evidence assignments
user-attributed proposition
relation hypotheses
```

Forbidden:

```text
activate P or L
inherit L into P
actual-world classification
claim understanding
```

### Response semantics

```text
remembers(self, user_assertion)
uncertain_about(self, relation_type + definitions)
```

Possible realization:

> I’ve recorded that you describe a president as a leader, but I don’t yet have grounded definitions for those senses or enough information to decide the exact relation.

## Turn 2

```text
User: A leader is someone or something that directs a group toward a goal.
```

### What was asserted

The utterance supplies evidence for:

```text
possible semantic family: role-like or relational concept
constitutive candidate:
    directs_toward(bearer, group, goal)
lexicalization: “leader” → candidate sense L1
```

The user did **not** directly assert:

```text
formal role occupancy
agentive entity as a named superclass
appointment rules
termination rules
authority
```

If grounded `directs_toward` has selectional constraints, those may be inherited as constraints with `inherited` provenance. If the architecture proposes an occupancy pattern because role-like schemas require one, it remains `hypothesized` until supported.

### Grounding frontier

Required dependencies include exact senses of:

```text
directs_toward
group
goal
```

The transaction checks their use profiles. Missing items become typed gaps subject to the probe budget.

### Structural assessment

If dependencies are valid, the candidate may become structurally executable.

Teaching-derived examples may test role binding and query projection, but they cannot independently validate discrimination.

Therefore the first result is normally:

```text
L1 status = provisional
structurally executable = possibly yes
independently validated = no
actual-context admissibility = attributed/user theory unless other evidence exists
```

A truthful response can say:

> I can now use the definition you gave provisionally: a leader directs a group toward a goal. I haven’t independently validated that as a complete general definition.

## Independent competence

Independent cases may come from:

```text
audited role invariants
independently grounded sibling/contrast schemas
adapter observations
independently sourced expected semantic cases
```

Examples must not be generated solely from the teaching definition.

If required discrimination passes and epistemic policy admits the definition for a context, L1 may atomically activate.

## Replay Turn 1

The original relation evidence is replayed under the exact active/provisional L1 revision.

P remains opaque. Replay asks:

```text
Does president denote a role, office, bearer, or title in this use?
What context and bearer constraints apply?
What distinguishes it from L1?
Is the relation strict, defeasible, contextual, or merely attributed?
```

No inheritance activates yet.

## Turn 3 probe

A minimal probe may be:

> In your usage, is a president a formal role in an institution, and what distinguishes it from other leaders?

The question records expected semantic evidence, not expected English wording.

## Turn 4

```text
User: A president holds a formally established office in an institution and has its defined presiding authority.
```

### Asserted contributions

```text
formal office relation
institution context
presiding-authority relation
```

### Hypotheses to validate

```text
schema family: role-like/office sense
parent relation to L1
eligible bearer constraints inherited from grounded predicates
occupancy/tenure behavior if required by family
```

Only the first group is directly asserted. Every other field retains its provenance kind.

### Structural result

If dependencies and family requirements pass:

```text
P1 provisional structural definition:
    institutionally constituted office
    defined presiding authority
    differentiator from generic leader
```

Independent competence and actual-context admission are still evaluated separately.

### Relation to leader

The system may validate one of:

```text
strict role specialization in a declared institution class
defeasible leader implication
context-specific office/leadership relation
no universal implication
```

It does not force `subtype` from the original copula.

## Instance use

```text
Ada is the president of Club C.
```

represents:

```text
Ada = instance referent
P1 = role/office schema sense
Club C = context/institution referent
occupies_role(Ada, P1, Club C, time)
```

Ada and P1 never unify.

The predication is interpreted under the exact P1 revision active/usable at assertion time.

## Final query behavior

```text
What did I tell you about presidents?
→ attributed propositions regardless of actual-context admission

What does “leader” mean according to my definition?
→ qualified user-theory definition if provisional

What is a leader?
→ actual/admitted definition or qualified abstention

What is a president?
→ base structure + differentiator only if exact relation/admissibility pass

Is every president a leader?
→ answer from validated relation scope, default strength, context, and evidence
```

## Downgrade behavior

If `directs_toward`, L1, a competence oracle, or an adapter contract changes:

- L1 assessment invalidates;
- P1 inherited structure and dependent readings invalidate;
- classifications/answers/plans using them retract or stale;
- original user assertions remain;
- prior output remains historical and may require repair;
- no effect or operation proceeds on stale authority.
