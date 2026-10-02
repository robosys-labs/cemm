"""Direct-owner admitted lookup; publication still requires independent review."""
from dataclasses import replace

import pytest

__cemm_test_inventory__ = {
    "tests/test_foundation_admitted_designations.py::test_readonly_integrity_inspection_registers_populated_unicode_index": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:readonly-integrity-inspection-registers-populated-unicode-index",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5a89b3b12969e19d1c706ea701b4f99d9afd6c6806aad92883b15b082c6b8a7d"
    },
    "tests/test_foundation_admitted_designations.py::test_designation_reads_do_not_coerce_structured_json_into_text[memory]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:designation-reads-do-not-coerce-structured-json-into-text-memory",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "4739e862429b142cc8e2d0c0c8e91871a990427607fea7c2b0608afe1b14378f"
    },
    "tests/test_foundation_admitted_designations.py::test_designation_reads_do_not_coerce_structured_json_into_text[sqlite]": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:designation-reads-do-not-coerce-structured-json-into-text-sqlite",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "4739e862429b142cc8e2d0c0c8e91871a990427607fea7c2b0608afe1b14378f"
    },
    "tests/test_foundation_admitted_designations.py::test_structured_designation_growth_is_excluded_by_sql_indexes": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:structured-designation-growth-is-excluded-by-sql-indexes",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "39c549f3ca65ab5c45f630642be1154c0783a6e5b4aab681e1a871a8dc3cf9a1"
    },
    "tests/test_foundation_admitted_designations.py::test_designation_text_index_migration_preserves_existing_store_once": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:designation-text-index-migration-preserves-existing-store-once",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "5467984b37c32a2cdc3f84cb884b8ab4720b9e6aaf321c6ac95fb6b79ce9ae2a"
    },

    "tests/test_foundation_admitted_designations.py::test_admitted_reader_survives_current_proposer_change_without_writes": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:admitted-reader-survives-current-proposer-change-without-writes",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "043fd8c6043b0807b9774f02d18ee8cfec85b8c4e4ae92b583210473a65d7060"
    },
    "tests/test_foundation_admitted_designations.py::test_publication_preserves_cross_turn_models_and_reads_under_new_proposer": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:publication-preserves-cross-turn-models-and-reads-under-new-proposer",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "c4a7e04632ab462e13d91c1818313bacdba016c2eb35f79de8f2a6dd243baea1"
    },
    "tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_foreign_historical_publication_model": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:admitted-reader-rejects-foreign-historical-publication-model",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-5",
        "owner_ref": "effect-learning-response",
        "source_ast_sha256": "f75845b6dcffd37443ec7ed136eab91b6a4bb84bfcd2d153599c82febb3f1341"
    },
'tests/test_foundation_admitted_designations.py::test_admitted_reader_retains_actual_publication_proof[memory]': {'activation_phase': 'R3',
                                                                                                                   'assertion_ref': 'assertion:admitted-reader-retains-actual-publication-proof-memory',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-5',
                                                                                                                   'owner_ref': 'effect-learning-response',
                                                                                                                   'source_ast_sha256': '7dc750eb6994eff8b3bf972dc27853b2e7c7bfcfab72b9c99ad254af67aa7db9'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_retains_actual_publication_proof[sqlite]': {'activation_phase': 'R3',
                                                                                                                   'assertion_ref': 'assertion:admitted-reader-retains-actual-publication-proof-sqlite',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-5',
                                                                                                                   'owner_ref': 'effect-learning-response',
                                                                                                                   'source_ast_sha256': '7dc750eb6994eff8b3bf972dc27853b2e7c7bfcfab72b9c99ad254af67aa7db9'},
 'tests/test_foundation_admitted_designations.py::test_reader_merges_static_exact_before_unicode_fold[memory]': {'activation_phase': 'R3',
                                                                                                                 'assertion_ref': 'assertion:reader-merges-static-exact-before-unicode-fold-memory',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-5',
                                                                                                                 'owner_ref': 'effect-learning-response',
                                                                                                                 'source_ast_sha256': 'abe07837d0ec51cc7473b4a41d78ca63407668a4e481d49b55050da6b96a20f2'},
 'tests/test_foundation_admitted_designations.py::test_reader_merges_static_exact_before_unicode_fold[sqlite]': {'activation_phase': 'R3',
                                                                                                                 'assertion_ref': 'assertion:reader-merges-static-exact-before-unicode-fold-sqlite',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'Foundation-Task-5',
                                                                                                                 'owner_ref': 'effect-learning-response',
                                                                                                                 'source_ast_sha256': 'abe07837d0ec51cc7473b4a41d78ca63407668a4e481d49b55050da6b96a20f2'},
 'tests/test_foundation_admitted_designations.py::test_reader_excludes_naked_fact_and_rejects_claimed_lineage[memory]': {'activation_phase': 'R3',
                                                                                                                         'assertion_ref': 'assertion:reader-excludes-naked-fact-and-rejects-claimed-lineage-memory',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-5',
                                                                                                                         'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '066989da526f7abda7ed7d9ff58a0fec48cf8c827641d396a6ea19b227fd2ca1'},
 'tests/test_foundation_admitted_designations.py::test_reader_excludes_naked_fact_and_rejects_claimed_lineage[sqlite]': {'activation_phase': 'R3',
                                                                                                                         'assertion_ref': 'assertion:reader-excludes-naked-fact-and-rejects-claimed-lineage-sqlite',
                                                                                                                         'diagnostic_role': 'owner',
                                                                                                                         'introduced_by_task': 'Foundation-Task-5',
                                                                                                                         'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '066989da526f7abda7ed7d9ff58a0fec48cf8c827641d396a6ea19b227fd2ca1'},
 'tests/test_foundation_admitted_designations.py::test_designation_index_detaches_structured_fact_inputs_and_outputs[memory]': {'activation_phase': 'R3',
                                                                                                                                'assertion_ref': 'assertion:designation-index-detaches-structured-fact-inputs-and-outputs-memory',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                'owner_ref': 'effect-learning-response',
                                                                                                                                'source_ast_sha256': '657972d9901ff17110c833ab52d3370f57fbcaed50e18b5186c5d5d33055c92b'},
 'tests/test_foundation_admitted_designations.py::test_designation_index_detaches_structured_fact_inputs_and_outputs[sqlite]': {'activation_phase': 'R3',
                                                                                                                                'assertion_ref': 'assertion:designation-index-detaches-structured-fact-inputs-and-outputs-sqlite',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                'owner_ref': 'effect-learning-response',
                                                                                                                                'source_ast_sha256': '657972d9901ff17110c833ab52d3370f57fbcaed50e18b5186c5d5d33055c92b'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_reopens_without_key_after_expiry_and_refuses_copy': {'activation_phase': 'R3',
                                                                                                                            'assertion_ref': 'assertion:admitted-reader-reopens-without-key-after-expiry-and-refuses-copy',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-5',
                                                                                                                            'owner_ref': 'effect-learning-response',
                                                                                                                            'source_ast_sha256': '3dfdb70830558ce5a720d8bc42d4e13d9f1fd7239cf85eb27a421caac7dddcf5'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_cache_cannot_mask_peer_staleness_and_batch_is_coherent': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:admitted-reader-cache-cannot-mask-peer-staleness-and-batch-is-coherent',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                 'owner_ref': 'effect-learning-response',
                                                                                                                                 'source_ast_sha256': '0b0839482b6f47e00d31df2d1a605097e2ef925712ad7edcdf7884814629d7d7'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-journal]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-journal',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-proposal]': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-proposal',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-5',
                                                                                                                               'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-source]': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-source',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-5',
                                                                                                                             'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-completed]': {'activation_phase': 'R3',
                                                                                                                                'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-completed',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-target]': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-target',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-5',
                                                                                                                             'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-generation]': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-generation',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                 'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-future]': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-future',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-5',
                                                                                                                             'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-partial]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-partial',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[memory-receipt]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-memory-receipt',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-journal]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-journal',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-proposal]': {'activation_phase': 'R3',
                                                                                                                               'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-proposal',
                                                                                                                               'diagnostic_role': 'owner',
                                                                                                                               'introduced_by_task': 'Foundation-Task-5',
                                                                                                                               'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-source]': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-source',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-5',
                                                                                                                             'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-completed]': {'activation_phase': 'R3',
                                                                                                                                'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-completed',
                                                                                                                                'diagnostic_role': 'owner',
                                                                                                                                'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-target]': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-target',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-5',
                                                                                                                             'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-generation]': {'activation_phase': 'R3',
                                                                                                                                 'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-generation',
                                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                                 'introduced_by_task': 'Foundation-Task-5',
                                                                                                                                 'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-future]': {'activation_phase': 'R3',
                                                                                                                             'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-future',
                                                                                                                             'diagnostic_role': 'owner',
                                                                                                                             'introduced_by_task': 'Foundation-Task-5',
                                                                                                                             'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-partial]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-partial',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_broken_publication_evidence[sqlite-receipt]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-broken-publication-evidence-sqlite-receipt',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                         'source_ast_sha256': '33106080fbc52d56e7b5120d064b7acc1f64dd28645157e972ab4e21d71c32b6'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_unseen_signed_surface_and_language[memory]': {'activation_phase': 'R3',
                                                                                                                     'assertion_ref': 'assertion:admitted-reader-unseen-signed-surface-and-language-memory',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-5',
                                                                                                                     'owner_ref': 'effect-learning-response',
                                                                                                                     'source_ast_sha256': '6f2445ddedfd52626fbaec8ac5e90eaefc0d0ae56aa529429568cce749989ffb'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_unseen_signed_surface_and_language[sqlite]': {'activation_phase': 'R3',
                                                                                                                     'assertion_ref': 'assertion:admitted-reader-unseen-signed-surface-and-language-sqlite',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-5',
                                                                                                                     'owner_ref': 'effect-learning-response',
                                                                                                                     'source_ast_sha256': '6f2445ddedfd52626fbaec8ac5e90eaefc0d0ae56aa529429568cce749989ffb'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_bounded_index_work_and_cache[memory]': {'activation_phase': 'R3',
                                                                                                               'assertion_ref': 'assertion:admitted-reader-bounded-index-work-and-cache-memory',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-5',
                                                                                                               'owner_ref': 'effect-learning-response',
                                                                                                               'source_ast_sha256': 'c480e8d2f2c84738d5f8fd6b9f325ef6a68da44b194f5dfd8482a4d79459dbc5'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_bounded_index_work_and_cache[sqlite]': {'activation_phase': 'R3',
                                                                                                               'assertion_ref': 'assertion:admitted-reader-bounded-index-work-and-cache-sqlite',
                                                                                                               'diagnostic_role': 'owner',
                                                                                                               'introduced_by_task': 'Foundation-Task-5',
                                                                                                               'owner_ref': 'effect-learning-response',
                                                                                                               'source_ast_sha256': 'c480e8d2f2c84738d5f8fd6b9f325ef6a68da44b194f5dfd8482a4d79459dbc5'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_preserves_same_exact_static_alternative[memory]': {'activation_phase': 'R3',
                                                                                                                          'assertion_ref': 'assertion:admitted-reader-preserves-same-exact-static-alternative-memory',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-5',
                                                                                                                          'owner_ref': 'effect-learning-response',
                                                                                                                          'source_ast_sha256': '56824c123369c2a1b1f395583b8bf343e744e675732987c4f819b7a69d011a2b'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_preserves_same_exact_static_alternative[sqlite]': {'activation_phase': 'R3',
                                                                                                                          'assertion_ref': 'assertion:admitted-reader-preserves-same-exact-static-alternative-sqlite',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-5',
                                                                                                                          'owner_ref': 'effect-learning-response',
                                                                                                                          'source_ast_sha256': '56824c123369c2a1b1f395583b8bf343e744e675732987c4f819b7a69d011a2b'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_peer_metadata_before_cached_miss[world]': {'activation_phase': 'R3',
                                                                                                                          'assertion_ref': 'assertion:admitted-reader-rejects-peer-metadata-before-cached-miss-world',
                                                                                                                          'diagnostic_role': 'owner',
                                                                                                                          'introduced_by_task': 'Foundation-Task-5',
                                                                                                                          'owner_ref': 'effect-learning-response',
                                                                                                                          'source_ast_sha256': 'd29c042ef6c1c59ea40e22e78a12598960d23b92cd29081112aec758439b6a39'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_peer_metadata_before_cached_miss[session]': {'activation_phase': 'R3',
                                                                                                                            'assertion_ref': 'assertion:admitted-reader-rejects-peer-metadata-before-cached-miss-session',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-5',
                                                                                                                            'owner_ref': 'effect-learning-response',
                                                                                                                            'source_ast_sha256': 'd29c042ef6c1c59ea40e22e78a12598960d23b92cd29081112aec758439b6a39'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_peer_metadata_before_cached_miss[episode]': {'activation_phase': 'R3',
                                                                                                                            'assertion_ref': 'assertion:admitted-reader-rejects-peer-metadata-before-cached-miss-episode',
                                                                                                                            'diagnostic_role': 'owner',
                                                                                                                            'introduced_by_task': 'Foundation-Task-5',
                                                                                                                            'owner_ref': 'effect-learning-response',
                                                                                                                            'source_ast_sha256': 'd29c042ef6c1c59ea40e22e78a12598960d23b92cd29081112aec758439b6a39'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_peer_metadata_before_cached_miss[effect]': {'activation_phase': 'R3',
                                                                                                                           'assertion_ref': 'assertion:admitted-reader-rejects-peer-metadata-before-cached-miss-effect',
                                                                                                                           'diagnostic_role': 'owner',
                                                                                                                           'introduced_by_task': 'Foundation-Task-5',
                                                                                                                           'owner_ref': 'effect-learning-response',
                                                                                                                           'source_ast_sha256': 'd29c042ef6c1c59ea40e22e78a12598960d23b92cd29081112aec758439b6a39'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_rejects_peer_metadata_before_cached_miss[authority]': {'activation_phase': 'R3',
                                                                                                                              'assertion_ref': 'assertion:admitted-reader-rejects-peer-metadata-before-cached-miss-authority',
                                                                                                                              'diagnostic_role': 'owner',
                                                                                                                              'introduced_by_task': 'Foundation-Task-5',
                                                                                                                              'owner_ref': 'effect-learning-response',
                                                                                                                              'source_ast_sha256': 'd29c042ef6c1c59ea40e22e78a12598960d23b92cd29081112aec758439b6a39'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_requires_language_and_exact_bounded_inputs': {'activation_phase': 'R3',
                                                                                                                     'assertion_ref': 'assertion:admitted-reader-requires-language-and-exact-bounded-inputs',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-5',
                                                                                                                     'owner_ref': 'effect-learning-response',
                                                                                                                     'source_ast_sha256': '5ca977c50e9cb272fbf17e22ad36a81b7d5d1654e0db63e08cf6c20535f3bcaf'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_requires_existing_eligible_target[missing]': {'activation_phase': 'R3',
                                                                                                                     'assertion_ref': 'assertion:admitted-reader-requires-existing-eligible-target-missing',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'Foundation-Task-5',
                                                                                                                     'owner_ref': 'effect-learning-response',
                                                                                                                     'source_ast_sha256': '3ada5494dc12feb5e59a6aeed7b681704574b5ecd1dc622fde0499bea1de874d'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_requires_existing_eligible_target[ineligible]': {'activation_phase': 'R3',
                                                                                                                        'assertion_ref': 'assertion:admitted-reader-requires-existing-eligible-target-ineligible',
                                                                                                                        'diagnostic_role': 'owner',
                                                                                                                        'introduced_by_task': 'Foundation-Task-5',
                                                                                                                        'owner_ref': 'effect-learning-response',
                                                                                                                        'source_ast_sha256': '3ada5494dc12feb5e59a6aeed7b681704574b5ecd1dc622fde0499bea1de874d'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_overflow_does_not_become_unknown[memory]': {'activation_phase': 'R3',
                                                                                                                   'assertion_ref': 'assertion:admitted-reader-overflow-does-not-become-unknown-memory',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-5',
                                                                                                                   'owner_ref': 'effect-learning-response',
                                                                                                                   'source_ast_sha256': 'f6fe7fd44a06467209c873e544b09dd9bee6e75a96e982f60a68958ae744f463'},
 'tests/test_foundation_admitted_designations.py::test_admitted_reader_overflow_does_not_become_unknown[sqlite]': {'activation_phase': 'R3',
                                                                                                                   'assertion_ref': 'assertion:admitted-reader-overflow-does-not-become-unknown-sqlite',
                                                                                                                   'diagnostic_role': 'owner',
                                                                                                                   'introduced_by_task': 'Foundation-Task-5',
                                                                                                                   'owner_ref': 'effect-learning-response',
                                                                                                                   'source_ast_sha256': 'f6fe7fd44a06467209c873e544b09dd9bee6e75a96e982f60a68958ae744f463'}}

from cemm_authoritative_hybrid import bootstrap, persistence, r3_learning
from cemm_authoritative_hybrid.authority import DesignationFact, DesignationIndex
from cemm_authoritative_hybrid.gaps import BudgetExhausted
from tests.test_foundation_alias_publication import _publication, _signed
from tests.test_foundation_learning_proposal import ROOT


def _reader(runtime, backend):
    assert hasattr(r3_learning, "AdmittedDesignationReader"), "missing shared admitted designation reader"
    return r3_learning.AdmittedDesignationReader(runtime.authority, runtime.stores,
        memory_review_binding="trusted-process:test-publication" if backend == "memory" else None)


def _physically_corrupt_fact_for_integrity_test(stores, backend, fact):
    """Bypass the public immutability boundary to exercise read-side detection."""
    if backend == "memory":
        stores._backend.world._store_fact(fact)
        return
    row = persistence._fact_to_row(fact)
    with stores._backend._conn:
        stores._backend._conn.execute(
            "UPDATE world_facts SET operator=:operator,args_json=:args_json,stance=:stance,"
            "confidence=:confidence,derived=:derived,proof_json=:proof_json,payload_hash=:payload_hash "
            "WHERE fact_ref=:fact_ref",
            {**row, "payload_hash": persistence._payload_hash(persistence._fact_payload(fact))},
        )


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_admitted_reader_retains_actual_publication_proof(tmp_path, monkeypatch, backend):
    runtime, source, proposal, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        reader = _reader(runtime, backend)
        with reader.batch(runtime.stores.revision_pin()) as batch:
            assert batch.for_surface("velnora", "en", maximum=8) == ()
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        with reader.batch(runtime.stores.revision_pin()) as batch:
            rows = batch.for_surface("velnora", "en", maximum=8)
            assert len(rows) == 1
            row = rows[0]
            assert row.designation == DesignationFact.create(surface="velnora", target_ref="rel:likes", language="en")
            assert row.world_fact_ref == receipt.committed_fact_refs[0]
            assert row.world_fact_ref != row.designation.designation_fact_ref
            assert row.authority_designation_ref is None
            assert {receipt.receipt_ref, pending.obligation_ref, proposal.effect_receipt.receipt_ref,
                source.effect_receipt.journal_preterminal_ref}.issubset(set(row.provenance_refs))
            assert batch.exact_surface("velnora", maximum=16) == rows
            assert row in batch.for_target("rel:likes", "en", maximum=16)
            assert batch.resolve_world_fact(row.world_fact_ref) == row
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_reader_merges_static_exact_before_unicode_fold(tmp_path, monkeypatch, backend):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        static = (
            DesignationFact.create(surface="VELNORA", target_ref="rel:knows", language="en"),
            DesignationFact.create(surface="velnora", target_ref="rel:knows", language="fr"),
            DesignationFact.create(surface="Straße", target_ref="rel:likes", language="de"),
            DesignationFact.create(surface="STRASSE", target_ref="rel:knows", language="de"),
        )
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex(static))
        reader = _reader(runtime, backend)
        with reader.batch(runtime.stores.revision_pin()) as batch:
            assert [r.designation.target_ref for r in batch.for_surface("velnora", "en", maximum=8)] == ["rel:likes"]
            assert [r.designation.target_ref for r in batch.for_surface("VELNORA", "en", maximum=8)] == ["rel:knows"]
            assert len(batch.for_surface("Velnora", "en", maximum=8)) == 2
            assert len(batch.exact_surface("velnora", maximum=16)) == 2
            assert len(batch.for_surface("strasse", "de", maximum=8)) == 2
            with pytest.raises(BudgetExhausted):
                batch.for_surface("Velnora", "en", maximum=1)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_reader_excludes_naked_fact_and_rejects_claimed_lineage(tmp_path, monkeypatch, backend):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        stores = runtime.stores
        fact = stores.world.get(receipt.committed_fact_refs[0])
        naked = replace(fact, fact_ref="fact:naked", args={**fact.args, "role:surface": "fakeword"},
            proof={"source": "reviewer:trusted", "alias_language": "en"})
        stores.world.commit((naked,), expected_revision=stores.world.revision)
        reader = _reader(runtime, backend)
        with reader.batch(stores.revision_pin()) as batch:
            assert batch.for_surface("fakeword", "en", maximum=8) == ()
        _physically_corrupt_fact_for_integrity_test(
            stores, backend, replace(fact, proof={**fact.proof, "publication_key": "key:missing"})
        )
        with reader.batch(stores.revision_pin()) as batch, pytest.raises(ValueError):
            batch.for_surface("velnora", "en", maximum=8)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_designation_index_detaches_structured_fact_inputs_and_outputs(tmp_path, backend):
    stores = (persistence.memory_stores() if backend == "memory" else
        persistence.open_stores(tmp_path, authority_generation="authority:test"))
    try:
        args = {"role:surface": "Straße", "role:target": "rel:likes", "nested": {"items": [1, 2]}}
        proof = {"alias_language": "de"}
        fact = persistence.Fact("fact:input", "op:designation", args, proof=proof)
        stores.world.commit((fact,), expected_revision=0)
        args["role:surface"] = "mutated"
        args["nested"]["items"].append(3)
        proof["alias_language"] = "en"
        found = stores.r3_designation_facts("folded", "STRASSE", "de", maximum=8)
        assert len(found) == 1 and found[0].args["role:surface"] == "Straße"
        assert found[0].args["nested"]["items"] == [1, 2]
        found[0].args["role:surface"] = "changed-return"
        stores.world.get("fact:input").proof["alias_language"] = "es"
        assert stores.r3_designation_facts("exact", "Straße", "de", maximum=8)[0].proof["alias_language"] == "de"
        replacement = replace(stores.world.get("fact:input"), args={"role:surface": {"typed": [1]}, "role:target": [2]})
        stores.world.commit((replacement,), expected_revision=stores.world.revision)
        assert stores.r3_designation_facts("folded", "STRASSE", "de", maximum=8) == ()
        assert stores.world.get("fact:input").args == replacement.args
    finally:
        stores.close()


def test_admitted_reader_reopens_without_key_after_expiry_and_refuses_copy(tmp_path, monkeypatch):
    import shutil
    runtime, _, _, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    # Advance through the existing effect owner, not a fabricated publication.
    for _ in range(5):
        runtime.process(pending.session_ref, "Alice likes Bob")
    # A later phase is independent of the historical publication phase.
    conn = runtime.stores._backend._conn
    session = runtime.stores.sessions.get(pending.session_ref)
    assert session.turn_index >= grant["expires_at_turn"]
    session.phase = "closed"
    payload = persistence._session_to_payload(session)
    with conn:
        conn.execute("UPDATE sessions SET payload_json=?,payload_hash=? WHERE session_ref=?",
            (persistence._r3_canonical_json(payload), persistence._payload_hash(payload), pending.session_ref))
    runtime.stores.close()
    del gateway, secret
    reopened = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "proposal.db")
    try:
        reader = _reader(reopened, "sqlite")
        with reader.batch(reopened.stores.revision_pin()) as batch:
            assert batch.for_surface("VELNORA", "en")[0].world_fact_ref == receipt.committed_fact_refs[0]
        with pytest.raises(ValueError, match="closed"):
            batch.for_surface("velnora", "en")
    finally:
        reopened.stores.close()
    shutil.copytree(tmp_path / "proposal.db", tmp_path / "copy.db")
    copied = bootstrap.load_runtime(ROOT, profile="development", store_path=tmp_path / "copy.db")
    try:
        with _reader(copied, "sqlite").batch(copied.stores.revision_pin()) as batch, pytest.raises(ValueError, match="trusted store"):
            batch.for_surface("velnora", "en")
    finally:
        copied.stores.close()


def test_admitted_reader_cache_cannot_mask_peer_staleness_and_batch_is_coherent(tmp_path, monkeypatch):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation)
    try:
        reader = _reader(runtime, "sqlite")
        pin = stores.revision_pin()
        with reader.batch(pin) as batch:
            rows = batch.for_surface("velnora", "en")
            assert batch.for_surface("absent", "en") == ()
            peer.world.commit((persistence.Fact("fact:peer", "op:type", {}),), expected_revision=peer.world.revision)
            assert batch.for_surface("velnora", "en") == rows
            assert batch.for_surface("absent", "en") == ()
        assert stores.revision_pin() == pin  # legacy cache has not observed the peer
        with pytest.raises(persistence.StaleRevisionError), reader.batch(pin):
            pytest.fail("cache must not be consulted under stale metadata")
    finally:
        peer.close()
        stores.close()


@pytest.mark.parametrize("backend,case", (
    ("memory", "journal"), ("memory", "proposal"), ("memory", "source"), ("memory", "completed"),
    ("memory", "target"), ("memory", "generation"), ("memory", "future"), ("memory", "partial"), ("memory", "receipt"),
    ("sqlite", "journal"), ("sqlite", "proposal"), ("sqlite", "source"), ("sqlite", "completed"),
    ("sqlite", "target"), ("sqlite", "generation"), ("sqlite", "future"), ("sqlite", "partial"), ("sqlite", "receipt")),
    ids=("memory-journal", "memory-proposal", "memory-source", "memory-completed", "memory-target", "memory-generation",
        "memory-future", "memory-partial", "memory-receipt", "sqlite-journal", "sqlite-proposal", "sqlite-source",
        "sqlite-completed", "sqlite-target", "sqlite-generation", "sqlite-future", "sqlite-partial", "sqlite-receipt"))
def test_admitted_reader_rejects_broken_publication_evidence(tmp_path, monkeypatch, backend, case):
    import json
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, EffectJournalState
    runtime, _, _, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        terminal = stores.r3_effect_journal_get(receipt.idempotency_key)
        if case in {"journal", "proposal", "source"}:
            key = {"journal": receipt.idempotency_key, "proposal": grant["proposal_key"],
                "source": terminal["entry"]["request_payload"]["proposal"]["entry"]["request_payload"]["learning_source_key"]}[case]
            if backend == "memory":
                stores._backend._r3_effect_journals.pop(key)
            else:
                with stores._backend._conn:
                    stores._backend._conn.execute("DELETE FROM r3_effect_journal WHERE idempotency_key=?", (key,))
        elif case == "completed":
            original = terminal["entry"]["request_payload"]["proposal"]["entry"]["request_payload"]["learning_source_obligation"]
            from cemm_authoritative_hybrid.dialogue import DialogueObligation
            original.pop("obligation_ref")
            original.pop("abi_version")
            completed = DialogueObligation.create(**{**original, "revision_pin": pending.revision_pin,
                "kind": pending.kind, "completion_receipt_ref": receipt.receipt_ref})
            if backend == "memory":
                stores._backend.obligations._obligations.pop(completed.obligation_ref)
            else:
                with stores._backend._conn:
                    stores._backend._conn.execute("DELETE FROM obligations WHERE obligation_ref=?", (completed.obligation_ref,))
        elif case == "target":
            fact = stores.world.get(receipt.committed_fact_refs[0])
            _physically_corrupt_fact_for_integrity_test(
                stores, backend, replace(fact, args={**fact.args, "role:target": "rel:knows"})
            )
        elif case == "generation":
            # LinkedAuthority is an immutable generation snapshot.  Exercise
            # the reader's mismatch boundary by corrupting only the store-side
            # test backend pin; never mutate semantic authority in place.
            monkeypatch.setattr(
                stores._backend, "_authority_generation", "authority:other"
            )
        else:
            data = terminal["entry"]
            if case == "future":
                data["request_payload"]["publication_pin"]["world_revision"] += 100
            elif case == "partial":
                data["parent_journal_ref"] = "journal:missing-parent"
            else:
                from cemm_authoritative_hybrid.r3_effects import EffectReceipt, EffectStatus
                changed = dict(terminal["receipt"])
                changed.pop("receipt_ref")
                changed.pop("abi_version")
                changed["decision_ref"] = "decision:wrong"
                changed["status"] = EffectStatus(changed["status"])
                for field in ("observed_delta_refs", "committed_fact_refs", "proof_refs", "blocker_refs"):
                    changed[field] = tuple(changed[field])
                for field in ("input_revision_pin", "output_revision_pin"):
                    changed[field] = persistence.RevisionPin.from_dict(changed[field])
                terminal["receipt"] = EffectReceipt.create(**changed).as_dict()
                data["outcome_ref"] = terminal["receipt"]["receipt_ref"]
            data.pop("journal_ref")
            data.pop("abi_version")
            data["state"] = EffectJournalState(data["state"])
            data["blocker_refs"] = tuple(data["blocker_refs"])
            terminal["entry"] = EffectJournalEntry.create(**data).as_dict()
            if backend == "memory":
                stores._backend._r3_effect_journals[receipt.idempotency_key] = terminal
            else:
                with stores._backend._conn:
                    stores._backend._conn.execute("UPDATE r3_effect_journal SET entry_json=?,entry_hash=?,receipt_json=?,receipt_hash=? WHERE idempotency_key=?",
                        (json.dumps(terminal["entry"]), persistence._payload_hash(terminal["entry"]),
                         json.dumps(terminal["receipt"]), persistence._payload_hash(terminal["receipt"]), receipt.idempotency_key))
        with pytest.raises(
            (ValueError, PermissionError, persistence.StaleRevisionError)
        ), _reader(runtime, backend).batch(stores.revision_pin()) as batch:
            batch.for_surface("velnora", "en")
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_admitted_reader_unseen_signed_surface_and_language(tmp_path, monkeypatch, backend):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        # Independent review authorizes another literal; no production string branch.
        surface = "Straße"
        source = runtime.process("session:second", f"What does {surface} mean?")
        proposal = runtime.process("session:second", f"learn {surface} means likes")
        plan = proposal.response_meaning.learning_plan
        journal = runtime.stores.r3_effect_journal_get(proposal.effect_receipt.idempotency_key)
        changed = {**grant, "surface": surface, "language": "de", "proposal_key": proposal.effect_receipt.idempotency_key,
            "proposal_journal_ref": journal["entry"]["journal_ref"], "proposal_receipt_ref": proposal.effect_receipt.receipt_ref,
            "plan_ref": plan.plan_ref, "source_obligation_ref": plan.source_obligation_ref,
            "source_query_ref": plan.source_query_ref,
            "source_journal_ref": journal["entry"]["request_payload"]["learning_source_journal"]["entry"]["journal_ref"],
            "expires_at_turn": plan.expires_at_turn, "nonce": "independently-authorized-unseen-surface"}
        receipt = gateway.publish_learning(changed["proposal_key"], _signed(changed, secret))
        reader = _reader(runtime, backend)
        with reader.batch(runtime.stores.revision_pin()) as batch:
            rows = batch.for_surface("STRASSE", "de")
            assert rows[0].designation.surface == surface and rows[0].world_fact_ref == receipt.committed_fact_refs[0]
            assert batch.exact_surface("STRASSE") == ()
            assert batch.for_surface(surface, "en") == ()
            assert batch.canonical_surface_for_target("rel:likes", "de", "strasse") == rows
            assert batch.exact_surface(surface) == rows
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_admitted_reader_bounded_index_work_and_cache(tmp_path, monkeypatch, backend):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        reader = _reader(runtime, backend)
        def forbidden(*args, **kwargs):
            pytest.fail("admitted designation reads must never scan whole stores")
        monkeypatch.setattr(stores, "r3_world_facts", forbidden)
        monkeypatch.setattr(stores, "r3_world_snapshot", forbidden)
        calls = []
        original = stores.r3_effect_journal_get
        def journal_get(key):
            calls.append(key)
            return original(key)
        monkeypatch.setattr(stores, "r3_effect_journal_get", journal_get)
        counts = []
        for count in (0, 128, 2048):
            if count:
                stores.world.commit(tuple(persistence.Fact(f"fact:irrelevant:{count}:{i}", "op:designation",
                    {"role:surface": f"irrelevant-{count}-{i}", "role:target": "concept:other"},
                    proof={"alias_language": "fr"}) for i in range(count)), expected_revision=stores.world.revision)
                if backend == "sqlite":
                    # Irrelevant rows exercise primary-key lookup growth, not activation validity.
                    conn = stores._backend._conn
                    with conn:
                        conn.executemany("INSERT INTO r3_effect_journal SELECT 'irrelevant:'||?,entry_json,entry_hash,receipt_json,receipt_hash,effect_revision "
                            "FROM r3_effect_journal WHERE idempotency_key=?",
                            ((f"{count}:{i}", grant["proposal_key"]) for i in range(count)))
                else:
                    for i in range(count):
                        stores._backend._r3_effect_journals[f"irrelevant:{count}:{i}"] = original(grant["proposal_key"])
            calls.clear()
            steps = []
            if backend == "sqlite":
                stores._backend._conn.set_progress_handler(lambda: steps.append(1) or 0, 1)
            with reader.batch(stores.revision_pin()) as batch:
                rows = batch.for_surface("velnora", "en")
                assert len(rows) == 1
                assert batch.exact_surface("velnora") == rows
                before = len(calls)
                assert batch.for_surface("velnora", "en") == rows
                assert batch.for_surface("missing", "en") == ()
                assert batch.for_surface("missing", "en") == ()
                assert len(calls) == before == 3
            if backend == "sqlite":
                stores._backend._conn.set_progress_handler(None, 0)
            counts.append(len(steps))
        if backend == "sqlite":
            assert max(counts) - min(counts) < 80, counts
            queries = []
            stores._backend._conn.set_trace_callback(queries.append)
            for mode, key, language in (("exact", "velnora", "en"), ("exact", "velnora", None),
                    ("folded", "VELNORA", "en"), ("target", "rel:likes", "en")):
                stores.r3_designation_facts(mode, key, language, maximum=16)
            stores._backend._conn.set_trace_callback(None)
            for sql in queries:
                detail = " ".join(row[3] for row in stores._backend._conn.execute("EXPLAIN QUERY PLAN " + sql))
                assert "SEARCH" in detail and "world_designation" in detail and "TEMP" not in detail, detail
        with reader.batch(stores.revision_pin()) as batch:
            for i in range(300):
                assert batch.for_surface(f"missing-{i}", "en") == ()
        assert len(reader._cache) <= 256
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_admitted_reader_preserves_same_exact_static_alternative(tmp_path, monkeypatch, backend):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, backend)
    try:
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        monkeypatch.setattr(runtime.authority, "designations", DesignationIndex((
            DesignationFact.create(surface="velnora", target_ref="participant:user", language="en"),)))
        with _reader(runtime, backend).batch(runtime.stores.revision_pin()) as batch:
            rows = batch.for_surface("velnora", "en")
            assert {row.designation.target_ref for row in rows} == {"rel:likes", "participant:user"}
            assert sum(row.world_fact_ref is not None for row in rows) == 1
            assert sum(row.authority_designation_ref is not None for row in rows) == 1
            with pytest.raises(BudgetExhausted):
                batch.for_surface("velnora", "en", maximum=1)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("field", ("world_revision", "session_revision", "episode_revision", "effect_revision", "authority_generation"),
    ids=("world", "session", "episode", "effect", "authority"))
def test_admitted_reader_rejects_peer_metadata_before_cached_miss(tmp_path, monkeypatch, field):
    runtime, _, _, _, _, _, _ = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    peer = persistence.open_stores(tmp_path / "proposal.db", authority_generation=runtime.authority.generation)
    try:
        reader = _reader(runtime, "sqlite")
        pin = stores.revision_pin()
        with reader.batch(pin) as batch:
            assert batch.for_surface("missing", "en") == ()
        with peer._backend._conn:
            peer._backend._conn.execute("INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (field, "authority:other" if field == "authority_generation" else str(getattr(pin, field) + 1)))
        with pytest.raises(persistence.StaleRevisionError), reader.batch(pin):
            pytest.fail("metadata check must precede the cached miss")
    finally:
        peer.close()
        stores.close()


def test_admitted_reader_requires_language_and_exact_bounded_inputs(tmp_path, monkeypatch):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        with _reader(runtime, "memory").batch(runtime.stores.revision_pin()) as batch:
            with pytest.raises((TypeError, ValueError)):
                batch.for_surface("velnora", None)
            with pytest.raises((TypeError, ValueError)):
                batch.canonical_surface_for_target("rel:likes", "en", 123)
            with pytest.raises((TypeError, ValueError)):
                batch.for_surface("velnora", "en", maximum=9)
            with pytest.raises((TypeError, ValueError)):
                batch.exact_surface("velnora", maximum=True)
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("case", ("missing", "ineligible"), ids=("missing", "ineligible"))
def test_admitted_reader_requires_existing_eligible_target(tmp_path, monkeypatch, case):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        if case == "missing":
            monkeypatch.delitem(runtime.authority.atoms, "rel:likes")
        else:
            atom = runtime.authority.atoms["rel:likes"]
            monkeypatch.setitem(runtime.authority.atoms, "rel:likes", replace(atom, kind="permission"))
        with pytest.raises(ValueError), _reader(runtime, "memory").batch(runtime.stores.revision_pin()) as batch:
            batch.for_surface("velnora", "en")
    finally:
        runtime.stores.close()


def test_admitted_reader_survives_current_proposer_change_without_writes(tmp_path, monkeypatch):
    runtime, _, _, pending, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    authority = runtime.authority
    with _reader(runtime, "sqlite").batch(runtime.stores.revision_pin()) as batch:
        original_evidence = batch.for_surface("velnora", "en")
    original_fact = runtime.stores.world.get(receipt.committed_fact_refs[0])
    original_journal = runtime.stores.r3_effect_journal_get(receipt.idempotency_key)
    original_pending = runtime.stores.obligations.keyed_row(pending.obligation_ref)
    runtime.stores.close()
    stores = persistence.open_stores(tmp_path / "proposal.db", authority_generation=authority.generation,
        model_identity="model:new-proposer")
    try:
        before = stores.revision_pin(), stores.obligations.revision
        assert before[0].model_identity != receipt.input_revision_pin.model_identity
        with r3_learning.AdmittedDesignationReader(authority, stores).batch(before[0]) as batch:
            assert batch.for_surface("velnora", "en") == original_evidence
            assert batch.exact_surface("velnora") == original_evidence
        assert (stores.revision_pin(), stores.obligations.revision) == before
        assert stores.world.get(original_fact.fact_ref) == original_fact
        assert stores.r3_effect_journal_get(receipt.idempotency_key) == original_journal
        assert stores.obligations.keyed_row(pending.obligation_ref) == original_pending
    finally:
        stores.close()


def test_publication_preserves_cross_turn_models_and_reads_under_new_proposer(tmp_path, monkeypatch):
    from tests import test_foundation_alias_publication as fixture_owner
    original_setup = fixture_owner._setup
    def changed_model_after_source(*args):
        result = original_setup(*args)
        result[0].stores._backend._model_identity = "model:answer-only"
        monkeypatch.setattr(result[0]._owners["proposal"], "model_identity", "model:answer-only")
        return result
    monkeypatch.setattr(fixture_owner, "_setup", changed_model_after_source)
    runtime, source, proposal, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        assert source.evaluation.revision_pin.model_identity != proposal.evaluation.revision_pin.model_identity
        assert proposal.evaluation.revision_pin.model_identity == runtime.stores.revision_pin().model_identity
        source_record = runtime.stores.r3_effect_journal_get(source.effect_receipt.idempotency_key)
        answer_record = runtime.stores.r3_effect_journal_get(grant["proposal_key"])
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        original_fact = runtime.stores.world.get(receipt.committed_fact_refs[0])
        assert receipt.input_revision_pin.model_identity == proposal.evaluation.revision_pin.model_identity
        runtime.stores._backend._model_identity = "model:reader-only"
        before = runtime.stores.revision_pin(), runtime.stores.obligations.revision
        with _reader(runtime, "memory").batch(before[0]) as batch:
            evidence, = batch.for_surface("velnora", "en")
            assert evidence.world_fact_ref == original_fact.fact_ref
            assert grant["source_journal_ref"] in evidence.provenance_refs
            assert grant["proposal_journal_ref"] in evidence.provenance_refs
        assert (runtime.stores.revision_pin(), runtime.stores.obligations.revision) == before
        assert runtime.stores.world.get(original_fact.fact_ref) == original_fact
        assert runtime.stores.r3_effect_journal_get(source.effect_receipt.idempotency_key) == source_record
        assert runtime.stores.r3_effect_journal_get(grant["proposal_key"]) == answer_record
    finally:
        runtime.stores.close()


def test_readonly_integrity_inspection_registers_populated_unicode_index(tmp_path, monkeypatch):
    import sqlite3
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        original_fact = runtime.stores.world.get(receipt.committed_fact_refs[0])
    finally:
        runtime.stores.close()
    connection = sqlite3.connect((tmp_path / "proposal.db" / "semantic.db").as_uri() + "?mode=ro", uri=True)
    try:
        persistence.register_sqlite_functions(connection)
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT unicode_casefold(?)", ("Straße",)).fetchone() == ("strasse",)
        for value in (None, 1, 1.5, b"bytes"):
            assert connection.execute("SELECT unicode_casefold(?)", (value,)).fetchone() == (None,)
        assert connection.execute("SELECT fact_ref FROM world_facts").fetchall() == [(original_fact.fact_ref,)]
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM world_facts")
        assert connection.total_changes == 0
    finally:
        connection.close()


def test_admitted_reader_rejects_foreign_historical_publication_model(tmp_path, monkeypatch):
    from cemm_authoritative_hybrid.r3_persistence import EffectJournalEntry, EffectJournalState
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch, "memory")
    try:
        receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
        terminal = runtime.stores.r3_effect_journal_get(receipt.idempotency_key)
        entry = terminal["entry"]
        entry["request_payload"]["publication_pin"]["model_identity"] = "model:foreign-history"
        entry.pop("abi_version")
        entry.pop("journal_ref")
        entry["state"] = EffectJournalState(entry["state"])
        entry["blocker_refs"] = tuple(entry["blocker_refs"])
        terminal["entry"] = EffectJournalEntry.create(**entry).as_dict()
        runtime.stores._backend._r3_effect_journals[receipt.idempotency_key] = terminal
        with _reader(runtime, "memory").batch(runtime.stores.revision_pin()) as batch:
            with pytest.raises(ValueError, match="historical.*model"):
                batch.for_surface("velnora", "en")
    finally:
        runtime.stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_admitted_reader_overflow_does_not_become_unknown(tmp_path, monkeypatch, backend):
    runtime, _, _, _, _, _, _ = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        stores.world.commit(tuple(persistence.Fact(f"fact:unreviewed:{i}", "op:designation",
            {"role:surface": "crowded", "role:target": f"ref:{i}"}, proof={"alias_language": "en"})
            for i in range(17)), expected_revision=stores.world.revision)
        with _reader(runtime, backend).batch(stores.revision_pin()) as batch:
            with pytest.raises(BudgetExhausted):
                batch.for_surface("crowded", "en")
            with pytest.raises(BudgetExhausted):
                batch.exact_surface("crowded")
    finally:
        stores.close()


@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_designation_reads_do_not_coerce_structured_json_into_text(tmp_path, monkeypatch, backend):
    import json
    runtime, _, _, _, _, _, _ = _publication(tmp_path, monkeypatch, backend)
    stores = runtime.stores
    try:
        for structured in ({"typed": [1]}, [2]):
            serialized = json.dumps(structured, separators=(",", ":"))
            for field, modes in (("surface", ("exact", "folded", "all", "conflict")),
                    ("target", ("target",)), ("language", ("exact", "folded", "target", "conflict"))):
                surface, target, language = f"surface-{field}-{serialized}", f"target:{field}:{serialized}", "en"
                args = {"role:surface": surface, "role:target": target}
                proof = {"alias_language": language}
                if field == "language":
                    proof["alias_language"] = structured
                    language = serialized
                else:
                    args[f"role:{field}"] = structured
                    if field == "surface":
                        surface = serialized
                    else:
                        target = serialized
                facts = tuple(persistence.Fact(f"fact:structured:{field}:{serialized}:{i}", "op:designation",
                    args, proof=proof) for i in range(9))
                stores.world.commit(facts, expected_revision=stores.world.revision)
                for mode in modes:
                    if mode == "conflict":
                        assert stores.r3_alias_facts(surface, language, maximum=8) == ()
                    else:
                        assert stores.r3_designation_facts("exact" if mode == "all" else mode,
                            target if mode == "target" else surface, None if mode == "all" else language,
                            maximum=8) == ()
                if field == "surface":
                    with _reader(runtime, backend).batch(stores.revision_pin()) as batch:
                        assert batch.for_surface(surface, language) == ()
                        assert batch.exact_surface(surface) == ()
                    assert stores.r3_designation_facts("target", args["role:target"], language, maximum=16) == facts
                elif field == "language":
                    assert stores.r3_designation_facts("exact", surface, None, maximum=16) == facts
                # Actual JSON-string values remain valid raw textual evidence.
                textual = persistence.Fact(f"fact:text:{field}:{serialized}", "op:designation",
                    {"role:surface": surface, "role:target": target}, proof={"alias_language": language})
                stores.world.commit((textual,), expected_revision=stores.world.revision)
                for mode in modes:
                    if mode == "conflict":
                        assert stores.r3_alias_facts(surface, language, maximum=8) == (textual,)
                    else:
                        assert stores.r3_designation_facts("exact" if mode == "all" else mode,
                            target if mode == "target" else surface, None if mode == "all" else language,
                            maximum=8) == (textual,)
        # Unqualified exact lookup intentionally requires only a textual surface.
        raw = persistence.Fact("fact:all-language", "op:designation", {"role:surface": "all-language-text",
            "role:target": [2]}, proof={"alias_language": {"typed": [1]}})
        stores.world.commit((raw,), expected_revision=stores.world.revision)
        assert stores.r3_designation_facts("exact", "all-language-text", None, maximum=8) == (raw,)
        assert stores.world.get(raw.fact_ref) == raw
    finally:
        stores.close()


def test_structured_designation_growth_is_excluded_by_sql_indexes(tmp_path, monkeypatch):
    runtime, _, _, _, _, _, _ = _publication(tmp_path, monkeypatch)
    stores = runtime.stores
    try:
        reader = _reader(runtime, "sqlite")
        counts = []
        for count in (0, 128, 4096):
            if count:
                rows = tuple(persistence.Fact(f"fact:structured-growth:{count}:{i}", "op:designation",
                    {"role:surface": {"typed": [1]}, "role:target": [2]}, proof={"alias_language": "en"})
                    for i in range(count)) + tuple(persistence.Fact(f"fact:structured-language:{count}:{i}", "op:designation",
                    {"role:surface": "language-collision", "role:target": "target:language-collision"},
                    proof={"alias_language": {"typed": [1]}}) for i in range(count))
                stores.world.commit(rows, expected_revision=stores.world.revision)
            queries, query_steps = [], []
            conn = stores._backend._conn
            def trace_query(sql):
                queries.append(sql)
                query_steps.append(0)
            def record_step():
                query_steps[-1] += 1
                return 0
            conn.set_trace_callback(trace_query)
            conn.set_progress_handler(record_step, 1)
            with reader.batch(stores.revision_pin()) as batch:
                assert batch.for_surface('{"typed":[1]}', "en") == ()
                assert batch.exact_surface('{"typed":[1]}') == ()
                assert batch.for_target("[2]", "en") == ()
                assert stores.r3_alias_facts('{"typed":[1]}', "en", maximum=8) == ()
                assert batch.for_surface("language-collision", '{"typed":[1]}') == ()
                assert batch.for_target("target:language-collision", '{"typed":[1]}') == ()
                assert stores.r3_alias_facts("language-collision", '{"typed":[1]}', maximum=8) == ()
            conn.set_progress_handler(None, 0)
            conn.set_trace_callback(None)
            designation_steps = [steps for sql, steps in zip(queries, query_steps)
                if "FROM world_facts" in sql]
            assert len(designation_steps) == 9
            counts.append(sum(designation_steps))
            for sql in queries:
                if "FROM world_facts" in sql:
                    detail = " ".join(row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql))
                    assert "SEARCH" in detail and "text_v2" in detail and "TEMP" not in detail, detail
        # Measure indexed retrieval itself. First world commit inserts a fixed
        # metadata revision key; that changes pin-read work, not index traversal.
        # All nine actual designation queries retain their semantic/plan guards.
        assert all(after <= before for before, after in zip(counts, counts[1:])), counts
    finally:
        stores.close()


def test_designation_text_index_migration_preserves_existing_store_once(tmp_path, monkeypatch):
    runtime, _, _, _, gateway, grant, secret = _publication(tmp_path, monkeypatch)
    receipt = gateway.publish_learning(grant["proposal_key"], _signed(grant, secret))
    stores, authority = runtime.stores, runtime.authority
    conn = stores._backend._conn
    old = {
        "world_designation_surface_language": "operator, json_extract(args_json, '$.\"role:surface\"'), json_extract(proof_json, '$.alias_language'), fact_ref",
        "world_designation_surface": "operator, json_extract(args_json, '$.\"role:surface\"'), fact_ref",
        "world_designation_folded": "operator, unicode_casefold(json_extract(args_json, '$.\"role:surface\"')), json_extract(proof_json, '$.alias_language'), fact_ref",
        "world_designation_target": "operator, json_extract(args_json, '$.\"role:target\"'), json_extract(proof_json, '$.alias_language'), fact_ref",
    }
    new_names = {name + "_text_v2" for name in old}
    with conn:
        for name in new_names:
            conn.execute(f"DROP INDEX IF EXISTS {name}")
        for name, expression in old.items():
            conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON world_facts({expression})")
    original_pin = stores.revision_pin()
    original_fact = stores.world.get(receipt.committed_fact_refs[0])
    original_journal = stores.r3_effect_journal_get(receipt.idempotency_key)
    original_obligation_revision = stores.obligations.revision
    stores.close()
    statements = []
    real_connect = persistence.sqlite3.connect
    def traced_connect(*args, **kwargs):
        result = real_connect(*args, **kwargs)
        result.set_trace_callback(statements.append)
        return result
    monkeypatch.setattr(persistence.sqlite3, "connect", traced_connect)
    schema_cookie = None
    for reopening in range(2):
        statements.clear()
        reopened = persistence.open_stores(tmp_path / "proposal.db", authority_generation=authority.generation,
            model_identity=original_pin.model_identity)
        try:
            conn = reopened._backend._conn
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
            assert new_names <= names and not set(old) & names
            assert reopened.revision_pin() == original_pin and reopened.obligations.revision == original_obligation_revision
            assert reopened.world.get(original_fact.fact_ref) == original_fact
            assert reopened.r3_effect_journal_get(receipt.idempotency_key) == original_journal
            assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "1"
            with r3_learning.AdmittedDesignationReader(authority, reopened).batch(original_pin) as batch:
                assert batch.for_surface("velnora", "en")[0].world_fact_ref == original_fact.fact_ref
            cookie = conn.execute("PRAGMA schema_version").fetchone()[0]
            index_ddl = [sql for sql in statements if "INDEX" in sql.upper() and "world_designation" in sql
                and sql.lstrip().upper().startswith(("CREATE", "DROP"))]
            if reopening == 0:
                assert index_ddl
            else:
                assert cookie == schema_cookie and index_ddl == []
            schema_cookie = cookie
        finally:
            reopened.close()
