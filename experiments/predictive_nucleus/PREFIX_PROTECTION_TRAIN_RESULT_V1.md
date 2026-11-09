# Prefix protection TRAIN comparison — closed

**Date:** 2026-11-09. **Decision:** `REVISE_PREFIX_OBJECTIVE`.
**42/70 registered checks pass; 0/10 native law/seed cells pass all seven.**
This is a completed development comparison on previously observed TRAIN data.
It does not establish held-out improvement or G5 admission.

The fixed allocation improved pooled protection immediately after the claim,
but worsened final protected accuracy and Brier in every native condition.
Final target accuracy improved in aggregate while one condition regressed.
The allocation is rejected under its registered budget. This version is closed:
no schedule, seed subset, extra updates or loss-weight retry follows this result.

## What was tested

The [published protocol](PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md) changed only
the horizon of the existing sixth, protected loss term. It distributed that
term across after-claim, after-first-answer and after-both-answer predictions.
The first five losses, model, initialization, original minibatches and observed
TRAIN histories stayed fixed. Original baseline forecasts were read from the
[completed trace](TEMPORAL_TRAIN_TRACE_RESULT_V1.md); its models were not rerun.

Each of ten fresh fits used 256 updates of 128 histories, six equally weighted
NLL terms per history and Adam at .01: 32,768 sampled histories and 196,608 loss
terms per fit. Protected horizons received 10,923 / 10,923 / 10,922 terms. This
reduced final-specific protected supervision from 32,768 terms to 10,922 while
retaining the total protected weight of 1/6. Native and flat retained 1,108 and
1,144 trainable parameters respectively, with eight recurrent coordinates.
Each arm received identical tensors and the same deterministic horizon schedule.

All ten initial parameter and minibatch fingerprints match their original fit
receipts. The only dataset is the 2,048-history TRAIN projection with SHA-256
`660bb412f2d165295c30d2248daa2ae7a334c56d4fa95fe324f80aa356b7063f`.
Fitting and evaluation did not open TEST, oracle or combined public artifacts.

## Native results

Each row pools 10,240 evaluations: the same 2,048 histories across five model
seeds. These are repeated evaluations of a finite training bank, not 10,240 new
independent worlds. Brier and uncapped NLL are lower-is-better.

| Forecast | Original correct | Candidate correct | Original accuracy | Candidate accuracy | Original Brier | Candidate Brier | Original NLL | Candidate NLL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Protected after teaching | 10,196 | 10,227 | 99.5703% | 99.8730% | .022514 | .014991 | .090331 | .078519 |
| Protected after claim | 9,778 | 10,130 | 95.4883% | 98.9258% | .108476 | .060689 | .233544 | .168659 |
| Protected after first answer | 9,517 | 9,456 | 92.9395% | 92.3438% | .121750 | .122050 | .238188 | .235276 |
| Protected after both answers | 9,532 | 8,985 | 93.0859% | 87.7441% | .113187 | .180534 | .221619 | .316367 |
| Target after teaching | 7,277 | 7,309 | 71.0645% | 71.3770% | .475927 | .472304 | .852274 | .843228 |
| Target after claim | 7,259 | 7,292 | 70.8887% | 71.2109% | .375076 | .373258 | .585906 | .585165 |
| Target after first answer | 8,321 | 8,235 | 81.2598% | 80.4199% | .261968 | .267933 | .433914 | .442222 |
| Target after both answers | 8,527 | 8,680 | 83.2715% | 84.7656% | .224659 | .209469 | .376510 | .358848 |

The final protected result contains **630 regressions and 83 repairs**, giving
547 additional errors. Final target predictions contain 193 regressions and
346 repairs, giving 153 additional correct predictions. Mean protected Brier
across claim / first / both worsens from .114471 to .121091; early improvement
does not compensate for later damage under the registered criterion.

Claim-time protection improves in aggregate, not universally: claim accuracy
declines in NAND/7 and NOR/11. Native final protected accuracy declines in all
ten cells, by 2.23–7.57 percentage points. NAND/37 has the lowest final protected
accuracy and largest decline: 939/1,017 to 862/1,017, or 92.33% to 84.76%.
The largest absolute final protected Brier is NAND/7 (.224938); its largest
increase is NOR/7 (+.091780). These identify different adverse conditions.

## Fixed decision by condition

Each NAND cell contains 1,017 histories; each NOR cell contains 1,031.
Correct-count deltas below are candidate minus original. Gates retain the exact
protocol tolerances: 1e-12 for Brier non-increase and strictly more than 1e-4
for required Brier improvement. No pooled metric substitutes for a cell.

| Seed | Law | Checks passed | Final target correct delta | Final protected correct delta |
| --- | --- | ---: | ---: | ---: |
| 7 | NAND | 3/7 | +8 | -61 |
| 7 | NOR | 4/7 | +28 | -65 |
| 11 | NAND | 4/7 | +22 | -52 |
| 11 | NOR | 3/7 | +32 | -73 |
| 23 | NAND | 5/7 | +12 | -34 |
| 23 | NOR | 5/7 | +6 | -23 |
| 37 | NAND | 4/7 | +9 | -77 |
| 37 | NOR | 5/7 | +28 | -62 |
| 53 | NAND | 4/7 | -7 | -54 |
| 53 | NOR | 5/7 | +15 | -46 |

| Registered check | Passing cells |
| --- | ---: |
| Final target accuracy preserved | 9/10 |
| Final target Brier preserved | 10/10 |
| Final protected accuracy preserved | 0/10 |
| Final protected Brier improved | 0/10 |
| Mean protected prefix Brier improved | 5/10 |
| After-teaching protected accuracy preserved | 10/10 |
| After-teaching protected Brier preserved | 8/10 |
| **Total** | **42/70** |

NAND/53 is the sole final-target-accuracy failure (868 to 861). Both teaching
checks pass except teaching Brier in NAND/7 and NOR/11. The five mean-prefix
Brier passes are NAND/23, NOR/23, NOR/37, NAND/53 and NOR/53. The complete
[decision](results/prefix-protection-train-v1/scored/decision.json) retains
every cell's original and candidate metrics and all seven gate booleans.

## Flat comparison and adverse records

The flat arm is descriptive; the protocol does not use it to claim superiority.
It shows a similar aggregate tradeoff. All rows again contain 10,240 evaluations.

| Forecast | Original correct | Candidate correct | Original accuracy | Candidate accuracy | Original Brier | Candidate Brier | Original NLL | Candidate NLL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Protected after teaching | 8,815 | 8,964 | 86.0840% | 87.5391% | .240300 | .214076 | .460274 | .420058 |
| Protected after claim | 8,437 | 8,879 | 82.3926% | 86.7090% | .284307 | .243443 | .515740 | .461665 |
| Protected after first answer | 8,355 | 8,350 | 81.5918% | 81.5430% | .282797 | .278517 | .506407 | .498744 |
| Protected after both answers | 8,511 | 8,014 | 83.1152% | 78.2617% | .254546 | .309383 | .462051 | .539220 |
| Target after teaching | 6,742 | 6,813 | 65.8398% | 66.5332% | .483168 | .480439 | .829656 | .833049 |
| Target after claim | 6,865 | 6,960 | 67.0410% | 67.9688% | .441236 | .439838 | .741586 | .743699 |
| Target after first answer | 7,555 | 7,654 | 73.7793% | 74.7461% | .365738 | .358731 | .638133 | .628464 |
| Target after both answers | 7,780 | 8,002 | 75.9766% | 78.1445% | .334014 | .314083 | .585932 | .559007 |

Flat final protected predictions have 618 regressions and 121 repairs (497 net
additional errors); final target predictions have 253 regressions and 475 repairs
(222 net additional correct predictions). Mean protected prefix Brier worsens
from .273883 to .277114.

The [full saved comparison](results/prefix-protection-train-v1/scored/score.json.xz)
retains every case ID for accuracy regressions, repairs, worse Brier and worse
NLL at every stage, for both arms, each seed, each law and pooled groups.
At native final protection, 6,227 case forecasts have worse Brier and 6,241 worse
NLL; at native final target, those counts are 5,483 and 5,507 despite better
aggregate proper scores. No adverse case is removed from the denominator.

## Interpretation and one next task

This allocation moved protection toward earlier prefixes while weakening final
preservation. Its reduced final-specific supervision makes a shifted tradeoff
plausible; that is an interpretation, not an identified internal mechanism.
The experiment does not distinguish recurrent-state information loss from a
query-dependent readout defect, prove insufficient memory capacity, or establish
that increasing model size would help. Keep the original temporal result intact.

The next bounded task is a successor contract for **learned selective recurrent
updates** on prospectively new, counterbalanced two-meaning histories. Its owner
is the temporal recurrence and readout (`Model.receive` / `Model.predict`). A
candidate may use shared learned soft write/read gates over bounded generic
memory slots. State, parameter, observation and optimization budgets and a
matched unstructured control must be explicit before implementation or fitting.

Either meaning, or both, must sometimes change; interleave receipts so relevance
must be learned from evidence. Do not assign slots to word 0/1, supply a protected
flag, hard-mask writes by identity, or copy the old answer. The existing fixture
always challenges word 0 and protects word 1, so such routing would supply the
desired retention. New observable histories/structures and fresh challenge
custody are required; renaming opened cases is insufficient. Final correction
and retention must pass in every condition under the unchanged admission gates.

This selects a local architectural hypothesis for design, not a proven repair.
No second schedule or fit on the opened bank is the next task. Full G5, G6–G8,
independent scientific custody and general calibration remain open.

## Publication, validation and cost

All protocol/source/checkpoint/raw stages were published before their dependents:

| Stage | Published commit |
| --- | --- |
| Protocol, completed baseline trace | `caee7dd730a6d6e661a5d0a2b5af7a6bebc0a2b5` |
| Implementation and synthetic checks, before fitting | `0811a82daf926e32a333def21320ffb688795be6` |
| All ten completed fits, before evaluation | `d59e7021de6bc562940b86ba68b0210b68c60543` |
| All candidate raw forecasts, before comparison | `1242323074f49bf6dc44e4379348bc32f36cb812` |

The [fit manifest](data/prefix-protection-fit-v1/manifest.json) has SHA-256
`33611bb26131c794b1ee7cd8057491ad790efe8631e857e26b3001923beca84d`.
The [raw manifest](results/prefix-protection-train-v1/raw/manifest.json) binds
all ten banks and 163,840 eight-endpoint distributions to those checkpoints,
the TRAIN input and frozen source. Evaluation performed zero optimizer updates,
left weights unchanged and produced no parameter gradients.

The [preflight](results/prefix-protection-train-v1/preflight.json) records **12
passing synthetic tests**: exact final-only equivalence with the original loop,
matched observations/sampling, horizon inventory, future-answer isolation,
frozen inference, threshold and cell rules, adverse IDs, infinite-loss handling,
and source/checkpoint custody. The implementation's
[full isolated-invariant CI](https://github.com/robosys-labs/cemm/actions/runs/42612987658)
and [source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/42612987863)
both passed. Those CI claims refer to the published implementation commit above.

The separate [scalar audit](results/prefix-protection-train-v1/independent-gate-audit.json)
recomputes all 70 native checks directly from saved distributions, without a
learner or primary-scorer import, and agrees on every decision. Read-only review
also reconciles 1,044 report relationships, including pooled adverse counts and
repair-minus-regression identities. This is internal verification, not separate
scientific custody. Neither verification reran fitting or inference.

| Stage | Invocations | Wall seconds | CPU seconds | Peak RSS KiB |
| --- | ---: | ---: | ---: | ---: |
| Fit all ten models | 1 | 28.5785 | 28.5331 | 374,884 |
| Evaluate all ten on TRAIN | 1 | 26.2346 | 26.1545 | 373,620 |

Execution used Python 3.12.14, torch 2.10.0+cpu, NumPy 2.3.5, float64 CPU and one
torch thread. Actual optimizer-loop CPU totals were 7.82753 seconds native and
7.41690 flat; stage totals also include verification and serialization. Equal
update/loss budgets do not imply equal consumed compute.

This comparison adds 517 source, 68 independent-audit and 225 test Python lines
(810 total). Including the preceding trace, this continuation adds 1,256 Python
lines relative to `ec62c25`, with no inherited-core reduction. These are research
implementation and instrumentation; the inclusive 2,000-line objective remains
unmet. Production runtime, semantic authority and ABIs are unchanged.

**Continue from [ACTIVE_NUCLEUS.md](ACTIVE_NUCLEUS.md). This experiment is complete.**
