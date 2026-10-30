# Alias evidence v1: REVISE_EVIDENCE_FIX

The fresh, fixed-architecture evidence intervention completed, but **failed its
predeclared five-seed self-contact criterion**. G1 remains **NOT_ADMITTED**.
The historical continuation-v1 `STOP_INCOMPLETE_RUN` is unchanged.

## Measured result

| Seed | Ordinary-only self | Observed-alias self | Continuation, each arm |
|---|---:|---:|---:|
| 7 | 8/16 | 16/16 | 704/704 |
| 11 | 8/16 | 16/16 | 704/704 |
| 23 | 8/16 | 16/16 | 704/704 |
| 37 | 8/16 | **8/16** | 704/704 |
| 53 | 8/16 | 16/16 | 704/704 |

Self accuracy improves **40/80 → 72/80 (50% → 90%)**. All eight starting-one
cases still fail at seed 37. Every starting-zero case succeeds. All 136
continuation role-pair conjunctions per seed remain exact. There are **32 self
repairs, zero self regressions, and zero continuation regressions**. No missing
forecast, abstention, terminal failure, or incomplete inventory occurred among
13,690 planned forecasts. The decision is a measured competence failure, not an
execution stop. Neither threshold nor tie handling was changed.

Across all actions, ordinary scores **6,013/6,845 (87.845142%)**, alias
**6,051/6,845 (88.400292%)**. There are also 185 acquisition repairs and 179
acquisition regressions, all at ambiguous acquisition points. All-action
unchanged-bit errors are 384 → 563; self/continuation errors remain zero.
Consequently the preservation claim is scoped to the declared identifiable
queries. The original 95% all-action target remains unmet.

Self joint NLL improves **2.954131 → 0.079189** and Brier **0.991300 → 0.050278**.
These are diagnostics on this public fixed-law bank, not broad calibration.

## Localized remaining failure

Seed 37's failed self-starting-one forecasts have mean wrong-world probability
**49.868504%** and truth probability **49.773975%**. They are not exact ties.
This differs from the original confidently wrong extrapolation: the ordinary
control gives its wrong world 99.253843% mean probability.

Retained tensors show that seed 37 learned the alias-zero outcome in one latent
branch (probability **0.9942864**) but not the other (**0.0047649**). Their equal
prior mixture gives correct active-bit probability **0.4995257**. The small
remaining difference still fails the frozen MAP criterion.

For branch probability r_m = sigmoid(z00_m - z11_m), the first-alias zero-event
loss gradient is -responsibility_m * (1-r_m), where responsibility_m is
r_m/(r_0+r_1). The wrong branch's responsibility is 0.0047694 and its logit-difference
gradient is **-0.0047467**. An identified branch would receive **-0.9952351**,
approximately **210 times** the correction. An actually observed ordinary
11→10 contact gives the same model a posterior [0.0015771, 0.9984229]; a following
starting-one alias then gives the wrong branch gradient **-0.7485143**, about
**157.7 times** its first-alias correction, with no hidden mode label.

These are endpoint tensor/gradient calculations, not a recovered optimization
trajectory. They support a specific latent-mixture credit-assignment hypothesis.
Four successful seeds establish representability for this law; the fifth does
not prove architectural inability. The next fresh experiment moves the same
amount of alias evidence after informative observed acquisition, retaining the
architecture, objective, parameter/update budget and retention criteria.

## Evidence and cost

- Prefit source/data commitment: `f9cc9e66b3ee44db61ea5a4f3b51e75781d4890a`.
- Actual checkpoint/plan commitment: `b2441a8a825a78150a99ae2893d78f8880040bf9`.
- [Protocol](alias_evidence_protocol_v1.json), [study design](ALIAS_EVIDENCE_V1.md),
  [checkpoints/plan](data/alias-evidence-fit-v1/plan.json),
  [result manifest](results/alias-evidence-v1/manifest.json).
- Ten fits, 562 parameters each, identical initial tensors within each of five
  seeds, 128 updates, 340 observed events and 1,538 visible bits per update.
- Sixteen contact substitutions from eight dependent source lineages. No tuning,
  selection/calibration fitting, research retry, or historical-bank refit.
- Fitting CPU **446.100774 seconds**; collection CPU **104.847747 seconds**.
  Consumed compute differs between arms and is reported, not claimed matched.
- 655 local invariant tests passed; all 20 protocol locks and preflight passed.
  Both [prefit invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41063316079)
  and [source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/41063316108) passed.
- Separate JSON-only review verified all 14 result artifact hashes, 15 tensor
  fingerprints, 3,200 implementation hashes, 13,690 forecast receipts and 82,140
  point-metric comparisons. This is internal engineering review, not independent
  scientific custody.

## Size and scope

The inference repair adds two net lines and no parameters. The two reused study
modules add 375 source lines and their tests add 235 lines; all retained research
Python is 27,791 lines, including 12,582 test lines. The active imported source
closure is 2,732 lines, or 2,917 with its historical pin. The inclusive 2,000-line
objective remains unmet. The next intervention reuses this runner/data path;
no new network, checkpoint format, generic framework, or language work is justified.
