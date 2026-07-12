# CEMM v3.4 — Foundational Reliability Acceptance Tests

Tests must assert structures and authority decisions, not only response strings.

## 1. Opaque relation preservation

Input:

```text
A dax is a wug.
```

Expected:

- lexical/schema refs may be created;
- user-attributed proposition persists;
- neither schema becomes active;
- no inheritance/effects/query definition are enabled;
- response does not claim understanding.

## 2. Claim count does not ground meaning

Inputs:

```text
A leader leads.
Leading is what a leader does.
A leader is a chief.
A chief is a leader.
```

Expected:

- circular dependency detected;
- no operational activation;
- support count cannot override closure failure.

## 3. Single complete definition may suffice structurally

Provide one definition containing semantic family, required roles, constitutive pattern, grounded dependencies, and differentiator.

Expected:

- semantic closure may pass from one utterance;
- confidence/scope remains governed by evidence policy;
- structural sufficiency is not blocked by an arbitrary two-fact minimum.

## 4. Parent grounding gate

Input:

```text
A president is a leader.
```

with opaque `leader`.

Expected:

- relation remains attributed/deferred;
- no inherited role/effect/query behavior;
- `understands(self, president)` and `understands(self, leader)` are false/not supported.

## 5. Child differentiator gate

Ground `leader`, then teach only:

```text
A president is a leader.
```

Expected:

- president may become typed as a candidate specialization;
- it does not become a complete non-synonym definition without differentiating constraints;
- system asks or records a gap for the distinguishing condition.

## 6. Role bearer separation

Input:

```text
Ada is the president of Club C.
```

Expected:

- Ada is an instance referent;
- president is a schema ref;
- role occupancy connects Ada, role, context, and time;
- instance and schema identities never unify.

## 7. Understanding versus remembering

After only the opaque assertion:

```text
Do you know what a president is?
```

Expected response semantics:

```text
remembers(self, user_assertion)
NOT understands(self, president_schema)
```

## 8. Ordinary replay proof

After completing `leader` and `president` definitions:

- original Turn 1 is replayed through normal composer/grounder/resolver;
- no special learning resolver is invoked;
- exact relation type is selected;
- competence tests pass before activation.

## 9. Boot concepts are ordinary schemas

For `person`, `agent`, `software_system`, and other boot concepts:

- records have boot provenance;
- grounding specifications exist;
- startup validation executes;
- no hard-coded domain Python type is required for meaning.

## 10. No new authority

Architecture test fails when any component outside `SemanticSchemaStore` can mark a schema active or independently determine executable understanding.
