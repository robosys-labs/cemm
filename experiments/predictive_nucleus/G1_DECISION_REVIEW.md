# G1 decision review: stop preparation-only iterations

Tracking #22; follow-up to #51. 2026-10-29.

## Diagnosis

The work has produced real corrections, but the process has drifted into a
preparation loop. More passing tests, protocol hashes and draft PRs have not
established the roadmap's learned-world generalization claim. By #51 there were
348 invariant tests and about 15,736 retained Python lines, but the corrected
common-objective comparison had not run. This is not evidence that the nucleus
hypothesis has failed; it is evidence that the workflow is not producing the
scientific decision efficiently enough.

Useful findings to retain: uncertainty and prediction failure must be separated;
missing targets/persistence and ID treatment confounded the original comparison;
the opened replay's stronger flat arm materially narrowed the gap; the first
second-pair fixture exposed the probe answer in current state; query and pooled
all-step accuracy are not interchangeable. These findings justified repairs.
They do NOT justify endlessly expanding the simulator, audit system or gate.

## Concrete change now

Finish and execute the existing frozen 120-fit public comparison. Do not create
another curriculum, change any learner, tune after seeing results, or call this
opened diagnostic an independent G1 test. Reuse #51's fit/checkpoint phase.
`comparison_run.py` adds the missing replay/scoring/publication path;
`comparison_scoring.py` supplies vectorized, directly testable arithmetic.

Every forecast block is flushed before its feedback. Raw and normalized log
probabilities remain separate, structural zeros differ from exponentiation
underflow, abstentions have no numeric proper score, and paired regression IDs
survive. Full controls, role pairs, ID permutations, per-step ambiguity scores,
latencies and all initial/final checkpoints remain required by the frozen
protocol. No scope reduction or replacement of the existing experiment occurs.

Ordinary CI now runs the complete invariant suite, every manifest lock and the
frozen preflight, with explicit single-thread settings and pinned NumPy 2.3.5.
It no longer refits and rescores the old public studies on every commit. Their
source, manifests, results and prior workflow remain in Git history unchanged;
they are reproducibility evidence, not fresh scientific progress. Research
execution gets a separate, reviewed, one-attempt workflow.

## Decision rules, not another indefinite HOLD loop

1. First read the informative second-pair query and its per-seed proper scores.
   Compare persistent versus reset memory and the flat/empirical controls at the
   declared exposure/CPU budgets. Report all seeds, failures and regressions.
2. If retained evidence is not usefully exploited even here, identify the first
   failing learned representation or optimization component. Change ONE cause
   with an ablation; do not add language, extra physics or another audit layer.
3. If a supplied empirical abstraction or the plain baseline explains the
   result, reject architectural-superiority claims. A correct small baseline is
   preferable to a larger bespoke model justified only by labels.
4. If the informative task succeeds, STOP optimizing this public fixture. The
   next experiment is one frozen, separately authored trajectory-family
   challenge with identifiable and ambiguous strata, shared histories and
   explicit compute/capacity comparisons. G1 admission still requires its actual
   evidence; this public run cannot supply it.

The independent-custody requirement must be a concrete review/execution task,
not a claim made about an assistant's own test authoring. Similarly, partial/noisy
sensors and learned acquisition must not be smuggled into the current completed
scope or deferred with a claim that they already work. The roadmap remains
world learning first, then composition/language; production/PR21 are untouched.

## Validation boundary

Local validation uses the retained source archive: arithmetic, serialization,
renaming, failure and causal-order tests run without new-parent modules. The
complete-branch CI additionally runs the synthetic all-six-model pipeline and
failure-publication test. No substantive public fits occur in invariant CI.
Report exact final CI and study results in the PR, not presumed successes here.
