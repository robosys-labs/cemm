# Active nucleus — G5 matched native temporal updater

## Current handoff on November 8

**Current state: preparation complete; fitting and TEST not yet run.**
The [completed temporal result](TEMPORAL_OBSERVABILITY_RESULT_V1.md) closes
PR #100 and records the restricted-input audit. Both PR #99 persistence and
PR #100 observation-support results are present on this branch. Continue from
their saved artifacts; do not repeat either completed qualification.

The restricted-input audit retains 448 unidentifiable group/target cells per
menu and gives a full-menu ceiling of 249/256. This prevents a false 100% gate
from triggering another model-tuning loop. It is a post hoc information audit,
not learned performance.

The prepared bank contains 2,048 TRAIN histories and 12,288 held-out cases.
Its manifest SHA-256 is `6467823ca1238718d06fd3a39483d54339ccd614ab0e1cfb58b8cb6f6384c6d3`.
The full isolated suite passed 1,366 cases with two intentional skips; all 37
historical manifests, original protocol and guarded preflight pass.

The [frozen next study](TEMPORAL_NATIVE_TRANSFER_PROTOCOL_V1.md) is executable
in `temporal_native_transfer_v1.py`: native versus flat readout with identical
realized training histories, five seeds, 256 updates, and no target-equivalent
query. The supplied four-way rule and cleared-first-answer controls remain
visible. Exact conditional bounds are calculated for its own fixed schedule.

Execute stages once, in this order, publishing each stage before starting the
next. Inspect the stage manifest before continuing; an existing complete stage
must not be repeated just because a new chat began.

```bash
python -m experiments.predictive_nucleus.temporal_native_transfer_v1 prepare --output experiments/predictive_nucleus/data/temporal-native-transfer-v1
python -m experiments.predictive_nucleus.temporal_native_transfer_v1 fit --prepared experiments/predictive_nucleus/data/temporal-native-transfer-v1 --output experiments/predictive_nucleus/data/temporal-native-fit-v1
python -m experiments.predictive_nucleus.temporal_native_transfer_v1 collect --prepared experiments/predictive_nucleus/data/temporal-native-transfer-v1 --fitted experiments/predictive_nucleus/data/temporal-native-fit-v1 --output experiments/predictive_nucleus/results/temporal-native-transfer-v1/raw
python -m experiments.predictive_nucleus.temporal_native_score_v1 --prepared experiments/predictive_nucleus/data/temporal-native-transfer-v1 --raw experiments/predictive_nucleus/results/temporal-native-transfer-v1/raw --output experiments/predictive_nucleus/results/temporal-native-transfer-v1/scored
```

Read the single scored decision and retain every failed gate; do not extend
training, sweep hazards, reopen old banks or add another generic preflight.
This is a bounded learned-update comparison. New sentence-family acquisition,
full episodic-memory-cleared retention, G5 admission and G6–G8 remain open.

## Historical handoff on November 7

The [transformed-frame recovery result](COORDINATE_PERSISTENCE_RESULT_V1.md)
records `QUALIFIED_TRANSFORMED_FRAME_RECOVERY`. Both complete executions at
`9083c5c0f371c8d8a950abb4e8f748b95ff8d778` reproduce all 46,080 checkpoints,
138,240 query-policy branches, and 138,240 conflict rejections per invocation.
Their reports and checkpoint banks match byte for byte. The published evidence
includes the complete checkpoint archive, source bindings, separate execution
receipts, and independent file/numerical audits. This recovery tranche is closed;
continue from its artifacts instead of rerunning it without a new defect.

The next bounded task is the temporal observation-support preflight in
[PR #100](https://github.com/robosys-labs/cemm/pull/100), followed by one
prospectively exposure-matched temporal/scope learner comparison. G5 learned
correction and scientific admission remain open; G6–G8 keep their dependencies.

## Previous handoff on November 6

The [static coordinate-transport qualification](COORDINATE_TRANSPORT_RESULT_V1.md)
records `KEEP_TRANSPORT_PREFLIGHT`, with all 80 condition gates passing.
The prospective bank contains 1,536 trials with fresh participant identities,
evaluated through all five saved fits and both native laws. Every intact
retained condition achieves 100% target-endpoint and local-action accuracy.
Mean target Brier is .012301 against .562502 for reset, .287323 for latest
only and .502294 with the learned layout response removed.

Cheap clarification uses the second demonstration to predict a different
target instance. Retained evidence buys 4,320 answers against 5,760 for
reset, with 100% against 71.875% final correctness and .971875 against
.681250 mean net reward. Both native runs and both scoring runs reproduced
byte-for-byte. The full isolated suite ran 1,313 tests with zero failures
and two intentional sealed-collector skips.

The result retains 184 small Brier regressions against latest-only evidence
and 480 cheap-query net regressions from additional fees. Retained ECE is
.068927, with 28.125% confidence coverage at .95 and zero confident errors.
Cycled layout produces 1,196 confident errors. This qualification uses two
existing acquired words and four supplied transformations of their learned
coordinates, within a finite static task.

The [v8 audit](JOINT_TRUST_AUDIT_V8.md) confirms the frozen
`REVISE_JOINT_V8` decision. Six of 13 quantitative gates passed. The joint
model achieved .06048 five-view meaning Brier against .06283 for the fitted
neutral control, while its net utility was .82996 against .84768 and its
paid queries were 156 against 148. All five seeds lost utility. Genuine
meaning changes account for −87.75 reward, offset by +19.70 on stable
meanings. The fixed-time decision metrics cover 1,920 worlds / 960 pairs.

The auxiliary joint payoff comparison has an event-order defect. Sorting
tied receipts changes their causal order, and a positional scoring join
misattributes 11,520 of 28,800 forecasts. The accompanying synthetic test
exposes both the wrong receipt identity and the changed observation history.
The reported zero premature-confidence count is guaranteed by the fixed
hazard, which bounds probabilities to [.15,.85]. On indistinguishable
balanced twins, prefix Brier was .35638 against .25 for equal probabilities.

The [G3 coordinate intervention](G3_TRAIN_COORDINATE_INTERVENTION.md) was
frozen before execution and reproduced every archived training objective.
Across five fits, mean endpoint NLL rose from .04134 to .52204 with effect
removed, or .37439 with role removed. Restoration reproduced every forecast.
Role influenced exactly the bit-changing observations. Each identity owns a
separate row and both taught words represent the same operation, which
bounds claims of shared learning.

The [native receipt qualification](G3_G5_RECEIPT_PREFLIGHT_RESULT.md)
retained all 16 teaching rows across five frozen worlds and reproduced twice
byte-for-byte. Changing the current endpoint preserved every forecast and
public-prefix digest. A single physical answer left two candidate
interpretations nearly tied in every case.

The [physical-query study](PHYSICAL_QUERY_PREFLIGHT_RESULT_V1.md) now computes
the expected value of the actual endpoint distribution. It qualifies a
one-observation decision with supplied menu-identification rewards. Across
80 ordered TRAIN pairs, a retained first observation led to 40 additional
cheap queries, against 80 with that observation discarded. The retained arm skipped
the second paid question on the role-ambiguous all-ones cases. Expensive,
unavailable and indifferent-goal conditions also received zero queries.
All 960 policy cases were retained, and exhaustive Bayesian enumeration
agreed within 2.22e−16. Eight synthetic checks cover the formula and edge
conditions, including normalization drift and arithmetic overflow.

The [physical evidence ledger](PHYSICAL_LEDGER_RESULT_V1.md) now qualifies
duplicate protection and cold-process recovery on the same TRAIN receipts.
Both complete three-process invocations produced byte-identical reports.
All 160 initial priors, 960 decisions and 120 purchased posteriors matched
the uninterrupted and published references exactly. Every one of 320 duplicate
deliveries was idempotent, and all 960 conflicting-ID attempts rejected
atomically. Valid physical counterexamples with zero computed predictive mass
remain retained with an explicitly unavailable belief. The full isolated suite
ran 1,264 tests with zero failures and two intentional sealed-collector skips.

Next, qualify duplicate-safe cold-process persistence of the transformed
hypothesis frame, then freeze temporal/scope correction and a prospectively
matched neural comparison. The archived GRU parent received 1,024 events per
update against 1,152 for the accepted coordinate parent, and the current
text-only arm omits physical state. New sentence families, correction,
contradictory sources, irreducible ambiguity and durable competence after
episodic-memory clearing remain G5 requirements.

The retained G5 baseline is the v1 scoped evidence rule. G5 learned
ask–revise–retain and formal admission are open. G6 corpus acquisition, G7
measured Wikipedia utility and G8 guarded integration remain pending.

## Historical v7 handoff

## G5 v7: sealed source-conditioned challenge completed — no promotion (2026-11-04)

[Draft PR #93](https://github.com/robosys-labs/cemm/pull/93) directly
tests the failure attributed in PR #92 without altering G1–G4,
v5/v6 evidence, production runtime or the existing G5 rule.
The preregistered one-extra-scalar
`(h,e_A,e_B)` model fixed a **physical observation-noise likelihood
mismatch** discovered before TEST, retained the two-state temporal
recursion and compared an equally TRAIN-fitted physics-matched
two-scalar control. All fits used observed selected physical payoffs
only; no gold meanings or participant labels.

Frozen TRAIN fit: v7 `h=.15,e_A=.03,e_B=.20`, causal NLL
**.49980**; neutral `h=.15,e=.10`, **.52251**; TRAIN-smoothed
G5 rule `delta=.20`, **.56904**.
The [ten raw challenge banks](results/independent-v7/raw/manifest.json)
were committed at `79a62ce8dc25b5421672a0a0b77d8f1f27866dd3`
**before evaluator scoring**: 1,920 distinct worlds, 28,800
one-step payoff forecasts, 9,600 correlated scope views,
no public-world-ID overlap with v6.
[The scored decision](results/independent-v7/scored/decision.json)
was independently rerun from frozen raw at
`41890264288` with **1,230 tests passing**; a prior
formatting-only scorer failure and repair remain disclosed.

**Decision: `REVISE_SOURCE_V7` (6/10 gates pass), G5
`NOT_ADMITTED`.** The source-aware model improves five-view meaning
Brier to **.04807** (neutral **.05221**; retained rule **.07211**),
but has **148 vs 127** paid queries, **94.32% vs 94.87%**
optimal actions, **152 vs 102** ≥95%-confident meaning errors
and **53 newly wrong parent/sentinel confident states** versus
frozen v6. Net/action **.85250 vs .85181** buys too little to
offset adverse calibration/cost/retention gates. Seed 53 with
reversed source reliability falls to **.83105 vs .85306** net/action.
Of the 53 newly confident retained mistakes, **36** occur in the
reversed regime.

The key mechanism is **stable-B versus true-change-B tension**:
stationary first-post-epoch Brier improves from **.07424** to
**.04155** when meaning stayed stable under noisy B, yet worsens
from **.29548** to **.42946** when B reports a *real* revision.
Static source trust cannot separate transient sensor corruption
from durable change and does not transfer when source reliabilities
reverse. The v7 model gains on proper average calibration but fails
the **query**, **optimal-action**, **retention-safety**, and
**worst-seed** gates. TRAIN-smoothed rule also fails efficiency
(355 queries versus 100 original G5 rule queries).

**Next highest-information tranche:** one *representation* diagnostic,
not another sweep of fixed h/e. Prospectively measure whether a minimal
learned source-trust state jointly maintained with time-indexed
competing meaning hypotheses can distinguish single noisy receipts from
durable change, adapt after source shifts from observed selected
payoffs and reduce genuinely useless questions. Include an
**identical-history fixed-trust control**, newly seeded matched
stable/flip/source-switch challenges, adversarial calibration,
per-seed/query value, and explicit abstention before information
becomes discriminative. Do not reuse the opened v7 challenge to fit
or tune. Keep original G5 rule as active bounded baseline;
no G6, no production integration, no formal scientific admission.
[Full adverse decision](SOURCE_CONDITIONED_DECISION_V7.md) ·
[raw custody](results/independent-v7/raw/manifest.json) ·
[scored custody](results/independent-v7/scored/manifest.json) ·
[pre-fit physical erratum](SOURCE_CONDITIONED_PREFIT_ERRATUM_V7.md) ·
[post-score presentation erratum](SOURCE_CONDITIONED_SCORING_ERRATUM_V7.md).

## Latest G5 v6 scored and diagnosed — no promotion

[PR #91](https://github.com/robosys-labs/cemm/pull/91) froze a two-scalar
temporal learner on new, law/seed/world-distinct noise with no forced
contradiction. One shared outcome-only TRAIN fit selected **h=.15, e=.10**
from 576 NAND TRAIN worlds / 8,640 selected payoffs. Ten raw TEST
banks were sealed **before** scoring at
`3f0d247d88c51132ff63e1fde34dfca1b45747ab`.
The scored ten conditions pass **1,224 software tests**; v6
mean meaning Brier **.05593 vs .07430** for the zero-parameter
scoped rule, net/action **.84167 vs .82947**, but bought **88 vs 73**
clarifications and regressed NAND seeds 37/53. Formal G5
scientific admission is still **NOT_ADMITTED**.

[PR #92](https://github.com/robosys-labs/cemm/pull/92)'s read-only
post-score attribution independently reproduces all **1,920**
world IDs and policy utility totals. **1,225 hosted tests pass.**
All 73 rule requests are shared; the temporal learner buys 15
additional questions. Four are beneficial on their realized
trajectories and eleven have no realized action benefit, for
**+3.25 net utility units** from extra questions. The
dominant failure subgroup is *stable meaning with source-B epoch
observation*, **−34.95 net units** temporal-minus-rule. The
unchanged filter ignores source identity and uses **e=.10** even
though observed TEST inversion rates were **A 398/14,486 (2.75%)**
and **B 3,470/14,314 (24.24%)**. Source-B NLL is .665 vs A .475.
The first stable-B local prediction is worse than the scoped rule,
but two later observations repair it. The old no-more-questions and
worst-seed gates therefore **remain failed**.

[Failure-attribution decision](V6_FAILURE_ATTRIBUTION_DECISION.md) ·
[immutable post-score diagnostic](results/independent-v6/posthoc-attribution.json) ·
[v6 scored manifest](results/independent-v6/scored/manifest.json).

**Next highest-information tranche:** prospectively compare
`(h,e_A,e_B)`—one extra source-reliability parameter—against the
unchanged v6 two-scalar filter and a TRAIN-smoothed G5 rule using
a *fresh, independently seeded challenge*. Fit only from observed
selected payoffs. Score immediate and final meaning calibration,
epoch flips/stable errors by source, high-confidence errors,
actual question value, retained correctness and cost. Do not
retroactively alter the opened v6 gate or increase neural layers
without evidence. Real semantic scope inheritance and learned
cross-process answer persistence remain unproven, and G6–G8
and the inclusive 2,000-LOC target remain open.



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
| G5 | Scoped evidence baseline retained. Static learned-coordinate transport and transformed-frame recovery qualified. Temporal correction and scientific admission remain open. |
| G6–G8 | Corpus bridge, measured Wikipedia utility and guarded integration remain open. |

Independent custody, matched consumed compute, general calibration and formal
scientific admission remain open. The inclusive **2,000-line objective remains
unmet**. Production runtime, authority, ABIs and integration status are unchanged.
