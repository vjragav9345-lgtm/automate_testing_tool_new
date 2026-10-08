"""TEST-ONLY bounded check of step-1 redirect verification, on a local server (hosts 127.0.0.1 vs localhost)."""
import importlib.util, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as HTTPServer
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script

PORT = None
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        alt = f"http://localhost:{PORT}"
        if self.path == "/http302":   self.send_response(302); self.send_header("Location", alt + "/ok"); self.end_headers(); return
        if self.path == "/http302err": self.send_response(302); self.send_header("Location", alt + "/err"); self.end_headers(); return
        if self.path == "/err":       self.send_response(500); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(b"<h1>error</h1>"); return
        body = (f"<html><body>hello<script>if(location.hostname==='127.0.0.1'&&location.pathname==='/jsredirect')"
                f"location.replace('{alt}/ok')</script></body></html>").encode()
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)

srv = HTTPServer(("0.0.0.0", 0), H); PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

def run_case(label, target, want_ok, start=None):
    start = start or target
    tc = {"name": "navredir_" + label, "start_url": start, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": target},
        {"action_type": "scroll", "value": None, "locator_profile": None, "page_url": target, "delta_x": 0, "delta_y": 100, "scroll_y_before": 0, "scroll_y_after": 0},
        {"action_type": "scroll", "value": None, "locator_profile": None, "page_url": target, "delta_x": 0, "delta_y": 100, "scroll_y_before": 0, "scroll_y_after": 0}]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name=f"navredir_{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("nr_" + label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(start, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    st = res["steps"]
    print(f"{label}: step1={'PASS' if st[0]['success'] else 'FAIL'} later={[('NOT RUN' in str(s.get('error'))) for s in st[1:]]} err={str(st[0].get('error'))[:100]!r}")
    assert st[0]["success"] is want_ok, label
    if not want_ok:
        assert all("NOT RUN" in str(s.get("error")) for s in st[1:]), "cascade"
    return st

base = f"http://127.0.0.1:{PORT}"
run_case("control_http302_to_other_host_ok", base + "/http302", True)
run_case("script_redirect_other_host", base + "/jsredirect", False)
run_case("http302_to_error_page", base + "/http302err", False)
run_case("unreachable_step1_target", "http://127.0.0.1:9/", False, start=base + "/ok")
print("PASS")
