# Hybrid MVP R3–R4 Corrective-Replay Implementation Plan

> **Historical completion notice (2026-08-13):** R3 and R4 are admitted; the
> body records their implementation-time procedure and is not current status.
> Status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> R4 external review was superseded by
> repository-owned artifact integrity.

**Status at publication:** implementation source complete; R3 and R4 remain red until separately admitted
**Date:** 2026-08-05  
**Scope:** `hybrid_mvp/` only  
**Required predecessor:** admitted R2 source lineage at or after `68c8c041376bcd1b0d17b7a51a676442418b26d3`

## 1. Non-negotiable boundary

R3 starts only from a selected canonical `VerifiedMeaning` and an independently
verified `SituationContext`.

```text
ORIENT → PROPOSE → VERIFY
                    │
                    └─ VerifiedMeaning + SituationContext
                       → EVALUATE
                       → EFFECT
                       → ResponseMeaning
                       → typed R5 realization gap
```

A `SemanticSwitchProgram` is derivation lineage only. No R3 owner may read
program actions, `program.graph`, source text, tokens, or ref spelling to make a
semantic decision.

R4 starts only after R3 is green. It compiles reviewed assertions into expected
semantic contracts independently of PROPOSE, runs authentic R3 cycles, preserves
expected and observed artifacts separately, generates authentic negatives, and
seals independent holdout axes. R4 does not train models.

## 2. Implemented R3 source

The bundle implements the complete post-VERIFY source path without changing the
meaning authority boundary:

1. structural four-mode projection from reviewed form hypotheses;
2. strict Situation Context ABI 1 and independent verification;
3. recursive expression projection and integrity indexes;
4. Decision ABI 1 and expression-only QUERY, OBSERVE, REQUEST and SIMULATE owners;
5. bounded reviewed-rule query inference with proof-local witnesses and exact
   proof DAG lineage;
6. epistemic admission, conflict-preserving state deltas, transition simulation
   and capability derivation;
7. exactly one EffectReceipt or NoEffectReceipt per selected cycle through one
   atomic persistence owner;
8. Learning Plan ABI 2 and persistent dialogue obligation;
9. Response Meaning ABI 2 with no surface text;
10. one public runtime path through all six phase materials, ending at the exact
    `contract:r5:realize_surface` boundary;
11. crash/retry-safe effect identity and focused public-runtime canaries.

The implementation intentionally does not append a green R3 ledger row.  A clean
full-suite run, immutable test-inventory migration, SQLite restart canaries and
fresh admission receipt are still required.

## 3. Implemented R4 source

R4 is implemented as a deterministic reviewed-data pipeline, not as training:

1. closed reviewed assertion vocabulary and total Expected Cycle Contract ABI 1;
2. separate Expected Derivation Contract ABI 1 labels;
3. every-surface and bounded reviewed-environment expansion;
4. authentic public-runtime episodes with expected/observed/comparison separation;
5. single-dimension semantic and environmental mutations executed by an
   injected authentic earliest-owner runner;
6. explicit structural sufficiency minima/maxima;
7. seven independently sealed partition axes and an intersection-only training
   allowlist;
8. content-addressed build receipt;
9. unsigned external-review request generation and separately injected signature
   verification; no source module can self-sign or self-approve.

Generated contracts, episodes, mutations, partitions and approval are not
embedded in this bundle because they must be regenerated from the applied,
committed and admitted R3 source lineage.

## 4. Required completion procedure

1. Apply the bundle to the exact admitted R2 commit or a reviewed
   history-preserving descendant.
2. Run focused validation and the legacy-test migration audit.
3. Rewrite or supersede every predecessor-era Program/fixture test found by the
   audit and regenerate the immutable governed test inventory.
4. Run all R2 owner/phase/admission verification to prove no regression.
5. Run R3 owner, phase, SQLite restart and public canary gates.
6. Commit deterministic R3 inputs and run one fresh R3 admission.
7. Build R4 artifacts using an admitted-R3 environment owner.
8. Obtain an external signature over the exact artifact graph.
9. Run R4 owner/phase/admission gates and only then append the R4 status record.
## 5. Admission invariants

Neither phase may be green when any active governed test is failed, errored,
skipped, xfailed or xpassed. A phase receipt must bind the exact committed clean
source, predecessor admission, authority, ABI registry, configuration, stores,
tests and generated artifacts. Generated files and self-declared
`"review_status": "reviewed"` values are never semantic review authority.

## Complete bundle allocation

This implementation bundle allocates the active code owners as follows:

- `situation.py`: Situation Context ABI 1.
- `decision.py`: Decision ABI 1 and exact EVALUATE dispatch.
- `r3_artifacts.py`: proof, query, admission, state, transition, capability,
  effect-intent and Evaluation Bundle ABIs.
- `r3_cognition.py`: expression-only OBSERVE, QUERY, REQUEST and SIMULATE owners.
- `r3_effects.py` and `r3_persistence.py`: Effect/No-Effect Receipt ABI 1 and
  the single atomic persistence boundary.
- `r3_learning.py`: Learning Plan ABI 2 and persistent learning obligation.
- `r3_response.py`: Response Meaning ABI 2.
- `runtime.py` and `r3_cycle.py`: the single public six-phase path, ending at
  the exact R5 surface-realization gap.
- `r4_contracts.py`: reviewed assertion and Expected Cycle Contract ABIs.
- `r4_expansion.py`: every reviewed surface and environment combination.
- `r4_episodes.py`: expected/observed separation over authentic public cycles.
- `r4_mutations.py`: reviewed semantic/environment mutation contracts and
  authentic earliest-owner observations.
- `r4_partitions.py`: independently sealed holdout axes and the intersection
  training allowlist.
- `r4_review.py`: externally signed corpus review authority.
- `r4_pipeline.py`: deterministic artifact construction without training or
  self-approval.

The installer does not append green R3/R4 ledger records.  Technical gates,
committed deterministic artifacts and independent corpus approval must be run
on the applied checkout before those transitions are permitted.
# R4 supersession notice

The R4 external-review and signed-manifest tasks in this plan are superseded by [R4 Repository-Owned Admission Plan](2026-08-12-r4-repository-owned-admission-plan.md). Its R3 implementation history remains authoritative where it does not conflict with that plan.
