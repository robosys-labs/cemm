"""Proof artifacts: proof nodes and proof graphs for derived answers.

This module owns :class:`ProofNode` and :class:`ProofGraph`.  A proof graph is
a DAG of proof nodes where each node records its conclusion, source facts (for
leaf nodes), the rule applied (for derived nodes), and premise node refs.

Proof graphs are frozen, hashable, and carry the semantic refs, source program
refs, rule applications, and transient existential witness refs touched during
derivation.  Existential witnesses remain proof-local: they are never committed
to the world store.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ProofNode",
    "ProofGraph",
]


@dataclass(frozen=True)
class ProofNode:
    """A single node in a proof graph.

    Attributes:
        conclusion_ref: the semantic ref concluded by this node (e.g. a
            fact ref for leaf nodes or a derived conclusion ref).
        source_fact_refs: tuple of fact refs that directly support this node
            (empty for derived nodes whose support comes from premises).
        rule_ref: the rule ref applied to derive this node, or None for leaf
            nodes supported directly by source facts.
        premise_node_refs: tuple of proof node refs that are premises of this
            node (empty for leaf nodes).
    """

    conclusion_ref: str
    source_fact_refs: tuple[str, ...]
    rule_ref: str | None
    premise_node_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProofGraph:
    """A proof graph for a derived answer.

    Attributes:
        root_node_ref: the ref of the root proof node (the final conclusion).
        nodes: tuple of all :class:`ProofNode` instances in the graph.
        semantic_refs: all semantic refs touched during the proof (atoms,
            relations, states, concepts appearing in facts or rules).
        source_refs: source program refs that contributed to the proof.
        rule_applications: tuple of rule refs applied during the proof.
        transient_witness_refs: existential witness refs created during the
            proof (proof-local, never committed to the world store).
    """

    root_node_ref: str
    nodes: tuple[ProofNode, ...]
    semantic_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    rule_applications: tuple[str, ...]
    transient_witness_refs: tuple[str, ...]
