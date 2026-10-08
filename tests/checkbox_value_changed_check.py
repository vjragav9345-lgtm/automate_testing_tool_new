"""TEST-ONLY: FOLLOW-UP FIX 1 verification (V1/V2). Record a "check" step
on a checkbox that has a STABLE id/name (so the "id" strategy resolves it
first, never the text-based tiers) whose associated <label> text carries a
volatile count. Confirms the generic _verify_resolved_target-based
value-changed note now fires regardless of which strategy matched."""
import importlib.util
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from generator.script_generator import generate_script

ORIGINAL = "checkbox_volatile_number.html"
CHANGED = "checkbox_volatile_number_changed.html"


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
        pg.check("#filterCheckbox")
        pg.wait_for_timeout(300)
        tc = rec.stop(name="checkbox_volatile", stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        b.close()
    for d in drafts:
        if d:
            Path(d).unlink(missing_ok=True)
    return tc


def replay(tc, url, label):
    d = Path(f"tests/_probe_out/checkbox_{label}")
    d.mkdir(parents=True, exist_ok=True)
    sp = generate_script(tc, out_name=f"checkbox_{label}_script.py", output_dir=d)
    spec = importlib.util.spec_from_file_location(f"checkbox_{label}_mod", sp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
    print(f"\n=== {label} ===")
    for s in res["steps"]:
        print(s["index"], s["action_type"], "success=" + str(s["success"]), "strategy=" + repr(s.get("strategy_used")), "warning=" + repr(s.get("warning")))
    print("status:", res["status"])
    return res


with FixtureServer() as srv:
    url_orig = srv.url(ORIGINAL)
    url_changed = srv.url(CHANGED)

    tc = record(url_orig)
    check_step = next(a for a in tc["actions"] if a["action_type"] == "check")
    lp = check_step.get("locator_profile") or {}
    print("Recorded check locator_profile text:", lp.get("text"))
    print("Recorded check locator_profile id:", lp.get("id"))
    assert lp.get("text") and "418534" in lp["text"], f"expected recorded text to include the original count, got {lp.get('text')!r}"
    assert lp.get("id") == "#filterCheckbox", f"expected a stable id to be recorded, got {lp.get('id')!r}"

    # --- V2: baseline, same site, no change - PASS, no warning ---
    res0 = replay(tc, url_orig, "v2_baseline_same_site")
    assert res0["status"] == "PASS" and all(s["success"] for s in res0["steps"])
    assert not any(s.get("warning") for s in res0["steps"]), "no warning expected when nothing changed"
    check_result0 = next(s for s in res0["steps"] if s["action_type"] == "check")
    print("strategy used on unchanged site:", check_result0.get("strategy_used"))
    print("V2 (unchanged value) PASS, no warning: CONFIRMED")

    # --- V1: changed site - PASS with warning, resolved via a NON-TEXT strategy ---
    res1 = replay(tc, url_changed, "v1_changed_site")
    assert res1["status"] == "PASS" and all(s["success"] for s in res1["steps"]), "expected PASS"
    check_result1 = next(s for s in res1["steps"] if s["action_type"] == "check")
    strategy = check_result1.get("strategy_used")
    warning = check_result1.get("warning") or ""
    print("strategy used on changed site:", strategy)
    assert strategy not in ("text+tag", "text+tag-number-normalized"), (
        f"expected a non-text strategy (id) to resolve this step, got {strategy!r}"
    )
    assert warning.startswith("Warning:") and "changed" in warning and "recording:" in warning, f"expected the value-changed warning, got {warning!r}"
    assert "418534" in warning and "418542" in warning, f"warning must name both old and new text: {warning!r}"
    print(f"V1 (changed value, resolved via {strategy!r}): PASS with warning: {warning!r}")

print("\nCHECKBOX VALUE-CHANGED (FIX 1) FOLLOW-UP: ALL CHECKS PASS")
