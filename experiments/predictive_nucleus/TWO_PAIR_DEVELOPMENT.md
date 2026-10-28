# Public two-pair development fixture

**Development mechanics only; G1 remains HOLD / REVISE.** This fixture
extends the public four-step curriculum to two distinct interaction pairs.
It supplies a full initial anchor and the following fixed five actions:

| Action | Supplied feedback coverage |
|---|---|
| contact(A, B) | A, B |
| set(B, x) | B |
| observe | B, C |
| contact(B, C) | B, C |
| set(C, y) | C |

The observation-only action leaves simulator state unchanged and consumes a
step. Its B,C visibility is explicitly supplied by this curriculum; it is an
additional sensor-policy assumption, not participant-only feedback. The flat
extractor includes this measured step in its objective; the structured
contact/set extractor does not. Consequently shared histories do not make the
objectives, effective examples or compute equal.

The public factorial enumerates eight initial A/B/C bit assignments, four
fixed `(x, y)` assignments and two orientations. In its 64 cases, all 128
contact and 128 set events have complete immediate before/after participant
readings; each supervised input context occurs 16 times at each relevant
position. The 64 observation actions contribute two feedback bits each.
The case block shares identities and is not 64 independent worlds. Two of
the 32 orientation-twin pairs have identical complete sensor histories, so
these observations do not identify the hidden orientation in every episode.
The public evaluator and full offline records are inspectable and do not
provide blindness, independent custody, or authenticated physical events.

An explicit development-history replay accepts bounded sensor-only histories
without changing the older four-step fixture's strict constructor. It validates
logical sequence and copies records, not the timing or physical origin of a
reading. Its observe actions can supply any subset of known anchor IDs; the
specific B,C policy above is fixed and checked by this fixture, not enforced
as an independently custodied sensor plan by the generic replay. Offline
feature collection preserves chronology and the structured episode grouping;
it is not online gradient training or a security boundary.

The development control `FullWorldEventMemory` lifts a frozen, local empirical
outcome table to a distribution over supplied anchor IDs by carrying forward
the last readings for nonparticipants. It identifies stale carried readings
and abstains for unseen or incompletely observed participant contexts. Anchor
completeness, sensor accuracy and nonparticipant persistence are assumptions;
the control is not a full-history memorizer or a calibrated challenge baseline.
Its zero probabilities remain represented zero when scored, rather than being
silently replaced by finite uncapped loss.

No independent validation, challenge, or model comparison is performed here.
Before G1 admission, separately review and freeze split lineage, sensor and
event provenance, controls and compute; evaluate the independent challenge
and held-out compositions under the roadmap. Existing G0–V8 locks are intact.

This tranche has 8,594 Python physical lines across 61 files including tests,
above the roadmap's practical 2,000-line target. Any later consolidation
must retain the independent correctness checks and historical replay evidence.
