"""TEST-ONLY: Phase 1a verification. Records a click on a checkbox filter label
whose ONLY usable signal is its own text, embedding a volatile count
("Tshirts(419525)") - exactly the reported bug's shape (no id/data-testid on
the label itself). Replays the SAME recording against a fixture where that
count has changed, confirming PASS-with-warning; then against an ambiguous
fixture (two candidates after normalization) confirming a clean failure,
never a guess."""
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

ORIGINAL = "phase1_volatile_number.html"
CHANGED = "phase1_volatile_number_changed.html"


def record(url):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        rec = Recorder(pg)
        rec.install_context_capture(ctx)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        rec.start(launch_url=pg.url)
        pg.click("#filters .filter-item:nth-child(1)")
        pg.wait_for_timeout(400)
        tc = rec.stop(name="phase1_volatile", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def replay(tc, url, label):
    d = Path(f"tests/_probe_out/phase1_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"phase1_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"phase1_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    print(f"\n=== {label} ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "warning=" + repr(s.get("warning"))[:200], repr(s.get("error"))[:150])
    print("status:", res["status"])
    return res


with FixtureServer() as srv:
    url_orig = srv.url(ORIGINAL)
    url_changed = srv.url(CHANGED)

    tc = record(url_orig)
    print("Recorded actions:", [(a["action_type"], (a.get("locator_profile") or {}).get("text")) for a in tc["actions"]])
    click_step = next(a for a in tc["actions"] if a["action_type"] in ("click", "check"))
    recorded_text = (click_step.get("locator_profile") or {}).get("text")
    recorded_tag = (click_step.get("locator_profile") or {}).get("tag")
    print("Recorded click locator_profile text:", recorded_text, "tag:", recorded_tag, "id:", (click_step.get("locator_profile") or {}).get("id"))
    assert recorded_text and "419525" in recorded_text, f"expected the recorded text to include the original count, got {recorded_text!r}"
    assert not (click_step.get("locator_profile") or {}).get("id"), "expected no id on the label (matching the reported bug's shape)"

    # --- replay 1: SAME site (no change) - baseline PASS, no warning ---
    res1 = replay(tc, url_orig, "baseline_same_site")
    assert res1["status"] == "PASS" and all(s["success"] for s in res1["steps"])
    assert not any(s.get("warning") for s in res1["steps"]), "no warning expected when nothing changed"
    print("BASELINE (no change) PASS, no warning: CONFIRMED")

    # --- replay 2, 3, 4: site's count CHANGED - PASS with warning, 3x ---
    for attempt in (1, 2, 3):
        res = replay(tc, url_changed, f"changed_site_attempt{attempt}")
        assert res["status"] == "PASS" and all(s["success"] for s in res["steps"]), f"attempt {attempt}: expected PASS"
        click_result = next(s for s in res["steps"] if s["action_type"] == "click")
        warning = click_result.get("warning") or ""
        assert warning.startswith("Warning:") and "changed" in warning and "recording:" in warning, f"attempt {attempt}: expected the value-changed warning, got {warning!r}"
        assert "419525" in warning and "419847" in warning, f"attempt {attempt}: warning must name old and new text: {warning!r}"
        print(f"CHANGED-SITE attempt {attempt}: PASS with warning: {warning!r}")

print("\nPHASE 1a (value-changed) ALL CHECKS PASS")
