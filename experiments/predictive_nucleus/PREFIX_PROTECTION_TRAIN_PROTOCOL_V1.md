# One TRAIN-only prefix-protection feasibility comparison

Freeze and publish this contract before implementation. Publish implementation
and its synthetic checks before fitting. Fit each arm/seed once, publish all
checkpoints before evaluation, then publish raw forecasts before comparison.
This is a development diagnosis on already observed TRAIN data. It neither
opens a new TEST bank nor changes any G5 admission gate.

## Single hypothesis and change

The completed [receipt trace](TEMPORAL_TRAIN_TRACE_RESULT_V1.md) shows protected
predictions deteriorating after the claim and first physical answer, while the
target benefits from those observations. Test whether allocating the existing
protected loss across these prefixes improves preservation without degrading
final target prediction. Do not add a write mask, new state, new hypothesis,
source rule, operation label or extra endpoint observation.

Use `temporal_native_models_v1.Model` unchanged: native 1,108 and flat 1,144
parameters, eight recurrent coordinates, float64 CPU and one torch thread.
Use exactly the published `data/temporal-train-trace-v1/input.json.xz`, SHA-256
`660bb412f2d165295c30d2248daa2ae7a334c56d4fa95fe324f80aa356b7063f`.
Its 2,048 original TRAIN histories and native projections are the only data.
Never open shared public, TEST-answer, oracle or held-out raw artifacts.

## Matched fitting budget

For seeds 7, 11, 23, 37 and 53 fit both native and flat from their original
initialization. Adam lr=.01 and all other defaults, 256 updates, batch size 128,
no clipping, stopping, search or calibration. Use the original Random sampler
seed `20261108200 + model_seed`. Verify initialization and minibatch digests
against the published original fit receipts. Do not refit original baselines.

Preserve the first five loss forecasts: first answer before receipt, second
answer after the first, and target before either answer / after first / after
both. Replace only the sixth, protected-after-both forecast with one protected
forecast whose recurrent state is selected per sampled history:

`horizon = (zero_based_update * 128 + zero_based_batch_position) % 3`

Horizons 0, 1 and 2 mean after claim, after first answer and after both answers.
The deterministic allocation is independent of the minibatch sampler and is
identical in both arms: 10,923 / 10,923 / 10,922 protected terms across 32,768
sampled histories. Record its digest. All three states already exist in the
original computation. Each sample still supplies six equally weighted uncapped
NLL terms, totaling 196,608 terms per fit; the protected loss keeps weight 1/6.
The single observed protected endpoint is reused at different forecast horizons.
This trades final-only protection for distributed protection, without increasing
the term or update budget. Record actual CPU/wall time and RSS separately.

## Validation and saved forecasts

Before fitting, verify the new loop with its protected horizon fixed to final
on a synthetic fixture against the unchanged original loop: exact initial and
final parameter fingerprints, minibatch digest and loss values must match.
Verify the horizon inventory independently and verify that both arms receive
identical receipt and label tensors. Synthetic checks do not execute an
additional real-data fit. Original source and checkpoint bytes remain frozen.

Publish all ten final checkpoints before an inference-only evaluation on the
same 2,048 TRAIN histories. Save every target and protected eight-endpoint
distribution at the four existing trace stages. Compare with the published
frozen original trace, without rerunning the original models. Preserve all
case IDs, labels, per-stage accuracy, Brier, uncapped NLL, per-case regressions
and repairs, all five seeds, both laws and flat-arm comparisons.

## Fixed development decision

Retain this objective only as a candidate for a fresh-study design if every one
of the ten native law/seed cells meets all seven checks against the original
native TRAIN trace:

1. Final target accuracy does not decrease.
2. Final target Brier does not increase beyond 1e-12.
3. Final protected accuracy does not decrease.
4. Final protected Brier decreases by more than 1e-4.
5. Mean protected Brier across claim / first / both decreases by more than 1e-4.
6. After-teaching protected accuracy does not decrease.
7. After-teaching protected Brier does not increase beyond 1e-12.

Record `KEEP_PREFIX_OBJECTIVE_FOR_FRESH_STUDY` only if all 70 checks pass;
otherwise record `REVISE_PREFIX_OBJECTIVE` and stop this version. Report NLL
changes and every adverse case regardless of the decision. Do not substitute
pooled gains for a failed cell or run another budget, schedule or seed subset.
The flat comparison is descriptive here; passing is not a superiority claim.
Failure rejects this fixed allocation under this budget, not the possibility
of learning preservation or the adequacy of a particular memory size.

No held-out performance or G5 admission follows from this TRAIN comparison.
The original finite TEST bank has been opened. Any later admission study needs
prospectively new observable histories/structures, counterbalanced challenged
and protected word roles, matched exposure and the unchanged admission gates.
G6–G8 and production integration remain gated. No architecture rewrite is part
of this comparison.
