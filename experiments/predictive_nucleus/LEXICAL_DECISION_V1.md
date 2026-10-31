# G3 lexical direction: learned contrast, failed structural transfer

Tracking: [roadmap #22](https://github.com/robosys-labs/cemm/issues/22) and
[draft PR #69](https://github.com/robosys-labs/cemm/pull/69). Completed 31 October 2026.

**Decision: KEEP_LEXICAL_GROUNDING. Structural decision:
STRUCTURAL_TRANSFER_NOT_ESTABLISHED.** All 130 primary checks pass. Seen
word–layout combinations pass all 40 structural checks; held-out combinations
fail all 40. The fixed-order lexical gain is retained. G3 structural transfer
remains open, and this result does not advance the project to G4.

## What changed and what was learned

The existing **474-parameter neural OrderEncoder** was continued from its five
successful bilingual checkpoints, using only observed complete-world outcomes
for linguistic events. All ten acquired **562-parameter world models** stayed
frozen. There are **zero added model parameters**, new action kinds or world
physics. The same NAND-trained language weights were then used under NOR.

At fixed names, positions and history, `Ada contacts Ben` and `Ada receives Ben`
now predict opposite directed contacts. The OSV lexicon does the same with
`Ben Ada dax` and `Ben Ada vok`; each has a second lexical variant. These are
declared controlled-language meanings, not claims about unrestricted English.
The generator defines them, but candidate inference contains no literal-word
dispatch, semantic lookup table or gold linguistic participant-order mapping.

| Supplied | Learned from observed consequences |
|---|---|
| Token/event boundaries, roster identities and exact name matching | The text encoder's probabilities over the two candidate operand orders |
| Two ordered-contact alternatives and the world/mode mixture computation | Direct/inverse lexical behavior in trained word–layout combinations |
| Native calibration actions with ordered operands and subsequent readings | Earlier acquired pair dynamics, retained here without fitting |
| Evaluator-only oracle metadata, decoded after all collected traces were saved | No new world law, symbolic grammar or action vocabulary is claimed |

Linguistic events receive **no gold participant-order, action-kind, language-ID,
parser or teacher-logit supervision**. Supplied native calibration actions still
have ordered operands; this is not a claim that all action labels have disappeared
from the experiment. Identity grounding and the two alternatives are also supplied.
Full endpoint readings are delivered as feedback after each forecast. The oracle
ordering is a collection discipline, not an operating-system access boundary.

## Frozen execution and results

One prescribed cycle completed: **five fits × 256 updates = 1,280 updates**,
followed by one collection of **138,560 candidate/control rows** in 60 traces.
The evaluator separately recorded **41,600 gold-action native references**.
No scientific fit or collection was retried, selected by challenge score or tuned
after evaluation. All forecasts were saved and validated before oracle decoding.

Each update used 640 episodes and 768 outcomes: 384 original rehearsal outcomes
and 384 new atomic lexical outcomes. Fresh direct/inverse evidence was balanced;
the all-direct rehearsal made total exposure **576 direct : 192 inverse**.
The loss averaged individual observed outcomes. Adam state was fresh; weights
were continued. Training used NAND only and the final checkpoint of every seed.

The fresh bank contains three-to-five-contact chain, fork, cycle, repeated and
disjoint trajectories. Final lexical twins share the roster, calibration,
prefix, names and token positions; only the final lexical item differs. Every
model seed passes under both laws.

| Measurement across five seeds and both laws | Correct / planned |
|---|---:|
| Fresh complete-world predictions | **41,600 / 41,600** |
| Fresh participant orders | **41,600 / 41,600** |
| Entire fresh trajectories | **11,520 / 11,520** |
| Final lexical probes | **11,520 / 11,520** |
| Both members of final lexical pairs | **5,760 / 5,760** |
| Archived-bank complete worlds and participant orders | **20,800 / 20,800** each |
| Archived-bank entire trajectories | **5,760 / 5,760** |

Whole trajectories are conjunctions with the prescribed intermediate feedback,
not free-running rollouts. Seeds, laws, paired views and reused physical histories
are dependent measurements, not 138,560 independent experiments.

The unchanged parent achieves 17,168/41,600 fresh complete worlds, 50% of final
lexical probes and zero both-correct lexical pairs. Continuation repairs **24,432
exact errors with zero new exact errors** on that bank. There are zero
native-correct → candidate-wrong worlds, zero old-correct → updated-wrong worlds,
and zero realized unchanged-bit errors in the primary and retention predictions.

Mean primary NLL is **0.00608004 nats** and mean Brier score **0.0000572342**.
The minimum true-world probability is **0.98408629**, maximum opposite-order
world probability **0.00959745**, and minimum final lexical probability gap
**0.97537125**. Maximum bilingual and synonym TV are **0.00311136** and
**0.00501269**. All frozen cell, conjunction and probability bounds pass.

## The controls establish lexical necessity

Masking only the current word makes each lexical twin's effective inputs and
forecast distributions identical: **maximum paired TV = 0**. Accuracy falls to
5,760/11,520, exactly 50%, with **zero both-correct lexical pairs**. Names and
positions alone therefore cannot solve this contrast.

Swapping direct/inverse words is a valid counterfactual message. All
**11,520/11,520** predictions match the counterpart's world, with **maximum TV = 0**
against that counterpart's canonical distribution. Minimum counterpart-truth
probability is **0.98449633**. The generic raw swapped summary scores against the
unmodified message and reports zero accuracy; that is expected, not a failed
counterfactual control. These views reuse the candidate's exact prefix state and
native likelihoods; prefixes are not counted again as control predictions.

## Structural reuse failed

`contacts/receives` and `dax/vok` were observed in both layouts. `touches/accepts`
were observed only in SVO, and `mip/nuz` only in OSV. The final same-meaning
substitution tests known words in a different layout, with names, layout and
history otherwise fixed. The actual final lexical variant (`contrast_synonym`)
determines the seen/held-out stratum.

| Structural stratum | Complete worlds and orders | Both lexical twins |
|---|---:|---:|
| Seen word × layout | 5,760 / 5,760 — 100% | 2,880 / 2,880 — 100% |
| Held-out word × layout | **2,016 / 5,760 — 35%** | **576 / 2,880 — 20%** |

Pooled transfer accuracy of 67.5% conceals this gap. Every law/seed fails all
four held-out structural checks: cell accuracy, critical probabilities, lexical
pair conjunctions and lexical separation. Held-out mean NLL is **3.57774029**;
minimum true-world probability is **0.00042039** and maximum opposite-order world
probability **0.99857948**. Held-out realized unchanged-bit errors total 2,672.

| Word in its withheld layout | Correct / planned |
|---|---:|
| `touches` in OSV | 0 / 1,440 |
| `accepts` in OSV | 0 / 1,440 |
| `mip` in SVO | 576 / 1,440 — 40% |
| `nuz` in SVO | 1,440 / 1,440 — 100% |

| Seed | Held-out correct per law | Accuracy under each law |
|---|---:|---:|
| 7, 11, 53 | 144 / 576 each | 25% |
| 23, 37 | 288 / 576 each | 50% |

The separate [saved-trace diagnostic](results/lexical-binding-diagnostic-v1.json)
localizes every wrong held-out world to the wrong operand order; each wrong MAP
is the opposite-action foil. There are no wrong-world/correct-order cases. The
pattern is identical under NAND and NOR. Wrong selections can be very confident;
low softmax confidence alone would not reliably trigger clarification. Seed 23's
successful `mip` crossing is itself weak: correct-order probability is about .512.

This is evidence consistent with word/layout entanglement in the text binding.
It does **not** prove that the 474-parameter GRU cannot represent a reusable
solution or that the acquired world needs greater capacity. Warm-start history,
the 3:1 overall direction exposure, uneven per-word evidence and optimization
remain possible contributors. The diagnostic reads saved rows only; it is a
post-result localization, not another model run or a new preregistered decision.

## Exact retention has a probability cost

The old-bank comparison uses the updated encoder against archived parent
forecasts. It is an opened-bank regression check, not fresh generalization.
Earlier checkpoints, traces and decisions remain unchanged.

| Reference | Exact regressions | NLL worsened | Mean NLL increase | Maximum increase |
|---|---:|---:|---:|---:|
| Archived parent on old bank | 0 | **20,800 / 20,800** | **0.0006803064** | **0.0020646568** |
| Gold-action native on fresh bank | 0 | **41,600 / 41,600** | **0.0021633676** | **0.0075154996** |

Against the parent on the fresh bank, NLL improves on 32,112 predictions and
worsens on 9,488; the mean change is −3.71273684 nats. Every pointwise change is
retained. The KEEP rule requires exact retention and the declared canonical
probability bounds; it does not imply zero probability degradation.

## Provenance and verification

| Freeze | Public commit |
|---|---|
| Source, prepared data and protocol before fitting | `7645485bd75c80051a480d6b24aa459a1c8c0d48` |
| All five lexical checkpoints before collection | `12adb6bdb0361a37d36bb2d8a1ddf16cbe225592` |
| Parent language checkpoints | `2db941c2dd4fed97d0b5cef718b24f17ba88bb39` |
| Ten native world checkpoints | `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420` |

The [raw manifest](results/lexical-v1/manifest.json) SHA-256 is
`ab439608fd7c7068b62c5d81796ba618e00be4fa97965b19cc56008b11097d1e`.
The [compressed raw summary](results/lexical-v1/summary.json.xz) SHA-256 is
`327dd4ebff4b7fae82d5edd396feba353b942299a8a5272b5d6e6d952c177d58`.

The stdlib-only [audit](results/lexical-validation-v1.json), with its
[source](audit_lexical_saved.py), reconstructs both decisions using **2,787,821
checks with zero discrepancies**. It verifies 62 source bindings, six prepared
artifacts, 23 historical bindings, all 60 traces and 20 tensor fingerprints.
It executes no model, collector or study scorer. This is separate implementation
within the same team, not independent scientific custody.

The suite contains **817 tests**, including 21 new tests, with **28 locks**.
The initial local run had one existing clean-checkout preflight error while
documentation was uncommitted; that exact test passed after commit. Public source
CI passes [invariants](https://github.com/robosys-labs/cemm/actions/runs/41214328710)
and [source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41214328655).
[PR #69 checks](https://github.com/robosys-labs/cemm/pull/69/checks) track the final
published result head. No research run was repeated for verification.

## Cost and restraint

| Recorded region | CPU seconds | Wall seconds |
|---|---:|---:|
| Five fits | 13.2199 | 13.2488 |
| Shared native-cache preparation | 5.9489 | 5.9494 |
| Forecast chunks | 1.6034 | 1.6010 |
| Scoring and native references | 17.9298 | 17.9319 |

Peak recorded RSS is **431,448 KiB**. Candidate batch-amortized p95 is
**12.490–20.673 μs**, excluding cache construction and not measuring individual
request latency. Serialization, process startup and publication are outside some
recorded regions; their sum is not a complete end-to-end runtime benchmark.

The tranche adds **697 study-source + 237 audit-source + 547 test = 1,481 Python
lines**, with zero model growth. Total retained research Python is **36,513 lines**,
including 16,084 test lines. The program's inclusive 2,000-line objective remains
unmet. These totals include historical experiments, but that does not excuse
presenting the whole implementation as a tiny system.

## Roadmap decision

Retain learned world dynamics, joint dependence, composition, hidden propagation,
timing, bilingual role binding and this lexical gain. G1/G2 development is not
reopened. Original scientific admission, baseline limitations and failed study
decisions remain unchanged. G4 communication and G5 clarification stay later work;
they cannot substitute for reusable meaning or repair confident structural errors
by assumption.

**Select one small neural binding comparison next, not yet implemented or frozen:**
a learned lexical-content factor and learned layout/mention-binding factor with
a small learned interaction, compared with the current GRU architecture. Use no
handwritten inverse rule, word dispatch, language ID, role labels or teacher
grammar. Train both through the same prospectively fixed observed curriculum and
history from a declared initialization policy; a fresh architecture versus the
old warm-start checkpoint alone would confound architecture with prior training.
Keep existing successful weights as retention references.

Cap each language candidate at **474 actual parameters**, report consumed compute
and reuse the existing collector, metrics and acquired worlds. Factorization is
a hypothesis, not a guarantee: the learned interaction could still memorize
word–layout exceptions. Require a fresh frozen word × layout holdout and retain
these opened failures as regression cases. Do not train on these failed cells
and call their later accuracy new generalization. The comparison can establish
a difference under its specified curriculum; it cannot by itself disentangle
every effect of exposure and optimization.

No new workspace, world refit, general framework, corpus ingestion or generic
harness is selected. The next increment should change the binding hypothesis
and measure reusable meaning with the current infrastructure. Broader claims of
structural intelligence remain contingent on that evidence.

Primary artifacts: [design](LEXICAL_STUDY_V1.md),
[protocol](lexical_protocol_v1.json), [decision](results/lexical-v1/decision.json),
[headline](results/lexical-headline-v1.json),
[training](data/lexical-fit-v1/training.json),
[audit](results/lexical-validation-v1.json).
