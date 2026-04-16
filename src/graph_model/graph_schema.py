from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
from enum import Enum


# -----------------------------
# ENUMS
# -----------------------------


class GraphType(str, Enum):
    DAG = "DAG"
    CPDAG = "CPDAG"
    PAG = "PAG"
    MAG = "MAG"
    PDAG = "PDAG"


class Endpoint(str, Enum):
    TAIL = "tail"
    ARROW = "arrow"
    CIRCLE = "circle"


class NodeType(str, Enum):
    OBSERVED = "observed"
    LATENT = "latent"
    SELECTION = "selection"
    EXPOSURE = "exposure"
    OUTCOME = "outcome"
    ADJUSTED = "adjusted"
    UNKNOWN = "unknown"


# -----------------------------
# DATA STRUCTURES
# -----------------------------


@dataclass
class Layout:
    x: float
    y: float


@dataclass
class VizNode:
    color: Optional[str] = None
    size: Optional[float] = None
    shape: Optional[str] = None


@dataclass
class VizEdge:
    color: Optional[str] = None
    width: Optional[float] = None
    curveMode: Optional[str] = None
    curveDirection: Optional[str] = None
    curveStrength: Optional[float] = None
    curveBend: Optional[float] = None


@dataclass
class Node:
    id: str
    label: Optional[str] = None
    observed: bool = True
    node_type: NodeType = NodeType.OBSERVED
    group: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    viz: Optional[VizNode] = None
    layout: Optional[Layout] = None


@dataclass
class Edge:
    source: str
    target: str
    source_endpoint: Endpoint
    target_endpoint: Endpoint
    lag: int = 0
    weight: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    viz: Optional[VizEdge] = None


@dataclass
class GraphInfo:
    name: str
    graph_type: GraphType
    is_time_series: bool = False
    description: Optional[str] = None
    source_format: Optional[str] = None
    source_version: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    info: GraphInfo
    nodes: List[Node]
    edges: List[Edge]
    metadata: Dict[str, Any] = field(default_factory=dict)


# -----------------------------
# VALIDATION
# -----------------------------


def validate_graph(graph: Graph):
    node_ids = {n.id for n in graph.nodes}

    if len(node_ids) != len(graph.nodes):
        raise ValueError("Duplicate node IDs detected")

    for edge in graph.edges:
        if edge.source not in node_ids:
            raise ValueError(f"Edge source not found: {edge.source}")

        if edge.target not in node_ids:
            raise ValueError(f"Edge target not found: {edge.target}")

        if edge.source == edge.target:
            raise ValueError("Self-loops are not allowed")

        if graph.info.graph_type == GraphType.DAG:
            endpoints = {edge.source_endpoint, edge.target_endpoint}
            if endpoints != {Endpoint.TAIL, Endpoint.ARROW}:
                raise ValueError("DAG edges must be directed with one tail and one arrow")

        if graph.info.graph_type in {GraphType.CPDAG, GraphType.PDAG}:
            endpoints = {edge.source_endpoint, edge.target_endpoint}
            allowed = (
                endpoints == {Endpoint.TAIL, Endpoint.ARROW}
                or endpoints == {Endpoint.TAIL}
            )
            if not allowed:
                raise ValueError(
                    f"{graph.info.graph_type.value} does not allow circle or bidirected endpoints"
                )


# -----------------------------
# JSON SERIALIZATION
# -----------------------------


def graph_to_dict(graph: Graph) -> Dict:
    def node_to_dict(n: Node):
        return {
            "id": n.id,
            "label": n.label,
            "observed": n.observed,
            "node_type": n.node_type.value,
            "group": n.group,
            "attributes": n.attributes,
            "viz": vars(n.viz) if n.viz else None,
            "layout": vars(n.layout) if n.layout else None,
        }

    def edge_to_dict(e: Edge):
        return {
            "source": e.source,
            "target": e.target,
            "endpoints": {
                "source": e.source_endpoint.value,
                "target": e.target_endpoint.value,
            },
            "lag": e.lag,
            "weight": e.weight,
            "attributes": e.attributes,
            "viz": vars(e.viz) if e.viz else None,
        }

    return {
        "schema_version": "1.0",
        "graph": {
            "name": graph.info.name,
            "graph_type": graph.info.graph_type.value,
            "is_time_series": graph.info.is_time_series,
            "description": graph.info.description,
            "source_format": graph.info.source_format,
            "source_version": graph.info.source_version,
            "provenance": graph.info.provenance,
        },
        "nodes": [node_to_dict(n) for n in graph.nodes],
        "edges": [edge_to_dict(e) for e in graph.edges],
        "metadata": graph.metadata,
    }


def save_graph(graph: Graph, path: str):
    validate_graph(graph)
    with open(path, "w") as f:
        json.dump(graph_to_dict(graph), f, indent=2)


# -----------------------------
# JSON LOADING
# -----------------------------


def load_graph(path: str) -> Graph:
    with open(path, "r") as f:
        data = json.load(f)

    info = GraphInfo(
        name=data["graph"]["name"],
        graph_type=GraphType(data["graph"]["graph_type"]),
        is_time_series=data["graph"].get("is_time_series", False),
        description=data["graph"].get("description"),
        source_format=data["graph"].get("source_format"),
        source_version=data["graph"].get("source_version"),
        provenance=data["graph"].get("provenance", {}),
    )

    nodes = []
    for n in data["nodes"]:
        viz = None
        if n.get("viz"):
            viz = VizNode(**n["viz"])

        layout = None
        if n.get("layout"):
            layout = Layout(**n["layout"])

        nodes.append(
            Node(
                id=n["id"],
                label=n.get("label"),
                observed=n.get("observed", True),
                node_type=NodeType(
                    n.get(
                        "node_type",
                        NodeType.OBSERVED.value if n.get("observed", True) else NodeType.LATENT.value,
                    )
                ),
                group=n.get("group"),
                attributes=n.get("attributes", {}),
                viz=viz,
                layout=layout,
            )
        )

    edges = []
    for e in data["edges"]:
        viz = None
        if e.get("viz"):
            viz = VizEdge(**e["viz"])

        endpoints = e["endpoints"]

        edges.append(
            Edge(
                source=e["source"],
                target=e["target"],
                source_endpoint=Endpoint(endpoints["source"]),
                target_endpoint=Endpoint(endpoints["target"]),
                lag=e.get("lag", 0),
                weight=e.get("weight"),
                attributes=e.get("attributes", {}),
                viz=viz,
            )
        )

    graph = Graph(
        info=info, nodes=nodes, edges=edges, metadata=data.get("metadata", {})
    )

    validate_graph(graph)

    return graph
