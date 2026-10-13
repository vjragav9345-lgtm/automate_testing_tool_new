"""TEST-ONLY: ISSUE 2 - a close button hidden by an idle toolbar is revealed by moving the mouse over the popup and
then CLICKED (no Escape); only a control that is not in the page at all falls back to Escape, as a WARNING."""
import importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/popup_idle"; OUT.mkdir(parents=True, exist_ok=True)
FP = {"kind": "layer", "tag": "div", "id": "pop", "role": None, "aria_label": None, "css_path": "div#pop", "text_hint": None}
close = {"action_type": "click", "value": None, "scroll_y": 0, "popup_container": FP,
         "locator_profile": {"id": "x", "tag": "button", "text": "", "title": "Close", "accessible_name": "", "attributes": {"title": "Close"}}}
def run(page, label):
    url = fx.url(page); d = OUT / label; d.mkdir(exist_ok=True)
    tc = {"name": label, "start_url": url, "actions": [{"action_type": "navigate", "page_url": url, "locator_profile": {}, "value": None}, dict(close, page_url=url)]}
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    return res["steps"][1], [e["message"] for e in (res.get("live_log") or [])]
fails = []
with FixtureServer() as fx:
    s, log = run("pop_idle.html", "idle"); print("idle:", s["success"], s.get("warning"), [l for l in log if "mouse" in l or "Escape" in l or "No close" in l])
    if not s["success"] or s.get("warning") or s.get("workarounds"): fails.append(("idle must PASS cleanly", s.get("warning"), s.get("error")))
    if not any("Moved the mouse over the popup to show the 'Close' button" in l for l in log): fails.append(("no reveal line", log))
    if any("Escape" in l or "No close button" in l for l in log): fails.append(("Escape used", log))
    s, log = run("pop_idle_noclose.html", "noclose"); print("noclose:", s["success"], s.get("warning"), [l for l in log if "Escape" in l or "No close" in l])
    if not s["success"] or "pressed Escape to close the popup. The test continued." not in (s.get("warning") or ""): fails.append(("noclose must be a WARNING", s.get("warning"), s.get("error")))
    if sum(1 for l in log if "Escape" in l) != 1: fails.append(("duplicate Escape lines", log))
print("POPUP IDLE CHECK", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
