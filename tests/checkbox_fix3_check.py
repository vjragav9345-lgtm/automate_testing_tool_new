"""TEST-ONLY: FIX 3 checks, split into its two real halves so each is verified directly and deterministically:
  (1) BACKEND: recorder.pick_element._on_pick_result computes checkbox_state_info for a real pick (via the
      same start_pick_session() path used elsewhere, no modal/app.py involved) - confirms the shared helper
      really runs during a real pick and the info reaches the stored result.
  (2) FRONTEND: the editor's own applyPickedProfile()/modalValidateBtn rendering, given that exact data shape,
      produces the info line / "Current state" line - run in a real page via Playwright, no live picker browser
      needed (a synthetic response is enough to exercise the DOM-building code itself).
"""
import sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import recorder.pick_element as pe
from phase4_fixture_server import FixtureServer
from playwright.sync_api import sync_playwright

# ---------- (1) backend ----------
with FixtureServer() as srv:
    url = srv.url("checkbox_state_fixture.html")
    pick_id = pe.start_pick_session(url, [])

    def click_only(browser, context):
        p = context.pages[0]
        box = p.locator("#custom-checked .tick").bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        p.mouse.move(cx, cy); p.wait_for_timeout(80)
        p.mouse.click(cx, cy)
        # does NOT close the browser here - checkbox_state_info is computed
        # in the wait loop's OWN next tick (see pick_element.py's own
        # comment on why it can't be computed inside the click handler's
        # callback), which needs the browser to stay open a little longer
        # to get that next tick at all, exactly like a real human leaving
        # the picker open while they look at the modal.

    pe._TEST_DRIVE_QUEUE.put(click_only)
    t0 = time.time()
    status = {}
    while time.time() - t0 < 30:
        status = pe._PICK_RESULTS.get(pick_id) or {}
        if status.get("checkbox_state_info") is not None:
            break
        time.sleep(0.3)
    print("locked status keys:", list(status.keys()))
    print("backend picked xpath:", status.get("xpath"))
    print("backend checkbox_state_info:", status.get("checkbox_state_info"))
    info = status.get("checkbox_state_info") or {}
    # NOTE: which exact element the picker resolves the click to (a11y/
    # geometry-dependent - see action_capture.js's own realElementAt) is
    # outside this fix's own scope (10/10 cases in
    # tests/checkbox_state_helper_check.py already cover the RESOLVER logic
    # itself precisely, independent of picking). What THIS check proves is
    # the mechanism end to end for a REAL pick: no deadlock (the wait loop
    # actually reached the next tick and ran the resolver), and a well-
    # formed result reaches the stored status.
    assert info.get("state") in ("checked", "unchecked", "indeterminate", "not_a_checkbox")
    assert info.get("resolvedHow") in ("self", "aria", "label.control", "descendant", "ancestor", "ambiguous", "none")

    pe._TEST_DRIVE_QUEUE.put(lambda browser, context: browser.close())
    t0 = time.time()
    while time.time() - t0 < 15:
        if (pe._PICK_RESULTS.get(pick_id) or {}).get("status") == "done":
            break
        time.sleep(0.3)
print("PASS (1): backend computes checkbox_state_info for a real pick\n")

# ---------- (2) frontend rendering ----------
with FixtureServer() as srv2, sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(srv2.url("rendered_editor_fixture.html"))
    pg.wait_for_selector("#actionsList", state="attached")

    # populate just enough state for the modal to be open on a
    # validate_checked step, without a real recording load
    pg.evaluate("""() => {
        recordingData = { start_url: 'http://x/', actions: [] };
        modalContext = { mode: 'after', index: -1, insertAfterIndex: -1, pageUrl: 'http://x/', pageId: 0 };
        modalActionType.innerHTML = '<option value="validate_checked">Validate Checkbox State</option>';
        modalActionType.value = 'validate_checked';
        addActionModal.hidden = false;
        renderModalFields();
    }""")

    # applyPickedProfile() is a function LOCAL to modalPickElementBtn's own
    # click handler (not reachable by name from outside it) - exercised here
    # by mocking window.fetch for the two routes that handler itself calls
    # and then clicking the REAL button, so the REAL handler (and therefore
    # the REAL applyPickedProfile) runs, with a canned status response
    # standing in for a live picker browser.
    def pick_case(tag, checkbox_state_info, picked_tag="div"):
        pg.evaluate("""(info) => {
            window.__afqaMockStatus = {
                status: 'done', xpath: "//label[normalize-space(text())='Tshirts']/div",
                tag: info.pickedTag, match_count: 1, checkbox_state_info: info.cbInfo,
            };
            window.fetch = (url, opts) => {
                if (String(url).includes('/pick_element/start')) {
                    return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, pick_id: 'x' }) });
                }
                if (String(url).includes('/pick_element/status')) {
                    return Promise.resolve({ ok: true, json: () => Promise.resolve(window.__afqaMockStatus) });
                }
                return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) });
            };
        }""", {"cbInfo": checkbox_state_info, "pickedTag": picked_tag})
        pg.click("#modalPickElementBtn")
        pg.wait_for_function(
            "() => document.getElementById('modalValidateResult').textContent.includes('Found')"
            " || document.getElementById('modalValidateResult').textContent.includes('match')",
            timeout=10000,
        )
        pg.wait_for_timeout(200)
        return pg.eval_on_selector("#modalValidateResult", "e => e.innerHTML")

    # (a) the pick-time info line
    html_pick = pick_case("a", {"state": "checked", "resolvedTag": "input", "resolvedHow": "label.control"})
    print("applyPickedProfile() result HTML:\n ", html_pick[:400])
    # exact wording the task specified: "Note: picked <div>; state will be
    # read from its associated checkbox <input>." - resolvedHow itself is
    # deliberately not shown here (only on the Validate button's own
    # "Current state" line below), matching that spec precisely.
    assert "picked &lt;div&gt;" in html_pick and "associated checkbox &lt;input&gt;" in html_pick

    # (b) ambiguous case
    html_ambig = pick_case("b", {"state": "not_a_checkbox", "resolvedHow": "ambiguous", "ambiguousCount": 3})
    print("\nambiguous case HTML:\n ", html_ambig[:400])
    assert "3 checkboxes" in html_ambig

    # (c) not-a-checkbox case
    html_none = pick_case("c", {"state": "not_a_checkbox", "resolvedHow": "none", "resolvedTag": "button"}, picked_tag="button")
    print("\nnot-a-checkbox case HTML:\n ", html_none[:400])
    assert "not a checkbox" in html_none

    # (d) normal case (native input picked directly) - no extra note expected
    html_normal = pick_case("d", {"state": "checked", "resolvedHow": "self", "resolvedTag": "input"}, picked_tag="input")
    print("\nnormal (self) case HTML:\n ", html_normal[:400])
    assert "associated checkbox" not in html_normal and "ambiguous" not in html_normal.lower()

    # (e) the modal's own Validate button - same mocking approach, for /validate_locator
    pg.evaluate("""(info) => {
        window.fetch = (url) => {
            if (String(url).includes('/validate_locator')) {
                return Promise.resolve({ ok: true, json: () => Promise.resolve({
                    success: true, found: true, match_count: 1, checkbox_state_info: info,
                }) });
            }
            return Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) });
        };
    }""", {"state": "checked", "resolvedHow": "label.control", "resolvedTag": "input"})
    pg.fill("#modalXpath", "//label[normalize-space(text())='Tshirts']/div")
    pg.click("#modalValidateBtn")
    pg.wait_for_function(
        "() => document.getElementById('modalValidateResult').textContent.includes('Current state')",
        timeout=10000,
    )
    html_validate_btn = pg.eval_on_selector("#modalValidateResult", "e => e.innerHTML")
    print("\nValidate-button rendering HTML:\n ", html_validate_btn[:400])
    assert "Current state: checked" in html_validate_btn and "label.control" in html_validate_btn

    print("\npage errors:", errs)
    assert not errs
    b.close()
print("\nPASS (2): frontend rendering shows the info/warning line and the real state, for every case, via the REAL button handlers")
