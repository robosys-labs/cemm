# Public G1 training-schedule feasibility fixture

**Status: development design only; G1 remains HOLD / REVISE.** The
[roadmap](../../docs/research/2026-10-predictive-world-nucleus-roadmap.md)
requires learning world dynamics from observations, actions and subsequent
outcomes before language, with flat-recurrent, no-change and memorizing
controls at matched examples and compute. Its G1 exit requires the frozen
independent challenge, at least five model seeds, complete-world performance,
role reversals, withheld compositions and no leakage. This fixture is a
small step toward an admissible training design, not that challenge or an
architecture comparison. The historical frozen protocols remain unchanged.

## Proposed schedule

Supply a complete initial sensor anchor, two distinct ordered participants A
and B, and two fixed binary set values x and y. Do not choose the actions or
values from the hidden orientation or later outcomes. In a noiseless public
fixture, observe exactly the participants after each action:

| Step | Action | Feedback | Immediate complete sample |
|---|---|---|---|
| 1 | contact(A, B) | A and B | contact: yes |
| 2 | contact(B, A) | B and A | contact: yes |
| 3 | set(A, x) | A | set: yes |
| 4 | set(A, y) | A | set: yes |

Feedback from each step is the next step's observation. Measurement order is
permuted; missing entities are not interpreted as zero. Every case has one
pair and two contacts, so the schedule does not establish generalization to
multiple pairs, longer trajectories or withheld graph families. The initial
complete anchor, participant-only feedback, actions, preparation curriculum,
and fixed no-dropout/no-noise sensors are supplied assumptions, not learned
capabilities. Action operand order is observable; a hidden source role is not
supplied as a learner field.

The executable fixture enumerates 32 public combinations: four ordered
initial participant-bit pairs, four (x, y) combinations and two simulator
orientations. All 32 cases in a block share the same three identities; each
orientation twin has the same initial observation and action schedule. For
this block the count is 64/64 complete contact pairs and
64/64 complete set pairs. At each of the two contact positions the four
ordered pre-contact bit pairs occur eight times each; at each set position the
four `(previous bit, assigned value)` pairs occur eight times each. These are
designed fixture counts, not 32 independent challenge draws or accuracy
results. All initial states and outcomes come from the evaluator's simulator;
the fixture does not establish an independently authored oracle.

Run the count with `python -m experiments.predictive_nucleus.schedule_fixture`.

Both consumers can receive separate copies of the same realized sensor/action
history. The offline view intentionally supports existing batch extractors and
does not enforce prediction-before-feedback; future readings remain offline
training targets, not input features. It does not expose simulator state,
orientation or gold as explicit learner fields. The evaluator, its case indices
and the complete offline history remain available to the caller; this fixture
cannot establish the roadmap's no-leakage requirement. The earlier training
generator also has a separate documented public-ID orientation leak. Matching
raw histories and complete events also does not match the models' objectives,
effective training examples, compute or supplied inductive biases.

## Next requirements before comparison

- Specify fresh training, selection and calibration lineages and retain a
  separately held, independently authored challenge. Preserve all existing
  manifests and never inspect frozen challenge cases during development. Do
  not split this shared-identity factorial block across those partitions.
- Implement a reviewed causal channel or training pipeline that prevents future
  records from becoming input features; verify the exact same realized anchor,
  action, sensor mask and values reach both models at every step.
- Measure effective examples, objective weighting, compute, memory and
  latency. Add no-change and memorization controls and explicit ablations for
  analytic belief, object-local bias and the repeated-pair curriculum.
- Predeclare visibility, dropout and sensor noise, then independently control
  sensor randomness and physical event provenance for the intended setting.
  The public noiseless fixture supplies no authentication or independent custody.
- Include new identities, multiple pairs and paths, unchanged entities,
  counterexamples and withheld compositions in later controlled evaluation;
  do not infer performance from fixture coverage.

The experimental Python tree has 6,213 physical lines across 50 Python files,
including tests (5,858 lines before this tranche), above the roadmap's
practical 2,000-line target. That is a deviation to track and rationalize;
correctness and test coverage take priority over shrinking the count. The
supplied analytic belief and local-effect
structure are additional architectural biases to report, not evidence that a
general meaning nucleus has been learned. PR #21 and production stay separate.
