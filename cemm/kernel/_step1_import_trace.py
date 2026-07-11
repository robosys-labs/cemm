with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

c = c.replace(
    'from ..types.graph_patch import GraphPatch, PatchOperation',
    'from ..learning.learning_types import StructuralObservation\nfrom ..types.graph_patch import GraphPatch, PatchOperation'
)

c = c.replace(
    "graph_patch_candidate_count': len(graph.patch_candidates)",
    "graph_patch_candidate_count': len(graph.structural_observations)"
)

assert 'from ..learning.learning_types import StructuralObservation' in c
assert "graph_patch_candidate_count': len(graph.structural_observations)" in c

with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('Step 1: import + trace OK')
