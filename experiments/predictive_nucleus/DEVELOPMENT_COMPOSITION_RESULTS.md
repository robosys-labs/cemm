# Public composition diagnostic: results

**Decision: REVISE; G1 NOT RUN.** The reviewed v2 protocol was committed
before this public run. The [complete per-case artifact](results/public-composition-v2-1f6f5bb.zip)
is retained in the research branch; it is the exact ZIP from
[CI run 40682686408](https://github.com/robosys-labs/cemm/actions/runs/40682686408).
Its ZIP SHA-256 is `c0dc4f5e696d71b237242df67e7ecc8b8e941094e29afd0febfb47efce38b08f`.
It preserves per-case records and weight fingerprints, not trained model
checkpoints; hashes cannot reconstruct weights.
The five model seeds reused the same 64 public cases, so these are not 320
independent worlds. Models received the realized feedback after each forecast.

## Exact complete-world forecasts by action

Each cell is correct forecasts out of 64 queries, per seed. Flat ranges show
the five seeds; the other figures were identical across seeds. The event
control abstained on all observation-only actions.

| Action | Structured | Flat range | No change | Local event + persistence |
|---|---:|---:|---:|---:|
| First contact | 40/64 | 8–16/64 | 32/64 | 40/64 |
| First set | 64/64 | 6–20/64 | 32/64 | 64/64 |
| Observe | 64/64 | 10–18/64 | 64/64 | 0/64 answered |
| Second contact | 58/64 | 16–22/64 | 32/64 | 40/64 |
| Second set | 64/64 | 16–23/64 | 32/64 | 64/64 |

Contact/set only, the structured model got 226/256 queries correct per seed;
flat got 52–74/256, no change 128/256 and the local control 208/256. These
counts are repeated action queries on public constructed histories, not
independent samples or evidence of architectural superiority. The models
have different supplied biases, training objectives and compute. The local
control explicitly assumes persistence for nonparticipants.

The first-contact majority limit of 40/64 was independently enumerated before
the run under a reset deterministic predictor restricted to the initial sensor
turn. A separate **post-run descriptive** grouping by the entire delivered
history through the second contact yields 28 groups and a majority maximum of
58/64. Both are bounds for this finite fixture and the stated information
restriction, not thresholds or confidence intervals for G1. The structured
counts match those fixture bounds; this does not prove independent transfer.

As a **post-run descriptive** check, all five one-step forecasts in a case were
correct for 34/64 structured cases per seed, 0–2/64 flat cases, and 4/64
no-change cases. This is not a free-running rollout: actual feedback was
delivered between forecasts. The local event control answered zero complete
five-step cases because it abstained on every observe action.

## Accounting and interpretation

The no-change control assigned represented probability zero to the truth on
128/256 contact/set queries per seed, so its uncapped mean log loss is
infinite; the separately archived clipped value must not replace it. The
structured filter returned `EVIDENCE_SUPPORTED` *after feedback* on some
previously wrong MAP forecasts; this status is not a certificate that the
prior forecast was correct. None of the recorded structured updates retained
an unconditioned forecast because of the likelihood threshold.

All evaluation contact and set tuples occurred in training. Eight of 64
evaluation cases matched the ordered contact list and ordered set list after
grouping by type, not the full chronological trajectory. Evaluation also
uses a first contact operand-rank pair and first set target rank absent from
training, plus a differently placed observe action. These confounds prevent attributing flat-model failures to
any one cause. The flat model's 336 input weights connected to always-zero
training columns remained unchanged; all 21 observe-column weights changed.

Both learners used 200 updates, but compute was not matched. On this runner,
structured fit took 0.294–0.295 seconds for four seeds and 0.982 seconds for
the first; flat fit took 0.626–0.630 seconds. The first structured outlier's
cause is unproven. Timings are not stable FLOP comparisons. The tracked tree
was clean, untracked files were present, and PyTorch deterministic algorithms
were disabled. Cross-machine bitwise reproducibility remains unestablished.

Before a G1 decision, review a fresh independent oracle and challenge,
matched examples and compute, a complete-world memorization control,
sensor/event provenance and the treatment of unidentifiable first contacts.
Do not retune against an opened fixture and call the result a held-out test.
