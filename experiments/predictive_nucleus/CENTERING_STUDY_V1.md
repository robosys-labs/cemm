# One-bias initialization comparison — prospective protocol

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22).
Continues [PR #74](https://github.com/robosys-labs/cemm/pull/74) at
`db354af1f904f626648f32e7d43fb1519eff80b0`. Registered 2026-11-01.
This file specifies a fresh bounded experiment; it is not a passing result.

## Hypothesis and intervention

The training-only gradient audit found same-sign fitted layout factors in all
three failed unsaturated seeds. That geometry cannot reverse word preference
across layouts. Both successful seeds learned a sign reversal. The audit did
not establish a capacity impossibility or that a different initializer will help.

Compare the standard unsaturated encoder against PR #74's existing initializer:
`layout.0.bias = -(2/3) * sum(layout.0.weight)`. The three identity-marker layouts
have mean `(2/3, 2/3, 2/3)`. This centers initial responses without assigning a
word meaning, role label, inverse rule or layout polarity. The bias stays trainable.

Both arms use the exact same 89-parameter class, forward pass and outcome loss;
the other 88 initial scalars are byte-identical. Actual initial tensors and
fingerprints are retained, with an explicit one-scalar intervention receipt.
No additional learned parameter or production path is introduced.

## Fixed evidence and budget

- Seeds: **7, 11, 23, 37, 53**, with no selection or replacement.
- Exact saturation-v1 training bytes: **1,152 observed NAND outcomes** per update.
- **256 updates**, Adam at **0.02**, gradient clip **5.0**, 120 CPU seconds per arm.
- Python **3.13.5**, PyTorch **2.10.0+cpu**, NumPy **2.3.5**, float64, deterministic
  algorithms and one thread. Equal exposure and budget do not imply equal consumed compute.
- The ten acquired NAND/NOR world checkpoints remain frozen. Language fits use
  NAND only; the same language weights transfer unchanged to NOR.
- Standard controls repeat an earlier deterministic configuration. They do not
  constitute independent new training evidence.

## Freshness and retention

New ordered event families are `relay4` and `fork_return5`, with four/five active
entities and four/five contacts. The generator rejects equivalence to earlier
language challenge schedules under active-entity relabeling, even after ignoring
edge direction. It produces 384 episodes and 1,728 canonical forecasts per law.

Words, layouts and physics are already opened. The eight cells labeled `held`
are absent from training but have appeared in prior evaluation. The fresh claim
is **ordered event-structure transfer**, not new lexical or grammatical discovery.
All layouts, modes, laws, role reversals and four nonuniform anchors remain;
no outcomes are filtered to make a contrast easier.

Bilingual-v1, lexical-v1, binding-v1 and saturation-v1 are explicitly retention
banks. Preserve the archived lexical forecasts, original binding-factor forecasts
and saturation-unsaturated forecasts as their respective references. Also compare
the candidate pointwise with the paired standard arm. Final-word masking and
swapping use the same canonical prefix; native-action references are evaluator-only.

Expected inventory: **243,840** candidate/control/canonical/probe/retention rows,
plus **17,280** separate native reference rows. Pooled rows are dependent views,
not independent trials.

## Decision and custody

The candidate must pass every existing cell, role-pair, lexical-pair, probability,
masking and swapping criterion at every seed and law. Training NLL must be at most
0.05; native, archived and paired exact regressions must be zero; fresh mean NLL
must not increase relative to the paired standard. No failed seed is dropped.
The result is `KEEP_CENTERED_INITIALIZATION` only if all conditions pass;
otherwise `REVISE_CENTERING_HYPOTHESIS`. Preserve all adverse probability changes.

Publish source, protocol and all data hashes before fitting. Publish all ten
actual checkpoints before collection. Fit and collect once into exclusive output
directories; retain failures. Synthetic pipeline tests use toy observations and
random toy worlds, not research checkpoints. Offline publication SHA arguments
are attestations checked against GitHub separately, not authentication.

This is public same-team custody. It cannot independently admit G1, G2 or G3,
establish general language competence or justify production integration. G4 is
not advanced by this experiment. Historical sources, weights and failed decisions
remain unchanged. `ACTIVE_NUCLEUS.md` records the completed outcome after scoring.

## Execution

Use `python -m experiments.predictive_nucleus.centering_run` with stages
`prepare`, `fit`, `collect`, then `score`. Preparation uses
`data/centering-v1`; fitting uses `data/centering-fit-v1`; traces and scoring use
`results/centering-v1/traces` and `results/centering-v1/scoring`. Each output must
be absent before its stage. Fit receives the externally verified source commit
through `--publication`; collection receives the checkpoint-publication commit.
The independent saved-record auditor executes no model or original scorer.
