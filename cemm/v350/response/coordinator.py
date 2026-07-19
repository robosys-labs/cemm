"""Atomic Response UOL/proof persistence."""
from __future__ import annotations
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record,record_fingerprints,record_ref,record_revision
from ..storage.model import GraphPatch,PatchOperation,PatchOperationKind,RecordDependency,RecordKind
from ..learning.model import LearningFrontierRecord
from .model import ResponseTransformationProof,ResponseUOLRecord
from .planner import ResponseAuthorizationGate

class ResponseUOLCommitCoordinator:
 def __init__(self,store): self.store=store
 def commit(self,response:ResponseUOLRecord,proofs:tuple[ResponseTransformationProof,...],frontiers:tuple[LearningFrontierRecord,...]=()):
  ResponseAuthorizationGate(self.store).require_authorized(response,proofs)
  with self.store.snapshot() as snapshot:
   # Reject a plan built before any intervening store change. The exact response snapshot is authority.
   if snapshot.store_revision!=response.snapshot_revision or snapshot.fingerprint!=response.snapshot_fingerprint:
    raise ValueError("stale Response UOL snapshot; re-plan before commit")
   ops=[]; proof_fps={}; frontier_fps={}
   if set(response.unresolved_frontier_refs)!={f.frontier_ref for f in frontiers}:
    raise ValueError("Response UOL frontier records do not match unresolved_frontier_refs")
   for frontier in frontiers:
    deps=(RecordDependency(response.goal_decision_pin.record_kind,response.goal_decision_pin.record_ref,response.goal_decision_pin.revision,response.goal_decision_pin.record_fingerprint,"response_frontier_goal_decision"),)
    ops.append(self._upsert(RecordKind.LEARNING_FRONTIER,frontier,deps,"persist exact response-planning frontier"))
    frontier_fps[frontier.frontier_ref]=record_fingerprints(RecordKind.LEARNING_FRONTIER,frontier)[1]
   for proof in proofs:
    deps=[RecordDependency(proof.goal_candidate_pin.record_kind,proof.goal_candidate_pin.record_ref,proof.goal_candidate_pin.revision,proof.goal_candidate_pin.record_fingerprint,"response_goal")]
    deps.append(RecordDependency(proof.rule_pin.record_kind,proof.rule_pin.record_ref,proof.rule_pin.revision,proof.rule_pin.record_fingerprint,"response_transform_rule"))
    deps += [RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,"response_input") for p in (*proof.input_pins,*proof.authorization_pins)]
    ops.append(self._upsert(RecordKind.RESPONSE_TRANSFORMATION_PROOF,proof,tuple(deps),"persist proof-carrying semantic response transformation"))
    proof_fps[proof.proof_ref]=record_fingerprints(RecordKind.RESPONSE_TRANSFORMATION_PROOF,proof)[1]
   deps=[RecordDependency(response.goal_decision_pin.record_kind,response.goal_decision_pin.record_ref,response.goal_decision_pin.revision,response.goal_decision_pin.record_fingerprint,"response_goal_decision")]
   deps += [RecordDependency(p.record_kind,p.record_ref,p.revision,p.record_fingerprint,"response_source") for p in (*response.selected_goal_pins,*response.source_pins)]
   deps += [RecordDependency(RecordKind.RESPONSE_TRANSFORMATION_PROOF,r,1,proof_fps[r],"response_transform_proof") for r in response.transformation_proof_refs]
   deps += [RecordDependency(RecordKind.LEARNING_FRONTIER,r,1,frontier_fps[r],"response_unresolved_frontier") for r in response.unresolved_frontier_refs]
   ops.append(self._upsert(RecordKind.RESPONSE_UOL,response,tuple(deps),"persist all-and-only authorized Response UOL"))
   patch=GraphPatch(patch_ref="graph-patch:response-uol:"+semantic_fingerprint("response-uol-patch",(response.response_ref,snapshot.fingerprint),24),context_ref=response.context_ref,scope_ref="phase16:response-uol",source_ref="source:phase16:response-meaning-planner",permission_ref=response.permission_ref,operations=tuple(ops),expected_store_revision=snapshot.store_revision,validation_requirements=("phase16_all_and_only_authorized_meaning","phase16_no_surface_authority"),metadata={"phase":16,"surface_strings":False})
  result=self.store.apply_patch(patch)
  if not result.committed: raise RuntimeError("Response UOL commit failed: "+"; ".join(result.errors))
  return result
 @staticmethod
 def _upsert(kind,record,deps,reason):
  return PatchOperation(operation_ref="patch-operation:phase16-response:"+semantic_fingerprint("phase16-response-op",(kind.value,record_ref(kind,record),record_revision(kind,record),reason),20),operation_kind=PatchOperationKind.UPSERT,record_kind=kind,target_ref=record_ref(kind,record),record_revision=record_revision(kind,record),payload=encode_record(kind,record),dependencies=deps,reason=reason)
