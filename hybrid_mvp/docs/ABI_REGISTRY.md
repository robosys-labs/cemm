# ABI Registry

**Status:** landed candidate ABI inventory; activation requires admitted R1 status
**Runtime cutover: hard**

This registry records the owner file, serialized/transient status, validator
and intended activation gate for each landed ABI candidate. No row is an active
replay contract until R1 admission succeeds. All listed candidate versions are
version 1.

| ABI | Version | Owner file | Serialized / Transient | Validator | Activation gate |
|---|---|---|---|---|---|
| Semantic Contribution ABI | 1 | `src/cemm_authoritative_hybrid/contributions.py` | Transient | `ContributionExpander` | Contributions are bounded by `max_designations_per_span` and `max_affordances_per_target`; every form yields at least one typed contribution or one typed unresolved contribution. |
| Semantic Switch Program ABI | 1 | `src/cemm_authoritative_hybrid/programs.py` | Transient | `ExactProgramVerifier` | Programs are bounded by `max_complete_candidates`, `max_applications` and `max_graph_depth`; invalid candidates receive typed rejection codes. |
| Coverage ABI | 1 | `src/cemm_authoritative_hybrid/coverage.py` | Transient | `CoverageVerifier` | Every source unit is consumed into exactly one semantic role or retained as exactly one typed residual; critical residuals block execution. |
| Phase Receipt ABI | 1 | `src/cemm_authoritative_hybrid/cycle.py` | Serialized (opt-in trace) | Historical candidate: `KernelCycleResult`; R1 Task 8 must replace and revalidate it as `CycleResult` | Each of ORIENT, PROPOSE, VERIFY, EVALUATE, EFFECT, REALIZE emits one receipt with causal artifact refs and revision pins. |
| Gap Receipt ABI | 1 | `src/cemm_authoritative_hybrid/gaps.py` | Serialized | `GapClassifier` | Budget exhaustion, unknown literals and unsupported residuals yield a typed frontier rather than a phrase fallback. |
| Learning Plan ABI | 1 | `src/cemm_authoritative_hybrid/learning.py` | Serialized | `LearningCoordinator` | At most `max_learning_obligations` pending plan; plans lower to `op:designation` and require `cap:learn`. |
| Response Meaning ABI | 1 | `src/cemm_authoritative_hybrid/response.py` | Transient | `RealizationVerifier` | Response meaning is constructed from the exact decision, proof, blockers, effects and obligation; internal refs are not exposed. |
| Realization Receipt ABI | 1 | `src/cemm_authoritative_hybrid/realization.py` | Serialized | `RealizationVerifier` | Verified semantic focus is recorded only after exact realization equivalence; non-empty output is required for authorized response actions. |

## Invariants

- No ABI carries a backward-compatible adapter for the superseded architecture.
- No active ABI version is hidden behind a permissive fallback.
- Renaming an ABI owner requires updating this registry and every downstream
  plan before implementation continues.
