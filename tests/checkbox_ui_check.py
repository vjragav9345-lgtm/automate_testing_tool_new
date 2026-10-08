"""TEST-ONLY: FIX 3 UI checks - Pick Element on a custom checkbox's visible <div>, confirm the info-line note,
then use the modal's Validate button and confirm it shows the real resolved state; also confirm the orphan
warning (FIX 4) no longer fires when a preceding Click Checkbox step targets the SAME text-anchored label."""
import json, sys, threading, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as appmod
import recorder.pick_element as pe
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from storage import repository

srv = make_server("127.0.0.1", 5001, appmod.app, threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()

with FixtureServer() as fx:
    url = fx.url("checkbox_state_fixture.html")
    tc = {"name": "zz_checkbox_ui_check", "start_url": url, "actions": [
        {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": url},
        # step 2: a "Click Checkbox (Set State)" step whose OWN xpath targets the same
        # label by its exact visible text - mirrors the repro's step 4
        {"action_type": "check", "value": None, "page_url": url, "expected_state": True,
         "locator_profile": {"xpath": "//label[normalize-space(.)='Tshirts']", "tag": "label", "text": "Tshirts",
                              "css_path": None, "id": None, "attributes": {}}},
    ]}
    repository.save_recording(tc)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); pg = b.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:5001/recording/edit?path=storage/recordings/zz_checkbox_ui_check.json")
        pg.wait_for_selector("#actionsList > *", timeout=20000)

        # Add Action After Step 2, type validate_checked xpath by hand first (mirrors the div
        # Pick Element saved in the repro), check the orphan-warning behaviour (FIX 4)
        pg.locator('button[title="Add Action After"]').nth(1).click()  # after STEP 2 (the check action), not step 1
        pg.select_option("#modalActionType", "validate_checked")
        pg.fill("#modalXpath", "//label[normalize-space(text())='Tshirts']/div")
        pg.dispatch_event("#modalXpath", "input")
        pg.wait_for_timeout(200)
        dbg = pg.evaluate("""() => ({
            tokensA: extractXPathTokens(document.getElementById('modalXpath').value),
            tokensB: extractXPathTokens((recordingData.actions[1].locator_profile||{}).xpath),
            related: xpathsAreRelated(document.getElementById('modalXpath').value, (recordingData.actions[1].locator_profile||{}).xpath),
            step2xpath: (recordingData.actions[1].locator_profile||{}).xpath,
            typedxpath: document.getElementById('modalXpath').value,
        })""")
        print("DEBUG:", dbg)
        warning_hidden = pg.eval_on_selector("#modalOrphanWarning", "e => e.hidden")
        print("FIX 4: orphan warning hidden (expected True, same 'Tshirts' text as step 2):", warning_hidden)
        assert warning_hidden, "the orphan warning should NOT fire - step 2 already sets up this exact label"

        # now drive an actual Pick Element pick on the visible tick <div>
        pg.click("#modalPickElementBtn")

        def drive(browser, context):
            p2 = context.pages[0]
            box = p2.locator("#custom-checked .tick").bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            p2.mouse.move(cx, cy); p2.wait_for_timeout(80)
            p2.mouse.click(cx, cy); p2.wait_for_timeout(500)
            browser.close()

        pe._TEST_DRIVE_QUEUE.put(drive)
        pg.wait_for_function(
            "() => document.getElementById('modalValidateResult').textContent.includes('Found')",
            timeout=30000,
        )
        pg.wait_for_timeout(500)
        result_html = pg.eval_on_selector("#modalValidateResult", "e => e.innerHTML")
        print("\nFIX 3 (pick note) modalValidateResult HTML:\n", result_html[:500])
        assert "associated checkbox" in result_html and "label.control" in result_html

        # now click the modal's own Validate button and confirm it shows the real state
        pg.click("#modalValidateBtn")
        pg.wait_for_function(
            "() => document.getElementById('modalValidateResult').textContent.includes('Current state')",
            timeout=20000,
        )
        result_html2 = pg.eval_on_selector("#modalValidateResult", "e => e.innerHTML")
        print("\nFIX 3 (Validate button) modalValidateResult HTML:\n", result_html2[:500])
        assert "Current state: checked" in result_html2 and "label.control" in result_html2

        print("\npage errors:", errs)
        assert not errs
        b.close()
print("\nPASS: FIX 3 (pick note + Validate button real state) and FIX 4 (orphan warning) all confirmed")
import os; os._exit(0)
