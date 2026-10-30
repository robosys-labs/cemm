# Predictive world nucleus — isolated research, G0 protocol

**Current entry point:** [ACTIVE_NUCLEUS.md](ACTIVE_NUCLEUS.md) records the live
interfaces, actual progress and next bounded comparison. The G0 instructions
below are retained historical scope; they are not the current implementation status.

> **Audit hold:** Read [the 2026-10-28 integrity audit](2026-10-28-AUDIT.md)
> before interpreting historical metrics or alarm rates. G1 is not admitted.

**Status: G0 implementation invariants runnable; no G1 learning or scientific result admitted.**
Tracks [issue #22](https://github.com/robosys-labs/cemm/issues/22) and the
[roadmap in draft PR #23](https://github.com/robosys-labs/cemm/pull/23).
No imports or writes into `cemm/`, `hybrid_mvp/`, authority packs, release ledgers,
or active runtimes. Root `AGENTS.md` remains controlling for production.

## Repeatable G0 checks (Python >=3.11, standard library only)

From the repository root:

```sh
python -m experiments.predictive_nucleus.protocol verify
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.evaluate smoke
# When independent oracle and model JSONL files exist:
python -m experiments.predictive_nucleus.evaluate score --oracle gold.jsonl --predictions model.jsonl
```

The scorer smoke cases are **fabricated score-validation fixtures**. Their numbers
must not be reported as training, generalization or gate results. No teacher,
pretrained model, neural training or inference is imported in this tranche.

## Freeze and audit

`protocol.json` is frozen by `snapshots/protocol.sha256` (SHA256 of its exact
file bytes). `protocol.verify` fails on drift, duplicate split seeds, topology
leakage and missing contract fields. Never quietly update this lock after seeing
a sealed challenge result: mint a new protocol version and a fresh external
challenge, then keep former failures as open regression fixtures. A public hash
records what was declared; **it does not make a publicly readable challenge
cryptographically blind**. Independent test data custody remains required for
claims of unseen success.

World contract v1 (declared, **not implemented in G0**): 3–6 opaque stable
same-kind identities with binary state; interventions and ordered two-party
contacts; hidden episode source-slot orientation; contact updates the other
slot by parity with the current source bit; observation-only operations leave
state unchanged; later sensor glimpses can be partial and shuffled. Training
receives only earlier sensor observations, the selected action and newly
arrived observations. Neither oracle hidden role nor post-action truth can
enter model features. Entire 3+ contact topology families are challenge-only.
This historical G0 contract remains a requirement for later independent
evaluation; subsequent public diagnostics do not establish the G1 gate.

## Metric and provenance boundaries

`evaluate.score_predictions(oracle_rows, prediction_rows)` takes evaluator-
only complete truth and an independently generated model prediction file.
Every predicted opaque entity must be present, including unchanged ones, and
no new entity may appear. Measures complete-world exactness rather than a
misleading mean bit accuracy; per-entity Brier and ECE; legacy per-entity NLL
clipped at `1e-12`; 2-direction
role-pair conjunction; abstention coverage; and breakdowns by family and seed.
An optional prior prediction file reports repaired/broken **case IDs**.
A pair with only one correct direction receives zero credit. No oracle labels
are passed into a learner by this scorer. `score --previous previous.jsonl`
also enumerates per-case repairs and regressions; a score by itself never admits
a research gate. Each JSONL record has a unique `case_id`; oracle rows have
`seed`, `family`, `truth` (complete opaque-ID -> bit map), and optional
`pair_id`/`direction`; prediction rows have `p1` (same IDs -> supplied
probability of bit 1), or `abstain: true` with no `p1`. This scorer does not
establish calibration, and its clipped NLL is not uncapped log loss.

The frozen manifest predeclares additional later metrics (external goal,
question efficiency, unanswerable claims, latency, parameters, resource cost),
which are **not yet implemented/scored**. Do not substitute absent metrics
with zeros or make cross-model claims without matched compute and data.

## Actual baselines and unresolved references

| Reference | Exact origin | Meaning at G0 |
|---|---|---|
| Production source on `main` | `24d8b68a4c9b0c992362a1c2e542579b5f0c4280` | Authority reference, **not** a world-model benchmark |
| Six-phase foundation (draft PR #21) | `ca4a592aacd6257bbfed601ea4143766ff4c1be9` | Separate architecture, **not** a learned G1 baseline |
| Historical code | `reference/mvp_v4/` and `archive/v3.5.1/` on frozen main | Reference only; task-commensurate scores **not established** |
| Last-state/no-change | G1 control, not yet executed | To run on identical episodes |
| Flat recurrent, memorization, shared/no-memory | G1 controls, not yet implemented | Parameter/compute match required; no fabricated results |

Record every model seed (7, 11, 23, 37, 53), episode lineage,
train examples/steps, parameter count, timing p50/p95, CPU/GPU identity,
peak RSS and case-level failures. The gate is **NOT RUN** until all models,
controls and challenge results exist. Explicit G0 decision:
**KEEP protocol / NO GO on G1 admission yet**.
