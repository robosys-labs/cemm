# Binding v1: prospective structural-transfer comparison

Tracks #22; based on PR #70, `e91e2cf42b9024ea117c967e1fd5cc4f48b97ae2`.
This is a new bounded G3 study, not a restart of G1/G2 or an admission decision.

## Frozen question

Can the unchanged 89-parameter factor model reuse observed lexical meanings
across withheld word layouts, compared with the unchanged 474-parameter GRU and
91-parameter additive control? All three start fresh. No word dispatch, inverse
rule, correct-order label, language ID or new world parameter enters learning.
The factor decomposition, identity lookup and two-contact interface are supplied.

The new challenge adds controlled words `tav/pel` and `zun/vek`, a third VOS
layout, and mixed-layout four/five-contact return/cross sequences. It is not
merely a seed/name permutation of the opened two-layout failure bank. It remains
a public same-team challenge under already known physics, not independent custody.

## Data and exposure

Every arm receives exactly 1,024 observed NAND outcomes per update: 640 fresh
single-contact events and the original 384 bilingual TRAIN events. There are 896
training episodes. Bridge words appear in all three layouts; the other pairs
appear only in their home layout. All eight held cells are absent from training.
No old challenge outcome or prediction enters fitting.

Each law has 384 fresh episodes / 1,728 required forecasts, with 3/6 entities,
both modes, reversed roles and all three layout rotations. Every final lexical
pair has distinct physical consequences; earlier non-discriminating events are
also retained. All actions have full endpoint feedback; this is not open-loop
rollout or general-language comprehension.

Five seeds (7,11,23,37,53), three arms, 256 prescribed Adam updates: 15 fits and
3,840 updates, NAND only. Each trained encoder transfers unchanged to NOR.
Equal history and updates do not imply matched capacity or consumed compute.
The runtime is pinned to Python 3.13.5, Torch 2.10.0+cpu and NumPy 2.3.5.

Planned collection: 51,840 canonical fresh predictions, 23,040 final mask/swap
controls and 187,200 opened-bank retention predictions = **262,080 forecasts**.
The 17,280 evaluator-only native references are separate. Old bilingual and
lexical forecasts are read from the archived lexical-v1 results, never rerun.
Model seeds, role views, layouts, laws and lexical pairs are dependent views.

## Criteria and failure handling

`binding_protocol_v1.json` fixes per-family/word/layout accuracy and order
accuracy >=95%, mean NLL <=0.05, critical truth probability >=0.9, foil <=0.1,
lexical probability gap >=0.8, pair conjunction >=95%, mask/swap invariance,
zero native/old exact regressions, and >=20 percentage-point held-order gain
over the additive control at every seed/law. A GRU tie does not fail the factor
hypothesis. Every local NLL increase, repair and regression remains reported;
undefined infinity-minus-infinity differences are explicit, not dropped.

One fit/collection attempt, no retry, no checkpoint selection and no post-score
tuning. Any incomplete or invalid inventory stops. Historical results/thresholds
are immutable. A successful bounded comparison would not automatically close G3.

## Reproduction and publication

The deterministic recipe and `binding_freeze_v1.json` commit the exact seven
prepared-file hashes, including the complete source/native/history manifest.
Generated data need not be manually transcribed before fitting; `prepare`
recreates it byte-for-byte and `verify` checks the public commitments.

```sh
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
ROOT=experiments/predictive_nucleus
python -m experiments.predictive_nucleus.binding_study prepare --output "$ROOT/data/binding-v1"
# Only after source/data commitment publication; use the actual verified commit:
python -m experiments.predictive_nucleus.binding_study fit --data "$ROOT/data/binding-v1" --output "$ROOT/data/binding-fit-v1" --publication "$SOURCE_COMMIT"
# Only after actual checkpoint bundle publication:
python -m experiments.predictive_nucleus.binding_study collect --data "$ROOT/data/binding-v1" --fitted "$ROOT/data/binding-fit-v1" --output "$ROOT/results/binding-v1/traces" --publication "$WEIGHTS_COMMIT"
python -m experiments.predictive_nucleus.binding_study score --data "$ROOT/data/binding-v1" --fitted "$ROOT/data/binding-fit-v1" --traces "$ROOT/results/binding-v1/traces" --output "$ROOT/results/binding-v1/scoring"
```

These are reproduction commands, not permission to replace the registered run.
Publication arguments are externally verified caller attestations; the offline
runner checks bytes, not network authenticity or independent custody.

The narrowly scoped one-shot GitHub workflow performs **collection/scoring only**
when the checkpoint-publication commit creates its request file. Subsequent doc
commits skip it; manual reruns are disabled by its attempt guard. It preserves
raw data/traces/results or failure on this research branch, using a head check
before its non-force push. It never changes production or fits another model.

## Implementation scope

Reuse the existing model definitions, `fit_comparison`, native checkpoint loader,
pack/forecast path and proper-score functions. Three thin study modules add data,
publication/collection and scoring, with 17 focused tests. No native inference,
learning, checkpoint, language-model or historical result file changes.

The original inclusive 2,000-line research target remains unmet. Source/test LOC,
actual cost, final verification and scientific outcome belong in the result
record; passing tests alone is not evidence of repaired structural transfer.
