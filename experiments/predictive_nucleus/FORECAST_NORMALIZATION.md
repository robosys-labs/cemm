# Proposed opt-in forecast normalization

The locked v2 public study remains **incomplete**. Its first post-hoc case-6
inspection found one flat-model represented world with probability
`1.00000003851976`, but did not retain that forecast's full distribution. A
[later post-hoc replay](results/case6-masses-0adc3a2.json) captured all eight
world masses for that same reported context. Their accurately summed mass is
`1.0000000433514706`, within this helper's tolerance. The original failed
run did not record its offending forecast or host, so neither replay proves
the original failure's exact cause or reconstructs its complete distribution.

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

Tests include fabricated distributions and a regression against the complete
vector retained from the later post-hoc replay. For that vector, the helper's
largest per-world adjustment is approximately `4.34e-8`, and the
lexicographic MAP remains unchanged. This checks a recorded vector without
reading evaluator truth or computing a score; it does not establish a general
repair or identify the original offender. A study applying the helper must
retain the complete raw forecast, predeclare the transform and its diagnostics
in a new frozen protocol, independently review the new runner, and preserve the
v2 failure. No original score or historical protocol is changed by this
standalone code.
