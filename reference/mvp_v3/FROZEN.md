# FROZEN — Permanent Reference

**Status:** Frozen. Do not modify.
**Purpose:** Permanent executable reference of the CEMM MVP v3 demo.

This directory is a read-only reference. CEMM v1 is built from mvp_v4 but lives
in the root `cemm/` package. To run this reference:

```bash
cd reference/mvp_v3
PYTHONPATH=. python -m unittest -v tests.test_mvp
```

**Key contribution:** Active semantic workspace, self-state (3 dimensions),
language packs, semantic-pointer NLG, authority/read generation separation.
