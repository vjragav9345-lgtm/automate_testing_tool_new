/* REMOTE LIVE BROWSER panel (cloud server only - see remote_view.py).
   Asks /api/remote_view/status once. When the server is NOT in remote mode (every local Windows / macOS run) it
   stops right there: no panel, no further requests, nothing else on the page is touched. In remote mode it builds
   its own floating "Live Browser" panel (own element ids, nothing existing is changed), shows the latest frame of
   the server's active page, and - while the panel is focused - sends mouse and keyboard input to it.
   Every error is only logged to the console. */
(function () {
    "use strict";

    var FRAME_POLL_MS = 150;        // while a live browser is active
    var IDLE_POLL_MS = 1500;        // while nothing is live
    var MOVE_THROTTLE_MS = 50;      // mouse moves sent at most this often
    var FLUSH_MS = 40;              // input batch interval

    var state = { seq: 0, width: 0, height: 0, input: false, active: false, minimized: false };
    var pending = [];
    var lastMove = 0;
    var flushTimer = null;
    var els = {};

    function log(msg, err) {
        try { console.log("[remote-view] " + msg, err || ""); } catch (e) {}
    }

    function getJSON(url) {
        return fetch(url, { headers: { "Accept": "application/json" } }).then(function (r) { return r.json(); });
    }

    function buildPanel() {
        var panel = document.createElement("div");
        panel.id = "afqaRemotePanel";
        panel.style.cssText = "position:fixed;right:12px;bottom:12px;width:min(46vw,760px);z-index:99990;" +
            "background:#fff;border:1px solid #c9ced6;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.18);" +
            "font:13px sans-serif;display:none;overflow:hidden;";

        var head = document.createElement("div");
        head.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px 8px;background:#f3f5f8;" +
            "border-bottom:1px solid #e1e5ea;";
        var title = document.createElement("strong");
        title.textContent = "Live Browser";
        var source = document.createElement("span");
        source.id = "afqaRemoteSource";
        source.style.cssText = "color:#5b6573;font-size:12px;";
        var url = document.createElement("input");
        url.id = "afqaRemoteUrl";
        url.type = "text";
        url.readOnly = true;
        url.style.cssText = "flex:1;min-width:0;font-size:12px;padding:2px 6px;border:1px solid #d5d9df;" +
            "border-radius:4px;background:#fff;color:#333;";
        var toggle = document.createElement("button");
        toggle.id = "afqaRemoteToggle";
        toggle.type = "button";
        toggle.textContent = "–";
        toggle.title = "Minimize / restore";
        toggle.style.cssText = "border:1px solid #d5d9df;background:#fff;border-radius:4px;cursor:pointer;padding:0 8px;";
        head.appendChild(title);
        head.appendChild(source);
        head.appendChild(url);
        head.appendChild(toggle);

        var body = document.createElement("div");
        body.id = "afqaRemoteBody";
        body.tabIndex = 0;
        body.style.cssText = "position:relative;display:flex;align-items:center;justify-content:center;" +
            "background:#20242a;height:min(58vh,480px);outline:none;";
        var img = document.createElement("img");
        img.id = "afqaRemoteImage";
        img.alt = "Live browser";
        img.draggable = false;
        img.style.cssText = "display:block;user-select:none;cursor:default;";
        var hint = document.createElement("div");
        hint.id = "afqaRemoteHint";
        hint.style.cssText = "position:absolute;left:8px;bottom:6px;color:#cfd6df;font-size:11px;pointer-events:none;";
        body.appendChild(img);
        body.appendChild(hint);

        panel.appendChild(head);
        panel.appendChild(body);
        document.body.appendChild(panel);

        els = { panel: panel, source: source, url: url, toggle: toggle, body: body, img: img, hint: hint };

        toggle.addEventListener("click", function () {
            state.minimized = !state.minimized;
            body.style.display = state.minimized ? "none" : "flex";
            toggle.textContent = state.minimized ? "+" : "–";
        });
        body.addEventListener("focus", function () { body.style.boxShadow = "inset 0 0 0 2px #ff4081"; updateHint(); });
        body.addEventListener("blur", function () { body.style.boxShadow = "none"; updateHint(); });
        attachInput();
    }

    function updateHint() {
        if (!els.hint) return;
        if (!state.input) {
            els.hint.textContent = "View only";
        } else {
            els.hint.textContent = (document.activeElement === els.body)
                ? "Controlling the live browser - click outside to release"
                : "Click to control the live browser";
        }
    }

    function fitImage() {
        try {
            if (!state.width || !state.height || !els.body) return;
            var bw = els.body.clientWidth, bh = els.body.clientHeight;
            if (!bw || !bh) return;
            var scale = Math.min(bw / state.width, bh / state.height);
            els.img.style.width = Math.max(1, Math.floor(state.width * scale)) + "px";
            els.img.style.height = Math.max(1, Math.floor(state.height * scale)) + "px";
        } catch (e) { log("fit failed", e); }
    }

    // panel coordinates -> the page's own viewport coordinates (from the real frame size, never a fixed size)
    function toPage(e) {
        var r = els.img.getBoundingClientRect();
        if (!r.width || !r.height || !state.width || !state.height) return null;
        var x = (e.clientX - r.left) * state.width / r.width;
        var y = (e.clientY - r.top) * state.height / r.height;
        if (x < 0 || y < 0 || x > state.width || y > state.height) return null;
        return { x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 };
    }

    function send(ev) {
        if (!state.input || !state.active) return;
        pending.push(ev);
        if (!flushTimer) flushTimer = setTimeout(flush, FLUSH_MS);
    }

    function flush() {
        flushTimer = null;
        if (!pending.length) return;
        var batch = pending;
        pending = [];
        try {
            fetch("/api/remote_view/input", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify({ events: batch }),
            }).catch(function (err) { log("input not sent", err); });
        } catch (e) { log("input not sent", e); }
    }

    var BUTTONS = { 0: "left", 1: "middle", 2: "right" };

    function attachInput() {
        var body = els.body;
        body.addEventListener("mousedown", function (e) {
            try {
                body.focus();
                var p = toPage(e);
                if (!p) return;
                e.preventDefault();
                send({ type: "down", x: p.x, y: p.y, button: BUTTONS[e.button] || "left", clickCount: e.detail || 1 });
            } catch (err) { log("mousedown", err); }
        });
        body.addEventListener("mouseup", function (e) {
            try {
                var p = toPage(e);
                if (!p) return;
                e.preventDefault();
                send({ type: "up", x: p.x, y: p.y, button: BUTTONS[e.button] || "left", clickCount: e.detail || 1 });
            } catch (err) { log("mouseup", err); }
        });
        body.addEventListener("mousemove", function (e) {
            try {
                var now = Date.now();
                if (now - lastMove < MOVE_THROTTLE_MS) return;
                var p = toPage(e);
                if (!p) return;
                lastMove = now;
                send({ type: "move", x: p.x, y: p.y });
            } catch (err) { log("mousemove", err); }
        });
        // clicks / double-clicks happen on the page itself from the forwarded down / up (with their click count)
        body.addEventListener("contextmenu", function (e) { e.preventDefault(); });
        body.addEventListener("dblclick", function (e) { e.preventDefault(); });
        body.addEventListener("wheel", function (e) {
            try {
                var p = toPage(e);
                if (!p) return;
                e.preventDefault();          // the dashboard itself never scrolls while over the panel
                var k = e.deltaMode === 1 ? 16 : (e.deltaMode === 2 ? (state.height || 1) : 1);
                send({ type: "wheel", x: p.x, y: p.y, dx: e.deltaX * k, dy: e.deltaY * k });
            } catch (err) { log("wheel", err); }
        }, { passive: false });
        // keys only while the panel itself is focused (the listeners are on the panel, never on the page)
        body.addEventListener("keydown", function (e) {
            try {
                if (!state.input) return;
                e.preventDefault();
                e.stopPropagation();
                var printable = e.key && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey;
                if (printable) {
                    send({ type: "text", text: e.key });
                } else if (e.key && e.key !== "Unidentified" && e.key !== "Dead") {
                    send({ type: "keydown", key: e.key });
                }
            } catch (err) { log("keydown", err); }
        });
        body.addEventListener("keyup", function (e) {
            try {
                if (!state.input) return;
                e.preventDefault();
                e.stopPropagation();
                var printable = e.key && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey;
                if (!printable && e.key && e.key !== "Unidentified" && e.key !== "Dead") {
                    send({ type: "keyup", key: e.key });
                }
            } catch (err) { log("keyup", err); }
        });
        window.addEventListener("resize", fitImage);
    }

    function show(on) {
        if (!els.panel) return;
        els.panel.style.display = on ? "block" : "none";
        if (!on && document.activeElement === els.body) {
            try { els.body.blur(); } catch (e) {}
        }
    }

    function poll() {
        getJSON("/api/remote_view/frame?after=" + encodeURIComponent(state.seq)).then(function (d) {
            if (!d || d.remote === false) return;            // remote mode went away: stop quietly
            state.active = !!d.active && (d.changed === true || !!d.seq || state.seq > 0);
            if (!d.active) {
                state.active = false;
                state.seq = 0;
                show(false);
                setTimeout(poll, IDLE_POLL_MS);
                return;
            }
            state.input = !!d.input;
            if (d.changed && d.data) {
                state.seq = d.seq || 0;
                if (d.width && d.height && (d.width !== state.width || d.height !== state.height)) {
                    state.width = d.width;
                    state.height = d.height;
                    fitImage();
                }
                els.img.src = "data:image/jpeg;base64," + d.data;
            }
            if (d.width && d.height && !els.img.style.width) {
                state.width = d.width;
                state.height = d.height;
                fitImage();
            }
            els.source.textContent = d.source ? "(" + d.source + ")" : "";
            if (typeof d.url === "string" && els.url.value !== d.url) els.url.value = d.url;
            state.active = true;
            show(true);
            updateHint();
            setTimeout(poll, FRAME_POLL_MS);
        }).catch(function (err) {
            log("frame poll failed", err);
            setTimeout(poll, IDLE_POLL_MS);
        });
    }

    function init() {
        getJSON("/api/remote_view/status").then(function (s) {
            if (!s || s.remote !== true) return;            // local run: nothing at all
            buildPanel();
            poll();
        }).catch(function (err) {
            log("not available", err);
        });
    }

    try {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", init);
        } else {
            init();
        }
    } catch (e) {
        log("init failed", e);
    }
})();
