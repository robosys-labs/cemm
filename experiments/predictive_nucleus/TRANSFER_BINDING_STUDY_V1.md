# G4 transfer to unseen sender bindings

## Hypothesis

Can one learned set of parameters route the reading of the goal-relevant
site when the complete badge binding is unseen, including when both badges
are new? The earlier finite sender had seen all sixteen of its possible
inputs. This study compares held-out bindings of familiar badges and bindings
of entirely fresh badges. It also tests whether the receiver avoids buying
information when either physical action already earns full utility.

## What is supplied and learned

Use the immutable PR #83 parent at `78e1dcd22f31147dc5433420185d6f3e9ae17245`.
Both sites supply independently reset physical tasks, private binary readings,
different badge identities and frozen G3 native action values. Under a regular
goal the reward is one if the action achieves the named site's native endpoint.
The indifferent goal pays one for either action. Goal grounding in the receiver
and exact identity in the evaluator are supplied. Every intervention has one
physical action and at most one costly bit. Claims carry source, original
round/turn and both witness IDs, separately from physical evidence.

Badge features are four bipolar coordinates. A goal with site representation
`(a,b,c,d)` is shown to the sender as `(-b,a,-d,c)`. Dotting the goal with
its own site's untransformed vector gives zero for every badge. The shared
sender gets both site vectors, that transformed goal and both readings.
It sees no canonical identity, matched-site index, stratum, menu order,
candidate action or counterfactual payoff. The one-bit measurement convention
and the architecture's ability to choose between two measurements are supplied.

Each TRAIN example provides its explored symbol and the realized binary reward
for the one receiver action taken. Fit a 4×4 matrix W on the contrast between
the two sites. Each design row is the outer product of site-vector difference
and goal vector times the reading difference. The response is the product of
the signed emitted bit and signed terminal reward. Solve ridge least squares
with penalty 1e-6 on the unnormalized Gram matrix in float64, one BLAS thread.
At deployment compare the two bilinear site scores and send the winning site's
reading. Equal scores emit their shared reading if they agree and zero otherwise.
A fixed identity matrix, an untrained geometric control, and a literal
comparison with the evaluator's privileged goal mapping are kept distinct.
This design tests a shared cross-view relationship in a supplied feature
space. General equality over arbitrary opaque symbols is outside its scope.

## Prospective split and budgets

Each law uses 12 physical TRAIN pairs and 12 held physical pairs from the
published parent. The held pairs are reused for both challenge partitions.
The eight TRAIN badges have even parity. The 16 unordered TRAIN pairings use
four preassigned XOR masks. One challenge partition uses eight disjoint
pairings of the same badges, with masks 10 and 12. The other uses eight
pairings of the eight odd-parity badges, with masks 3 and 12. The assignment
schedule balances badge frequency and reverses the two site positions.
Register exact input-sequence SHA256s by split, law and seed before fitting.
The full TRAIN contrast matrix must have rank sixteen. Each held partition
is a restricted family. Physical tapes and entity rosters cannot cross splits.

Across all TRAIN physical assignments there are 256 distinct sender-visible
patterns. Each held partition has 128. Require zero TRAIN overlap in complete
encoded sender inputs and unordered badge pairs. Known versus fresh badge
membership is checked separately. Cross both goal positions, every private
bit pair, cheap hidden/known, costly hidden, indifferent goals and four
replicates. TRAIN has 6,144 episodes per law/seed, and challenge has 3,072 per
law/seed in each partition. NAND, NOR and seeds 7/11/23/37/53 yield ten
dependent conditions. The two TRAIN exploration choices share the same
physical menu order within each contrasted pair. The first two replicates
always ask and counterbalance emitted bits; the second two counterbalance
requests and silence using the fitted sender. Archive every chosen payoff.

The decision to ask compares empirical gross benefit with the 0.05 or 0.75
cost. One head estimates that benefit in four bins of the absolute difference
between prior action utilities. The candidate adds a four-bin maximum prior
utility coordinate, available before requesting. Both heads use exactly the
same observed requested/silent outcomes and default to silence without support.
No explicit opportunity bit or goal-indifference label is fed to either head.

## Controls and registered decision

Nine comparison arms accompany the learned sender. A same-input exact lookup
learns token rewards with a global fallback learned on TRAIN. The parent
finite sender has public registrations for exactly two legacy badges (0,3)
and uses token zero outside its domain. Raw dot product sees the same two
perceptual views. The goal-aware router has the correct identity mapping.
Other controls are paid suppression, free silence, independent random
delivery, a fixed-point-free donor shuffle and the fitted margin-only query
head with the learned sender. Interventions other than the margin-only head
and free silence share the candidate's question schedule. Independently score
all 16 fixed two-bit Boolean channels per task and oriented badge pair and
retain the highest achieved net utility without supplying a goal to the code.

For each partition at each law/seed require all registered checks:

- Net gain strictly above 0.03 versus literal lookup, legacy, raw dot,
  suppression, random, shuffled, free silence and the hindsight goal-blind
  envelope. The learned sender must be within 0.005 of, or above, the explicit
  goal-aware router.
- Net gain strictly above 0.005 over the margin-only request head, with zero
  gross-success losses. Hidden low-cost asks and goal successes must each
  reach 80%. Known, costly and indifferent request rates must each be at most 20%.
- On hidden cases, changing only the relevant reading switches the emitted bit
  at least 80% of the time. Changing only the irrelevant reading switches at
  most 20%. Changing only the target site switches the bit at least 40% overall
  and at least 80% when readings disagree. On disagreeing readings the emitted
  value must match the relevant reading at least 80% of the time.

A complete pass yields KEEP_UNSEEN_BINDING. A complete numerical failure
yields REVISE. Failed or unsealed execution cannot support a transfer decision.
Save pointwise outcomes, adverse examples, selected-action Brier score,
latency/cost scope, source attribution and input denominator. Same-team record
replay is additional verification. Full G4, the inclusive 2,000-line objective,
formal admission and production integration remain open. The present source
is a single reliable W0 with immediate delivery; broader conflict, ambiguous
intent and delays remain on the roadmap.

## Execution

Run `OPENBLAS_NUM_THREADS=1 python -m experiments.predictive_nucleus.transfer_run`
with `prepare`, `fit`, `raw` and `scored` respectively. Publish the exact
source/fixture commitment, then fitted checkpoints, then the raw bank before
their dependent stages. Each research stage consumes a write-once attempt.
