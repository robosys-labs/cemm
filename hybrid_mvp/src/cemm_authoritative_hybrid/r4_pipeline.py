"""Deterministic R4 reviewed-data pipeline and ABI 4 candidate generation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .persistence import RevisionPin
from .r3_codec import exact_fields, exact_text
from .r4_contracts import (
    AssertionRegistry,
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ExpectedDerivationContract,
    ReviewedScenario,
)
from .r4_episodes import (
    AuthenticEpisode,
    AuthenticEpisodeBuilder,
    EpisodeExecutionOwner,
)
from .r4_expansion import CaseExpander, ExpandedCase
from .r4_mutations import (
    MutationExecutionOwner,
    MutationExecutor,
    MutationGenerator,
    MutationObservation,
    SemanticMutation,
)
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
    canonical_json_bytes,
)
from .r4_partition_verify import verify_partition_assignment
from .r4_partitions import GlobalLeakagePartitioner
from .r4_sufficiency import (
    StructuralSufficiencyEvaluator,
    StructuralSufficiencyReceipt,
)

R4_BUILD_RECEIPT_ABI_VERSION = 4
_SHA_RE = re.compile(r"sha256:[0-9a-f]{64}")
_REVISION_RE = re.compile(r"[0-9a-f]{40}")

__all__ = [
    "R4_BUILD_RECEIPT_ABI_VERSION",
    "R4BuildReceipt",
    "R4BuildResult",
    "R4Pipeline",
    "load_reviewed_scenarios",
    "write_jsonl",
]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_json_line(value: Mapping[str, Any]) -> bytes:
    return _canonical_json(dict(value)) + b"\n"


def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_bytes(raw: bytes) -> str:
    return f"sha256:{_sha256_hex(raw)}"


def _rows_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    material = tuple(dict(row) for row in rows)
    return b"" if not material else b"".join(_canonical_json_line(row) for row in material)


def _set_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    return _sha256_bytes(_rows_bytes(rows))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> str:
    raw = _rows_bytes(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return _sha256_bytes(raw)


def load_reviewed_scenarios(path: Path) -> tuple[ReviewedScenario, ...]:
    rows: list[ReviewedScenario] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if type(value) is not dict:
            raise TypeError(f"scenario line {line_number} is not an object")
        scenario = ReviewedScenario.from_dict(value)
        if scenario.review_status != "reviewed":
            raise ValueError(
                f"scenario {scenario.scenario_ref} is not marked reviewed source"
            )
        rows.append(scenario)
    if not rows:
        raise ValueError("scenario source is empty")
    refs = tuple(row.scenario_ref for row in rows)
    if len(refs) != len(set(refs)):
        raise ValueError("scenario refs must be unique")
    return tuple(rows)


def _exact_sha(value: object, name: str) -> str:
    text = exact_text(value, name, maximum=71)
    if _SHA_RE.fullmatch(text) is None:
        raise ValueError(f"{name} must be sha256:<lowercase hex>")
    return text


def _exact_split_hashes(value: object) -> tuple[str, str, str, str]:
    if type(value) is not tuple or len(value) != len(SPLITS):
        raise ValueError("split_payload_sha256s must contain exactly four canonical hashes")
    hashes = tuple(_exact_sha(item, "split_payload_sha256s item") for item in value)
    return hashes  # type: ignore[return-value]


@dataclass(frozen=True, init=False)
class R4BuildReceipt:
    abi_version: int
    receipt_ref: str
    source_revision: str
    authority_generation: str
    abi_registry_ref: str
    scenario_source_sha256: str
    assertion_registry_sha256: str
    contract_set_sha256: str
    derivation_contract_set_sha256: str
    expanded_case_set_sha256: str
    episode_set_sha256: str
    mutation_set_sha256: str
    mutation_observation_set_sha256: str
    structural_sufficiency_sha256: str
    partition_evidence_sha256: str
    split_manifest_sha256: str
    partition_sufficiency_sha256: str
    split_payload_sha256s: tuple[str, str, str, str]
    train_capability_sha256: str
    train_authorization_sha256: str
    admission_state: str

    _FIELDS = frozenset(
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
            "partition_evidence_sha256",
            "split_manifest_sha256",
            "partition_sufficiency_sha256",
            "split_payload_sha256s",
            "train_capability_sha256",
            "train_authorization_sha256",
            "admission_state",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use R4BuildReceipt.create")

    @classmethod
    def create(cls, **values: Any) -> "R4BuildReceipt":
        expected = cls._FIELDS - {"abi_version", "receipt_ref"}
        if frozenset(values) != expected:
            raise ValueError("R4BuildReceipt create fields mismatch")
        source_revision = exact_text(values["source_revision"], "source_revision", maximum=40)
        if _REVISION_RE.fullmatch(source_revision) is None:
            raise ValueError("source_revision must be a full 40-character Git SHA")
        canonical: dict[str, Any] = {
            "source_revision": source_revision,
            "authority_generation": exact_text(
                values["authority_generation"], "authority_generation", maximum=128
            ),
            "abi_registry_ref": exact_text(values["abi_registry_ref"], "abi_registry_ref"),
        }
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
            "partition_evidence_sha256",
            "split_manifest_sha256",
            "partition_sufficiency_sha256",
            "train_capability_sha256",
            "train_authorization_sha256",
        ):
            canonical[name] = _exact_sha(values[name], name)
        canonical["split_payload_sha256s"] = _exact_split_hashes(
            values["split_payload_sha256s"]
        )
        canonical["admission_state"] = exact_text(values["admission_state"], "admission_state")
        if canonical["admission_state"] != "candidate":
            raise ValueError("R4 build receipt must remain an admission candidate")
        material = {
            "abi_version": R4_BUILD_RECEIPT_ABI_VERSION,
            **{
                key: list(value) if type(value) is tuple else value
                for key, value in canonical.items()
            },
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", R4_BUILD_RECEIPT_ABI_VERSION)
        object.__setattr__(obj, "receipt_ref", stable_ref("r4_build_v4", material))
        for name, value in canonical.items():
            object.__setattr__(obj, name, value)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "receipt_ref": self.receipt_ref,
            "source_revision": self.source_revision,
            "authority_generation": self.authority_generation,
            "abi_registry_ref": self.abi_registry_ref,
            "scenario_source_sha256": self.scenario_source_sha256,
            "assertion_registry_sha256": self.assertion_registry_sha256,
            "contract_set_sha256": self.contract_set_sha256,
            "derivation_contract_set_sha256": self.derivation_contract_set_sha256,
            "expanded_case_set_sha256": self.expanded_case_set_sha256,
            "episode_set_sha256": self.episode_set_sha256,
            "mutation_set_sha256": self.mutation_set_sha256,
            "mutation_observation_set_sha256": self.mutation_observation_set_sha256,
            "structural_sufficiency_sha256": self.structural_sufficiency_sha256,
            "partition_evidence_sha256": self.partition_evidence_sha256,
            "split_manifest_sha256": self.split_manifest_sha256,
            "partition_sufficiency_sha256": self.partition_sufficiency_sha256,
            "split_payload_sha256s": list(self.split_payload_sha256s),
            "train_capability_sha256": self.train_capability_sha256,
            "train_authorization_sha256": self.train_authorization_sha256,
            "admission_state": self.admission_state,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4BuildReceipt":
        row = exact_fields(value, cls._FIELDS, "R4BuildReceipt")
        if row["abi_version"] != R4_BUILD_RECEIPT_ABI_VERSION:
            raise ValueError("unsupported R4 Build Receipt ABI")
        if type(row["split_payload_sha256s"]) is not list or len(row["split_payload_sha256s"]) != 4:
            raise ValueError("split_payload_sha256s must be the four canonical split hashes")
        values = {
            key: row[key]
            for key in cls._FIELDS - {"abi_version", "receipt_ref", "split_payload_sha256s"}
        }
        values["split_payload_sha256s"] = tuple(row["split_payload_sha256s"])
        rebuilt = cls.create(**values)
        if rebuilt.receipt_ref != row["receipt_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4BuildReceipt")
        return rebuilt

    def to_json_bytes(self) -> bytes:
        return _canonical_json_line(self.as_dict())


@dataclass(frozen=True)
class R4BuildResult:
    scenarios: tuple[ReviewedScenario, ...]
    contracts: tuple[ExpectedCycleContract, ...]
    derivation_contracts: tuple[ExpectedDerivationContract, ...]
    expanded_cases: tuple[ExpandedCase, ...]
    episodes: tuple[AuthenticEpisode, ...]
    mutations: tuple[SemanticMutation, ...]
    mutation_observations: tuple[MutationObservation, ...]
    sufficiency: StructuralSufficiencyReceipt
    partition_evidence: PartitionEvidence
    partition_sufficiency: R4PartitionSufficiencyReceipt
    split_payloads: tuple[tuple[str, bytes], ...]
    split_manifest: R4SplitManifest
    train_capability: R4ClassCapability
    train_authorization: R4ClassAuthorization
    receipt: R4BuildReceipt


class R4Pipeline:
    """Build reviewed contracts, authentic observations and four sealed classes."""

    def __init__(
        self,
        *,
        authority: Any,
        revision_pin: RevisionPin,
        abi_registry_ref: str,
        episode_owner: EpisodeExecutionOwner,
        mutation_owner: MutationExecutionOwner,
        source_revision: str,
        partition_config: R4PartitionConfig,
        minimums: Mapping[str, int] | None = None,
        maximums: Mapping[str, int] | None = None,
        strict: bool = True,
    ) -> None:
        if type(partition_config) is not R4PartitionConfig:
            raise TypeError("partition_config must be an exact R4PartitionConfig")
        self._pin = revision_pin
        self._abi_registry_ref = exact_text(abi_registry_ref, "abi_registry_ref")
        self._source_revision = exact_text(source_revision, "source_revision", maximum=40)
        if _REVISION_RE.fullmatch(self._source_revision) is None:
            raise ValueError("source_revision must be a full 40-character Git SHA")
        self._partition_config = partition_config
        self._compiler = ExpectedCycleContractCompiler(
            authority, abi_registry_ref=self._abi_registry_ref
        )
        self._expander = CaseExpander(self._compiler)
        self._episode_builder = AuthenticEpisodeBuilder(episode_owner)
        self._mutation_generator = MutationGenerator()
        self._mutation_executor = MutationExecutor(mutation_owner)
        self._sufficiency = StructuralSufficiencyEvaluator(
            minimums=minimums, maximums=maximums
        )
        self._partitioner = GlobalLeakagePartitioner()
        self._strict = bool(strict)

    def build(
        self,
        scenario_path: Path,
        *,
        derivation_contracts: Iterable[ExpectedDerivationContract] = (),
        derivation_validator: Any | None = None,
    ) -> R4BuildResult:
        scenarios = load_reviewed_scenarios(scenario_path)
        scenario_sha = _sha256_bytes(scenario_path.read_bytes())
        cases: list[ExpandedCase] = []
        for scenario in scenarios:
            metadata = dict(scenario.metadata)
            environments = metadata.get("environments", ({},))
            if isinstance(environments, list):
                environments = tuple(environments)
            if type(environments) is not tuple:
                raise TypeError("reviewed environments metadata must be a sequence")
            cases.extend(
                self._expander.expand(
                    scenario,
                    revision_pin=self._pin,
                    environments=environments,
                )
            )
        contracts = tuple(case.contract for case in cases)
        episodes = self._episode_builder.build_many(cases)
        mutations = tuple(
            mutation
            for case in cases
            for mutation in self._mutation_generator.generate(case)
        )
        observations = self._mutation_executor.execute(mutations)

        derivations = tuple(derivation_contracts)
        if any(type(row) is not ExpectedDerivationContract for row in derivations):
            raise TypeError("derivation_contracts must contain ExpectedDerivationContract")
        if derivations:
            if not callable(getattr(derivation_validator, "validate_derivation", None)):
                raise TypeError("derivations require an independent validator owner")
            by_ref = {row.contract_ref: row for row in contracts}
            for derivation in derivations:
                contract = by_ref.get(derivation.expected_contract_ref)
                if contract is None:
                    raise ValueError("derivation references unknown expected contract")
                if derivation_validator.validate_derivation(derivation, contract) is not True:
                    raise ValueError("reviewed derivation failed independent validation")

        sufficiency = self._sufficiency.evaluate(contracts, episodes=episodes)
        assignment = self._partitioner.assign(
            episodes,
            config=self._partition_config,
            mutations=mutations,
        )
        verify_partition_assignment(
            episodes,
            mutations=mutations,
            config=self._partition_config,
            evidence=assignment.evidence,
        )
        if self._strict:
            mismatches = tuple(
                row.episode_ref for row in episodes if not row.comparison.passed
            )
            mutation_mismatches = tuple(
                row.observation_ref for row in observations if not row.passed
            )
            if mismatches:
                raise ValueError(f"authentic episodes differ from reviewed truth: {mismatches[:8]}")
            if mutation_mismatches:
                raise ValueError(
                    f"mutation observations differ from reviewed labels: {mutation_mismatches[:8]}"
                )
            if not sufficiency.passed:
                raise ValueError(
                    f"structural sufficiency failed: {sufficiency.violations[:8]}"
                )

        evidence = assignment.evidence
        partition_sufficiency = _partition_sufficiency(
            evidence=evidence,
            config=self._partition_config,
        )
        if not partition_sufficiency.passed:
            raise ValueError("global partition sufficiency failed")
        episode_by_ref = {row.episode_ref: row for row in episodes}
        split_payloads = _split_payloads(evidence, episode_by_ref)
        classes = _split_classes(evidence, split_payloads)
        split_manifest = R4SplitManifest.create(
            source_set_ref=evidence.source_set_ref,
            generator_source_revision=self._source_revision,
            authority_generation=self._pin.authority_generation,
            config_ref=self._partition_config.config_ref,
            partition_evidence_ref=evidence.evidence_ref,
            partition_sufficiency_ref=partition_sufficiency.receipt_ref,
            classes=classes,
        )
        train_class = next(row for row in classes if row.split == "train")
        train_capability = R4ClassCapability.create(
            purpose="training",
            split="train",
            payload_path=train_class.payload_path,
            payload_sha256=train_class.payload_sha256,
            payload_count=train_class.payload_count,
            source_set_ref=evidence.source_set_ref,
            split_manifest_ref=split_manifest.manifest_ref,
        )
        capability_sha = _sha256_hex(train_capability.to_json_bytes())
        train_authorization = R4ClassAuthorization.create(
            purpose="training",
            expected_capability_ref=train_capability.capability_ref,
            expected_capability_sha256=capability_sha,
            artifact_graph_ref=artifact_graph_ref_for(
                source_set_ref=evidence.source_set_ref,
                config_ref=self._partition_config.config_ref,
                partition_evidence_ref=evidence.evidence_ref,
                partition_sufficiency_ref=partition_sufficiency.receipt_ref,
                split_manifest_ref=split_manifest.manifest_ref,
                capability_ref=train_capability.capability_ref,
            ),
            generator_source_revision=self._source_revision,
            authority_generation=self._pin.authority_generation,
        )

        assertion_registry_sha = _sha256_bytes(
            _canonical_json(
                {
                    kind: {
                        "required": sorted(spec.required),
                        "optional": sorted(spec.optional),
                        "family": spec.family,
                    }
                    for kind, spec in AssertionRegistry.SPECS.items()
                }
            )
        )
        receipt = R4BuildReceipt.create(
            source_revision=self._source_revision,
            authority_generation=self._pin.authority_generation,
            abi_registry_ref=self._abi_registry_ref,
            scenario_source_sha256=scenario_sha,
            assertion_registry_sha256=assertion_registry_sha,
            contract_set_sha256=_set_hash(row.as_dict() for row in contracts),
            derivation_contract_set_sha256=_set_hash(row.as_dict() for row in derivations),
            expanded_case_set_sha256=_set_hash(row.as_dict() for row in cases),
            episode_set_sha256=_set_hash(row.as_dict() for row in episodes),
            mutation_set_sha256=_set_hash(row.as_dict() for row in mutations),
            mutation_observation_set_sha256=_set_hash(row.as_dict() for row in observations),
            structural_sufficiency_sha256=_sha256_bytes(_canonical_json_line(sufficiency.as_dict())),
            partition_evidence_sha256=_sha256_bytes(evidence.to_json_bytes()),
            split_manifest_sha256=_sha256_bytes(split_manifest.to_json_bytes()),
            partition_sufficiency_sha256=_sha256_bytes(partition_sufficiency.to_json_bytes()),
            split_payload_sha256s=tuple(
                _sha256_bytes(raw) for split, raw in split_payloads if split in SPLITS
            ),
            train_capability_sha256=_sha256_bytes(train_capability.to_json_bytes()),
            train_authorization_sha256=_sha256_bytes(train_authorization.to_json_bytes()),
            admission_state="candidate",
        )
        return R4BuildResult(
            scenarios=scenarios,
            contracts=contracts,
            derivation_contracts=derivations,
            expanded_cases=tuple(cases),
            episodes=episodes,
            mutations=mutations,
            mutation_observations=observations,
            sufficiency=sufficiency,
            partition_evidence=evidence,
            partition_sufficiency=partition_sufficiency,
            split_payloads=split_payloads,
            split_manifest=split_manifest,
            train_capability=train_capability,
            train_authorization=train_authorization,
            receipt=receipt,
        )

    @staticmethod
    def write_candidate_tree(result: R4BuildResult, output_root: Path) -> tuple[Path, ...]:
        if type(result) is not R4BuildResult:
            raise TypeError("result must be exact R4BuildResult")
        output = output_root.resolve()
        if output.exists():
            raise FileExistsError(f"candidate output already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=str(output.parent))
        ).resolve()
        if staging.parent != output.parent:
            raise RuntimeError("candidate staging directory escaped output parent")
        try:
            payloads = _candidate_bytes(result)
            for relative, raw in payloads:
                _atomic_write(staging / relative, raw)
            _verify_staged_tree(result, staging, payloads)
            staging.replace(output)
            _fsync_dir(output.parent)
            return tuple(sorted((output / relative for relative, _ in payloads), key=str))
        except BaseException:
            if staging.exists() and staging.parent == output.parent and staging.name.startswith(
                f".{output.name}.staging-"
            ):
                shutil.rmtree(staging)
            raise


def _partition_sufficiency(
    *, evidence: PartitionEvidence, config: R4PartitionConfig
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
            raise ValueError(f"configured dimension missing from evidence: {dimension_ref}")
        label_members = frozenset(label.member_refs)
        source_support = len(label_members)
        feasible_component_support = sum(bool(label_members.intersection(members)) for members in component_members)
        for split in SPLITS:
            observed = len(label_members.intersection(members_by_split[split]))
            lower = minima[(dimension_ref, split)]
            upper = maxima[(dimension_ref, split)]
            passed = lower <= observed <= upper
            rows.append(
                DimensionSufficiency.create(
                    dimension_ref=dimension_ref,
                    split=split,
                    source_support=source_support,
                    feasible_component_support=feasible_component_support,
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


def _split_payloads(
    evidence: PartitionEvidence,
    episode_by_ref: Mapping[str, AuthenticEpisode],
) -> tuple[tuple[str, bytes], ...]:
    owner = {
        member: component.split
        for component in evidence.components
        for member in component.member_refs
    }
    if set(owner) != set(episode_by_ref):
        raise ValueError("partition evidence does not exactly cover authentic episodes")
    payloads: list[tuple[str, bytes]] = []
    for split in SPLITS:
        refs = tuple(sorted(ref for ref, assigned in owner.items() if assigned == split))
        if not refs:
            raise ValueError(f"partition split is empty: {split}")
        raw = _rows_bytes(episode_by_ref[ref].as_dict() for ref in refs)
        payloads.append((split, raw))
    return tuple(payloads)


def _split_classes(
    evidence: PartitionEvidence,
    payloads: tuple[tuple[str, bytes], ...],
) -> tuple[SplitClassRecord, ...]:
    classes: list[SplitClassRecord] = []
    for split, raw in payloads:
        components = tuple(row for row in evidence.components if row.split == split)
        member_refs = tuple(sorted(member for row in components for member in row.member_refs))
        label_counts = tuple(
            LabelCount.create(
                label_ref=label.label_ref,
                count=len(set(label.member_refs).intersection(member_refs)),
            )
            for label in evidence.labels
            if set(label.member_refs).intersection(member_refs)
        )
        classes.append(
            SplitClassRecord.create(
                split=split,
                purpose=PURPOSE_BY_SPLIT[split],
                payload_path=f"artifacts/r4/splits/{split}.jsonl",
                payload_sha256=_sha256_hex(raw),
                payload_count=len(member_refs),
                member_refs=member_refs,
                component_refs=tuple(sorted(row.component_ref for row in components)),
                label_counts=label_counts,
            )
        )
    return tuple(classes)


def _candidate_bytes(result: R4BuildResult) -> tuple[tuple[Path, bytes], ...]:
    split_payloads = dict(result.split_payloads)
    rows = (
        (Path("expected_contracts.jsonl"), _rows_bytes(row.as_dict() for row in result.contracts)),
        (Path("expected_derivations.jsonl"), _rows_bytes(row.as_dict() for row in result.derivation_contracts)),
        (Path("expanded_cases.jsonl"), _rows_bytes(row.as_dict() for row in result.expanded_cases)),
        (Path("episodes.jsonl"), _rows_bytes(row.as_dict() for row in result.episodes)),
        (Path("mutations.jsonl"), _rows_bytes(row.as_dict() for row in result.mutations)),
        (Path("mutation_observations.jsonl"), _rows_bytes(row.as_dict() for row in result.mutation_observations)),
        (Path("structural_sufficiency.json"), _canonical_json_line(result.sufficiency.as_dict())),
        (Path("partition_evidence.json"), result.partition_evidence.to_json_bytes()),
        (Path("partition_sufficiency.json"), result.partition_sufficiency.to_json_bytes()),
        (Path("split_manifest.json"), result.split_manifest.to_json_bytes()),
        *( (Path(f"splits/{split}.jsonl"), split_payloads[split]) for split in SPLITS ),
        (Path("capabilities/train.json"), result.train_capability.to_json_bytes()),
        (Path("authorizations/train.json"), result.train_authorization.to_json_bytes()),
        (Path("BUILD_RECEIPT.json"), result.receipt.to_json_bytes()),
    )
    return tuple(sorted(rows, key=lambda row: row[0].as_posix()))


def _atomic_write(path: Path, raw: bytes) -> None:
    if type(raw) is not bytes or len(raw) > 128 * 1024 * 1024:
        raise ValueError("candidate artifact violates byte bounds")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        _fsync_dir(path.parent)
    finally:
        if temp.exists():
            temp.unlink()


def _fsync_dir(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _verify_staged_tree(
    result: R4BuildResult,
    staging: Path,
    expected: tuple[tuple[Path, bytes], ...],
) -> None:
    expected_paths = tuple(path.as_posix() for path, _ in expected)
    actual_paths = tuple(
        sorted(path.relative_to(staging).as_posix() for path in staging.rglob("*") if path.is_file())
    )
    if actual_paths != expected_paths:
        raise ValueError("candidate tree path inventory mismatch")
    expected_by_path = dict(expected)
    for relative, raw in expected:
        observed = (staging / relative).read_bytes()
        if observed != raw:
            raise ValueError(f"candidate artifact reread mismatch: {relative}")
    PartitionEvidence.from_json_bytes((staging / "partition_evidence.json").read_bytes())
    R4PartitionSufficiencyReceipt.from_json_bytes(
        (staging / "partition_sufficiency.json").read_bytes()
    )
    manifest = R4SplitManifest.from_json_bytes((staging / "split_manifest.json").read_bytes())
    capability = R4ClassCapability.from_json_bytes(
        (staging / "capabilities/train.json").read_bytes()
    )
    authorization = R4ClassAuthorization.from_json_bytes(
        (staging / "authorizations/train.json").read_bytes()
    )
    receipt = R4BuildReceipt.from_dict(
        json.loads((staging / "BUILD_RECEIPT.json").read_text("utf-8"))
    )
    if manifest != result.split_manifest or capability != result.train_capability:
        raise ValueError("candidate manifest/capability reconstruction mismatch")
    if authorization != result.train_authorization or receipt != result.receipt:
        raise ValueError("candidate authorization/receipt reconstruction mismatch")
    source_refs: list[str] = []
    for split in SPLITS:
        raw = (staging / f"splits/{split}.jsonl").read_bytes()
        if not raw.endswith(b"\n"):
            raise ValueError("split payload is not newline-normalized")
        rows = [json.loads(line) for line in raw.decode("utf-8", errors="strict").splitlines()]
        decoded = tuple(AuthenticEpisode.from_dict(row) for row in rows)
        refs = tuple(row.episode_ref for row in decoded)
        if refs != tuple(sorted(refs)):
            raise ValueError("split payload is not ordered by episode_ref")
        source_refs.extend(refs)
    if len(source_refs) != len(set(source_refs)) or set(source_refs) != {
        row.episode_ref for row in result.episodes
    }:
        raise ValueError("split payloads are not disjoint and exhaustive")
    for relative, raw in expected_by_path.items():
        if (staging / relative).read_bytes() != raw:
            raise ValueError(f"candidate artifact changed during verification: {relative}")
