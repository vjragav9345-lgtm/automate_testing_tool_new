"""TEST-ONLY: Item A - the post-click side-check (generic local fixtures; no site value anywhere).
 A-1 click fills a visible labelled field that was not changed while recording -> WARNING naming it, run continues
 A-2 click while the script changes a hidden input                               -> ignored, PASS, no warning
 A-3 a field that changes on a timer by itself                                    -> ignored, PASS, no warning
 A-4 chat-like page (type, Enter, reply appended, hidden state updated, click box again, type, Enter) -> all PASS
 A-5 the clicked element itself is missing                                         -> still FAILS in plain English"""
import copy, importlib.util, json, re, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository
from generator.script_generator import generate_script
from validation.report_generator import step_headline
import app as dash

OUT = BASE / "tests" / "_probe_out" / "sidecheck"; OUT.mkdir(parents=True, exist_ok=True)
TECH = re.compile(r"locator|css_path|xpath|selector|strategy|hit-testable|bounding|\bDOM\b|\[details\]|data-afqa|None\b|the item|parts", re.I)
fails = []
def check(name, ok, extra=""):
    print(("  PASS " if ok else "  FAIL ") + name, extra)
    if not ok: fails.append(name)

def record(url, driver, name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1100, "height": 760}); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded"); pg.wait_for_timeout(400)
        rec.start(launch_url=url)
        driver(pg)
        pg.wait_for_timeout(1500)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        for d in (rec._draft_path, rec._draft_jsonl_path):
            if d: Path(d).unlink(missing_ok=True)
        b.close()
    return tc

def replay(tc, label):
    tc = repository.migrate_recording(copy.deepcopy(tc))
    d = OUT / label; d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.run(tc["start_url"], output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True), tc

def swap(tc, old, new): return json.loads(json.dumps(tc).replace(old, new))
def show(res):
    for s in res["steps"]:
        print("     step", s["index"], s["action_type"], "ok=" + str(s["success"]), "|", (s.get("error") or "")[:160], "| warn:", (s.get("warning") or "")[:200])

with FixtureServer() as fx:
    u = fx.url
    tc = record(u("sc_a_click.html"), lambda pg: (pg.locator("#msgbox").click(), pg.wait_for_timeout(500)), "sc_a_click")
    print("== A-1 click fills a visible labelled field")
    res, _ = replay(swap(tc, "sc_a_click.html", "sc_a_click.html?fill=1"), "a1"); show(res)
    w = " ".join(s.get("warning") or "" for s in res["steps"])
    check("A-1 run continues, all steps PASS", all(s["success"] for s in res["steps"]))
    check("A-1 WARNING names the field and the button", "Email" in w and "Message box" in w and not TECH.search(w.split("[details]")[0]), w[:200])
    print("== A-2 hidden input changed by script")
    res, _ = replay(swap(tc, "sc_a_click.html", "sc_a_click.html?hidden=1"), "a2"); show(res)
    check("A-2 PASS, no warning", all(s["success"] for s in res["steps"]) and not any(s.get("warning") for s in res["steps"]))
    print("== A-3 field changing on a timer")
    res, _ = replay(swap(tc, "sc_a_click.html", "sc_a_click.html?timer=1"), "a3"); show(res)
    check("A-3 PASS, no warning", all(s["success"] for s in res["steps"]) and not any(s.get("warning") for s in res["steps"]))
    print("== A-4 chat-like page")
    def chat(pg):
        pg.locator("#box").click(); pg.keyboard.type("hello there", delay=30); pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
        pg.locator("#box").click(); pg.keyboard.type("second one", delay=30); pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
    tcc = record(u("sc_a_chat.html"), chat, "sc_a_chat")
    print("   recorded:", [a["action_type"] for a in tcc["actions"]])
    res, _ = replay(tcc, "a4"); show(res)
    check("A-4 all steps PASS", all(s["success"] for s in res["steps"]))
    check("A-4 no warning", not any(s.get("warning") for s in res["steps"]))
    print("== A-5 clicked element missing")
    res, _ = replay(swap(tc, "sc_a_click.html", "sc_a_click_missing.html"), "a5"); show(res)
    bad = [s for s in res["steps"] if not s["success"] and not s.get("not_run")]
    head = step_headline(bad[0], "Message box") if bad else ""
    check("A-5 FAILS in plain English", bool(bad) and not TECH.search(head), head[:160])

print("\nSIDECHECK:", "ALL PASS" if not fails else f"FAILED {fails}")
sys.exit(1 if fails else 0)
