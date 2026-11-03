# G4 matched source conventions

Can a receiver learn from selected physical outcomes which source to use on
the next menu, carry that convention to unfamiliar attributed sources and
ask for verification when the observed history leaves a real information gap?
This is a bounded, two-turn study. The preceding [single-source shortcut](conflict_preflight.py)
is possible when the two reports always oppose each other. Both reports are
varied independently here.

## Paired experiment

Use PR #84 at `dfb62319f7e650997529aeeada6635840455d283`. Reuse the hash-bound
G3 path-return training and branch-return challenge physical pairs. Their
entities, site IDs, physical tape IDs, witness IDs and structure lineages
must be disjoint within each law across splits. The parent physical traces
were opened in earlier research. The fitted receiver sees this communication
schedule for the first time. Independently authored physical worlds are outside
the claim.

For each pair, two named sources report on one site during calibration and
the other during the target turn. Use distinct opaque identities per pair.
Factor both sites as calibration site, both probe actions, all four pairs
of calibration reports, all four pairs of target reports, each possible
initially reliable source, and both arrival orders at each turn. The report
of the reliable source equals the physical reading. The other report ranges
independently over both bits. Neither source receives a reliability label.
There are 6,144 histories per physical law/seed/split, including the
unidentifiable twins. The observed probe payoff is shared between conventions.
In one training environment the initially reliable source stays reliable.
In the other the opposite source is reliable at the target. Both environments
receive the identical observed inputs, earlier payoffs and explored target
actions in the same order. Only the selected target outcomes can teach the
difference. The explored target action is balanced by target-report order.
Each fit sees only that one realized target reward per history.

Run NAND and NOR with inherited seeds 7, 11, 23, 37 and 53. Each physical
pair has two independently reset disjoint rosters. G3 receives actual earlier
observations and the current surface utterance. Redact the final endpoint
before running the frozen language encoder and native world model. Batch
identical physical prefixes within a stage, compute the full-world
goal probabilities live, and require absolute parity within 1e-10 and
identical physical action rankings against the parent archive. Keep native
sensor evidence separate from attributed claims. The receiver receives only
conditional action values, opaque source labels and reports, the selected
probe action and its payoff. It sees no case, regime, law or convention IDs,
target truth or unchosen training payoff.

## Learners and controls

For each source, compute support for the observed calibration reward from
the public native action forecast under that source's report. A shared
logistic unit learns the slope on the difference between the two supports.
Its output mixes the two target reports into a probability for the target
bit. Initialize the slope at zero. Fit with 128 full-batch float64 updates
at learning rate 4 on selected-action Bernoulli loss. Clip the slope to
[-16,16] and the derivative denominator probabilities to [1e-12,1-1e-12].
The one-bit empirical learner chooses the sign on that same support
difference by minimizing TRAIN selected-action squared error. The likelihood
feature, two-source mixture, physical sensor convention and decision rule
are supplied. There is no learned language of questions or unrestricted
reputation memory in this study.

Record the unassisted choice first. A perfect physical verification can then
reveal the actual target reading at fee 0.05 or 0.75, or be unavailable.
Buy it only when expected improvement in the best physical action exceeds
its price. The query rule is supplied, driven by the fitted beliefs.
Evaluate all three prices on the same history. Keep the unassisted choice,
belief, request and final physical action for each arm and price.

Compare the learned receiver with the empirical receiver, the opposite
convention's fit, and the two fixed named witnesses individually. Each fixed
witness gets its own calibration report, earlier outcome and target report,
plus the fitted empirical convention. Its probability of being the reliable
calibration source is 2/3 after a correct single report or zero after an
incorrect one. Also compare equal weighting of the two current reports and
free silence with neither source's information. Paid suppression and shuffled
verification reuse the learned request schedule. Shuffle donors within each
physical pair and information stratum with a fixed-point-free permutation
that changes half of the verified bits. Each claim is bound to source,
turn and physical menu through the frozen generator and paired input hash.
The simulator's true sensor receipt and physical endpoints are reconstructible
from the immutable parent and schedule. They never enter the receiver.

## Decision registered before fitting

Apply gates in **every** physical law/seed and in **both** conventions. On
informative calibration with conflicting target reports require at least
95% unassisted accuracy and at least 95% of matched pairs correct on
both opposite choices. The crossed fit must score at most 10% there.
Equal weighting must score 50%. The exact best-choice ceiling must be 50%
on those critical cases with earlier payoff erased, with source identities
erased, and over the two matched environments if the same choice is made
without knowing which target outcomes trained the policy. Target agreement must
produce at least 95% correct actions. When calibration reports agree and
current ones disagree, require exactly 50% unassisted correctness and
maximum absolute deviation of the bit probability from 0.5 of at most 0.1.
On that stratum require at least 95% cheap requests and 95% cheap final
success. Allow zero requests on resolved, costly or unavailable cases.
Across the complete target factorial, each fixed source must score at most
75% before verification, with learned pre-verification gain greater than
five percentage points. Require net gain above 0.03 against free silence,
paid suppression and shuffled verification over the three prices, and
mean net no more than 0.005 below the empirical learner at each price and
overall. Report bit Brier scores, misses, denominators and all failed checks.
An exact tie on every pre-choice, request and final choice retains the
one-bit empirical mechanism for this task.

All gates passing yields KEEP_MATCHED_CONFLICT and permits bounded G5
development. Any numerical failure yields REVISE_MATCHED_CONFLICT. A failed
or unsealed run yields no scientific decision. Report chronological order
separately from report age and changed referent: only arrival order and
movement to a second designated site are varied here. Broader adverse-message
conditions, formal independent admission, durable correction, performance
at scale and the inclusive 2,000-line objective remain open.

Run `python -m experiments.predictive_nucleus.conflict_run` with
`prepare`, `fit`, `raw` and `scored` in sequence, setting OpenBLAS, OMP and
MKL thread counts to one. Publish the freeze, actual TRAIN checkpoints and
feedback, and complete raw records in separate commits before their dependent
stages. All three research stages are write-once. The external verifier may
reconstruct the result from sealed records. It cannot change the thresholds.
