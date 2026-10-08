# CEMM - canonical semantic foundation

CEMM is an experimental semantic cognition system with exact meaning,
evidence, and effect boundaries. The active six-phase implementation lives in
[`hybrid_mvp/`](hybrid_mvp/), not the former Stage 0-22 root package.

## What runs today

- Text -> form/grounding -> bounded proposal -> exact expression verifier.
- Evaluated meaning -> proof-aware decision -> effect/no-effect receipt.
- A verifiable **structured semantic surface**, preserving the complete
  ResponseMeaning, effect lineage and revision pin.
- Reviewer-authorized, durable learning of lexical aliases for existing
  semantic targets; forged or replayed requests never create authority.
- A **bounded reference English output** for one reviewed binary relation
  with a single proof-supported query answer. Every generated sentence is
  reparsed read-only, compared to the exact answer graph, and suppressed
  unless equivalent at the current execution revision.
- Exact authority/form/proposer store fingerprinting, fresh cross-connection
  revisions and fail-closed handling for unsupported semantics.

This does **not** imply general language understanding, autonomous ontology
creation, production-ready external effects or complete natural-language
realization. The restricted reference output is NOT the unadmitted neural R5
release. Full-suite regressions are a separate mandatory CI gate.

## Reference run from a clean checkout

```bash
python -m pip install -e '.[test]'
cemm --root hybrid_mvp --store ./foundation.sqlite3 --text 'hello'
pytest hybrid_mvp/tests/test_foundation_*.py
```

The checkout contains the reviewed authority bundle. A standalone installed
wheel must be given an explicit checkout `--root`; relocatable authority
packaging remains a separate release requirement.

See [foundation cutover](docs/FOUNDATION_CUTOVER.md),
[recovery contract](hybrid_mvp/docs/FOUNDATION_RECOVERY.md) and
[architecture](ARCHITECTURE.md), and
[reference generation boundary](docs/REFERENCE_GENERATION_BOUNDARY.md).
Historical root implementations and archives
are preserved on branch `archive/cemm-pre-foundation-20261008`.
