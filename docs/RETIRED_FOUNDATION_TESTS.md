# Retired predecessor test and script inventory

These paths were removed from the active checkout after independently
identifying assumptions incompatible with the canonical six-phase foundation.
Their bytes remain in Git history and the frozen pre-recovery branch
`archive/cemm-pre-foundation-20261008`. **No behavioral gate may be
reintroduced by reviving an invalid compatibility API.**

| Removed path | Defect | Admitted replacement |
| --- | --- | --- |
| `tests/test_bootstrap_episode_generation.py` | Uses retired Program ABI 1 `action_encoding_hash` and calls a generator that instantiates old `OrientationProjector`, `BootstrapProposer(authority=...)`, and `ExactProgramVerifier(authority,...)` interfaces. It cannot produce valid Program ABI 2 gold. | `test_foundation_semantic_surface.py`, `test_foundation_algebra.py`, `test_foundation_query_role_direction.py`, reviewed R2/ABI 2 proposer/verification tests |
| `scripts/build_bootstrap_episodes.py` | Executable self-authored bootstrap gold under retired constructor contracts. Running it contradicts current policy that candidate outputs cannot become independent reviewed semantic gold. | Independently reviewed R4 corpus contracts and held-out foundation acceptance |
| `tests/test_dialogue_focus.py` | Calls forbidden direct `VerifiedSemanticFocus(...)` constructor with retired field names and expects removed `FocusStore.query()`; tests a predecessor session simulator, not canonical R3 persisted snapshots. | `test_foundation_restart.py`, `test_r3_learning_transaction.py`, R3 session/focus snapshot and receipt tests |
| `tests/test_dialogue_obligations.py` | Assumes pre-R3 `DialogueObligation(...)` constructor and legacy free-form `DialogueObligationManager` semantics; exact R3 learning plans/obligations require content-addressed factories and EFFECT-owned persistence. | `test_r3_learning_transaction.py`, `test_foundation_reviewed_learning_effect.py` with pending one-active/expiry/approval/restart guards |

| `tests/test_discourse_reference.py` | Uses obsolete direct `VerifiedSemanticFocus(...)` constructor and `ReferenceConstraints(scope=...)` fields removed by exact dialogue ABI. The current runtime does not yet prove equivalent discourse-reference resolution; this is a **capability debt**, not a green replacement. | R3 focus snapshots and pending independent discourse-reference gold (unadmitted) |
| `tests/test_evaluation_metrics.py` | Imports nonexistent `evaluation.build_release_runtime` and asserts green proposal/realizer neural-release metrics even though release activation deliberately raises `MissingOwner`. It is an invalid historical release assertion, not a current foundation quality gate. | Current source-bound foundation acceptance, R5 red release gate and future independent evaluated R5 corpus |

This is **not** license to remove every failing test. Future full-suite
failures must be triaged by actual owner/ABI and admitted source behavior,
with an explicit retirement record when a test is legitimately obsolete.

The current full-suite job remains a hard fail when other active modules
violate their contract.

| `tests/test_g0_integration.py` | Enforces frozen pre-recovery G0 test-inventory selectors and source digests. New independent foundation tests and reviewed test retirements are intentionally excluded by those immutable G0 receipts; continuing to require their exact counts would reauthorize historical governance as the current interpreter. | Current `.github/workflows/foundation-validation.yml` active foundation and full active Hybrid regression gates; current public path source/ABI protections |
| `tests/test_r1_cognitive_restart_successors.py` | Requires every successful cognition turn to stop after VERIFY with `MissingOwner(r3_owner)`, and no R3 evaluation/effect—contradicting the admitted R3 successor that is now the single canonical runtime. | `test_r3_public_cycle.py`, `test_foundation_semantic_surface.py`, `test_foundation_restart.py`, `test_foundation_reviewed_learning_effect.py` |

Current test migrations (not retirements) retain their behavioral checks:
- `test_form_grounding_lineage_abi1.py` accepts the stronger exact-integer error wording while still rejecting bool-for-integer forgery.
- `test_lazy_package_imports.py` enumerates the new canonical foundation exports while retaining lazy import proof.
- `test_gap_matrix.py` checks the current public `CycleStatus.from_gap_receipt` owner rather than the removed runtime helper.
- `test_gap_receipts.py` uses the strict content-addressed factory instead of a forged direct constructor.
- `test_phase_receipts.py` constructs Orientation through the canonical factory, rejects fixed/negative revision changes, and explicitly permits the R3 effect owner to advance session revisions.
- `test_gap_owner_evaluation.py` recomputes owner correctness from the active classifier and independent typed examples, never a stale historical R5 evaluation snapshot.
