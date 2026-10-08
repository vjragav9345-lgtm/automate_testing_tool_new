"""TEST-ONLY, bounded verification for Bug 1: records a clean (correctly-paced) flow on the real dynamic_controls
site, then forces the 'click input' step's own delay_before_ms to 0 (the exact fast-replay race from the bug
report: replay attempts the click immediately after Enable, before the real ~3s toggle finishes) and replays that
with (a) the ORIGINAL (pre-fix, .bak) generator - expected to FAIL with the reported symptom, and (b) the FIXED
generator - expected to PASS, waiting for the element to become enabled."""
import importlib.machinery, importlib.util, json, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder

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
    pg.wait_for_timeout(3300)                        # real toggle finishes - clean, correctly-paced recording
    pg.locator("#input-example input").click()
    pg.locator("#input-example input").fill("hello")
    pg.click("#input-example button")                # Disable
    pg.wait_for_timeout(3300)
    tc = rec.stop(name="dc_bug1_verify", stop_reason="terminal_enter")
    drafts = (rec._draft_path, rec._draft_jsonl_path)
    b.close()
for d in drafts:
    if d: Path(d).unlink(missing_ok=True)

print("=== clean recording ===")
for i, a in enumerate(tc["actions"], 1):
    print(i, a["action_type"], a.get("delay_before_ms"), (a.get("locator_profile") or {}).get("tag"))

# force the race: the click-on-input step gets delay_before_ms=0, so replay attempts it
# IMMEDIATELY after the Enable click, before the real ~3s toggle can finish
for a in tc["actions"]:
    if a["action_type"] == "click" and (a.get("locator_profile") or {}).get("tag") == "input":
        a["delay_before_ms"] = 0

def load(path, name):
    l = importlib.machinery.SourceFileLoader(name, str(path)); s = importlib.util.spec_from_loader(name, l)
    m = importlib.util.module_from_spec(s); l.exec_module(m); return m

def run_with(generator_path, label):
    m = load(generator_path, "gen_" + label)
    scratch = Path(f"tests/_probe_out/dc_bug1_{label}")
    scratch.mkdir(parents=True, exist_ok=True)
    sp = m.generate_script(tc, out_name=f"dc_bug1_{label}_script.py", output_dir=scratch)
    spec = importlib.util.spec_from_file_location(f"dc_bug1_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    t0 = time.monotonic()
    res = mod.run(URL, output_json_path=scratch / "report.json", screenshot_dir=scratch / "shots", headless=True)
    dt = time.monotonic() - t0
    print(f"\n=== {label} generator (total {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s.get("step"), s.get("action_type"), "PASS" if s.get("success") else "FAIL", (s.get("error") or "")[:220])
    return res

bk = Path(open(BASE / "tests/_probe_out/waitfix_backup_dir.txt").read().strip())
run_with(bk / "generator" / "script_generator.py", "original")
run_with(BASE / "generator" / "script_generator.py", "fixed")
