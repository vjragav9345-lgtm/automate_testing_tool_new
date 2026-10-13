"""TEST-ONLY diagnostic for FIX D - dumps outerHTML + ancestor chain and
calls the REAL, unmodified action_capture.js's buildProfile() directly
(via its RECORDER_DEBUG hook) against the 3 previously-misclassified
elements ("+", "Send OTP", the icon-only "Pick from your saved
people"-ish button) on the live site, WITHOUT ever dispatching a real
click - never touches the Send OTP budget.

    venv/Scripts/python.exe tests/flowfixd_diagnostic.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402
import json  # noqa: E402
import importlib.util  # noqa: E402
import tempfile  # noqa: E402


ANCESTOR_DUMP_JS = """
(el) => {
    function describe(node) {
        if (!node) return null;
        var attrs = {};
        if (node.attributes) {
            for (var i = 0; i < node.attributes.length; i++) {
                attrs[node.attributes[i].name] = node.attributes[i].value;
            }
        }
        var cs = getComputedStyle(node);
        return {
            tag: node.tagName,
            attrs: attrs,
            ownText: (node.childNodes ? Array.from(node.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim() : ''),
            innerText: (node.innerText || '').slice(0, 80),
            cursor: cs.cursor,
            hasSvg: !!node.querySelector('svg'),
            rect: (function () { var r = node.getBoundingClientRect(); return {w: r.width, h: r.height}; })(),
        };
    }
    var chain = [];
    var node = el;
    var depth = 0;
    while (node && node.nodeType === 1 && depth < 7) {
        chain.push(describe(node));
        node = node.parentElement;
        depth++;
    }
    return { outerHTML: el.outerHTML.slice(0, 500), chain: chain };
}
"""


def main():
    recording_path = BASE_DIR / "storage" / "recordings" / "session_20260924_121410.json"
    with open(recording_path, "r", encoding="utf-8") as f:
        recording = json.load(f)
    acts = recording["actions"]

    # Only steps 17 ("+") and 18 (click Continue, opens the Sign-In modal)
    # are actually DISPATCHED for real - both are safe, zero-side-effect
    # UI-only actions (no SMS, no payment). "Send OTP" (step 21) is
    # diagnosed by RESOLVING its element (already present in the opened
    # modal) and calling buildProfile() directly via evaluate - it is
    # NEVER clicked, so this costs nothing against that site's real SMS
    # budget. Step 24's icon element lives on the participants page,
    # reachable only after a real OTP verification - not diagnosed here;
    # see the written report for why.
    register_url = acts[15]["page_url"]  # step 16's own url = .../register
    synthetic_navigate = {"action_type": "navigate", "page_url": register_url, "page_id": 0}
    actions = [synthetic_navigate] + acts[16:18]  # steps 17 (check +), 18 (click Continue)

    test_case = {"name": "flowfixd_diag", "start_url": register_url, "actions": actions}
    scratch_dir = Path(tempfile.mkdtemp(prefix="flowfixd_diag_"))
    script_path = generate_script(test_case, out_name="flowfixd_diag_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location("flowfixd_diag_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    capture_js = (BASE_DIR / "recorder" / "action_capture.js").read_text(encoding="utf-8")
    debug_capture_js = "window.__RECORDER_DEBUG__ = true;\n" + capture_js

    diag_state = {}
    from playwright.sync_api import Browser, BrowserContext

    orig_new_context = Browser.new_context
    orig_new_page = BrowserContext.new_page

    def patched_new_context(self, *a, **kw):
        ctx = orig_new_context(self, *a, **kw)
        ctx.add_init_script(debug_capture_js)
        return ctx

    def patched_new_page(self, *a, **kw):
        p = orig_new_page(self, *a, **kw)
        diag_state["page"] = p
        return p

    Browser.new_context = patched_new_context
    BrowserContext.new_page = patched_new_page

    import builtins
    orig_print = builtins.print
    results = {}

    def spy_print(*args, **kwargs):
        if args and str(args[0]).startswith("[") is False and str(args[0]) == "REPLAY COMPLETED":
            page = diag_state.get("page")
            if page is not None:
                targets = {
                    "step17_plus": acts[16]["locator_profile"],   # "+"
                    "step21_send_otp": acts[20]["locator_profile"],  # "Send OTP" - resolved, never clicked
                }
                for label, lp in targets.items():
                    css_path = lp.get("css_path")
                    xpath = lp.get("xpath")
                    el_handle = None
                    try:
                        if css_path:
                            loc = page.locator(css_path)
                            if loc.count() > 0:
                                el_handle = loc.first.element_handle()
                    except Exception:
                        pass
                    if el_handle is None and xpath:
                        try:
                            loc = page.locator(f"xpath={xpath}")
                            if loc.count() > 0:
                                el_handle = loc.first.element_handle()
                        except Exception:
                            pass
                    if el_handle is None:
                        results[label] = {"error": "could not resolve element live"}
                        continue
                    try:
                        dump = page.evaluate(ANCESTOR_DUMP_JS, el_handle)
                    except Exception as e:
                        dump = {"error": str(e)}
                    try:
                        profile = page.evaluate(
                            "(el) => window.__RECORDER_DEBUG_BUILD_PROFILE__(el, 'click', null)",
                            el_handle,
                        )
                    except Exception as e:
                        profile = {"error": str(e)}
                    results[label] = {"dump": dump, "profile": profile}
        orig_print(*args, **kwargs)

    builtins.print = spy_print
    try:
        output_json = scratch_dir / "report.json"
        screenshot_dir = scratch_dir / "screenshots"
        module.run(
            test_case["start_url"], output_json_path=output_json,
            screenshot_dir=screenshot_dir, headless=False,
        )
    finally:
        builtins.print = orig_print
        Browser.new_context = orig_new_context
        BrowserContext.new_page = orig_new_page

    out_path = BASE_DIR / "tests" / "flowfixd_diagnostic_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    print(f"\ndiagnostic result saved to {out_path}")
    for label, r in results.items():
        print(f"\n=== {label} ===")
        prof = r.get("profile", {})
        print("action_type:", prof.get("action_type"))
        print("classified_by:", prof.get("classified_by"))
        print("expected_state:", prof.get("expected_state"))


if __name__ == "__main__":
    main()
