console.log("==============================");
console.log("AutoFlow QA JavaScript Loaded");
console.log("==============================");


/* =========================================================
   ELEMENT REFERENCES
========================================================= */

const websiteUrlInput =
    document.getElementById(
        "websiteUrlInput"
    );

const launchBrowserBtn =
    document.getElementById(
        "launchBrowserBtn"
    );

const stopRecordingBtn =
    document.getElementById(
        "stopRecordingBtn"
    );

const recordingStatusPanel =
    document.getElementById(
        "recordingStatusPanel"
    );

const recordingStatusBadge =
    document.getElementById(
        "recordingStatusBadge"
    );

const recordingStatusMessage =
    document.getElementById(
        "recordingStatusMessage"
    );

const connectDbBtn =
    document.getElementById(
        "connectDbBtn"
    );

const systemStatusBtn =
    document.getElementById(
        "systemStatusBtn"
    );

const browserResultPanel =
    document.getElementById(
        "browserResultPanel"
    );

const visitedUrlValue =
    document.getElementById(
        "visitedUrlValue"
    );

const pageTitleValue =
    document.getElementById(
        "pageTitleValue"
    );

const statusValue =
    document.getElementById(
        "statusValue"
    );


const resultOutput =
    document.getElementById(
        "resultOutput"
    );


/* =========================================================
   RECORDING ELEMENTS
========================================================= */

const recordingsList =
    document.getElementById(
        "recordingsList"
    );

const recordingsLoading =
    document.getElementById(
        "recordingsLoading"
    );

const recordingsEmpty =
    document.getElementById(
        "recordingsEmpty"
    );

const recordingsError =
    document.getElementById(
        "recordingsError"
    );

const refreshRecordingsBtn =
    document.getElementById(
        "refreshRecordingsBtn"
    );

const recordingsPagination =
    document.getElementById(
        "recordingsPagination"
    );

const recordingsPrevBtn =
    document.getElementById(
        "recordingsPrevBtn"
    );

const recordingsNextBtn =
    document.getElementById(
        "recordingsNextBtn"
    );

const recordingsPageLabel =
    document.getElementById(
        "recordingsPageLabel"
    );


/* =========================================================
   RECORDING PAGINATION STATE - the full, already newest-first
   sorted list from /api/recordings is fetched once per load/refresh
   and kept here; renderRecordingsPage() slices PAGE_SIZE items out of
   it per page, so Previous/Next never re-fetch or re-sort anything.
========================================================= */

let allRecordings = [];
let currentPage = 1;
const PAGE_SIZE = 10;

// in-memory cache of the most recent Replay result per recording, keyed
// by recording.path - populated right after each successful Replay
// (see runRecording()) so "View Last Log" can render instantly without
// a network call for the current page session; lost on reload, at
// which point "View Last Log" falls back to /api/recordings/last_result
const lastResults = new Map();


/* =========================================================
   GENERIC API HELPER
========================================================= */

async function callApi(
    button,
    url,
    options = {}
) {

    if (button) {
        button.disabled = true;
    }


    try {

        const response =
            await fetch(
                url,
                options
            );


        const contentType =
            response.headers.get(
                "content-type"
            ) || "";


        /*
         * IMPORTANT:
         *
         * Never blindly call response.json().
         *
         * If Flask returns an HTML page,
         * JSON parsing gives:
         *
         * Unexpected token '<'
         *
         */

        if (
            !contentType.includes(
                "application/json"
            )
        ) {

            const text =
                await response.text();

            // the raw HTML (a Flask error page, most likely) is a
            // developer diagnostic - logged to the console, never shown
            // to the user as-is
            console.error(
                "Unexpected non-JSON response from " + url + ":",
                text.slice(0, 500)
            );

            throw new Error(
                "Something went wrong on the server. Please try again."
            );
        }


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "Request failed."
            );
        }


        if (resultOutput) {

            resultOutput.textContent =
                JSON.stringify(
                    data,
                    null,
                    2
                );
        }


        return data;

    }

    catch (error) {

        console.error(
            "API request failed:",
            error
        );


        if (resultOutput) {

            resultOutput.textContent =
                "Request failed: " +
                error.message;
        }


        return null;

    }

    finally {

        if (button) {
            button.disabled = false;
        }

    }
}


/* =========================================================
   RECORDING STATUS POLLING - drives the Stop Recording button and the
   Recording / Stopping... / Recording Completed / Recording Failed
   badge from /api/recording/status. Started the moment Launch Browser
   is clicked (so "launching" is visible even before that request
   resolves) and on page load (so reloading mid-recording still shows
   the real state), and kept running via setInterval only while a
   recording is actually in flight.
========================================================= */

const RECORDING_STATUS_LABELS = {
    launching: "Launching...",
    recording: "Recording",
    stopping: "Stopping...",
    completed: "Recording Completed",
    failed: "Recording Failed"
};

let recordingPollTimer = null;

function renderRecordingStatus(data) {

    if (!recordingStatusPanel) {
        return;
    }

    const phase = (data && data.phase) || "idle";
    const isActivePhase =
        phase === "launching" ||
        phase === "recording" ||
        phase === "stopping";

    if (phase === "idle") {
        recordingStatusPanel.hidden = true;
    } else {
        recordingStatusPanel.hidden = false;
        recordingStatusBadge.className =
            "recording-status-badge status-" + phase;
        recordingStatusBadge.textContent =
            RECORDING_STATUS_LABELS[phase] || phase;
        recordingStatusMessage.textContent =
            data.message ||
            (data.current_url ? "Recording " + data.current_url : "");
    }

    if (stopRecordingBtn) {
        stopRecordingBtn.hidden = !isActivePhase;
        stopRecordingBtn.disabled = phase !== "recording";
    }

    if (launchBrowserBtn) {
        launchBrowserBtn.disabled = isActivePhase;
    }

    if (isActivePhase && !recordingPollTimer) {
        recordingPollTimer = setInterval(pollRecordingStatusOnce, 1000);
    } else if (!isActivePhase && recordingPollTimer) {
        clearInterval(recordingPollTimer);
        recordingPollTimer = null;
        if (phase === "completed") {
            // the new recording is now saved on disk - refresh the
            // Recorded Tests list so it shows up without a manual reload
            loadRecordings();
            // PHASE 2a: this branch only runs once per completion (it's
            // gated by the active->inactive phase TRANSITION above, not
            // by every poll tick), so the modal is shown exactly once,
            // pre-filled with the auto name already computed server-side.
            openNameTestModal(data.recording_path, data.recording_name);
        }
    }
}

/* =========================================================
   PHASE 2a: "Name this test" modal - shown once right after a
   recording finishes. Skip (or closing without Save) keeps the
   auto-generated name exactly as it already is; Save calls the SAME
   set_display_name endpoint the dashboard card's own Rename action uses.
========================================================= */

const nameTestModal = document.getElementById("nameTestModal");
const nameTestInput = document.getElementById("nameTestInput");
const nameTestSkipBtn = document.getElementById("nameTestSkipBtn");
const nameTestSaveBtn = document.getElementById("nameTestSaveBtn");
let nameTestModalPath = null;

function openNameTestModal(recordingPath, autoName) {
    if (!nameTestModal || !recordingPath) return;
    nameTestModalPath = recordingPath;
    nameTestInput.value = autoName || "";
    nameTestModal.hidden = false;
}

function closeNameTestModal() {
    if (!nameTestModal) return;
    nameTestModal.hidden = true;
    nameTestModalPath = null;
}

if (nameTestSkipBtn) {
    nameTestSkipBtn.addEventListener("click", closeNameTestModal);
}

// FOLLOW-UP FIX 3: Enter = confirm, Esc = cancel, same as the newer
// Rename/Delete modals.
if (nameTestInput) {
    nameTestInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") nameTestSaveBtn && nameTestSaveBtn.click();
        else if (e.key === "Escape") closeNameTestModal();
    });
}

if (nameTestSaveBtn) {
    nameTestSaveBtn.addEventListener("click", async () => {
        const path = nameTestModalPath;
        const name = nameTestInput.value;
        closeNameTestModal();
        if (!path) return;
        try {
            const response = await fetch("/api/recordings/set_display_name", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({ path: path, display_name: name }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || "Couldn't save the name.");
            }
            loadRecordings(); // refresh the card so the new name shows immediately
        } catch (error) {
            console.error("set_display_name failed:", error);
        }
    });
}

/* =========================================================
   FOLLOW-UP FIX 3: "Rename this test" modal for the dashboard card's own
   Rename button - replaces the native prompt()/alert() it used to use.
   Same set_display_name endpoint as the modal above and the editor
   header's own Rename button.
========================================================= */

const renameCardModal = document.getElementById("renameCardModal");
const renameCardInput = document.getElementById("renameCardInput");
const renameCardError = document.getElementById("renameCardError");
const renameCardCancelBtn = document.getElementById("renameCardCancelBtn");
const renameCardSaveBtn = document.getElementById("renameCardSaveBtn");
let _renameCardContext = null; // { recording, title }

function openRenameCardModal(recording, title) {
    if (!renameCardModal) return;
    _renameCardContext = { recording, title };
    renameCardInput.value = recording.display_name || "";
    renameCardError.hidden = true;
    renameCardModal.hidden = false;
    renameCardInput.focus();
}

function closeRenameCardModal() {
    if (!renameCardModal) return;
    renameCardModal.hidden = true;
    _renameCardContext = null;
}

async function _saveRenameCard() {
    if (!_renameCardContext) return;
    const { recording, title } = _renameCardContext;
    const next = renameCardInput.value;
    renameCardSaveBtn.disabled = true;
    try {
        const response = await fetch("/api/recordings/set_display_name", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ path: recording.path, display_name: next }),
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || "Couldn't save the name.");
        }
        recording.display_name = data.display_name;
        title.textContent = recording.display_name || recording.name || "Unnamed Recording";
        closeRenameCardModal();
    } catch (error) {
        renameCardError.textContent = "Rename failed: " + error.message;
        renameCardError.hidden = false;
    } finally {
        renameCardSaveBtn.disabled = false;
    }
}

if (renameCardCancelBtn) {
    renameCardCancelBtn.addEventListener("click", closeRenameCardModal);
}
if (renameCardSaveBtn) {
    renameCardSaveBtn.addEventListener("click", _saveRenameCard);
}
if (renameCardInput) {
    renameCardInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") _saveRenameCard();
        else if (e.key === "Escape") closeRenameCardModal();
    });
}

async function pollRecordingStatusOnce() {

    try {

        const response =
            await fetch(
                "/api/recording/status",
                { headers: { "Accept": "application/json" } }
            );

        const data = await response.json();

        renderRecordingStatus(data);

    } catch (error) {
        // a transient network hiccup here just means the next tick (or
        // the next explicit call after Launch/Stop) retries - nothing to
        // surface to the user for a single missed poll
        console.error("recording status poll failed:", error);
    }
}


/* =========================================================
   LAUNCH BROWSER
========================================================= */

if (launchBrowserBtn) {

    launchBrowserBtn.addEventListener(
        "click",
        async () => {

            const url =
                websiteUrlInput.value.trim();


            // starts polling immediately (in parallel with the request
            // below, which doesn't resolve until the page has loaded and
            // recording has actually started or failed) so "Launching..."
            // is visible right away instead of only after that finishes
            pollRecordingStatusOnce();

            const data =
                await callApi(
                    launchBrowserBtn,
                    "/api/browser/launch",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        },

                        body:
                            JSON.stringify({
                                url: url
                            })
                    }
                );


            pollRecordingStatusOnce();


            if (!data) {
                return;
            }


            browserResultPanel.hidden =
                false;


            visitedUrlValue.textContent =
                data.url || "-";


            pageTitleValue.textContent =
                data.page_title || "-";


            statusValue.textContent =
                data.success
                    ? "Success - recording (use Stop Recording, or press ENTER in the terminal, to stop)"
                    : "Failed - " +
                      (
                          data.message ||
                          "unknown error"
                      );
        }
    );

}


/* =========================================================
   STOP RECORDING
========================================================= */

if (stopRecordingBtn) {

    stopRecordingBtn.addEventListener(
        "click",
        async () => {

            await callApi(
                stopRecordingBtn,
                "/api/recording/stop",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                }
            );

            pollRecordingStatusOnce();
        }
    );

}


// picks up an already-in-progress recording on page load/reload, so the
// dashboard reflects reality instead of always starting from "idle"
pollRecordingStatusOnce();


/* =========================================================
   DATABASE
========================================================= */

if (connectDbBtn) {

    connectDbBtn.addEventListener(
        "click",
        async () => {

            await callApi(
                connectDbBtn,
                "/api/database/connect"
            );

        }
    );

}


/* =========================================================
   SYSTEM STATUS
========================================================= */

if (systemStatusBtn) {

    systemStatusBtn.addEventListener(
        "click",
        async () => {

            await callApi(
                systemStatusBtn,
                "/status"
            );

        }
    );

}


/* =========================================================
   LOAD RECORDINGS
========================================================= */

async function loadRecordings() {

    console.log(
        "Loading JSON recordings..."
    );


    recordingsLoading.hidden =
        false;

    recordingsEmpty.hidden =
        true;

    recordingsError.hidden =
        true;


    recordingsList.innerHTML =
        "";


    try {

        const response =
            await fetch(
                "/api/recordings",
                {
                    method: "GET",

                    headers: {
                        "Accept":
                            "application/json"
                    }
                }
            );


        const contentType =
            response.headers.get(
                "content-type"
            ) || "";


        /*
         * THIS IS THE IMPORTANT FIX.
         *
         * If /api/recordings accidentally
         * returns index.html, we don't
         * call response.json().
         */

        if (
            !contentType.includes(
                "application/json"
            )
        ) {

            const text =
                await response.text();

            console.error(
                "Unexpected server response:",
                text.substring(
                    0,
                    200
                )
            );


            throw new Error(
                "Server returned HTML instead of JSON."
            );
        }


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Failed to load recordings."
            );
        }


        const recordings =
            Array.isArray(
                data.recordings
            )
                ? data.recordings
                : [];


        recordingsLoading.hidden =
            true;


        if (
            recordings.length === 0
        ) {

            recordingsEmpty.hidden =
                false;

            return;
        }


        allRecordings = recordings;
        renderRecordingsPage(1);


        console.log(
            "Recordings loaded:",
            recordings.length
        );

    }

    catch (error) {

        console.error(
            "Failed to load recordings:",
            error
        );


        recordingsLoading.hidden =
            true;


        recordingsError.textContent =
            "Failed to load recordings: " +
            error.message;


        recordingsError.hidden =
            false;
    }
}


/* =========================================================
   RENDER RECORDINGS PAGE - slices PAGE_SIZE items out of the already
   newest-first sorted allRecordings array and renders just that page,
   via the existing, unmodified createRecordingCard() - one call per
   item in the slice, exactly as it was already being called before.
========================================================= */

function renderRecordingsPage(page) {

    const totalPages =
        Math.max(
            1,
            Math.ceil(allRecordings.length / PAGE_SIZE)
        );

    const clampedPage =
        Math.min(
            Math.max(page, 1),
            totalPages
        );

    currentPage = clampedPage;

    recordingsList.innerHTML =
        "";

    const start =
        (clampedPage - 1) * PAGE_SIZE;

    const pageItems =
        allRecordings.slice(
            start,
            start + PAGE_SIZE
        );

    pageItems.forEach(
        recording => {

            createRecordingCard(
                recording
            );

        }
    );

    if (recordingsPagination) {

        recordingsPagination.hidden =
            allRecordings.length === 0;

        recordingsPageLabel.textContent =
            `Page ${clampedPage} of ${totalPages}`;

        recordingsPrevBtn.disabled =
            clampedPage <= 1;

        recordingsNextBtn.disabled =
            clampedPage >= totalPages;
    }
}


/* =========================================================
   CREATE RECORDING CARD
========================================================= */

function createRecordingCard(
    recording
) {

    const card =
        document.createElement(
            "div"
        );

    card.className =
        "recording-card";


    const title =
        document.createElement(
            "h3"
        );

    // PHASE 2c: display_name (large, the title) when this recording has
    // one - recording.name (the file's own auto name) still shows too,
    // via the existing "path"/"saved" lines just below, exactly as
    // before. Absent display_name (any recording saved before this
    // existed, or never named) falls back to showing recording.name as
    // the title, unchanged from today.
    title.textContent =
        recording.display_name || recording.name || "Unnamed Recording";


    const count =
        document.createElement(
            "span"
        );

    count.className =
        "action-count";

    count.textContent =
        `${recording.step_count || 0} actions`;


    const path =
        document.createElement(
            "p"
        );

    path.className =
        "recording-path";

    path.textContent =
        recording.path || "-";


    const saved =
        document.createElement(
            "p"
        );

    saved.className =
        "recording-saved";

    saved.textContent =
        recording.timestamp
            ? `Saved: ${recording.timestamp}`
            : "Saved: -";


    const buttons =
        document.createElement(
            "div"
        );

    buttons.className =
        "recording-buttons";


    const viewButton =
        document.createElement(
            "button"
        );

    viewButton.className =
        "action-btn";

    viewButton.textContent =
        "View / Edit";


    viewButton.addEventListener(
        "click",
        () => {

            const editorUrl =
                "/recording/edit?path=" +
                encodeURIComponent(
                    recording.path
                );


            window.location.href =
                editorUrl;
        }
    );


    buttons.appendChild(
        viewButton
    );


    const runButton =
        document.createElement(
            "button"
        );

    runButton.className =
        "action-btn";

    runButton.textContent =
        "Replay";

    const runResult =
        document.createElement(
            "div"
        );

    runResult.className =
        "editor-message";

    runResult.hidden =
        true;

    runButton.addEventListener(
        "click",
        () => runRecording(recording, runButton, runResult)
    );

    buttons.appendChild(
        runButton
    );


    // PHASE 2c: Rename action - same set_display_name endpoint the
    // editor header's own Rename button and the "Name this test" modal
    // both use.
    const renameButton =
        document.createElement(
            "button"
        );

    renameButton.className =
        "secondary-btn";

    renameButton.textContent =
        "Rename";

    // FOLLOW-UP FIX 3: opens the in-page renameCardModal instead of the
    // native prompt()/alert() this used to use.
    renameButton.addEventListener(
        "click",
        () => openRenameCardModal(recording, title)
    );

    buttons.appendChild(
        renameButton
    );


    const lastLogButton =
        document.createElement(
            "button"
        );

    lastLogButton.className =
        "secondary-btn";

    lastLogButton.textContent =
        "View Last Log";

    lastLogButton.addEventListener(
        "click",
        () => viewLastLog(recording, runResult)
    );

    buttons.appendChild(
        lastLogButton
    );


    const screenshotsButton =
        document.createElement(
            "button"
        );

    screenshotsButton.className =
        "secondary-btn";

    screenshotsButton.textContent =
        "Screenshots";

    screenshotsButton.addEventListener(
        "click",
        () => {
            window.location.href =
                "/screenshots?session=" +
                encodeURIComponent(
                    recording.name || ""
                );
        }
    );

    buttons.appendChild(
        screenshotsButton
    );


    const deleteButton =
        document.createElement(
            "button"
        );

    deleteButton.className =
        "action-btn stop-btn";

    deleteButton.textContent =
        "Delete";

    deleteButton.addEventListener(
        "click",
        () => deleteRecording(recording, deleteButton, runResult)
    );

    buttons.appendChild(
        deleteButton
    );


    card.appendChild(
        title
    );

    card.appendChild(
        count
    );

    card.appendChild(
        path
    );

    card.appendChild(
        saved
    );

    card.appendChild(
        buttons
    );

    card.appendChild(
        runResult
    );


    recordingsList.appendChild(
        card
    );
}


/* =========================================================
   VALIDATION RESULT PANEL - shared renderer used by both a fresh
   Replay result (Part 2) and "View Last Log" re-displaying a past
   result (Part 3), so the rendering logic exists in exactly one place.
========================================================= */

// plain-English label per recorded action type - no existing dropdown/
// mapping was found anywhere in this project's templates or JS to reuse
// (checked templates/ and static/ directly), so this is a small, new,
// self-contained mapping covering every action type this project's
// replay engine actually supports; any future/unknown action type still
// gets a reasonable label via the title-cased fallback below rather
// than showing raw snake_case.
const ACTION_TYPE_LABELS = {
    click: "Click",
    dblclick: "Double Click",
    right_click: "Right Click",
    fill: "Fill",
    select: "Select",
    submit: "Submit",
    press: "Key Press",
    scroll: "Scroll",
    navigate: "Navigate",
    tab_open: "Open Tab",
    tab_switch: "Switch Tab",
    tab_close: "Close Tab",
    validate: "Validate",
    click_if_exists: "Click If Exists",
    conditional_click: "Conditional Click",
    screenshot: "Screenshot",
    check: "Checkbox Toggle",
    check_checked: "Checkbox check",
    capture_value: "Capture Value",
    compare_value: "Compare Value",
    validate_element: "Validate Element",
    validate_text: "Validate Text",
    validate_attribute: "Validate Attribute",
    validate_visible: "Validate Visible",
    validate_url: "Validate URL",
    validate_value: "Validate Value",
    validate_enabled: "Validate Enabled",
    count_elements: "Count Elements",
    compare_counts: "Compare Counts",
    count_summary: "Count Summary",
    detect_duplicates: "Detect Duplicates",
    capture_list: "Capture List",
    compare_list_overlap: "Compare List Overlap",
    validate_value_range: "Validate Value Range",
    // ITEM 7 FIX: validate_checked was wired into replay/ACTION_FIELD_DEFS
    // but never added to this label map (or the other two copies this
    // codebase keeps - see templates/live_log.html and
    // templates/recording_editor.html's own ACTION_TYPE_LABELS).
    validate_checked: "Validate Checkbox State",
};

function actionTypeLabel(actionType) {

    if (!actionType) {
        return "(unknown step)";
    }

    if (ACTION_TYPE_LABELS[actionType]) {
        return ACTION_TYPE_LABELS[actionType];
    }

    return actionType
        .split("_")
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}


// action types whose own pass/fail IS an assertion about the page (a
// validate_*/check_checked/compare_*/detect_duplicates/... step), as
// opposed to an interaction (click/fill/...) or a passive data capture
// (capture_value/capture_list/count_elements/count_summary/screenshot) -
// same set recording_editor.html's own ACTION_FIELD_DEFS already marks
// `readOnly: true`, kept in sync with it by hand since that object lives
// in a different template and isn't reachable from here as data.
const VALIDATION_ACTION_TYPES = new Set([
    "validate", "validate_element", "validate_text", "validate_attribute",
    "validate_visible", "validate_url", "validate_value", "validate_enabled",
    "check_checked", "validate_value_range", "compare_value",
    "compare_counts", "count_summary", "detect_duplicates",
    "compare_list_overlap",
]);

// FOLLOW-UP FIX (Part 1d): mirrors plain_language_reason's own one new
// pattern in validation/report_generator.py (kept in sync with it by
// hand, same reason every other small JS/Python pair in this project
// is - script_generator.py's whole replay engine is one large
// string.Template, so its own text can't be imported here). Every OTHER
// warning's raw text is already plain (e.g. "Value changed on the
// site..." - see that Python function's own comment) and passes through
// unchanged; only this one technical string needs translating.
function _plainWarningText(warning) {
    if (warning && warning.indexOf("next recorded step's target never appeared") !== -1) {
        return "The page took longer than usual to show the next item. Continued anyway.";
    }
    return warning;
}

// FIX 4 (report/live-log correctness): a step the backend flagged as
// not_run (stop_on_failure halted before reaching it) or otp_role (a
// manual-input/OTP step that didn't itself fail) must never render as a
// plain failure - CONFIRMED REAL BUG this fixes, against an actual Myntra
// recording: 48 never-attempted steps were shown as red FAILED. Every
// place that used to read `step.success` directly for coloring/counting
// now goes through this instead, so all four outcomes (pass/fail/not_run/
// manual_input) stay visually and numerically distinct everywhere.
function _stepOutcome(step) {
    if (step.not_run) return "not_run";
    if (step.otp_role && step.success !== false) return "manual_input";
    // FOLLOW-UP FIX 2: a step that SUCCEEDED but carries a non-fatal
    // warning note (e.g. Fix 1's "Value changed on the site..." note) is
    // its own distinct outcome, not indistinguishable from a clean pass.
    if (step.success && step.warning) return "warning";
    return step.success ? "pass" : "fail";
}

// one plain-English line for a validation card, built entirely from
// fields the report already carries (expected/actual/locator_report/
// error) - never re-derives anything the backend didn't already compute
function _validationCardLine(step) {
    if (step.expected !== null && step.expected !== undefined && step.expected !== "") {
        const subject = (step.locator_report && step.locator_report.message)
            ? step.locator_report.message.split(" found using ")[0].split(" could not be resolved")[0]
            : actionTypeLabel(step.action_type);
        return step.success
            ? `${subject} equals ${JSON.stringify(step.expected)}`
            : `${subject} mismatch`;
    }
    return actionTypeLabel(step.action_type);
}

function renderValidationPanel(container, result) {

    container.innerHTML = "";
    container.className = "validation-panel";
    container.hidden = false;

    const passed = result.status === "PASS";
    const steps = Array.isArray(result.steps) ? result.steps : [];

    const badge = document.createElement("span");
    badge.className =
        "validation-badge " +
        (passed ? "validation-badge-pass" : "validation-badge-fail");
    badge.textContent = passed ? "TEST PASSED" : "TEST FAILED";
    container.appendChild(badge);

    // true once real validation cards render below - at that point the
    // stats line + cards already say everything the raw result.message
    // would, in a cleaner form, so that raw (terminal-style, e.g. "steps
    // failed: [2]") message is skipped rather than shown underneath it
    let hasValidationCards = false;

    if (steps.length > 0) {

        const validationSteps = steps.filter(s => VALIDATION_ACTION_TYPES.has(s.action_type));
        const actionSteps = steps.filter(s => !VALIDATION_ACTION_TYPES.has(s.action_type));
        // FOLLOW-UP FIX 2: "warning" still counts as passed here - it's a
        // distinct, yellow OUTCOME for a step that succeeded (see
        // _stepOutcome's own comment), not a third passed/failed bucket
        // these X/Y counts need to split out separately.
        const actionsPassed = actionSteps.filter(s => ["pass", "warning"].includes(_stepOutcome(s))).length;
        const validationsPassed = validationSteps.filter(s => ["pass", "warning"].includes(_stepOutcome(s))).length;
        const failedCount = steps.filter(s => _stepOutcome(s) === "fail").length;
        const notRunCount = steps.filter(s => _stepOutcome(s) === "not_run").length;
        const manualInputCount = steps.filter(s => _stepOutcome(s) === "manual_input").length;
        const warningCount = steps.filter(s => s.warning).length;
        const locatorWarnings = steps.filter(s => s.locator_report && s.locator_report.weak).length;

        const statsLine = document.createElement("p");
        statsLine.className = "validation-summary";
        const statsParts = [
            `${steps.length} step${steps.length === 1 ? "" : "s"} executed`,
            `${actionsPassed}/${actionSteps.length} action${actionSteps.length === 1 ? "" : "s"} passed`,
        ];
        if (validationSteps.length > 0) {
            statsParts.push(`${validationsPassed}/${validationSteps.length} validation${validationSteps.length === 1 ? "" : "s"} passed`);
        }
        statsParts.push(`${failedCount} failed`);
        if (notRunCount > 0) {
            statsParts.push(`${notRunCount} not run`);
        }
        if (manualInputCount > 0) {
            statsParts.push(`${manualInputCount} manual-input`);
        }
        // FOLLOW-UP FIX 2: "the Warnings counter shows the number" - shown
        // whenever there's at least one, same threshold convention as the
        // not-run/manual-input counts just above.
        if (warningCount > 0) {
            statsParts.push(`${warningCount} warning${warningCount === 1 ? "" : "s"}`);
        }
        if (locatorWarnings > 0) {
            statsParts.push(`${locatorWarnings} locator warning${locatorWarnings === 1 ? "" : "s"}`);
        }
        statsLine.textContent = statsParts.join(" · ");
        container.appendChild(statsLine);

        if (validationSteps.length > 0) {

            hasValidationCards = true;

            const cardsWrap = document.createElement("div");
            cardsWrap.className = "validation-cards";

            validationSteps.forEach(step => {

                const outcome = _stepOutcome(step);
                const card = document.createElement("div");
                card.className = "validation-card validation-card-" + outcome.replace("_", "-");

                const icons = { pass: "✓ ", warning: "⚠ ", fail: "✗ ", not_run: "○ ", manual_input: "🔐 " };
                const line = document.createElement("div");
                line.className = "validation-card-line";
                line.textContent = icons[outcome] + _validationCardLine(step);
                card.appendChild(line);

                if (outcome === "fail") {
                    const fields = [
                        ["Expected", step.expected],
                        ["Actual", step.actual],
                        ["Step", step.index],
                        ["Element", step.locator_report ? step.locator_report.strategy_label : null],
                    ];
                    fields.forEach(([label, value]) => {
                        if (value === null || value === undefined || value === "") {
                            return;
                        }
                        const row = document.createElement("div");
                        row.className = "validation-card-field";
                        row.textContent = `${label}: ${value}`;
                        card.appendChild(row);
                    });
                    if (step.screenshot) {
                        const shotLink = document.createElement("a");
                        shotLink.href = "/screenshots/raw?path=" + encodeURIComponent(step.screenshot);
                        shotLink.target = "_blank";
                        shotLink.rel = "noopener";
                        shotLink.textContent = "Screenshot: View";
                        shotLink.className = "validation-card-field validation-card-screenshot";
                        card.appendChild(shotLink);
                    }
                }

                cardsWrap.appendChild(card);
            });

            container.appendChild(cardsWrap);
        }
    }

    if (!hasValidationCards && result.message) {
        const summary = document.createElement("p");
        summary.className = "validation-summary";
        summary.textContent = result.message;
        container.appendChild(summary);
    }

    if (steps.length > 0) {

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "secondary-btn validation-toggle";
        toggle.textContent = `Show all steps (${steps.length})`;

        const stepList = document.createElement("div");
        stepList.className = "validation-steps";
        stepList.hidden = true;

        steps.forEach(step => {

            const row = document.createElement("div");
            row.className = "validation-step-row";

            const stepOutcome = _stepOutcome(step);
            const icon = document.createElement("span");
            icon.className = "validation-step-icon";
            icon.textContent = { pass: "✅", warning: "⚠️", fail: "❌", not_run: "⚪", manual_input: "🔐" }[stepOutcome];

            // FOLLOW-UP FIX 5: an explicit step.name (set by the Recording
            // Editor's auto-namer for an added step, or a manual rename)
            // is far more meaningful than the generic action-type label -
            // see _step_element_label's own equivalent preference in
            // app.py for the live log.
            const label = document.createElement("span");
            label.textContent = (step.name && step.name.trim()) || actionTypeLabel(step.action_type);

            row.appendChild(icon);
            row.appendChild(label);
            row.className += " validation-step-row-" + stepOutcome.replace("_", "-");

            // plain-English locator resolution message (see
            // _describe_locator_resolution in script_generator.py) -
            // raw selector strings are never shown here, only in the
            // downloadable HTML report's own "Advanced" detail
            if (step.locator_report && step.locator_report.message) {
                const locatorLine = document.createElement("div");
                locatorLine.className =
                    "validation-step-locator" +
                    (step.locator_report.weak ? " validation-step-locator-weak" : "");
                locatorLine.textContent = step.locator_report.message;
                row.appendChild(locatorLine);
            }

            if (stepOutcome !== "pass" && stepOutcome !== "warning" && step.error) {
                const reason = document.createElement("div");
                reason.className = "validation-step-reason";
                reason.textContent = step.error;
                row.appendChild(reason);
            }

            // FOLLOW-UP FIX 2: a passing step's own warning note (e.g.
            // Fix 1's "Value changed on the site..." note) - never shown
            // before, since only a non-passing step's `error` was ever
            // rendered here.
            if (step.warning) {
                const warningNote = document.createElement("div");
                warningNote.className = "validation-step-warning";
                warningNote.textContent = _plainWarningText(step.warning);
                row.appendChild(warningNote);
            }

            // PHASE 5b: one line per stored count, under this Count
            // Summary step specifically - the exact same label/count/
            // expected/result data the HTML report's own table shows
            // (see generator/script_generator.py's count_summary branch,
            // count_summary_rows), nothing re-run or re-counted here.
            if (Array.isArray(step.count_summary_rows) && step.count_summary_rows.length) {
                const summaryList = document.createElement("div");
                summaryList.className = "validation-step-locator";
                summaryList.innerHTML = step.count_summary_rows.map(r => {
                    const mark = (r.expected === null || r.expected === undefined) ? "" :
                        (r.ok ? " ✓" : " ✗");
                    const expectedPart = (r.expected === null || r.expected === undefined) ? "" : ` (expected ${r.expected})`;
                    return `${r.label} = ${r.count}${expectedPart}${mark}`;
                }).join("<br>");
                row.appendChild(summaryList);
            }

            stepList.appendChild(row);
        });

        toggle.addEventListener("click", () => {
            const willShow = stepList.hidden;
            stepList.hidden = !willShow;
            toggle.textContent = willShow
                ? `Hide all steps (${steps.length})`
                : `Show all steps (${steps.length})`;
        });

        container.appendChild(toggle);
        container.appendChild(stepList);
    }
}


/* =========================================================
   LIVE REPLAY PROGRESS - renders the in-flight step list (done/current/
   pending), pass/fail/warning counts and elapsed time for one async
   replay, from whatever /api/test/run/progress last returned. Read-only
   rendering only - all the real state lives server-side (see
   executor/run_execution.py's start_replay()/poll_replay()); this just
   reflects it.
========================================================= */

function renderReplayProgress(container, data, elapsedMs) {

    container.innerHTML = "";
    container.className = "replay-progress-panel";
    container.hidden = false;

    const totalSteps = data.total_steps || 0;
    const doneSteps = Array.isArray(data.steps) ? data.steps : [];

    const header = document.createElement("div");
    header.className = "replay-progress-header";
    header.textContent =
        (data.test_name || "Replay") +
        " - step " + Math.min(doneSteps.length + 1, totalSteps || doneSteps.length + 1) +
        " of " + (totalSteps || "?");
    container.appendChild(header);

    // FIX 4: Passed/Failed/Not run/Manual-input as their own counts,
    // recomputed from the steps actually reported so far via
    // _stepOutcome() - a step_counts field on `data` server-side isn't
    // guaranteed to exist yet mid-run (poll_replay() streams the raw,
    // in-progress report; step_counts is only added by _finalize_result()
    // once the run is fully done), so this stays accurate throughout.
    const liveCounts = { pass: 0, warning: 0, fail: 0, not_run: 0, manual_input: 0 };
    doneSteps.forEach(s => { liveCounts[_stepOutcome(s)]++; });

    const counts = document.createElement("div");
    counts.className = "replay-progress-counts";
    counts.innerHTML =
        "<span class=\"count-passed\">Passed: " + liveCounts.pass + "</span>" +
        "<span class=\"count-failed\">Failed: " + liveCounts.fail + "</span>" +
        "<span class=\"count-not-run\">Not run: " + liveCounts.not_run + "</span>" +
        "<span class=\"count-manual-input\">Manual-input: " + liveCounts.manual_input + "</span>" +
        "<span class=\"count-warnings\">Warnings: " + (data.warnings || 0) + "</span>" +
        "<span class=\"count-elapsed\">Elapsed: " + (elapsedMs / 1000).toFixed(1) + "s</span>";
    container.appendChild(counts);

    const list = document.createElement("div");
    list.className = "replay-progress-steps";

    for (let i = 1; i <= (totalSteps || doneSteps.length); i++) {

        const stepResult = doneSteps.find(s => s.index === i);
        const row = document.createElement("div");
        row.className = "replay-progress-step-row";

        const icon = document.createElement("span");
        icon.className = "replay-progress-step-icon";

        const label = document.createElement("span");

        if (stepResult) {
            const outcome = _stepOutcome(stepResult);
            icon.textContent = { pass: "✓", warning: "⚠", fail: "✗", not_run: "○", manual_input: "🔐" }[outcome];
            icon.classList.add("step-" + outcome.replace("_", "-"));
            // FOLLOW-UP FIX 5: an explicit step.name (Recording Editor
            // auto-namer, or a manual rename) beats the generic action-
            // type label - same preference as _step_element_label in
            // app.py and renderValidationPanel's own step list above.
            label.textContent = (stepResult.name && stepResult.name.trim()) || actionTypeLabel(stepResult.action_type);
        } else if (i === doneSteps.length + 1) {
            icon.textContent = "⏳";
            icon.classList.add("step-current");
            label.textContent = "Running...";
        } else {
            icon.textContent = "○";
            icon.classList.add("step-pending");
            label.textContent = "Pending";
        }

        row.appendChild(icon);
        row.appendChild(label);

        // FOLLOW-UP FIX 2/6: a passing step's own warning note, and any
        // count_elements/count_summary numbers it collected - shown
        // during the in-progress view too, not just the final one.
        if (stepResult && stepResult.warning) {
            const note = document.createElement("div");
            note.className = "replay-progress-step-note";
            note.textContent = _plainWarningText(stepResult.warning);
            row.appendChild(note);
        }
        if (stepResult && Array.isArray(stepResult.count_summary_rows) && stepResult.count_summary_rows.length) {
            const countNote = document.createElement("div");
            countNote.className = "replay-progress-step-note";
            countNote.innerHTML = stepResult.count_summary_rows.map(r => {
                const mark = (r.expected === null || r.expected === undefined) ? "" : (r.ok ? " ✓" : " ✗");
                const expectedPart = (r.expected === null || r.expected === undefined) ? "" : ` (expected ${r.expected})`;
                return `${r.label} = ${r.count}${expectedPart}${mark}`;
            }).join("<br>");
            row.appendChild(countNote);
        }

        list.appendChild(row);
    }

    container.appendChild(list);
}


/* =========================================================
   REPLAY A RECORDING - starts an async replay (/api/test/run/start),
   then polls /api/test/run/progress until it's done, rendering live
   step-by-step progress the whole time instead of a single opaque
   "Replaying..." message. Same underlying engine as before (the
   blocking /api/test/run route is untouched and still used by anything
   else that calls it) - this just adds a way to watch it happen.
========================================================= */

const REPLAY_POLL_INTERVAL_MS = 800;

async function runRecording(recording, runButton, runResult) {

    runButton.disabled = true;
    runResult.hidden = true;
    runResult.className = "editor-message";
    runResult.textContent = "Starting replay...";
    runResult.hidden = false;

    try {

        const viewUrl =
            "/api/recordings/view?path=" +
            encodeURIComponent(recording.path);

        const viewResponse = await fetch(viewUrl, {
            headers: { "Accept": "application/json" }
        });

        const viewData = await viewResponse.json();

        if (!viewResponse.ok || !viewData.success) {
            throw new Error(viewData.message || "Couldn't load this recording.");
        }

        const startUrl = viewData.recording.start_url || "";

        const startResponse = await fetch("/api/test/run/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                qa_url: startUrl,
                recording_path: recording.path
            })
        });

        const startData = await startResponse.json();

        if (!startResponse.ok || !startData.success) {
            throw new Error(startData.message || "Couldn't start the replay.");
        }

        const runId = startData.run_id;
        const startedAt = Date.now();

        // opens the live log in its OWN separate browser window/tab, not
        // an in-page panel - the replay's own Chromium window (a totally
        // separate OS-level browser process, launched headed so the user
        // can watch it) otherwise covers this same dashboard tab for the
        // whole run, with nothing left visible to show progress on. A
        // popup is a different window entirely, so the replay browser
        // opening/closing can never hide or close it. Positioned in the
        // top-right corner of the screen; the replay browser itself is
        // launched at a fixed top-left position/size (see
        // generator/script_generator.py's run()) so the two sit side by
        // side without overlapping on a normal single-monitor setup.
        // Reuses the SAME window name across runs (not appending runId)
        // so re-running a recording updates the existing popup instead of
        // piling up a new one each time; a popup blocked by the browser
        // is a silent no-op here - live progress still fully works via
        // the polling loop below regardless.
        try {
            const logWidth = 460;
            const logLeft = Math.max(0, (window.screen.availWidth || 1280) - logWidth - 10);
            window.open(
                "/logs?run_id=" + encodeURIComponent(runId),
                "autoflow_live_log",
                `width=${logWidth},height=760,left=${logLeft},top=20,resizable=yes,scrollbars=yes`
            );
        } catch (popupErr) {
            console.warn("Couldn't open the live log window:", popupErr);
        }

        // polls until the run reports done - a run that never finishes
        // (a genuinely hung subprocess) is still bounded server-side by
        // the executor's own per-run timeout, so this loop always ends
        // one way or another once that fires
        const runData = await new Promise((resolve, reject) => {

            const poll = async () => {

                try {

                    const progressUrl =
                        "/api/test/run/progress?run_id=" + encodeURIComponent(runId);

                    const progressResponse = await fetch(progressUrl, {
                        headers: { "Accept": "application/json" }
                    });

                    const progressData = await progressResponse.json();

                    if (!progressResponse.ok || !progressData.success) {
                        reject(new Error(progressData.message || "Lost track of the replay in progress."));
                        return;
                    }

                    if (progressData.done) {
                        resolve(progressData);
                        return;
                    }

                    renderReplayProgress(
                        runResult,
                        { ...progressData, test_name: progressData.test_name || startData.test_name },
                        Date.now() - startedAt
                    );

                    setTimeout(poll, REPLAY_POLL_INTERVAL_MS);

                } catch (pollError) {
                    reject(pollError);
                }
            };

            poll();
        });

        lastResults.set(recording.path, runData);
        renderValidationPanel(runResult, runData);

        if (runData.json_report) {
            const runDir = runData.json_report.replace(/\/report\.json$/, "");

            const stagesLink = document.createElement("a");
            stagesLink.href = "/run/stages?run_dir=" + encodeURIComponent(runDir);
            stagesLink.textContent = "View Screenshots by Stage";
            stagesLink.style.display = "block";
            stagesLink.style.marginTop = "8px";

            runResult.appendChild(stagesLink);
        }

    } catch (error) {

        console.error("Run failed:", error);
        runResult.className = "editor-error";
        runResult.textContent = "Run failed: " + error.message;
        runResult.hidden = false;

    } finally {
        runButton.disabled = false;
    }
}


/* =========================================================
   VIEW LAST VALIDATION LOG - re-displays a session's most recent
   Replay result without re-running it. Checks the in-memory cache
   first (populated by runRecording() above); falls back to the new
   read-only /api/recordings/last_result route (e.g. after a page
   reload, when nothing is cached). Reuses renderValidationPanel() for
   the actual rendering either way - no duplicated rendering logic.
========================================================= */

// FOLLOW-UP FIX 3: replaces the native confirm() this used to use - opens
// the in-page deleteCardModal instead; the actual deletion (unchanged)
// only runs once the user confirms there, via _performDeleteRecording.
const deleteCardModal = document.getElementById("deleteCardModal");
const deleteCardMessage = document.getElementById("deleteCardMessage");
const deleteCardCancelBtn = document.getElementById("deleteCardCancelBtn");
const deleteCardConfirmBtn = document.getElementById("deleteCardConfirmBtn");
let _deleteCardContext = null; // { recording, button, container }

function deleteRecording(recording, button, container) {
    if (!deleteCardModal) return;
    _deleteCardContext = { recording, button, container };
    deleteCardMessage.textContent =
        "Delete session \"" + (recording.name || recording.path) + "\"? " +
        "This permanently deletes its recording, generated scripts, " +
        "screenshots and reports.";
    deleteCardModal.hidden = false;
}

function closeDeleteCardModal() {
    if (!deleteCardModal) return;
    deleteCardModal.hidden = true;
    _deleteCardContext = null;
}

async function _performDeleteRecording() {
    if (!_deleteCardContext) return;
    const { recording, button, container } = _deleteCardContext;
    closeDeleteCardModal();

    button.disabled = true;

    try {

        const response = await fetch("/api/recordings/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ path: recording.path })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Couldn't delete the session.");
        }

        lastResults.delete(recording.path);
        await loadRecordings();

    } catch (error) {

        console.error("Delete failed:", error);
        button.disabled = false;
        container.innerHTML = "";
        container.className = "editor-error";
        container.textContent = "Couldn't delete this session: " + error.message;
        container.hidden = false;
    }
}

if (deleteCardCancelBtn) {
    deleteCardCancelBtn.addEventListener("click", closeDeleteCardModal);
}
if (deleteCardConfirmBtn) {
    deleteCardConfirmBtn.addEventListener("click", _performDeleteRecording);
}
document.addEventListener("keydown", (e) => {
    if (deleteCardModal && !deleteCardModal.hidden && e.key === "Escape") closeDeleteCardModal();
});


async function viewLastLog(recording, container) {

    if (lastResults.has(recording.path)) {
        renderValidationPanel(container, lastResults.get(recording.path));
        return;
    }

    container.innerHTML = "";
    container.className = "editor-message";
    container.textContent = "Loading last result...";
    container.hidden = false;

    try {

        const url =
            "/api/recordings/last_result?path=" +
            encodeURIComponent(recording.path);

        const response = await fetch(url, {
            headers: { "Accept": "application/json" }
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Couldn't load the last result.");
        }

        if (!data.found) {
            container.className = "editor-message";
            container.textContent =
                data.message || "No replay has been run yet for this session.";
            container.hidden = false;
            return;
        }

        lastResults.set(recording.path, data);
        renderValidationPanel(container, data);

    } catch (error) {

        console.error("View Last Log failed:", error);
        container.className = "editor-error";
        container.textContent = "Couldn't load the last result: " + error.message;
        container.hidden = false;
    }
}


/* =========================================================
   REFRESH RECORDINGS
========================================================= */

if (refreshRecordingsBtn) {

    refreshRecordingsBtn.addEventListener(
        "click",
        loadRecordings
    );

}


/* =========================================================
   RECORDINGS PAGINATION CONTROLS
========================================================= */

if (recordingsPrevBtn) {

    recordingsPrevBtn.addEventListener(
        "click",
        () => renderRecordingsPage(currentPage - 1)
    );

}

if (recordingsNextBtn) {

    recordingsNextBtn.addEventListener(
        "click",
        () => renderRecordingsPage(currentPage + 1)
    );

}


/* =========================================================
   PAGE LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        console.log(
            "DOM Loaded successfully."
        );


        /*
         * Only load recordings when
         * the Recorded Tests section
         * exists.
         */

        if (
            recordingsList
        ) {

            loadRecordings();

        }

    }
);