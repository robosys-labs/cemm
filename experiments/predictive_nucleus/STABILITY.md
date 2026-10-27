# G1d-d — temporal validation / falsification before language

**Why this exists:** The public G1d v3 stress test exposed only **2%**
complete-world accuracy and **zero generic model-mismatch alarms** when
interaction orientation changed *after the first contact*. The active probe
typically stopped after that first contact, leaving no observation of the
change before the hypothetical next prediction. No posterior can identify
an unobserved future change with certainty.

**Proposed mechanism:** after an informative probe has made one anonymous
mechanism sufficiently likely, use a *different objective* for one additional
physical observation. Choose the candidate contact whose **predicted sensor
outcomes** differ most between (a) the current persistent-mechanism belief and
(b) a read-only counterfactual belief that preserves the entire world-state
distribution but resamples the anonymous mechanism. Score this difference as
total variation, including the declared sensor error channel. Nothing in the
learner imports the evaluator's switch time or new physics.

Validation proposals are read-only. No effect is authorized until the
isolated lab actually executes a physical contact and returns sensor evidence.
Counterfactual resets are **not** admitted as actual world state; they are
forecast comparators, not teaching labels or an automatic ontology update.

The monitor may score a second, **predictable** likelihood-ratio e-process
using the reset-hypothesis forecast as its alternative instead of a uniform
binary reference. A change-point alarm is still **evidence against fixed-mode
forecasts**, not proof of physics changes. Instrument miscalibration or correlated
sensor faults can also trigger it; compare the separate sensor-failure stratum.

## New experiment, not retroactive repair

G1d v3 worlds (601,607,613,617,619) are now **opened development examples**.
The mechanism and experiment were declared before v4 results under
\`stability_protocol_v4.json\` with a distinct SHA256 lock and *new public*
world seeds (701,709,719,727,733). These are **not externally authored blind
challenges**; the model is still trained only on original reference outcome
episodes and frozen calibration seeds. No post-result threshold retuning.

The added policy uses at most two actual contact/set actions:

1. Request a role-informative probe if role belief remains uncertain.
2. Once role belief is sharp, use a *falsification* contact when predicted
   sensor outcomes distinguish fixed vs reset hypotheses.
3. If no physical probe can distinguish mechanisms, abstain from asserting
   temporal reliability; no fake validation or oracle peek.

Report paired exact full-world success, both role orders, NLL/Brier/ECE,
coverage and confidence, change-point and generic alarms, conflicting
evidence, extra validation cost, and exact case IDs newly won or broken.
Compare with original role-IG-only active policy and random contacts executed
on the **same starting world at the same number of physical actions actually
used by temporal validation**. Active-vs-original is not cost matched when
the original stops earlier; do not confuse its lower step count with a fair
accuracy comparator.

The next threshold is **not** the result of this public dev test: require an
independently held new challenge, a parameter/compute-matched flat recurrent
control, and robust sensor-calibration failure detection. A second probe
cannot guarantee knowledge of a mechanism that will shift only after that
probe. Retain residual uncertainty. No G2–G5 or production runtime cutover.

**Status: DRAFT RESEARCH / G1 NOT ADMITTED.**

Run:

    python -m unittest discover -s experiments/predictive_nucleus/tests -v
    python -m experiments.predictive_nucleus.stability_trial \
      --train 600 --calibration 200 --worlds 10 --steps 200 \
      --seeds 7,11,23,37,53
