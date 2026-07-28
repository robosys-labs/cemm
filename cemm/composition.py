"""Bounded bottom-up composition of atomic semantic graphlets.

The chart is the single Stage-5 orchestrator.  It consumes already-grounded form
units, reuses the existing atomic graph matcher, and combines reviewed semantic
frame contributions into transient :class:`PropositionGraph` values.  It never
parses raw text, mints semantic identities, writes world state, or introduces a
sixth operator.
"""
from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass, replace
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from cemm.codec import Candidate
from cemm.model import stable
from cemm.propositions import (
    ATOMIC_COMPOSITION_ABI,
    MAX_PROPOSITION_APPLICATIONS,
    MAX_PROPOSITION_DEPTH,
    PropositionApplication,
    PropositionCoverage,
    PropositionGraph,
    PropositionUnit,
)
from cemm.semantic_coverage import CoveragePolicy


@dataclass(frozen=True)
class CompositionLimits:
    max_scope_units: int = 16
    max_scopes_per_hypothesis: int = 96
    max_graphlets_per_cell: int = 8
    max_total_graphlets: int = 48
    max_depth: int = MAX_PROPOSITION_DEPTH
    state_budget: int = 12000
    max_partial_gaps: int = 24

    def __post_init__(self) -> None:
        if any(not isinstance(value, int) or value <= 0 for value in vars(self).values()):
            raise ValueError("composition limits must be positive integers")
        if self.max_depth > MAX_PROPOSITION_DEPTH:
            raise ValueError("composition depth exceeds PropositionGraph ABI")

    @classmethod
    def from_config(cls, config: Any) -> "CompositionLimits":
        return cls(**{
            field: int(getattr(config, f"composition_{field}", default))
            for field, default in {
                "max_scope_units": 16,
                "max_scopes_per_hypothesis": 96,
                "max_graphlets_per_cell": 8,
                "max_total_graphlets": 48,
                "max_depth": MAX_PROPOSITION_DEPTH,
                "state_budget": 12000,
                "max_partial_gaps": 24,
            }.items()
        })


@dataclass(frozen=True)
class CompositionGap:
    gap_ref: str
    kind: str
    hypothesis_ref: str
    scope_ref: str
    parent_proposition_ref: str | None = None
    child_proposition_refs: tuple[str, ...] = ()
    unsatisfied_ports: tuple[str, ...] = ()
    candidate_roles: tuple[str, ...] = ()
    source_unit_refs: tuple[str, ...] = ()
    known_unit_refs: tuple[str, ...] = ()
    unknown_unit_refs: tuple[str, ...] = ()
    blocks: tuple[str, ...] = ("interpretation", "answer")
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, kind: str, hypothesis_ref: str, scope_ref: str, **kwargs):
        normalized = {
            key: tuple(dict.fromkeys(map(str, value)))
            if key in {
                "child_proposition_refs", "unsatisfied_ports", "candidate_roles",
                "source_unit_refs", "known_unit_refs", "unknown_unit_refs", "blocks",
            }
            else value
            for key, value in kwargs.items()
        }
        return cls(
            stable("composition-gap-v1", kind, hypothesis_ref, scope_ref, normalized),
            str(kind), str(hypothesis_ref), str(scope_ref), **normalized,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "gap_ref": self.gap_ref,
            "gap_kind": self.kind,
            "hypothesis_ref": self.hypothesis_ref,
            "scope_ref": self.scope_ref,
            "parent_proposition_ref": self.parent_proposition_ref,
            "child_proposition_refs": list(self.child_proposition_refs),
            "unsatisfied_ports": list(self.unsatisfied_ports),
            "candidate_roles": list(self.candidate_roles),
            "source_unit_refs": list(self.source_unit_refs),
            "known_unit_refs": list(self.known_unit_refs),
            "unknown_unit_refs": list(self.unknown_unit_refs),
            "blocks": list(self.blocks),
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class ChartGraphlet:
    proposition: PropositionGraph
    unit: PropositionUnit
    score: float
    source: str
    trace: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompositionResult:
    candidates: tuple[Candidate, ...]
    graphlets: tuple[ChartGraphlet, ...]
    gaps: tuple[CompositionGap, ...]
    diagnostics: Mapping[str, Any]


class RecursiveCompositionChart:
    """One bounded, N-best chart around the existing atomic assembler."""

    def __init__(self, assembler: Any, config: Any) -> None:
        self.assembler = assembler
        self.limits = CompositionLimits.from_config(config)

    @staticmethod
    def _features(unit: Any) -> dict[str, Any]:
        return dict(getattr(unit, "features", {}) or {})

    @classmethod
    def _is_force(cls, unit: Any) -> bool:
        features = cls._features(unit)
        return bool(
            features.get("discourse_force")
            or features.get("force_evidence")
            or features.get("interrogative")
        )

    @classmethod
    def _is_structural(cls, unit: Any) -> bool:
        features = cls._features(unit)
        return bool(
            cls._is_force(unit)
            or features.get("copular")
            or features.get("auxiliary")
            or features.get("modal")
            or features.get("negation")
            or features.get("scope_operator")
        )

    @classmethod
    def _is_predicate(cls, unit: Any) -> bool:
        features = cls._features(unit)
        return bool(
            features.get("contribution_kind") == "predicate"
            or features.get("predicate")
        )

    @staticmethod
    def _is_anchor(unit: Any) -> bool:
        return bool(
            getattr(unit, "kind", None) == "anchor"
            and getattr(unit, "semantic_ref", None)
        )

    @classmethod
    def _critical(cls, unit: Any) -> bool:
        features = cls._features(unit)
        return bool(
            getattr(unit, "kind", None) in {"unknown", "proposition"}
            or cls._is_predicate(unit)
            or cls._is_force(unit)
            or cls._is_anchor(unit)
            or features.get("copular")
            or features.get("negation")
            or features.get("modal")
        )

    @staticmethod
    def _unique_units(units: Sequence[Any]) -> tuple[Any, ...]:
        output = []
        seen: set[str] = set()
        for unit in units:
            ref = str(getattr(unit, "unit_ref", ""))
            if not ref or ref in seen:
                continue
            seen.add(ref)
            output.append(unit)
        return tuple(output)

    @staticmethod
    def _scope_ref(hypothesis_ref: str, units: Sequence[Any]) -> str:
        return stable(
            "composition-scope-v1", hypothesis_ref,
            tuple(str(getattr(unit, "unit_ref", "")) for unit in units),
        )

    def _scopes(self, hypothesis: Any) -> tuple[tuple[Any, ...], ...]:
        units = tuple(getattr(hypothesis, "units", ()))
        output: list[tuple[Any, ...]] = []
        seen: set[tuple[str, ...]] = set()
        maximum = min(len(units), self.limits.max_scope_units)
        # Short scopes first allow inner clauses to become proposition units before
        # outer frames are considered.  Surface order bounds search only; semantic
        # legality remains type/port/frame driven.
        for length in range(1, maximum + 1):
            for start in range(0, len(units) - length + 1):
                selected = units[start:start + length]
                refs = tuple(str(item.unit_ref) for item in selected)
                if refs in seen:
                    continue
                if not any(
                    self._is_predicate(item)
                    or self._is_force(item)
                    or getattr(item, "kind", None) == "proposition"
                    for item in selected
                ):
                    continue
                seen.add(refs)
                output.append(selected)
                if len(output) >= self.limits.max_scopes_per_hypothesis:
                    return tuple(output)
        return tuple(output)

    @staticmethod
    def _fake_lattice(hypothesis: Any, units: Sequence[Any]) -> Any:
        scoped_ref = stable(
            "scoped-grounding-hypothesis-v1",
            getattr(hypothesis, "hypothesis_ref", ""),
            tuple(getattr(item, "unit_ref", "") for item in units),
        )
        if is_dataclass(hypothesis):
            scoped = replace(hypothesis, hypothesis_ref=scoped_ref, units=tuple(units))
        else:
            values = dict(vars(hypothesis))
            values.update({"hypothesis_ref": scoped_ref, "units": tuple(units)})
            scoped = SimpleNamespace(**values)
        return SimpleNamespace(grounding_hypotheses=(scoped,))

    def _schema_graphlets(
        self, hypothesis: Any, units: Sequence[Any], participant_frame: Any, language: str
    ) -> tuple[list[ChartGraphlet], list[Any]]:
        output: list[ChartGraphlet] = []
        partial: list[Any] = []
        scoped_lattice = self._fake_lattice(hypothesis, units)
        for evidence in self.assembler.evidence_records(scoped_lattice, participant_frame):
            if not evidence.coverage.executable:
                partial.append(evidence)
                continue
            try:
                packet = self.assembler.instantiate(evidence, participant_frame, language)
                # A state-value predication is one semantic graph. Clause force
                # determines whether that graph is asserted or queried; it is
                # never a property of a particular state word. The reviewed
                # schema remains the authority for subject/dimension/value
                # ports, while interrogative evidence supplies the boolean
                # query wrapper.
                if (
                    any(self._is_force(item) for item in units)
                    and packet.get("force") == "claim"
                    and len(packet.get("apps", ())) == 1
                    and packet["apps"][0].get("operator") == "op:state"
                ):
                    state_application = dict(packet["apps"][0])
                    packet = {
                        **packet,
                        "force": "query",
                        "apps": [],
                        "query": {
                            "restrictions": [state_application],
                            "variables": [],
                            "projection": [],
                            "qualifiers": {
                                "query_kind": "state_value_query",
                                "answer_mode": "boolean",
                            },
                        },
                    }
                coverage = PropositionCoverage.create(
                    hypothesis.hypothesis_ref,
                    direct_unit_refs=evidence.consumed_unit_refs,
                    role_by_source_unit_ref=evidence.role_by_unit_ref,
                    projected_slots=evidence.projected_slots,
                )
                graph = PropositionGraph.from_packet(
                    packet,
                    coverage=coverage,
                    depth=1,
                    provenance={
                        "source": "atomic_feature_schema",
                        "schema_ref": evidence.schema_ref,
                        "match_ref": evidence.match_ref,
                    },
                )
            except (KeyError, TypeError, ValueError):
                continue
            consumed = [
                unit for unit in units if unit.unit_ref in set(evidence.consumed_unit_refs)
            ]
            if not consumed:
                continue
            unit = PropositionUnit.create(
                graph,
                token_start=min(item.token_start for item in consumed),
                token_end=max(item.token_end for item in consumed),
                char_start=min(item.char_start for item in consumed),
                char_end=max(item.char_end for item in consumed),
                score=float(evidence.score),
                surface=" ".join(item.surface for item in sorted(consumed, key=lambda x: x.token_start)),
            )
            output.append(
                ChartGraphlet(
                    graph, unit, float(evidence.score), "atomic_schema",
                    {"schema_ref": evidence.schema_ref, "match_ref": evidence.match_ref},
                )
            )
        return output, partial

    def _description_graphlets(
        self, hypothesis: Any, units: Sequence[Any]
    ) -> list[ChartGraphlet]:
        forces = [item for item in units if self._is_force(item)]
        binders = [item for item in units if self._features(item).get("copular")]
        targets = [
            item for item in units
            if self._is_anchor(item)
            and self._features(item).get("contribution_kind") == "anchor"
            and getattr(item, "atom_kind", None) in {
                "concept", "entity", "participant", "event_type", "relation_type",
                "state_dimension", "value", "capability", "label_type", "time",
            }
        ]
        if not forces or not binders or not targets:
            return []
        # Description is a generic semantic operation only when there is no other
        # open-class predicate competing inside the same scope.
        other_predicates = [
            item for item in units
            if self._is_predicate(item) and item not in targets
            and not self._features(item).get("copular")
        ]
        if other_predicates:
            return []
        output: list[ChartGraphlet] = []
        for target in targets[:4]:
            relation_var, object_var = "?description_relation", "?description_object"
            app = PropositionApplication.create(
                "op:relation",
                {
                    "role:subject": target.semantic_ref,
                    "role:relation": relation_var,
                    "role:object": object_var,
                },
                qualifiers={"query_kind": "semantic_description"},
            )
            selected = self._unique_units((*forces, *binders, target))
            role_map = {item.unit_ref: "force" for item in forces}
            role_map.update({item.unit_ref: "binder" for item in binders})
            role_map[target.unit_ref] = "subject"
            coverage = PropositionCoverage.create(
                hypothesis.hypothesis_ref,
                direct_unit_refs=(item.unit_ref for item in selected),
                role_by_source_unit_ref=role_map,
            )
            request = {
                "description_kind": "semantic_target",
                "target_ref": target.semantic_ref,
                "requested_facets": [
                    "designation", "kind", "type", "supertype",
                    "defining_relation", "frame", "state_schema",
                    "capability", "part_structure", "provenance",
                ],
            }
            graph = PropositionGraph.create(
                (app,), root_application_ref=app.application_ref, force="query",
                projected_variables=(relation_var, object_var),
                ports_provided=("argument:proposition",), coverage=coverage,
                provenance={
                    "source": "core_semantic_description",
                    "packet_qualifiers": {
                        "query_kind": "semantic_description",
                        "target_ref": target.semantic_ref,
                    },
                    "describe_request": request,
                },
            )
            unit = PropositionUnit.create(
                graph,
                token_start=min(item.token_start for item in selected),
                token_end=max(item.token_end for item in selected),
                char_start=min(item.char_start for item in selected),
                char_end=max(item.char_end for item in selected),
                score=sum(float(item.score) for item in selected) + 0.35,
                surface=" ".join(item.surface for item in sorted(selected, key=lambda x: x.token_start)),
            )
            output.append(ChartGraphlet(graph, unit, unit.score, "semantic_description"))
        return output

    def _definition_description_graphlets(
        self, hypothesis: Any, units: Sequence[Any]
    ) -> list[ChartGraphlet]:
        """Describe a grounded target selected by definition semantics.

        This is not a phrase rule: the descriptor and target are selected from
        their reviewed semantic contribution metadata.  It covers forms such
        as a definition predicate applied to a grounded event/type/value where
        the target itself contributes a predicate rather than a nominal anchor.
        """
        forces = [item for item in units if self._is_force(item)]
        descriptors = [
            item for item in units
            if self._is_predicate(item)
            and self._features(item).get("evaluation_kind") == "semantic_description"
        ]
        allowed_kinds = {
            "concept", "entity", "participant", "event_type", "relation_type",
            "state_dimension", "value", "capability", "label_type", "time",
        }
        targets = [
            item for item in units
            if item not in descriptors
            and getattr(item, "semantic_ref", None)
            and getattr(item, "atom_kind", None) in allowed_kinds
            and (
                self._is_anchor(item)
                or self._is_predicate(item)
            )
        ]
        if not forces or not descriptors or not targets:
            return []

        structural = [
            item for item in units
            if self._is_structural(item)
            and not self._is_force(item)
            and item not in descriptors
            and item not in targets
        ]
        output: list[ChartGraphlet] = []
        for descriptor in descriptors[:4]:
            for target in targets[:4]:
                relation_var = "?description_relation"
                object_var = "?description_object"
                app = PropositionApplication.create(
                    "op:relation",
                    {
                        "role:subject": target.semantic_ref,
                        "role:relation": relation_var,
                        "role:object": object_var,
                    },
                    qualifiers={"query_kind": "semantic_description"},
                )
                selected = self._unique_units(
                    (*forces, descriptor, target, *structural)
                )
                role_map = {item.unit_ref: "force" for item in forces}
                role_map[descriptor.unit_ref] = "predicate_head"
                role_map[target.unit_ref] = "described_target"
                role_map.update({item.unit_ref: "scope" for item in structural})
                coverage = PropositionCoverage.create(
                    hypothesis.hypothesis_ref,
                    direct_unit_refs=(item.unit_ref for item in selected),
                    role_by_source_unit_ref=role_map,
                )
                request = {
                    "description_kind": "semantic_target",
                    "target_ref": target.semantic_ref,
                    "requested_facets": [
                        "designation", "kind", "type", "supertype",
                        "defining_relation", "frame", "state_schema",
                        "capability", "part_structure", "provenance",
                    ],
                }
                graph = PropositionGraph.create(
                    (app,), root_application_ref=app.application_ref, force="query",
                    projected_variables=(relation_var, object_var),
                    ports_provided=("argument:proposition",), coverage=coverage,
                    provenance={
                        "source": "definition_semantic_description",
                        "packet_qualifiers": {
                            "query_kind": "semantic_description",
                            "target_ref": target.semantic_ref,
                            "descriptor_ref": descriptor.semantic_ref,
                        },
                        "describe_request": request,
                    },
                )
                unit = PropositionUnit.create(
                    graph,
                    token_start=min(item.token_start for item in selected),
                    token_end=max(item.token_end for item in selected),
                    char_start=min(item.char_start for item in selected),
                    char_end=max(item.char_end for item in selected),
                    # A reviewed definition-to-description transition is more
                    # specific than a generic event-frame paraphrase over the
                    # same evidence.  Keep its rank above that paraphrase so
                    # the settled graph preserves the licensed description
                    # operation rather than answering a different event query.
                    score=sum(float(item.score) for item in selected) + 5.7,
                    surface=" ".join(
                        item.surface for item in sorted(selected, key=lambda x: x.token_start)
                    ),
                )
                output.append(
                    ChartGraphlet(graph, unit, unit.score, "definition_semantic_description")
                )
        return output

    def _possessive_relation_event_graphlets(
        self, hypothesis: Any, units: Sequence[Any]
    ) -> list[ChartGraphlet]:
        """Compose a possessive relational nominal with an event predicate.

        The construction is selected exclusively from contribution kinds,
        kernel operators, participant-reference features and typed operator
        roles. It therefore applies to a newly designated relational target
        without requiring a language-pack regeneration or a domain dispatch.
        The introduced relative and event are candidate-local referents that
        the compiler materializes only if the enclosing claim is admitted.
        """
        possessives = [
            item for item in units
            if self._is_anchor(item)
            and self._features(item).get("possessive")
            and getattr(item, "semantic_ref", None)
        ]
        relations = [
            item for item in units
            if self._is_predicate(item)
            and self._features(item).get("kernel_operator_ref") == "op:relation"
            and getattr(item, "semantic_ref", None)
        ]
        events = [
            item for item in units
            if self._is_predicate(item)
            and self._features(item).get("kernel_operator_ref") == "op:event"
            and getattr(item, "semantic_ref", None)
        ]
        times = [
            item for item in units
            if self._is_anchor(item) and getattr(item, "atom_kind", None) == "time"
        ]
        if not possessives or not relations or not events:
            return []

        output: list[ChartGraphlet] = []
        for possessive in possessives[:4]:
            for relation in relations[:4]:
                if relation.token_start < possessive.token_end:
                    continue
                for event in events[:4]:
                    if event.token_start < relation.token_end:
                        continue
                    for time in (*times[:2], None):
                        selected = self._unique_units(
                            tuple(
                                item for item in (possessive, relation, event, time)
                                if item is not None
                            )
                        )
                        relative_token = "@Xrelative_" + stable(
                            "possessive-relative", hypothesis.hypothesis_ref,
                            possessive.unit_ref, relation.unit_ref,
                        )[-10:]
                        event_token = "@Xevent_" + stable(
                            "possessive-event", hypothesis.hypothesis_ref,
                            event.unit_ref, relative_token,
                        )[-10:]
                        relative = {"new": relative_token, "kind": "entity"}
                        relation_app = PropositionApplication.create(
                            "op:relation",
                            {
                                "role:subject": relative,
                                "role:relation": relation.semantic_ref,
                                "role:object": possessive.semantic_ref,
                            },
                        )
                        event_args: dict[str, Any] = {
                            "role:event": {"new": event_token, "kind": "event"},
                            "role:type": event.semantic_ref,
                            "role:actor": relative,
                        }
                        if time is not None:
                            event_args["role:time"] = time.semantic_ref
                        event_app = PropositionApplication.create("op:event", event_args)
                        role_map = {
                            possessive.unit_ref: "possessive_reference",
                            relation.unit_ref: "relation_predicate",
                            event.unit_ref: "event_predicate",
                        }
                        if time is not None:
                            role_map[time.unit_ref] = "time"
                        coverage = PropositionCoverage.create(
                            hypothesis.hypothesis_ref,
                            direct_unit_refs=(item.unit_ref for item in selected),
                            role_by_source_unit_ref=role_map,
                        )
                        graph = PropositionGraph.create(
                            (relation_app, event_app),
                            root_application_ref=event_app.application_ref,
                            force="claim",
                            coverage=coverage,
                            provenance={
                                "source": "possessive_relation_event",
                                "relation_ref": relation.semantic_ref,
                                "event_type_ref": event.semantic_ref,
                                "participant_ref": possessive.semantic_ref,
                            },
                        )
                        unit = PropositionUnit.create(
                            graph,
                            token_start=min(item.token_start for item in selected),
                            token_end=max(item.token_end for item in selected),
                            char_start=min(item.char_start for item in selected),
                            char_end=max(item.char_end for item in selected),
                            score=sum(float(item.score) for item in selected) + 0.7,
                            surface=" ".join(
                                item.surface for item in sorted(
                                    selected, key=lambda item: item.token_start
                                )
                            ),
                        )
                        output.append(
                            ChartGraphlet(
                                graph, unit, unit.score,
                                "possessive_relation_event",
                            )
                        )
        return output

    def _provenance_graphlets(
        self, hypothesis: Any, units: Sequence[Any], participant_frame: Any
    ) -> list[ChartGraphlet]:
        context = dict(getattr(participant_frame, "dialogue_context", {}) or {})
        focus = context.get("verified_semantic_focus")
        if not isinstance(focus, Mapping) or not focus.get("focus_ref"):
            return []
        force_units = [item for item in units if self._is_force(item)]
        anaphors = [
            item for item in units
            if self._features(item).get("anaphoric")
            or self._features(item).get("demonstrative")
        ]
        predicates = [
            item for item in units
            if self._is_predicate(item)
            and (
                self._features(item).get("evaluation_kind") in {
                    "answerability", "epistemic_support", "evidence",
                }
                or self._features(item).get("explanation_kind") in {
                    "evidence", "reason", "provenance",
                }
            )
        ]
        reason_force = any(
            self._features(item).get("question_domain") in {
                "reason", "manner", "evidence", "source",
            }
            for item in force_units
        )
        if not force_units or not anaphors or not predicates or not reason_force:
            return []
        target_refs = tuple(map(str, focus.get("target_refs", ())))
        target_ref = target_refs[0] if target_refs else participant_frame.addressee_ref
        evidence_var = "?supporting_evidence"
        app = PropositionApplication.create(
            "op:relation",
            {
                "role:subject": evidence_var,
                "role:relation": "rel:evidence_for",
                "role:object": target_ref,
            },
            qualifiers={"query_kind": "epistemic_provenance"},
        )
        selected = self._unique_units((*force_units, *predicates, *anaphors))
        role_map = {item.unit_ref: "force" for item in force_units}
        role_map.update({item.unit_ref: "predicate_head" for item in predicates})
        role_map.update({item.unit_ref: "reference" for item in anaphors})
        coverage = PropositionCoverage.create(
            hypothesis.hypothesis_ref,
            direct_unit_refs=(item.unit_ref for item in selected),
            role_by_source_unit_ref=role_map,
        )
        request = {
            "description_kind": "epistemic_provenance",
            "target_ref": target_ref,
            "focus_ref": str(focus["focus_ref"]),
        }
        graph = PropositionGraph.create(
            (app,), root_application_ref=app.application_ref, force="query",
            projected_variables=(evidence_var,),
            ports_provided=("argument:proposition",), coverage=coverage,
            provenance={
                "source": "verified_semantic_focus_provenance",
                "packet_qualifiers": {
                    "query_kind": "epistemic_provenance",
                    "focus_ref": str(focus["focus_ref"]),
                    "target_ref": target_ref,
                },
                "describe_request": request,
            },
        )
        unit = PropositionUnit.create(
            graph,
            token_start=min(item.token_start for item in selected),
            token_end=max(item.token_end for item in selected),
            char_start=min(item.char_start for item in selected),
            char_end=max(item.char_end for item in selected),
            score=sum(float(item.score) for item in selected) + 0.6,
            surface=" ".join(item.surface for item in sorted(selected, key=lambda x: x.token_start)),
        )
        return [ChartGraphlet(graph, unit, unit.score, "epistemic_provenance")]

    @classmethod
    def _candidate_score(
        cls, unit: Any, role: Mapping[str, Any], predicate: Any
    ) -> float:
        features = cls._features(unit)
        score = float(getattr(unit, "score", 0.0))
        semantic_port = role.get("semantic_port")
        if semantic_port and semantic_port in set(map(str, features.get("ports_provided", ()))):
            score += 0.45
        role_ref = str(role.get("role_ref", ""))
        if role_ref in {"role:actor", "role:subject", "role:experiencer"}:
            score += 0.08 if unit.token_end <= predicate.token_start else -0.04
        elif role_ref in {"role:object", "role:target", "role:content"}:
            score += 0.08 if unit.token_start >= predicate.token_end else -0.04
        return score

    @classmethod
    def _role_candidates(
        cls, role: Mapping[str, Any], units: Sequence[Any], predicate: Any,
        used_refs: set[str], proposition_taking: bool,
    ) -> list[Any]:
        filler_kinds = set(map(str, role.get("filler_kinds", ())))
        role_ref = str(role.get("role_ref", ""))
        output = []
        for unit in units:
            if unit.unit_ref in used_refs or unit.unit_ref == predicate.unit_ref:
                continue
            kind = getattr(unit, "kind", None)
            if kind == "proposition":
                if "app" in filler_kinds and proposition_taking:
                    output.append(unit)
                continue
            if kind not in {"anchor", "reference"} or not getattr(unit, "semantic_ref", None):
                continue
            # A predicate may only satisfy an app-valued role after the chart
            # has composed it into a proposition unit.  Treating its semantic
            # target as a bare atom consumes the child head and destroys the
            # recursive graph boundary.
            if cls._is_predicate(unit):
                continue
            atom_kind = str(getattr(unit, "atom_kind", ""))
            if not filler_kinds or "atom" in filler_kinds or atom_kind in filler_kinds:
                output.append(unit)
        return sorted(
            output,
            key=lambda item: (
                -cls._candidate_score(item, role, predicate),
                item.token_start, item.unit_ref,
            ),
        )

    def _frame_graphlets(
        self, hypothesis: Any, units: Sequence[Any], participant_frame: Any
    ) -> list[ChartGraphlet]:
        predicates = [
            item for item in units
            if self._features(item).get("contribution_kind") == "predicate"
            and self._features(item).get("kernel_operator_ref") in {
                "op:event", "op:relation", "op:type", "op:state",
            }
        ]
        force_host_ref = min(
            predicates,
            key=lambda item: (item.token_start, item.token_end, item.unit_ref),
        ).unit_ref if predicates else None
        output: list[ChartGraphlet] = []
        for predicate in predicates[:8]:
            features = self._features(predicate)
            operator = str(features["kernel_operator_ref"])
            semantic_ref = str(
                features.get("semantic_ref") or getattr(predicate, "semantic_ref", "")
            )
            if not semantic_ref:
                continue
            controlled_roles = {
                str(role): str(source)
                for role, source in dict(
                    features.get("controlled_role_bindings", {}) or {}
                ).items()
            }
            roles = sorted(
                (dict(item) for item in features.get("semantic_roles", ())),
                key=lambda item: (
                    str(item.get("role_ref", "")) in controlled_roles,
                    str(item.get("role_ref", "")),
                ),
            )
            proposition_taking = bool(features.get("proposition_taking"))
            base_args: dict[str, Any] = {}
            if operator == "op:event":
                base_args.update({
                    "role:event": "?event_" + stable("event-var", predicate.unit_ref)[-8:],
                    "role:type": semantic_ref,
                })
            elif operator == "op:relation":
                base_args["role:relation"] = semantic_ref
            elif operator == "op:type":
                base_args["role:class"] = semantic_ref
            else:
                base_args["role:dimension"] = semantic_ref

            # Beam entries preserve all bounded compatible role assignments rather
            # than greedily freezing the first surface-nearest filler.
            beam = [({
                "args": base_args,
                "direct_units": [predicate],
                "child_graphs": [],
                "role_map": {predicate.unit_ref: "predicate_head"},
                "used_refs": {predicate.unit_ref},
                "assignment_score": 0.0,
            })]
            for role in roles:
                role_ref = str(role.get("role_ref") or "")
                if not role_ref or role_ref in base_args:
                    continue
                next_beam = []
                for entry in beam:
                    default_source = role.get("default_source")
                    if default_source:
                        source_ref = {
                            "speaker": participant_frame.speaker_ref,
                            "addressee": participant_frame.addressee_ref,
                            "self": participant_frame.self_ref,
                        }.get(str(default_source))
                        if source_ref:
                            updated = {**entry, "args": {**entry["args"], role_ref: source_ref}}
                            next_beam.append(updated)
                            continue
                    candidates = self._role_candidates(
                        role, units, predicate, set(entry["used_refs"]), proposition_taking
                    )[: self.limits.max_graphlets_per_cell]
                    if (
                        not candidates
                        and role_ref in controlled_roles
                        and entry["child_graphs"]
                    ):
                        inherited = None
                        for child in reversed(entry["child_graphs"]):
                            root = next(
                                (
                                    app for app in child.applications
                                    if app.application_ref == child.root_application_ref
                                ),
                                None,
                            )
                            if root is not None:
                                inherited = root.args.get(controlled_roles[role_ref])
                            if isinstance(inherited, str):
                                break
                        if isinstance(inherited, str):
                            next_beam.append({
                                **entry,
                                "args": {**entry["args"], role_ref: inherited},
                            })
                            continue
                    # Optional roles admit an explicit empty assignment even
                    # when compatible evidence exists; otherwise an optional
                    # adjunct greedily consumes the only filler needed by a
                    # required role or an enclosing frame.
                    if not role.get("required", True):
                        next_beam.append(entry)
                    for selected in candidates:
                        args = dict(entry["args"])
                        direct_units = list(entry["direct_units"]) + [selected]
                        child_graphs = list(entry["child_graphs"])
                        role_map = dict(entry["role_map"])
                        role_map[selected.unit_ref] = role_ref.split(":", 1)[-1]
                        if getattr(selected, "kind", None) == "proposition":
                            child = selected.proposition
                            child_graphs.append(child)
                            args[role_ref] = {"app": child.root_application_ref}
                        else:
                            args[role_ref] = selected.semantic_ref
                        next_beam.append({
                            "args": args,
                            "direct_units": direct_units,
                            "child_graphs": child_graphs,
                            "role_map": role_map,
                            "used_refs": set(entry["used_refs"]) | {selected.unit_ref},
                            "assignment_score": float(entry["assignment_score"])
                                + self._candidate_score(selected, role, predicate),
                        })
                beam = sorted(
                    next_beam,
                    key=lambda entry: (
                        -float(entry["assignment_score"]),
                        tuple(sorted(entry["used_refs"])),
                    ),
                )[: self.limits.max_graphlets_per_cell]
                if not beam:
                    break

            for entry in beam:
                args = dict(entry["args"])
                direct_units = list(entry["direct_units"])
                child_graphs = list(entry["child_graphs"])
                role_map = dict(entry["role_map"])
                used_refs = set(entry["used_refs"])
                force_units = [
                    item for item in units
                    if predicate.unit_ref == force_host_ref
                    and self._is_force(item) and item.unit_ref not in used_refs
                ]
                structural = [
                    item for item in units
                    if self._is_structural(item)
                    and not self._is_force(item)
                    and item.unit_ref not in used_refs
                    and getattr(item, "kind", None) != "proposition"
                ]
                for item in self._unique_units((*force_units, *structural)):
                    used_refs.add(item.unit_ref)
                    direct_units.append(item)
                    role_map[item.unit_ref] = (
                        "force" if item in force_units
                        else "binder" if self._features(item).get("copular")
                        else "scope"
                    )

                standalone = bool(features.get("standalone_licensed"))
                if not child_graphs and not standalone:
                    minimum = 2 if operator == "op:event" else 1
                    if len(args) <= minimum:
                        continue
                child_apps = [app for graph in child_graphs for app in graph.applications]
                parent = PropositionApplication.create(
                    operator, args,
                    qualifiers={
                        "semantic_frame_ref": features.get("affordance_ref"),
                        "evaluation_kind": features.get("evaluation_kind"),
                    },
                )
                applications = tuple((*child_apps, parent))
                if len(applications) > MAX_PROPOSITION_APPLICATIONS:
                    continue
                child_coverages = [graph.coverage for graph in child_graphs if graph.coverage]
                child_refs = [graph.proposition_ref for graph in child_graphs]
                child_unit_refs = {
                    unit.unit_ref for unit in direct_units
                    if getattr(unit, "kind", None) == "proposition"
                }
                direct_refs = [
                    unit.unit_ref for unit in self._unique_units(direct_units)
                    if unit.unit_ref not in child_unit_refs
                ]
                coverage = PropositionCoverage.create(
                    hypothesis.hypothesis_ref,
                    direct_unit_refs=direct_refs,
                    child_coverages=child_coverages,
                    child_proposition_refs=child_refs,
                    role_by_source_unit_ref={
                        ref: role for ref, role in role_map.items() if ref in set(direct_refs)
                    },
                )
                depth = 1 + max((graph.depth for graph in child_graphs), default=0)
                if depth > self.limits.max_depth:
                    continue
                force = "query" if force_units else str(features.get("default_force") or "claim")
                query_kind = (
                    "embedded_proposition_query" if child_refs and force == "query"
                    else "event_query" if force == "query"
                    else None
                )
                packet_qualifiers = {
                    "construction_family": "core_frame_application",
                    "semantic_frame_ref": features.get("affordance_ref"),
                    "predicate_ref": semantic_ref,
                    "evaluation_kind": features.get("evaluation_kind"),
                    "embedded_proposition_refs": child_refs,
                    "embedded_proposition_graphs": [graph.as_dict() for graph in child_graphs],
                    "response_expectation": features.get("response_expectation"),
                    "answer_mode": "boolean" if force == "query" else None,
                    "query_kind": query_kind,
                }
                graph = PropositionGraph.create(
                    applications, root_application_ref=parent.application_ref,
                    force=force, ports_provided=("argument:proposition",), depth=depth,
                    coverage=coverage,
                    provenance={
                        "source": "semantic_frame",
                        "packet_qualifiers": packet_qualifiers,
                        "embedded_proposition_graphs": [graph.as_dict() for graph in child_graphs],
                    },
                )
                token_units = list(self._unique_units(direct_units))
                unit = PropositionUnit.create(
                    graph,
                    token_start=min(item.token_start for item in token_units),
                    token_end=max(item.token_end for item in token_units),
                    char_start=min(item.char_start for item in token_units),
                    char_end=max(item.char_end for item in token_units),
                    score=sum(float(getattr(item, "score", 0.0)) for item in token_units)
                        + float(entry["assignment_score"]) + 0.5 - 0.04 * depth
                        + (0.3 if force == "query" else 0.0)
                        + (
                            0.28
                            if str(features.get("affordance_ref", "")).startswith("frame:")
                            else 0.0
                        ),
                    surface=" ".join(
                        item.surface for item in sorted(token_units, key=lambda x: x.token_start)
                    ),
                )
                output.append(ChartGraphlet(graph, unit, unit.score, "semantic_frame"))
        return sorted(
            output, key=lambda item: (-item.score, item.proposition.proposition_ref)
        )[: self.limits.max_total_graphlets]

    def _standalone_final(
        self, hypothesis: Any, graphlet: ChartGraphlet
    ) -> Candidate | None:
        original = tuple(hypothesis.units)
        # Discourse force is clause-level evidence.  Once the form layer has
        # supplied interrogative evidence, a force-less graph cannot be a
        # complete reading of the same source units.  Rejecting it here keeps
        # the evidence in the semantic graph rather than relying on a ranking
        # bonus to repair an otherwise invalid alternative.
        if any(self._is_force(unit) for unit in original) and (
            graphlet.proposition.force != "query"
        ):
            return None
        coverage_source = graphlet.proposition.coverage
        expanded = set(coverage_source.expanded_unit_refs if coverage_source else ())
        # A child graph owns the source units it consumes.  Carry those exact
        # assignments into the top-level receipt so recursive composition does
        # not turn valid child evidence into an unassigned residual.
        merged_roles: dict[str, str] = {}
        stack = [graphlet.proposition]
        while stack:
            graph = stack.pop()
            if graph.coverage:
                merged_roles.update(graph.coverage.role_by_source_unit_ref)
            for child_packet in dict(graph.provenance or {}).get(
                "embedded_proposition_graphs", ()
            ):
                try:
                    stack.append(PropositionGraph.from_dict(child_packet))
                except (KeyError, TypeError, ValueError):
                    continue
        coverage = CoveragePolicy.build(
            original,
            expanded,
            role_by_unit_ref=merged_roles,
            required_semantic_roles=(),
            required_semantic_slots=(),
            schema_ref="core:recursive-composition:v1",
            hypothesis_ref=hypothesis.hypothesis_ref,
            match_seed_ref=stable(
                "recursive-composition-match-seed-v1",
                graphlet.proposition.proposition_ref,
            ),
            seed=graphlet.proposition.semantic_signature,
        )
        if not coverage.executable:
            return None
        trace = {
            "source": "recursive_atomic_composition",
            "candidate_ref": graphlet.proposition.proposition_ref,
            "construction_ref": "core:recursive-composition:v1",
            "construction_evidence_ref": graphlet.proposition.proposition_ref,
            "match_seed_ref": coverage.match_seed_ref,
            "hypothesis_ref": hypothesis.hypothesis_ref,
            "coverage": coverage.as_dict(),
            "proposition_graph": graphlet.proposition.as_dict(),
            "composition_depth": graphlet.proposition.depth,
            "expanded_source_unit_refs": sorted(expanded),
        }
        return Candidate(graphlet.proposition.packet(), graphlet.score, trace)

    @staticmethod
    def _replace_span(
        units: Sequence[Any], graphlet: ChartGraphlet
    ) -> tuple[Any, ...] | None:
        coverage = graphlet.proposition.coverage
        covered = set(coverage.expanded_unit_refs if coverage else ())
        selected = [item for item in units if item.unit_ref in covered]
        if not selected:
            return None
        remaining = [item for item in units if item.unit_ref not in covered]
        output = sorted(
            (*remaining, graphlet.unit),
            key=lambda item: (item.token_start, item.token_end, item.unit_ref),
        )
        seen: set[str] = set()
        for unit in output:
            if getattr(unit, "kind", None) != "proposition":
                continue
            refs = set(unit.proposition.coverage.expanded_unit_refs)
            if seen.intersection(refs):
                return None
            seen.update(refs)
        return tuple(output)

    @staticmethod
    def _residual_refs(residual: Mapping[str, Any]) -> tuple[str, ...]:
        refs = residual.get("unit_refs")
        if isinstance(refs, (list, tuple)):
            return tuple(map(str, refs))
        ref = residual.get("unit_ref")
        return (str(ref),) if ref else ()

    def compose(
        self, resolved: Any, participant_frame: Any, language: str
    ) -> CompositionResult:
        complete: list[Candidate] = []
        all_graphlets: dict[tuple[str, tuple[str, ...]], ChartGraphlet] = {}
        gaps: list[CompositionGap] = []
        states_examined = scopes_examined = max_depth = pruned = 0

        hypotheses = tuple(getattr(resolved, "grounding_hypotheses", ()))
        hypothesis_count = max(1, len(hypotheses))
        per_hypothesis_budget = max(1, self.limits.state_budget // hypothesis_count)
        per_hypothesis_graphlet_budget = max(
            1, self.limits.max_total_graphlets // hypothesis_count
        )
        for hypothesis in hypotheses:
            queue: list[tuple[Any, ...]] = [tuple(hypothesis.units)]
            seen_states: set[tuple[str, ...]] = set()
            hypothesis_graphlets: dict[
                tuple[str, tuple[str, ...]], ChartGraphlet
            ] = {}
            hypothesis_states = 0
            while queue and hypothesis_states < per_hypothesis_budget:
                units = queue.pop(0)
                state_key = tuple(item.unit_ref for item in units)
                if state_key in seen_states:
                    continue
                seen_states.add(state_key)
                states_examined += 1
                hypothesis_states += 1
                for scope in self._scopes(
                    SimpleNamespace(hypothesis_ref=hypothesis.hypothesis_ref, units=units)
                ):
                    scopes_examined += 1
                    schema_graphlets, partial = self._schema_graphlets(
                        hypothesis, scope, participant_frame, language
                    )
                    native = self._description_graphlets(hypothesis, scope)
                    native.extend(
                        self._definition_description_graphlets(hypothesis, scope)
                    )
                    native.extend(
                        self._possessive_relation_event_graphlets(hypothesis, scope)
                    )
                    native.extend(
                        self._provenance_graphlets(hypothesis, scope, participant_frame)
                    )
                    native.extend(
                        self._frame_graphlets(hypothesis, scope, participant_frame)
                    )
                    cell: dict[tuple[str, tuple[str, ...]], ChartGraphlet] = {}
                    for graphlet in (*schema_graphlets, *native):
                        expanded = tuple(sorted(
                            graphlet.proposition.coverage.expanded_unit_refs
                            if graphlet.proposition.coverage else ()
                        ))
                        key = (graphlet.proposition.semantic_signature, expanded)
                        prior = cell.get(key)
                        if prior is None or graphlet.score > prior.score:
                            cell[key] = graphlet
                    selected_graphlets = sorted(
                        cell.values(), key=lambda item: (-item.score, item.proposition.proposition_ref)
                    )[: self.limits.max_graphlets_per_cell]
                    pruned += max(0, len(cell) - len(selected_graphlets))
                    for graphlet in selected_graphlets:
                        expanded = tuple(sorted(graphlet.proposition.coverage.expanded_unit_refs))
                        key = (graphlet.proposition.semantic_signature, expanded)
                        prior = hypothesis_graphlets.get(key)
                        if prior is None or graphlet.score > prior.score:
                            hypothesis_graphlets[key] = graphlet
                        max_depth = max(max_depth, graphlet.proposition.depth)
                        final = self._standalone_final(hypothesis, graphlet)
                        if final is not None:
                            complete.append(final)
                        if (
                            graphlet.proposition.depth < self.limits.max_depth
                        ):
                            replaced = self._replace_span(units, graphlet)
                            if replaced and tuple(item.unit_ref for item in replaced) != state_key:
                                queue.append(replaced)
                    for item in partial[:2]:
                        critical = tuple(
                            residual.as_dict()
                            for residual in item.coverage.critical_residuals
                        )
                        if not critical or len(gaps) >= self.limits.max_partial_gaps:
                            continue
                        unknown = tuple(
                            ref for residual in critical
                            if residual.get("residual_class") == "unknown_form"
                            for ref in self._residual_refs(residual)
                        )
                        known = tuple(
                            ref for residual in critical
                            if residual.get("residual_class") != "unknown_form"
                            for ref in self._residual_refs(residual)
                        )
                        gap_kind = (
                            "unknown_form" if unknown and not known
                            else "missing_proposition_link"
                            if any(getattr(unit, "kind", None) == "proposition" for unit in units)
                            else "known_form_composition_gap"
                        )
                        gaps.append(CompositionGap.create(
                            gap_kind,
                            hypothesis.hypothesis_ref,
                            self._scope_ref(hypothesis.hypothesis_ref, scope),
                            unsatisfied_ports=getattr(
                                item.coverage, "missing_semantic_roles", ()
                            ),
                            source_unit_refs=tuple(
                                ref for residual in critical
                                for ref in self._residual_refs(residual)
                            ),
                            known_unit_refs=known,
                            unknown_unit_refs=unknown,
                            evidence={
                                "schema_ref": item.schema_ref,
                                "coverage": item.coverage.as_dict(),
                            },
                        ))
                # Retain only the configured number of graphlets, but allow
                # one chart expansion beyond the leaf state.  Without that
                # expansion, a busy leaf cell can exhaust its storage quota
                # before any app-valued parent has a chance to consume it.
                if (
                    len(hypothesis_graphlets) >= per_hypothesis_graphlet_budget
                    and hypothesis_states >= 4
                ):
                    break
            for key, graphlet in sorted(
                hypothesis_graphlets.items(),
                key=lambda item: (-item[1].score, item[1].proposition.proposition_ref),
            )[:per_hypothesis_graphlet_budget]:
                prior = all_graphlets.get(key)
                if prior is None or graphlet.score > prior.score:
                    all_graphlets[key] = graphlet
            if hypothesis_states >= per_hypothesis_budget and queue:
                gaps.append(CompositionGap.create(
                    "budget_exhausted", hypothesis.hypothesis_ref,
                    stable("composition-scope-budget", hypothesis.hypothesis_ref),
                    source_unit_refs=(item.unit_ref for item in hypothesis.units),
                    evidence={
                        "state_budget": self.limits.state_budget,
                        "per_hypothesis_budget": per_hypothesis_budget,
                    },
                ))

        by_signature: dict[tuple[str, str], Candidate] = {}
        for candidate in complete:
            trace = dict(candidate.trace or {})
            graph = dict(trace.get("proposition_graph", {}) or {})
            key = (
                str(graph.get("semantic_signature")),
                str(trace.get("hypothesis_ref")),
            )
            prior = by_signature.get(key)
            if prior is None or float(candidate.score) > float(prior.score):
                by_signature[key] = candidate
        candidates = tuple(sorted(
            by_signature.values(),
            key=lambda item: (-float(item.score), str(item.trace.get("candidate_ref"))),
        ))
        graphlets = tuple(sorted(
            all_graphlets.values(),
            key=lambda item: (-item.score, item.proposition.proposition_ref),
        ))
        gap_by_ref = {gap.gap_ref: gap for gap in gaps}
        ordered_gaps = tuple(sorted(
            gap_by_ref.values(), key=lambda item: (item.kind, item.gap_ref)
        )[: self.limits.max_partial_gaps])
        diagnostics = {
            "atomic_composition_abi": ATOMIC_COMPOSITION_ABI,
            "states_examined": states_examined,
            "scopes_examined": scopes_examined,
            "graphlets_generated": len(graphlets),
            "graphlets_pruned": pruned,
            "complete_candidate_count": len(candidates),
            "gap_count": len(ordered_gaps),
            "max_depth_reached": max_depth,
            "bounds": vars(self.limits),
        }
        return CompositionResult(
            candidates, graphlets,
            ordered_gaps, diagnostics,
        )
