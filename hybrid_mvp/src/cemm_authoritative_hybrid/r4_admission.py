"""Fail-closed R4 artifact graph and external-review admission verification.

This module is admission-only infrastructure.  It never signs a review and it
contains no trust root.  The operator must supply an external verifier object
and an independently pinned SHA-256 for the verifier module.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, TypeVar

from .r4_contracts import AssertionRegistry, ExpectedCycleContract, ExpectedDerivationContract
from .r4_episodes import AuthenticEpisode
from .r4_expansion import ExpandedCase
from .r4_mutations import MutationObservation, SemanticMutation
from .r4_partitions import AXES, PartitionAxisManifest, TrainingAllowlist
from .r4_pipeline import (
    ApprovedR4Build,
    R4BuildReceipt,
    R4BuildResult,
    load_reviewed_scenarios,
)
from .r4_review import CorpusReviewManifest, ReviewManifestVerifier
from .r4_sufficiency import StructuralSufficiencyReceipt

__all__ = ["R4AdmissionError", "verify_r4_admission"]


class R4AdmissionError(ValueError):
    """Raised when committed R4 evidence cannot be independently reconstructed."""


T = TypeVar("T")


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise R4AdmissionError(f"value is not canonical JSON: {exc}") from exc


def _sha(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _content_ref(kind: str, value: object) -> str:
    return f"{kind}:{hashlib.sha256(_canonical_json(value)).hexdigest()[:24]}"


def _strict_json(raw: bytes, *, label: str) -> object:
    if not raw:
        raise R4AdmissionError(f"{label} is empty")

    def pairs(rows: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in rows:
            if key in result:
                raise R4AdmissionError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise R4AdmissionError(f"{label} contains non-finite JSON constant {value}")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    except R4AdmissionError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise R4AdmissionError(f"{label} is not strict UTF-8 JSON") from exc


def _load_json(path: Path, decoder: Callable[[Mapping[str, Any]], T], *, canonical_bytes: bool = True) -> T:
    raw = path.read_bytes()
    value = _strict_json(raw, label=path.as_posix())
    if type(value) is not dict:
        raise R4AdmissionError(f"{path.as_posix()} must contain one JSON object")
    if canonical_bytes and raw != _canonical_json(value) + b"\n":
        raise R4AdmissionError(f"{path.as_posix()} is not canonical JSON bytes")
    try:
        return decoder(value)
    except (TypeError, ValueError) as exc:
        raise R4AdmissionError(f"{path.as_posix()} failed canonical ABI decoding: {exc}") from exc


def _load_jsonl(
    path: Path,
    decoder: Callable[[Mapping[str, Any]], T],
    *,
    allow_empty: bool = False,
) -> tuple[T, ...]:
    raw = path.read_bytes()
    if raw == b"\n" and allow_empty:
        return ()
    if not raw or not raw.endswith(b"\n"):
        raise R4AdmissionError(f"{path.as_posix()} must be LF-terminated JSONL")
    rows: list[T] = []
    canonical_lines: list[bytes] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line:
            raise R4AdmissionError(f"{path.as_posix()} contains blank line {number}")
        value = _strict_json(line, label=f"{path.as_posix()}:{number}")
        if type(value) is not dict:
            raise R4AdmissionError(f"{path.as_posix()}:{number} must be an object")
        encoded = _canonical_json(value)
        if line != encoded:
            raise R4AdmissionError(f"{path.as_posix()}:{number} is not canonical JSON")
        canonical_lines.append(encoded)
        try:
            rows.append(decoder(value))
        except (TypeError, ValueError) as exc:
            raise R4AdmissionError(
                f"{path.as_posix()}:{number} failed canonical ABI decoding: {exc}"
            ) from exc
    if raw != b"\n".join(canonical_lines) + b"\n":
        raise R4AdmissionError(f"{path.as_posix()} JSONL bytes are non-canonical")
    return tuple(rows)


def _rows_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    material = tuple(dict(row) for row in rows)
    return _sha(b"\n".join(_canonical_json(row) for row in material) + b"\n")


def _assertion_registry_hash() -> str:
    material = {
        kind: {
            "required": sorted(spec.required),
            "optional": sorted(spec.optional),
            "family": spec.family,
        }
        for kind, spec in AssertionRegistry.SPECS.items()
    }
    return _sha(_canonical_json(material))


def _load_external_verifier(spec: str, expected_sha256: str):
    if type(spec) is not str or spec.count(":") != 1:
        raise R4AdmissionError("external verifier spec must be module:attribute")
    if type(expected_sha256) is not str or len(expected_sha256) != 64:
        raise R4AdmissionError("external verifier SHA-256 must be 64 lowercase hex")
    try:
        int(expected_sha256, 16)
    except ValueError as exc:
        raise R4AdmissionError("external verifier SHA-256 is not lowercase hex") from exc
    if expected_sha256 != expected_sha256.lower():
        raise R4AdmissionError("external verifier SHA-256 must be lowercase")
    module_name, attribute_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    source_path_text = inspect.getsourcefile(module) or getattr(module, "__file__", None)
    if not source_path_text:
        raise R4AdmissionError("external verifier module has no inspectable source file")
    source_path = Path(source_path_text).resolve(strict=True)
    if not source_path.is_file():
        raise R4AdmissionError("external verifier source is not a regular file")
    actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise R4AdmissionError("external verifier source hash differs from pinned hash")
    candidate = getattr(module, attribute_name, None)
    if candidate is None:
        raise R4AdmissionError("external verifier attribute does not exist")
    if not hasattr(candidate, "verify_signature"):
        if not callable(candidate):
            raise R4AdmissionError("external verifier attribute is neither owner nor factory")
        candidate = candidate()
    verifier = ReviewManifestVerifier(candidate)
    verifier_ref = _content_ref(
        "external_review_verifier",
        {"spec": spec, "sha256": actual_sha256},
    )
    return verifier, verifier_ref, actual_sha256


def verify_r4_admission(
    root: str | Path,
    *,
    expected_source_revision: str,
    expected_authority_generation: str,
    verifier_spec: str,
    verifier_sha256: str,
) -> dict[str, object]:
    project = Path(root).resolve(strict=True)
    artifacts = project / "artifacts" / "r4"
    scenarios_path = project / "data" / "scenarios" / "use_cases.jsonl"
    review_path = project / "data" / "review" / "R4_REVIEW_MANIFEST.json"

    contracts = _load_jsonl(artifacts / "expected_contracts.jsonl", ExpectedCycleContract.from_dict)
    derivations = _load_jsonl(
        artifacts / "expected_derivations.jsonl",
        ExpectedDerivationContract.from_dict,
        allow_empty=True,
    )
    cases = _load_jsonl(artifacts / "expanded_cases.jsonl", ExpandedCase.from_dict)
    episodes = _load_jsonl(artifacts / "episodes.jsonl", AuthenticEpisode.from_dict)
    mutations = _load_jsonl(artifacts / "mutations.jsonl", SemanticMutation.from_dict)
    observations = _load_jsonl(
        artifacts / "mutation_observations.jsonl", MutationObservation.from_dict
    )
    sufficiency = _load_json(
        artifacts / "structural_sufficiency.json", StructuralSufficiencyReceipt.from_dict
    )
    manifests = tuple(
        _load_json(
            artifacts / "partitions" / f"{axis}.json", PartitionAxisManifest.from_dict
        )
        for axis in AXES
    )
    allowlist = _load_json(
        artifacts / "training_allowlist.json", TrainingAllowlist.from_dict
    )
    receipt = _load_json(artifacts / "BUILD_RECEIPT.json", R4BuildReceipt.from_dict)
    # A reviewer is free to choose JSON whitespace; semantic canonicalization is
    # enforced by CorpusReviewManifest.from_dict and its content identity.
    manifest = _load_json(review_path, CorpusReviewManifest.from_dict, canonical_bytes=False)

    if not contracts or not cases or not episodes:
        raise R4AdmissionError("R4 corpus evidence is empty")
    if tuple(row.axis for row in manifests) != AXES:
        raise R4AdmissionError("partition manifest axes are incomplete or misordered")
    if any(not row.comparison.passed for row in episodes):
        raise R4AdmissionError("R4 contains an authentic episode mismatch")
    if any(not row.passed for row in observations):
        raise R4AdmissionError("R4 contains a mutation observation mismatch")
    if not sufficiency.passed:
        raise R4AdmissionError("R4 structural sufficiency is not passed")
    if receipt.source_revision != expected_source_revision:
        raise R4AdmissionError("R4 build receipt is not bound to current source revision")
    if receipt.authority_generation != expected_authority_generation:
        raise R4AdmissionError("R4 build receipt is not bound to current authority generation")

    scenario_raw = scenarios_path.read_bytes()
    scenarios = load_reviewed_scenarios(scenarios_path)
    partition_hashes = tuple(
        _sha(_canonical_json(row.as_dict()))
        for row in sorted(manifests, key=lambda item: item.axis)
    )
    rebuilt = R4BuildReceipt.create(
        source_revision=receipt.source_revision,
        authority_generation=receipt.authority_generation,
        abi_registry_ref=receipt.abi_registry_ref,
        scenario_source_sha256=_sha(scenario_raw),
        assertion_registry_sha256=_assertion_registry_hash(),
        contract_set_sha256=_rows_hash(row.as_dict() for row in contracts),
        derivation_contract_set_sha256=_rows_hash(row.as_dict() for row in derivations),
        expanded_case_set_sha256=_rows_hash(row.as_dict() for row in cases),
        episode_set_sha256=_rows_hash(row.as_dict() for row in episodes),
        mutation_set_sha256=_rows_hash(row.as_dict() for row in mutations),
        mutation_observation_set_sha256=_rows_hash(row.as_dict() for row in observations),
        structural_sufficiency_sha256=_sha(_canonical_json(sufficiency.as_dict())),
        partition_manifest_sha256s=partition_hashes,
        training_allowlist_sha256=_sha(_canonical_json(allowlist.as_dict())),
        review_state="external_review_required",
    )
    if rebuilt.as_dict() != receipt.as_dict():
        raise R4AdmissionError("R4 BUILD_RECEIPT does not reconstruct from committed artifacts")

    build = R4BuildResult(
        scenarios=scenarios,
        contracts=contracts,
        derivation_contracts=derivations,
        expanded_cases=cases,
        episodes=episodes,
        mutations=mutations,
        mutation_observations=observations,
        sufficiency=sufficiency,
        partition_manifests=manifests,
        training_allowlist=allowlist,
        receipt=receipt,
    )
    verifier, verifier_ref, verifier_hash = _load_external_verifier(
        verifier_spec, verifier_sha256
    )
    approval = ApprovedR4Build.create(build=build, manifest=manifest, verifier=verifier)
    artifact_refs = tuple(
        sorted(
            (
                receipt.receipt_ref,
                manifest.manifest_ref,
                approval.approval_ref,
                *(row.contract_ref for row in contracts),
                *(row.case_ref for row in cases),
                *(row.episode_ref for row in episodes),
                *(row.mutation_ref for row in mutations),
                *(row.observation_ref for row in observations),
                *(row.manifest_ref for row in manifests),
                allowlist.allowlist_ref,
                sufficiency.receipt_ref,
            )
        )
    )
    material: dict[str, object] = {
        "schema": "cemm-r4-artifact-review-step-report-v1",
        "artifact_count": len(artifact_refs),
        "artifact_set_ref": _content_ref("r4_admission_artifact_set", list(artifact_refs)),
        "build_receipt_ref": receipt.receipt_ref,
        "review_manifest_ref": manifest.manifest_ref,
        "approval_ref": approval.approval_ref,
        "reviewer_ref": manifest.reviewer_ref,
        "verifier_ref": verifier_ref,
        "verifier_sha256": verifier_hash,
        "source_revision": receipt.source_revision,
        "authority_generation": receipt.authority_generation,
    }
    material["integrity_ref"] = _content_ref("r4_artifact_review", material)
    return material
