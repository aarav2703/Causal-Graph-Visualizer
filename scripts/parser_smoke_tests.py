from pathlib import Path
import sys

from src.importers.graph_importers import parse_graph_dict


ROOT = Path(__file__).resolve().parents[1]


CASES = [
    ("tetrad", "parser_test_outputs/tetrad/graph1-tetrad.txt", 7, 10, "CPDAG"),
    ("tetrad", "parser_test_outputs/tetrad/graph2-tetrad.txt", 7, 10, "PAG"),
    ("tetrad", "parser_test_outputs/tetrad/graph3-tetrad.txt", 7, 9, "PAG"),
    ("tetrad", "parser_test_outputs/tetrad/tetrad_04_comprehensive_mixed_edges.txt", 18, 9, "PAG"),
    ("causal-learn", "parser_test_outputs/causal_learn/causal_learn_01_pc_raw.dot", 7, 10, "CPDAG"),
    ("causal-learn", "parser_test_outputs/causal_learn/causal_learn_02_fci_raw.dot", 7, 10, "PAG"),
    ("causal-learn", "parser_test_outputs/causal_learn/causal_learn_03_ges_raw.dot", 7, 10, "CPDAG"),
    ("causal-learn", "parser_test_outputs/causal_learn/causal_learn_02_fci_raw_edges_raw_dump.txt", 7, 10, "PAG"),
    ("causal-learn", "parser_test_outputs/causal_learn/causal_learn_04_comprehensive_pydot.dot", 18, 9, "PAG"),
    ("causal-learn", "parser_test_outputs/causal_learn/causal_learn_05_comprehensive_fci_edge_dump.txt", 6, 3, "PAG"),
    ("dagitty", "parser_test_outputs/dagitty/dagitty_01_dag_raw_as_character.txt", 7, 8, "DAG"),
    ("dagitty", "parser_test_outputs/dagitty/dagitty_02_mag_raw_as_character.txt", 8, 6, "MAG"),
    ("dagitty", "parser_test_outputs/dagitty/dagitty_03_pag_raw_as_character.txt", 7, 6, "PAG"),
    ("dagitty", "parser_test_outputs/dagitty/dagitty_04_comprehensive_pag_as_character.txt", 18, 9, "PAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_01_simple_dag_raw.dot", 5, 5, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_02_metadata_dag_raw.dot", 6, 6, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_03_latent_dag_raw.dot", 6, 6, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_01_simple_dag_raw.gml", 5, 5, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_02_metadata_dag_raw.gml", 6, 6, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_03_latent_dag_raw.gml", 6, 6, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_04_comprehensive_metadata_raw.dot", 6, 7, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_04_comprehensive_metadata_raw.gml", 6, 7, "DAG"),
    ("dowhy", "parser_test_outputs/dowhy/dowhy_05_undirected_dot_regression.dot", 2, 1, "CPDAG"),
    ("causal-learn", "sample v3 inputs/causal_learn_complex_pag.txt", 10, 15, "PAG"),
    ("tetrad", "sample v3 inputs/tetrad_complex_pag.txt", 10, 15, "PAG"),
    ("dagitty", "sample v3 inputs/dagitty_sample.txt", 5, 4, "DAG"),
    ("dowhy", "sample v3 inputs/dowhy_sample.dot", 5, 4, "DAG"),
    ("causal-learn", "DS poster/graph_outputs/visualizer_graph_final.txt", 10, 12, "PAG"),
    ("causal-learn", "DS poster/graph_outputs/visualizer_input_graph.txt", 9, 12, "PAG"),
    ("causal-learn", "DS poster/graph_outputs/causal_learn_pc_edges.txt", 9, 12, "PAG"),
    ("tetrad", "DS poster/graph_outputs/graph1.txt", 19, 26, "PAG"),
]


def endpoint_counts(graph):
    counts = {}
    for edge in graph["edges"]:
        key = f"{edge['endpoints']['source']}:{edge['endpoints']['target']}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def has_endpoint(graph, source_endpoint, target_endpoint):
    return any(
        edge["endpoints"]["source"] == source_endpoint
        and edge["endpoints"]["target"] == target_endpoint
        for edge in graph["edges"]
    )


def has_edge_metadata(graph, key, value=None):
    for edge in graph["edges"]:
        if key == "weight":
            current = edge.get("weight")
        else:
            current = edge["attributes"].get(key)
        if value is None and current is not None:
            return True
        if current == value:
            return True
    return False


def extra_checks(path, graph):
    checks = []
    path_text = str(path).replace("\\", "/")

    if path_text.endswith("graph3-tetrad.txt"):
        source_meta = graph["metadata"].get("source_metadata", {}).get("tetrad", {})
        checks.append(("tetrad graph score", "Score" in source_meta.get("graph_attributes", {})))
        checks.append(("tetrad node score", any("tetrad_score" in node["attributes"] for node in graph["nodes"])))

    if "tetrad_04_comprehensive_mixed_edges" in path_text:
        for endpoints in [
            ("tail", "arrow"),
            ("arrow", "tail"),
            ("tail", "tail"),
            ("arrow", "arrow"),
            ("circle", "arrow"),
            ("arrow", "circle"),
            ("circle", "circle"),
            ("circle", "tail"),
            ("tail", "circle"),
        ]:
            checks.append((f"tetrad endpoint {endpoints[0]}:{endpoints[1]}", has_endpoint(graph, *endpoints)))
        checks.append(("tetrad weight", has_edge_metadata(graph, "weight", 0.42)))
        checks.append(("tetrad beta", has_edge_metadata(graph, "beta", -0.37)))
        checks.append(("tetrad confidence", has_edge_metadata(graph, "confidence", 0.91)))
        checks.append(("tetrad unknown suffix", any(edge["attributes"].get("unknown_tetrad_properties") for edge in graph["edges"])))

    if "causal_learn_02_fci_raw.dot" in path_text:
        counts = endpoint_counts(graph)
        checks.append(("causal-learn circle endpoints", counts.get("circle:arrow", 0) > 0 and counts.get("circle:circle", 0) > 0))
        checks.append(("causal-learn labels as ids", any(node["id"] == "Infant_Age" for node in graph["nodes"])))

    if "causal_learn_02_fci_raw_edges_raw_dump" in path_text:
        checks.append(("fci properties", any(edge["attributes"].get("properties") for edge in graph["edges"])))

    if "causal_learn_04_comprehensive_pydot" in path_text:
        for endpoints in [
            ("tail", "arrow"),
            ("arrow", "tail"),
            ("tail", "tail"),
            ("arrow", "arrow"),
            ("circle", "arrow"),
            ("arrow", "circle"),
            ("circle", "circle"),
            ("circle", "tail"),
            ("tail", "circle"),
        ]:
            checks.append((f"causal-learn dot endpoint {endpoints[0]}:{endpoints[1]}", has_endpoint(graph, *endpoints)))
        checks.append(("causal-learn labels as ids comprehensive", any(node["id"] == "Infant_Age" for node in graph["nodes"])))
        checks.append(("causal-learn graphviz attrs", any(edge["attributes"].get("graphviz") for edge in graph["edges"])))
        checks.append(("causal-learn dot beta", has_edge_metadata(graph, "beta", -0.37)))
        checks.append(("causal-learn dot confidence", has_edge_metadata(graph, "confidence", 0.91)))

    if "causal_learn_05_comprehensive_fci_edge_dump" in path_text:
        checks.append(("causal-learn fci properties comprehensive", any(edge["attributes"].get("properties") for edge in graph["edges"])))
        checks.append(("causal-learn fci raw block", all(edge["attributes"].get("raw_block") for edge in graph["edges"])))

    if "dagitty_03_pag_raw_as_character" in path_text:
        checks.append(("dagitty @ endpoints", endpoint_counts(graph).get("circle:circle", 0) > 0))
        checks.append(("dagitty layout", all(node.get("layout") for node in graph["nodes"])))

    if "dagitty_04_comprehensive_pag_as_character" in path_text:
        for endpoints in [
            ("tail", "arrow"),
            ("arrow", "tail"),
            ("tail", "tail"),
            ("arrow", "arrow"),
            ("circle", "arrow"),
            ("arrow", "circle"),
            ("circle", "circle"),
            ("circle", "tail"),
            ("tail", "circle"),
        ]:
            checks.append((f"dagitty endpoint {endpoints[0]}:{endpoints[1]}", has_endpoint(graph, *endpoints)))
        checks.append(("dagitty roles", {"exposure", "outcome", "adjusted", "selection", "latent"}.issubset({node["node_type"] for node in graph["nodes"]})))
        checks.append(("dagitty layout comprehensive", all(node.get("layout") for node in graph["nodes"])))
        checks.append(("dagitty beta", has_edge_metadata(graph, "beta", -0.37)))
        checks.append(("dagitty confidence", has_edge_metadata(graph, "confidence", 0.91)))

    if "dowhy_02_metadata_dag_raw" in path_text:
        checks.append(("dowhy weights", any(edge.get("weight") is not None for edge in graph["edges"])))
        checks.append(("dowhy roles", any(node["attributes"].get("role") for node in graph["nodes"])))

    if "dowhy_03_latent_dag_raw" in path_text:
        checks.append(("dowhy latent", any(node["node_type"] == "latent" and node["observed"] is False for node in graph["nodes"])))

    if "dowhy_04_comprehensive_metadata_raw" in path_text:
        checks.append(("dowhy comprehensive weights", has_edge_metadata(graph, "weight", 0.42)))
        checks.append(("dowhy comprehensive beta", has_edge_metadata(graph, "beta", -0.37)))
        checks.append(("dowhy comprehensive confidence", has_edge_metadata(graph, "confidence", 0.91)))
        checks.append(("dowhy comprehensive roles", any(node["attributes"].get("role") == "treatment" for node in graph["nodes"])))
        checks.append(("dowhy comprehensive latent", any(node["node_type"] == "latent" and node["observed"] is False for node in graph["nodes"])))

    if "dowhy_05_undirected_dot_regression" in path_text:
        checks.append(("dowhy undirected dot endpoint", has_endpoint(graph, "tail", "tail")))
        checks.append(("dowhy undirected source operator", any(edge["attributes"].get("source_operator") == "--" for edge in graph["edges"])))

    return checks


def run_case(parser, relative_path, expected_nodes, expected_edges, expected_type):
    path = ROOT / relative_path
    graph = parse_graph_dict(parser, path.read_text(encoding="utf-8"), filename=path.name)
    failures = []
    if len(graph["nodes"]) != expected_nodes:
        failures.append(f"nodes {len(graph['nodes'])} != {expected_nodes}")
    if len(graph["edges"]) != expected_edges:
        failures.append(f"edges {len(graph['edges'])} != {expected_edges}")
    if graph["graph"]["graph_type"] != expected_type:
        failures.append(f"type {graph['graph']['graph_type']} != {expected_type}")
    for label, passed in extra_checks(path, graph):
        if not passed:
            failures.append(label)
    return graph, failures


def main():
    failures = 0
    print("status\tparser\tfile\tnodes\tedges\ttype\tdetails")
    for parser, relative_path, expected_nodes, expected_edges, expected_type in CASES:
        try:
            graph, case_failures = run_case(parser, relative_path, expected_nodes, expected_edges, expected_type)
            status = "PASS" if not case_failures else "FAIL"
            if case_failures:
                failures += 1
            print(
                f"{status}\t{parser}\t{relative_path}\t"
                f"{len(graph['nodes'])}\t{len(graph['edges'])}\t{graph['graph']['graph_type']}\t"
                f"{'; '.join(case_failures) if case_failures else '-'}"
            )
        except Exception as exc:
            failures += 1
            print(f"FAIL\t{parser}\t{relative_path}\t-\t-\t-\t{type(exc).__name__}: {exc}")
    print(f"\nResult: {'PASS' if failures == 0 else 'FAIL'} ({len(CASES) - failures}/{len(CASES)} passing)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
