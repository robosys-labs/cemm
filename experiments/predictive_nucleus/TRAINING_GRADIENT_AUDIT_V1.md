# Training-only gradient audit and one-bias initialization candidate

Base: `148a98f62665445e6bb0a39cbabe23689ec0614b` (PR #73). Tracks #22.
**Diagnostic complete; G3 remains OPEN. No model was fitted or promoted.**
The historical decision remains `REVISE_SATURATION_HYPOTHESIS`.

## Executed scope

All ten saved factor/unsaturated checkpoints were analyzed on exactly the same
1,152 observed NAND training events per model: 11,520 dependent event evaluations,
not new independent outcomes. The audit loaded only ten allowlisted non-source
files: protocol, protocol lock, source/data manifest, training tape, language
checkpoint bundle, and five NAND world checkpoints. No challenge, oracle, parser
label, NOR checkpoint or retention bank was read by the diagnostic. The existing
regression suite separately checks its historical synthetic/static fixtures.

The read boundary is a Python audit-hook check, not an OS sandbox. Data/source
hashes and tensors were checked. Every recomputed mean NLL matches its saved
post-training value within 1e-11; weights, caller gradients, mode/trainability
flags and RNG are preserved. There are zero optimizer updates.

The derivative report retains per-word/position losses, every training error ID,
latent action probabilities and observation-conditioned responsibilities, lexical
and layout values, hidden-tanh derivatives, immediate versus future-feedback
logit gradients, parameter-block norms, cell-gradient cancellation, and all 89
Hessian eigenvalues. Responsibilities come from the frozen learned world and the
observed outcome; they are not external role labels or independently correct
semantic truth. Full derivatives include belief updates through later events.

## Result: fitted layout geometry is incompatible in all three failing candidates

| Unsaturated seed | Observed training NLL | Exact errors / 1,152 | Layout responses at lexical positions 0, 1, 2 |
|---|---:|---:|---|
| 7 | 0.0024593734 | 0 | -1.441110, +1.716344, -1.598372 |
| 11 | 0.3380641918 | 192 | +0.152930, +2.643407, +0.011731 |
| 23 | 0.1515727678 | 64 | +3.846379, +0.259038, +3.994774 |
| 37 | 0.0043464179 | 0 | +1.609461, -1.988642, +1.776192 |
| 53 | 0.1576236502 | 64 | +4.159623, +0.341272, +4.555427 |

Seeds 23 and 53 mispredict all 32 observed instances of both `receives` and `vok`
at lexical position 1. Seed 11 fails six cells in total, listed in the
machine-readable summary. These are observational string/position buckets, not
labels supplied to training. All three failing candidates have same-sign layout
responses; both passing controls have sign-changing responses.

This is more than a correlation for this fitted rank-one representation. Its
log odds have the form `d(word,position) = a*c(word)*l(position) + b`. Consequently,
`d(w1,p)-d(w2,p) = a*(c(w1)-c(w2))*l(p)`. The observed training outcomes for
`contacts` versus `receives` require the preference ranking to reverse between
positions 0 and 1. In each failing candidate, the frozen-world conditional
log-likelihood ratios have the required opposite signs with absolute margins
above 6.1 nats in those cells. Same-sign `l(p)` cannot express both rankings,
regardless of changes to the lexical branch alone. This is a defect of the
*fitted factors*, not proof that the function class lacks a solution.

The loss mixture is not withholding all correction signal. Failing-cell mean
immediate two-logit gradient L1 magnitudes are approximately 1.27-1.57 in the
unsaturated failures. Full parameter gradient norms are 0.088287, 0.121965 and
0.024733 for seeds 11/23/53. Future-feedback contributions are small, not silently
detached: norms 0.000318, 0.0000315 and 0.0000235 respectively. Cell gradients
partially cancel; this is a descriptive decomposition, not a proof that one
optimizer change will fix the problem. The Hessians contain negative directions,
and these points are nonstationary; do not label them certified local minima.
Hessian coordinates/scales depend on the parameterization.

## Smallest implemented next intervention

`binding_centered_init.centered_encoder(seed)` changes only the initial scalar
`layout.0.bias`. It sets `bias = -(2/3) * sum(layout_weight)`, so the three legal
identity-marker layouts have zero-mean initial responses. The three layouts each
contain two ones, making their mean `(2/3, 2/3, 2/3)` without assigning any semantic
role or polarity. Which position is positive is not prescribed and varies by seed.

The other 88 initial scalars, model class, forward pass, observed-outcome loss and
89-parameter count stay unchanged. The bias remains trainable; later same-sign
responses remain possible. No terminal activation, word dispatch, inverse rule,
role label, new optimizer or runtime/checkpoint registration was added.

**IMPLEMENTED_NOT_SCIENTIFICALLY_EVALUATED.** This is a geometry-informed
initialization hypothesis. It does not prove the saved failure was caused only
by initialization, or that centering will prevent recurrence.

Next: freeze a genuinely fresh five-seed standard-unsaturated versus centered-
initialization comparison before fitting. Keep all other initial tensors, common
observed histories, 256-update budget, optimizer, world weights and criteria
fixed; explicitly disclose the intentional one-scalar initialization difference.
Publish actual checkpoints before one collection, retain all failed seeds and
old-bank retention, and require exact/probability/retention success before G3
advances. No such fit, new bank or collection has been executed here.

## Verification and costs

Thirteen new tests pass, including analytic responsibility gradients, full loss
parity, immediate/future separation, exact cell-gradient partition, synthetic
finite-difference verification of all Hessian eigenvalues, no-mutation and input
boundaries, and one-scalar initialization/determinism checks. The first focused
run had a float32-versus-float64 assertion-fixture error; it was corrected before
the research diagnostic. The original log is retained.

Full local suite: **906 discovered, 905 passed, one full-checkout-only skip** in
92.922 seconds. The original protocol and all **30 historical locks** pass.
Maximum cell-gradient sum discrepancy: 2.220446049250313e-16; maximum Hessian
asymmetry: 4.263256414560601e-14. Derivative computation took 7.858441 CPU / 7.858833
wall seconds; peak RSS was not recorded. This is not service latency or an
independently validated scientific result.

Adds 211 audit +19 initializer +178 test = **408 Python lines**. Retained research
Python is **39,444**, including **17,199 test lines**. The inclusive 2,000-line
objective remains unmet. Historical models, checkpoints, data, protocols and
failed decisions are byte-identical; only the active handoff changes among prior
files. Production, world dynamics and authority boundaries are untouched.

The committed `results/training-gradient-summary-v1.json` retains all ten seeds,
source/input hashes and complete error-cell counts. The delivery bundle holds the
full per-cell/eigenvalue/error-ID artifact `training-gradient-v1.json.xz`, SHA-256
`06ef26498d8dc73d6de9a822f97129d8fcec8d88b02794920828ef13b8e36943` (66,664 bytes),
and all local logs. That full binary artifact is delivered separately, not stored
in this commit. No hosted CI result is assumed by this document.

Reproduce the read-only diagnostic on this source (new output path required):

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
python -m experiments.predictive_nucleus.training_gradient_audit \
  --output /tmp/cemm-training-gradient-new.json
```
