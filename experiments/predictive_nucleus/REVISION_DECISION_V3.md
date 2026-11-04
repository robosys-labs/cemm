# G5 v3 — balanced selected-payoff TRAIN diagnosis (2026-11-04)

**Decision: retain objective correction as a useful diagnostic, but REVISE the bounded one-scalar G5 candidate. DO NOT PROMOTE.** Seven NAND/NOR × seed conditions passed the immutable joint TRAIN gate; three NOR conditions failed. The original G5 v1 zero-parameter scoped rule remains the selected development baseline. No G5 formal scientific admission, new independent challenge, production runtime or ancestor result is changed.

## Freeze and execution

- Protocol frozen in `10e049c683b7810561db80cb18421ba1ce3edd1c` before source, fitting and scoring.
- Corrected public evidence IDs were made independent of hidden bit values; the original pre-correction run was **invalid for no-leakage evidence** and is not scored.
- A separate test harness wrongly expected two catalogue reads instead of ten law/seed reads; its failed CI is retained. Fix changed no training data, posterior, objective, parameter grid or gate.
- The valid source/test checkout was `80c556581fa53bb80fed3d687115d7c1a4a5a28d`. [Final 1,210-test hosted run](https://github.com/robosys-labs/cemm/actions/runs/41810117256) and its source snapshot passed. This is software confirmation and a reproducible **TRAIN-only** diagnostic, not a blind challenge.
- The original and all fitted grid values, losses and audit counts are stored in [the complete result](results/revision-v3/train-diagnosis.json). The inherited challenge bank was **not** opened for G5 v3.

## Audited results

| Metric, all ten dependent conditions | Published v2 fitted switch | v3 balanced NLL-selected switch |
|---|---:|---:|
| Confident despite identical pre-payoff twin evidence | **864/960 pairs** | **54/960 pairs** |
| Correct and confident after discriminating payoff | Not the selection criterion | **1,916/1,920** |
| Wrong and confident after payoff | — | **0** |
| Post-payoff abstentions | — | **4** |
| Correct/confident parent, sibling and sentinel retention | — | **5,760/5,760** |
| Mean of per-condition balanced NLLs | **0.8671181484** | **0.2975212009** |

All ten new TRAIN fits select **s=0.0025**, the **lowest frozen grid point**. Seven conditions pass every frozen joint gate and have zero premature confident pairs. Three fail: NOR seed 37 (**20** premature pairs), NOR seed 53 (**16** premature pairs plus four post-probe abstentions), and NOR seed 7 (**18** premature pairs). No one of the eight preregistered grid values jointly satisfies pre, post and retention in those three conditions.

The unchanged v1 zero-parameter rule still abstains on **960/960** pre-payoff pairs and correctly commits on **1,920/1,920** post-payoff and **5,760/5,760** retention cases. It does not supply a comparable calibrated probability, so assigning it an NLL would be fabricated. TRAIN rows reuse six physical triples and shared synthetic structures per condition, and the ten seed/law conditions are not independent physical replications.

## Interpretation and next action

Properly weighting indistinguishable pre-payoff outcomes addresses **most** of v2's overconfidence without adding capacity: 93.75% fewer unwarranted commitments and 65.69% lower *balanced TRAIN loss*, with unchanged retained world checkpoints. That narrows the root cause to objective weighting **plus** an unresolved one-parameter **grid-boundary** limitation. It does **not** prove a continuous one-dimensional model is inherently insufficient; the selected rate lies at the minimum allowed value, so lower rates were not tested. Do not introduce a new latent mode based only on this result.

**Next highest-information step:** preregister a *small* additional TRAIN-only parameter-boundary/feasibility study using the exact same histories, v2 updater and decision gate, but explicitly search below 0.0025 and report the pre/post/retention trade-off. Include a separate no-information receipt invariance check: in the current filter, each evidence timestamp can apply a switch transition even when the likelihood ratio is 1, which may drift a belief without semantic evidence. Diagnose this separately as a possible temporal-state modeling defect, without quietly patching the v3 source or retrying a sealed challenge.

If a feasible one-scalar interval exists, do not add representation; freeze new independent held-out evaluation. If none is found over a justified interval, compare one minimal exception-vs-persistent latent state with an equal-budget simpler control. Any tie favors the rule. G6–G8 remain gated, and the inclusive 2,000-line research target remains unmet.
