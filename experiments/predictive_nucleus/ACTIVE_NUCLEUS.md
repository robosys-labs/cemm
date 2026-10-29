# Active nucleus: evidence diagnostics and engineering continuation

Tracking: #22 / draft #57; built on draft #56 at `0b6744d78d920b2ef3ad90e047bf5f09ff984d31`.
Published code: `44193776aabd3f10186d5ebcba1fe6df4aaafc61`. Its tree exactly matches locally verified
`be65e4424ac34f4db67fc8895a2dea86f9de77c8` (Git metadata differs).
Decision: KEEP the repaired filters and the verified advisory evidence integration.
**G1 remains NOT ADMITTED. Engineering does not wait solely on issue #55.**

## Active versus frozen paths

`active_participant.py` is the opt-in repository-backed command for the repaired
filters in `active_paths.py`. It reuses the existing streaming session, receipt
checks, joint models, empirical tables, probability normalization and verified
bundle loader. Startup identifies `active-inference-v3` and source hashes;
feedback reports inference diagnostics and the `active-evidence-v1` assessment.
The new evidence layer observes the existing forecast and feedback sequence; it
does not alter forecasts, model weights, table counts or action selection. It is not
the standalone v1 artifact or a claim of a complete active training/evaluation
stack. The narrower v1 export and all old sources/reports remain unchanged.

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m experiments.predictive_nucleus.active_participant \
  --bundle /absolute/path/participant \
  --manifest-sha256 2373c2d366c4f8a855dbb7498e5d6a88bc55b9078a00400eb51db86ca115a1a8 \
  --participant kernel_supplied_persistence --seed 7
```

The bundle is the verified existing v1 handoff, not newly trained weights.
The existing JSONL start/predict/feedback/end requests remain accepted. Active
v3 additionally accepts optional `sensor_ids` on `predict`, a nonempty list of
distinct episode IDs selected before feedback (default: all IDs). Feedback
still names every episode ID; readings outside selected coverage must be null.
A new receipt is returned after each forecast and must accompany its own feedback. Unknown
readings stay null on the wire. All original constraints remain: three binary
entities, complete initial anchor, noiseless visible readings, no self-contact,
and the inherited transport action limit. This command is not a security sandbox.

## Integrated evidence contract

The forecast receipt now binds its action, normalized joint log distribution,
canonical sensor coverage, observed-context assessment, diagnostic thresholds,
and active implementation identity. Internal copies prevent caller mutation of
the response or original request from changing the committed evidence. The
transport rejects a wrong episode, step, receipt, duplicate feedback, unexpected
field, invalid reading or outside-coverage observation before any evidence update.

`active_evidence.py` reuses `ObservedContextSupport` for completed observed
contact contexts. It implements the historical adequacy monitor's uniform
reference calculation directly in log space and latches the episode alarm.
It does not manufacture the older monitor/guard's two-hypothesis belief API or
claim its alternate change-point process or posterior-support analysis is active.

| Feedback assessment | Meaning |
|---|---|
| `NO_EVIDENCE` | All selected readings are missing; no likelihood evidence is added. |
| `UNSUPPORTED_PREDICTION` | Actual readings arrived, but the empirical participant abstained; model likelihood and log-e increment are absent. |
| `OBSERVATION_COMPATIBLE` | The observed joint event is compatible and does not meet either diagnostic threshold. |
| `SURPRISING_BUT_UNCONFIRMED` | Joint likelihood is below the explicitly declared heuristic 0.03 threshold, without a current log-e crossing. |
| `MODEL_MISMATCH_EVIDENCE` | The conditional log-e statistic meets the declared threshold; it does not identify the cause. |

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

## Current integration verification

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

`active_status.json` keeps the current boundaries machine-readable. Direct
observed-context support and joint-log adequacy diagnostics are now integrated;
posterior-context support, alternate change-point evidence, calibrated confidence
and learned probe selection remain unestablished. Next cover the original
3–6-entity/self-contact domain and complete one coherent
train/predict/observe/checkpoint/evaluate path with the strong controls retained.
Version the information-aware automatic acceptance specification BEFORE new
scores; never relabel historical final-query results as whole-trajectory G1.

Continue the concrete G2 composition workload (longer interactions, chains,
forks, cycles, disjoint interactions, repeated actions and coherent uncertain
worlds), then grounded bilingual language and G3–G8 in dependency order. Reuse
existing experiment infrastructure rather than adding a general-purpose harness.
Do not add learned communication or lifelong learning as new G1 prerequisites.

Issue #55 remains pending for independent scientific validation; it does not
replace or block these implementation requirements. Automatic correctness and
regression tests remain required. No scientific gate is weakened or admitted by
this status update, and no production/PR21 cutover or language implementation
occurs in this diagnostics tranche.
