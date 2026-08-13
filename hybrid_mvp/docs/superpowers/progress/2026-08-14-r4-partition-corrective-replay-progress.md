# R4 Partition Corrective Replay Progress Tracker

**Tracker date:** 2026-08-14
**Tracker role:** operational evidence; never replay-status authority
**Effective status owner:** [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl)
**Working branch:** `codex/r4-partition-corrective-replay`
**Base commit:** `107c5189353564ce8b66317c897bc28a62cfd403`
**Remote target:** `origin/codex/r4-partition-corrective-replay`

## 1. Executive summary

The R5 hard-cut foundation is complete, independently reviewed, fully verified,
and published. R5 remains red by design. Entry analysis for R5 neural activation
found that the admitted R4 training boundary is vacuous: the checked-in R4
training allowlist contains zero episode refs.

The approved repair is a separate R4 corrective replay. It replaces independent
per-axis split hashing plus empty intersection with one globally coherent,
leakage-safe four-class partition. Neural training remains prohibited until R4
is invalidated, repaired, regenerated, and re-admitted.

This tracker records implementation progress. It does not copy or override the
effective phase matrix, admission run refs, or ledger transitions.

## 2. Baseline evidence

| Evidence | Value | State |
|---|---|---|
| Published R5 foundation commit | `107c5189353564ce8b66317c897bc28a62cfd403` | verified |
| R5 foundation branch | `origin/codex/r5-hard-cut-foundation` | published |
| Governed R5 active suite | 1,641 passed; 0 failed/error/skip/xfail/xpass | verified |
| R5 active-set ref | `active_test_nodes:88eb3a69bff515c3766400f6` | verified at base |
| R5 disposition | 17 successor / 25 deferred / 1 retired | verified at base |
| Frozen inventory SHA-256 | `7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8` | unchanged at base |
| R4 source universe | 400 authentic episodes | verified |
| Current R4 training allowlist | 0 refs | defect confirmed |
| Legacy partition data | 234 train / 78 validation / 78 test | quarantined; not R4 authority |

## 3. Root-cause evidence

| Finding | Evidence | Earliest owner | Decision |
|---|---|---|---|
| Lexical axis collapses the corpus | Standalone `language_family=en` joins all 400 episodes; lexical split is 0/0/400 | `r4_partitions.py` | Language becomes a stratification qualifier, not a union key |
| Independent intersections are globally incoherent | Common train remains zero even without lexical; semantic-target assignment removes the last two rows | Partition assignment architecture | Replace independent split hashing with one global assignment |
| R5 cannot use legacy partitions | Legacy 234/78/78 data is not bound to admitted R4 build receipt | R4 artifact graph | Materialize four classes from R4 source universe |
| Epoch tuning cannot repair entry | Current neural stack and artifacts target retired Program ABI 1 | Future R5 neural owners | No retraining before R4 repair and current-ABI design |
| Existing calibration is not model evidence | Confidence is derived from gold episode fields, not selected model outputs | Future calibration owner | Replace during R5, not this increment |

## 4. Approved decisions

| ID | Decision | Rationale | Approval |
|---|---|---|---|
| D1 | Repair R4 before R5 neural activation | The defect belongs to the admitted data owner | User approved 2026-08-13 |
| D2 | Use one global component assignment | Per-axis independent intersection is empty by construction | User approved 2026-08-14 |
| D3 | Materialize train/selection/calibration/frozen_test | R5 needs purpose-separated access classes | User approved 2026-08-14 |
| D4 | Preserve per-axis evidence, not per-axis assignments | Independent evidence remains useful without conflicting membership | Design decision |
| D5 | Hard-cut data ABIs | Compatibility would preserve the vacuous allowlist | Design decision |
| D6 | Keep R5 red and forbid training during repair | Prevents tuning against unauthoritative data | Design decision |
| D7 | Tracker is non-authoritative | Prevents a second mutable phase-status source | Design decision |
| D8 | Preserve exact protected identities across all seven axes | Leakage guarantees cannot be weakened to make a split feasible | Contract review |
| D9 | Migrate the active R5 train-only foundation boundary during R4 repair | Prevents legacy `data/partitions` from remaining a second authority | Contract review |
| D10 | Expose class-scoped capabilities only | A global manifest would disclose unauthorized sibling classes | Contract review |

## 5. Work breakdown

Status vocabulary: `complete`, `in_progress`, `pending`, `blocked`, `stopped`.

| Work item | Deliverable | Status | Entry evidence | Exit evidence |
|---|---|---|---|---|
| P0 | R5 foundation closeout and remote publication | complete | Published base commit | 1,641-test governed pass; Task 10 closeout |
| P1 | R4/R5 entry audit | complete | Empty allowlist and stale neural artifacts | Root-cause reports and approved repair direction |
| P2 | Written R4 corrective design | complete | Approved architecture | Written spec and independent contract review passed |
| P3 | Governing implementation plan | pending | Approved written spec | Detailed TDD plan reviewed and committed |
| P4 | Governance authority and R4 invalidation | pending | Governing spec/plan and clean branch | Append-only R4 red record; chain verified |
| P5 | Partition ABI and algorithm implementation | pending | RED corruption/feasibility tests | Global assignment and independent reconstruction green |
| P6 | Active R5 train-only capability migration | pending | New class-capability ABI | Legacy train authority absent; foundation isolation green |
| P7 | Four-class artifact regeneration | pending | Committed generator source | Two byte-identical candidate trees and ABI 4 artifact commit |
| P8 | R4 owner/phase/admission verification | pending | Clean artifact commit | All gates plus clean repository-owned admission pass |
| P9 | R4 green re-admission | pending | Passed exact R4 admission receipt | Append-only green record; chain verified |
| P10 | Full regression and closeout publication | pending | Re-admitted R4 | G0-R4 phases, governed suite, docs, branch review, push |
| P11 | R5 Neural Activation design/implementation | blocked | Re-admitted non-vacuous R4 | Separate approved R5 plan |

## 6. Detailed implementation checklist

### Governance and planning

- [x] Confirm exact empty-allowlist defect.
- [x] Confirm lexical global-component defect.
- [x] Confirm the intersection remains empty without lexical.
- [x] Obtain approval for R4-first corrective replay.
- [x] Obtain approval for globally coherent four-class architecture.
- [ ] Complete written-spec review.
- [ ] Add approved spec and implementation plan to document authority.
- [ ] Write append-only invalidation procedure and exact evidence binding.

### Partition contracts

- [ ] Define Partition Evidence ABI 3 schema and strict decoder.
- [ ] Define R4 Split Manifest ABI 1 schema and strict decoder.
- [ ] Define R4 Partition Sufficiency ABI 1 schema and strict decoder.
- [ ] Define Build Receipt ABI 4 exact artifact identities.
- [ ] Reject every ABI 2 training allowlist and ABI 3 build receipt as current input.
- [ ] Separate leakage-equivalence keys from stratification labels.
- [ ] Preserve every exact protected identity across all seven axes as a
  namespaced leakage hyperedge.
- [ ] Reject sentinel/coarse categorical union keys.
- [ ] Implement deterministic global component assignment.
- [ ] Implement independent verifier reconstruction.

### Data and access

- [ ] Materialize canonical train JSONL.
- [ ] Materialize canonical selection JSONL.
- [ ] Materialize canonical calibration JSONL.
- [ ] Materialize canonical frozen-test JSONL.
- [ ] Prove nonempty/disjoint/exhaustive membership.
- [ ] Prove no leakage key crosses classes.
- [ ] Prove exact payload count/hash/ref binding.
- [ ] Keep frozen-test payload unopened by training/model code.
- [ ] Mint class-scoped capabilities that disclose no sibling class identity.
- [ ] Migrate the active R5 train-only loader and trainer provenance to the R4
  train capability.
- [ ] Retire legacy `PartitionManifest`, `Partitioner`, and three-way loader
  authority with structural absence tests.

### Sufficiency and anti-vacuity

- [ ] Generate feasibility report before freezing thresholds.
- [ ] Review exact positive minimum counts.
- [ ] Require support and feasible-component denominators.
- [ ] Require held-out coverage across configured dimensions.
- [ ] Reject empty classes and zero-denominator success.
- [ ] Reject assignment changes from seed/objective/tie-break tamper.

### Replay and validation

- [ ] Append reviewed R4 red invalidation.
- [ ] Verify G0-R3 remain green and R4+ reset correctly.
- [ ] Run two independent deterministic artifact builds.
- [ ] Run all R4 owner gates.
- [ ] Run R4 phase gate.
- [ ] Run repository-owned R4 admission.
- [ ] Append exact R4 green transition.
- [ ] Verify the complete replay chain.
- [ ] Run G0-R4 phase gates and governed active suite.
- [ ] Confirm R5 remains red.

### Documentation and publication

- [ ] Update ABI registry and R4 architecture boundary.
- [ ] Add narrow supersession notices to displaced R4 partition claims.
- [ ] Regenerate living evidence receipts mechanically.
- [ ] Complete spec and quality reviews.
- [ ] Push every reviewed checkpoint to the corrective branch.
- [ ] Record final commit, artifact refs, run refs, and remote publication here.

## 7. Acceptance evidence register

| Gate/evidence | Required result | Current result | Evidence ref/location |
|---|---|---|---|
| Written design review | approved | pending | Corrective design spec |
| Frozen inventory integrity | unchanged unless separately governed | base verified | `docs/DOCUMENT_AUTHORITY.json` pin |
| R4 invalidation | append-only red | pending | replay ledger |
| Four-class source coverage | exact 400/400 | pending | split manifest |
| Class disjointness | zero overlap | pending | partition sufficiency receipt |
| Leakage isolation | zero cross-class key | pending | Partition Evidence ABI 3 |
| R5 train authority | only authenticated R4 train capability | pending | class-capability and data-isolation gates |
| Class non-vacuity | four nonempty classes | pending | partition sufficiency receipt |
| Deterministic generation | two byte-identical trees | pending | generation comparison receipt |
| Artifact integrity | exact Build Receipt ABI 4 reconstruction | pending | R4 admission report |
| R4 re-admission | passed clean committed run | pending | validation run receipt |
| Replay chain | ledger-derived accepted state | pending after repair | `update_replay_status.py --verify-chain` |
| Governed regression | zero active failures/skips | pending after repair | active-suite result |
| Remote publication | corrective branch at reviewed HEAD | pending | origin branch |

## 8. Risk register

| Risk | Severity | Mitigation | Trigger/stop condition |
|---|---|---|---|
| Correct leakage graph produces components too large for four classes | high | Generate feasibility evidence before thresholds; fail closed | Any required class cannot be nonempty without splitting a component |
| Stratification labels accidentally become union keys | high | Separate types/APIs and add coarse-value corruption tests | One broad label creates an oversized component |
| Frozen-test information leaks into training decisions | critical | Purpose-bound manifests/readers; no metrics during R4 | Training or selection code receives frozen path/hash/payload |
| Legacy partitions are reused for convenience | critical | Structural absence/authority tests | R5 config opens `data/partitions/*.jsonl` as admitted R4 data |
| Ledger is changed before governing authority exists | high | Spec/plan review and clean committed invalidation candidate first | Status mutation precedes approved authority |
| Thresholds are tuned to model results | high | Freeze from component/coverage feasibility only | Any model metric influences partition config |
| Gate/process proliferation | medium | Keep current R4 owners; one pytest process per tier | New owner or repeated corpus build is proposed without necessity |
| Generated artifacts exceed practical repository bounds | medium | Bounded canonical payloads and artifact-size gates | Candidate violates reviewed byte limits |
| Tracker becomes a second status source | high | Link ledger; ban copied mutable phase matrix/run claim | Tracker conflicts with ledger or is consumed by admission code |
| Root adoption is implied | high | Scope tests and explicit non-goal | Any root runtime/acceptance file changes |
| Exact protected axes are weakened into labels | critical | Type leakage hyperedges separately and reconstruct all seven axes | Any exact target/topology/dialogue/mutation/response identity crosses classes |
| Global split manifest leaks sibling data identities | critical | Give consumers class-scoped capabilities only | A consumer receives another class path/hash/ref/count |

## 9. Performance budget

| Operation | Bound/expectation |
|---|---|
| Source episodes | Current 400; explicit configured maximum required |
| Assignment choices | Exactly four per component |
| Graph construction | Bounded leakage keys/edges per episode |
| Assignment math | Exact integer objective only |
| Normal runtime impact | None |
| Pytest processes per validation tier | One |
| Artifact generation | Once per candidate root; twice for determinism checkpoint |
| Neural training during R4 repair | Zero |

## 10. Publication log

| Date | Branch/commit | Event | Verification |
|---|---|---|---|
| 2026-08-13 | `origin/codex/r5-hard-cut-foundation@107c518` | R5 foundation published | Full governed suite and Task 10 closeout passed |
| 2026-08-14 | `codex/r4-partition-corrective-replay@107c518` | Corrective branch created | Clean exact base; remote publication pending |

## 11. Current checkpoint

**Current work:** P3, governing implementation plan.
**Next required decision:** review of the detailed implementation plan before source or ledger mutation.
**Implementation authorization:** design approved; source, ledger, ABI, and artifact mutation remain gated on the detailed implementation plan.
**R5 neural work:** blocked on authentic R4 re-admission.

## 12. Exact invalidation evidence

The governing corrective spec binds the defect to:

- `training_allowlist_v2:51c0cc234805cdda54f8e2c7`;
- allowlist file SHA-256
  `3c47c3e66771add72a541342a5669ef5c93286356eb1ae0c0de9eb86d9b3d2db`;
- `r4_build_v3:5d5eee0ee8c0e7bb1bcba522`; and
- Build Receipt file SHA-256
  `0069ae2c8a301700498aba4801df96205f9166938e1b21d3336aa1768d75dec6`.

The future red record uses the current ledger schema. Its committed
`source_base`, not a nonexistent ledger evidence field, binds this reviewed
diagnosis.
