# Frozen sensor transfer completed: keep capability, close this fixture

Tracking: #22 / draft #53, stacked on #52. Date: 2026-10-29.
**Decision: KEEP bounded evidence-conditioned prediction; CLOSE this public
sensor-transfer diagnostic; REJECT special neural superiority over the strong
empirical abstraction. G1 admission remains NOT ADMITTED.**

The prior common-objective study remains closed. This test restored unchanged
weights and measured new chronological/missing-reading conditions without fitting,
selection, calibration or retries. It is same-assistant-authored, separately
implemented evaluation, not independently authored or independently held evidence.

## Execution and lineage

- `a6f3cc1ae1561819b41eedcd06eef5148f3d4896`: protocol committed before implementation or outcomes.
- `a8abb123852e4c9c4dff51f2cabc173e2452670c`: supplied missing-reading adapter, separate fixture, tests and runner.
- `6664a2412d28e909c4a277400dc5c787337e3c57`: separate one-attempt workflow.
- [Scientific run 40844965323](https://github.com/robosys-labs/cemm/actions/runs/40844965323) succeeded, including durable retention and recovery artifact upload. No repeat was performed.

All 30 informative/fixed-exposure checkpoints were restored and verified against
the hash-pinned original report: six variants, five seeds (7,11,23,37,53).
Initial/final weights and original training costs remain in the prior study's
retained evidence. This test makes no matched-capacity or matched-compute claim.
It adds no optimization or training path.

The transfer inventory is 180 neural and 30 control evaluations: 210 total,
2,211,840 neural forecast rows, 2,580,480 total prediction/abstention rows,
and 1,120 full-to-masked per-step paired comparisons. Each family/sensor policy
contains 256 factorial cases and six related identifier views, not 1,536
independent worlds. All eight steps remain reported; the table below is the
predeclared final query (zero-based step 6), not pooled all-step G1 performance.

## Query outcomes

Equal-weight neural mean over five seeds and two chronological families.
Controls average the two families and were not repeatedly trained per seed.
Every displayed answering method has 100% final-query coverage.

| Model / control | Full readings | Hidden reset readings | Hidden decisive probe |
|---|---:|---:|---:|
| Structured, learned background/persistence | 100% | 100% | 62.5% |
| Structured, supplied persistence | 100% | 100% | 62.5% |
| Structured, untied role hypotheses | 100% | 100% | 62.5% |
| Structured, memory reset | 62.5% | 62.5% | 62.5% |
| Flat GRU | 58.6458% | 58.2617% | 57.9036% |
| Flat GRU + supplied persistence | 40.0716% | 39.5378% | 40.2018% |
| Prior-contact empirical abstraction | 100% | 100% | 62.5% |
| First-contact empirical abstraction | 100% | 100% | 62.5% |
| Local state/action empirical memory | 62.5% | 62.5% | 62.5% |
| Last-observed/no-change | 50% | 18.75% | 50% |

Every seed of each of the three non-reset structured variants achieved 1,536/1,536
on both answerable conditions in both families. Exact-prefix memory abstained on
all final queries; do not describe this as 0%-accurate numeric forecasting.
The controls' supported abstraction keys remain familiar training contexts. This
is transferred chronology and missing-observation inference, not new physics.
Both the unchanged prior-contact and predeclared first-contact controls match
perfect MAP and have zero NLL/Brier on the answerable queries. The simpler
supplied abstraction still explains the success; a neural-superiority claim is
not supported merely because the flat GRU performs worse.

## Missing evidence versus prediction failure

Hidden reset readings omit the current A/B values, but earlier actions and the
observed probe still make the physical query answer identifiable. The models
must integrate hypothetical states, not copy simulator truth. All three
persistent variants retain perfect MAP; the learned-background arm has zero
correct-to-wrong query transitions from full to hidden-reset conditions.

Proper scores nevertheless worsen: the learned-background arm's mean query NLL
rises from 0.00201979633 to 0.00440371792, and mean Brier from 0.00000588994
to 0.00002870953. Perfect MAP does not mean uncertainty or numerical probability
quality is unchanged. The flat model has 140 correct-to-wrong and 81
wrong-to-correct query transitions under hidden resets; the supplied-persistence
flat model has 104 and 22. These counts aggregate the ten related seed/family
cells (15,360 queries), not independent samples. The reset-memory arm has 960
repairs and 960 regressions despite unchanged aggregate accuracy.

Hiding the decisive probe instead leaves the mode unknowable before the query.
The exhaustive evaluator's optimal deterministic query accuracy is 62.5%:
one quarter is unambiguous and three quarters have two equiprobable outcomes.
The optimal all-query NLL is 0.75*ln(2) = 0.51986038542, Brier 0.375.
The learned-background arm achieves NLL 0.52147764201 and Brier 0.37500296077;
both contact controls attain the exact finite-fixture floors. This supports the
missing-evidence interpretation on this task, not independently calibrated
uncertainty or a general explanation of all future prediction failures.

## Supplied versus learned, and remaining limitations

The new common finite-path Bayesian wrapper is supplied to both model families
and empirical controls. It enumerates hypothetical states, conditions only on
visible readings and retains per-path model state. Missing readings are -1 plus
an explicit mask; they are never recorded as observed bits. The wrapper does
not import simulator physics. Its 64-path bound fails instead of pruning.
It is not evidence that the learner discovered an uncertainty algorithm or
learned active acquisition. Longer missing histories can exceed the bound.

The structured variants still supply two latent modes, locality and identity-
equivariant parameter sharing. Three entities, static noiseless two-mode physics,
authored probe schedules, and familiar atomic contexts remain. New handle strings
are mapped to supplied slots; this is not learned arbitrary identity grounding.
The empirical first-contact abstraction is supplied, not an emergent discovery.
Original model capacities and training costs are unequal. No conclusion over
Claude/DeepSeek, Wikipedia utility, general intelligence or production readiness
follows from these results.

## Validation and separate archive arithmetic check

[Implementation CI 40844566136](https://github.com/robosys-labs/cemm/actions/runs/40844566136)
passed 379 tests, no skips, all 16 manifest locks and the real frozen preflight.
The execution-workflow commit's invariant CI 40844965260 also passed. The local
archive suite passed 378 with its one real-Git-checkout test explicitly skipped;
complete-branch CI executed that test. Sixteen new synthetic/fixture tests verify
full-sensor parity, correlated uncertainty, forecast-before-feedback ordering,
missing-value validation, unsupported empirical branches and two evaluator checks.

`sensor_transfer_archive_check.py` then checked the downloaded raw archive without
project, simulator, model or scorer imports. It independently recomputed arithmetic
from stored forecasts; it did not replay a model or repeat the study. All 210 files,
2,580,480 status rows (2,520,576 answered; 59,904 abstentions), 1,680 per-step cells
with their identifiable/ambiguous subsets, and 1,120 paired comparison ID lists
passed. Scope includes hashes, sensor masks, normalization, MAP/NLL/Brier,
unchanged-bit errors, role pairs and distribution-renaming TV. This separate
same-author implementation is not independent scientific review/custody.
The portable-output form of the checker reproduced the same verification JSON.

```sh
python experiments/predictive_nucleus/sensor_transfer_archive_check.py \
  /path/to/sensor-transfer-output /path/to/verification.json
```

The retained verification JSON is `results/sensor-transfer-arithmetic-40844965323.json`.
SHA-256: `d4d6d81465202d88ca277d0c731acab91caa89352ac21c813666827c88f0c080`.
The checker SHA-256 is `1177a4618a18ab0450d4c33b7ebc4a0a2afcd86e2c66e3a15452429d1e260f68`.
Its assertions must remain enabled; running under Python -O is rejected.

## Durable evidence and costs

[Results commit eacdfc0](https://github.com/robosys-labs/cemm/commit/eacdfc0813c28cc9630fda1ceb16e5b2486fcbe4),
branch `research-results/sensor-transfer-40844965323`, directory
`experiments/predictive_nucleus/results/sensor-transfer-40844965323/`.
The archive retains raw/normalized forecasts, masks, actions, truth, oracle
probabilities, paired regression IDs, summaries and checkpoint/table checks.
Original checkpoints remain durably retained in the prior common-objective run.

Full report SHA-256: `d3a34852f04ee2d03e17eee1f3a1c4d9c74cd5cf5d4242a3622ef00455293e89`.
Downloaded recovery ZIP SHA-256: `aa316ae6303f019e8e2f94fc2494d3889d504bb4d19e530603989161b9908dcd`.
Durable branch's tar bundle SHA-256: `a98452ced30262bbb1288e0d503dfd4431c276c4b2116d3fcbbff592813662a9`.
The ZIP/report were checked locally; the tar hash is the published retention hash,
not a claim that the separate tar bytes were downloaded and rehashed locally.

Recorded evaluation pipeline cost: 130.211 wall seconds, 130.050 process-CPU
seconds, peak RSS 722,024 KiB on AMD EPYC 7763, Python 3.13.17, PyTorch 2.10.0+cpu,
one intra/inter-op thread. These include replay/scoring/output I/O, not single-query
service latency. Models use explicit float64; torch's default dtype was float32.

## Stop rule and next decision

Close this fixture: no additional tuning, masks, seeds or repair chosen from its
outcomes. Both completed diagnostics support reusable evidence-conditioned
prediction under strong supplied structure, but neither establishes a special
neural advantage over the empirical abstraction. Adding another layer or another
same-physics accuracy sweep is not justified by these outcomes.

The next admission work must resolve independent held challenge authorship/custody,
frozen unfamiliar trajectory families, explicit capacity/compute comparability,
and the roadmap's material gain criterion while retaining the strong empirical
control. Do not rebrand this same-author exercise as that challenge. No language,
lifelong-learning or communication requirement is newly added to G1; those remain
later gates. No production, PR21, governance or historical frozen artifact changed.

New inference/fixture/runner/tests add 655 physical Python lines, plus 119 for the
archive-only checker: 774 this tranche. Direct local source enumeration now totals
17,389 retained Python lines including tests and historical studies. This does not
meet the practical 2,000-line target; files were not deleted to improve the count.
