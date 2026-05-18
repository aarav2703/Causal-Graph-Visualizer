import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
    "->": (Endpoint.TAIL, Endpoint.ARROW),
    "<--": (Endpoint.ARROW, Endpoint.TAIL),
    "<-": (Endpoint.ARROW, Endpoint.TAIL),
    "---": (Endpoint.TAIL, Endpoint.TAIL),
    "--": (Endpoint.TAIL, Endpoint.TAIL),
    "<->": (Endpoint.ARROW, Endpoint.ARROW),
    "o->": (Endpoint.CIRCLE, Endpoint.ARROW),
    "<-o": (Endpoint.ARROW, Endpoint.CIRCLE),
    "o-o": (Endpoint.CIRCLE, Endpoint.CIRCLE),
    "o--": (Endpoint.CIRCLE, Endpoint.TAIL),
    "--o": (Endpoint.TAIL, Endpoint.CIRCLE),
    "@->": (Endpoint.CIRCLE, Endpoint.ARROW),
    "<-@": (Endpoint.ARROW, Endpoint.CIRCLE),
    "@-@": (Endpoint.CIRCLE, Endpoint.CIRCLE),
    "@--": (Endpoint.CIRCLE, Endpoint.TAIL),
    "--@": (Endpoint.TAIL, Endpoint.CIRCLE),
}

OPERATOR_PATTERN = "|".join(re.escape(op) for op in sorted(EDGE_OPERATORS, key=len, reverse=True))
NODE_TOKEN_PATTERN = r'"(?:\\.|[^"])*"|[A-Za-z0-9_.:-]+'
EDGE_PATTERN = re.compile(
    rf"(?P<source>{NODE_TOKEN_PATTERN})\s*"
    rf"(?P<operator>{OPERATOR_PATTERN})\s*"
    rf"(?P<target>{NODE_TOKEN_PATTERN})"
)
ATTRIBUTE_PATTERN = re.compile(r"\[(?P<body>[^\]]+)\]\s*$")
TETRAD_PROPERTY_SEMANTICS = {
    "dd": ("directness", "definitely_direct"),
    "pd": ("directness", "possibly_direct"),
    "nl": ("latent_confounding", "no_latent_confounder"),
    "pl": ("latent_confounding", "possible_latent_confounder"),
}
GRAPHVIZ_ENDPOINTS = {
    "normal": Endpoint.ARROW,
    "none": Endpoint.TAIL,
    "odot": Endpoint.CIRCLE,
}


def normalize_parser_name(parser_name: str) -> str:
    return parser_name.strip().lower().replace("_", "-")


def add_warning(graph_or_metadata: Any, message: str):
    metadata = graph_or_metadata.metadata if isinstance(graph_or_metadata, Graph) else graph_or_metadata
    import_meta = metadata.setdefault("import", {})
    warnings = import_meta.setdefault("warnings", [])
    if message not in warnings:
        warnings.append(message)


def unquote_token(token: Any) -> Any:
    if not isinstance(token, str):
        return token
    text = token.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return bytes(text[1:-1], "utf-8").decode("unicode_escape")
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]
    return text


def _coerce_attribute_value(value: Any):
    if not isinstance(value, str):
        return value
    normalized = unquote_token(value.strip())
    if not isinstance(normalized, str):
        return normalized
    lowered = normalized.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    try:
        return int(normalized)
    except ValueError:
        pass
    try:
        return float(normalized)
    except ValueError:
        return normalized


def strip_comments_safely(content: str) -> str:
    lines = []
    for line in content.splitlines():
        quote = None
        bracket_depth = 0
        cut_at = len(line)
        i = 0
        while i < len(line):
            char = line[i]
            if quote:
                if char == quote and (i == 0 or line[i - 1] != "\\"):
                    quote = None
            elif char in {'"', "'"}:
                quote = char
            elif char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth = max(0, bracket_depth - 1)
            elif bracket_depth == 0 and char == "#":
                cut_at = i
                break
            elif bracket_depth == 0 and char == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut_at = i
                break
            i += 1
        lines.append(line[:cut_at])
    return "\n".join(lines)


def split_statements_safely(content: str) -> List[str]:
    statements = []
    current = []
    quote = None
    bracket_depth = 0
    for i, char in enumerate(content):
        if quote:
            current.append(char)
            if char == quote and (i == 0 or content[i - 1] != "\\"):
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            current.append(char)
            continue
        if char == "[":
            bracket_depth += 1
            current.append(char)
            continue
        if char == "]":
            bracket_depth = max(0, bracket_depth - 1)
            current.append(char)
            continue
        if bracket_depth == 0 and char in {";", "\n", "\r"}:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue
        current.append(char)
    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def _split_commas_safely(text: str) -> List[str]:
    parts = []
    current = []
    quote = None
    for i, char in enumerate(text):
        if quote:
            current.append(char)
            if char == quote and (i == 0 or text[i - 1] != "\\"):
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            current.append(char)
            continue
        if char == ",":
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)
    part = "".join(current).strip()
    if part:
        parts.append(part)
    return parts


def parse_attr_block(text: str) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    body = text.strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return attrs

    chunks = _split_commas_safely(body) if "," in body else [body]
    for chunk in chunks:
        part = chunk.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            attrs[key.strip()] = _coerce_attribute_value(value.strip())
            continue
        match = re.match(rf"(?P<key>[A-Za-z_][\w.-]*)\s+(?P<value>{NODE_TOKEN_PATTERN}|[^\s]+)$", part)
        if match:
            attrs[match.group("key")] = _coerce_attribute_value(match.group("value"))
            continue
        attrs[part] = True
    return attrs


def parse_gml_attrs(snippet: str) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    token_pattern = re.compile(r'"(?:\\.|[^"])*"|[^\s\]]+')
    tokens = token_pattern.findall(snippet)
    i = 0
    while i < len(tokens):
        key = unquote_token(tokens[i])
        if i + 1 < len(tokens) and not re.match(r"^[A-Za-z_][\w.-]*$", unquote_token(tokens[i + 1])):
            attrs[str(key)] = _coerce_attribute_value(tokens[i + 1])
            i += 2
        elif i + 1 < len(tokens):
            attrs[str(key)] = _coerce_attribute_value(tokens[i + 1])
            i += 2
        else:
            attrs[str(key)] = True
            i += 1
    return attrs


def _extract_bracket_body(text: str, start_index: int = 0) -> Tuple[Optional[str], int]:
    start = text.find("[", start_index)
    if start == -1:
        return None, -1
    quote = None
    depth = 0
    for i in range(start, len(text)):
        char = text[i]
        if quote:
            if char == quote and text[i - 1] != "\\":
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
    return None, -1


def map_operator_to_endpoints(operator: str) -> Tuple[Endpoint, Endpoint]:
    return EDGE_OPERATORS[operator]


def map_graphviz_arrow_attrs_to_endpoints(attrs: Dict[str, Any]) -> Tuple[Endpoint, Endpoint]:
    arrowtail = str(attrs.get("arrowtail", "none")).lower()
    arrowhead = str(attrs.get("arrowhead", "normal")).lower()
    return (
        GRAPHVIZ_ENDPOINTS.get(arrowtail, Endpoint.TAIL),
        GRAPHVIZ_ENDPOINTS.get(arrowhead, Endpoint.ARROW),
    )


def infer_graph_type_from_edges(edges: Iterable[Edge], declared: Optional[str] = None) -> GraphType:
    if declared:
        upper = declared.strip().upper()
        if upper in GraphType.__members__:
            return GraphType[upper]
        for item in GraphType:
            if item.value == upper:
                return item

    edge_list = list(edges)
    has_circle = any(
        edge.source_endpoint == Endpoint.CIRCLE or edge.target_endpoint == Endpoint.CIRCLE
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


_infer_graph_type = infer_graph_type_from_edges


def _make_nodes(
    node_ids: Iterable[str],
    node_types: Optional[Dict[str, NodeType]] = None,
    layouts: Optional[Dict[str, Tuple[float, float]]] = None,
    labels: Optional[Dict[str, str]] = None,
    attributes: Optional[Dict[str, Dict[str, Any]]] = None,
    observed: Optional[Dict[str, bool]] = None,
) -> List[Node]:
    nodes = []
    ordered = sorted(set(node_ids))
    for node_id in ordered:
        layout = None
        if layouts and node_id in layouts:
            x, y = layouts[node_id]
            layout = Layout(x=x, y=y)

        node_type = (node_types or {}).get(node_id, NodeType.OBSERVED)
        node_observed = (observed or {}).get(node_id, node_type != NodeType.LATENT)
        nodes.append(
            Node(
                id=node_id,
                label=(labels or {}).get(node_id, node_id),
                observed=node_observed,
                node_type=node_type,
                attributes=dict((attributes or {}).get(node_id, {})),
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
    node_ids: Optional[Iterable[str]] = None,
    layouts: Optional[Dict[str, Tuple[float, float]]] = None,
    labels: Optional[Dict[str, str]] = None,
    node_attributes: Optional[Dict[str, Dict[str, Any]]] = None,
    observed: Optional[Dict[str, bool]] = None,
) -> Graph:
    all_node_ids = list(node_ids or [])
    for edge in edges:
        all_node_ids.extend([edge.source, edge.target])

    nodes = _make_nodes(
        all_node_ids,
        node_types=node_types,
        layouts=layouts,
        labels=labels,
        attributes=node_attributes,
        observed=observed,
    )
    metadata = metadata or {}
    info = GraphInfo(
        name=name,
        graph_type=infer_graph_type_from_edges(edges, declared=declared_graph_type),
        source_format=source_format,
        provenance={"tool": source_format},
    )
    if not edges:
        add_warning(metadata, "No edges were parsed from the input.")
    return Graph(info=info, nodes=nodes, edges=edges, metadata=metadata)


def _extract_trailing_attributes_and_suffixes(text: str) -> Tuple[Dict[str, Any], List[str]]:
    attrs = {}
    suffix_text = text.strip()
    match = ATTRIBUTE_PATTERN.search(suffix_text)
    if match:
        attrs = parse_attr_block(match.group("body"))
        suffix_text = suffix_text[: match.start()].strip()
    suffixes = [token for token in suffix_text.split() if token]
    return attrs, suffixes


def _apply_tetrad_suffixes(edge: Edge, suffixes: List[str], metadata: Dict[str, Any]):
    if not suffixes:
        return
    edge.attributes["tetrad_properties"] = suffixes
    unknown = []
    for suffix in suffixes:
        semantic = TETRAD_PROPERTY_SEMANTICS.get(suffix)
        if semantic:
            key, value = semantic
            edge.attributes[key] = value
        else:
            unknown.append(suffix)
    if unknown:
        edge.attributes["unknown_tetrad_properties"] = unknown
        add_warning(metadata, f"Unknown Tetrad edge properties preserved: {', '.join(unknown)}")


def parse_edge_statement(statement: str, metadata: Optional[Dict[str, Any]] = None, preserve_suffixes: bool = False) -> Optional[Edge]:
    line = re.sub(r"^\s*\d+\.\s*", "", statement.strip())
    match = EDGE_PATTERN.search(line)
    if not match:
        return None
    operator = match.group("operator")
    source_endpoint, target_endpoint = map_operator_to_endpoints(operator)
    attrs, suffixes = _extract_trailing_attributes_and_suffixes(line[match.end() :])
    weight = attrs.pop("weight", None)
    edge = Edge(
        source=unquote_token(match.group("source")),
        target=unquote_token(match.group("target")),
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        weight=weight,
        attributes=attrs,
    )
    edge.attributes["raw_statement"] = statement.strip()
    edge.attributes["source_operator"] = operator
    if preserve_suffixes and metadata is not None:
        _apply_tetrad_suffixes(edge, suffixes, metadata)
    elif suffixes:
        edge.attributes["raw_suffixes"] = suffixes
    return edge


def _parse_graph_node_attributes(line: str) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if ":" not in line:
        return result
    attr_name, rest = line.split(":", 1)
    attr_name = attr_name.strip().lower().replace(" ", "_")
    body_match = re.search(r"\[(.*)\]", rest)
    if not body_match:
        return result
    for chunk in body_match.group(1).split(";"):
        if ":" not in chunk:
            continue
        node_id, value = chunk.split(":", 1)
        node_id = node_id.strip()
        result.setdefault(node_id, {})[f"tetrad_{attr_name}"] = _coerce_attribute_value(value.strip())
    return result


def _parse_edge_list_text(content: str, source_format: str, graph_type: Optional[str] = None, preserve_tetrad_metadata: bool = False) -> Graph:
    lines = [line.strip() for line in strip_comments_safely(content).splitlines() if line.strip()]
    edges: List[Edge] = []
    nodes: List[str] = []
    metadata: Dict[str, Any] = {"source_metadata": {source_format: {}}}
    graph_attrs: Dict[str, Any] = {}
    node_attrs: Dict[str, Dict[str, Any]] = {}
    section = None

    for line in lines:
        lower = line.lower()
        if lower.startswith("graph nodes"):
            section = "nodes"
            _, raw_nodes = line.split(":", 1)
            nodes.extend([token.strip() for token in re.split(r"[;,]", raw_nodes) if token.strip()])
            continue
        if lower.startswith("graph edges"):
            section = "edges"
            continue
        if lower.startswith("graph attributes"):
            section = "graph_attributes"
            continue
        if lower.startswith("graph node attributes"):
            section = "graph_node_attributes"
            continue

        if section == "graph_attributes" and ":" in line:
            key, value = line.split(":", 1)
            graph_attrs[key.strip()] = _coerce_attribute_value(value.strip())
            continue
        if section == "graph_node_attributes":
            for node_id, attrs in _parse_graph_node_attributes(line).items():
                node_attrs.setdefault(node_id, {}).update(attrs)
            continue

        edge = parse_edge_statement(line, metadata=metadata, preserve_suffixes=preserve_tetrad_metadata)
        if edge:
            edges.append(edge)

    if graph_attrs:
        metadata["source_metadata"][source_format]["graph_attributes"] = graph_attrs
    if node_attrs:
        metadata["source_metadata"][source_format]["graph_node_attributes"] = node_attrs

    graph = _build_graph(
        name=f"{source_format} import",
        edges=edges,
        source_format=source_format,
        declared_graph_type=graph_type,
        metadata=metadata,
        node_ids=nodes,
        node_attributes=node_attrs,
    )
    return graph


def _layout_from_positions(raw_positions: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
    if not raw_positions:
        return {}
    xs = [pos[0] for pos in raw_positions.values()]
    ys = [pos[1] for pos in raw_positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    return {
        node_id: (0.08 + 0.84 * ((x - min_x) / span_x), 0.08 + 0.84 * ((y - min_y) / span_y))
        for node_id, (x, y) in raw_positions.items()
    }


def _node_type_from_attrs(attrs: Dict[str, Any]) -> Tuple[NodeType, bool]:
    lowered = {str(key).lower(): value for key, value in attrs.items()}
    truthy = {key for key, value in lowered.items() if value not in {False, "0", 0, None}}
    if {"latent", "unobserved"} & truthy:
        return NodeType.LATENT, False
    if "selection" in truthy:
        return NodeType.SELECTION, True
    if "exposure" in truthy:
        return NodeType.EXPOSURE, True
    if "outcome" in truthy:
        return NodeType.OUTCOME, True
    if "adjusted" in truthy:
        return NodeType.ADJUSTED, True
    if str(lowered.get("observed", "")).lower() == "no":
        return NodeType.LATENT, False
    return NodeType.OBSERVED, True


def _parse_dagitty(content: str) -> Graph:
    text = strip_comments_safely(content.strip())
    header = re.search(r"^\s*(dag|pdag|pag|mag)\s*\{", text, flags=re.IGNORECASE)
    declared = header.group(1).upper() if header else None
    body_match = re.search(r"\{(.*)\}", text, flags=re.DOTALL)
    body = body_match.group(1) if body_match else text

    metadata: Dict[str, Any] = {"source_metadata": {"dagitty": {"declared_graph_type": declared}}}
    edges: List[Edge] = []
    node_ids: List[str] = []
    node_types: Dict[str, NodeType] = {}
    node_attrs: Dict[str, Dict[str, Any]] = {}
    observed: Dict[str, bool] = {}
    raw_positions: Dict[str, Tuple[float, float]] = {}

    for statement in split_statements_safely(body):
        line = statement.strip()
        if not line or line.startswith("Variables:") or line.startswith("Exposures:") or line.startswith("Outcomes:"):
            continue

        edge = parse_edge_statement(line, metadata=metadata)
        if edge:
            edges.append(edge)
            continue

        attr_match = re.match(rf"(?P<node>{NODE_TOKEN_PATTERN})\s*\[(?P<attrs>.*)\]$", line)
        if attr_match:
            node_id = unquote_token(attr_match.group("node"))
            attrs = parse_attr_block(attr_match.group("attrs"))
            node_ids.append(node_id)
            node_attrs.setdefault(node_id, {}).update(attrs)
            node_type, is_observed = _node_type_from_attrs(attrs)
            node_types[node_id] = node_type
            observed[node_id] = is_observed
            if "pos" in attrs:
                raw = str(attrs["pos"])
                node_attrs[node_id]["dagitty_pos_raw"] = raw
                try:
                    x, y = [float(part.strip()) for part in raw.split(",", 1)]
                    raw_positions[node_id] = (x, y)
                except Exception:
                    add_warning(metadata, f"Could not parse Dagitty position for node {node_id}: {raw}")
            continue

        bare_node = re.match(rf"^(?P<node>{NODE_TOKEN_PATTERN})$", line)
        if bare_node:
            node_ids.append(unquote_token(bare_node.group("node")))
            continue

        add_warning(metadata, f"Skipped unrecognized Dagitty statement: {line}")

    return _build_graph(
        name="dagitty import",
        edges=edges,
        source_format="dagitty",
        declared_graph_type=declared,
        node_types=node_types,
        metadata=metadata,
        node_ids=node_ids,
        layouts=_layout_from_positions(raw_positions),
        node_attributes=node_attrs,
        observed=observed,
    )


def _parse_dot_attrs(attr_text: Optional[str]) -> Dict[str, Any]:
    return parse_attr_block(attr_text or "")


def _extract_dot_body(content: str) -> str:
    match = re.search(r"\{(.*)\}", content, flags=re.DOTALL)
    return match.group(1) if match else content


def _parse_dot(content: str, source_format: str, use_labels_as_ids: bool = False) -> Graph:
    body = _extract_dot_body(strip_comments_safely(content))
    declared = (
        "DAG"
        if source_format != "causal-learn" and re.search(r"\bdigraph\b", content, flags=re.IGNORECASE)
        else None
    )
    metadata: Dict[str, Any] = {"source_metadata": {source_format: {"subformat": "dot"}}}
    dot_nodes: Dict[str, Dict[str, Any]] = {}
    edge_rows: List[Tuple[str, str, str, Dict[str, Any], str]] = []
    graph_attrs: Dict[str, Any] = {}

    for statement in split_statements_safely(body):
        line = statement.strip().strip(",")
        if not line:
            continue

        edge_match = re.match(
            rf"^(?P<source>{NODE_TOKEN_PATTERN})\s*(?P<operator>->|--)\s*(?P<target>{NODE_TOKEN_PATTERN})(?:\s*\[(?P<attrs>.*)\])?$",
            line,
        )
        if edge_match:
            edge_rows.append(
                (
                    unquote_token(edge_match.group("source")),
                    edge_match.group("operator"),
                    unquote_token(edge_match.group("target")),
                    _parse_dot_attrs(edge_match.group("attrs")),
                    line,
                )
            )
            continue

        node_match = re.match(rf"^(?P<node>{NODE_TOKEN_PATTERN})\s*\[(?P<attrs>.*)\]$", line)
        if node_match:
            raw_id = unquote_token(node_match.group("node"))
            dot_nodes[raw_id] = _parse_dot_attrs(node_match.group("attrs"))
            continue

        graph_attr_match = re.match(r"^(?P<key>[A-Za-z_][\w.-]*)\s*=\s*(?P<value>.+)$", line)
        if graph_attr_match:
            graph_attrs[graph_attr_match.group("key")] = _coerce_attribute_value(graph_attr_match.group("value"))
            continue

        add_warning(metadata, f"Skipped unrecognized DOT statement: {line}")

    id_map: Dict[str, str] = {}
    labels: Dict[str, str] = {}
    node_attrs: Dict[str, Dict[str, Any]] = {}
    node_types: Dict[str, NodeType] = {}
    observed: Dict[str, bool] = {}
    for raw_id, attrs in dot_nodes.items():
        label = str(attrs.get("label", raw_id))
        node_id = label if use_labels_as_ids and label else raw_id
        id_map[raw_id] = node_id
        labels[node_id] = label
        preserved = dict(attrs)
        preserved["raw_dot_id"] = raw_id
        node_attrs[node_id] = preserved
        node_type, is_observed = _node_type_from_attrs(attrs)
        role = str(attrs.get("role", "")).lower()
        if role == "treatment":
            node_type = NodeType.EXPOSURE
        elif role == "outcome":
            node_type = NodeType.OUTCOME
        node_types[node_id] = node_type
        observed[node_id] = is_observed

    edges: List[Edge] = []
    for raw_source, operator, raw_target, attrs, raw_line in edge_rows:
        source = id_map.get(raw_source, raw_source)
        target = id_map.get(raw_target, raw_target)
        if "arrowhead" in attrs or "arrowtail" in attrs:
            source_endpoint, target_endpoint = map_graphviz_arrow_attrs_to_endpoints(attrs)
        elif operator == "--":
            source_endpoint, target_endpoint = Endpoint.TAIL, Endpoint.TAIL
        else:
            source_endpoint, target_endpoint = Endpoint.TAIL, Endpoint.ARROW
        edge_attrs = {key: value for key, value in attrs.items() if key != "weight"}
        if attrs:
            edge_attrs["graphviz"] = dict(attrs)
        edge_attrs["raw_statement"] = raw_line
        edge_attrs["source_operator"] = operator
        edges.append(
            Edge(
                source=source,
                target=target,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                weight=attrs.get("weight"),
                attributes=edge_attrs,
            )
        )

    if graph_attrs:
        metadata["source_metadata"][source_format]["graph_attributes"] = graph_attrs

    return _build_graph(
        name=f"{source_format} dot import",
        edges=edges,
        source_format=source_format,
        declared_graph_type=declared,
        metadata=metadata,
        node_ids=id_map.values(),
        labels=labels,
        node_attributes=node_attrs,
        node_types=node_types,
        observed=observed,
    )


def _parse_gml(content: str) -> Graph:
    directed = re.search(r"\bdirected\s+1\b", content)
    metadata: Dict[str, Any] = {"source_metadata": {"dowhy": {"subformat": "gml"}}}
    labels: Dict[str, str] = {}
    node_attrs: Dict[str, Dict[str, Any]] = {}
    node_types: Dict[str, NodeType] = {}
    observed: Dict[str, bool] = {}
    node_ids: List[str] = []

    for block in re.finditer(r"node\s*\[(.*?)\]", content, flags=re.DOTALL):
        attrs = parse_gml_attrs(block.group(1))
        node_id = str(attrs.get("id", "")).strip()
        if not node_id:
            add_warning(metadata, f"Skipped GML node without id: {block.group(0).strip()}")
            continue
        node_ids.append(node_id)
        labels[node_id] = str(attrs.get("label", node_id))
        node_attrs[node_id] = dict(attrs)
        node_type, is_observed = _node_type_from_attrs(attrs)
        role = str(attrs.get("role", "")).lower()
        if role == "treatment":
            node_type = NodeType.EXPOSURE
        elif role == "outcome":
            node_type = NodeType.OUTCOME
        node_types[node_id] = node_type
        observed[node_id] = is_observed

    edges: List[Edge] = []
    for block in re.finditer(r"edge\s*\[(.*?)\]", content, flags=re.DOTALL):
        attrs = parse_gml_attrs(block.group(1))
        source = attrs.get("source")
        target = attrs.get("target")
        if not source or not target:
            add_warning(metadata, f"Skipped GML edge without source/target: {block.group(0).strip()}")
            continue
        source_endpoint, target_endpoint = (Endpoint.TAIL, Endpoint.ARROW) if directed else (Endpoint.TAIL, Endpoint.TAIL)
        edge_attrs = {key: value for key, value in attrs.items() if key not in {"source", "target", "weight"}}
        edge_attrs["raw_statement"] = block.group(0).strip()
        edge_attrs["source_operator"] = "gml-directed" if directed else "gml-undirected"
        edges.append(
            Edge(
                source=str(source),
                target=str(target),
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                weight=attrs.get("weight"),
                attributes=edge_attrs,
            )
        )

    return _build_graph(
        name="dowhy gml import",
        edges=edges,
        source_format="dowhy",
        declared_graph_type="DAG" if directed else "CPDAG",
        metadata=metadata,
        node_ids=node_ids,
        labels=labels,
        node_attributes=node_attrs,
        node_types=node_types,
        observed=observed,
    )


def _parse_causal_learn_edge_dump(content: str) -> Optional[Graph]:
    if "EDGE " not in content or "endpoint1:" not in content:
        return None
    metadata: Dict[str, Any] = {"source_metadata": {"causal-learn": {"subformat": "fci_edge_dump"}}}
    edges: List[Edge] = []
    blocks = re.split(r"(?=^EDGE\s+\d+)", content, flags=re.MULTILINE)
    for block in blocks:
        if not block.strip().startswith("EDGE"):
            continue
        str_match = re.search(r"^str:\s*(.+)$", block, flags=re.MULTILINE)
        if not str_match:
            add_warning(metadata, f"Skipped causal-learn edge block without str line: {block.strip()[:80]}")
            continue
        edge = parse_edge_statement(str_match.group(1), metadata=metadata)
        if not edge:
            add_warning(metadata, f"Could not parse causal-learn edge str: {str_match.group(1)}")
            continue
        edge.attributes["raw_block"] = block.strip()
        prop_match = re.search(r"^properties:\s*\[(.*)\]$", block, flags=re.MULTILINE)
        if prop_match:
            properties = re.findall(r"Property\.([A-Za-z_]+)", prop_match.group(1))
            if properties:
                edge.attributes["properties"] = properties
                _apply_tetrad_suffixes(edge, properties, metadata)
        for key in ["endpoint1", "endpoint2", "numerical_endpoint_1", "numerical_endpoint_2", "node1", "node2"]:
            match = re.search(rf"^{key}:\s*(.+)$", block, flags=re.MULTILINE)
            if match:
                edge.attributes[key] = _coerce_attribute_value(match.group(1).strip())
        edges.append(edge)
    return _build_graph(
        name="causal-learn fci edge dump import",
        edges=edges,
        source_format="causal-learn",
        metadata=metadata,
    )


def _parse_json_graph(content: str, source_format: str) -> Graph:
    data = json.loads(content)

    if {"graph", "nodes", "edges"}.issubset(data.keys()):
        return _parse_canonical_json_data(data)

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
        node_attrs = {}
        labels = {}
        for node in data["nodes"]:
            labels[node["id"]] = node.get("label", node["id"])
            node_attrs[node["id"]] = {key: value for key, value in node.items() if key not in {"id", "label", "latent"}}
            if node.get("latent"):
                node_types[node["id"]] = NodeType.LATENT

        return _build_graph(
            name=f"{source_format} json import",
            edges=edges,
            source_format=source_format,
            node_types=node_types,
            node_ids=[node["id"] for node in data["nodes"]],
            labels=labels,
            node_attributes=node_attrs,
        )

    raise ValueError("Unsupported JSON graph structure")


def _filter_viz(cls, viz_data: Optional[Dict[str, Any]], attrs: Dict[str, Any]):
    if not viz_data:
        return None
    allowed = set(getattr(cls, "__dataclass_fields__", {}).keys())
    known = {key: value for key, value in viz_data.items() if key in allowed}
    extra = {key: value for key, value in viz_data.items() if key not in allowed}
    if extra:
        attrs["_extra_viz"] = extra
    return cls(**known)


def _parse_canonical_json_data(data: Dict[str, Any]) -> Graph:
    info = data["graph"]
    nodes = []
    for node in data["nodes"]:
        attrs = dict(node.get("attributes", {}))
        nodes.append(
            Node(
                id=node["id"],
                label=node.get("label"),
                observed=node.get("observed", True),
                node_type=NodeType(node.get("node_type", "observed")),
                group=node.get("group"),
                attributes=attrs,
                viz=_filter_viz(VizNode, node.get("viz"), attrs),
                layout=Layout(**node["layout"]) if node.get("layout") else None,
            )
        )
    edges = []
    for edge in data["edges"]:
        attrs = dict(edge.get("attributes", {}))
        edges.append(
            Edge(
                source=edge["source"],
                target=edge["target"],
                source_endpoint=Endpoint(edge["endpoints"]["source"]),
                target_endpoint=Endpoint(edge["endpoints"]["target"]),
                lag=edge.get("lag", 0),
                weight=edge.get("weight"),
                attributes=attrs,
                viz=_filter_viz(VizEdge, edge.get("viz"), attrs),
            )
        )
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


def parse_graph_content(parser_name: str, content: str, filename: Optional[str] = None) -> Graph:
    parser = normalize_parser_name(parser_name)
    text = content.strip()

    if parser == "tetrad":
        return _parse_edge_list_text(text, source_format="tetrad", preserve_tetrad_metadata=True)

    if parser == "causal-learn":
        edge_dump = _parse_causal_learn_edge_dump(text)
        if edge_dump:
            return edge_dump
        if re.search(r"\bdigraph\b", text, flags=re.IGNORECASE):
            return _parse_dot(text, source_format="causal-learn", use_labels_as_ids=True)
        graph = _parse_edge_list_text(text, source_format="causal-learn", preserve_tetrad_metadata=True)
        if not graph.nodes and not graph.edges:
            add_warning(graph, f"Unsupported or empty causal-learn output: {filename or 'input'}")
        return graph

    if parser == "dagitty":
        return _parse_dagitty(text)

    if parser == "dowhy":
        if text.startswith("{"):
            return _parse_json_graph(text, source_format="dowhy")
        if "graph [" in text.lower():
            return _parse_gml(text)
        return _parse_dot(text, source_format="dowhy", use_labels_as_ids=False)

    if parser == "canonical-json":
        return _parse_canonical_json_data(json.loads(text))

    raise ValueError(f"Unsupported parser: {parser_name}")


def parse_graph_dict(parser_name: str, content: str, filename: Optional[str] = None) -> Dict:
    return graph_to_dict(parse_graph_content(parser_name, content, filename=filename))
