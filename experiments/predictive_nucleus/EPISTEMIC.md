# G1c: evidence, active probes and predictive-model mismatch

**Research status:** KEEP as a small **unsealed diagnostic**, **G1 NOT ADMITTED**.
Tracks [#22](https://github.com/robosys-labs/cemm/issues/22); stacked on
[PR #23](https://github.com/robosys-labs/cemm/pull/23), [#24](https://github.com/robosys-labs/cemm/pull/24),
[#25](https://github.com/robosys-labs/cemm/pull/25), [#26](https://github.com/robosys-labs/cemm/pull/26),
and [#27](https://github.com/robosys-labs/cemm/pull/27). Production CEMM / Hybrid,
root AGENTS, five operators, ABI and effect authorization are untouched.

## Reason for this experiment

Historical nucleus checkpoints showed that atomic directed effects could work yet
break under composition, equivalently reordered clauses and new-word contexts;
active vs passive clarification could tie; and contextual priors sometimes lost
to shuffled controls. These are warnings against taking a high accuracy number
from a single optimizer seed or a temporary top-1 meaning as a learned mechanism.
The earlier G1b recurrent baseline produced a 64.8% mean full-state validation
rate versus 48% persistence *on its own different unprobed task*. This is **not**
a comparable head-to-head with the figures below. The user-supplied shared-chat
URL could not be fetched in the connected environment; checkpoint lessons were
cross-checked against the linked research issue and available project history.

The original frozen G0 world includes a **per-episode latent contact orientation**:
same observations and actions can lead to different future complete states. In
fair first-contact binary states, deterministic exact accuracy has a 62.5%
Bayes ceiling. Declaring those unknowable cases "model errors" is scientifically
wrong; silently picking one orientation is equally wrong.

## What is supplied / what is actually learned

- **Supplied bias:** binary sensor geometry, opaque stable IDs, 2 anonymous
  alternative participant-role orientations, a shared pairwise neural kernel,
  two-party output scope, physical set/contact affordances, and a bounded
  exact 2×2^n possible-world posterior (3–6 entities, at most 128 slots).
  This is an *explicit inductive bias*, not proof that roles arise spontaneously.
  The current prototype **does not** model self-contact or two-source dynamics.
- **Learned:** a 1,446-parameter neural joint distribution over the two observed
  participants' next bits and a neural physical-intervention distribution.
  Training loss marginalizes over one **persistent** anonymous orientation
  per episode. No oracle direction label is used in training; two mode indices
  are permitted to swap between model initializations.
- **Never imported:** simulator physics/XOR tables, future hidden states, gold
  current full world, handwritten word grammar, teacher weights, effect
  authorization. Training extracts only **sensor-visible pre/post** pairs and
  ignores incomplete pairs rather than imputing unseen truth.
- **After learning:** numerical tables may cache the small neural kernel's
  own frozen predictions; these are computed from weights, **not** copied from
  simulator outcomes or evaluator truth.

## Evidence-aware state machine

Every action has a pure forecast. Only a subsequent, identified sensor event
commits the belief update. Hypotheses persist coherently across successive
interactions. A partial reading conditions only what was seen. A source/time
receipt is counted once; conflicting reuse of an evidence ID is rejected.

| Diagnostic | What it means | Behavior |
|---|---|---|
| INSUFFICIENT_EVIDENCE | Distinct plausible hypotheses predict different outcomes | Retain alternatives, abstain on that action, propose an informative contact |
| PREDICT_WITH_EVIDENCE | All sufficiently likely complete-world outcomes agree about this action | Predict even when unrelated latent details remain unresolved |
| ABSTAIN_UNRESOLVED | Low complete-world confidence, but no available contact distinguishes the alternatives | Abstain; never invent certainty |
| CONFLICTING_EVIDENCE | A new reading fits another mechanism but contradicts strong **prior** evidence for a fixed mechanism | Flag a provenance/possible change-point investigation, abstain |
| MODEL_MISMATCH_CANDIDATE | All known hypotheses assign extremely low probability to the reading | Quarantine unsupported effects, abstain; not a verdict about physics/sensor |
| EVIDENCE_SUPPORTED | New observed feedback is consistent with the filtered model | Continue observing with deduplicated event IDs |

The model cannot *prove* predictive failure from one noisy or false reading:
only independent reliable measurements, counterfactual tests and external
oracle evaluation can confirm a true mismatch. "Wrong confident" is scored
as a model error by the **independent evaluator**, never inferred from the
learner's own self-agreement.

The probe planner maximizes expected information gain **over observed future
sensor outcomes**, not uncertainty alone. It subtracts query cost and can
propose a two-step physical intervention→contact plan when all present contacts
are uninformative. Proposal has no effect itself and does not authorize an
external physical or production action. Actual feedback is required between
steps; a no-value probe is correctly omitted.

## Separate, frozen version 2 experiment protocol

The original G0 manifest and lock are untouched. The versioned
epistemic_protocol_v2.json has a distinct SHA-256 lock. This protocol freezes
train/calibration/diagnostic seed roles, two-step budget, proper scores,
abstention/mismatch strata, negative controls, and proposed independent gate
thresholds **before any external challenge**. The original G1 challenge is
not repurposed. A fresh, independently authored/custodied challenge is still
required before G1 admission.

## Reproduce observed-only diagnostic

From repository root, with Python >=3.11 and CPU PyTorch:

\`\`\`sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.probe_trial \
  --train 1200 --calibration 250 --validation 100 \
  --steps 300 --seeds 7,11,23,37,53
\`\`\`

Five optimization seeds; 1,200 training episodes each over five train-world
seeds; 250 calibration episodes across disjoint seeds; 100 validation worlds
per optimizer seed, two reversed target queries per world. Probe feedback in
this diagnostic is **fully observable**. The learned kernel is fitted only on
train observations; temperature is selected only on calibration observations.
All target truth is accessed by a separate evaluator only after prediction.

| Policy/control | Mean exact complete world | Both reversed queries exact | Mean physical probe steps |
|---|---:|---:|---:|
| Learned + informative active probes | **100.0%** | **100.0%** | **1.08** |
| Learned + random two contacts | 98.5% | 97.0% | 2.00 |
| Learned + no probes | 50.5% | 27.0% | 0 |
| Learned + probes, then erase latent memory | 42.7% | 18.4% | 1.08 |
| Same architecture, outcomes shuffled during training | 43.9% | 26.0% | 1.91 |
| Same architecture, untrained weights | 30.3% | 16.2% | 0 |

All five model seeds achieved 100% post-probe on this *tiny, deterministic,
unsealed binary world*. Probe models had zero mismatch alarms here. Scalar
temperature selected **0.5** on sensor-only calibration across all five seeds.
Full-world ECE in the post-probe diagnostic rounds to 0.0, which **does not**
establish calibration on partial sensors, changed physics or independent
challenges. Mean outcomes in the table are **correlated within world and
shared world seeds**; they are not independent trial-based confidence intervals.

The learned kernel has **1,446 parameters**. A local run included **38 passing
unit/invariant tests** across G0/G1c. The runner prints source Python LOC
(including tests), peak process RSS, elapsed CPU time and p50/p95
plan/forecast latency. Local peak process RSS was ~327 MiB with PyTorch loaded;
p95 active planning/forecast was ~1 ms. Hardware: CPU, PyTorch 2.10, Python
3.13. These are environment-specific, not production performance guarantees.

### What would falsify the claim

1. A fresh independent challenge of distinct simulator mechanism families or
   unexpected effects exposes the two-orientation function-class limitation.
2. Real partial/occluded/noisy evidence triggers false certainty or excessive
   mismatch flags; measure NLL, Brier, full-world ECE and selective risk.
3. A matched-budget flat recurrent and memorization control performs equally
   well, negating any distinct compositional/efficiency advantage.
4. An unadmitted new structure (self-contact, multi-source influence, deeper
   cycles) needs hand-coded parser/effect branches rather than a learned
   extension; this is a representation problem, not missing language.
5. Probe costs exceed the achieved decision gain or evidence is double counted.

**Next:** freeze independent evidence-aware G1 challenge with a reviewer; test
probe-vs-random at *matched realized costs*, full partial observations and
new hidden physics, plus parameter/compute-matched flat recurrent baseline.
Do **not** begin G2–G5 or Wikipedia ingestion on the strength of this diagnostic.
