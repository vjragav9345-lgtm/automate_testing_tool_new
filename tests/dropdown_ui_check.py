"""TEST-ONLY: Add-Action dropdown trimming, checked on the real editor page (server on port 5001)."""
import sys
from playwright.sync_api import sync_playwright
HIDDEN = {"submit", "select", "validate", "validate_attribute", "capture_list", "compare_list_overlap"}
URL = "http://127.0.0.1:5001/recording/edit?path=storage/recordings/session_20260928_145711.json"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_selector("#actionsList > *", timeout=20000)
    n = pg.locator("#actionsList > *").count()
    all_keys = pg.evaluate("Object.keys(ACTION_FIELD_DEFS)")
    always_hidden = pg.evaluate("Object.keys(ACTION_FIELD_DEFS).filter(k => ACTION_FIELD_DEFS[k].hiddenFromAddMenu && !%s.includes(k))" % list(HIDDEN))
    expected = [k for k in all_keys if k not in HIDDEN and k not in always_hidden]
    # 1) Add Action After Step 1
    pg.locator('button[title="Add Action After"]').first.click()
    print("modal title:", pg.locator("#modalTitle").inner_text() if pg.locator("#modalTitle").count() else "(n/a)")
    vals = pg.eval_on_selector_all("#modalActionType option", "els => els.map(e => e.value)")
    labels = pg.eval_on_selector_all("#modalActionType option", "els => els.map(e => e.textContent)")
    print("1) options offered:", len(vals), "| removed six present:", sorted(HIDDEN & set(vals)), "| expected list identical & same order:", vals == expected)
    assert not (HIDDEN & set(vals)) and vals == expected
    for lab in ("Submit", "Select", "Assert Text Visible", "Validate Attribute", "Compare List Overlap", "Capture List"):
        assert not any(l.startswith(lab) for l in labels), lab
    pg.click("#modalCancelBtn")
    # 2) existing step with a hidden type (validate) still displays / edits / deletes / undo
    idx = pg.evaluate("recordingData.actions.findIndex(a => a.action_type === 'validate')")
    row = pg.locator("#actionsList > *").nth(idx)
    print("2) step", idx + 1, "row text:", row.inner_text().replace("\n", " | ")[:120])
    row.locator('button[title^="Edit this step"]').click()
    print("   edit modal type value:", pg.eval_on_selector("#modalActionType", "e => e.value"), "| title:", pg.locator("#modalTitle").inner_text())
    assert pg.eval_on_selector("#modalActionType", "e => e.value") == "validate"
    field = pg.locator("#modalField_value")
    print("   'Expected text' field rendered, value:", repr(field.input_value()))
    assert field.count() == 1
    pg.click("#modalCancelBtn")
    # add-mode list must be back to the filtered list after that edit
    pg.locator('button[title="Add Action After"]').first.click()
    vals2 = pg.eval_on_selector_all("#modalActionType option", "els => els.map(e => e.value)")
    print("   after editing a hidden-type step, Add list still filtered:", vals2 == expected)
    assert vals2 == expected
    pg.click("#modalCancelBtn")
    before = pg.evaluate("recordingData.actions.length")
    pg.locator("#actionsList > *").nth(idx).locator('button[title="Delete"]').click()
    after = pg.evaluate("recordingData.actions.length")
    pg.click("#undoDeleteBtn")
    restored = pg.evaluate("[recordingData.actions.length, recordingData.actions[%d].action_type]" % idx)
    print("   delete:", before, "->", after, "| undo restores:", restored)
    assert after == before - 1 and restored == [before, "validate"]
    print("page errors:", errs)
    assert not errs
    print("PASS")
    b.close()
