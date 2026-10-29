# Active nucleus: versioned repair and engineering continuation

Tracking: #22 / draft #56. Code commit: `bab17260075a82b59a9bb9f9cec7fc6b1e8ef0f4`.
Decision: KEEP the two demonstrated repairs and their streaming integration.
**G1 remains NOT ADMITTED. Engineering does not wait solely on issue #55.**

## Active versus frozen paths

`active_participant.py` is the opt-in repository-backed command for the repaired
filters in `active_paths.py`. It reuses the existing streaming session, receipt
checks, joint models, empirical tables, probability normalization and verified
bundle loader. Startup identifies `active-inference-v2` and source hashes;
feedback reports live-path counts or empirical recovery diagnostics. It is not
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
Use the unchanged JSONL start/predict/feedback/end message schema. A new receipt
is returned after each forecast and must accompany its own feedback. Unknown
readings stay null on the wire. All original constraints remain: three binary
entities, complete initial anchor, noiseless visible readings, no self-contact,
and the inherited transport action limit. This command is not a security sandbox.

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

## Verification completed

Both audit examples reproduced against unchanged frozen source. Twenty-five
new tests cover both fixes, causal ordering, malformed inputs, per-episode
budgets, unequal masks, history-specific recovery, real conflicts, underflow,
retained recurrent distinctions and end-to-end streaming behavior.

**Complete-branch CI run 40932601276 passed all 435 tests with no skips in
24.347 seconds**, all 16 historical manifest locks and frozen-input preflight.
This includes the checkout-dependent test unavailable in a source archive.
The later documentation/evidence commit's CI is a separate result to check.

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

`active_status.json` keeps the current boundaries machine-readable. Next reuse
the earlier `evidence_monitor.py`, `evidence_guard.py` and `context_support.py`
where valid behind the active prediction/observation interface. Their existence
alone does not mean they are already integrated or calibrated for this path.
Then cover the original 3–6-entity/self-contact domain and complete one coherent
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
occurs in this repair tranche.
