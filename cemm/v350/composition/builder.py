"""Compile Phase-7/8 evidence into a Phase-9 UOL factor graph.

The builder is the only semantic-aware part of Phase 9.  It resolves exact
reviewed schema revisions, use profiles, local port contracts, and candidate
proofs into finite factor tables.  The solver itself remains ontology-agnostic.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable

from ..grounding.model import (
    GroundingCandidate,
    GroundingFactorKind,
    GroundingResult,
    MentionHypothesis,
)
from ..language.model import (
    FormLattice, SemanticContributionKind, SenseCandidate, SenseTargetKind,
)
from ..schema.model import OpenBindingPurpose, PortFillerClass, UseOperation, semantic_fingerprint
from ..storage import SemanticStore, StoreSnapshot
from .model import (
    MeaningFactor,
    MeaningFactorGraph,
    MeaningFactorKind,
    MeaningValue,
    MeaningVariable,
    MeaningVariableKind,
)

_INACTIVE = "choice:inactive"
_UNRESOLVED = "choice:unresolved"
_OMITTED = "choice:omitted"
_GAP = "choice:gap"
_MAX_MULTI_FILLERS = 4


class MeaningFactorGraphBuilder:
    """Build a finite, proof-bearing factor graph from pinned upstream evidence."""

    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def build(
        self,
        lattice: FormLattice,
        grounding: GroundingResult,
        *,
        context_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> MeaningFactorGraph:
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.build(
                    lattice, grounding, context_ref=context_ref, snapshot=pinned
                )
        self.store.assert_snapshot(snapshot)
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        language = self.store.repositories.language.registry(snapshot=snapshot)

        variables: list[MeaningVariable] = []
        factors: list[MeaningFactor] = []
        unresolved = set(grounding.frontier_refs)
        unresolved.update(grounding.unresolved_mention_refs)
        unresolved.update(
            f"span:{item.start}:{item.end}" for item in lattice.unresolved_spans
        )
        evidence = {lattice.lattice_ref, grounding.grounding_ref}

        forms = {item.candidate_ref: item for item in lattice.form_candidates}
        senses_by_form: dict[str, list[SenseCandidate]] = defaultdict(list)
        for sense in lattice.sense_candidates:
            if sense.use_operation != UseOperation.GROUND:
                continue
            senses_by_form[sense.form_candidate_ref].append(sense)
            evidence.update(sense.evidence_refs)

        # Stage-5 sense/schema variables.  The exact target schema revision is
        # carried by the lexical candidate and validated against schema use.
        sense_var_for_form: dict[str, str] = {}
        sense_candidate_to_var: dict[str, str] = {}
        schema_var_for_form: dict[str, str] = {}
        for form_ref in sorted(senses_by_form):
            candidates = tuple(sorted(senses_by_form[form_ref], key=lambda item: item.candidate_ref))
            if not candidates:
                continue
            sense_var_ref = _var_ref("sense", lattice.lattice_ref, form_ref)
            sense_var_for_form[form_ref] = sense_var_ref
            for item in candidates:
                sense_candidate_to_var[item.candidate_ref] = sense_var_ref
            variables.append(MeaningVariable(
                variable_ref=sense_var_ref,
                variable_kind=MeaningVariableKind.SENSE,
                values=tuple(
                    MeaningValue(
                        value_ref=item.candidate_ref,
                        score=_confidence_logit(item.confidence),
                        evidence_refs=item.evidence_refs,
                        metadata={
                            "sense_ref": item.sense_ref,
                            "sense_revision": item.sense_revision,
                            "target_kind": None if item.target_kind is None else item.target_kind.value,
                            "target_ref": item.target_ref,
                            "target_revision": item.target_revision,
                            "target_schema_class": None if item.target_schema_class is None else item.target_schema_class.value,
                            "scope_behavior": item.scope_behavior,
                            "lexeme_ref": item.lexeme_ref,
                            "authority_path": item.authority_path,
                            "semantic_contribution_refs": tuple(
                                contribution.contribution_ref for contribution in item.contributions
                            ),
                            "form_candidate_ref": item.form_candidate_ref,
                        },
                    )
                    for item in candidates
                ),
                evidence_refs=tuple(sorted({ref for item in candidates for ref in item.evidence_refs})),
                metadata={"form_candidate_ref": form_ref},
            ))

            schema_values: list[MeaningValue] = []
            allowed_links: list[tuple[str, str]] = []
            for item in candidates:
                targets = tuple(
                    contribution
                    for contribution in item.contributions
                    if contribution.contribution_kind == SemanticContributionKind.TARGET
                    and contribution.target_ref is not None
                )
                for contribution in targets:
                    choice_ref = _choice_ref("schema", contribution.contribution_ref)
                    valid = True
                    schema_metadata = {
                        "sense_candidate_ref": item.candidate_ref,
                        "semantic_contribution_ref": contribution.contribution_ref,
                        "target_kind": None if contribution.target_kind is None else contribution.target_kind.value,
                        "target_ref": contribution.target_ref,
                        "target_revision": contribution.target_revision,
                    }
                    if contribution.target_kind != SenseTargetKind.STRUCTURAL:
                        if contribution.target_revision is None:
                            valid = False
                        else:
                            try:
                                schema = registry.schema(
                                    contribution.target_ref,
                                    contribution.target_revision,
                                )
                            except Exception:
                                valid = False
                            else:
                                valid = schema.use_profile.permits(
                                    UseOperation.COMPOSE, provisional=True
                                )
                                schema_metadata.update({
                                    "schema_ref": schema.schema_ref,
                                    "schema_revision": schema.revision,
                                    "schema_class": schema.schema_class.value,
                                    "compose_authorized": valid,
                                })
                    else:
                        schema_metadata["structural"] = True
                    if valid:
                        schema_values.append(MeaningValue(
                            value_ref=choice_ref,
                            score=0.0,
                            evidence_refs=contribution.evidence_refs or item.evidence_refs,
                            metadata=schema_metadata,
                        ))
                        allowed_links.append((item.candidate_ref, choice_ref))
            if schema_values:
                schema_var_ref = _var_ref("schema", lattice.lattice_ref, form_ref)
                schema_var_for_form[form_ref] = schema_var_ref
                variables.append(MeaningVariable(
                    variable_ref=schema_var_ref,
                    variable_kind=MeaningVariableKind.SCHEMA,
                    values=tuple(schema_values),
                    evidence_refs=tuple(sorted({ref for value in schema_values for ref in value.evidence_refs})),
                    metadata={"form_candidate_ref": form_ref},
                ))
                factors.append(_hard_factor(
                    "sense-schema",
                    (sense_var_ref, schema_var_ref),
                    tuple(allowed_links),
                    tuple(sorted({ref for item in candidates for ref in item.evidence_refs})),
                    "selected lexical sense must use its exact reviewed semantic target",
                    MeaningFactorKind.LINK,
                ))

        # Cycle context is explicit before identity variables so every referent
        # choice can be constrained against the same pinned world/context.  The
        # domain is intentionally finite per cycle; later attributed contexts add
        # values as evidence, never through solver branches.
        context_var_ref = _var_ref("context", lattice.lattice_ref, context_ref)
        variables.append(MeaningVariable(
            variable_ref=context_var_ref,
            variable_kind=MeaningVariableKind.CONTEXT,
            values=(MeaningValue(
                value_ref=context_ref,
                score=0.0,
                evidence_refs=(lattice.lattice_ref,),
                metadata={"context_ref": context_ref},
            ),),
            evidence_refs=(lattice.lattice_ref,),
        ))

        # Referent identity variables retain every Phase-8 candidate.  Candidate
        # scores are decomposed into explicit evidence factors instead of being
        # hidden inside an opaque local score.  A single global hard table then
        # preserves cross-mention constraints already proven by Phase 8 without
        # making its top choice final.
        candidates_by_mention: dict[str, list[GroundingCandidate]] = defaultdict(list)
        for candidate in grounding.candidates:
            candidates_by_mention[candidate.mention_ref].append(candidate)
            evidence.update(
                factor_ref
                for factor in candidate.factors
                for factor_ref in factor.evidence_refs
            )
        referent_var_for_mention: dict[str, str] = {}
        time_var_for_ref: dict[str, str] = {}
        for mention in grounding.mentions:
            candidates = tuple(
                sorted(
                    candidates_by_mention.get(mention.mention_ref, ()),
                    key=lambda item: item.candidate_ref,
                )
            )
            if not candidates:
                unresolved.add(mention.mention_ref)
                continue
            var_ref = _var_ref("referent", grounding.grounding_ref, mention.mention_ref)
            referent_var_for_mention[mention.mention_ref] = var_ref
            selected_candidate_ref = None
            if grounding.selected is not None:
                selected_refs = set(grounding.selected.candidate_refs)
                selected_candidate_ref = next(
                    (item.candidate_ref for item in candidates if item.candidate_ref in selected_refs),
                    None,
                )
            candidate_evidence = {
                item.candidate_ref: tuple(
                    sorted(
                        {
                            ref
                            for factor in item.factors
                            for ref in factor.evidence_refs
                        }
                    )
                )
                for item in candidates
            }
            variables.append(MeaningVariable(
                variable_ref=var_ref,
                variable_kind=MeaningVariableKind.REFERENT,
                values=tuple(
                    MeaningValue(
                        value_ref=item.candidate_ref,
                        score=0.0,
                        evidence_refs=candidate_evidence[item.candidate_ref],
                        metadata={
                            "target_ref": item.target_ref,
                            "origin": item.origin.value,
                            "storage_kind": item.storage_kind.value,
                            "type_refs": item.type_refs,
                            "context_refs": item.context_refs,
                            "valid_time_ref": item.valid_time_ref,
                            "provisional": item.provisional,
                            "candidate_metadata": dict(item.metadata),
                        },
                    )
                    for item in candidates
                ),
                evidence_refs=mention.evidence_refs,
                metadata={
                    "mention_ref": mention.mention_ref,
                    "span": (mention.span.start, mention.span.end),
                    "syntactic_role": mention.syntactic_role,
                },
            ))

            # Every Phase-8 proof factor is exposed to Phase 9. Hard proof classes
            # compile to finite allowed domains; soft proof classes compile to
            # named unary factors. This prevents local_score from becoming a
            # hidden semantic authority.
            for factor_kind in sorted(GroundingFactorKind, key=lambda item: item.value):
                hard_candidates = tuple(
                    item.candidate_ref
                    for item in candidates
                    if any(
                        factor.factor_kind == factor_kind and factor.hard
                        for factor in item.factors
                    )
                )
                if hard_candidates:
                    factors.append(_hard_factor(
                        f"grounding-{factor_kind.value}",
                        (var_ref,),
                        tuple((ref,) for ref in hard_candidates),
                        tuple(
                            sorted(
                                {
                                    evidence_ref
                                    for item in candidates
                                    for factor in item.factors
                                    if factor.factor_kind == factor_kind and factor.hard
                                    for evidence_ref in factor.evidence_refs
                                }
                            )
                        ),
                        f"Phase-8 {factor_kind.value} compatibility remains a hard meaning constraint",
                        _hard_grounding_factor_kind(factor_kind),
                    ))

                for item in candidates:
                    for proof in item.factors:
                        if proof.factor_kind != factor_kind or proof.hard:
                            continue
                        tuple_scores = tuple(
                            ((value.candidate_ref,), proof.score if value.candidate_ref == item.candidate_ref else 0.0)
                            for value in candidates
                        )
                        factors.append(MeaningFactor(
                            factor_ref=_factor_ref(
                                f"grounding-evidence-{proof.factor_kind.value}",
                                (var_ref, item.candidate_ref, proof.factor_ref),
                            ),
                            factor_kind=_soft_grounding_factor_kind(proof.factor_kind),
                            variable_refs=(var_ref,),
                            hard=False,
                            tuple_scores=tuple_scores,
                            evidence_refs=proof.evidence_refs,
                            reason=proof.reason,
                            metadata={
                                "upstream_factor_ref": proof.factor_ref,
                                "upstream_factor_kind": proof.factor_kind.value,
                            },
                        ))

            # Context isolation is rechecked in the composition graph rather than
            # trusted as an implicit property of the Phase-8 candidate list.
            allowed_context = tuple(
                (context_ref, item.candidate_ref)
                for item in candidates
                if context_ref in item.context_refs or "global" in item.context_refs
            )
            if allowed_context:
                factors.append(_hard_factor(
                    "context-isolation",
                    (context_var_ref, var_ref),
                    allowed_context,
                    mention.evidence_refs,
                    "referent identity must remain visible in the selected semantic context",
                    MeaningFactorKind.CONTEXT_ISOLATION,
                ))

            # Type compatibility is explicit even when Phase 8 already filtered
            # candidates. Learned type refs flow through data and closure evidence;
            # no type name is interpreted by this builder.
            allowed_types = tuple(
                item.candidate_ref
                for item in candidates
                if not mention.expected_type_refs
                or bool(set(mention.expected_type_refs).intersection(item.type_refs))
            )
            if allowed_types:
                factors.append(_hard_factor(
                    "type-entitlement",
                    (var_ref,),
                    tuple((ref,) for ref in allowed_types),
                    mention.evidence_refs,
                    "candidate type closure must satisfy the mention's reviewed semantic restrictions",
                    MeaningFactorKind.TYPE_ENTITLEMENT,
                ))

            # Explicit temporal evidence becomes its own Stage-5 variable. A
            # candidate with no intrinsic time restriction can coexist with the
            # selected time; an incompatible pinned time cannot.
            if mention.time_ref is not None:
                time_var_ref = time_var_for_ref.get(mention.time_ref)
                if time_var_ref is None:
                    time_var_ref = _var_ref("time", lattice.lattice_ref, mention.time_ref)
                    time_var_for_ref[mention.time_ref] = time_var_ref
                    variables.append(MeaningVariable(
                        variable_ref=time_var_ref,
                        variable_kind=MeaningVariableKind.TIME,
                        values=(MeaningValue(
                            value_ref=mention.time_ref,
                            score=0.0,
                            evidence_refs=mention.evidence_refs,
                            metadata={"time_ref": mention.time_ref},
                        ),),
                        evidence_refs=mention.evidence_refs,
                    ))
                allowed_time = tuple(
                    (mention.time_ref, item.candidate_ref)
                    for item in candidates
                    if item.valid_time_ref is None or item.valid_time_ref == mention.time_ref
                )
                if allowed_time:
                    factors.append(_hard_factor(
                        "time-compatibility",
                        (time_var_ref, var_ref),
                        allowed_time,
                        mention.evidence_refs,
                        "referent identity must remain compatible with explicit time evidence",
                        MeaningFactorKind.CONTEXT_ISOLATION,
                    ))

            # The prior Phase-8 selected assignment is only one soft coherence
            # signal. It cannot override any Phase-9 hard factor or erase close
            # alternatives.
            if selected_candidate_ref is not None:
                factors.append(MeaningFactor(
                    factor_ref=_factor_ref("grounding-selected-prior", (var_ref, selected_candidate_ref)),
                    factor_kind=MeaningFactorKind.GROUNDING_COHERENCE,
                    variable_refs=(var_ref,),
                    hard=False,
                    tuple_scores=tuple(
                        ((item.candidate_ref,), 0.35 if item.candidate_ref == selected_candidate_ref else 0.0)
                        for item in candidates
                    ),
                    evidence_refs=grounding.evidence_refs,
                    reason="Phase-8 best assignment is a defeasible coherence prior, not final identity authority",
                ))

        ordered_mentions = tuple(
            mention.mention_ref for mention in grounding.mentions
            if mention.mention_ref in referent_var_for_mention
        )
        if ordered_mentions and grounding.assignments:
            vars_for_grounding = tuple(referent_var_for_mention[ref] for ref in ordered_mentions)
            candidate_index = {item.candidate_ref: item for item in grounding.candidates}
            allowed = []
            for assignment in grounding.assignments:
                by_mention = {
                    candidate_index[ref].mention_ref: ref
                    for ref in assignment.candidate_refs
                    if ref in candidate_index
                }
                if all(ref in by_mention for ref in ordered_mentions):
                    allowed.append(tuple(by_mention[ref] for ref in ordered_mentions))
            if allowed:
                factors.append(_hard_factor(
                    "grounding-joint",
                    vars_for_grounding,
                    tuple(sorted(set(allowed))),
                    grounding.evidence_refs,
                    "referent choices must preserve Phase-8 joint grounding constraints",
                    MeaningFactorKind.GROUNDING_COHERENCE,
                ))

        # Construction variables preserve N-best clause analyses.  Activating a
        # construction never creates meaning unless its exact output contract is
        # composable and its semantic ports can be populated or explicitly left
        # open under the schema's own policy.
        construction_var: dict[str, str] = {}
        candidate_by_ref = {item.candidate_ref: item for item in lattice.construction_candidates}
        for candidate in sorted(lattice.construction_candidates, key=lambda item: item.candidate_ref):
            record = language.require_construction(candidate.construction_ref, candidate.construction_revision)
            active_allowed = True
            if record.output_schema_ref is not None:
                try:
                    output_schema = registry.schema(record.output_schema_ref, record.output_schema_revision)
                except Exception:
                    active_allowed = False
                else:
                    active_allowed = output_schema.use_profile.permits(UseOperation.COMPOSE, provisional=True)
            var_ref = _var_ref("construction", lattice.lattice_ref, candidate.candidate_ref)
            construction_var[candidate.candidate_ref] = var_ref
            values = [MeaningValue(
                value_ref=_INACTIVE,
                score=0.0,
                evidence_refs=candidate.evidence_refs,
                metadata={"active": False},
            )]
            if active_allowed:
                values.append(MeaningValue(
                    value_ref="choice:active",
                    score=_confidence_logit(candidate.confidence),
                    evidence_refs=candidate.evidence_refs,
                    metadata={
                        "active": True,
                        "construction_ref": record.construction_ref,
                        "construction_revision": record.revision,
                        "construction_kind": record.construction_kind.value,
                        "output_schema_ref": record.output_schema_ref,
                        "output_schema_revision": record.output_schema_revision,
                    },
                ))
            variables.append(MeaningVariable(
                variable_ref=var_ref,
                variable_kind=MeaningVariableKind.CONSTRUCTION,
                values=tuple(values),
                evidence_refs=candidate.evidence_refs,
                metadata={"construction_candidate_ref": candidate.candidate_ref},
            ))

            trigger_sense_refs = set(record.trigger_sense_refs)
            trigger_candidates = [
                item for item in lattice.sense_candidates
                if item.sense_ref in trigger_sense_refs and item.candidate_ref in candidate.trigger_refs
            ]
            # Some analyzers expose trigger form/observation refs rather than
            # the sense-candidate ref.  A construction can still activate when
            # no lexical ambiguity needs a linking factor.
            for trigger in trigger_candidates:
                sense_var_ref = sense_candidate_to_var.get(trigger.candidate_ref)
                if sense_var_ref is None:
                    continue
                allowed = []
                sense_var = next(item for item in variables if item.variable_ref == sense_var_ref)
                for value in sense_var.values:
                    allowed.append((value.value_ref, _INACTIVE))
                    if value.value_ref == trigger.candidate_ref and active_allowed:
                        allowed.append((value.value_ref, "choice:active"))
                factors.append(_hard_factor(
                    "construction-trigger",
                    (sense_var_ref, var_ref),
                    tuple(sorted(set(allowed))),
                    candidate.evidence_refs,
                    "active construction must be licensed by its reviewed trigger sense",
                    MeaningFactorKind.CONSTRUCTION_COMPATIBILITY,
                ))

            if record.output_schema_ref is not None and active_allowed:
                schema = registry.schema(record.output_schema_ref, record.output_schema_revision)
                slot_map = {item.slot_ref: item for item in record.slots}
                for slot_ref, filler_refs in candidate.slot_fillers:
                    slot = slot_map.get(slot_ref)
                    if slot is None or not slot.semantic_port_ref:
                        continue
                    try:
                        port = schema.port(slot.semantic_port_ref)
                    except KeyError:
                        # The language record cannot smuggle a port that the
                        # exact semantic schema does not own.
                        factors.append(_hard_factor(
                            "unknown-port",
                            (var_ref,),
                            ((_INACTIVE,),),
                            candidate.evidence_refs,
                            "construction semantic port is absent from the exact output schema",
                            MeaningFactorKind.PORT_COMPATIBILITY,
                        ))
                        continue
                    mention_refs = tuple(
                        mention.mention_ref for mention in grounding.mentions
                        if candidate.candidate_ref in mention.construction_candidate_refs
                        and mention.syntactic_role in {slot.slot_ref, slot.semantic_port_ref, port.port_ref, port.role_family}
                    )
                    compatible = tuple(
                        candidate_item
                        for mention_ref in mention_refs
                        for candidate_item in candidates_by_mention.get(mention_ref, ())
                        if _port_accepts_candidate(port, candidate_item)
                    )
                    value_specs = _port_value_specs(
                        compatible,
                        minimum=port.cardinality.minimum,
                        maximum=port.cardinality.maximum,
                        allow_open=OpenBindingPurpose.PARTIAL_COMPOSITION in port.open_binding_purposes,
                        allow_omitted=port.cardinality.minimum == 0,
                        evidence_refs=candidate.evidence_refs,
                    )
                    port_var_ref = _var_ref(
                        "port", candidate.candidate_ref, f"{schema.schema_ref}@{schema.revision}:{port.port_ref}"
                    )
                    variables.append(MeaningVariable(
                        variable_ref=port_var_ref,
                        variable_kind=MeaningVariableKind.PORT_FILLER,
                        values=(MeaningValue(
                            value_ref=_INACTIVE,
                            score=0.0,
                            evidence_refs=candidate.evidence_refs,
                            metadata={"inactive": True},
                        ), *value_specs),
                        evidence_refs=candidate.evidence_refs,
                        metadata={
                            "construction_candidate_ref": candidate.candidate_ref,
                            "schema_ref": schema.schema_ref,
                            "schema_revision": schema.revision,
                            "port_ref": port.port_ref,
                            "role_family": port.role_family,
                            "filler_classes": tuple(sorted(item.value for item in port.filler_classes)),
                            "accepted_type_refs": port.accepted_type_refs,
                            "accepted_storage_kinds": tuple(sorted(item.value for item in port.accepted_storage_kinds)),
                            "open_binding_purposes": tuple(sorted(item.value for item in port.open_binding_purposes)),
                        },
                    ))
                    factors.append(_hard_factor(
                        "construction-port-active",
                        (var_ref, port_var_ref),
                        tuple(
                            [(_INACTIVE, _INACTIVE)]
                            + [
                                ("choice:active", value.value_ref)
                                for value in value_specs
                            ]
                        ),
                        candidate.evidence_refs,
                        "semantic port fillers are active exactly when their construction is active",
                        MeaningFactorKind.PORT_COMPATIBILITY,
                    ))

                    # Tie selected port candidate(s) to the corresponding joint
                    # referent variable so construction and identity cannot drift.
                    for mention_ref in mention_refs:
                        referent_var = referent_var_for_mention.get(mention_ref)
                        if referent_var is None:
                            continue
                        referent_values = next(item.values for item in variables if item.variable_ref == referent_var)
                        allowed_pairs = []
                        for referent_value in referent_values:
                            for port_value in value_specs:
                                selected_refs = tuple(port_value.metadata.get("candidate_refs", ()))
                                if port_value.value_ref in {_GAP, _OMITTED} or referent_value.value_ref in selected_refs:
                                    allowed_pairs.append((referent_value.value_ref, port_value.value_ref))
                        # Inactive construction leaves the port inactive; the
                        # referent variable remains independently resolvable.
                        allowed_pairs.extend((value.value_ref, _INACTIVE) for value in referent_values)
                        if allowed_pairs:
                            factors.append(_hard_factor(
                                "port-grounding-link",
                                (referent_var, port_var_ref),
                                tuple(sorted(set(allowed_pairs))),
                                candidate.evidence_refs,
                                "port filler identity must agree with the selected grounding candidate",
                                MeaningFactorKind.LINK,
                            ))

        # Competing construction candidates that consume the same trigger span
        # and represent the same construction family cannot both be selected.
        constructions = tuple(sorted(lattice.construction_candidates, key=lambda item: item.candidate_ref))
        for left, right in combinations(constructions, 2):
            if left.span != right.span:
                continue
            left_record = language.require_construction(left.construction_ref, left.construction_revision)
            right_record = language.require_construction(right.construction_ref, right.construction_revision)
            if left_record.construction_kind != right_record.construction_kind:
                continue
            if not set(left.trigger_refs).intersection(right.trigger_refs):
                continue
            factors.append(_hard_factor(
                "construction-exclusivity",
                (construction_var[left.candidate_ref], construction_var[right.candidate_ref]),
                ((_INACTIVE, _INACTIVE), (_INACTIVE, "choice:active"), ("choice:active", _INACTIVE)),
                tuple(sorted(set(left.evidence_refs) | set(right.evidence_refs))),
                "competing constructions may not double-consume the same trigger evidence",
                MeaningFactorKind.EVIDENCE_EXCLUSIVITY,
            ))

        # Operator-scope variables are structural N-best links over selected
        # semantic candidates.  No operator name is special-cased: the scope
        # behavior comes from the reviewed lexical-sense record.
        sense_by_ref = {item.candidate_ref: item for item in lattice.sense_candidates}
        scoped_candidates = tuple(
            item for item in lattice.sense_candidates
            if item.target_kind != SenseTargetKind.STRUCTURAL
        )
        form_by_ref = forms
        for operator in sorted(
            (item for item in scoped_candidates if item.scope_behavior and item.scope_behavior != "none"),
            key=lambda item: item.candidate_ref,
        ):
            operator_form = form_by_ref.get(operator.form_candidate_ref)
            if operator_form is None:
                continue
            targets = []
            for target in scoped_candidates:
                if target.candidate_ref == operator.candidate_ref:
                    continue
                target_form = form_by_ref.get(target.form_candidate_ref)
                if target_form is None:
                    continue
                distance = abs(target_form.span.start - operator_form.span.end)
                right_bias = 0.4 if target_form.span.start >= operator_form.span.end else 0.0
                targets.append((target, -(distance * 0.01) + right_bias))
            scope_var_ref = _var_ref("scope", lattice.lattice_ref, operator.candidate_ref)
            scope_values = [MeaningValue(
                value_ref=_UNRESOLVED,
                score=-0.8,
                evidence_refs=operator.evidence_refs,
                metadata={"unresolved": True, "operator_sense_candidate_ref": operator.candidate_ref},
            )]
            for target, score in sorted(targets, key=lambda item: item[0].candidate_ref):
                scope_values.append(MeaningValue(
                    value_ref=_choice_ref("scope-target", target.candidate_ref),
                    score=score,
                    evidence_refs=tuple(sorted(set(operator.evidence_refs) | set(target.evidence_refs))),
                    metadata={
                        "operator_sense_candidate_ref": operator.candidate_ref,
                        "target_sense_candidate_ref": target.candidate_ref,
                        "scope_behavior": operator.scope_behavior,
                    },
                ))
            variables.append(MeaningVariable(
                variable_ref=scope_var_ref,
                variable_kind=MeaningVariableKind.SCOPE,
                values=tuple(scope_values),
                evidence_refs=operator.evidence_refs,
                metadata={
                    "operator_sense_candidate_ref": operator.candidate_ref,
                    "scope_behavior": operator.scope_behavior,
                },
            ))

            # Operator scope is meaningful only when that operator sense is the
            # chosen lexical analysis for its form.  Alternative senses force an
            # unresolved/inactive scope choice rather than manufacturing scope.
            sense_var_ref = sense_candidate_to_var.get(operator.candidate_ref)
            if sense_var_ref:
                sense_values = next(item.values for item in variables if item.variable_ref == sense_var_ref)
                allowed = []
                for sense_value in sense_values:
                    if sense_value.value_ref == operator.candidate_ref:
                        allowed.extend((sense_value.value_ref, value.value_ref) for value in scope_values)
                    else:
                        allowed.append((sense_value.value_ref, _UNRESOLVED))
                factors.append(_hard_factor(
                    "sense-scope",
                    (sense_var_ref, scope_var_ref),
                    tuple(sorted(set(allowed))),
                    operator.evidence_refs,
                    "operator scope can activate only for the selected operator sense",
                    MeaningFactorKind.SCOPE_COMPATIBILITY,
                ))

        # Soft simplicity prior is represented explicitly and only breaks ties;
        # it cannot violate hard semantic compatibility.
        for variable in tuple(variables):
            if variable.variable_kind not in {MeaningVariableKind.CONSTRUCTION, MeaningVariableKind.SCOPE}:
                continue
            tuple_scores = []
            for value in variable.values:
                penalty = -0.02 if value.value_ref not in {_INACTIVE, _UNRESOLVED} else 0.0
                tuple_scores.append(((value.value_ref,), penalty))
            factors.append(MeaningFactor(
                factor_ref=_factor_ref("complexity", (variable.variable_ref,)),
                factor_kind=MeaningFactorKind.COMPLEXITY,
                variable_refs=(variable.variable_ref,),
                hard=False,
                tuple_scores=tuple(tuple_scores),
                evidence_refs=variable.evidence_refs,
                reason="bounded complexity prior ranks equally supported meanings without creating facts",
            ))

        graph = MeaningFactorGraph(
            graph_ref="meaning-factor-graph:" + semantic_fingerprint(
                "meaning-factor-graph-ref",
                (lattice.fingerprint, grounding.fingerprint, snapshot.fingerprint, context_ref),
                24,
            ),
            source_lattice_ref=lattice.lattice_ref,
            grounding_ref=grounding.grounding_ref,
            snapshot_fingerprint=snapshot.fingerprint,
            variables=tuple(sorted(variables, key=lambda item: item.variable_ref)),
            factors=tuple(sorted(factors, key=lambda item: item.factor_ref)),
            unresolved_refs=tuple(sorted(unresolved)),
            evidence_refs=tuple(sorted(evidence or {lattice.lattice_ref, grounding.grounding_ref})),
            metadata={
                "context_ref": context_ref,
                "store_revision": snapshot.store_revision,
                "language_evidence_only": True,
                "claims_admitted": False,
                "transitions_authorized": False,
            },
        )
        return graph


def _hard_grounding_factor_kind(kind: GroundingFactorKind) -> MeaningFactorKind:
    if kind == GroundingFactorKind.CONTEXT or kind == GroundingFactorKind.TIME:
        return MeaningFactorKind.CONTEXT_ISOLATION
    if kind == GroundingFactorKind.TYPE:
        return MeaningFactorKind.TYPE_ENTITLEMENT
    if kind in {GroundingFactorKind.STORAGE, GroundingFactorKind.CLAIM_ROLE}:
        return MeaningFactorKind.PORT_COMPATIBILITY
    return MeaningFactorKind.GROUNDING_COHERENCE


def _soft_grounding_factor_kind(kind: GroundingFactorKind) -> MeaningFactorKind:
    if kind in {GroundingFactorKind.DISCOURSE, GroundingFactorKind.SALIENCE, GroundingFactorKind.SYNTAX, GroundingFactorKind.CLAIM_ROLE}:
        return MeaningFactorKind.DISCOURSE_COHERENCE
    if kind == GroundingFactorKind.PROVISIONAL:
        return MeaningFactorKind.COMPLEXITY
    if kind in {
        GroundingFactorKind.IDENTITY,
        GroundingFactorKind.TYPE,
        GroundingFactorKind.STORAGE,
        GroundingFactorKind.CONTEXT,
        GroundingFactorKind.TIME,
        GroundingFactorKind.DESCRIPTION,
        GroundingFactorKind.MULTIMODAL,
        GroundingFactorKind.SYSTEM_OUTPUT,
        GroundingFactorKind.SCHEMA_TOPIC,
    }:
        return MeaningFactorKind.WORLD_PLAUSIBILITY
    return MeaningFactorKind.GROUNDING_COHERENCE


def _port_accepts_candidate(port, candidate: GroundingCandidate) -> bool:
    if PortFillerClass.REFERENT not in port.filler_classes:
        return False
    if port.accepted_storage_kinds and candidate.storage_kind not in port.accepted_storage_kinds:
        return False
    if port.accepted_type_refs and not set(port.accepted_type_refs).intersection(candidate.type_refs):
        return False
    return True


def _port_value_specs(
    candidates: tuple[GroundingCandidate, ...],
    *,
    minimum: int,
    maximum: int | None,
    allow_open: bool,
    allow_omitted: bool,
    evidence_refs: tuple[str, ...],
) -> tuple[MeaningValue, ...]:
    unique = {item.candidate_ref: item for item in candidates}
    ordered = tuple(unique[key] for key in sorted(unique))
    upper = min(len(ordered), _MAX_MULTI_FILLERS if maximum is None else maximum)
    values: list[MeaningValue] = []
    start = max(1, minimum)
    for count in range(start, upper + 1):
        for chosen in combinations(ordered, count):
            refs = tuple(item.candidate_ref for item in chosen)
            values.append(MeaningValue(
                value_ref=_choice_ref("port-fillers", *refs),
                score=0.0,
                evidence_refs=tuple(sorted({ref for item in chosen for factor in item.factors for ref in factor.evidence_refs})),
                metadata={"candidate_refs": refs, "filler_count": count},
            ))
    if allow_omitted:
        values.append(MeaningValue(
            value_ref=_OMITTED,
            score=0.0,
            evidence_refs=evidence_refs,
            metadata={"candidate_refs": (), "omitted": True},
        ))
    if allow_open and (minimum > 0 or not values):
        values.append(MeaningValue(
            value_ref=_GAP,
            score=-0.35,
            evidence_refs=evidence_refs,
            metadata={"candidate_refs": (), "gap": True},
        ))
    # If a required port has no compatible candidate and is not allowed open,
    # no active filler value is returned; the active construction will be pruned.
    return tuple(values)


def _hard_factor(prefix, variable_refs, allowed, evidence_refs, reason, kind):
    return MeaningFactor(
        factor_ref=_factor_ref(prefix, (*variable_refs, allowed)),
        factor_kind=kind,
        variable_refs=tuple(variable_refs),
        hard=True,
        allowed_value_tuples=tuple(allowed),
        evidence_refs=tuple(sorted(set(evidence_refs))),
        reason=reason,
    )


def _var_ref(kind: str, *parts: str) -> str:
    return f"meaning-variable:{kind}:" + semantic_fingerprint("meaning-variable-ref", parts, 24)


def _choice_ref(kind: str, *parts: str) -> str:
    return f"choice:{kind}:" + semantic_fingerprint("meaning-choice-ref", parts, 24)


def _factor_ref(kind: str, parts) -> str:
    return f"meaning-factor:{kind}:" + semantic_fingerprint("meaning-factor-ref", parts, 24)


def _confidence_logit(value: float) -> float:
    # Bounded monotone evidence weight.  This is deliberately not a truth score.
    return (float(value) - 0.5) * 2.0
