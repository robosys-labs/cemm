# Goal-dependent one-bit communication, study v1

## Question and task

Can a sender learn which of two private observations helps a receiver achieve
a supplied goal when only one bit can be transmitted? Can the receiver decide
when the communication fee is worth paying without the earlier opportunity
flag? The outcome is a bounded sender decision. Full G4 remains open.

The parent is PR #82 commit `f654226c11d22accfa4c161aa5997053f0e5011f`.
[Receiver review](RECEIVER_REVIEW_V1.md) records corrections to its denominators,
wire semantics and verification. All physical tasks use published G3 canonical
forecasts and real archived endpoint payoffs. In each episode two independently
reset scenes have disjoint entity rosters and independent binary calibration
readings. A compound physical action selects the same offered menu index at
both sites. The goal names one site's badge and rewards achieving its archived
G3 target. Every agent has a single decision turn. The learner receives only
the terminal payoff of the selected physical action.

The two badges, target badge, one-bit measurement convention, reward semantics,
independent fair private bits and receiver's native forecast catalogue are
supplied. Goal grounding on the receiver side selects the appropriate physical
forecast matrix. The sender sees both bits, badge placement and the target
badge. It cannot see the selected site index, action ordering, payoffs,
receiver observations, source name or the optimal message. It learns two
coefficients for each of four observed badge-placement/goal combinations from
the signed interaction of explored symbol, individual reading and terminal reward.

The request head sees only its two prior expected action values and the price.
It estimates gross benefit from realized requested and silent outcomes in four
fixed bins of absolute action-value margin; it asks if learned benefit exceeds
cost. Receiving a message selects a hypothetical payoff vector for decision.
The receiver's local observation takes precedence when present. The source's
claim cannot add a physical observation or execute an external action. Potential
claims carry source, both sensor receipt IDs, round identity, time (turn 1),
symbol and policy condition. Each paid delivery retains its actual or synthetic
origin. Dropped and declined deliveries carry no token.

## Fixtures and budgets

Per law, select 12 ordered compound pairs from the TRAIN path-return structure
and 12 from the held-out branch-return structure. Hash ranking and least-used
menu–goal case counts determine selection without predicted accuracy. Sites
can recur across pairs. This is a fresh compound communication task over
opened physical evidence. The two splits have disjoint physical rosters.
There are ten law/seed conditions, NAND and NOR × inherited seeds 7, 11, 23,
37, 53. Physical menu ordering reverses on alternate replicates, outside
the sender's view. No reported count is treated as independent replication.

Each split and condition contains 4,608 rounds. Cross four readings, two badge
placements, two goals, two source groups, three query scenarios and four
replicates per physical pair. W0 appears under both goals. W1 and W2 each
appear with one goal during TRAIN and the opposite goal on challenge. Since
both policies omit source identity this tests invariance built into their
inputs. It cannot demonstrate new source reliability learning. Cheap hidden
and already-known conditions cost 0.05. Costly hidden requests cost 0.75.

In replicates 0/1 the sender explores both wire symbols and always requests.
In replicates 2/3 the fitted sender acts and requesting alternates with silence.
Within each phase the exploration assignment is counterbalanced across source
group at fixed receiver action ordering. Report all 46,080 chosen-action TRAIN
outcomes. Freeze all sender and requester weights before challenge collection.
No research retries, tuning or denominator changes after challenge opening.

## Prospective gates

Compare the trained pair to free silence, matched paid suppression, random
bits, shuffled messages, fixed first/second readings and interpreting the
sender's bit directly as the physical action index. A deterministic same-input
goal-aware router sends the reading whose badge matches the target. All
controls except free silence use the learned request schedule. Shuffling is
a bijection over private states within each case, goal, source, stratum and
replicate. It always flips the irrelevant bit and flips the relevant bit on
half of hidden cases. Known local readings are preserved. Compare also to the
best in hindsight of all 16 fixed two-input Boolean codebooks, separately
optimizable by badge placement, using the same physical decoder and requests.

For every law and seed require all of the following.

- Net utility per episode exceeds every ordinary control by strictly more
  than 0.03 and is within 0.005 of, or above, the public goal-aware router.
  Require the same strictly positive 0.03 margin over the goal-blind codebook
  envelope, overall and in the crossed-source subset.
- Cheap hidden request and goal-success rates reach at least 80%. Known and
  costly request rates are at most 20%. Each held-out source/goal cell reaches
  the 80% thresholds on hidden trials and exceeds the stronger fixed-site
  sender by strictly more than 0.03 net utility.
- Changing only the relevant private reading changes at least 80% of potential
  messages; changing only the irrelevant one changes at most 20%. With source
  W0 and both readings fixed, changing only the goal changes at least 40% of
  messages. Both equal and unequal private readings are included.

All gates passing yields KEEP_BOUNDED_SENDER. Any completed numerical failure
yields REVISE. An incomplete run has no scientific decision. Report per-arm
calibration, costs and adverse choice changes. This study does not test
emergent symbols, an unrestricted vocabulary, new badge meanings, or learned
receiver grounding. The four supported combinations are represented directly.

## Same-task ablation of the earlier receiver

A separate descriptive comparison reuses PR #82's opened bank. Freeze its
action head. Fit three request heads on the very same phase-two selected
actions, randomized request decisions and gross outcomes. The first must
reproduce the published original parameter table, decisions, success counts
and costs. The second receives no opportunity cue. The third replaces that
cue with the new public four-bin action-value margin. Source, age and focus
remain available. Reuse all original potential replies even on rounds where
the earlier receiver declined. Retain all three decisions for all 34,560
rounds and report gains, harms and differences in fees. These exploratory
comparisons cannot upgrade the original frozen receiver decision.

## Publication

Prepare all source, runtime, pair catalogues and target identities before
fitting. Publish the fit and selected feedback before collecting. Publish
the raw records before scoring. Run the sender_run module with `prepare`,
`fit`, `raw`, and `scored` in that order. The last three stages require a
clean checkout at the published branch tip and are write-once. The registered
scorer separately validates full factorial coverage, physical action order,
public information and each intervention's payoff calculation from saved data.
