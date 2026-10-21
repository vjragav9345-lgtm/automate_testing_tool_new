/* =========================================================
   RUN CONTROL (shared by the dashboard and the Recording Editor)
   While any replay is running - a full replay (MODE A) or a Run Until Selected Step run (MODE B) - every
   control marked data-af-run-control (the dashboard's Replay buttons, the editor's step Run icons) is
   disabled, and enabled again as soon as the run has ended (also when it stopped by itself). Reads
   /api/test/run/active; any error here is only logged and leaves the page as it is. (No floating banner: a
   run is stopped from the live log page or its cards.)
========================================================= */
(function () {
    "use strict";

    const POLL_MS = 1500;
    let state = { active: false, runs: [] };

    // disables the marked controls while a run is active; re-enables only the ones it disabled itself
    function apply() {
        try {
            document.querySelectorAll("[data-af-run-control]").forEach((el) => {
                if (state.active) {
                    if (!el.disabled) {
                        el.disabled = true;
                        el.dataset.afRunDisabled = "1";
                    }
                } else if (el.dataset.afRunDisabled === "1") {
                    el.disabled = false;
                    delete el.dataset.afRunDisabled;
                }
            });
        } catch (e) {
            console.warn("run control:", e);
        }
    }

    async function poll() {
        try {
            const r = await fetch("/api/test/run/active", { headers: { "Accept": "application/json" } });
            const data = await r.json();
            if (data && data.success) {
                state = { active: !!data.active, runs: Array.isArray(data.runs) ? data.runs : [] };
                apply();
            }
        } catch (e) {
            // the server may be restarting - the page stays as it is
        } finally {
            setTimeout(poll, POLL_MS);
        }
    }

    window.AFRunControl = {
        isActive: () => !!state.active,
        // called right after a page re-renders its controls, and right after it starts a run
        apply: apply,
        markActive: () => { state = { active: true, runs: state.runs || [] }; apply(); },
        refresh: () => { fetch("/api/test/run/active").then((r) => r.json()).then((d) => {
            if (d && d.success) { state = { active: !!d.active, runs: d.runs || [] }; apply(); }
        }).catch(() => {}); },
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", poll);
    } else {
        poll();
    }
})();
