# Prospective acceptance: frozen forecasts and complete-world scoring

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22). This is an
engineering contract for collecting and scoring the active nucleus on declared
histories. **G1 remains NOT ADMITTED.** It neither executes a scientific study
nor changes the original `protocol.json`, its challenge, or any closed study.

## Scope and interpretation

Every action in every planned episode is a required prediction point. Episodes
contain three to six physical entities, a complete binary initial anchor and
noiseless visible readings. Missing readings remain absent. The active Session
limit is 128 actions; this does not replace the original G1 protocol's 12-action
budget. Shared-kernel self-contact still uses supplied alias conditioning.

All compared arms receive the same realized actions, sensor coverage, masks and
readings. Forecasts are retained before their own feedback. Gold truth and
answerability annotations are evaluator-only and never condition a participant
forecast. Evaluation restores native learned-state checkpoints for fresh
episodes; it does not fit, recalibrate or resume an optimizer.

The plan freezes every arm and seed, expected checkpoint digests, the observation
and oracle artifacts, source identities and the declared information law. Case
metadata identifies families, partitions, lineage, coordinate order and explicit
role pairs. Declared duplicate-risk lineage is checked across partitions; hashes
and declarations alone cannot prove the absence of undisclosed shared lineage.
`PROSPECTIVE_DIAGNOSTIC` plans require exactly the original five model seeds
`[7, 11, 23, 37, 53]`. `SYNTHETIC_INVARIANTS` permits a smaller seed inventory for
software verification; its scores are never research evidence. Repeating one
deterministic control checkpoint under seed labels does not create independent
control fits.
Seed labels are declarations rather than proof of the initialization RNG; the
report exposes checkpoint reuse across seed labels. Native checkpoint provenance
and collection records retain the actual state identities for review.

## API and command-line workflow

`acceptance_contract.py` validates artifacts and performs evaluator-only joins.
`acceptance_runner.collect` restores a native checkpoint and uses the existing
Session for every observed episode. `acceptance_scoring.evaluate` validates the
complete bundle before scoring; its lower-level `score_rows` only performs
arithmetic on already joined rows.

```python
from pathlib import Path
from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus.acceptance_runner import collect
from experiments.predictive_nucleus.acceptance_scoring import evaluate

inputs = contract.load_json("observed.json", INPUT_FILE_SHA256)
trace = collect(inputs, checkpoint=Path("learned-state.json"),
                expected_sha256=CHECKPOINT_FILE_SHA256,
                participant="kernel", model_seed=7)
trace_file_sha256 = contract.write_json("trace-kernel-7.json", trace)
# Oracle access belongs to the separate evaluator, after forecast collection.
plan = contract.load_json("plan.json", PLAN_FILE_SHA256)
oracle = contract.load_json("oracle.json", ORACLE_FILE_SHA256)
report = evaluate(plan, inputs, oracle, [trace])
report_file_sha256 = contract.write_json("acceptance-report.json", report)
```

Freeze the plan and its artifacts before collection; the example loads the
plan only in the subsequent evaluator phase. The uppercase names stand for
externally recorded 64-character lowercase SHA-256 values. Each output path must be new. The Python collector accepts a
`Path` checkpoint and a nonnegative integer seed; participant labels must match
the frozen plan. Run collection once for each planned participant/seed artifact,
then supply all traces to the evaluator. The example supplies one trace only;
any additional planned trials remain explicitly unproduced.

The equivalent collector command has no oracle, gold or plan argument:

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m experiments.predictive_nucleus.acceptance_runner collect \
  --inputs observed.json --inputs-sha256 INPUT_FILE_SHA256 \
  --checkpoint learned-state.json --checkpoint-sha256 CHECKPOINT_FILE_SHA256 \
  --participant kernel --seed 7 --output trace-kernel-7.json
```

Its CLI requires Python 3.13, PyTorch `2.10.0+cpu` and NumPy `2.3.5`, and enables
single-thread deterministic Torch execution. The scoring CLI uses the standard
library and no model, training or simulator imports:

```sh
python -m experiments.predictive_nucleus.acceptance_scoring \
  --plan plan.json --plan-sha256 PLAN_FILE_SHA256 \
  --inputs observed.json --inputs-sha256 INPUT_FILE_SHA256 \
  --oracle oracle.json --oracle-sha256 ORACLE_FILE_SHA256 \
  --trace trace-kernel-7.json --trace-sha256 TRACE_FILE_SHA256 \
  --output acceptance-report.json
```

Repeat `--trace` and `--trace-sha256` in corresponding order for further trials.
Omitting traces is allowed to expose the planned missing-work denominator; it
does not produce a complete experiment. The scorer prints the output file SHA
and `gate_g1: NOT_ADMITTED`.

## Artifact formats and hash meanings

Input, plan and oracle schemas reject unexpected structural fields. Byte loading
rejects duplicate keys and nonfinite constants and caps each artifact at 64 MiB.
There are two deliberately
different hash operations:

- `load_json(path, expected_sha256)` and all CLI SHA flags verify **exact file
  bytes**. `write_json(path, value)` returns that file hash and refuses overwrite.
- `digest(value)` hashes sorted compact JSON content. Plan `input_sha256` and
  `oracle_sha256`, oracle `input_sha256`, and trace `input_sha256` use this content
  digest. A pretty-printed file's byte hash is generally different.

`contract_digest()` verifies the exact `acceptance_protocol_v1.json` bytes against
`snapshots/active_acceptance_protocol_v1.sha256`. `software_sources()` supplies
the exact file hashes for the twelve active inference dependencies and three
acceptance modules. These form the required plan `software_sha256` inventory;
the evaluator rejects software drift. Oracle source and information-law hashes
are separate declared identities, not evidence that their claims are correct.

| Artifact | Exact top-level fields |
|---|---|
| Input | `version: active-acceptance-input-v1`, `episodes` |
| Plan | `version: active-acceptance-plan-v1`, `contract_sha256`, `study_id`, `scope`, `input_sha256`, `oracle_sha256`, `oracle_source_sha256`, `information_law_sha256`, `software_sha256`, `model_seeds`, `participants`, `reference_participant`, `cases`, `split_lineage`, `development_families` |
| Oracle | `version: active-acceptance-oracle-v1`, `input_sha256`, `source_sha256`, `information_law_sha256`, `episodes` |
| Collected trace | `version: active-acceptance-trace-v1`, `input_sha256`, `checkpoint_sha256`, `participant`, `model_seed`, `episodes`, `source_sha256`, `frozen_predictor_before`, `frozen_predictor_after`, optional `resources` |

An input episode contains exactly `episode`, `ids`, `observations`, `actions` and
`coverage`. For `T` actions there are `T+1` observation objects and `T` coverage
lists. Every observation names all IDs; absent later bits are JSON `null`, and
the initial anchor is complete. Coverage is a nonempty distinct-ID list selected
before feedback; observed bits must lie within it. Valid actions are:

```json
{"kind":"contact","participants":["a","b"]}
{"kind":"set","participants":["a"],"value":1}
{"kind":"observe","participants":[]}
```

Contact operands may alias. Binary values are integers 0/1, not booleans.
IDs and episode names are nonempty strings of at most 128 characters.

Plan `participants` maps each arm name to a map from **string seed** to native
checkpoint **byte SHA**, for example `{"kernel":{"7":"<64 hex characters>"}}`.
Every planned arm must contain every declared seed, and `reference_participant`
must name an arm. Each `cases` row has `episode`, `family`, `partition`
(`in_family` or `held_out`), `lineage`, `pair_id` and `direction`. Unpaired cases
use null for the last two fields. `split_lineage` has exactly `train`,
`selection`, `calibration` and `evaluation` lists of distinct, disjoint tokens;
each case's lineage belongs to `evaluation`. Held-out families cannot appear in
`development_families`.

A role pair contains two cases with directions 0 and 1, the same family,
partition, lineage, physical IDs, initial anchor, action count and coverage.
Every contact's operand order is reversed; set/observe actions are unchanged.
At least one contact has distinct operands. Subsequent readings may differ.

Each oracle episode has `episode`, `truth`, `possible_worlds` and
`information_keys`. `truth` contains `T+1` complete binary ID maps and must agree
with every delivered bit. Each of the `T` support lists is a nonempty sorted
list of distinct world indices containing that step's actual outcome. World
indices enumerate binary vectors lexicographically in **sorted physical-ID
order**: for three IDs, index 2 is `010` and index 4 is `100`.

Use `information_key(input_episode, step)` for each oracle key. It binds the
canonical delivered prefix, actions through the current action and coverage
through the current prediction. It excludes episode labels, family, hidden
truth, future observations and current realized dropout. Equal keys must have
equal declared support. This consistency check does not prove that all possible
alternatives were included. Predictable or outcome-ignorable dropout is a
declared assumption, not an authenticated property of the data.

Input, plan and oracle episode inventories must agree exactly. A missing trace
or trace episode instead creates `UNPRODUCED` points for every missing planned
action. Duplicate or unplanned trials, cases and output steps are rejected.
Native Session receipts bind action, coverage, implementation and forecast;
checkpoint/control/state identities and source hashes are checked on collection
and on the evaluator join.
The evaluator also checks that current and checkpoint metadata agree, and that
the raw and normalized log vectors share support and the recorded normalization
correction. A recomputed receipt does not excuse an internally contradictory
artifact.

## Denominators and uncertainty

The primary raw exactness denominator is every planned action. Report complete
worlds, including untouched coordinates, and keep answerable and ambiguous
strata separate. Answerability comes from the declared evaluator information law
and its compatible complete-world alternatives before the forecast's feedback.
It does not come from model confidence, later readings, the realized answer, or
the number of distinct targets in a sampled group.

Whole-trajectory exactness is the conjunction of all required predictions in an
episode **with delivered feedback**. It is not free-running rollout success or a
whole-hidden-trajectory likelihood. A role pair has two explicitly identified
directions; pair success requires both complete trajectories to be correct.
A failure while processing final feedback does not erase an already valid final
forecast, so a trajectory conjunction can be correct while execution is failed.
Correctness and execution completion are separate claims.

Abstentions and unproduced outputs remain in planned exactness and coverage
denominators. They have no invented distribution or numeric proper score.
Answered-only accuracy and probability averages are explicitly conditional;
missing work cannot silently improve an all-planned result. Invalid input or
gold inventories are rejected rather than repaired by dropping records.

Joint NLL uses the retained log probability of the complete true world. A true
zero produces infinite NLL; finite log values remain finite even when their
exponentials underflow. Brier scores use the complete joint distribution. No
oracle-support conditioning, probability clipping, smoothing or uniform-over-
support assumption is applied. Compatible alternatives establish a declared
answerability stratum, not a Bayes distribution or probability-score floor.

Ten fixed confidence bins provide a descriptive ECE diagnostic, using joint-MAP
confidence and the correctness of that same prediction. This does not establish
calibrated uncertainty or an ECE admission threshold. Identifier views are
correlated; repeated views and model seeds are not independent physical worlds.

The report retains per-point statuses `ANSWERED`, `ABSTAIN` and `UNPRODUCED`, plus
all/answerable/ambiguous summaries, trajectory and role-pair conjunctions,
per-participant seed/family/entity-count/action/partition breakdowns, and paired
repairs/regressions against the declared reference. `mean_nll` and `mean_brier`
are available only when every planned point in that summary has a distribution;
`conditional_mean_nll` and `conditional_mean_brier` name the supported subset.
Infinite scores use explicit `positive_infinity` strings in strict JSON; absent
scores use null. Failed and missing work remains in metadata and denominators.
Each seed has family breakdowns; per-forecast wall/CPU p50 and p95 describe only
the timed prediction region. Collection resources report actual neural parameter
count, empirical context/distinct-outcome/observed-event counts, numerical runtime
settings, total collection time and process-lifetime peak RSS. These figures do
not establish capacity or consumed-compute matching.

Collection freezes each forecast in memory before feedback and retains valid
prefixes on ordinary episode exceptions. It then proceeds to other declared
episodes without retrying the failed episode. The CLI writes the trace after
collection; it does not flush every forecast durably before feedback or guarantee
partial-file recovery after process termination. Predictor mutation or an
unverifiable frozen identity invalidates collection. A valid output file is not
proof that every episode completed; inspect failures and missing-work records.

## Scientific prerequisites remain separate

The original gate requires at least 95% in-family complete-world exactness for
each of at least five seeds, role reversals, no source-only spurious changes and
matched-baseline OOD improvement. The new all-action and answerability metrics
do not silently redefine its denominator. No score produced here admits G1.

A scientific comparison still needs fresh held-out families, independent
authorship and custody, reviewed oracle completeness, frozen checkpoint and
split lineage, calibration, predeclared significance and matching decisions,
and retained failure/regression records. Keep the strongest applicable empirical
controls and report their support and target eligibility. Equal histories,
update counts or CPU ceilings do not establish equal information, capacity or
consumed compute.

The current flat default has 1,512 parameters versus shared defaults of
470/584/972; these capacities are not matched. Three-to-six-entity support is not
unseen-count transfer, and fitting self-contact examples cannot count as success
on the original held-out self-contact family. New composition workloads must
carry earlier effects into later inputs without resets erasing the dependency.

The common-objective and sensor-transfer studies remain closed. A fresh seed,
second process, separately written evaluator, hash or manifest assertion does
not establish independent custody. External gold must remain outside the
participant environment under a separately accountable evaluator's policy;
the software's identity and causal-order checks do not enforce that isolation.
