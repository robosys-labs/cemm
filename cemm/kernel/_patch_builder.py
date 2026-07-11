"""One-time script to refactor meaning_graph_builder.py for 3.3 compliance."""

import re

with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

# Verify preconditions
assert 'from ..learning.learning_types import StructuralObservation' in c
assert "graph_patch_candidate_count': len(graph.structural_observations)" in c

# Step 1: Rename methods
c = c.replace('def _extract_emotional_evaluation_patches(', 'def _extract_emotional_evaluation_observations(')
c = c.replace('def _extract_state_delta_patches(', 'def _extract_state_delta_observations(')
c = c.replace('def _extract_remember_relation_patches(', 'def _extract_remember_relation_observations(')
assert 'def _extract_emotional_evaluation_observations' in c
assert 'def _extract_state_delta_observations' in c
assert 'def _extract_remember_relation_observations' in c

# Step 2: Update method calls in _extract_graph_patches
c = c.replace(
    'self._extract_remember_relation_patches(graph)\n        self._extract_emotional_evaluation_patches(graph)\n        self._extract_state_delta_patches(graph)',
    'self._extract_remember_relation_observations(graph)\n        self._extract_emotional_evaluation_observations(graph)\n        self._extract_state_delta_observations(graph)'
)
assert 'self._extract_remember_relation_observations(graph)' in c
assert 'self._extract_emotional_evaluation_observations(graph)' in c
assert 'self._extract_state_delta_observations(graph)' in c

# Step 3: Update docstrings
c = c.replace(
    "Extract upsert_state patch candidates from schema-driven state delta atoms.",
    "Extract state delta structural observations from schema-driven state delta atoms."
)
c = c.replace(
    "State atoms created by _compile_state_deltas have source='schema_state_delta'.\n        For each, we produce an upsert_state patch operation targeting the entity\n        that holds the state, with the dimension and direction from the schema.",
    "State atoms created by _compile_state_deltas have source='schema_state_delta'.\n        For each, we produce a structural observation for downstream patch compilation."
)
c = c.replace(
    "Extract relation patches from 'remember' command groups.",
    "Extract relation observations from 'remember' command groups."
)
c = c.replace(
    "Detects patterns like 'remember I like coffee' and creates\n        upsert_relation_candidate patches for the embedded relation.",
    "Detects patterns like 'remember I like coffee' and creates\n        structural observations for the embedded relation."
)

# Step 4: Replace GraphPatch creations with StructuralObservation

# 4a: Emotional evaluation - replace the GraphPatch body
old_eval = (
    '            graph.add_patch_candidate(GraphPatch(\n'
    '                source_graph_id=graph.id,\n'
    '                target="concept_lattice",\n'
    '                operations=[PatchOperation(\n'
    '                    operation="upsert_relation_candidate",\n'
    '                    target_id=f"relation:{relation_key}:{source.key}:{target.key}",\n'
    '                    fields={\n'
    '                        "relation_key": relation_key,\n'
    '                        "relation_family": relation_family,\n'
    '                        "subject_concept_id": self._concept_key_for(source),\n'
    '                        "subject_entity_id": source.key if source.kind in ("entity", "self") and source.key in ("user", "self", "world", "conversation", "memory") else "",\n'
    '                        "subject_surface": source.surface,\n'
    '                        "object_concept_id": self._concept_key_for(target),\n'
    '                        "object_entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",\n'
    '                        "object_surface": target.surface,\n'
    '                        "source_atom_ids": [source.id, target.id],\n'
    '                        "inverse_keys": [],\n'
    '                        "group_id": edge.group_id or "",\n'
    '                        "evidence_refs": evidence,\n'
    '                        "features": dict(edge.features) if edge.features else {},\n'
    '                        "relation_scope": edge.features.get("relation_scope", "") if edge.features else "",\n'
    '                        "dimension": edge.features.get("dimension", "") if edge.features else "",\n'
    '                        "qualifiers": self._extract_qualifier_fields(graph, source.id, target.id, edge.group_id or ""),\n'
    '                    },\n'
    '                    confidence=edge.confidence,\n'
    '                    reason="emotional_evaluation_relation",\n'
    '                )],\n'
    '                source_refs=self._source_refs_for_group(graph, edge.group_id or ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, edge.group_id or ""),\n'
    '                evidence_refs=evidence,\n'
    '                confidence=edge.confidence,\n'
    '                reason="emotional_evaluation_candidate",\n'
    '            ))'
)
new_eval = (
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="relation_candidate",\n'
    '                target="concept_lattice",\n'
    '                operation="upsert_relation_candidate",\n'
    '                target_id=f"relation:{relation_key}:{source.key}:{target.key}",\n'
    '                fields={\n'
    '                    "relation_key": relation_key,\n'
    '                    "relation_family": relation_family,\n'
    '                    "subject_concept_id": self._concept_key_for(source),\n'
    '                    "subject_entity_id": source.key if source.kind in ("entity", "self") and source.key in ("user", "self", "world", "conversation", "memory") else "",\n'
    '                    "subject_surface": source.surface,\n'
    '                    "object_concept_id": self._concept_key_for(target),\n'
    '                    "object_entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",\n'
    '                    "object_surface": target.surface,\n'
    '                    "source_atom_ids": [source.id, target.id],\n'
    '                    "inverse_keys": [],\n'
    '                    "group_id": edge.group_id or "",\n'
    '                    "evidence_refs": evidence,\n'
    '                    "features": dict(edge.features) if edge.features else {},\n'
    '                    "relation_scope": edge.features.get("relation_scope", "") if edge.features else "",\n'
    '                    "dimension": edge.features.get("dimension", "") if edge.features else "",\n'
    '                    "qualifiers": self._extract_qualifier_fields(graph, source.id, target.id, edge.group_id or ""),\n'
    '                },\n'
    '                confidence=edge.confidence,\n'
    '                reason="emotional_evaluation_relation",\n'
    '                source_group_id=edge.group_id or "",\n'
    '                source_refs=self._source_refs_for_group(graph, edge.group_id or ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, edge.group_id or ""),\n'
    '                evidence_refs=evidence,\n'
    '            ))'
)
assert old_eval in c, 'Emotional evaluation patch not found'
c = c.replace(old_eval, new_eval)
print('4a: Emotional evaluation done')

# 4b: State delta - replace operations list + GraphPatch
old_state = (
    '        operations: list[PatchOperation] = []\n'
    '        for state_atom in state_atoms:\n'
    '            dimension = state_atom.features.get("dimension", "")\n'
    '            direction = state_atom.features.get("direction", "unknown")\n'
    '            target_role = state_atom.features.get("target_role", "actor")\n'
    '            action_key = state_atom.features.get("action_key", "")\n'
    '            group_id = state_atom.group_id\n'
    '\n'
    '            entity_atom = None\n'
    '            for edge in graph.incoming(state_atom.id, "has_property"):\n'
    '                entity_atom = graph.atoms.get(edge.source_id)\n'
    '                break\n'
    '\n'
    '            if entity_atom is None:\n'
    '                continue\n'
    '\n'
    '            entity_id = entity_atom.key.replace("entity:", "").replace("self:", "")\n'
    '            family = dimension.split(".")[0] if "." in dimension else dimension\n'
    '\n'
    '            operations.append(PatchOperation(\n'
    '                operation="upsert_state",\n'
    '                target_id=f"state:{entity_id}:{dimension}",\n'
    '                fields={\n'
    '                    "entity_id": entity_id,\n'
    '                    "state_family": family,\n'
    '                    "dimension": dimension,\n'
    '                    "direction": direction,\n'
    '                    "action_key": action_key,\n'
    '                    "target_role": target_role,\n'
    '                    "source_atom_ids": [entity_atom.id, state_atom.id],\n'
    '                    "group_id": group_id,\n'
    '                },\n'
    '                confidence=state_atom.confidence,\n'
    '                reason="schema_state_delta",\n'
    '            ))\n'
    '\n'
    '        if operations:\n'
    '            graph.add_patch_candidate(GraphPatch(\n'
    '                source_graph_id=graph.id,\n'
    '                target="concept_lattice",\n'
    '                operations=operations,\n'
    '                source_refs=self._source_refs_for_group(graph, ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                evidence_refs=[f"state_delta:{a.id}" for a in state_atoms],\n'
    '                confidence=max(op.confidence for op in operations),\n'
    '                reason="schema_state_delta_candidates",\n'
    '            ))'
)
new_state = (
    '        for state_atom in state_atoms:\n'
    '            dimension = state_atom.features.get("dimension", "")\n'
    '            direction = state_atom.features.get("direction", "unknown")\n'
    '            target_role = state_atom.features.get("target_role", "actor")\n'
    '            action_key = state_atom.features.get("action_key", "")\n'
    '            group_id = state_atom.group_id\n'
    '\n'
    '            entity_atom = None\n'
    '            for edge in graph.incoming(state_atom.id, "has_property"):\n'
    '                entity_atom = graph.atoms.get(edge.source_id)\n'
    '                break\n'
    '\n'
    '            if entity_atom is None:\n'
    '                continue\n'
    '\n'
    '            entity_id = entity_atom.key.replace("entity:", "").replace("self:", "")\n'
    '            family = dimension.split(".")[0] if "." in dimension else dimension\n'
    '\n'
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="state_delta",\n'
    '                target="concept_lattice",\n'
    '                operation="upsert_state",\n'
    '                target_id=f"state:{entity_id}:{dimension}",\n'
    '                fields={\n'
    '                    "entity_id": entity_id,\n'
    '                    "state_family": family,\n'
    '                    "dimension": dimension,\n'
    '                    "direction": direction,\n'
    '                    "action_key": action_key,\n'
    '                    "target_role": target_role,\n'
    '                    "source_atom_ids": [entity_atom.id, state_atom.id],\n'
    '                    "group_id": group_id,\n'
    '                },\n'
    '                confidence=state_atom.confidence,\n'
    '                reason="schema_state_delta",\n'
    '                source_group_id=group_id,\n'
    '                source_refs=self._source_refs_for_group(graph, group_id),\n'
    '                permission_refs=self._permission_refs_for_group(graph, group_id),\n'
    '                evidence_refs=[f"state_delta:{state_atom.id}"],\n'
    '            ))'
)
assert old_state in c, 'State delta patch not found'
c = c.replace(old_state, new_state)
print('4b: State delta done')

# 4c: Remember relations - replace the GraphPatch body
old_rem = (
    '            graph.add_patch_candidate(GraphPatch(\n'
    '                source_graph_id=graph.id,\n'
    '                target="concept_lattice",\n'
    '                operations=[PatchOperation(\n'
    '                    operation="upsert_relation_candidate",\n'
    '                    target_id=f"relation:{relation_key}:{user_atom.key}:{object_atom.key}",\n'
    '                    fields={\n'
    '                        "relation_key": relation_key,\n'
    '                        "relation_family": relation_family,\n'
    '                        "subject_concept_id": self._concept_key_for(user_atom),\n'
    '                        "subject_entity_id": user_atom.key,\n'
    '                        "subject_surface": user_atom.key if user_atom.kind == "entity" else user_atom.surface,\n'
    '                        "object_concept_id": self._concept_key_for(object_atom),\n'
    '                        "object_entity_id": "",\n'
    '                        "object_surface": object_atom.surface,\n'
    '                        "source_atom_ids": [user_atom.id, object_atom.id],\n'
    '                        "inverse_keys": [],\n'
    '                        "group_id": group.id,\n'
    '                        "evidence_refs": evidence,\n'
    '                        "features": {},\n'
    '                        "qualifiers": self._extract_qualifier_fields(graph, user_atom.id, object_atom.id, group.id),\n'
    '                    },\n'
    '                    confidence=0.7,\n'
    '                    reason="remember_command_relation",\n'
    '                )],\n'
    '                source_refs=self._source_refs_for_group(graph, group.id),\n'
    '                permission_refs=self._permission_refs_for_group(graph, group.id),\n'
    '                evidence_refs=evidence,\n'
    '                confidence=0.7,\n'
    '                reason="remember_command_relation_candidate",\n'
    '            ))'
)
new_rem = (
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="relation_candidate",\n'
    '                target="concept_lattice",\n'
    '                operation="upsert_relation_candidate",\n'
    '                target_id=f"relation:{relation_key}:{user_atom.key}:{object_atom.key}",\n'
    '                fields={\n'
    '                    "relation_key": relation_key,\n'
    '                    "relation_family": relation_family,\n'
    '                    "subject_concept_id": self._concept_key_for(user_atom),\n'
    '                    "subject_entity_id": user_atom.key,\n'
    '                    "subject_surface": user_atom.key if user_atom.kind == "entity" else user_atom.surface,\n'
    '                    "object_concept_id": self._concept_key_for(object_atom),\n'
    '                    "object_entity_id": "",\n'
    '                    "object_surface": object_atom.surface,\n'
    '                    "source_atom_ids": [user_atom.id, object_atom.id],\n'
    '                    "inverse_keys": [],\n'
    '                    "group_id": group.id,\n'
    '                    "evidence_refs": evidence,\n'
    '                    "features": {},\n'
    '                    "qualifiers": self._extract_qualifier_fields(graph, user_atom.id, object_atom.id, group.id),\n'
    '                },\n'
    '                confidence=0.7,\n'
    '                reason="remember_command_relation",\n'
    '                source_group_id=group.id,\n'
    '                source_refs=self._source_refs_for_group(graph, group.id),\n'
    '                permission_refs=self._permission_refs_for_group(graph, group.id),\n'
    '                evidence_refs=evidence,\n'
    '            ))'
)
assert old_rem in c, 'Remember relation patch not found'
c = c.replace(old_rem, new_rem)
print('4c: Remember relations done')

# 4d: Teaching edges - replace the operations loop + GraphPatch in _extract_graph_patches
old_teach = (
    '                if operations:\n'
    '                    graph.add_patch_candidate(GraphPatch(\n'
    '                        source_graph_id=graph.id,\n'
    '                        target="concept_lattice",\n'
    '                        operations=operations,\n'
    '                        source_refs=self._source_refs_for_group(graph, group.id),\n'
    '                        permission_refs=self._permission_refs_for_group(graph, group.id),\n'
    '                        evidence_refs=self._collect_all_evidence(graph, operations) or [f"teaching_group:{group.id}"],\n'
    '                        confidence=max(operation.confidence for operation in operations),\n'
    '                        reason="teaching_group_relation_candidates",\n'
    '                    ))'
)
new_teach = (
    '                    graph.add_structural_observation(StructuralObservation(\n'
    '                        obs_type="relation_candidate",\n'
    '                        target="concept_lattice",\n'
    '                        operation="upsert_relation_candidate",\n'
    '                        target_id=f"relation:{edge.edge_type}:{source.key}:{target.key}",\n'
    '                        fields={\n'
    '                            "relation_key": edge.edge_type,\n'
    '                            "relation_family": self._relation_family_for_edge(edge.edge_type),\n'
    '                            "subject_concept_id": self._concept_key_for(source),\n'
    '                            "subject_entity_id": source.key if source.kind in ("entity", "self") and source.key in ("user", "self", "world", "conversation", "memory") else "",\n'
    '                            "subject_surface": source.surface,\n'
    '                            "object_concept_id": self._concept_key_for(target),\n'
    '                            "object_entity_id": target.key if target.kind in ("entity", "self") and target.key in ("user", "self", "world", "conversation", "memory") else "",\n'
    '                            "object_surface": target.surface,\n'
    '                            "source_atom_ids": [source.id, target.id],\n'
    '                            "inverse_keys": [],\n'
    '                            "group_id": group.id,\n'
    '                            "evidence_refs": evidence,\n'
    '                            "features": edge_features,\n'
    '                            "relation_scope": edge_features.get("relation_scope", ""),\n'
    '                            "dimension": edge_features.get("dimension", "") or edge_features.get("property_dimension", ""),\n'
    '                            "qualifiers": self._extract_qualifier_fields(graph, source.id, target.id, group.id),\n'
    '                        },\n'
    '                        confidence=edge.confidence,\n'
    '                        reason="user_teaching_graph_relation",\n'
    '                        source_group_id=group.id,\n'
    '                        source_refs=self._source_refs_for_group(graph, group.id),\n'
    '                        permission_refs=self._permission_refs_for_group(graph, group.id),\n'
    '                        evidence_refs=evidence,\n'
    '                    ))'
)
assert old_teach in c, 'Teaching edges patch not found'
c = c.replace(old_teach, new_teach)
print('4d: Teaching edges done')

# Remove the "operations = []" line from teaching edges block
old_ops_init = (
    '                operations = []\n'
    '                for edge in teaching_edges:'
)
new_ops_init = '                for edge in teaching_edges:'
assert old_ops_init in c, 'operations initializer not found'
c = c.replace(old_ops_init, new_ops_init)
print('4e: operations=[] removed')

# 4f: Concept resolutions - replace the operations loop + GraphPatch
old_conc = (
    '        concept_operations = []\n'
    '        for resolution in graph.concept_resolutions:\n'
    '            if resolution.state != "new_candidate":\n'
    '                continue\n'
    '            atom = graph.atoms.get(resolution.atom_id)\n'
    '            if atom is None:\n'
    '                continue\n'
    '            evidence = self._evidence_refs(atom.evidence) if hasattr(atom, "evidence") else []\n'
    '            if not evidence:\n'
    '                evidence = [f"concept_resolution:{resolution.atom_id}"]\n'
    '            concept_operations.append(PatchOperation(\n'
    '                operation="upsert_concept_candidate",\n'
    '                target_id=resolution.concept_id,\n'
    '                fields={\n'
    '                    "concept_key": atom.key,\n'
    '                    "atom_kind": atom.kind,\n'
    '                    "surface": atom.surface,\n'
    '                    "state": "candidate_atom",\n'
    '                    "evidence_refs": evidence,\n'
    '                },\n'
    '                confidence=resolution.confidence,\n'
    '                reason=resolution.reason,\n'
    '            ))\n'
    '        if concept_operations:\n'
    '            graph.add_patch_candidate(GraphPatch(\n'
    '                source_graph_id=graph.id,\n'
    '                target="concept_lattice",\n'
    '                operations=concept_operations,\n'
    '                source_refs=self._source_refs_for_group(graph, ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                evidence_refs=self._collect_all_evidence(graph, concept_operations) or ["concept_candidates"],\n'
    '                confidence=max(operation.confidence for operation in concept_operations),\n'
    '                reason="new_surface_concept_candidates",\n'
    '            ))'
)
new_conc = (
    '        for resolution in graph.concept_resolutions:\n'
    '            if resolution.state != "new_candidate":\n'
    '                continue\n'
    '            atom = graph.atoms.get(resolution.atom_id)\n'
    '            if atom is None:\n'
    '                continue\n'
    '            evidence = self._evidence_refs(atom.evidence) if hasattr(atom, "evidence") else []\n'
    '            if not evidence:\n'
    '                evidence = [f"concept_resolution:{resolution.atom_id}"]\n'
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="concept_candidate",\n'
    '                target="concept_lattice",\n'
    '                operation="upsert_concept_candidate",\n'
    '                target_id=resolution.concept_id,\n'
    '                fields={\n'
    '                    "concept_key": atom.key,\n'
    '                    "atom_kind": atom.kind,\n'
    '                    "surface": atom.surface,\n'
    '                    "state": "candidate_atom",\n'
    '                    "evidence_refs": evidence,\n'
    '                },\n'
    '                confidence=resolution.confidence,\n'
    '                reason=resolution.reason,\n'
    '                source_refs=self._source_refs_for_group(graph, ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                evidence_refs=evidence,\n'
    '            ))'
)
assert old_conc in c, 'Concept resolution patch not found'
c = c.replace(old_conc, new_conc)
print('4f: Concept resolutions done')

# 4g: Port bindings - replace the operations list + GraphPatch
old_port = (
    '        if graph.port_bindings:\n'
    '            operations = [\n'
    '                PatchOperation(\n'
    '                    operation="observe_port_binding",\n'
    '                    target_id=binding.port_id,\n'
    '                    fields={\n'
    '                        "owner_concept_id": binding.owner_concept_id,\n'
    '                        "port_key": binding.port_key,\n'
    '                        "filler_atom_id": binding.filler_atom_id,\n'
    '                        "status": binding.status,\n'
    '                    },\n'
    '                    confidence=binding.score,\n'
    '                    reason="runtime_port_binding_observation",\n'
    '                )\n'
    '                for binding in graph.port_bindings\n'
    '                if binding.score >= 0.55\n'
    '            ]\n'
    '            if operations:\n'
    '                graph.add_patch_candidate(GraphPatch(\n'
    '                    source_graph_id=graph.id,\n'
    '                    target="concept_lattice",\n'
    '                    operations=operations,\n'
    '                    source_refs=self._source_refs_for_group(graph, ""),\n'
    '                    permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                    confidence=max(operation.confidence for operation in operations),\n'
    '                    reason="port_binding_observations",\n'
    '                ))'
)
new_port = (
    '        for binding in graph.port_bindings:\n'
    '            if binding.score < 0.55:\n'
    '                continue\n'
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="port_binding",\n'
    '                target="concept_lattice",\n'
    '                operation="observe_port_binding",\n'
    '                target_id=binding.port_id,\n'
    '                fields={\n'
    '                    "owner_concept_id": binding.owner_concept_id,\n'
    '                    "port_key": binding.port_key,\n'
    '                    "filler_atom_id": binding.filler_atom_id,\n'
    '                    "status": binding.status,\n'
    '                },\n'
    '                confidence=binding.score,\n'
    '                reason="runtime_port_binding_observation",\n'
    '                source_refs=self._source_refs_for_group(graph, ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '            ))'
)
assert old_port in c, 'Port binding patch not found'
c = c.replace(old_port, new_port)
print('4g: Port bindings done')

# 4h: Construction matches - replace the GraphPatch
old_cons = (
    '        if graph.construction_matches:\n'
    '            graph.add_patch_candidate(GraphPatch(\n'
    '                source_graph_id=graph.id,\n'
    '                target="construction_lattice",\n'
    '                operations=[\n'
    '                    PatchOperation(\n'
    '                        operation="observe_construction_match",\n'
    '                        target_id=f"construction:{match.construction_key}",\n'
    '                        fields=match.to_dict(),\n'
    '                        confidence=match.confidence,\n'
    '                        reason="runtime_construction_match",\n'
    '                    )\n'
    '                    for match in graph.construction_matches\n'
    '                ],\n'
    '                source_refs=self._source_refs_for_group(graph, ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                confidence=max(match.confidence for match in graph.construction_matches),\n'
    '                reason="construction_observations",\n'
    '            ))'
)
new_cons = (
    '        for match in graph.construction_matches:\n'
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="construction_match",\n'
    '                target="construction_lattice",\n'
    '                operation="observe_construction_match",\n'
    '                target_id=f"construction:{match.construction_key}",\n'
    '                fields=match.to_dict(),\n'
    '                confidence=match.confidence,\n'
    '                reason="runtime_construction_match",\n'
    '                source_group_id=match.group_id,\n'
    '                source_refs=self._source_refs_for_group(graph, ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '            ))'
)
assert old_cons in c, 'Construction match patch not found'
c = c.replace(old_cons, new_cons)
print('4h: Construction matches done')

# Verify no more add_patch_candidate calls
if 'add_patch_candidate(GraphPatch' in c or 'add_patch_candidate(GraphPatch' in c:
    remaining = c.count('add_patch_candidate')
    print(f'WARNING: {remaining} add_patch_candidate calls remain!')
else:
    print('SUCCESS: No more GraphPatch creation in builder')

# Save
with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('File saved!')
