# Active nucleus: current implementation and next scientific decision

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22), [draft #61](https://github.com/robosys-labs/cemm/pull/61), stacked on [#60](https://github.com/robosys-labs/cemm/pull/60). Updated 2026-10-30 (Africa/Lagos).
Current cleanup source: `5a35c5d3db01901a5e016cb03cfe8c0284c6433d`; verified tree `e49d13cfd5ae2b912ab4bdbd9071910aed4de277`.
Prospective data source remains `8c662f588a9b81bdbcbdef48d3bdc26db1479c85`.
**G1 remains NOT ADMITTED. No later scientific gate is complete.**

## Progress and completion boundary

The latest learned result remains the closed [common-objective](COMMON_OBJECTIVE_DECISION.md)
and [sensor-transfer](SENSOR_TRANSFER_DECISION.md) studies: bounded use of retained
evidence, matched by strong empirical controls. Subsequent path/domain/learning/
acceptance/data work improves execution reliability; it adds no new learned
performance result. Invariant counts, PR counts and interfaces are not scientific
milestone completion. The earlier [decision review](G1_DECISION_REVIEW.md) already
identified a preparation loop; another planning-only cycle is not the next task.

The next substantive tranche must contain **one frozen comparison and its actual
KEEP / REVISE / REJECT / STOP result**. Commit the complete design before fitting,
then bind real checkpoints before collection in that same end-to-end tranche.
A further preparation-only tranche requires a reproduced defect that blocks that
specific comparison. Reuse the current APIs; no new general runner, checkpoint
format, diagnostics platform or model architecture follows merely from a low score.
The concrete task and decision boundaries are at the end of this document.

The 85.6287% expectation rejects the proposed **all-action 95% interpretation of
prospective-data-v1**, not the nucleus itself. Its archived finding and original
numeric target stay unchanged. The next task uses an explicitly declared
post-acquisition query scope; it cannot retroactively pass a historical gate.

## Active versus frozen paths

`active_participant.py` is the opt-in repository-backed command. Startup identifies
`active-inference-v5` and `active-evidence-v2`, including source hashes, predictor
class/configuration, declared domain, resource limits, weight/table fingerprints
and current training, checkpoint and adaptation provenance. Forecast receipts
bind this identity. `active-learning-v1` supplies Python training, replay and
evaluation APIs; `cemm-active-checkpoint-v1` stores registered learned state.
The prospective-data tranche preserved the eight learning/inference sources and
three `active-acceptance-v1` modules. The subsequent bounded cleanup changes only
`active_paths.py` to remove inherited initialization from frozen replay. `prospective-data-v1` adds four
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

## Current verification and dependency reduction

The cleanup source `5a35c5d3db01901a5e016cb03cfe8c0284c6433d` has exactly the locally verified tree
`e49d13cfd5ae2b912ab4bdbd9071910aed4de277` (local commit `f6ce5b4f12cbc324d474bd57db2fe3f45dc7182d`). The clean local suite passed
**627 tests, zero skips, in 68.430 seconds**; 67 existing path/domain/checkpoint
checks also passed. No new tests, model parameters, schema or framework were added.
`active_status.json` records the log hashes, source identity and dependency inventory;
final-head CI is tracked on [PR #61](https://github.com/robosys-labs/cemm/pull/61/checks).
The earlier data validation remains in
[prospective-data-validation-v1.json](results/prospective-data-validation-v1.json).

The empirical filter already overrode prediction and feedback; it now owns the
same three initialization statements directly. Its eight-world compatibility
constant comes from the existing geometry function. A fresh import of the active
participant, learning and checkpoint entrypoints loads **12 local modules / 2,730
physical lines**, down from 14 / 3,337. Including the still-required historical
hash pin, the package needs **2,915 lines**, down from 3,337. This measures source
dependencies, not resident memory, inference speed or learned performance.

The redundant 185-line `masked_replay.py` source pin stays because removing it
also changes the acceptance source inventory and pinned data commitments. That
migration is deferred; the module and old study runner are no longer imported.
Old native checkpoints remain bound to their original source checkout and fail
strict source matching here. Frozen v1 bundles, protocols and research evidence
are unchanged; there is no compatibility bypass.

The named fifteen-file integration inventory is **3,345 lines**, including
acceptance/data tools but excluding frozen dependencies. All retained research
Python is **26,039 lines**, including 11,809 test lines. These are distinct measures;
none meets the original inclusive 2,000-line goal. This cleanup reduces dependency
debt while adding one authored line. Duplicated historical handoff prose is replaced
by references below; the evidence itself is retained.

## Historical verification records

Historical verification is retained in the records below. Full test narratives,
local incomplete attempts, source/tree identities, compatibility checks and
historical size measurements remain in the
[immutable pre-consolidation handoff](https://github.com/robosys-labs/cemm/blob/1bfa4fbd9f57f25571505e13e31c71f97e01ac96/experiments/predictive_nucleus/ACTIVE_NUCLEUS.md).
These records establish implementation invariants, not new learned performance
or scientific admission. Historical source, checkpoints and failed studies are
unchanged.

| Tranche | Retained verification | CI reference |
|---|---|---|
| Acceptance v1 | [active-acceptance-validation-v1.json](results/active-acceptance-validation-v1.json) | [PR #60](https://github.com/robosys-labs/cemm/pull/60/checks) |
| Learning / inference v5 | [active-learning-validation-v5.json](results/active-learning-validation-v5.json) | [PR #59](https://github.com/robosys-labs/cemm/pull/59/checks) |
| Domain / inference v4 | [active-domain-validation-v4.json](results/active-domain-validation-v4.json) | [PR #58](https://github.com/robosys-labs/cemm/pull/58/checks) |
| Diagnostics / inference v3 | [active-evidence-validation-v3.json](results/active-evidence-validation-v3.json) | [PR #57](https://github.com/robosys-labs/cemm/pull/57/checks) |
| Repair / inference v2 | [active-repair-validation-v2.json](results/active-repair-validation-v2.json) | [PR #56](https://github.com/robosys-labs/cemm/pull/56/checks) |

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

## Next end-to-end tranche: evidence followed by prediction

**Task choice is settled; fitting and statistical commitments still need to be
frozen before execution.** This is externally scheduled acquisition, not a learned
clarification policy. Keep the v1 data recipe/archive and closed studies unchanged;
version the new information/query scope explicitly.

1. Use the **first existing distinct-entity contact** for acquisition, counted
   within the total contact budget. Choose its pre-contact pair from `01`, `10`,
   or `11` before latent-mode selection, and fully deliver its outcome. Account
   for any leading interventions when determining this pre-contact state.
   The two mode outcomes are respectively `(01,11)`, `(11,10)`, and `(10,01)`;
   they always differ. This proves sufficient evidence under the declared law,
   not that a model has learned to use it. Do not add a hidden third training contact.
2. Freeze **later contact indices** as post-acquisition queries before outcomes.
   Keep every acquisition/all-action forecast, proper score, abstention and failure
   in the existing report. Report query exactness and query-pair conjunctions
   separately without renumbering them as full trajectories. There are no
   intercontact resets, oracle-based query selection or easy-action padding.
3. Train on one or two **total** contacts. A single-contact episode has zero
   post-acquisition queries and remains acquisition/ambiguity evidence, never a
   100% query pass. Use fresh **two-contact in-family** episodes, with the second
   contact queried, for the 95% in-family continuation criterion. Separately
   evaluate **three to five total contacts for OOD composition** on declared
   chain/fork/cycle/disjoint histories. The old two-contact disjoint template needs explicitly
   declared repetitions; unique edges and total contacts are different quantities.
   Preserve the first held-out self-contact as a separate mode-invariant query,
   without an unscored self-contact warm-up or a false composition-depth claim.
4. Use the existing untied, learned-background shared kernel at hidden width 11,
   its reset-memory sibling with identical initial tensors, and the flat GRU at
   hidden width 3: **562 learned parameters each**, verified by construction.
   Keep no-change, untrained initial predictors and the strongest applicable
   observed-count controls, including contact and first-contact abstractions.
   Report eligible targets, unseen support and abstentions; matching parameter
   counts alone does not match function classes, evidence or consumed compute.
5. In the prefit commit, settle exact data/source hashes, primary contrast,
   fitting/selection/calibration rules, actual exposure/compute accounting,
   material gain, independent units and multiplicity. Use one fixed execution
   budget and all five model seeds. Five paired seeds alone cannot support a
   two-sided exact sign-flip p<.05 (minimum .0625); choose a justified analysis
   before outcomes instead of relabeling correlated views as independent samples.
   Then fit, bind actual checkpoint hashes, collect once and publish all outcomes.

The 95% criterion on declared post-acquisition queries is a **new prospective
scope**, with the original numeric threshold; it is not an all-action pass or
admission of the original frozen study. Independent challenge authorship/custody
and review remain necessary for admission. They do not prevent an honest bounded
public development decision. Use the existing adapter, fitting, artifacts and
acceptance scoring; a small query summary over validated points is sufficient.

**Decision at the fixed budget:** KEEP only the bounded competence actually
supported; REJECT superiority or choose the simpler control if it explains the
result; REVISE at most one reproduced representation/optimization/evidence cause
with its direct ablation; STOP this design if the comparison is infeasible or
adds no material useful transfer. Do not respond with another general audit
layer, a fresh same-fixture sweep or a larger architecture without that diagnosis.

## Remaining roadmap after that decision

| Stage | Evidence still required |
|---|---|
| G1 | Actual feasible, fair comparison and decision; independent evidence for admission. |
| G2 | Learned 1–2 to 3–5 composition, carried effects, independent-source functions and coherent uncertainty; reuse relevant G1 evidence. |
| G3 | Teach a relation nonverbally, then transfer it through two languages on the same frozen world model. |
| G4 | Communication improves held-out external-goal utility against silent/random/shuffled controls. |
| G5 | Answered experience persists across episodes, reduces later clarification and preserves earlier competence. |
| G6 | Corpus exposure improves new grounded decisions beyond retrieval/frequency controls. |
| G7 | The frozen task bank meets the stated 3× supported-utility, precision, retention and cost criteria. |
| G8 | Independent reproduction and reviewed integration with existing authority/effect boundaries. |

Learned probes, noisy sensors, lifelong learning, language, arbitrary entity counts,
optimizer/session resume, a durable forecast journal and a production isolation
platform are not added G1 prerequisites. Later success is conditional on evidence;
completion may require rejecting a hypothesis rather than growing its implementation.
