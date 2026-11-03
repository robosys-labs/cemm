# G4 matched conflict decision

**KEEP_MATCHED_CONFLICT. Retain the one-bit empirical receiver.** All 460
preregistered checks passed. The empirical and neural receivers made identical
unassisted choices, requests and final choices throughout. The empirical
receiver also had slightly lower bit Brier loss, 0.062500 versus 0.062518.
This decision advances bounded G5 development.
[Protocol](MATCHED_CONFLICT_STUDY_V1.md) · [Exact retained weights](results/matched-conflict-v1/retained.json) · [Registered results](results/matched-conflict-v1/scored/decision.json)

## Did the training outcomes change what the receiver chose?

Yes. Both receivers trained on the same public sequences, probe actions,
observed probe outcomes and explored target actions. Only the selected target
payoffs distinguished the persistent convention from the switching one. On
15,360 paired held histories where calibration was informative and the target
reports conflicted, the separately fitted receivers chose **both opposite
actions correctly on every pair**. Swapping their weights gave 0/30,720
correct individual choices. A rule fixed across both training histories can
get at most one of each twin pair right. Removing either the earlier payoff
or source attribution also capped accuracy at 50% on these critical cells.

| Policy or intervention | Correct before verification / 122,880 | Mean net utility |
|---|---:|---:|
| Fitted neural receiver | 107,520 | 0.912500 |
| Fitted one-bit receiver | 107,520 | 0.912500 |
| Equal weighting of target reports | 92,160 | 0.825000 |
| Either fixed named witness alone | 92,160 | 0.818750 |
| Learned request schedule with suppression or shuffled verification | 107,520 | 0.870833 |
| Opposite convention's fitted neural receiver | 76,800 | 0.662500 |
| Free silence without reports or verification | 61,440 | 0.500000 |

Mean net weights the three fee conditions equally. In the **30,720 genuinely
unresolved** cases, the earlier reports agreed and the target reports
conflicted. Both receivers assigned exactly 0.5 to the target bit. Without
verification they got 15,360 of those cases right. At fee 0.05 they verified
all 30,720, resolved them all, and made zero other requests. At fee 0.75 or
with verification unavailable, they made zero requests. All 15,360 remaining
misses in each of those two fee conditions are in this unresolved stratum.

| Fee | Requests | Goals achieved / 122,880 | Net utility per round |
|---|---:|---:|---:|
| 0.05 | 30,720 | 122,880 | 0.9875 |
| 0.75 | 0 | 107,520 | 0.8750 |
| Unavailable | 0 | 107,520 | 0.8750 |

## Scope and verification

The receiver learned a direction for weighting evidence from selected-action
outcomes. The two candidate interpretations, source matching, provision of a
perfect verification bit and expected-value request calculation were supplied.
The balanced conventions are deterministic. A single distinguishing reward
can identify the empirical sign. All five inherited seeds revisit the same
scenario IDs. The 122,880 evaluations comprise 12,288 distinct scenario IDs
across both physical laws, evaluated at five seeds and in two conventions.
Arrival order was counterbalanced. Stale or off-topic messages in open-ended
dialogue remain beyond this decision.

The frozen G3 language and world checkpoints ran on the observed prefixes,
with the final physical endpoint redacted. All 1,920 conditional goal-action
probabilities across training and challenge matched the archived values
exactly. The 960 held values came from 84 NAND and 68 NOR law-scoped input
episodes. Each live matrix was reused across its communication factorial.
The inherited physical traces were opened in prior work. The two-source
histories and matched-convention decision were prospectively registered.

The [source freeze](https://github.com/robosys-labs/cemm/commit/03f910131fef740e7d53e9e7117b4cec4a8e2f33)
preceded fitting. [Fitted checkpoints and selected training rewards](https://github.com/robosys-labs/cemm/commit/a817b9e446f7ff610a267af6f28b73525bf4e437)
preceded collection. The [complete raw decisions](https://github.com/robosys-labs/cemm/commit/fd502bd124ccfcfe1344a79d7e5c4964ac1c93f6)
preceded [scoring](https://github.com/robosys-labs/cemm/commit/f8b2942be735679576d4dd4dcb34457bb26ce541).
Two separate same-team reconstructions reproduced the selected training
outcomes, all 1,105,920 unassisted choices and all 3,317,760 priced arm
decisions. Direct ungrouped gradient fits reproduced the 20 neural slopes
within 8.89 × 10⁻¹⁶. All 20 empirical signs and all 37 stage-output hashes
agreed. The three formal stages used 38.18 CPU seconds, with peak reported
RSS of 347,560 KiB. These timings include batching, validation and output.
[Run the standalone replay](reviews/matched_conflict_replay.py) · [Replay receipt](results/matched-conflict-v1/replay.json)

A post-score warm timing on 120 held physical menu/seed combinations
recomputed all eight conditional G3 action values for both menus inside
each timed trial. The first empirical receiver's final choice took
**14.97 ms median and 19.30 ms p95** from already-loaded observed histories.
All 960 values and the 240 decisions across both conventions matched the
sealed records. This includes input preparation, world and language replay,
the request choice and immediate in-memory verification. Checkpoint loading,
external sensor/network latency, hashing and output were excluded. Peak
process RSS was 338,760 KiB including loaded validation data. The measured
path imported 25 research modules with 4,057 physical Python lines,
including validation helpers. The inclusive 2,000-line goal is still unmet.
[Timing measurements and module inventory](results/matched-conflict-v1/live-timing.json)

## G5 handoff

A TRAIN-only feasibility check starts with a physically corroborated directed
meaning and an independently established second word. An opposing observation
is compatible with either a lasting reversal or a one-off exception. Before
a later probe, the two possibilities yield identical observations and
opposite target meanings. After that probe, the agent receives a stale
duplicate and crosses an episode reset to a new roster, lineage and layout.

Across 768 matched twins the pre-probe ceiling was 768/1,536. The newest
distinct physically verified record by event time resolved all 1,536 later
choices, with zero additional queries and full retention of the second word.
The last-arriving receipt and the last unverified claim each scored 50%.
A reset policy also achieved full correctness by buying 1,536 extra checks.
This uses 12 triples of TRAIN menus and seed 7, with two supplied directed
interpretations per term. It establishes feasibility and a baseline for
future evaluation. Next, freeze a held-out correction-and-retention study
with multiple applicable scopes and include cases where even the latest
verified record is insufficient to choose a meaning.
[Executable G5 preflight](revision_preflight.py) · [Counts](results/revision-preflight-v1.json)
