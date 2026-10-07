# CEMM foundation cutover (in progress)

**Branch:** `codex/cemm-foundation-end-to-end-20261008`.
**Policy:** one canonical packaged cognitive runtime. Historical root execution
and snapshots were pruned after preserving their original main commit on the
archive branch.

## Installed package authority

The root `pyproject.toml` now installs the **Hybrid MVP** Python package
(`cemm_authoritative_hybrid`), not the superseded Stage 0–22 `cemm`
package. The root `cemm` command now invokes the foundation CLI. The former root package, root tests/tools, and snapshots have been removed
from this branch. Their bytes remain accessible in Git history and the
pre-foundation archive branch.

Do not merge as a general cognitive release until independent acquisition,
semantic-domain transfer, and real graph-equivalent natural language are green.
The active wheel and checkout no longer contain the old root `cemm/` package.

## Exact scope of this tranche

- Text enters the canonical HybridRuntime and its existing phases.
- The deterministic reference proposer is developmental, not an admitted
  neural proposer.
- The typed `ResponseMeaning` is externally returned in a reversible
  canonical JSON semantic protocol, with revision, decision and effect proof.
- No natural-language equivalence is claimed. Existing R5 release activation
  remains explicitly blocked.

A clean **checkout** can run
`cemm --root hybrid_mvp --store /tmp/cemm.sqlite3 --text hello`.

A self-contained wheel without a separately provisioned authority bundle is
not yet supported: the CLI requires `--root` and never invents authority.
Bundling canonical authority in a relocatable distribution is a separate
admission requirement.
