"""Externally signed R4 corpus-review authorization."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .r3_codec import exact_fields, exact_refs, exact_text, wire_refs

CORPUS_REVIEW_MANIFEST_ABI_VERSION = 2
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")

__all__ = [
    "CORPUS_REVIEW_MANIFEST_ABI_VERSION",
    "CorpusReviewManifest",
    "ExternalSignatureVerifier",
    "ReviewManifestVerifier",
    "ExternalReviewRequired",
]


class ExternalReviewRequired(RuntimeError):
    """Raised when independent review authorization is absent or invalid."""


@runtime_checkable
class ExternalSignatureVerifier(Protocol):
    def verify_signature(
        self,
        reviewer_ref: str,
        payload: Mapping[str, Any],
        algorithm: str,
        signature: str,
    ) -> bool:
        raise NotImplementedError


def _sha(value: object, name: str) -> str:
    text = exact_text(value, name)
    if _SHA256.fullmatch(text) is None:
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")
    return text


@dataclass(frozen=True, init=False)
class CorpusReviewManifest:
    abi_version: int
    manifest_ref: str
    scenario_source_sha256: str
    assertion_registry_sha256: str
    expected_contract_set_sha256: str
    derivation_contract_set_sha256: str
    expanded_case_set_sha256: str
    structural_sufficiency_sha256: str
    episode_set_sha256: str
    mutation_set_sha256: str
    mutation_observation_set_sha256: str
    partition_manifest_sha256s: tuple[str, ...]
    training_allowlist_sha256: str
    authority_generation: str
    abi_registry_ref: str
    source_revision: str
    reviewer_ref: str
    reviewer_policy_ref: str
    decision: str
    nonce: str
    issued_at: str
    signature_algorithm: str
    signature: str

    _FIELDS = frozenset(
        {
            "abi_version",
            "manifest_ref",
            "scenario_source_sha256",
            "assertion_registry_sha256",
            "expected_contract_set_sha256",
            "derivation_contract_set_sha256",
            "expanded_case_set_sha256",
            "structural_sufficiency_sha256",
            "episode_set_sha256",
            "mutation_set_sha256",
            "mutation_observation_set_sha256",
            "partition_manifest_sha256s",
            "training_allowlist_sha256",
            "authority_generation",
            "abi_registry_ref",
            "source_revision",
            "reviewer_ref",
            "reviewer_policy_ref",
            "decision",
            "nonce",
            "issued_at",
            "signature_algorithm",
            "signature",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use CorpusReviewManifest.create")

    @classmethod
    def create(cls, **values: Any) -> "CorpusReviewManifest":
        expected = cls._FIELDS - {"abi_version", "manifest_ref"}
        if frozenset(values) != expected:
            raise ValueError("CorpusReviewManifest create fields mismatch")
        canonical: dict[str, Any] = {}
        sha_fields = {
            "scenario_source_sha256",
            "assertion_registry_sha256",
            "expected_contract_set_sha256",
            "derivation_contract_set_sha256",
            "expanded_case_set_sha256",
            "structural_sufficiency_sha256",
            "episode_set_sha256",
            "mutation_set_sha256",
            "mutation_observation_set_sha256",
            "training_allowlist_sha256",
        }
        for name, value in values.items():
            if name == "partition_manifest_sha256s":
                rows = exact_refs(value, name, nonempty=True)
                canonical[name] = tuple(_sha(row, f"{name} item") for row in rows)
            elif name in sha_fields:
                canonical[name] = _sha(value, name)
            else:
                canonical[name] = exact_text(value, name)
        if canonical["decision"] != "approve":
            raise ValueError("review manifest decision must be approve")
        if canonical["signature_algorithm"].casefold() in {"none", "unsigned"}:
            raise ExternalReviewRequired("external cryptographic signature is required")
        if len(canonical["signature"]) < 16:
            raise ExternalReviewRequired("external signature is too short")
        material = {
            "abi_version": CORPUS_REVIEW_MANIFEST_ABI_VERSION,
            **{
                key: list(value) if type(value) is tuple else value
                for key, value in canonical.items()
            },
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", CORPUS_REVIEW_MANIFEST_ABI_VERSION)
        object.__setattr__(obj, "manifest_ref", stable_ref("corpus_review_manifest_v2", material))
        for name, value in canonical.items():
            object.__setattr__(obj, name, value)
        return obj

    def signing_payload(self) -> dict[str, Any]:
        data = self.as_dict()
        data.pop("manifest_ref")
        data.pop("signature")
        return data

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "manifest_ref": self.manifest_ref,
            "scenario_source_sha256": self.scenario_source_sha256,
            "assertion_registry_sha256": self.assertion_registry_sha256,
            "expected_contract_set_sha256": self.expected_contract_set_sha256,
            "derivation_contract_set_sha256": self.derivation_contract_set_sha256,
            "expanded_case_set_sha256": self.expanded_case_set_sha256,
            "structural_sufficiency_sha256": self.structural_sufficiency_sha256,
            "episode_set_sha256": self.episode_set_sha256,
            "mutation_set_sha256": self.mutation_set_sha256,
            "mutation_observation_set_sha256": self.mutation_observation_set_sha256,
            "partition_manifest_sha256s": list(self.partition_manifest_sha256s),
            "training_allowlist_sha256": self.training_allowlist_sha256,
            "authority_generation": self.authority_generation,
            "abi_registry_ref": self.abi_registry_ref,
            "source_revision": self.source_revision,
            "reviewer_ref": self.reviewer_ref,
            "reviewer_policy_ref": self.reviewer_policy_ref,
            "decision": self.decision,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "signature_algorithm": self.signature_algorithm,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CorpusReviewManifest":
        row = exact_fields(value, cls._FIELDS, "CorpusReviewManifest")
        if row["abi_version"] != CORPUS_REVIEW_MANIFEST_ABI_VERSION:
            raise ValueError("unsupported Corpus Review Manifest ABI")
        values = {
            key: row[key]
            for key in cls._FIELDS - {"abi_version", "manifest_ref"}
        }
        values["partition_manifest_sha256s"] = wire_refs(
            row["partition_manifest_sha256s"],
            "partition_manifest_sha256s",
            nonempty=True,
        )
        rebuilt = cls.create(**values)
        if rebuilt.manifest_ref != row["manifest_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical CorpusReviewManifest")
        return rebuilt


class ReviewManifestVerifier:
    """Verify one externally issued manifest using an injected trust root."""

    def __init__(self, verifier: ExternalSignatureVerifier) -> None:
        if callable(verifier) and not hasattr(verifier, "verify_signature"):
            raise TypeError("plain signature callback functions are forbidden")
        if not isinstance(verifier, ExternalSignatureVerifier):
            raise TypeError("verifier must implement ExternalSignatureVerifier")
        self._verifier = verifier

    def verify(self, manifest: CorpusReviewManifest) -> CorpusReviewManifest:
        if type(manifest) is not CorpusReviewManifest:
            raise TypeError("manifest must be exact CorpusReviewManifest")
        if not self._verifier.verify_signature(
            manifest.reviewer_ref,
            manifest.signing_payload(),
            manifest.signature_algorithm,
            manifest.signature,
        ):
            raise ExternalReviewRequired("external review signature verification failed")
        return manifest
