# Shared-history training wiring and controls

**Public mechanics only; G1 remains HOLD / REVISE.** Two collectors receive
copies of the same four-step sensor/action history. The callbacks named
`predict` capture features; they do not call a neural model or produce a
forecast. Each collector captures current inputs before receiving the next
sensor record. Flat targets preserve unmeasured bits as missing; structured
contact samples require both participants before and after, and set samples
require the participant at both times. Structured contacts retain episode
grouping. Failed replay returns no partial collection, although external
callback effects cannot be rolled back.

The 32 public factorial cases produce 128 measured events, 192 observed
target bits, 64 complete contact samples and 64 complete set samples in 32
structured episode groups. They share one identity block and are not 32
independently drawn worlds. The smoke fits each existing model for one fixed
optimizer step and checks finite losses, gradients and changed parameters;
it does not measure predictive quality or establish that anything generalized.
The report fingerprints inputs and weights and records runtime metadata for
reproduction; matching hashes on different machines is not guaranteed.

The loss functions remain materially different: structured training uses an
episode-level mixture over two modes plus 0.3 times mean set cross-entropy;
the flat model averages marginal joint log loss across measured events. The
same records and one update do not match effective objective weighting,
function class, compute or inference cost. The supplied analytic belief,
role symmetry, local effects and action curriculum remain biases to account
for. The one-step test uses a sequential CPU-only PyTorch installation; it
restores CPU RNG and thread settings, but does not isolate concurrent users
of process-global settings.

Two additional controls are available for development. `NoChange` predicts
the latest actually observed bits for the supplied anchor IDs, updates only
after feedback, and preserves prior values for missing readings; actual
anchor completeness is an external assumption. `EventMemory` freezes
empirical action-local outcome counts from caller-supplied histories and
abstains on unseen or incomplete contexts. It is an unsmoothed relative-slot
local frequency table, not a calibrated full-world or identity-specific
memorization baseline. It cannot check split custody or authenticate inputs.
Neither control has been evaluated on an independent challenge.

The fixture's blocks repeat normalized histories and local samples, even when
opaque IDs differ. Do not split them into calibration or generalization sets
and interpret the results as independent evidence. Before any comparison,
establish genuinely reviewed train/selection/calibration partitions and an
independently held challenge, predeclare sensor and event provenance, add the
remaining full-world controls, account for matched examples and compute, and
evaluate complete trajectories and regressions under the frozen protocol.
The prior G0–V8 manifests remain unchanged.

This tranche contains 7,675 Python physical lines across 58 files including
tests, above the roadmap's practical 2,000-line target. This is a tracked
deviation; later simplification must preserve the correctness evidence.

Reproduce only the wiring report on a CPU-only installation with:

```sh
python -m experiments.predictive_nucleus.shared_training_smoke
```
