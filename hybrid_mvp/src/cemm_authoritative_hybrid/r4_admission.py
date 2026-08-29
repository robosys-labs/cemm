"""Fail-closed R4 historical and ABI 4 candidate reconstruction."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping, TypeVar

from .canonical import stable_ref
from .r4_contracts import AssertionRegistry, ExpectedCycleContract, ExpectedDerivationContract
from .r4_episodes import AuthenticEpisode
from .r4_expansion import ExpandedCase
from .r4_mutations import MutationObservation, SemanticMutation
from .r4_partition_config import R4PartitionConfig
from .r4_partition_contracts import (
    PURPOSE_BY_SPLIT,
    SPLITS,
    ClassCount,
    DimensionSufficiency,
    LabelCount,
    PartitionEvidence,
    R4ClassAuthorization,
    R4ClassCapability,
    R4PartitionSufficiencyReceipt,
    R4SplitManifest,
    SplitClassRecord,
    artifact_graph_ref_for,
)
from .r4_partition_verify import verify_partition_assignment
from .r4_partitions import AXES, PartitionAxisManifest, TrainingAllowlist
from .r4_pipeline import R4BuildReceipt, load_reviewed_scenarios
from .r4_sufficiency import StructuralSufficiencyReceipt

__all__ = ["R4AdmissionError", "verify_r4_admission"]

_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
_MAX_JSONL_ROWS = 10_000
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_REVISION_RE = re.compile(r"[0-9a-f]{40}\Z")

_ABI4_INVENTORY = frozenset(
    {
        "BUILD_RECEIPT.json",
        "authorizations/train.json",
        "capabilities/train.json",
        "episodes.jsonl",
        "expanded_cases.jsonl",
        "expected_contracts.jsonl",
        "expected_derivations.jsonl",
        "mutation_observations.jsonl",
        "mutations.jsonl",
        "partition_evidence.json",
        "partition_sufficiency.json",
        "split_manifest.json",
        "splits/train.jsonl",
        "splits/selection.jsonl",
        "splits/calibration.jsonl",
        "splits/frozen_test.jsonl",
        "structural_sufficiency.json",
    }
)

_ABI3_RECEIPT_FIELDS = frozenset(
    {
        "abi_version",
        "receipt_ref",
        "source_revision",
        "authority_generation",
        "abi_registry_ref",
        "scenario_source_sha256",
        "assertion_registry_sha256",
        "contract_set_sha256",
        "derivation_contract_set_sha256",
        "expanded_case_set_sha256",
        "episode_set_sha256",
        "mutation_set_sha256",
        "mutation_observation_set_sha256",
        "structural_sufficiency_sha256",
        "partition_manifest_sha256s",
        "training_allowlist_sha256",
        "admission_state",
    }
)


class R4AdmissionError(ValueError):
    """Raised when R4 evidence cannot be independently reconstructed."""


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


def _sha_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _content_ref(kind: str, value: object) -> str:
    return f"{kind}:{hashlib.sha256(_canonical_json(value)).hexdigest()[:24]}"


def _read_bounded(path: Path, *, maximum: int = _MAX_ARTIFACT_BYTES) -> bytes:
    try:
        size = path.stat().st_size
        if size < 0 or size > maximum:
            raise R4AdmissionError(f"artifact exceeds byte bound: {path.as_posix()}")
        with path.open("rb") as handle:
            raw = handle.read(maximum + 1)
    except R4AdmissionError:
        raise
    except OSError as exc:
        raise R4AdmissionError(f"cannot read artifact: {path.as_posix()}") from exc
    if len(raw) != size or len(raw) > maximum:
        raise R4AdmissionError(f"artifact changed while reading: {path.as_posix()}")
    return raw


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


def _load_json_raw(
    path: Path,
    decoder: Callable[[Mapping[str, Any]], T],
) -> tuple[T, bytes]:
    raw = _read_bounded(path)
    value = _strict_json(raw, label=path.as_posix())
    if type(value) is not dict:
        raise R4AdmissionError(f"{path.as_posix()} must contain one JSON object")
    if raw != _canonical_json(value) + b"\n":
        raise R4AdmissionError(f"{path.as_posix()} is not canonical JSON bytes")
    try:
        decoded = decoder(value)
    except (TypeError, ValueError) as exc:
        raise R4AdmissionError(f"{path.as_posix()} failed canonical ABI decoding: {exc}") from exc
    return decoded, raw


def _load_json(
    path: Path,
    decoder: Callable[[Mapping[str, Any]], T],
) -> T:
    return _load_json_raw(path, decoder)[0]


def _load_jsonl_raw(
    path: Path,
    decoder: Callable[[Mapping[str, Any]], T],
    *,
    allow_empty: bool = False,
) -> tuple[tuple[T, ...], bytes]:
    raw = _read_bounded(path)
    if raw == b"\n" and allow_empty:
        return (), raw
    if not raw or not raw.endswith(b"\n"):
        raise R4AdmissionError(f"{path.as_posix()} must be LF-terminated JSONL")
    lines = raw.splitlines()
    if len(lines) > _MAX_JSONL_ROWS:
        raise R4AdmissionError(f"{path.as_posix()} exceeds row-count bound")
    rows: list[T] = []
    canonical_lines: list[bytes] = []
    for number, line in enumerate(lines, 1):
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
    return tuple(rows), raw


def _load_jsonl(
    path: Path,
    decoder: Callable[[Mapping[str, Any]], T],
    *,
    allow_empty: bool = False,
) -> tuple[T, ...]:
    return _load_jsonl_raw(path, decoder, allow_empty=allow_empty)[0]


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


def _exact_receipt_wire(path: Path) -> tuple[dict[str, object], bytes]:
    raw = _read_bounded(path)
    value = _strict_json(raw, label=path.as_posix())
    if type(value) is not dict:
        raise R4AdmissionError("R4 Build Receipt must be one JSON object")
    if raw != _canonical_json(value) + b"\n":
        raise R4AdmissionError("R4 Build Receipt bytes are non-canonical")
    return value, raw


def _decode_historical_v3(value: Mapping[str, object]) -> dict[str, object]:
    if frozenset(value) != _ABI3_RECEIPT_FIELDS:
        raise R4AdmissionError("historical R4 ABI 3 receipt fields are not exact")
    row = dict(value)
    if row["abi_version"] != 3 or row["admission_state"] != "candidate":
        raise R4AdmissionError("historical R4 receipt is not ABI 3 candidate evidence")
    source_revision = row["source_revision"]
    if type(source_revision) is not str or _REVISION_RE.fullmatch(source_revision) is None:
        raise R4AdmissionError("historical R4 source revision is malformed")
    for name in (
        "scenario_source_sha256",
        "assertion_registry_sha256",
        "contract_set_sha256",
        "derivation_contract_set_sha256",
        "expanded_case_set_sha256",
        "episode_set_sha256",
        "mutation_set_sha256",
        "mutation_observation_set_sha256",
        "structural_sufficiency_sha256",
        "training_allowlist_sha256",
    ):
        item = row[name]
        if type(item) is not str or _SHA_RE.fullmatch(item) is None:
            raise R4AdmissionError(f"historical R4 {name} is malformed")
    manifests = row["partition_manifest_sha256s"]
    if type(manifests) is not list or len(manifests) != len(AXES):
        raise R4AdmissionError("historical R4 partition hash list is malformed")
    if any(type(item) is not str or _SHA_RE.fullmatch(item) is None for item in manifests):
        raise R4AdmissionError("historical R4 partition hash is malformed")
    material = {key: row[key] for key in row if key != "receipt_ref"}
    expected_ref = stable_ref("r4_build_v3", material)
    if row["receipt_ref"] != expected_ref:
        raise R4AdmissionError("historical R4 Build Receipt identity is invalid")
    return row


def _base_artifacts(artifacts: Path) -> tuple[
    tuple[ExpectedCycleContract, ...],
    tuple[ExpectedDerivationContract, ...],
    tuple[ExpandedCase, ...],
    tuple[AuthenticEpisode, ...],
    tuple[SemanticMutation, ...],
    tuple[MutationObservation, ...],
    StructuralSufficiencyReceipt,
]:
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
    if not contracts or not cases or not episodes:
        raise R4AdmissionError("R4 corpus evidence is empty")
    if any(not row.comparison.passed for row in episodes):
        raise R4AdmissionError("R4 contains an authentic episode mismatch")
    if any(not row.passed for row in observations):
        raise R4AdmissionError("R4 contains a mutation observation mismatch")
    if not sufficiency.passed:
        raise R4AdmissionError("R4 structural sufficiency is not passed")
    return contracts, derivations, cases, episodes, mutations, observations, sufficiency


def _verify_historical_v3(
    *,
    project: Path,
    artifacts: Path,
    receipt_wire: Mapping[str, object],
    expected_source_revision: str,
    expected_authority_generation: str,
) -> dict[str, object]:
    receipt = _decode_historical_v3(receipt_wire)
    if receipt["source_revision"] != expected_source_revision:
        raise R4AdmissionError("historical R4 receipt is not bound to expected source revision")
    if receipt["authority_generation"] != expected_authority_generation:
        raise R4AdmissionError("historical R4 receipt is not bound to current authority generation")
    contracts, derivations, cases, episodes, mutations, observations, sufficiency = _base_artifacts(artifacts)
    manifests = tuple(
        _load_json(
            artifacts / "partitions" / f"{axis}.json", PartitionAxisManifest.from_dict
        )
        for axis in AXES
    )
    allowlist = _load_json(artifacts / "training_allowlist.json", TrainingAllowlist.from_dict)
    if tuple(row.axis for row in manifests) != AXES:
        raise R4AdmissionError("historical partition manifest axes are incomplete or misordered")
    scenarios_path = project / "data" / "scenarios" / "use_cases.jsonl"
    load_reviewed_scenarios(scenarios_path)
    partition_hashes = [
        _sha(_canonical_json(row.as_dict()))
        for row in sorted(manifests, key=lambda item: item.axis)
    ]
    rebuilt: dict[str, object] = {
        "abi_version": 3,
        "source_revision": receipt["source_revision"],
        "authority_generation": receipt["authority_generation"],
        "abi_registry_ref": receipt["abi_registry_ref"],
        "scenario_source_sha256": _sha(scenarios_path.read_bytes()),
        "assertion_registry_sha256": _assertion_registry_hash(),
        "contract_set_sha256": _rows_hash(row.as_dict() for row in contracts),
        "derivation_contract_set_sha256": _rows_hash(row.as_dict() for row in derivations),
        "expanded_case_set_sha256": _rows_hash(row.as_dict() for row in cases),
        "episode_set_sha256": _rows_hash(row.as_dict() for row in episodes),
        "mutation_set_sha256": _rows_hash(row.as_dict() for row in mutations),
        "mutation_observation_set_sha256": _rows_hash(row.as_dict() for row in observations),
        "structural_sufficiency_sha256": _sha(_canonical_json(sufficiency.as_dict())),
        "partition_manifest_sha256s": partition_hashes,
        "training_allowlist_sha256": _sha(_canonical_json(allowlist.as_dict())),
        "admission_state": "candidate",
    }
    rebuilt["receipt_ref"] = stable_ref("r4_build_v3", rebuilt)
    if rebuilt != receipt:
        raise R4AdmissionError("historical R4 Build Receipt does not reconstruct")
    artifact_refs = tuple(
        sorted(
            (
                str(receipt["receipt_ref"]),
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
    return _report(
        artifact_refs=artifact_refs,
        build_receipt_ref=str(receipt["receipt_ref"]),
        source_revision=str(receipt["source_revision"]),
        authority_generation=str(receipt["authority_generation"]),
        abi_version=3,
    )


def _expected_partition_sufficiency(
    evidence: PartitionEvidence,
    config: R4PartitionConfig,
) -> R4PartitionSufficiencyReceipt:
    members_by_split = {
        split: {
            member
            for component in evidence.components
            if component.split == split
            for member in component.member_refs
        }
        for split in SPLITS
    }
    components_by_split = {
        split: tuple(row for row in evidence.components if row.split == split)
        for split in SPLITS
    }
    class_counts = tuple(
        ClassCount.create(
            split=split,
            source_count=len(members_by_split[split]),
            component_count=len(components_by_split[split]),
        )
        for split in SPLITS
    )
    labels = {row.label_ref: row for row in evidence.labels}
    minima = {(row.dimension_ref, row.split): row.minimum for row in config.minima}
    maxima = {(row.dimension_ref, row.split): row.maximum for row in config.maxima}
    component_members = [frozenset(row.member_refs) for row in evidence.components]
    rows: list[DimensionSufficiency] = []
    for dimension_ref in sorted({row.dimension_ref for row in config.minima}):
        label = labels.get(dimension_ref)
        if label is None:
            raise R4AdmissionError(f"configured dimension missing from evidence: {dimension_ref}")
        label_members = frozenset(label.member_refs)
        for split in SPLITS:
            observed = len(label_members.intersection(members_by_split[split]))
            lower = minima[(dimension_ref, split)]
            upper = maxima[(dimension_ref, split)]
            passed = lower <= observed <= upper
            rows.append(
                DimensionSufficiency.create(
                    dimension_ref=dimension_ref,
                    split=split,
                    source_support=len(label_members),
                    feasible_component_support=sum(
                        bool(label_members.intersection(members)) for members in component_members
                    ),
                    observed_support=observed,
                    minimum=lower,
                    maximum=upper,
                    passed=passed,
                    infeasibility_reason="" if passed else "configured_bound_violation",
                )
            )
    return R4PartitionSufficiencyReceipt.create(
        passed=all(row.passed for row in rows),
        class_counts=class_counts,
        dimension_rows=tuple(rows),
    )


def _candidate_inventory(artifacts: Path) -> frozenset[str]:
    actual: set[str] = set()
    for path in artifacts.rglob("*"):
        if path.is_symlink():
            raise R4AdmissionError(f"candidate contains symlink: {path.as_posix()}")
        if path.is_file():
            relative = path.relative_to(artifacts).as_posix()
            if any(part in {"", ".", ".."} for part in Path(relative).parts):
                raise R4AdmissionError("candidate artifact path is non-canonical")
            actual.add(relative)
    return frozenset(actual)


def _verify_candidate_v4(
    *,
    project: Path,
    artifacts: Path,
    receipt_wire: Mapping[str, object],
    expected_source_revision: str,
    expected_authority_generation: str,
) -> dict[str, object]:
    inventory = _candidate_inventory(artifacts)
    if inventory != _ABI4_INVENTORY:
        raise R4AdmissionError(
            f"ABI 4 candidate inventory mismatch; missing={sorted(_ABI4_INVENTORY - inventory)}, "
            f"extra={sorted(inventory - _ABI4_INVENTORY)}"
        )
    if (artifacts / "partitions").exists() or (artifacts / "training_allowlist.json").exists():
        raise R4AdmissionError("ABI 4 candidate contains retired partition authority")

    try:
        receipt = R4BuildReceipt.from_dict(receipt_wire)
    except (TypeError, ValueError) as exc:
        raise R4AdmissionError(f"ABI 4 Build Receipt failed decoding: {exc}") from exc
    if receipt.source_revision != expected_source_revision:
        raise R4AdmissionError("ABI 4 Build Receipt source revision differs from expected source")
    if receipt.authority_generation != expected_authority_generation:
        raise R4AdmissionError("ABI 4 Build Receipt authority generation differs from expected authority")

    contracts, derivations, cases, episodes, mutations, observations, structural = _base_artifacts(artifacts)
    evidence, evidence_raw = _load_json_raw(artifacts / "partition_evidence.json", PartitionEvidence.from_dict)
    partition_sufficiency, partition_sufficiency_raw = _load_json_raw(
        artifacts / "partition_sufficiency.json", R4PartitionSufficiencyReceipt.from_dict
    )
    manifest, manifest_raw = _load_json_raw(artifacts / "split_manifest.json", R4SplitManifest.from_dict)
    capability, capability_raw = _load_json_raw(
        artifacts / "capabilities" / "train.json", R4ClassCapability.from_dict
    )
    authorization, authorization_raw = _load_json_raw(
        artifacts / "authorizations" / "train.json", R4ClassAuthorization.from_dict
    )
    config = R4PartitionConfig.from_json_bytes((project / "configs" / "r4_partitions.json").read_bytes())

    try:
        verify_partition_assignment(
            episodes,
            mutations=mutations,
            config=config,
            evidence=evidence,
        )
    except (TypeError, ValueError) as exc:
        raise R4AdmissionError(f"independent partition assignment verification failed: {exc}") from exc

    expected_sufficiency = _expected_partition_sufficiency(evidence, config)
    if partition_sufficiency != expected_sufficiency or not partition_sufficiency.passed:
        raise R4AdmissionError("partition sufficiency does not independently reconstruct")

    episode_by_ref = {row.episode_ref: row for row in episodes}
    evidence_owner = {
        member: component.split
        for component in evidence.components
        for member in component.member_refs
    }
    if set(evidence_owner) != set(episode_by_ref):
        raise R4AdmissionError("partition evidence does not exactly cover authentic episodes")

    expected_classes: list[SplitClassRecord] = []
    split_hashes: list[str] = []
    payload_refs: set[str] = set()
    labels = tuple(evidence.labels)
    for split in SPLITS:
        payload_path = artifacts / "splits" / f"{split}.jsonl"
        payload_rows, payload_raw = _load_jsonl_raw(payload_path, AuthenticEpisode.from_dict)
        refs = tuple(row.episode_ref for row in payload_rows)
        if not refs or refs != tuple(sorted(refs)):
            raise R4AdmissionError(f"{split} payload must be nonempty and sorted by episode_ref")
        if payload_refs.intersection(refs):
            raise R4AdmissionError("split payloads overlap")
        payload_refs.update(refs)
        expected_refs = tuple(sorted(ref for ref, owner in evidence_owner.items() if owner == split))
        if refs != expected_refs:
            raise R4AdmissionError(f"{split} payload membership differs from partition evidence")
        if any(episode_by_ref[row.episode_ref] != row for row in payload_rows):
            raise R4AdmissionError(f"{split} payload row differs from authenticated episode")
        components = tuple(row for row in evidence.components if row.split == split)
        label_counts = tuple(
            LabelCount.create(
                label_ref=label.label_ref,
                count=len(set(label.member_refs).intersection(refs)),
            )
            for label in labels
            if set(label.member_refs).intersection(refs)
        )
        expected_classes.append(
            SplitClassRecord.create(
                split=split,
                purpose=PURPOSE_BY_SPLIT[split],
                payload_path=f"artifacts/r4/splits/{split}.jsonl",
                payload_sha256=_sha_hex(payload_raw),
                payload_count=len(refs),
                member_refs=refs,
                component_refs=tuple(sorted(row.component_ref for row in components)),
                label_counts=label_counts,
            )
        )
        split_hashes.append(_sha(payload_raw))
    if payload_refs != set(episode_by_ref):
        raise R4AdmissionError("split payloads are not exhaustive")

    expected_manifest = R4SplitManifest.create(
        source_set_ref=evidence.source_set_ref,
        generator_source_revision=expected_source_revision,
        authority_generation=expected_authority_generation,
        config_ref=config.config_ref,
        partition_evidence_ref=evidence.evidence_ref,
        partition_sufficiency_ref=partition_sufficiency.receipt_ref,
        classes=tuple(expected_classes),
    )
    if manifest != expected_manifest:
        raise R4AdmissionError("global split manifest does not independently reconstruct")
    train_class = expected_classes[0]
    expected_capability = R4ClassCapability.create(
        purpose="training",
        split="train",
        payload_path=train_class.payload_path,
        payload_sha256=train_class.payload_sha256,
        payload_count=train_class.payload_count,
        source_set_ref=evidence.source_set_ref,
        split_manifest_ref=manifest.manifest_ref,
    )
    if capability != expected_capability:
        raise R4AdmissionError("train capability differs from global manifest ancestry")
    expected_authorization = R4ClassAuthorization.create(
        purpose="training",
        expected_capability_ref=capability.capability_ref,
        expected_capability_sha256=_sha_hex(capability_raw),
        artifact_graph_ref=artifact_graph_ref_for(
            source_set_ref=evidence.source_set_ref,
            config_ref=config.config_ref,
            partition_evidence_ref=evidence.evidence_ref,
            partition_sufficiency_ref=partition_sufficiency.receipt_ref,
            split_manifest_ref=manifest.manifest_ref,
            capability_ref=capability.capability_ref,
        ),
        generator_source_revision=expected_source_revision,
        authority_generation=expected_authority_generation,
    )
    if authorization != expected_authorization:
        raise R4AdmissionError("train authorization differs from global artifact ancestry")

    scenarios_path = project / "data" / "scenarios" / "use_cases.jsonl"
    load_reviewed_scenarios(scenarios_path)
    rebuilt = R4BuildReceipt.create(
        source_revision=expected_source_revision,
        authority_generation=expected_authority_generation,
        abi_registry_ref=receipt.abi_registry_ref,
        scenario_source_sha256=_sha(scenarios_path.read_bytes()),
        assertion_registry_sha256=_assertion_registry_hash(),
        contract_set_sha256=_rows_hash(row.as_dict() for row in contracts),
        derivation_contract_set_sha256=_rows_hash(row.as_dict() for row in derivations),
        expanded_case_set_sha256=_rows_hash(row.as_dict() for row in cases),
        episode_set_sha256=_rows_hash(row.as_dict() for row in episodes),
        mutation_set_sha256=_rows_hash(row.as_dict() for row in mutations),
        mutation_observation_set_sha256=_rows_hash(row.as_dict() for row in observations),
        structural_sufficiency_sha256=_sha(_canonical_json(structural.as_dict())),
        partition_evidence_sha256=_sha(evidence_raw),
        split_manifest_sha256=_sha(manifest_raw),
        partition_sufficiency_sha256=_sha(partition_sufficiency_raw),
        split_payload_sha256s=tuple(split_hashes),
        train_capability_sha256=_sha(capability_raw),
        train_authorization_sha256=_sha(authorization_raw),
        admission_state="candidate",
    )
    if rebuilt != receipt:
        raise R4AdmissionError("ABI 4 Build Receipt does not reconstruct from candidate artifacts")

    artifact_refs = tuple(
        sorted(
            (
                receipt.receipt_ref,
                *(row.contract_ref for row in contracts),
                *(row.case_ref for row in cases),
                *(row.episode_ref for row in episodes),
                *(row.mutation_ref for row in mutations),
                *(row.observation_ref for row in observations),
                structural.receipt_ref,
                evidence.evidence_ref,
                *(row.component_ref for row in evidence.components),
                partition_sufficiency.receipt_ref,
                manifest.manifest_ref,
                capability.capability_ref,
                authorization.authorization_ref,
            )
        )
    )
    return _report(
        artifact_refs=artifact_refs,
        build_receipt_ref=receipt.receipt_ref,
        source_revision=receipt.source_revision,
        authority_generation=receipt.authority_generation,
        abi_version=4,
    )


def _report(
    *,
    artifact_refs: tuple[str, ...],
    build_receipt_ref: str,
    source_revision: str,
    authority_generation: str,
    abi_version: int,
) -> dict[str, object]:
    material: dict[str, object] = {
        "schema": "cemm-r4-artifact-integrity-step-report-v1",
        "artifact_count": len(artifact_refs),
        "artifact_set_ref": _content_ref("r4_admission_artifact_set", list(artifact_refs)),
        "build_receipt_ref": build_receipt_ref,
        "build_receipt_abi_version": abi_version,
        "source_revision": source_revision,
        "authority_generation": authority_generation,
    }
    material["integrity_ref"] = _content_ref("r4_artifact_integrity", material)
    return material


def verify_r4_admission(
    root: str | Path,
    *,
    expected_source_revision: str,
    expected_authority_generation: str,
    candidate_root: str | Path | None = None,
) -> dict[str, object]:
    """Reconstruct historical ABI 3 evidence or an explicit/current ABI 4 tree.

    ``candidate_root`` is injection-only Task 6 evidence.  If supplied it must
    be ABI 4; historical ABI 3 is accepted only from the repository's current
    checked-in ``artifacts/r4`` path until the evidence policy is switched by
    the later reconciliation task.
    """
    if type(expected_source_revision) is not str or _REVISION_RE.fullmatch(expected_source_revision) is None:
        raise R4AdmissionError("expected source revision must be an exact 40-character Git SHA")
    if type(expected_authority_generation) is not str or not expected_authority_generation:
        raise R4AdmissionError("expected authority generation must be nonempty text")
    project = Path(root).resolve(strict=True)
    if candidate_root is None:
        artifacts = (project / "artifacts" / "r4").resolve(strict=True)
    else:
        artifacts = Path(candidate_root).resolve(strict=True)
        if artifacts == (project / "artifacts" / "r4").resolve():
            raise R4AdmissionError("candidate_root must be an explicitly separate temporary tree")
    receipt_wire, _ = _exact_receipt_wire(artifacts / "BUILD_RECEIPT.json")
    abi_version = receipt_wire.get("abi_version")
    if candidate_root is not None and abi_version != 4:
        raise R4AdmissionError("explicit candidate roots must use R4 Build Receipt ABI 4")
    if abi_version == 4:
        return _verify_candidate_v4(
            project=project,
            artifacts=artifacts,
            receipt_wire=receipt_wire,
            expected_source_revision=expected_source_revision,
            expected_authority_generation=expected_authority_generation,
        )
    if abi_version == 3 and candidate_root is None:
        return _verify_historical_v3(
            project=project,
            artifacts=artifacts,
            receipt_wire=receipt_wire,
            expected_source_revision=expected_source_revision,
            expected_authority_generation=expected_authority_generation,
        )
    raise R4AdmissionError(f"unsupported R4 Build Receipt ABI: {abi_version!r}")
