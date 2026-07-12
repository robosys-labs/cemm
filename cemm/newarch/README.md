# CEMM v3.4 — Foundation Reliability Revision

This package is a surgical correction to the existing v3.4 cognitive semantic kernel architecture.

It does **not** replace the v3.4 semantic graph, schema store, cognitive cycle, recursive learning transaction, or NLG architecture. It strengthens the exact point where the current design is under-specified: the difference between resolving a symbol/schema reference and possessing an executable, grounded understanding of it.

## Governing conclusion

A schema is not understood because:

- its name is recognized;
- it is linked to another schema;
- several claims mention it;
- it parses the teaching example;
- it has been written to memory.

A schema is operationally understood only when its definition has closed, non-circular dependencies on already executable semantic foundations and passes schema-family-specific competence checks.

## Files

- `ARCHITECTURE_RELIABILITY_REVISION.md` — exact minimal architecture changes.
- `UNDERSTANDING_PIPELINE.md` — strengthened existing understanding stages.
- `LEARNING_PIPELINE.md` — meaning-backed learning using the existing transaction/replay design.
- `SEMANTIC_FOUNDATIONS.md` — minimal native semantic basis and audited boot boundary.
- `DATA_MODEL_DELTA.md` — smallest required record/schema changes.
- `AGENTS_DELTA.md` — governing invariants to merge into `AGENTS.md`.
- `IMPLEMENTATION_PLAN_DELTA.md` — changes to existing v3.4 phases, not new parallel phases.
- `PRESIDENT_LEADER_TRACE.md` — complete worked example.
- `ACCEPTANCE_TESTS_DELTA.md` — foundational reliability tests.

## Supersession

This package supersedes the earlier over-expanded "foundational ontology" proposal where that proposal introduced a separate ontological pipeline or excessive new object families. The canonical architecture remains the v3.4 final architecture, amended by this reliability revision.
