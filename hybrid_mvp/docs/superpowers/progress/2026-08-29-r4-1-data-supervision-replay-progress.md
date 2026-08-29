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
| T01 | Govern the executable replay and create this progress owner | in_progress | pending task commit | TR-T01 pending | RC-T01 pending | AR-T01 pending | none beyond verification evidence |
| T02 | Define strict R4.1 reviewed-source schemas and decoders | pending | pending | pending | pending | pending | exact bounded source limits |
| T03 | Author the review manifest and reviewed source package | pending | pending | pending | RC-SOURCE required | pending | reviewer refs, policy, and exact source membership |
| T04 | Compile expected cycle contracts and exact expanded cases independently | pending | pending | pending | pending | pending | diagnostic-only classifications |
| T05 | Compile proposal derivations and explicit abstention supervision | pending | pending | pending | RC-SOURCE required | pending | reviewed blueprint reuse boundary |
| T06 | Compile realization signatures, surfaces, slots, perspective, and alignments | pending | pending | pending | RC-SOURCE required | pending | authorized surface variants and literal-copy spans |
| T07 | Externalize mutation contracts and independent mutation observations | pending | pending | pending | RC-SOURCE required | pending | reviewed mutation family coverage |
| T08 | Compile explicit purpose membership and duplicate-risk evidence | pending | pending | pending | RC-SOURCE required | pending | reviewed duplicate groups and challenge holdouts |
| T09 | Enforce fixed class-local semantic denominators and sufficiency | pending | pending | pending | RC-SOURCE required | pending | exact positive minima and source-support evidence |
| T10 | Join compact `R4SupervisedCase` rows and four purpose payloads | pending | pending | pending | pending | pending | final supervised versus diagnostic universe |
| T11 | Emit the ABI 5 artifact graph, train capability, and candidate authorization | pending | pending | pending | pending | pending | exact artifact-byte bounds |
| T12 | Independently reconstruct reviewed source, supervision, allocation, and artifacts | pending | pending | pending | pending | pending | no unresolved decision recorded yet |
| T13 | Hard-cut train access to the ABI 2 authenticated supervision batch | pending | pending | pending | pending | pending | exact future R5 consumer handoff fields |
| T14 | Reconcile validation owners, inventory evidence, ABI docs, and hard-cut guards | pending | pending | pending | pending | pending | selector/input changes only if existing ownership requires them |
| T15 | Run deterministic double generation and focused/full governed validation | pending | pending | pending | pending | pending | publication checkpoint identities |
| T16 | Freeze source after independent code and reviewed-data review | pending | pending | pending | RC-CODE-DATA required | pending | reviewer findings and required amendments |
| T17 | Publish the artifact-only commit from the exact reviewed source parent | pending | pending | pending | RC-ARTIFACT required | pending | exact source-parent and artifact-tree identities |
| T18 | Run clean repository admission, append the reviewed transition, and reconstruct closeout | pending | pending | pending | RC-ADMISSION required | pending | exact admission and ledger record refs |

## Commit references

| Ref | Commit | Meaning |
|---|---|---|
| CR-DESIGN | `ef9fd67d2b896b61c5a8ba12acace8b9ed188324` | Approved R4.1 replay design |
| CR-PLAN | `44f12a2aa7cb6c0d0c3175ebddd3f163c33ccdcf` | Governing executable replay plan and Task 1 source base |
| CR-T01 | pending | Task 1 governance/tracker commit; recorded only after commit exists |
| CR-SOURCE-FREEZE | pending | Reviewed source parent for deterministic publication |
| CR-ARTIFACT | pending | Artifact-only publication commit |
| CR-CLOSEOUT | pending | Final governance-only closeout commit, if required |

## Test receipts

| Ref | Scope | Evidence |
|---|---|---|
| TR-ENTRY | Focused entry baseline | Task dispatch reports 108 passing tests; no repository receipt ref was supplied |
| TR-T01-RED | Task 1 governance RED | One pytest process; focused 4-node command; 2 failed and 2 passed because the tracker file/classification did not yet exist |
| TR-T01 | Task 1 focused governance GREEN | One pytest process; same focused 4-node command; 4 passed after authority/tracker implementation |
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
