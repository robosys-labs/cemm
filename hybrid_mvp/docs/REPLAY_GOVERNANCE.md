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

Corrective-replay status is a separate concern. Replay status is derived only
from the append-only, machine-validated
[`governance/replay_status.jsonl`](../governance/replay_status.jsonl) ledger
introduced by G0 Task 2. Phase state and exact admission-run identities must be
read from that ledger, not copied into routing prose. R4 admission uses
repository-owned artifact integrity, not external review. Prose summaries and
inherited receipts remain non-authoritative.
