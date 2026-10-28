# G1b — first shared predictive learner: unsealed validation only

**Status: diagnostic, not G1 acceptance.** The predeclared G1 gate remains
blocked by the identifiability counterexample in `WORLD.md`; no challenge seed
has been opened. This tranche adds a small learned, object-shared PyTorch model
and a causal train/validation runner, not a parser or a world oracle in disguise.

## What is learned and what is supplied

The `SharedWorldModel` receives only opaque IDs, observed (possibly partial)
binary states, ordered action operands, and the **later** observed sensor
feedback. It learns per-object transition logits from a shared MLP and maintains
an episode-level GRU state across observations. Its input has two positional
participant indicators and values but neither the hidden source orientation
nor action effects; those must be inferred through outcomes. All model
parameters are trained from BCE on **actually revealed next-observation bits**;
never from hidden post-state or `World.hidden_source_slot`. A test replaces
`gold_after`/`states` with raising accessors during training.

The evaluator, after prediction, compares separately supplied full-world states for
*all* entities, including those not revealed to the learner. A separate
persistence control uses its own observed-only memory, not the model's guesses.
No training on validation/calibration/challenge, no roles or event glosses from
CEMM runtime, no pretrained weights or inference-time teacher lookups.

## Reproducible diagnostic

```sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.train --episodes 1000 --validation-episodes 100 --seeds 7,11,23,37,53
```

Python 3.13.5, PyTorch 2.10.0 CPU, seed-initialized. 1,000 training episodes
per model seed on `train` world seed 101; 100 separate validation episodes
from `validation` world seed 211; topology alternating one/two contacts;
**150 contact predictions per seed**. Full-world exact accuracy (all entities):

| Model seed | Shared GRU/MLP | Observed-state persistence | Brier / entity |
|---:|---:|---:|---:|
| 7 | 68.00% | 48.00% | 0.05470 |
| 11 | 66.00% | 48.00% | 0.05423 |
| 23 | 68.00% | 48.00% | 0.05463 |
| 37 | 56.67% | 48.00% | 0.05684 |
| 53 | 65.33% | 48.00% | 0.05546 |
| **Mean** | **64.80%** | **48.00%** | — |

6,673 parameters, 1,000 gradient updates per seed, ~4.1–5.2 s CPU training
per seed on this local hardware; p95 forward-only per-step 0.24–0.46 ms.
RAM is reported by the runner (process peak RSS includes PyTorch runtime).
The hard 0/1 persistence control is an **exact-state baseline**, not a
calibrated probabilistic comparator; do not claim superiority in NLL without
calibration and stronger matched flat recurrent/memorization controls.

## Correct interpretation and next decision

There is evidence that a small shared learned transition predictor outperforms
naive persistence on this *unsealed, in-family validation cohort*, but it has
not reached 95% full-state accuracy and the worst optimizer seed is only 56.67%.
This validation uses one master world seed per split and does **not** measure
OOD topologies, exact reversed-role pairs, or sealed challenges. Some
first-contact cases cannot be known deterministically without orientation
evidence, regardless of training. No G1 success, general cognition or release
claim follows. **Decision: retain the diagnostic model; REVISE protocol to
separate identifiable/post-probe exactness from genuinely unidentifiable
probabilistic cases; then run a fresh frozen challenge and matched controls.**
