# Active nucleus: explicit entity and alias domains

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22) / [draft #58](https://github.com/robosys-labs/cemm/pull/58), stacked on [draft #57](https://github.com/robosys-labs/cemm/pull/57).
Published code: `2b281cd7f1ba0de4a7985cacc4bbf272783d01ed`; its tree exactly matches locally verified
`9132fa626d15c197b49f4d77d0971ed54ba1ef8d` (Git metadata differs).
Decision: KEEP the bounded domain, migration and inference integration.
**G1 remains NOT ADMITTED. Engineering does not wait solely on issue #55.**

## Active versus frozen paths

`active_participant.py` is the opt-in repository-backed command. Startup identifies
`active-inference-v4` and `active-evidence-v2`, including source hashes, predictor
class/configuration, declared domain, resource limits, weight/table fingerprints
and explicit adaptation provenance. Forecast receipts bind this identity.
The five active source files reuse the frozen streaming transport, verified bundle
loader and learned modules. Frozen sources, protocols, checkpoints, studies and
standalone v1 exports remain unchanged.

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m experiments.predictive_nucleus.active_participant \
  --bundle /absolute/path/participant \
  --manifest-sha256 2373c2d366c4f8a855dbb7498e5d6a88bc55b9078a00400eb51db86ca115a1a8 \
  --participant kernel_supplied_persistence --seed 7 --expand-domain
```

The bundle is the verified existing v1 handoff, not newly trained weights.
`--expand-domain` explicitly converts a shared kernel or observed-count table.
Without it, existing kernel/table checkpoints retain their original domain.
The no-change baseline supports dynamic geometry directly. This command is not
a security sandbox or a replacement standalone export.

| Predictor | Entity counts | Self-contact | Interpretation |
|---|---|---|---|
| Legacy shared kernel, no adaptation | 3 | Rejected | Original checkpoint scope |
| Explicitly adapted shared kernel (all four variants) | 3, 4, 5, 6 | Supported | Supplied alias conditioning; learned tensors unchanged |
| Either legacy flat variant | 3 | Rejected | Fixed input/output geometry; expansion flag fails explicitly |
| Legacy empirical table, no adaptation | 3 | Rejected | Original table schema |
| Explicitly adapted empirical table | 3, 4, 5, 6 | Representable | Unsupported size/alias contexts abstain; no synthetic counts |
| No-change control | 3, 4, 5, 6 | Supported | Existing last-observed-state baseline |

The JSONL start/predict/feedback/end ordering remains. Each episode declares three
to six stable IDs and a complete binary initial anchor. `predict` accepts optional
`sensor_ids`, a nonempty set of distinct episode IDs selected before feedback
(default all IDs). Feedback names every episode ID; unknown or outside-coverage
readings remain null. Visible readings are assumed noiseless. Any feedback must
carry its forecast's matching receipt. An episode may end with a final forecast
still awaiting feedback; that forecast remains unevaluated. The transport caps
128 actions.

## Domain and self-contact contract

`domain_contract.py` derives the exact `2**N` joint world enumeration for the
current entity count. A physical entity has one state coordinate and one sensor
reading even when both action slots reference it. Current and historical alias
patterns are explicit in empirical context keys and direct-support signatures;
`(A,A)` cannot borrow the evidence for distinct `(A,B)` with equal input bits.
A completed observed self-contact contributes one context event.

`DomainKernel` retains the learned pair, intervention and optional background
modules of the four original shared-kernel configurations. Its world geometry is
derived from the episode instead of retaining a stale three-entity checkpoint
buffer. Conversion strictly checks topology, tensor inventory, shape, dtype,
finite values and original geometry, copies the tensors, preserves the source and
RNG, and records original full-state and learned-parameter fingerprints. No learned
parameters are added. Ordinary three-entity forecasts and latent updates retain
the legacy behavior within the declared numerical tolerance.

For an aliased pair, each latent mode conditions its pair factor on consistent
output slots **before** the modes are mixed:

`p_alias_mode(b) = p_mode(b,b) / (p_mode(0,0) + p_mode(1,1))`.

This is supplied identity consistency. It imports no simulator transition rule and
does not force a particular physical outcome. Empty diagonal support fails
explicitly. Finite diagonal log mass survives exponential underflow. Forecast
`filter.alias_conditioning` records the retained log mass per live path and mode,
labels the interpretation supplied, and is included in the receipt. Normalizing
an extremely small retained mass can still produce a confident conditional
forecast; this does **not** establish learned self-contact behavior or pass the
original held-out self-contact family.

`DomainMemory.from_legacy` copies existing counts into size/alias-aware keys and
retains the source table digest. It creates no larger-world or self-contact
outcomes. Its measured full-observation fit helper and prediction/recovery logic
never substitute model-generated or hidden bits for observed counts. Wider or
aliased contexts require actual recorded support; observed-context recovery does
not invent a table entry or update the frozen table online.

## Explicit resource limits

The live-path cap remains 64 per episode. A separate candidate-expansion cap of
512 is checked **before** invoking the predictor or allocating its expanded
forecast. It counts each live history against every possible next world:

| Entities | Joint worlds | Maximum live histories allowed at the next prediction under the default expansion cap |
|---|---:|---:|
| 3 | 8 | 64 |
| 4 | 16 | 32 |
| 5 | 32 | 16 |
| 6 | 64 | 8 |

The 64-live-path feedback cap still applies independently. A six-entity episode
with substantial missingness can therefore stop at its next prediction even
when its previous feedback was within the live-path cap. Distinct recurrent
histories are not merged, and no finite positive mass is pruned to make a case
fit. These are explicit resource failures, not evidence of predictive mismatch
or a solution to long-horizon uncertainty.

## Integrated evidence contract

The forecast receipt now binds its action, normalized joint log distribution,
canonical sensor coverage, observed-context assessment, diagnostic thresholds,
and active implementation identity. Internal copies prevent caller mutation of
the response or original request from changing the committed evidence. The
transport rejects a wrong episode, step, receipt, duplicate feedback, unexpected
field, invalid reading or outside-coverage observation before any evidence update.

`active_evidence.py` uses the alias-aware, direct-only `DomainSupport` for
completed observed contact contexts. It implements the historical adequacy monitor's uniform
reference calculation directly in log space and latches the episode alarm.
It does not manufacture the older monitor/guard's two-hypothesis belief API or
claim its alternate change-point process or posterior-support analysis is active.

| Feedback assessment | Meaning |
|---|---|
| `NO_EVIDENCE` | All selected readings are missing; no likelihood evidence is added. |
| `UNSUPPORTED_PREDICTION` | Actual readings arrived, but the empirical participant abstained; model likelihood and log-e increment are absent. |
| `OBSERVATION_COMPATIBLE` | The observed joint event is compatible and does not meet either diagnostic threshold. |
| `SURPRISING_BUT_UNCONFIRMED` | Uniform-reference likelihood divided by model likelihood exceeds 4, without a current cumulative log-e crossing. |
| `MODEL_MISMATCH_EVIDENCE` | The conditional log-e statistic meets the declared threshold; it does not identify the cause. |

The v2 evidence contract prospectively replaces v1's fixed `p < 0.03` heuristic
with `q/p > 4`, where `q = 2**(-observed_bits)`. This changes partial-coverage
thresholds as well as entity-count scaling. A uniform six-bit forecast has
`p = q = 1/64`, so it is compatible and contributes zero log-e evidence. The
heuristic and alpha remain uncalibrated; historical reports are not re-scored.

Visible likelihood is the joint marginal over compatible worlds, not a product
of independent bit marginals. Finite log mass such as `-1000` remains finite;
only an all-negative-infinite compatible set is impossible. The fixed reference
is `-observed_bits * log(2)` and the increment is reference log likelihood minus
model log likelihood. Numeric overflow/infinities have explicit JSON string
representations; null likelihood means no predictive distribution. An all-missing
event contributes exactly zero when a forecast exists, including after an alarm.

`status` describes the current assessment. `episode_alarm` records whether the
threshold was ever crossed, even if later compatible evidence lowers the statistic.
This is a **conditional, uncalibrated advisory diagnostic**. The statistical
interpretation assumes correct conditional forecasts, noiseless visible readings,
predictable sensor selection and ignorable/value-independent dropout. Selecting
coverage does not verify dropout independence. Logical episode/step/receipt
identity does not authenticate physical sensors. Alpha 0.05 is an episode-level
conditional threshold, not a demonstrated false-alarm rate or a multi-model bound.

Contact support counts only completed events with observed ordered input and
output operands. Predictions, posterior estimates and hidden bits supply no counts.
`set`/`observe` report `NOT_APPLICABLE` for this contact-only diagnostic. Reusing
unaffected prior readings relies on the supplied participant-locality assumption.
One observed context does not establish learned reliability or training support.

Feedback is assessed without mutation, the existing filter update runs, then
evidence/support are committed. A terminal filter error retains the candidate
assessment with `committed: false`: its log-e/scored-step values describe the
validated event's proposed contribution, while stored monitor/support state stays
unchanged. Path-budget or implementation errors retain their original error and
are not relabeled as predictive mismatch. Neural/empirical exact contradictions
remain terminal; the no-change control continues its existing last-reading update
while reporting and latching the contradiction. The active CLI preserves these
diagnostics in strict-JSON `ERROR` responses and exits with code 2.

## Current v4 integration verification

The clean local code commit `9132fa626d15c197b49f4d77d0971ed54ba1ef8d` passed
**498 tests in 37.279 seconds, zero skips**, including **41 new tests**: 13 domain
contract, 10 shared-kernel and 18 integration checks. The original protocol,
all 16 historical manifest locks and standalone frozen-input preflight passed.
The actual CLI loaded a verified **synthetic** v1 export, processed six entities
and self-contact with receipt-matched feedback/end, and rejected flat expansion.

Checks cover all entity counts and action kinds, arbitrary per-mode alias ratios,
finite underflow versus impossible support, direct-kernel finite gradients,
identity equivariance, candidate/live-path limits, unequal episode path counts,
observed-only table migration/recovery, dimension-aware evidence, configuration
identity and receipt binding. Twenty-four forecast vectors across all six
synthetic model variants match unchanged three-entity inference within `1e-12`;
source and adapted tensors remain unchanged. Empirical migration preserves
legacy three-entity predictions and source counts.

The first integration run exposed a classmethod/CLI adapter mismatch; it was
repaired before this full-suite run. Review also made configuration part of
startup identity and exposed retained alias mass. No test was weakened or skipped.
These are implementation invariants, not new trained-model accuracy,
calibration, entity-count transfer, self-contact generalization or an expanded
matched-baseline comparison. No research model was retrained, closed study rerun,
or historical score changed.

`results/active-domain-validation-v4.json` records code/tree equivalence, source
hashes, test output hash, preflight lineage and scope. This tranche adds **563 net
runtime lines** and **834 test lines**, with no additional learned parameters in
adapted kernels. Retained research Python totals **20,814 physical lines**.
The five active source files total **1,026 lines excluding frozen dependencies**;
this is not an inclusive implementation size. The inclusive 2,000-line goal
remains unmet. No historical evidence was deleted to improve the count. Test
runtime and preflight environment are recorded; no new inference-latency or
scientific compute benchmark is claimed. Both code-commit workflows passed: invariants run `40948565909` and source snapshot
run `40948566008`. Final documentation-head CI is linked from draft #58.

## Earlier v3 diagnostics verification

The clean local code commit `be65e4424ac34f4db67fc8895a2dea86f9de77c8` passed **457 tests in 36.421 seconds, zero skips**, including
22 new diagnostic/integration regressions and the full-checkout preflight test.
Standalone frozen-input preflight and all 16 historical manifest locks also passed.
Before the local code commit, the suite had 456 passes and one preflight error:
that required gate rejects an uncommitted tracked tree. It passed on the clean
commit; no test was disabled or weakened.

Twenty-four forecast vectors across all six synthetic model variants match the
unmonitored repaired path exactly on the hand-written full/missing-reading trace;
weight fingerprints remain unchanged. Empirical recovery tests preserve table
digests. These are software invariants, not new saved-model accuracy, calibration,
independent scientific validation or an architectural comparison. No research
model was retrained, public study rerun or historical result re-scored.

`results/active-evidence-validation-v3.json` records the code identity, source
hashes, test results, preflight lineage and scope. The tranche adds 225 net runtime
lines and 377 test lines. Retained research Python totals **19,417 physical lines**,
including historical studies/tests. The three active source files alone total
463 lines, excluding their frozen dependencies; neither count establishes the
inclusive 2,000-line goal. No evidence was deleted to improve a size figure.

## Exact repairs

**Live neural paths.** The old filter retained exact-zero histories and could
exhaust its limit with only one possible world. The successor packs finite
log-mass histories and applies the limit per episode AFTER eliminating only
negative-infinite mass. Finite values such as -1000 survive even when their
exponentials underflow. Distinct recurrent histories are not merged when their
current bits happen to match. Unequal per-episode paths and sensor masks work
without padded impossible histories. Real positive-mass growth still fails at
the configured bound; approximation and long-horizon scaling are not solved.

**Observed-context recovery.** Predictive table support and actual observations
are now retained separately. After an unsupported prediction, complete feedback
allows re-entry only when the control's sufficient observed context is known:
local needs current state; prefix needs its whole observed history; contact
needs every ordered contact operand's before/after readings; first-contact needs
only that first contact. Unknown historic bits are never invented. Unsupported
partial histories still abstain rather than renormalizing away unknown mass.
A previously supported prediction contradicted by reliable feedback remains an
explicit conflict, not a silent reinitialization or automatic model repair.

## Earlier v2 repair verification

Both audit examples reproduced against unchanged frozen source. Twenty-five
new tests cover both fixes, causal ordering, malformed inputs, per-episode
budgets, unequal masks, history-specific recovery, real conflicts, underflow,
retained recurrent distinctions and end-to-end streaming behavior.

**Complete-branch CI run 40932601276 passed all 435 tests with no skips in
24.347 seconds**, all 16 historical manifest locks and frozen-input preflight.
This includes the checkout-dependent test unavailable in a source archive.
The later documentation/evidence CI run 40933549651 also completed successfully.

Saved-weight compatibility checks restored all 30 original models. On a
hand-written four-action history, with full and missing readings, 240 forecast
vectors matched the old valid inference path within 1e-12; maximum absolute
finite-log difference was `1.7763568394002505e-15`. All five supplied-persistence
checkpoints survived 128 fully missing observe updates at path limit one, always
retaining exactly one live state. The actual new CLI completed ten such updates.
These are implementation regressions/equivalence checks, not new accuracy,
calibration, independent challenge or superiority results. No closed study was
rerun and no weights or empirical counts were changed.

Local focused tests passed. The old execution-test module separately passed
35 tests with one checkout-dependent skip. Several local full-suite attempts
hit their execution limits (45 seconds, 120 seconds and a separate selection);
they remain INCOMPLETE, not counted as passes. The cause of those local stalls
was not established. Remote full-branch CI supplied the complete verification.

The retained summary is `results/active-repair-validation-v2.json`; it identifies
the full downloadable local evidence by hash. All 189 pre-existing files in the
source archive were byte-compared with zero changes. New source is 238 lines;
new tests are 348 lines. Direct retained-tree enumeration is 18,815 Python lines,
including historical studies and tests. Neither new-file size nor archive size
is a complete active-dependency count or proof of meeting the inclusive 2,000-
line goal. No historical evidence was removed to improve a size figure.

## Remaining engineering, excluding manual sign-off

`active_status.json` separates completed domain/inference plumbing from the
remaining learning and evaluation requirements. The next bounded tranche should
complete **one common train/predict/observe/checkpoint/evaluate path** for the
expanded domain, with comparable flat, shared, no-change and empirical controls.
The current packed filters use inference mode and NumPy normalization; their
masked-observation path is not a differentiable training loop. Direct kernel
gradient checks do not close that gap. New checkpoint metadata must preserve
domain, configuration, supplied biases, learning/data provenance and budgets.

Before computing new research scores, version information-aware automatic
acceptance: exact prediction points, answerability under delivered observations,
coverage and abstention, joint probability scores, complete-world trajectories,
paired role reversals, all required seeds, matched controls and comparable costs.
Keep the roadmap's G1 target and held-out families; do not reinterpret historical
final-query results as whole-trajectory success. The original generator already
samples three through six entities during training, so supporting six IDs is not
an unseen-count transfer result. A prospective unseen-count split must withhold
those counts. Training self-contact examples cannot count as success on the
original untrained self-contact family.

Then implement the concrete G2 workload: train on one or two interactions and
evaluate three to five over declared chains, forks, cycles and disjoint groups,
including repeated actions, untouched entities and coherent joint alternatives.
Earlier outputs must become later inputs without reset interventions erasing
the dependency. A named graph or reset-separated edge sequence alone does not
establish causal composition. Repeated uses of one uncertain mechanism must
retain their shared uncertainty rather than independently resampling it.

Direct observed support and the joint-log advisory diagnostic are integrated.
Posterior-context support, alternate change-point evidence, calibrated confidence
and learned probe selection remain unestablished. Grounded bilingual language
and G3–G8 follow the roadmap dependency order. Learned communication and lifelong
learning are not new G1 prerequisites.

Issue #55 remains pending for independent scientific validation; it does not
replace or block these implementation requirements. Automatic correctness and
regression checks remain required. No scientific gate is weakened or admitted,
and no production/PR21 cutover or language implementation occurs in this tranche.
