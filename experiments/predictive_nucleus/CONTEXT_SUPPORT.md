# G1f: observed state-action context coverage

**Status: public research diagnostic; G1 remains unadmitted.** The prior v5
audit found confident bilateral failures where the target contact's ordered
input state had never been physically observed. This tranche tests a general
coverage signal, not a bilateral-specific rule or a learned new mechanism.

For one episode, a contact context consists of its action kind and the ordered
sensor readings of its two participants *before* the action. A context counts
only when both inputs were already observed and both participant outcomes are
actually received after the committed action. Contexts are shared across
same-kind entities; the order of action slots is retained. Duplicate receipts
cannot add evidence, missing readings are not zeros, and a pending action does
not count as an observation. After an action, readings for its participants
expire until actual feedback refreshes them.

The target action is eligible only if the existing episode guard already
allows it and this ordered context was observed earlier. The policy reads no
oracle, world family, transition table, future target result or inferred gold
state. It never alters the underlying model, posterior or physical probes.
The comparison is paired on one trajectory, with identical joint-MAP
predictions, sensor observations and realized physical action counts.

This support is **not a correctness certificate**. One observed transition
does not establish stable physics, particularly when mechanisms shift. Sensor
readings can be noisy or miscalibrated, so they are not verified world state.
The cache assumes that action effects are confined to the participants and
that a context can be shared across same-kind participants; both are supplied
inductive biases in the current sandbox and may fail outside it. There is no
learned relation, calibrated coverage guarantee, or automatic causal diagnosis.
These limitations and any loss of correct covered predictions must be reported.

`context_protocol_v6.json` and its checksum were created before the learned
model audit. It compares opened v5 worlds with separately seeded public v6
worlds. Both share developer-authored families, and the five optimizer seeds
reuse the same world lineages. They are **not** independently held blind tests.
The original G0 challenge stays unopened. Different budgets are labeled
noncanonical. Reproduce:

```sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.context_trial \
  --train 600 --calibration 200 --worlds 10 --steps 200 --seeds 7,11,23,37,53
```

The archived report contains baseline and context-gated coverage, covered
errors per all queries, error among covered predictions, correct abstentions,
per-case repairs/regressions, context reasons, physical/sensor costs and
context-update/assessment latency. No G2–G5 language work or production
runtime integration follows from this public diagnostic.
