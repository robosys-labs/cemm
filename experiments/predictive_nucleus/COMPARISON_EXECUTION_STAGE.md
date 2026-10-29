# Frozen comparison runner: preflight and fit/checkpoint phase

Tracking: #22, stacked on #50. Date: 2026-10-29.
Decision: **KEEP** this implementation tranche; **G1 HOLD / REVISE**.
The frozen study has NOT run. This is a partial runner implementation, not a
completed comparison or a claim of independently reviewed scientific evidence.

## Scope and roadmap

The roadmap still requires a small world-first learner, fair controls, preserved
failures and an independent challenge before language. This tranche implements
the execution mechanics for the already-frozen public comparison rather than
altering its data, model, objective, budgets, metrics or acceptance criteria.
The previous complete-branch CI for `2eeae63` is confirmed successful (run
40828511742). The protocol remains byte-identical at SHA-256
`15732afe065f19f3b412a7638e386373eb586ddaa273104e2de63c14a782b1f3`.

| Item | Implemented boundary |
|---|---|
| Hypothesis | A frozen fit can be reproduced and audited only if inputs, initialization, complete checkpoints and failure state remain identifiable. This is an engineering invariant, not evidence of cognitive competence. |
| Preflight | Exact protocol/source/data hashes; source-before-protocol-before-runner ancestry; committed source bytes; complete non-sparse history and present tracked files; clean tracked checkout. |
| Plan | Exactly 120 ordered fits, with the specified rotating model order across regimes, conditions and seeds. Constructing the plan does not instantiate or fit a model. |
| Initialization | Same model/seed has identical initial tensor fingerprints across conditions/regimes; checkpoint restoration preserves the RNG stream. |
| Fit | Use the unchanged common fitter and copy the same measured training history for each model; verify no mutation. No second-pair evaluation input is passed as training. |
| Checkpoints | Save initial and final plain CPU tensor dictionaries exclusively; flush; hash bytes and semantic tensors; verify exact keys, dtype, shape, finite values and strict restoration. Recheck all retained checkpoints before the phase report. |
| Controls | Only after all neural fits, fit and retain all six measured-outcome tables, verify complete counts, serialize and reconstruct them without scoring. No-change has no fitted table. |
| Costs | Retain actual updates, exposures, setup/wall/process-CPU costs and overshoot. An incomplete fixed-exposure fit is an error; a CPU-limited fit is labelled accordingly. Equal ceilings are not equal consumption. |
| Failure | Retain previous verified fits, the failed task, initial checkpoint and best-effort failed partial state; stop without retrying or skipping. Never admit a partial/nonfinite state as a completed fit. |
| Output | New directory outside source checkout, existing parent, no overwrite or symlink output. Nonfinite failed metadata receives explicit strict-JSON diagnostic tags, not a repaired numeric score. |

`comparison_execution.py --preflight` is the ONLY public command. It runs in a
fresh process with CPU-only PyTorch 2.10.0, Python 3.13, one intra-op thread,
one inter-op thread, deterministic algorithms and PYTHONHASHSEED=0. The inter-op
setting is not pretended to be safely restorable in an already-active process.
The internal `_fit_phase` helper is not called by that CLI or by CI on public
comparison data. It requires the future orchestrator to run the frozen preflight
and runtime setup first; it is not an independent authorization/custody boundary.

The phase can only produce `FITS_VERIFIED_NOT_EVALUATED`, with
`study_complete: false`. It cannot emit `COMPLETE` or a study-success report.
The files and hashes are cooperative provenance/integrity checks, not signatures,
independent custody, safe handling of arbitrary hostile checkpoints, or proof
of cross-host reproducibility.

## Validation and errors exercised

35 new tests: 34 run locally; one requires a complete committed checkout and is
explicitly skipped in the reconstructed local source archive. The complete-branch
CI must execute that test and verify the real frozen sources, four datasets,
120-fit plan and CLI no-execution status. Its final result belongs in the PR
checks, not an assumed local success.

Tests inject corrupt checkpoint bytes, semantic hashes, dtypes, shapes and
nonfinite tensors; changed initialization; malformed fit metadata; mutation of
sensor tensors; premature CPU stopping; later fit/control failures; and a
publication fsync failure. They verify no fallback, retry, overwritten evidence
or false phase-success marker. Synthetic Git repositories exercise dirty trees,
assume-unchanged hiding, sparse checkout and source/protocol/runner ordering.

The real fitting smoke uses only a hand-written three-action, single-episode
synthetic history, one optimizer update and the flat model. Other phase tests
use an explicitly fake fitter. These are not public-fixture comparison results.
No v2 learned score, empirical-control score, tuning, calibration or independent
challenge has been run.

Local regression: 257 retained historical tests plus 34 new tests passed (291).
The initial default-thread run timed out after 200 seconds without a reported
test failure; a separately recorded run with explicit single-thread settings
completed in 20.33 seconds. This was invariant-test execution, not a retry of
any frozen study. The full parent has 55 additional tests absent from the local
3493b3b archive; they are NOT claimed locally. CI checks the actual branch.
The four restored dependency modules match their frozen SHA-256 values.
Both new Python files' uploaded Git blob IDs match the locally tested bytes.

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m unittest experiments.predictive_nucleus.tests.test_comparison_execution -v
PYTHONHASHSEED=0 python -m experiments.predictive_nucleus.comparison_execution --preflight
```

## Required next tranche before execution

Implement the forecast/replay and audited log-probability scoring stage, then
integrate it with this fit phase. Save every forecast before its feedback;
retain raw/normalized log values and explicit structural-zero/underflow status;
check all per-step/query/abstention inventories, regression IDs, role pairs and
identifier views; implement the frozen latency procedure and success/failure
publication. Review the assembled runner and its test/workflow hashes before
adding the one-attempt execution gate. Ordinary CI must not start the study.

No production runtime, PR21, governance, historical experiment, learner or frozen
protocol changed. Independent challenge, partial/noisy sensors, stronger capacity
controls and learned acquisition remain outstanding. Language stays deferred.
This tranche adds 914 physical Python lines including tests. Adding these to
the prior complete-branch count yields 15,701 retained Python lines; this is
not a fresh enumeration of the full remote tree, nor satisfaction of the
practical 2,000-line goal. Historical failures were not deleted to reduce LOC.
