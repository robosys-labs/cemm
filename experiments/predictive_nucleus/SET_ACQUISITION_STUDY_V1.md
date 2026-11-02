# Native set acquisition with contact and language retention

Tracks [#22](https://github.com/robosys-labs/cemm/issues/22); continues the accepted
[PR #76](https://github.com/robosys-labs/cemm/pull/76) result at
`2ba2843b3a456957b9c4f0b789e42e90387354c8`. Registered 2026-11-02.
This is the prospective protocol, not a successful result.

## Smallest new capability

The accepted layout-coordinate selector resolves the bounded fitting problem.
It selects between supplied contact orders; it has not learned another effect.
The existing world model has a native set branch whose weights remained at
initialization because acquired-world training contained no sets. Setup readings
in language episodes did not establish learned set prediction.

Keep the exact 562-parameter world. Learn only all **57 intervention scalars**
and **11 weights in background.0.weight[:, 2]**, the set-only input column.
The other **494 scalars** must remain bitwise identical after every update.
The addressed entity, action family and requested value are supplied. Neural
likelihoods, including spectator persistence, must fit observed outcomes; the
predictor never writes the requested value directly into its forecast.

## Fixed data and optimizer

Train each of the ten inherited NAND/NOR checkpoints, seeds **7, 11, 23, 37, 53**,
on the same new **48 one-event episodes**: eight initial three-entity states,
three addressed slots and two requested bits. Every prior/request combination
occurs twelve times. No evaluation records, hidden mode, gold semantics or
language labels enter the fitter. Reuse the existing observed replay and full
joint likelihood; make no changes to earlier model, objective or inference files.

Use **256 updates**, fresh Adam at **0.02**, betas **0.9/0.999**, epsilon **1e-8**,
zero weight decay, gradient clip **1.0**, and a **180 CPU-second ceiling per fit**.
Mask before clipping, assert complementary bytes after every step and retain
the actual initial/final losses, full curve, checkpoint identities and costs.
Do not restore forbidden updates to hide them. No selection, early stopping,
extra updates or scientific retries. Retain complete failed-fit endpoints too.

Runtime: Python **3.13.16**, PyTorch **2.10.0+cpu**, NumPy **2.3.5**, float64,
one thread, deterministic algorithms. Earlier coordinate execution used Python
3.13.5; checkpoints are unchanged and numerical retention is checked explicitly.

## Fresh composition and controls

Each law has **384 episodes / 1,920 forecasts**, with fresh opaque identities
and three to six entities. Coherent five-action sequences cover repeated sets,
alternating values and set/contact bridges. All eight first-three-bit anchors
and both requests appear; spectator bits are deterministically seeded. Contact
bridges include both persistent hidden modes and **128 role-reversal pairs**.
Mode/reversal duplicates are omitted for set-only families.

All four atomic set input tuples are deliberately covered in training. Novelty
is in identities and action compositions; this does not test an unseen set truth
table. Audit identity, canonical blueprint and template split overlap before
fitting. Full observed feedback carries each action's consequence into the next
prediction; this is not an autonomous five-step rollout.

Compare the updated world with its inherited no-update parent and a deterministic
no-change control on identical histories. The latter is computed once per law
and reused under seed labels, not presented as five independent controls.
There are **1,664 identifiable and 256 ambiguous forecasts per law**. Best
expected raw exactness is 93.3333%; the original identifiable/probability
distinction must be preserved. No oracle support is used by the participant.

## Frozen acceptance

Every law and every seed must pass:

- Complete forecast coverage and the prescribed update count.
- At least 95% identifiable complete-world, identifiable trajectory and role-pair
  conjunction correctness; zero unsupported MAP worlds and zero errors on known
  fixed coordinates. Singleton support therefore effectively requires 100%.
- Mean oracle KL at most 0.05 nats in each nonempty family/information stratum;
  maximum ambiguous total variation at most 0.1.
- Set NLL at most 0.05 in every nonempty family/entity-count/prior/request/changed cell; at
  least 0.1 nats mean improvement over parent and no-change on changed sets.
- No identifiable previously-correct native prediction becomes wrong.
- Observed training NLL at most 0.05.

Infinite no-change log loss is retained as infinity, never clipped. Every actual
ambiguous error, repaired/broken identity, adverse probability change, trajectory
and subgroup remains in the saved reports. Counts include dependent views.

## Preserve the accepted language model

Use the **unchanged 88-parameter coordinate encoder** on all six opened banks:
bilingual, lexical, binding, saturation, centering and coordinates. Compare its
**131,520 canonical forecasts** with the archived accepted coordinate forecasts;
no old fit or reference forecast is rerun. Require zero exact regressions,
identical order probabilities and maximum absolute world log-probability change
at most **1e-10**, retaining every point's NLL change.

Contact weights alone do not guarantee bitwise identical downstream probability:
language setup includes set context. Its shared likelihood cancels from the mode
posterior mathematically, but finite arithmetic can leave tiny changes. The
prospective tolerance covers numerical residue rather than relaxing correctness.

## Execution and decision

Publish source, recipe, protocol and data hashes before fitting. Publish actual
checkpoints before collection; publish all **189,120 planned forecasts** before
scoring. Each stage uses exclusive output paths and retains failures. Protocol
and data commitments bind exact bytes. These are internal reproducibility
controls, not independent challenge custody.

Incomplete execution stops. A complete run passing every criterion yields
`KEEP_NATIVE_SET_ACQUISITION`; otherwise retain
`REVISE_NATIVE_SET_ACQUISITION`. Do not retune on this opened challenge.
Only after a pass should a new frozen study ground effect selection and roles
from endpoints without gold action-kind/participant-order labels. The current
88-parameter language budget remains a prospective target for that later task.

G1/G2 development gains and scientific limitations remain intact. Full G3 and
G4 are not advanced by this study alone. No new operator, workspace or production
interface is introduced. Record added/total code size honestly: the inclusive
2,000-line objective is already unmet and a small parameter count does not fix it.
