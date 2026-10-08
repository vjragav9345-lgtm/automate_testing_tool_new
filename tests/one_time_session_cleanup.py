"""ONE-TIME cleanup (dashboard data): keep only the four named sessions and everything that belongs to them
(per storage/session_files.py's mapping); delete every other session's recordings, generated scripts and replay
run folders (screenshots + report.json/report.html). Dry-run unless --execute. The names below are used ONLY here."""
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from storage import session_files as sf  # noqa: E402

KEEP = [
    "session_20260928_170052_edited",
    "session_20260928_170352_edited",
    "session_20260928_171139_edited",
    "session_20260928_181934_edited",
]

keep = set()
for name in KEEP:
    found = sf.session_files(name)
    for kind in found:
        keep.update(p.resolve() for p in found[kind])

rec_dirs = (sf.RECORDINGS_DIR, sf.EDITED_RECORDINGS_DIR, sf.TRIMMED_RECORDINGS_DIR)
candidates = {"recordings": [], "scripts": [], "run_dirs": []}
for d in rec_dirs:
    candidates["recordings"] += [f for f in d.iterdir() if f.is_file()]
for d in (sf.SCRIPTS_DIR, sf.EDITED_SCRIPTS_DIR):
    # generated scripts only ("<name>_script.py"); other helper files that live in this folder are not session data
    candidates["scripts"] += [f for f in d.iterdir() if f.is_file() and ("_script.py" in f.name)]
candidates["run_dirs"] += list(sf.RUNS_DIR.iterdir())

to_delete = {k: [p for p in v if p.resolve() not in keep] for k, v in candidates.items()}
print("KEEP (per session):")
for name in KEEP:
    f = sf.session_files(name)
    print(f"  {name}: {len(f['recordings'])} recording file(s), {len(f['scripts'])} script(s), {len(f['run_dirs'])} run folder(s)")
for k, v in to_delete.items():
    print(f"delete {k}: {len(v)} of {len(candidates[k])}")
missing = [n for n in KEEP if not sf.session_files(n)["recordings"]]
assert not missing, f"kept session recordings not found: {missing}"

if "--execute" not in sys.argv:
    print("\n(dry run - nothing deleted; pass --execute)")
    sys.exit(0)

errors = []
for kind, paths in to_delete.items():
    for p in paths:
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
        except OSError as e:
            errors.append(f"{p}: {e}")
print("\nDELETED. errors:", errors)
