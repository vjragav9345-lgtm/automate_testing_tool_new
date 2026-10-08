"""TEST-ONLY: generic behaviours, each RECORDED with the real recorder and REPLAYED (no site-specific values).
 A  search box with an autocomplete list -> Enter -> results page (full reload)   / same as a single-page app
    form submit -> next page / link -> new page / link that opens a new tab
    real dialog opens -> click inside it (video area) -> close with its X
    dropdown/menu opens -> click an item / tab changes content in place (count)
    a click that changes nothing / icon-only button + placeholder-only input (naming)
 F  real failures must still FAIL in plain English: popup never opens, target missing, Enter does nothing,
    page goes to a different address, page shows different content
 W  a changed count in the clicked item -> WARNING with before/now values, run continues
"""
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

OUT = BASE / "tests" / "_probe_out" / "generic"; OUT.mkdir(parents=True, exist_ok=True)
TECH = re.compile(r"locator|css_path|xpath|selector|strategy|hit-testable|PAGE_MISMATCH|bounding|\bDOM\b|tier|\[details\]|data-afqa|iframe|None\b", re.I)
fails = []
def check(name, ok, extra=""):
    print(("  PASS " if ok else "  FAIL ") + name, extra)
    if not ok: fails.append(name)

def record(url, driver, name, new_tab_ok=False):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1100, "height": 760}); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded"); pg.wait_for_timeout(400)
        rec.start(launch_url=url)
        def _np(npage):                       # same wiring as the dashboard's recording session
            try: npage.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception: pass
            rec.record_new_tab(npage)
        ctx.on("page", _np)
        driver(pg, ctx)
        pg.wait_for_timeout(2500)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        for d in (rec._draft_path, rec._draft_jsonl_path):
            if d: Path(d).unlink(missing_ok=True)
        b.close()
    return tc

def replay(tc, label, start=None):
    tc = repository.migrate_recording(copy.deepcopy(tc))
    d = OUT / label; d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(start or tc["start_url"], output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    return res, tc

def names(tc, res):
    out = []
    for i, a in enumerate(tc["actions"], 1):
        live = dash._step_element_label(tc["actions"], {"index": i})
        out.append(f"{live} | {res['steps'][i-1].get('name')}" if i <= len(res["steps"]) else str(live))
    return out

def _tc_of(name): return RECS[name][1]['actions']

def swap(tc, old, new):
    return json.loads(json.dumps(tc).replace(old, new))

def click(sel): return lambda pg: pg.locator(sel).first.click()

def scenario_drivers(fx):
    u = fx.url
    def search(pg, ctx):
        pg.locator("#q").click(); pg.keyboard.type("tamil", delay=40); pg.wait_for_timeout(500); pg.keyboard.press("Enter")
        pg.wait_for_timeout(1200); pg.locator("#r1").click(); pg.wait_for_timeout(800)
    def search_spa(pg, ctx):
        pg.locator("#q").click(); pg.keyboard.type("tamil", delay=40); pg.wait_for_timeout(500); pg.keyboard.press("Enter")
        pg.wait_for_timeout(1000); pg.locator("#r1").click(); pg.wait_for_timeout(800)
    def form(pg, ctx):
        pg.locator("input[name=email]").click(); pg.keyboard.type("ann@example.test", delay=30); pg.locator("#go").click(); pg.wait_for_timeout(800)
    def link_same(pg, ctx): pg.locator("#same").click(); pg.wait_for_timeout(800)
    def link_tab(pg, ctx): pg.locator("#tab").click(); pg.wait_for_timeout(1500)
    def dialog(pg, ctx):
        pg.locator("#open").click(); pg.wait_for_timeout(500); pg.locator("#video").click(); pg.wait_for_timeout(400); pg.locator("#x").click(); pg.wait_for_timeout(500)
    def menu(pg, ctx): pg.locator("#b").click(); pg.wait_for_timeout(400); pg.locator("#i1").click(); pg.wait_for_timeout(800)
    def tabs(pg, ctx): pg.locator("#t2").click(); pg.wait_for_timeout(500)
    def noop(pg, ctx): pg.locator("#n").click(); pg.wait_for_timeout(500)
    def icons(pg, ctx):
        pg.locator("#ib").click(); pg.wait_for_timeout(300); pg.locator("#ph").click(); pg.keyboard.type("Ann", delay=40); pg.keyboard.press("Tab")
        pg.locator("iframe").click(); pg.wait_for_timeout(300)
    return [("search_reload", u("g_search.html"), search), ("search_spa", u("g_search_spa.html"), search_spa),
            ("form", u("g_form.html"), form), ("link_same", u("g_links.html"), link_same), ("link_newtab", u("g_links.html"), link_tab),
            ("dialog", u("g_dialog.html"), dialog), ("menu", u("g_menu.html"), menu), ("tabs", u("g_tabs.html"), tabs),
            ("noop", u("g_noop.html"), noop), ("icons", u("g_icons.html"), icons),
            ("results_link", u("g_results.html?q=tamil"), lambda pg, ctx: (pg.locator("#r1").click(), pg.wait_for_timeout(800)))]

WANT = sys.argv[1:]
with FixtureServer() as fx:
    recs = {}
    RECS = recs
    print("== A: record + replay")
    for name, url, drv in scenario_drivers(fx):
        if WANT and name not in WANT and not ({'F', 'W'} & set(WANT) and name in ('search_reload', 'dialog', 'menu', 'tabs', 'results_link')):
            continue
        tc = record(url, drv, f"gen_{name}")
        recs[name] = (url, tc)
        res, tcm = replay(tc, f"a_{name}")
        nm = names(tcm, res)
        kinds = [a["action_type"] for a in tcm["actions"]]
        print(f"- {name}: {list(zip(kinds, nm))}")
        for s in res["steps"]:
            if not s["success"] or s.get("warning"):
                print("     step", s["index"], "ok=" + str(s["success"]), (s.get("error") or "")[:200], "| warn:", (s.get("warning") or "")[:150])
        check(f"{name}: all steps PASS", all(s["success"] for s in res["steps"]))
        check(f"{name}: no warning", not any(s.get("warning") for s in res["steps"]))
        check(f"{name}: readable names", not any(re.search(r"unnamed|\b(div|span|svg)\b|the element", n.split(" | ")[0] + " | " + n.split(" | ")[-1], re.I) for n in nm[1:]), str(nm[1:]))

    RUN_F = (not WANT) or "F" in WANT
    RUN_W = (not WANT) or "W" in WANT
    print("== F: real failures still FAIL in plain English")
    def fail_case(label, rec_name, old, new, want, step_idx=None):
        url, tc = recs[rec_name]
        tcf = swap(tc, old, new)
        res, _ = replay(tcf, f"f_{label}")
        bad = [s for s in res["steps"] if not s["success"] and not s.get("not_run")]
        msg = (bad[0].get("error") or "") if bad else ""
        head = step_headline(bad[0], dash._step_element_label(_tc_of(rec_name), bad[0])) if bad else ""
        print(f"- {label}: {'FAILED' if bad else 'PASSED(!)'} -> {head[:220]}")
        check(f"{label}: FAILS", bool(bad))
        check(f"{label}: plain English, expected wording", bool(bad) and want.lower() in head.lower() and not TECH.search(head), head[:120])
        return res
    if RUN_F:
        fail_case("popup_never_opens", "dialog", "g_dialog.html", "g_dialog_broken.html", "no popup appeared")
        fail_case("target_missing", "menu", "g_menu.html", "g_menu_missing.html", "could not find")
        fail_case("enter_does_nothing", "search_reload", "g_search.html", "g_search_noenter.html", "did not change the way it did during recording")
        fail_case("different_address", "search_reload", "g_search.html", "g_search_other.html", "instead")
        url, tc = recs["results_link"]
        res, _ = replay(swap(tc, "q=tamil", "q=other"), "f_content")
        st = res["steps"][1]
        warn = st.get("warning") or ""
        print("- content_changed (same element, different label):", "PASS+WARNING" if st["success"] and warn else ("PASS" if st["success"] else "FAIL"), "|", (st.get("error") or warn)[:260])
        check("content_changed: not silent - a WARNING names the recorded and the current label (or a plain FAIL)",
              (st["success"] and "tamil" in warn and "other" in warn) or (not st["success"] and not TECH.search(st.get("error") or "")), (st.get("error") or warn)[:140])
        # and the recorded item is simply gone -> FAIL, never another item
        res2, _ = replay(swap(tc, "g_results.html?q=tamil", "g_next.html"), "f_content_gone")
        bad2 = [x for x in res2["steps"] if not x["success"] and not x.get("not_run")]
        head2 = step_headline(bad2[0], "First result for tamil") if bad2 else ""
        print("- content_gone:", head2[:240])
        check("content_gone: FAILS in plain English", bool(bad2) and not TECH.search(head2), head2[:120])
    print("== W: a changed count in the clicked item is a WARNING that continues")
    if RUN_W:
        url, tc = recs["tabs"]
        res, _ = replay(swap(tc, "g_tabs.html", "g_tabs.html?after=80"), "w_count")
        st = res["steps"][1]
        print("- count step:", st["success"], (st.get("warning") or "")[:200])
        check("count change: step continues (PASS with WARNING)", st["success"] and bool(st.get("warning")))
        check("count change: shows before and now", "95" in (st.get("warning") or "") and "80" in (st.get("warning") or ""), (st.get("warning") or "")[:160])


print("\nGENERIC FLOW CHECK:", "ALL PASS" if not fails else f"FAILED {fails}")
sys.exit(1 if fails else 0)
