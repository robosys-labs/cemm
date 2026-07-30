# Comparison: Current CEMM, Earlier MVPs, and Authoritative Hybrid MVP

## 1. Design comparison

| Property | Current CEMM baseline | Deterministic true-hybrid demonstrator | Earlier neural MVP | Authoritative hybrid MVP |
|---|---|---|---|---|
| Five-operator exact kernel | Strong | Demonstrated | Exact wrapper | Strong |
| Reviewed semantic authority | Strong | Weak/in-memory | Small closed list | Immutable revision-pinned authority |
| Recursive multi-application graph | Present | Limited | No; one application | Present and tested |
| Bounded proof inference | Present | Minimal | No | Present with existential witnesses |
| Session lifecycle/obligations | Stage-oriented | Strong demonstration | Minimal | First-class isolated runtime |
| Real trainable neural component | Legacy/partial paths | No | Transformer flat parser | PyTorch text↔graph-action ranker |
| Neural owns truth | No | N/A | No | No |
| Dynamic alias reuse | Existing design intent | Demonstrated | Demonstrated | Governed and tested |
| Unknown atom manufacture risk | Exact store reduces risk | Confirmed defect | Closed labels | Explicitly prohibited and tested |
| Capability/permission/adapter split | Existing operational model | Partial | Capability only | All three exact and independently tested |
| Simulation isolation | Existing principle | Demonstrated | Demonstrated | Enforced and tested |
| Attribution isolation | Existing semantics | Not complete | No | Recursive and tested |
| Evaluation leakage disclosure | Existing tests | Demonstrator tests | Earlier synthetic leakage documented | Text/template/value-disjoint manifest plus composition holdout |
| Production coupling | Production runtime | Isolated | Isolated | Isolated |

## 2. What was retained from current CEMM

- exactly five semantic operators;
- bounded recursive proposition graphs;
- exact role and projection contracts;
- sparse bounded proof-bearing inference;
- transient existential witnesses;
- semantic authority rather than free-form atom creation.

The current repository describes proposition graphs as bounded, cycle-local structures over the five fixed operators, rather than a sixth operator or second store. The authoritative MVP preserves that principle.

## 3. What was retained from the true-hybrid proposal

- session as root event;
- direct opening and explicit closing;
- four semantic modes;
- obligation-driven dialogue;
- explicit effect ownership;
- simulation isolation;
- revision-pinned store separation.

## 4. What was retained from the neural MVP

- a real trainable PyTorch semantic proposal component;
- model artifacts separate from authority;
- structured semantic supervision;
- neural ranking rather than response-template selection;
- exact verifier downstream of the model.

## 5. Unsafe shortcuts excluded

### From the deterministic demonstrator

- automatic semantic ref creation from unknown nouns;
- mutable proposal-time authority/world state;
- phrase-specific meaning routes.

### From the earlier neural MVP

- one-application-only semantic output as the final architecture;
- fixed 12-target semantic authority as the long-term design;
- benchmark leakage being treated as true generalization;
- context supplied forever rather than eventually learned/retrieved;
- capability-only operational checks.

### From production legacy structure

- mandatory Stage 0–22 ordering as constitutional architecture;
- compatibility paths that can become parallel semantic authority;
- surface response tests as semantic acceptance.

## 6. Why this is a better MVP boundary

The MVP is small enough to run and inspect, but it contains the complete ownership skeleton needed for production evolution:

```text
reviewed authority
→ exact retrieval
→ trainable ranking
→ recursive exact graph
→ proof/effect engine
→ governed response meaning
```

Future neural capacity can expand without transferring truth or operational authority into model weights.
