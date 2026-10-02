"""Reviewed semantic frames are manifest-linked authority, never ambient data."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.authority import AuthorityLinker, AuthorityLinkError, AuthorityStore
from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
from cemm_authoritative_hybrid.canonical import sha256_governed_text
from cemm_authoritative_hybrid.config import RuntimeConfig

ROOT = Path(__file__).resolve().parents[1]

__cemm_test_inventory__ = {
    "tests/test_foundation_frame_authority.py::test_active_manifest_preserves_all_six_reviewed_profiles": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-active-manifest-preserves-all-six-reviewed-profiles", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4a22449e83c3b17a97d1cfedb4c127c1d19b42a7066c54097ef3cadb9c65faa8"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[generation]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-generation", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[owner-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-owner-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[frames-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-frames-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[row-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-row-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[unknown-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-unknown-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[missing-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-missing-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[bad-ref]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-bad-ref", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[ref-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-ref-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[unknown-target]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-unknown-target", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[target-kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-target-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[unknown-kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-unknown-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[kinds-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-kinds-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[empty-kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-empty-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[unknown-contribution]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-unknown-contribution", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[duplicate-contribution]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-duplicate-contribution", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[ports-type]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-ports-type", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[unknown-port]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-unknown-port", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[duplicate-port]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-duplicate-port", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[wrong-event-inputs]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-wrong-event-inputs", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[wrong-event-output]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-wrong-event-output", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[wrong-roles]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-wrong-roles", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[duplicate-frame]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-duplicate-frame", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[overlap-frame]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-overlap-frame", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[too-many-ports]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-too-many-ports", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[duplicate-json]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-duplicate-json", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[missing-frames]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-missing-frames", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[missing-generation]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-missing-generation", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_invalid_reviewed_frame_fails_before_activation[renamed-frames]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-invalid-reviewed-frame-fails-before-activation-renamed-frames", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "c3e87ed7781b884098537a032089b8132f5805bd0e3636515222d482cf8b55cc"},
    "tests/test_foundation_frame_authority.py::test_linked_frame_read_failures_never_become_defaults[missing]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-linked-frame-read-failures-never-become-defaults-missing", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "07d468e8963b6c1e7fca09071e3d78d0013147241d91e5aebc80a5d4ed22f320"},
    "tests/test_foundation_frame_authority.py::test_linked_frame_read_failures_never_become_defaults[tampered]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-linked-frame-read-failures-never-become-defaults-tampered", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "07d468e8963b6c1e7fca09071e3d78d0013147241d91e5aebc80a5d4ed22f320"},
    "tests/test_foundation_frame_authority.py::test_linked_frame_read_failures_never_become_defaults[json]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-linked-frame-read-failures-never-become-defaults-json", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "07d468e8963b6c1e7fca09071e3d78d0013147241d91e5aebc80a5d4ed22f320"},
    "tests/test_foundation_frame_authority.py::test_frame_hashes_are_deterministic_and_structurally_sensitive": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-frame-hashes-are-deterministic-and-structurally-sensitive", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "50cf0e4ede44f226276df2782dc4b56227562ff18edc9638c8028728a158bc58"},
    "tests/test_foundation_frame_authority.py::test_frames_are_linked_snapshot_and_explicit_absence_uses_defaults": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-frames-are-linked-snapshot-and-explicit-absence-uses-defaults", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "ef1bd02eeeb794837070fc114fac3e64a12ac3be2873c53b14127ffeaaae6f3b"},
    "tests/test_foundation_frame_authority.py::test_fresh_frame_generation_reopens_and_rejects_prior_store_without_mutation": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-fresh-frame-generation-reopens-and-rejects-prior-store-without-mutation", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "256f213a0e56db97c7190ddb0e0edde6080227d84e3d3e18a82c2f632a62bc56"},
    "tests/test_foundation_frame_authority.py::test_rejected_frame_generation_activation_closes_sqlite_connection": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-rejected-frame-generation-activation-closes-sqlite-connection", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "e48c006ca6184e382924907fda5b75a722abcb009d0c60bbe0b70202e812eae8"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[unknown-filler-kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-unknown-filler-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[string-filler-kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-string-filler-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[empty-filler-kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-empty-filler-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[bool-filler-kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-bool-filler-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[duplicate-filler-kind]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-duplicate-filler-kind", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[missing-filler-kinds]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-missing-filler-kinds", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[string-required]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-string-required", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[int-required]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-int-required", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[string-proposition]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-string-proposition", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[proposition-without-application]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-proposition-without-application", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[application-without-proposition]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-application-without-proposition", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[empty-mirrored-port]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-empty-mirrored-port", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[empty-role-name]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-empty-role-name", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[whitespace-role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-whitespace-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[wrong-role-namespace]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-wrong-role-namespace", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[overlong-role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-overlong-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_frame_source_role_schema_is_strict_before_activation[unknown-role-field]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-frame-source-role-schema-is-strict-before-activation-unknown-role-field", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "4d6df4b655ff557497aa2e14c7793518c50076f4c521f10af69377defe0fdcf6"},
    "tests/test_foundation_frame_authority.py::test_reviewed_relation_frame_requires_complete_fixed_operator_schema[missing-output]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-relation-frame-requires-complete-fixed-operator-schema-missing-output", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "3effbce2c57b77b0a57d11e4dbb1d4d7d2cfbaceaf18ca0020ec991357149473"},
    "tests/test_foundation_frame_authority.py::test_reviewed_relation_frame_requires_complete_fixed_operator_schema[duplicate-output]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-relation-frame-requires-complete-fixed-operator-schema-duplicate-output", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "3effbce2c57b77b0a57d11e4dbb1d4d7d2cfbaceaf18ca0020ec991357149473"},
    "tests/test_foundation_frame_authority.py::test_reviewed_relation_frame_requires_complete_fixed_operator_schema[wrong-mirrored-input]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-relation-frame-requires-complete-fixed-operator-schema-wrong-mirrored-input", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "3effbce2c57b77b0a57d11e4dbb1d4d7d2cfbaceaf18ca0020ec991357149473"},
    "tests/test_foundation_frame_authority.py::test_reviewed_event_frame_requires_fixed_operator_without_alias_contract[missing-output]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-event-frame-requires-fixed-operator-without-alias-contract-missing-output", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "ebcb69735443d2ef089a81bbd202c260f6dad7ac2b359e60a299d79583ed8dd4"},
    "tests/test_foundation_frame_authority.py::test_reviewed_event_frame_requires_fixed_operator_without_alias_contract[duplicate-output]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-event-frame-requires-fixed-operator-without-alias-contract-duplicate-output", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "ebcb69735443d2ef089a81bbd202c260f6dad7ac2b359e60a299d79583ed8dd4"},
    "tests/test_foundation_frame_authority.py::test_reviewed_event_frame_requires_fixed_operator_without_alias_contract[wrong-type-role]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-event-frame-requires-fixed-operator-without-alias-contract-wrong-type-role", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "ebcb69735443d2ef089a81bbd202c260f6dad7ac2b359e60a299d79583ed8dd4"},
    "tests/test_foundation_frame_authority.py::test_reviewed_event_frame_requires_fixed_operator_without_alias_contract[object-not-list]": {"activation_phase": "R1", "assertion_ref": "assertion:foundation-frame-reviewed-event-frame-requires-fixed-operator-without-alias-contract-object-not-list", "diagnostic_role": "owner", "introduced_by_task": "Foundation-Task-5", "owner_ref": "runtime-path", "source_ast_sha256": "ebcb69735443d2ef089a81bbd202c260f6dad7ac2b359e60a299d79583ed8dd4"},
}
SOURCE = ROOT / "data/authority/frames/semantic_affordances.json"
# Independent preservation witness for the six pre-de40359 reviewed records.
EXPECTED = (
    ("frame:event:greeting", "event:greeting", "event_type", ("predicate", "anchor"), ("role:actor", "role:addressee"), ("role:event",)),
    ("frame:event:say", "event:say", "event_type", ("predicate", "anchor"), ("role:actor", "role:content"), ("role:event",)),
    ("frame:event:learn_alias", "event:learn_alias", "event_type", ("predicate", "anchor", "reference"), ("role:actor", "role:target", "role:surface"), ("role:event",)),
    ("frame:event:set_state", "event:set_state", "event_type", ("predicate", "anchor", "reference"), ("role:actor", "role:target", "role:dimension", "role:value"), ("role:event",)),
    ("frame:rel:mother_in_law", "rel:mother_in_law", "relation_type", ("predicate", "anchor"), ("role:subject", "role:object"), ("role:relation",)),
    ("frame:rel:has_partner", "rel:has_partner", "relation_type", ("predicate", "anchor"), ("role:subject", "role:object"), ("role:relation",)),
)


def _source():
    source = json.loads(SOURCE.read_text("utf-8"))
    source["owner"] = "semantic_affordances"
    source["generation"] = "authority:test-frames"
    return source


def _bundle(tmp_path, source):
    manifest = json.loads((ROOT / "data/authority/manifest.json").read_text("utf-8"))
    manifest["generation"] = "authority:test-frames"
    manifest["owners"] = [row for row in manifest["owners"] if row["name"] != "semantic_affordances"]
    for row in manifest["owners"]:
        row["path"] = str(ROOT / "data/authority" / row["path"])
    path = tmp_path / "frames.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    manifest["owners"].append({"name": "semantic_affordances", "path": str(path), "sha256": sha256_governed_text(path)})
    store = AuthorityStore()
    manifest["_store"] = store
    return manifest, path, store


def test_active_manifest_preserves_all_six_reviewed_profiles():
    manifest = ROOT / "data/authority/manifest.json"
    authority = AuthorityLinker().link_path(manifest)
    index = SemanticAffordanceIndex(authority, RuntimeConfig.release())
    source = json.loads(SOURCE.read_text("utf-8"))
    assert source["generation"] == authority.generation
    assert len(source["frames"]) == 7
    assert tuple((row["frame_ref"], row["target_ref"], row["target_kind"], tuple(row["contribution_kinds"]), tuple(row["input_ports"]), tuple(row["output_ports"])) for row in source["frames"][:6]) == EXPECTED
    assert all(set(row) == {"frame_ref", "target_ref", "target_kind", "contribution_kinds", "input_ports", "output_ports", "role_candidates"} for row in source["frames"][:6])
    assert source["frames"][6] == {
        "frame_ref": "frame:event:farewell", "target_kind": "event_type",
        "target_ref": "event:farewell", "contribution_kinds": ["predicate", "anchor"],
        "input_ports": ["role:actor", "role:addressee"], "output_ports": ["role:event"],
        "role_candidates": ["role:actor", "role:addressee"],
    }
    assert all(row["role_candidates"] == row["input_ports"] for row in source["frames"])
    for row in source["frames"]:
        profiles = index.for_target(row["target_ref"])
        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.frame_ref == row["frame_ref"]
        assert profile.contribution_kinds == tuple(row["contribution_kinds"])
        assert profile.input_ports == tuple(row["input_ports"])
        assert profile.output_ports == tuple(row["output_ports"])
        assert profile.role_candidates == tuple(row["role_candidates"])
        assert authority.by_frame(row["frame_ref"]) == frozenset({row["target_ref"]})
        assert authority.reviewed_frames_for_target(row["target_ref"])[0].frame_ref == row["frame_ref"]
        assert authority.designations.for_surface(row["frame_ref"], "en") == ()


@pytest.mark.parametrize("mutation", [
    "generation", "owner-field", "frames-type", "row-type", "unknown-field", "missing-field",
    "bad-ref", "ref-type", "unknown-target", "target-kind", "unknown-kind", "kinds-type",
    "empty-kinds", "unknown-contribution", "duplicate-contribution", "ports-type", "unknown-port",
    "duplicate-port", "wrong-event-inputs", "wrong-event-output", "wrong-roles", "duplicate-frame",
    "overlap-frame", "too-many-ports", "duplicate-json", "missing-frames", "missing-generation", "renamed-frames",
], ids=[
    "generation", "owner-field", "frames-type", "row-type", "unknown-field", "missing-field",
    "bad-ref", "ref-type", "unknown-target", "target-kind", "unknown-kind", "kinds-type",
    "empty-kinds", "unknown-contribution", "duplicate-contribution", "ports-type", "unknown-port",
    "duplicate-port", "wrong-event-inputs", "wrong-event-output", "wrong-roles", "duplicate-frame",
    "overlap-frame", "too-many-ports", "duplicate-json", "missing-frames", "missing-generation", "renamed-frames",
])
def test_invalid_reviewed_frame_fails_before_activation(tmp_path, mutation):
    source = _source()
    row = source["frames"][0]
    if mutation == "generation": source["generation"] = "old-generation"
    elif mutation == "owner-field": source["unknown"] = True
    elif mutation == "frames-type": source["frames"] = {}
    elif mutation == "row-type": source["frames"][0] = []
    elif mutation == "unknown-field": row["reviewed"] = True
    elif mutation == "missing-field": del row["target_kind"]
    elif mutation == "bad-ref": row["frame_ref"] = "frame:bad ref"
    elif mutation == "ref-type": row["frame_ref"] = True
    elif mutation == "unknown-target": row["target_ref"] = "event:absent"
    elif mutation == "target-kind": row["target_kind"] = "relation_type"
    elif mutation == "unknown-kind": row["target_kind"] = "unknown"
    elif mutation == "kinds-type": row["contribution_kinds"] = "predicate"
    elif mutation == "empty-kinds": row["contribution_kinds"] = []
    elif mutation == "unknown-contribution": row["contribution_kinds"] = ["bogus"]
    elif mutation == "duplicate-contribution": row["contribution_kinds"] = ["predicate", "predicate"]
    elif mutation == "ports-type": row["input_ports"] = "role:actor"
    elif mutation == "unknown-port": row["input_ports"] = ["role:absent"]
    elif mutation == "duplicate-port": row["input_ports"] = ["role:actor", "role:actor"]
    elif mutation == "wrong-event-inputs": row["input_ports"] = ["role:actor"]
    elif mutation == "wrong-event-output": row["output_ports"] = ["role:relation"]
    elif mutation == "wrong-roles": row["role_candidates"] = ["role:subject"]
    elif mutation == "duplicate-frame": source["frames"].append(copy.deepcopy(row))
    elif mutation == "overlap-frame": source["frames"].append({**row, "frame_ref": "frame:conflict"})
    elif mutation == "too-many-ports": row["input_ports"] = [f"role:p{i}" for i in range(17)]
    elif mutation == "missing-frames": del source["frames"]
    elif mutation == "missing-generation": del source["generation"]
    elif mutation == "renamed-frames": source["frame_records"] = source.pop("frames")
    manifest, path, store = _bundle(tmp_path, source)
    if mutation == "duplicate-json":
        path.write_text(path.read_text("utf-8").replace('"frames":', '"frames": [], "frames":', 1), encoding="utf-8")
        manifest["owners"][-1]["sha256"] = sha256_governed_text(path)
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link(manifest)
    assert store.active_generation is None


@pytest.mark.parametrize("damage", ["missing", "tampered", "json"], ids=["missing", "tampered", "json"])
def test_linked_frame_read_failures_never_become_defaults(tmp_path, damage):
    manifest, path, store = _bundle(tmp_path, _source())
    if damage == "missing": path.unlink()
    elif damage == "tampered": path.write_text("{}", encoding="utf-8")
    else:
        path.write_text("{invalid", encoding="utf-8")
        manifest["owners"][-1]["sha256"] = sha256_governed_text(path)
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link(manifest)
    assert store.active_generation is None


def test_frame_hashes_are_deterministic_and_structurally_sensitive(tmp_path):
    source = _source()
    manifest, _, _ = _bundle(tmp_path, source)
    first = AuthorityLinker().link(manifest)
    source["frames"].reverse()
    manifest, _, _ = _bundle(tmp_path, source)
    reordered = AuthorityLinker().link(manifest)
    assert (first.content_hash, first.model_compatibility_hash) == (reordered.content_hash, reordered.model_compatibility_hash)
    source["frames"][0]["contribution_kinds"] = ["predicate"]
    manifest, _, _ = _bundle(tmp_path, source)
    changed = AuthorityLinker().link(manifest)
    assert changed.content_hash != first.content_hash
    assert changed.model_compatibility_hash != first.model_compatibility_hash


def test_frames_are_linked_snapshot_and_explicit_absence_uses_defaults(tmp_path):
    manifest, path, _ = _bundle(tmp_path, _source())
    linked = AuthorityLinker().link(manifest)
    path.unlink()
    index = SemanticAffordanceIndex(linked, RuntimeConfig.release())
    assert index.for_target("event:greeting")[0].frame_ref == "frame:event:greeting"
    manifest["owners"].pop()
    without_frames = AuthorityLinker().link(manifest)
    defaults = SemanticAffordanceIndex(without_frames, RuntimeConfig.release()).for_target("event:greeting")
    assert len(defaults) == 2
    assert all(profile.frame_ref is None for profile in defaults)


def test_fresh_frame_generation_reopens_and_rejects_prior_store_without_mutation(tmp_path):
    from cemm_authoritative_hybrid.bootstrap import load_runtime
    from cemm_authoritative_hybrid.persistence import open_stores, StoreActivationError

    prior_path = tmp_path / "prior.db"
    prior = open_stores(prior_path, authority_generation="authority-v1-2026-09-08-linked-alias-contract")
    prior.close()
    prior_bytes = (prior_path / "semantic.db").read_bytes()
    with pytest.raises(StoreActivationError, match="authority generation mismatch"):
        load_runtime(ROOT, profile="development", store_path=prior_path)
    assert (prior_path / "semantic.db").read_bytes() == prior_bytes
    # SQLite may open shared-memory bookkeeping; no durable page or WAL write
    # may accompany the rejected activation.
    wal = prior_path / "semantic.db-wal"
    assert not wal.exists() or wal.read_bytes() == b""
    fresh_path = tmp_path / "fresh.db"
    for _ in range(2):
        runtime = load_runtime(ROOT, profile="development", store_path=fresh_path)
        try:
            assert runtime.authority.generation == "authority-v1-2026-10-02-communicative-source"
            assert runtime.stores.revision_pin().authority_generation == runtime.authority.generation
            index = SemanticAffordanceIndex(runtime.authority, RuntimeConfig.release())
            for ref, target, kind, contributions, inputs, outputs in EXPECTED:
                assert index.for_target(target)[0].frame_ref == ref
        finally:
            runtime.stores.close()


def test_rejected_frame_generation_activation_closes_sqlite_connection(tmp_path, monkeypatch):
    import sqlite3
    from cemm_authoritative_hybrid import persistence
    from cemm_authoritative_hybrid.bootstrap import load_runtime

    path = tmp_path / "prior"
    prior = persistence.open_stores(path, authority_generation="authority-v1-2026-09-08-linked-alias-contract")
    prior.close()
    connections = []
    connect = sqlite3.connect

    def record_connection(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(persistence.sqlite3, "connect", record_connection)
    with pytest.raises(persistence.StoreActivationError, match="authority generation mismatch"):
        load_runtime(ROOT, profile="development", store_path=path)
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connections[0].execute("SELECT value FROM metadata WHERE key = 'authority_generation'")


@pytest.mark.parametrize("field,value", [
    ("filler_kinds", ["potato"]),
    ("filler_kinds", "participant"),
    ("filler_kinds", []),
    ("filler_kinds", [True]),
    ("filler_kinds", ["participant", "participant"]),
    ("filler_kinds", None),
    ("required", "no"),
    ("required", 1),
    ("proposition_valued", "false"),
    ("proposition_valued", True),
    ("filler_kinds", ["application"]),
    ("role", ""),
    ("role", "role:"),
    ("role", "role:bad port"),
    ("role", "event:actor"),
    ("overlong_role", "role:"),
    ("unexpected", True),
], ids=[
    "unknown-filler-kind", "string-filler-kinds", "empty-filler-kinds", "bool-filler-kind",
    "duplicate-filler-kind", "missing-filler-kinds", "string-required", "int-required",
    "string-proposition", "proposition-without-application", "application-without-proposition",
    "empty-mirrored-port", "empty-role-name", "whitespace-role", "wrong-role-namespace",
    "overlong-role", "unknown-role-field",
])
def test_reviewed_frame_source_role_schema_is_strict_before_activation(tmp_path, field, value):
    if field == "overlong_role":
        field, value = "role", value + "a" * 512
    source = _source()
    conversation = json.loads((ROOT / "data/authority/conversation.json").read_text("utf-8"))
    signature = next(row for row in conversation["event_signatures"] if row["event_type"] == "event:greeting")
    role = signature["roles"][0]
    if value is None:
        del role[field]
    else:
        role[field] = value
    # Equal invalid frame/signature strings must not constitute a legal port.
    if field == "role":
        source["frames"][0]["input_ports"][0] = value
        source["frames"][0]["role_candidates"][0] = value
    manifest, _, store = _bundle(tmp_path, source)
    path = tmp_path / "conversation.json"
    path.write_text(json.dumps(conversation), encoding="utf-8")
    owner = next(row for row in manifest["owners"] if row["name"] == "conversation")
    owner.update(path=str(path), sha256=sha256_governed_text(path))
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link(manifest)
    assert store.active_generation is None


@pytest.mark.parametrize("roles", [
    ["role:subject", "role:object"],
    ["role:subject", "role:relation", "role:relation", "role:object"],
    ["role:target", "role:relation", "role:object"],
], ids=["missing-output", "duplicate-output", "wrong-mirrored-input"])
def test_reviewed_relation_frame_requires_complete_fixed_operator_schema(tmp_path, roles):
    source = _source()
    if roles[0] == "role:target":
        for frame in source["frames"]:
            if frame["target_kind"] == "relation_type":
                frame["input_ports"][0] = "role:target"
                frame["role_candidates"][0] = "role:target"
    manifest, _, store = _bundle(tmp_path, source)
    kernel = json.loads((ROOT / "data/authority/kernel.json").read_text("utf-8"))
    kernel["operator_roles"]["op:relation"] = roles
    path = tmp_path / "kernel.json"
    path.write_text(json.dumps(kernel), encoding="utf-8")
    owner = next(row for row in manifest["owners"] if row["name"] == "kernel")
    owner.update(path=str(path), sha256=sha256_governed_text(path))
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link(manifest)
    assert store.active_generation is None


@pytest.mark.parametrize("roles", [
    ["role:type"],
    ["role:event", "role:event", "role:type"],
    ["role:event", "role:relation"],
    {"role:event": True, "role:type": True},
], ids=["missing-output", "duplicate-output", "wrong-type-role", "object-not-list"])
def test_reviewed_event_frame_requires_fixed_operator_without_alias_contract(tmp_path, roles):
    manifest, _, store = _bundle(tmp_path, _source())
    manifest["owners"] = [row for row in manifest["owners"] if row["name"] != "alias_learning"]
    kernel = json.loads((ROOT / "data/authority/kernel.json").read_text("utf-8"))
    kernel["operator_roles"]["op:event"] = roles
    path = tmp_path / "kernel.json"
    path.write_text(json.dumps(kernel), encoding="utf-8")
    owner = next(row for row in manifest["owners"] if row["name"] == "kernel")
    owner.update(path=str(path), sha256=sha256_governed_text(path))
    with pytest.raises(AuthorityLinkError):
        AuthorityLinker().link(manifest)
    assert store.active_generation is None
