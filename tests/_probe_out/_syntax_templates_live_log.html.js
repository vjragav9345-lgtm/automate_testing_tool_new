

// self-contained duplicate of static/js/script.js's ACTION_TYPE_LABELS -
// this page is a standalone popup window with no shared JS module system
// in this project, so it follows the SAME already-established pattern
// the codebase uses elsewhere (recording_editor.html/report_generator.py
// each keep their own copy too) rather than inventing a new shared-config
// mechanism just for this one page.
const ACTION_TYPE_LABELS = {
    click: "Click", dblclick: "Double Click", right_click: "Right Click",
    fill: "Fill", select: "Select", submit: "Submit", press: "Key Press",
    scroll: "Scroll", navigate: "Navigate", tab_open: "Open Tab",
    tab_switch: "Switch Tab", tab_close: "Close Tab", validate: "Validate",
    click_if_exists: "Click If Exists", screenshot: "Screenshot",
    check: "Checkbox Toggle", check_checked: "Checkbox Check",
    capture_value: "Capture Value", compare_value: "Compare Value",
    validate_element: "Validate Element", validate_text: "Validate Text",
    validate_attribute: "Validate Attribute", validate_visible: "Validate Visible",
    validate_value: "Validate Value", validate_enabled: "Validate Enabled",
    count_elements: "Count Elements", compare_counts: "Compare Counts",
    count_summary: "Count Summary", detect_duplicates: "Detect Duplicates",
    capture_list: "Capture List", compare_list_overlap: "Compare List Overlap",
    validate_value_range: "Validate Value Range",
    // ITEM 7 FIX: both were missing from this copy (validate_url was
    // already present in the other two ACTION_TYPE_LABELS copies this
    // file's own top comment says it mirrors; validate_checked is a
    // newer action type that was wired into replay/ACTION_FIELD_DEFS
    // but never added to any of the three label copies) - without an
    // explicit entry here, a step of either type fell back to the
    // generic underscore-to-title-case name, which happens to read
    // right for validate_checked by coincidence but not for validate_url.
    validate_url: "Validate URL", validate_checked: "Validate Checkbox State",
};

function actionLabel(actionType, element) {
    const base = ACTION_TYPE_LABELS[actionType] ||
        (actionType || "step").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    if (!element) return base;
    // a scroll/list-container target's own text can be its ENTIRE
    // multi-line visible content (every item in a list, say) - collapsed
    // to one line and capped here purely for this one-line log display;
    // the full, real text is untouched everywhere else (recording JSON,
    // report, etc.), this is a display-only trim
    let oneLine = String(element).replace(/\s+/g, " ").trim();
    if (oneLine.length > 60) oneLine = oneLine.slice(0, 57) + "...";
    return oneLine ? `${base} - ${oneLine}` : base;
}

function timestamp() {
    return new Date().toLocaleTimeString();
}

function appendLine(html) {
    const container = document.getElementById("logLines");
    const line = document.createElement("div");
    line.className = "log-line";
    line.innerHTML = html;
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(s) {
    if (s === null || s === undefined) return "";
    return String(s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

const params = new URLSearchParams(window.location.search);
const runId = params.get("run_id");
const currentStepEl = document.getElementById("currentStep");
const errorBanner = document.getElementById("errorBanner");
const summaryBanner = document.getElementById("summaryBanner");
const otpPrompt = document.getElementById("otpPrompt");
const otpPromptText = document.getElementById("otpPromptText");
const otpValueInput = document.getElementById("otpValueInput");
const otpSubmitBtn = document.getElementById("otpSubmitBtn");
const otpStatus = document.getElementById("otpStatus");

if (!runId) {
    currentStepEl.textContent = "No run_id given.";
} else {

    currentStepEl.textContent = "Connecting to replay " + runId + "...";

    const source = new EventSource("/api/test/run/stream?run_id=" + encodeURIComponent(runId));

    // PHASE 2d: sent once, right at the start of the stream - shows this
    // run's own name (display_name when the recording has one) instead
    // of the generic heading; falls back to test_name, then leaves the
    // heading exactly as it already is today when neither is set.
    source.addEventListener("meta", (e) => {
        const data = JSON.parse(e.data);
        const name = data.display_name || data.test_name;
        if (name) {
            document.getElementById("liveLogHeading").textContent = name;
            document.title = name + " - Live Replay Log - AutoFlow QA";
        }
    });

    source.addEventListener("running", (e) => {
        const data = JSON.parse(e.data);
        currentStepEl.innerHTML =
            `<span class="status-running">RUNNING</span> Step ${data.index}: ` +
            escapeHtml(actionLabel(data.action_type, data.element)) +
            ` (${data.elapsed_s}s elapsed)`;
    });

    // OTP-STEP HANDLING / HOVER-REVEAL: plain sub-step lines the
    // replay subprocess writes for a recognized OTP flow, or for a
    // hover-reveal it had to perform before a click - see app.py's own
    // "log" SSE event and generator/script_generator.py's _otp_flow_log/
    // _hover_reveal_log. Never sent at all for a run with neither.
    source.addEventListener("log", (e) => {
        const data = JSON.parse(e.data);
        appendLine(
            `<span class="ts">[${timestamp()}]</span>` +
            `<span class="otp-line">${escapeHtml(data.message)}</span>`
        );
    });

    let otpSubmitting = false;

    function submitOtp() {
        const value = otpValueInput.value.trim();
        if (!value || otpSubmitting) return;
        otpSubmitting = true;
        otpStatus.textContent = "Submitting...";
        fetch("/api/test/run/otp_submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ run_id: runId, value }),
        })
            .then((r) => r.json())
            .then((data) => {
                otpSubmitting = false;
                if (data.success) {
                    otpStatus.textContent = "Submitted - continuing...";
                    otpSubmitBtn.disabled = true;
                    otpValueInput.disabled = true;
                } else {
                    otpStatus.textContent = data.message || "Couldn't submit OTP.";
                }
            })
            .catch(() => {
                otpSubmitting = false;
                otpStatus.textContent = "Couldn't reach the server - try again.";
            });
    }

    otpSubmitBtn.addEventListener("click", submitOtp);
    otpValueInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") submitOtp();
    });

    // replay is genuinely paused, waiting for a human to type in a live
    // OTP (the recorded value is never reused - see script_generator.py's
    // own OTP-step handling) - shows the prompt; "otp_resolved" (sent
    // the instant replay stops waiting, either because a value arrived
    // or the wait timed out) hides it again and resets it for any LATER
    // OTP step in the same recording.
    source.addEventListener("otp_needed", (e) => {
        const data = JSON.parse(e.data);
        otpPromptText.textContent =
            `Step ${data.step_index}/${data.total_steps}: ${data.message || "Enter OTP to continue"}`;
        otpStatus.textContent = "";
        otpValueInput.value = "";
        otpValueInput.disabled = false;
        otpSubmitBtn.disabled = false;
        otpPrompt.style.display = "block";
        otpValueInput.focus();
    });

    source.addEventListener("otp_resolved", () => {
        otpPrompt.style.display = "none";
    });

    // a long-running replay's SSE connection can drop and reconnect for
    // reasons that have nothing to do with the replay itself (a dev-
    // server idle timeout, a network blip) - EventSource always
    // transparently reconnects on its own, and the server-side stream
    // (see api_test_run_stream in app.py) has no per-CLIENT resume
    // cursor, so a fresh connection replays every step already recorded
    // in report.json from the start. Deduping here, by step index,
    // means a reconnect is a harmless no-op for what's on screen instead
    // of every already-shown step appearing a second time - confirmed
    // real (not hypothetical) against an actual ~90s, 23-step replay.
    const renderedSteps = new Set();

    source.addEventListener("step", (e) => {
        const data = JSON.parse(e.data);
        if (renderedSteps.has(data.index)) return;
        renderedSteps.add(data.index);
        const label = escapeHtml(actionLabel(data.action_type, data.element));
        const statusText = { pass: "PASS", fail: "FAILED", skipped: "SKIPPED" }[data.status] || data.status.toUpperCase();
        const statusClass = "status-" + data.status;

        appendLine(
            `<span class="ts">[${timestamp()}]</span>` +
            `Step ${data.index}: ${label} - <span class="${statusClass}">${statusText}</span>`
        );

        if (data.status === "fail" && data.reason) {
            const r = data.reason;
            const parts = [];
            if (r.error) parts.push(`<div><strong>Reason:</strong> ${escapeHtml(r.error)}</div>`);
            if (r.selector) parts.push(`<div><strong>Locator strategy:</strong> ${escapeHtml(r.selector)}</div>`);
            if (r.url) parts.push(`<div><strong>URL at failure:</strong> ${escapeHtml(r.url)}</div>`);
            if (r.warning) parts.push(`<div><strong>Warning:</strong> ${escapeHtml(r.warning)}</div>`);
            if (r.screenshot) {
                parts.push(
                    `<div><strong>Screenshot:</strong> ` +
                    `<a href="/screenshots/raw?path=${encodeURIComponent(r.screenshot)}" target="_blank">${escapeHtml(r.screenshot)}</a></div>`
                );
            }
            const detail = document.createElement("div");
            detail.className = "fail-detail";
            detail.innerHTML = parts.join("");
            document.getElementById("logLines").appendChild(detail);
        }
    });

    source.addEventListener("summary", (e) => {
        const data = JSON.parse(e.data);
        source.close();
        currentStepEl.textContent = "Replay finished.";

        summaryBanner.className = (data.status === "PASS") ? "pass" : "fail";
        summaryBanner.style.display = "block";

        let html =
            `<strong>${escapeHtml(data.status || "DONE")}</strong> - ${escapeHtml(data.message || "")}<br>` +
            `Total steps: ${data.total_steps} &nbsp; ` +
            `Passed: ${data.passed} &nbsp; ` +
            `Failed: ${data.failed} &nbsp; ` +
            `Skipped: ${data.skipped} &nbsp; ` +
            `Duration: ${data.duration_s}s`;

        if (data.html_report) {
            html += `<br><a href="/${data.html_report}" target="_blank">Open full HTML report</a>`;
        }

        summaryBanner.innerHTML = html;
    });

    // application-level errors the server sends deliberately (bad/unknown
    // run_id) - named "stream_error", NOT "error", specifically so this
    // never collides with EventSource's own native "error" event below
    // (a real dropped/failed connection), which carries no usable
    // message of its own at all
    source.addEventListener("stream_error", (e) => {
        const data = JSON.parse(e.data);
        errorBanner.textContent = data.message || "Something went wrong reading this replay's log.";
        errorBanner.style.display = "block";
        source.close();
    });

    // genuine connection failure (server restarted, network dropped) -
    // EventSource auto-retries on its own by default, so this is purely
    // informational, not fatal
    source.addEventListener("error", () => {
        if (errorBanner.style.display !== "block") {
            errorBanner.textContent = "Connection to the replay log was interrupted - retrying...";
            errorBanner.style.display = "block";
        }
    });

}

