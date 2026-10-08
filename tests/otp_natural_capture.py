"""TEST-ONLY natural-conditions diagnostic capture for the intermittent
Sportzia OTP flow - NO injected network delay anywhere in this script
(the previous item-#5 wrapper's injected page.route() delay was flagged
as a possible confound: the delay itself might be what closes the modal,
which would not prove anything about the real, undelayed failure path).
Run directly:

    venv/Scripts/python.exe tests/otp_natural_capture.py

Calls the REAL, completely unmodified run() in-process (same technique as
tests/otp_real_run_wrapper.py: generate a throwaway script via
generate_script(), import it, monkeypatch only Playwright's own public
Browser.new_context()/BrowserContext.new_page() from OUTSIDE to reach the
live context/page). run() itself is never edited, patched, or given any
artificial delay.

Captures, around the Send OTP step specifically:
  - a full Playwright trace (screenshots + snapshots)
  - per-locator-strategy match count and timing (role, text+tag, css_path,
    xpath) for the Send OTP element, probed read-only just before the real
    dispatch - mirrors _resolve_element_with_strategy's own finder tiers
    without replacing or interfering with them
  - the actually-resolved element's tag/text/is_visible/is_enabled/
    bounding_box, and document.elementFromPoint() at its center (reusing
    the product's own _ELEMENTS_FROM_POINT_JS, which normally only runs
    for action_type=="click", not "check" - Send OTP is recorded as
    "check", so this is otherwise never logged for it)
  - a PARALLEL, independent MutationObserver (armed at the same moment,
    never replacing the product's own effect-tracking) recording every
    mutation's target/type/attributeName, read back once replay finishes
  - the full xhr/fetch request+response log for the whole run, with
    monotonic timestamps for correlation

Like otp_real_run_wrapper.py, this bypasses recorded steps 1-9 (the
events-list -> click event card sequence, independently flaky right now,
unrelated to the OTP flow) via a synthetic direct navigate to the event's
own /register URL - the same URL recorded step 10 already navigates to.
This is the ONLY deviation from the raw recording; nothing else is
altered, and no artificial timing is introduced anywhere.

Caveat, disclosed rather than hidden: the pre-click probes themselves take
real time (the text+tag probe walks every <div> on the page) - so the
click that follows is not dispatched at the exact instant it would be
with zero instrumentation. This is an unavoidable tension in observing
without disturbing; the probes are read-only and never touch the element
being resolved for the real dispatch, but they do add wall-clock delay
before it.
"""
import argparse
import builtins
import importlib.util
import json
import re
import sys
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import Browser, BrowserContext  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402


_STEP_HEADER_RE = re.compile(r"^\[(\d+)/\d+\]$")

_ARM_MUTATION_JS = """
() => {
    window.__diagMutations = [];
    if (window.__diagObserver) { try { window.__diagObserver.disconnect(); } catch (e) {} }
    window.__diagObserver = new MutationObserver((records) => {
        for (const r of records) {
            let targetDesc = r.target.tagName || ('#' + r.target.nodeType);
            if (r.target.className) targetDesc += '.' + String(r.target.className).trim().replace(/\\s+/g, '.');
            window.__diagMutations.push({
                type: r.type,
                target: targetDesc,
                attributeName: r.attributeName || null,
                oldValue: r.oldValue || null,
            });
        }
    });
    window.__diagObserver.observe(document.documentElement, {
        childList: true, subtree: true, attributes: true, attributeOldValue: true,
        characterData: true, characterDataOldValue: true,
    });
}
"""

_READ_MUTATIONS_JS = """
() => {
    const out = (window.__diagMutations || []).slice();
    if (window.__diagObserver) { try { window.__diagObserver.disconnect(); } catch (e) {} }
    return out;
}
"""


def install_capture_patch(capture_state):
    orig_new_context = Browser.new_context
    orig_new_page = BrowserContext.new_page

    def patched_new_context(self, *args, **kwargs):
        context = orig_new_context(self, *args, **kwargs)
        capture_state["context"] = context
        try:
            context.tracing.start(screenshots=True, snapshots=True, sources=False)
            capture_state["tracing_started"] = True
        except Exception as e:
            print(f"[capture] tracing.start failed: {e}", flush=True)
        return context

    def patched_new_page(self, *args, **kwargs):
        page = orig_new_page(self, *args, **kwargs)
        capture_state["page"] = page

        def _on_request(req):
            if req.resource_type in ("xhr", "fetch"):
                capture_state["net_log"].append({
                    "event": "request", "t": time.monotonic(), "method": req.method, "url": req.url,
                })

        def _on_response(res):
            if res.request.resource_type in ("xhr", "fetch"):
                capture_state["net_log"].append({
                    "event": "response", "t": time.monotonic(), "status": res.status, "url": res.url,
                })

        page.on("request", _on_request)
        page.on("response", _on_response)
        return page

    Browser.new_context = patched_new_context
    BrowserContext.new_page = patched_new_page
    return orig_new_context, orig_new_page


def restore_capture_patch(orig_new_context, orig_new_page):
    Browser.new_context = orig_new_context
    BrowserContext.new_page = orig_new_page


def _probe_locator_strategies(page, lp, module, out):
    role = lp.get("role")
    name = lp.get("accessible_name") or lp.get("text")
    if role:
        t0 = time.monotonic()
        try:
            count = page.get_by_role(role, name=name).count()
            err = None
        except Exception as e:
            count, err = None, str(e)
        out["role"] = {"count": count, "elapsed_s": round(time.monotonic() - t0, 3), "error": err, "name_used": name}

    tag, text = lp.get("tag"), lp.get("text")
    if tag and text:
        t0 = time.monotonic()
        try:
            loc = page.locator(tag)
            total = loc.count()
            texts = loc.all_inner_texts()
            exact = sum(1 for t in texts if t.strip() == text.strip())
            exact_ci = sum(1 for t in texts if t.strip().lower() == text.strip().lower())
            err = None
        except Exception as e:
            total = exact = exact_ci = None
            err = str(e)
        out["text_tag"] = {
            "total_tag_matches": total, "exact_text_matches": exact,
            "case_insensitive_matches": exact_ci, "elapsed_s": round(time.monotonic() - t0, 3), "error": err,
        }

    css_path = lp.get("css_path")
    if css_path:
        t0 = time.monotonic()
        try:
            count = page.locator(css_path).count()
            err = None
        except Exception as e:
            count, err = None, str(e)
        out["css_path"] = {"count": count, "elapsed_s": round(time.monotonic() - t0, 3), "error": err}

    xpath = lp.get("xpath")
    if xpath:
        t0 = time.monotonic()
        try:
            count = page.locator(f"xpath={xpath}").count()
            err = None
        except Exception as e:
            count, err = None, str(e)
        out["xpath"] = {"count": count, "elapsed_s": round(time.monotonic() - t0, 3), "error": err}

    t0 = time.monotonic()
    try:
        real_loc, real_strategy = module._resolve_element_with_strategy(page, lp)
        real_elapsed = round(time.monotonic() - t0, 3)
        if real_loc is not None:
            try:
                box = real_loc.bounding_box()
            except Exception:
                box = None
            try:
                is_visible = real_loc.is_visible()
            except Exception:
                is_visible = None
            try:
                is_enabled = real_loc.is_enabled()
            except Exception:
                is_enabled = None
            try:
                tag_name = real_loc.evaluate("e => e.tagName")
            except Exception:
                tag_name = None
            try:
                inner_text = real_loc.inner_text()
            except Exception:
                inner_text = None
            out["actual_resolution"] = {
                "strategy": real_strategy, "elapsed_s": real_elapsed,
                "bounding_box": box, "is_visible": is_visible, "is_enabled": is_enabled,
                "tag": tag_name, "inner_text": (inner_text or "")[:200],
            }
            if box and box.get("width") and box.get("height"):
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                try:
                    stack = real_loc.evaluate(module._ELEMENTS_FROM_POINT_JS, [cx, cy])
                except Exception as e:
                    stack = f"error: {e}"
                out["element_from_point"] = {"x": cx, "y": cy, "stack": stack}
        else:
            out["actual_resolution"] = {"strategy": None, "elapsed_s": real_elapsed, "error": "not resolved"}
    except Exception as e:
        out["actual_resolution"] = {"error": str(e)}


def arm_diag_gate(capture_state, target_step, lp, module):
    orig_print = builtins.print

    def spy_print(*args, **kwargs):
        if args:
            text = str(args[0])
            m = _STEP_HEADER_RE.match(text)
            if m and int(m.group(1)) == target_step and not capture_state.get("pre_click_done"):
                capture_state["pre_click_done"] = True
                capture_state["pre_click_t"] = time.monotonic()
                orig_print(f"[capture] step {target_step} header seen - running pre-click diagnostics", flush=True)
                page = capture_state.get("page")
                if page is not None:
                    pre = {}
                    try:
                        _probe_locator_strategies(page, lp, module, pre)
                    except Exception as e:
                        pre["probe_error"] = str(e)
                    capture_state["pre_click"] = pre
                    try:
                        page.evaluate(_ARM_MUTATION_JS)
                        capture_state["mutation_armed"] = True
                    except Exception as e:
                        orig_print(f"[capture] mutation observer arm failed: {e}", flush=True)
                    orig_print(f"[capture] pre-click diagnostics: {json.dumps(pre, default=str)[:3000]}", flush=True)
            elif text == "REPLAY COMPLETED" and not capture_state.get("post_run_done"):
                capture_state["post_run_done"] = True
                capture_state["post_run_t"] = time.monotonic()
                page = capture_state.get("page")
                context = capture_state.get("context")
                if page is not None:
                    try:
                        mutations = page.evaluate(_READ_MUTATIONS_JS) if capture_state.get("mutation_armed") else None
                    except Exception as e:
                        mutations = f"error: {e}"
                    capture_state["post_click_mutations"] = mutations
                    try:
                        capture_state["post_body_text"] = page.evaluate("() => document.body.innerText")[:2000]
                    except Exception:
                        pass
                    try:
                        capture_state["post_screenshot"] = str(BASE_DIR / "tests" / "otp_natural_capture_final.png")
                        page.screenshot(path=capture_state["post_screenshot"])
                    except Exception as e:
                        orig_print(f"[capture] final screenshot failed: {e}", flush=True)
                if context is not None and capture_state.get("tracing_started"):
                    try:
                        trace_path = BASE_DIR / "tests" / "otp_natural_capture_trace.zip"
                        context.tracing.stop(path=str(trace_path))
                        capture_state["trace_path"] = str(trace_path)
                    except Exception as e:
                        orig_print(f"[capture] tracing.stop failed: {e}", flush=True)
        orig_print(*args, **kwargs)

    builtins.print = spy_print
    return orig_print


def disarm_diag_gate(orig_print):
    builtins.print = orig_print


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recording",
        default=str(BASE_DIR / "storage" / "recordings" / "session_20260923_140957.json"),
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--run-label", default="run1")
    args = parser.parse_args()

    with open(args.recording, "r", encoding="utf-8") as f:
        recording = json.load(f)

    register_url = recording["actions"][14]["page_url"]  # step 15's page_url
    synthetic_navigate = {"action_type": "navigate", "page_url": register_url, "page_id": 0}
    full_actions = [synthetic_navigate] + recording["actions"][14:22]  # original steps 15-22
    target_step = 7  # Send OTP, in this synthetic numbering
    lp = recording["actions"][19]["locator_profile"]  # original step 20 = Send OTP

    test_case = {
        "name": "otp_natural_capture",
        "start_url": register_url,
        "actions": full_actions[:target_step],
    }

    scratch_dir = Path(tempfile.mkdtemp(prefix="otp_natural_capture_"))
    script_path = generate_script(test_case, out_name="otp_natural_capture_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location("otp_natural_capture_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    capture_state = {"net_log": []}
    orig_new_context, orig_new_page = install_capture_patch(capture_state)
    orig_print = arm_diag_gate(capture_state, target_step, lp, module)
    try:
        output_json = scratch_dir / "report.json"
        screenshot_dir = scratch_dir / "screenshots"
        result = module.run(
            test_case["start_url"],
            output_json_path=output_json,
            screenshot_dir=screenshot_dir,
            headless=args.headless,
        )
    finally:
        disarm_diag_gate(orig_print)
        restore_capture_patch(orig_new_context, orig_new_page)

    print("\n===== RESULT =====")
    print("status:", result.get("status"))
    for s in result.get("steps", []):
        print(s.get("index"), s.get("action_type"), "success=", s.get("success"), (s.get("error") or "")[:150])

    send_otp_step = next((s for s in result.get("steps", []) if s.get("index") == target_step), None)

    pre_t = capture_state.get("pre_click_t")
    post_t = capture_state.get("post_run_t")
    net_log = capture_state.get("net_log") or []
    net_log_window = [n for n in net_log if pre_t is not None and post_t is not None and pre_t - 2.0 <= n["t"] <= post_t]

    out = {
        "result_status": result.get("status"),
        "send_otp_step_report": send_otp_step,
        "pre_click": capture_state.get("pre_click"),
        "post_click_mutations": capture_state.get("post_click_mutations"),
        "post_body_text": capture_state.get("post_body_text"),
        "post_screenshot": capture_state.get("post_screenshot"),
        "trace_path": capture_state.get("trace_path"),
        "net_log_full": net_log,
        "net_log_around_send_otp": net_log_window,
    }
    out_path = BASE_DIR / "tests" / f"otp_natural_capture_result_{args.run_label}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nfull diagnostic capture saved to {out_path}")
    print(f"trace saved to {capture_state.get('trace_path')}")
    print(f"final screenshot saved to {capture_state.get('post_screenshot')}")


if __name__ == "__main__":
    main()
