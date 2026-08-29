# R4.1 Data and Supervision Replay Progress

**Historical/operational evidence only.**

governance/replay_status.jsonl is the sole phase-status authority. This
tracker does not copy a mutable phase matrix, does not claim replay completion,
and cannot admit a phase, artifact, model, or root-runtime change. Task state
below is work coordination evidence only and must be reconciled against the
governing design, governing implementation plan, committed source, exact test
evidence, and the append-only ledger before any release decision.

## Task register

State vocabulary: `in_progress`, `pending`, `blocked`, `stopped`. A task state
is not a phase state. No task is recorded as complete until its exact commit,
test, review, and artifact evidence has been added after the work exists.

| Task | Deliverable | State | Commit ref | Test receipt | Review checkpoint | Artifact ref | Unresolved decision |
|---|---|---|---|---|---|---|---|
| T01 | Govern the executable replay and create the progress owner | in_progress | CR-T01 | TR-T01 and TR-T01-REVIEW | RC-T01 pending | AR-T01 pending | none beyond verification evidence |
| T02 | Add strict reviewed-source schemas and immutable decoders | pending | pending | pending | pending | pending | exact bounded source limits |
| T03 | Authenticate the review manifest and source bundle | pending | pending | pending | RC-SOURCE required | pending | reviewer refs, policy, and exact source membership |
| T04 | Check in the independently reviewed source package | pending | pending | pending | RC-SOURCE required | pending | diagnostic-only classifications and exact reviewed bytes |
| T05 | Compile proposal derivations and typed abstentions independently | pending | pending | pending | RC-SOURCE required | pending | reviewed blueprint reuse boundary |
| T06 | Compile ResponseMeaning-to-surface supervision independently | pending | pending | pending | RC-SOURCE required | pending | authorized surface variants and literal-copy spans |
| T07 | Make mutation truth independent of mutation execution | pending | pending | pending | RC-SOURCE required | pending | reviewed mutation family coverage |
| T08 | Replace global semantic union with reviewed purpose ownership | pending | pending | pending | RC-SOURCE required | pending | reviewed duplicate groups and challenge holdouts |
| T09 | Prove fixed class-local semantic sufficiency | pending | pending | pending | RC-SOURCE required | pending | exact positive minima and source-support evidence |
| T10 | Build compact supervised cases and four payloads | pending | pending | pending | pending | pending | final supervised versus diagnostic universe |
| T11 | Version the R4 artifact graph to ABI 5 | pending | pending | pending | pending | pending | exact artifact-byte bounds |
| T12 | Independently reconstruct admission and train access | pending | pending | pending | pending | pending | exact independent reconstruction and ABI 2 train boundary |
| T13 | Quarantine ineligible R5 supervision consumers | pending | pending | pending | pending | pending | exact blocked consumer set before the R5 plan |
| T14 | Retire predecessor current paths and migrate exact test authority | pending | pending | pending | pending | pending | selector/input changes only when exact ownership requires them |
| T15 | Generate twice, review data, and publish the artifact-only commit | pending | pending | pending | RC-CODE-DATA and RC-ARTIFACT required | pending | exact source-parent and byte-identical artifact-tree identities |
| T16 | Run clean repository-owned admission | pending | pending | pending | RC-ADMISSION required | pending | exact clean admission receipt and run refs |
| T17 | Append R4 green and close the replay | pending | pending | pending | RC-ADMISSION required | pending | exact append-only ledger record and closeout refs |
| T18 | Produce the R5 handoff audit without implementing R5 | pending | pending | pending | pending | pending | exact eligible handoff evidence and confirmed R5 quarantine |

## Commit references

| Ref | Commit | Meaning |
|---|---|---|
| CR-DESIGN | `ef9fd67d2b896b61c5a8ba12acace8b9ed188324` | Approved R4.1 replay design |
| CR-PLAN | `44f12a2aa7cb6c0d0c3175ebddd3f163c33ccdcf` | Governing executable replay plan and Task 1 source base |
| CR-T01 | `27b8a5a1295b8f49c30a63e67110b71b19a0c122` | Initial Task 1 governance/tracker commit; exact-mapping review fix follows separately |
| CR-SOURCE-FREEZE | pending | Reviewed source parent for deterministic publication |
| CR-ARTIFACT | pending | Artifact-only publication commit |
| CR-CLOSEOUT | pending | Final governance-only closeout commit, if required |

## Test receipts

| Ref | Scope | Evidence |
|---|---|---|
| TR-ENTRY | Focused entry baseline | Task dispatch reports 108 passing tests; no repository receipt ref was supplied |
| TR-T01-RED | Task 1 governance RED | One pytest process; focused 4-node command; 2 failed and 2 passed because the tracker file/classification did not yet exist |
| TR-T01 | Task 1 focused governance GREEN | One pytest process; same focused 4-node command; 4 passed after authority/tracker implementation |
| TR-T01-REVIEW-RED | Task 1 exact task mapping RED | One pytest process; exact tracker test failed at T01 before the reviewed one-for-one mapping was applied |
| TR-T01-REVIEW | Task 1 exact task mapping GREEN | One pytest process; exact tracker test passed after T01-T18 were aligned verbatim |
| TR-INVENTORY | G0/R4 source-only inventory reconstruction | pending |
| TR-DETERMINISM | Two byte-identical candidate trees | pending |
| TR-PREADMISSION | Bounded governed validation | pending |
| TR-ADMISSION | Clean repository-owned R4 admission | pending |

## Review checkpoints

| Ref | State | Evidence required |
|---|---|---|
| RC-DESIGN | satisfied | CR-DESIGN |
| RC-PLAN | satisfied | CR-PLAN and exact document-authority ordering |
| RC-T01 | pending | Task 1 self-review plus fresh verification |
| RC-SOURCE | pending | Separate human approval of exact reviewed source bytes before artifact publication |
| RC-CODE-DATA | pending | Independent code and reviewed-data findings resolved against frozen source |
| RC-ARTIFACT | pending | Exact source-parent and byte-identical artifact tree reviewed |
| RC-ADMISSION | pending | Clean admission receipt and append-only transition candidate reviewed |

## Artifact references

| Ref | State | Path or identity |
|---|---|---|
| AR-T01 | pending | This tracker, `docs/DOCUMENT_AUTHORITY.json`, governed test-node metadata, and its existing validation input |
| AR-REVIEW-MANIFEST | pending | `data/review/r4_1/REVIEW_MANIFEST.json` |
| AR-SUPERVISION | pending | Reviewed proposal, realization, mutation, and purpose source package |
| AR-BUILD | pending | `artifacts/r4/BUILD_RECEIPT.json` at ABI 5 plus its exact artifact graph |
| AR-TRAIN-CAPABILITY | pending | ABI 2 train capability and authorization projection |
| AR-ADMISSION | pending | Exact repository-owned admission receipt and run evidence |
| AR-LEDGER | unchanged | `governance/replay_status.jsonl`; only the reviewed status updater may append |

The checked-in predecessor R4 artifact tree is invalidated historical evidence.
Listing its path here does not promote, rebuild, or admit it.

## Unresolved decisions

| Ref | Decision owner | Stop condition |
|---|---|---|
| UD-01 | Reviewed source approval | Reviewer refs, policy, exact source membership, and source hashes are not approved together |
| UD-02 | Proposal supervision review | A semantic case lacks exact compiling derivation gold or a gap lacks explicit abstention gold |
| UD-03 | Realization supervision review | Perspective, semantic slots, authorized surface, or literal alignment is unresolved |
| UD-04 | Mutation review | Expected earliest owner or effect/no-effect truth is not independent of execution output |
| UD-05 | Purpose review | Duplicate-risk membership, challenge holdouts, or exact purpose assignment is unresolved |
| UD-06 | Sufficiency review | Stable denominators or fixed positive class-local minima remain unsupported or unapproved |
| UD-07 | Publication review | Frozen source parent, deterministic artifact identities, or byte bounds disagree |
| UD-08 | Admission review | Clean admission evidence or the exact append-only transition candidate is unresolved |

No unresolved decision may be replaced by solver output, bootstrap output,
mutable runtime observations, or a task-state edit in this file.
