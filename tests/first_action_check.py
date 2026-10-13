"""TEST-ONLY (verify only): a recording whose first action is not a Navigate still stops the replay with a clear message."""
import importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/first_action"; OUT.mkdir(parents=True, exist_ok=True)
with FixtureServer() as fx:
    url = fx.url("gap_page.html")
    tc = {"name": "fa", "start_url": url, "actions": [
        {"action_type": "click", "page_url": url, "value": None, "locator_profile": {"tag": "button", "text": "x", "attributes": {}}},
        {"action_type": "navigate", "page_url": url, "locator_profile": {}, "value": None}]}
    sp = generate_script(tc, out_name="fa.py", output_dir=OUT)
    spec = importlib.util.spec_from_file_location("fa", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    res = m.run(url, output_json_path=OUT / "report.json", screenshot_dir=OUT / "shots", headless=True)
    print("MESSAGE:", res.get("message"))
    ok = "first action" in (res.get("message") or "") and not any(s["success"] for s in res.get("steps", []))
    print("FIRST ACTION CHECK", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
