# Keep layout coordinates; close the bounded G3 fitting comparison

Tracks [#22](https://github.com/robosys-labs/cemm/issues/22),
[PR #76](https://github.com/robosys-labs/cemm/pull/76), stacked on #75.
Recorded 2026-11-01. **KEEP_LAYOUT_COORDINATES; execution complete.**

[Prospective protocol](COORDINATE_STUDY_V1.md) ·
[full saved summary](results/coordinate-v1/scoring/summary.json.xz) ·
[headline](results/coordinate-headline-v1.json) ·
[separate saved-record audit](results/coordinate-validation-v1.json) ·
[execution receipt](results/coordinate-execution-v1.json).

## Result and controlled intervention

The existing 88-parameter coordinate encoder passes every frozen criterion at
all five seeds and both acquired world laws. It fixes the remaining seed-11
failure without adding capacity, training examples, updates or gold role labels.
This closes the selected fitting comparison; it does not complete full G3.

The centered control has 89 parameters; direct layout responses remove one
redundant scalar. Both arms start with the same function on all three supported
identity masks and the same 85 nonlayout scalars. All initial states and response
receipts are retained. Both use the exact 1,152-event observed NAND tape, Adam at
0.02, gradient clip 5.0 and 256 updates, at seeds 7/11/23/37/53. The ten
562-parameter acquired world checkpoints remain frozen; the same language weights
transfer to NOR. Every centered control exactly reproduces its archived initial
weights, final weights, training curve and final NLL.

The changed coordinates also change Adam and clipping geometry. The result
supports this parameterization under the frozen optimizer, not a proof that the
old 7:1 ordinary-gradient sensitivity alone caused the previous failures.

## Same-bank fresh evidence

The new event structures are fanout_cross4 and chain_shortcut5. Words/layouts and
the eight training-withheld cells have appeared in previous evaluations. These
are per-step complete-world predictions conditioned on observed-prefix feedback,
not autonomous open-loop rollouts. Counts pool dependent laws, seeds and paired
views; they are not independent physical trials or a historical accuracy series.

| Metric on this same new bank | Centered, 89 parameters | Coordinates, 88 parameters |
|---|---:|---:|
| Complete worlds correct | 15,278 / 17,280 (88.4144%) | **17,280 / 17,280** |
| Training-withheld-cell worlds correct | 9,750 / 11,520 | **11,520 / 11,520** |
| Mean NLL, nats | 0.371709152 | **0.004349190** |
| Mean joint Brier | 0.151489888 | **0.000026217** |
| Lexical pairs correct | 1,672 / 1,920 | **1,920 / 1,920** |
| Reversed-role pairs correct | 1,568 / 1,920 | **1,920 / 1,920** |
| Untouched-bit errors | 1,529 | **0** |

The candidate repairs **2,002** previously wrong fresh worlds and breaks **zero**.
All repairs belong to seed 11: 1,012 NAND and 990 NOR. Its observed training NLL
falls from **0.33604226** to **0.00361210**. Every coordinate training fit meets
the unchanged 0.05 threshold.

Minimum fresh critical-case true-world probability is 0.99025882, maximum wrong-order
probability 0.00590075, and minimum critical lexical gap 0.98854516. Masked and
swapped total-variation discrepancies are both zero. These meet the frozen
probability/control gates; they do not establish general uncertainty calibration.

## Retention and adverse changes

All **114,240 / 114,240** canonical candidate predictions across the five opened
banks are correct. Native, archived and paired exact-regression counts are zero.

| Retention bank | Correct / planned | Repairs versus paired centered control | New exact errors |
|---|---:|---:|---:|
| Bilingual | 20,800 / 20,800 | 0 | 0 |
| Lexical | 41,600 / 41,600 | 2,080 | 0 |
| Binding | 17,280 / 17,280 | 1,606 | 0 |
| Saturation | 17,280 / 17,280 | 2,012 | 0 |
| Centering | 17,280 / 17,280 | 2,012 | 0 |

Zero exact regressions does **not** mean every probability improves. Fresh NLL
improves on **10,503**, worsens on **6,773**, and ties on **four** records. Eight
paired historical bank/law/seed mean-NLL comparisons worsen slightly: bilingual
seeds 23/37 and binding seeds 23/53, under both laws. The unchanged gate requires
exact retention and fresh mean-NLL nonincrease; no post-outcome veto or relaxed
criterion was introduced. Full differences remain in the saved summary.

## Publication and verification

- Source/protocol/data before fitting: `9ee7f240d00d896c012217dbcdca6db684f27f64`.
- All ten actual checkpoints before collection: `c71afe2d7f83230a7980e5b0a946c397c38e87ac`.
- All raw forecasts before scoring: `52b66d6b81c05f72d1cab559406f95940fbd0c08`.
- **278,400** forecasts/probes/retention records plus **17,280** separately
  labeled native references; no missing seed or research retry.
- **954 tests pass**, no skips/failures/errors, in 87.392 seconds; original
  protocol, all **32 locks** and frozen-input preflight pass.
- The stdlib saved-record audit performs **3,966,958 checks with zero
  discrepancies**, covering 82 source and 99 historical bindings, all ten initial
  states/checkpoints and every saved record. It executes no model or original
  scorer. A separate same-team review reconstructs all **130 decision checks**.

This remains public same-team evidence, not independent challenge custody.
Fitting used 33.903276 CPU seconds; cached prediction regions used 6.339827 CPU
seconds, excluding preparation, serialization, scoring and native references.
Equal updates/exposure do not establish matched consumed compute or service latency.

The study adds **1,132 Python lines**, reusing existing inference, objective,
controls and metrics. Retained research Python is **41,850 lines**, including
18,110 test lines. The inclusive 2,000-line target remains unmet. The language
model shrank by one parameter; the research implementation did not shrink.

## Next tranche: acquire a native effect before naming it

**PLANNED_NOT_IMPLEMENTED_NOT_FITTED.** Stop the initialization/optimizer sequence.
Keep this accepted result and all earlier failures/checkpoints unchanged. G1/G2
development progress and their original formal-admission limits remain intact.

The [native-effect inventory](results/native-effect-inventory-v1.json) finds
exactly **256 contact actions and zero sets per law** in the acquired-world
training tapes. All four intervention tensors, and the set-only background input
column, remain identical to initialization in all ten final world checkpoints.
The branch is neural, not a hardcoded assignment, but it has not acquired set
outcomes. Complete setup observations are not evidence of accurate set forecasts.
This inventory ran no models or new scientific forecasts.

The next substantive step is fresh nonverbal before/action/after observation of
the existing set action, covering both prior bit values and both requested values.
Keep **562 total world parameters**; permit updates only to the **57 intervention
scalars** and **11 set-only background weights**. Keep both contact pair modules
and all other parameters unchanged. The addressed entity, requested value and
action family remain supplied; target-state likelihood and set-conditioned
background behavior must be learned from subsequent observations. Never copy the
requested value directly into the predicted world.

Before fitting, freeze the new tape, split lineage, resource/update budget,
permitted parameter mask, acquisition gates and complete retention checks. Use
all five seeds and retain failures. Contact inputs do not activate the set-only
column, providing a preservation argument that must be verified against actual
tensors and predictions, including earlier language banks and probability changes.
Do not repurpose opened challenge records as new training evidence.

Only after native acquisition passes, freeze the acquired worlds and ground
effect selection as well as roles. Target at most **88 language parameters**;
this is a prospective design target whose feasibility and retention are not yet
validated, and the final budget/controls must be preregistered before fitting. A
word-independent alternative set can contain contact(A,B), contact(B,A), set(A,1)
and set(B,1). This illustrates a later lexical task restricted to setting one;
native acquisition itself covers both requested values. Endpoint outcomes train
alternative probabilities without gold action-kind or participant-order labels.
Evaluate new bilingual surfaces, synonyms, reversed
roles, changed layouts, new identities and withheld combinations, with the
relevant message/grounding, text-only, supervised-parser and neural controls.
This output extension is not yet implemented or validated.

G3 still needs reusable acquired effects and their linguistic realizations beyond
two operand orders. General language, G4 communication, G5 durable learning,
corpus expansion, independent admission and production integration remain later
work. No new operator, workspace, world-physics implementation or generic harness
is selected by this result.
