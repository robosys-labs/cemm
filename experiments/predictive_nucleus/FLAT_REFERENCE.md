# G1g: flat recurrent reference

> **Audit hold:** The nonzero sensor-error input is untrained, training sensor
> geometry differs from stress probes, and historical joint log loss is
> clipped. See [the integrity audit](2026-10-28-AUDIT.md).

**Public development only; G1 is not admitted.** The roadmap requires a flat
recurrent comparison before interpreting the shared nucleus as an architectural
advantage. This reference sees sensor observations and ordered actions, not
hidden orientation, simulator rules, complete future state, or gold labels.

The flat model is a single GRU and joint-world output layer: **1,457 trainable
parameters**, compared with **1,446** in the learned contact kernel. Its fixed
input contains observed bits and masks, valid opaque-ID slots, ordered action
participants, action kind, set value and the same supplied sensor-error rate.
Missing observations are masked, not interpreted as zero. A 64-way output is
marginalized over padded and unobserved state bits. IDs are sorted opaque
handles; neither their spelling nor their ordering represents semantic roles.

Both models train on the **same generated sensor-visible training episodes**
and use the same separate calibration episodes. Their objectives are different:
the nucleus uses complete observed participant pairs for contact learning and
observed set outcomes; the flat model predicts all available post-action sensor
bits, including observed nonparticipants and observation-only steps. It may
therefore use more of the same raw sensor records. Both use Adam and a maximum
of 200 optimizer steps. The structured fit is timed on one CPU thread and the
flat fit stops before the estimated next step exceeds that measured budget;
the actual time, any overshoot, and the exact number of flat steps are recorded.
This is an **approximate wall-time match**, not a FLOP-equivalent compute match.
Preprocessing and calibration are separately timed. Time-dependent scheduling
can vary by run; `--flat-steps` replays a recorded per-seed optimizer schedule.

The structured model's bounded analytic joint belief and probe planner have no
trainable parameters but do consume inference time and memory. The flat model
replays the *same structured-selected physical actions and sensor outcomes*;
it does not choose its own probes. It receives the same assumed sensor error
metadata, but training examples only contain zero-error reference sensors,
while the structured filter explicitly uses the supplied likelihood model.
These asymmetries matter when interpreting a result. Target latency reports the
structured decision and subsequent forecast (two previews), versus one flat
preview; they are named separately rather than presented as equal work.

The v7 manifest and SHA256 lock predeclare new public world seeds; opened v6
worlds are separately reported. Both remain developer-authored physics
families, and the five model seeds share the same world lineages. The sealed
G0 challenge is not opened. Each model's raw joint-MAP accuracy, both-direction
accuracy, joint NLL, Brier, ECE, coverage, covered errors, paired case IDs,
physical probe budget and measured costs are reported for every seed/stratum.
The structured episode and context guard decisions are also reported; the
flat model uses its calibrated joint-MAP probability threshold only.

```sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.flat_trial \
  --train 600 --calibration 200 --worlds 10 --steps 200 --seeds 7,11,23,37,53
# Replay a recorded five-seed flat-step schedule, for example:
python -m experiments.predictive_nucleus.flat_trial --flat-steps 10,10,10,10,10
```

Do not claim equal FLOPs, a stronger independent baseline, generalization to
language, or a G1 gate pass from this diagnostic. Independent challenge
custody, tighter compute accounting and validated instruments remain required.
