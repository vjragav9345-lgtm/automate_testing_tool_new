"""TEST-ONLY: checks 2-4 of the dashboard task on the real dashboard (server on port 5001)."""
import json, sys, base64
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from storage import repository, session_files as sf
from generator.script_generator import generate_script, EDITED_OUTPUT_DIR

KEEP = ["session_20260928_170052_edited", "session_20260928_170352_edited",
        "session_20260928_171139_edited", "session_20260928_181934_edited"]
THROW = "zz_throwaway_session_test"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")

def make_throwaway():
    tc = json.loads((BASE / "storage/recordings/edited/session_20260928_170052_edited.json").read_text(encoding="utf-8"))
    tc["name"] = THROW
    repository.save_recording(tc)
    generate_script(tc)                                   # generated_scripts/<name>_script.py
    generate_script(tc, output_dir=EDITED_OUTPUT_DIR)     # generated_scripts/edited/<name>_script.py
    run = sf.RUNS_DIR / f"{THROW}_20260928_230000"
    (run / "stage_one").mkdir(parents=True, exist_ok=True)
    (run / "stage_one" / "img1.png").write_bytes(PNG)
    (run / "report.html").write_text("<html>throwaway</html>", encoding="utf-8")
    (run / "report.json").write_text("{}", encoding="utf-8")
    f = sf.session_files(THROW)
    print("throwaway created:", {k: len(v) for k, v in f.items()})
    return f

def snapshot_paths(names):
    return {n: sorted(str(p) for k in sf.session_files(n).values() for p in k) for n in names}

kept_before = snapshot_paths(KEEP)
make_throwaway()

with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:5001/"); pg.wait_for_selector(".recording-card", timeout=20000)
    names = pg.eval_on_selector_all(".recording-card h3", "els => els.map(e => e.textContent)")
    print("cards with throwaway present:", len(names), sorted(names))
    assert sorted(names) == sorted(KEEP + [THROW])
    # --- check 4a: global Screenshots button is gone from the top
    assert pg.locator("#screenshotsViewerBtn").count() == 0
    top_btns = pg.eval_on_selector_all("section.action-panel button, header button, body > section button", "els => els.map(e => e.textContent.trim())") if False else None
    top_texts = pg.eval_on_selector_all("button:not(.recording-buttons button)", "els => els.map(e => e.textContent.trim())")
    print("all non-card buttons:", top_texts)
    assert "Screenshots" not in top_texts
    # --- per-card buttons
    card = pg.locator(".recording-card", has=pg.locator("h3", has_text=KEEP[0])).first
    texts = [t.strip() for t in card.locator(".recording-buttons button").all_inner_texts()]
    print("card buttons:", texts)
    assert texts == ["View / Edit", "Replay", "View Last Log", "Screenshots", "Delete"]
    # --- check 4b: each session's Screenshots button shows only its own runs
    def card_of(name):
        return pg.locator(".recording-card").filter(has=pg.locator(f"h3:text-is('{name}')")).first
    for name in (KEEP[0], THROW):
        card_of(name).locator("button", has_text="Screenshots").click()
        pg.wait_for_url("**/screenshots?session=*"); pg.wait_for_selector("#cardList .action-card", timeout=15000)
        heads = pg.eval_on_selector_all("#cardList .action-card h3", "els => els.map(e => e.textContent)")
        print(f"Screenshots of {name}:", pg.url.split('?')[1], "->", heads)
        assert heads and all(h.lower().startswith(name + "_") and sf.is_run_folder_of(name, h) for h in heads)
        pg.go_back(); pg.wait_for_selector(".recording-card")
    # --- View/Edit and View Last Log still work for a kept session
    card_of(KEEP[1]).locator("button", has_text="View / Edit").click()
    pg.wait_for_url("**/recording/edit?*"); pg.wait_for_selector("#actionsList > *", timeout=20000)
    print("View/Edit opened:", pg.url.split('?')[1][:70], "| steps rendered:", pg.locator("#actionsList > *").count())
    pg.go_back(); pg.wait_for_selector(".recording-card")
    card = card_of(KEEP[1]); card.locator("button", has_text="View Last Log").click()
    pg.wait_for_timeout(1500)
    print("View Last Log panel text:", card.locator(".editor-message, .editor-error, .validation-panel").first.inner_text()[:100].replace("\n", " | ") if card.locator(".editor-message, .editor-error, .validation-panel").count() else "(no panel)")
    # --- check 3: Delete asks for confirmation; dismiss keeps, accept deletes
    dialogs = []
    def on_dialog(d):
        dialogs.append((d.type, d.message.split("\n")[0]))
        d.dismiss() if len(dialogs) == 1 else d.accept()
    pg.on("dialog", on_dialog)
    card_of(THROW).locator("button", has_text="Delete").click(); pg.wait_for_timeout(800)
    still = sf.session_files(THROW)
    print("after DISMISSING confirm -> files still there:", {k: len(v) for k, v in still.items()}, "| cards:", pg.locator(".recording-card").count())
    assert sum(len(v) for v in still.values()) == 4 and pg.locator(".recording-card").count() == 5
    card_of(THROW).locator("button", has_text="Delete").click()
    pg.wait_for_function("document.querySelectorAll('.recording-card').length === 4", timeout=15000)
    gone = sf.session_files(THROW)
    names2 = pg.eval_on_selector_all(".recording-card h3", "els => els.map(e => e.textContent)")
    print("dialogs:", dialogs)
    print("after ACCEPTING -> files:", {k: len(v) for k, v in gone.items()}, "| cards:", sorted(names2))
    assert sum(len(v) for v in gone.values()) == 0 and sorted(names2) == sorted(KEEP)
    assert not (sf.RUNS_DIR / f"{THROW}_20260928_230000").exists()
    print("page errors:", errs); assert not errs
    b.close()
assert snapshot_paths(KEEP) == kept_before, "kept sessions' files changed"
print("kept sessions' files untouched by the delete: OK")
print("PASS")
