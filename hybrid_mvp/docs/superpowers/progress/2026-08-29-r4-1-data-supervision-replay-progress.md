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
| T03 | Authenticate the review manifest and source bundle | in_progress | CR-T03, CR-T03-HARDEN, CR-T03-TOPOLOGY, CR-SOURCE-READINESS-GOV, CR-SOURCE-READINESS-HARDEN, CR-SOURCE-READINESS-SR1, and CR-SOURCE-READINESS-SR1-TOPOLOGY | TR-T03, TR-T03-GOVERNANCE, TR-INVENTORY-G0-T03, TR-INVENTORY-R4-T03, TR-T03-STATIC, TR-SOURCE-READINESS-GOV, TR-SOURCE-READINESS-HARDEN, TR-SOURCE-READINESS-SR1, TR-SOURCE-READINESS-SR1-INVENTORY, and TR-SOURCE-READINESS-SR1-STATIC | RC-T03 satisfied; RC-SOURCE-READINESS SR1 independently reviewed PASS through exact topology alignment, SR2-SR6 pending | AR-T03 and AR-SOURCE-UNIVERSE satisfied | SR1 source-only pin ownership, bounded expansion, exact source dispositions and current 210-to-400 reconstruction are complete; SR2-SR5 must still implement selector/assignment/rejection truth, all-supervised realization, purpose rejection membership, cross-source completeness and exact review worksheets before the human-approved canonical scenario patch can be applied in SR6 |
| T04 | Check in the independently reviewed source package | pending | pending | pending | RC-SOURCE-READINESS and RC-SOURCE required | pending | two committed SR6 changes (approved canonical scenario patch, then approval evidence), successor-universe-derived identities/counts, diagnostic-only restart classification and exact reviewed package bytes |
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
| CR-T03 | `8569b8c4fee0574dfded00eef41f927e02c3ceaf` | Add the exact six-file, bounded, read-once reviewed-source authentication loader |
| CR-T03-HARDEN | `ed6383ce254cc480501f278950f7c5d79a86c43b` | Remove the public authenticated-bundle mint, handle bounded partial/EINTR reads on one descriptor, and eliminate duplicate decoding |
| CR-T03-TOPOLOGY | `5810c40f3d74a2e662eb208dee266169d4f4155a` | Align the exact single-process R4 data-owner count with the 92 authenticated-loader contract nodes |
| CR-SOURCE-READINESS-GOV | `ef928a6b52fc4a49c8884998ba259100cd747594` | Govern the pre-source SR1-SR6 correction, block Task 4, and preserve exact design-before-plan authority ordering without adding a gate tier or process |
| CR-SOURCE-READINESS-HARDEN | `c2ac8f21b3a1d34aafe119d2db3ae3478f6b3af0` | Resolve source-readiness review findings for internal source pins, bounded iterables, selector/assignment/rejection ownership, all-supervised realization, cross-source completeness, canonical patch application, approval classification and five-row ABI registry reconciliation |
| CR-SOURCE-READINESS-SR1 | `af63ca962f281663555b14a564632eaed3e36ef9` | Establish the canonical bounded model-free source universe, remove duplicate gap truth, classify exact source dispositions, migrate three frozen assertions through explicit R4 successors, reconcile ABI truth and regenerate living inventory evidence without changing frozen governance authority |
| CR-SOURCE-READINESS-SR1-TOPOLOGY | `88702baf16289fcc65cc436141929b645be727dc` | Align the living R4 selector-count assertion with the exact 42/93/8 SR1 owner-node topology and regenerate dependent G0/R5 inventory evidence without changing selector structure or frozen authority |
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
| TR-T03 | Task 3 authenticated-loader GREEN | `python -m pytest tests/test_r4_supervision_contracts.py tests/test_r4_purpose_contracts.py -q -p no:cacheprovider` returned 56 passed after CR-T03-HARDEN; exactly six file opens produced one manifest decode and five non-manifest validations |
| TR-T03-GOVERNANCE | Existing R4 owner and topology GREEN | The repository-owned R4 `mutation-partition` owner passed with governance, source compilation and one `r4_data_owner_tests` process; the selector contains 92 exact nodes with no new phase, step, tier, input, or pytest process |
| TR-INVENTORY-G0-T03 | Task 3 G0 source-only inventory reconstruction | `python scripts/check_test_inventory.py --phase G0 --source-only` passed after CR-T03-TOPOLOGY: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:b74133490fe4916290cf5c1c`, active set `active_test_nodes:8113493d949eb028b4e3a06c` with 190 nodes, collectable set `collectable_test_nodes:5de14f280aaf506e793484e5` with 1,892 nodes |
| TR-INVENTORY-R4-T03 | Task 3 R4 source-only inventory reconstruction | `python scripts/check_test_inventory.py --phase R4 --source-only` passed after CR-T03-TOPOLOGY: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:b74133490fe4916290cf5c1c`, active set `active_test_nodes:910a58399db4588e9927edfd` with 1,610 nodes, collectable set `collectable_test_nodes:5de14f280aaf506e793484e5` with 1,892 nodes |
| TR-T03-STATIC | Task 3 bounded-I/O and static evidence | Python compilation, JSON/config parsing and `git diff --check` passed; normal six-file fixture authentication took about 0.20 seconds, file reads are bounded to 8,192 same-descriptor attempts per file and 49,152 aggregate attempts, and the portable restored-ancestor/remote-filesystem limitation is documented rather than overclaimed |
| TR-SOURCE-READINESS-GOV-RED | Source-readiness governance RED | `python -m pytest tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority -q -p no:cacheprovider` returned 1 failed because the correction design/plan were absent from the exact post-main-plan authority positions |
| TR-SOURCE-READINESS-GOV | Source-readiness governance GREEN | The scoped authority, authority-like classification, operational tracker and exact R4 gate topology command returned 4 passed after CR-SOURCE-READINESS-GOV; the existing tracker node enforces correction-doc ordering, Task 3 routing, SR1-SR6 headings and absence of a second Task 1-18 namespace |
| TR-SOURCE-READINESS-INVENTORY-G0 | Source-readiness G0 source-only inventory | `python scripts/check_test_inventory.py --phase G0 --source-only` passed: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:82a25fe8004072c60fd033c2`, active set `active_test_nodes:8113493d949eb028b4e3a06c` with 190 nodes, collectable set `collectable_test_nodes:5de14f280aaf506e793484e5` with 1,892 nodes |
| TR-SOURCE-READINESS-INVENTORY-R4 | Source-readiness R4 source-only inventory | `python scripts/check_test_inventory.py --phase R4 --source-only` passed: inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:82a25fe8004072c60fd033c2`, active set `active_test_nodes:910a58399db4588e9927edfd` with 1,610 nodes, collectable set `collectable_test_nodes:5de14f280aaf506e793484e5` with 1,892 nodes |
| TR-SOURCE-READINESS-STATIC | Source-readiness static evidence | Governing-document scans, Python compilation, all schema/config/document JSON parsing and `git diff --check` passed; no runtime, contract, reviewed-source, artifact, selector topology or process count changed |
| TR-SOURCE-READINESS-HARDEN-RED | Source-readiness review-contract RED | The existing tracker/governance node failed after assertions were added for the 13 rejected-review requirements because the first correction design lacked internal pin ownership and the dependent hardening contracts |
| TR-SOURCE-READINESS-HARDEN | Source-readiness review-contract GREEN | The scoped authority, authority-like classification, operational tracker and exact R4 topology command returned 4 passed after CR-SOURCE-READINESS-HARDEN; the existing node now enforces internal source-pin/bound markers, closed selector/source-assignment/rejection ownership, all-supervised realization, cross-source joins, SR5 exact-byte promotion, SR6 canonical patch sequencing, approval classification, five-row registry reconciliation and cwd-correct Git staging |
| TR-SOURCE-READINESS-HARDEN-INVENTORY | Source-readiness hardening source-only inventories | G0 and R4 source-only reconstruction passed with inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:594ec0d35e08e57c2842e525`, active G0 set `active_test_nodes:8113493d949eb028b4e3a06c` with 190 nodes, active R4 set `active_test_nodes:910a58399db4588e9927edfd` with 1,610 nodes, and collectable set `collectable_test_nodes:5de14f280aaf506e793484e5` with 1,892 nodes |
| TR-SOURCE-READINESS-SR1 | SR1 source-universe and contract GREEN | One-process focused source, assertion-compiler, expansion/CLI, mutation, sufficiency, supervision and inventory tests passed after both independent reviews; canonical reconstruction remains 210 scenarios to 400 expanded cases with exact dispositions 248 semantic, 112 explicit gap, 20 verification rejection and 20 restart diagnostic candidate |
| TR-SOURCE-READINESS-SR1-INVENTORY | SR1 exact inventory and successor reconstruction | G0 and R4 source-only checks passed through CR-SOURCE-READINESS-SR1-TOPOLOGY with immutable inventory `test_inventory:c715e262526c0ea26a6fef90`, literal metadata `literal_test_metadata:3ecb5c862041e1732020644d`, active G0 set `active_test_nodes:8113493d949eb028b4e3a06c` with 190 nodes, active R4 set `active_test_nodes:dfd83f5713eea2a66f408af7` with 1,623 nodes, and collectable set `collectable_test_nodes:0a83e58f2b28f4003f5ee6c5` with 1,905 nodes; exact R4 owner counts are 42 expected-contract, 93 mutation-partition and 8 surface-expansion, while `governance/test_inventory.json` and `governance/r5_test_dispositions.json` remained unchanged |
| TR-SOURCE-READINESS-SR1-STATIC | SR1 deterministic and bounded static evidence | Scenario generation is byte-identical to checked source at SHA-256 `88a22052ee2dc6a9759d64acbb60ebcc74f5c129723e4c7a26d149d302810f8e`; two CLI expansions are byte-identical at output SHA-256 `34c74301a33770fe0500b1230d68d7e8807436be7700418936c4550df0d54d7d`; the sorted-LF case-ref digest is `262e9f6de46ceeb991e3cb8abda2df143b866c2f5c77bccd00c3856a2916764d`; compilation, strict JSON checks, generated-receipt reconstruction and `git diff --check` passed; independent specification and quality re-reviews both returned PASS |
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
| RC-T03 | satisfied | Independent specification review PASS and quality review APPROVED through CR-T03-HARDEN; the post-review exact topology assertion is green at CR-T03-TOPOLOGY; loader-only minting, partial/EINTR handling, once-only decoding, path/identity checks and bounded failure behavior were adversarially verified |
| RC-SOURCE-READINESS | pending | SR1 is committed at CR-SOURCE-READINESS-SR1 plus CR-SOURCE-READINESS-SR1-TOPOLOGY and independently reviewed PASS; SR2-SR5 implementation commits, deterministic exactly promoted source-only worksheets and one exact human approval of the scenario patch and all supervision/purpose decisions remain required; then two SR6 commits must occur in order—approved canonical scenario patch with verified successor universe, followed by approval evidence classified exactly once as historical/operational review evidence |
| RC-SOURCE | pending | Separate human approval of exact reviewed source bytes before artifact publication |
| RC-CODE-DATA | pending | Independent code and reviewed-data findings resolved against frozen source |
| RC-ARTIFACT | pending | Exact source-parent and byte-identical artifact tree reviewed |
| RC-ADMISSION | pending | Clean admission receipt and append-only transition candidate reviewed |

## Artifact references

| Ref | State | Path or identity |
|---|---|---|
| AR-T01 | satisfied | `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`; `docs/DOCUMENT_AUTHORITY.json`; `tests/test_replay_governance.py::test_r4_1_replay_tracker_is_operational_not_status_authority`; `tests/test_validation_gate.py::test_r4_gate_plans_are_exact_bounded_and_single_process`; `configs/validation_gates.json::r4_phase_tests`; inventory `test_inventory:c715e262526c0ea26a6fef90`; literal metadata `literal_test_metadata:d20d307eeae959dd7b7dc2cc`; G0 selector `active_test_nodes:7ec97bc4c63c6824928f9681`; R4 selector `active_test_nodes:5c2d7d60fdea1668c75dc4fb` |
| AR-T02 | satisfied | Contract sources only: five `schemas/r4_*` reviewed-source schemas, `src/cemm_authoritative_hybrid/_r4_source_codec.py`, `r4_supervision.py`, `r4_purpose.py`, and their two exact test owners; no reviewed source package, compiled candidate, build receipt, or admitted artifact exists |
| AR-T03 | satisfied | Loader contract only: `src/cemm_authoritative_hybrid/r4_supervision.py::load_authenticated_r4_review_bundle` and its exact bounded-I/O tests; the real repository load fails closed because `data/review/r4_1/REVIEW_MANIFEST.json` is intentionally absent pending RC-SOURCE |
| AR-SOURCE-UNIVERSE | satisfied | Canonical source-only seam `src/cemm_authoritative_hybrid/r4_expansion.py::expand_reviewed_source_universe`, strict CLI `scripts/expand_r4_cases.py`, reviewed scenario source SHA-256 `88a22052ee2dc6a9759d64acbb60ebcc74f5c129723e4c7a26d149d302810f8e`, 400-case sorted-LF identity `262e9f6de46ceeb991e3cb8abda2df143b866c2f5c77bccd00c3856a2916764d`, and exact disposition counts 248/112/20/20; this is source-readiness evidence only and is not a reviewed R4.1 package or phase admission |
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
