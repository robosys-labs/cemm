"""Semantic output-reference resolution; never transcript-substring matching."""
from __future__ import annotations
from dataclasses import dataclass

from ..learning.model import FrontierResolutionStatus, LearningFrontierRecord
from ..schema.model import semantic_fingerprint
from ..storage.model import RecordKind
from .model import OutputReferenceAnchorRecord


@dataclass(frozen=True,slots=True)
class OutputReferenceResolution:
    selected: OutputReferenceAnchorRecord|None
    candidates: tuple[OutputReferenceAnchorRecord,...]
    frontier: LearningFrontierRecord|None


class OutputReferenceResolver:
    def __init__(self,store):self.store=store

    def resolve(self,*,context_ref:str,permission_ref:str,audience_refs:tuple[str,...],accepted_target_kind_refs:tuple[str,...]=(),target_ref_hint:str|None=None) -> OutputReferenceResolution:
        rows=[]
        for stored in self.store.records(RecordKind.OUTPUT_REFERENCE_ANCHOR):
            item=stored.payload
            if not isinstance(item,OutputReferenceAnchorRecord):continue
            if item.context_ref!=context_ref:continue
            if item.permission_ref not in {"public",permission_ref}:continue
            if not set(audience_refs).issubset(set(item.audience_refs)):continue
            if accepted_target_kind_refs and item.target_kind_ref not in accepted_target_kind_refs:continue
            if target_ref_hint is not None and item.target_ref!=target_ref_hint:continue
            # Exact target pins, when present, must still resolve. Historical discourse itself remains,
            # but a stale target cannot silently become current reference authority.
            if item.target_pin is not None:
                exact=self.store.get_record(item.target_pin.record_kind,item.target_pin.record_ref,item.target_pin.revision)
                if exact is None or exact.record_fingerprint!=item.target_pin.record_fingerprint:continue
            rows.append(item)
        rows.sort(key=lambda x:(-x.salience,-x.ordinal,x.anchor_ref))
        candidates=tuple(rows)
        if not candidates:
            return OutputReferenceResolution(None,(),self._frontier(context_ref,permission_ref,"no_output_reference_candidate",()))
        best=candidates[0]
        ties=tuple(x for x in candidates if x.salience==best.salience and x.ordinal==best.ordinal)
        if len(ties)>1:
            return OutputReferenceResolution(None,candidates,self._frontier(context_ref,permission_ref,"ambiguous_output_reference",tuple(x.target_ref for x in ties)))
        return OutputReferenceResolution(best,candidates,None)

    @staticmethod
    def _frontier(context_ref,permission_ref,missing,refs):
        return LearningFrontierRecord(
            frontier_ref="learning-frontier:output-reference:"+semantic_fingerprint("output-reference-frontier",(context_ref,permission_ref,missing,refs),24),
            target_ref=None,missing_contract=missing,expected_record_kinds=(RecordKind.OUTPUT_REFERENCE_ANCHOR,),expected_schema_classes=(),
            accepted_anchor_types=(),evidence_refs=(),candidate_refs=tuple(refs),resolution_status=FrontierResolutionStatus.OPEN,context_ref=context_ref,permission_ref=permission_ref)
