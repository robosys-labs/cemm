# Common-objective review: two evaluation defects, then a repaired diagnostic

Tracking: #22, follow-up to #49. Date: 2026-10-29.
Decision: **KEEP** the tested common-objective math; **REVISE** the public
curriculum and metric interpretation. **G1 remains HOLD / REVISE.**

## Findings before any substantive comparison

1. The v1 informative second-pair query leaves the first probe participant's
   bit untouched. That bit identifies the persistent mode. Exhaustive grouping
   by only the CURRENT complete observation and action yields 768/768 possible
   correct query forecasts, just like grouping by the whole history. Therefore
   this fixture does not establish a need to retain prior evidence. This is a
   legitimate observable-state shortcut, not a leaked private simulator label.
   The same-pair current-only ceiling is 480/768 (62.5%).
2. Query identifiability is not all-step predictability. V1's informative probe
   itself has two equally supported outcomes before its feedback. Its all-step
   deterministic ceiling is 92.8571%; the uninformative condition's is 94.6429%.
   Neither can satisfy a 95% all-step G1 interpretation, even with a perfect
   model. Earlier query bounds were correct, but insufficient for that use.

No historical scores or fixtures have been changed. These observations are
exhaustive finite-public-fixture calculations, not measured model performance,
a new independent sample, or a general population limit.

## Repair: all three bits are reset before the final query

`comparison_data.py` creates a separate v2 public fixture. After the same
three-action probe, three set actions cover all eight complete query states,
including resetting the nonparticipant. Orientation twins then have identical
current observations/actions at the query. Remembered informative probe
outcomes remain available in the history. The uninformative probe never reveals
the mode. Costs remain equal between information conditions: eight actions,
nine complete three-bit readings, 256 enumerated cases and six correlated
identifier views per case (1,536 histories; 12,288 event targets per update).

For BOTH same-pair and second-pair fixtures:

| Query evidence | Informative condition | Uninformative condition |
|---|---:|---:|
| Full history: best possible deterministic query accuracy | 100% | 62.5% |
| Current observation/action only | 62.5% | 62.5% |

The v2 informative all-step ceiling is 93.75%. The uninformative ceiling is
95.3125% simply because another easy reset was added, NOT because the ambiguous
query improved. This illustrates why pooled easy actions cannot be used to
claim this diagnostic passed G1. The primary comparison must separate the
post-probe query from every other step and score uncertainty on ambiguous
queries. The roadmap's independent, partially observed G1 gate is unchanged.

## Controls and overlap, without premature comparison scores

`empirical_joint.py` implements three complete-world count-table controls:
exact full prefix; current state/action in operand-relative coordinates; and
that local context plus all earlier ordered contact before/after observations.
The last control supplies an explicit, strong cross-pair abstraction; it is a
baseline, not a newly learned nucleus. All outcome probabilities are learned
from measured full states, including untouched bits. No persistence formula,
private mode, simulator import, smoothing or fallback is used. Unseen keys
abstain; observed zero probabilities remain zero.

Preforecast-key audit, not model scoring: second-pair exact prefixes overlap
training at the first three steps only and have zero coverage thereafter.
Both abstraction controls cover every step. All 1,536 final-query prefixes
are absent from training, but all local/contact-abstraction keys are present.
Thus this is withheld chronological structure built from familiar local
contexts, NOT independent atomic dynamics or unseen physics. Same-pair
assessment is resubstitution. No control has been scored on this fixture.

## Math and regression checks

The current joint kernel was compared with a separate scalar probability
calculation over every binary state and legal ordered contact/set/observe
(104 contexts x four persistence/role-tying configurations). All 416 complete
vectors agreed within 1e-12. Selected parameters in every parameter tensor of
three models passed central-difference whole-sequence gradient checks within
1e-7, extending the prior episode-mixture value/gradient test. The 8,192 v2
physical transitions also agree with a separately written scalar oracle check.
That check is evaluator-only and authored in this tranche, NOT independent
oracle custody or independent scientific review.

18 new tests cover the shortcut regression, complete reset, all-step bounds,
proper-score floors, future-feedback exclusion, ID round trips, input checks,
key coverage, synthetic empirical frequency/abstention/coordinate mapping,
no simulator dependency in model/control source, scalar probabilities and
finite-difference gradients. Local reconstructed-source suite: **301 passed**.
All 13 historical manifest locks pass unchanged. Local reconstruction uses the
retained 3493b3b source and blob-verified PR49 files; the six parent archive-audit
tests absent from that source are NOT counted locally. Complete-branch CI must
verify them. The parent 26e20c5 CI was independently checked as successful.

Reproduction:

```sh
python -m unittest experiments.predictive_nucleus.tests.test_comparison_data -v
python -m experiments.predictive_nucleus.comparison_data
python -m unittest discover -s experiments/predictive_nucleus/tests -v
```

The audit command generates fixture/input hashes, per-step current/history
bounds, uncertainty floors and all control key coverage. It never trains a
neural model or fits/scores a control. Unit tests fit controls only to explicit
synthetic histories. No new substantive fit, calibration or challenge was run.

## Roadmap continuation

Freeze the corrected public comparison before fitting: five seeds, all six
model arms, both information conditions, fixed-exposure and separately
CPU-budgeted regimes, empirical/no-change controls, per-step/query/proper
scores, reversals, renaming and paired regressions, complete checkpoints and
failure retention. Implement and review its runner separately; do not silently
execute a changed study. Independent held challenges, noisy/partial sensors,
matched-capacity comparisons and learned acquisition remain outstanding.

This tranche adds 456 physical Python lines including tests. The full retained
namespace becomes 14,725 lines, not under the practical 2,000-line target.
The 1,269 lines of this new bridge and follow-up are a subset, not an honest
replacement for the total including dependencies and historical diagnostics.
Production, PR21, existing models, source protocols and failed studies stay
unchanged. Language work remains deferred.
