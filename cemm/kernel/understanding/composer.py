"""SemanticComposer — sole semantic composition authority.

Import boundary: model + schema + language + understanding submodules only.

Architectural guardrails (AGENTS.md §8, UNDERSTANDING_PIPELINE.md §3,
AUTHORITY_MATRIX.md):
- SemanticComposer is the SOLE authority for semantic composition.
- It creates separate candidates for: lexical sense, schema family,
  predication/proposition structure, communicative force, role bindings
  and open ports, embedded propositions, context/world, source evidence.
- Whole-turn construction and pragmatic cues may ADD candidates or
  discourse relations. They may NOT replace compositional content.
- For an opaque lexeme, composition creates a lexical reference and
  one or more provisional candidate sense clusters. It does not assume
  that identical spellings share one schema.
- Unknown content is never converted into a generic entity, role marker,
  or durable concept fact merely to keep the pipeline moving.
- A question is a communicative predication over a proposition pattern
  with open ports. A command is a directive predication whose content
  denotes a desired operation or state. (AGENTS.md §5)
- Negation is proposition polarity. Reported and hypothetical meanings
  are contexts. (AGENTS.md §5)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .candidate_graph import (
    CandidateGraph,
    CandidatePredication,
    CandidateProposition,
    CandidateCommunicativeForce,
    CandidateContext,
    DiscourseRelation,
)
from ..model.predication import Predication, RoleBinding, OpenPort, AspectProfile
from ..model.proposition import Proposition, ModalQualifier
from ..model.context_frame import ContextFrame
from ..model.evidence import EvidenceRecord
from ..model.role_binding import Constraint
from ..model.surface import SurfaceSpan, LexicalFormRef, KindHypothesis
from ..model.identity import Provenance, Scope, ScopeLevel, TimeExtent
from ..schema.store import SemanticSchemaStore
from ..schema.resolver import SchemaResolver
from ...language.interfaces import SurfaceEvidence
from ...language.stream import Token, TokenKind, TokenStream


class SemanticComposer:
    """Sole semantic composition authority.

    Takes surface evidence from a language adapter and produces a
    candidate graph with competing alternatives. Does NOT select
    final meaning — that is InterpretationResolver's job.

    Key invariants:
    - Preserves alternatives (multiple candidates for same evidence)
    - Pragmatic cues add, never replace
    - Opaque lexemes get provisional sense clusters, not generic entities
    - Unknown content stays unknown — not converted to durable facts
    - Nested propositions work without whole-phrase aliases
    - Negation is proposition polarity, not a separate predication
    - Communicative force is independent from polarity/context/modality
    """

    def __init__(
        self,
        store: SemanticSchemaStore,
        resolver: SchemaResolver | None = None,
    ) -> None:
        self._store = store
        self._resolver = resolver or SchemaResolver(store)

    def compose(self, evidence: SurfaceEvidence) -> CandidateGraph:
        """Compose surface evidence into a candidate graph.

        This is the main entry point. It:
        1. Resolves lexical sense candidates from the evidence
        2. Builds predication candidates from construction candidates
        3. Wraps predications in proposition candidates with context/polarity/modality
        4. Adds communicative force candidates
        5. Adds pragmatic cues as discourse relations (never replacing content)
        6. Preserves opaque lexemes as provisional sense clusters
        """
        candidate_predications: list[CandidatePredication] = []
        candidate_propositions: list[CandidateProposition] = []
        candidate_forces: list[CandidateCommunicativeForce] = []
        candidate_contexts: list[CandidateContext] = []
        discourse_relations: list[DiscourseRelation] = []
        open_ports: list[OpenPort] = []
        opaque_refs: list[str] = []
        evidence_refs: list[str] = []

        stream = evidence.token_stream

        # 1. Process lexical sense candidates → predication candidates
        for lex_candidate in evidence.lexical_sense_candidates:
            # Resolve via schema resolver — may produce multiple candidates
            resolution = self._resolver.resolve_key(lex_candidate.semantic_key)

            if not resolution.candidates:
                # Opaque lexeme — create provisional sense cluster
                opaque_ref = f"opaque:{lex_candidate.lexical_form_ref.surface}:{uuid4().hex[:8]}"
                opaque_refs.append(opaque_ref)
                continue

            # Build predication candidates from resolved senses
            for sense in resolution.candidates:
                pred = self._build_predication(
                    sense, lex_candidate, stream, evidence
                )
                if pred is not None:
                    candidate_predications.append(pred)

        # 1b. Detect unknown tokens as opaque even without lexical candidates
        for i, token in enumerate(stream.tokens):
            if token.is_unknown and not any(
                lex.source_token_indices and i in lex.source_token_indices
                for lex in evidence.lexical_sense_candidates
            ):
                opaque_ref = f"opaque:{token.raw_form}:{uuid4().hex[:8]}"
                opaque_refs.append(opaque_ref)

        # 2. Process construction candidates → predication candidates
        for constr in evidence.construction_candidates:
            pred = self._build_construction_predication(constr, stream, evidence)
            if pred is not None:
                candidate_predications.append(pred)

        # 3. Process negation — polarity on propositions, not separate predications
        has_negation = stream.has_negation

        # 4. Build proposition candidates from predications
        for cp in candidate_predications:
            # Determine context (default: actual)
            context = ContextFrame(
                id=f"ctx:{uuid4().hex[:12]}",
                context_kind="actual",
            )
            candidate_contexts.append(CandidateContext(
                context_frame=context,
                confidence=0.9,
            ))

            # Build proposition with polarity from negation
            polarity = "negative" if has_negation else "positive"
            prop = Proposition(
                id=f"prop:{uuid4().hex[:12]}",
                predication_ref=cp.predication.id,
                context_ref=context.id,
                polarity=polarity,
            )
            candidate_propositions.append(CandidateProposition(
                proposition=prop,
                candidate_source=cp.candidate_source,
                confidence=cp.confidence,
                source_evidence_refs=cp.source_evidence_refs,
            ))

        # 5. Process communicative force candidates
        for comm_candidate in evidence.communicative_candidates:
            # Match to best proposition candidate
            target_ref = ""
            if candidate_propositions:
                best = max(candidate_propositions, key=lambda c: c.confidence)
                target_ref = best.proposition.id

            candidate_forces.append(CandidateCommunicativeForce(
                force=comm_candidate.force,
                target_proposition_ref=target_ref,
                confidence=comm_candidate.confidence,
                source_evidence_refs=(),
            ))

        # If no communicative force detected, default to assert
        if not candidate_forces and candidate_propositions:
            for cp in candidate_propositions:
                candidate_forces.append(CandidateCommunicativeForce(
                    force="assert",
                    target_proposition_ref=cp.proposition.id,
                    confidence=0.5,
                ))

        # 6. Process pragmatic cues — ADD only, never replace
        for cue in evidence.pragmatic_cues:
            # Pragmatic cues add discourse relations
            # They must NOT replace content propositions
            assert not cue.replaces_content, (
                "Pragmatic cue cannot replace content — "
                "this violates UNDERSTANDING_PIPELINE.md §3"
            )

            # Add discourse relation from pragmatic cue
            if candidate_propositions:
                discourse_relations.append(DiscourseRelation(
                    source_ref=candidate_propositions[0].proposition.id,
                    target_ref=candidate_propositions[-1].proposition.id,
                    relation_kind=cue.cue_kind,
                    confidence=cue.confidence,
                    from_pragmatic_cue=True,
                ))

        # 7. Handle questions — communicative predication with open ports
        for force in candidate_forces:
            if force.force == "ask":
                # Questions have open ports for the unknown role
                open_ports.append(OpenPort(
                    role_schema_ref="role:unknown",
                    required=True,
                    cardinality="one",
                ))

        return CandidateGraph(
            candidate_predications=tuple(candidate_predications),
            candidate_propositions=tuple(candidate_propositions),
            candidate_communicative_forces=tuple(candidate_forces),
            candidate_contexts=tuple(candidate_contexts),
            discourse_relations=tuple(discourse_relations),
            open_ports=tuple(open_ports),
            opaque_lexeme_refs=tuple(opaque_refs),
            source_evidence_refs=tuple(evidence_refs),
        )

    def compose_nested(
        self,
        outer_evidence: SurfaceEvidence,
        inner_evidence: SurfaceEvidence,
    ) -> CandidateGraph:
        """Compose nested propositions (e.g. 'Do you know what an engineer is?').

        Nested propositions work without whole-phrase aliases.
        The inner proposition is embedded as a role filler in the outer.
        """
        outer_graph = self.compose(outer_evidence)
        inner_graph = self.compose(inner_evidence)

        # Embed inner propositions as role fillers in outer predications
        embedded_refs: list[str] = []
        for inner_prop in inner_graph.candidate_propositions:
            embedded_refs.append(inner_prop.proposition.id)

        # Create embedded proposition candidates
        nested_propositions: list[CandidateProposition] = []
        for outer_prop in outer_graph.candidate_propositions:
            nested = CandidateProposition(
                proposition=outer_prop.proposition,
                candidate_source=outer_prop.candidate_source,
                confidence=outer_prop.confidence,
                embedded_proposition_refs=tuple(embedded_refs),
                source_evidence_refs=outer_prop.source_evidence_refs,
            )
            nested_propositions.append(nested)

        return CandidateGraph(
            candidate_predications=outer_graph.candidate_predications,
            candidate_propositions=tuple(nested_propositions),
            candidate_communicative_forces=outer_graph.candidate_communicative_forces,
            candidate_contexts=outer_graph.candidate_contexts + inner_graph.candidate_contexts,
            discourse_relations=outer_graph.discourse_relations,
            open_ports=outer_graph.open_ports + inner_graph.open_ports,
            opaque_lexeme_refs=outer_graph.opaque_lexeme_refs + inner_graph.opaque_lexeme_refs,
            source_evidence_refs=outer_graph.source_evidence_refs + inner_graph.source_evidence_refs,
        )

    def _build_predication(
        self,
        sense: Any,  # SenseCandidate from resolver
        lex_candidate: Any,  # LexicalSenseCandidate from evidence
        stream: TokenStream,
        evidence: SurfaceEvidence,
    ) -> CandidatePredication | None:
        """Build a predication candidate from a resolved lexical sense."""
        pred_id = f"pred:{uuid4().hex[:12]}"

        # Build role bindings from construction candidates if available
        bindings: list[RoleBinding] = []
        for constr in evidence.construction_candidates:
            if constr.predicate_schema_ref == sense.record_id:
                for role_key, token_idx in constr.role_mappings.items():
                    if 0 <= token_idx < len(stream.tokens):
                        token = stream.tokens[token_idx]
                        bindings.append(RoleBinding(
                            role_schema_ref=f"role:{role_key}",
                            filler_ref=f"ref:token:{token_idx}",
                            confidence=constr.confidence,
                        ))

        pred = Predication(
            id=pred_id,
            predicate_schema_ref=sense.record_id,
            bindings=tuple(bindings),
            source_span_refs=tuple(
                f"span:{idx}" for idx in lex_candidate.source_token_indices
            ),
            confidence=sense.confidence * lex_candidate.confidence,
        )

        return CandidatePredication(
            predication=pred,
            candidate_source="lexical",
            confidence=sense.confidence * lex_candidate.confidence,
            source_token_indices=lex_candidate.source_token_indices,
        )

    def _build_construction_predication(
        self,
        constr: Any,  # ConstructionCandidate from evidence
        stream: TokenStream,
        evidence: SurfaceEvidence,
    ) -> CandidatePredication | None:
        """Build a predication candidate from a construction candidate."""
        pred_id = f"pred:{uuid4().hex[:12]}"

        bindings: list[RoleBinding] = []
        for role_key, token_idx in constr.role_mappings.items():
            if 0 <= token_idx < len(stream.tokens):
                bindings.append(RoleBinding(
                    role_schema_ref=f"role:{role_key}",
                    filler_ref=f"ref:token:{token_idx}",
                    confidence=constr.confidence,
                ))

        pred = Predication(
            id=pred_id,
            predicate_schema_ref=constr.predicate_schema_ref,
            bindings=tuple(bindings),
            source_span_refs=tuple(
                f"span:{idx}" for idx in constr.source_token_indices
            ),
            confidence=constr.confidence,
        )

        return CandidatePredication(
            predication=pred,
            candidate_source="construction",
            confidence=constr.confidence,
            source_token_indices=constr.source_token_indices,
        )
