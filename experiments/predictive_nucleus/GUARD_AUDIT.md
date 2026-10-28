# G1d-e: evidence persistence and paired selective-risk audit

**Decision: G1 remains unadmitted.** This is an isolated development experiment,
not a new world model, a physical-fault diagnosis, or an independent challenge.

## Why

The v4 public development run saw conflict in 90% of switch-orientation worlds
and 66% of bilateral worlds, yet its evaluator only carried the generic alarm
into the final eligibility decision. `EvidenceBelief` exposes its latest
diagnostic; a subsequent ordinary or missing observation can replace a prior
conflict. The new **opt-in episode guard** retains such a conflict for the rest
of that episode. It neither edits the belief nor decides that physics changed.
There is deliberately no automatic clearing rule in the experiment.

Another v4 measurement issue was that the rounded marginal-bit prediction was
scored against confidence from the highest-probability *joint* world. Correlated
beliefs can make those two predictions different. The new report instead uses
the joint maximum-probability world and its own probability, while retaining
all existing legacy fields and leaving the old protocol locks untouched. Its
new numbers should not be treated as numerically identical to historical v4.

## What is compared

Both policies use **one trajectory**, the same trained/calibrated kernel, probe
actions, observations, posterior and joint-world prediction. The legacy policy
uses the latest belief decision and its generic alarm. The guard uses that same
belief decision plus a latched conflict or mixed-process alarm. It cannot change
the physical action or the unconditional prediction. It reports four case-level
eligibility transitions: wrong and correct answers newly blocked, and wrong and
correct answers newly covered. Coverage, wrong covered per all queries, error
among covered queries, correct answers abstained per all queries, raw exactness,
joint NLL, Brier, joint-MAP ECE, sensor/probe costs and guard-record latency are
reported per scenario and optimizer seed. The paired answers are two role orders
for each world; five optimizer runs reuse the same worlds and are not independent
world samples. After the first audit revealed persistent covered errors, the
report was extended to include the initial anchor, observed probe trace, target
action, predicted world and evaluator-only truth for each covered wrong case.
This post-result instrumentation does not change the policy or world seeds.

## Statistical and measurement limits

The guard mixes the **existing** uniform-reference and reset-reference
prequential e-processes with fixed weights of one half. Under a common correct
conditional forecast, independent calibrated sensor noise, outcome-independent
missingness and precommitted coverage, their mixture is an e-process, so its
own ever-crossing threshold has the stated nominal alpha. This is not the same
as simply OR-ing two alpha=.05 alarms. The conflict heuristic is not covered by
that bound, and sensor misspecification invalidates it. An alternative with a
zero e-value stays at zero; an impossible null observation still gives the
generic process infinite evidence. No alarm identifies physics versus sensor
failure or grants authority to learn, update, or act.

The legacy policy still has its generic alpha=.05 alarm; the mixture has a
different threshold. Consequently the new policy is **not** guaranteed to be
a subset of legacy coverage: it can newly cover a legacy-abstained error. All
such transitions must be reported, not hidden behind a selective accuracy.
Conflict latching can also discard correct predictions until the episode ends.
Instrument calibration, temporal risk after the last probe, and attribution are
not solved by this guard.

## Reproduction and provenance

`guard_protocol_v5.json` and its SHA256 lock were created before running v5.
The run reports the already opened v4 worlds and a different set of new public
v5 world seeds. The new worlds still share developer-authored physics families,
and are not externally custodied or blind. The original sealed G0 challenge is
not opened. During initial implementation a toy-kernel structural smoke test
also exercised the first v5 lineage in each scenario; only assertions about
result shape and probe limits were inspected. The test now uses separate
synthetic lineages. CI executes:

```sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.guard_trial \
  --train 600 --calibration 200 --worlds 10 --steps 200 --seeds 7,11,23,37,53
```

Any alternate budget is labeled noncanonical. No model training uses v4/v5
results. Remaining gate blockers include an independently held challenge,
parameter/compute-matched flat recurrent baseline, validated instruments and
case-level failure review. G2–G5 and production integration remain out of scope.
