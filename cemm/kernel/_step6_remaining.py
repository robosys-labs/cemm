with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

# ----- 1. State delta (line 1582): multi-operation -----
old1 = (
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
new1 = (
    '        if operations:\n'
    '            for op in operations:\n'
    '                graph.add_structural_observation(StructuralObservation(\n'
    '                    obs_type="state_delta",\n'
    '                    target="concept_lattice",\n'
    '                    operation=op.operation,\n'
    '                    target_id=op.target_id,\n'
    '                    fields=op.fields,\n'
    '                    confidence=op.confidence,\n'
    '                    reason=op.reason,\n'
    '                    source_group_id="",\n'
    '                    source_refs=self._source_refs_for_group(graph, ""),\n'
    '                    permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                    evidence_refs=[f"state_delta:{a.id}" for a in state_atoms],\n'
    '                ))'
)
assert old1 in c, 'state delta multi-op block not found'
c = c.replace(old1, new1)
print('1/6 State delta multi-op replaced')

# ----- 2. Remember relation (line 1659): single operation -----
old2 = (
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
new2 = (
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
assert old2 in c, 'remember relation block not found'
c = c.replace(old2, new2)
print('2/6 Remember relation replaced')

# ----- 3. Teaching edges (line 1753): multi-operation -----
old3 = (
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
new3 = (
    '                if operations:\n'
    '                    for op in operations:\n'
    '                        graph.add_structural_observation(StructuralObservation(\n'
    '                            obs_type="teaching_edge",\n'
    '                            target="concept_lattice",\n'
    '                            operation=op.operation,\n'
    '                            target_id=op.target_id,\n'
    '                            fields=op.fields,\n'
    '                            confidence=op.confidence,\n'
    '                            reason=op.reason,\n'
    '                            source_group_id=group.id,\n'
    '                            source_refs=self._source_refs_for_group(graph, group.id),\n'
    '                            permission_refs=self._permission_refs_for_group(graph, group.id),\n'
    '                            evidence_refs=self._collect_all_evidence(graph, [op]) or [f"teaching_group:{group.id}"],\n'
    '                        ))'
)
assert old3 in c, 'teaching edges block not found'
c = c.replace(old3, new3)
print('3/6 Teaching edges replaced')

# ----- 4. Concept resolution (line 1792): multi-operation -----
old4 = (
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
new4 = (
    '        if concept_operations:\n'
    '            for op in concept_operations:\n'
    '                graph.add_structural_observation(StructuralObservation(\n'
    '                    obs_type="concept_candidate",\n'
    '                    target="concept_lattice",\n'
    '                    operation=op.operation,\n'
    '                    target_id=op.target_id,\n'
    '                    fields=op.fields,\n'
    '                    confidence=op.confidence,\n'
    '                    reason=op.reason,\n'
    '                    source_group_id="",\n'
    '                    source_refs=self._source_refs_for_group(graph, ""),\n'
    '                    permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                    evidence_refs=self._collect_all_evidence(graph, [op]) or ["concept_candidates"],\n'
    '                ))'
)
assert old4 in c, 'concept resolution block not found'
c = c.replace(old4, new4)
print('4/6 Concept resolution replaced')

# ----- 5. Port bindings (line 1821): multi-operation -----
old5 = (
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
new5 = (
    '            if operations:\n'
    '                for op in operations:\n'
    '                    graph.add_structural_observation(StructuralObservation(\n'
    '                        obs_type="port_binding",\n'
    '                        target="concept_lattice",\n'
    '                        operation=op.operation,\n'
    '                        target_id=op.target_id,\n'
    '                        fields=op.fields,\n'
    '                        confidence=op.confidence,\n'
    '                        reason=op.reason,\n'
    '                        source_group_id="",\n'
    '                        source_refs=self._source_refs_for_group(graph, ""),\n'
    '                        permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                        evidence_refs=[],\n'
    '                    ))'
)
assert old5 in c, 'port bindings block not found'
c = c.replace(old5, new5)
print('5/6 Port bindings replaced')

# ----- 6. Construction matches (line 1832): multi-operation -----
old6 = (
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
new6 = (
    '        if graph.construction_matches:\n'
    '            for match in graph.construction_matches:\n'
    '                graph.add_structural_observation(StructuralObservation(\n'
    '                    obs_type="construction_match",\n'
    '                    target="construction_lattice",\n'
    '                    operation="observe_construction_match",\n'
    '                    target_id=f"construction:{match.construction_key}",\n'
    '                    fields=match.to_dict(),\n'
    '                    confidence=match.confidence,\n'
    '                    reason="runtime_construction_match",\n'
    '                    source_group_id="",\n'
    '                    source_refs=self._source_refs_for_group(graph, ""),\n'
    '                    permission_refs=self._permission_refs_for_group(graph, ""),\n'
    '                    evidence_refs=[],\n'
    '                ))'
)
assert old6 in c, 'construction matches block not found'
c = c.replace(old6, new6)
print('6/6 Construction matches replaced')

with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('Step 6: all remaining replacements written')
