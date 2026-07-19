"""Semantic—not string—equivalence runner for Phase 19."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping,Protocol,Any

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from .model import EquivalenceOutcome,MigrationIntentionalChangeRecord,SemanticEquivalenceRecord

SEMANTIC_DIMENSIONS=("selected_meaning","referent_identity","epistemic_stance","state_transition","capability_status","impact_importance","goal_selection","operation_decision","response_uol","output_commitment")

@dataclass(frozen=True,slots=True)
class SemanticTrace:
 trace_ref:str
 dimension_fingerprints:Mapping[str,str]
 record_pins:tuple[PinnedRecord,...]
 proof_refs:tuple[str,...]=()

class BehaviorTraceRunner(Protocol):
 runner_ref:str
 runner_revision:str
 def run(self,fixture:Any)->SemanticTrace:...

class EquivalenceRunner:
 def __init__(self,runner_ref="runner:phase19:semantic-equivalence",runner_revision="1"):
  self.runner_ref=runner_ref;self.runner_revision=runner_revision
 def compare(self,*,source_fixture_pins:tuple[PinnedRecord,...],legacy_trace:SemanticTrace,v350_trace:SemanticTrace,intentional_changes:tuple[MigrationIntentionalChangeRecord,...]=(),permission_ref="internal"):
  changes={(x.legacy_behavior_ref,x.v350_behavior_ref):x for x in intentional_changes}
  dimensions=[];diffs=[];change_pins=[]
  for name in SEMANTIC_DIMENSIONS:
   left=legacy_trace.dimension_fingerprints.get(name);right=v350_trace.dimension_fingerprints.get(name)
   if left is None or right is None:
    outcome=EquivalenceOutcome.UNTESTABLE;diffs.append(f"untestable:{name}")
   elif left==right:
    outcome=EquivalenceOutcome.EQUIVALENT
   else:
    change=changes.get((left,right))
    comparison_pins={(p.key,p.record_fingerprint) for p in (*source_fixture_pins,*v350_trace.record_pins)}
    if change is not None and {(p.key,p.record_fingerprint) for p in change.fixture_pins}.issubset(comparison_pins):
     outcome=EquivalenceOutcome.INTENTIONALLY_CHANGED
     change_pins.append(PinnedRecord(RecordKind.MIGRATION_INTENTIONAL_CHANGE,change.change_ref,change.revision,record_fingerprints(RecordKind.MIGRATION_INTENTIONAL_CHANGE,change)[1]))
    else:
     outcome=EquivalenceOutcome.NOT_EQUIVALENT;diffs.append(f"semantic_difference:{name}:{left}!={right}")
   dimensions.append((name,outcome))
  values={o for _,o in dimensions}
  if EquivalenceOutcome.NOT_EQUIVALENT in values:overall=EquivalenceOutcome.NOT_EQUIVALENT
  elif EquivalenceOutcome.UNTESTABLE in values:overall=EquivalenceOutcome.PARTIALLY_EQUIVALENT
  elif EquivalenceOutcome.INTENTIONALLY_CHANGED in values:overall=EquivalenceOutcome.INTENTIONALLY_CHANGED
  else:overall=EquivalenceOutcome.EQUIVALENT
  target_pins=tuple(v350_trace.record_pins)
  return SemanticEquivalenceRecord(equivalence_ref="semantic-equivalence:"+semantic_fingerprint("semantic-equivalence",(legacy_trace.trace_ref,v350_trace.trace_ref,tuple(dimensions)),24),source_fixture_pins=source_fixture_pins,target_trace_pins=target_pins,dimensions=tuple(dimensions),overall=overall,intentional_change_pins=tuple(sorted(set(change_pins),key=lambda p:p.key)),difference_refs=tuple(diffs),proof_refs=tuple(sorted(set((*legacy_trace.proof_refs,*v350_trace.proof_refs)))),runner_ref=self.runner_ref,runner_revision=self.runner_revision,permission_ref=permission_ref)
