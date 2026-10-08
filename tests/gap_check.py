"""TEST-ONLY (I4): gaps between steps and per-step timing on non-navigating steps, from the run's own timestamps."""
import importlib.util, json, sys
from datetime import datetime
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
d = Path("tests/_probe_out/gap"); d.mkdir(parents=True, exist_ok=True)
def lp(i, t): return {"id": "#" + i, "tag": "button", "text": t, "element_text": t, "attributes": {}}
with FixtureServer() as srv:
    u = srv.url("gap_page.html")
    acts = [{"action_type": "navigate", "page_url": u, "locator_profile": {}, "value": None}]
    for i, t in (("b1", "One"), ("b2", "Two"), ("b3", "Three"), ("b4", "Four")):
        acts.append({"action_type": "click", "page_url": u, "value": None, "locator_profile": lp(i, t)})
    acts.append({"action_type": "fill", "page_url": u, "value": "Ada", "locator_profile": {"id": "#t", "tag": "input", "aria_label": "Name", "text": "", "element_text": "", "attributes": {}}})
    acts.append({"action_type": "scroll", "page_url": u, "value": None, "locator_profile": None, "delta_x": 0, "delta_y": 300, "scroll_y_before": 0, "scroll_y_after": 300})
    sp = generate_script({"name": "gap", "start_url": u, "actions": acts}, out_name="gap.py", output_dir=d)
    spec = importlib.util.spec_from_file_location("gap", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(u, output_json_path=d / "r.json", screenshot_dir=d / "s", headless=True)
steps = res["steps"]
f = lambda s: datetime.fromisoformat(s)
worst = 0
for a, b in zip(steps, steps[1:]):
    gap = (f(b["started_at"]) - f(a["ended_at"])).total_seconds() * 1000
    worst = max(worst, gap)
    print(f"step {a['index']}->{b['index']} gap {gap:.0f}ms | step {a['index']} {a['action_type']} {a['duration']}s timing={a.get('timing_ms')}")
assert all(s["success"] for s in steps)
assert worst < 500, f"gap {worst}ms"
print(f"GAP CHECK PASS (worst gap {worst:.0f}ms)")
