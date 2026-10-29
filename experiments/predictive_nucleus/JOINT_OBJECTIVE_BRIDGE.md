# Common full-world objective and informative probe curriculum

**Tracking:** #22, draft #49, stacked on #48. **Date:** 2026-10-29.
**Decision:** KEEP the common-objective implementation; **G1 HOLD / REVISE**.
This is implemented training/data plumbing with invariant tests and one-update
wiring, not a completed model comparison, independent review or admission.
All historical studies, failures, frozen manifests, production code and PR #21
remain unchanged. The completed post-hoc replay is not rerun.

## Why this change

PR #48 established that the earlier structured/flat score gap was confounded
by targets, supplied persistence and identifier treatment. This tranche removes
the different-loss path from the NEXT comparison instead of adding another
analysis to the opened study. It does not relabel any historical result.

`joint_objective.py` has one sensor-only batch, forecast-before-feedback loop,
full-state negative log likelihood and Adam/budget loop. Both families predict
eight complete three-bit worlds. Every event, including sets and observes,
receives the same weight. There is no participant-only target, masked label,
separate intervention multiplier, clipping or post-hoc mass repair.

For the structured model, a forecast mixes two anonymous persistent hypotheses
using only earlier feedback. The current outcome updates that mixture AFTER
its forecast. A synthetic check proves equality of this sequential loss and
explicit whole-episode marginal likelihood, including parameter gradients.
The reduction over impossible worlds avoids the undefined gradient of an
all-negative-infinity logsumexp while retaining exact zero probability. An
observation contradicting supplied persistence is an error, not a repaired bit.

## Supplied biases are exposed, not called learned intelligence

| Arm | Parameters | Change / retained assumption |
|---|---:|---|
| Structured, supplied persistence | 470 | Two latent modes; swap-tied pair kernel; exact nonparticipant persistence |
| Structured, learned background | 584 | Learn nonparticipant bit transitions instead of forcing persistence |
| Structured, untied roles | 972 | Separate pair networks for the two modes; no swap tying |
| Structured, reset memory | 584 | Uniform mode prior at each action, rather than evidence accumulation |
| Flat | 648 | GRU over 14 active sensor/action features and eight joint outcomes |
| Flat, supplied persistence | 648 | The SAME support constraint as the structured persistence arm |

All structured arms still supply action locality, a two-mode mechanism family,
conditional factorization and identifier-equivariant parameter sharing.
**Untying roles is not an ID-equivariance ablation.** The tests verify that all
structured variants remain equivariant under all six identifier permutations.
Parameter counts are not matched; untying roles also increases parameters.
The flat model is deliberately unpadded, unlike the old 36-input/64-output
model. New results must not be compared to old scores as a one-factor change.
Neither family imports simulator rules, historical inference, gold mode labels,
future state or a pretrained teacher. Missing/partial readings are rejected;
this narrow path is not yet the partially observed or noisy-world comparison.

## Controlled information, with equal declared action cost

Each condition contains 128 openly enumerable factorial cases and six related
identifier views per case: 768 histories, NOT 768 independent worlds. Both
families receive the same realized history within a condition, verified with
input fingerprints. Every history contains seven actions and eight complete
three-bit readings, including the anchor. One update uses 5,376 event targets.

The supplied three-action probe sets A and B to one then contacts A,B in the
informative condition; the equal-action-cost control sets both to zero first.
Under this particular simulator's stable two-mode physics the first probe
reveals orientation and the second does not. This policy is authored using
known physics, NOT learned active acquisition. Costs are declared unit action
counts, not equal real-world duration, information quantity or energy.

Two more set actions cover all four query input states. The sixth action is the
query contact, in both participant orders; the seventh is observe. Training
queries reuse A,B. A public composition fixture queries B,C after the same
probe. Its labels have only been used for fixture feasibility, not model scores.

| Public final-contact fixture | Observable prefixes | Ambiguous prefixes | Maximum deterministic correct / views |
|---|---:|---:|---:|
| Informative, same pair | 768 | 0 | 768 / 768 (100%) |
| Uninformative, same pair | 384 | 288 | 480 / 768 (62.5%) |
| Informative, second pair | 768 | 0 | 768 / 768 (100%) |
| Uninformative, second pair | 384 | 288 | 480 / 768 (62.5%) |

These are finite-fixture frequency/identifiability bounds, **not learned
accuracies**. They create an identifiable comparison condition without deleting
the ambiguous control. The same simulator supplies both histories and this
feasibility check; this is not an independently authored oracle. All earlier
forecasts must remain in a later comparison, including ambiguous probe steps.
The post-probe query metric does not replace or weaken the G1 research gate.

## Checks and retained wiring evidence

Code commit: `4e39a54b1580d840d2d4ce5383b347c1f7647e88`.
The three uploaded file blobs were checked against the locally tested bytes.
There are 26 new tests. Local reconstruction from the retained `3493b3b` source
plus this tranche passed 283 tests (257 archived plus 26 new). The six audit
tests introduced at parent `596593b` were absent from that local archive; the
remote branch includes them and CI checks the actual complete branch.

`results/joint-objective-wiring-v1.json` retains source/input/initial/final-weight
fingerprints, one-update pre-update losses, parameter counts, measured CPU/wall
costs, ceilings, overshoot and host data. All six arms completed one update in
both conditions; all fingerprints were identical across a validation-only
repeat, and process RNG/thread/determinism settings were restored. No learned
accuracy, calibration, independent challenge, model selection or multi-seed
scientific comparison was run. Weight fingerprints are NOT saved checkpoints.

Report SHA-256:
`2c8f8cc0adac994eb04998c01425a45ea6a78a7ff98f296b455623e48833bb5d`.
Local host: Python 3.13.5, PyTorch 2.10.0+cpu, CPU float64, one intra-op thread.
The report states the local reconstruction accurately; it is not evidence of a
complete git checkout or cross-host bitwise reproducibility.

```sh
python -m unittest experiments.predictive_nucleus.tests.test_joint_objective -v
PYTHONHASHSEED=0 python -m experiments.predictive_nucleus.informative_curriculum
python -m unittest discover -s experiments/predictive_nucleus/tests -v
```

## Next comparison must be frozen before substantive fits or scores

Fix seeds, source/data hashes, all six arms and both information conditions.
Specify fixed-exposure and separately CPU-budgeted regimes: equal update counts
are not equal consumed compute, and equal CPU ceilings can produce different
numbers of exposures. The common fitter measures actual cost and last-step
overshoot; it does not certify a hard real-time limit or matched FLOPs.

Retain every checkpoint and raw forecast, specify failure handling, and report
all steps, post-probe complete-world predictions, proper scores on ambiguous
cases, reversed-role pairs, identifier sensitivity and correct-to-wrong changes.
Include useful empirical controls; the old exact-prefix controls had inadequate
coverage. Audit cross-fixture overlap before interpreting composition transfer.
The current public composition fixture is already opened and cannot become the
independent G1 challenge. A fresh independently authored and held challenge,
partial-observation/noise tests and calibrated uncertainty remain outstanding.

The new common path plus tests is **813 physical Python lines**. The complete
retained research namespace is **14,269** including historical studies, not below
the practical 2,000-line goal. This is a compact replacement path for upcoming
comparisons, not authorization to delete failed studies or hide dependency size.
