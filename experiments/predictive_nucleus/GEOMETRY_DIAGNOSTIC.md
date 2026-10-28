# Participant-visibility feasibility diagnostic

**Development-only; G1 remains on hold.** This diagnostic counts the
immediate observation pairs available to the existing structured sample
extractor under a newly generated, noiseless participant-only sensor trace.
It does not train or compare models and is not an evaluation protocol.

The historical reference training episodes begin with a complete observation,
then generally set each contact participant before performing the contact.
For this diagnostic, the evaluator constructs fresh readings from the relevant
simulator states: after a set or contact it observes exactly the action's
participants; after an observe-only action, with no participants, it returns
an empty reading. Each reading becomes the next action's input. This is not
an intersection with the old, already partially sampled readings. Visibility
is noiseless with no dropout. It models only this visibility rule; the action
distribution and the initial anchor are also part of any future comparison.
The reconstruction returns an entire offline trace and cannot enforce
prediction before feedback. It is not a learner or training interface.

On the 600 public reference training episodes used in the flat diagnostic,
the schedule contains 1,800 sets, 900 contacts and 278 observe-only actions.
There are **0 of 900 contacts** with both ordered participants observed in
both the immediately preceding and following readings; 805 of the 1,800 sets
have their participant in both readings. The current `sensor_only_samples`
requires exactly those immediate before/after readings for contact supervision.
Thus switching this schedule to the diagnostic visibility rule would provide
that extractor no complete contact samples. This does not establish what a
different extractor, memory model, action schedule or sensor process could
learn. The result is a count of a public development fixture, not a challenge
score or a claim about general model capability.

The follow-on [public schedule feasibility design](SCHEDULE_DESIGN.md)
tests a four-action curriculum that provides complete immediate pairs; it
does not replace an independently reviewed experiment or challenge.

Reproduce the fixed public sample count with:

```sh
python -m experiments.predictive_nucleus.geometry_diagnostic
```

Before training under a new geometry, specify and inspect its action schedule,
visibility, missingness, noise and usable-sample counts. Both models must be
given the same realized action and sensor histories; compare objectives and
actual compute separately. Treat world lineage, not repeated actions or
optimizer seeds sharing worlds, as the unit for world-level analysis, subject
to verifying independence between lineages. A
separately held challenge, independent sensor-randomness custody, authenticated
physical-event provenance, and independently reviewed frozen protocol remain
necessary. This public helper supplies none of those properties, and the
historical G0–V8 manifests and diagnostics remain unchanged.
