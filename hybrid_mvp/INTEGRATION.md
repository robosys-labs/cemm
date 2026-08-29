# Hybrid MVP Integration

The **CEMM Authoritative Hybrid MVP** is integrated as the top-level
`hybrid_mvp/` subtree. It remains a separately governed proof: root adoption
requires its own reviewed decision.

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
not current admission authority. Current replay status and exact admission
identities are derived only from
[`governance/replay_status.jsonl`](governance/replay_status.jsonl). This page
does not copy or promote phase status. If the ledger is absent or fails
validation, no prose summary or inherited receipt can promote a replay phase.

The corrective investigation found upstream contract, data and runtime drift,
not insufficient training:

- M1's validation receipt is too weak (`--profile` mostly changes the label).
- M2 introduced two incompatible `SemanticSwitchProgram`/`ProposalResult`
  paths; the release proposer uses the new ABI while `HybridRuntime.process()`
  still expects the old fixture ABI.
- M3's cognition modules exist largely as isolated components with fixture
  owners injected in tests.
- M4 trained on bootstrap-selected program derivations instead of reviewed
  canonical semantic expressions; hard negatives are mostly unchanged clones;
  calibration is not based on model inference; evaluation can collapse
  pointer-distinct meanings and bypasses the authentic six-phase loop.

The inherited 100-epoch experiment reduced exact accuracy from 61/78 to 59/78.
That result is diagnostic evidence against further training on the current
pipeline, not a release or replay receipt.

## Next steps

Proceed under the [August 29 R4.1 data/supervision amendment](docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md),
the [semantic-algebra amendment](docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md),
and the [document authority map](docs/DOCUMENT_AUTHORITY.json).

R5 training, selection, calibration, frozen evaluation and realization
activation are unavailable until a fresh R4.1 admission proves meaningful
purpose-class semantic coverage and independent derivation/realization gold.
