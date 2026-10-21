"""Configurable-age cleanup for the directories this project accumulates
files in over time: recordings, generated scripts, replay run folders
(screenshots + reports), the top-level launch-screenshot folder, and the
shared reports/ fallback.

Deliberately NOT a background scheduler (no cron/APScheduler) - this
project explicitly doesn't want that kind of always-on infra. Cleanup
runs only when something calls run_cleanup() (see app.py's
/api/maintenance/cleanup route), with dry_run=True as the safe default
so a human reviews what WOULD be removed before anything actually is.

Safety rules, all enforced here rather than left to the caller:
  - age-based only, using each item's own mtime against RETENTION_DAYS -
    nothing younger than the configured window is ever touched, and
    there's no other basis (name, "looks unused", ...) for removing
    something
  - an item currently in use is skipped regardless of age: a recording
    with an active recording session in progress, or ANY file under a
    run folder that a currently in-flight replay (see executor/
    run_execution.py's own _active_replays registry) is still writing to
  - every candidate path is verified to actually resolve inside one of
    the configured target directories before any removal - never
    touches anything else, even if a bug elsewhere fed this a bad path
  - a missing/already-gone file is logged and skipped, never an error
    that aborts the rest of the sweep
  - archive mode (the default) moves matched items under retention_archive/
    instead of deleting them outright, so "cleanup" is recoverable by
    default; delete mode removes them for good. Both are logged per item.
"""
import logging
import shutil
import time
from pathlib import Path

from storage.repository import BASE_DIR

logger = logging.getLogger(__name__)

# overridable per call, but this is the documented default the feature
# was specified with
RETENTION_DAYS = 30

ARCHIVE_DIR = BASE_DIR / "retention_archive"

# (label, directory, glob pattern, recursive) - recursive=False means
# "list this directory's own direct children" (used for run-folders,
# stage-subfolders, dated screenshot folders - the natural unit is one
# whole folder, not each file inside it); recursive=True means "match
# this glob anywhere under the directory" (used for flat collections of
# individual files, e.g. every recording).
_TARGETS = (
    ("recordings", BASE_DIR / "storage" / "recordings", "*.json", False),
    ("recordings-edited", BASE_DIR / "storage" / "recordings" / "edited", "*.json", False),
    ("recordings-trimmed", BASE_DIR / "storage" / "recordings" / "trimmed", "*.json", False),
    ("generated-scripts", BASE_DIR / "generated_scripts", "*.py", False),
    ("generated-scripts-edited", BASE_DIR / "generated_scripts" / "edited", "*.py", False),
    ("fill-diagnostics", BASE_DIR / "generated_scripts" / "fill_diagnostics", "*.png", False),
    ("replay-runs", BASE_DIR / "generated_scripts" / "screenshoots", "*", False),
    ("launch-screenshots", BASE_DIR / "screenshots", "*", False),
    ("reports", BASE_DIR / "reports", "*.html", False),
)


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except (ValueError, OSError):
        return False


def _active_run_dirs():
    """Run folders a currently in-flight replay is still writing to -
    imported lazily (not at module load) so this module has no import-
    time dependency on executor/run_execution.py, and a circular-import
    or executor-unavailable situation can never break retention sweeps
    for everything else.
    """
    try:
        from executor.run_execution import _active_replays, _active_replays_lock
    except Exception:
        return set()
    try:
        with _active_replays_lock:
            return {
                str(Path(entry["run_dir"]).resolve())
                for entry in _active_replays.values()
                if not entry.get("done") and entry.get("run_dir")
            }
    except Exception:
        return set()


def _recording_active():
    """True while a recording session is actually in progress - imported
    lazily for the same reason as _active_run_dirs above.

    Read from the app module that is actually RUNNING: started as
    `python app.py` that module is __main__, and `import app` would load a
    second, separate copy of app.py whose session_state never records
    anything (so a live recording always looked inactive)."""
    import sys
    app_module = next(
        (m for m in (sys.modules.get("__main__"), sys.modules.get("app"))
         if m is not None and hasattr(m, "session_state") and hasattr(m, "state_lock")),
        None,
    )
    if app_module is None:
        return False
    session_state, state_lock = app_module.session_state, app_module.state_lock
    try:
        with state_lock:
            return bool(session_state.get("active"))
    except Exception:
        return False


def _age_days(path: Path, now: float) -> float:
    return (now - path.stat().st_mtime) / 86400.0


def preview_cleanup(retention_days=RETENTION_DAYS):
    """Read-only: returns what run_cleanup(dry_run=True) would report,
    without needing a separate call shape - same function, just named for
    the common "just show me" case.
    """
    return run_cleanup(retention_days=retention_days, dry_run=True)


def run_cleanup(retention_days=RETENTION_DAYS, dry_run=True, mode="archive"):
    """Sweeps every configured target directory for items older than
    retention_days and either archives (mode="archive", the default) or
    deletes (mode="delete") them - or, with dry_run=True (the default),
    just reports what would happen without touching anything.

    Returns {"dry_run", "mode", "retention_days", "items": [...],
    "archived": N, "deleted": N, "skipped": N, "errors": [...]} - one
    entry per item actually matched (whether or not dry_run skipped the
    real action), so the caller can show a full preview either way.
    """
    if mode not in ("archive", "delete"):
        raise ValueError(f"mode must be 'archive' or 'delete', got {mode!r}")

    now = time.time()
    active_run_dirs = _active_run_dirs()
    recording_in_progress = _recording_active()

    items = []
    archived_count = 0
    deleted_count = 0
    skipped_count = 0
    errors = []

    for label, directory, pattern, recursive in _TARGETS:
        try:
            if not directory.exists():
                continue
            directory = directory.resolve()
        except OSError as e:
            errors.append(f"{label}: couldn't access {directory}: {e}")
            continue

        glob_fn = directory.rglob if recursive else directory.glob
        try:
            candidates = sorted(glob_fn(pattern))
        except OSError as e:
            errors.append(f"{label}: couldn't list {directory}: {e}")
            continue

        for candidate in candidates:
            try:
                if not candidate.exists():
                    # gone between listing and now (another process
                    # already removed it, a race with a real run) -
                    # nothing wrong, just nothing to do
                    continue

                if not _is_within(candidate, directory):
                    # defensive only - glob() against a resolved
                    # directory can't actually produce this, but a
                    # removal is never issued against a path that
                    # hasn't been proven to live inside a configured
                    # target directory, no exceptions
                    errors.append(f"{label}: {candidate} resolved outside its target directory - skipped")
                    continue

                age_days = _age_days(candidate, now)
                if age_days < retention_days:
                    continue

                # safety: never touch a recording while a recording
                # session is actually in progress - it may be the file
                # about to be written, or one the user is mid-review of
                if label.startswith("recordings") and recording_in_progress:
                    skipped_count += 1
                    items.append({"label": label, "path": str(candidate), "age_days": round(age_days, 1), "action": "skipped-recording-active"})
                    continue

                # safety: never touch a run folder a currently in-flight
                # replay is still writing to
                if label == "replay-runs" and str(candidate) in active_run_dirs:
                    skipped_count += 1
                    items.append({"label": label, "path": str(candidate), "age_days": round(age_days, 1), "action": "skipped-run-active"})
                    continue

                action = "would-" + mode
                if not dry_run:
                    if mode == "delete":
                        if candidate.is_dir():
                            shutil.rmtree(candidate)
                        else:
                            candidate.unlink()
                        deleted_count += 1
                        action = "deleted"
                    else:
                        dest_dir = ARCHIVE_DIR / label
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest = dest_dir / candidate.name
                        if dest.exists():
                            dest = dest_dir / f"{candidate.stem}_{int(now)}{candidate.suffix}"
                        shutil.move(str(candidate), str(dest))
                        archived_count += 1
                        action = "archived"

                logger.info(
                    "retention: %s %s (%s, %.1f days old)%s",
                    action, candidate, label, age_days,
                    "" if not dry_run else " [dry run]",
                )
                items.append({"label": label, "path": str(candidate), "age_days": round(age_days, 1), "action": action})

            except OSError as e:
                logger.warning("retention: couldn't process %s: %s", candidate, e)
                errors.append(f"{label}: {candidate}: {e}")

    return {
        "dry_run": dry_run,
        "mode": mode,
        "retention_days": retention_days,
        "items": items,
        "archived": archived_count,
        "deleted": deleted_count,
        "skipped": skipped_count,
        "errors": errors,
    }
