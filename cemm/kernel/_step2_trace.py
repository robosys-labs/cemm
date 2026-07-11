with open('cemm/kernel/meaning_graph_builder.py') as f:
    c = f.read()

c = c.replace(
    '"graph_patch_candidate_count": len(graph.patch_candidates),',
    '"graph_patch_candidate_count": len(graph.structural_observations),'
)

assert '"graph_patch_candidate_count": len(graph.structural_observations),' in c

with open('cemm/kernel/meaning_graph_builder.py', 'w') as f:
    f.write(c)
print('Step 2: trace OK')
