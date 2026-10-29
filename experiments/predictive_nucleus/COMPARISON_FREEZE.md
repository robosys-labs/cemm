# Corrected common-objective comparison: frozen, not executed

Tracking: #22 / draft #50. Source: `3bbce83121386501ae39567b48fc9aa62325de79`.
Decision: **G1 HOLD / REVISE**. See COMPARISON_AUDIT.md for the two design
errors found and the new fixture/control implementation. No historical source,
protocol, outcome or production authority was changed.

The complete-branch code CI run [40827462302](https://github.com/robosys-labs/cemm/actions/runs/40827462302)
passed **307 tests**, all 13 historical manifest locks and inherited diagnostics.
The six parent archive-audit tests absent from the local reconstruction were
included in this CI count. The local suite with five additional protocol tests
passes **306 tests**; complete-branch validation of this second commit is
reported separately in the PR checks, not assumed from that local result.

## Fixed comparison

`common_objective_comparison_protocol_v1.json` fixes five seeds (7, 11, 23, 37,
53), all six model variants, both information conditions and two separately
reported regimes: 128 full-batch updates with a 60-second process-CPU safety
ceiling, or a 2-second process-CPU budget with a 100,000-update safety ceiling.
This gives 120 neural fits. The first regime must complete all 128 updates;
an early CPU stop is incomplete. Actual updates, CPU, wall time and last-step
overshoot must be reported. Neither equal exposure nor equal ceilings proves
equal consumed compute. No architecture/capacity superiority claim is allowed.

Every update contains the same 12,288 full-world targets within its information
condition. Training uses only the same-pair fixture. Same-pair scores are
resubstitution; second-pair evaluation contains novel chronological prefixes but
familiar local contexts. Controls are no-change and three empirical memories.
The primary query at step 6 is reported separately from all eight per-step
scores, proper scores on ambiguous cases, role reversals and ID renamings.
Correct-to-wrong changes and abstentions cannot be hidden by aggregate gains.

All 120 initial/final checkpoints and full forecast records must be retained.
Uniform audited log-domain normalization is specified BEFORE substantive fits
or scores; no post-hoc probability clipping is allowed. A numerical zero from
exponentiation is distinguished from a genuine negative-infinite log value.
A partial run must remain incomplete, with its failure and available artifacts
retained rather than silently rerun or selectively reported.

Protocol SHA-256:
`15732afe065f19f3b412a7638e386373eb586ddaa273104e2de63c14a782b1f3`.
Five new tests lock source hashes, all four realized datasets, paired query
truth, model/fit inventory and the NOT_RUN / HOLD status.

## Retained fixture audit

`results/comparison-fixture-audit-v2.json.xz` contains the deterministic,
recomputed bounds and preforecast-key coverage, NOT model-performance scores.
Compressed SHA-256:
`df43e2171bc5f0b93c2549a003ff8c4bd3b0ca742afdfaa915dfff23a630b764`.
Decompressed JSON SHA-256:
`96a87b8b09fb87b8d0099d83a1cc52ab07878e22ed07dc8ed408a71eaf973b43`.
The audit was generated twice with identical bytes. Its sensor tensor hashes
are pinned in the protocol. Missing evidence, changed experimental questions,
and a stronger baseline remain limitations to report, not reasons to move G1.

## Execution boundary

The protocol is committed before any substantive comparison. Its runner is
NOT implemented or reviewed in this tranche; a separate runner commit and
implementation review are required before one guarded execution. No new v2
model/control comparison, independent challenge or calibrated performance is
claimed. The already opened public fixture cannot become a sealed G1 test.
Independent held challenges, partial/noisy observations, stronger capacity and
budget controls, and learned acquisition remain outstanding. Language waits.

The five protocol tests add 62 Python lines. The full retained namespace now
contains **14,787 physical Python lines** including tests, using the prior
complete-branch count plus these additions. The 1,331-line common path and
follow-up are only a subset, excluding retained historical code/dependencies;
they must not be presented as satisfying the practical 2,000-line total target.
