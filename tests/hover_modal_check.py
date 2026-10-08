"""TEST-ONLY: I2 (hidden hover-menu targets, another-copy guard) and I3 (modal Close).

 I2a a menu item hidden until its trigger is hovered, with NO recorded hover chain and a
     visible twin link in the footer: the click reaches the MENU item (not the footer),
     within seconds, without the legacy fallback chain
 I2b two visible links with the same name, the wrong one first in the DOM: the click goes to
     the one where the target was recorded
 I3a close button inside an open shadow root -> found by accessible name (title) and clicked
 I3b no modal and no close control -> PASS "modal was already closed", at once
 I3c overlay without a close control -> Escape once -> overlay gone -> PASS
 I3d overlay still there after Escape -> FAIL in plain English
"""
import importlib.util
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_fixture_server import FixtureServer
from generator.script_generator import generate_script

OUT = Path("tests/_probe_out/hover_modal")
OUT.mkdir(parents=True, exist_ok=True)


def lp(**kw):
    base = {"id": None, "tag": None, "text": "", "element_text": "", "aria_label": None,
            "accessible_name": "", "attributes": {}}
    base.update(kw)
    return base


def run(actions, start, label):
    d = OUT / label
    d.mkdir(parents=True, exist_ok=True)
    tc = {"name": label, "start_url": start, "actions": [
        {"action_type": "navigate", "page_url": start, "locator_profile": {}, "value": None}] + actions}
    sp = generate_script(tc, out_name=f"{label}.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(label, sp)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    t = time.monotonic()
    res = m.run(start, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    took = time.monotonic() - t
    print(f"\n=== {label} ({took:.1f}s) ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "ok=" + str(s["success"]), "| dur", s.get("duration"), "|", (s.get("error") or "")[:160])
    return res


with FixtureServer() as srv:
    url = srv.url("hov_menu.html")

    # ---- I2a: hidden menu item, no hover chain, footer twin
    click = {"action_type": "click", "page_url": url, "value": None, "scroll_y": 0,
             "bounding_box": {"x": 20, "y": 40, "width": 90, "height": 20},
             "locator_profile": lp(id="pa", tag="a", text="Pro Analytics", element_text="Pro Analytics",
                                   href="hov_menu_target.html")}
    res = run([click], url, "i2a_hidden_menu")
    s = res["steps"][1]
    assert s["success"], s.get("error")
    assert "hov_menu_target" in (res.get("final_url") or ""), res.get("final_url")
    assert s["duration"] < 8, f"hidden-menu click must not run the whole fallback chain: {s['duration']}s"
    print("I2a ok:", res.get("final_url"), f"{s['duration']}s")

    # ---- I2b: two visible same-named links; recorded at the header, footer first in the DOM
    click2 = {"action_type": "click", "page_url": url, "value": None, "scroll_y": 0,
              "bounding_box": {"x": 150, "y": 10, "width": 40, "height": 20},
              "locator_profile": lp(tag="a", text="Open", element_text="Open")}
    res = run([click2], url, "i2b_far_copy")
    s = res["steps"][1]
    assert s["success"], s.get("error")
    assert "hov_menu_target" in (res.get("final_url") or ""), f"went to the other copy: {res.get('final_url')}"
    print("I2b ok:", res.get("final_url"))

    # ---- I3
    close = {"action_type": "click", "value": None, "scroll_y": 0,
             "locator_profile": lp(tag="button", title="Close", accessible_name="")}
    page = srv.url("modal_shadow.html")
    c = dict(close, page_url=page)
    res = run([c], page, "i3a_shadow")
    assert res["steps"][1]["success"], res["steps"][1].get("error")
    print("I3a ok")

    page = srv.url("modal_none.html")
    c = dict(close, page_url=page)
    t = time.monotonic()
    res = run([c], page, "i3b_none")
    s = res["steps"][1]
    assert s["success"], s.get("error")
    assert s["duration"] < 3, f"an absent modal must be decided at once, took {s['duration']}s"
    assert "already closed" in (s.get("warning") or ""), s.get("warning")
    print("I3b ok")

    FPD = {"kind": "dialog", "tag": "div", "id": "dlg", "role": "dialog", "aria_label": None, "css_path": "div#dlg", "text_hint": None}
    page = srv.url("modal_esc.html")
    c = dict(close, page_url=page, popup_container=FPD)
    res = run([c], page, "i3c_escape")
    assert res["steps"][1]["success"], res["steps"][1].get("error")
    print("I3c ok")

    page = srv.url("modal_stuck.html")
    c = dict(close, page_url=page, popup_container=FPD)
    res = run([c], page, "i3d_stuck")
    s = res["steps"][1]
    assert not s["success"], "a stuck overlay must FAIL"
    assert s["error"].startswith("Failed: The pop-up"), s["error"]
    print("I3d ok:", s["error"])

print("\nHOVER / MODAL CHECKS PASS")
