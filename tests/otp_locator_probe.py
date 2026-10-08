"""TEST-ONLY, read-only locator probe for the Send OTP element - reaches
the real page state via the REAL, unmodified run() (steps 1-6 only: nav,
scroll, +5K counter, Continue, phone click, phone fill) and STOPS THERE -
step 7 (Send OTP) is never included in the test_case, so this never
clicks/checks Send OTP and costs nothing against the Send OTP click
budget. Once run() finishes (steps 1-6 done, browser about to close),
independently resolves EVERY locator strategy for Send OTP's recorded
locator_profile and describes exactly what each one points to (tag,
text, class, bounding box, and whether it is the actual hit-testable
element at its own center) - so the xpath/css_path/text/role candidates
can be compared before any resolver code changes. Purely diagnostic;
run() itself is never edited or monkeypatched beyond capturing the live
context/page reference from outside (same technique as
otp_natural_capture.py).

    venv/Scripts/python.exe tests/otp_locator_probe.py
"""
import builtins
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import Browser, BrowserContext  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402


def install_capture_patch(capture_state):
    orig_new_context = Browser.new_context
    orig_new_page = BrowserContext.new_page

    def patched_new_context(self, *args, **kwargs):
        context = orig_new_context(self, *args, **kwargs)
        capture_state["context"] = context
        return context

    def patched_new_page(self, *args, **kwargs):
        page = orig_new_page(self, *args, **kwargs)
        capture_state["page"] = page
        return page

    Browser.new_context = patched_new_context
    BrowserContext.new_page = patched_new_page
    return orig_new_context, orig_new_page


def restore_capture_patch(orig_new_context, orig_new_page):
    Browser.new_context = orig_new_context
    BrowserContext.new_page = orig_new_page


def _describe(loc, module, label, out):
    entry = {}
    try:
        entry["count"] = loc.count()
    except Exception as e:
        entry["count_error"] = str(e)
        out[label] = entry
        return
    n = entry.get("count") or 0
    entry["items"] = []
    for i in range(min(n, 8)):
        item = {}
        cand = loc.nth(i)
        try:
            item["tag"] = cand.evaluate("e => e.tagName")
        except Exception:
            item["tag"] = None
        try:
            item["class"] = cand.evaluate("e => e.className")
        except Exception:
            item["class"] = None
        try:
            item["inner_text"] = (cand.inner_text() or "")[:60]
        except Exception:
            item["inner_text"] = None
        try:
            item["bounding_box"] = cand.bounding_box()
        except Exception:
            item["bounding_box"] = None
        try:
            item["is_visible"] = cand.is_visible()
        except Exception:
            item["is_visible"] = None
        box = item.get("bounding_box")
        if box and box.get("width") and box.get("height"):
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            try:
                stack = cand.evaluate(module._ELEMENTS_FROM_POINT_JS, [cx, cy])
                item["is_top_hit_or_self"] = bool(stack and (stack[0].get("isResolvedElement") or stack[0].get("pointerEvents") != "none"))
                item["top_of_stack"] = stack[0] if stack else None
            except Exception as e:
                item["hit_test_error"] = str(e)
        entry["items"].append(item)
    out[label] = entry


def main():
    recording_path = BASE_DIR / "storage" / "recordings" / "session_20260923_140957.json"
    with open(recording_path, "r", encoding="utf-8") as f:
        recording = json.load(f)

    register_url = recording["actions"][14]["page_url"]
    synthetic_navigate = {"action_type": "navigate", "page_url": register_url, "page_id": 0}
    # steps 1-6 ONLY (through phone-fill) - Send OTP (step 7) deliberately
    # excluded, so it is never dispatched. recording["actions"][14:19] is
    # 0-based indices 14..18 = original 1-based steps 15..19 (phone fill,
    # the LAST one) - NOT 14:20, which off-by-one included index 19 =
    # original step 20 = Send OTP itself (a mistake caught after the fact
    # in an earlier run of this script - see the investigation report).
    full_actions = [synthetic_navigate] + recording["actions"][14:19]
    lp = recording["actions"][19]["locator_profile"]  # original step 20 = Send OTP

    test_case = {"name": "otp_locator_probe", "start_url": register_url, "actions": full_actions}

    scratch_dir = Path(tempfile.mkdtemp(prefix="otp_locator_probe_"))
    script_path = generate_script(test_case, out_name="otp_locator_probe_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location("otp_locator_probe_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    capture_state = {}
    orig_new_context, orig_new_page = install_capture_patch(capture_state)

    orig_print = builtins.print
    probe_result = {}

    def spy_print(*args, **kwargs):
        if args and str(args[0]) == "REPLAY COMPLETED" and not capture_state.get("probed"):
            capture_state["probed"] = True
            page = capture_state.get("page")
            if page is not None:
                orig_print("[probe] reached REPLAY COMPLETED - probing all locator strategies for Send OTP", flush=True)
                role = lp.get("role")
                name = lp.get("accessible_name") or lp.get("text")
                if role:
                    try:
                        _describe(page.get_by_role(role, name=name), module, "role", probe_result)
                    except Exception as e:
                        probe_result["role"] = {"error": str(e)}
                tag = lp.get("tag")
                if tag:
                    try:
                        all_tag = page.locator(tag)
                        texts = all_tag.all_inner_texts()
                        text = (lp.get("text") or "").strip()
                        exact_idx = [i for i, t in enumerate(texts) if t.strip() == text]
                        entry = {"total": all_tag.count(), "exact_idx": exact_idx, "items": []}
                        for i in exact_idx[:8]:
                            cand = all_tag.nth(i)
                            item = {}
                            try:
                                item["class"] = cand.evaluate("e => e.className")
                            except Exception:
                                item["class"] = None
                            try:
                                item["bounding_box"] = cand.bounding_box()
                            except Exception:
                                item["bounding_box"] = None
                            try:
                                item["outer_html_head"] = cand.evaluate("e => e.outerHTML.slice(0,150)")
                            except Exception:
                                item["outer_html_head"] = None
                            try:
                                item["contains_other"] = cand.evaluate(
                                    "(e, other_idx) => null", None
                                )
                            except Exception:
                                pass
                            entry["items"].append(item)
                        # relationship check between the two exact-text divs (ancestor/descendant vs separate)
                        if len(exact_idx) == 2:
                            try:
                                a = all_tag.nth(exact_idx[0]).element_handle()
                                b = all_tag.nth(exact_idx[1]).element_handle()
                                rel = page.evaluate(
                                    "([a, b]) => a.contains(b) ? 'a_contains_b' : (b.contains(a) ? 'b_contains_a' : 'separate')",
                                    [a, b],
                                )
                                entry["relationship"] = rel
                            except Exception as e:
                                entry["relationship_error"] = str(e)
                        probe_result["text_tag"] = entry
                    except Exception as e:
                        probe_result["text_tag"] = {"error": str(e)}
                css_path = lp.get("css_path")
                if css_path:
                    try:
                        _describe(page.locator(css_path), module, "css_path", probe_result)
                    except Exception as e:
                        probe_result["css_path"] = {"error": str(e)}
                xpath = lp.get("xpath")
                if xpath:
                    try:
                        _describe(page.locator(f"xpath={xpath}"), module, "xpath", probe_result)
                    except Exception as e:
                        probe_result["xpath"] = {"error": str(e)}
                orig_print(f"[probe] result: {json.dumps(probe_result, default=str)[:4000]}", flush=True)
        orig_print(*args, **kwargs)

    builtins.print = spy_print
    try:
        output_json = scratch_dir / "report.json"
        screenshot_dir = scratch_dir / "screenshots"
        result = module.run(
            test_case["start_url"],
            output_json_path=output_json,
            screenshot_dir=screenshot_dir,
            headless=False,
        )
    finally:
        builtins.print = orig_print
        restore_capture_patch(orig_new_context, orig_new_page)

    print("\n===== RESULT =====")
    print("status:", result.get("status"))
    for s in result.get("steps", []):
        print(s.get("index"), s.get("action_type"), "success=", s.get("success"), (s.get("error") or "")[:150])

    out_path = BASE_DIR / "tests" / "otp_locator_probe_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(probe_result, f, indent=2, default=str)
    print(f"\nprobe result saved to {out_path}")


if __name__ == "__main__":
    main()
