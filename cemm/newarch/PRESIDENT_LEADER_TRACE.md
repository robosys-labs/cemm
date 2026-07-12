# Canonical Trace — “A President Is a Leader”

## Initial state

Assume the English lexical forms `president` and `leader` have no executable schema definitions.

## Turn 1

```text
User: A president is a leader.
```

### Compose

Create:

```text
lexeme sense candidate: president → provisional schema ref P
lexeme sense candidate: leader → provisional schema ref L
classification/relation hypotheses:
  subtype_of(P, L)
  subrole_of(P, L)
  bearer_implication(P, L)
  synonym_or_paraphrase(P, L)
```

### Ground

```text
P definition usability = opaque
L definition usability = opaque
semantic families unresolved
exact relation unresolved
```

### Resolve

Select the communicative meaning:

```text
asserts(user, relation_hypothesis(P, L))
```

Do not select an executable inheritance relation.

### Commit

Permitted:

```text
store user-attributed proposition
store lexical references
store candidate relation evidence
```

Forbidden:

```text
activate P or L
inherit L into P
claim CEMM understands either term
```

### Honest response

> I’ve recorded that you describe a president as a leader, but I do not yet have a grounded definition of “leader” or enough information to determine the exact relation.

## Turn 2

```text
User: A leader is someone or something that directs a group toward a goal.
```

### Target discrimination

This is a partial schema definition for L, not merely an instance fact.

### Candidate structure

```text
schema family hypothesis: role-like concept
eligible bearer: agentive entity
context: group + goal
constitutive pattern: directs_toward(bearer, group, goal)
occupancy pattern: occupies_role(bearer, L, context, interval)
```

`agentive entity`, `group`, `goal`, and `directs_toward` must already be grounded or produce their own concrete blockers.

### Validation

If dependencies are grounded and competence tests pass, L may activate.

Competence examples:

```text
Ada directs Team A toward Goal G → candidate role occupancy
Ada is merely a member of Team A → insufficient
What does a leader direct? → group/participants
What is leadership relative to? → group/activity + goal/context
```

## Deferred replay

Re-evaluate Turn 1 using grounded L.

P remains opaque. The relation is still not fully activated because CEMM must determine:

```text
Is president also a role-like schema?
What bearer/context does it require?
What differentiates it from generic leader?
Is the relation strict, contextual, or defeasible?
```

## Turn 3 probe

A semantic probe may be realized as:

> Is a president a formal role in an institution, and what makes that role different from other leaders?

## Turn 4

```text
User: A president holds a formally established office in an institution and has its defined presiding authority.
```

### Candidate P definition

```text
schema family: role-like concept
parent: L, if validated
eligible bearer: institution-eligible agent
context: institution
constitutive pattern: occupies_formal_office(bearer, institution, office)
authority pattern: has_presiding_authority(bearer, institution, scope)
differentiator: formal office + institution-defined authority
```

### Activation

P activates only if dependencies and competence checks pass.

### Resulting distinction

```text
leader:
  role relative to directing/coordinating a group toward a goal

president:
  institutionally constituted role
  inherits compatible leader structure
  distinguished by formal office and defined presiding authority
```

### Instance use

```text
Ada is the president of Club C.
```

creates a bearer-role occupancy predication. Ada remains the instance; president remains the schema.

## Final query behavior

```text
What is a leader?
→ grounded constitutive definition

What is a president?
→ inherited base + formal-office differentiator

Is every leader a president?
→ no; differentiating constraints are absent

Is every president a leader?
→ answer according to validated relation scope and evidence
```
