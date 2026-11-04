# G5 v6 failure attribution — read-only post-score audit

**Parent:** PR #91 at `61e1a979b79e2174ea634b5849f2db89dbb4501f`.
**Status:** diagnostic protocol frozen **after TEST scoring**. Not an independent
challenge, admission study, optimizer, or a revised v6 acceptance rule.

## Question

Why did the outcome-trained v6 filter improve mean belief Brier and goal
utility while asking 88 questions instead of the zero-parameter rule's
73, and why did NAND seeds 37 and 53 lose utility? Is the discrepancy due
to source reliability, actual epoch flips, belief calibration, or genuinely
useful extra verification? The archived ten-condition TEST evidence is
**open**. Conclusions are descriptive/causal diagnostics, not fresh
generalization estimates.

## Immutable inputs

- Original v6 source/protocol `972ca4fbc6f9e0376b1a1253e5ac2ddd08aad89b`.
- Global TRAIN fit `8fa94db75e610a1dec451a9049bb88c36405a53e`:
  `h=.15, e=.1`; **do not refit**.
- Sealed TEST probabilities `3f0d247d88c51132ff63e1fde34dfca1b45747ab`.
- Scorer and ten stored TEST results at `61e1a979b79e2174ea634b5849f2db89dbb4501f`.
- Evaluator-only truth from the *unchanged* `independent_task_v6.inventory`,
  joined to the same records by world identity and evidence digest.

## Frozen posthoc partitions

Across exactly 10 conditions × 192 worlds:

1. Partition paid questions into **both policies**, **temporal-only**,
   **rule-only**, or **neither**, with the same goal/fee. Confirm
   counts 73/15/0/1832 from raw probability-only audit.
2. For temporal-only questions, report exact realized incremental
   *two-action gross reward* and *net reward after the .05 fee* versus
   following the same temporal policy **without buying** an answer.
   Count beneficial, neutral and adverse realized queries; do not call
   posthoc observed benefit an unbiased estimate of expected VOI.
3. Attribute actual net utility differences between temporal and the
   scoped rule by law/seed, source at the epoch observation, presence
   of a *true* local meaning flip, and goal/fee. Reconstruct both
   original policies and require per-condition sums to match the
   immutable saved scorer to tolerance 1e-9.
4. Audit **mid-local and final-local** meaning Brier separately by
   flip/no-flip and epoch source A/B; also report parent/sentinel
   wrong-confident cases and their baseline controls.
5. Report the model's single global exception rate `e=.10` against
   declared TEST observation errors A=.03, B=.24, and whether the
   existing filter actually reads source IDs. Treat this as a
   model-specification limitation, **not** proof a new learned scalar
   would win a fresh test.
6. Preserve the existing confidence, utility and question limits,
   reused opened G3 world-family warning, and all negative seeds.

## Decision boundary

If extra questions increase realized reward, report them as
potentially rational uncertainty under a rule that under-questions;
otherwise identify wasted clarification. Retain **failure of the
pre-registered no-more-questions and no-worse-seed gates in all cases**.
Do not relabel v6 as KEEP, change the frozen v6 challenge, invent
independent replications, tune a model on this opened TEST,
or alter production authority, G1–G4 evidence or G6–G8 gate.

Publish the single diagnostic result, reproducible source and
case-level adverse identifiers with short trace excerpts. Any
architectural recommendation must propose a **new prospectively
registered TRAIN/challenge comparison**, prioritizing minimum capacity
and proper posterior + goal utility over training loss alone.
