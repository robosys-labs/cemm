# Frozen-checkpoint transfer: implementation, before outcomes

Tracks #22 / draft #53, stacked on #52. The previous public diagnostic is closed.
Protocol commit: `a6f3cc1ae1561819b41eedcd06eef5148f3d4896`.
No learner, training objective, checkpoint, historical source or protocol was changed.

The next capability is a common finite-path filter for missing sensor values.
Both model families propagate their own learned conditional distributions and
condition on actual visible readings. Branch states are hypotheses, not observed
facts. This filter is supplied; it does not demonstrate learned acquisition or
native partial-observation training. No hidden truth or mode enters the filter.
Full-sensor synthetic replay matches the existing execution path for all six arms.
Exact-zero paths are not fed to undefined posterior updates; there is no sampling,
pruning, smoothing or truncation. A 64-path cap rejects excess instead of hiding it.

The same hypothesis calculation wraps the unchanged empirical tables. Any positive
unsupported branch causes abstention instead of conditioning on only known paths.
The predeclared first-contact abstraction uses the existing table without refitting.
No-change remains a visibly separate last-measured-bit persistence baseline.

The separately implemented evaluator uses two reordered/reversed eight-action
families, 256 cases and six related identifier views. Full readings, hidden reset
readings, and a hidden probe are tested. Only the last condition removes decisive
mode information: its ideal query MAP ceiling is 62.5%, versus 100% with the
available informative history in the other conditions. Those are evaluator bounds,
not model scores. Changing masks never changes actual actions or physical outcomes.
The oracle is evaluator-only and uses no private-mode input when forming forecasts.

This is SAME-AUTHOR evaluation with a separate simulator implementation, not
independent authorship or custody. G1 admission remains unproved. Source and data
are public; no later retuning on these outcomes is allowed. We are not running the
old closed study again or extending language. Existing checkpoints fix all 30
informative/fixed-exposure models (six variants, five seeds), including original
capacity/exposure/CPU records. These budgets are not matched architectural capacity.

Local source was obtained from a hash-verified GitHub source-export artifact for
the protocol commit, not a complete local Git checkout. The checkpoint archive ZIP
and original report hashes were verified. The implementation manifest pins all new
source/tests and reused model/scoring code. Historical source locks remain intact.

Before scientific evaluation: 16 new tests pass. The full local suite discovers
379 tests: 378 pass and one real-checkout preflight is explicitly skipped because
this is an archive. Complete-branch CI must execute that test. New tests cover full
sensor equivalence, correlated uncertainty, missing-value validation, feedback
ordering, unsupported empirical mass, the path cap, both evaluators against old
physics, orientation twins, and exact oracle identifier equivariance. No saved
model has been evaluated on the new fixture during implementation testing.

The implementation and tests add 655 physical Python lines at this stage; direct
enumeration of the retained namespace gives 17,270. Historical failed work is not
deleted to make a smaller count. Reuse of old scoring/restoration is deliberate.

Next: verify exact uploaded implementation bytes and complete-branch CI; then run
one guarded evaluation and retain complete or failed output. The result must remain
bounded transfer evidence, never an independent G1 pass. No further prep or model
tuning is planned for this fixture after the retained result.
