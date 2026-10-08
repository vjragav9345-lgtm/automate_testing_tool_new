"""TEST-ONLY: full repro-case verification for Task's Bug1+Bug2.
1) Records the exact flow (Navigate, Click Enable, Click input, Fill hello, Click Disable, Close Tab) via the REAL
   recorder against the real site, using realistic (fast, replay-like) timing so step 3's click on the input lands
   WHILE it is still disabled - the exact race from the bug report.
2) Appends a hand-added Validate Element State (Disabled) step on the input (mirrors "Pick Element then add
   validate", without needing the interactive picker).
3) Replays the whole 7-step recording with the FIXED generator and reports every step's outcome + timing.
"""
import json, sys, time
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
    t0 = time.monotonic()
    pg.click("#input-example button")              # Enable
    pg.click("#input-example input", timeout=200, force=True)   # click the input INSTANTLY (still disabled) - reproduces the race, recorder just captures the click target
    print(f"[repro] clicked input at t={time.monotonic()-t0:.2f}s after Enable (still disabled: {pg.locator('#input-example input').is_disabled()})")
    pg.wait_for_timeout(3200)   # let the real 3s toggle actually finish before continuing the recording
    pg.locator("#input-example input").fill("hello")
    pg.click("#input-example button")              # Disable
    pg.wait_for_timeout(3300)  # let the SECOND toggle (back to disabled) actually finish
    print("[repro] input disabled after Disable+wait?", pg.locator("#input-example input").is_disabled())
    tc = rec.stop(name="dc_full_repro", stop_reason="terminal_enter")
    drafts = (rec._draft_path, rec._draft_jsonl_path)
    b.close()
for d in drafts:
    if d: Path(d).unlink(missing_ok=True)

# hand-add a Validate Element State (Disabled) step, mirroring what the editor's
# Add Action / Pick Element flow would produce, and a tab_close to finish the 7 steps
input_lp = None
for a in tc["actions"]:
    if a["action_type"] == "click" and (a.get("locator_profile") or {}).get("tag") == "input":
        input_lp = a["locator_profile"]
if input_lp is None:
    for a in tc["actions"]:
        if a["action_type"] == "fill":
            input_lp = a["locator_profile"]
assert input_lp, "couldn't find the input's own locator_profile in the recording"
tc["actions"].append({
    "action_type": "validate_element", "value": None, "locator_profile": input_lp,
    "bounding_box": None, "page_url": tc["actions"][-1]["page_url"], "expected_state": "disabled",
    "delay_before_ms": 3800,
})
tc["actions"].append({"action_type": "tab_close", "value": None, "locator_profile": None,
                       "bounding_box": None, "page_url": tc["actions"][-1]["page_url"]})

print("\n=== recorded/edited steps ===")
for i, a in enumerate(tc["actions"], 1):
    print(i, a["action_type"], json.dumps(a.get("locator_profile", {}).get("xpath") if a.get("locator_profile") else None, ensure_ascii=False), a.get("value"), a.get("expected_state"))

scratch = Path("tests/_probe_out/dc_full_repro")
scratch.mkdir(parents=True, exist_ok=True)
sp = generate_script(tc, out_name="dc_full_repro_script.py", output_dir=scratch)
import importlib.util
spec = importlib.util.spec_from_file_location("dc_full_repro_mod", sp)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
res = mod.run(URL, output_json_path=scratch / "report.json", screenshot_dir=scratch / "shots", headless=True)
print("\n=== REPLAY RESULT ===")
print("status:", res["status"], "|", res.get("message"))
for s in res["steps"]:
    print(s.get("step") if s.get("step") is not None else "?", s.get("action_type"), "PASS" if s.get("success") else "FAIL", (s.get("error") or "")[:200])
