"""TEST-ONLY: record + replay on public sites of different kinds (no site value is used anywhere in the product code):
  wiki   - search box with an autocomplete list -> Enter -> a result page -> a link in it  (search / suggestion list)
  pyorg  - a hover menu -> an item -> a page                                           (documentation site with menus)
  shop   - category links -> sub category -> a product                                 (e-commerce navigation)
 python tests/real_sites_check.py wiki pyorg shop"""
import copy, importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from storage import repository
from generator.script_generator import generate_script
from validation.report_generator import step_headline
import app as dash

OUT = BASE / "tests" / "_probe_out" / "real"; OUT.mkdir(parents=True, exist_ok=True)

def record(url, driver, name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1280, "height": 800}); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        rec.start(launch_url=url)
        def _np(npage):
            try: npage.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception: pass
            rec.record_new_tab(npage)
        ctx.on("page", _np)
        driver(pg)
        pg.wait_for_timeout(2500)
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

def wiki(pg):
    pg.locator("input[name=search]:visible").first.click(); pg.keyboard.type("Chennai", delay=70); pg.wait_for_timeout(1200)
    pg.keyboard.press("Enter"); pg.wait_for_timeout(3000)
    pg.get_by_role("link", name="Tamil Nadu", exact=True).first.click(timeout=10000); pg.wait_for_timeout(2500)

def pyorg(pg):
    pg.locator("#downloads > a").first.hover(); pg.wait_for_timeout(700)
    pg.locator("#downloads ul.subnav a", has_text="Source code").first.click(timeout=10000); pg.wait_for_timeout(2500)

def shop(pg):
    pg.locator(".sidebar a, #side-menu a", has_text="Computers").first.click(); pg.wait_for_timeout(1500)
    pg.locator(".sidebar a, #side-menu a", has_text="Laptops").first.click(); pg.wait_for_timeout(1500)
    pg.locator(".product-wrapper a.title, .caption a.title").first.click(); pg.wait_for_timeout(2000)

def paste(pg):
    pg.locator("textarea").first.click(); pg.keyboard.type("hello from a test", delay=30); pg.wait_for_timeout(400)
    pg.locator("button[type=submit], input[type=submit]").first.click(); pg.wait_for_timeout(3000)

def form(pg):
    pg.locator("input[name=custname]").click(); pg.keyboard.type("Ann Test", delay=30)
    pg.locator("input[name=custemail]").click(); pg.keyboard.type("ann@example.test", delay=30)
    pg.locator("input[value=cheese]").check(); pg.wait_for_timeout(300)
    pg.locator("button").first.click(); pg.wait_for_timeout(2500)

def more(pg):
    pg.locator("a.btn.btn-primary.btn-lg, .ecomerce-items-scroll-more").first.click(); pg.wait_for_timeout(1500)
    pg.mouse.wheel(0, 1500); pg.wait_for_timeout(800)
    pg.locator(".product-wrapper a.title, .caption a.title").first.click(); pg.wait_for_timeout(2000)

SITES = {"more": ("https://webscraper.io/test-sites/e-commerce/more/computers/laptops", more), "paste": ("https://bpa.st/", paste), "form": ("https://httpbin.org/forms/post", form), "wiki": ("https://en.wikipedia.org/wiki/Main_Page", wiki), "pyorg": ("https://www.python.org/", pyorg),
         "shop": ("https://webscraper.io/test-sites/e-commerce/allinone", shop)}
bad = []
for name in (sys.argv[1:] or list(SITES)):
    url, drv = SITES[name]
    tc = record(url, drv, f"real_{name}")
    repository.save_recording(dict(tc))      # kept so the same recording can be replayed with another build
    kinds = [(a["action_type"], dash._step_element_label(tc["actions"], {"index": i}) or "") for i, a in enumerate(tc["actions"], 1)]
    print(f"=== {name}: recorded {kinds}")
    res, tcm = replay(tc, f"real_{name}")
    ok = True
    for s in res["steps"]:
        head = step_headline(s, dash._step_element_label(tcm["actions"], s)) or ""
        print(f"   step {s['index']} {s['action_type']:8s} {'PASS' if s['success'] else ('NOT RUN' if s.get('not_run') else 'FAIL'):8s} {s.get('duration')}s {head[:150]}")
        ok = ok and s["success"]
    if not ok: bad.append(name)
print("REAL SITES", "ALL PASS" if not bad else f"NOT ALL PASS: {bad}")
