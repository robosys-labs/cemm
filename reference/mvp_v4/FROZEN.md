# FROZEN — Permanent Reference

**Status:** Frozen. Do not modify.
**Purpose:** Permanent executable reference of the CEMM MVP v4 demo.
**Basis for:** CEMM v1 (root `cemm/` package).

This directory is a read-only reference. CEMM v1 is built from this kernel.
To run this reference:

```bash
cd reference/mvp_v4
PYTHONPATH=. python -m unittest -v tests.test_mvp
```

**Key contribution:** Open structured graph prediction, N-best candidate
settling, rule induction with provisional→promoted lifecycle, vocabulary
acquisition, authority/world atom separation.
