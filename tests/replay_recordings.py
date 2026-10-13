"""TEST-ONLY: replay saved recordings (through load-time migration) headlessly."""
import importlib.util, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from storage import repository
from generator.script_generator import generate_script
for name in sys.argv[1:]:
    tc = repository.load_recording(f"recordings/{name}.json")
    d = BASE / "tests/_probe_out/rr" / name; d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{name}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(name, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    t = time.monotonic()
    res = m.run(tc.get("start_url") or tc["actions"][0]["page_url"], output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    print(f"\n##### {name}: {time.monotonic()-t:.0f}s")
    for s in res["steps"]:
        print(" ", s["index"], s["action_type"], "ok=" + str(s["success"]), "|", (s.get("error") or s.get("warning") or "")[:200])
