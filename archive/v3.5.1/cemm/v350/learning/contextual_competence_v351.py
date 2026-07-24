"""Independent structural competence for low-risk contextual lexical/type learning."""
from __future__ import annotations

from ..language.model import FormSenseLinkRecord, LanguageFormRecord, LexicalSenseRecord
from ..schema.model import ReferentTypeSchema, UseOperation
from ..storage.model import RecordKind
from .competence import CompetenceObservation
from .contextual_induction_v351 import (
    CONTEXTUAL_COMPETENCE_RUNNER_REF,
    CONTEXTUAL_COMPETENCE_RUNNER_REVISION,
)


class ContextualLexicalCompetenceExecutorV351:
    """Verify only structural competence; it never validates a candidate by repeating induction evidence."""

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "contextual_lexical_competence_executor"
    COMPETENCE_RUNNER_REF = CONTEXTUAL_COMPETENCE_RUNNER_REF
    COMPETENCE_RUNNER_REVISION = CONTEXTUAL_COMPETENCE_RUNNER_REVISION

    def execute(self, sandbox, package, operation: UseOperation, case_refs):
        candidates = {
            pin.record_kind: [
                sandbox.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                for pin in package.candidate_pins
                if pin.record_kind == pin.record_kind
            ]
            for pin in package.candidate_pins
        }
        forms = [
            item.payload for item in sandbox.store.records(RecordKind.LANGUAGE_FORM, all_revisions=True)
            if isinstance(item.payload, LanguageFormRecord)
            and any(pin.record_kind == RecordKind.LANGUAGE_FORM and pin.record_ref == item.record_ref for pin in package.candidate_pins)
        ]
        senses = [
            item.payload for item in sandbox.store.records(RecordKind.LEXICAL_SENSE, all_revisions=True)
            if isinstance(item.payload, LexicalSenseRecord)
            and any(pin.record_kind == RecordKind.LEXICAL_SENSE and pin.record_ref == item.record_ref for pin in package.candidate_pins)
        ]
        links = [
            item.payload for item in sandbox.store.records(RecordKind.FORM_SENSE_LINK, all_revisions=True)
            if isinstance(item.payload, FormSenseLinkRecord)
            and any(pin.record_kind == RecordKind.FORM_SENSE_LINK and pin.record_ref == item.record_ref for pin in package.candidate_pins)
        ]
        schemas = [
            item.payload for item in sandbox.store.records(RecordKind.SCHEMA, all_revisions=True)
            if isinstance(item.payload, ReferentTypeSchema)
            and any(pin.record_kind == RecordKind.SCHEMA and pin.record_ref == item.record_ref for pin in package.candidate_pins)
        ]
        reasons = []
        if len(forms) != 1 or len(senses) != 1 or len(links) != 1 or len(schemas) != 1:
            reasons.append("candidate_chain_cardinality")
        if not reasons:
            form, sense, link, schema = forms[0], senses[0], links[0], schemas[0]
            if (link.form_ref, link.form_revision) != (form.form_ref, form.revision):
                reasons.append("form_link_mismatch")
            if (link.sense_ref, link.sense_revision) != (sense.sense_ref, sense.revision):
                reasons.append("sense_link_mismatch")
            if (sense.target_ref, sense.target_revision) != (schema.schema_ref, schema.revision):
                reasons.append("sense_target_mismatch")
            if len(schema.parent_links) != 1:
                reasons.append("contextual_schema_requires_one_exact_parent")
            else:
                parent = schema.parent_links[0]
                stored_parent = sandbox.store.get_record(
                    RecordKind.SCHEMA, parent.parent_ref, parent.revision
                )
                if stored_parent is None or not isinstance(stored_parent.payload, ReferentTypeSchema):
                    reasons.append("exact_parent_missing")
            if operation not in {UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY}:
                reasons.append("unsupported_contextual_use")
        passed = () if reasons else tuple(case_refs)
        failed = tuple(case_refs) if reasons else ()
        return CompetenceObservation(
            passed_case_refs=passed,
            failed_case_refs=failed,
            counterexample_refs=tuple(package.counterexample_link_refs),
            proof_refs=(
                "proof:contextual-lexical:exact-chain",
                "proof:contextual-lexical:exact-parent",
            ) if not reasons else (),
            failure_frontier_refs=tuple("frontier:competence:"+reason for reason in reasons),
            independent_lineage_refs=(
                "lineage:competence:contextual-lexical-v351",
            ),
            environment_refs=(
                "environment:isolated-contextual-lexical-v351",
            ),
            metadata={
                "executor": self.SERVICE_KIND,
                "independent_from_induction": True,
                "operation": operation.value,
            },
        )


__all__ = ["ContextualLexicalCompetenceExecutorV351"]
