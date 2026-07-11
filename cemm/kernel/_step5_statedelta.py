with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

old = (
    '            graph.add_patch_candidate(GraphPatch(\n'
    '                source_graph_id=graph.id,\n'
    '                target="state_lattice",\n'
    '                operations=[PatchOperation(\n'
    '                    operation="upsert_state",\n'
    '                    target_id=f"state:{atom.entity_id}:{dimension}",\n'
    '                    fields={\n'
    '                        "entity_id": atom.entity_id,\n'
    '                        "dimension": dimension,\n'
    '                        "direction": atom.direction or "set",\n'
    '                        "value": atom.value,\n'
    '                        "source_atom_ids": [atom.id],\n'
    '                        "state_scope": "",\n'
    '                        "state_group_id": atom.group_id or "",\n'
    '                        "features": dict(atom.features) if atom.features else {},\n'
    '                        "qualifiers": self._extract_qualifier_fields(graph, atom.id, "", atom.group_id or ""),\n'
    '                    },\n'
    '                    confidence=atom.confidence,\n'
    '                    reason="schema_state_delta",\n'
    '                )],\n'
    '                source_refs=self._source_refs_for_group(graph, atom.group_id or ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, atom.group_id or ""),\n'
    '                evidence_refs=[],\n'
    '                confidence=atom.confidence,\n'
    '                reason="state_delta_candidate",\n'
    '            ))'
)
new = (
    '            graph.add_structural_observation(StructuralObservation(\n'
    '                obs_type="state_delta",\n'
    '                target="state_lattice",\n'
    '                operation="upsert_state",\n'
    '                target_id=f"state:{atom.entity_id}:{dimension}",\n'
    '                fields={\n'
    '                    "entity_id": atom.entity_id,\n'
    '                    "dimension": dimension,\n'
    '                    "direction": atom.direction or "set",\n'
    '                    "value": atom.value,\n'
    '                    "source_atom_ids": [atom.id],\n'
    '                    "state_scope": "",\n'
    '                    "state_group_id": atom.group_id or "",\n'
    '                    "features": dict(atom.features) if atom.features else {},\n'
    '                    "qualifiers": self._extract_qualifier_fields(graph, atom.id, "", atom.group_id or ""),\n'
    '                },\n'
    '                confidence=atom.confidence,\n'
    '                reason="schema_state_delta",\n'
    '                source_group_id=atom.group_id or "",\n'
    '                source_refs=self._source_refs_for_group(graph, atom.group_id or ""),\n'
    '                permission_refs=self._permission_refs_for_group(graph, atom.group_id or ""),\n'
    '                evidence_refs=[],\n'
    '            ))'
)
assert old in c, 'state delta body not found'
c = c.replace(old, new)
print('State delta body replaced')

with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('Step 5: state delta OK')
