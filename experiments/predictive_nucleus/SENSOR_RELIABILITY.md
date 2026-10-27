# G1d-a — sensor reliability is not world physics

**Scope:** isolated experimental filter change only. Previous G0/G1c protocols,
trained weights, reference checkpoints, and production runtimes are unchanged.

Previously the exact two-mechanism posterior treated every post-action sensor
bit as infallible. One mistaken bit could remove an otherwise plausible world,
artificially force a mechanism decision, and be mislabeled a physics failure.

The filter now accepts an **out-of-band, independently calibrated** symmetric
bit-error probability in [0, 0.5) on construction. Default zero preserves
the legacy perfect-sensor behavior. This is *supplied instrument reliability*,
not learned world dynamics and never parsed from an untrusted message. The
first full state observation remains a verified anchor; only later readings
are modeled as noisy. Conditional on world state, successive observed bits
are assumed independent. These limitations require explicit future ablations.

For every observed bit, the likelihood contribution is

    P(observed | world state) = 1-epsilon if equal else epsilon

The joint world/mode posterior is updated with these likelihoods **only after
real sensor feedback**. Missing bits contribute a factor of 1; no reading is
not evidence for a 0 state. Hypotheses are not thrown away merely because one
noisy reading disagrees. Replay IDs remain idempotent.

The information-gain planner now computes expected *sensor reading* outcomes,
not information from inaccessible error-free oracle states. Consequently a
noisy contact offers less expected information than the same perfect-sensor
contact. Physical intervention proposals remain read-only; no effect gateway
is added.

This alone **does not** prove model mismatch vs sensor failure. One unusual
reading cannot identify its cause without independent sensor characterization
and repeated discriminating observations. The next tranche will attach a
prequential forecast adequacy test with a separately declared false-alarm
budget and evaluator-only physics/sensor-shift stress cases.

**Decision: retain sensor likelihood integration; G1 NOT ADMITTED.**

Run:

    python -m unittest discover -s experiments/predictive_nucleus/tests -v

See test_sensor_reliability.py for exact compatibility and noise controls.
