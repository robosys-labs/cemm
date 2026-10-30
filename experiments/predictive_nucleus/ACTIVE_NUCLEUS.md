# Active nucleus: observed learning, acceptance and prospective data

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22); prospective-data
[draft #61](https://github.com/robosys-labs/cemm/pull/61),
stacked on [draft #60](https://github.com/robosys-labs/cemm/pull/60).
Prospective data source: `8c662f588a9b81bdbcbdef48d3bdc26db1479c85`.
Locally verified code/assets: `cd9df92861f9e0ea1c2000ee4aa1c356b40e1169`, tree
`7fbf1f6c670f2e77d4bfac32a69636974fc8a6e5`.
Decision: KEEP the public observed curriculum, exact conditional oracle, asset
audit and observed-only batch adapter; REVISE the prospective information/query
and comparison contract before research fitting. The default evaluation
in-family all-action ceiling is 85.6287% under its declared information law.
**G1 remains NOT ADMITTED. The original 95% target is unchanged.**

## Active versus frozen paths

`active_participant.py` is the opt-in repository-backed command. Startup identifies
`active-inference-v5` and `active-evidence-v2`, including source hashes, predictor
class/configuration, declared domain, resource limits, weight/table fingerprints
and current training, checkpoint and adaptation provenance. Forecast receipts
bind this identity. `active-learning-v1` supplies Python training, replay and
evaluation APIs; `cemm-active-checkpoint-v1` stores registered learned state.
The eight learning/inference sources and three `active-acceptance-v1` modules
are unchanged by the prospective-data tranche. `prospective-data-v1` adds four
sources for generation, a conditional oracle, auditing and observed-only batch
conversion, bringing the active-file inventory to fifteen. The existing Session,
native artifacts, streaming transport, verified bundle loader and learned modules
are reused. Historical sources, protocols, checkpoints, studies and standalone
v1 exports remain unchanged.

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

This delivered-event evaluator has **no hidden gold**. It does not measure complete-world
accuracy on unobserved bits, trajectory correctness, role-pair success,
calibration, scientific independence or G1 acceptance. Its engineering scope
must not be promoted to the roadmap's outcome gate.

## Prospective acceptance contract, collector and scorer

`ACCEPTANCE.md` documents the implemented APIs, commands and artifact formats.
`acceptance_protocol_v1.json` freezes the scoring/recording contract,
not a complete scientific study. The original protocol and its target remain
unchanged. Inference stays `active-inference-v5`, learning stays
`active-learning-v1`, and the native checkpoint format is unchanged.

`acceptance_contract.py` validates exact input, plan and evaluator-only oracle
inventories. A plan commits every participant/seed checkpoint hash, observed
input and oracle digests, oracle-source and information-law identities, and the
fifteen inference/acceptance source files. It names each case's family,
partition, declared duplicate-risk lineage and optional reversed-role pair.
Declared lineage tokens cannot cross train/selection/calibration/evaluation
partitions, and held-out families cannot appear in the declared development
family inventory. These checks do not establish the completeness of external
lineage declarations. Prospective plans require all five original model seeds;
synthetic invariant plans can use fewer and remain explicitly synthetic.

`acceptance_runner.collect` and its CLI take observed histories and a
hash-verified native checkpoint, with no gold or oracle argument. Each episode
uses the existing Session with three to six entities, a complete anchor,
noiseless visible readings and the 128-action limit. Every action is a required
prediction point. Receipt-checked forecasts are copied before their feedback;
the collector checks frozen weights/tables, configuration and current/native
metadata throughout the run. It records per-forecast timings, path diagnostics,
actual parameter/table size, runtime identity and process costs. Equal recorded
ceilings or parameters do not establish matched consumed compute.

Collection retains valid prefixes and ordinary episode failures and proceeds
to other declared episodes without retrying the failed one. Forecast freezing
is **in memory**; the CLI writes the trace after collection. It does not provide
crash-durable per-forecast journaling or an OS isolation boundary. Identity
mutation invalidates collection. Sensor provenance, predictable/outcome-ignorable
dropout and independently held gold remain external assumptions or requirements.

`acceptance_scoring.evaluate` and its CLI join the frozen traces to separate
complete-world truth only for scoring. Joins check source commitments, native
specification/state/control/provenance, forecast receipts and raw-versus-normalized
log consistency. Missing or extra input/gold cases are rejected. Missing trials,
episodes or later forecasts become `UNPRODUCED` and retain every planned
denominator; empirical `ABSTAIN` remains distinct and has no invented score.

Answerability is singleton **declared complete oracle support** under the
delivered prefix/current action/selected coverage. Consistent information keys
cannot receive conflicting support. The acceptance validator does not prove
that caller-supplied alternatives are exhaustive, infer a uniform prior from
support size, calculate a Bayes floor from it, or condition a submitted forecast
on oracle support. The separate prospective oracle below computes alternatives
under its explicitly declared physical and observation law.

Reports include all-planned complete-world MAP accuracy, answerable/ambiguous
strata, joint NLL/Brier, unchanged-coordinate errors, explicit coverage, fixed
ten-bin joint-MAP ECE diagnostics, per-seed/family breakdowns and reference-arm
repair/regression IDs. Exact-zero truth probability gives infinite uncapped NLL;
finite log underflow is preserved. Full proper-score means require distributions
at every planned point; supported-only means are explicitly conditional. Reused
checkpoints and physical lineages remain visible rather than counted as new
independent fits or worlds. Latency summaries cover the reported prediction
region, not end-to-end service performance.

Whole-trajectory exactness is an AND of all required forecasts **with delivered
feedback**, and role-pair success requires both explicitly reversed trajectories
to be correct. Neither is a free-running rollout or a hidden-trajectory
likelihood. A failure during final feedback does not erase its valid forecast;
forecast correctness and execution completion remain separate. The per-seed
comparison to 0.95 is numeric reporting only, with `admission_decision: false`.
Every report retains `gate_g1: NOT_ADMITTED`.

## Prospective observed curriculum and conditional oracle

`PROSPECTIVE_DATA.md` documents the new `prospective-data-v1` data contract,
exporter and findings. The source/hash-pinned default archive is
`data/prospective-assets-v1.json.xz`, SHA-256
`42cf52fb84fece67d23b78751080cd6c6d603767cc6981a517116dca52995f6d`.
Two separate exports of the same public recipe produced identical bytes for
all eleven files. This is reproducibility, not independent authorship or custody.

| Split | Physical draws | Episode views |
|---|---:|---:|
| Train | 64 | 128 |
| Selection | 32 | 64 |
| Calibration | 32 | 64 |
| Evaluation | 200 | 368 |
| Total | 328 | 624 |

Development contains single contacts and overlapping or repeated two-contact
histories. Evaluation also includes the original chain, fork, cycle, disjoint
and self-contact families. The domain remains three to six entities, with a
complete initial anchor and at most twelve actions. Self-contact is evaluation-
only and has no redundant reversed view. Entity-count support is not unseen-count
transfer. The original protocol and all historical challenge seeds remain untouched.

`prospective_data.py` samples an observable blueprint before its hidden mode.
Blueprint identity includes the anchor, action schedule, full selected coverage
and realized masks, canonicalized over naming and global contact reversal.
No resulting bits or actual orientation enter deduplication. Accepted blueprints
and physical lineages do not cross splits; 45 concrete action templates are
shared across in-family splits and explicitly disclosed. Disjoint blueprints do
not imply unfamiliar atomic contexts or independently authored families.

A leading set and trailing observe are independently proposed with probability
one half, and there are no resets between contacts. Duplicate rejection can
change accepted proposal frequencies. All cases, including no-change and no-carry
cases, remain. Each reversed pair shares its actual hidden orientation, anchor,
IDs, coverage and masks; both directions are simulated separately. At most three
missing bit-events occur over an episode, so the full-support bound is eight
recurrent histories and 512 candidate expansions. The participant receives no
oracle support for pruning.

`prospective_oracle.py` composes affine binary maps for both persistent source
orientations. Before current feedback, it emits every complete world compatible
with the delivered prefix and its conditional probability under the explicit
balanced prior. It preserves mode identity even when world states coincide.
Only delivered feedback filters alternatives. The oracle's arguments contain no
actual mode, family or hidden truth. Completeness is conditional on this supplied
two-mode law; it is not proof of externally correct physics or a measurement of
the learner's uncertainty over unknown laws.

`prospective_audit.py` reconstructs both modes of each fixed blueprint, checks
exact family/count/pair inventories, and computes law-weighted event accuracy
ceilings and proper-score floors. These use explicit probabilities, not a
uniform-prior assumption inferred from support size. Trajectory and role-pair
conjunctions use coherent branches and the frozen lexicographic MAP tie rule;
they are not products of event ceilings or optimal joint-policy bounds. A correct
probability forecast can have zero paired MAP exactness when complementary role
outcomes tie. Carry witnesses check whether suppressing an earlier contact
changes a later contact's destination, rather than merely preserving a bystander
change. Evaluation has 198 carry-positive branches out of 736 mode/view branches;
these correlated branches are not independent samples.

The evaluation in-family design has 334 planned actions and law-expected
ambiguous mass of 96. Its expected optimal event accuracy is
`1 - 0.5 * 96 / 334 = 0.8562874251497006`, or **85.6287%**. Across all evaluation
families it is **87.1730%** over 1,185 actions. These are conditional information-
design calculations, not trained-model scores or hard bounds on a finite
realized sample. They quantify why an all-action interpretation of the unchanged
95% target is unattainable in expectation on this design. The historical 93.75%
ceiling belongs to a different closed workload. Neither finding is a model
regression or permission to redefine G1.

`observed_io.load_batches` converts the same delivered input files into validated
`ObservedBatch` records. It groups full episodes by entity count and length,
canonicalizes coordinates and preserves missing values and masks without temporal
padding or gold filling. It imports no simulator or prospective oracle. Every
compared arm must use the same batching policy. Of the training tape's 336 events,
332 deliver at least one bit; four all-missing events remain. Of 192 contacts,
64 have full before/after readings and 104 have both operand readings. These
counts do not establish equal target eligibility under every empirical history
policy, or matched exposure/cost.

The exporter writes separate observed and evaluator files and a completion
manifest last; an existing destination is rejected. An I/O failure can leave a
new incomplete directory without its manifest. Keep the combined archive, audit
and case metadata on the evaluator side. The code does not impose OS isolation,
secret seed custody or physical provenance. This public same-author asset audit
runs no research fit, saved-model evaluation or scientific comparison.

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

## Current prospective-data integration verification

The clean source/assets commit `cd9df92861f9e0ea1c2000ee4aa1c356b40e1169` passed
**627 tests in 72.123 seconds, zero skips**. The **37 new tests** comprise eight
oracle, nine generator, thirteen audit, five observed-adapter and two integration
checks; the focused set passed in 7.519 seconds. The original protocol, all
16 historical locks, the acceptance lock, the new data lock and frozen-input
preflight passed: **20 standalone checks**. Preflight retained complete history,
a clean tracked tree and no untracked files, with study execution disabled.
Published source commit `8c662f588a9b81bdbcbdef48d3bdc26db1479c85` has exactly the
locally verified tree; only Git commit metadata differs. Final-head CI belongs to
[the prospective-data PR](https://github.com/robosys-labs/cemm/pull/61).
The retained validation record is `results/prospective-data-validation-v1.json`.

The oracle checks exhaust every binary initial state and action at each supported
entity count against the original imperative physics, with separate checks for
persistent correlations, mode coalescence, aliases, intervention constants,
partial readings and causal timing. Generator tests cover exact inventories,
source commitments, latent-independent selection, canonical overlap and paired
sensor/role coupling. Two malformed audit reproductions exposed complete-pair
deletion and family relabeling; both are rejected after the fixes. Adapter tests
check observed-only conversion and native forecast parity, while integration
checks cover the actual exporter CLI, no overwrite and reproducible artifacts.

No research model was fitted or scored. Inference, learning and acceptance
sources remain unchanged; learned parameter delta is **zero**. The tranche adds
**659 runtime lines** and **839 test lines**. Fifteen active files total **3,344
physical Python lines excluding frozen dependencies**; retained research Python
totals **26,038 lines**. The inclusive 2,000-line goal remains **unmet**. No
historical evidence was deleted, and suite timing is not a scientific-compute or
inference-latency benchmark.

## Earlier acceptance integration verification

The clean code commit `956078ffc509b945bd86b2393d8453ee5bdb81bc` passed
**590 tests in 54.477 seconds, zero skips**. The **44 new tests** comprise
13 artifact-contract, 10 collector, 17 scoring and four integration checks;
the focused set passed in 6.752 seconds. The original protocol, all 16 historical
manifest locks, the new acceptance-contract lock and frozen-input preflight
passed: 19 standalone checks. Preflight ran with a clean tracked tree, no
untracked files and study execution disabled. The published source tree exactly
matches the clean locally verified code tree. Full evidence is recorded in
`results/active-acceptance-validation-v1.json`; final-head CI status is recorded
on [the acceptance PR](https://github.com/robosys-labs/cemm/pull/60).

Synthetic checks exercise dynamic geometry, causal information keys, missing
and incomplete inventories, role-pair and trajectory conjunctions, source and
lineage drift, ambiguity, exact zeros, finite underflow, conditional means,
native checkpoint collection and actual command-line scoring. Integration
reproduced three malformed traces that previously passed: a frozen predictor
specification inconsistent with its checkpoint, inconsistent raw/normalized log
vectors and an oversized normalization correction. All three are now rejected.
The valid terminal-contradiction forecast and future unproduced denominator are
retained, and changing evaluator-only targets cannot change collected forecasts.

No research fitting or new scientific performance comparison ran. Closed studies,
historical results and all learned modules remain unchanged; learned parameter
delta is **zero**. This tranche adds **892 runtime lines** and **940 test lines**.
The eleven active files total **2,685 physical Python lines excluding frozen
dependencies**, and retained research Python totals **24,540 lines**. The
inclusive 2,000-line goal remains **unmet**. No historical evidence was removed
to improve the size figure, and suite timing is not a compute/latency benchmark.

## Earlier v5 learning integration verification

Published v5 code `94c059a0fd4fdb78ad5f442419053ac99e41c124` matches the
locally verified `5a857ab0879cb1e67ca01a1de888eafbabace5d0` tree
`adb0ec97aac6e3f28d5e24f5909d8c9ae2e470ec`.

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

The common learning/inference/native-checkpoint path, acceptance collector and
scorer, and public prospective data/oracle/audit/observed adapter are implemented.
The next engineering decision is the **information/query and comparison contract
before fitting**. The 85.6287% expected in-family ceiling makes an all-action 95%
interpretation incompatible with the current data law. Define any proposed task,
query scope or information intervention from permitted preforecast evidence,
quantify its identifiability and state the scientific interpretation explicitly.
Preserve all-action diagnostics, ambiguous proper scores, role-pair tie behavior,
and the original gate. Do not pad easy actions, select cases from outcomes or
silently substitute an answerable-only denominator.

Then freeze concrete arm configurations, fitting/selection/calibration rules,
material effect sizes, statistical units and multiplicity decisions, and actual
exposure/capacity/consumed-compute comparisons. Retain the strongest applicable
empirical abstractions, eligible-target/support accounting and every planned
failure or regression. Equal histories, update limits or CPU ceilings do not
match information or cost. Five seed labels are not five independent physical
worlds; repeated views and steps are correlated. Under a two-sided exact sign-flip
test on only five seed pairs, the minimum p-value is `2 / 2**5 = 0.0625`; a claimed
5% test requires a prospectively justified design rather than a convenient label.

There are two freeze stages. Commit the complete data and comparison design
before substantive fitting; after the prescribed fitting and selection, bind
actual native checkpoint byte hashes to those prefit commitments before
collection. A data manifest is not a completed acceptance plan, and placeholder
weight hashes cannot substitute for fitted artifacts. Reuse the existing
observed adapter, fitting APIs, native checkpoints and acceptance collector/scorer.
The current data contract deliberately leaves research fitting and model scoring
disabled while its scientific comparison remains incomplete.

Separately accountable challenge authorship/custody, external oracle review and
evaluator-controlled isolation remain admission requirements. The new analytic
oracle is complete only under the declared law; public same-author assets and
new deterministic seeds do not independently validate that law or a learner.
Issue #55 remains pending and does not replace the engineering decisions above.
The opened common-objective and sensor-transfer studies stay closed.

Keep the roadmap's G1 target and held-out families. Historical final-query results
are not whole-trajectory success. Supporting three through six entities is not
unseen-count transfer without a withheld-count design, and training self-contact
cannot count as success on the original untrained self-contact family.

G2 remains the subsequent concrete workload: train on one or two interactions
and evaluate three to five over declared chains, forks, cycles and disjoint
groups, including repeated actions, untouched entities and coherent joint
alternatives. Earlier effects must enter later transitions without resets erasing
the dependency. Shared uncertain mechanisms must retain correlation across uses.
The current asset audit does not admit G2 or establish learned composition.

Posterior-context support, alternate change-point evidence, calibrated confidence
and learned probe selection remain unestablished. Grounded bilingual language
and G3–G8 follow the roadmap dependency order. Learned communication and lifelong
learning are not new G1 prerequisites. No scientific gate is weakened or admitted,
and no production/PR21 cutover or language implementation occurs here.
