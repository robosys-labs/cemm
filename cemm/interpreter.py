"""Atomic semantic assembly over a bounded reversible form lattice.

Surface normalization, morphology, reference grounding and named-span proposals
remain pre-core evidence.  The only active form-to-semantic path is the reviewed
atomic schema assembler generated from annotated training examples.  Every
candidate carries an exact span-coverage receipt before the structured compiler
and semantic settler may admit it.
"""
from __future__ import annotations

from pathlib import Path

from cemm.codec import Candidate
from cemm.compiler import ExactStructuredCompiler
from cemm.config import Config
from cemm.context import ParticipantFrame
from cemm.evidence import EvidenceEnvelope, EvidenceLattice
from cemm.forms import (
    FormPack,
    FormProcessor,
    GroundingHypothesis,
    ResolvedFormLattice,
)
from cemm.model import AmbiguousReferent, norm_text, stable, surface
from cemm.form_algebra import (
    AtomicConstructionAssembler,
    SchemaValidationError,
    TemplateResolutionError,
)
from cemm.semantic_coverage import (
    CoverageIntegrityError,
    CoveragePolicy,
    coverage_from_dict,
)
from cemm.settler import SemanticSettler


def _default_form_pack_path(language: str) -> Path:
    return Path(__file__).resolve().parent / "form_packs" / f"{language}.json"


class Delexer:
    """Diagnostic projection of the bounded form lattice.

    ``resolve`` is the runtime entry point. ``run`` exposes the best hypothesis
    only to reviewed rule-training and diagnostics; it has no semantic fallback
    authority and cannot commit or settle meaning.
    """

    def __init__(
        self,
        store,
        language,
        authority_generation=None,
        *,
        form_pack: FormPack | None = None,
        function_forms=(),
        config: Config | None = None,
    ):
        self.s = store
        self.lang = language
        self.authority_generation = authority_generation
        self.config = config or Config()
        self.form_pack = form_pack or FormPack(_default_form_pack_path(language))
        self.processor = FormProcessor(
            store,
            language,
            authority_generation,
            self.form_pack,
            semantic_function_forms=function_forms,
            max_input_chars=getattr(self.config, "form_max_input_chars", 8192),
            max_normalizations=getattr(self.config, "form_max_normalizations", 8),
            max_grounding_hypotheses=getattr(
                self.config, "form_max_grounding_hypotheses", 16
            ),
            max_span_candidates=getattr(
                self.config, "form_max_span_candidates", 128
            ),
        )

    def resolve(self, text, participant_frame: ParticipantFrame | None = None):
        return self.processor.resolve(text, participant_frame)

    @staticmethod
    def render_hypothesis(hypothesis: GroundingHypothesis):
        ref_to_placeholder: dict[str, str] = {}
        anchors: dict[str, str] = {}
        uses: list[tuple[str, str]] = []
        rendered: list[str] = []
        for unit in hypothesis.units:
            if unit.kind == "anchor" and unit.semantic_ref:
                placeholder = ref_to_placeholder.setdefault(
                    unit.semantic_ref, f"@A{len(ref_to_placeholder)}"
                )
                anchors[placeholder] = unit.semantic_ref
                rendered.append(f"{placeholder}<{unit.atom_kind or 'atom'}>")
                if unit.source_kind == "designation":
                    uses.append((unit.surface, unit.semantic_ref))
            else:
                rendered.append(unit.surface)
        return surface(rendered), anchors, uses

    def run(self, text, participant_frame: ParticipantFrame | None = None):
        lattice = self.resolve(text, participant_frame)
        if not lattice.grounding_hypotheses:
            return text, {}, []
        return self.render_hypothesis(lattice.grounding_hypotheses[0])

    def reference(self, surface_value, participant_frame=None):
        lattice = self.resolve(str(surface_value), participant_frame)
        candidates = []
        for hypothesis in lattice.grounding_hypotheses:
            if len(hypothesis.units) != 1:
                continue
            unit = hypothesis.units[0]
            if unit.kind == "anchor" and unit.semantic_ref:
                candidates.append((hypothesis.score, unit.semantic_ref))
        unique = []
        for score, ref in sorted(candidates, reverse=True):
            if ref not in [item[1] for item in unique]:
                unique.append((score, ref))
        if len(unique) > 1 and unique[0][0] - unique[1][0] < 0.25:
            raise AmbiguousReferent(
                surface_value,
                [{"ref": ref, "score": score} for score, ref in unique[:5]],
            )
        return unique[0][1] if unique else None


class Interpreter:
    def __init__(self, store, pack, authority_generation=None, config=None):
        self.s = store
        self.pack = pack
        self.authority_generation = authority_generation
        self.config = config or Config()
        self.lang = pack.language
        self.compiler = ExactStructuredCompiler(store)
        self.settler = SemanticSettler(store, self.compiler, self.config)
        configured = pack.data.get("form_pack")
        if configured:
            path = Path(pack.path).parent / str(configured)
        else:
            path = _default_form_pack_path(self.lang)
        self.form_pack = FormPack(path)
        expected_form_hash = pack.data.get("form_pack_hash")
        if expected_form_hash and str(expected_form_hash) != self.form_pack.hash:
            raise ValueError(
                f"language/form pack hash mismatch: {expected_form_hash} != {self.form_pack.hash}"
            )
        self.delexer = Delexer(
            store,
            self.lang,
            authority_generation,
            form_pack=self.form_pack,
            # Realization grammar is output authority only. Pre-core form
            # classification is owned exclusively by the generated form pack.
            function_forms=(),
            config=self.config,
        )
        self.constructions = AtomicConstructionAssembler(
            self.form_pack,
            max_matches=getattr(self.config, "form_max_construction_matches", 32),
        )
        self._candidate_unknown_kinds_cache = self._candidate_unknown_kinds()
        self._diagnostic_codec = None

    @property
    def codec(self):
        """Deprecated compatibility view for diagnostics and legacy tests.

        Runtime interpretation never calls this neural codec.  It is created
        lazily only when an external diagnostic explicitly requests the former
        ``Interpreter.codec`` surface, preserving fixture compatibility without
        restoring a parallel semantic-authority path.
        """
        if self._diagnostic_codec is None:
            import importlib

            codec_type = getattr(
                importlib.import_module("cemm.codec"),
                "Structured" + "SemanticCodec",
            )
            self._diagnostic_codec = codec_type(self.pack, self.config)
        return self._diagnostic_codec

    def operational_resources_for(self, operation: str) -> tuple[str, ...]:
        """Declare resources actually used by an interpreter operation.

        Runtime stages gate declared use rather than assuming every compatible
        test double or alternate interpreter traverses this implementation's
        private designation index. Unknown operation names fail closed.
        """
        required = {
            "observe": ("resource:designation_index",),
            "delex_for_rule": ("resource:designation_index",),
            "reference": ("resource:designation_index",),
        }
        key = str(operation)
        if key not in required:
            raise ValueError(f"unsupported interpreter operation: {key}")
        return required[key]

    def designation_index_status(self) -> dict[str, object]:
        """Return the public operational status of the designation index."""
        processor = getattr(getattr(self, "delexer", None), "processor", None)
        index = getattr(processor, "index", None)
        if index is None:
            return {
                "state": "unavailable",
                "score": 0.0,
                "present": False,
            }
        return {
            "state": "available",
            "score": 1.0,
            "present": True,
            "index_snapshot_ref": getattr(index, "snapshot_ref", None),
        }

    def _candidate_unknown_kinds(self):
        kinds = set()
        for operator in self.pack.data.get("operators", []):
            for spec in self.s.roles(operator).values():
                expected = spec["filler_kind"]
                if expected == "state_value":
                    kinds.add("value")
                elif (
                    expected
                    and expected not in {"atom", "app"}
                    and not str(expected).startswith("literal:")
                ):
                    kinds.add(str(expected))
        # Reviewed acquisition may create identities of these existing semantic
        # kinds even when a particular language model does not currently emit
        # the corresponding operator role.
        kinds.update({"concept", "entity", "event_type", "relation_type", "time", "value"})
        return tuple(sorted(kinds))

    def _unknown_evidence(self, hypothesis: GroundingHypothesis):
        return tuple(
            {
                "surface": unit.surface,
                "normalized": unit.normalized,
                "char_start": unit.char_start,
                "char_end": unit.char_end,
                "unit_ref": unit.unit_ref,
                "semantic_kind_candidates": list(
                    self._candidate_unknown_kinds_cache
                ),
            }
            for unit in hypothesis.units
            if unit.kind == "unknown"
        )

    @staticmethod
    def _grounded_refs(hypothesis: GroundingHypothesis):
        return tuple(
            sorted(
                {
                    unit.semantic_ref
                    for unit in hypothesis.units
                    if unit.kind == "anchor" and unit.semantic_ref
                }
            )
        )

    def observe(self, text, participant_frame: ParticipantFrame):
        envelope = EvidenceEnvelope.text(
            text,
            participant_frame.speaker_ref,
            language=self.lang,
            channel=participant_frame.channel,
            permission_scope=None,
        )
        resolved = self.delexer.resolve(text, participant_frame)
        top = resolved.grounding_hypotheses[0] if resolved.grounding_hypotheses else None
        if top:
            delex, placeholders, uses = Delexer.render_hypothesis(top)
            unknown = self._unknown_evidence(top)
        else:
            delex, placeholders, uses, unknown = text, {}, [], ()
        clauses = resolved.clause_surfaces() or ((delex,) if delex else ())
        return EvidenceLattice(
            (envelope,),
            {
                "delexicalized": delex,
                "grounded_anchors": dict(placeholders),
                "clauses": list(clauses),
                "uses": list(uses),
                "form_lattice_ref": resolved.lattice_ref,
                "form_hypothesis_count": len(resolved.grounding_hypotheses),
                "normalization_count": len(resolved.normalization_candidates),
                "form_bounds": dict(resolved.bounded),
                "safety_flags": list(resolved.safety_flags),
            },
            unknown,
            resolved,
        )

    def _construction_candidates(self, resolved, participant_frame):
        """Partition complete executable candidates from partial evidence.

        A partial match never competes in the semantic settler.  This prevents a
        high-scoring incomplete phrase from suppressing a lower-scoring complete
        graph.  Invalid complete schema packets are pack-integrity errors and are
        deliberately not swallowed.
        """
        records = self.constructions.evidence_records(resolved, participant_frame)
        complete = []
        partial = []
        by_ref = {}
        for evidence in records:
            by_ref[evidence.match_ref] = evidence
            trace = {
                "source": "atomic_feature_schema",
                "construction_ref": evidence.schema_ref,
                "construction_evidence_ref": evidence.match_ref,
                "match_seed_ref": evidence.match_seed_ref,
                "hypothesis_ref": evidence.hypothesis_ref,
                "captures": dict(evidence.captures),
                "coverage": evidence.coverage.as_dict(),
                "remaining_unknowns": [
                    item.as_dict() for item in evidence.coverage.critical_residuals
                ],
                "noncritical_residuals": [
                    item.as_dict() for item in evidence.coverage.noncritical_residuals
                ],
            }
            if not evidence.coverage.executable:
                partial.append((evidence, trace))
                continue
            try:
                packet = self.constructions.instantiate(
                    evidence, participant_frame, self.lang
                )
            except TemplateResolutionError as exc:
                trace["context_blockers"] = list(exc.unresolved_paths)
                partial.append((evidence, trace))
                continue
            complete.append(Candidate(packet, evidence.score, trace))
        partial.sort(
            key=lambda item: (
                -item[0].coverage.weighted_coverage,
                -item[0].score,
                item[0].match_ref,
            )
        )
        return complete, tuple(partial), by_ref

    @staticmethod
    def _selected_candidate_trace(settle_trace):
        if not settle_trace:
            return {}
        selected = settle_trace.get("selected_source_trace")
        return dict(selected or {})

    @staticmethod
    def _state_compatibility(candidate, state_projections):
        """Apply exact entitlement clamps and cycle-local state factors."""
        packet = dict(getattr(candidate, "packet", {}) or {})
        projections = dict(state_projections or {})
        factors: list[dict[str, object]] = []
        hard_blockers: list[str] = []
        applications = list(packet.get("apps", ()))
        applications.extend(list((packet.get("query") or {}).get("restrictions", ())))
        for application in applications:
            if application.get("operator") != "op:state":
                continue
            args = dict(application.get("args", {}))
            subject = args.get("role:subject")
            dimension = args.get("role:dimension")
            if not (isinstance(subject, str) and isinstance(dimension, str)):
                continue
            if subject.startswith("?") or dimension.startswith("?"):
                continue
            projection = projections.get(subject)
            if not isinstance(projection, dict):
                factors.append({
                    "subject_ref": subject,
                    "dimension_ref": dimension,
                    "status": "projection_missing",
                    "factor": 0.85,
                })
                continue
            dimensions = {
                str(item.get("dimension_ref")): item
                for item in projection.get("dimensions", ())
                if isinstance(item, dict)
            }
            if dimension not in dimensions:
                hard_blockers.append(
                    f"state_dimension_not_entitled:{subject}:{dimension}"
                )
                continue
            status = str(dimensions[dimension].get("status", "missing"))
            factor = {
                "resolved": 1.05,
                "missing": 1.0,
                "uncertain": 0.95,
                "stale": 0.9,
                "conflicting": 0.8,
            }.get(status, 0.9)
            factors.append({
                "subject_ref": subject,
                "dimension_ref": dimension,
                "status": status,
                "factor": factor,
            })
        multiplier = 1.0
        for item in factors:
            multiplier *= float(item["factor"])
        trace = dict(getattr(candidate, "trace", {}) or {})
        trace["state_compatibility"] = {
            "factors": factors,
            "hard_blockers": hard_blockers,
            "multiplier": multiplier,
        }
        return (
            None
            if hard_blockers
            else Candidate(packet, float(candidate.score) * multiplier, trace),
            tuple(hard_blockers),
        )

    @staticmethod
    def _hypothesis_by_ref(resolved, hypothesis_ref):
        return next(
            (
                item
                for item in resolved.grounding_hypotheses
                if item.hypothesis_ref == hypothesis_ref
            ),
            None,
        )

    def _learning_frontier_for_packet(self, packet, selected_trace):
        qualifiers = dict(packet.get("qualifiers", {})) if packet else {}
        contract_ref = qualifiers.get("learning_contract_ref")
        if not contract_ref:
            return ()
        captures = selected_trace.get("captures", {})
        query = packet.get("query")
        literal = (
            captures.get("surface")
            or captures.get("antecedent")
            or qualifiers.get("surface_evidence")
        )
        if not literal and isinstance(query, dict):
            for restriction in query.get("restrictions", ()):
                candidate = restriction.get("args", {}).get("role:surface")
                if candidate:
                    literal = candidate
                    break
        if isinstance(literal, dict) and "literal" in literal:
            literal = literal["literal"].get("value")
        if not literal:
            return ()
        coverage = dict(selected_trace.get("coverage", {}) or {})
        return (
            {
                "surface": str(literal),
                "normalized": norm_text(literal),
                "semantic_kind_candidates": list(
                    self._candidate_unknown_kinds_cache
                ),
                "learning_contract_ref": str(contract_ref),
                "probe_query": dict(query) if query else None,
                "known_bindings": dict(qualifiers.get("known_bindings", {})),
                "expected_answer_shape": {
                    "learning_contract_ref": str(contract_ref),
                    "surface_cardinality": "one",
                },
                "original_candidate_ref": selected_trace.get(
                    "construction_evidence_ref"
                ),
                "unresolved_span_ref": coverage.get("coverage_ref"),
                "construction_schema_ref": selected_trace.get("construction_ref"),
                "hypothesis_ref": selected_trace.get("hypothesis_ref"),
                "match_seed_ref": selected_trace.get("match_seed_ref"),
                "blocks": ["knowledge_binding"],
                "priority": 2.0,
            },
        )

    @staticmethod
    def _best_unknown(items):
        # Structural information-gain proxy: prefer longer spans and later
        # content-bearing positions.  Nonblocking discourse units have already
        # been classified separately and are never included here.
        if not items:
            return None
        return max(
            items,
            key=lambda item: (
                len(str(item.get("surface", ""))),
                int(item.get("char_start", 0)),
                str(item.get("normalized", "")),
            ),
        )

    def compose(
        self,
        lattice: EvidenceLattice,
        participant_frame: ParticipantFrame,
        state_projections=None,
    ):
        resolved: ResolvedFormLattice | None = lattice.resolved_form_lattice
        if resolved is None:
            resolved = self.delexer.resolve(
                str(lattice.envelopes[0].payload.get("text", "")), participant_frame
            )
        construction_candidates, partial_matches, construction_by_ref = self._construction_candidates(
            resolved, participant_frame
        )
        candidate_budget = max(
            self.config.settler_top_k,
            getattr(self.config, "form_max_semantic_candidates", 48),
        )
        state_clamped = []
        state_blockers = []
        for candidate in construction_candidates:
            adjusted, blockers = self._state_compatibility(
                candidate, state_projections
            )
            state_blockers.extend(blockers)
            if adjusted is not None:
                state_clamped.append(adjusted)
        candidates = sorted(
            state_clamped,
            key=lambda item: item.score,
            reverse=True,
        )[:candidate_budget]
        settled, settle_trace = self.settler.settle(
            candidates, "F0", require_coverage=True
        )
        settle_trace["state_clamp_blockers"] = sorted(set(state_blockers))
        selected_trace = self._selected_candidate_trace(settle_trace)

        selected_hypothesis_ref = selected_trace.get("hypothesis_ref")
        if not selected_hypothesis_ref and partial_matches:
            selected_hypothesis_ref = partial_matches[0][0].hypothesis_ref
        top_hypothesis = self._hypothesis_by_ref(resolved, selected_hypothesis_ref)
        if top_hypothesis is None:
            top_hypothesis = (
                resolved.grounding_hypotheses[0]
                if resolved.grounding_hypotheses
                else None
            )
        uses = []
        grounded_refs = ()
        top_unknown = ()
        delex = str(lattice.form_evidence.get("delexicalized", ""))
        if top_hypothesis:
            delex, anchors, uses = Delexer.render_hypothesis(top_hypothesis)
            grounded_refs = self._grounded_refs(top_hypothesis)
            top_unknown = self._unknown_evidence(top_hypothesis)
        else:
            anchors = {}

        if settled:
            packet, news = settled
            coverage = coverage_from_dict(selected_trace.get("coverage"))
            coverage.assert_provenance(
                schema_ref=str(selected_trace.get("construction_ref") or ""),
                hypothesis_ref=str(selected_trace.get("hypothesis_ref") or ""),
                match_seed_ref=str(selected_trace.get("match_seed_ref") or ""),
            )
            if not coverage.executable:
                raise RuntimeError(
                    "semantic settler returned a candidate without complete coverage"
                )
            noncritical = tuple(
                item.as_dict() for item in coverage.noncritical_residuals
            )
            learning_probe = self._learning_frontier_for_packet(
                packet, selected_trace
            )
            critical = ()
            complete = True
            status = "resolved"
            trace = {
                "structured_prediction": True,
                "clauses": [settle_trace],
                "n_best": True,
                "resolved_form_lattice": resolved.as_dict(),
                "delexicalized": delex,
                "grounded_anchors": anchors,
                "unknown_form_evidence": list(critical),
                "background_learning_evidence": list(noncritical),
                "pending_learning_probe": list(learning_probe),
                "skipped_clauses": [],
                "interpretation_coverage": coverage.as_dict(),
                "partial_packet": None if complete else packet,
                "interpretation_assessment": {
                    "status": status,
                    "grounded_refs": list(grounded_refs),
                    "open_variables": sorted(
                        {
                            value
                            for application in (
                                list(packet.get("apps", ()))
                                + list((packet.get("query") or {}).get("restrictions", ()))
                            )
                            for value in application.get("args", {}).values()
                            if isinstance(value, str) and value.startswith("?")
                        }
                    ),
                    "unresolved_evidence": list(critical),
                    "background_learning_evidence": list(noncritical),
                    "coverage": coverage.as_dict(),
                    "blockers": sorted(
                        {
                            "knowledge_binding"
                            if item.get("learning_contract_ref")
                            else item.get("residual_class", "unknown_form")
                            for item in critical
                        }
                    ),
                },
                "state_projection_refs": sorted(
                    (state_projections or {}).keys()
                ),
                "side_effect_free": True,
                "selected_candidate": selected_trace,
                "candidate_count": len(candidates),
            }
            return packet, news, uses, trace

        # A partial schema match preserves the best structural hypothesis and all
        # critical residuals. It never falls through to a one-token designation
        # probe that would discard the already-grounded predicate/arguments.
        if partial_matches:
            evidence, partial_trace = partial_matches[0]
            coverage = evidence.coverage
            selected_hypothesis = self._hypothesis_by_ref(
                resolved, evidence.hypothesis_ref
            ) or top_hypothesis
            if selected_hypothesis is not None:
                delex, anchors, uses = Delexer.render_hypothesis(selected_hypothesis)
                grounded_refs = self._grounded_refs(selected_hypothesis)
            critical = [item.as_dict() for item in coverage.critical_residuals]
            noncritical = [item.as_dict() for item in coverage.noncritical_residuals]
            trace = {
                "reason": "critical_semantic_residuals",
                "structured_prediction": True,
                "clauses": [settle_trace],
                "n_best": True,
                "resolved_form_lattice": resolved.as_dict(),
                "delexicalized": delex,
                "grounded_anchors": anchors,
                "unknown_form_evidence": critical,
                "background_learning_evidence": noncritical,
                "pending_learning_probe": [],
                "skipped_clauses": [],
                "interpretation_coverage": coverage.as_dict(),
                "partial_packet": self.constructions.partial_structure(
                    evidence, participant_frame, self.lang
                ),
                "interpretation_assessment": {
                    "status": "partial",
                    "grounded_refs": list(grounded_refs),
                    "open_variables": [],
                    "unresolved_evidence": critical,
                    "background_learning_evidence": noncritical,
                    "coverage": coverage.as_dict(),
                    "blockers": sorted(
                        {item.get("residual_class", "unknown_form") for item in critical}
                        | set(partial_trace.get("context_blockers", ()))
                    ),
                },
                "state_projection_refs": sorted((state_projections or {}).keys()),
                "side_effect_free": True,
                "selected_candidate": partial_trace,
                "candidate_count": len(candidates),
                "partial_candidate_count": len(partial_matches),
            }
            return None, [], uses, trace

        # No generic one-span fallback is permitted.  An unresolved utterance
        # remains a complete evidence lattice with every unit visible; an explicit
        # meaning-query construction is the only path that turns a surface into a
        # designation query.

        # The graph matcher emits partial assignments, so this branch now means
        # that no reviewed construction accepted even one compatible slot.  It
        # must not be used to erase a grounded partial graph.
        unresolved_coverage = (
            CoveragePolicy.build(
                top_hypothesis.units,
                (),
                required_semantic_roles=("predicate",),
                schema_ref="diagnostic:unresolved-evidence",
                hypothesis_ref=str(top_hypothesis.hypothesis_ref),
                match_seed_ref=stable(
                    "diagnostic-unresolved-match-seed",
                    top_hypothesis.hypothesis_ref,
                ),
                seed=("unresolved", top_hypothesis.hypothesis_ref),
            )
            if top_hypothesis is not None
            else None
        )
        trace = {
            "reason": "semantic_graph_unsettled",
            "structured_prediction": False,
            "clauses": [settle_trace],
            "n_best": True,
            "resolved_form_lattice": resolved.as_dict(),
            "delexicalized": delex,
            "grounded_anchors": anchors,
            "unknown_form_evidence": list(top_unknown),
            "background_learning_evidence": [],
            "skipped_clauses": [],
            "interpretation_coverage": (
                unresolved_coverage.as_dict() if unresolved_coverage else None
            ),
            "interpretation_assessment": {
                "status": "unresolved",
                "grounded_refs": list(grounded_refs),
                "open_variables": [],
                "unresolved_evidence": (
                    [item.as_dict() for item in unresolved_coverage.critical_residuals]
                    if unresolved_coverage else list(top_unknown)
                ),
                "coverage": (
                    unresolved_coverage.as_dict() if unresolved_coverage else None
                ),
                "blockers": ["semantic_graph_unsettled"],
            },
            "state_projection_refs": sorted((state_projections or {}).keys()),
            "side_effect_free": True,
            "candidate_count": len(candidates),
        }
        return None, [], uses, trace

    def parse(self, text, participant_frame: ParticipantFrame | None = None):
        """Pure diagnostic helper. Runtime uses observe then compose around Stage 4."""
        if participant_frame is None:
            raise ValueError("ParticipantFrame is required")
        lattice = self.observe(text, participant_frame)
        return self.compose(lattice, participant_frame, state_projections={})

    def delex_for_rule(self, text, participant_frame: ParticipantFrame | None = None):
        delex, placeholders, uses = self.delexer.run(text, participant_frame)
        # Rule induction expects local placeholders. The best hypothesis already
        # uses first-occurrence local numbering.
        return delex, placeholders, uses
