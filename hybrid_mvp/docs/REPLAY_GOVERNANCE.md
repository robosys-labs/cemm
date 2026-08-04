# Corrective Replay Governance

`DOCUMENT_AUTHORITY.json` is the single machine-readable owner of document
precedence for the corrective replay. Its `path_base` makes listed paths
relative to the repository's `hybrid_mvp/` directory, never relative to the JSON
file. Its authority is intentionally limited to that subtree; the repository-root
`AGENTS.md` continues to govern the root runtime. Adoption outside the Hybrid MVP
requires a separate reviewed decision.

The ordered `governing_documents` list identifies the current Hybrid MVP
contract, approved design, executable plans, architecture and ABI inventory.
The 2026-08-02 semantic-algebra amendment has precedence over the July-31
design and plans where they previously treated a `SemanticSwitchProgram` as
canonical meaning. It amends those active documents in place; it does not
reactivate any superseded July-29 or July-30 execution claim.
Files listed under `superseded_execution_claims` remain useful evidence, but
their milestone-completion and admission claims cannot authorize current work.
The `historical_evidence` entries likewise cannot promote generated artifacts
or test receipts into semantic or release authority.

Corrective-replay status is a separate concern. G0 Task 2 introduces the
append-only, machine-validated status and invalidation ledgers. Until that owner
is present and admitted, prose status summaries and inherited receipts are
non-authoritative. This document explains the boundary; it does not duplicate a
status table.
