"""TEST-ONLY: ISSUE 1 - the replay names what really covers the target, waits for it, and presses Escape only
when it is still there AND no menu/dropdown/popup is open."""
import importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/cover"; OUT.mkdir(parents=True, exist_ok=True)
def run(page, label, with_trigger=False, text="Buy now"):
    url = fx.url(page); d = OUT / label; d.mkdir(exist_ok=True)
    lp = {"id": "t", "tag": "button", "text": text, "element_text": text, "accessible_name": text, "attributes": {"id": "t"}, "css_path": "button#t", "xpath": "//*[@id='t']"}
    tc = {"name": label, "start_url": url, "actions": [
        {"action_type": "navigate", "page_url": url, "locator_profile": {}, "value": None},
        *([{"action_type": "click", "page_url": url, "value": None, "scroll_y": 0, "locator_profile": {"id": "trg", "tag": "a", "text": "Menu", "element_text": "Menu", "accessible_name": "Menu", "attributes": {"id": "trg", "href": "#"}, "css_path": "a#trg", "xpath": "//*[@id='trg']"}, "bounding_box": {"x": 400, "y": 150, "width": 40, "height": 20}}] if with_trigger else []),
        {"action_type": "click", "page_url": url, "value": None, "scroll_y": 0, "locator_profile": lp,
         "bounding_box": {"x": 100, "y": 20, "width": 120, "height": 40}}]}
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    return res["steps"][-1], [e["message"] for e in (res.get("live_log") or [])]
fails = []
with FixtureServer() as fx:
    s, log = run("cov_banner_timer.html", "timer"); print("timer:", s["success"], log)
    if not s["success"] or not any("banner" in l and "covering" in l for l in log) or any("Escape was pressed" in l for l in log): fails.append(("timer", log))
    if s.get("workarounds"): fails.append(("timer workaround", s["workarounds"]))
    s, log = run("cov_banner_stuck.html", "stuck"); print("stuck:", s["success"], log, s.get("workarounds"))
    if not any("Escape was pressed" in l for l in log) or not s.get("workarounds"): fails.append(("stuck", log))
    s, log = run("cov_banner_menu_open.html", "menu", with_trigger=True); print("menu:", s["success"], log)
    if any("Escape was pressed and" in l for l in log) or not any("Escape was not pressed" in l for l in log): fails.append(("menu open: Escape must not be pressed", log))
    s, log = run("cov_copy.html", "copy", text="Features"); print("copy:", s["success"], log, s.get("workarounds"), s.get("warning"))
    if not s["success"] or s.get("workarounds") or any("covering" in l or "Escape" in l for l in log): fails.append(("copy: a hidden twin must not trigger cover handling", log, s.get("warning")))
print("COVER CHECK", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
