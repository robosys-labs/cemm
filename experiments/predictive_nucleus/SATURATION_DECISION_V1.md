# Paired terminal-activation study: REVISE_SATURATION_HYPOTHESIS

Tracks [#22](https://github.com/robosys-labs/cemm/issues/22) and
[PR #73](https://github.com/robosys-labs/cemm/pull/73). Completed 2026-10-31.
**Execution complete; G3 remains open.** All historical decisions remain unchanged.

## What was executed

The [frozen protocol](SATURATION_STUDY_V1.md) compared the original factor with
its unsaturated variant: **89 language parameters each**, identical initial
weights and observed histories at five seeds. The only treatment is removal of
two terminal tanh operations. The ten fits each completed 256 prescribed updates
on 1,152 observed NAND outcomes per update. No world-model fitting, gold role
supervision, seed selection, retries or early stopping occurred. NAND-trained
encoders then transferred unchanged to NOR.

Source/data recipe publication: `cf6943b552dc7c255e416c47222d97b084b31ea3`.
Actual checkpoint publication: `1b73d3e94406bf5ceb55a5390bfb4b3a1c2f0cf4`.
Single collection/result commit: `526c39db7030080cf7c1fd1f8ff7e1f9c6190051`.
[Collection workflow](https://github.com/robosys-labs/cemm/actions/runs/41238796424).

All **209,280 planned candidate/control/retention records** were produced and
validated, plus 17,280 separate evaluator-only native references. There are no
missing records or failed stages. Final masking/swapping uses the same delivered
prefix; old banks are explicitly retention, not fresh evidence. The new bank
uses four new words, eight withheld word-layout cells and four/five-participant
diamond/bridge sequences. This is same-team public custody, not independent
scientific evaluation, novel grammar or arbitrary-language understanding.

## Result, not a replacement claim

Counts pool dependent law/seed/role/lexical views; they are not independent trials.

| Metric | Original factor | Unsaturated factor |
|---|---:|---:|
| Fresh exact complete worlds | 8,809/17,280 (50.98%) | 11,886/17,280 (68.78%) |
| Withheld-cell exact worlds | 4,272/11,520 (37.08%) | 7,064/11,520 (61.32%) |
| Fresh mean NLL, nats | 1.572310 | 1.493039 |
| Complete reversed-role pairs | 112/1,920 | 864/1,920 |
| Final lexical-pair conjunctions | 876/1,920 | 1,240/1,920 |
| Archived bilingual exact regressions | 0/20,800 | 0/20,800 |
| Archived lexical exact regressions | 12,480/41,600 | 4,160/41,600 |
| Archived binding exact regressions | 3,724/17,280 | 1,208/17,280 |

Relative to the paired original, the candidate repairs **4,148 fresh worlds** but
breaks **1,071** previously correct ones; fresh NLL worsens on **5,114** records
and improves on 12,166. Paired retention also has 1,040 lexical and 980 binding
regressions, despite 9,360 and 4,028 repairs respectively. Archived binding
comparison retains 1,580 repairs alongside its 1,208 regressions. These comparisons
have different references and must not be combined into one regression claim.
The previous 35% and PR #71 results use different banks, not a time series.

Seeds **7 and 37 pass every frozen criterion under both laws**, including full
fresh exactness, probability quality, controls and zero archived/paired exact
regressions. Seeds **11, 23 and 53 fail**. All masking/swap checks pass, but this
does not rescue inaccurate or overconfident answers. The unchanged decision is
[REVISE_SATURATION_HYPOTHESIS](results/saturation-v1/scoring/decision.json).

| Seed | Original final observed training NLL | Unsaturated final observed training NLL |
|---|---:|---:|
| 7 | 0.377999 | 0.002459 |
| 11 | 0.385007 | 0.338064 |
| 23 | 0.355182 | 0.151573 |
| 37 | 0.317399 | 0.004346 |
| 53 | 0.364557 | 0.157624 |

Removing the activations improves observed training fit at every seed, but the
same three seeds still exceed the frozen 0.05 limit. Their fresh mean NLL is
also worse than the paired original under both laws. Thus terminal saturation
is not a sufficient explanation or a reliable repair. The two passing seeds
show a bounded solution exists in this function class; they do not establish
robust learning, general capacity or scientific G3 admission.

## Verification and resources

A [standard-library saved-record audit](audit_saturation_saved.py), reusing the
independent arithmetic helpers rather than the study scorer, reproduces the
complete decision and comparisons: **3,032,778 checks, zero discrepancies**.
It validates 70 source bindings, 63 historical bindings, ten checkpoint
fingerprints, all 209,280 records and 17,280 saved native references. It performs
no fitting, inference or closed-study recollection. [Compact validation](results/saturation-validation-v1.json)
and [complete compressed audit](results/saturation-audit-v1.json.xz) retain its
hashes and scope. Internal arithmetic verification is not independent custody.

Twenty new tests pass. Final local suite: **893 discovered, 892 passed, one
full-checkout-only skip**, 84.510 seconds; all 30 protocol locks pass. The source
freeze also passed hosted [invariants/preflight](https://github.com/robosys-labs/cemm/actions/runs/41238489796)
and [source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41238489672).
Exact final-head CI is tracked separately in PR #73, not inferred from this run.
Prefreeze fixture failures and the initial timed-out test invocation are retained
in the delivery logs; neither was a research fitting/collection retry.

Ten fits consumed 22.530950 CPU / 22.532822 wall seconds in the reported region,
peak RSS 336,120 KiB. Saved collection prediction regions total 4.890074 CPU /
4.891005 wall seconds, peak RSS 477,120 KiB. These are cached batched predictions,
not end-to-end collection or service latency; preparation, serialization,
scoring and native-reference evaluation are excluded. Equal updates are not
identical consumed compute.

No learned-model or production implementation changes were needed. Study code
adds 447 lines, the audit 131 and tests 287. Retained research Python is **39,036
lines**, including 17,021 test lines: the inclusive 2,000-line goal remains unmet.
All 1,002 previous source-archive files were byte-identical before the deliberate
active-handoff update. Frozen code, data, weights and decisions remain unchanged.

## Next bounded task

Do not rerun this closed bank or enlarge the nucleus on the strength of pooled
accuracy. First perform a **training-only loss/gradient audit** of the existing
failed checkpoints and observed tape, with no updates or challenge access:
separate poor lexical fitting, layout fitting and weak gradient through the
latent-action likelihood mixture. Include the passing checkpoints as controls;
retain the original loss and supplied-world boundary. This distinguishes an
optimization bottleneck from an unsupported architectural story.

Only after identifying the earliest failing component, freeze one minimal
training intervention with identical exposure/budget and a genuinely fresh held
challenge. Keep every seed and archived regression. No optimizer change, new
training schedule, extra fit or G4 work is admitted by this result. G1/G2
development readiness and their original scientific requirements are preserved.
