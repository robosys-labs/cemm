# Public composition: independent recheck and limits

The archived v2 diagnostic was rechecked from the retained per-case ZIP.
All 6,400 forecast MAP results, truth probabilities and categorical Brier
scores were recomputed. The first-contact 40/64 and second-contact 58/64
fixture-specific majority limits were also reproduced. Independently
reconstructing the public simulator's dynamics reproduced all 1,600
post-action truths. This checks the opened fixture and its implementation;
it does not create an independently authored oracle or a G1 challenge.

## A further asymmetry in training information

The flat learner's sensor likelihood marginalizes unobserved bits. In its
64 training histories, each contact supplies 128 participant-bit targets
and leaves 64 nonparticipant bits unobserved; each set supplies 64 targets
and leaves 128 nonparticipant bits unobserved. Each inserted observation
supplies 128 participant-bit targets and leaves 64 other bits unobserved.
No three-entity post-action world is directly supervised. This does not mean
the flat model cannot infer persistence from other evidence. However, the
structured model and local event control are explicitly supplied persistence
for nonparticipants, so their training and inductive information differ.

In the archived flat predictions, the number of cases with at least one
incorrect nonparticipant bit is shown below. A forecast can also be wrong on
participants, so these counts cannot be added to other error counts or used
to estimate how many errors a persistence intervention would fix. These are
post-hoc descriptions of the same 64 public cases per seed, not independent
trials. Values refer to the projection of each complete-world MAP prediction.

| Action | Seed 7 | Seed 11 | Seed 23 | Seed 37 | Seed 53 |
|---|---:|---:|---:|---:|---:|
| First contact | 8 | 16 | 16 | 24 | 16 |
| First set | 42 | 46 | 36 | 38 | 40 |
| Second contact | 38 | 24 | 32 | 26 | 30 |
| Second set | 48 | 38 | 47 | 38 | 46 |

These observations do not identify a cause of the flat model's failures.
ID-slot exposure, observation ordering, objectives, available supervision,
model biases and compute all differ. A consistent identifier-renaming probe
can measure sensitivity to slot assignment on the opened cases, but cannot
alone assign a causal share of the performance gap. G1 remains HOLD / REVISE;
matched controls and a fresh independently authored and held challenge are
still required.

## Post-hoc persistence lift

As a descriptive counterfactual, the archived flat joint distribution was
summed over nonparticipant bits. The resulting participant distribution was
combined with the most recent *delivered* reading for each nonparticipant,
assuming that reading persisted, and then scored by complete-world MAP. All
required readings were available and this supplied assumption matched the
nonparticipant truth on these noiseless public contact/set cases. It would not
necessarily hold with stale, noisy or changing nonparticipant state.

| Seed | Archived flat correct / 256 | With supplied persistence / 256 |
|---|---:|---:|
| 7 | 52 | 146 |
| 11 | 65 | 126 |
| 23 | 66 | 155 |
| 37 | 67 | 149 |
| 53 | 74 | 169 |

This transformation changes the distribution and can also change the chosen
participant assignment; it is not simply overwriting the old MAP. It was
selected after observing results and adds an explicit assumption rather than
showing the flat model learned it. It is neither an independent challenge nor
a matched-compute comparison. No originally correct contact/set forecast
became incorrect under this transformation on these cases.

The reproducible archive-only calculation is `python -m
experiments.predictive_nucleus.persistence_lift_audit`. It verifies the ZIP
hash and emits every original case together with the counterfactual scores;
the projected distribution is normalized to account for small floating-point
rounding in the archived probabilities.

## Next control and identifier probe

`HistoryMemory` memorizes exact literal-ID action and sensor prefixes using
only complete post-action sensor readings. It does not infer missing bits and
abstains on unseen prefixes. The current 64 training episodes contain **zero
complete three-entity post-action readings in 320 events**, so this exact
control abstains on every query for that corpus. It is not yet the strong
baseline required by the roadmap; a usable observation schedule or a clearly
declared persistence assumption is still needed.

`python -m experiments.predictive_nucleus.relabel_diagnostic` refits the
frozen public protocol and replays the same cases under all six consistent
permutations of their existing ID strings. Joint distributions are mapped
back before total variation is measured, with MAP ties reported separately.
It checks archived input, weight and identity-forecast fingerprints and labels
the refit accordingly. This post-hoc test probes ID-slot sensitivity on opened
cases; it neither tests new identifiers nor proves the cause of a model gap.
