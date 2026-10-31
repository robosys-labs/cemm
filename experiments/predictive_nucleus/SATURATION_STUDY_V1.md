# Paired terminal-activation ablation — prospective v1

Tracks #22, continues #72 at `594dc715d7562587568858be4ad62bc51c581786`.
Status at source freeze: **PREPARED_NOT_FITTED**. G3 remains open. Historical
REVISE/STOP decisions and all old learned weights are immutable.

## Question and isolation

Compare the original factor with the existing opt-in unsaturated factor. Both
have **89 trainable parameters**, identical initial tensors at seeds
7/11/23/37/53, identical observed histories, Adam learning rate .02, clipping 5,
and 256 updates. Only the two terminal lexical/layout tanh operations differ.
The hidden lexical tanh and learned bilinear readout remain. No gold participant
order, dictionary dispatch, language label or handwritten inverse rule enters
training. Equal updates do not establish identical consumed CPU.

The previous data suggested saturation, not a demonstrated causal explanation.
This experiment tests that bounded hypothesis and retains failed seeds. Historical
GRU/additive results are context, not fresh-bank superiority comparators.

## Fresh data and explicit retention

Use all 1,024 previous binding TRAIN outcomes unchanged, plus 128 single-contact
NAND observations teaching **kef/ruz** at SVO and **wom/jit** at VOS. Every new
word and all three layouts are observed, but eight new word-layout cells are
withheld. Every arm receives 1,152 observed outcomes per update, with equal event
weighting. No challenge or archived prediction is fitted.

The fresh bank uses four-participant diamond4 and five-participant bridge5
sequences, four nonuniform initial patterns, both physical modes, both role
directions, three layout rotations and final lexical twins. Each law has 384
views / 1,728 canonical forecasts. All 192 final lexical pairs per law are
physically discriminating, as checked by a separate truth-table implementation.
No outcome-based filtering is used. These are fresh lexical cells and sequences,
not a novel grammar, unseen physics, independent authorship or general language.

Each NAND-trained encoder transfers unchanged to NOR. The two arms produce
34,560 fresh canonical predictions plus 15,360 mask/swap probes. Labeled opened
bilingual/lexical/binding retention contributes 159,360 predictions: **209,280
planned candidate/control/retention records** total. The 17,280 gold-action native
references are evaluated separately after all candidate records are validated.
All counts pool dependent laws, seeds, lexical and role views.

## Frozen criteria

Keep the prior cell/pair thresholds: at least 95% exact worlds and participant
orders per family/word/layout, mean NLL <=.05, critical truth probability >=.9,
foil <=.1, lexical probability gap >=.8, role/lexical conjunction >=95%, and
mask/swap invariance within 1e-10. Additionally require observed-training mean
NLL <=.05, no previously correct native/archived/paired exact regressions, and
no mean fresh NLL increase against the paired original. All local proper-score
losses and exact repairs/regressions remain reported.

All ten seed/law criterion groups must pass for `KEEP_UNSATURATED_BINDING`;
otherwise `REVISE_SATURATION_HYPOTHESIS`. A tie would not establish an exclusive
activation advantage. Training-fit diagnostics never select seeds for collection.
An incomplete/invalid inventory is an execution failure, not a scientific pass.
The original scientific gates remain unchanged, including independent custody.

## Execution and guardrails

Publish source, protocol, recipe and `saturation_freeze_v1.json` before fitting.
Publish actual fitted checkpoints before collection. Offline publication SHAs
are externally verified attestations, not authentication. Exclusive output paths
and a one-attempt CI request preserve failures; no retry, early stopping, seed
selection or closed-bank retuning is permitted.

```sh
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
ROOT=experiments/predictive_nucleus
python -m experiments.predictive_nucleus.saturation_run prepare --output "$ROOT/data/saturation-v1"
python -m experiments.predictive_nucleus.saturation_run fit --data "$ROOT/data/saturation-v1" --output "$ROOT/data/saturation-fit-v1" --publication "$SOURCE_COMMIT"
# After publishing the actual weights, exactly one collection:
python -m experiments.predictive_nucleus.saturation_run collect --data "$ROOT/data/saturation-v1" --fitted "$ROOT/data/saturation-fit-v1" --output "$ROOT/results/saturation-v1/traces" --publication "$WEIGHTS_COMMIT"
python -m experiments.predictive_nucleus.saturation_run score --data "$ROOT/data/saturation-v1" --fitted "$ROOT/data/saturation-fit-v1" --traces "$ROOT/results/saturation-v1/traces" --output "$ROOT/results/saturation-v1/scoring"
```

The collector does not decode oracle files. Forecast-cache preparation uses only
observed prefixes, and final probes do not mutate the true prefix. The scorer
checks every file, model identity and required forecast before decoding targets.
The runtime/learning/checkpoint APIs and production authority are unchanged.
The original inclusive 2,000-line objective remains unmet; new code is study
orchestration, not a larger nucleus or another runtime framework.
