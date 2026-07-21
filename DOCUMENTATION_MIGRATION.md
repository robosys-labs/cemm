# CEMM v3.5.1 Documentation Migration Guide

Use this file once when adopting the revised documentation set.

---

## 1. Root canonical documents after migration

Keep as active root contracts:

```text
AGENTS.md
ARCHITECTURE.md
CORE_LOOP.md
RUNTIME_PLAN.md
CEMM_CORE_MATHS.md
IMPLEMENTATION_PLAN.md
CORE_ISSUES.md
ISSUES_TO_AVOID.md
ACCEPTANCE_CONTRACT.md
README.md
```

`RUNTIME_PLAN.md` is new and mandatory.

---

## 2. Supersede/archive

After adopting the new `IMPLEMENTATION_PLAN.md`:

```text
PRE_3_5_1_STABILIZATION_PLAN.md
V3_5_1_IMPLEMENTATION_PLAN.md
```

must no longer be active plans.

Recommended move:

```text
docs/archive/v350/PRE_3_5_1_STABILIZATION_PLAN.md
docs/archive/v351/V3_5_1_IMPLEMENTATION_PLAN.md
```

Add a header:

```text
SUPERSEDED — historical planning context only.
Canonical roadmap: /IMPLEMENTATION_PLAN.md
```

Do not delete useful historical reasoning until migration is complete.

---

## 3. CEMM_CORE_MATHS.md

Retain the current v3.5.1 mathematical document if it remains consistent with:

- exact CSIR identity;
- recurrent typed message passing;
- state belief;
- causality;
- prediction error;
- semantic equivalence;
- bounded computation.

Update terminology only where needed to match:
- `AuthorityGeneration`;
- `ReadGeneration`;
- `CycleWorkspace`;
- new Stage 0–22 names.

Do not create a second competing maths document.

---

## 4. README.md changes

Replace the canonical-documentation section with this order:

```text
1. AGENTS.md
2. ARCHITECTURE.md
3. CORE_LOOP.md
4. RUNTIME_PLAN.md
5. CEMM_CORE_MATHS.md
6. IMPLEMENTATION_PLAN.md
7. CORE_ISSUES.md
8. ISSUES_TO_AVOID.md
9. ACCEPTANCE_CONTRACT.md
```

State clearly:

```text
Current implementation priority:
complete IMPLEMENTATION_PLAN.md Phases 0–4 stabilization
before v3.5.1 semantic-brain authority migration.
```

Do not tell contributors to use archived plans.

---

## 5. AGENTS.md changes

The supplied replacement `AGENTS.md` becomes highest-priority local implementation governance.

Any nested `AGENTS.md` must:
- narrow local implementation details only;
- not redefine architecture;
- not redefine stage order;
- not introduce a second plan;
- defer to root authority order.

---

## 6. Tests/docs linkage

Create a machine-readable mapping, for example:

```text
docs/acceptance_matrix.json
```

Fields:

```json
{
  "gate": "A12",
  "test_refs": ["tests/..."],
  "issue_refs": ["CI-011", "CI-013"],
  "phase": "14",
  "status": "implemented|verified"
}
```

The point is traceability, not exact file format.

---

## 7. Code naming migration

Old stage/API names should be migrated deliberately.

Do not preserve old public names indefinitely merely to avoid changing tests.

During transition:
- compatibility aliases may exist internally;
- canonical traces/manifests use the new Stage ABI;
- aliases have deletion issue/phase.

---

## 8. Required adoption sequence

```text
1. land documentation-only migration
2. update README/canonical links
3. archive superseded plans
4. create acceptance/issue trace
5. baseline current main
6. begin IMPLEMENTATION_PLAN Phase 1
```

Do not mix the documentation migration commit with large semantic code changes.
