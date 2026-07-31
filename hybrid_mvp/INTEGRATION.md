# Hybrid MVP Integration

This branch integrates the **CEMM Authoritative Hybrid MVP** worktree into the
main CEMM repository as a top-level `hybrid_mvp/` subdirectory.

## Layout

```
hybrid_mvp/
  src/cemm_authoritative_hybrid/   # Python package (six-phase runtime)
  tests/                           # pytest test suite
  data/                            # authority data, episodes, partitions, scenarios
  artifacts/                       # trained models, calibration, evaluation reports
  configs/                         # release configurations
  scripts/                         # CLI scripts (training, evaluation, demos)
  docs/                            # architecture, plans, specs
  schemas/                         # JSON schemas
  AGENTS.md                        # worktree-level governing contract
  pyproject.toml                   # package definition
```

## Status

Inherited milestone receipts and generated artifacts are historical evidence,
not current admission authority. Effective replay status is owned only by the
append-only ledger specified in G0 Task 2. If that ledger is absent or fails
validation, no prose summary or inherited receipt can promote a replay phase.

The corrective investigation found upstream contract, data and runtime drift,
not insufficient training:

- M1's validation receipt is too weak (`--profile` mostly changes the label).
- M2 introduced two incompatible `SemanticSwitchProgram`/`ProposalResult`
  paths; the release proposer uses the new ABI while `HybridRuntime.process()`
  still expects the old fixture ABI.
- M3's cognition modules exist largely as isolated components with fixture
  owners injected in tests.
- M4 trained on bootstrap-selected labels instead of reviewed semantic
  assertions; hard negatives are mostly unchanged clones; calibration is not
  based on model inference; evaluation bypasses the authentic six-phase loop.

The inherited 100-epoch experiment reduced exact accuracy from 61/78 to 59/78.
That result is diagnostic evidence against further training on the current
pipeline, not a release or replay receipt.

## Next steps

Proceed under the [approved design](docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md),
[master replay plan](docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md)
and [G0-R1 implementation plan](docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md).
Those owners define replay order, performance-bounded validation tiers and
admission commands; this integration note intentionally does not duplicate
them.
