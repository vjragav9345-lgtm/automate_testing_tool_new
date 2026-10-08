"""TEST-ONLY: replay a recording through the real dashboard endpoints of a server (port arg) and print the outcome + marker lines."""
import json, sys, time, urllib.request
from pathlib import Path
port, name = sys.argv[1], sys.argv[2]
rec = json.load(open(f"storage/recordings/{name}.json", encoding="utf-8"))
def post(u, b):
    r = urllib.request.Request(u, json.dumps(b).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))
def get(u): return json.load(urllib.request.urlopen(u, timeout=60))
base = f"http://127.0.0.1:{port}"
st = post(base + "/api/test/run/start", {"qa_url": rec["start_url"], "recording_path": f"storage/recordings/{name}.json"})
print("started", st.get("run_id"), st.get("run_dir"))
rid = st["run_id"]
for _ in range(240):
    pr = get(f"{base}/api/test/run/progress?run_id={rid}")
    if pr.get("done"): break
    time.sleep(2)
print("done:", pr.get("status"), pr.get("message"))
for i, s in enumerate(pr.get("steps") or [], 1):
    print(i, s.get("success"), s.get("action_type"), (s.get("error") or "")[:150])
json.dump(pr, open(f"tests/_probe_out/proof_{name}_{port}.json", "w"), indent=1, default=str)
print("run_dir", pr.get("run_dir") or st.get("run_dir"))
