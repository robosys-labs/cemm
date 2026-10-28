# Proposed opt-in forecast normalization

The locked v2 public study remains **incomplete**. Its post-hoc case-6
inspection found one flat-model represented world with probability
`1.00000003851976`, but did not retain that forecast's complete raw world
distribution. The replay host and the original failure's host may differ.
This observation supports a numerical-mass hypothesis; it does not establish
the original failure's exact cause or demonstrate that the forecast satisfies
the proposed normalizer's preconditions.

`forecast_normalization.normalize_joint` is a separate, opt-in helper. It is
not connected to the v2 runner, existing models or historical scorers. For a
nonempty in-process dictionary of one-to-six-bit worlds and finite,
nonnegative probabilities, it computes the joint total using `math.fsum` and
requires that total to be within `1e-6` of one. This bound mirrors the existing
scorer's total-mass tolerance; it is a design choice, not independent evidence
that a particular forecast is valid. A missing world stays missing, an explicit
zero stays zero, and positive values must not underflow to zero.

Every represented value is divided by the same total; no entry is clipped
independently or supplied from an evaluator. Invalid types or world shapes,
negative or nonfinite values, zero mass, material mass drift, and any
normalization that loses positive support or produces out-of-range values are
rejected. The returned audit includes every raw value, normalized value and
delta, original and normalized total mass, the largest raw overshoot, and the
maximum and total absolute adjustments. These records make the numerical
change reviewable rather than silently concealing it.

Floating-point division can make previously distinct maximum values become
an exact tie. The audit therefore reports the raw and normalized maximizer
sets and lexicographically selected MAPs, including whether either changed.
The helper does not promise unchanged MAP choices or calibration. It checks
an in-process dictionary and cannot detect duplicate serialized keys that
were already discarded before that dictionary was constructed.

Tests use fabricated distributions, including one with the same *individual*
overshoot as the observed anomaly; the remaining world masses in that test
are synthetic. The tests do not reconstruct or score the actual case. Any
study that applies this helper must first measure and retain the complete raw
forecast, predeclare the transform and its diagnostics in a new frozen
protocol, independently review the new runner, and preserve the v2 failure.
No original score or historical protocol is changed by this standalone code.
