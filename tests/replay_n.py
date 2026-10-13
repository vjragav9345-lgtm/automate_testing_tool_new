"""TEST-ONLY: replay saved recordings N times each (through load-time migration), table of results.
   python tests/replay_n.py N [--headed] name1 name2 ..."""
import importlib.util, sys, time, json
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from storage import repository
from generator.script_generator import generate_script
args = [a for a in sys.argv[1:] if not a.startswith("--")]
n = int(args[0]); names = args[1:]; headed = "--headed" in sys.argv
rows = []
for name in names:
    tc = repository.load_recording(f"recordings/{name}.json")
    for k in range(1, n + 1):
        d = BASE / "tests/_probe_out/rn" / f"{name}_{k}"; d.mkdir(parents=True, exist_ok=True)
        sp = generate_script(tc, out_name=f"{name}.py", output_dir=d)
        spec = importlib.util.spec_from_file_location(f"{name}_{k}", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        t = time.monotonic()
        res = m.run(tc.get("start_url") or tc["actions"][0]["page_url"], output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=not headed)
        took = time.monotonic() - t
        st = res["steps"]
        passed = sum(1 for s in st if s["success"])
        fail = [(s["index"], (s.get("error") or "")[:110]) for s in st if not s["success"] and not s.get("not_run")]
        sig = "".join("P" if s["success"] else ("n" if s.get("not_run") else "F") for s in st)
        rows.append((name, k, sig, f"{took:.0f}s", fail))
        print("ROW", name, k, sig, f"{took:.0f}s", fail, flush=True)
        json.dump({"name": name, "run": k, "sig": sig, "took": took, "steps": [(s["index"], s["action_type"], s["success"], s.get("duration"), s.get("timing_ms"), s.get("error"), s.get("warning")) for s in st]},
                  open(d / "summary.json", "w"), default=str)
