"""TEST-ONLY: follow-up task verification. Confirms a HOVER step's own target
resolution already goes through resolve_and_act's main tier loop (which already
has the Phase 1 number-tolerant fallback + _verify_resolved_target tolerance),
with NO additional code change - see the investigation report for the call
path evidence (comment at generator/script_generator.py's own hover dispatch
branch, ~line 9955-9965)."""
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

ORIGINAL = "hover_volatile_number.html"
CHANGED = "hover_volatile_number_changed.html"


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
        pg.hover(".cat-trigger")
        pg.wait_for_timeout(300)
        pg.click("#submenuLink")
        pg.wait_for_timeout(300)
        tc = rec.stop(name="hover_volatile", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def replay(tc, url, label):
    d = Path(f"tests/_probe_out/hover_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"hover_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"hover_{label}_mod", sp)
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
    hover_step = next(a for a in tc["actions"] if a["action_type"] == "hover")
    lp = hover_step.get("locator_profile") or {}
    print("Recorded hover locator_profile text:", lp.get("text"))
    print("Recorded hover locator_profile id/name/data-testid:", lp.get("id"), lp.get("name"), (lp.get("attributes") or {}).get("data-testid"))
    assert lp.get("text") and "419525" in lp["text"], f"expected the recorded text to include the original count, got {lp.get('text')!r}"
    assert not lp.get("id"), "expected no id on the hover target (matching the reported bug's shape)"

    # --- baseline: same site, no change - PASS, no warning ---
    res0 = replay(tc, url_orig, "baseline_same_site")
    assert res0["status"] == "PASS" and all(s["success"] for s in res0["steps"])
    assert not any(s.get("warning") for s in res0["steps"]), "no warning expected when nothing changed"
    print("BASELINE (no change) PASS, no warning: CONFIRMED")

    # --- 3x replay against the CHANGED page - PASS with warning every time ---
    for attempt in (1, 2, 3):
        res = replay(tc, url_changed, f"changed_site_attempt{attempt}")
        assert res["status"] == "PASS" and all(s["success"] for s in res["steps"]), f"attempt {attempt}: expected PASS"
        hover_result = next(s for s in res["steps"] if s["action_type"] == "hover")
        warning = hover_result.get("warning") or ""
        assert warning.startswith("Warning:") and "changed" in warning and "recording:" in warning, f"attempt {attempt}: expected the value-changed warning, got {warning!r}"
        assert "419525" in warning, f"attempt {attempt}: warning must name the old text: {warning!r}"
        print(f"CHANGED-SITE attempt {attempt}: PASS with warning: {warning!r}")

print("\nHOVER VOLATILE-NUMBER FOLLOW-UP: ALL CHECKS PASS")
