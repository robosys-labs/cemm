# Frozen participant handoff — no new public experiment

Tracking: #22 / draft #54, after the closed #52 and #53 studies.
Decision: **KEEP the bounded retained-evidence capability; stop same-author
same-physics sweeps; hand the frozen participants to an external evaluator.**
G1 remains **NOT ADMITTED**. No independent author has yet accepted custody,
and no independent challenge or new performance result exists in this tranche.

## What this changes

The research replay API takes a complete trace and imports research-runner
helpers. Its published causal-ordering checks were not a process boundary.
This handoff exports only the definitions needed for inference and gives the
external evaluator a strict streaming interface. It does not repair or relabel
any historical result, nor assert that the previous studies leaked answers.

`export_participant.py` checks the completed original report, its fit inventory,
all selected checkpoint/table bytes and five frozen source hashes. It extracts
whole definitions verbatim; only module-level import/constants scaffolding is
selected. No neural architecture, learned tensor, table count, filtering rule,
normalization tolerance or supplied inductive bias changes. Tests compare the
extracted definition ASTs and original/exported predictions.

The generated package includes all six informative/fixed-exposure variants and
seeds 7, 11, 23, 37 and 53: **30 unchanged checkpoints**. Three original count
tables support prefix/local/contact memory; first-contact uses the unchanged
contact table with its declared context truncation; no-change is last-observed
state. Do not fabricate seed replication for those five control variants.
Original parameter counts, observed-training-input hashes and measured training
costs are retained in the manifest. They do **not** become matched-capacity or
matched-consumed-compute comparisons by being packaged together.

The exported runtime contains **671 physical Python lines**, including the
transport and selected inference dependencies. It contains no simulator,
dataset generator, neural optimizer loop, accuracy scorer or research-runner
import. The original `SensorMemory` class keeps its count-table `fit` method
verbatim; the endpoint neither exposes nor calls it. No training examples are
exported beyond the empirical baseline's required learned count tables.

This is not a claim to meet the roadmap's inclusive 2,000-line goal: the exporter
and new tests add another 596 lines, evaluation is deliberately absent, and the
retained research namespace is **18,229 physical Python lines** including all
historical studies/tests. No history was deleted or reformatted to reduce LOC.

## Build and verify without training

Use the completed PR52 evidence directory containing `report.json`, `COMPLETE`
and `fits/`. Its durable repository result is commit
`d622161fc7e27165715415c5a50c0d64bd076f49`, branch
`research-results/common-objective-40838302597`. The original report hash is
`581172fcfd257127772ea9962544bae1071bc43ce683fca225128e9de5f5d078`.

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m experiments.predictive_nucleus.export_participant \
  --evidence /absolute/path/common-objective-output \
  --output /absolute/path/new-participant-directory --verify > verification.json
```

The output must not exist, and must be outside the source checkout. A failed
export has no successful manifest. Source origins remain PR53 commit
`0d48f779215296120577b850d4c9ee329082e59f`; the exporter and transport are new code,
not falsely attributed to that historical commit.

Expected exported manifest SHA-256:
`2373c2d366c4f8a855dbb7498e5d6a88bc55b9078a00400eb51db86ca115a1a8`.

The `--verify` path restores every selected checkpoint and all control variants,
then compares **280 forecast vectors** with the original implementation on one
hand-written four-action history, with and without missing readings. It does
not generate a world, query a gold evaluator, fit weights, compute accuracy or
rerun either closed public fixture. It is same-author software verification,
not independent research validation or evidence of generalization.

## External runtime contract

Python 3.13, CPU-only PyTorch 2.10.0 and NumPy 2.3.5 are required. One intra-op
and inter-op thread and deterministic algorithms are set. Run one process for
one episode and chosen participant; account for process/startup costs separately
from the reported per-forecast CPU/wall timing. This single-episode transport is
not a high-throughput serving benchmark.

```sh
python participant.py \
  --manifest-sha256 2373c2d366c4f8a855dbb7498e5d6a88bc55b9078a00400eb51db86ca115a1a8 \
  --participant kernel_learned_persistence --seed 7
```

Neural names: `kernel_supplied_persistence`, `kernel_learned_persistence`,
`kernel_untied_roles`, `kernel_memory_reset`, `flat`,
`flat_supplied_persistence`. Controls: `prefix`, `local`, `contact`,
`first_contact`, `no_change`, without `--seed`.

One JSON object per newline, request then response:

```json
{"op":"start","episode":"held-001","ids":["a","b","c"],"observation":{"a":1,"b":1,"c":0}}
{"op":"predict","episode":"held-001","step":0,"action":{"kind":"contact","participants":["a","b"]}}
```

Read and durably retain the forecast BEFORE delivering any next observation.
The response includes raw and normalized log probabilities, coordinate order,
normalization correction, filter diagnostics and a receipt. Then send feedback
with the returned receipt, not the placeholder below:

```json
{"op":"feedback","episode":"held-001","step":0,"receipt":"<returned receipt>","observation":{"a":null,"b":0,"c":0}}
```

`null` is genuinely absent sensor evidence; both families receive the same
visible readings, masks and actions. A complete initial anchor is required.
Set actions additionally require a binary integer `value`; observe has an empty
participant list. ID strings are mapped to supplied sorted slots, not learned
identity semantics. Results enumerate all eight three-bit worlds in lexicographic
order. Finite log probabilities remain finite even if exponentiation underflows;
null log values explicitly mean negative infinity. Abstentions have no numeric
forecast and must not be treated as zero-confidence predictions.

Finish with `{"op":"end","episode":"held-001"}`. Ending after a final forecast
without feeding its answer is allowed and explicitly reported as pending.
The end response checks unchanged weights/tables, but is NOT an evaluation or
study-success marker. Any ordering/schema/support/path-limit error terminates
the process with a nonzero exit; preserve its prior outputs and do not silently
retry, drop that episode or substitute a favorable seed. Duplicate feedback
and a second prediction over an unconsumed forecast are rejected.

Limits are explicit: **three binary entities, full initial observation, noiseless
visible bits, 128 actions, and the existing 64-path cap without pruning**. Keep
over-limit/out-of-support failures in the external report. Missingness is not
noise handling. The two-mode family, locality, identity-equivariant sharing and
exact path filter remain supplied assumptions. There is no language, learned
probing policy, online weight update or new architecture here.

## What an independent evaluator must own

Before any scored run, a separately accountable author/custodian must accept
ownership, commit the participant hash, freeze the challenge/protocol and retain
undisclosed gold outcomes outside the participant environment. A fresh seed, a
second process or a second implementation by this assistant is not independent
authorship. No independence claim can be obtained merely by editing a manifest.

The evaluator must predeclare unfamiliar trajectory/graph families, all test
and exclusion counts, support/overlap analysis, the valid in-family domain,
answerable versus genuinely ambiguous strata, precise G1 gate interpretation,
capacity/resource comparisons and all stopping/failure rules. These choices
must not be selected to make the neural model win or after observing its scores.
Keep the strong empirical control, all five neural seeds and explicit regressions.
Evaluate complete worlds and preserved entities, reversals and renamings; retain
proper probability scores and abstentions, not only MAP accuracy. Do not inflate
sample sizes with identifier permutations or pool easy resets to manufacture a
95% pass. No admission target or denominator is changed by this handoff.

Use separate evaluator-owned sandbox/container policy: no network access, no
oracle/test files mounted into the participant, read-only reviewed bundle,
explicit CPU/RAM/time budgets and retained stdout/stderr. The code checks hashes
and message order; it does **not** enforce an OS sandbox, signatures, sensor
provenance or independent custody. The mandatory expected digest must come from
an independently recorded release, not simply be trusted from a mutable local
file. Review the entrypoint and dependency installation as well as its manifest.

## Verification and stop rule

31 new tests cover source extraction, deterministic exports, schema/order and
receipt checks, missing readings, corruption, checkpoint restoration, unchanged
predictions and actual standalone CLI invocation. The final local suite found
410 tests: **409 passed, one skipped** because the verified source archive lacks
Git history. All **16 historical manifest locks** pass. Complete-branch CI runs
the checkout-dependent integration test; its actual result is recorded in #54.
The retained actual-weight parity record is
`results/external-participant-validation-v1.json`.

No public fixture was reopened and no research workflow was enabled. Production,
PR21, old protocols, checkpoints and failed studies are unchanged. The next
scientific dependency is acceptance by an external challenge author/custodian,
not another same-author diagnostic or a new neural layer. After that, run the
agreed evaluation once and retain ties, failures and regressions. Until then,
only concrete handoff defects or an explicitly reviewed hypothesis revision
justify further work on this path; green software tests do not admit G1.
