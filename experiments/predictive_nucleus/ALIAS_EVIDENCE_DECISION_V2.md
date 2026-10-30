# Alias evidence v2: KEEP_EVIDENCE_FIX

The fresh paired experiment passed its frozen five-seed criteria. **Keep the
observed acquired-alias curriculum with the existing model. G1 remains
NOT_ADMITTED.** The original 95% all-action target is unchanged, and no later
scientific gate is complete.

The [continuation-v1 STOP](CONTINUATION_DECISION_V1.md) and
[alias-v1 REVISE](ALIAS_EVIDENCE_DECISION_V1.md) remain unchanged. Both alias
studies were executed once with separately committed fresh inputs and weights;
the opened v1 bank was not refitted.

## Measured result

| Seed | Ordinary-only self | Acquired-alias self | Continuation, each arm | Role pairs, each arm |
|---|---:|---:|---:|---:|
| 7 | 8/16 | 16/16 | 704/704 | 136/136 |
| 11 | 8/16 | 16/16 | 704/704 | 136/136 |
| 23 | 8/16 | 16/16 | 704/704 | 136/136 |
| 37 | 8/16 | 16/16 | 704/704 | 136/136 |
| 53 | 8/16 | 16/16 | 704/704 | 136/136 |

Treatment scores **8/8 on each starting bit at every seed**. Ordinary controls
score 8/8 starting-zero and 0/8 starting-one. The paired gain is exactly **50
percentage points at all five seeds**, exceeding the frozen 20-point mean-gain
criterion. There are **40 self repairs, zero self regressions and zero
continuation MAP regressions**. All self/continuation predictions have support
and zero unchanged-bit errors. Continuations include all 672 OOD queries per
seed. Every one of the 13,520 planned forecasts was produced and scored; there
were no abstentions, terminal failures or incomplete inventories.

These are five initializations on the same public bank. Related views and query
positions are not independent physical worlds. Exactness under delivered
feedback is not free-running rollout success.

### Proper scores and all-action changes

| Scope and metric | Ordinary | Acquired alias |
|---|---:|---:|
| Self exactness | 40/80 (50%) | 80/80 (100%) |
| Self mean joint NLL | 2.448227940 | 0.011322738 |
| Self mean joint Brier | 0.975370319 | 0.000247953 |
| Continuation exactness | 3,520/3,520 | 3,520/3,520 |
| Continuation mean joint NLL | 0.006229735 | 0.008788209 |
| Continuation mean joint Brier | 0.000062993 | 0.000153956 |
| All-action exactness | 5,905/6,760 (87.352071%) | 5,999/6,760 (88.742604%) |
| All-action mean joint NLL | 0.190019059 | 0.162614091 |
| All-action mean joint Brier | 0.124009251 | 0.112563510 |
| All-action unchanged-bit errors | 290 | 473 |

Continuation proper scores become slightly worse despite unchanged MAP
exactness. The preservation claim is therefore specific to the frozen accuracy,
support and unchanged-bit criteria; it is not a claim of universal improvement.

Across all actions there are **277 repairs** (40 self and 237 acquisition) and
**183 regressions**, all of the latter at ambiguous first-acquisition points.
All-action unchanged-bit errors likewise occur at ambiguous acquisition points.
The selected MAP world can differ from the realized hidden orientation even when
both are compatible with the delivered evidence. These errors remain counted.
The alias arm scores 5,240/5,240 on oracle-identifiable actions and 759/1,520 on
ambiguous actions; ordinary scores 5,200/5,240 and 705/1,520 respectively.

Each seed has 304 ambiguous first acquisitions among 1,352 actions. Under the
declared balanced mode prior, expected best all-action exactness is
`1 - 0.5 * 304 / 1352 = 88.75739645%`. This is an information-design expectation,
not a finite-realization bound, a learned-model score, or permission to replace
the historical 95% target. Neither this study nor its KEEP admits G1.

## Exact diagnosis and smallest correction

The original self-contact extrapolation used supplied per-mode diagonal
conditioning of the learned distinct-role output distribution. Ordinary `11`
contacts teach `10` or `01`; those principal outcomes are discarded by alias
conditioning, leaving an untaught ratio of `00` and `11` tails. Ordinary evidence
therefore did not identify the needed self outcome.

V1 added observed alias examples as first contacts. Four seeds succeeded, but
seed 37 learned one branch while, at the retained endpoint, the other had little
responsibility for an alias-zero observation.
Its per-branch starting-one probability of the correct zero was
`[0.99428642, 0.00476490]`. The equal-prior mixture fell just below one half.
The retained endpoint gradient calculation showed that informative observed
acquisition could give the wrong branch about 158 times the local correction.
This was a specific training-context hypothesis, not architectural impossibility.

V2 retained the first informative ordinary contact and its observation, then
substituted the second contact with an alias on an untouched entity. Both arms
received identical acquisition evidence. The supplied posterior update could
then assign the alias loss to the branch supported by actual observations.
Selected environmental orientations were balanced in both arms before data
realization; no hidden orientation field entered the learner input.

The saved V2 seed-37 tensors now give per-branch correct-zero probabilities
**[0.98714038, 0.99034227]**, with equal-prior local mixture **0.98874132**.
Across all ten treatment branch probabilities, the range is
**0.97817948–0.99133833**. These are local alias probabilities, excluding
background-state factors; they are not full-world confidence. The result is not
merely a marginal MAP crossing.
These values were independently reconstructed from saved JSON weights using
the MLP equations, without executing another benchmark or fitting a model.
Endpoint arithmetic does not reconstruct the optimization trajectory.

V2 also changes the selected lineages, orientation balance, fresh bank and event
inventory relative to V1. Its controlled result is acquired-alias evidence
versus its paired ordinary arm. The difference between V1 and V2 does not isolate
acquisition timing alone.

| Component | Status |
|---|---|
| Entity handles, simulator law, actions, locality, two persistent branches and alias consistency | Supplied |
| Informative action selection and balanced training orientation allocation | Supplied curriculum |
| First-contact outcome and subsequent alias outcome | Actually observed |
| Branch-specific outcome likelihoods and alias diagonal ratios | Learned parameters |
| Bayesian filtering and gradient responsibility computation | Supplied algorithms |
| Autonomous information seeking, learned clarification and arbitrary-law transfer | Not established |

The current diagonal constraint is compatible with this law and did not prevent
success on the frozen criteria. It does not express every independently specified
ordinary/alias law under the same latent mode/history: for example,
requiring ordinary `00` to produce `00` with near-certainty while self `0`
produces `1` with near-certainty conflicts with the same diagonal ratio. No such
new law was tested here. A larger network cannot remove that constraint by
itself; a future law-specific failure would need diagnosis at that owner.

## Separate empirical recovery repair

The last continuation run exposed a premature exception in
`EmpiricalPaths.receive`: a contradicted supported prediction was rejected
before the existing observed-context recovery could run. Removing that guard
and retaining `support_contradiction` adds **two net inference lines**. Complete
feedback permits recovery only when the selected policy's sufficient observed
history is available; otherwise the control abstains.

The old forecast keeps zero truth probability and infinite NLL. The committed
mismatch alarm persists; counts stay fixed, and hidden historical values are
never manufactured. The defect is source-localized and regression-tested through
all four empirical policies and native feedback/evaluation paths. **No retained
historical episode or continuation study was rerun.** Both alias studies contain
neural arms only, so neither establishes improved empirical run-level accuracy
or turns the historical STOP into a completed comparison.

## Execution, commitments and verification

- [Frozen design](ALIAS_EVIDENCE_V2.md) and
  [protocol](alias_evidence_protocol_v2.json).
- Prefit source/data commit: `12de2bd8d8c8ab5619552acc04c473a9f3335047`;
  tree `91c90c2a357e5d1d151ecc502503ef25f16efa58`.
- Actual checkpoint/plan commitment before collection:
  `48de76e0780900bc2ce4bac12195c00116dcb678`;
  [plan](data/alias-evidence-fit-v2/plan.json).
- [Complete result manifest](results/alias-evidence-v2/manifest.json), SHA-256
  `edbe25cb23d8a2c3f57c5ab97ab3aa223f64ad43683f590177fcdcd2a579c49b`.
- Ten fits, **562 parameters**, identical initialization within each pair,
  **128 updates**, 334 observed events and 1,514 visible bits per update.
  Sixteen substitutions from eight dependent training lineages. No tuning,
  selection/calibration fitting, same-bank retry or parameter expansion.
- Eight prepared files reproduce byte for byte; all 21 protocol/manifest locks
  and existing preflight pass. **658 local research/invariant tests**, zero
  skips, completed in **102.916 seconds** at the byte-identical prefit tree.
- Exact-prefit [invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41067452292)
  and [source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/41067452302)
  passed. Final-head CI is reported in PR #62.
- Separate internal JSON audits verified 33 committed source hashes, seven
  prepared artifact hashes, all 14 collected artifact hashes, 15 tensor
  fingerprints, 160 batch/dataset bindings, 3,200 implementation hashes,
  13,520 forecast receipts and 81,120 point-metric comparisons, with no
  mismatches. This is engineering review, not independent scientific custody.
  [Validation record](results/alias-evidence-validation-v2.json).

| Measured CPU cost | Ordinary | Acquired alias | Total |
|---|---:|---:|---:|
| Fitting, seconds | 313.423761 | 278.251950 | 591.675712 |
| Collection, seconds | 55.814609 | 53.971806 | 109.786415 |

Matching applies to parameter counts, exposure, update counts and resource
ceilings; actual consumed CPU differs. Fits used 427,520 path-model evaluations
and 12,902,400 candidate worlds in total. Fitting wall time was 592.162501
seconds. Peak process RSS was 352,004 KiB during fitting and 700,400 KiB during
collection. The latter includes accumulated traces in a shared process and is
not isolated per-model memory. Per-seed continuation prediction p95 wall times
were 4.137–6.038 ms ordinary and 3.846–7.090 ms treatment; these measure the
recorded prediction region, not end-to-end service latency.

## Size and next roadmap step

The model, loss, optimizer and checkpoint implementation are unchanged. The
active import closure is **2,732 lines**, or **2,917 with its historical source
pin**, two more than the starting checkpoint. The two reused alias-study modules
total **438 lines**; V2 adds **63** to them and no inference code. Study tests
total 302 lines. All retained research Python is **27,921 lines**, including
**12,649 test lines**. Physical counts include comments/blanks. The inclusive
2,000-line objective remains unmet; runtime restraint does not erase study debt.

The next bounded deliverable is one fresh **frozen-weight mixed-composition
challenge**, using the existing collector: ordinary acquisition followed by
alias and reversed continuation; alias before acquisition; repeated aliases;
and withheld observations requiring coherent uncertainty. Alias outcomes in
this world must not spuriously reveal the persistent orientation. Score complete
worlds, joint NLL/Brier, untouched entities, mode coherence and repaired/broken
cases, with answerable and ambiguous points distinguished prospectively.

This study tested standalone self-contact separately from ordinary compositions;
their interoperability is still unmeasured. Keep all five weights fixed, retain
these opened results, and define the new challenge before execution. Further
architecture, workspace or language work requires evidence of a specific gap.
G1 baseline adequacy and independent challenge authorship/custody remain open;
the weak historical flat fit does not establish broad architectural superiority.
