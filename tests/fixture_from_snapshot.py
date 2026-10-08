"""RC4 (real DOM evidence for the future): turns a DOM snapshot saved
during recording (storage/snapshots/<session_id>/<timestamp>.html,
written by recorder/record_session.py's _capture_dom_snapshot on every
navigate) into a standalone local fixture file under tests/fixtures/, so
a real recorded site's actual markup at that moment can be replayed
against offline/locally - via phase4_fixture_server.FixtureServer, the
same way every other tests/fixtures/phase4_*.html fixture already is -
instead of only ever being re-testable against the live site, which may
have changed or become unreachable by the time a fix needs re-checking.

Usage:
    python tests/fixture_from_snapshot.py <snapshot.html path>
    python tests/fixture_from_snapshot.py <session_id> [--step N] [--out NAME]

Given a bare session_id, --step selects which navigate's snapshot to use
(1-based, counted only among navigate actions that actually saved one -
a navigate recorded before this feature existed has no snapshot and is
skipped); omitting --step uses the last one, typically the page's final,
most "settled" state. The session's own storage/recordings/session_*.json
already carries the step<->snapshot-file mapping (matched by timestamp,
the same value record_session.py names each snapshot file after), so no
separate index file is needed.
"""
import argparse
import gzip
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = BASE_DIR / "storage" / "snapshots"
RECORDINGS_DIR = BASE_DIR / "storage" / "recordings"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _find_recording_for_session(session_id):
    for path in RECORDINGS_DIR.glob("session_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("session_id") == session_id:
            return data
    return None


def _resolve_snapshot(ref, step=None):
    direct = Path(ref)
    if direct.suffix in (".html", ".gz") and direct.exists():
        return direct, None

    session_dir = SNAPSHOTS_DIR / ref
    if not session_dir.is_dir():
        raise SystemExit(f"no snapshot file or session found for {ref!r} (checked {session_dir})")

    recording = _find_recording_for_session(ref)
    navs_with_snapshot = []
    if recording:
        for i, action in enumerate(recording.get("actions", []), start=1):
            if action.get("action_type") == "navigate" and action.get("dom_snapshot_path"):
                navs_with_snapshot.append((i, action))

    if navs_with_snapshot:
        idx = step if step is not None else navs_with_snapshot[-1][0]
        match = next((a for (i, a) in navs_with_snapshot if i == idx), None)
        if match is None:
            raise SystemExit(
                f"step {idx} is not a navigate step with a saved snapshot; "
                f"steps with a snapshot: {[i for i, _ in navs_with_snapshot]}"
            )
        return BASE_DIR / match["dom_snapshot_path"], match

    # recording JSON missing/unmatched (e.g. deleted after recording) -
    # fall back to picking straight out of the session's own snapshot
    # folder, in filename order (filenames are timestamps, so this is
    # also chronological order)
    files = sorted(session_dir.glob("*.html")) + sorted(session_dir.glob("*.html.gz"))
    if not files:
        raise SystemExit(f"no .html/.html.gz snapshots found under {session_dir}")
    idx = (step - 1) if step else -1
    try:
        return files[idx], None
    except IndexError:
        raise SystemExit(f"step {step} out of range (found {len(files)} snapshots)")


def build_fixture(ref, step=None, out_name=None):
    snapshot_path, action = _resolve_snapshot(ref, step)
    if not snapshot_path.exists():
        raise SystemExit(f"snapshot file not found: {snapshot_path}")

    # FIX 5 (scale): snapshots are gzip-compressed on disk (.html.gz) -
    # older snapshots saved before this existed are still plain .html and
    # read the same as before.
    if snapshot_path.suffix == ".gz":
        html = gzip.decompress(snapshot_path.read_bytes()).decode("utf-8", errors="replace")
    else:
        html = snapshot_path.read_text(encoding="utf-8")

    out_name = out_name or f"from_snapshot_{snapshot_path.stem}"
    if not out_name.endswith(".html"):
        out_name += ".html"
    out_path = FIXTURES_DIR / out_name
    out_path.write_text(html, encoding="utf-8")

    print(f"Wrote fixture: {out_path}")
    if action:
        print(f"  captured from {action.get('page_url')} at timestamp {action.get('timestamp')}")
    print(
        "Note: this is the page's raw markup exactly as captured - "
        "relative/absolute resource URLs (images, CSS, JS) still point "
        "at the ORIGINAL site's domain, so anything depending on those "
        "won't load offline. Meant for locator/DOM-shape testing "
        "(reproducing a recorder/replay bug against the real markup), "
        "not a pixel-perfect offline mirror of the live page."
    )
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ref", help="a snapshot .html file path, or a session_id to pick one from")
    parser.add_argument("--step", type=int, default=None, help="which navigate step's snapshot to use (1-based); default: the last one")
    parser.add_argument("--out", default=None, help="output fixture filename (default: from_snapshot_<timestamp>.html)")
    args = parser.parse_args()
    build_fixture(args.ref, step=args.step, out_name=args.out)


if __name__ == "__main__":
    main()
