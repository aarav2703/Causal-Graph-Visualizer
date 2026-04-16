import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


ROOT = app_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.import_graph_server import HOST, PORT, create_server, server_is_reachable


VIEWER_PATH = ROOT / "Causal viewer_v3" / "index.html"


def wait_for_server(host: str, port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server_is_reachable(host, port):
            return True
        time.sleep(0.1)
    return False


def open_viewer(viewer_path: Path):
    webbrowser.open(viewer_path.resolve().as_uri(), new=1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the causal graph viewer and local import service."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the import service without opening the viewer in a browser.",
    )
    parser.add_argument("--host", default=HOST, help="Host for the local import service.")
    parser.add_argument("--port", type=int, default=PORT, help="Port for the local import service.")
    args = parser.parse_args()

    if not VIEWER_PATH.exists():
        print(f"Viewer file not found: {VIEWER_PATH}")
        return 1

    os.environ.setdefault("PYTHONPATH", str(ROOT))

    if server_is_reachable(args.host, args.port):
        print(f"Import server already running at http://{args.host}:{args.port}")
        if not args.no_browser:
            open_viewer(VIEWER_PATH)
        print("Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nLauncher stopped.")
        return 0

    server = create_server(host=args.host, port=args.port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if not wait_for_server(args.host, args.port):
        print(f"Failed to start import server on http://{args.host}:{args.port}")
        server.shutdown()
        server.server_close()
        return 1

    print(f"Import server listening on http://{args.host}:{args.port}")
    if not args.no_browser:
        open_viewer(VIEWER_PATH)
        print("Viewer opened in your default browser.")
    else:
        print("Browser launch skipped.")

    print("Press Ctrl+C to stop the app.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.shutdown()
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
