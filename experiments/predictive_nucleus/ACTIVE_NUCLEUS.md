# Active nucleus: one observed-history learning and inference path

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22); v5 draft
[#59](https://github.com/robosys-labs/cemm/pull/59), stacked on [draft #58](https://github.com/robosys-labs/cemm/pull/58).
Published v5 source: `94c059a0fd4fdb78ad5f442419053ac99e41c124`.
Locally verified code: `5a857ab0879cb1e67ca01a1de888eafbabace5d0`, tree
`adb0ec97aac6e3f28d5e24f5909d8c9ae2e470ec`. Publication preserves that exact tree;
Git commit metadata differs.
Decision: KEEP the common observed-history learning path, wider flat control and
native learned-state artifacts. Prospective scientific acceptance remains next.
**G1 remains NOT ADMITTED. Engineering does not wait solely on issue #55.**

## Active versus frozen paths

`active_participant.py` is the opt-in repository-backed command. Startup identifies
`active-inference-v5` and `active-evidence-v2`, including source hashes, predictor
class/configuration, declared domain, resource limits, weight/table fingerprints
and current training, checkpoint and adaptation provenance. Forecast receipts
bind this identity. `active-learning-v1` supplies Python training, replay and
evaluation APIs; `cemm-active-checkpoint-v1` stores registered learned state.
The eight active source files reuse the frozen streaming transport, verified
bundle loader and learned modules. Frozen sources, protocols, checkpoints,
studies and standalone v1 exports remain unchanged.

The native artifact route starts a fresh streaming episode from a separately
saved and hash-verified checkpoint:

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m experiments.predictive_nucleus.active_participant \
  --checkpoint /absolute/path/learned-state.json \
  --checkpoint-sha256 ACTUAL_CHECKPOINT_SHA256
```

Use the SHA returned by `save_checkpoint`, recorded with the artifact. The native
route owns its predictor/configuration and rejects legacy participant, seed,
manifest or expansion selectors. The original verified-bundle route remains:

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
The no-change baseline supports dynamic geometry directly. The command remains
repository-backed; neither route enforces an OS sandbox or independent custody.

| Predictor | Entity counts | Self-contact | Interpretation |
|---|---|---|---|
| Legacy shared kernel, no adaptation | 3 | Rejected | Original checkpoint scope |
| Native or explicitly adapted shared kernel (all four variants) | 3, 4, 5, 6 | Supported | Supplied alias conditioning; conversion preserves tensors and later fitting has separate provenance |
| Either legacy flat variant | 3 | Rejected | Fixed input/output geometry; expansion flag fails explicitly |
| Fresh `DomainFlatGRU`, either persistence setting | 3, 4, 5, 6 | Supported | Global flat model with explicit domain geometry; no legacy-flat conversion |
| Legacy empirical table, no adaptation | 3 | Rejected | Original table schema |
| Native or explicitly adapted empirical table | 3, 4, 5, 6 | Representable | Observed-only counts; unsupported size/alias contexts abstain; conversion creates no counts |
| No-change control | 3, 4, 5, 6 | Supported | Existing last-observed-state baseline |

The JSONL start/predict/feedback/end ordering remains. Each episode declares three
to six stable IDs and a complete binary initial anchor. `predict` accepts optional
`sensor_ids`, a nonempty set of distinct episode IDs selected before feedback
(default all IDs). Feedback names every episode ID; unknown or outside-coverage
readings remain null. Visible readings are assumed noiseless. Any feedback must
carry its forecast's matching receipt. An episode may end with a final forecast
still awaiting feedback; that forecast remains unevaluated. The transport caps
128 actions.

## Common learning, prediction and observation

`active_learning.py` accepts caller-supplied `ObservedBatch` records: binary
readings with `-1` for absent values, explicit reading masks, actions, declared
sensor coverage and unique episode IDs. Each batch has one entity count and
equal-length histories; a dataset may contain batches of different lengths and
counts. The initial anchor is complete. Validation checks that delivered bits
are inside declared coverage and that all action references and aliases are
legal. Copies and hashes bind the realized histories used by every arm.
The records contain no hidden world state, mode label or evaluator outcome.
They do not authenticate event provenance, independently establish lineage, or
prove that the caller selected coverage before observing the outcome.

`replay` uses the same `NeuralPaths.predict`/`receive` implementation as active
inference, with an explicit differentiable option. Torch log normalization
preserves gradients through path probabilities, recurrent state and persistent
mode updates. Inference defaults to disabled gradients; the existing transport
still has an explicit detached NumPy output boundary. The loss for a delivered
event is the negative log probability of the **joint observed event**, summing
over every complete world compatible with the readings. It is not a sum of
independent bit losses. Every forecast precedes its own feedback update.

`fit` averages this joint-event loss across all events with at least one visible
reading, including contact, set and observe events, across all batches. It does
not average batch means with different event counts. An all-null event adds no
loss but still advances hypothetical dynamics; later evidence can propagate a
gradient through that transition. An entirely unobserved target dataset is
rejected. Exact-zero support is handled without undefined all-negative-infinity
gradients; finite values such as `-1000` remain represented. Distinct recurrent
histories and their shared uncertain mechanism are not collapsed or resampled.

The common Adam fitter records the optimizer settings, requested/completed
updates, learning rate, path/expansion limits, input and training-source hashes,
initial/final tensor fingerprints, parent checkpoint identity, actual CPU/wall
cost, last-step overshoot, path work and process peak RSS. These costs do not
establish matched consumed compute. Fitting updates current training provenance
and clears stale checkpoint identity. If an update is interrupted after mutation,
including a `KeyboardInterrupt`, provenance is marked `INTERRUPTED` and the old
checkpoint metadata is cleared. Cleanup also covers post-update report failures;
it invalidates stale identity before trying a final fingerprint. If fingerprinting
also fails, the current hash is explicitly unavailable and the original error
propagates. Weight rollback and optimizer resume are not
provided; an interrupted fit is not a completed fit.

`fit_empirical` consumes the same delivered batches. Prefix, local, contact and
first-contact controls count an event only when its complete before/after world
and the control's sufficient historical context were actually delivered.
Reports retain counted events and incomplete-current/history skips. The neural
objective can use partial targets that these full-outcome count tables cannot;
identical histories do not imply identical usable target counts. Missing bits
are never filled from predictions, later readings or evaluator truth. The fitted
history policy is bound to the memory and preserved by default replay, Session
and checkpoint calls; an explicit conflicting policy fails.

These are Python APIs over validated histories, not a new training/evaluation
CLI or an automatic scientific comparison. Synthetic one-update tests verify
wiring; no research model has been retrained on an opened study.

## Wider flat control and comparison limits

`DomainFlatGRU` is a fresh baseline with one global GRU and one 64-logit head.
Its 29 features are six padded bits, six existence flags, two ordered six-slot
operand indicators, three action-kind indicators and two intervention-value
indicators. The existence mask distinguishes an absent slot from a measured
zero. For `N` physical entities, it selects the `2**N` output coordinates whose
unused trailing slots are zero, then normalizes those logits. The optional
supplied-persistence variant uses the same physical support constraint as the
shared model. An alias names one physical output coordinate.

| Native default arm | Learned parameters | Important supplied structure |
|---|---:|---|
| Shared kernel, supplied persistence | 470 | Two modes, locality, sharing, role tying, exact nonparticipant persistence |
| Shared kernel, learned background | 584 | Two modes, locality, sharing, role tying, learned background |
| Shared kernel, untied roles | 972 | Two modes, locality and sharing; separate pair networks |
| Shared kernel, reset memory | 584 | Mode prior reset at each action; other shared structure retained |
| Flat, either persistence setting | 1,512 | Six address slots, existence mask and restricted global output geometry |

The flat default uses hidden width eight; shared defaults use width sixteen.
These capacities are **not matched**. The new flat architecture does not restore
old three-entity flat weights, and its supplied padding/output geometry is not
learned count transfer. Shared and flat arms now use the same delivered-history
loss and filter; they still have different function classes, parameter counts
and costs. Strong empirical abstractions and no-change remain controls. No
wider-domain performance comparison, calibrated superiority or scientific
advantage has been established by this implementation tranche.

## Native checkpoint and evaluation boundaries

`active_checkpoint.save_checkpoint` writes a new plain-JSON artifact after
validation and refuses overwrite. `load_checkpoint` requires an explicit expected
file SHA-256, matching inference-source hashes and a registered constructor.
Configuration, domain, supplied biases, tensor inventory/dtypes/shapes, empirical
keys/counts and provenance are checked. Duplicate or unexpected structural fields, arbitrary classes,
nonfinite values and booleans used as integer settings/counts are rejected.
The artifact is capped at 16 MiB and registered hidden widths at 256. No pickle
or source embedded in the artifact is executed; save/load preserve source state
and RNG. Hashes verify identity, not independent review or provenance truth.

Registered artifacts cover the four shared configurations, both fresh flat
settings, empirical modes including first-contact policy, and no-change. They
restore **learned state for fresh episodes only**. Live filters, pending forecasts,
optimizer state and episode resume are outside this format. Immutable legacy
origin fingerprints remain separate from current trained-state identity.
Training provenance records a declared input hash, objective and completed update
count, plus finite fit metadata; it is explicitly caller-declared and unauthenticated.
Loaded metadata is copied, and active receipts bind the current artifact and
training identity without reusing stale pre-fit checkpoint claims.

`evaluate` replays frozen predictors and reports delivered-observation joint
likelihood, forecast/observed-event coverage and explicit failures. Evaluation
input hashes are recorded separately from training provenance; this API does not
enforce split disjointness. It retains valid forecast
prefixes and the current valid forecast when feedback fails, while keeping all
planned events in the denominator. Exact contradictions retain negative-infinite
log likelihood and infinite NLL; unsupported predictions have no distribution or
likelihood. A failed filter update is marked uncommitted. Overall observed NLL
is present only when every planned observed event was scored; answered-only NLL
is explicitly conditional. Strict JSON distinguishes these cases.

This evaluator has **no hidden gold**. It does not measure complete-world
accuracy on unobserved bits, trajectory correctness, role-pair success,
calibration, scientific independence or G1 acceptance. Its engineering scope
must not be promoted to the roadmap's outcome gate.

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

## Current v5 learning integration verification

The clean local code commit `5a857ab0879cb1e67ca01a1de888eafbabace5d0` passed
**546 tests in 52.151 seconds, zero skips**, including **48 new tests**: 18 learning,
11 checkpoint, nine flat-model and ten active-contract checks. The original
protocol, all 16 historical manifest locks and standalone frozen-input preflight
passed. The published source tree matches this locally verified tree exactly.
Checks on the final documentation head are recorded at
[draft #59 checks](https://github.com/robosys-labs/cemm/pull/59/checks).

Synthetic tests compare masked sequence likelihoods and parameter gradients
with a separate whole-history enumeration across the covered model arms and
entity counts. They also check the frozen all-visible three-entity objective,
correlated joint events, causal timing, gradients through hidden transitions,
finite underflow versus exact zero, unequal episode path counts and explicit
resource failures. The fresh flat model is not claimed to reproduce legacy flat
weights. Observed-only table eligibility, bound first-contact policy, native
checkpoint round trips, retained failure forecasts and interruption metadata are
covered. Two final regressions reproduced stale identity after report interruption
and persistent fingerprint failure; both now pass without weakening earlier tests.
The actual native CLI was exercised with synthetic flat/no-change
artifacts; legacy bundle regressions remain covered.

These are software and synthetic fitting invariants. No closed fixture was
reopened, historical checkpoint retrained, saved research model newly scored,
or scientific result changed. The tranche establishes a differentiable shared
implementation, not learned self-contact/count transfer, matched-budget advantage,
calibration or G1 admission.

`results/active-learning-validation-v5.json` records code identity, source hashes,
test output and frozen-input checks. This tranche adds **767 net runtime lines**
and **1,127 net test lines**. Retained research Python totals **22,708 physical
lines**. The eight active source files total **1,793 lines excluding frozen
dependencies**. That subset is not an inclusive size measure; the inclusive
2,000-line goal remains **unmet**. Historical code/evidence was not deleted to
improve a count. Test runtime is not an inference-latency or scientific-compute
benchmark.

## Earlier v4 domain integration verification

Published v4 code `2b281cd7f1ba0de4a7985cacc4bbf272783d01ed` has the same tree as
its locally verified `9132fa626d15c197b49f4d77d0971ed54ba1ef8d` (Git metadata differs).

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

`active_status.json` records the common expanded-domain training, prediction,
observation, native checkpoint and delivered-event evaluation APIs as implemented.
The next bounded tranche is a **prospective information-aware acceptance contract
and evaluator**, using this common path. It must freeze exact prediction points,
answerability under delivered observations, coverage/abstention rules, complete
worlds and whole-trajectory outcomes, proper probability scores, paired role
reversals, unchanged-entity errors, all required seeds, and failure/regression
denominators before any new substantive fit or research score. The current
delivered-event evaluator supplies none of the hidden-gold acceptance machinery.

Fresh held-out trajectory families, split/oracle lineage and checkpoint freezes
must accompany that contract. Retain the strongest applicable empirical controls
and separately report fixed exposure, capacity and actual compute; equal ceilings
or identical histories alone do not match them. A later controlled comparison
must include calibration and ambiguity strata, preserve every failure, and satisfy
the independent authorship/custody requirement for any G1 admission claim. The
opened common-objective and sensor-transfer studies remain closed. Another
same-author fixture or fresh seed does not become independent validation.

Keep the roadmap's G1 target and held-out families. Do not reinterpret historical
final-query results as whole-trajectory success or pool easy resets to manufacture
a 95% pass. The original generator already samples three through six entities
during training, so supporting six IDs is not an unseen-count transfer result.
A prospective unseen-count split must withhold those counts. Training self-contact
examples cannot count as success on the original untrained self-contact family.

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
