"""Tests for 3.3 Obligation Graph (Phase 9)."""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.types.obligation_graph import (
    ObligationGraph, ObligationNode, ObligationNodeKind, ObligationEdge
)
from cemm.kernel.obligation_graph_builder import ObligationGraphBuilder


class TestObligationGraph:
    def test_add_node(self):
        graph = ObligationGraph()
        node = ObligationNode(node_id="n1", kind=ObligationNodeKind.QUERY)
        graph.add_node(node)
        assert graph.get_node("n1") is not None

    def test_execution_order_with_deps(self):
        graph = ObligationGraph()
        n1 = ObligationNode(node_id="write", kind=ObligationNodeKind.WRITE)
        n2 = ObligationNode(node_id="query", kind=ObligationNodeKind.QUERY, depends_on=("write",))
        graph.add_node(n1)
        graph.add_node(n2)
        order = graph.execution_order()
        assert order == ["write", "query"]

    def test_learning_question_detection(self):
        graph = ObligationGraph()
        lq_node = ObligationNode(node_id="lq", kind=ObligationNodeKind.LEARNING_QUESTION)
        graph.add_node(lq_node)
        assert graph.has_learning_question()

    def test_blocked_node_not_executable(self):
        graph = ObligationGraph()
        n1 = ObligationNode(node_id="write", kind=ObligationNodeKind.WRITE, blocked_by=("safety",))
        n2 = ObligationNode(node_id="safety", kind=ObligationNodeKind.SAFETY)
        graph.add_node(n1)
        graph.add_node(n2)
        assert not n1.can_execute(set())
        assert n2.can_execute(set())

    def test_execution_order_with_blocked_node(self):
        graph = ObligationGraph()
        n1 = ObligationNode(node_id="blocked", kind=ObligationNodeKind.WRITE, blocked_by=("safety",))
        n2 = ObligationNode(node_id="safety", kind=ObligationNodeKind.SAFETY, depends_on=())
        graph.add_node(n1)
        graph.add_node(n2)
        order = graph.execution_order()
        assert "blocked" not in order

    def test_nodes_by_kind(self):
        graph = ObligationGraph()
        graph.add_node(ObligationNode(node_id="q1", kind=ObligationNodeKind.QUERY))
        graph.add_node(ObligationNode(node_id="q2", kind=ObligationNodeKind.QUERY))
        graph.add_node(ObligationNode(node_id="w1", kind=ObligationNodeKind.WRITE))
        assert len(graph.nodes_by_kind(ObligationNodeKind.QUERY)) == 2

    def test_clear(self):
        graph = ObligationGraph()
        graph.add_node(ObligationNode(node_id="n1", kind=ObligationNodeKind.QUERY))
        graph.clear()
        assert len(graph.all_nodes()) == 0
