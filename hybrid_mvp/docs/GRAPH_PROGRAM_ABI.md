# Graph-Action and Proposition Program ABI

## 1. Persistent semantic kernel

Only five operators are persistent:

```text
op:designation
op:type
op:relation
op:state
op:event
```

`intent`, `proposition`, `query`, `command`, `definition`, and `rule` are not extra semantic operators.

## 2. Graph actions

A candidate is a bounded sequence of transient construction actions. Representative actions include:

- set mode;
- create application;
- bind role;
- bind literal;
- bind variable;
- bind child application;
- set root;
- project variable;
- attach scope/qualifier;
- request or simulate a transition;
- complete graph.

The exact compiler—not the model—turns these actions into a proposition graph.

## 3. Proposition graph

A graph contains:

- one to 24 applications;
- one exact root application;
- maximum depth 6;
- exact application refs;
- role bindings;
- stance and qualifiers;
- projected variables;
- mode and transition metadata;
- source-coverage evidence.

Application-valued roles use:

```json
{"app": "application-ref"}
```

The verifier rejects:

- absent child refs;
- recursive cycles;
- malformed roles;
- projections absent from the graph;
- a sixth operator;
- illegal semantic refs;
- illegal event/state/relation roles.

## 4. Recursive attribution

Example:

```text
app:say = EVENT(
  type=event:say,
  actor=entity:mary,
  content={app: app:leave}
)

app:leave = EVENT(
  type=event:leave,
  actor=entity:bob
)
```

The graph is structurally recursive but bounded and acyclic.

## 5. Capability as a graph query

`can you learn?` is not a capability intent label. It becomes a recursive graph:

```text
app:learn = EVENT(type=event:learn, actor=participant:system, content=?content)
app:admissible = STATE(
  subject={app: app:learn},
  dimension=dim:admissibility,
  value=?admissible
)
```

The evaluator checks reviewed capability, permission and adapter dependencies for the candidate event.

## 6. Source coverage

Every candidate identifies which evidence units it covers. Unknown literal units must be:

- bound to a legal literal role;
- explicitly consumed by alias learning;
- or left residual, causing rejection.

Coverage is part of semantic governance, not only a model feature.
