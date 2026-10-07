# CEMM - canonical semantic foundation

CEMM is an experimental semantic cognition system with exact meaning,
evidence, and effect boundaries. The active six-phase implementation lives in
[`hybrid_mvp/`](hybrid_mvp/), not the former Stage 0-22 root package.

## What runs today

- Text -> form/grounding -> bounded proposal -> exact expression verifier.
- Evaluated meaning -> proof-aware decision -> effect/no-effect receipt.
- A verifiable **structured semantic surface**, preserving the complete
  ResponseMeaning, effect lineage and revision pin.
- Fail-closed handling for unknown content and unadmitted language realization.

This does **not** imply general language understanding, autonomous learning,
production-ready effects, or complete natural-language realization. The
current neural release and R5 text equivalence remain unadmitted.

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
[architecture](ARCHITECTURE.md). Historical root implementations and archives
are preserved on branch `archive/cemm-pre-foundation-20261008`.
