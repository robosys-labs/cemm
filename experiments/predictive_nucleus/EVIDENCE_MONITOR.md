# G1d-b — prequential predictive-adequacy monitor

**Not G1 admission; not a certificate of new physical laws.**

A two-hypothesis posterior alone cannot distinguish unexpectedly changed physics
from a mislabeled observation, sensor error, stale evidence or distribution
shift. The isolated \`PredictiveAdequacyMonitor\` therefore scores successive
*committed* model forecasts before reading the next observed sensor values.

## Hypothesis and statistical contract

Let \`p_t(y | history, chosen action, sensor coverage)\` be the **joint**
probability of the actually observed sensor bits, integrating over all current
world states and all anonymous persistent mechanism hypotheses. The noise
channel is a separately supplied, source-specific, independently characterized
symmetric bit-error rate. It cannot come from the utterance itself.

Use a predictable reference \`q_t(y) = 2^{-m_t}\` where \`m_t\` is the number
of observed binary readings. Maintain the prequential evidence ratio:

    E_T = product(t=1..T) q_t(y_t) / p_t(y_t)

Update only on a real, unique, time-ordered observation whose sensor set was
precommitted **before** seeing outcome values. If the model's predictive
conditional distributions and sensor assumptions are correct, E_T is a
nonnegative martingale and a threshold \`E_T >= 1/alpha\` is an anytime-valid
test (Ville bound). With alpha=.05 the nominal *ever-flagged* probability is
at most 5% **under those assumptions**, not a promise of zero mistakes.

The monitor reports:
- \`NO_EVIDENCE\`: no measurement arrived; no information increase;
- \`OBSERVATION_COMPATIBLE\`: observation does not cross the statistical gate;
- \`SURPRISING_BUT_UNCONFIRMED\`: low likelihood without accumulated evidence;
- \`MODEL_MISMATCH_EVIDENCE\`: accumulated likelihood ratio crosses the gate.

These are *predictive-model adequacy* diagnostics, not labels for causality.
Independent sensor audit and controlled counterfactual outcomes are still
needed to distinguish unreliable instruments, unmodeled mechanisms and
nonstationary world physics. A mismatch alarm alone does **not** authorize
learning/retraining, claims, external actions, or a release promotion.

Sensor/source IDs are allowlisted and frozen at monitor creation; observation
content cannot assert a better error rate. Forecasts are deep-copied at commit
time to prohibit post hoc probability edits. The same sensor event cannot be
counted twice under either the same or a different evidence ID. Out-of-order,
unknown-source, malformed, future, and uncommitted observations fail closed.

**Assumptions/limits:** independent calibrated sensor errors conditional on
world state; predeclared sensor coverage, with missingness independent of
unseen outcome; complete and correct conditional probabilistic forecasts.
Misspecification or correlated sensor faults invalidate nominal false-alarm
bounds. A reliable zero-error channel produces infinite model evidence for
an impossible event; this is deliberate and should be sensitivity-tested.
The test is not a general-purpose drift detector and does not itself learn a
new mechanism.

## Reproduction / next experiment

    python -m unittest discover -s experiments/predictive_nucleus/tests -v

Nine synthetic, evaluator-independent tests check ambiguous histories,
single plausible noisy sensor errors, accumulation across unique time
steps, precommitment, dropout, duplicates, frozen forecast snapshots,
correlated possible worlds, and invalid probabilities.

The next tranche will run controlled *unsealed* physics-shift and sensor
corruption experiments against identical predictive weights, with matched
realized probe actions and per-case uncertainty/false-alarm reporting.

**Decision: KEEP experimental diagnostic / G1 gate NOT RUN.**
