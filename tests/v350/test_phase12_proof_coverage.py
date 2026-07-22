from cemm.v350.csir.model import (
    CSIRGraph, Coordination, ExactAuthorityPin, ScopeEmbedding, SemanticApplication, SemanticTerm, TermKind,
)
from cemm.v350.realization.proof_v351 import required_semantic_coverage


def pin(ref):
    return ExactAuthorityPin("test", "test", ref, 1, "sha:" + ref, "global")


def test_csir_scope_and_coordination_are_mandatory_realization_coverage():
    a = SemanticTerm("a", TermKind.REFERENT, identity_ref="r:a")
    b = SemanticTerm("b", TermKind.REFERENT, identity_ref="r:b")
    app = SemanticApplication("scope-op", pin("operator"))
    coord = Coordination("coord", pin("and"), (a.node_ref, b.node_ref))
    emb = ScopeEmbedding("scope-1", app.node_ref, coord.node_ref, pin("scope-kind"))
    graph = CSIRGraph(
        terms=(a, b), applications=(app,), coordinations=(coord,), scope_embeddings=(emb,),
        root_refs=(app.node_ref, coord.node_ref),
    )
    coverage = set(required_semantic_coverage(graph))
    assert "scope-1" in coverage
    assert "coord" in coverage
    assert "scope-op" in coverage
