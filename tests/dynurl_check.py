"""TEST-ONLY: Item B - generated ids in page addresses (generic local fixtures; no site value anywhere).
 B-1 a page creates a new random id in the address on every action (twice) -> PASS, the "expected on this site" note, ids mapped
 B-2 the replay lands on a different fixed path (error page)                 -> FAIL in plain English
 B-3 recording returns to the same id twice, replay gets a NEW id the 2nd time -> FAIL (mapping broken); a consistent site PASSES
 B-4 the search term in the address differs                                   -> FAIL
 B-5 an automatically saved Navigate to an old generated address is not opened -> PASS with the note when the structure matches
 B-6 a PASS step with the note shows the note in the live log
 plus the structural rules of the detector (words, short numbers, slugs are exact; ids are dynamic)"""
import json, subprocess, sys, time, urllib.request
from sidecheck_helpers import *

def clicks(pg, seq):
    for s in seq:
        pg.locator(s).click(); pg.wait_for_timeout(700)

def steps_text(res):
    return " || ".join(((s.get("warning") or "") + " " + (s.get("error") or "")) for s in res["steps"])

def notes(res):
    return [e["message"] for e in (res.get("live_log") or []) if "new id" in (e.get("message") or "")]

def first_bad(res, label):
    bad = [s for s in res["steps"] if not s["success"] and not s.get("not_run")]
    return bad, (step_headline(bad[0], label) if bad else "")

with FixtureServer() as fx:
    u = fx.url
    tc = record(u("sc_b_ids.html"), lambda pg: clicks(pg, ["#oa", "#ob", "#oa"]), "sc_b_ids")
    print("recorded:", [(a["action_type"], a.get("expected_url")) for a in tc["actions"]])

    print("== B-1 new random id on every action")
    two = json.loads(json.dumps(tc)); two["actions"] = two["actions"][:3]          # Open A, Open B
    res, _ = replay(swap(two, "sc_b_ids.html", "sc_b_ids.html?m=rand"), "b1")
    check("B-1 all steps PASS", all(s["success"] for s in res["steps"]), steps_text(res)[:200])
    n = notes(res)
    check("B-1 'expected on this site' note for each new address", len(n) >= 2 and all("expected on this site" in x for x in n), str(n))
    check("B-1 no technical text in the note", not any(TECH.search(x) for x in n))

    print("== B-2 replay lands on a different fixed path")
    res, _ = replay(swap(tc, "sc_b_ids.html", "sc_b_ids.html?m=err"), "b2")
    bad, head = first_bad(res, "Open A")
    print("   ", head[:240])
    check("B-2 FAILS in plain English naming the other page", bool(bad) and "/error" in head and "<id>" in head and not TECH.search(head.split("[details]")[0]), head[:200])

    print("== B-3 same recorded id twice, replay gives a different one the second time")
    res, _ = replay(swap(tc, "sc_b_ids.html", "sc_b_ids.html?m=rand"), "b3")
    bad, head = first_bad(res, "Open A")
    print("   ", [(s["index"], s["success"]) for s in res["steps"]], head[:240])
    check("B-3 the return to the first id FAILS (steps before it pass)", bool(bad) and bad[0]["index"] == 4 and "different id" in head, head[:200])
    res, _ = replay(swap(tc, "sc_b_ids.html", "sc_b_ids.html?m=salt"), "b3b")
    check("B-3 a site that gives the SAME new id on return PASSES", all(s["success"] for s in res["steps"]), steps_text(res)[:200])

    print("== B-4 search term differs")
    ts = record(u("sc_b_search.html"), lambda pg: (pg.locator("#q").click(), pg.keyboard.type("tamil", delay=30), pg.locator("#go").click(), pg.wait_for_timeout(700)), "sc_b_search")
    print("   recorded:", [(a["action_type"], a.get("expected_url"), a.get("value")) for a in ts["actions"]])
    res, _ = replay(ts, "b4ok")
    check("B-4 same term PASSES", all(s["success"] for s in res["steps"]), steps_text(res)[:200])
    res, _ = replay(swap(ts, "sc_b_search.html", "sc_b_search.html?m=other"), "b4")
    bad, head = first_bad(res, "Go")
    print("   ", head[:240])
    check("B-4 FAILS in plain English", bool(bad) and not TECH.search(head.split("[details]")[0]), head[:200])

    print("== B-5 automatic Navigate to an old generated address")
    nav = json.loads(json.dumps(tc)); acts = nav["actions"]
    old = acts[1]["expected_url"]
    acts.insert(2, {"action_type": "navigate", "page_url": old, "caused_by_timestamp": acts[1].get("timestamp"), "delay_before_ms": 30,
                    "timestamp": str(acts[1].get("timestamp")) + "x"})
    acts[1].pop("expected_url", None)                      # the click itself no longer carries it: the Navigate is the only check
    nav["actions"] = acts[:3]
    res, _ = replay(swap(nav, "sc_b_ids.html", "sc_b_ids.html?m=salt"), "b5")
    fin = res.get("final_url") or ""
    print("   ", [(s["index"], s["action_type"], s["success"]) for s in res["steps"]], fin)
    check("B-5 PASS (structure matches)", all(s["success"] for s in res["steps"]), steps_text(res)[:200])
    check("B-5 the old address was NOT opened", "a7k2m9x4q1" not in fin, fin)
    check("B-5 the note was shown", bool(notes(res)), str(notes(res)))
    res, _ = replay(swap(nav, "sc_b_ids.html", "sc_b_ids.html?m=login"), "b5f")
    bad, head = first_bad(res, "Open A")
    print("   ", head[:240], "| final:", res.get("final_url"))
    check("B-5 a different page FAILS in plain English, old address not opened", bool(bad) and "/login" in head and "a7k2m9x4q1" not in (res.get("final_url") or ""), head[:200])

    print("== B-6 the note is visible in the live log (real dashboard)")
    name = "_test_dynurl_b6"
    rec = swap(two, "sc_b_ids.html", "sc_b_ids.html?m=rand"); rec["name"] = name
    rp = BASE / "storage" / "recordings" / f"{name}.json"
    json.dump(rec, open(rp, "w", encoding="utf-8"))
    PORT = 5083
    srv = subprocess.Popen([sys.executable, "-c", f"import app; app.app.run(host='127.0.0.1', port={PORT}, threaded=True)"], cwd=BASE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/recordings", timeout=3); break
            except Exception: time.sleep(0.5)
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/test/run/start", json.dumps({"qa_url": rec["start_url"], "recording_path": f"storage/recordings/{name}.json"}).encode(), {"Content-Type": "application/json"})
            st = json.load(urllib.request.urlopen(req, timeout=60))
            pg = b.new_page(viewport={"width": 1100, "height": 900})
            pg.goto(f"http://127.0.0.1:{PORT}/logs?run_id={st['run_id']}")
            pg.wait_for_function("() => { const s = document.getElementById('summaryBanner'); return s && s.style.display === 'block'; }", timeout=300000)
            pg.wait_for_timeout(500)
            rows = pg.eval_on_selector_all("#logLines > *", "els => els.map(e => e.innerText.trim().replace(/\\s+/g, ' '))")
            b.close()
        for r in rows: print("    |", r[:150])
        nrows = [i for i, r in enumerate(rows) if "expected on this site" in r]
        check("B-6 the note is in the live log: one short line per new address", len(nrows) == 2 and all(len(rows[i]) < 140 for i in nrows), str(len(nrows)))
        check("B-6 each note comes right after its step line", all(i > 0 and "Step" in rows[i - 1] for i in nrows), str([rows[i - 1][:40] for i in nrows]))
        check("B-6 no sub-lines", not any("↳" in r for r in rows))
    finally:
        srv.terminate(); rp.unlink(missing_ok=True)

print("== detector")
spec = importlib.util.spec_from_file_location("dynmod", generate_script(tc, out_name="_dyn.py", output_dir=OUT)); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for s in ["3f2b8c1e-9d4a-4b7e-8c21-1a2b3c4d5e6f", "1234567890", "a1b2c3d4e5", "k3jd9xa2lm", "aGVsbG9Xb3JsZFRlc3Q", "deadbeef1234"]:
    check(f"dynamic: {s}", m._is_dynamic_url_segment(s))
for s in ["cart", "2", "2024", "python3", "version2024", "covid-19-update", "my-first-blog-post", "conversation", "login", "ConversationPage"]:
    check(f"exact (not dynamic): {s}", not m._is_dynamic_url_segment(s))

print("\nDYNURL:", "ALL PASS" if not fails else f"FAILED {fails}")
sys.exit(1 if fails else 0)
