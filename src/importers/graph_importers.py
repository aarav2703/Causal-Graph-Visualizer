import json
import re
from typing import Dict, Iterable, List, Optional, Tuple

from src.graph_model.graph_schema import (
    Edge,
    Endpoint,
    Graph,
    GraphInfo,
    GraphType,
    Layout,
    Node,
    NodeType,
    VizEdge,
    VizNode,
    graph_to_dict,
)


EDGE_OPERATORS = {
    "-->": (Endpoint.TAIL, Endpoint.ARROW),
    "<--": (Endpoint.ARROW, Endpoint.TAIL),
    "---": (Endpoint.TAIL, Endpoint.TAIL),
    "<->": (Endpoint.ARROW, Endpoint.ARROW),
    "o->": (Endpoint.CIRCLE, Endpoint.ARROW),
    "<-o": (Endpoint.ARROW, Endpoint.CIRCLE),
    "o-o": (Endpoint.CIRCLE, Endpoint.CIRCLE),
    "o--": (Endpoint.CIRCLE, Endpoint.TAIL),
    "--o": (Endpoint.TAIL, Endpoint.CIRCLE),
    "->": (Endpoint.TAIL, Endpoint.ARROW),
    "<-": (Endpoint.ARROW, Endpoint.TAIL),
    "--": (Endpoint.TAIL, Endpoint.TAIL),
}

EDGE_PATTERN = re.compile(
    r"(?P<source>[A-Za-z0-9_.:-]+)\s*"
    r"(?P<operator><->|---|-->|<--|o->|<-o|o-o|o--|--o|->|<-|--)\s*"
    r"(?P<target>[A-Za-z0-9_.:-]+)"
)

ATTRIBUTE_PATTERN = re.compile(r"\[(?P<body>[^\]]+)\]\s*$")


def _infer_graph_type(edges: Iterable[Edge], declared: Optional[str] = None) -> GraphType:
    if declared:
        upper = declared.strip().upper()
        if upper in GraphType.__members__:
            return GraphType[upper]
        for item in GraphType:
            if item.value == upper:
                return item

    edge_list = list(edges)
    has_circle = any(
        edge.source_endpoint == Endpoint.CIRCLE
        or edge.target_endpoint == Endpoint.CIRCLE
        for edge in edge_list
    )
    has_bidirected = any(
        edge.source_endpoint == Endpoint.ARROW and edge.target_endpoint == Endpoint.ARROW
        for edge in edge_list
    )
    has_undirected = any(
        edge.source_endpoint == Endpoint.TAIL and edge.target_endpoint == Endpoint.TAIL
        for edge in edge_list
    )

    if has_circle:
        return GraphType.PAG
    if has_bidirected:
        return GraphType.MAG
    if has_undirected:
        return GraphType.CPDAG
    return GraphType.DAG


def _make_nodes(
    node_ids: Iterable[str],
    node_types: Optional[Dict[str, NodeType]] = None,
    layouts: Optional[Dict[str, Tuple[float, float]]] = None,
) -> List[Node]:
    nodes = []
    ordered = sorted(set(node_ids))
    for node_id in ordered:
        layout = None
        if layouts and node_id in layouts:
            x, y = layouts[node_id]
            layout = Layout(x=x, y=y)

        node_type = (node_types or {}).get(node_id, NodeType.OBSERVED)
        nodes.append(
            Node(
                id=node_id,
                label=node_id,
                observed=node_type != NodeType.LATENT,
                node_type=node_type,
                layout=layout,
            )
        )
    return nodes


def _build_graph(
    name: str,
    edges: List[Edge],
    source_format: str,
    declared_graph_type: Optional[str] = None,
    node_types: Optional[Dict[str, NodeType]] = None,
    metadata: Optional[Dict] = None,
) -> Graph:
    node_ids = []
    for edge in edges:
        node_ids.extend([edge.source, edge.target])

    nodes = _make_nodes(node_ids, node_types=node_types)
    info = GraphInfo(
        name=name,
        graph_type=_infer_graph_type(edges, declared=declared_graph_type),
        source_format=source_format,
        provenance={"tool": source_format},
    )
    return Graph(info=info, nodes=nodes, edges=edges, metadata=metadata or {})


def _edge_from_match(match: re.Match, attributes: Optional[Dict] = None) -> Edge:
    operator = match.group("operator")
    source_endpoint, target_endpoint = EDGE_OPERATORS[operator]
    edge_attributes = dict(attributes or {})
    weight = edge_attributes.pop("weight", None)
    return Edge(
        source=match.group("source"),
        target=match.group("target"),
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        weight=weight,
        attributes=edge_attributes,
    )


def _coerce_attribute_value(value: str):
    normalized = value.strip().strip('"').strip("'")
    lowered = normalized.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(normalized)
    except ValueError:
        pass
    try:
        return float(normalized)
    except ValueError:
        return normalized


def _parse_trailing_attributes(text: str) -> Dict:
    match = ATTRIBUTE_PATTERN.search(text)
    if not match:
        return {}

    attributes: Dict = {}
    for chunk in match.group("body").split(","):
        part = chunk.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        attributes[key.strip()] = _coerce_attribute_value(value)
    return attributes


def _parse_edge_list_text(content: str, source_format: str, graph_type: Optional[str] = None) -> Graph:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    edges: List[Edge] = []
    nodes: List[str] = []

    for line in lines:
        if line.lower().startswith("graph nodes"):
            _, raw_nodes = line.split(":", 1)
            nodes = [token.strip() for token in re.split(r"[;,]", raw_nodes) if token.strip()]
            continue

        line = re.sub(r"^\d+\.\s*", "", line)
        match = EDGE_PATTERN.search(line)
        if match:
            attributes = _parse_trailing_attributes(line[match.end():])
            edges.append(_edge_from_match(match, attributes=attributes))

    graph = _build_graph(
        name=f"{source_format} import",
        edges=edges,
        source_format=source_format,
        declared_graph_type=graph_type,
    )

    if nodes:
        existing = {node.id for node in graph.nodes}
        graph.nodes.extend(_make_nodes([node for node in nodes if node not in existing]))

    return graph


def _parse_dagitty(content: str) -> Graph:
    header = re.search(r"^\s*(dag|pdag|pag|mag)\s*\{", content, flags=re.IGNORECASE)
    declared = header.group(1).upper() if header else None
    body_match = re.search(r"\{(.*)\}", content, flags=re.DOTALL)
    body = body_match.group(1) if body_match else content

    edges: List[Edge] = []
    node_types: Dict[str, NodeType] = {}
    declared_nodes: List[str] = []

    for statement in body.split(";"):
        line = statement.strip()
        if not line:
            continue

        edge_match = EDGE_PATTERN.search(line)
        if edge_match:
            attributes = _parse_trailing_attributes(line[edge_match.end():])
            edges.append(_edge_from_match(edge_match, attributes=attributes))
            continue

        attr_match = re.match(r"(?P<node>[A-Za-z0-9_.:-]+)\s*\[(?P<attrs>[^\]]+)\]", line)
        if attr_match:
            node_id = attr_match.group("node")
            declared_nodes.append(node_id)
            attrs = attr_match.group("attrs").lower()
            if "latent" in attrs:
                node_types[node_id] = NodeType.LATENT
            elif "selection" in attrs:
                node_types[node_id] = NodeType.SELECTION
            elif "exposure" in attrs:
                node_types[node_id] = NodeType.EXPOSURE
            elif "outcome" in attrs:
                node_types[node_id] = NodeType.OUTCOME
            elif "adjusted" in attrs:
                node_types[node_id] = NodeType.ADJUSTED
            continue

        bare_node = re.match(r"^[A-Za-z0-9_.:-]+$", line)
        if bare_node:
            declared_nodes.append(line)

    graph = _build_graph(
        name="dagitty import",
        edges=edges,
        source_format="dagitty",
        declared_graph_type=declared,
        node_types=node_types,
    )
    if declared_nodes:
        existing = {node.id for node in graph.nodes}
        graph.nodes.extend(
            _make_nodes(
                [node for node in declared_nodes if node not in existing],
                node_types=node_types,
            )
        )
    return graph


def _parse_dot(content: str, source_format: str) -> Graph:
    declared = "DAG" if re.search(r"\bdigraph\b", content, flags=re.IGNORECASE) else None
    edges: List[Edge] = []
    node_types: Dict[str, NodeType] = {}
    node_ids: List[str] = []

    for statement in content.split(";"):
        line = statement.strip()
        if not line or line in {"{", "}"}:
            continue

        edge_match = EDGE_PATTERN.search(line)
        if edge_match:
            edges.append(_edge_from_match(edge_match))
            continue

        node_match = re.match(r'(?P<node>"?[\w.:-]+"?)\s*\[(?P<attrs>[^\]]+)\]', line)
        if node_match:
            node_id = node_match.group("node").strip('"')
            node_ids.append(node_id)
            attrs = node_match.group("attrs").lower()
            if "observed=\"no\"" in attrs or "latent=true" in attrs or "unobserved" in attrs:
                node_types[node_id] = NodeType.LATENT

    graph = _build_graph(
        name=f"{source_format} dot import",
        edges=edges,
        source_format=source_format,
        declared_graph_type=declared,
        node_types=node_types,
    )
    if node_ids:
        existing = {node.id for node in graph.nodes}
        graph.nodes.extend(
            _make_nodes(
                [node for node in node_ids if node not in existing],
                node_types=node_types,
            )
        )
    return graph


def _parse_gml(content: str) -> Graph:
    directed = re.search(r"\bdirected\s+1\b", content)
    node_map: Dict[str, str] = {}
    node_types: Dict[str, NodeType] = {}

    for block in re.finditer(r"node\s*\[(.*?)\]", content, flags=re.DOTALL):
        snippet = block.group(1)
        node_id = _extract_gml_value(snippet, "id")
        label = _extract_gml_value(snippet, "label") or node_id
        if node_id:
            node_map[node_id] = label
            if "unobserved" in snippet.lower():
                node_types[label] = NodeType.LATENT

    edges: List[Edge] = []
    for block in re.finditer(r"edge\s*\[(.*?)\]", content, flags=re.DOTALL):
        snippet = block.group(1)
        source_id = _extract_gml_value(snippet, "source")
        target_id = _extract_gml_value(snippet, "target")
        if not source_id or not target_id:
            continue
        source = node_map.get(source_id, source_id)
        target = node_map.get(target_id, target_id)
        if directed:
            source_endpoint, target_endpoint = Endpoint.TAIL, Endpoint.ARROW
        else:
            source_endpoint, target_endpoint = Endpoint.TAIL, Endpoint.TAIL
        edges.append(
            Edge(
                source=source,
                target=target,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
            )
        )

    return _build_graph(
        name="dowhy gml import",
        edges=edges,
        source_format="dowhy",
        declared_graph_type="DAG" if directed else "CPDAG",
        node_types=node_types,
    )


def _extract_gml_value(snippet: str, key: str) -> Optional[str]:
    match = re.search(rf"\b{key}\s+\"?([^\s\"\]]+)\"?", snippet)
    return match.group(1) if match else None


def _parse_json_graph(content: str, source_format: str) -> Graph:
    data = json.loads(content)

    if {"graph", "nodes", "edges"}.issubset(data.keys()):
        from src.graph_model.graph_schema import load_graph  # local import to avoid cycle

        temp_path = None
        raise ValueError(
            "Canonical JSON should be loaded from disk with the existing loader; use parse_graph_content for raw tool outputs."
        )

    if "nodes" in data and "links" in data:
        edges = []
        for edge in data["links"]:
            source = edge["source"]
            target = edge["target"]
            operator = edge.get("type", "->")
            if operator not in EDGE_OPERATORS:
                operator = "->"
            source_endpoint, target_endpoint = EDGE_OPERATORS[operator]
            attributes = {
                key: value
                for key, value in edge.items()
                if key not in {"source", "target", "type", "weight"}
            }
            edges.append(
                Edge(
                    source=source,
                    target=target,
                    source_endpoint=source_endpoint,
                    target_endpoint=target_endpoint,
                    attributes=attributes,
                    weight=edge.get("weight"),
                )
            )

        node_types = {}
        for node in data["nodes"]:
            if node.get("latent"):
                node_types[node["id"]] = NodeType.LATENT

        graph = _build_graph(
            name=f"{source_format} json import",
            edges=edges,
            source_format=source_format,
            node_types=node_types,
        )
        existing = {node.id for node in graph.nodes}
        graph.nodes.extend(
            _make_nodes(
                [node["id"] for node in data["nodes"] if node["id"] not in existing],
                node_types=node_types,
            )
        )
        return graph

    raise ValueError("Unsupported JSON graph structure")


def parse_graph_content(parser_name: str, content: str, filename: Optional[str] = None) -> Graph:
    parser = parser_name.strip().lower()
    text = content.strip()

    if parser == "tetrad":
        return _parse_edge_list_text(text, source_format="tetrad")

    if parser == "causal-learn":
        return _parse_edge_list_text(text, source_format="causal-learn")

    if parser == "dagitty":
        return _parse_dagitty(text)

    if parser == "dowhy":
        if text.startswith("{"):
            return _parse_json_graph(text, source_format="dowhy")
        if "graph [" in text.lower():
            return _parse_gml(text)
        return _parse_dot(text, source_format="dowhy")

    if parser == "canonical-json":
        data = json.loads(text)
        info = data["graph"]
        nodes = [
            Node(
                id=node["id"],
                label=node.get("label"),
                observed=node.get("observed", True),
                node_type=NodeType(node.get("node_type", "observed")),
                group=node.get("group"),
                attributes=node.get("attributes", {}),
                viz=VizNode(**node["viz"]) if node.get("viz") else None,
                layout=Layout(**node["layout"]) if node.get("layout") else None,
            )
            for node in data["nodes"]
        ]
        edges = [
            Edge(
                source=edge["source"],
                target=edge["target"],
                source_endpoint=Endpoint(edge["endpoints"]["source"]),
                target_endpoint=Endpoint(edge["endpoints"]["target"]),
                lag=edge.get("lag", 0),
                weight=edge.get("weight"),
                attributes=edge.get("attributes", {}),
                viz=VizEdge(**edge["viz"]) if edge.get("viz") else None,
            )
            for edge in data["edges"]
        ]
        return Graph(
            info=GraphInfo(
                name=info["name"],
                graph_type=GraphType(info["graph_type"]),
                is_time_series=info.get("is_time_series", False),
                description=info.get("description"),
                source_format=info.get("source_format"),
                source_version=info.get("source_version"),
                provenance=info.get("provenance", {}),
            ),
            nodes=nodes,
            edges=edges,
            metadata=data.get("metadata", {}),
        )

    raise ValueError(f"Unsupported parser: {parser_name}")


def parse_graph_dict(parser_name: str, content: str, filename: Optional[str] = None) -> Dict:
    return graph_to_dict(parse_graph_content(parser_name, content, filename=filename))
