"""TEST-ONLY: compares a recording's manual scroll/drag data with a probe result.
    venv/Scripts/python.exe tests/dragscroll_compare.py <recording.json> <probe_result.json> [--log probe.log]
For every step it prints manual scroll position (recorded) vs replay scroll position at END of step
on the tab whose URL path matches the recording, and for drags the recorded value vs replay readings.
"""
import argparse, json, re, sys
from pathlib import Path
from urllib.parse import urlsplit

ap = argparse.ArgumentParser()
ap.add_argument("recording"); ap.add_argument("probe"); ap.add_argument("--log", default=None)
ap.add_argument("--tol", type=float, default=5.0)
a = ap.parse_args()
rec = json.loads(Path(a.recording).read_text(encoding="utf-8"))["actions"]
pr = json.loads(Path(a.probe).read_text(encoding="utf-8"))
sp = pr.get("step_pages", {})
steps = {s["index"]: s for s in pr["steps"]}

def path(u): 
    try: return urlsplit(u).path
    except Exception: return u

def manual_end_pos(i):
    """manual scroll position at END of step i == position recorded at the START of the next action
    on the same page_id (scroll_y for non-scroll, scroll_y_before for scroll), or scroll_y_after if step i is a scroll."""
    x = rec[i-1]
    if x["action_type"] == "scroll": return x.get("scroll_y_after")
    for j in range(i, len(rec)):
        y = rec[j]
        if y.get("page_id", 0) != x.get("page_id", 0): continue
        v = y.get("scroll_y_before") if y["action_type"] == "scroll" else y.get("scroll_y")
        if v is not None: return v
    return None

bad = 0; checked = 0; info = 0
print("step type        | manual_end | replay_end | diff | note")
for i, x in enumerate(rec, start=1):
    m = manual_end_pos(i)
    pages = sp.get(str(i)) or []
    cand = [p for p in pages if path(p["url"]) == path(x.get("page_url", "")) and p.get("pos")]
    # a navigate/tab_open changes the page: match the NEXT action's url instead
    if x["action_type"] in ("navigate", "tab_open", "tab_close"):
        continue
    r = cand[-1]["pos"][1] if cand else None
    if m is None or r is None:
        continue
    checked += 1
    d = round(r - m, 1)
    flag = "" if abs(d) <= a.tol else "  <<< MISMATCH"
    if flag: bad += 1
    if x["action_type"] != "scroll":
        info += 1 if flag else 0
        continue
    if True:
        print(f"{i:3d} {x['action_type']:11s}| {m:10.1f} | {r:10.1f} | {d:6.1f}{flag} | {'not_run' if steps.get(i,{}).get('not_run') else ('ok' if steps.get(i,{}).get('success') else 'FAILED')}")
print(f"\nchecked={checked}  mismatches(>{a.tol}px)={bad}")
if a.log:
    t = Path(a.log).read_text(encoding="utf-8", errors="replace")
    print("\n[drag-verify]/[drag-] lines in log:")
    for l in t.splitlines():
        if l.startswith("[drag") : print("  ", l[:230])
for i, x in enumerate(rec, start=1):
    if x["action_type"] == "drag":
        print(f"\nDRAG step {i}: recorded value_before={x.get('value_before')} value_after={x.get('value_after')}  replay_result={steps.get(i,{}).get('success')} {(steps.get(i,{}).get('error') or '')[:160]}")
