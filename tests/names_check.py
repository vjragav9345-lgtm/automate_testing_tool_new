"""TEST-ONLY: ISSUE 4 - readable names and plain-English failure messages for elements without visible text."""
import importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
import app as dash
OUT = BASE / "tests/_probe_out/names"; OUT.mkdir(parents=True, exist_ok=True)

def lp(**kw):
    b = {"id": None, "tag": None, "text": "", "element_text": "", "aria_label": None, "accessible_name": "", "attributes": {}}
    b.update(kw); return b

# labels shown in the live log
cases = {
    "aria-label": lp(tag="button", aria_label="Save draft", attributes={"aria-label": "Save draft"}),
    "title": lp(tag="button", attributes={"title": "Close"}, title="Close"),
    "alt": lp(tag="img", attributes={"alt": "Company logo"}),
    "nothing": lp(tag="button"),
}
exp = {"aria-label": "Save draft", "title": "Close", "alt": "Company logo", "nothing": "button"}
fails = []
for k, l in cases.items():
    got = dash._step_element_label([{"action_type": "click", "locator_profile": l}], {"index": 1})
    print(f"label[{k}] = {got!r}")
    if got != exp[k]: fails.append((k, got))

with FixtureServer() as fx:
    url = fx.url("gap_page.html")
    for k, l in (("aria-label", cases["aria-label"]), ("nothing", cases["nothing"])):
        tc = {"name": f"n_{k}", "start_url": url, "actions": [
            {"action_type": "navigate", "page_url": url, "locator_profile": {}, "value": None},
            {"action_type": "click", "page_url": url, "value": None, "scroll_y": 0, "locator_profile": l}]}
        d = OUT / k; d.mkdir(exist_ok=True)
        sp = generate_script(tc, out_name=f"n_{k}.py", output_dir=d)
        spec = importlib.util.spec_from_file_location(f"n_{k}", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
        s = res["steps"][1]
        print(f"error[{k}] =", s.get("error"))
        e = s.get("error") or ""
        if "the element" in e: fails.append((k, "still says 'the element'"))
        if not e.startswith("Failed: Could not find the ") or "may have been removed or hidden" not in e: fails.append((k, e))
        if k == "aria-label" and "'Save draft' button" not in e: fails.append((k, e))
print("NAMES CHECK", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
