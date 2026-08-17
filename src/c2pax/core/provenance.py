"""Модель графа происхождения (ProvenanceGraph как DAG) для c2pax."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from c2pax.core.exceptions import CyclicProvenanceError


class Relationship(str, Enum):
    """Тип семантического отношения между узлами манифестов C2PA."""

    PARENT_OF = "parentOf"
    COMPONENT_OF = "componentOf"
    INPUT_TO = "inputTo"


@dataclass(slots=True)
class Action:
    """Атомарное действие или трансформация над цифровым ассетом."""

    name: str
    software: str | None = None
    timestamp: datetime | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "software": self.software,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "parameters": self.parameters,
        }


@dataclass(slots=True)
class ProvenanceNode:
    """Узел в графе происхождения (представляет конкретный ассет или ингредиент)."""

    id: str
    title: str
    format: str | None = None
    hash: str | None = None
    actions: list[Action] = field(default_factory=list)
    thumbnail: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "format": self.format,
            "hash": self.hash,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ProvenanceEdge:
    """Ориентированное ребро графа происхождения."""

    source_id: str
    target_id: str
    relationship: Relationship | str

    def to_dict(self) -> dict[str, Any]:
        rel = (
            self.relationship.value
            if isinstance(self.relationship, Relationship)
            else self.relationship
        )
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": rel,
        }


@dataclass(slots=True)
class ProvenanceGraph:
    """Направленный ациклический граф (DAG) происхождения стандарта C2PA."""

    root_id: str
    _nodes: dict[str, ProvenanceNode] = field(default_factory=dict)
    _edges: list[ProvenanceEdge] = field(default_factory=list)

    @property
    def root(self) -> ProvenanceNode:
        """Возвращает корневой узел текущего ассета."""
        if self.root_id not in self._nodes:
            # Fallback узел, если корневой ещё не добавлен
            return ProvenanceNode(id=self.root_id, title="Root Asset")
        return self._nodes[self.root_id]

    @property
    def actions(self) -> list[Action]:
        """Возвращает список действий корневого узла."""
        return self.root.actions

    def nodes(self) -> Iterable[ProvenanceNode]:
        """Возвращает все узлы графа."""
        return self._nodes.values()

    def edges(self) -> Iterable[ProvenanceEdge]:
        """Возвращает все ребра графа."""
        return tuple(self._edges)

    def get_node(self, node_id: str) -> ProvenanceNode | None:
        """Получает узел по идентификатору."""
        return self._nodes.get(node_id)

    def add_node(self, node: ProvenanceNode) -> None:
        """Добавляет узел в граф."""
        self._nodes[node.id] = node

    def add_edge(self, edge: ProvenanceEdge) -> None:
        """Добавляет ребро в граф с валидацией."""
        self._edges.append(edge)

    def ancestors(
        self,
        node_id: str | None = None,
        visited: set[str] | None = None,
        max_depth: int = 512,
    ) -> Iterator[ProvenanceNode]:
        """Итератор по всем узлам-предкам в DAG с защитой от циклов и исчерпания ресурсов."""
        if visited is None:
            visited = set()

        target_id = node_id or self.root_id
        if target_id in visited:
            raise CyclicProvenanceError(
                f"Обнаружен циклический граф происхождения при обходе узла: {target_id}"
            )
        if len(visited) >= max_depth:
            raise CyclicProvenanceError(
                f"Превышена максимальная допустимая глубина графа ({max_depth}) при обходе узла: {target_id}"
            )
        visited.add(target_id)

        # source_id -> target_id (где target_id является родителем/ингредиентом source_id)
        parent_ids = [e.target_id for e in self._edges if e.source_id == target_id]
        for pid in parent_ids:
            if pid in self._nodes:
                yield self._nodes[pid]
                yield from self.ancestors(pid, visited=set(visited), max_depth=max_depth)

    def descendants(
        self,
        node_id: str | None = None,
        visited: set[str] | None = None,
        max_depth: int = 512,
    ) -> Iterator[ProvenanceNode]:
        """Итератор по всем узлам-потомкам в DAG с защитой от циклов и исчерпания ресурсов."""
        if visited is None:
            visited = set()

        target_id = node_id or self.root_id
        if target_id in visited:
            raise CyclicProvenanceError(
                f"Обнаружен циклический граф происхождения при обходе потомков узла: {target_id}"
            )
        if len(visited) >= max_depth:
            raise CyclicProvenanceError(
                f"Превышена максимальная допустимая глубина графа ({max_depth}) при обходе потомков узла: {target_id}"
            )
        visited.add(target_id)

        child_ids = [e.source_id for e in self._edges if e.target_id == target_id]
        for cid in child_ids:
            if cid in self._nodes:
                yield self._nodes[cid]
                yield from self.descendants(cid, visited=set(visited), max_depth=max_depth)

    def to_dict(self) -> dict[str, Any]:
        """Сериализует граф в словарь."""
        return {
            "root_id": self.root_id,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
        }
