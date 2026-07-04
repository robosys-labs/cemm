# Dynamic Affordances And Effects

Purpose: clarify whether fields like `possible_effect: discomfort` are static schemas or dynamically composed learnable relations.

## 1. Short Answer

`possible_effect` should not be a universal static port that applies the same way to every atom.

It is better modeled as a **causal affordance**:

```text
contextual condition -> probable effect
```

For `cold`, discomfort is not always implied.

```text
cold weather -> possible discomfort
cold drink -> desirable refreshment
cold person -> low body temperature / health risk
cold reply -> social/emotional evaluation
cold storage -> preservation
```

So `possible_effect` must be dynamic, contextual, and learnable.

## 2. Port vs Affordance vs Effect

| Structure | Meaning | Example |
|---|---|---|
| Port | Role opening that needs a filler | `cold.holder`, `cold.intensity`, `cold.place` |
| Affordance | What the atom enables or tends to support | `cold_environment enables discomfort_risk` |
| Effect | Predicted state change from a process or condition | `exposure_to_cold causes body_temperature_decrease` |
| Policy | Runtime handling rule | `user_state_report does not require external verification` |

Do not put all of these into "ports."

Ports bind structure.

Affordances predict possibilities.

Effects model causal change.

Policies guide action.

## 3. Cold Example

The shallow representation:

```text
Atom cold
ports:
  holder: entity | environment
  intensity: quantity
  place: place
  time: time
  possible_effect: discomfort
```

The deeper representation:

```text
cold:
  kind: state/quality concept
  ports:
    holder: entity | environment | object | utterance
    intensity: quantity
    domain: temperature | social | emotional | storage
    place: place
    time: time
  affordances:
    if domain=temperature and holder=user_environment and intensity>=moderate:
      predicts discomfort_risk
    if domain=temperature and holder=drink:
      predicts refreshment_affordance
    if domain=social and holder=reply/person:
      predicts emotional_distance
    if domain=storage and holder=food:
      enables preservation
```

## 4. Dynamic Composition

Affordances are composed from:

```text
atom identity
bound ports
inherited parent concepts
construction context
source
time
place
intensity
user state
known causal patterns
```

Example:

```text
User: it is very cold where I am
```

Graph:

```text
State(cold)
  holder = environment_near_user
  intensity = very
  place = user_location_unknown
  time = now
```

Affordance prediction:

```text
cold_environment + high_intensity + near_user -> discomfort_risk
```

Action:

```text
acknowledge state
possibly suggest warmth
do not answer as weather query unless asked
```

## 5. Learning Affordances

CEMM should learn affordances from repeated graph patterns:

```text
condition graph
-> subsequent state/effect
-> repeated across sources
-> causal affordance candidate
-> promote if useful and supported
```

Example transcript patterns:

```text
I am cold -> I need a sweater
it is cold here -> I am freezing
cold drink -> refreshing
cold answer -> rude / distant
```

Consolidated:

```text
cold has multiple domain-conditioned affordances
```

## 6. Causal Affordance Object

```typescript
interface CausalAffordance {
  affordance_id: string
  trigger_pattern: GraphPattern
  required_bindings: PortBindingPattern[]
  predicted_effect: GraphPatchTemplate
  effect_type:
    | "state_change"
    | "need_activation"
    | "action_enablement"
    | "action_prevention"
    | "evaluation_shift"
  confidence: number
  source_support: SourceSupport[]
  counterexamples: GraphPattern[]
}
```

## 7. Why This Matters

If `possible_effect` is static, CEMM becomes brittle:

```text
cold -> discomfort
```

This fails for:

```text
cold water
cold storage
cold logic
cold color
cold person
cold response
```

If affordances are dynamic:

```text
cold + domain + holder + context -> likely effect
```

Then the system learns the structure behind the word.

## 8. Relation To Operators

The Semantic CPU should use:

```text
BIND -> fill ports
INHERIT -> pull parent affordances
PREDICT -> activate possible effects
COMPARE -> check if later events confirm
COMPRESS -> promote recurring effect
```

Affordance activation is a prediction, not truth.

## 9. Design Rule

Use static slots only for kernel mechanics.

Use dynamic causal affordances for meaning.

In other words:

```text
possible_effect is not a port.
possible_effect is an affordance prediction produced by operators over bound ports.
```
