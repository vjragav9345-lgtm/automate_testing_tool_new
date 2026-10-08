"""TEST-ONLY: FIX 1-5 acceptance on local fixtures (no site-specific code).

 A  hover mega menu, recorded 5 times with different mouse paths via the REAL
    Recorder -> identical step list, every replay PASSES
 B  click-to-open menu (href="#" + aria-expanded), hover does nothing -> replay PASSES
 C  hash-routed SPA (#/route links) -> replay PASSES, fragments never "page changed"
 D  a wrong destination still FAILS in plain English
"""
import importlib.util
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository
from generator.script_generator import generate_script

OUT = BASE / "tests" / "_probe_out" / "reveal"
OUT.mkdir(parents=True, exist_ok=True)
HEADLESS = "--headed" not in sys.argv


def record(url, driver, name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=HEADLESS)
        ctx = b.new_context(viewport={"width": 1100, "height": 700})
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(500)
        rec.start(launch_url=pg.url)
        driver(pg)
        pg.wait_for_timeout(2500)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def center(pg, sel):
    bb = pg.locator(sel).first.bounding_box()
    return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2


def steps_of(tc):
    out = []
    for a in tc["actions"]:
        lp = a.get("locator_profile") or {}
        out.append((a["action_type"], (lp.get("text") or "")[:20].replace("\n", " ")))
    return out


def replay(tc, label, start):
    d = OUT / label
    d.mkdir(parents=True, exist_ok=True)
    tc = repository.migrate_recording(tc)
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    t = time.monotonic()
    res = m.run(start, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    took = time.monotonic() - t
    print(f"  replay {label}: {took:.1f}s final_url={res.get('final_url')}")
    for s in res["steps"]:
        print("   ", s["index"], s["action_type"], "ok=" + str(s["success"]), "|", (s.get("error") or s.get("warning") or "")[:150])
    return res, tc


def path_fast(pg):
    x, y = center(pg, "#feat"); pg.mouse.move(x, y, steps=2)
    x, y = center(pg, "#pa"); pg.mouse.move(x, y, steps=2); pg.mouse.click(x, y)


def path_slow(pg):
    x, y = center(pg, "#feat"); pg.mouse.move(x - 40, y - 5, steps=5); pg.mouse.move(x, y, steps=40)
    pg.wait_for_timeout(900)
    x2, y2 = center(pg, "#pa"); pg.mouse.move(x2, y2, steps=40); pg.wait_for_timeout(500); pg.mouse.click(x2, y2)


def path_linger(pg):
    x, y = center(pg, "#feat"); pg.mouse.move(x, y, steps=8)
    pg.wait_for_timeout(400)
    for sel in ("aside.panel", "#wf", "#imp", "aside.panel"):
        a, b = center(pg, sel); pg.mouse.move(a, b, steps=12); pg.wait_for_timeout(500)
    a, b = center(pg, "#pa"); pg.mouse.move(a, b, steps=10); pg.wait_for_timeout(700); pg.mouse.click(a, b)


def path_click_trigger(pg):
    x, y = center(pg, "#feat"); pg.mouse.move(x, y, steps=10); pg.wait_for_timeout(300); pg.mouse.click(x, y)
    pg.wait_for_timeout(400)
    a, b = center(pg, "#pa"); pg.mouse.move(a, b, steps=15); pg.mouse.click(a, b)


def path_hover_then_empty(pg):
    x, y = center(pg, "#feat"); pg.mouse.move(x, y, steps=6)
    pg.wait_for_timeout(300)
    pg.mouse.move(x + 150, y + 180, steps=12); pg.wait_for_timeout(300)   # empty panel space
    a, b = center(pg, "#pa"); pg.mouse.move(a, b, steps=6); pg.mouse.click(a, b)


fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("  CHECK FAILED:", msg)


with FixtureServer() as srv:
    url = srv.url("rv_mega_hover.html")
    print("== A: hover mega menu, 5 mouse paths")
    lists = {}
    for nm, fn in (("fast", path_fast), ("slow", path_slow), ("linger", path_linger),
                   ("click_trigger", path_click_trigger), ("hover_empty", path_hover_then_empty)):
        tc = record(url, fn, f"rv_a_{nm}")
        tc = repository.migrate_recording(tc)
        lists[nm] = steps_of(tc)
        print(" ", nm, "->", lists[nm])
        res, _ = replay(tc, f"a_{nm}", url)
        check(all(s["success"] for s in res["steps"]), f"A/{nm}: replay not all PASS")
        check("hov_menu_target" in (res.get("final_url") or ""), f"A/{nm}: wrong final url {res.get('final_url')}")
    ref = lists["fast"]
    for nm, lst in lists.items():
        if nm == "click_trigger":
            # the user CLICKED the trigger: that click is kept as a Click step, never a hover
            check(lst == [("navigate", ""), ("click", "Features"), ("click", "Pro Analytics")], f"A: click_trigger steps {lst}")
        else:
            check(lst == ref, f"A: step list of {nm} differs from fast: {lst} vs {ref}")

    print("== B: click-to-open menu")
    url = srv.url("rv_click_menu.html")

    def drv_b(pg):
        x, y = center(pg, "#lang"); pg.mouse.move(x, y, steps=8); pg.mouse.click(x, y)
        pg.wait_for_timeout(400)
        a, b = center(pg, "#es"); pg.mouse.move(a, b, steps=12); pg.wait_for_timeout(300); pg.mouse.click(a, b)
    tc = record(url, drv_b, "rv_b")
    kinds_b = steps_of(repository.migrate_recording(dict(tc)))
    print(" ", kinds_b)
    check(kinds_b == [("navigate", ""), ("click", "Language"), ("click", "Espanol")], f"B: steps {kinds_b}")
    res, _ = replay(tc, "b_click_menu", url)
    check(all(s["success"] for s in res["steps"]), "B: replay not all PASS")
    check("hov_menu_target" in (res.get("final_url") or ""), f"B: wrong final url {res.get('final_url')}")

    print("== C: hash-routed SPA")
    url = srv.url("rv_spa.html")

    def drv_c(pg):
        x, y = center(pg, "#p"); pg.mouse.move(x, y, steps=5); pg.mouse.click(x, y)
        pg.wait_for_timeout(500)
        x, y = center(pg, "#a"); pg.mouse.move(x, y, steps=5); pg.mouse.click(x, y)
        pg.wait_for_timeout(500)
    tc = record(url, drv_c, "rv_c")
    res, _ = replay(tc, "c_spa", url)
    check(all(s["success"] for s in res["steps"]), "C: replay not all PASS")
    check((res.get("final_url") or "").endswith("#/about"), f"C: wrong final url {res.get('final_url')}")

    print("== E: hover opens, click on the trigger toggles it closed -> re-hover once")
    url = srv.url("rv_toggle_menu.html")

    def drv_e(pg):
        x, y = center(pg, "#trg"); pg.mouse.move(x, y, steps=8); pg.wait_for_timeout(300)
        pg.mouse.click(x, y); pg.wait_for_timeout(400)          # closes it
        pg.mouse.move(x, y + 200, steps=5); pg.wait_for_timeout(200)   # leave: bar mouseleave
        pg.mouse.move(x, y, steps=8); pg.wait_for_timeout(300)  # hover again: reopens
        a, b = center(pg, "#item"); pg.mouse.move(a, b, steps=8); pg.wait_for_timeout(200); pg.mouse.click(a, b)
    tc = record(url, drv_e, "rv_e")
    print(" ", steps_of(repository.migrate_recording(dict(tc))))
    res, _ = replay(tc, "e_toggle", url)
    check(all(s["success"] for s in res["steps"]), "E: replay not all PASS")
    check("hov_menu_target" in (res.get("final_url") or ""), f"E: wrong final url {res.get('final_url')}")

    print("== D: wrong destination still fails in plain English")
    url = srv.url("rv_mega_hover.html")
    tc = record(url, path_fast, "rv_d")
    tc = repository.migrate_recording(tc)
    print("  D actions:", [(a["action_type"], a.get("expected_url")) for a in tc["actions"]])
    for a in tc["actions"]:
        if a.get("expected_url"):
            a["expected_url"] = srv.url("hov_footer.html")
            a["expected_url_chain"] = [srv.url("hov_footer.html")]
    res, _ = replay(tc, "d_wrong", url)
    bad = [s for s in res["steps"] if not s["success"]]
    check(bool(bad) and all((s.get("error") or "").strip() for s in bad), "D: expected a FAIL with a reason")

print("\nFAILED CHECKS:" if fails else "\nALL CHECKS PASSED")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
