# G3 v1: post-publication TRAIN-only diagnosis

## Scope and evidence

Weights publication: `6742c7df5b00f966c99c2a93d885d91eb21034e6`.

This analysis used the saved training reports, accepted coordinate parent language weights, the five final grounded language checkpoints, the five accepted NAND world checkpoints, the original 16-example teaching tape and 1,152-event rehearsal tape, their registry, and their freeze metadata. No fresh challenge input, evaluator, parser-label tape, retention challenge, or scored decision was opened. No optimizer was instantiated or stepped. No weights, frozen source, protocol, criteria, or repository files were changed.

A separately authorized diagnostic reconstructed the initial and final states and evaluated three conditions per seed: v1 initialization, published v1 final weights, and a proposed normalization at unchanged initialization. This covers 15 TRAIN-only forecast/gradient conditions, each with 16 teaching forecasts and 1,152 rehearsal forecasts (17,520 forecast rows in total). World likelihoods were cached only for these two original TRAIN tapes. All ten v1 initial/final objectives reproduce their saved reports within 1e-12. Fingerprints verify that diagnostic language/world tensors remained unchanged.

Reproducible script: `/tmp/cemm_g3_v1_train_diagnostic.py`.
Detailed results and input hashes: `/tmp/cemm_g3_v1_train_diagnostic.json`.
Result SHA-256: `3285249fff3c438b038ae871f5142b50626a4f7bcc978b31d4d498f493f7426d`.

## Finding

The failure is concentrated on the new lexical identity **zef**, whose accepted parent representation strongly prefers an existing contact action before teaching. It is not an inability to learn either new word, an immutable-world defect, or floating-point underflow.

| Seed 7 TRAIN quantity | v1 initialization | Published final |
|---|---:|---:|
| lights endpoint NLL | 0.902450 | 0.023916 |
| zef endpoint NLL | 5.751843 | 5.752409 |
| zef total SET prior probability | 3.881199e-7 | 2.095047e-11 |
| zef posterior SET responsibility for its observed endpoint | 5.663238e-4 | 3.530119e-8 |
| zef-only new-head gradient norm | 0.00209697 | 6.842678e-7 |

The combined teaching NLL of 2.888162 averages successful lights acquisition with failed zef acquisition. The final rehearsal NLL is 0.003427. All four other grounded seeds learn both new words; their total teaching NLL is 0.054581–0.066514. The supervised parser for seed 7 reaches teaching NLL 0.136923, consistent with trainable capacity but a different credit-assignment path.

### Why zero new weights were not neutral

The four-action v1 head appends two raw zero logits to the two trained contact logits. For seed 7 zef, the larger inherited contact logit is 14.939322 in SVO and 16.578839 in OSV. A raw zero SET logit therefore starts with very little probability. lights has much smaller inherited logits and avoids this exclusion.

An accepted two-class softmax is invariant to a common shift of both old logits. Appending raw zeros makes that formerly irrelevant shift affect the new action probabilities. The extension therefore imports the old head's confidence and arbitrary logit gauge as an unintended prior against the new action family.

| Seed | Initial mean zef SET probability | Initial mean posterior SET responsibility |
|---|---:|---:|
| 7 | 3.881199e-7 | 0.000566 |
| 11 | 3.170883e-5 | 0.025365 |
| 23 | 5.983404e-5 | 0.042117 |
| 37 | 0.001394 | 0.362470 |
| 53 | 0.000980 | 0.321378 |

Seed 7 is an outlier before any G3 update. By the final checkpoint its dominant contact logits have grown to 82.125537 and 77.718575, while the appropriate SET logits are only 53.221351 and 53.816158. Those gaps explain the further probability collapse.

### Interaction with the native model's finite tails

On the teaching rows whose participants already have value 1, observing the unchanged all-1 endpoint is very likely under SET (about 0.998001) and unlikely under either contact action (0.000303207 or 0.000601944, depending on revealed mode). These are learned finite softmax tails, not a hard clipping floor in the implementation.

For action prior pi and native endpoint likelihood L, the latent-action responsibility is

`r[a] = pi[a] L[a] / sum_b pi[b] L[b]`.

The endpoint-loss derivative with respect to an action logit is `pi[a] - r[a]`. With SET prior mass already far below the contact tail, even a strongly diagnostic endpoint receives mostly contact responsibility. Its corrective gradient is consequently small. This is ordinary finite-probability competition, not numerical underflow. The supervised parser loss instead gives the labeled action a direct gradient and does not have this suppression mechanism.

Shared updates can learn lights while making zef more extreme in the contact region. The final weights and reports establish that this happened; they do not identify every intervening optimizer step because only final weights and periodic losses were saved.

## Smallest future prospective hypothesis

Keep all 88 inherited scalars and all four new scalars initialized exactly as in v1. Change only the future scoring normalization:

`p = softmax(concat(log_softmax(contact_logits) + log(2), new_SET_logits))`.

At the unchanged zero initialization of the new rows:

- The parent contact distribution is preserved conditional on choosing contact.
- Contact receives total probability 1/2.
- SET receives total probability 1/2, split equally between its two participant directions.
- No literal word selects an action or role.
- All four new scalars remain free to learn, so future SET family mass is not fixed at 1/2.

The current contact logits must be normalized as part of the forward computation. This is a persistent scoring/parameterization change, not merely a claim about initialization. Independently normalizing both blocks and fixing their family masses would prevent learning the effect family; that is not the proposed formula.

The zero-update TRAIN-only diagnostic confirms the formula removes the measured exclusion at initialization. For seed 7 zef, posterior SET responsibility becomes 0.832800 and the new-head gradient norm becomes 1.618906. Its teaching NLL is 0.766482. Across all seeds, total teaching NLL at this initialization is 0.746482–0.766342. No update or generalization test was performed.

There is a real tradeoff: the neutral initialization assigns exploratory mass to SET on old contact messages too. Seed 7 rehearsal NLL rises from 0.015416 to 0.396851 at initialization. Final rehearsal/retention gates must remain unchanged. The candidate is not entitled to acceptance because its initial teaching loss improves.

The normalized family gate still has representational capacity: learned lexical magnitudes can put old contacts in an interior interaction region and new SET expressions in exterior regions, with the signs selecting participant direction. This changes the optimization geometry; it does not prove that the 256-update run will find such a solution.

## Why not simply increase updates

More updates is a separate compute-budget hypothesis. The observed failure has not exhausted representational precision: it has reduced zef's posterior responsibility and gradient by several orders of magnitude while the other word learns. Extra updates may or may not escape that state. Increasing the budget would not directly remove the arbitrary-logit-scale dependence and would confound a normalization test.

After the complete v1 decision is saved, the smallest clean next experiment would freeze this one normalization change, retain the 92-scalar inventory, inherited initialization, original TRAIN tapes, five seeds, 256 updates, optimizer, .5/.5 tape weighting and all scientific criteria, and prospectively commit the new evaluation recipe before execution. v1 negative evidence must remain intact. This document proposes no change to the running v1 study and makes no claim of G3 completion or formal admission.

## Saved-curve-only budget assessment

A subsequent arithmetic review used only the saved v1 training curves; it added no model forecasts or updates. The four successful grounded seeds improve their teaching NLL by 46–51% between logged update 192 and the final checkpoint, including 13.6–15.7% between logged update 240 and final. Their rehearsal losses also continue decreasing. Parser teaching losses show similar ongoing progress. The text-only teaching losses improve by only 0.4–2.6% over the final interval. Grounded seed 7 improves by only 0.057% in that interval.

These observations justify considering a longer fixed budget as a separate future hypothesis for residual TRAIN loss. They do not identify 1,024 as a justified stopping point, establish held-out or retention success, or show that more steps repair seed 7's exclusion. Curve entries report pre-update losses, whereas the final objective is measured after update 256; the interval labels should not be interpreted as exact equal-length samples.

The prospective normalization candidate therefore retains 256 updates for every arm. If both normalization and compute were changed, any later pass would establish the combined intervention rather than a causal effect of normalization alone. Full curve arithmetic is retained in `/tmp/cemm_g3_v1_curve_arithmetic.json`.
