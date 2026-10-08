"""TEST-ONLY: mismatch policy + page-generated input, offline.

 R1a recorder: a value the PAGE typed into a box is saved as an expectation
     (validate_value, value_source=page); a value the user typed stays a fill
     (value_source=user)
 R1b replay (old recording shape: a plain Fill): the page animates its own
     text into the box -> the replay waits, does NOT type on top, PASS with
     the "filled this box by itself" note; the text is exactly the recorded one
 R1c page keeps changing the box forever -> FAIL "kept changing ... could not
     type safely" and nothing typed
 R1d ordinary fill still types and verifies
 R2a navigation mismatch (clicked link goes to another path) -> FAIL, the next
     (recorded navigate) step is NOT RUN and is not force-loaded
 R2b covered target: permanent overlay -> FAIL "...covering..."; an overlay
     that closes on Escape is cleared and the click succeeds
 R3  incidental hover: a hover that opens a flyout over the next step's
     target, nothing used inside it -> mouse moved away, next click lands
"""
import importlib.util
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from generator.script_generator import generate_script

OUT = Path("tests/_probe_out/classifier")
OUT.mkdir(parents=True, exist_ok=True)


def record(url, do_actions, name):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        do_actions(pg)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def replay(tc, url, label, steps_only=False):
    d = OUT / label
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    print(f"\n=== {label} ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "ok=" + str(s["success"]), "\n     warning=" + repr(s.get("warning")),
              "\n     error=" + repr(s.get("error"))[:260])
    return res


def hand(actions, start):
    return {"name": "hand", "start_url": start, "actions": actions}


def lp(**kw):
    base = {"id": None, "tag": None, "text": "", "element_text": "", "aria_label": None, "accessible_name": "", "attributes": {}}
    base.update(kw)
    return base


with FixtureServer() as srv:
    # ---------------- R1a: recorder value_source
    def act_page_typed(pg):
        pg.click("#anime")
        pg.wait_for_timeout(5500)      # the page types the prompt itself
        pg.click("#other")              # blur -> the recorder sees the value
        pg.wait_for_timeout(500)

    tc = record(srv.url("cls_anim.html"), act_page_typed, "cls_page")
    kinds = [(a["action_type"], a.get("value_source")) for a in tc["actions"]]
    print("recorded (page typed):", kinds)
    # a value the PAGE typed produces NO step at all - not a fill, not a validation
    assert not any(a["action_type"] in ("fill", "validate_value", "validate") for a in tc["actions"]),         f"page-generated value must not become any step: {kinds}"
    expected_text = "Create a trending anime art style image from the uploaded subject with bold lines"

    def act_user_typed(pg):
        pg.click("#q")
        pg.type("#q", "fitness clothing", delay=20)
        pg.click("#go")
        pg.wait_for_timeout(400)

    tc_u = record(srv.url("cls_plain_form.html"), act_user_typed, "cls_user")
    kinds_u = [(a["action_type"], a.get("value_source")) for a in tc_u["actions"]]
    print("recorded (user typed):", kinds_u)
    assert ("fill", "user") in kinds_u, kinds_u
    print("R1a ok")

    # ---------------- R1b: OLD recording shape (a Fill recorded for a page-typed value)
    old = {"name": "old_fill", "start_url": srv.url("cls_anim.html"), "actions": []}
    click = next(a for a in tc["actions"] if a["action_type"] == "click")
    fill_lp = {"id": "prompt", "tag": "textarea", "aria_label": "Image description", "text": "Image description",
               "element_text": "Image description", "accessible_name": "Image description", "attributes": {}}
    fill = {"action_type": "fill", "value": expected_text, "locator_profile": fill_lp,
            "page_url": srv.url("cls_anim.html")}
    old["actions"] = [a for a in tc["actions"] if a["action_type"] in ("navigate",)][:1] + [click, fill]
    res = replay(old, srv.url("cls_anim.html"), "r1b_old_fill")
    st = res["steps"]
    assert all(s["success"] for s in st), "R1b: must PASS"
    notes = [e["message"] for e in (res.get("live_log") or [])]
    assert any("filled this box by itself" in n for n in notes), f"R1b: expected the plain note, got {notes}"
    with sync_playwright() as p:      # the field must hold exactly the recorded text (no garbling)
        pass
    print("R1b ok:", notes)

    # ---------------- R1c: page never stops changing the box
    forever = json.loads(json.dumps(old))
    for a in forever["actions"]:
        a.pop("post_click", None)      # recorded on another page: no post-click result to compare
    res = replay(forever, srv.url("cls_anim_forever.html"), "r1c_forever")
    fill_step = next(s for s in res["steps"] if s["action_type"] == "fill")
    assert not fill_step["success"], "R1c: must FAIL"
    assert "kept changing this text box by itself" in fill_step["error"], fill_step["error"]
    print("R1c ok:", fill_step["error"])

    # ---------------- R1d: ordinary user fill still types + verifies
    res = replay(tc_u, srv.url("cls_plain_form.html"), "r1d_user")
    assert all(s["success"] for s in res["steps"]), "R1d: ordinary fill must still PASS"
    print("R1d ok")

    # ---------------- R2a: navigation mismatch stops, no forced navigation afterwards
    t_click = "2026-01-01T00:00:00.000Z"
    nav_tc = hand([
        {"action_type": "navigate", "page_url": srv.url("cls_nav_start.html"), "locator_profile": {}, "value": None},
        {"action_type": "click", "page_url": srv.url("cls_nav_start.html"), "timestamp": t_click, "value": None,
         "locator_profile": lp(id="go", tag="a", text="Open details", element_text="Open details", href="cls_nav_wrong.html?utm=abc")},
        {"action_type": "navigate", "page_url": srv.url("cls_nav_expected.html"), "caused_by_timestamp": t_click,
         "delay_before_ms": 200, "locator_profile": {}, "value": None},
    ], srv.url("cls_nav_start.html"))
    res = replay(nav_tc, srv.url("cls_nav_start.html"), "r2a_navmismatch")
    st = res["steps"]
    click_step = next(s for s in st if s["action_type"] == "click")
    assert not click_step["success"], "R2a: wrong page must FAIL"
    from validation.report_generator import step_headline
    head = step_headline(click_step, "Open details")
    print("R2a headline:", head)
    assert head.startswith("Failed: Expected to open '/cls_nav_expected.html' but the browser went to '/cls_nav_wrong.html' instead"), head
    last = st[-1]
    assert last.get("not_run"), "R2a: the following navigate must be NOT RUN"
    assert "cls_nav_expected" not in (res.get("final_url") or ""), "R2a: nothing may force-load the recorded URL"
    print("R2a ok")

    # ---------------- R2b: covered target
    cover_tc = hand([
        {"action_type": "navigate", "page_url": srv.url("cls_cover_perm.html"), "locator_profile": {}, "value": None},
        {"action_type": "click", "page_url": srv.url("cls_cover_perm.html"), "value": None,
         "locator_profile": lp(id="buy", tag="button", text="Buy now", element_text="Buy now")},
    ], srv.url("cls_cover_perm.html"))
    res = replay(cover_tc, srv.url("cls_cover_perm.html"), "r2b_cover_perm")
    c = next(s for s in res["steps"] if s["action_type"] == "click")
    assert not c["success"], "R2b: permanently covered target must FAIL"
    assert c["error"].startswith("Failed: Something on the page (a popup or menu) was covering the 'Buy now' button"), c["error"]
    print("R2b (permanent) ok")

    esc_tc = json.loads(json.dumps(cover_tc).replace("cls_cover_perm", "cls_cover_esc"))
    res = replay(esc_tc, srv.url("cls_cover_esc.html"), "r2b_cover_esc")
    assert all(s["success"] for s in res["steps"]), "R2b: an Escape-closable popup must be cleared and the click must succeed"
    print("R2b (dismissible) ok")

    # ---------------- R3: incidental hover
    hov_tc = hand([
        {"action_type": "navigate", "page_url": srv.url("cls_hover.html"), "locator_profile": {}, "value": None},
        {"action_type": "hover", "page_url": srv.url("cls_hover.html"), "value": None,
         "locator_profile": lp(id="acct", tag="div", text="Account", element_text="Account")},
        {"action_type": "click", "page_url": srv.url("cls_hover.html"), "value": None,
         "locator_profile": lp(id="product", tag="a", text="Cool Product", element_text="Cool Product", href="cls_product.html")},
    ], srv.url("cls_hover.html"))
    res = replay(hov_tc, srv.url("cls_hover.html"), "r3_hover")
    assert all(s["success"] for s in res["steps"]), "R3: hover then click must PASS"
    assert "cls_product" in (res.get("final_url") or ""), f"R3: the click must reach the product, not the flyout: {res.get('final_url')}"
    notes = [e["message"] for e in (res.get("live_log") or [])]
    assert any("moved away" in n for n in notes), notes
    print("R3 ok:", notes)

print("\nCLASSIFIER CHECKS PASS")
