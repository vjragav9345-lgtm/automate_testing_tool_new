"""Tiny local static file server for the Phase 4 offline bug-repro
fixtures (tests/fixtures/phase4_*.html) - lets the real Recorder/replay
code run against pages that behave exactly like the reported live-site
bugs, without depending on Myntra/Sportzia actually being reachable.

    from phase4_fixture_server import FixtureServer
    with FixtureServer() as srv:
        url = srv.url("phase4_hover_menu.html")
"""
import http.server
import socketserver
import threading
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FIXTURES_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass


class FixtureServer:
    def __init__(self, port=0):
        self._httpd = socketserver.TCPServer(("127.0.0.1", port), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def port(self):
        return self._httpd.server_address[1]

    def url(self, path=""):
        return f"http://127.0.0.1:{self.port}/{path}"
