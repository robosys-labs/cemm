# G3 v1: broader failure diagnosis from saved evidence

## Read scope and execution boundary

This is a post-outcome review of the completed v1 evidence, not a fresh validation. It read the ten saved v1 scored reports and decision; the five saved grounded language states produced by v1 TRAIN fitting; the v1 TRAIN lexical registry; and frozen model, coordinate, scorer and protocol source. The companion JSON records exact repository-relative source paths and SHA-256 hashes.

**This broader review performed zero model executions, zero new forward forecasts, zero gradient evaluations, zero optimizer steps, zero fits, and zero collections.** It did not open any challenge input or evaluator file, or any v2 candidate checkpoint or forecast. The earlier seed-7 TRAIN-only forward/gradient diagnostic is a separate exposure and must retain its own receipt; it is not reclassified as zero execution here.

## Complete result: all ten conditions require revision

The decision is `REVISE_EFFECT_ROLE_GROUNDING`, with G3 incomplete. The failure is broader than seed 7's previously diagnosed exclusion of zef.

- Seed 7 fails substantial fresh competence, probability, uncertainty, trajectory and goal checks under both laws. It passes the old-bank retention gates.
- Seeds 11, 23, 37 and 53 pass the fresh MAP/action/goal checks but fail both bilingual probability agreement and conditional probability quality under both laws.
- Seeds 23, 37 and 53 also fail the old-bank mean NLL criterion on the saturation, centering and coordinate banks under both laws.
- Seed 37 additionally changes exact action choices and regresses exact world predictions on those three banks.
- The saved exact lexical identity controls all pass. Identity storage is not the demonstrated failure.

The companion JSON preserves every false decision check, rather than only a selected explanation.

## Probability quality and layout transfer

| Seed | NAND maximum bilingual TV | NOR maximum bilingual TV | NAND mean KL | NOR mean KL | Learned absolute VOS/SVO response ratio |
|---|---:|---:|---:|---:|---:|
| 11 | 0.068815 | 0.068865 | 0.042071 | 0.045443 | 1.4161 |
| 23 | 0.066054 | 0.066117 | 0.035625 | 0.038485 | 1.4382 |
| 37 | 0.130794 | 0.131015 | 0.045401 | 0.049016 | 1.6577 |
| 53 | 0.077885 | 0.078006 | 0.037920 | 0.041177 | 1.4231 |

The TV limit is 0.05. Overall mean KL can be below 0.05 while the frozen criterion still fails: each required nonempty stratum must pass. That distinction is scientifically material and must not be replaced by an overall average.

For every seed in this table, the worst saved bilingual pair contains a new SET word at VOS and its physically equivalent counterpart at SVO or OSV. Both points have the correct action MAP. The disagreement is therefore in predictive probabilities, not a failure to choose the correct action label at those specific points. Challenge layouts rotate by event, so an episode pair's initial language/layout category does not imply every paired event has the same two layouts.

VOS also has the largest layout-level mean KL in all four successful-acquisition seeds. For example, seed 37 NAND has mean KL 0.031468 in SVO, 0.035716 in OSV and 0.069020 in VOS. Its worst new-SET cell reaches 0.132998 under NAND and 0.151192 under NOR.

**VOS is not the whole problem.** New SET cells at the taught SVO and OSV layouts also exceed the 0.05 KL criterion. The remaining teaching loss and the still-decreasing v1 learning curves support an additional finite-budget calibration hypothesis. The available evidence does not establish that more updates would clear every criterion.

## Retention: old words acquire unwanted SET mass

The failing retention banks have substantial probability on SET even though their accepted action predictions are contact. For the saturation/centering/coordinate bank family:

| Seed | Mean SET mass | Maximum SET mass | Mean retained NLL range across those banks and laws |
|---|---:|---:|---:|
| 11 | 0.027525 | 0.220733 | 0.023399–0.025482 |
| 23 | 0.083669 | 0.447377 | 0.067641–0.076382 |
| 37 | 0.105573 | 0.595720 | 0.092852–0.104660 |
| 53 | 0.078797 | 0.421827 | 0.063041–0.070916 |

Seed 11 retains the required mean NLL below 0.05. The other three do not.

Seed 37 has exactly **128 changed action MAPs in each of the three failing banks under each law**, and every changed action is menu index 3, SET of the second mentioned participant. These are effect substitutions, not contact participant reversals. Exact-world regressions range from 83 to 94 per bank/law, depending on the bank and native law. The repeated views share their language model and are not independent trials.

Saved retention reports do not attach the lexical/layout fields needed to attribute every changed action to a particular old word. This review did not open old bank inputs to add those labels. The observed effect substitution is established; its exact word-by-layout distribution is not claimed here.

## Mechanism: effect and role share one scalar interaction

The source computes a learned lexical scalar c and a learned layout response q, then uses z=c*q in every four-action logit. Consequently the same interaction determines both:

1. which effect family receives probability; and
2. which participant direction receives probability within that family.

This dependence is established by source structure. There is no separate lexical effect gate. Layout magnitude can therefore change effect confidence, even when its sign still selects the correct direction.

The learned VOS magnitudes are 42–66% larger than SVO for the four seeds in the table; OSV magnitudes are closer to SVO. In v1's learned head geometry, stronger interaction magnitude can move an expression toward an outer contact region and away from the SET region. The largest saved layout ratio occurs for seed 37, which also has the largest bilingual TV and the strongest retention effect leakage.

This pattern strongly supports a layout/effect coupling hypothesis. **It does not isolate that coupling as the sole cause.** Word-specific lexical values, head biases, finite training, and accumulated mode-posterior differences also affect probabilities. The layout values are freely learned; they are not hard-coded gold role signs or a hard-coded magnitude rule. Hard sign replacement, clipping, or forced unit magnitudes would introduce a new modeling assumption rather than simply repair a numerical defect.

## What the isolated v2 normalization can and cannot establish

The v2 candidate remains unchanged: 92 parameters, all 88 inherited scalar values copied, four new zeros, 256 updates, identical objectives and optimizer, frozen native worlds, and unchanged criteria.

Its scoring rule removes the arbitrary inherited contact-logit gauge and gives the new effect family useful initial mass. That directly addresses the established seed-7 exclusion mechanism and may improve the optimization trajectory more broadly.

However, its SET family probability is still

`P(SET) = S(z)/(2+S(z)), S(z)=exp(w2*z+b2)+exp(w3*z+b3), z=c*q`.

Thus layout magnitude still affects effect selection. This normalization favors a different geometry: the low-SET region of z is an interval, with SET probability increasing outside it. That may improve new-word VOS confidence, while also making old-word retention depend on sufficient learned lexical margins. It does not structurally guarantee bilingual agreement or retention.

A v2 pass would be evidence for the complete fixed normalization intervention under the frozen budget and checks. A failure would remain evidence, including any improvements and remaining defects. Neither an initial gradient improvement nor success on seed 7 alone can close G3.

## One defensible next mechanism, only if complete v2 evidence warrants it

If layout-dependent effect leakage remains, the smallest targeted architectural hypothesis is to separate a lexical-only effect gate from conditional participant roles, while retaining 92 scalar parameters:

- Keep the 88 inherited scalars and their conditional contact predictor.
- Use two new scalars for `g = sigmoid(a*c*c+b)`, a lexical-only SET-family gate.
- Use two new scalars for SET participant direction, `h=d*c*q+e`, with probabilities `softmax([h,-h])`.
- Form the four-action joint distribution as `(1-g)*P(contact roles)` and `g*P(SET roles)`.

The squared lexical feature is a generic sign-invariant magnitude feature: reversing a role sign need not change the effect family. Its coefficient and bias remain learned. It is not a literal-word rule or a supplied effect label. At four new zero scalars, the effect families remain 1/2 each and the SET directions 1/4 each.

This factorization would remove layout magnitude from the effect-family probability while allowing layout to determine role. It is a new, explicit inductive-bias hypothesis, not a proven fix, and the bounded setting does not establish general polysemy handling. Shared lexical training and conditional role confidence can still cause retention or probability errors, so all existing gates remain necessary.

No such next mechanism has been implemented or tested. If v2 instead leaves only smooth residual probability error with layout and retention gates intact, a separately frozen longer compute budget is a smaller hypothesis than another architectural change. Neither contingency changes the currently isolated v2 experiment.
