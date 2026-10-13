"""TEST-ONLY: drives the REAL recorder.pick_element session (fresh path, same slice as app.py's pick_element/start) for
'Add Action After Step N' on a recording, then asks the picker's own thread (via its test-drive queue) which pages exist
and which one the picker overlay is on.   usage: pick_prefix_probe.py <recording.json> <N: step number to add after>"""
import json, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import recorder.pick_element as pe

rec_path, n = sys.argv[1], int(sys.argv[2])
rec = json.loads(Path(rec_path).read_text(encoding="utf-8"))
actions = rec["actions"]
preceding = actions[:max(0, min((n - 1) + 1, len(actions)))]     # app.py: insert_after_index = N-1 (0-based), slice_end = index+1
print(f"[probe] recording={Path(rec_path).name} add-after-step={n} -> replaying {len(preceding)} step(s):",
      [a["action_type"] for a in preceding], flush=True)
pick_id = pe.start_pick_session(rec["start_url"], preceding)
out = {}
def drive(browser, context):
    info = []
    for p in context.pages:
        try:
            info.append({"url": p.url, "picker_injected": bool(p.evaluate("!!window.__afqaPickMode"))})
        except Exception as e:
            info.append({"url": p.url, "picker_injected": f"err {e}"[:60]})
    out["pages"] = info
    browser.close()
pe._TEST_DRIVE_QUEUE.put(drive)
deadline = time.time() + 240
while time.time() < deadline and "pages" not in out:
    time.sleep(0.5)
time.sleep(1)
st = pe._PICK_RESULTS.get(pick_id) or {}
print("[probe] pages at picker time:", json.dumps(out.get("pages"), indent=1))
print("[probe] status:", {k: st.get(k) for k in ("status", "page_url_check", "content_mismatch")})
