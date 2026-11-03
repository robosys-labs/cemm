# G4 transfer to unseen sender bindings

**KEEP_UNSEEN_BINDING.** The 16-coefficient sender selected the requested
site's reading on unseen pairings of familiar badges and on pairs of entirely
new badges. All 20 registered checks passed separately in all 20
partition × law × seed cells. Both partitions produced the same candidate
totals. Each had 26,880 successes, 7,680 requests and 0.8625 mean net utility
over 30,720 rounds.

| Policy or intervention | Goals achieved | Requests | Net utility per round |
|---|---:|---:|---:|
| Reward-trained sender and requester | 53,760 | 15,360 | 0.8625 |
| Supplied goal-aware router | 53,760 | 15,360 | 0.8625 |
| Same sender with margin-only requester | 53,760 | 30,720 | 0.8500 |
| Strongest goal-blind code by context | 49,920 | 15,360 | 0.8000 |
| Raw-coordinate dot product | 49,920 | 15,360 | 0.8000 |
| Free silence | 46,080 | 0 | 0.7500 |
| Lookup, legacy sender, shuffled or paid silence, each | 46,080 | 15,360 | 0.7375 |
| Random delivery | 45,920 | 15,360 | 0.7349 |

Holding the other reading fixed, changing the relevant reading changed all
7,680 paired hidden messages. Changing the irrelevant reading changed none.
Switching the goal changed all 3,840 paired messages with opposing readings.
The receiver asked on all 15,360 cheap hidden rounds and on zero known, costly
or indifferent rounds. Including the best available action's prior utility in
the request head saved 768 cost units over using the action margin alone, with
identical gross success.

All 7,680 missed goals occurred on costly rounds, where a reply cost 0.75
for a mean gross gain of 0.50. For example, on NAND/7 round
`17e6ff3bfe934e8e1a60bcd3ba439fc1d420817afc41096d40473ff45e181722`,
the receiver declined the request, gave its chosen action probability
0.498884 and earned zero. Mean selected-action Brier score was 0.062872.
[Registered per-condition results](results/transfer-binding-v1/scored/decision.json)

## How much did rewards explain?

A post hoc sender used only the unordered pair of site vectors and the
displayed goal vector from TRAIN. For each of the eight familiar goal vectors,
exactly one site appeared in every pair containing that goal. These eight
correspondences determine the linear map between the goal and site views.
The control used that map to select a site, then sent its reading under the
same supplied one-bit convention. It matched every one of the 61,440 emitted
bits and every final action with the archived reward-trained requester.

The prospective result establishes transfer within this encoding. Both terminal
rewards and the training inputs alone suffice to recover the sender's routing
rule here. The receiver still used rewards to fit its request policy. The
lookup control fell back on every held input, and the raw-coordinate control
tied on every fresh badge pair. Neither comparison measures the benefit of
rewards over learning the input structure.
[Control implementation](transfer_cooccurrence_review.py) ·
[Per-condition control results](results/transfer-binding-v1/cooccurrence.json)

The 61,440 evaluations cover 12,288 distinct scenario IDs across the two laws.
Five inherited model seeds revisit each ID. All ten fits yield the same sender
matrix, with four nonzero coefficients, and the two challenge partitions reuse
the same 24 law-scoped physical pairs. Each partition has 128 sender-visible
inputs absent from TRAIN. All registered badge pairs differ in two of four
coordinates. In a separate post-score check, the fitted sender also routed
correctly on all 1,920 possible inputs over this finite alphabet, including
1,408 outside every registered split. That check exercised the sender alone.

## Verification

The [protocol and input commitments](https://github.com/robosys-labs/cemm/commit/6873d9b3aaabc4ccade524ded128d4764b8f9360)
preceded fitting. All [checkpoints and observed TRAIN rewards](https://github.com/robosys-labs/cemm/commit/423ae3a5842fd59aefa9c2ba1d0befc8f142a3a7)
preceded collection. The [complete raw bank](https://github.com/robosys-labs/cemm/commit/9de76d4fd0124b21cb854cff1b98a9ae9c6b1948)
was published before the [registered decision](https://github.com/robosys-labs/cemm/commit/617631c7272d87eb92b011dfee10a3d0c4bca0d9).

A separate same-team implementation reconstructed all 61,440 observed TRAIN
rewards and all 614,400 held-out arm choices from the physical catalogues.
All 400 registered checks, 20 goal-blind envelopes, 200 arm summaries and 31
stage-output hashes reproduced. A direct SVD refit agreed with the published
sender within 3.34 × 10⁻¹⁶ per coefficient.
[Verification receipt](results/transfer-binding-v1/review.json)

The fit, raw collection and scoring together used 29.85 CPU seconds. The
largest reported peak RSS was 126,052 KiB. A warmed, single-process timing
of sender selection, request and action on the 6,144 NAND/7 rounds took
5.05 μs median and 8.51 μs p95 on the study host. This timing excludes the
native forecast computation, serialization and audit.

## Next G4 test

Vary which of two conflicting sources predicts the physical outcome while
holding the visible report stream, menus and explored actions identical.
Fit source reliability only from the observed consequences. A learner that
ignores outcomes must face the same evidence in both regimes and make the
same choice, even when the correct choices differ. Counterbalance source
identity and arrival order, then test delayed and off-focus reports at the
same query cost. Preserve both claims separately from physical evidence.

A [TRAIN-only feasibility check](conflict_preflight.py) constructed 7,680
matched twins from 19 physical menus. On 15,360 target decisions, the optimal
outcome-blind history rule achieved 50%. Removing source attribution also
capped success at 50%, even with the earlier outcome. A reference rule with
both inputs reached 100%. This establishes that the proposed fixture can
distinguish the two mechanisms. Fitting a learner and testing it on a sealed
challenge are subsequent work.
[Preflight counts](results/conflict-preflight-v1.json)

Full G4, formal scientific admission and the inclusive 2,000-line objective
remain open.
