# Phase-20 completion audit findings

Audited reachable v3.5 substrate: Phase16/17 remote base `e58f5f3f...` plus the exact Phase18/19 bundle applied by the user.

## Newly confirmed blockers

### P20-1 — Installable package still declares v3.4.7
`pyproject.toml` version remains 3.4.7 and package-data declarations name only `data/v347`. A wheel can omit v3.5 semantic contracts/data even when source checkout tests pass.

### P20-2 — Top-level version authority remains v3.4.7
`cemm/__init__.py` imports `v347.version.VERSION`.

### P20-3 — Public Runtime remains v3.4.7
`cemm/app/runtime.py` imports `..v347.runtime.Runtime`.

### P20-4 — CLI remains v3.4.7
`cemm/__main__.py` constructs the old Runtime and labels itself canonical v3.4.7.

### P20-5 — v3.5 package explicitly remains non-public
`cemm/v350/__init__.py` states that it is a migration substrate and is intentionally not wired as public runtime.

### P20-6 — A blind import swap would be a false cutover
There is no evidence in the reachable remote tree of a single concrete Stage-0..22 v3.5 composition root. Phase20 must therefore gate activation on an explicit complete stage-adapter graph rather than silently falling back to v3.4.7 or inventing a thin façade.

## Phase20 implementation response

- Adds exact CoreStage 0..22 orchestration topology and duplicate/missing-stage rejection.
- Adds runtime authority manifest/guard with code/data/denylist fingerprints.
- Adds machine-readable legacy authority denylist.
- Adds static runtime import/fallback scanner.
- Adds release verifier distinguishing PASS / FAIL / INCOMPLETE.
- Adds exact runtime authority manifest builder requiring one adapter per stage.
- Adds activation replacements for public imports/CLI, but activation is fail-closed behind a PASS report.
- Adds v3.5 version authority and Phase20 competence/contract data.
- Adds wheel-content verification so source-vs-installed drift cannot hide missing v3.5 data.

## Honest remaining release evidence required

This environment cannot clone the repository or run the user-applied post-Phase19 checkout because container DNS cannot resolve GitHub. Therefore the final full-suite, wheel, boot-DB, live callgraph, performance and end-to-end semantic verification must be run in the actual checkout before `--activate`. The patch is deliberately designed to reject activation without that evidence rather than claim false completion.
