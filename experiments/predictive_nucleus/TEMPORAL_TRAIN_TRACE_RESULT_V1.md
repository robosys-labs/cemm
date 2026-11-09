# Temporal TRAIN receipt trace — completed

**Date:** 2026-11-09. **Decision:** `LOCALIZED_POST_TEACHING_INTERFERENCE`.
This is a closed post hoc TRAIN diagnostic, not a new admission test.

The trace ran once from published source
`eb8c4879f72a7da1f65dec50ef104032d4487872`, after the approved source trees
were published. All ten original checkpoints stayed frozen. All 2,048 existing
TRAIN histories were evaluated after teaching, the tested-word claim, the first
physical answer and the second physical answer. No optimizer, simulator,
evaluator or TEST records were used by the trace.

The input projection was made separately from the original combined public
artifact; that projection command selected only its hash-bound TRAIN rows and
the 104 required native keys per seed. The inference process opened only the
published projection, frozen checkpoints, manifests and source files.

## Observed trajectory

Each arm has 10,240 case evaluations: 2,048 histories across five checkpoints.
These are repeated observations of a finite TRAIN bank, not independent worlds.

| Stage | Native protected correct | Native protected accuracy | Native protected NLL | Native target NLL | Flat protected accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| After teaching | 10,196 | 99.5703% | .090331 | .852274 | 86.0840% |
| After claim | 9,778 | 95.4883% | .233544 | .585906 | 82.3926% |
| After first answer | 9,517 | 92.9395% | .238188 | .433914 | 81.5918% |
| After second answer | 9,532 | 93.0859% | .221619 | .376510 | 83.1152% |

Native protected accuracy declines from teaching to the final forecast in every
seed and every public law/scope group. Four seeds begin with perfect protected
predictions; seed 37 begins with 2,004/2,048 correct. Native final target accuracy
is 83.2715%; flat is 75.9766%. These TRAIN figures do not replace the closed
held-out result.

## Earliest damage and subsequent repair

The baseline is after all eight teaching receipts. The diagnostic cannot locate
the cause of errors already present at that point.

| Earliest post-teaching loss among initially correct protected predictions | First losses | Repaired by final | Still wrong at final |
| --- | ---: | ---: | ---: |
| Claim | 441 | 294 | 147 |
| First physical answer | 540 | 228 | 312 |
| Second physical answer | 237 | 0 | 237 |
| Total | 1,218 | 522 | 696 |

Another 12 final errors were already wrong after teaching, making 708 final
protected errors. Adjacent-stage regressions are 441, 540 and 261; the last
number includes 24 repeated losses and must not be confused with first losses.
Adjacent repairs are 23, 279 and 276.

The first physical answer accounts for the most persistent earliest losses.
The claim also damages retention, but most claim-first losses recover later.
The same update repairs a target while damaging protected meaning in 100 claim,
246 first-answer and 84 second-answer transitions. These are transition counts,
not necessarily distinct histories. Every paired ID is retained in the audit.

## Interpretation and next decision

The existing network can usually forecast the protected outcome immediately
after teaching. Subsequent updates use useful information for the target while
degrading unrelated predictions. The claim alone improves target NLL from
.852274 to .585906 while protected NLL worsens from .090331 to .233544.
Suppressing all claim updates would discard useful information.

This does not distinguish information loss inside recurrent state from a
state-dependent readout problem. The original objective supervised protected
forecasts only after both probes; its intermediate protected forecasts were not
directly supervised. The evidence therefore motivates one objective-only TRAIN
feasibility comparison, frozen in
[PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md](PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md).

That comparison distributes the existing protected loss across three update
horizons, keeping the model, initialization, physical histories, minibatches,
256-update budget and six loss terms per sampled history fixed. It does not
hard-route writes by the supplied word identity. Such routing would guarantee
protection in this fixture, where corrections always concern word 0 and word 1
is always protected. A later generalization study needs new observable
histories and counterbalanced word roles; renaming old cases is insufficient.

## Evidence, validation and cost

- [Raw manifest](results/temporal-train-trace-v1/raw/manifest.json): all ten raw
  banks and summary, totaling 163,840 eight-endpoint forecast distributions.
- [Independent arithmetic audit](results/temporal-train-trace-v1/audit.json.xz):
  **5,358 checks pass**, including hashes, exact IDs, all metrics and transition
  lists, baseline partitions and final-state attribution. A separate read-only
  reviewer recalculated 86 pooled comparisons directly from raw arrays and
  found no discrepancy. Neither audit executes a model.
- [Execution receipt](results/temporal-train-trace-v1/execution.json): one
  invocation, zero optimizer updates, 24.576 wall / 24.572 CPU seconds and
  377,208 KiB peak RSS; float64 CPU, one torch thread.
- [Preflight](results/temporal-train-trace-v1/preflight.json): 14 focused tests,
  synthetic paired-ID checks, all 16 frozen source hashes and ten checkpoint
  hashes verified. The saved audit also verifies parameter-byte fingerprints.
- [Publication mapping](results/temporal-train-trace-v1/publication.json):
  authenticated GitHub publication assigned new commit metadata; both complete
  source trees exactly match their approved local counterparts.

The tracer adds 207 Python lines and the independent audit 239 lines; both are
research instrumentation. The learned model and parameter count are unchanged.
The inclusive 2,000-line objective remains unmet. The frozen temporal v1 result,
G5 admission status, G6–G8 dependencies, production runtime and ABIs are unchanged.

**This trace is complete. Do not rerun it when continuing the roadmap.**
