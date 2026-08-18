"""Independent reconstruction for R4 global partition evidence.

This verifier intentionally does not call GlobalLeakagePartitioner, its union/find,
its component builder, or its allocator.  It reconstructs the source graph from
wire-compatible episode/mutation material and validates the admitted assignment.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import unicodedata
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .r4_partition_config import (
    R4PartitionConfig, RATIO_DENOMINATOR, RARITY_SCALE, DimensionMinimum
)
from .r4_partition_contracts import (
    PARTITION_EVIDENCE_ABI_VERSION,
    SPLITS,
    GlobalPartitionComponent,
    LeakageHyperedge,
    PartitionEvidence,
    StratificationLabel,
)


class PartitionVerificationError(ValueError):
    pass


def _raw(value: object, kind: str) -> dict[str, Any]:
    if type(value) is dict:
        row = value
    else:
        encoder = getattr(value, "as_dict", None)
        if not callable(encoder):
            raise TypeError(f"{kind} must be a mapping or expose as_dict()")
        row = encoder()
    if type(row) is not dict:
        raise TypeError(f"{kind} serialization must be an object")
    return row


def _lineage(rows: object, prefix: str) -> str | None:
    if type(rows) is not list:
        return None
    matches = [row for row in rows if type(row) is str and row.startswith(prefix)]
    if len(matches) > 1:
        raise PartitionVerificationError(f"duplicate {prefix} lineage")
    return matches[0] if matches else None


def _normalized_surface(surface: str, language: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", surface).casefold().split())
    if not normalized or not language:
        raise PartitionVerificationError("empty normalized surface identity")
    return stable_ref(
        "normalized_surface_v3",
        {"language": language, "surface": normalized},
    )


def _grounded(expression: Mapping[str, Any]) -> tuple[str, ...]:
    refs: set[str] = set()
    apps = expression.get("applications", [])
    if type(apps) is not list:
        raise TypeError("applications must be a list")
    for app in apps:
        if type(app) is not dict:
            raise TypeError("application must be an object")
        for name in ("roles", "qualifiers"):
            bindings = app.get(name, [])
            if type(bindings) is not list:
                raise TypeError("bindings must be a list")
            for binding in bindings:
                if type(binding) is not dict:
                    raise TypeError("binding must be an object")
                filler = binding.get("filler")
                if type(filler) is dict and filler.get("kind") == "grounded":
                    ref = filler.get("target_ref")
                    if type(ref) is str and ":" in ref:
                        refs.add(ref)
    return tuple(sorted(refs))


def _topology(expression: Mapping[str, Any]) -> str:
    apps = expression.get("applications", [])
    material = []
    for app in apps:
        if type(app) is not dict:
            raise TypeError("application must be an object")
        material.append(
            {
                "operator": app.get("operator"),
                "predicate_ref": app.get("predicate_ref"),
                "roles": [
                    binding.get("role_ref")
                    for binding in app.get("roles", [])
                    if type(binding) is dict
                ],
                "qualifiers": [
                    binding.get("role_ref")
                    for binding in app.get("qualifiers", [])
                    if type(binding) is dict
                ],
            }
        )
    return stable_ref(
        "r4_expression_topology_v3",
        {
            "applications": material,
            "root_count": len(expression.get("root_refs", [])),
            "scope_operators": [
                row.get("operator_type")
                for row in expression.get("scope_operators", [])
                if type(row) is dict
            ],
            "expression_links": [
                [row.get("link_type"), len(row.get("operand_refs", []))]
                for row in expression.get("expression_links", [])
                if type(row) is dict
            ],
            "binder_count": len(expression.get("binders", [])),
        },
    )


def _topology_category(expression: Mapping[str, Any]) -> str:
    apps = expression.get("applications", [])
    return stable_ref(
        "r4_topology_category_v1",
        {
            "application_count": len(apps),
            "operators": [
                app.get("operator")
                for app in apps
                if type(app) is dict and type(app.get("operator")) is str
            ],
            "root_count": len(expression.get("root_refs", [])),
            "scope_count": len(expression.get("scope_operators", [])),
            "link_count": len(expression.get("expression_links", [])),
        },
    )


def _obligations(episode: Mapping[str, Any]) -> tuple[str, ...]:
    observed = episode.get("observed_cycle")
    if type(observed) is not dict:
        return ()
    response = observed.get("response_meaning")
    if type(response) is not dict:
        return ()
    refs: set[str] = set()
    value = response.get("obligation_ref")
    if type(value) is str and ":" in value:
        refs.add(value)
    for container_name in ("obligation", "learning_plan"):
        container = response.get(container_name)
        if type(container) is not dict:
            continue
        for name in (
            "obligation_ref",
            "plan_ref",
            "expected_answer_contract_ref",
            "completion_receipt_ref",
        ):
            value = container.get(name)
            if type(value) is str and ":" in value:
                refs.add(value)
    return tuple(sorted(refs))


def _response_expression(episode: Mapping[str, Any]) -> str | None:
    observed = episode.get("observed_cycle")
    response = observed.get("response_meaning") if type(observed) is dict else None
    expression = response.get("response_expression") if type(response) is dict else None
    ref = expression.get("expression_ref") if type(expression) is dict else None
    return ref if type(ref) is str and ":" in ref else None


def _response_semantics(episode: Mapping[str, Any]) -> str | None:
    observed = episode.get("observed_cycle")
    response = observed.get("response_meaning") if type(observed) is dict else None
    if type(response) is not dict:
        return None
    material = {
        name: response.get(name)
        for name in (
            "cycle_status",
            "discourse_action",
            "epistemic_status_ref",
            "modality_ref",
            "polarity_ref",
        )
    }
    if not any(value is not None for value in material.values()):
        return None
    return stable_ref("r4_response_semantic_family_v1", material)


class _UF:
    def __init__(self, refs: Iterable[str]) -> None:
        self.parent = {ref: ref for ref in refs}

    def find(self, ref: str) -> str:
        while self.parent[ref] != ref:
            self.parent[ref] = self.parent[self.parent[ref]]
            ref = self.parent[ref]
        return ref

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if b < a:
            a, b = b, a
        self.parent[b] = a


def _extract(
    episodes: Iterable[object], mutations: Iterable[object]
) -> tuple[str, tuple[LeakageHyperedge, ...], tuple[StratificationLabel, ...], tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]]:
    rows = tuple(_raw(row, "episode") for row in episodes)
    mutation_rows = tuple(_raw(row, "mutation") for row in mutations)
    refs = tuple(sorted(row.get("episode_ref") for row in rows))
    if any(type(ref) is not str for ref in refs) or len(refs) != len(set(refs)):
        raise PartitionVerificationError("invalid source episode refs")
    source_set_ref = stable_ref("r4_partition_source_v3", list(refs))
    by_ref = {row["episode_ref"]: row for row in rows}
    mutations_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for mutation in mutation_rows:
        parent = mutation.get("parent_case_ref")
        if type(parent) is str:
            mutations_by_parent[parent].append(mutation)
    keys: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    labels: dict[str, set[str]] = defaultdict(set)

    def edge(axis: str, namespace: str, ref: object, member: str) -> None:
        if ref is None:
            return
        if type(ref) is not str or ":" not in ref:
            raise PartitionVerificationError("non-reference leakage key")
        keys[(axis, namespace, ref)].add(member)

    def label(namespace: str, member: str) -> None:
        labels[namespace].add(member)

    for episode_ref in refs:
        episode = by_ref[episode_ref]
        case = episode.get("expanded_case")
        contract = episode.get("expected_contract")
        if type(case) is not dict or type(contract) is not dict:
            raise PartitionVerificationError("episode case/contract missing")
        for namespace, ref in (
            ("scenario", case.get("scenario_ref")),
            ("case", case.get("case_ref")),
            ("trajectory", case.get("trajectory_ref")),
        ):
            edge("general", namespace, ref, episode_ref)
        for ref in episode.get("generator_lineage_refs", []):
            if type(ref) is str and ":" in ref:
                edge("general", "generator_lineage", ref, episode_ref)

        surface_family = _lineage(case.get("lineage_refs"), "surface_family:")
        edge("lexical", "surface_family", surface_family, episode_ref)
        surface, language = case.get("surface"), case.get("language")
        if type(surface) is str and type(language) is str:
            edge("lexical", "normalized_surface", _normalized_surface(surface, language), episode_ref)
            label(f"coverage:language:{language}", episode_ref)
        if surface_family:
            label(f"coverage:surface:{surface_family}", episode_ref)
        environment_family = _lineage(case.get("lineage_refs"), "environment_family:")
        if environment_family:
            label(f"coverage:environment:{environment_family}", episode_ref)

        expressions = contract.get("expected_expressions", [])
        if expressions:
            for expression in expressions:
                if type(expression) is not dict:
                    raise PartitionVerificationError("expression row invalid")
                edge("semantic_target", "semantic_expression", expression.get("expression_ref"), episode_ref)
                for app in expression.get("applications", []):
                    if type(app) is not dict:
                        raise PartitionVerificationError("application row invalid")
                    edge("semantic_target", "predicate", app.get("predicate_ref"), episode_ref)
                    operator = app.get("operator")
                    if type(operator) is str:
                        label(f"coverage:operator:{operator}", episode_ref)
                for target in _grounded(expression):
                    edge("semantic_target", "grounded_target", target, episode_ref)
                    label(f"coverage:target_category:{target.split(':', 1)[0]}", episode_ref)
                edge("topology", "expression_topology", _topology(expression), episode_ref)
                label(f"coverage:topology:{_topology_category(expression)}", episode_ref)
        else:
            label("coverage:topology:none", episode_ref)

        edge("dialogue", "trajectory", case.get("trajectory_ref"), episode_ref)
        obligation_refs = _obligations(episode)
        for ref in obligation_refs:
            edge("dialogue", "obligation_lineage", ref, episode_ref)
        label(
            "coverage:dialogue_obligation:present" if obligation_refs else "coverage:dialogue_obligation:none",
            episode_ref,
        )

        case_ref = case.get("case_ref")
        if type(case_ref) is str:
            edge("mutation", "parent_case", case_ref, episode_ref)
            for mutation in mutations_by_parent.get(case_ref, ()):
                edge("mutation", "mutation_child", mutation.get("mutation_ref"), episode_ref)
                family = _lineage(mutation.get("lineage_refs"), "mutation_family:")
                if family:
                    edge(
                        "mutation",
                        "reviewed_mutation_family",
                        stable_ref(
                            "r4_reviewed_mutation_family_v1",
                            {"scenario_ref": case.get("scenario_ref"), "family_ref": family},
                        ),
                        episode_ref,
                    )
                dimension = mutation.get("dimension")
                if type(dimension) is str:
                    label(f"coverage:mutation:{dimension}", episode_ref)

        edge("realization", "response_expression", _response_expression(episode), episode_ref)
        edge("realization", "response_semantics", _response_semantics(episode), episode_ref)
        expected_response = contract.get("expected_response")
        if type(expected_response) is dict and type(expected_response.get("discourse_action")) is str:
            label(f"coverage:response:{expected_response['discourse_action']}", episode_ref)

        for field, prefix in (
            ("expected_mode", "mode"),
            ("expected_owner", "owner"),
            ("expression_relation", "expression_relation"),
        ):
            value = contract.get(field)
            if type(value) is str:
                label(f"coverage:{prefix}:{value}", episode_ref)
        decision = contract.get("expected_decision")
        if type(decision) is dict:
            for field, prefix in (("action", "decision_action"), ("status", "decision_status")):
                value = decision.get(field)
                if type(value) is str:
                    label(f"coverage:{prefix}:{value}", episode_ref)
        effect = contract.get("expected_effect")
        if type(effect) is dict:
            for field, prefix in (("kind", "effect_kind"), ("status_or_reason", "effect_status")):
                value = effect.get(field)
                if type(value) is str:
                    label(f"coverage:{prefix}:{value}", episode_ref)
        assertions = contract.get("normalized_assertions", [])
        if type(assertions) is list:
            for assertion in assertions:
                if type(assertion) is dict and type(assertion.get("kind")) is str:
                    label(f"coverage:assertion_kind:{assertion['kind']}", episode_ref)
        outcome = contract.get("outcome_kind")
        if type(outcome) is str:
            label(f"coverage:outcome:{outcome}", episode_ref)
        gap = contract.get("expected_gap")
        if type(gap) is dict:
            gap_kind = gap.get("kind") or gap.get("gap_kind")
            if type(gap_kind) is str:
                label(f"coverage:gap:{gap_kind}", episode_ref)
        elif gap is None:
            label("coverage:gap:none", episode_ref)

    hyperedges = tuple(
        sorted(
            (
                LeakageHyperedge.create(
                    axis=axis,
                    key_namespace=namespace,
                    key_ref=key_ref,
                    member_refs=tuple(sorted(members)),
                )
                for (axis, namespace, key_ref), members in keys.items()
                if len(members) >= 2
            ),
            key=lambda row: row.hyperedge_ref,
        )
    )
    label_rows = tuple(
        sorted(
            (
                StratificationLabel.create(namespace=namespace, member_refs=tuple(sorted(members)))
                for namespace, members in labels.items()
            ),
            key=lambda row: row.label_ref,
        )
    )
    uf = _UF(refs)
    for row in hyperedges:
        first = row.member_refs[0]
        for member in row.member_refs[1:]:
            uf.union(first, member)
    members_by_root: dict[str, list[str]] = defaultdict(list)
    for ref in refs:
        members_by_root[uf.find(ref)].append(ref)
    owner_by_edge = {
        row.hyperedge_ref: uf.find(row.member_refs[0]) for row in hyperedges
    }
    components = []
    for root, members in members_by_root.items():
        member_refs = tuple(sorted(members))
        edge_refs = tuple(sorted(ref for ref, owner in owner_by_edge.items() if owner == root))
        component_ref = stable_ref(
            "r4_global_partition_component_v3",
            {
                "source_set_ref": source_set_ref,
                "partition_abi_version": PARTITION_EVIDENCE_ABI_VERSION,
                "member_refs": list(member_refs),
                "hyperedge_refs": list(edge_refs),
            },
        )
        components.append((component_ref, member_refs, edge_refs))
    return source_set_ref, hyperedges, label_rows, tuple(sorted(components))



@dataclass(frozen=True)
class _VComponent:
    component_ref: str
    member_refs: tuple[str, ...]


def _remaining_minima(
    minima: tuple[DimensionMinimum, ...], *, split: str, contribution: Mapping[str, int]
) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (row.dimension_ref, row.split, max(0, row.minimum - contribution.get(row.dimension_ref, 0)) if row.split == split else row.minimum)
        for row in minima
    )


class _VerifierOracle:
    def __init__(
        self,
        components: tuple[_VComponent, ...],
        labels_by_ref: Mapping[str, StratificationLabel],
        minima: tuple[DimensionMinimum, ...],
    ) -> None:
        self.components = components
        self.dimensions = tuple(sorted({row.dimension_ref for row in minima}))
        members = {ref: frozenset(labels_by_ref[ref].member_refs) for ref in self.dimensions}
        self.contrib = tuple(
            tuple(len(frozenset(component.member_refs) & members[ref]) for ref in self.dimensions)
            for component in components
        )
        self.suffix: list[tuple[int, ...]] = [(0,) * len(self.dimensions) for _ in range(len(components) + 1)]
        running = [0] * len(self.dimensions)
        for index in range(len(components) - 1, -1, -1):
            for dim, value in enumerate(self.contrib[index]):
                running[dim] += value
            self.suffix[index] = tuple(running)
        self.memo: dict[tuple[int, ...], tuple[int, ...] | None] = {}

    def completion(
        self, index: int, class_counts: tuple[int, int, int, int], minima: tuple[tuple[str, str, int], ...]
    ) -> tuple[int, ...] | None:
        by_key = {(split, ref): value for ref, split, value in minima}
        needs = tuple(by_key.get((split, ref), 0) for split in SPLITS for ref in self.dimensions)
        return self._search(index, class_counts, needs)

    def _search(self, index: int, class_counts: tuple[int, int, int, int], needs: tuple[int, ...]) -> tuple[int, ...] | None:
        key = (index, *class_counts, *needs)
        if key in self.memo:
            return self.memo[key]
        if len(self.memo) >= 250_000:
            raise PartitionVerificationError("independent verifier solver state bound exceeded")
        if index == len(self.components):
            result = () if all(class_counts) and not any(needs) else None
            self.memo[key] = result
            return result
        remaining = len(self.components) - index
        if sum(value == 0 for value in class_counts) > remaining:
            self.memo[key] = None
            return None
        width = len(self.dimensions)
        capacity = self.suffix[index]
        for dim in range(width):
            if sum(needs[split * width + dim] for split in range(4)) > capacity[dim]:
                self.memo[key] = None
                return None
        contribution = self.contrib[index]
        choices = []
        seen = set()
        for split_index in range(4):
            segment = needs[split_index * width:(split_index + 1) * width]
            shape = (class_counts[split_index], segment)
            if shape in seen:
                continue
            seen.add(shape)
            coverage = sum(min(segment[dim], value) for dim, value in enumerate(contribution))
            choices.append((0 if class_counts[split_index] == 0 else 1, -coverage, split_index))
        for _, __, split_index in sorted(choices):
            next_counts = list(class_counts)
            next_counts[split_index] += len(self.components[index].member_refs)
            next_needs = list(needs)
            base = split_index * width
            for dim, value in enumerate(contribution):
                next_needs[base + dim] = max(0, next_needs[base + dim] - value)
            tail = self._search(index + 1, tuple(next_counts), tuple(next_needs))
            if tail is not None:
                result = (split_index, *tail)
                self.memo[key] = result
                return result
        self.memo[key] = None
        return None


def _objective(
    *, source_count: int, class_counts: tuple[int, int, int, int], observed: Mapping[tuple[str, str], int],
    config: R4PartitionConfig, global_counts: Mapping[str, int], tie: str
) -> tuple[int, int, int, str]:
    weights = {row.split: row.weight for row in config.target_weights}
    size = sum(abs(RATIO_DENOMINATOR * class_counts[i] - source_count * weights[split]) for i, split in enumerate(SPLITS))
    label = sum(abs(RATIO_DENOMINATOR * observed.get((split, ref), 0) - global_counts[ref] * weights[split]) for split in SPLITS for ref in sorted(global_counts))
    minima = {(row.split, row.dimension_ref): row.minimum for row in config.minima}
    maxima = {(row.split, row.dimension_ref): row.maximum for row in config.maxima}
    bounds = sum(max(0, minima[(split, ref)] - observed.get((split, ref), 0)) + max(0, observed.get((split, ref), 0) - maxima[(split, ref)]) for split in SPLITS for ref in sorted(global_counts))
    return size, label, bounds, tie


def _expected_assignment(
    reconstructed: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...],
    labels: tuple[StratificationLabel, ...],
    config: R4PartitionConfig,
) -> tuple[dict[str, str], tuple[int, int, int, str]]:
    labels_by_ref = {row.label_ref: row for row in labels}
    dimensions = tuple(sorted({row.dimension_ref for row in config.minima}))
    member_sets = {ref: frozenset(labels_by_ref[ref].member_refs) for ref in dimensions}
    components = tuple(_VComponent(ref, members) for ref, members, _ in reconstructed)
    counts_by_component = {
        component.component_ref: {ref: len(frozenset(component.member_refs) & member_sets[ref]) for ref in dimensions if frozenset(component.member_refs) & member_sets[ref]}
        for component in components
    }
    global_counts = {ref: len(member_sets[ref]) for ref in dimensions}
    ordered = tuple(sorted(components, key=lambda component: (-len(component.member_refs), -sum(RARITY_SCALE // global_counts[ref] for ref in counts_by_component[component.component_ref]), component.component_ref)))
    oracle = _VerifierOracle(ordered, labels_by_ref, config.minima)
    class_counts = [0, 0, 0, 0]
    observed = {(split, ref): 0 for split in SPLITS for ref in dimensions}
    remaining = tuple((row.dimension_ref, row.split, row.minimum) for row in config.minima)
    assignment: dict[str, str] = {}
    source_count = sum(len(row.member_refs) for row in ordered)
    for index, component in enumerate(ordered):
        options = []
        contribution = counts_by_component[component.component_ref]
        for split_index, split in enumerate(SPLITS):
            next_counts = list(class_counts)
            next_counts[split_index] += len(component.member_refs)
            next_remaining = tuple((ref, row_split, max(0, value - contribution.get(ref, 0)) if row_split == split else value) for ref, row_split, value in remaining)
            if oracle.completion(index + 1, tuple(next_counts), next_remaining) is None:
                continue
            next_observed = dict(observed)
            for ref, value in contribution.items():
                next_observed[(split, ref)] += value
            options.append((_objective(source_count=source_count, class_counts=tuple(next_counts), observed=next_observed, config=config, global_counts=global_counts, tie=stable_ref("r4_partition_tie", {"component": component.component_ref, "split": split, "seed": config.seed})), split_index))
        if not options:
            raise PartitionVerificationError("independent verifier found no deterministic assignment")
        _, chosen = min(options, key=lambda row: row[0])
        split = SPLITS[chosen]
        assignment[component.component_ref] = split
        class_counts[chosen] += len(component.member_refs)
        contribution = counts_by_component[component.component_ref]
        for ref, value in contribution.items():
            observed[(split, ref)] += value
        remaining = tuple((ref, row_split, max(0, value - contribution.get(ref, 0)) if row_split == split else value) for ref, row_split, value in remaining)
    tie = stable_ref("r4_partition_assignment_tie_v1", sorted(assignment.items()))
    return assignment, _objective(source_count=source_count, class_counts=tuple(class_counts), observed=observed, config=config, global_counts=global_counts, tie=tie)

def verify_partition_assignment(
    episodes: Iterable[object],
    *,
    mutations: Iterable[object],
    config: R4PartitionConfig,
    evidence: PartitionEvidence,
) -> tuple[int, int, int, str]:
    if type(config) is not R4PartitionConfig or type(evidence) is not PartitionEvidence:
        raise TypeError("verifier requires exact config and evidence contracts")
    episode_rows = tuple(episodes)
    mutation_rows = tuple(mutations)
    source_set_ref, hyperedges, labels, reconstructed = _extract(episode_rows, mutation_rows)
    if source_set_ref != evidence.source_set_ref:
        raise PartitionVerificationError("source_set_ref mismatch")
    if evidence.config_ref != config.config_ref:
        raise PartitionVerificationError("partition config_ref mismatch")
    if hyperedges != evidence.hyperedges:
        raise PartitionVerificationError("leakage hyperedge reconstruction mismatch")
    if labels != evidence.labels:
        raise PartitionVerificationError("stratification label reconstruction mismatch")
    actual_by_ref = {row.component_ref: row for row in evidence.components}
    expected_refs = {row[0] for row in reconstructed}
    if set(actual_by_ref) != expected_refs:
        raise PartitionVerificationError("component identity reconstruction mismatch")
    for component_ref, members, edge_refs in reconstructed:
        row = actual_by_ref[component_ref]
        if row.member_refs != members or row.hyperedge_refs != edge_refs:
            raise PartitionVerificationError("component membership reconstruction mismatch")

    expected_assignment, expected_objective = _expected_assignment(reconstructed, labels, config)
    actual_assignment = {row.component_ref: row.split for row in evidence.components}
    if actual_assignment != expected_assignment:
        raise PartitionVerificationError("component assignment differs from canonical integer allocator")

    source_owner: dict[str, str] = {}
    class_counts = {split: 0 for split in SPLITS}
    for row in evidence.components:
        class_counts[row.split] += len(row.member_refs)
        for member in row.member_refs:
            if member in source_owner:
                raise PartitionVerificationError("episode assigned more than once")
            source_owner[member] = row.split
    expected_source_refs = {
        ref
        for row in episode_rows
        for ref in [_raw(row, "episode").get("episode_ref")]
        if type(ref) is str
    }
    if not all(class_counts.values()) or set(source_owner) != expected_source_refs:
        raise PartitionVerificationError("assignment is empty or non-exhaustive")
    for edge in evidence.hyperedges:
        if len({source_owner[member] for member in edge.member_refs}) != 1:
            raise PartitionVerificationError("leakage hyperedge crosses splits")

    labels_by_ref = {row.label_ref: row for row in evidence.labels}
    dimensions = tuple(sorted({row.dimension_ref for row in config.minima}))
    observed = {(split, ref): 0 for split in SPLITS for ref in dimensions}
    for ref in dimensions:
        label = labels_by_ref.get(ref)
        if label is None:
            raise PartitionVerificationError("config dimension missing from evidence")
        for member in label.member_refs:
            observed[(source_owner[member], ref)] += 1
    minima = {(row.split, row.dimension_ref): row.minimum for row in config.minima}
    maxima = {(row.split, row.dimension_ref): row.maximum for row in config.maxima}
    for key in minima:
        value = observed[key]
        if value < minima[key] or value > maxima[key]:
            raise PartitionVerificationError(f"dimension bound violated: {key}")

    weights = {row.split: row.weight for row in config.target_weights}
    total = sum(class_counts.values())
    size_deviation = sum(
        abs(RATIO_DENOMINATOR * class_counts[split] - total * weights[split])
        for split in SPLITS
    )
    label_deviation = sum(
        abs(
            RATIO_DENOMINATOR * observed[(split, ref)]
            - len(labels_by_ref[ref].member_refs) * weights[split]
        )
        for split in SPLITS
        for ref in dimensions
    )
    bound_violation = sum(
        max(0, minima[key] - observed[key]) + max(0, observed[key] - maxima[key])
        for key in minima
    )
    assignment = sorted((row.component_ref, row.split) for row in evidence.components)
    tie = stable_ref("r4_partition_assignment_tie_v1", assignment)
    # Rebuilding through the immutable contract also proves canonical bytes.
    rebuilt_components = tuple(
        sorted(
            (
                GlobalPartitionComponent.create(
                    source_set_ref=source_set_ref,
                    member_refs=members,
                    hyperedge_refs=edge_refs,
                    split=actual_by_ref[component_ref].split,
                )
                for component_ref, members, edge_refs in reconstructed
            ),
            key=lambda row: row.component_ref,
        )
    )
    rebuilt = PartitionEvidence.create(
        source_set_ref=source_set_ref,
        config_ref=config.config_ref,
        hyperedges=hyperedges,
        labels=labels,
        components=rebuilt_components,
    )
    if rebuilt.to_json_bytes() != evidence.to_json_bytes():
        raise PartitionVerificationError("partition evidence bytes are not independently reconstructible")
    objective = (size_deviation, label_deviation, bound_violation, tie)
    if objective != expected_objective:
        raise PartitionVerificationError("assignment objective reconstruction mismatch")
    return objective


__all__ = ["PartitionVerificationError", "verify_partition_assignment"]
