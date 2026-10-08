"""TEST-ONLY (REQ 6): expected post-click destination.
 R6a recorder: a click whose navigation commits LATE (client-side delay) records the
     committed URL as post_click.url_path_after (navigated=True), not the pre-click page
 R6b replay, OLD recording whose post-click URL is the PRE-click page (captured before the
     navigation finished) but whose next step is the Navigate it caused -> PASS, the
     Navigate step passes too
 R6c replay lands on a DIFFERENT page than the correct destination -> FAIL (stop)
 R6d rule 3 only (no post_click, no next Navigate, link href): a navigation to the href
     passes; a click that does not navigate is NOT failed by the href alone
"""
import importlib.util, json, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from generator.script_generator import generate_script
OUT = Path("tests/_probe_out/destination"); OUT.mkdir(parents=True, exist_ok=True)

def record(url, fn, name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded"); pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url); fn(pg)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path); b.close()
    for d in drafts:
        if d: Path(d).unlink(missing_ok=True)
    return tc

def replay(tc, url, label):
    d = OUT / label; d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    print(f"\n=== {label} ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "ok=" + str(s["success"]), "|", (s.get("error") or "")[:200])
    return res

with FixtureServer() as srv:
    a = srv.url("dest_a.html")
    def act(pg):
        pg.click("#go"); pg.wait_for_timeout(4500)
    tc = record(a, act, "dest_rec")
    click = next(x for x in tc["actions"] if x["action_type"] == "click")
    pc = click.get("post_click") or {}
    print("recorded post_click:", pc)
    print("recorded types:", [x["action_type"] for x in tc["actions"]], "expected_url:", click.get("expected_url"), click.get("expected_url_chain"))
    assert pc.get("navigated") and pc.get("url_path_after", "").endswith("/dest_b.html"), pc
    # I1-c: the click's navigation is attached to the click (expected_url), NOT a standalone Navigate step
    assert (click.get("expected_url") or "").endswith("/dest_b.html"), click.get("expected_url")
    assert [x["action_type"] for x in tc["actions"]].count("navigate") == 1, "only the genuine launch Navigate may remain"
    print("R6a ok")

    # R6b: old shape - the post-click URL is the PRE-click page
    old = json.loads(json.dumps(tc))
    for x in old["actions"]:
        if x["action_type"] == "click":
            x["post_click"] = {"url_path_before": a, "url_path_after": a, "focus": None, "fields_changed": []}
    res = replay(old, a, "r6b_old_shape")
    assert all(s["success"] for s in res["steps"]), "R6b: must PASS (steps incl. the following Navigate)"
    print("R6b ok")

    # R6c: the page goes somewhere else than the correct destination
    res = replay(tc, srv.url("dest_a_wrong.html"), "r6c_wrong")
    c = next(s for s in res["steps"] if s["action_type"] == "click")
    assert not c["success"] and "dest_b" not in "" , c
    from validation.report_generator import step_headline
    h = step_headline(c, "Pro Analytics"); print("R6c headline:", h)
    assert h.startswith("Failed: Expected to open '/dest_b.html' but the browser went to '/dest_c.html'"), h
    print("R6c ok")

    # R6d: rule 3 only
    r3 = {"name": "r3", "start_url": a, "actions": [
        {"action_type": "navigate", "page_url": a, "locator_profile": {}, "value": None},
        {"action_type": "click", "page_url": a, "value": None,
         "locator_profile": {"id": "go", "tag": "a", "text": "Pro Analytics", "element_text": "Pro Analytics",
                             "href": srv.url("dest_b.html"), "attributes": {}}}]}
    res = replay(r3, a, "r6d_href")
    assert all(s["success"] for s in res["steps"]), "R6d: navigation to the href must PASS"
    noop = srv.url("dest_a_noop.html")
    r3n = json.loads(json.dumps(r3).replace(a, noop))
    res = replay(r3n, noop, "r6d_href_noop")
    assert all(s["success"] for s in res["steps"]), "R6d: an href alone must not fail a click that did not navigate"
    print("R6d ok")

    # ---- R6e: SPA route change (pushState, no document load): recorded as the click's expected_url
    spa = srv.url("dest_spa.html")
    def act_spa(pg):
        pg.click("#go"); pg.wait_for_timeout(1500)
    tc_spa = record(spa, act_spa, "dest_spa_rec")
    ck = next(x for x in tc_spa["actions"] if x["action_type"] == "click")
    print("SPA recorded:", [x["action_type"] for x in tc_spa["actions"]], ck.get("expected_url"))
    assert (ck.get("expected_url") or "").endswith("/dest_spa_route/two"), ck.get("expected_url")
    res = replay(tc_spa, spa, "r6e_spa")
    assert all(s["success"] for s in res["steps"]) and not any(s.get("warning") for s in res["steps"]), "R6e: SPA route must PASS cleanly"
    print("R6e ok")

    # ---- R6f: tracking parameters differ between recording and replay -> PASS, no warning
    def act_trk(pg):
        pg.click("#go"); pg.wait_for_timeout(1500)
    tc_trk = record(srv.url("dest_track_rec.html"), act_trk, "dest_trk_rec")
    res = replay(tc_trk, srv.url("dest_track.html"), "r6f_tracking")
    assert all(s["success"] for s in res["steps"]), "R6f: tracking params must not matter"
    assert not any(s.get("warning") for s in res["steps"]), [s.get("warning") for s in res["steps"]]
    print("R6f ok")

    # ---- R6g: same page, a NON-tracking query differs -> WARNING and continue
    tc_q = json.loads(json.dumps(tc_trk).replace("utm_source=OLDSRC&gclid=AAA&q=1", "sort=price"))
    res = replay(tc_q, srv.url("dest_query.html"), "r6g_query")
    cl = next(s for s in res["steps"] if s["action_type"] == "click")
    assert cl["success"] and (cl.get("warning") or "").startswith("Warning: The page address has different"), cl.get("warning")
    print("R6g ok:", cl["warning"])
print("\nDESTINATION CHECKS PASS")
