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

Milestones M1–M3 are complete. M4 Tasks 1–4 are implemented but **not passing
release thresholds**. Investigation found the root cause is upstream
contract/data/runtime drift in M1–M3, not insufficient training:

- M1's validation receipt is too weak (`--profile` mostly changes the label).
- M2 introduced two incompatible `SemanticSwitchProgram`/`ProposalResult`
  paths; the release proposer uses the new ABI while `HybridRuntime.process()`
  still expects the old fixture ABI.
- M3's cognition modules exist largely as isolated components with fixture
  owners injected in tests.
- M4 trained on bootstrap-selected labels instead of reviewed semantic
  assertions; hard negatives are mostly unchanged clones; calibration is not
  based on model inference; evaluation bypasses the authentic six-phase loop.

The 100-epoch retrain reduced exact accuracy from 61/78 to 59/78, confirming
that more epochs cannot repair the system.

## Next steps

An evidence-gated corrective replay is planned:

1. Revalidate M1 (verify advertised owner graph and neural runtime).
2. Repair M2's single ABI/composer/model path.
3. Integrate M3 through the real runtime (no fixture owners).
4. Regenerate episodes and partitions, then retrain with validation-based
   model selection.
5. Rewrite Task 4 evaluation around actual six-phase receipts.

See `hybrid_mvp/docs/superpowers/plans/` for the original milestone plans.
