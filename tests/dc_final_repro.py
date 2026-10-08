"""TEST-ONLY: FINAL bounded verification for this task's items 1-2. Records the exact 7-step Dynamic Controls
repro (Navigate, Click Enable, Click input, Fill hello, Click Disable, Validate Element State expect Disabled,
Close Tab) with a DELIBERATELY SHORT pause before the validate step (reproducing the race), then replays it."""
import importlib.util, json, sys, tempfile, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/dynamic_controls"

def record(pause_before_validate_s=0.3, expect_state="disabled"):
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
        pg.wait_for_timeout(pause_before_validate_s * 1000)  # deliberately short - reproduces the exact race
        tc = rec.stop(name="dc_final_repro", stop_reason="terminal_enter")
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
                           "bounding_box": None, "page_url": tc["actions"][-1]["page_url"], "check": expect_state})
    tc["actions"].append({"action_type": "tab_close", "value": None, "locator_profile": None,
                           "bounding_box": None, "page_url": tc["actions"][-1]["page_url"]})
    return tc


def replay(tc, label):
    d = Path(f"tests/_probe_out/dc_final_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"dc_final_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"dc_final_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t0 = time.monotonic()
    res = mod.run(URL, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    dt = time.monotonic() - t0
    print(f"\n=== {label} (total wall time {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:130])
    print("status:", res["status"], "|", res.get("message"))
    print("CLI-style counts:")
    return res


def check3():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx)
        pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_timeout(800)
        rec.start(launch_url=pg.url)
        tc = rec.stop(name="dc_final_check3", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path); b.close()
    for d in drafts:
        if d: Path(d).unlink(missing_ok=True)
    input_lp = {"id": None, "css_path": "#input-example input", "xpath": "//*[@id='input-example']//input",
                "text": "", "role": None, "tag": "input", "attributes": {}}
    tc["actions"].append({"action_type": "validate_element", "value": None, "locator_profile": input_lp,
                           "bounding_box": None, "page_url": tc["actions"][-1]["page_url"], "check": "disabled"})
    tc["actions"].append({"action_type": "tab_close", "value": None, "locator_profile": None,
                           "bounding_box": None, "page_url": tc["actions"][-1]["page_url"]})
    replay(tc, "check3_instant_pass")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("all", "1"):
        tc1 = record(pause_before_validate_s=0.3, expect_state="disabled")
        replay(tc1, "check1_7of7")

    if which in ("all", "2"):
        # NOTE (investigation finding, reported separately): recorded
        # delay_before_ms/_step_delay is dead code in this generator -
        # nothing in the main replay loop ever calls it, so replay never
        # actually re-creates a human's OWN pacing between steps. That
        # means right after Click Disable the input briefly still reads
        # "enabled" (the real toggle is ~2-3s async) with NO pause before
        # validate_element's own first poll - checking "enabled" there
        # would trivially match that transient split-second and pass
        # instantly, testing nothing. To exercise a WRONG expectation that
        # is never true at any point (the real target of this check), this
        # validates a state that never changes at all: the input right
        # after Navigate, before Enable is ever clicked - it starts (and
        # stays) disabled, so expecting "enabled" is wrong from t=0 through
        # the whole poll window.
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True); ctx = b.new_context(); pg = ctx.new_page()
            rec = Recorder(pg); rec.install_context_capture(ctx)
            pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_timeout(800)
            rec.start(launch_url=pg.url)
            tc2 = rec.stop(name="dc_final_check2", stop_reason="terminal_enter")
            drafts = (rec._draft_path, rec._draft_jsonl_path); b.close()
        for d in drafts:
            if d: Path(d).unlink(missing_ok=True)
        input_lp2 = {"id": None, "css_path": "#input-example input", "xpath": "//*[@id='input-example']//input",
                     "text": "", "role": None, "tag": "input", "attributes": {}}
        tc2["actions"].append({"action_type": "validate_element", "value": None, "locator_profile": input_lp2,
                                "bounding_box": None, "page_url": tc2["actions"][-1]["page_url"], "check": "enabled"})
        tc2["actions"].append({"action_type": "tab_close", "value": None, "locator_profile": None,
                                "bounding_box": None, "page_url": tc2["actions"][-1]["page_url"]})
        replay(tc2, "check2_wrong_expectation")

    if which in ("all", "3"):
        check3()
