# G5 outcome-trained correction — prospective controlled comparison v2

**Parent:** retained rule-only G5 baseline in PR #86, commit `9afd0c4aeed258fd888a1386ce694eba3f707af8`. **Status:** frozen hypothesis before fitting or challenge scoring; no claim of scientific admission.

## Question

Can one shared, genuinely outcome-fitted parameter predict whether an independently observed contradiction is an exception or a lasting change, while respecting attributed scope and uncertainty? Compare directly with the zero-trainable-parameter dated-evidence rule. A tie favors the simpler rule. Do not modify any inherited G3/G4 checkpoint, frozen study, scorer, or production source.

## Data and information law

Use the frozen G4 `transfer_task.catalogue` **train** pairs to fit; use the disjoint `challenge` pairs only after publishing fitted values. Six distinct metadata-selected triples per law/seed, selected with the existing `revision_study.select_triples`, each spanning all three word orders with disjoint lineages and entities. Both NAND and NOR, seeds 7/11/23/37/53. Two opaque terms, `qor` and independent sentinel `nav`; disjoint nested root/region/unit scopes; selected physical action and realized binary payoff; candidate-conditional G3 forecasts; receipt ID, event time, source and verification status. The learner must never read evaluator interpretation labels, final actions, later payoffs, or `reversal` at prediction time. Same histories, actions, sensors, prices and information for all arms.

TRAIN contains balanced single-exception/permanent-revision twins, their distinguishing or nondistinguishing later observations, and root, sibling, local and unrelated-scope queries. Only **observed next-action payoff** is used for fitting log likelihood. Challenge is reused from previously opened physical families: not externally blind, not independent replication.

## One-parameter candidate and controls

Use a two-interpretation, scope-inherited sequential Bayesian filter. One global persistence/switch parameter `s` is selected without interpretation labels by minimizing selected-payoff TRAIN NLL, from this fixed ordered grid: `[0.0025, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32]` (tie: smallest). Each distinct verified physical receipt contributes the likelihood of its observed selected-action outcome under each hypothesis; simultaneous receipts form one evidence group with no arrival-order preference. A transition `p' = (1-s)p + s(1-p)` occurs once per distinct evidence timestamp and at scope entry, not for replays. Use one shared scalar across all scopes, identities and terms. Prior `p=0.5` at the root. Unverified assertions, reused evidence IDs and nondiscriminating observations cannot add information. A conflicting reuse of one evidence ID is rejected. Preserve evidence and the independent sentinel across resets.

A probability at most 0.05 commits meaning 0, at least 0.95 commits meaning 1; otherwise the candidate explicitly abstains. Perfect, supplied verification is purchased *only* for an abstention with a discriminating query costing 0.05, never for cost 0.75, uninformative or unavailable queries. Do not tune this rule on challenge. Controls: v1 scoped rule, most-specific/latest receipt, no-memory, fixed non-learned `s=0.5`, reversed payoff sign, removed or duplicated evidence, shuffled timestamps, and unverified false claims where applicable. Report the number of free parameters and storage separately.

## Immutable evaluation and decision rule

Report all planned challenge contexts (9,216 per condition; 7,680 identifiable, 1,536 indistinguishable), prequery accuracy, abstentions, resolved and unresolved confusion, sentinel/parent preservation, per-scope changes, question counts, net rewards at 0.05 and 0.75/unavailable, average payoff NLL and calibration, duplicate and order violations, and paired deltas versus **both** v1 scoped rule and strongest latest-receipt rule.

Require zero false confident assignments on indistinguishable twins, no incorrect resolved confident assignments, zero irrelevant/costly questions, stable deduplication/same-time behavior, and no parent/sentinel overwrite. Require actual useful generalization on held-out identities and lineages and *strict* improvement in at least one prespecified valid loss/utility metric with no deterioration in any safety/retention gate versus v1 to justify the extra parameter. Exact parity keeps v1 on simplicity grounds. If any gate fails, report `REVISE_OUTCOME_UPDATE`; do not edit frozen thresholds or repeat the opened challenge. If the controls reveal a shortcut, report `STOP_CONFOUNDED`. Formal G5 admission remains **NOT_ADMITTED** even if the bounded candidate wins.

## Sequence and resource limits

(1) Publish this protocol. (2) Publish source and synthetic tests, without challenge execution. (3) Fit TRAIN once, publish all ten learned values, scores and source/runtime identities. (4) Run and seal challenge outcomes once; score with code separate from training. (5) Publish adverse cases, process/CPU cost and code-size delta. No neural framework, learned meaning labels, additional vocabulary tables or changes to the main runtime. This comparison may fail; a negative result is still the retained result.
