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

            throw new Error(
                "Server returned HTML instead of JSON."
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
   LAUNCH BROWSER
========================================================= */

if (launchBrowserBtn) {

    launchBrowserBtn.addEventListener(
        "click",
        async () => {

            const url =
                websiteUrlInput.value.trim();


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
                    ? "Success - recording in terminal"
                    : "Failed - " +
                      (
                          data.message ||
                          "unknown error"
                      );
        }
    );

}


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


        recordings.forEach(
            recording => {

                createRecordingCard(
                    recording
                );

            }
        );


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

    title.textContent =
        recording.name || "Unnamed Recording";


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


    recordingsList.appendChild(
        card
    );
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