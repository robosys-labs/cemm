# CEMM v1 Phases 5–9 Review and Implementation Notes

**Reviewed head:** `ea5d880aa110b7fb9794c44a3690a6740ff8ebe8`  
**Patch scope:** Phases 5–9 from `v1-fixes.md`  
**Forward contracts preserved:** Phase 10 transition previews and Phase 13 target-aware Response CSIR inputs

## Confirmed defects in the pushed Phase 1–4 merge

### Critical

1. **Surface punctuation/CLI mode overrode stabilized semantics.**
   `learn=True` plus no final question mark rewrote a predicted query into an assertion. This made a UI/storage permission mode part of meaning and introduced a hidden phrase-form shortcut.

2. **`SessionSelf` still corrupted semantic self state.**
   A frontier set global self interpretation to unresolved and global response state to `confused`; an unknown query set global self epistemics to insufficient. One unresolved target therefore contaminated unrelated self capability and knowledge.

3. **Query execution remained boolean and non-projective.**
   The packet still represented a query as one application and `Inference.match()` discarded variable bindings. It could not correctly express or answer `state(X, knownD, ?V)`, `state(X, ?D, ?V)`, or multi-restriction queries.

4. **Every learn-mode claim was directly admitted into world belief.**
   Claim occurrence, source-attribution, epistemic placement and admitted belief were still collapsed into one database write.

### High

5. **`role:dimension` remained absent from learned structured semantics.**
   The exact operator required it, but the network still relied on value→dimension restoration as the normal representation.

6. **Unknown material aborted the entire interpretation.**
   Known clauses/referents were discarded instead of preserving partial stable meaning and opening a scoped frontier for only the unresolved material.

7. **Function-word authority still came from incidental training-example text.**
   Adding/removing examples silently changed whether a surface form was treated as grammar or an unknown semantic item.

8. **Workspace still injected runtime bookkeeping as semantic self facts.**
   `SessionSelf.slots()` entered attention as `op:state(self, ...)`, preserving the layer conflation Phase 5 was intended to remove.

### Medium

9. **Directives had no semantic separation from claims.**
   There was no explicit route to capability/permission/transition preview; the same application list could be learned as world fact.

10. **Runtime outputs lacked stable Phase 13 inputs.**
    Query proof, projected bindings, coverage, missing variables, target-scoped epistemics and state-space projections were not collected into one response input contract.

## Implemented architecture

### Phase 5 — scoped cognition, no global self poisoning

- Added `InterpretationAssessment`, `LearningFrontier`, `FrontierGraph` and `ScopedEpistemicAssessment`.
- `SessionSelf` remains only as a compatibility facade and emits no semantic slots.
- `Workspace` accepts exact/derived facts and explicitly required facts; it no longer adds synthetic self-state facts.
- `SelfRuntimeView` reports transport/runtime viability independently of linguistic labels such as “ready”.

### Phase 6 — first-class state dimensions

- Added query variable source classes `Q0..Q2`.
- Added `role:dimension` to merged v1 language supervision.
- Exact compilation supports grounded or variable dimensions/values.
- Grounded unique value→dimension completion remains only a compatibility normalization.

### Phase 7 — QueryCSIR

- Added `SemanticVariable`, `QueryStructure`, `QueryBinding` and `QueryResult`.
- Queries contain restriction graphs, variable declarations, projections and qualifiers.
- Inference returns bindings, proof refs, proof structures, support/opposition counts, coverage and unresolved variables.

### Phase 8 — discourse force

- Added explicit learned/compositional forces: claim, query, description request, directive, correction, retraction and acknowledgment.
- Removed the punctuation/learn-mode override.
- Directives produce goal/capability/permission/transition-preview requirements and never assert or execute their requested effects.
- Language-specific force examples live in language-package sidecars, not kernel branches.

### Phase 9 — epistemic placement

- Added durable `claim_occurrences` and `epistemic_placements` tables.
- Added admission classes:
  - `ATTRIBUTED_ONLY`
  - `SESSION_PARTICIPANT_FACT`
  - `SCOPED_USER_ASSERTED_FACT`
  - `CORROBORATION_REQUIRED`
  - `HIGH_RISK_NO_AUTO_ADMISSION`
  - `HYPOTHETICAL_ONLY`
- Admission policy is driven by force, context, participant binding and semantic metadata.
- Only admitted claims create ordinary world-belief applications/claims.
- Corrections/retractions are recorded but await the later reconciliation/invalidation phase.

## Phase 10 compatibility

Every directive result already carries:

```text
source discourse act
capability-check requirement
permission-check requirement
transition-preview requirement
transition_candidates = []
blocks_effect = true
```

This prevents Phase 10 from needing to reinterpret surface text. It will fill role-addressed mechanisms and predicted deltas into the existing candidate slot.

Claims and queries explicitly produce no transition candidate merely because their words mention a state.

## Phase 13 compatibility

Query cycles now expose a stable `response_inputs` structure containing:

```text
QueryResult
ScopedEpistemicAssessment
StateSpaceProjection(s)
InterpretationAssessment
DiscourseAct
FrontierGraph where applicable
transition candidates
proofs / coverage / missing variables
```

Phase 13 can therefore construct targeted Response CSIR without reading global `self.epistemic_state` or reparsing the original utterance.

## Deliberate scope limits

- Full causal transition mechanisms are Phase 10.
- Canonical full Stage 0–22 orchestration is Phase 11.
- Derived digital-self readiness lexicalization is Phase 12.
- Target-aware Response CSIR and faithful realization are Phase 13.
- Correction/retraction invalidation is not silently implemented as deletion in Phase 9.
- Unknown forms remain frontiers; they are not defaulted to concepts.
