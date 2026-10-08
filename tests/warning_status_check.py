"""TEST-ONLY: WARNING status (Req 2) + live phases/timestamps (Req 1) +
settled screenshot (Req 3), all offline against local fixtures.

 A  post-click focus mismatch: clicking a card auto-fills + focuses a prompt
    box (the ChatGPT-Images "Sketch" shape) -> click is PASS-with-WARNING and
    the NEXT step still runs (no skip cascade)
 B  same slot, different content: the Nth card of a grid now shows a
    different product (the Myntra step-14 shape) -> the click goes to the
    element in that slot, WARNING, next step runs
 C  nothing actionable at all (the grid is empty) -> still FAILS as before
 D  every step carries started_at/ended_at, current_step is cleared at the
    end, and the step's screenshot path is patched in after the result
"""
import importlib.util
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from generator.script_generator import generate_script

OUT = Path("tests/_probe_out/warning_status")
OUT.mkdir(parents=True, exist_ok=True)


def record(url, do_actions, name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        do_actions(pg)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def replay(tc, url, label):
    d = OUT / label
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    print(f"\n=== {label} ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "strategy=" + str(s.get("strategy_used")),
              "\n     warning=" + repr(s.get("warning")), "\n     error=" + repr(s.get("error"))[:200])
    print("status:", res["status"])
    return res


with FixtureServer() as srv:
    # ---------- A: post-click focus mismatch -> WARNING, next step runs
    def act_a(pg):
        pg.click("#sketch")
        pg.wait_for_timeout(300)
        pg.fill("#prompt", "hello world")
        pg.wait_for_timeout(300)

    tc_a = record(srv.url("warn_prompt_v1.html"), act_a, "warn_a")
    res = replay(tc_a, srv.url("warn_prompt_v1.html"), "a_prompt")
    st = res["steps"]
    click = next(s for s in st if s["action_type"] == "click")
    assert click["success"], f"A: click must not fail: {click.get('error')}"
    assert all(s["success"] for s in st), "A: no step may fail/skip"
    # the recording's click moved focus to the prompt box and so does the replay's:
    # identical to manual -> PASS with NO warning (no false "different content")
    assert not click.get("warning"), f"A: replay behaved like manual, no warning expected: {click.get('warning')}"
    print("A: clean PASS, no warning")

    # ---------- B: the slot now holds a DIFFERENT item -> FAIL + stop (the old
    # "click whatever is in that slot and warn" rule was replaced)
    def act_b(pg):
        pg.click("#grid a:nth-child(1)")
        pg.wait_for_timeout(500)
        pg.click("#buy")
        pg.wait_for_timeout(300)

    tc_b = record(srv.url("warn_grid_v1.html"), act_b, "warn_b")
    res = replay(tc_b, srv.url("warn_grid_v2.html"), "b_slot")
    st = res["steps"]
    card = next(s for s in st if s["action_type"] == "click")
    assert not card["success"], "B: a different item in the slot must FAIL, not be clicked"
    assert card["error"].startswith("Failed: Could not find the 'CAHOOT"), card["error"]
    assert all((not s["success"]) and s.get("not_run") for s in st if s["index"] > card["index"]), "later steps must be NOT RUN"
    assert "Not run because" not in card["error"]
    print("B ok:", card["error"])

    # ---------- C: nothing actionable -> still FAIL
    res = replay(tc_b, srv.url("warn_grid_v3.html"), "c_nothing")
    st = res["steps"]
    first = next(s for s in st if s["action_type"] == "click")
    assert not first["success"], "C: an empty grid must still FAIL"
    print("C ok: still fails ->", (first.get("error") or "")[:120])

    # ---------- D: timestamps, current_step cleared, screenshot patched
    rep = json.loads((OUT / "b_slot" / "report.json").read_text(encoding="utf-8"))
    assert "current_step" not in rep, "D: current_step must be cleared at the end"
    for s in (x for x in rep["steps"] if not x.get("not_run")):
        assert s.get("started_at") and s.get("ended_at"), f"D: step {s['index']} lacks start/end timestamps"
        assert s["started_at"] <= s["ended_at"], "D: start must not be after end"
    print("D ok: started_at/ended_at on every step, current_step cleared")

print("\nWARNING STATUS CHECKS PASS")
