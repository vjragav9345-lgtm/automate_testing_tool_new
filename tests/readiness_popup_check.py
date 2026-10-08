"""TEST-ONLY: page readiness before a step, Enter / send result check, popups the site opens by itself
(generic local fixtures; no site value anywhere).
 C-1 chat-like page streams an answer 4s and ignores Enter meanwhile; 4 questions recorded waiting for each answer -> replay all PASS, every message sent
 C-2 same recording, readiness wait switched off (test only) -> the Enter during streaming FAILS: "nothing was sent"
 C-3 live search whose results load after a delay; next step clicks a result -> PASS
 C-4 form whose submit button stays disabled during async validation -> PASS
 C-5 popup the site opened by itself (recorded), not shown in replay -> popup steps skipped with the note, run PASS
 C-6 same page, popup shown in replay -> closed with its X, run PASS
 C-7 popup shown in replay only, blocks the next step -> closed, note, run PASS
 C-8 popup opened by a user click that does not open in replay -> still FAILS
 C-9 input re-rendered (new element, new label) after the first send -> second click PASS"""
import os
from sidecheck_helpers import *

def wait_idle(pg):
    pg.wait_for_function("() => document.getElementById('status').textContent === 'idle'", timeout=30000)
    pg.wait_for_timeout(300)

def replay_env(tc, label, env=None):
    old = {k: os.environ.get(k) for k in (env or {})}
    os.environ.update(env or {})
    try:
        return replay(tc, label)
    finally:
        for k, v in old.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v

def bad_steps(res): return [s for s in res["steps"] if not s["success"] and not s.get("not_run")]
def allpass(res): return all(s["success"] for s in res["steps"])
def sig(res): return "".join("P" if s["success"] else ("n" if s.get("not_run") else "F") for s in res["steps"])
def notes(res, word): return [e["message"] for e in (res.get("live_log") or []) if word in (e.get("message") or "")]
def center(loc):
    b = loc.bounding_box(); return int(b["x"] + b["width"] / 2), int(b["y"] + b["height"] / 2)

only = sys.argv[1:]
def want(tag): return not only or tag in only

with FixtureServer() as fx:
    u = fx.url
    if want("C1") or want("C2"):
        print("== C-1 / C-2 chat that streams")
        def chat(pg):
            for qn in ("first question", "second question", "third question", "fourth question"):
                pg.locator("#box").click(); pg.keyboard.type(qn, delay=25); pg.keyboard.press("Enter"); wait_idle(pg)
            pg.wait_for_timeout(600)
        tcc = record(u("sc_c_chat.html?s=4"), chat, "sc_c_chat")
        print("   recorded:", [a["action_type"] for a in tcc["actions"]])
        res, _ = replay(tcc, "c1")
        print("   sig:", sig(res), "| waits:", notes(res, "Waited"))
        sent = (res.get("final_text") or "").count("You: ")
        check("C-1 all steps PASS", allpass(res), sig(res))
        check("C-1 every question was really sent (4 messages on the page)", sent == 4, f"sent={sent}")
        def chat2(pg):
            for qn in ("first question", "second question"):
                pg.locator("#box").click(); pg.keyboard.type(qn, delay=25); pg.keyboard.press("Enter"); wait_idle(pg)
                pg.wait_for_timeout(600)
        tcc2 = record(u("sc_c_chat.html?s=10"), chat2, "sc_c_chat2")
        res, _ = replay_env(tcc2, "c2", {"AUTOFLOW_READINESS_WAIT": "0"})
        bad = bad_steps(res); head = step_headline(bad[0], "Message box") if bad else ""
        print("   sig:", sig(res), "|", head[:200])
        check("C-2 Enter during streaming FAILS: nothing was sent", bool(bad) and "nothing was sent" in head and "text is still in the box" in head and not TECH.search(head.split("[details]")[0]), head[:160])

    if want("C3"):
        print("== C-3 live search")
        def search(pg):
            pg.locator("#q").click(); pg.keyboard.type("tamil", delay=30)
            pg.wait_for_function("() => document.getElementById('res').innerText.indexOf('Results for') === 0", timeout=10000)
            pg.wait_for_timeout(300); pg.get_by_role("button", name="Result one").click(); pg.wait_for_timeout(500)
        tcs = record(u("sc_c_search.html"), search, "sc_c_search")
        res, _ = replay(tcs, "c3")
        print("   sig:", sig(res), "| waits:", notes(res, "Waited"))
        check("C-3 PASS and the result was really picked", allpass(res) and "picked Result one" in (res.get("final_text") or ""), sig(res))

    if want("C4"):
        print("== C-4 submit disabled during async validation")
        def form(pg):
            pg.locator("#em").click(); pg.keyboard.type("ann@example.test", delay=30)
            pg.wait_for_function("() => !document.getElementById('go').disabled", timeout=10000)
            pg.locator("#go").click(); pg.wait_for_timeout(500)
        tcf = record(u("sc_c_form.html"), form, "sc_c_form")
        res, _ = replay(tcf, "c4")
        print("   sig:", sig(res), "| waits:", notes(res, "Waited"))
        check("C-4 submit waited and PASSED, order placed", allpass(res) and "Thanks, order placed" in (res.get("final_text") or ""), sig(res))

    if want("C5") or want("C6"):
        print("== C-5 / C-6 popup the site opens by itself")
        def auto(pg):
            pg.wait_for_selector("#dlg", state="visible", timeout=10000); pg.wait_for_timeout(500)
            pg.mouse.move(*center(pg.locator("#sub"))); pg.wait_for_timeout(500)
            pg.locator("#closeX").click(); pg.wait_for_timeout(500)
            pg.locator("#next").click(); pg.wait_for_timeout(500)
        tcp = record(u("sc_c_popup.html?m=auto"), auto, "sc_c_popup")
        print("   recorded:", [(a["action_type"], bool(a.get("site_popup")), bool(a.get("popup_container"))) for a in tcp["actions"]])
        check("C-5 the recorder marked the popup steps as site-opened", any(a.get("site_popup") for a in tcp["actions"]))
        res, _ = replay(swap(tcp, "sc_c_popup.html?m=auto", "sc_c_popup.html?m=none"), "c5")
        n = notes(res, "Expected on this site")
        print("   sig:", sig(res), "|", n, "|", [s.get("skipped") for s in res["steps"]])
        check("C-5 popup not shown: its steps skipped, run PASS, 'went next'", allpass(res) and "went next" in (res.get("final_text") or "") and any(s.get("skipped") for s in res["steps"]), sig(res))
        check("C-5 the note names the popup (Expected on this site ... Join our newsletter)", len(n) == 1 and "Join our newsletter" in n[0] and "skipped" in n[0], str(n))
        res, _ = replay(tcp, "c6")
        print("   sig:", sig(res), "|", [s.get("skipped") for s in res["steps"]])
        check("C-6 popup shown: closed with its X, run PASS, nothing skipped", allpass(res) and "went next" in (res.get("final_text") or "") and not any(s.get("skipped") for s in res["steps"]), sig(res))

    if want("C7"):
        print("== C-7 popup only in the replay, blocks the next step")
        tcn = record(u("sc_c_popup.html?m=none"), lambda pg: (pg.locator("#next").click(), pg.wait_for_timeout(400)), "sc_c_nopopup")
        res, _ = replay(swap(tcn, "sc_c_popup.html?m=none", "sc_c_popup.html?m=late"), "c7")
        print("   sig:", sig(res), "| warn:", [(s.get("warning") or "")[:120] for s in res["steps"]], "| notes:", notes(res, "popup"))
        check("C-7 closed, run PASS (note, not a failure)", allpass(res) and "went next" in (res.get("final_text") or ""), sig(res))

    if want("C8"):
        print("== C-8 popup opened by a user click that does not open in replay")
        def user(pg):
            pg.locator("#login").click(); pg.wait_for_selector("#dlg", state="visible"); pg.wait_for_timeout(400)
            pg.locator("#closeX").click(); pg.wait_for_timeout(400)
        tcu = record(u("sc_c_popup.html"), user, "sc_c_userpopup")
        print("   recorded:", [(a["action_type"], bool(a.get("site_popup"))) for a in tcu["actions"]])
        res, _ = replay(swap(tcu, "sc_c_popup.html", "sc_c_popup.html?m=broken"), "c8")
        bad = bad_steps(res); head = step_headline(bad[0], "Log in") if bad else ""
        print("   sig:", sig(res), "|", head[:200])
        check("C-8 still FAILS in plain English", bool(bad) and not any(s.get("skipped") for s in res["steps"]) and not TECH.search(head.split("[details]")[0]), head[:160])
        res, _ = replay(tcu, "c8ok")
        check("C-8 control: the popup opens normally -> PASS", allpass(res), sig(res))

    if want("C9"):
        print("== C-9 input re-rendered after the first send")
        def rer(pg):
            for t_ in ("one", "two"):
                pg.locator("textarea").click(); pg.keyboard.type(t_, delay=30); pg.get_by_role("button", name="Send").click(); pg.wait_for_timeout(400)
        tcr = record(u("sc_c_rerender.html"), rer, "sc_c_rerender")
        print("   recorded:", [a["action_type"] for a in tcr["actions"]])
        for label, url2 in (("c9a", "sc_c_rerender.html"), ("c9b", "sc_c_rerender.html?m=relabel")):
            res, _ = replay(swap(tcr, "sc_c_rerender.html", url2), label)
            print("   ", label, sig(res), [(s.get("error") or "")[:100] for s in res["steps"] if s.get("error")])
            check(f"C-9 {label}: all PASS, both messages sent", allpass(res) and (res.get("final_text") or "").count("You: ") == 2, sig(res))

print("\nREADINESS/POPUP:", "ALL PASS" if not fails else f"FAILED {fails}")
sys.exit(1 if fails else 0)
