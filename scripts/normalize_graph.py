import argparse
import json
from pathlib import Path

from src.importers.graph_importers import parse_graph_dict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parser_name")
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    content = input_path.read_text(encoding="utf-8")
    graph = parse_graph_dict(args.parser_name, content, filename=input_path.name)
    output_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Wrote normalized graph to {output_path}")


if __name__ == "__main__":
    main()
