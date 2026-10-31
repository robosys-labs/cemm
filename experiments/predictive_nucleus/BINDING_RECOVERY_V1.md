# Binding v1: recovered evidence, failed transfer, next minimal ablation

Tracking: #22 and PR #71. Updated 2026-10-31 (Africa/Lagos).
**Recovered arithmetic: REVISE_STRUCTURAL_BINDING. Original process:
STOP_INCOMPLETE_EXECUTION. G3 remains open.**

## What actually ran

The repository, not the earlier unpushed conversation bundle, is authoritative.
PR #71 froze source/data at `cd1c1fd2663677121f7ec81ffa08e521931ef71f`,
published fifteen fitted checkpoints at `b227063a36362d3d3a3d475fc2862b75031e4141`,
and retained the single collection at `b63749c90fd91148f0451bd2e2fd030f3de279cd`.
All three arms used five seeds, 256 updates and 1,024 observed outcomes per update;
NAND training transferred unchanged to NOR. World parameters remained frozen.
This is 3,840 completed language-model updates, not another proposed experiment.

The scorer wrote its complete summary and REVISE decision, then raised
`NameError: name 'json' is not defined` while printing the decision. The original
failure receipt and its prohibition on retries remain unchanged. The saved
`decision.execution_complete` field describes the inventory calculation; it does
not override the failed process or establish scientific admission. No collection,
training or original scorer was rerun for this recovery.

## Saved-evidence recovery

`audit_binding_saved.py` uses standard-library arithmetic and the existing
independently implemented bilingual metric helper, not the study scorer. It
validates every planned forecast and its artifact binding before opening targets,
then reconstructs oracle physics, probability scores, pair conjunctions, mask/swap
controls, exact repairs/regressions and every saved pointwise NLL difference.
Native reference forecasts are audited as saved records, not regenerated.

The audit completes **3,255,288 checks with zero discrepancies** across **262,080
candidate/control/retention records**, **17,280 separately labeled native
references**, **64 source bindings**, **46 historical file bindings** and all
fifteen checkpoint fingerprints. The original protocol thresholds are unchanged.
This is internal saved-byte/arithmetic verification, not independent custody,
proof of complete causal validity, or additional learned evidence.

[Compact result](results/binding-audit-headline-v1.json) and
[full compressed audit](results/binding-saved-audit-v1.json.xz) preserve the scope.
The uncompressed report SHA-256 is
`bcd1255bb158fd0e66d8312b5588a21f944f749f9df1a8264a0273e74916f659`.
The compressed report SHA-256 is
`95c30a64863a651a8a4ca40dc7495924ccc25098f3fbdeb51cc8d444ff0c0acd`.

## Result: structural binding is not repaired

Counts pool two laws and five seeds; repeated views are dependent, not independent
physical trials. Complete-world and participant-order accuracy are distinct.

| Arm | Fresh correct worlds / 17,280 | Held-cell correct worlds / 11,520 | Held-cell correct orders / 11,520 | Old lexical regressions / 41,600 |
|---|---:|---:|---:|---:|
| GRU, 474 parameters | 10,912 | 5,496 | 6,144 | 0 |
| Factor, 89 parameters | 11,680 | 6,304 | 6,528 | 6,240 |
| Additive, 91 parameters | 7,456 | 2,240 | 2,368 | 7,280 |

All arms retain the 20,800 old bilingual exact predictions. The factor model
achieves every fresh exact world at seeds 7 and 37 under both laws, but neither
passes probability quality and lexical retention. Every factor seed fails the
registered combined decision. A pooled gain does not cancel those failures.
The previous 35% result used a different bank and is not a like-for-like baseline.

## Failure localization and implemented next candidate

This is not exclusively an unseen-layout failure. The original factor training
loss remains much higher than the GRU's, and old lexical errors include words
already taught in the delivered training history. Inspection of saved scalar
bottlenecks reveals highly saturated lexical outputs: for example, `vok` at
seeds 7 and 37 has terminal-tanh derivatives about 1.18e-10 and 2.00e-11.
These are local derivatives, not total parameter gradients. They suggest an
optimization bottleneck; they do not prove it caused the failures or rule out
other representation/curriculum issues.

`binding_unsaturated.py` implements **one opt-in 89-parameter ablation**. It removes
only the terminal lexical and layout tanh operations, retaining the hidden lexical
tanh, all learned tensors, feature inputs and learned bilinear readout. At every
original seed its initial tensors are identical to the original factor model's.
It supplies no lexical sign, gold role, language ID, dictionary or inverse rule.
Nonfinite logits fail explicitly; caller RNG and source models are preserved.

The candidate is **IMPLEMENTED_NOT_SCIENTIFICALLY_EVALUATED**. It is not registered
as a historical trainer/checkpoint arm, not enabled in the active runtime, and has
no research fit or challenge result. Its eight synthetic tests establish the
specified ablation, not repaired structural transfer. The old scorer is preserved
under its source freeze; the new audit's output/console path has explicit
serialization and CLI regression tests instead of silently rewriting history.

## Validation and cost of this tranche

Eighteen new tests pass. The final suite discovers **873 tests: 872 pass, one
full-checkout-only preflight is skipped** because this workspace is a verified
source archive without Git ancestry. Local suite time is 80.770 seconds. The
original protocol and all **29 locks** pass. All historical model source,
checkpoints, protocols, datasets and results remain byte-identical. Only the active
status index is updated among existing source files.

The addition is **322 source lines (287 audit + 35 candidate) and 190 test lines**,
512 total. Retained research Python is **38,171 lines**; the inclusive 2,000-line
objective remains unmet. No new model parameters, production changes, G1/G2 reruns
or scientific admission follow. Hosted checks for the original result head were
`action_required`; local success must not be relabeled hosted CI success.

## Reproduction and next bounded task

From a complete checkout of this recovery commit, using a new output filename:

```sh
python -m experiments.predictive_nucleus.audit_binding_saved \
  --repo . --output /tmp/binding-recovery-new.json
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m unittest discover -s experiments/predictive_nucleus/tests -v
```

Keep the original fifteen weights, raw records and failure receipt immutable.
Before another research fit, freeze a paired original-versus-unsaturated
89-parameter comparison with identical initial tensors, observed histories,
optimizer/update budget and all five seeds. Freeze a genuinely fresh structural
challenge; opened old banks are labeled retention references only. Retain the GRU
and additive context, learned-world transfer, probability criteria and exact
regressions. Publish weights before collection, and retain failed seeds without
selection or retries. The candidate must first fit observed training evidence;
passing that diagnostic alone does not admit G3 or justify starting G4.
