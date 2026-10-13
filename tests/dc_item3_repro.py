"""TEST-ONLY: reproduce the exact Dynamic Controls repro (Navigate, Click Enable, Click input, Fill hello,
Click Disable, Validate Element State expect Disabled, Close Tab) BEFORE any validator changes, to check
the CLI summary's Failed count against the per-step results."""
import json, sys, tempfile
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/dynamic_controls"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    rec = Recorder(pg)
    rec.install_context_capture(ctx)
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(800)
    rec.start(launch_url=pg.url)
    pg.click("#input-example button")               # Enable
    pg.wait_for_timeout(3300)
    pg.locator("#input-example input").click()
    pg.locator("#input-example input").fill("hello")
    pg.click("#input-example button")                # Disable
    pg.wait_for_timeout(300)                          # deliberately NOT waiting the full 3s - reproduces the race
    tc = rec.stop(name="dc_item3_repro", stop_reason="terminal_enter")
    drafts = (rec._draft_path, rec._draft_jsonl_path)
    b.close()
for d in drafts:
    if d: Path(d).unlink(missing_ok=True)

input_lp = None
for a in tc["actions"]:
    if a["action_type"] == "click" and (a.get("locator_profile") or {}).get("tag") == "input":
        input_lp = a["locator_profile"]
assert input_lp
tc["actions"].append({"action_type": "validate_element", "value": None, "locator_profile": input_lp,
                       "bounding_box": None, "page_url": tc["actions"][-1]["page_url"], "check": "disabled"})
tc["actions"].append({"action_type": "tab_close", "value": None, "locator_profile": None,
                       "bounding_box": None, "page_url": tc["actions"][-1]["page_url"]})

print("=== steps ===")
for i, a in enumerate(tc["actions"], 1):
    print(i, a["action_type"])

d = Path("tests/_probe_out/dc_item3_repro")
d.mkdir(parents=True, exist_ok=True)
sp = generate_script(tc, out_name="dc_item3_repro_script.py", output_dir=d)
import importlib.util
spec = importlib.util.spec_from_file_location("dc_item3_repro_mod", sp)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
res = mod.run(URL, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
print("\n=== per-step results ===")
for s in res["steps"]:
    print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:100])
print("\nreport status:", res["status"], "|", res.get("message"))
