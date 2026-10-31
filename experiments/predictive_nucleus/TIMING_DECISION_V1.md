# Explicit timing v1 — implementation and prospective study

**Stage: PREPARED; collection has not opened.** 2026-10-31, Africa/Lagos.
The [locked protocol](timing_protocol_v1.json) owns the decision criteria.
This tranche follows [hidden cycle v1](HIDDEN_CYCLE_DECISION_V1.md) and reuses
the ten checkpoints frozen at `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420`.
Formal G1 scientific admission remains **NOT_ADMITTED**.

## Implemented capability

The separate `timing_session.Session` accepts ordinary contacts and an explicit
two-contact group. `ordered` marginalizes two native transitions with no
intermediate feedback. `common_snapshot` makes both learned pair factors read
the same base world, conditional on the same persistent mode, then merges their
event-local changes using the supplied binary delta-union rule:

`y_i = x_i XOR OR_e(z_e,i XOR x_i)`.

The merger is supplied computation. Isolated contact data do not identify an
arbitrary simultaneous interaction law. The experiment tests reuse of learned
pair likelihoods under the declared timing contract. It adds no neural tensors,
training updates, law-specific inference branches, source/target labels or
gold write masks. Native model, inference, checkpoint and partial-feedback
implementations retain their original bytes and source pins.

The opt-in interface is restricted to full endpoint observations, 3–6 binary
entities, registered persistent-mode `DomainKernel` checkpoints and distinct
handles within each contact. It has at most 64 hypothetical intermediate worlds
and 4,096 ordered world pairs, or 16 common event-output combinations. It
preserves all four learned pair outcomes, including tiny source-change tails,
exact zero support and finite log probabilities that underflow on exponentiation.

Only actual endpoint feedback updates the committed world and mode posterior.
Every forecast binds timing, contacts, sensor coverage, checkpoint fingerprint
and the separately hashed scheduler into its receipt before feedback.

## Frozen design

Each episode has one fully observed acquisition contact, one grouped event,
then zero to two ordinary suffix contacts. Both timings have one group forecast
and one endpoint feedback: ordered timing receives no extra observation.

| Family | Group | Suffix | Atomic contacts |
|---|---|---|---:|
| Chain | `ab;bc` | `ca` | 4 |
| Repeated | `ab;ab` | None | 3 |
| Fan-in | `ac;bc` | `ab;ca` | 5 |
| Disjoint | `ab;cd` | None | 3 |

The third condition reverses the common-snapshot event list. It preserves each
contact's internal participant order. All eight three-vertex core anchors and
all sixteen four-vertex disjoint anchors are included, with both persistent
modes and global role reversals. Applicable entity counts are 3–6, with 4–6 for
disjoint groups. Spectators use one deterministic pattern per core/size/family;
this is not exhaustive coverage of all full-world anchors. The data audit
records actual group-entry core-state coverage after acquisition.

Per law/seed: **1,728 episodes, 4,608 forecasts, 6,336 atomic contacts**;
2,880 forecasts are identifiable and 1,728 acquisition forecasts ambiguous.
There are 864 role pairs, 576 timing pairs and 576 event-permutation pairs;
448 permutations change the list and 128 repeated-contact controls are trivial.
Across ten checkpoints the planned denominator is **46,080 forecasts**.

An independently coded truth-table oracle identifies **120 timing-sensitive
pairs per law** before collection: 16 chain, 64 repeated, 40 fan-in, zero disjoint.
All remaining views are retained. The expected pooled oracle MAP accuracy is
**81.25%**, because the first contact precedes mode-identifying feedback.
Episode, mode, timing, identity and seed views are dependent records.

## Decision and controls

Every seed/law/family/condition must preserve complete support, identifiable
complete-world accuracy and role conjunctions, full-joint probability quality,
known-fixed values and oracle-supported MAP predictions. Every critical pair
must give its own required world at least 0.9 and the opposite timing's world
at most 0.1, with at least 0.8 probability separation between timing inputs.
Every common-snapshot permutation must preserve the entire vector at every
forecast within `1e-12`. Missing forecasts or incomplete feedback retain their
planned denominators and cause `STOP_INCOMPLETE_EXECUTION`.

Native ordered composition applies learned background twice, including to a
future or former participant. Common snapshots apply it once outside the union
of participants. Disjoint oracle outcomes therefore agree, but their learned
soft distributions can differ. Their TV and NLL differences are descriptive;
lower common-time NLL does not establish superior dynamics. Suffix contacts may
legitimately erase a timing difference; convergence and all local NLL changes
are recorded rather than treated as failures.

The public source, protocol, bank and checkpoint-plan freeze precedes one
collection. All ten observed-only traces are saved before evaluator targets are
parsed. There is no fitting, tuning, retry or historical-study replay.

## Validation before collection

Synthetic tests independently enumerate both schedulers, verify exact native
single-contact compatibility, shared-mode dependence, event and identity
permutations, negative-infinity versus finite tails, receipts, endpoint-only
belief updates, rejection of invalid raw mass, and failure/omission accounting.
Fresh untrained synthetic checkpoints are separate from the ten study weights.
The full isolated regression result and source freeze will be recorded with the
collection result; no outcome is claimed in this preparation commit.
