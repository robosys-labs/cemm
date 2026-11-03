# G4 sender v1 decision

**KEEP_BOUNDED_SENDER.** All 230 registered checks passed across ten law/seed
conditions. The learned sender and requester achieved 38,400 goals in 46,080
held-out rounds with 15,360 queries. The 768 units spent on communication
bought 7,680 additional successes over free silence, for a net gain of 6,912.
A hand-coded sender given the same observations and the goal-routing rule
matched the trained pair on every round.

| Channel | Successful goals | Requests | Net utility per round |
|---|---:|---:|---:|
| Learned sender | 38,400 | 15,360 | 0.816667 |
| Supplied goal-aware router | 38,400 | 15,360 | 0.816667 |
| First or second fixed reading, each | 34,560 | 15,360 | 0.733333 |
| Best goal-blind codebook by badge placement | 34,560 | 15,360 | 0.733333 |
| Free silence | 30,720 | 0 | 0.666667 |
| Matched paid suppression, shuffled delivery or direct action code, each | 30,720 | 15,360 | 0.650000 |
| Independent random wire bit | 30,595 | 15,360 | 0.647287 |

Holding goal, source, menu and the other reading fixed, changing the relevant
private bit changed all 7,680 paired hidden messages. Changing the irrelevant
bit changed zero of 7,680. Holding source W0 and both readings fixed, changing
only the target badge changed 5,760 of 11,520 potential messages over all
cost/knowledge conditions. Exactly half of the paired private readings agreed.

The requester bought all 15,360 cheap hidden replies and succeeded every time.
It declined all 15,360 known queries and still succeeded. All 7,680 failures
occurred on costly hidden rounds. Its gross success rate there was 50%, and
the potential gain of 0.5 was below the fee of 0.75.

## What transferred

The sender fitted eight coefficients, two per badge-placement/goal cell, using
terminal rewards. Each requester fitted two occupied action-margin bins. TRAIN
and challenge have disjoint physical rosters and sensor receipt identities.
The 24 held-out compound pairs use 48 menu–goal cases drawn from 38 distinct
law-scoped physical menus. The 9,216 distinct scheduled episodes are reused
across five inherited model seeds. These are dependent evaluations.

**All 16 sender-visible input patterns had already appeared in TRAIN.** The
result establishes reward-learning this finite selection rule and carrying it
across different physical tasks and action orderings. It does not establish
generalization to unseen badge identities or bindings. The receiver's badge
matching, one-bit convention and physical forecast interpretation were supplied.
The held-out source/goal cells also use a source-blind policy by construction.
No new source reliability, emergent language or production authority follows.

## Same-task receiver cue ablation

On the original 34,560 PR #82 rounds, identical phase-two training histories
and the same frozen action policy gave the following results.

| Request inputs | Requests | Goals achieved | Net utility per round |
|---|---:|---:|---:|
| Original opportunity bit plus source metadata | 11,520 | 26,880 | 0.761111 |
| Source metadata alone | 23,040 | 26,880 | 0.744444 |
| Source metadata plus four-bin action-value margin | 15,360 | 26,880 | 0.755556 |

Removing the opportunity bit cost an extra 576 units. The public margin
recovered 384 units by avoiding queries on physically known and known-conflict
cases. It still bought every irrelevant reply, costing 192 units beyond the
original. On an indifferent goal both actions have utility one; on an ambiguous
useful goal both may be near one half. A margin alone discards this distinction.
The ablation used previously opened evidence and carries no fresh-task claim.

[Per-condition decision, controls and calibration](results/sender-v1/scored/decision.json) ·
[Receiver refits and adverse examples](results/sender-v1/scored/receiver-ablation.json) ·
[Separate same-team record check](results/sender-v1/peer-review.json).

## Publication and next step

The [source and target freeze](https://github.com/robosys-labs/cemm/commit/9947ccae8b65ddded3741dc6a95274806dc88969)
preceded fitting. All [actual checkpoints and TRAIN feedback](https://github.com/robosys-labs/cemm/commit/a7f53a403785b22b492dee75e38cd97d2f2e46fb)
preceded challenge collection. The [raw bank](https://github.com/robosys-labs/cemm/commit/1d0ee96fab6c30edb4544e638669c2de3570b7ff)
preceded scoring. The separate checker reconstructed all ten sender/requester
fits and all 414,720 physical choices from saved records and matched all 90
condition/arm totals. The three formal stages used 37.28 CPU seconds together
and at most 150,420 KiB RSS. Median/p95 time for the entire nine-arm decision
and receipt calculation was 9.224/33.480 microseconds on this host.

G4 remains open. The next prospective task should counterbalance fresh badge
identities, withhold whole sender-visible binding configurations, and compare a
shared selector with this finite table, a same-input exact-match baseline and
the supplied router. A one-bit protocol is sufficient for this comparison.
Keep the old unknown/irrelevant and conflict challenges visible before making
broader claims about when to ask. The 2,000-line objective and formal scientific
admission remain open.
