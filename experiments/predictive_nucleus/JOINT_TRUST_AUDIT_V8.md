# G5 v8 decision and post-score audit

On November 4 the frozen scorer recorded `REVISE_JOINT_V8`. Six of 13 quantitative gates passed. The November 6 audit verified the sealed Git blobs for all ten raw banks, ten scored reports and the decision. It uses the existing 1,920 worlds in 960 matched pairs. The v1 scoped rule remains the bounded G5 baseline. G5 scientific admission is open.

| Frozen measure | Joint v8 | Fitted neutral |
|---|---:|---:|
| Five-view meaning Brier | 0.06048 | 0.06283 |
| First local Brier on a genuine change | 0.23777 | 0.22000 |
| Net utility per action | 0.82996 | 0.84768 |
| Optimal actions | 91.85% | 94.43% |
| Paid clarifications | 156 | 148 |
| Wrong predictions at ≥95% confidence | 185 | 176 |

Both arms received identical evidence, goals and fees at each fixed-time meaning and decision checkpoint. The neutral control earned more on every seed. V8 did improve first-local Brier and utility against the fixed *source-aware v7* on the reversed and within-episode source-switch conditions.

## Where the utility went

Across 3,840 actions the joint model lost 68.05 net reward relative to neutral. The difference was 67.65 in gross reward and 0.40 in extra fees. Reducing question count alone cannot recover this loss.

| True meaning after the epoch | First source | Worlds | Joint minus neutral net reward | Joint / neutral first-local Brier |
|---|---|---:|---:|---:|
| Changed | A | 499 | −30.75 | .19152 / .19604 |
| Changed | B | 461 | −57.00 | .28783 / .24594 |
| Stable | A | 499 | +3.05 | .05529 / .05700 |
| Stable | B | 461 | +16.65 | .06282 / .07969 |

V8 gained 19.70 when meaning stayed stable and lost 87.75 on genuine changes. Its mean Brier advantage came mainly from the sibling, root and sentinel views. On the first local action its mean Brier was .00439 worse. These are within-world arm differences partitioned by evaluator truth. Only 21 of 960 twin pairs shared both goal menus and the fee, so a direct comparison of utility between twins would confound the effect of changing meaning.

## What the matched twins establish

Both twins produced the same pre-epoch forecast in every pair. Under the fixed transition hazard, a local probability `p` becomes `.15 + .70p`. Every possible prediction therefore passes the .95 abstention cutoff. In this balanced bank, each identical prefix precedes one positive and one negative outcome. The pair's average Brier equals `.25 + (p_post − .5)²`. The observed prefix Brier was **.35638**, against **.25000** for equal probabilities. In 801 of 960 pairs v8 assigned one alternative over 80%. The .50 reference describes the constructed twin population.

The joint model couples scopes through the shared trust state. The twins received the same prior root, sentinel and local records, with no new root or sentinel observations. After different local evidence, each protected view's joint probability differed across 949 pairs (tolerance 1e−12). Forty-four root pairs and 41 sentinel pairs changed confidence band (≤.05, interior, ≥.95). The neutral control had zero changes. The frozen scorer separately found 21 newly confident wrong root/sentinel predictions versus neutral. The twins establish sensitivity to local evidence. The aggregate files cannot assign each of those 21 errors to that mechanism, or separate the effects of local truth and local noise.

## Payoff scorer erratum

The task delivers `qor` then `nav` at each of the first three timestamps. The joint model sorts tied timestamps by evidence ID and emits `nav` then `qor`. Both controls use delivery order. The scorer joins the joint probability array to delivered receipts by position. **11,520 of 28,800** joint forecasts are attached to the other receipt and 5,596 are also attributed to the other sensor. This invalidates the published joint payoff Brier/NLL comparison, including its source breakdown.

A synthetic two-receipt witness shows why swapping saved columns is insufficient. Changing the second delivered outcome changes the joint forecast that a reindex would assign to the first receipt. The arms would still have different observation histories. The protocol's matched-history prerequisite fails for this endpoint. The thirteen reported gates use a separate path that reads fixed-time meaning forecasts, choices, costs and twin prefixes. The scored negative decision stands.

## Roadmap consequence

The generator supplies the scope slots, the source labels and a public change opportunity. The evidence supports a bounded diagnosis of source/meaning confusion. Discovery of those roles remains an open gate. For the next G5 transfer study, record the evidence ID and delivered-prefix digest with every arm's forecast, use informative as well as indistinguishable histories, and keep twin goals and fees matched when estimating causal utility. Measure whether an answered physical observation reduces paid clarification after an episode reset at matched correctness on fresh identities. Include the retained rule, a matched learner with its retained state cleared, and a matched unstructured learner on the same realized histories. Preserve the existing retention and worst-seed gates.

Reproduce locally with `python -m experiments.predictive_nucleus.audit_joint_v8` and `python -m unittest experiments.predictive_nucleus.tests.test_v8_postscore_order`. The audit imports neither the challenge generator nor the candidate. The [study](JOINT_TRUST_STUDY_V8.md), [raw manifest](results/independent-v8/raw/manifest.json), [frozen decision](results/independent-v8/scored/decision.json) and [scored manifest](results/independent-v8/scored/manifest.json) remain the historical record.
