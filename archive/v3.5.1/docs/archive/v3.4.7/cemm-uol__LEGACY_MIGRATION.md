# UOL authority migration

CEMM v3.4.7 physically replaces previous UOL definitions. The only canonical
record definitions are in `cemm/v347/model.py`; modules in this directory are
public re-exports. Legacy UOL/fact records may enter through the one-way,
fail-closed adapters in `cemm/migration/v347.py`. Canonical code must never
convert new records back into a legacy graph or import a legacy composer.
