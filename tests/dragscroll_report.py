"""TEST-ONLY: consolidated manual-vs-replay evidence for one recording.

    venv/Scripts/python.exe tests/dragscroll_report.py <recording.json> <probe_result.json> <probe.log> [--manual manual_log.json] [--tol 5]

Prints
  * overall pass / fail / not_run
  * every DRAG: recorded value (at release) vs replay value at release (+ nudges), replay value after the
    site settled, and (when a manual log exists) the value the person SAW settled after the manual drag
  * every SCROLL: manual position (recorded scroll_y_after) vs replay position at the end of that step
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ap = argparse.ArgumentParser()
ap.add_argument("recording"); ap.add_argument("probe"); ap.add_argument("log")
ap.add_argument("--manual", default=None); ap.add_argument("--tol", type=float, default=5.0)
ap.add_argument("--quiet-scrolls", action="store_true", help="only print scroll mismatches, not every scroll")
a = ap.parse_args()

rec = json.loads(Path(a.recording).read_text(encoding="utf-8"))["actions"]
pr = json.loads(Path(a.probe).read_text(encoding="utf-8"))
log = Path(a.log).read_text(encoding="utf-8", errors="replace")
manual = json.loads(Path(a.manual).read_text(encoding="utf-8")) if a.manual else []
steps = {s["index"]: s for s in pr["steps"]}
total = len(rec) + (0)
parts = re.split(r"\n\[(\d+)/(\d+)\]\n", log)
seg = {int(parts[k]): parts[k + 2] for k in range(1, len(parts) - 2, 3)}
sp = pr.get("step_pages", {})


def path(u):
    try:
        return urlsplit(u).path
    except Exception:
        return u


npass = sum(1 for s in pr["steps"] if s["success"])
nfail = sum(1 for s in pr["steps"] if not s["success"] and not s.get("not_run"))
nnr = sum(1 for s in pr["steps"] if s.get("not_run"))
print(f"RESULT: {len(pr['steps'])} steps -> {npass} pass / {nfail} FAILED / {nnr} NOT RUN")
for s in pr["steps"]:
    if not s["success"] and not s.get("not_run"):
        print(f"   FAILED step {s['index']} ({s['action_type']}): {(s['error'] or '')[:170]}")

print("\nDRAGS (manual vs replay)")
m_drags = [m for m in manual if m.get("kind") == "drag"]
k = 0
drag_bad = 0
for i, x in enumerate(rec, start=1):
    if x["action_type"] != "drag":
        continue
    s = seg.get(i, "")
    held = re.search(r"\[drag-verify\] value at release matches recorded (.*?) \(held=(\w+), nudges=(\d+)\); after settle it reads (.*)", s)
    old = re.search(r"\[drag-verify\] value_target reads (.*?) \(matches recorded\)", s)
    rec_val = (x.get("value_after") or {}).get("value") or (x.get("value_after") or {}).get("text")
    rv = held.group(1) if held else (old.group(1) if old else None)
    nud = held.group(3) if held else "-"
    after_settle = held.group(4) if held else (old.group(1) if old else None)
    nudge_lines = len(re.findall(r"^\[drag\] nudge", s, re.M))
    man = None
    if k < len(m_drags):
        mv = m_drags[k].get("settled_value") or {}
        man = mv.get("value") if mv.get("kind") != "nearby_text" else mv.get("value")
    k += 1
    ok = steps.get(i, {}).get("success")
    if not ok:
        drag_bad += 1
    print(f"  step {i:3d}: recorded@release={rec_val!s:>22} | replay@release={'(see below)' if rv is None else 'MATCH'} nudges={nud} "
          f"| replay settled={str(after_settle)[:60]} | manual settled={man!s:>22} | step {'PASS' if ok else ('NOT RUN' if steps.get(i,{}).get('not_run') else 'FAILED')}")
print(f"  drags failing: {drag_bad}")

print("\nSCROLLS (manual scroll_y_after vs replay position at end of step)")
bad = tot = 0
for i, x in enumerate(rec, start=1):
    if x["action_type"] != "scroll":
        continue
    m = x.get("scroll_y_after")
    pages = sp.get(str(i)) or []
    cand = [p for p in pages if path(p["url"]) == path(x.get("page_url", "")) and p.get("pos")]
    r = cand[-1]["pos"][1] if cand else None
    if steps.get(i, {}).get("not_run") or r is None or m is None:
        continue
    tot += 1
    d = round(r - m, 1)
    flag = abs(d) > a.tol
    bad += 1 if flag else 0
    if flag or not a.quiet_scrolls:
        print(f"  step {i:3d}: manual={m:9.1f} replay={r:9.1f} diff={d:6.1f} {'<<< MISMATCH' if flag else ''}")
print(f"  scroll steps compared: {tot}   mismatches (>{a.tol}px): {bad}")

wheel = sum(1 for e in pr.get("events", []) if e["kind"] == "mouse.wheel" and rec[e["step"] - 1]["action_type"] != "scroll" if 1 <= e["step"] <= len(rec))
print(f"\nmouse.wheel events fired during NON-scroll steps (unwanted scrolling): {wheel}")
