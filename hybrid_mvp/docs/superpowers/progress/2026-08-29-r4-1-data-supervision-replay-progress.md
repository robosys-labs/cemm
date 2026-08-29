# R4.1 Data and Supervision Replay Progress

**Historical/operational evidence only.**

governance/replay_status.jsonl is the sole phase-status authority. This
tracker does not copy a mutable phase matrix, does not claim replay completion,
and cannot admit a phase, artifact, model, or root-runtime change. Task state
below is work coordination evidence only and must be reconciled against the
governing design, governing implementation plan, committed source, exact test
evidence, and the append-only ledger before any release decision.

## Task register

State vocabulary: `in_progress`, `pending`, `blocked`, `stopped`, `complete`
`complete` is terminal. A task state is not a phase state. No task is recorded
as complete until its exact commit, test, review, and artifact evidence has
been added after the work exists.

| Task | Deliverable | State | Commit ref | Test receipt | Review checkpoint | Artifact ref | Unresolved decision |
|---|---|---|---|---|---|---|---|
| T01 | Govern the executable replay and create the progress owner | complete | CR-T01, CR-T01-ALIGN, CR-T01-HARDEN, CR-T01-CLAIMS, and CR-T01-TENSE | TR-T01-TENSE, TR-R4-SELECTOR, TR-INVENTORY-G0, TR-INVENTORY-R4, and TR-STATIC | RC-T01 satisfied | AR-T01 satisfied | none |
| T02 | Add strict reviewed-source schemas and immutable decoders | complete | CR-T02, CR-T02-HARDEN, and CR-T02-BOUND | TR-T02, TR-T02-GOVERNANCE, TR-INVENTORY-G0-T02, TR-INVENTORY-R4-T02, and TR-T02-STATIC | RC-T02 satisfied | AR-T02 satisfied | none |
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
| CR-T01-ALIGN | `86eb9fb7a5841c0fa246a9453d99a033cab6e13c` | Task 1 exact plan-mapping review fix |
| CR-T01-HARDEN | `28ddd332afe590f75f617bc381628b2c9f4797da` | Task 1 quality hardening commit |
| CR-T01-CLAIMS | `69b2363f014b5758aff1f19749d0f33b672b99a4` | Reject positive tracker authority/completion claims and arbitrary task states |
| CR-T01-TENSE | `17786dffd31691d843668c096c1f33cc06c9d844` | Cover tracker authority-claim tense, aspect, helper, and spelling variants |
| CR-T02 | `2ac69b45de1a31dc53150f84869c720156ca1f45` | Initial strict R4.1 reviewed-source schemas, immutable decoders, and exact R4 owner integration |
| CR-T02-HARDEN | `7826a15befbd87d772c744960a9bb91190107ef2` | Close exact-ABI, provenance, nested-factory, Program-shape, realization-signature, literal-source, and purpose-integrity review findings |
| CR-T02-BOUND | `413c64c9a4b541ef4b127617203df02e9bf4fd8e` | Align challenge-holdout refs with actual authority namespaces and make schema/JSON validation bounded |
| CR-SOURCE-FREEZE | pending | Reviewed source parent for deterministic publication |
| CR-ARTIFACT | pending | Artifact-only publication commit |
| CR-CLOSEOUT | pending | Final governance-only closeout commit, if required |

## Test receipts

| Ref | Scope | Evidence |
|---|---|---|
| TR-ENTRY | Focused entry baseline | Task dispatch reports 108 passing tests; no repository receipt ref was supplied |
| TR-T01-RED | Task 1 governance RED | `python -m pytest tests/test_replay_governance.py -q -p no:cacheprovider -k "document_authority_is_scoped_and_classifications_are_exact or authority_cleanup_classifies_every_authority_like_document_once or corrective_tracker_is_operational_not_status_authority or initial_replay_status_is_truthful_and_receipt_free"` returned 2 failed, 2 passed before the tracker/classification existed |
| TR-T01 | Task 1 focused governance GREEN | The exact TR-T01-RED command returned 4 passed after initial implementation |
| TR-T01-REVIEW-RED | Task 1 exact task mapping RED | `python -m pytest tests/test_replay_governance.py::test_corrective_tracker_is_operational_not_status_authority -q -p no:cacheprovider` returned 1 failed before exact T01-T18 alignment |
| TR-T01-REVIEW | Task 1 exact task mapping GREEN | The exact TR-T01-REVIEW-RED command returned 1 passed after verbatim alignment |
| TR-T01-HARDEN-RED | Task 1 governance hardening RED | `python -m pytest tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority -q -p no:cacheprovider` returned 1 failed because terminal `complete` was absent |
| TR-T01-HARDEN | Task 1 governance hardening GREEN | The exact TR-T01-HARDEN-RED command returned 1 passed after hardening |
| TR-T01-CLAIMS-RED | Task 1 authority/state mutation RED | `python -m pytest tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority -q -p no:cacheprovider` returned 1 failed because the appended positive tracker claim was not rejected |
| TR-T01-CLAIMS | Task 1 authority/state mutation GREEN | The exact TR-T01-CLAIMS-RED command returned 1 passed after positive-claim and arbitrary-state rejection |
| TR-T01-TENSE-RED | Task 1 authority-claim tense mutation RED | `python -m pytest tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority -q -p no:cacheprovider` returned 1 failed because a past-tense admission claim was not rejected |
| TR-T01-TENSE | Task 1 authority-claim tense mutation GREEN | The exact TR-T01-TENSE-RED command returned 1 passed after independent admit, authorize, and declare-complete tense/aspect coverage with negative-disclaimer controls |
| TR-T02-RED | Task 2 contract and review RED | The initial one-process contract run returned two collection errors before the canonical owners existed; subsequent adversarial cycles reproduced boolean ABI acceptance, spoofed review provenance, invalid Program selectors/local graphs, forged nested objects, input-as-output tag confusion, incomplete realization signatures, asymmetric purpose membership, invalid holdout identities, quadratic object-array uniqueness, authority-prefix drift, schema length drift, and unbounded hostile JSON rejection |
| TR-T02 | Task 2 one-process contract GREEN | `python -m pytest tests/test_r4_supervision_contracts.py tests/test_r4_purpose_contracts.py -q -p no:cacheprovider` returned 34 passed after CR-T02-BOUND |
| TR-T02-GOVERNANCE | Existing R4 owner and topology GREEN | The exact R4 data-owner selector, single-process gate topology, and tracker-governance checks returned 3 passed; `r4_data_owner_tests` contains 70 exact nodes and no new phase, step, tier, or pytest process |
| TR-INVENTORY-G0-T02 | Task 2 G0 source-only inventory reconstruction | `python scripts/check_test_inventory.py --phase G0 --source-only` passed: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:86877b61da28afac03598247`, active set `active_test_nodes:8113493d949eb028b4e3a06c` with 190 nodes, collectable set `collectable_test_nodes:b8b532c0d19aaa81ba169e12` with 1,870 nodes |
| TR-INVENTORY-R4-T02 | Task 2 R4 source-only inventory reconstruction | `python scripts/check_test_inventory.py --phase R4 --source-only` passed: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:86877b61da28afac03598247`, active set `active_test_nodes:f00692beac3ea4c9bd978284` with 1,588 nodes, collectable set `collectable_test_nodes:b8b532c0d19aaa81ba169e12` with 1,870 nodes |
| TR-T02-STATIC | Task 2 static and bounded-validation evidence | Python compilation, strict JSON parsing, all five Draft 2020-12 schema checks and `git diff --check` passed; the non-gating 4,096-membership schema benchmark improved from about 18.02 seconds to 1.44 seconds after redundant object-array `uniqueItems` validation was removed, while indexed decoder uniqueness remained mandatory |
| TR-R4-SELECTOR | Exact R4 selector/config GREEN | `python -m pytest tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority tests/test_validation_gate.py::test_r4_gate_plans_are_exact_bounded_and_single_process -q -p no:cacheprovider` returned 2 passed |
| TR-INVENTORY-G0 | G0 source-only inventory reconstruction | `python scripts/check_test_inventory.py --phase G0 --source-only` passed: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:d20d307eeae959dd7b7dc2cc`, active set `active_test_nodes:7ec97bc4c63c6824928f9681` with 190 nodes, collectable set `collectable_test_nodes:7344a87282c6685a08348d3c` with 1,836 nodes |
| TR-INVENTORY-R4 | R4 source-only inventory reconstruction | `python scripts/check_test_inventory.py --phase R4 --source-only` passed: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:d20d307eeae959dd7b7dc2cc`, active set `active_test_nodes:5c2d7d60fdea1668c75dc4fb` with 1,554 nodes, collectable set `collectable_test_nodes:7344a87282c6685a08348d3c` with 1,836 nodes |
| TR-STATIC | Task 1 static validation | `python -m py_compile tests/test_replay_governance.py tests/test_validation_gate.py`; `python -m json.tool docs/DOCUMENT_AUTHORITY.json`; `python -m json.tool configs/validation_gates.json`; `git diff --check`; all exited 0 in the final pre-commit check |
| TR-DETERMINISM | Two byte-identical candidate trees | pending |
| TR-PREADMISSION | Bounded governed validation | pending |
| TR-ADMISSION | Clean repository-owned R4 admission | pending |

## Review checkpoints

| Ref | State | Evidence required |
|---|---|---|
| RC-DESIGN | satisfied | CR-DESIGN |
| RC-PLAN | satisfied | CR-PLAN and exact document-authority ordering |
| RC-T01 | satisfied | Requirements review PASS and quality review APPROVED for CR-T01 through CR-T01-TENSE, with the focused, selector, inventory, metadata, compile, JSON, and diff evidence recorded above |
| RC-T02 | satisfied | Independent specification review PASS and quality review APPROVED through CR-T02-BOUND; all reproduced trust-boundary and performance findings are closed, and the Task 2 checkpoint remains source-free and fail-closed |
| RC-SOURCE | pending | Separate human approval of exact reviewed source bytes before artifact publication |
| RC-CODE-DATA | pending | Independent code and reviewed-data findings resolved against frozen source |
| RC-ARTIFACT | pending | Exact source-parent and byte-identical artifact tree reviewed |
| RC-ADMISSION | pending | Clean admission receipt and append-only transition candidate reviewed |

## Artifact references

| Ref | State | Path or identity |
|---|---|---|
| AR-T01 | satisfied | `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`; `docs/DOCUMENT_AUTHORITY.json`; `tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority`; `tests/test_validation_gate.py::test_r4_gate_plans_are_exact_bounded_and_single_process`; `configs/validation_gates.json::r4_phase_tests`; inventory `test_inventory:c715e262526c0ea26a6fef90`; literal metadata `literal_test_metadata:d20d307eeae959dd7b7dc2cc`; G0 selector `active_test_nodes:7ec97bc4c63c6824928f9681`; R4 selector `active_test_nodes:5c2d7d60fdea1668c75dc4fb` |
| AR-T02 | satisfied | Contract sources only: five `schemas/r4_*` reviewed-source schemas, `src/cemm_authoritative_hybrid/_r4_source_codec.py`, `r4_supervision.py`, `r4_purpose.py`, and their two exact test owners; no reviewed source package, compiled candidate, build receipt, or admitted artifact exists |
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
