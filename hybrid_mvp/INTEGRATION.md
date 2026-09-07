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

The inherited milestone investigation recorded upstream contract, data and
runtime drift, not insufficient training. The following are historical findings,
not a fresh inventory of current owners:

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

Proceed under the approved
[foundation amendment](docs/superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md)
and [implementation plan](docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md),
with the [document authority map](docs/DOCUMENT_AUTHORITY.json) defining precedence.
Preserve the August 29 data/supervision and August 2 semantic-algebra laws.
The September 3 closure and narrow unresolved-designation routes are historical;
their completed acyclic frame and canonical designation work remains reusable.

Correct stale documentation first, specify the complete independent semantic
matrix, remove false atom-kind definition answers and repair the earliest query,
uncertainty, learning and response owners. Graph validity is distinct from
intended meaning and supported answers. Containment alone does not complete
definition support or the conversation loop.

A development-only compositional response reference through existing owners is
permitted, not a learned surface or product fallback. It preserves provenance,
scope and perspective and cannot bypass normal verified-focus equivalence.
Bulk R4.1 authoring, review/export, purpose allocation, realization-recipe review,
corpus expansion and package publication remain frozen.

R5 training, selection, calibration, frozen evaluation and realization
activation are unavailable until a fresh R4.1 admission proves meaningful
purpose-class semantic coverage and independent derivation/realization gold.
No pilot training is authorized before that admission and explicit isolated
R4.1-compliant data authorization. This increment authorizes no network research
adapter, root adoption, new phase or new gate.
