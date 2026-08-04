# End-to-End Runtime Traces

## 1. Direct substantive opening

Input:

```text
what can you do?
```

Flow:

1. session phase is `opening`;
2. closed-class query evidence and `capability` designations are retrieved;
3. capability-inventory action candidate is ranked;
4. exact relation graph is compiled;
5. query returns reviewed capability atoms;
6. session moves directly to `active`;
7. deterministic realizer produces capability surfaces.

No greeting is forced.

## 2. Learned synonym reuse

Teaching:

```text
yoz means hello
```

Program:

```text
DESIGNATION(
  target=event:greeting,
  label_type=label:lexical,
  surface="yoz"
)
```

Checks:

- `event:greeting` is reviewed authority;
- `yoz` is an explicitly consumed literal;
- alias-learning permission and adapter are present;
- proof and world revision are recorded.

New session:

```text
yoz
```

The exact world designation resolves to `event:greeting`; no retraining or form-pack regeneration occurs.

## 3. Capability question

Input:

```text
can you learn?
```

Recursive program:

```text
EVENT(
  type=event:learn,
  actor=participant:system,
  content=?content
)

STATE(
  subject={app:learn},
  dimension=dim:admissibility,
  value=?admissible
)
```

The verifier accepts the unspecified required content as a query variable. The evaluator checks reviewed runtime dependencies and returns `true` only when capability, permission and adapter requirements pass.

## 4. Unknown noun abstention

Input:

```text
do you have a telescope?
```

Flow:

- `telescope` has no reviewed or learned designation;
- it remains an unknown literal unit;
- no relation candidate can bind it to an authority-licensed entity;
- abstention/frontier wins;
- authority and world revisions remain unchanged.

## 5. Mother-in-law inference

Observation:

```text
Alice is Bob's mother-in-law
```

Admitted fact:

```text
RELATION(Alice, rel:mother_in_law, Bob)
```

Reviewed rule 1 derives:

```text
RELATION(Bob, rel:has_partner, exists:partner/...)
```

Reviewed rule 2 derives:

```text
STATE(Bob, dim:marital_status, value:married)
```

Query:

```text
is Bob married?
```

returns `Yes` with a proof tree containing both rules and the original observation. The existential partner ref is absent from durable world identities.

## 6. Attribution

Observation:

```text
Mary said Bob left
```

Recursive graph:

```text
EVENT(say, actor=Mary, content={app:leave})
EVENT(leave, actor=Bob, epistemic_scope=attributed)
```

Direct query:

```text
did Bob leave?
```

returns unknown because direct world matching excludes attributed child facts.

Attributed query can still return the report and its source proof.

## 7. Operation and simulation

Request:

```text
turn the lamp on
```

Checks:

```text
cap:set_state
permission:set_state
adapter:set_state
```

Only after all pass is `STATE(lamp, power, on)` admitted from an operation result.

Simulation:

```text
what if the server becomes online?
```

returns a state-effect preview. The world revision and admitted server state remain unchanged.
