from typing import Set
from copy import deepcopy

from .graph_schema import Graph, Node, Edge, Endpoint


# -----------------------------
# BASIC EDGE HELPERS
# -----------------------------


def is_directed(edge: Edge) -> bool:
    return (
        edge.source_endpoint == Endpoint.TAIL and edge.target_endpoint == Endpoint.ARROW
    )


def is_reverse_directed(edge: Edge) -> bool:
    return (
        edge.source_endpoint == Endpoint.ARROW and edge.target_endpoint == Endpoint.TAIL
    )


def get_parents(graph: Graph, node_id: str) -> Set[str]:
    parents = set()

    for e in graph.edges:
        if is_directed(e) and e.target == node_id:
            parents.add(e.source)

        if is_reverse_directed(e) and e.source == node_id:
            parents.add(e.target)

    return parents


def get_children(graph: Graph, node_id: str) -> Set[str]:
    children = set()

    for e in graph.edges:
        if is_directed(e) and e.source == node_id:
            children.add(e.target)

        if is_reverse_directed(e) and e.target == node_id:
            children.add(e.source)

    return children


# -----------------------------
# INDUCED SUBGRAPH
# -----------------------------


def induced_subgraph(graph: Graph, node_ids: Set[str]) -> Graph:
    nodes = [deepcopy(n) for n in graph.nodes if n.id in node_ids]

    edges = [
        deepcopy(e)
        for e in graph.edges
        if e.source in node_ids and e.target in node_ids
    ]

    return Graph(
        info=graph.info,
        nodes=nodes,
        edges=edges,
        metadata=deepcopy(graph.metadata),
    )


# -----------------------------
# ANCESTORS
# -----------------------------


def ancestors(graph: Graph, node_id: str) -> Set[str]:
    visited = set()
    stack = [node_id]

    while stack:
        current = stack.pop()

        for parent in get_parents(graph, current):
            if parent not in visited:
                visited.add(parent)
                stack.append(parent)

    return visited


# -----------------------------
# DESCENDANTS
# -----------------------------


def descendants(graph: Graph, node_id: str) -> Set[str]:
    visited = set()
    stack = [node_id]

    while stack:
        current = stack.pop()

        for child in get_children(graph, current):
            if child not in visited:
                visited.add(child)
                stack.append(child)

    return visited


# -----------------------------
# MARKOV BLANKET
# -----------------------------


def markov_blanket(graph: Graph, node_id: str) -> Set[str]:
    parents = get_parents(graph, node_id)

    children = get_children(graph, node_id)

    parents_of_children = set()

    for child in children:
        parents_of_children |= get_parents(graph, child)

    blanket = parents | children | parents_of_children

    if node_id in blanket:
        blanket.remove(node_id)

    return blanket
