"""TEST-ONLY: replays one recording through the real dashboard endpoints of a
running server (port arg) and prints the Live Log SSE stream exactly as the
live-log popup receives it, each line prefixed with the second it ARRIVED -
so a step that shows 'running' for longer than the step really takes (the
old lag) is visible, and so are the new sub-phases, start/end stamps, the
WARNING lines and the final summary.

    python tests/warning_live_run.py 5055 session_20261001_105105
"""
import json
import sys
import time
import urllib.request
from datetime import datetime

port, name = sys.argv[1], sys.argv[2]
rec = json.load(open(f"storage/recordings/{name}.json", encoding="utf-8"))
base = f"http://127.0.0.1:{port}"


def post(u, b):
    r = urllib.request.Request(u, json.dumps(b).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))


st = post(base + "/api/test/run/start", {"qa_url": rec["start_url"], "recording_path": f"storage/recordings/{name}.json"})
rid = st["run_id"]
print("started", rid, "run_dir", st.get("run_dir"))
t0 = time.monotonic()
last_running = None
event = None
with urllib.request.urlopen(f"{base}/api/test/run/stream?run_id={rid}", timeout=900) as resp:
    for raw in resp:
        line = raw.decode("utf-8", "replace").rstrip("\n")
        if line.startswith("event:"):
            event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        data = json.loads(line[5:])
        at = f"[+{time.monotonic() - t0:6.1f}s]"
        if event == "running":
            key = (data.get("index"), data.get("phase"))
            if key != last_running:
                last_running = key
                print(f"{at} RUNNING Step {data['index']} ({data.get('action_type')}) "
                      f"phase={data.get('phase')} started_at={data.get('started_at')}")
        elif event == "step":
            # live-log latency: how long after the step ENDED did its line reach the client
            # (same wall clock as ended_at: the replay subprocess runs on this machine)
            try:
                lat = (datetime.now() - datetime.fromisoformat(data["ended_at"])).total_seconds() * 1000
                lat_txt = f" log_latency={lat:.0f}ms"
            except Exception:
                lat_txt = ""
            print(f"{at} Step {data['index']} {data['action_type']} - {data['status'].upper()}  "
                  f"started={data.get('started_at')} ended={data.get('ended_at')} duration={data.get('duration')}s{lat_txt}")
            r = data.get("reason") or {}
            if r.get("plain"):
                print(f"           {r['plain']}")
        elif event == "step_note":
            print(f"{at}   note step {data['index']}: {data.get('phase')}")
        elif event == "step_update":
            print(f"{at}   update step {data['index']}: status={data['status']} screenshot={data.get('screenshot')}")
        elif event == "log":
            print(f"{at}   log: {data.get('message')}")
        elif event == "summary":
            print(f"{at} SUMMARY {data.get('status')} - {data.get('message')}")
            print(f"           Total {data['total_steps']}  Passed {data['passed']}  Warnings {data['warnings']}  "
                  f"Failed {data['failed']}  Skipped {data['skipped']}  Duration {data['duration_s']}s")
            print(f"           {data.get('plain_summary')}")
            break
        elif event == "stream_error":
            print(f"{at} STREAM ERROR {data}")
            break
