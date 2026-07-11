import re

with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

# Add import
c = c.replace(
    'from ..types.graph_patch import GraphPatch, PatchOperation',
    'from ..learning.learning_types import StructuralObservation\nfrom ..types.graph_patch import GraphPatch, PatchOperation'
)

# Update trace
c = c.replace(
    "graph_patch_candidate_count': len(graph.patch_candidates)",
    "graph_patch_candidate_count': len(graph.structural_observations)"
)

# Verify import was added
assert 'from ..learning.learning_types import StructuralObservation' in c
assert "graph_patch_candidate_count': len(graph.structural_observations)" in c
print('Preconditions OK')

with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('Step 1 written')
