"""TEST-ONLY, report-only (no product code changes): times step 5 (validate_checked) of the real
session_20260929_105345_edited recording by timestamping every print() line during an in-process replay."""
import builtins, importlib.util, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script
from storage import repository

REC = "storage/recordings/edited/session_20260929_105345_edited.json"
tc = repository.load_recording(REC)

timestamps = []
_orig_print = builtins.print
def _timed_print(*args, **kwargs):
    timestamps.append((time.monotonic(), " ".join(str(a) for a in args)))
    _orig_print(*args, **kwargs)
builtins.print = _timed_print

d = Path("tests/_probe_out/timing_105345")
d.mkdir(parents=True, exist_ok=True)
sp = generate_script(tc, out_name="timing_105345_script.py", output_dir=d)
spec = importlib.util.spec_from_file_location("timing_105345_mod", sp)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
res = mod.run(tc["start_url"], output_json_path=d / "r.json", screenshot_dir=d / "s", headless=False)
builtins.print = _orig_print

start_i = next(i for i, (_, l) in enumerate(timestamps) if l == "ACTION: validate_checked")
end_i = next(i for i, (_, l) in enumerate(timestamps[start_i:], start_i) if l == "ACTION: tab_close")
t_start, t_end = timestamps[start_i][0], timestamps[end_i][0]
print(f"\n=== STEP 5 (validate_checked) TIMING ===")
print(f"start (ACTION: validate_checked) -> next ACTION (tab_close): {t_end - t_start:.3f}s")
print("lines in between:")
for t, l in timestamps[start_i:end_i]:
    print(f"  +{t - t_start:.3f}s  {l}")

print("\n=== ALL STEP RESULTS ===")
for i, s in enumerate(res["steps"], 1):
    print(i, s.get("action_type"), "PASS" if s.get("success") else "FAIL", s.get("error"))
