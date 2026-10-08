"""TEST-ONLY: STEP 1 investigation, part 2. Records a REAL tab_open/tab_close via a genuine
target="_blank" link (the-internet.herokuapp.com/windows), using the real Recorder (so page_id/
from_page_id/remaining_page_id are assigned the normal way), then replays it with the real
generator to see whether tab_open/tab_close actually work correctly when page_id is NOT
corrupted (i.e. genuinely distinct from the opener's page_id) - a baseline/control for comparison
against the exact page_id=0-for-everything pattern seen in the real bug report's recording."""
import importlib.util
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from generator.script_generator import generate_script

URL = "https://the-internet.herokuapp.com/windows"


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
        with ctx.expect_page() as new_page_info:
            pg.click("text=Click Here")
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        rec.record_new_tab(new_page)
        pg.wait_for_timeout(400)
        new_page.close()
        pg.wait_for_timeout(400)
        tc = rec.stop(name="tabopen_investigate2", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def replay(tc, label):
    d = Path(f"tests/_probe_out/tabopen_investigate2_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"tabopen_investigate2_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"tabopen_investigate2_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    start_url = tc.get("start_url") or URL
    t0 = time.monotonic()
    res = mod.run(start_url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    dt = time.monotonic() - t0
    print(f"\n=== {label} (total wall time {dt:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "not_run=" + str(s.get("not_run")), repr(s.get("error"))[:160])
    print("status:", res["status"], "|", res.get("message"))
    return res


if __name__ == "__main__":
    tc = record()
    print("\nRECORDED ACTIONS:")
    for i, a in enumerate(tc["actions"], 1):
        print(i, a.get("action_type"), "page_id=", a.get("page_id"), "from_page_id=", a.get("from_page_id"),
              "remaining_page_id=", a.get("remaining_page_id"), "page_url=", a.get("page_url"))
    Path("tests/_probe_out").mkdir(exist_ok=True)
    Path("tests/_probe_out/tabopen_investigate2_recorded.json").write_text(json.dumps(tc, indent=2), encoding="utf-8")
    replay(tc, "normal_control")
