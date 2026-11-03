# G4 receiver v1 decision

**KEEP_BOUNDED_RECEIVER.** All 150 frozen numerical gates passed across ten
law/seed conditions. The outcome-trained receiver achieved 26,880 goals in
34,560 held-out rounds. It made 11,520 requests and paid 576 utility units.
Free silence achieved 23,040 goals. The receiver gained 3,264 net utility
units, or 0.094444 per round. G4 remains open.

| Delivery intervention | Requests | Goal successes | Net utility per round |
|---|---:|---:|---:|
| Learned use of delivered reply | 11,520 | 26,880 | 0.761111 |
| Free silence | 0 | 23,040 | 0.666667 |
| Random reply at matched cost | 11,520 | 23,050 | 0.650289 |
| Shuffled reply at matched cost | 11,520 | 23,040 | 0.650000 |
| Suppressed reply at matched cost | 11,520 | 23,040 | 0.650000 |
| Literal trust at matched cost | 11,520 | 23,040 | 0.650000 |

The receiver asked and achieved the goal on all 7,680 useful and systematically
inverted-source rounds. It declined in every already-known, irrelevant,
too-costly, stale, shifted-focus and known-conflict round. On 23,040 declined
rounds all arms made the same decision with the same reported values. The
delivered arm repaired 3,840 incorrect free-silent choices with zero gross
success regressions. The source-blind literal shortcut lost the gain from
informative replies by interpreting the inverted source literally.

**Adverse result.** The receiver paid for all 3,840 decoder-unresolved replies and
achieved 1,920 goals, the same as silence. This consumed 192 units, one third
of the entire communication spend. The public request features in these
episodes match a potentially useful source. The unknown code becomes visible
only after delivery. The measured result gives no evidence of recognizing
whether the frozen decoder will resolve a reply in advance. The raw token names encode the private bit exactly. On stale, shifted and overly costly rounds, both
the receiver and free silence achieved 50% gross success.

The [subsequent receiver review](RECEIVER_REVIEW_V1.md) found that a post hoc
zero-fit rule with supplied source polarity reproduced every query and physical choice.

## Evidence and scope

There are 96 held-out menu–goal cases across 63 physical menus, nine communication conditions, two
possible readings and four replicates. The 6,912 distinct communication
scenarios are each evaluated with five inherited model seeds. The five seeds
share scenario assignments and terminal payoffs. Training used 46,440
selected-action outcomes. Per law and seed, the receiver fitted four signed
source corrections and six gross request-gain entries. The G3 models were
reused through archived canonical forecasts. A two-symbol sensor code,
fixed source behavior, hypothetical
action utilities and the public opportunity feature are supplied parts of
the task. Only the receiver's source corrections and request values are learned.

Delivery interventions at the same realized query schedule isolate the
payload's effect on this receiver. Absolute net gains depend on the constructed
mix of decision-switching menus, costs and source regimes. The physical tasks
and forecasts were opened during earlier G3 work. New communication evaluation
held out the branch-return structure and its rosters from receiver fitting.
Source reliability is stable by construction. Source conflict here is an
existing claim and a possible contrary reply with decisive local evidence.
Staleness and focus changes use independent synthetic probes. General
conflict resolution, natural-language speech acts and novel source behavior
remain open.

The selected-action reward Brier score pooled over trials was 0.111372 for
delivery and 0.166859 for free silence. Training, collection and scoring used
17.23 CPU seconds combined, with maximum stage RSS of 224,596 KiB. Median/p95
decision time was 4.907/10.496 microseconds for all six arms on this host;
these timings exclude input construction and archive I/O.

[Prospective study](COMMUNICATION_STUDY_V1.md) ·
[Per-condition gates, calibration and adverse examples](results/communication-v1/scored/decision.json) ·
[Same-team saved-record arithmetic and receipt checks](results/communication-v1/saved-review.json).

| Published stage | Commit |
|---|---|
| Source, runtime and targets | `42aee414e2671a8c9bb170f902e795f331d93633` |
| Actual checkpoints and TRAIN feedback | `085602a9d5976dadedf5ed76839aa4758aa57f02` |
| Raw decisions and source receipts before scoring | `a7c64e721cdc3d762482e99b9549b9e3a7f2a361` |

The separate saved-record arithmetic agreed on all 60 condition/arm net
means and checked 71 artifact hashes, the reconstructed sensor priors and
the paid donor chains. Source provenance is stored once per scenario and
reused across seeds. This is a within-team check. The full roadmap, formal
scientific admission and the inclusive 2,000-line objective remain open.

## Next G4 experiment

Freeze a goal-dependent sender comparison on a fresh communication family.
Give the speaker two observed attributes and a single-symbol bandwidth limit.
Cross which attribute matters with the receiver's goal, hold physical state
and menu fixed, and learn what to send from terminal reward. Compare the
learned sender against silence, a fixed attribute, shuffled messages and a
matched shortcut channel. Withhold source/goal combinations and record whether
the same observation produces different beneficial messages under changed
goals. Test requests with the computed opportunity cue ablated before giving
the receiver credit for discovering its own information gaps.
