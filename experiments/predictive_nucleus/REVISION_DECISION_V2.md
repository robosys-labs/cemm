# G5 outcome-trained correction v2 — TRAIN-only stop (2026-11-04)

**Decision: REVISE_OUTCOME_UPDATE_TRAIN_ONLY.** Do **not** promote the fitted one-scalar updater or score the reserved challenge from this candidate. Preserve the accepted zero-parameter scoped memory baseline in PR #86. G5 and formal admission remain open.

The prospective protocol was frozen at `7697a7f37692f8e5acb5d08a48e503a6c16fcef9`; candidate source and initial tests at `a5f1ce194cd4e419a0e8df044f2a143a68c2d468`. Ten trained switch rates and full grid TRAIN NLL curves were published in `results/revision-v2/train-fitted.json` at `4e3090f256440f10e8416f0943d451a839663cc4` **before** the additional prefix audit. The post-fit audit was added at `6447eac62087b6be45066b4e824ccdd8380b9281`; it is a diagnostic of a roadmap-required uncertainty property, **not** a pre-registered independent challenge score.

## Recorded evidence

- All ten fits used exactly 1,152 TRAIN examples each, selected by observed next-action payoff NLL and **without gold meaning labels**.
- Nine of ten conditions selected the maximum allowed switch rate **0.32**. NAND seed 37 selected **0.0025**.
- Over **960 matched, TRAIN-only evidence-prefix pairs**, **864** received a confident interpretation despite the opposite target worlds being strictly indistinguishable before the later physical payoff. Every such pair entails one necessarily wrong high-confidence prediction among its two possible worlds. Maximum recorded posterior confidence: **0.999970575**.
- All **96/96** pairs were prematurely committed in each of the nine aggressive-rate conditions; **0/96** in NAND seed 37. Total necessarily wrong over the paired 1,920 possible worlds: **864** (45%).
- The **1,209 software tests**, historical manifest locks, preflight and final source-snapshot workflow all passed. Green code tests must not be interpreted as a positive scientific decision.

[Machine-readable TRAIN audit](results/revision-v2/train-prefix-audit.json) · [Fitted TRAIN curves](results/revision-v2/train-fitted.json) · [Hosted invariant suite](https://github.com/robosys-labs/cemm/actions/runs/41808077247) · [Source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41808077201).

## What failed, and what did not

The one-scalar objective rewards overall selected-payoff likelihood and can strongly prefer a recent contrary observation before the available evidence identifies whether it indicates a temporary exception or a durable meaning change. This identifies an **objective/uncertainty mismatch** in this setup, not proof that the general architecture is impossible. The supplied two hypotheses, source/verification flags, scopes and complete conditional reward forecasts remain major limits. The 960 pairs are dependent controlled counterfactuals, not independent environments.

This is a **TRAIN-prefix failure**; no v2 physical challenge bank was opened for scoring. Earlier G1–G4 evidence, the accepted G5 baseline, all frozen parents and production authority are unchanged. Do not rerun this study with altered thresholds and relabel it a pass.

## Smallest next step

Before adding parameters, compare the existing candidate and rule baseline on a new **TRAIN-only, balanced pre-probe next-outcome objective** with explicit abstention penalty / proper probability scoring for indistinguishable twins. Determine whether the failure is objective weighting or a representational limitation. If objective-only correction cannot preserve both current-scope uncertainty and post-probe confident revision, preregister a new study with the smallest additional latent distinction (transient exception versus lasting change), fresh challenge custody, matched data/compute and no extra language rules. No G6 or production promotion follows.
