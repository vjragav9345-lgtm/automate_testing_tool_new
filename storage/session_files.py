"""The ONE place that knows which files on disk belong to a recorded session.

A session is identified by its recording name. Everything derived from it is
found the same way the code that WRITES it names it (nothing here is a
guessed layout):

  recordings   storage/recordings/<name>.json, storage/recordings/edited/
               and storage/recordings/trimmed/ (repository.save_recording /
               save_edited_recording), plus an interrupted atomic write's
               leftover "<name>.json.tmp<pid>" (repository._write_json)
  scripts      generated_scripts/<name>_script.py and
               generated_scripts/edited/<name>_script.py
               (generator.script_generator.generate_script's default name and
               OUTPUT_DIR / EDITED_OUTPUT_DIR), plus a leftover
               "<name>_script.py.tmp<pid>"
  run folders  generated_scripts/screenshoots/<slug(name)>_<YYYYmmdd_HHMMSS>/
               (executor.run_execution._prepare_run) - each holds that
               replay's screenshots, report.json and report.html

Run-folder matching is exact (slug + "_" + a timestamp, nothing else), never
a bare prefix: "session_X" must not claim "session_X_edited"'s runs. A name
so long that its slug hit the slug's length cap can't be matched reliably
(two names could share that prefix), so it owns no run folders here rather
than risk another session's.

Used by the dashboard's per-session Delete and Screenshots actions
(app.py) and by one-off data cleanups - see session_files() /
delete_session().
"""
import re
import shutil

from storage.repository import (
    BASE_DIR,
    RECORDINGS_DIR,
    EDITED_RECORDINGS_DIR,
    TRIMMED_RECORDINGS_DIR,
)

SCRIPTS_DIR = BASE_DIR / "generated_scripts"
EDITED_SCRIPTS_DIR = SCRIPTS_DIR / "edited"
RUNS_DIR = SCRIPTS_DIR / "screenshoots"

_RUN_TS_RE = re.compile(r"\d{8}_\d{6}")
_SLUG_MAX_LEN = 40  # executor.run_execution._slug's max_len for run folder names


def _run_slug(name):
    from executor.run_execution import _slug  # the function that builds the run id
    return _slug(name, _SLUG_MAX_LEN)


def _dir_children(directory):
    try:
        return list(directory.iterdir())
    except OSError:
        return []


def is_run_folder_of(name, folder_name):
    """True when `folder_name` is a replay run folder of the session `name`."""
    slug = _run_slug(name)
    if not slug or len(slug) >= _SLUG_MAX_LEN:
        return False
    folder_name = folder_name.lower()
    prefix = slug + "_"
    return folder_name.startswith(prefix) and bool(_RUN_TS_RE.fullmatch(folder_name[len(prefix):]))


def session_files(name):
    """Every existing file/folder that belongs to session `name`:
    {"recordings": [Path], "scripts": [Path], "run_dirs": [Path]}."""
    rec_re = re.compile(re.escape(name) + r"\.json(\.tmp\d+)?")
    script_re = re.compile(re.escape(name) + r"_script\.py(\.tmp\d+)?")

    recordings = [
        f for d in (RECORDINGS_DIR, EDITED_RECORDINGS_DIR, TRIMMED_RECORDINGS_DIR)
        for f in _dir_children(d) if f.is_file() and rec_re.fullmatch(f.name)
    ]
    scripts = [
        f for d in (SCRIPTS_DIR, EDITED_SCRIPTS_DIR)
        for f in _dir_children(d) if f.is_file() and script_re.fullmatch(f.name)
    ]
    run_dirs = [d for d in _dir_children(RUNS_DIR) if d.is_dir() and is_run_folder_of(name, d.name)]
    return {"recordings": recordings, "scripts": scripts, "run_dirs": run_dirs}


def delete_session(name):
    """Deletes everything session_files(name) finds. Returns the deleted
    paths grouped the same way (plus "errors" for anything that couldn't go)."""
    found = session_files(name)
    deleted = {"recordings": [], "scripts": [], "run_dirs": [], "errors": []}
    for kind in ("recordings", "scripts", "run_dirs"):
        for path in found[kind]:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                deleted[kind].append(path)
            except OSError as e:
                deleted["errors"].append(f"{path}: {e}")
    # the session's page snapshots (Pick Element): storage/snapshots/<name>/
    try:
        from recorder.page_snapshot import delete_snapshots
        removed = delete_snapshots(name)
        if removed is not None:
            deleted.setdefault("snapshots", []).append(removed)
    except OSError as e:
        deleted["errors"].append(f"snapshots of {name}: {e}")
    except Exception:
        pass
    return deleted
