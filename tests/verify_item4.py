"""TEST-ONLY: VERIFY item 4. https://the-internet.herokuapp.com/dynamic_loading/1
Click Start -> Validate Visible (expect visible) on #finish -> should PASS only after the ~5s loader,
now that validate_visible polls via the shared poll_until_expected helper."""
import importlib.util, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/dynamic_loading/1"


def record():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(500)
        rec.start(launch_url=pg.url)
        pg.click("#start button")
        # a short settle so the recorder's own capture bridge flushes the
        # click event before stop() reads it out (NOT waiting for the
        # loader itself - that's exactly what validate_visible's own poll
        # must now cover)
        pg.wait_for_timeout(500)
        tc = rec.stop(name="dl1_verify4", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    finish_lp = {"id": "finish", "css_path": "#finish", "xpath": "//*[@id='finish']",
                 "text": "", "role": None, "tag": "div", "attributes": {"id": "finish"}}
    tc["actions"].append({"action_type": "validate_visible", "value": None, "locator_profile": finish_lp,
                           "bounding_box": None, "page_url": tc["actions"][-1]["page_url"], "expected_state": "visible"})
    tc["actions"].append({"action_type": "tab_close", "value": None, "locator_profile": None,
                           "bounding_box": None, "page_url": tc["actions"][-1]["page_url"]})
    return tc


def replay(tc, label):
    d = Path(f"tests/_probe_out/verify4_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"verify4_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"verify4_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t0 = time.monotonic()
    res = mod.run(URL, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    dt = time.monotonic() - t0
    print(f"\n=== {label} (total wall time {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:130])
    print("status:", res["status"], "|", res.get("message"))
    return res


if __name__ == "__main__":
    tc = record()
    replay(tc, "start_then_visible")
