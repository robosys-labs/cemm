# Public shared-history replay boundary

**Development inference smoke test only; G1 remains HOLD / REVISE.** The
public schedule fixture can be replayed to two distinct consumer objects. The
driver validates and copies one offline sensor/action history before invoking
the consumers. It supplies separate copies of the initial anchor, then for
each step supplies identical current observations and actions to both
`predict` callbacks. Only after both callbacks have returned synchronously
does it deliver separate copies of that step's feedback to each `receive`
callback. The callback order is fixed; returned forecasts are not scored.

The driver checks delivered records and callback order for cooperative
consumers. It does not establish that callbacks actually predicted, used the
record, or lacked other information. The evaluator and full offline trace are
available in the Python process; Python private attributes and copies are not
security isolation. This is neither independent custody nor authenticated
physical-event provenance. The fixture's 32 cases share identities and are not
independent challenge worlds.

The replay is single-use. A malformed input, invalid callback, callback error,
deferred callback result, or nested/concurrent run aborts the session. A
callback may already have mutated its learner before an error; no rollback is
provided, so discard and rebuild both learners after failure. Concurrent abort
can race with a callback that has already passed its state check; it cannot
stop or undo such a callback. Distinct wrapper objects can also share state;
object-identity checks do not prove model independence.

The existing structured kernel and flat GRU fit through different **offline**
batch objectives. The flat model's online forecast uses no gradients. Running
this replay with the existing untrained models tests inference integration
only: it does not perform training, match optimization or compute, or prove
that an eventual training pipeline is causal. Before comparison, validate a
separately designed training data path, account for different loss weighting
and effective examples, specify fresh splits and controls, and arrange the
independent oracle, randomness and challenge custody described in the audit.
All existing frozen manifests and challenge families remain untouched.

At this tranche the experimental Python tree contains 6,601 physical lines
across 52 files including tests, above the roadmap's practical 2,000-line
target. Preserve correctness checks and track the excess for a later review.
