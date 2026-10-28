# G1d-c: development stress without language

> **Audit hold:** Joint log loss is clipped, sensor randomness derives from a
> public handle, and physics strata use different initial worlds. See [the
> integrity audit](2026-10-28-AUDIT.md).

This tranche tests the same frozen G1c learned kernel and belief engine under
sensor uncertainty and physics changes. It is **not an independently blinded
challenge**: the worlds in stress_world.py are public, developer-authored
and intentionally used for diagnostic evaluation only.

The test oracle is separate from world.py and is never imported into
latent_model.py, calibration.py or uncertainty.py. The evaluator alone
has hidden mechanism selection, complete future state and shifted physics.
The learner still receives the familiar ordered contact/set action, opaque
handles, frozen neural predictions, then actual measured outcomes.
The full initial observation is externally verified; after each action
the sensor coverage is fixed **before** observing the outcome.

Seven predeclared scenarios are frozen in stress_protocol_v3.json and protected
by its own SHA256 lock, while the original G0/G1c protocol hashes and sealed
challenge seeds remain unchanged:

- reference without corruption;
- reference with up to 65% random participant-sensor missingness;
- reference with independently calibrated 8% random sensor errors;
- reference with 20% actual error but falsely assumed 1% (instrument
  misspecification control, **not** proof of changed physics);
- bilateral pair updates, where both participants change;
- conditional pair updates, changing the effect function;
- orientation switching after the first contact, violating the assumed
  fixed latent mechanism.

Each original world is evaluated under the same initial state, the same
held-out target pair in both directions and separate probe policies:
information-gain active probing, uniformly random contact-only,
uniformly random actions from the candidate action inventory, and no probe.
**Both random controls consume exactly the number of physical actions actually
used by active probing for that same world** (including active 0-step worlds).
This improves over comparing 1.08 active steps with 2 random steps, but
differences in physical action type and consequent post-probe world state
remain a limitation; report interventions separately. Query bit-visibility
may still differ under random dropouts; observed bits are reported.

Reported for each model seed and scenario: exact complete-world accuracy,
both directions correct, legacy clipped joint NLL, Brier, ECE, answered coverage and
precision, statistical alarm rates, average probe cost, sensor bits received,
p95 planning time and case IDs where active wins/loses to cost-matched random
contact probes. The e-process acts on **real committed probe observations**,
never the two hypothetical scored target outcomes.

The corrected paths separately report represented-probability uncapped log
loss and zero/floor counts. The historical NLL is clipped at `1e-12`.

Nominal 5% false-alarm bounds apply only under correctly specified conditional
forecasts, calibrated independent sensor errors and pre-outcome sensor selection;
the experiment explicitly tests one false calibration. An alarm is evidence
against the *current predictive distribution*, NOT reliable causal attribution
to an architectural bug, a sensor fault or new physics.

Reproduce:

    python -m unittest discover -s experiments/predictive_nucleus/tests -v
    python -m experiments.predictive_nucleus.stress_trial --train 600 \
      --calibration 200 --worlds 10 --steps 200 --seeds 7,11,23,37,53

The fixed v3 manifest is reviewed independently of CI output before adjusting
any world family. Any subsequent model/parameter revision gets a **new** split
and protocol. More evidence is needed on new-physics families, partial
observations and a parameter/compute-matched flat recurrent baseline before
G1 can be admitted; nothing here licenses G2–G5 or runtime integration.

**Decision: G1 STILL NOT ADMITTED.**
