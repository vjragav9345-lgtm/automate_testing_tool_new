"""TEST-ONLY: two VISIBLE same-named links (header + footer): the one matching the RECORDED identity
(link target, landmark, parents) is clicked - never just "any visible copy"."""
import importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/twin"; OUT.mkdir(parents=True, exist_ok=True)
def lp(href, css):
    return {"id": None, "tag": "a", "text": "Pricing", "element_text": "Pricing", "accessible_name": "Pricing",
            "attributes": {"href": href}, "href": href, "css_path": css, "xpath": "//stale/path"}
def run(label, rec_lp, box=None):
    url = fx.url("twin_header_footer.html"); d = OUT / label; d.mkdir(exist_ok=True)
    act = {"action_type": "click", "page_url": url, "value": None, "scroll_y": 0, "locator_profile": rec_lp}
    if box: act["bounding_box"] = box
    tc = {"name": label, "start_url": url, "actions": [{"action_type": "navigate", "page_url": url, "locator_profile": {}, "value": None}, act]}
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    return res.get("final_url") or "", res["steps"][1]
fails = []
with FixtureServer() as fx:
    for label, rec, want in (
        ("header_by_href", lp("hov_menu_target.html?src=header", "body > header > nav > ul > li > a"), "src=header"),
        ("footer_by_href", lp("hov_menu_target.html?src=footer", "body > footer > ul > li > a"), "src=footer"),
        ("header_by_landmark", lp(None, "body > header > div > nav > span > a"), "src=header"),
        ("footer_by_landmark", lp(None, "body > footer > div > span > a"), "src=footer"),
    ):
        url, s = run(label, rec)
        print(f"{label}: -> {url} ({s.get('strategy_used')}, ok={s['success']})")
        if want not in url: fails.append((label, url))
print("TWIN CHECK", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
