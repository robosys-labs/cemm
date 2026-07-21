"""Phase-8 runtime learning frontier typing and pre-cycle promotion cutover."""
from __future__ import annotations

from dataclasses import dataclass

from ..schema.model import SchemaClass
from ..storage.model import RecordKind
from ..runtime_kernel import FrontierClass
from .frontier import EvidenceAggregator, FrontierObservation
from .model import LearningPackageStatus, PromotionDecisionKind
from .promotion import PromotionCoordinator, PromotionPolicyEngine


class TypedRuntimeFrontierCompiler:
    """Compile typed learning frontiers from runtime artifacts.

    Artifact contracts are primary. Canonical frontier-prefix fallback exists only
    for older StageOutcome producers and never inspects user surface text.
    """

    def compile(self, cycle) -> tuple[FrontierObservation, ...]:
        observations: dict[tuple, FrontierObservation] = {}

        def add(item: FrontierObservation) -> None:
            key = (
                item.missing_contract, item.expected_record_kinds,
                item.expected_schema_classes, item.accepted_anchor_types,
                item.target_ref, item.context_ref, item.permission_ref,
            )
            observations.setdefault(key, item)

        lattice = cycle.artifacts.get("form_lattice")
        if lattice is not None:
            senses_by_form = {}
            for sense in getattr(lattice, "sense_candidates", ()):
                senses_by_form.setdefault(
                    sense.form_candidate_ref, []
                ).append(sense)
            for form in getattr(lattice, "form_candidates", ()):
                if senses_by_form.get(form.candidate_ref):
                    continue
                add(FrontierObservation(
                    missing_contract=(
                        "lexical_sense:"
                        f"{form.form_ref}@{form.form_revision}"
                    ),
                    expected_record_kinds=(
                        RecordKind.LEXEME,
                        RecordKind.FORM_LEXEME_LINK,
                        RecordKind.LEXICAL_SENSE,
                        RecordKind.LEXEME_SENSE_LINK,
                        RecordKind.SEMANTIC_CONTRIBUTION_SPEC,
                    ),
                    expected_schema_classes=(),
                    accepted_anchor_types=(
                        "form_candidate",
                        "lexical_sense",
                    ),
                    evidence_refs=form.evidence_refs
                    or (lattice.lattice_ref,),
                    candidate_refs=(),
                    target_ref=form.form_ref,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                ))
            for sense in getattr(lattice, "sense_candidates", ()):
                semantic = tuple(
                    contribution
                    for contribution in sense.contributions
                    if contribution.contribution_kind.value
                    != "grammatical_feature"
                )
                if semantic or bool(
                    sense.metadata.get("semantic_targetless", False)
                ):
                    continue
                add(FrontierObservation(
                    missing_contract=(
                        "semantic_contribution:"
                        f"{sense.sense_ref}@{sense.sense_revision}"
                    ),
                    expected_record_kinds=(
                        RecordKind.SEMANTIC_CONTRIBUTION_SPEC,
                        RecordKind.CONSTRUCTION,
                        RecordKind.CONSTRUCTION_PROGRAM,
                    ),
                    expected_schema_classes=(),
                    accepted_anchor_types=(
                        "lexical_sense",
                        "semantic_contribution",
                        "semantic_construction",
                    ),
                    evidence_refs=sense.evidence_refs
                    or (lattice.lattice_ref,),
                    candidate_refs=(),
                    target_ref=sense.sense_ref,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                ))
            for span in getattr(lattice, "unresolved_spans", ()):
                add(FrontierObservation(
                    missing_contract=f"form_span:{span.start}:{span.end}",
                    expected_record_kinds=(
                        RecordKind.LANGUAGE_FORM, RecordKind.LEXEME,
                        RecordKind.FORM_LEXEME_LINK, RecordKind.LEXICAL_SENSE,
                        RecordKind.LEXEME_SENSE_LINK,
                        RecordKind.SEMANTIC_CONTRIBUTION_SPEC,
                        RecordKind.MORPHOLOGY_ANALYSIS_RULE,
                    ),
                    expected_schema_classes=(),
                    accepted_anchor_types=("form_span",),
                    evidence_refs=(lattice.lattice_ref,),
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                ))

        bundle = cycle.artifacts.get("meaning_bundle")
        if (
            bundle is not None
            and bundle.metadata.get("selection_authority")
            == "ambiguous_semantic_clusters"
        ):
            add(FrontierObservation(
                missing_contract="meaning_selection:semantic_cluster_ambiguity",
                expected_record_kinds=(
                    RecordKind.SCHEMA,
                    RecordKind.SEMANTIC_APPLICATION,
                ),
                expected_schema_classes=(),
                accepted_anchor_types=(
                    "meaning_hypothesis",
                    "clarification",
                ),
                evidence_refs=bundle.evidence_refs
                or (cycle.cycle_ref,),
                candidate_refs=tuple(
                    bundle.selection.close_alternative_refs
                ),
                target_ref=None,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
            ))

        grounding = cycle.artifacts.get("grounding_result") or cycle.artifacts.get("grounding_preparation")
        if grounding is not None:
            candidate_mentions = {item.mention_ref for item in getattr(grounding, "candidates", ())}
            for mention in getattr(grounding, "mentions", ()):
                if mention.mention_ref in candidate_mentions:
                    continue
                add(FrontierObservation(
                    missing_contract=f"referent_grounding:{mention.mention_ref}",
                    expected_record_kinds=(
                        RecordKind.REFERENT, RecordKind.TYPE_ASSERTION,
                        RecordKind.IDENTITY_FACET,
                    ),
                    expected_schema_classes=(SchemaClass.REFERENT_TYPE,),
                    accepted_anchor_types=("mention", "discourse_anchor", "referent_knowledge"),
                    evidence_refs=tuple(getattr(mention, "evidence_refs", ())) or (cycle.cycle_ref,),
                    target_ref=mention.mention_ref,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                ))

        query = cycle.artifacts.get("retrieval_result")
        if query is not None:
            unresolved = set(getattr(query, "unresolved_query_refs", ()))
            for variable in getattr(getattr(query, "request", None), "variables", ()):
                if variable.variable_ref not in unresolved:
                    continue
                kinds = {RecordKind.SCHEMA, RecordKind.SEMANTIC_APPLICATION}
                classes = tuple(variable.expected_schema_classes)
                if SchemaClass.STATE_DIMENSION in classes:
                    kinds.add(RecordKind.STATE_ASSIGNMENT)
                if SchemaClass.REFERENT_TYPE in classes:
                    kinds.update({RecordKind.REFERENT, RecordKind.TYPE_ASSERTION})
                if SchemaClass.EVENT in classes:
                    kinds.add(RecordKind.EVENT_OCCURRENCE)
                add(FrontierObservation(
                    missing_contract=f"query_binding:{variable.variable_ref}",
                    expected_record_kinds=tuple(sorted(kinds, key=lambda item: item.value)),
                    expected_schema_classes=classes,
                    accepted_anchor_types=tuple(sorted({
                        "semantic_variable", "query_projection",
                        "referent_knowledge", *variable.expected_type_refs,
                    })),
                    evidence_refs=tuple(variable.evidence_refs) or (query.result_ref,),
                    candidate_refs=tuple(
                        f"{ref}@{revision}" for ref, revision in variable.projection_candidates
                    ),
                    target_ref=variable.variable_ref,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                ))

        covered = {item.missing_contract for item in observations.values()}
        learnable_classes = {
            FrontierClass.SEMANTIC_LEARNING,
            FrontierClass.GROUNDING_AMBIGUITY,
            FrontierClass.REFERENCE_AMBIGUITY,
            FrontierClass.REALIZATION_GAP,
        }
        for frontier in cycle.artifacts.get("runtime_frontiers", ()):
            if frontier.frontier_class not in learnable_classes and not bool(
                frontier.metadata.get("learnable", False)
            ):
                continue
            if frontier.missing_contract in covered:
                continue
            kinds = (
                (RecordKind.LEXICAL_SENSE, RecordKind.LEXEME,
                 RecordKind.LEXEME_SENSE_LINK, RecordKind.LANGUAGE_FORM,
                 RecordKind.ARGUMENT_FRAME, RecordKind.LINEARIZATION_RULE)
                if frontier.frontier_class == FrontierClass.REALIZATION_GAP
                else (RecordKind.SCHEMA, RecordKind.SEMANTIC_APPLICATION)
            )
            add(FrontierObservation(
                missing_contract=frontier.missing_contract,
                expected_record_kinds=tuple(kinds),
                expected_schema_classes=(),
                accepted_anchor_types=(frontier.frontier_class.value,),
                evidence_refs=frontier.evidence_refs or (cycle.cycle_ref,),
                candidate_refs=frontier.candidate_refs,
                target_ref=frontier.target_refs[0] if len(frontier.target_refs) == 1 else None,
                context_ref=frontier.context_ref,
                permission_ref=frontier.permission_ref,
            ))
            covered.add(frontier.missing_contract)
        compatibility = (
            (("frontier:realization:",), (RecordKind.LEXICAL_SENSE, RecordKind.LEXEME, RecordKind.LEXEME_SENSE_LINK, RecordKind.LANGUAGE_FORM, RecordKind.ARGUMENT_FRAME, RecordKind.LINEARIZATION_RULE), ("response_uol",)),
            (("frontier:operation:", "frontier:operation-"), (RecordKind.OPERATION_ADAPTER_CONTRACT, RecordKind.CAPABILITY_INSTANCE), ("operation_contract",)),
            (("frontier:construction:", "frontier:composition:"), (RecordKind.CONSTRUCTION, RecordKind.CONSTRUCTION_PROGRAM, RecordKind.SCHEMA), ("semantic_construction",)),
        )
        for ref in sorted(set(cycle.frontiers)):
            if ref in covered or any(ref.endswith(item.target_ref or "\0") for item in observations.values() if item.target_ref):
                continue
            matched = None
            for prefixes, kinds, anchors in compatibility:
                if ref.startswith(prefixes):
                    matched = (kinds, anchors)
                    break
            # Unknown raw frontier prefixes are diagnostics until a producer emits
            # a typed learnable RuntimeFrontier. Do not convert every runtime
            # failure into a generic schema-learning task.
            if matched is None:
                continue
            kinds, anchors = matched
            add(FrontierObservation(
                missing_contract=ref,
                expected_record_kinds=tuple(kinds),
                expected_schema_classes=(),
                accepted_anchor_types=tuple(anchors),
                evidence_refs=(cycle.cycle_ref,),
                target_ref=None,
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
            ))
        return tuple(sorted(observations.values(), key=lambda item: (item.missing_contract, item.target_ref or "")))


@dataclass(frozen=True, slots=True)
class RuntimeActivationTrace:
    considered_package_refs: tuple[str, ...]
    promoted_package_refs: tuple[str, ...]
    blocked_package_refs: tuple[str, ...]


class LearningRuntimeActivator:
    """Promote only already-reviewed, competence-ready exact-pin packages.

    This runs before Stage 0 so the cycle pins the post-promotion substrate. It
    never invents candidates or treats observation frequency as authority.
    """

    def __init__(self, store) -> None:
        self.store = store

    def activate_ready(self) -> RuntimeActivationTrace:
        considered = []
        promoted = []
        blocked = []
        # Only effective/latest package revisions are eligible. A package promoted
        # in a prior cycle leaves its older PROMOTABLE revision in history; scanning
        # all revisions would otherwise attempt to promote stale authority again.
        packages = tuple(
            item.payload for item in self.store.repositories.learning_packages.all()
            if item.payload.lifecycle_status == LearningPackageStatus.PROMOTABLE
        )
        for package in packages:
            considered.append(package.package_ref)
            # Human/review authority and explicit activation authorization remain
            # mandatory. The runtime does not self-sign a learned concept.
            if not package.review_refs or not package.metadata.get("authorization_refs"):
                blocked.append(package.package_ref)
                continue
            competence = tuple(
                item.payload for item in self.store.repositories.competence_results.all(all_revisions=True)
                if item.payload.package_ref == package.package_ref
                and item.payload.package_revision == package.revision
            )
            evidence_links = tuple(
                item.payload for item in self.store.repositories.learning_evidence_links.all(all_revisions=True)
                if item.payload.package_ref == package.package_ref
                and item.payload.package_revision == package.revision
            )
            summary = EvidenceAggregator.summarize(evidence_links)
            try:
                engine = PromotionPolicyEngine(self.store)
                result = engine.evaluate(package, competence, summary)
                if result.decision != PromotionDecisionKind.PROMOTE:
                    blocked.append(package.package_ref)
                    continue
                decision = engine.decision_record(
                    package,
                    result,
                    policy_ref=str(package.metadata.get("promotion_policy_ref", "policy:runtime-reviewed-learning-promotion")),
                    review_refs=tuple(package.review_refs),
                    authorization_refs=tuple(package.metadata.get("authorization_refs", ())),
                    risk_refs=tuple(package.metadata.get("risk_refs", ())),
                )
                commit = PromotionCoordinator(self.store).promote(package, decision)
            except (ValueError, RuntimeError):
                # A stale/malformed package is a blocked learning frontier, not a
                # reason to corrupt or abort an otherwise valid runtime cycle.
                blocked.append(package.package_ref)
                continue
            if not commit.committed:
                blocked.append(package.package_ref)
                continue
            promoted.append(package.package_ref)
        return RuntimeActivationTrace(tuple(sorted(considered)), tuple(sorted(promoted)), tuple(sorted(blocked)))
