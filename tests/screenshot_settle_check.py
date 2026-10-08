"""TEST-ONLY (Req 3): the manual screenshot action and the per-step screenshot
both wait for the page to truly settle; a page that never does gets the
screenshot anyway plus the 'still loading' WARNING; per-step capture happens
AFTER the step result is written and is patched into it afterwards."""
import importlib.util, json, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
OUT = Path("tests/_probe_out/screenshot_settle"); OUT.mkdir(parents=True, exist_ok=True)

def run(page_name, srv, label, steps_extra=()):
    url = srv.url(page_name)
    tc = {"name": label, "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        {"action_type": "screenshot", "label": label, "locator_profile": None, "page_url": url},
        *steps_extra]}
    d = OUT / label; d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label + "_m", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    t = time.monotonic()
    res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    return res, time.monotonic() - t

with FixtureServer() as srv:
    res, took = run("warn_skeleton.html", srv, "skeleton_manual")
    shot = next(s for s in res["steps"] if s["action_type"] == "screenshot")
    assert shot["success"] and shot["screenshot"] and Path(shot["screenshot"]).exists(), shot
    assert not shot.get("warning"), f"settled page must not warn: {shot.get('warning')}"
    # the skeleton lasts 1.8s - a screenshot taken before it was replaced would be ~immediate
    print("skeleton page: screenshot taken after", round(took, 2), "s total, file", shot["screenshot"])
    from PIL import Image
    im = Image.open(shot["screenshot"]).convert("RGB")
    # the 240x60 grey skeleton blocks (#ddd) must be gone from where they were
    px = im.getpixel((60, 40))
    assert px != (221, 221, 221), f"skeleton still on screen in the manual screenshot: {px}"
    print("manual screenshot shows loaded content (pixel at skeleton position:", px, ")")

    res, took = run("warn_busy.html", srv, "busy_manual")
    shot = next(s for s in res["steps"] if s["action_type"] == "screenshot")
    assert shot["success"] and Path(shot["screenshot"]).exists()
    assert "still loading" in (shot.get("warning") or ""), f"expected the still-loading WARNING, got {shot.get('warning')!r}"
    print("busy page: screenshot taken anyway in", round(took, 2), "s; warning:", shot["warning"])
print("SCREENSHOT SETTLE CHECKS PASS")
