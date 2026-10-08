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
