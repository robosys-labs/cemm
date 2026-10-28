# Proposed full-sensor controlled study

**Status: reviewable proposal; not frozen, not run, not a G1 test.** The
opened PR43 and PR44 results motivated these choices. This plan must be
independently reviewed, converted to a versioned, hash-locked protocol and
committed before the proposed fits or scored outputs. Any defect found after
results requires a new protocol and an explicit revision, not silent edits.

## Question and controls

On the opened public fixture, how do complete target supervision and
consistent training-ID permutations affect the flat learner when every arm
receives the same complete sensor histories? A 2 × 2 design separates those
interventions. They do not isolate persistence learning or establish an
architectural advantage; the full sensor histories themselves expose more
information than the original PR43 partial-feedback curriculum.

| Factor | Reference | Treatment |
|---|---|---|
| Flat loss targets | Mask each post-action label to the original PR43 visibility | Use all three measured labels |
| Training IDs | Repeat each unrenamed history six times | Apply all six consistent bijections of its three existing IDs |

Keep the flat model's *inputs* complete in both target-mask arms. Construct
its input tensors and valid-event mask once per ID arm; make a separate target
tensor with only the loss labels masked. The mask must never remove readings
from the input history or alter the evaluator, feedback or another model's
inputs. Assert identical input tensors, action sequence, anchor, ordering and
full realized feedback between the two target-mask arms. The two ID arms are
consistently renamed views of the same physical histories; their bytewise
records and flat tensors will differ, but inverse mapping must recover the
same history exactly. Structured and flat consumers within each arm must
receive identical copied action and sensor records, including full feedback.

The reference label mask follows the original sensor selection, transformed
with the same ID bijection: after the two contacts and inserted observe it
retains A and B; after each set it retains A. This is a **loss-mask
intervention**, not a participant-only sensor intervention: later flat inputs
still contain the complete delivered feedback. Full targets are actual
noiseless sensor readings, never imputed hidden bits or evaluator gold.

## Fixed public data and budgets for review

Use the same public one-pair episodes as PR43: blocks 0 and 1, 32 cases each,
with the same IDs, physical initial states, values and five actions. Each
block has its own shared three-ID set. The actions are
`contact(A,B), observe(), contact(B,A), set(A,x), set(A,y)`. The inserted
observe is an evaluator no-op. A full-sensor fixture directly measures all
three anchor IDs after every action; it does not replace a missing bit using
persistence. No evaluator index, hidden orientation, state or future record
is passed to a learner. This public in-process fixture is not a custody or
isolation boundary.

Traverse block, case and then permutation index in fixed ascending order. For
augmentation enumerate all permutations of the sorted three anchor IDs in
lexicographic order and apply each bijection to every ID in the episode,
preserving measurement order, action roles, values and timestamps. For the
reference use six exact copies of the original record in the corresponding
positions. Check bijection and inverse round-trip before fitting. There is no
outcome-dependent sampling, and each physical episode appears six times in
both ID arms. These 384 records are repeated views of 64 constructed cases,
not independent worlds.

Each arm has 384 episode records, 1,920 actions and 1,152 initial anchor bits.
Full feedback contains 5,760 observed bits in every arm. The flat objective
uses 3,072 target bits with the reference loss mask or 5,760 with full targets;
all 1,920 events retain at least one target. Each structured arm receives the
same realized complete histories and, under the existing local extractor,
768 contact and 768 set tuples; observe targets are not part of its loss.
Assert these counts from generated records, retain hashes of unmasked and
masked tensors, and stop on mismatches. Target bits and structured samples
are different effective supervision, so equal episode or update counts do
not imply equal information or equal work.

For each arm use seeds 7, 11, 23, 37 and 53; 200 full-batch Adam updates per
learner, learning rate 0.02, one CPU thread, no calibration, and the existing
PR43 structured and flat objectives. Fix optimizer settings, float types and
software versions in the locked protocol. Run all arms, including failures;
do not select a seed or tune on the opened evaluation cases. No-change,
local-event-with-persistence and literal-ID full-history memorization are
controls, with exact-memory training and query coverage reported explicitly.
The full-history control sees complete sensor targets in every arm; it is not
an equal-objective learner and may abstain on unseen IDs or prefixes. The
opened evaluation has disjoint IDs, so its coverage may be zero; complete
training observations alone do not make it a strong memorization control.

Before fitting, verify that a given seed's initial flat weight fingerprint is
identical across all four arms and that the ordered structured sample tensors
and episode grouping are equal across arms. Fail on a mismatch. This does
not make flat and structured losses, optimization or compute equivalent.

Report preprocessing and fit wall/CPU time, process-wide peak RSS, parameter and active
feature counts, updates, event/bit counts and callback latency for each arm
and model. Fixed updates and examples are **not matched compute**. Run on the
same host where feasible, record CPU, software and determinism settings, and
retain weights or sufficient checkpoints in addition to fingerprints. Report
differences across hosts as separate refits unless weight and prediction
identity is verified; do not assume bitwise reproducibility.

## Opened evaluation and interpretation

Score the same 64 public two-pair cases previously opened in PR43, with every
one of the six bijections applied consistently per case; this yields 384
related views and 1,920 action queries per model and seed. The proposed
evaluation must measure all three IDs after each action using the actual
evaluator sensor, retaining the original PR43 reading order and appending
previously unobserved IDs. Its full-feedback fixture does not yet exist and
must be implemented and reviewed before use. Full-feedback scores cannot be
directly compared with PR43's partial-feedback scores, because the histories
and information differ. Use the same realized evaluation histories for all
models and finish fitting all arms and controls before any evaluation score.
Forecast before feedback and finish all arms' and permutations' replays for
the case before reading evaluator truth. Map joint worlds back to physical IDs
before comparing distributions. Select each model's MAP first in sorted
*renamed* ID order, with the lexicographically smallest tuple breaking exact
ties, then map that selected world back to physical IDs. Report per-case and
per-action original and renamed predictions, exact complete-world MAP,
coverage and abstentions, categorical Brier, represented-zero and uncapped
joint log loss, plus total variation and tie-sensitive MAP changes. Score
contact/set and observe separately and preserve every seed and failure.

For a seed, ID arm `a` and target mask `m`, define the primary descriptive
scalar `A(a,m)` as flat-model correct complete-world MAP forecasts divided by
**1,536** total contact/set queries (64 cases × 6 ID views × 4 actions).
Report observe separately. Report coverage and abstentions alongside this
per-query value; an abstention is not a zero-probability forecast. Report
every seed separately, and show both within-ID-arm target-mask contrasts and
within-mask ID-augmentation contrasts. The interaction is
`[A(augmented,full) - A(augmented,masked)] -
[A(repeated,full) - A(repeated,masked)]`. Report structured and control
results separately without treating their objectives, biases or compute as
matched, or assuming that the flat-only mask changes their training. These contrasts
describe repeatedly used public cases; no IID confidence intervals or
held-out claims follow. All models still receive actual feedback between
one-step forecasts, so these are not free-running trajectories. Balanced ID
views do not isolate an input column from an output coordinate or prove a
mechanism for the original performance gap.

An independently authored and independently held challenge, genuinely
withheld composition families, matched resource comparisons and provenance
remain prerequisites for G1. New block numbers, hashes or deterministic
seeds in this public generator do not create independence or blind custody.
