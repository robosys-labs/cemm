# G5 v4 — subgrid switch-boundary TRAIN review (2026-11-04)

**Decision: STOP_SWITCH_SWEEPS; retain the original zero-parameter scoped memory baseline.** The post-hoc TRAIN-only feasibility extension shows that lowering the persistence switch improves several conditions but does **not** solve the current one-scalar filter across all ten law/seed conditions. No G5 model or production runtime is promoted, and no independent G5 challenge was opened.

## Integrity and origin

This is a separate **post-hoc** study motivated by the opened v3 TRAIN outcome; it is **not** an unseen challenge or an independent scientific replication. The protocol was frozen at `0ef599a3e0f8edbb2bb4e78c6be75eb53dba6b2e`, source/test at `e5ec25f8cd79773f677431dfb375a42cbae87fd0`, and the full result is preserved in [train-boundary.json](results/revision-v4/train-boundary.json). [Hosted execution](https://github.com/robosys-labs/cemm/actions/runs/41811098322): **1,211 tests passed**, historical manifests and preflight passed. [Source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41811098094) passed. The test reproduces every v3 boundary result at `s=0.0025` before interpreting any new rate.

The tested rates were frozen in [REVISION_STUDY_V4.md](REVISION_STUDY_V4.md), span **0.00001 to 0.0025**, and do not alter the `posterior`, .95 commitment threshold, source records, physical payoffs, or retained G3/G4 weights. Evaluator outcomes select *no* fitted parameter; they are used solely for a feasibility audit.

## Fixed-grid outcome

- **Nine of ten** conditions have at least one rate meeting all pre-payoff uncertainty, post-payoff correctness and retained-meaning gates. Across these nine conditions, the common feasible rates are **0.0006, 0.0008, 0.001, 0.00125**.
- **NOR seed 53 has no passing rate in the fifteen-point grid.** Its best PRE commitment count is **8/96 still-unidentifiable pairs** at `s=0.0002`, where all **192/192** post-probe and **576/576** retained meanings are correct/confident. Other values trade more pre-confidence for more post-probe abstentions; none passes every gate.
- There is therefore **no globally feasible sampled rate** across all ten conditions, and allowing a separately selected rate per condition still fails NOR seed 53.
- Making `s` arbitrarily smaller is not a monotonic repair: at the smallest sampled `s=0.00001`, there are **460/960** premature confident pairs, only **1,518/1,920** correct confident post-probe decisions across ten conditions and **four** retention abstentions in NOR seed 53. At the previous boundary `s=0.0025`, PRE premature confident pairs number **54/960**. These are correlated TRAIN counterfactuals, not independent environments.

## Nondiscriminating evidence sensitivity

At `s=0.0025`, adding a new authenticated receipt with identical candidate likelihoods `(.5,.5)` and a *later timestamp* changed **28/1,920** PRE confidence decisions in two NOR conditions (16 in NOR seed 37; 12 in NOR seed 7), although that receipt contains no differentiating observation. The maximum observed posterior drift across conditions was approximately **0.002475**. This follows from the current model's implicit switch on each new evidence timestamp. Whether that is inappropriate depends on whether timestamps encode actual elapsed world time: the experiment does not specify an independently learned clock, so flag it as a **temporal-evidence sensitivity**, not an automatic implementation defect.

## Meaning and next tranche

The v3 training objective imbalance was real and strongly reduced overconfidence, but the remaining failure is not fixed by extending the one-scalar search boundary. This is **grid-bounded evidence**, not a mathematical impossibility proof over every real-valued switch rate. Do not spend another tranche tuning the same scalar or revise the opened criterion.

The next bounded G5 comparison should test **one extra general temporal distinction**: maintain competing hypotheses for a transient observation exception versus a persistent meaning change, updating their weights from selected physical payoffs only. The existing G5 v1 pending-evidence rule is the zero-parameter control; any learned alternative must either improve a pre-registered *noisy* correction task the rule cannot solve or remain unpromoted on simplicity grounds. Keep source, provenance, scopes and unknown alternatives explicit; no sentence-specific grammar, learned meaning labels, new runtime brain, or new G3 weights. Freeze distinct new topology/lineage, source-reliability and temporal-scope challenge families before any fit, reserve independent evaluation, and report query cost, proper loss, calibration, confidence mistakes, retention, compute and parameter count.

**G5 formal scientific admission: NOT_ADMITTED. G6–G8 remain open, and the inclusive 2,000-line target is still unmet.**
