# Active nucleus — G5 v5 temporal comparison reviewed; rule baseline retained

## Latest G5 v5 — temporal alternatives, bounded development only

[PR #90](https://github.com/robosys-labs/cemm/pull/90) froze a
two-scalar outcome-trained model of persistent change versus transient
observation exceptions. All ten TRAIN fits selected `h=0.5, e=0.1`
from 2,880 selected payoffs per condition. The first challenge collection
was sealed at `0988a525a8c315f4ba245400ab81d438857717d8` before
evaluator scoring. The corrected hosted score and 1,217 software tests
passed. On 9,600 **dependent** decision contexts, cheap verification
reached 9,580 successes with 4,420 requests versus 9,380 successes
with 2,480 requests for the zero-parameter G5 rule. The temporal
candidate buys more correct results, but also **1,940 extra queries**,
failing the declared query-efficiency gate.

All 960 indistinguishable pre-probe pairs abstain under the frozen .95
decision threshold, but the **meaning probabilities are miscalibrated**
on the equal-latent twin bank: mean Brier **0.40845** vs the proper
50/50 benchmark **0.25**. There are 20 confident post-probe mistakes,
zero confident wrong parent/sentinel decisions, and a posthoc
source-integrity finding: law/seed conditions reuse the **same hashed
noise schedule**. The event selection is also explicitly forced
contradictory, which the learner's causal observation model does not
represent. Thus results are not ten independent environments or
formal scientific admission. The first evaluator miscounted PRE
confidence through a tuple index; its original run is retained and
the scorer was repaired without altering sealed raw forecasts or
retraining.

**Disposition: `REVISE_TEMPORAL_CANDIDATE;`
`STOP_CONFOUNDED_FOR_INDEPENDENT_REPLICATION`. Keep the simpler G5 v1
scoped evidence baseline.** No G1–G4 reopened, no production activation,
and no G6 corpus ingestion. [Decision](TEMPORAL_DECISION_V5.md) ·
[full corrected scoring](results/temporal-v5/scored/results.json) ·
[latent calibration](results/temporal-v5/scored/latent-calibration.json) ·
[raw manifest](results/temporal-v5/raw/manifest.json).



## Latest G5 v4 review — stop switch-rate tuning

[PR #89](https://github.com/robosys-labs/cemm/pull/89) extends the
**TRAIN-only** switch grid without modifying the v2 one-scalar posterior,
the v3 balanced objective, accepted physical models or production runtime.
Across all ten law/seed conditions, **nine** have some jointly passing switch
rate. **NOR seed 53 has none** among the 15 registered values; the best case
still commits prematurely on **8/96** epistemically ambiguous pairs. No
sampled rate passes all ten conditions. At the smallest rate, premature
confidence worsens substantially instead of vanishing. Adding one
non-discriminating later-time receipt changes 28 confidence decisions at the
previous rate, exposing dependence on receipt timestamps rather than
independent elapsed-time evidence.

[Decision](REVISION_DECISION_V4.md) ·
[complete rate table](results/revision-v4/train-boundary.json) ·
[hosted 1,211-test CI](https://github.com/robosys-labs/cemm/actions/runs/41811098322).
This is a post-hoc TRAIN diagnostic, not a blind challenge.
**STOP_SWITCH_SWEEPS; KEEP G5 v1 rule; G5 admission NOT_ADMITTED.**
Next: one minimal exception-versus-durable temporal hypothesis learned
from observed payoffs, compared with the v1 rule on genuinely new noisy
scope/reliability families. Retain uncertainty, prior abilities, source
provenance, priced clarification and full adverse-case reporting. No
new parser family or production cutover.



## Latest G5 v3 TRAIN result — seven joint passes, three NOR failures

[PR #88](https://github.com/robosys-labs/cemm/pull/88) freezes a
balanced selected-payoff loss and tests the **unchanged v2 one-scalar
updater** against the retained rule on identical TRAIN histories.
The corrected hosted run passes **1,210 tests** and historical locks.
Previously unjustified confident answers on identical pre-payoff twins
drop **864 → 54 out of 960 pairs**; after the physical probe, the
candidate makes **1,916/1,920** correct confident choices, four abstentions,
zero confident errors and **5,760/5,760** correct confident unrelated
retentions. The simple G5 rule still meets every controlled TRAIN gate.

All ten balanced fits select **the minimum grid rate 0.0025**.
Seven conditions pass every frozen joint gate; NOR seeds 7, 37 and 53
do not. No grid value passes in those three. **REVISE / DO NOT PROMOTE**:
the result supports a training-objective defect but cannot rule out an
untested lower switch rate or justify adding another architecture layer.
[Decision](REVISION_DECISION_V3.md) ·
[complete TRAIN grids](results/revision-v3/train-diagnosis.json).
No G5 v3 held-out challenge was scored; formal admission remains open.



## Latest G5 v2 review — TRAIN-only failure, no challenge opened

[PR #87](https://github.com/robosys-labs/cemm/pull/87) froze a one-scalar,
selected-payoff-trained revision update and published ten fitted values. A
post-fit TRAIN-only matched-prefix audit found premature confident commitments
on **864/960** indistinguishable pairs (nine conditions 96/96, one 0/96).
Each confident pair necessarily misclassifies one of two opposite latent
worlds with the same public evidence. All **1,209** software tests pass, but
the scientific decision is **REVISE_OUTCOME_UPDATE_TRAIN_ONLY**; the G5 v1
scoped rule remains selected. [Decision](REVISION_DECISION_V2.md) ·
[Data](results/revision-v2/train-prefix-audit.json). The new challenge was
not scored, no model was promoted and formal admission remains open.


Updated 2026-11-04. Tracking [#22](https://github.com/robosys-labs/cemm/issues/22),
[PR #85](https://github.com/robosys-labs/cemm/pull/85) and [PR #86](https://github.com/robosys-labs/cemm/pull/86).

## G5 bounded result

[Scoped correction v1](REVISION_DECISION_V1.md) kept a minimal
provenance-preserving two-meaning memory. On 92,160 structured contexts across
both laws and five inherited seeds, 76,800/76,800 resolved meanings and
92,160/92,160 sentinel meanings were retained across simulated episode
resets. With a cheap, useful clarification, final correctness was 95.83%
with 7,680 requests, versus 75% with 46,080 requests when memory was
discarded. All 1,204 hosted invariant tests pass.

The scope hierarchy, two candidate meanings, evidence identity, verifier
flag and query rule are supplied. This is a **rule-based baseline**, not a
learned general belief updater, independent physical validation or formal
G5 completion. The next experiment must learn when evidence warrants a
durable correction, preserve a competing explanation when the outcome is
unidentifiable, and beat or tie this simpler baseline without bloat.

## Latest G4 result

[Matched source conventions](MATCHED_CONFLICT_DECISION_V1.md) passed all 460
registered checks. On 15,360 held-out pairs with the same test inputs and
opposite correct choices, both fitted receivers made both choices correctly
every time. Crossed checkpoints failed every critical choice. At 0.05 the
receiver verified every unresolved case. At 0.75 it preserved uncertainty
and declined. The one-bit outcome-trained empirical policy tied the neural
receiver on every choice and request and is retained at 0.9125 mean net
utility. Live G3 probabilities matched the archive exactly.

[Transfer binding v1](TRANSFER_BINDING_DECISION_V1.md) passed all 400
registered checks on new pairings of familiar badges and on fresh badges.
The pair achieved 53,760/61,440 goals at a mean net utility of 0.8625,
compared with 0.8000 for the strongest goal-blind code and 0.7500 for free
silence. A post hoc sender learned the same routing from TRAIN co-occurrences
alone. With the original requester it reproduced every message and action.
The 61,440 evaluations reuse 12,288 scenarios, and all ten fits have identical
sender weights. The earlier [finite sender](SENDER_DECISION_V1.md) had seen
all 16 of its possible inputs in TRAIN.

G5 development begins with correction of a physically corroborated meaning
and retention across episode resets. The [TRAIN-only revision preflight](revision_preflight.py)
separates a lasting revision from a single exception. A simple dated-evidence
reference transferred all 1,536 post-probe choices without requerying. A
prospective held-out learner must now address scope and preserve an existing
second meaning at matched correctness.

[Receiver review](RECEIVER_REVIEW_V1.md) reproduced every PR #82 decision.
Its 96 menu–goal cases use 63 physical menus, its decoder-unresolved tokens
encode the physical bit, and a supplied source-polarity rule ties the learned
receiver. In a same-task request refit, removing the opportunity cue doubled
queries with identical success. A public margin recovered two thirds of the
extra cost while still buying irrelevant replies.

## Accepted G3 result

[Lexical effect/role v3](EFFECT_ROLE_DECISION_V3.md) is
**DEVELOPMENT_G3_COMPLETE**. All ten NAND/NOR × seed conditions pass every one
of their 73 prospective gates; all six lexical-identity controls pass. All 15
fits and **1,099,200 new-study forecast rows** are retained. The
[full saved-record audit](results/effect-role-saved-audit-v3.json) reproduces the
decision with **42,658,751 checks and zero discrepancies**, without model,
original-scorer or oracle execution. Formal scientific admission remains
**NOT_ADMITTED / false**; this is bounded development completion.

[Headline and adverse changes](results/effect-role-headline-v3.json) ·
[Execution receipt](results/effect-role-execution-v3.json) ·
[Saved decision](results/effect-role-v3/scored/decision.json).

All **61,440/61,440 fresh identifiable world outcomes**, **69,120/69,120 taught
action identities** are correct; **15,360/15,360 supplied-goal choices** are
oracle-optimal, with zero goal regret. Fresh and both opened banks pass the unchanged probability,
bilingual, ambiguity, role-reversal, goal and control gates in every condition.
The largest gated stratum mean KL is 0.046373566253 (limit 0.05); maximum
bilingual TV is 0.002139198003421 (limit 0.05). The 7,680 fresh ambiguous
realizations remain explicit: 3,840 MAP outcomes are correct. They are not
relabeled as identifiable successes or removed from the denominator.

All **131,520 historical exact-world outcomes** remain correct, with zero
world/action MAP changes and zero exact-world regressions. Structural retention
does not imply bit-identical probabilities: 828 pointwise NLL values worsen,
with maximum increase 8.673617379884035e-19. Both opened banks have zero
canonical identifiable-world and taught-action regressions. Their ambiguous
realized-world changes, all pointwise losses and masked-control regressions
remain reported in the decision and headline.

## Accepted mechanism and limits

The entire 88-scalar coordinate language parent remains frozen. Two exact new
identities each learn an effect-family coordinate and role coordinate from
observed endpoints: **92 total language scalars, 88 protected and four trained**.
All four new values begin at zero. The grounded arm receives no gold action or
participant-order labels; the supervised parser alone receives action labels.
The same 16 teaching / 1,152 rehearsal events, five seeds and 256-update recipe
are preserved. All ten acquired native worlds remain frozen at 562 parameters.
Each NAND-fitted language state is evaluated unchanged with NAND and NOR worlds.

Legacy words keep the inherited contact-action support by construction. This is
structural retention with per-identity storage growth, not shared-parameter
continual learning, zero-shot meaning or unrestricted polysemy. Unknown raw
identities remain unresolved. New-word/VOS cells are withheld from TRAIN but
were opened in earlier studies; only v3 participant structures and identities
are fresh. The task supplies action candidates, entity markers, controlled
SVO/OSV/VOS forms and external goals. It does not establish unrestricted language,
natural-language goal parsing, autonomous planning or general calibration.

## Publication and preserved history

Source/data/runtime were published at `2c5cdbe2c6293298545f59e6d8ac002a4c079fdb`,
all actual weights at `66a749218195365e32f3f23c86823bbcedaafdad`, and the sealed
raw bank at `6622c653c9dc521dd4fa3cfc5a6f9cd468ea48e0`, before scoring.
All ten collection shards were published before the next shard; no research
retry occurred. The current bank has 160 traces and 183 raw files in total.

[Effect/role v1](EFFECT_ROLE_DECISION_V1.md) remains
**REVISE_EFFECT_ROLE_GROUNDING** in all ten conditions. Its 408,000 formal
forecasts and 12,946,593-check audit remain unchanged, including bilingual/KL
failures, seed 7 fresh competence/goal failure, retained-NLL failures and seed 37's
525 exact-world regressions / 768 action changes. Negative evidence is retained.

[Normalization v2](EFFECT_ROLE_DECISION_V2.md) remains
**STOP_INCOMPLETE_EVIDENCE**, with no scientific pass/fail decision. All 15
checkpoints survive at `30880caf676c10773857221d9d5bc2437651fb6f`; the original
raw collection was lost before publication and never scored. Its frozen Intel
runtime guard remains unchanged. V3's 138,240 forecasts of those weights on the
new AMD runtime are explicit new-study references, not recovered original v2
results. The [interruption receipt](results/effect-role-interruption-v2.json)
and original text-only reproduction receipt retain their original scope.

[Coordinate transfer](COORDINATE_DECISION_V1.md), PR #76, and
[native SET v2](SET_ACQUISITION_DECISION_V2.md), PR #78, retain their KEEP
decisions. Native SET v1 remains SCORING_ABORTED / REVISE under its original rule.
Accepted G1/G2 development gains and all historical source/data locks remain intact.

## Roadmap state

| Stage | State |
|---|---|
| G1 | Development ready for G2; original scientific admission NOT_ADMITTED. |
| G2 | Accepted bounded composition, hidden propagation and supplied timing retained; no full scientific-admission claim. |
| G3 | Bounded development COMPLETE by audited v3; v1 REVISE and v2 STOP_INCOMPLETE_EVIDENCE remain unchanged. |
| G4 | Bounded matched-convention receiver retained. Broader conflict, delay, off-topic communication and formal admission remain open. |
| G5 | Held-out scoped evidence **baseline** retained; learned update/correction and independent scientific admission remain open. |
| G6–G8 | Corpus bridge, measured Wikipedia utility and guarded integration remain open. |

Independent custody, matched consumed compute, general calibration and formal
scientific admission remain open. The inclusive **2,000-line objective remains
unmet**. Production runtime, authority, ABIs and integration status are unchanged.
