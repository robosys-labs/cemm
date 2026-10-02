"""Private Task-7.2a predecessor envelopes and activated matching controls."""
from copy import deepcopy
from dataclasses import fields, replace
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from cemm_authoritative_hybrid.authority import DesignationFact
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.gaps import BudgetExhausted
from cemm_authoritative_hybrid.proposal_context import ProposalContext
import cemm_authoritative_hybrid.proposal_context as context_owner
import cemm_authoritative_hybrid.role_schemas as schema_owner
from tests.test_foundation_semantics import _static_composition_context

__cemm_test_inventory__ = {
  "tests/test_foundation_projection_construction.py::test_private_projection_explicit_contents_preserve_target_and_ports[en-bare]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-explicit-contents-preserve-target-and-ports-en-bare",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "3213fc895024a59870739a2df3eb78c9f899eb7cfe04418bcdc913ee9f5f4ce1"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_explicit_contents_preserve_target_and_ports[en-determiner]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-explicit-contents-preserve-target-and-ports-en-determiner",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "3213fc895024a59870739a2df3eb78c9f899eb7cfe04418bcdc913ee9f5f4ce1"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_explicit_contents_preserve_target_and_ports[es-bare]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-explicit-contents-preserve-target-and-ports-es-bare",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "3213fc895024a59870739a2df3eb78c9f899eb7cfe04418bcdc913ee9f5f4ce1"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_explicit_contents_preserve_target_and_ports[es-determiner]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-explicit-contents-preserve-target-and-ports-es-determiner",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "3213fc895024a59870739a2df3eb78c9f899eb7cfe04418bcdc913ee9f5f4ce1"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_context_abi3_exact_detached_roundtrip": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-context-abi3-exact-detached-roundtrip",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "aee4c379f2d030667b1ee29d9cefd962172533d47d0108ce02d708c86527693f"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[unknown]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-unknown",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[deictic]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-deictic",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[person]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-person",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[scope]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-scope",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[compound]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-compound",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[punctuation]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-punctuation",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[extra-target]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-extra-target",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_unlicensed_evidence_does_not_match[double-determiner]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-unlicensed-evidence-does-not-match-double-determiner",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fca3df15b1d901f722fd1d746697bec209580fec2c084ced736844acfdce2853"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_old_pack_has_no_content_authority[en]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-old-pack-has-no-content-authority-en",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a65250e38bf7e550e6e685506b18ae67e6a409dd71cb736af64a36987b5083ff"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_old_pack_has_no_content_authority[es]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-old-pack-has-no-content-authority-es",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a65250e38bf7e550e6e685506b18ae67e6a409dd71cb736af64a36987b5083ff"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_alias_polysemy_is_cartesian_without_pack_rewrite": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-alias-polysemy-is-cartesian-without-pack-rewrite",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "ff7ddf671eb03e017fe58d52f187b9e2013ca816c7838a9db150a4ac8f595cca"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_quantification_is_not_an_article[every]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-quantification-is-not-an-article-every",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "89b0ef5305aa5a5efac64c3f63d78e0a757944f8c9537b4c7adb90e5296050f1"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_quantification_is_not_an_article[all]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-quantification-is-not-an-article-all",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "89b0ef5305aa5a5efac64c3f63d78e0a757944f8c9537b4c7adb90e5296050f1"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[abi2]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-abi2",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[abi-float]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-abi-float",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[missing]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-missing",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[extra]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-extra",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[cycle]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-cycle",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[alias]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-alias",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[list-subclass]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-list-subclass",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[binding-extra]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-binding-extra",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[binding-cycle]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-binding-cycle",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[too-many-slots]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-too-many-slots",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_wire_is_strict_bounded_and_alias_free[too-many-sources]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-wire-is-strict-bounded-and-alias-free-too-many-sources",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "a8d1719a21c5b6c4fe880a9d27557f1b72a487bf65ae8db7cccaa9c1f4d68e19"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[target]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-target",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[pointer]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-pointer",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[source]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-source",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[span]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-span",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[ownership]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-ownership",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[order]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-order",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[orthography]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-orthography",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_slot_context_rejects_crossbindings[subclass]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-slot-context-rejects-crossbindings-subclass",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5bfc671f158e17d1871d981f5e36e699d2e218052c4f33d00e09d8d47a505b36"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_rehashed_codec_is_not_an_activation_claim": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-rehashed-codec-is-not-an-activation-claim",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "0d03cb8e1e54fefb022d4ff9154b702ef704b6ddb535132ca6e8f1e3be5ede7e"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_rejects_unreviewed_schema_shapes[contents]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-rejects-unreviewed-schema-shapes-contents",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "b32f1a86b59f085ec2eb1eef50d557d1b69727cdb463cb521cfffecb1d83f101"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_rejects_unreviewed_schema_shapes[result-extra]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-rejects-unreviewed-schema-shapes-result-extra",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "b32f1a86b59f085ec2eb1eef50d557d1b69727cdb463cb521cfffecb1d83f101"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_rejects_unreviewed_schema_shapes[target-kind]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-rejects-unreviewed-schema-shapes-target-kind",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "b32f1a86b59f085ec2eb1eef50d557d1b69727cdb463cb521cfffecb1d83f101"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_rejects_unreviewed_schema_shapes[persistent-role]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-rejects-unreviewed-schema-shapes-persistent-role",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "b32f1a86b59f085ec2eb1eef50d557d1b69727cdb463cb521cfffecb1d83f101"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_rejects_unreviewed_schema_shapes[unknown-feature]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-rejects-unreviewed-schema-shapes-unknown-feature",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "b32f1a86b59f085ec2eb1eef50d557d1b69727cdb463cb521cfffecb1d83f101"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_rejects_unreviewed_schema_shapes[required-determiner]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-rejects-unreviewed-schema-shapes-required-determiner",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "b32f1a86b59f085ec2eb1eef50d557d1b69727cdb463cb521cfffecb1d83f101"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_identity_is_pinned[pack]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-identity-is-pinned-pack",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "186d40ee4600e0a5f386d838d94960039386029b831db1d4990938304fcd9ce2"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_identity_is_pinned[generation]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-identity-is-pinned-generation",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "186d40ee4600e0a5f386d838d94960039386029b831db1d4990938304fcd9ce2"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_identity_is_pinned[schemas]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-identity-is-pinned-schemas",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "186d40ee4600e0a5f386d838d94960039386029b831db1d4990938304fcd9ce2"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_identity_is_pinned[patterns]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-identity-is-pinned-patterns",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "186d40ee4600e0a5f386d838d94960039386029b831db1d4990938304fcd9ce2"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_activation_identity_is_pinned[bounds]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-activation-identity-is-pinned-bounds",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "186d40ee4600e0a5f386d838d94960039386029b831db1d4990938304fcd9ce2"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_alternatives_spend_existing_bounds[matches]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-alternatives-spend-existing-bounds-matches",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c1f6c61a015dc9ae723958d359bce1b393b11a8b3c9dfb20a2458a4b2c182086"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_alternatives_spend_existing_bounds[attempts]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-alternatives-spend-existing-bounds-attempts",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c1f6c61a015dc9ae723958d359bce1b393b11a8b3c9dfb20a2458a4b2c182086"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_alternatives_spend_existing_bounds[slots]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-alternatives-spend-existing-bounds-slots",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c1f6c61a015dc9ae723958d359bce1b393b11a8b3c9dfb20a2458a4b2c182086"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_alternatives_spend_existing_bounds[source]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-alternatives-spend-existing-bounds-source",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c1f6c61a015dc9ae723958d359bce1b393b11a8b3c9dfb20a2458a4b2c182086"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_closed_features_cannot_hide_in_known_alias": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-closed-features-cannot-hide-in-known-alias",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "f9613d48111afdadd824cb70eda0c71a1a17459f55c1dfe69d21ec01849609b3"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_multiword_alias_keeps_whitespace_orthographic": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-multiword-alias-keeps-whitespace-orthographic",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "8382b0b7e1554e481c3261692e265ea7e0795af2c8e21e53f610d7278a8b61e7"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_target_kinds_are_explicit_designations[concept]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-target-kinds-are-explicit-designations-concept",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "4f87715f496b6baf41e7b4ab8ed5f8d3ab35ac0390fb53c7eb225919c1f8cf20"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_target_kinds_are_explicit_designations[entity]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-target-kinds-are-explicit-designations-entity",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "4f87715f496b6baf41e7b4ab8ed5f8d3ab35ac0390fb53c7eb225919c1f8cf20"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_target_kinds_are_explicit_designations[participant-designation]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-target-kinds-are-explicit-designations-participant-designation",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "4f87715f496b6baf41e7b4ab8ed5f8d3ab35ac0390fb53c7eb225919c1f8cf20"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_primitive_ownership_is_independently_checked[ref]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-primitive-ownership-is-independently-checked-ref",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c17fb1c89b194687c17d4b6f0c26f4c1d05f114f75c01c3bf6bb795291e45fe5"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_primitive_ownership_is_independently_checked[provenance]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-primitive-ownership-is-independently-checked-provenance",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c17fb1c89b194687c17d4b6f0c26f4c1d05f114f75c01c3bf6bb795291e45fe5"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_primitive_ownership_is_independently_checked[overlap]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-primitive-ownership-is-independently-checked-overlap",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "c17fb1c89b194687c17d4b6f0c26f4c1d05f114f75c01c3bf6bb795291e45fe5"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_maximum_target_content_set_is_not_truncated": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-maximum-target-content-set-is-not-truncated",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "09147340e4fd46446634597eb6edc3baada64845e2447d6f0f5e151cf8771f25"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_sum_preserves_persistent_role_schemas": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-sum-preserves-persistent-role-schemas",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "1e9b00e6439a8baa2aa26374823474bd9c8a70bc0b497617d9319403f98f6d8e"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_optional_article_binding_subclass_is_rejected": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-optional-article-binding-subclass-is-rejected",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "5fc2a48965ba117c1e72191841f84df27c7ffcb5b0f1797d01ebb61b6610f772"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_mutable_collection_subclass_is_rejected[create]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-mutable-collection-subclass-is-rejected-create",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "9ad5704346b14c924760b35b647391f914cecc87e5cb3772544fe1a3b82efc43"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_mutable_collection_subclass_is_rejected[dataclass]": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-mutable-collection-subclass-is-rejected-dataclass",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "9ad5704346b14c924760b35b647391f914cecc87e5cb3772544fe1a3b82efc43"
  },
  "tests/test_foundation_projection_construction.py::test_private_projection_accepted_long_context_ref_round_trips_detached": {
    "activation_phase": "R4",
    "assertion_ref": "assertion:foundation-private-projection-accepted-long-context-ref-round-trips-detached",
    "diagnostic_role": "owner",
    "introduced_by_task": "Foundation-Task-7",
    "owner_ref": "decision-query-proof",
    "source_ast_sha256": "fd64e0c37b67e1d931466308b43d345d72f0d3e648481b0cc615595120e337bc"
  }
}

ROOT = Path(__file__).resolve().parents[1]


def _pack(language="en", *, licensed=True):
    pack = json.loads((ROOT / "data/languages" / language / "forms.json").read_text(encoding="utf-8"))
    if not licensed:
        # Exact pre-7.2b source reconstruction, not an unlicensed current pack.
        pack["application_role_orders"].pop("content_target_projection", None)
        for surface in (("a", "an", "the") if language == "en" else ("un", "una", "el", "la")):
            pack["determiners"][surface].pop("construction_role", None)
        if language == "es":
            pack["query_projection"]["qué"].pop("interrogative", None)
        return pack
    if language == "es":
        pack["query_projection"]["qué"]["interrogative"] = "content"
    for surface in (("a", "an", "the") if language == "en" else ("un", "una", "el", "la")):
        pack["determiners"][surface]["construction_role"] = "query_target_article"
    if licensed:
        pack["application_role_orders"]["content_target_projection"] = {
            "evidence_order": [
                {"kind": "feature", "port": "request", "features": [["query", "query"], ["interrogative", "content"]]},
                {"kind": "feature", "port": "binder", "features": [["binder", "copula"]]},
                {"kind": "feature", "port": "determiner", "features": [["determiner", "determiner"], ["construction_role", "query_target_article"]], "cardinality": "optional"},
                {"kind": "designation", "port": "target", "target_kinds": ["concept", "entity", "participant"]},
            ],
            "result": {"kind": "query_projection", "target_port": "target", "requested_contents": ["description", "definition"]},
        }
    return pack


@pytest.fixture
def runtime(tmp_path):
    value = load_runtime(ROOT, profile="development", store_path=tmp_path / "construction.db")
    yield value
    value.stores.close()


def _fixture(runtime, surface="what is Bob?", language="en", *, facts=None, licensed=True):
    pack = _pack(language, licensed=licensed)
    if facts is None and language == "es":
        facts = (DesignationFact.create(surface="Bob", target_ref="entity:bob", language=language),)
    # Retain the private predecessor envelope explicitly. Successor derivation
    # tests separately inspect actual public builder emission with current rows.
    builder, context = _static_composition_context(runtime.authority, runtime.stores, pack, surface, facts=facts)
    return pack, builder.role_schema_index, _with_slots(context, ())


def _with_slots(context, slots):
    values = {f.name: getattr(context, f.name) for f in fields(context) if f.init and f.name not in {"context_ref", "abi_version"}}
    values["query_projection_slots"] = slots
    return ProposalContext.create(**values)


@pytest.mark.parametrize("language,surface", (("en", "what is Bob?"), ("en", "what is the Bob?"), ("es", "qué es Bob?"), ("es", "qué es el Bob?")), ids=("en-bare", "en-determiner", "es-bare", "es-determiner"))
def test_private_projection_explicit_contents_preserve_target_and_ports(runtime, language, surface):
    _, index, context = _fixture(runtime, surface, language)
    matches = index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
    assert len(matches) == 2
    assert {type(m).__name__ for m in matches} == {"QueryProjectionMatch"}
    assert {m.requested_content for m in matches} == {"description", "definition"}
    assert len({m.match_ref for m in matches}) == 2
    assert schema_owner.relation_projection_matches(index, matches) == ()
    slots = context_owner.licensed_query_projection_slots(index, context)
    assert len(slots) == 2 and context.query_projection_slots == ()
    assert {s.target_designation_slot_ref for s in slots} == {d.slot_ref for d in context.designation_slots}
    assert all(not hasattr(s, "target_ref") for s in slots)
    for slot in slots:
        ports = tuple(b.port for b in slot.bindings)
        assert ports == (("request", "binder", "determiner", "target") if " the " in surface or " el " in surface else ("request", "binder", "target"))
        owned = [ref for b in slot.bindings for ref in b.source_unit_refs]
        assert len(owned) == len(set(owned))
        assert set(owned).isdisjoint(slot.orthographic_source_unit_refs)
        assert set(owned) | set(slot.orthographic_source_unit_refs) == set(slot.source_unit_refs)
        assert slot.source_unit_spans == context.source_unit_spans
        assert {b.contribution_slot_ref for b in slot.bindings} <= {c.slot_ref for c in context.contribution_slots}
        assert (slot.index_ref, slot.schema_ref, slot.match_ref) == slot.provenance_refs[:3]
    assert context.application_frames == ()


def test_private_projection_context_abi3_exact_detached_roundtrip(runtime):
    _, index, context = _fixture(runtime)
    assert context_owner.PROPOSAL_CONTEXT_ABI_VERSION == 3
    slots = context_owner.licensed_query_projection_slots(index, context)
    value = _with_slots(context, slots)
    wire = value.as_dict()
    decoded = ProposalContext.from_dict(json.loads(json.dumps(wire)))
    assert decoded == value and decoded.as_dict() == wire
    assert decoded.query_projection_slots is not value.query_projection_slots
    assert isinstance(value._query_projection_by_ref, MappingProxyType)
    assert value.query_projection(slots[0].slot_ref) is slots[0]
    assert value.query_projection("projection:absent") is None
    assert decoded.query_projection(slots[0].slot_ref) is decoded.query_projection_slots[0]
    wire["query_projection_slots"][0]["requested_content"] = "definition"
    assert value.query_projection_slots[0].as_dict() != wire["query_projection_slots"][0]


@pytest.mark.parametrize("surface", ("what is velnora?", "what is you?", "who is Bob?", "what is not Bob?", "what is Bob and Alice?", "what is Bob,?", "what is Bob Alice?", "what is the the Bob?"), ids=("unknown", "deictic", "person", "scope", "compound", "punctuation", "extra-target", "double-determiner"))
def test_private_projection_unlicensed_evidence_does_not_match(runtime, surface):
    _, index, context = _fixture(runtime, surface)
    assert index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans) == ()
    assert context_owner.licensed_query_projection_slots(index, context) == ()


@pytest.mark.parametrize("language", ("en", "es"), ids=("en", "es"))
def test_private_projection_old_pack_has_no_content_authority(runtime, language):
    _, index, context = _fixture(runtime, "what is Bob?" if language == "en" else "qué es Bob?", language, licensed=False)
    assert index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans) == ()
    assert context.query_projection_slots == ()


def test_private_projection_alias_polysemy_is_cartesian_without_pack_rewrite(runtime):
    facts = tuple(DesignationFact.create(surface="velnora", target_ref=target, language="en") for target in ("entity:bob", "entity:alice"))
    pack, index, context = _fixture(runtime, "what is velnora?", facts=facts)
    before = deepcopy(pack)
    matches = index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
    slots = context_owner.licensed_query_projection_slots(index, context)
    assert len(matches) == len(slots) == 4
    assert {(context.designation(s.target_designation_slot_ref).target_ref, s.requested_content) for s in slots} == {(target, content) for target in ("entity:bob", "entity:alice") for content in ("description", "definition")}
    assert pack == before and len({s.slot_ref for s in slots}) == 4


@pytest.mark.parametrize("surface", ("what is every mother?", "what is all mother?"), ids=("every", "all"))
def test_private_projection_quantification_is_not_an_article(runtime, surface):
    _, index, context = _fixture(runtime, surface)
    assert index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans) == ()


@pytest.mark.parametrize("mutation", ("abi2", "abi-float", "missing", "extra", "cycle", "alias", "list-subclass", "binding-extra", "binding-cycle", "too-many-slots", "too-many-sources"), ids=("abi2", "abi-float", "missing", "extra", "cycle", "alias", "list-subclass", "binding-extra", "binding-cycle", "too-many-slots", "too-many-sources"))
def test_private_projection_wire_is_strict_bounded_and_alias_free(runtime, mutation):
    _, index, context = _fixture(runtime)
    value = _with_slots(context, context_owner.licensed_query_projection_slots(index, context))
    wire = value.as_dict()
    if mutation == "abi2": wire["abi_version"] = 2
    elif mutation == "abi-float": wire["abi_version"] = 3.0
    elif mutation == "missing": del wire["query_projection_slots"]
    elif mutation == "extra": wire["query_projection_slots"][0]["target_ref"] = "entity:bob"
    elif mutation == "cycle": wire["query_projection_slots"].append(wire)
    elif mutation == "alias": wire["query_projection_slots"][1]["source_unit_refs"] = wire["query_projection_slots"][0]["source_unit_refs"]
    elif mutation == "list-subclass":
        class WireList(list): pass
        wire["query_projection_slots"] = WireList(wire["query_projection_slots"])
    elif mutation == "binding-extra": wire["query_projection_slots"][0]["bindings"][0]["role"] = "role:subject"
    elif mutation == "binding-cycle": wire["query_projection_slots"][0]["bindings"][0]["source_unit_refs"] = wire["query_projection_slots"]
    elif mutation == "too-many-slots": wire["query_projection_slots"] = [deepcopy(wire["query_projection_slots"][0]) for _ in range(17)]
    elif mutation == "too-many-sources": wire["query_projection_slots"][0]["source_unit_refs"] = ["source:extra" for _ in range(65)]
    with pytest.raises((TypeError, ValueError)):
        ProposalContext.from_dict(wire)


@pytest.mark.parametrize("mutation", ("target", "pointer", "source", "span", "ownership", "order", "orthography", "subclass"), ids=("target", "pointer", "source", "span", "ownership", "order", "orthography", "subclass"))
def test_private_projection_rehashed_slot_context_rejects_crossbindings(runtime, mutation):
    _, index, context = _fixture(runtime)
    slot = context_owner.licensed_query_projection_slots(index, context)[0]
    values = {f.name: getattr(slot, f.name) for f in fields(slot) if f.name != "slot_ref"}
    bindings = list(slot.bindings)
    if mutation == "target": values["target_designation_slot_ref"] = "designation_slot:foreign"
    elif mutation == "pointer": bindings[0] = replace(bindings[0], contribution_slot_ref=bindings[1].contribution_slot_ref)
    elif mutation == "source": bindings[0] = replace(bindings[0], source_unit_refs=("source:foreign",))
    elif mutation == "span": values["source_unit_spans"] = tuple((ref, start + 1, end + 1) for ref, start, end in slot.source_unit_spans)
    elif mutation == "ownership": bindings[1] = replace(bindings[1], source_unit_refs=bindings[0].source_unit_refs)
    elif mutation == "order": values["source_unit_refs"] = tuple(reversed(slot.source_unit_refs))
    elif mutation == "orthography": values["orthographic_source_unit_refs"] = slot.source_unit_refs
    elif mutation == "subclass":
        class Binding(schema_owner.QueryProjectionBinding): pass
        bindings[0] = Binding(bindings[0].port, bindings[0].contribution_slot_ref, bindings[0].source_unit_refs)
    values["bindings"] = tuple(bindings)
    values["provenance_refs"] = tuple(dict.fromkeys((slot.index_ref, slot.schema_ref, slot.match_ref,
        values["target_designation_slot_ref"], *(b.contribution_slot_ref for b in bindings))))
    with pytest.raises((TypeError, ValueError)):
        forged = context_owner.QueryProjectionSlot.create(**values)
        _with_slots(context, (forged,))


def test_private_projection_rehashed_codec_is_not_an_activation_claim(runtime):
    _, index, context = _fixture(runtime)
    slot = context_owner.licensed_query_projection_slots(index, context)[0]
    values = {f.name: getattr(slot, f.name) for f in fields(slot) if f.name != "slot_ref"}
    values["match_ref"] = "reviewed_query_projection_match:unlicensed"
    values["provenance_refs"] = tuple(values["match_ref"] if ref == slot.match_ref else ref for ref in slot.provenance_refs)
    forged = context_owner.QueryProjectionSlot.create(**values)
    value = _with_slots(context, (forged,))
    assert ProposalContext.from_dict(value.as_dict()) == value
    # Only real rematching licenses a slot; structural hashes cannot do it.
    assert forged not in context_owner.licensed_query_projection_slots(index, context)


@pytest.mark.parametrize("mutation", ("contents", "result-extra", "target-kind", "persistent-role", "unknown-feature", "required-determiner"), ids=("contents", "result-extra", "target-kind", "persistent-role", "unknown-feature", "required-determiner"))
def test_private_projection_activation_rejects_unreviewed_schema_shapes(runtime, mutation):
    pack = _pack()
    row = pack["application_role_orders"]["content_target_projection"]
    if mutation == "contents": row["result"]["requested_contents"] = ["description", "description"]
    elif mutation == "result-extra": row["result"]["operator"] = "op:type"
    elif mutation == "target-kind": row["evidence_order"][-1]["target_kinds"] = ["event_type"]
    elif mutation == "persistent-role": row["evidence_order"][0]["role"] = "role:subject"
    elif mutation == "unknown-feature": row["evidence_order"][0]["features"].append(["request_content", "description"])
    elif mutation == "required-determiner": row["evidence_order"][2]["cardinality"] = "required"
    with pytest.raises(ValueError):
        schema_owner.ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, RuntimeConfig.release())


@pytest.mark.parametrize("mutation", ("pack", "generation", "schemas", "patterns", "bounds"), ids=("pack", "generation", "schemas", "patterns", "bounds"))
def test_private_projection_activation_identity_is_pinned(runtime, mutation):
    pack, index, context = _fixture(runtime)
    if mutation == "pack":
        pack["language"] = "different-reviewed-pack"
        with pytest.raises(ValueError): index.validate_activation(runtime.authority, pack)
        return
    if mutation == "generation": object.__setattr__(index, "authority_generation", "authority:stale")
    elif mutation == "schemas": object.__setattr__(index, "schemas", tuple(reversed(index.schemas)))
    elif mutation == "patterns": object.__setattr__(index, "primitive_patterns", ())
    elif mutation == "bounds": object.__setattr__(index, "match_limit", 17)
    with pytest.raises(ValueError): context_owner.licensed_query_projection_slots(index, context)


@pytest.mark.parametrize("bound", ("matches", "attempts", "slots", "source"), ids=("matches", "attempts", "slots", "source"))
def test_private_projection_alternatives_spend_existing_bounds(runtime, bound):
    facts = tuple(DesignationFact.create(surface="velnora", target_ref=target, language="en") for target in ("entity:bob", "entity:alice"))
    pack, index, context = _fixture(runtime, "what is velnora?", facts=facts)
    assert (index.match_limit, index.attempt_limit) == (16, 32)
    if bound in {"matches", "attempts"}:
        if bound == "matches":
            row = pack["application_role_orders"]["content_target_projection"]
            pack["application_role_orders"] = {"projection_one": row, "projection_two": deepcopy(row)}
        config = replace(RuntimeConfig.release(), **({"max_orientation_alternatives": 4} if bound == "matches" else {"max_beam_states": 7}))
        bounded = schema_owner.ReviewedRoleSchemaIndex.from_pack(pack, runtime.authority, config)
        with pytest.raises(BudgetExhausted) as raised:
            bounded.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)
        assert raised.value.budget_name == ("reviewed_role_matches" if bound == "matches" else "reviewed_role_match_attempts")
    elif bound == "slots":
        slot = context_owner.licensed_query_projection_slots(index, context)[0]
        with pytest.raises(ValueError): _with_slots(context, (slot,) * 17)
    else:
        spans = tuple((f"source:{i}", i, i + 1) for i in range(65))
        with pytest.raises(ValueError): index.matches((), (), spans)


def test_private_projection_closed_features_cannot_hide_in_known_alias(runtime):
    facts = (DesignationFact.create(surface="not Bob", target_ref="entity:bob", language="en"),)
    _, index, context = _fixture(runtime, "what is not Bob?", facts=facts)
    assert context.designation_slots
    assert index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans) == ()


def test_private_projection_multiword_alias_keeps_whitespace_orthographic(runtime):
    facts = (DesignationFact.create(surface="vel nora", target_ref="entity:bob", language="en"),)
    _, index, context = _fixture(runtime, "what is vel nora?", facts=facts)
    slots = context_owner.licensed_query_projection_slots(index, context)
    assert len(slots) == 2
    value = _with_slots(context, slots)
    assert ProposalContext.from_dict(value.as_dict()) == value
    for slot in slots:
        target = slot.bindings[-1]
        assert len(target.source_unit_refs) == 2
        assert not set(target.source_unit_refs) & set(slot.orthographic_source_unit_refs)


@pytest.mark.parametrize("target", ("concept:mother", "entity:bob", "participant:system"), ids=("concept", "entity", "participant-designation"))
def test_private_projection_target_kinds_are_explicit_designations(runtime, target):
    facts = (DesignationFact.create(surface="velnora", target_ref=target, language="en"),)
    _, index, context = _fixture(runtime, "what is velnora?", facts=facts)
    slots = context_owner.licensed_query_projection_slots(index, context)
    assert len(slots) == 2
    assert {context.designation(s.target_designation_slot_ref).target_ref for s in slots} == {target}


@pytest.mark.parametrize("mutation", ("ref", "provenance", "overlap"), ids=("ref", "provenance", "overlap"))
def test_private_projection_primitive_ownership_is_independently_checked(runtime, mutation):
    _, index, context = _fixture(runtime)
    primitive = next(c for c in context.contribution_slots if c.kind == "binder")
    values = {f.name: getattr(primitive, f.name) for f in fields(primitive) if f.name != "slot_ref"}
    if mutation == "ref": values["contribution_ref"] = "form_contribution:forged"
    elif mutation == "provenance": values["provenance_refs"] = ("source:foreign",)
    else:
        source = primitive.source_unit_refs[0]
        extra = context_owner.ContributionSlot.create(contribution_ref=context_owner._primitive_form_ref(source, "polarity", "negation"),
            kind="scope", source_unit_refs=(source,), target_ref=None, target_kind=None,
            input_ports=context_owner._primitive_form_ports("scope")[0],
            output_ports=context_owner._primitive_form_ports("scope")[1],
            constraints=(("polarity", "negation"),), provenance_refs=(source,))
        contributions = (*context.contribution_slots, extra)
        assert index.matches(context.designation_slots, contributions, context.source_unit_spans) == ()
        return
    forged = context_owner.ContributionSlot.create(**values)
    contributions = tuple(forged if c.slot_ref == primitive.slot_ref else c for c in context.contribution_slots)
    with pytest.raises(ValueError, match="primitive contribution ownership"):
        index.matches(context.designation_slots, contributions, context.source_unit_spans)


def test_private_projection_maximum_target_content_set_is_not_truncated(runtime):
    targets = tuple(atom.ref for atom in runtime.authority.atoms.values() if atom.reviewed and atom.kind in {"concept", "entity", "participant"})[:8]
    assert len(targets) == 8
    facts = tuple(DesignationFact.create(surface="velnora", target_ref=target, language="en") for target in targets)
    _, index, context = _fixture(runtime, "what is velnora?", facts=facts)
    slots = context_owner.licensed_query_projection_slots(index, context)
    assert len(slots) == 16
    assert {(context.designation(s.target_designation_slot_ref).target_ref, s.requested_content) for s in slots} == {(target, content) for target in targets for content in ("description", "definition")}
    value = _with_slots(context, slots)
    assert ProposalContext.from_dict(value.as_dict()) == value


def test_private_projection_sum_preserves_persistent_role_schemas(runtime):
    base = schema_owner.ReviewedRoleSchemaIndex.from_pack(_pack(licensed=False), runtime.authority, RuntimeConfig.release())
    _, index, context = _fixture(runtime)
    assert tuple(s for s in index.schemas if type(s) is schema_owner.ReviewedRoleSchema) == tuple(
        s for s in base.schemas if type(s) is schema_owner.ReviewedRoleSchema)
    assert tuple(s for s in index.schemas if type(s) is schema_owner.ReviewedCommunicativeSchema) == tuple(
        s for s in base.schemas if type(s) is schema_owner.ReviewedCommunicativeSchema)
    projection = next(s for s in index.schemas if type(s) is schema_owner.ReviewedQueryProjectionSchema)
    assert tuple(s.port for s in projection.selectors) == ("request", "binder", "determiner", "target")
    match = index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans)[0]
    foreign = replace(match, schema_ref=base.schemas[0].schema_ref)
    assert schema_owner.relation_projection_matches(index, (foreign,)) == ()


def test_private_projection_optional_article_binding_subclass_is_rejected(runtime):
    _, index, context = _fixture(runtime, "what is the Bob?")
    slot = context_owner.licensed_query_projection_slots(index, context)[0]
    assert tuple(binding.port for binding in slot.bindings) == ("request", "binder", "determiner", "target")
    canonical = _with_slots(context, (slot,))
    assert ProposalContext.from_dict(json.loads(json.dumps(canonical.as_dict()))) == canonical

    class OptionalArticleBinding(schema_owner.QueryProjectionBinding):
        pass

    bindings = list(slot.bindings)
    article = bindings[2]
    bindings[2] = OptionalArticleBinding(article.port, article.contribution_slot_ref, article.source_unit_refs)
    values = {f.name: getattr(slot, f.name) for f in fields(slot) if f.name != "slot_ref"}
    values["bindings"] = tuple(bindings)
    with pytest.raises(ValueError, match="exact ordered binding records"):
        context_owner.QueryProjectionSlot.create(**values)


@pytest.mark.parametrize("constructor", ("create", "dataclass"), ids=("create", "dataclass"))
def test_private_projection_mutable_collection_subclass_is_rejected(runtime, constructor):
    _, index, context = _fixture(runtime)
    canonical_slots = context_owner.licensed_query_projection_slots(index, context)
    canonical = _with_slots(context, canonical_slots)

    class MutableProjectionSlots(tuple):
        active = True

        def __iter__(self):
            return super().__iter__() if self.active else iter(())

    mutable = MutableProjectionSlots(canonical_slots)
    values = {f.name: getattr(canonical, f.name) for f in fields(canonical) if f.init}
    values["query_projection_slots"] = mutable
    with pytest.raises(TypeError, match="query projection slots must be an exact tuple"):
        accepted = _with_slots(context, mutable) if constructor == "create" else ProposalContext(**values)
        # Before the repair, both constructors admitted the mutable tuple:
        # iteration changed wire content after hashing while lookup stayed live.
        assert len(accepted.as_dict()["query_projection_slots"]) == 2
        original_ref = accepted.context_ref
        mutable.active = False
        assert accepted.as_dict()["query_projection_slots"] == []
        assert accepted.context_ref == original_ref
        assert accepted.query_projection(canonical_slots[0].slot_ref) is canonical_slots[0]


def test_private_projection_accepted_long_context_ref_round_trips_detached(runtime):
    _, index, context = _fixture(runtime)
    canonical = _with_slots(context, context_owner.licensed_query_projection_slots(index, context))
    values = {f.name: getattr(canonical, f.name) for f in fields(canonical) if f.init and f.name not in {"context_ref", "abi_version"}}
    values["context_refs"] = ("session:" + "s" * 16_385,)
    accepted = ProposalContext.create(**values)
    wire = json.loads(json.dumps(accepted.as_dict()))
    assert ProposalContext.from_dict(wire) == accepted
