# G5 native temporal updater v1 — completed negative result

**Date:** 2026-11-09
**Execution:** CLOSED; preparation, ten fits, fifteen raw banks and scoring are complete.
**Decision:** `REVISE_NATIVE_TEMPORAL_UPDATER` — **52/80** registered cell gates pass.
**Admission:** G5 `NOT_ADMITTED`; the original v1 scoped evidence rule remains the bounded baseline.

The native readout improves on the matched flat decoder in every law/seed cell,
but does not meet the absolute correction, probability or retention requirements.
Close this version with its negative result. Its completed stages are not tasks
for the next session to repeat.

## Evidence and sequence

The [unchanged protocol](TEMPORAL_NATIVE_TRANSFER_PROTOCOL_V1.md) fixes five seeds,
two physical laws, 256 updates per fit and the two-probe schedule. Both learned
arms consume the same realized observations and minibatches. No target-equivalent
question is available. Each fit consumes 32,768 sampled histories and 196,608
forecast terms; the same observed target supplies three forecast horizons.

| Published stage | Commit |
| --- | --- |
| Protocol | `0bdb45172f85b755c7916907cefbcd30f21766ed` |
| Implementation | `cd8f2f6b650b315a71797338b9d43374b71d1631` |
| 2,048 TRAIN histories, 12,288 TEST cases and validation | `dd65ff04a17ee3fa69b15c911b6a8796d7b2f7ae` |
| All ten fitted checkpoints | `3586f5432db10047cd856b07e1f0ac68fda02e60` |
| All fifteen raw forecast banks and ordered-prefix provenance | `a1b360d449c1ab0d54cd6a17714ba65a7cbef533` |

The November 9 continuation verified 43 local prepared/fitted/raw/source blobs
against the remote tree at the raw publication commit before scoring. Raw
publication was already complete, despite the old handoff still listing it as
pending. A dangling local worktree pointer was repaired from that remote head;
the recovered checkout was clean. No fitting or collection was repeated.

Two invocations of the unchanged saved-record scorer produced identical
55,139,219-byte outputs with SHA-256
`9dc1e5b7c4b1955af1b84aba1e3fe1763194426e1427366e086058022ed7b806`.
The [complete score](results/temporal-native-transfer-v1/scored/score.json.xz)
retains all adverse cases and is stored losslessly compressed. The
[compact decision](results/temporal-native-transfer-v1/scored/decision.json),
[artifact manifest](results/temporal-native-transfer-v1/scored/manifest.json)
and [reproduction receipt](results/temporal-native-transfer-v1/scored/reproduction.json)
bind the complete evidence.

## Registered decision

Each row below is evaluated separately in all ten law/seed cells. Pooled results
cannot replace a failed cell.

| Registered requirement | Cells passing |
| --- | ---: |
| After-both accuracy within .02 of its conditional optimum | 0/10 |
| After-both excess Brier at most .02 | 0/10 |
| Protected-word accuracy at least .95 | 2/10 |
| Confident wrong targets at most 1% of all targets | 10/10 |
| After-both Brier no worse than flat | 10/10 |
| After-both Brier better than omitting the first answer | 10/10 |
| Cheap-query net reward no worse than flat | 10/10 |
| Cheap-query net reward no worse than omitting the first answer | 10/10 |

Protected retention passes only NOR/11 and NOR/23. All NAND conditions and
NOR/7, NOR/37 and NOR/53 fail it. Native after-both accuracy ranges from 77.91%
to 86.78%; the conditional optimum is 94.27% for NAND and 94.01% for NOR.
The excess-Brier range is .11921–.22220, against the .02 limit. The failures
are substantial and cannot be attributed solely to irreducible ambiguity.

These optima belong to this study's fixed two-probe schedule. The earlier
249/256 unrestricted-menu ceiling is not used as a gate here.

## Comparative results

The denominator is 61,440 case evaluations per arm: the same 12,288 finite
TEST cases evaluated with five fitted seeds. The 184,320 raw records across
three arms are not independent worlds or independent replications.

| Measure | Native updater | Flat decoder | Supplied rule | Native, first answer omitted |
| --- | ---: | ---: | ---: | ---: |
| Correct after both available observations | 50,688 | 45,958 | 46,080 | 48,154 |
| After-both accuracy | 82.50% | 74.80% | 75.00% | 78.38% |
| Observed multiclass Brier, lower is better | .23813 | .35236 | .25667 | .29361 |
| Observed uncapped NLL, lower is better | .39958 | .61937 | .39086 | .47887 |
| Protected-word accuracy | 92.73% | 82.59% | 100.00% | 95.37% |
| Wrong targets at at least .95 confidence | 15 | 47 | 0 | 57 |
| Paid second questions at fee .05 | 17,643 | 19,699 | 0 | 29,324 |
| Optional-query target accuracy | 82.92% | 74.49% | 73.44% | 77.00% |
| Optional-query mean net reward | .81486 | .72887 | .73438 | .74614 |

Native Brier, retained-answer Brier gain and cheap-query net reward beat their
registered comparators in every cell. This supports a bounded advantage from
reusing the native endpoint family under the supplied inputs. It does not
establish G5 clarification savings at matched final correctness.

The supplied rule preserves all protected outcomes and has lower pooled NLL
than native, despite weaker target accuracy and Brier. It is a diagnostic
control, not a replacement for the historical G5 baseline. Confidence coverage
and conditional error rates remain in the complete score; the confident-error
gate alone does not establish calibration.

The question policy is not uniformly useful. NOR/53 loses 10.7 net reward units
relative to its own no-second-question decisions. The full score also reports
the discrepancy between current predictions and the average of predicted
conditional branches. Relative utility gains do not erase these adverse cases.

## Post hoc localization from existing records

The separately implemented
[protected-pair audit](results/temporal-native-transfer-v1/scored/protected-pair-audit.json)
reproduces every saved regression/repair identity. It changes no model or gate.

| Effect of retaining the first physical answer | Tested target | Protected word |
| --- | ---: | ---: |
| Previously wrong, now correct | 3,728 | 892 |
| Previously correct, now wrong | 1,194 | 2,512 |
| Net additional correct outcomes | +2,534 | **−1,620** |

Protected accuracy falls from 95.3678% to 92.7311%, with a decline in every
law/seed cell. Of the 2,512 new protected errors, 2,297 occur during parent
correction, 183 during local correction, and 16 each during a one-event
exception and report-only change. There are 913 cases where the same retained
answer repairs the target but damages the protected meaning.

The native arm averages 66.86% accuracy on local corrections, 65.38% on parent
corrections, and 98.88% on each stable/report-only category. These are evaluator
breakdowns after scoring; temporal cause is never a learner input.

**Inference:** the learned update can use new evidence, but carries some
corrections too broadly across meanings. Every receipt has a word indicator,
yet all words rewrite the same eight recurrent coordinates. The records
identify cross-word interference; they do not prove a memory-size limitation
or establish which repair will work. The next bounded analysis is a TRAIN-only
trace of the frozen recurrence, locating the earliest damaging receipt before
selecting a new candidate. Longer training, new primitive hypotheses and a
larger model are not justified by this result alone.

## Verification and cost

- The portable [evidence audit](results/temporal-native-transfer-v1/scored/saved-evidence-audit.json)
  passes 25,200 checks: hashes, tensor-byte fingerprints, all ordered prefixes,
  matched exposure, target-input exclusion and pre-answer invariance. The
  largest identical-prefix forecast difference is 7.77e-16, including groups
  with different still-unseen second answers.
- The separate [NumPy scoring audit](results/temporal-native-transfer-v1/scored/independent-score-audit.json)
  passes 2,027 checks and independently reproduces all 80 gates and the decision.
  The protected-pair audit passes 20 exact regression/repair list comparisons.
- The published implementation validation ran 1,366 isolated tests: 1,364
  passed, two intentional sealed-collector skips, zero failures/errors. All
  37 historical manifests, the original protocol and guarded preflight passed.
  Both hosted workflows passed on raw publication commit `a1b360d`.
- Complete fit-stage cost was 28.58 CPU/wall seconds with 482,388 KiB peak RSS;
  collection used 293.32 CPU / 293.35 wall seconds and 849,652 KiB peak RSS.
  Native fit loops consumed 7.56 CPU seconds against flat's 7.03. Matching
  examples and updates does not mean matching consumed compute.
- The native updater has 1,108 trainable parameters, flat 1,144. This study
  adds 878 Python source lines and 255 focused-test lines; the three closure
  audit scripts add 391 lines. These counts exclude inherited dependencies,
  so they do not satisfy the inclusive 2,000-line objective. Scoring changed
  zero learner parameters or learner-source lines.

Saved-record reproduction, without fitting or collection:

```bash
python -m experiments.predictive_nucleus.temporal_native_score_v1 \
  --prepared experiments/predictive_nucleus/data/temporal-native-transfer-v1 \
  --raw experiments/predictive_nucleus/results/temporal-native-transfer-v1/raw \
  --output /tmp/cemm-temporal-v1-rescore
```

The output directory must be new. Compare its score hash with the value above.
This command is for explicit reproducibility checks, not the next research task.

## Roadmap effect

This is a closed negative comparison with a retained relative native-readout
gain and a concrete retention defect. The supplied hypothesis family, scopes,
external rewards and existing G3 layouts remain limitations. Omitting one
answer is not clearing all episodic memory. Separate same-team arithmetic
audits do not establish independent challenge custody.

G1–G3 accepted bounded development and G4 matched-convention results remain
intact. Full G5, new sentence-family acquisition, durable competence after full
episodic clearing, G6 corpus acquisition, G7 Wikipedia utility and G8 integration
remain open. Production runtime, authority and ABIs are unchanged.
