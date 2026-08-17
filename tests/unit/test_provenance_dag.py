"""Тесты графа происхождения (ProvenanceGraph DAG) и циклов."""

from datetime import datetime, timezone

import pytest

from c2pax.core.exceptions import CyclicProvenanceError
from c2pax.core.provenance import (
    Action,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    Relationship,
)


def test_action_creation() -> None:
    dt = datetime(2026, 8, 17, 10, 0, tzinfo=timezone.utc)
    action = Action(name="c2pa.created", software="c2pax", timestamp=dt, parameters={"key": "val"})
    d = action.to_dict()
    assert d["name"] == "c2pa.created"
    assert d["software"] == "c2pax"
    assert d["timestamp"] == "2026-08-17T10:00:00+00:00"
    assert d["parameters"]["key"] == "val"


def test_provenance_node_and_edge() -> None:
    node = ProvenanceNode(id="node_1", title="Original RAW", format="image/tiff", hash="sha256:abc")
    edge = ProvenanceEdge(source_id="root", target_id="node_1", relationship=Relationship.PARENT_OF)
    assert node.to_dict()["title"] == "Original RAW"
    assert edge.to_dict()["relationship"] == "parentOf"


def test_provenance_graph_dag_ancestors() -> None:
    root = ProvenanceNode(
        id="root",
        title="Final Poster",
        actions=[Action(name="c2pa.edited", software="Photoshop")],
    )
    ing1 = ProvenanceNode(id="ing_1", title="Model Photo")
    ing2 = ProvenanceNode(id="ing_2", title="Background")
    raw = ProvenanceNode(id="raw_1", title="RAW Sensor Data")

    graph = ProvenanceGraph(
        root_id="root",
        _nodes={"root": root, "ing_1": ing1, "ing_2": ing2, "raw_1": raw},
        _edges=[
            ProvenanceEdge(
                source_id="root", target_id="ing_1", relationship=Relationship.COMPONENT_OF
            ),
            ProvenanceEdge(
                source_id="root", target_id="ing_2", relationship=Relationship.COMPONENT_OF
            ),
            ProvenanceEdge(
                source_id="ing_1", target_id="raw_1", relationship=Relationship.PARENT_OF
            ),
        ],
    )

    assert graph.root.title == "Final Poster"
    assert len(graph.actions) == 1

    ancestors = list(graph.ancestors())
    ancestor_ids = [n.id for n in ancestors]
    assert "ing_1" in ancestor_ids
    assert "ing_2" in ancestor_ids
    assert "raw_1" in ancestor_ids


def test_provenance_graph_cycle_detection() -> None:
    """Тест защиты от бесконечной рекурсии при наличии циклов в DAG."""
    node_a = ProvenanceNode(id="a", title="Node A")
    node_b = ProvenanceNode(id="b", title="Node B")

    graph = ProvenanceGraph(
        root_id="a",
        _nodes={"a": node_a, "b": node_b},
        _edges=[
            ProvenanceEdge(source_id="a", target_id="b", relationship=Relationship.PARENT_OF),
            ProvenanceEdge(
                source_id="b", target_id="a", relationship=Relationship.PARENT_OF
            ),  # Цикл
        ],
    )

    with pytest.raises(CyclicProvenanceError):
        list(graph.ancestors())
