"""Deterministic R4 reviewed-data pipeline with external-only approval."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .persistence import RevisionPin
from .r3_codec import exact_fields, exact_refs, exact_text, wire_refs
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
from .r4_partitions import (
    IndependentAxisPartitioner,
    PartitionAxisManifest,
    TrainingAllowlist,
)
from .r4_sufficiency import (
    StructuralSufficiencyEvaluator,
    StructuralSufficiencyReceipt,
)

R4_BUILD_RECEIPT_ABI_VERSION = 3

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


def _sha256_bytes(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _rows_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    material = tuple(dict(row) for row in rows)
    return b"\n".join(_canonical_json(row) for row in material) + b"\n"


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
    partition_manifest_sha256s: tuple[str, ...]
    training_allowlist_sha256: str
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
            "partition_manifest_sha256s",
            "training_allowlist_sha256",
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
        canonical: dict[str, Any] = {}
        for name, value in values.items():
            if name == "partition_manifest_sha256s":
                canonical[name] = exact_refs(value, name, nonempty=True)
            else:
                canonical[name] = exact_text(value, name)
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
        object.__setattr__(obj, "receipt_ref", stable_ref("r4_build_v3", material))
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
            "partition_manifest_sha256s": list(self.partition_manifest_sha256s),
            "training_allowlist_sha256": self.training_allowlist_sha256,
            "admission_state": self.admission_state,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "R4BuildReceipt":
        row = exact_fields(value, cls._FIELDS, "R4BuildReceipt")
        if row["abi_version"] != R4_BUILD_RECEIPT_ABI_VERSION:
            raise ValueError("unsupported R4 Build Receipt ABI")
        values = {
            key: row[key]
            for key in cls._FIELDS - {"abi_version", "receipt_ref"}
        }
        values["partition_manifest_sha256s"] = wire_refs(
            row["partition_manifest_sha256s"],
            "partition_manifest_sha256s",
            nonempty=True,
        )
        rebuilt = cls.create(**values)
        if rebuilt.receipt_ref != row["receipt_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical R4BuildReceipt")
        return rebuilt


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
    partition_manifests: tuple[PartitionAxisManifest, ...]
    training_allowlist: TrainingAllowlist
    receipt: R4BuildReceipt


class R4Pipeline:
    """Build reviewed contracts, authentic observations and sealed datasets."""

    def __init__(
        self,
        *,
        authority: Any,
        revision_pin: RevisionPin,
        abi_registry_ref: str,
        episode_owner: EpisodeExecutionOwner,
        mutation_owner: MutationExecutionOwner,
        source_revision: str,
        seed: int = 1701,
        minimums: Mapping[str, int] | None = None,
        maximums: Mapping[str, int] | None = None,
        partition_ratios: tuple[int, int, int] = (60, 20, 20),
        strict: bool = True,
    ) -> None:
        self._pin = revision_pin
        self._abi_registry_ref = exact_text(abi_registry_ref, "abi_registry_ref")
        self._source_revision = exact_text(source_revision, "source_revision")
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
        self._partitioner = IndependentAxisPartitioner(
            seed=seed, ratios=partition_ratios
        )
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
        manifests, allowlist = self._partitioner.partition(
            episodes, mutations=mutations
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
        partition_hashes = tuple(
            _sha256_bytes(_canonical_json(row.as_dict()))
            for row in sorted(manifests, key=lambda item: item.axis)
        )
        receipt = R4BuildReceipt.create(
            source_revision=self._source_revision,
            authority_generation=self._pin.authority_generation,
            abi_registry_ref=self._abi_registry_ref,
            scenario_source_sha256=scenario_sha,
            assertion_registry_sha256=assertion_registry_sha,
            contract_set_sha256=_set_hash(row.as_dict() for row in contracts),
            derivation_contract_set_sha256=_set_hash(
                row.as_dict() for row in derivations
            ),
            expanded_case_set_sha256=_set_hash(row.as_dict() for row in cases),
            episode_set_sha256=_set_hash(row.as_dict() for row in episodes),
            mutation_set_sha256=_set_hash(row.as_dict() for row in mutations),
            mutation_observation_set_sha256=_set_hash(
                row.as_dict() for row in observations
            ),
            structural_sufficiency_sha256=_sha256_bytes(
                _canonical_json(sufficiency.as_dict())
            ),
            partition_manifest_sha256s=partition_hashes,
            training_allowlist_sha256=_sha256_bytes(
                _canonical_json(allowlist.as_dict())
            ),
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
            partition_manifests=manifests,
            training_allowlist=allowlist,
            receipt=receipt,
        )

    @staticmethod
    def write(result: R4BuildResult, output: Path) -> None:
        if type(result) is not R4BuildResult:
            raise TypeError("result must be exact R4BuildResult")
        output.mkdir(parents=True, exist_ok=True)
        write_jsonl(output / "expected_contracts.jsonl", (row.as_dict() for row in result.contracts))
        write_jsonl(output / "expected_derivations.jsonl", (row.as_dict() for row in result.derivation_contracts))
        write_jsonl(output / "expanded_cases.jsonl", (row.as_dict() for row in result.expanded_cases))
        write_jsonl(output / "episodes.jsonl", (row.as_dict() for row in result.episodes))
        write_jsonl(output / "mutations.jsonl", (row.as_dict() for row in result.mutations))
        write_jsonl(output / "mutation_observations.jsonl", (row.as_dict() for row in result.mutation_observations))
        (output / "structural_sufficiency.json").write_bytes(
            _canonical_json(result.sufficiency.as_dict()) + b"\n"
        )
        partitions = output / "partitions"
        partitions.mkdir(exist_ok=True)
        for manifest in result.partition_manifests:
            (partitions / f"{manifest.axis}.json").write_bytes(
                _canonical_json(manifest.as_dict()) + b"\n"
            )
        (output / "training_allowlist.json").write_bytes(
            _canonical_json(result.training_allowlist.as_dict()) + b"\n"
        )
        (output / "BUILD_RECEIPT.json").write_bytes(
            _canonical_json(result.receipt.as_dict()) + b"\n"
        )
