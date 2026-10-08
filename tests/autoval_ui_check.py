"""TEST-ONLY: checks 2-3 of the auto-validation removal, on the real editor (server on 5001), using a throwaway copy."""
import json, shutil, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from storage import session_files as sf

COPY_A, COPY_B = "zz_autoval_copy_a", "zz_autoval_copy_b"   # A: the 212033 recording as it is now (Fill+Enter, no validate); B: a kept session that has a validate step
def make_copy(src, name):
    d = json.loads((BASE / src).read_text(encoding="utf-8")); d["name"] = name
    (BASE / f"storage/recordings/{name}.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
make_copy("storage/recordings/edited/session_20260928_212033_edited.json", COPY_A)
make_copy("storage/recordings/edited/session_20260928_170352_edited.json", COPY_B)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); pg = b.new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
        # ---- check 2 (copy B): what Add Action offers today + an existing validate step is fully editable
        pg.goto(f"http://127.0.0.1:5001/recording/edit?path=storage/recordings/{COPY_B}.json"); pg.wait_for_selector("#actionsList > *", timeout=20000)
        vidx = pg.evaluate("recordingData.actions.findIndex(a => a.action_type === 'validate')")
        print(f"B: existing validate step is #{vidx + 1}:", pg.locator('#actionsList > *').nth(vidx).inner_text().splitlines()[0])
        pg.locator('button[title="Add Action After"]').first.click()
        offered = pg.eval_on_selector_all("#modalActionType option", "els => els.map(e => e.value)")
        print("B: Add Action offers 'validate' (Assert Text Visible)?", "validate" in offered, "| options offered:", len(offered))
        pg.click("#modalCancelBtn")
        pg.locator("#actionsList > *").nth(vidx).locator('button[title^="Edit this step"]').click()
        fld = pg.locator("#modalField_value")
        st = fld.evaluate("e => ({disabled: e.disabled, readOnly: e.readOnly})")
        print("B: edit modal type =", pg.eval_on_selector("#modalActionType", "e => e.value"), "| 'Expected text' field:", st, "| value:", repr(fld.input_value()))
        assert not st["disabled"] and not st["readOnly"]
        fld.fill("edited-by-hand"); pg.click("#modalSaveBtn")
        assert pg.evaluate(f"recordingData.actions[{vidx}].value") == "edited-by-hand"
        print("B: after Save in the edit modal the step value is now:", pg.evaluate(f"recordingData.actions[{vidx}].value"))
        # ---- check 3 (copy A): open + save through the real pipeline, nothing may be injected
        pg.goto(f"http://127.0.0.1:5001/recording/edit?path=storage/recordings/{COPY_A}.json"); pg.wait_for_selector("#actionsList > *", timeout=20000)
        before = pg.evaluate("recordingData.actions.map(a => a.action_type)")
        pg.click("#saveEditedBtn"); pg.wait_for_selector("#saveStatus:not([hidden])", timeout=15000)
        print("A: save status:", pg.locator("#saveStatus").inner_text()[:90])
        print("page errors:", errs); assert not errs
        b.close()
    saved = json.loads((BASE / f"storage/recordings/edited/{COPY_A}_edited.json").read_text(encoding="utf-8"))
    types = [a["action_type"] for a in saved["actions"]]
    print("A: before save:", before); print("A: after save :", types)
    assert types == before and "validate" not in types
    print("PASS: nothing was added by open + save")
finally:
    for name in (COPY_A, COPY_A + "_edited", COPY_B, COPY_B + "_edited"):
        r = sf.delete_session(name)
        print("cleanup", name, {k: len(v) for k, v in r.items() if k != "errors"})
