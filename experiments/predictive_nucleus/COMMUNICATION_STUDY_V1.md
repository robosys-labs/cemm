# G4 receiver study v1

## Question

Can one receiver learn when to pay for a private observation and how to use the
attributed reply to choose a physical action? Success retains a bounded
receiver capability. Sender strategy, natural-language communication, broader
source conflict, full G4 and formal scientific admission remain open.

## Task and information

The parent is G3 v3 at `a0ec72982c9f2b1808564c88da46b1e2aa316fb6`.
Use the archived grounded decoder and native endpoint distributions for seeds
7, 11, 23, 37 and 53 with NAND and NOR. Each candidate physical action has an
exact G3 utterance. Compute the probability assigned to the externally supplied
target world for each action under each of two possible physical histories.
The participant bits specify the goal and other entities must be preserved
relative to their own history. Settlement uses the recorded physical endpoint.

The environment offers all two-action menus in established calibration contexts
where the two private readings switch which action achieves the goal. Eligibility
uses physical endpoints only. Equal prior odds on these two histories are
supplied. The receiver gets a menu, a goal, its available sensor evidence,
source metadata, cost and the two model-conditioned possible histories.
The speaker can see the first native calibration reading. One physical choice is
required in every arm. Completed-action utility is 0 or 1 and requesting incurs
an additional 0.05, or 0.75 in the costly stratum.

Path-return tasks supply receiver TRAIN, 63 NAND and 66 NOR menus. Branch-return
tasks supply the held-out receiver challenge, 66 NAND and 30 NOR menus; the
two families have disjoint entity rosters. All parent physical tapes and
forecasts have previously been opened. The new challenge consists of the
communication tasks, fixed split, and prospective policy evaluation. Five
inherited model seeds, both histories, repeated interventions and related
menus are dependent measurements. No independent-trial inference is planned.

## Supplied and learned

The two wire symbols denote sensor readings by convention. The source, age,
focus match, effective query cost and goal are public. A speaker follows the
fixed reporting channel and receives no optimization. Source A reports truthfully
in the useful condition; source B systematically inverts the reading in the
misleading condition. This tests whether outcome feedback can teach the receiver
to interpret a source. It does not establish strategic deceptive-speech detection.

A claim carries its own attribution and evidence identity and can inform a
hypothetical action value. Only physical receipts restrict the sensor support.
Unresolved messages have no decoded value. Repeated appearances of the same
receipt add no independent evidence. Known and contradictory-report episodes
already supply the receiver with the physical reading. The irrelevant external
goal awards unit utility for completing either offered action. Stale and
out-of-focus sources report independent synthetic probes with their own evidence identities. An unknown payload is
unresolvable only after opening the reply. A changed supplied goal can switch
the rewarded action for the same surface menu.

For each law and inherited seed, fit a signed source correction to the terminal
reward for the single explored action with ridge 1/16 and no intercept. The
gross action values use the change from the sensor-only estimate under the
claimed reading. The correction varies with source, current/old age and focus
match. The public opportunity flag checks disagreement of best actions among
physically supported possibilities. A second head estimates the gross benefit
of a request by comparing realized requested and silent rewards in each public
stratum. Use a strict gain-over-cost threshold, default silence without support,
clip action reward estimates to [0,1], and break action ties toward index zero.
Neither head receives intent, truthfulness, the hidden reading, the evaluator
stratum, an oracle payoff table or the rewards of unchosen actions.

## Frozen budget and controls

Each menu has nine strata × two equiprobable private histories × four
replicates. In TRAIN the first two replicates request and counterbalance
the selected physical action; the last two counterbalance requesting versus
silence with the action head fixed. This yields 4,536 NAND and 4,752 NOR
terminal rewards per seed. The fitted parameters for each condition must be
published before collecting its held-out records. No challenge-driven restart
or parameter selection is permitted.

For each challenge episode the delivered, suppressed, independent-random,
shuffled and literal-trust shortcut arms share the receiver's request decision,
cost, menu and one physical action opportunity. The shuffle permutes deliveries
within a case and stratum while preserving source, public context, marginal
content and donor identity. Free silence makes no request and pays no cost.
The shortcut follows the literal resolved report without estimating source
reliability. All six arms agree when the receiver declines to request. Random
and shuffled replies are interventions on delivery; they are scored against
the original recipient's physical outcome. Keep every trial, including unresolved
messages, wrong choices and regressions.

## Prospective decision

The independent saved-record scorer joins unique round identities to the
published target bank. It requires all 34,560 held-out rounds across ten
conditions and the complete six-arm inventory. The following hold separately
for every law and seed.

- Mean paired net utility gain must be strictly above 0.03 against paid
  suppression, random, shuffled and free silence, and above 0.01 against the
  source-blind shortcut.
- In each of useful and systematically misleading conditions, both request rate
  and goal success must reach 80%.
- Known, irrelevant, costly, contradictory-to-known, stale and shifted-focus
  request rates must each be at most 20%. Unknown payload results are descriptive
  because the payload is unavailable when deciding whether to pay.
- Report action changes, opposing gains/losses and examples, per-arm net utility,
  chosen-action reward Brier and 10-bin ECE. Calibration is diagnostic.
  A complete pass yields `KEEP_BOUNDED_RECEIVER`. A failed numerical gate yields
  `REVISE`. Incomplete or unsealed evidence cannot support either decision.

## Execution and limits

Run the communication runner's `prepare` stage and the communication freeze
module to bind source, runtime, parent objects and the prepared bank. Publish
them to the study branch. Run `fit`, publish actual weights and feedback, run
`collect`, publish the raw records, then run `score`. Each stage is exclusive
and records its input commit. Synthetic tests and inspection of opened G3
records are permitted before publication. Training and evaluation use the
frozen Python standard-library runtime, without invoking a new neural training
or inference run. Retain elapsed time, CPU time, per-round decision timing
and raw bytes. All potential source and delivery receipts are retained once per
law under seed 7. Each seed records the actual request and action by episode ID. This is a same-team bounded comparison on a constructed
information gap with supplied physical candidate models, fixed source
conventions, and a fixed clear-text sensor code. Production integration and
the inclusive 2,000-line objective remain open.
