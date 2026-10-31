# G3 bilingual participant grounding: KEEP_BILINGUAL_GROUNDING

Tracking: [roadmap #22](https://github.com/robosys-labs/cemm/issues/22),
[PR #68](https://github.com/robosys-labs/cemm/pull/68). Recorded 31 October 2026
(Africa/Lagos). **Bounded role-binding study complete; broader G3 lexical
grounding remains open.** Formal scientific admission is unchanged.

## Result

The outcome-trained adapter correctly binds participants across English-like SVO
and artificial OSV, fresh opaque names, reversed roles and three-to-five-contact
compositions. Five encoders trained on NAND outcomes transfer unchanged to the
five separately acquired NOR worlds. No gold action order or linguistic role
label entered candidate fitting. All ten acquired world checkpoints remain
byte-identical; the new encoder has 474 parameters and each world 562.

| Grounded metric | Result |
|---|---:|
| Complete-world forecasts | 20,800 / 20,800 correct |
| Participant-order classifications | 20,800 / 20,800 correct |
| Entire trajectories | 5,760 / 5,760 correct |
| Both-direction whole-trajectory role conjunctions | 2,880 / 2,880 correct |
| Native correct → language wrong | 0 |
| Errors on realized unchanged coordinates | 0 |
| Minimum true-world probability | 0.991386864 |
| Maximum reversed-action counterfactual probability | 0.00226804147 |
| Worst family/language mean NLL | 0.00593435707 nats |
| Maximum bilingual probability-vector TV | 0.0000931755 |
| Maximum synonym probability-vector TV | 0.0000663044 |

Each twin category contains 2,880 MAP-consistent trajectory pairs and 10,400
forecast comparisons. All 110 preregistered checks pass across both laws and
all five seeds. The complete collection retains **124,800 candidate/control
forecasts**, with **20,800 gold-action native references** separately labeled.
These counts are dependent views of the declared synthetic trajectories, not
independent physical trials. Full endpoint feedback follows each prediction.

## Controls and qualifications

All five fitted arms use the prescribed 256 language updates and final checkpoint;
exchanged-name evaluation reuses the grounded checkpoint. There was no early
stopping, hyperparameter search or post-challenge tuning.

| Arm | NAND correct / 10,400 | NOR correct / 10,400 |
|---|---:|---:|
| Outcome-grounded adapter | 10,400 (100%) | 10,400 (100%) |
| Supervised parser control | 10,400 (100%) | 10,400 (100%) |
| Direct neural sequence | 1,468 (14.12%) | 1,528 (14.69%) |
| Text-only | 746 (7.17%) | 505 (4.86%) |
| Untrained frozen world | 432 (4.15%) | 460 (4.42%) |
| Exchanged-name messages | 5,655 (54.38%) | 6,188 (59.50%) |

The direct control has 1,048 parameters versus 1,036 for encoder plus acquired
world. Its lifetime evidence and consumed compute do not match the candidate.
At five/six entities its fixed 64-coordinate head activates untrained output
coordinates. The counts below separate that limitation from trajectory transfer;
all columns still contain held-out trajectory families.

| Law / arm | 3–4 entities | 5–6 entities |
|---|---:|---:|
| NAND grounded / parser, each | 4,640 / 4,640 | 5,760 / 5,760 |
| NAND direct sequence | 1,220 / 4,640 | 248 / 5,760 |
| NAND text-only | 674 / 4,640 | 72 / 5,760 |
| NAND untrained world | 332 / 4,640 | 100 / 5,760 |
| NAND exchanged names | 2,531 / 4,640 | 3,124 / 5,760 |
| NOR grounded / parser, each | 4,640 / 4,640 | 5,760 / 5,760 |
| NOR direct sequence | 1,064 / 4,640 | 464 / 5,760 |
| NOR text-only | 345 / 4,640 | 160 / 5,760 |
| NOR untrained world | 296 / 4,640 | 164 / 5,760 |
| NOR exchanged names | 2,768 / 4,640 | 3,420 / 5,760 |

The poor direct-control result does not establish architecture superiority.
Exchanged messages can change the subsequent persistent-mode posterior after
feedback; that ablation measures the complete wrong-message pipeline.

**Probability retention is imperfect:** all 20,800 grounded forecasts have
slightly worse NLL than the gold-action native reference. The mean increase is
**0.0000908180 nats**, the maximum **0.0001535498 nats**, and none improve. Every
case remains in the raw summary. Zero exact-world regressions must not be
described as zero probability degradation.

## What this establishes, and the next G3 task

The supported capability is **learned bilingual participant/order binding from
observed consequences**. Supplied roster equality preserves new identity strings.
Supplied event boundaries, a contact-only interface and two candidate operand
orders bound the problem. With one contact relation, generic identity-token
positions can distinguish SVO from OSV; the bank does not establish that lexical
identity is necessary or that synonym semantics were independently learned.
There is no language generation, clarification or general comprehension result.

Keep this success and select one fresh, small **lexical contrast**: hold identity
layout and word order fixed while different lexical items denote at least two
already acquired native effects. Train only the text adapter from outcomes;
never supply the candidate an action-kind label. Require the correct world to
change when the lexical item changes, and include a lexical masking/shuffling
control so position alone cannot satisfy the task. Preserve both languages,
held-out combinations and all earlier role-binding successes. Publish a new
source/data/fit plan before fitting. This next task is **selected, not yet
implemented or frozen**; no G1/G2 refitting, new physics or larger workspace is
introduced. G4 communication and G5 clarification remain later roadmap work.

## Provenance and verification

- Source/data/fit freeze: `d1e04fbcb2ff70af10a38ddb42a85a8128df2bcd`, identical
  tree to approved local `4fce3ac`; published before all 25 research fits.
- All language checkpoints published at
  `2db941c2dd4fed97d0b5cef718b24f17ba88bb39` before the one challenge collection.
- Original world checkpoint freeze:
  `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420`.
- Saved-result manifest:
  `c650958da148ec0d16d540ffce24ed0b216a27e4bb1328e80b79ae5d41ac7a85`.

A separate stdlib-only [audit](audit_bilingual_saved.py) reconstructs all scoring
and decision arithmetic: **1,060,066 checks, zero discrepancies**, 57 source
bindings, eight prepared artifacts, 63 result bindings and 35 tensor
fingerprints. It executes no model, collector or repository scorer. This is
independent implementation within the same team, not independent scientific
custody. Run from the repository root:

```sh
python experiments/predictive_nucleus/audit_bilingual_saved.py \
  --repo . --output /tmp/cemm-bilingual-audit.json
```

All 796 isolated invariants pass. Hosted source and invariant checks pass at the
[weight commit](https://github.com/robosys-labs/cemm/actions/runs/41206835494)
and after the [test-only portability correction](https://github.com/robosys-labs/cemm/actions/runs/41207234593).
The initial source CI found a bitwise-equality assertion across different CPU
batch shapes. Synthetic kernels reproduce at most 8.89e-16 log differences;
the test now uses 1e-14 absolute tolerance, zero relative tolerance, and rejects
reversed-role/reversed-world negative controls. No research source, checkpoint,
data, metric or threshold changed, and no scientific fit/collection was rerun.

## Resources and size

| Recorded region | CPU seconds | Wall seconds |
|---|---:|---:|
| 25 fits and preparation, 6,400 updates | 44.247 | 44.249 |
| Collection cache preparation, counted once | 4.663 | 4.671 |
| Cached forecast loops | 2.523 | 2.526 |
| Scoring and evaluator-native references | 9.727 | 9.735 |

Peak recorded RSS is **361,800 KiB**. Grounded batch-amortized p95 is
**19.326–31.330 microseconds**; this excludes native-cache construction and is
not single-request latency. Serialization/publication are outside those
collection regions. Shared preparation costs are not multiplied by arm count.

This tranche adds **1,984 Python lines**: 914 study source, 415 audit source and
655 test lines. Total retained research Python is **35,032 lines**; the inclusive
2,000-line program objective remains unmet. No production runtime or authority
contract is changed.

## Saved evidence

- [Frozen prospective design](BILINGUAL_STUDY_V1.md)
- [Decision](results/bilingual-v1/decision.json)
- [Raw trace manifest](results/bilingual-v1/manifest.json)
- [Full compressed summary and native references](results/bilingual-v1/summary.json.xz)
- [Headline metrics](results/bilingual-headline-v1.json)
- [All entity-count/control details](results/bilingual-detail-v1.json)
- [Independent arithmetic validation](results/bilingual-validation-v1.json)
- [Language training reports](data/bilingual-fit-v1/training.json)
