# CEMM v3.5.1 Revised Documentation Bundle

This bundle is designed to replace the conflicting/faulty active planning and runtime documentation.

## Files

- `AGENTS.md` — governing implementation contract.
- `ARCHITECTURE.md` — canonical target architecture.
- `CORE_LOOP.md` — canonical logical Stage 0–22 loop.
- `RUNTIME_PLAN.md` — concrete runtime ownership/persistence/generation contract.
- `IMPLEMENTATION_PLAN.md` — sole unified roadmap (stabilization + semantic-brain work).
- `CORE_ISSUES.md` — active defect register with current critical issues.
- `ISSUES_TO_AVOID.md` — anti-regression contract.
- `ACCEPTANCE_CONTRACT.md` — v3.5.1 CSIR-first executable acceptance gates.
- `DOCUMENTATION_MIGRATION.md` — adoption/archive instructions.

## Intentionally not replaced

`CEMM_CORE_MATHS.md` should be retained if its current v3.5.1 mathematical definitions remain consistent, with terminology patched to match the new runtime-generation and Stage ABI contracts. Do not create competing maths documents.

## Recommended first commit

Documentation-only:
1. replace the matching root files;
2. add `RUNTIME_PLAN.md`;
3. archive/supersede `PRE_3_5_1_STABILIZATION_PLAN.md` and `V3_5_1_IMPLEMENTATION_PLAN.md`;
4. update README canonical links;
5. do not mix this commit with runtime code changes.
