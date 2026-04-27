import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.importers.graph_importers import parse_graph_dict


HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parents[1]
LEGEND_FILES = {
    "simple": ROOT / "sample v3 inputs" / "legend_simple.json",
    "complex_pag": ROOT / "sample v3 inputs" / "legend_complex_pag.json",
    "tetrad_complex_pag": ROOT / "sample v3 inputs" / "legend_tetrad_complex_pag.json",
    "poster_infant_regulation": ROOT / "DS poster" / "graph_outputs" / "visualizer_graph_final_legend.json",
}


class ImportHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(200, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/legend":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        query = parse_qs(parsed.query)
        key = query.get("key", [None])[0]
        if not key or key not in LEGEND_FILES:
            self._send_json(400, {"ok": False, "error": "Unknown legend key"})
            return

        try:
            payload = json.loads(LEGEND_FILES[key].read_text(encoding="utf-8"))
            self._send_json(200, {"ok": True, "legend": payload, "key": key})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def do_POST(self):
        if self.path != "/api/import":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
            parser = payload["parser"]
            content = payload["content"]
            filename = payload.get("filename")
            normalized = parse_graph_dict(parser, content, filename=filename)
            self._send_json(200, {"ok": True, "graph": normalized})
        except Exception as exc:
            self._send_json(400, {"ok": False, "error": str(exc)})


def create_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), ImportHandler)


def server_is_reachable(host: str = HOST, port: int = PORT, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_server(host: str = HOST, port: int = PORT):
    server = create_server(host=host, port=port)
    print(f"Import server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
