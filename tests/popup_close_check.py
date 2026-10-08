"""TEST-ONLY: ISSUE 2 - a close step is judged against ITS popup only.
 A popup open + X + unrelated cookie banner  -> click X, popup hidden, banner untouched, PASS
 B popup already gone, cookie banner left    -> PASS "Popup already closed" (5x identical)
 C popup open, close control not found       -> FAIL naming the container (a real failure)
 D old recording (no popup_container), banner only -> PASS "Popup already closed"
"""
import importlib.util, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/popup_close"; OUT.mkdir(parents=True, exist_ok=True)
FP = {"kind": "dialog", "tag": "div", "id": "pop", "role": "dialog", "aria_label": "Video",
      "css_path": "div#pop", "text_hint": "Video player"}

def lp(**kw):
    b = {"id": None, "tag": None, "text": "", "element_text": "", "aria_label": None, "accessible_name": "", "attributes": {}}
    b.update(kw); return b

def run(step, start, label):
    d = OUT / label; d.mkdir(parents=True, exist_ok=True)
    tc = {"name": label, "start_url": start, "actions": [
        {"action_type": "navigate", "page_url": start, "locator_profile": {}, "value": None}, dict(step, page_url=start)]}
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(start, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    s = res["steps"][1]
    notes = [e.get("message") for e in (res.get("live_log") or [])]
    return s, notes

close = {"action_type": "click", "value": None, "scroll_y": 0, "locator_profile": lp(tag="button", id="x", title="Close", accessible_name="")}
with FixtureServer() as srv:
    s, n = run(dict(close, popup_container=FP), srv.url("pop_cookie.html"), "a_open")
    assert s["success"], s.get("error"); print("A ok", s["duration"], n)
    first = None
    for i in range(5):
        s, n = run(dict(close, popup_container=FP), srv.url("pop_closed_cookie.html"), f"b_closed{i}")
        assert s["success"], s.get("error")
        assert "already closed" in (s.get("warning") or ""), (s.get("warning"), n)
        first = first or (n, s.get("error"), s.get("warning"))
        assert (n, s.get("error"), s.get("warning")) == first
        assert s["duration"] < 6, s["duration"]
        print("B", i, "ok", s["duration"])
    bad = dict(close, locator_profile=lp(tag="button", id="does-not-exist", title="Close", accessible_name=""), popup_container=FP)
    s, n = run(bad, srv.url("pop_noclose_cookie.html"), "c_stuck")
    assert not s["success"] and "pop-up" in s["error"] and "Video" in s["error"], s
    print("C ok (real failure caught):", s["error"], s["duration"])
    s, n = run(dict(close), srv.url("pop_closed_cookie.html"), "d_old")
    assert s["success"] and "already closed" in (s.get("warning") or ""), (s, n)
    print("D ok", s["duration"])
print("POPUP CLOSE CHECKS PASS")
