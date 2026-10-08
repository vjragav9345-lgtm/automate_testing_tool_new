"""TEST-ONLY bounded checks for the step-1 navigate host comparison (fixed generator).
 A: helper unit cases      B: www<->non-www redirecting site PASS (real network)
 C: genuinely different host FAILS and later steps cascade to NOT RUN"""
import importlib.util, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script


def build(name, start, target):
    tc = {"name": name, "start_url": start, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": target},
        {"action_type": "scroll", "value": None, "locator_profile": None, "page_url": target,
         "delta_x": 0, "delta_y": 200, "scroll_y_before": 0, "scroll_y_after": 0},
        {"action_type": "scroll", "value": None, "locator_profile": None, "page_url": target,
         "delta_x": 0, "delta_y": 200, "scroll_y_before": 0, "scroll_y_after": 0}]}
    d = Path(tempfile.mkdtemp())
    sp = generate_script(tc, out_name=f"{name}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(name + "_m", sp)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m, d


m, d = build("navhost_unit", "http://x/", "http://x/")
H = m._hosts_equivalent
for a, b, want in [("blinkit.com", "www.blinkit.com", True), ("www.blinkit.com", "blinkit.com", True),
                   ("WWW.Site.com", "site.com", True), ("a.com", "b.com", False), ("app.site.com", "site.com", False),
                   ("site.com:8080", "site.com", False), (None, "a.com", False), ("wwwx.com", "x.com", False)]:
    assert H(a, b) is want, (a, b)
print("A ok: helper unit cases")

for label, start, target, want_ok in [
        ("B www->non-www redirect", "https://www.github.com/", "https://www.github.com/", True),
        ("B2 http->https + www", "http://www.wikipedia.org/", "http://www.wikipedia.org/", True),
        ("C different host", "https://example.com/", "https://httpbin.org/redirect-to?url=https%3A%2F%2Fexample.org%2F", False)]:
    m, d = build("navhost_" + label[0] + label[1], start, target)
    res = m.run(start, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
    st = res["steps"]
    print(label, "->", [(s["success"], (s.get("error") or "")[:110], s.get("status")) for s in st])
    print("   final url:", res.get("final_url"))
    assert st[0]["success"] is want_ok, label
    if not want_ok:
        assert all(not s["success"] for s in st[1:]) and "NOT RUN" in str(st[1]), "cascade"
        assert "host mismatch" in st[0]["error"]
print("PASS")
