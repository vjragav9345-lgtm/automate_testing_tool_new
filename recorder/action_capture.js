// Injected once per page load. Always listens and always forwards to
// Python via window.recordAction - whether an event actually gets kept as
// a recorded step is decided on the Python side (Recorder.recording), not
// here. Keeping the on/off switch out of page JS means it can't survive a
// navigation and silently start capturing again after a recording ends.
(function () {
    // VERSION MARKER - bump this literal string on every meaningful
    // change to this file. _CAPTURE_JS (recorder/record_session.py)
    // reads this file's TEXT once, at process import time, into a
    // module-level constant - with the Flask app run with debug=False
    // (no reloader at all, and even Werkzeug's reloader only ever
    // watches .py files by default, never .js ones), a running server
    // process can silently keep serving whatever this string contained
    // when IT started, no matter how many times this file changes on
    // disk afterward. Logging this once per page, right when pick mode
    // activates, is the one-line, impossible-to-misread way to confirm
    // whether a given browser session is actually running current code
    // instead of inferring it from symptoms.
    window.__afqaCaptureVersion = "2026-10-07-a";
    if (window.__afqaPickMode) {
        console.log("[afqa-pick] action_capture.js version:", window.__afqaCaptureVersion);
    }

    if (window.__afqaListenersAttached) return;
    window.__afqaListenersAttached = true;

    // ==================================================================
    // PICK ELEMENT MODE - OVERLAY SETUP. Only ever runs when recorder/
    // pick_element.py's own init script has already set window.
    // __afqaPickMode = true before this script executes (normal
    // recording never sets that flag, so this whole block is always
    // skipped then - zero effect on recording). A single full-viewport,
    // ALWAYS-pointer-events-auto div, created once per page load and
    // left in place for the entire pick session, physically sitting on
    // top of everything else on the page (z-index: 2147483647, the
    // maximum valid CSS z-index) so it is the one and only element that
    // ever receives a real mousemove/click while picking is active - the
    // real page underneath NEVER gets a live pointer event of its own,
    // so no real :hover CSS, tooltip, or JS mouseover/mouseenter handler
    // can ever fire on it during picking. This is deliberately NOT the
    // "elementFromPoint() + toggle pointer-events to none" approach: that
    // technique briefly exposes the real page to real events on every
    // single mousemove tick specifically so elementFromPoint can see
    // past the overlay, which is exactly the leak this design avoids by
    // construction - pointer-events on the overlay is set once, to
    // 'auto', and never touched again for as long as picking lasts.
    // Finding "what's really under the cursor" instead uses
    // document.elementsFromPoint(x, y) (plural) on the SAME event,
    // which returns the whole stack of elements at that point without
    // needing the overlay to step aside at all - the overlay (and the
    // highlight box, if it happens to be under the cursor too) is simply
    // skipped when reading that stack.
    function _afqaSetupPickOverlay() {
        if (window.__afqaPickOverlay) return; // idempotent - safe if called more than once

        var overlay = document.createElement('div');
        overlay.id = '__afqaPickOverlay';
        overlay.style.cssText =
            'position:fixed;top:0;left:0;width:100vw;height:100vh;' +
            'z-index:2147483647;background:transparent;cursor:crosshair;';
        (document.body || document.documentElement).appendChild(overlay);
        window.__afqaPickOverlay = overlay;

        var highlight = document.createElement('div');
        highlight.id = '__afqaPickHighlight';
        highlight.style.cssText =
            'position:fixed;pointer-events:none;z-index:2147483647;' +
            'border:2px solid #ff4081;background:rgba(255,64,129,0.15);' +
            'box-sizing:border-box;display:none;';
        (document.body || document.documentElement).appendChild(highlight);
        window.__afqaPickHighlight = highlight;

        // small "LOCKED" tag shown pinned to the top-left corner of the
        // highlight box once an element is locked - the spec's own
        // "locked state should look slightly different" requirement,
        // on top of the thicker border toggled in lockPick() below.
        // pointer-events:none so it can never itself become the "real"
        // element realElementAt() finds (same reasoning as overlay/
        // highlight already being excluded there).
        var lockLabel = document.createElement('div');
        lockLabel.id = '__afqaPickLockLabel';
        lockLabel.textContent = 'LOCKED';
        lockLabel.style.cssText =
            'position:fixed;pointer-events:none;z-index:2147483647;' +
            'background:#ff4081;color:#fff;font:bold 11px sans-serif;' +
            'padding:1px 5px;border-radius:2px;display:none;';
        (document.body || document.documentElement).appendChild(lockLabel);

        // LOCK STATE - single click locks onto whatever realElementAt()
        // resolved at that point (see the click handler further down
        // this file); double click releases it. Kept here, not as a
        // bare module-level var, so it shares scope with realElementAt/
        // overlay/highlight without needing yet another window.__afqa*
        // global just to pass it around internally.
        var pickLocked = false;
        var pickLockedEl = null;

        // ITEM 4: getBoundingClientRect() is relative to the element's
        // OWN window - for an element found inside a same-origin iframe
        // (see realElementAt's own drilling below), that's the iframe's
        // viewport, not the top-level page's. highlight/lockLabel are
        // both appended to the TOP-level document.body and positioned
        // position:fixed against the TOP-level viewport, so using an
        // iframe-local rect directly renders the box wherever the
        // iframe's own (0,0) happens to be relative to the page - often
        // nowhere near the real element, sometimes off-screen entirely.
        // Confirmed as the actual cause of "highlight sometimes missing"
        // via a live probe: an iframe-nested button resolved to the
        // correct element (realElementAt already handled that part) but
        // its highlight box rendered offset by exactly the iframe's own
        // page position. Walks up through however many same-origin
        // iframes the element is nested in (generic - no assumption
        // about depth), summing each ancestor iframe's own top-level-
        // relative rect; a shadow-DOM element needs no such walk since
        // shadow roots share their host's coordinate space already.
        function _afqaTopLevelRect(el) {
            var r = el.getBoundingClientRect();
            var left = r.left, top = r.top;
            var win;
            try {
                win = el.ownerDocument.defaultView;
            } catch (e) {
                win = null;
            }
            var depth = 0;
            while (win && win.frameElement && depth < MAX_DRILL_DEPTH) {
                var frameRect;
                try {
                    frameRect = win.frameElement.getBoundingClientRect();
                } catch (e) {
                    break;
                }
                left += frameRect.left;
                top += frameRect.top;
                try {
                    win = win.frameElement.ownerDocument.defaultView;
                } catch (e) {
                    break;
                }
                depth++;
            }
            return { left: left, top: top, width: r.width, height: r.height };
        }

        function _afqaSyncLockedHighlight() {
            if (!pickLocked || !pickLockedEl || !pickLockedEl.isConnected) return;
            var r;
            try {
                r = _afqaTopLevelRect(pickLockedEl);
            } catch (e) {
                return;
            }
            highlight.style.left = r.left + 'px';
            highlight.style.top = r.top + 'px';
            highlight.style.width = r.width + 'px';
            highlight.style.height = r.height + 'px';
            lockLabel.style.left = r.left + 'px';
            lockLabel.style.top = Math.max(0, r.top - 16) + 'px';
        }

        function lockPick(el) {
            pickLocked = true;
            pickLockedEl = el;
            highlight.style.display = 'block';
            highlight.style.borderWidth = '4px';
            lockLabel.style.display = 'block';
            _afqaSyncLockedHighlight();
        }

        function releasePick() {
            pickLocked = false;
            pickLockedEl = null;
            highlight.style.borderWidth = '2px';
            highlight.style.display = 'none';
            lockLabel.style.display = 'none';
        }

        window.__afqaPickIsLocked = function () { return pickLocked; };
        window.__afqaPickLock = lockPick;
        window.__afqaPickRelease = releasePick;

        // Z-INDEX-TIE DEFENSE: 2147483647 is the CSS maximum, but when
        // two elements share the SAME z-index, the LATER one in DOM
        // order wins the paint order - a site's own "always on top"
        // widget (a chat bubble, a cookie-consent banner, a promo
        // modal) that also happens to use the max value, and mounts
        // AFTER this overlay, would still paint over it and let real
        // clicks through underneath - confirmed as a real cause of
        // clicks reaching the live page during picking. Keeping the
        // overlay+highlight as the LAST two children of <body> at all
        // times - re-asserted on every DOM mutation, plus a short
        // interval as a fallback for anything a MutationObserver could
        // plausibly miss - means any such tie is always broken in our
        // favor, no matter what the site adds or when.
        function _keepOnTop() {
            var body = document.body;
            if (!body) return;
            if (body.lastElementChild !== lockLabel) {
                body.appendChild(overlay);    // appendChild on an already-
                body.appendChild(highlight);  // connected node MOVES it, never
                body.appendChild(lockLabel);  // clones it
            }
        }
        new MutationObserver(_keepOnTop).observe(document.documentElement, { childList: true, subtree: true });
        // same interval also re-syncs the LOCKED highlight's position on
        // every tick - the spec's own "stays fixed on that element even
        // when the mouse moves, scrolls, or leaves the page" requirement.
        // A no-op (returns immediately) whenever nothing is locked, so
        // this costs nothing extra for the far more common unlocked case.
        setInterval(function () { _keepOnTop(); _afqaSyncLockedHighlight(); }, 250);
        _keepOnTop();
        // capture-phase + passive: catches scroll on ANY nested
        // container, not just the window, without interfering with the
        // page's own scroll handling at all - tighter, immediate re-sync
        // than waiting for the 250ms interval above to catch up
        window.addEventListener('scroll', _afqaSyncLockedHighlight, { capture: true, passive: true });
        window.addEventListener('resize', _afqaSyncLockedHighlight, { passive: true });

        // shared by the mousemove highlight below AND the click handler
        // further down this file - both need the SAME "what's really
        // there, ignoring our own overlay/highlight nodes" answer.
        //
        // DRILLS INTO same-origin iframes and open shadow roots - a
        // plain document.elementsFromPoint() stops at the <iframe>/
        // shadow-host element itself, never revealing what's actually
        // rendered inside it (confirmed via a live probe: an iframe
        // resolved to tag=iframe, a shadow-DOM button resolved to its
        // host div, neither ever the real inner target). Recurses up to
        // MAX_DRILL_DEPTH times so a nested shadow-root-inside-an-
        // iframe-inside-a-shadow-root (unlikely, but not impossible)
        // still bottoms out instead of looping forever; each level
        // re-runs elementsFromPoint in THAT level's own coordinate
        // space, translating through the iframe's own bounding rect
        // when crossing into one (shadow roots need no translation -
        // they share the same viewport coordinate system as their
        // host). A cross-ORIGIN iframe's contentDocument throws on
        // access (browser security) - caught and treated as "can't
        // drill further, use the iframe element itself", the exact
        // same same-origin-only scope generator/script_generator.py's
        // own _find_in_iframes() replay fallback already has, so this
        // never promises more than replay can actually deliver on.
        var MAX_DRILL_DEPTH = 5;

        // the overlay is position:fixed at the viewport level, so it
        // shows up as the topmost hit in EVERY elementsFromPoint() call
        // this drills into - not just the initial one on `document` -
        // confirmed via a live probe: host.shadowRoot.elementsFromPoint()
        // returned the overlay first too, ahead of the real shadow-DOM
        // button. Every stack this function examines, at every drill
        // depth, needs the same overlay/highlight filter applied.
        function firstReal(stack) {
            for (var i = 0; i < stack.length; i++) {
                if (stack[i] !== overlay && stack[i] !== highlight) {
                    return stack[i];
                }
            }
            return null;
        }

        function realElementAt(x, y) {
            var found = firstReal(document.elementsFromPoint(x, y));
            var curX = x, curY = y, depth = 0;
            while (found && depth < MAX_DRILL_DEPTH) {
                depth++;
                if (found.shadowRoot) {
                    var deeper = firstReal(found.shadowRoot.elementsFromPoint(curX, curY));
                    if (deeper && deeper !== found) {
                        found = deeper;
                        continue; // same coordinate space as the host - no translation needed
                    }
                    break; // shadow root reported nothing deeper - stop here
                }
                if (found.tagName === 'IFRAME') {
                    var innerDoc = null;
                    try {
                        innerDoc = found.contentDocument;
                    } catch (e) {
                        innerDoc = null; // cross-origin - can't see inside, stop drilling
                    }
                    if (!innerDoc) break;
                    var frameRect = found.getBoundingClientRect();
                    var relX = curX - frameRect.left, relY = curY - frameRect.top;
                    var innerDeeper;
                    try {
                        innerDeeper = firstReal(innerDoc.elementsFromPoint(relX, relY));
                    } catch (e) {
                        break;
                    }
                    if (innerDeeper && innerDeeper !== found) {
                        found = innerDeeper;
                        curX = relX;
                        curY = relY;
                        continue;
                    }
                    break;
                }
                break; // neither a shadow host nor an iframe - this is the real target
            }
            return found;
        }
        window.__afqaPickRealElementAt = realElementAt;

        // BUG 2 FIX (picker): the element the click handler below should
        // pick is "whatever the hover highlight is currently showing" -
        // tracked here, live, on every hover move, so the click handler
        // can use THIS instead of re-deriving it from the click event's
        // own coordinate. Exposed on window (like realElementAt above)
        // so the click handler - defined far below, in a different scope
        // - can read it; cleared whenever the highlight itself is hidden
        // (nothing real under the cursor) so a stale value can never be
        // used.
        window.__afqaPickLastHovered = null;

        overlay.addEventListener('mousemove', function (e) {
            if (pickLocked) return; // locked highlight tracks pickLockedEl instead - see _afqaSyncLockedHighlight
            if (dragActive) return; // a drag-select is in progress - see the drag-select block below, its own rectangle is the only thing that should update right now
            var real = realElementAt(e.clientX, e.clientY);
            if (real) {
                var r = _afqaTopLevelRect(real);
                highlight.style.display = 'block';
                highlight.style.left = r.left + 'px';
                highlight.style.top = r.top + 'px';
                highlight.style.width = r.width + 'px';
                highlight.style.height = r.height + 'px';
                window.__afqaPickLastHovered = real;
            } else {
                highlight.style.display = 'none';
                window.__afqaPickLastHovered = null;
            }
        });

        // ==============================================================
        // DRAG-SELECT (multi-pick) - lets Pick Element return ONE xpath
        // that matches every repeating item (product card, list row, ...)
        // inside a Windows-Explorer-style drag rectangle, instead of only
        // ever picking a single element. Rides the SAME overlay/pick-mode
        // machinery above; a plain click (mouse released within
        // DRAG_THRESHOLD_PX of where it went down) never enters any of
        // this and runs the EXISTING single-element click handler further
        // below completely unchanged - dragActive only ever becomes true
        // once real movement is seen, and everything here is a no-op
        // until then.
        var DRAG_THRESHOLD_PX = 5;
        var AUTO_SCROLL_EDGE_PX = 40;
        var AUTO_SCROLL_STEP_PX = 15;

        var dragMouseDownClient = null; // {x, y} viewport coords at mousedown, or null between drags
        var dragActive = false;         // true once movement has exceeded DRAG_THRESHOLD_PX
        var dragCancelled = false;      // Esc was pressed mid-drag - the button is still down, waiting for mouseup to clean up (see the keydown/mouseup handlers below)
        var dragStartDoc = null;        // {x, y} in DOCUMENT coords (survives scrolling)
        var dragEndDoc = null;
        var dragLastClientX = 0, dragLastClientY = 0; // last known viewport coords, reused to recompute dragEndDoc on scroll
        var dragAutoScrollRAF = null;
        var multiLocked = false;        // parallel to pickLocked, but for a drag-select result (no single pickLockedEl to track)
        var multiHighlightEls = [];     // outline boxes for every element the last multi-pick's xpath matched

        var dragRect = document.createElement('div');
        dragRect.id = '__afqaDragRect';
        dragRect.style.cssText =
            'position:fixed;pointer-events:none;z-index:2147483647;' +
            'border:1px solid #2979ff;background:rgba(41,121,255,0.15);' +
            'box-sizing:border-box;display:none;';
        (document.body || document.documentElement).appendChild(dragRect);

        function _afqaPreventDefault(e) { e.preventDefault(); }

        function _afqaClearMultiHighlights() {
            for (var i = 0; i < multiHighlightEls.length; i++) {
                try { multiHighlightEls[i].remove(); } catch (e) {}
            }
            multiHighlightEls = [];
        }

        // outline colour (#00c853, green) deliberately different from the
        // single-pick highlight's pink, so it's visually obvious which
        // mode picked what's on screen
        function _afqaDrawMultiHighlights(nodes) {
            _afqaClearMultiHighlights();
            for (var i = 0; i < nodes.length; i++) {
                try {
                    var r = _afqaTopLevelRect(nodes[i]);
                    var box = document.createElement('div');
                    box.className = '__afqaMultiHighlight';
                    box.style.cssText =
                        'position:fixed;pointer-events:none;z-index:2147483646;' +
                        'border:2px solid #00c853;box-sizing:border-box;';
                    box.style.left = r.left + 'px';
                    box.style.top = r.top + 'px';
                    box.style.width = r.width + 'px';
                    box.style.height = r.height + 'px';
                    (document.body || document.documentElement).appendChild(box);
                    multiHighlightEls.push(box);
                } catch (e) {}
            }
        }

        function lockMulti() { multiLocked = true; }
        function releaseMulti() {
            multiLocked = false;
            _afqaClearMultiHighlights();
        }
        window.__afqaPickIsMultiLocked = function () { return multiLocked; };
        window.__afqaReleaseMulti = releaseMulti;

        function _afqaUpdateDragRect() {
            if (!dragStartDoc || !dragEndDoc) return;
            var x1 = Math.min(dragStartDoc.x, dragEndDoc.x);
            var x2 = Math.max(dragStartDoc.x, dragEndDoc.x);
            var y1 = Math.min(dragStartDoc.y, dragEndDoc.y);
            var y2 = Math.max(dragStartDoc.y, dragEndDoc.y);
            // dragRect is position:fixed (viewport-relative) - converted
            // back from document coords using the CURRENT scroll position
            // so it renders correctly even mid-auto-scroll
            dragRect.style.left = (x1 - window.scrollX) + 'px';
            dragRect.style.top = (y1 - window.scrollY) + 'px';
            dragRect.style.width = (x2 - x1) + 'px';
            dragRect.style.height = (y2 - y1) + 'px';
            dragRect.style.display = 'block';
        }

        // single source of truth for dragEndDoc - recomputed from the
        // last known viewport coords plus whatever the CURRENT scroll
        // position is, so both an actual mousemove and a scroll (mouse
        // wheel, or the auto-scroll loop below) update it identically
        function _afqaRecomputeDragEnd() {
            dragEndDoc = { x: dragLastClientX + window.scrollX, y: dragLastClientY + window.scrollY };
            _afqaUpdateDragRect();
        }

        function _afqaAutoScrollFrame() {
            if (!dragActive) { dragAutoScrollRAF = null; return; }
            var dy = 0;
            if (dragLastClientY < AUTO_SCROLL_EDGE_PX) {
                dy = -AUTO_SCROLL_STEP_PX;
            } else if (dragLastClientY > window.innerHeight - AUTO_SCROLL_EDGE_PX) {
                dy = AUTO_SCROLL_STEP_PX;
            }
            if (dy !== 0) {
                window.scrollBy(0, dy); // triggers the 'scroll' listener below, which recomputes dragEndDoc
            }
            dragAutoScrollRAF = requestAnimationFrame(_afqaAutoScrollFrame);
        }

        window.addEventListener('scroll', function () {
            if (dragActive) {
                _afqaRecomputeDragEnd();
                // FOLLOW-UP FIX (Part B): auto-scroll (and an ordinary
                // mouse-wheel scroll mid-drag) can move content past the
                // viewport - and, on a virtualized list, out of the DOM
                // entirely - WITHOUT a mousemove event necessarily firing
                // at the same rate, so this needs its own sampling call
                // too, not just the mousemove handler's.
                _afqaAccumulateDragCandidates(false, dragStartDoc, dragEndDoc);
            }
        }, { passive: true });

        function _afqaStableClasses(el) {
            var classes = [];
            if (el.classList) {
                for (var i = 0; i < el.classList.length; i++) {
                    var c = el.classList[i];
                    // ignore classes that look generated/dynamic: contain
                    // digits, are hash-like (all hex chars), or are
                    // implausibly long for a hand-authored class name
                    if (/\d/.test(c)) continue;
                    if (c.length > 30) continue;
                    if (/^[a-f]{6,}$/i.test(c)) continue;
                    classes.push(c);
                }
            }
            classes.sort();
            return classes;
        }

        function _afqaSharedStableClass(els) {
            var common = null;
            for (var i = 0; i < els.length; i++) {
                var cls = _afqaStableClasses(els[i]);
                common = (common === null) ? cls.slice() : common.filter(function (c) { return cls.indexOf(c) !== -1; });
                if (!common.length) break;
            }
            return (common && common.length) ? common[0] : null;
        }

        function _afqaSharedDataOrRoleAttr(els) {
            if (!els.length) return null;
            var first = els[0];
            for (var i = 0; i < first.attributes.length; i++) {
                var name = first.attributes[i].name;
                if (name !== 'role' && name.indexOf('data-') !== 0) continue;
                var allHave = true;
                for (var j = 1; j < els.length; j++) {
                    if (!els[j].hasAttribute(name)) { allHave = false; break; }
                }
                if (allHave) return name;
            }
            return null;
        }

        function _afqaDomDepth(el) {
            var d = 0, cur = el;
            while (cur && cur !== document.documentElement) { d++; cur = cur.parentElement; }
            return d;
        }

        // small, self-contained XPath 1.0 string-literal quoter - same
        // logic as xPath()'s own private xpathLiteral() further down this
        // file, duplicated rather than shared since that one is a nested
        // function private to xPath()'s own closure
        function _afqaXpathLiteral(value) {
            value = String(value);
            if (value.indexOf("'") === -1) return "'" + value + "'";
            if (value.indexOf('"') === -1) return '"' + value + '"';
            var pieces = value.split("'");
            var exprParts = [];
            for (var i = 0; i < pieces.length; i++) {
                exprParts.push("'" + pieces[i] + "'");
                if (i < pieces.length - 1) exprParts.push('"\'"');
            }
            return 'concat(' + exprParts.join(', ') + ')';
        }

        function _afqaCountXpathMatches(xpath) {
            try {
                var result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                return result.snapshotLength;
            } catch (e) {
                return -1;
            }
        }

        function _afqaXpathMatchedElements(xpath) {
            var out = [];
            try {
                var result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                for (var i = 0; i < result.snapshotLength; i++) out.push(result.snapshotItem(i));
            } catch (e) {}
            return out;
        }

        // is `el` one of this picker's own UI nodes (overlay/highlight/
        // drag rectangle/lock label/multi-highlight outlines)? Checked by
        // id/class, not object identity alone, so a multi-highlight box
        // (created fresh on every drag) is always excluded too, not just
        // whichever ones exist at the time this runs.
        function _afqaIsPickerUiNode(el) {
            if (el === overlay || el === highlight || el === lockLabel || el === dragRect) return true;
            var id = el.id || '';
            if (id === '__afqaPickOverlay' || id === '__afqaPickHighlight' ||
                id === '__afqaPickLockLabel' || id === '__afqaDragRect') return true;
            return !!(el.classList && el.classList.contains('__afqaMultiHighlight'));
        }

        // CONTENT BOX (thin/wrapped-layout fix): a nav link that's as tall
        // as its whole header, or any element whose padding/line-height
        // makes its OWN box much bigger than what a human actually sees
        // and drags over, would never reach 60% area overlap from a
        // natural, tight drag across just its visible text - this is a
        // SECOND way for an element to qualify as a candidate, based on
        // where its actual rendered content sits rather than its full box.
        var CONTENT_BOX_OWN_BOX_TAGS = { IMG: 1, SVG: 1, INPUT: 1, BUTTON: 1, SELECT: 1, TEXTAREA: 1 };

        function _afqaGetContentBox(el) {
            if (CONTENT_BOX_OWN_BOX_TAGS[el.tagName]) {
                try {
                    var r = el.getBoundingClientRect();
                    return (r.width > 0 && r.height > 0) ? r : null;
                } catch (eOwn) { return null; }
            }
            // direct (non-descendant) non-whitespace text node children only -
            // a wrapper whose only text lives inside a nested child element
            // has none of its OWN, and correctly returns null here (that
            // child, walked separately as its own candidate, is what
            // should match instead)
            var firstTextNode = null, lastTextNode = null;
            for (var i = 0; i < el.childNodes.length; i++) {
                var node = el.childNodes[i];
                if (node.nodeType === 3 && node.textContent && node.textContent.trim()) {
                    if (!firstTextNode) firstTextNode = node;
                    lastTextNode = node;
                }
            }
            if (!firstTextNode) return null;
            try {
                var range = document.createRange();
                range.setStart(firstTextNode, 0);
                range.setEnd(lastTextNode, lastTextNode.textContent.length);
                var rect = range.getBoundingClientRect();
                return (rect.width > 0 && rect.height > 0) ? rect : null;
            } catch (eRange) {
                return null;
            }
        }

        // a token (class or id) that looks generated/dynamic (contains
        // digits, is hash-like, or implausibly long) is never "stable" -
        // same policy _afqaStableClasses already applies per-class,
        // reused here for a single string (an id) too
        function _afqaIsStableToken(s) {
            return !!s && !/\d/.test(s) && s.length <= 30 && !/^[a-f]{6,}$/i.test(s);
        }

        // the relative XPath from a (verified) ancestor `fromEl` down to
        // `toEl`, expressed purely as positional /*[N] steps - no class/
        // text/attribute dependency at all, since fromEl was already
        // chosen specifically to anchor the FULL parent xpath on
        // something stable; this part only needs to reach the exact
        // element from there, not describe it generically.
        function _afqaRelativeXpathFrom(fromEl, toEl) {
            if (fromEl === toEl) return '';
            var chain = [];
            var cur = toEl;
            while (cur && cur !== fromEl) {
                chain.unshift(cur);
                cur = cur.parentElement;
            }
            if (cur !== fromEl) return ''; // fromEl is always an ancestor-or-self of toEl by construction below
            var steps = '';
            for (var i = 0; i < chain.length; i++) {
                var idx = 1;
                var sib = chain[i].previousElementSibling;
                while (sib) { idx++; sib = sib.previousElementSibling; }
                steps += '/*[' + idx + ']';
            }
            return steps;
        }

        // CONTENT-INDEPENDENT parent XPath (multi-pick only) - never a
        // text()/contains(text(), ...)/normalize-space(text()) predicate
        // anywhere, so a listing whose visible text changes (a different
        // product, a re-fetch) can never break the count. Preference
        // order: (a) nearest ancestor-or-self of P with a stable id,
        // (b) P or the nearest ancestor with a stable class, (c) a shared
        // data-*/role attribute on P or an ancestor, (d) the existing
        // generic xPath() generator as a last resort (single-click pick
        // keeps using that generator directly, unchanged - this is only
        // ever called for a drag-select's own parent).
        function _afqaBuildContentFreeParentXpath(P) {
            var cur = P;
            while (cur && cur !== document.documentElement) {
                if (cur.id && _afqaIsStableToken(cur.id)) {
                    return "//*[@id=" + _afqaXpathLiteral(cur.id) + "]" + _afqaRelativeXpathFrom(cur, P);
                }
                cur = cur.parentElement;
            }
            cur = P;
            while (cur && cur !== document.documentElement) {
                var stable = _afqaStableClasses(cur);
                if (stable.length) {
                    var tag = cur.tagName.toLowerCase();
                    var clsXpath = '//' + tag + "[contains(concat(' ',normalize-space(@class),' '), ' " + stable[0] + " ')]";
                    return clsXpath + _afqaRelativeXpathFrom(cur, P);
                }
                cur = cur.parentElement;
            }
            cur = P;
            while (cur && cur !== document.documentElement) {
                for (var i = 0; i < cur.attributes.length; i++) {
                    var name = cur.attributes[i].name;
                    if (name === 'role' || name.indexOf('data-') === 0) {
                        return '//*[@' + name + ']' + _afqaRelativeXpathFrom(cur, P);
                    }
                }
                cur = cur.parentElement;
            }
            return xPath(P);
        }

        // WALK-UP GROUPING (thin/wrapped-layout fix): the "same direct
        // parent" grouping above requires every repeating item to be an
        // IMMEDIATE child of the same container - true for a plain grid
        // of cards, but not for a nav menu shaped like
        // <li><a>MEN</a></li><li><a>WOMEN</a></li>... where each hit (the
        // <a>) has its OWN wrapper, so no two hits ever share a direct
        // parent. Walking up from each hit (never above <body>, at most 6
        // levels) finds the level where an ancestor A's OWN parent P has
        // >= 2 element children sharing A's tag+stable-class signature -
        // that shared parent/signature pair, with hits landing under at
        // least 2 of those children, is the real repeating unit (the
        // wrapper, not the inner link). Only ever tried when the same-
        // parent grouping above already found nothing (see its own call
        // site) - never replaces or reorders that first, simpler try.
        function _afqaFindGroupViaAncestorWalk(hits) {
            var pairAccum = new Map(); // P -> { sig -> {level, siblingsWithHits:Set} }
            for (var hi = 0; hi < hits.length; hi++) {
                var A = hits[hi].parentElement;
                var level = 0;
                while (A && level < 6) {
                    var P = A.parentElement;
                    if (!P || P === document.documentElement) break; // never above <body>
                    var sig = A.tagName.toLowerCase() + '|' + _afqaStableClasses(A).join(',');
                    var siblingCount = 0;
                    for (var c = 0; c < P.children.length; c++) {
                        var childSig = P.children[c].tagName.toLowerCase() + '|' + _afqaStableClasses(P.children[c]).join(',');
                        if (childSig === sig) siblingCount++;
                    }
                    if (siblingCount >= 2) {
                        var bySig = pairAccum.get(P);
                        if (!bySig) { bySig = {}; pairAccum.set(P, bySig); }
                        if (!bySig[sig]) bySig[sig] = { level: level, siblingsWithHits: new Set() };
                        bySig[sig].level = Math.min(bySig[sig].level, level);
                        bySig[sig].siblingsWithHits.add(A);
                    }
                    level++;
                    A = P;
                }
            }
            var best = null;
            pairAccum.forEach(function (bySig, P) {
                Object.keys(bySig).forEach(function (sig) {
                    var info = bySig[sig];
                    if (info.siblingsWithHits.size < 2) return; // need hits from >= 2 DIFFERENT siblings
                    if (!best || info.siblingsWithHits.size > best.count ||
                        (info.siblingsWithHits.size === best.count && info.level < best.level)) {
                        best = { P: P, sig: sig, level: info.level, count: info.siblingsWithHits.size, siblingsWithHits: info.siblingsWithHits };
                    }
                });
            });
            if (!best) return null;
            // FOLLOW-UP FIX (Part A, CONFIRMED REAL BUG): this used to
            // rebuild groupEls from EVERY one of best.P's children sharing
            // best.sig, discarding best.siblingsWithHits (the actual set
            // of wrappers a drag hit landed in) - the exact same "counts
            // every similar item on the page, not just the ones selected"
            // bug this whole task exists to fix, just in the walk-up
            // (nested/thin-layout) grouping path instead of the simpler
            // same-parent one. Filtering to only the hit wrappers (still
            // walked in best.P.children's own DOM order, needed later for
            // position()-based XPath scoping) fixes it here too.
            var groupEls = [];
            for (var c2 = 0; c2 < best.P.children.length; c2++) {
                var child = best.P.children[c2];
                if (best.siblingsWithHits.has(child)) groupEls.push(child);
            }
            return { parent: best.P, els: groupEls, inBoxCount: best.count };
        }

        // CANDIDATE TEST: does `el` currently have EITHER at least 60% of
        // its own area inside the (document-coordinate) rectangle
        // [rx1,ry1,rx2,ry2], OR the center of its rendered CONTENT (see
        // _afqaGetContentBox) inside it - the second rule is what makes a
        // thin drag across a nav link's visible text strip work, when
        // that link's own full box is as tall as the whole header. An
        // element whose own box fully contains the rectangle is excluded
        // either way (a "too big to be a repeating item" container, e.g.
        // that same header itself). Pure predicate, no side effects -
        // reused both by the incremental accumulation during the drag
        // (see _afqaAccumulateDragCandidates) and the one-shot legacy
        // path this used to be inlined into.
        function _afqaElementQualifiesForBox(el, rx1, ry1, rx2, ry2) {
            var rect;
            try { rect = el.getBoundingClientRect(); } catch (eR) { return false; }
            if (rect.width <= 0 || rect.height <= 0) return false;
            var style;
            try { style = getComputedStyle(el); } catch (eS) { return false; }
            if (!style || style.display === 'none' || style.visibility === 'hidden') return false;
            var elX1 = rect.left + window.scrollX, elX2 = rect.right + window.scrollX;
            var elY1 = rect.top + window.scrollY, elY2 = rect.bottom + window.scrollY;
            if (elX1 <= rx1 && elY1 <= ry1 && elX2 >= rx2 && elY2 >= ry2) return false; // a container spanning the whole rectangle is never a valid candidate
            var ix1 = Math.max(elX1, rx1), ix2 = Math.min(elX2, rx2);
            var iy1 = Math.max(elY1, ry1), iy2 = Math.min(elY2, ry2);
            var iw = Math.max(0, ix2 - ix1), ih = Math.max(0, iy2 - iy1);
            var elArea = rect.width * rect.height;
            if (elArea > 0 && (iw * ih) / elArea >= 0.6) return true;
            var contentBox = _afqaGetContentBox(el);
            if (contentBox) {
                var ccx = contentBox.left + contentBox.width / 2 + window.scrollX;
                var ccy = contentBox.top + contentBox.height / 2 + window.scrollY;
                if (ccx >= rx1 && ccx <= rx2 && ccy >= ry1 && ccy <= ry2) return true;
            }
            return false;
        }

        // FOLLOW-UP FIX (Part B, CONFIRMED REAL BUG): candidates used to
        // be scanned exactly ONCE, at mouseup, against document.
        // querySelectorAll('*') at that single moment - correct in its
        // own coordinate math (rect + scrollX/scrollY, already document-
        // relative, not viewport-only), but blind to any element that
        // scrolled past and was then REMOVED from the DOM by the page's
        // own lazy-rendering/virtualization before mouseup ever ran (a
        // live repro: dragging over ~25 cards while auto-scrolling found
        // only the ~7 still-mounted near the final scroll position).
        // Sampling on every throttled tick DURING the drag instead, and
        // accumulating into a persistent Map that's never pruned, means
        // an element that qualified at ANY point while it still existed
        // stays selected even after it's later unmounted - exactly
        // "everything the box covered", not just what's left at the end.
        //
        // A Map (element -> its parentElement AT THE MOMENT it qualified),
        // not a plain Set - CONFIRMED REAL BUG this fixes: once an
        // element is actually removed from the DOM (.remove(), or a
        // framework re-render), its OWN .parentElement reads back null
        // from then on - the grouping step further down groups candidates
        // BY parent, so silently re-reading .parentElement fresh at
        // grouping time (after the drag/scroll has already unmounted
        // some of them) would drop every one of those elements right back
        // out, defeating this whole fix. Remembering the parent at
        // accumulation time keeps it valid regardless of what happens to
        // the element afterward.
        var dragCandidateMap = null; // Map<Element, parentElement>, live only during an active drag
        var DRAG_SAMPLE_THROTTLE_MS = 120;
        var _lastDragSampleAt = 0;

        function _afqaAccumulateDragCandidates(force, startDoc, endDoc) {
            // CONFIRMED REAL BUG this signature fixes: the module-level
            // dragStartDoc/dragEndDoc are already reset to null by the
            // mouseup handler BEFORE _afqaHandleDragSelection's own final
            // sample runs (see that handler's own cleanup order) - reading
            // them here instead of taking explicit bounds silently made
            // that final, un-throttled sample a no-op every time. Callers
            // during an active drag pass the live dragStartDoc/dragEndDoc;
            // the final call from _afqaHandleDragSelection passes its own
            // startDoc/endDoc parameters (the values captured BEFORE that
            // reset), which are still valid.
            if (!dragCandidateMap || !startDoc || !endDoc) return;
            var now = Date.now();
            if (!force && now - _lastDragSampleAt < DRAG_SAMPLE_THROTTLE_MS) return;
            _lastDragSampleAt = now;
            var rx1 = Math.min(startDoc.x, endDoc.x), rx2 = Math.max(startDoc.x, endDoc.x);
            var ry1 = Math.min(startDoc.y, endDoc.y), ry2 = Math.max(startDoc.y, endDoc.y);
            var allEls = document.querySelectorAll('*');
            for (var i = 0; i < allEls.length; i++) {
                var el = allEls[i];
                if (dragCandidateMap.has(el) || _afqaIsPickerUiNode(el)) continue;
                if (_afqaElementQualifiesForBox(el, rx1, ry1, rx2, ry2)) dragCandidateMap.set(el, el.parentElement);
            }
        }

        // FOLLOW-UP FIX (Part A): given a step base (e.g.
        // "div[contains(@class,'card')]") and the SPECIFIC elements the
        // user actually selected (bestGroup.els - already narrowed to
        // just the ones a drag hit, see _afqaHandleDragSelection's own
        // grouping and the walk-up path's own siblingsWithHits fix),
        // builds an xpath that matches EXACTLY those elements via
        // position() - never the whole sibling family a plain tag/class
        // match would. position() here counts among the elements THIS
        // stepBase itself matches under parentXpath (the same set the
        // final xpath will be evaluated against on replay), which is
        // exactly what "compute a and b among the siblings that match
        // the child step" calls for.
        //
        // Returns {xpath, count} once verified via a fresh document.
        // evaluate() against the xpath this just built - never trusts the
        // position math alone. Returns null (caller falls back to the
        // previous, unscoped behavior and shows a yellow note) when
        // selectedEls isn't a clean subset of what stepBase matches, or
        // the built xpath doesn't verify - this must never guess a wrong
        // subset.
        function _afqaBuildPositionScopedXpath(parentXpath, stepBase, selectedEls) {
            var fullXpath = parentXpath + '/' + stepBase;
            var allMatched = _afqaXpathMatchedElements(fullXpath);
            if (!allMatched.length) return null;
            var positions = [];
            for (var i = 0; i < selectedEls.length; i++) {
                var idx = allMatched.indexOf(selectedEls[i]);
                if (idx === -1) return null; // selectedEls isn't fully reachable via this stepBase
                positions.push(idx + 1); // XPath position() is 1-based
            }
            positions.sort(function (a, b) { return a - b; });
            var uniquePositions = [];
            for (var p = 0; p < positions.length; p++) {
                if (p === 0 || positions[p] !== positions[p - 1]) uniquePositions.push(positions[p]);
            }
            if (!uniquePositions.length) return null;
            var isContiguous = true;
            for (var j = 1; j < uniquePositions.length; j++) {
                if (uniquePositions[j] !== uniquePositions[j - 1] + 1) { isContiguous = false; break; }
            }
            var predicate;
            if (uniquePositions.length === 1) {
                predicate = '[position()=' + uniquePositions[0] + ']';
            } else if (isContiguous) {
                predicate = '[position()>=' + uniquePositions[0] + ' and position()<=' + uniquePositions[uniquePositions.length - 1] + ']';
            } else {
                var parts = [];
                for (var k = 0; k < uniquePositions.length; k++) parts.push('position()=' + uniquePositions[k]);
                predicate = '[' + parts.join(' or ') + ']';
            }
            var scopedXpath = fullXpath + predicate;
            var verifyCount = _afqaCountXpathMatches(scopedXpath);
            if (verifyCount !== uniquePositions.length) return null; // never guess - caller falls back
            return { xpath: scopedXpath, count: verifyCount };
        }

        function _afqaHandleDragSelection(startDoc, endDoc, fallbackClientX, fallbackClientY) {
            var rx1 = Math.min(startDoc.x, endDoc.x), rx2 = Math.max(startDoc.x, endDoc.x);
            var ry1 = Math.min(startDoc.y, endDoc.y), ry2 = Math.max(startDoc.y, endDoc.y);

            // one final, un-throttled sample (catches anything that only
            // qualified in the last few pixels of movement before
            // mouseup, which the throttle above may have skipped), then
            // use the WHOLE accumulated map - not a fresh one-shot scan -
            // as this drag's own candidates.
            _afqaAccumulateDragCandidates(true, startDoc, endDoc);
            var candidates = dragCandidateMap ? Array.from(dragCandidateMap.keys()) : [];

            // GROUP by structural signature: tagName + parent element +
            // sorted stable class list. Map keyed by the REMEMBERED parent
            // (see dragCandidateMap's own docstring - an element unmounted
            // during the drag no longer reports a live .parentElement, so
            // this reads the parent captured at accumulation time instead,
            // never a fresh .parentElement lookup) so two visually-
            // identical parents elsewhere on the page are never merged
            // into one group.
            var parentGroups = new Map();
            for (var gi = 0; gi < candidates.length; gi++) {
                var gel = candidates[gi];
                var gparent = dragCandidateMap.get(gel);
                if (!gparent) continue;
                var sig = gel.tagName.toLowerCase() + '|' + _afqaStableClasses(gel).join(',');
                var bySig = parentGroups.get(gparent);
                if (!bySig) { bySig = {}; parentGroups.set(gparent, bySig); }
                if (!bySig[sig]) bySig[sig] = [];
                bySig[sig].push(gel);
            }
            var allGroups = [];
            parentGroups.forEach(function (bySig, parentEl) {
                Object.keys(bySig).forEach(function (sig) {
                    allGroups.push({ parent: parentEl, els: bySig[sig] });
                });
            });
            allGroups = allGroups.filter(function (g) { return g.els.length >= 2; });
            // most members wins; ties broken by whichever group sits
            // highest in the DOM (the outer repeating card, not something
            // nested inside it)
            allGroups.sort(function (a, b) {
                if (b.els.length !== a.els.length) return b.els.length - a.els.length;
                return _afqaDomDepth(a.els[0]) - _afqaDomDepth(b.els[0]);
            });
            var bestGroup = allGroups.length ? allGroups[0] : null;
            if (bestGroup) bestGroup.inBoxCount = bestGroup.els.length;

            // WALK-UP GROUPING: only tried when the same-direct-parent
            // grouping above found nothing (a nav-menu-shaped selection,
            // where each hit has its own individual wrapper) - see
            // _afqaFindGroupViaAncestorWalk's own comment.
            if (!bestGroup) {
                bestGroup = _afqaFindGroupViaAncestorWalk(candidates);
            }

            if (!bestGroup) {
                // NO SILENT FALLBACK: a drag that finds no repeating group
                // of >= 2 must never guess a single element and report it
                // as a success (CONFIRMED REAL BUG this fixes - a live
                // Myntra repro saved exactly that kind of guess with
                // expected_count=6, and replay then failed "found 1").
                // Nothing is locked, no xpath is sent - the picker stays
                // in plain hover mode so the user can just try again, and
                // recording_editor.html's own applyPickedProfile leaves
                // its current xpath field completely untouched for this
                // exact mode.
                try {
                    window.pickResult(JSON.stringify({ mode: 'multi_none', xpath: null, match_count: 0, in_box_count: 0 }));
                } catch (eNone) {
                    // pickResult binding not ready - nothing more to do
                }
                return;
            }

            var parentXpath = _afqaBuildContentFreeParentXpath(bestGroup.parent);
            var memberTag = bestGroup.els[0].tagName.toLowerCase();
            var inBoxCount = bestGroup.inBoxCount;

            var stepOptions = [];
            var sharedClass = _afqaSharedStableClass(bestGroup.els);
            if (sharedClass) stepOptions.push(memberTag + '[contains(@class,' + _afqaXpathLiteral(sharedClass) + ')]');
            var sharedAttr = _afqaSharedDataOrRoleAttr(bestGroup.els);
            if (sharedAttr) stepOptions.push(memberTag + '[@' + sharedAttr + ']');
            stepOptions.push(memberTag); // tag name alone - matches every sibling of that tag under the parent

            // FOLLOW-UP FIX (Part A, CONFIRMED REAL BUG): the OLD loop
            // below accepted the FIRST stepOption whose match count was
            // >= inBoxCount, then used that tag/class-identity xpath
            // as-is - matching every CURRENT AND FUTURE similar item
            // under the parent (a live repro: 50 product cards on the
            // page, only 7-25 actually dragged over), never just the
            // ones selected. Try each stepOption's own POSITION-SCOPED
            // version first (see _afqaBuildPositionScopedXpath - matches
            // exactly bestGroup.els via position(), verified by re-
            // evaluating the built xpath) before ever falling back to the
            // old, unscoped behavior.
            var chosenXpath = null, chosenMatchCount = 0, positionScoped = false;
            for (var so = 0; so < stepOptions.length; so++) {
                var scoped = _afqaBuildPositionScopedXpath(parentXpath, stepOptions[so], bestGroup.els);
                if (scoped) {
                    chosenXpath = scoped.xpath;
                    chosenMatchCount = scoped.count;
                    positionScoped = true;
                    break;
                }
            }
            var scopeFallbackNote = null;
            if (!chosenXpath) {
                // could not scope down to EXACTLY the selected items for
                // any stepOption (the DOM changed between measurement and
                // verification, or none of these step bases even reach
                // every selected element) - fall back to the previous,
                // unscoped behavior rather than silently guessing a wrong
                // subset, and say so, per this task's own "never guess,
                // show a yellow note" requirement.
                for (var so2 = 0; so2 < stepOptions.length; so2++) {
                    var candidateXpath = parentXpath + '/' + stepOptions[so2];
                    var mc = _afqaCountXpathMatches(candidateXpath);
                    if (mc >= inBoxCount) { chosenXpath = candidateXpath; chosenMatchCount = mc; break; }
                }
                if (!chosenXpath) {
                    chosenXpath = parentXpath + '/' + stepOptions[stepOptions.length - 1];
                    chosenMatchCount = _afqaCountXpathMatches(chosenXpath);
                }
                scopeFallbackNote = 'Could not narrow this pick down to exactly your selection - it matches every similar item on the page instead.';
            }

            var profile = {
                id: null,
                name: null,
                role: null,
                aria_label: null,
                accessible_name: null,
                placeholder: null,
                title: null,
                href: null,
                product_id: null,
                css_path: null,
                xpath: chosenXpath,
                xpath_candidates: [chosenXpath],
                xpath_candidates_confidence: [],
                text: null,
                element_text: null,
                tag: memberTag,
                attributes: {},
                cross_boundary: false,
                icon_class_hint: null,
                match_count: chosenMatchCount,
                mode: 'multi',
                in_box_count: inBoxCount,
                // FOLLOW-UP FIX (Part A): true when chosenXpath matches
                // EXACTLY the selected items (via position()), false when
                // it fell back to the old, unscoped tag/class-identity
                // match - see scope_fallback_note for why, when false.
                position_scoped: positionScoped,
                scope_fallback_note: scopeFallbackNote,
                // FOLLOW-UP FIX (Part 4a, last bullet): a generic plural
                // noun for the repeating group as a whole - see
                // _afqaGenericGroupLabel's own docstring for why this
                // never reads any one member's own text.
                element_label: _afqaGenericGroupLabel(memberTag, bestGroup.els[0]),
                element_kind: 'element',
                element_section: '',
            };

            lockMulti();
            _afqaDrawMultiHighlights(_afqaXpathMatchedElements(chosenXpath));
            try {
                window.pickResult(JSON.stringify(profile));
            } catch (eSend) {
                // pickResult binding not ready - nothing more to do
            }
        }

        document.addEventListener('mousedown', function (e) {
            if (!window.__afqaPickMode) return;
            if (e.button !== 0) return; // left button only
            if (pickLocked || multiLocked) return; // already locked - dblclick releases it first, same as single-pick today
            dragMouseDownClient = { x: e.clientX, y: e.clientY };
            dragActive = false;
            dragStartDoc = null;
            dragEndDoc = null;
        }, true);

        document.addEventListener('mousemove', function (e) {
            if (!window.__afqaPickMode || !dragMouseDownClient || dragCancelled) return; // Esc already cancelled this gesture - ignore further movement until mouseup resets it
            dragLastClientX = e.clientX;
            dragLastClientY = e.clientY;
            if (!dragActive) {
                var dx = e.clientX - dragMouseDownClient.x;
                var dy = e.clientY - dragMouseDownClient.y;
                if (Math.sqrt(dx * dx + dy * dy) > DRAG_THRESHOLD_PX) {
                    dragActive = true;
                    dragStartDoc = { x: dragMouseDownClient.x + window.scrollX, y: dragMouseDownClient.y + window.scrollY };
                    // FOLLOW-UP FIX (Part B): a fresh accumulation set for
                    // THIS drag gesture - see _afqaAccumulateDragCandidates's
                    // own docstring for why this persists across the whole
                    // drag instead of a single scan at the end.
                    dragCandidateMap = new Map();
                    _lastDragSampleAt = 0;
                    // hide the pink hover box for the duration of the drag
                    // (and, since nothing shows it again until a real
                    // mousemove happens - see the hover listener's own
                    // `if (dragActive) return;` guard - it stays hidden
                    // right through the result being sent too; normal
                    // hover resumes on its own the next time the mouse
                    // actually moves)
                    highlight.style.display = 'none';
                    window.__afqaPickLastHovered = null;
                    document.documentElement.style.userSelect = 'none';
                    document.addEventListener('dragstart', _afqaPreventDefault, true);
                    document.addEventListener('selectstart', _afqaPreventDefault, true);
                    dragAutoScrollRAF = requestAnimationFrame(_afqaAutoScrollFrame);
                }
            }
            if (dragActive) {
                _afqaRecomputeDragEnd();
                _afqaAccumulateDragCandidates(false, dragStartDoc, dragEndDoc);
            }
        }, true);

        document.addEventListener('mouseup', function (e) {
            if (!window.__afqaPickMode || !dragMouseDownClient) return;
            var wasDragging = dragActive;
            var wasCancelled = dragCancelled;
            var upClientX = e.clientX, upClientY = e.clientY;
            var finishedStart = dragStartDoc, finishedEnd = dragEndDoc;

            dragMouseDownClient = null;
            dragActive = false;
            dragCancelled = false;
            if (dragAutoScrollRAF !== null) { cancelAnimationFrame(dragAutoScrollRAF); dragAutoScrollRAF = null; }
            document.documentElement.style.userSelect = '';
            document.removeEventListener('dragstart', _afqaPreventDefault, true);
            document.removeEventListener('selectstart', _afqaPreventDefault, true);
            dragRect.style.display = 'none';
            dragStartDoc = null;
            dragEndDoc = null;

            if (wasCancelled) {
                // Esc already cancelled this drag (see the keydown handler
                // below) - the browser still fires a 'click' right after
                // THIS mouseup though, same as a completed drag would;
                // swallow it too, but make no selection at all.
                dragCandidateMap = null;
                window.__afqaJustDragSelected = true;
                e.preventDefault();
                e.stopImmediatePropagation();
                return;
            }

            if (!wasDragging) { dragCandidateMap = null; return; } // an ordinary click - let the existing click handler below run unchanged

            // a real drag just completed - the browser still fires a
            // 'click' event right after this mouseup (mousedown and
            // mouseup landed on the same element - the overlay - so
            // nothing here suppresses it automatically); this flag is
            // what the EXISTING single-pick click handler further below
            // checks to swallow that click instead of also running its
            // own single-element pick logic. window.__afqa*, not a bare
            // var, so it's readable from that handler's own, separate
            // scope - same cross-scope convention this file already uses
            // for __afqaPickLastHovered/__afqaPickIsLocked/etc.
            window.__afqaJustDragSelected = true;
            e.preventDefault();
            e.stopImmediatePropagation();

            try {
                _afqaHandleDragSelection(finishedStart, finishedEnd, upClientX, upClientY);
            } catch (eDrag) {
                // nothing more to do here - Python side's own timeout covers this
            }
            dragCandidateMap = null; // consumed - never leaks into the NEXT drag gesture
        }, true);

        document.addEventListener('keydown', function (e) {
            if (!window.__afqaPickMode) return;
            if (e.key !== 'Escape' || !dragActive) return;
            // deliberately does NOT clear dragMouseDownClient - the mouse
            // button is still physically down at this point, and the
            // mouseup listener above needs to still see a gesture "in
            // flight" (via dragCancelled) so it can swallow the 'click'
            // the browser fires right after that same mouseup too;
            // clearing dragMouseDownClient here would make that mouseup
            // look like an ordinary click and let an unwanted single-
            // element pick through instead of a clean, selection-less
            // cancel (CONFIRMED via a live repro before this fix).
            dragActive = false;
            dragCancelled = true;
            if (dragAutoScrollRAF !== null) { cancelAnimationFrame(dragAutoScrollRAF); dragAutoScrollRAF = null; }
            document.documentElement.style.userSelect = '';
            document.removeEventListener('dragstart', _afqaPreventDefault, true);
            document.removeEventListener('selectstart', _afqaPreventDefault, true);
            dragRect.style.display = 'none';
            dragStartDoc = null;
            dragEndDoc = null;
        }, true);
    }

    if (window.__afqaPickMode) {
        _afqaSetupPickOverlay();
    }

    // ==================================================================
    // TEMPORARY DIAGNOSTIC INSTRUMENTATION - gated behind DEBUG_RECORDER
    // (set the DEBUG_RECORDER=1 environment variable when launching a
    // recording; see record_session.py for how it reaches window.
    // __RECORDER_DEBUG__). Purely additive, purely observational - does
    // not change what gets captured, discarded, or how, on any site, for
    // any element. Fully generic: logs event TYPE/target/timing, never
    // any specific button text or site-specific string. Safe to delete
    // this whole block (and its call sites below, each clearly marked)
    // once the investigation it's for is done.
    // ==================================================================
    var RECORDER_DEBUG = !!window.__RECORDER_DEBUG__;

    // "container-like": a wrapper, never the thing the user clicked. Named limits, not site-specific.
    var AFQA_CONTAINER_MIN_STRONG_DESCENDANTS = 2;     // holds this many strong interactive descendants or more
    var AFQA_CONTAINER_VIEWPORT_AREA_RATIO = 0.25;     // or covers more than this share of the viewport
    var AFQA_CONTAINER_MAX_TEXT_CHARS = 80;            // or its text is longer than this
    var AFQA_OWN_LABEL_MAX_CHARS = 60;                 // a label / text locator taken from an element is at most this long
    var AFQA_STRONG_INTERACTIVE_SELECTOR =
        'button, a[href], input, select, textarea, label, summary, [role=button], [role=link], [role=menuitem], ' +
        '[role=menuitemcheckbox], [role=menuitemradio], [role=tab], [role=option], [role=switch], [role=checkbox], ' +
        '[role=radio], [role=combobox], [aria-haspopup], [aria-expanded], [contenteditable=true]';

    function afqaIsContainerLike(node) {
        try {
            if (!node || node.nodeType !== 1) return false;
            if (node.querySelectorAll(AFQA_STRONG_INTERACTIVE_SELECTOR).length >= AFQA_CONTAINER_MIN_STRONG_DESCENDANTS) return true;
            var r = node.getBoundingClientRect();
            var vw = window.innerWidth || 1, vh = window.innerHeight || 1;
            if (r.width * r.height > AFQA_CONTAINER_VIEWPORT_AREA_RATIO * vw * vh) return true;
            if (((node.innerText || '') + '').trim().length > AFQA_CONTAINER_MAX_TEXT_CHARS) return true;
        } catch (eContainerLike) {}
        return false;
    }
    // the innermost real target of an event (reaches into a shadow tree)
    var afqaLastPress = null;          // { target, x, y, t }: the last trusted pointerdown
    var AFQA_PRESS_CLICK_MAX_MS = 3000;
    var AFQA_PRESS_CLICK_MAX_PX = 12;
    function afqaInnerEvent(ev) {
        try {
            var path = ev && ev.composedPath ? ev.composedPath() : null;
            var inner = path && path.length ? path[0] : null;
            if (!inner || inner.nodeType !== 1) inner = ev.target;
            // a click that landed on the page root right after a press somewhere else: the press target
            if (inner && (inner === document.documentElement || inner === document.body) && afqaLastPress &&
                afqaLastPress.target && afqaLastPress.target !== inner && afqaLastPress.target.nodeType === 1 &&
                (Date.now() - afqaLastPress.t) < AFQA_PRESS_CLICK_MAX_MS &&
                Math.abs((ev.clientX || 0) - afqaLastPress.x) <= AFQA_PRESS_CLICK_MAX_PX &&
                Math.abs((ev.clientY || 0) - afqaLastPress.y) <= AFQA_PRESS_CLICK_MAX_PX) {
                inner = afqaLastPress.target;
            }
            if (!inner || inner === ev.target || inner.nodeType !== 1) return ev;
            return {
                target: inner, isTrusted: ev.isTrusted, clientX: ev.clientX, clientY: ev.clientY, button: ev.button,
                preventDefault: function () { ev.preventDefault(); },
                stopPropagation: function () { ev.stopPropagation(); },
                stopImmediatePropagation: function () { ev.stopImmediatePropagation(); }
            };
        } catch (eInnerEvent) { return ev; }
    }

    function debugDescribeTarget(el) {
        if (!el) return '(no target)';
        try {
            var tag = el.tagName ? el.tagName.toLowerCase() : String(el);
            var id = el.id ? ('#' + el.id) : '';
            var cls = (el.className && typeof el.className === 'string' && el.className.trim())
                ? ('.' + el.className.trim().split(/\s+/).join('.'))
                : '';
            return tag + id + cls;
        } catch (e) {
            return '(target unreadable: ' + e + ')';
        }
    }

    function debugLog() {
        if (!RECORDER_DEBUG) return;
        var args = Array.prototype.slice.call(arguments);
        // one distinctive, greppable prefix - record_session.py's
        // console relay (only active when DEBUG_RECORDER is set) only
        // forwards lines starting with this, so a busy site's own
        // console noise never floods the terminal
        try {
            console.log.apply(console, ['[recorder-debug]'].concat(args));
        } catch (e) { /* console unavailable - nothing more to do */ }
    }

    // raw capture-phase listeners for the whole pointer/mouse/click
    // sequence a single physical click actually produces, on document,
    // so this reflects EVERY event Chromium itself dispatches for that
    // click before recorder-specific logic (dedup, buffering, profile-
    // building) ever runs - answers "did the event even fire" separately
    // from "did OUR code then decide to keep or discard it"
    if (RECORDER_DEBUG) {
        ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click'].forEach(function (evtType) {
            window.addEventListener(evtType, function (e) {
                debugLog(
                    evtType,
                    'target=' + debugDescribeTarget(e.target),
                    'isTrusted=' + e.isTrusted,
                    'defaultPrevented=' + e.defaultPrevented,
                    't=' + Date.now() + 'ms'
                );
            }, true);
        });
    }
    // ==================================================================
    // end of raw event listeners - dedup/discard logging is added at
    // each existing early-return point further below, marked the same way
    // ==================================================================

    function cssPath(el) {
        // NOT "el instanceof Element" - an element from a same-origin
        // IFRAME's own document belongs to a DIFFERENT JS realm, with
        // its own separate Element constructor, so instanceof always
        // reads false for it even though it's a perfectly normal
        // element (confirmed real: this silently produced an empty
        // css_path for every iframe-internal pick). nodeType is a
        // plain number, identical across realms, and 1 === ELEMENT_NODE
        // works the same test without that gap.
        if (!el || el.nodeType !== 1) return '';
        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE && el.tagName !== 'HTML') {
            let sel = el.tagName.toLowerCase();
            if (el.id) {
                parts.unshift(sel + '#' + el.id);
                break;
            }
            let sib = el, nth = 1;
            while (sib.previousElementSibling) {
                sib = sib.previousElementSibling;
                if (sib.tagName === el.tagName) nth++;
            }
            if (nth > 1) sel += ':nth-of-type(' + nth + ')';
            parts.unshift(sel);
            el = el.parentElement;
        }
        return parts.join(' > ');
    }

    // Confirms a candidate XPath resolves to exactly one live element,
    // for a given target element - shared by xPath()'s own internal
    // xpathIsUnique() and buildXpathCandidates() further down this file,
    // so there's exactly one place that knows how to verify a candidate
    // rather than two copies drifting apart. Never trust a candidate
    // that matches 0 or more than 1.
    function xpathIsUniqueFor(el, candidate) {
        if (!candidate) return false;
        // a shadow-DOM element's xpath can never be verified this way
        // at all - standard XPath/document.evaluate() has no concept of
        // shadow roots and always reports zero matches for anything
        // describing a path that crosses into one, regardless of
        // whether the candidate is actually correct. Every candidate is
        // still the best real signal available (id/data-testid/text/
        // ...) - accepted unverified here rather than incorrectly
        // rejected as "not unique" for a reason unrelated to whether it
        // identifies el uniquely. See buildLocatorProfile's own
        // cross_boundary flag for how this gets surfaced instead of
        // silently pretending the xpath was actually confirmed.
        try {
            if (el.getRootNode() instanceof ShadowRoot) return true;
        } catch (e) {}
        try {
            // el's OWN document, not necessarily the top-level one -
            // matters for an element inside a same-origin iframe
            // (el.ownerDocument is that iframe's own document there);
            // verifying against the wrong document would always read as
            // "zero matches" even for a genuinely correct, unique
            // candidate
            var doc = el.ownerDocument || document;
            var result = doc.evaluate(
                candidate, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
            );
            return result.snapshotLength === 1;
        } catch (e) {
            return false;
        }
    }

    // PHASE 1b (record-time locator building must not depend on volatile
    // numbers): same policy as the replay-side Python port of this exact
    // function (generator/script_generator.py's own _strip_volatile_
    // numbers - keep the two in sync if this policy ever changes). A
    // bracketed count like "(419525)"/"[12]"/"(1.2k)" is always stripped;
    // an UNBRACKETED number is only stripped when it carries a comma/dot
    // separator or a k/K/M suffix (a bare standalone digit run like
    // "Page 2" is left alone - plenty of real labels are just a number).
    // Digits glued directly onto letters (iPhone15, RTX4090) are never
    // touched either way.
    var AFQA_BRACKETED_VOLATILE_NUM_RE = /[\(\[]\s*\d[\d,.]*\s*[kKmM]?\s*[\)\]]/g;
    var AFQA_STANDALONE_VOLATILE_NUM_RE = /(?<!\w)(?:\d[\d,.]*[kKmM]|\d+(?:[.,]\d+)+)(?!\w)/g;

    function _afqaStripVolatileNumbers(text) {
        if (!text) return text;
        var out = text.replace(AFQA_BRACKETED_VOLATILE_NUM_RE, ' ');
        out = out.replace(AFQA_STANDALONE_VOLATILE_NUM_RE, ' ');
        return out.replace(/\s+/g, ' ').trim();
    }

    // ==================================================================
    // FOLLOW-UP FIX (Part 4a): element_label/element_kind/element_section -
    // added to the SAME pickResult payload both Pick Element flows below
    // already send (no new channel). CONFIRMED REAL BUG this fixes: a
    // picked radio option's own visual "circle" <div> has no text of its
    // own, and the editor's naming only ever read the picked element's
    // OWN text - it fell all the way back to the generic "element" label
    // even though the option's real, human name ("Girls") was sitting
    // right there in the wrapping <label> a moment away. Purely
    // structural (tag/role/type/ancestor shape) - never a site-specific
    // selector, class or text.
    // ==================================================================

    var AFQA_HEADING_TAG_RE = /^h[1-6]$/;

    function _afqaLooksLikeHeading(node) {
        if (!node || !node.tagName) return false;
        var tag = node.tagName.toLowerCase();
        if (AFQA_HEADING_TAG_RE.test(tag) || tag === 'legend') return true;
        var role = (node.getAttribute && node.getAttribute('role')) || '';
        if (role.toLowerCase() === 'heading') return true;
        // a short bold/uppercase text block - generic, structural,
        // never tied to any one site's own class naming
        try {
            var text = (node.innerText || '').trim();
            if (!text || text.length > 40) return false;
            var cs = getComputedStyle(node);
            var weight = parseInt(cs.fontWeight, 10);
            var isBold = (!isNaN(weight) && weight >= 600) || cs.fontWeight === 'bold';
            var isUpper = text === text.toUpperCase() && /[A-Za-z]/.test(text);
            return isBold || isUpper;
        } catch (eHeading) {
            return false;
        }
    }

    // radio/checkbox/link/button/input/select/image/heading/list-item, or
    // "element" when nothing more specific applies. A styled <div>/<span>
    // wrapping (or sitting next to) a real radio/checkbox <input> counts
    // as that input's own kind, even though the input itself is what was
    // actually picked - matches how a person would describe what they
    // clicked ("the Girls radio option"), not the implementation detail
    // underneath it.
    function _afqaClassifyElementKind(el) {
        if (!el || !el.tagName) return 'element';
        var tag = el.tagName.toLowerCase();
        var role = ((el.getAttribute && el.getAttribute('role')) || '').toLowerCase();
        var type = ((el.getAttribute && el.getAttribute('type')) || '').toLowerCase();

        // CONFIRMED REAL BUG this fixes: el.parentElement.querySelector
        // ('input') searches the parent's ENTIRE descendant subtree, not
        // just el's own immediate siblings - on a shallow page (a link, a
        // button and a text input all sitting as plain siblings under
        // <body>, say) this found an unrelated checkbox input elsewhere
        // on the page entirely and misclassified an ordinary link/button
        // as a "checkbox". "Nearby" now means only: an input inside a
        // wrapping <label>, an input among el's OWN descendants (el
        // itself wraps its input), or an input that is an IMMEDIATELY
        // ADJACENT sibling - never a broader subtree search.
        var nearbyInput = null;
        if (tag === 'input') {
            nearbyInput = el;
        } else {
            var wrappingLabel = el.closest ? el.closest('label') : null;
            if (wrappingLabel && wrappingLabel.querySelector) {
                nearbyInput = wrappingLabel.querySelector('input');
            }
            if (!nearbyInput && el.querySelector) {
                nearbyInput = el.querySelector('input');
            }
            if (!nearbyInput) {
                var prevSib = el.previousElementSibling;
                var nextSib = el.nextElementSibling;
                if (prevSib && prevSib.tagName === 'INPUT') nearbyInput = prevSib;
                else if (nextSib && nextSib.tagName === 'INPUT') nearbyInput = nextSib;
            }
        }
        if (nearbyInput) {
            var inputType = (nearbyInput.getAttribute('type') || '').toLowerCase();
            if (inputType === 'radio') return 'radio';
            if (inputType === 'checkbox') return 'checkbox';
        }
        if (role === 'radio') return 'radio';
        if (role === 'checkbox') return 'checkbox';
        if (tag === 'a' || role === 'link') return 'link';
        if (tag === 'button' || role === 'button') return 'button';
        if (tag === 'select') return 'select';
        if (tag === 'input') {
            if (type === 'radio') return 'radio';
            if (type === 'checkbox') return 'checkbox';
            return 'input';
        }
        if (tag === 'textarea') return 'input';
        if (tag === 'img' || role === 'img') return 'image';
        if (AFQA_HEADING_TAG_RE.test(tag) || role === 'heading') return 'heading';
        if (tag === 'li' || role === 'listitem') return 'list-item';
        return 'element';
    }

    // the 5-tier fallback cascade from this task's own spec: (1) the
    // element's own visible text, (2) aria-label/aria-labelledby/title/
    // alt/placeholder/a button's own value, (3) an associated <label>
    // (wrapping ancestor, or label[for=id]), (4) the nearest ancestor (max
    // 3 levels up) with short visible text, (5) a short adjacent sibling's
    // text. Volatile numbers stripped, icon-font glyphs stripped, capped
    // at 40 chars - same normalization every other recorded label already
    // gets (see _afqaStripVolatileNumbers/_stripIconFontText).
    function _afqaComputeElementLabel(el) {
        if (!el) return '';
        var label = '';
        try {
            label = (el.innerText || '').trim();
        } catch (eOwn) {}
        if (!label && el.getAttribute) {
            label = el.getAttribute('aria-label') || '';
        }
        if (!label && el.getAttribute && el.getAttribute('aria-labelledby')) {
            try {
                var ids = el.getAttribute('aria-labelledby').split(/\s+/);
                label = ids.map(function (id) {
                    var ref = document.getElementById(id);
                    return ref ? (ref.innerText || ref.textContent || '') : '';
                }).join(' ').trim();
            } catch (eLabelledby) {}
        }
        if (!label && el.getAttribute) label = el.getAttribute('title') || '';
        if (!label && el.getAttribute) label = el.getAttribute('alt') || '';
        if (!label && el.getAttribute) label = el.getAttribute('placeholder') || '';
        if (!label && el.tagName && el.tagName.toLowerCase() === 'input') {
            var inputType = (el.getAttribute('type') || '').toLowerCase();
            if (inputType === 'button' || inputType === 'submit') {
                label = el.value || '';
            }
        }
        if (!label) {
            try {
                var ancestorLabel = el.closest ? el.closest('label') : null;
                if (ancestorLabel) {
                    label = (ancestorLabel.innerText || ancestorLabel.textContent || '').trim();
                } else if (el.id) {
                    var lf = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
                    if (lf) label = (lf.innerText || lf.textContent || '').trim();
                }
            } catch (eAssocLabel) {}
        }
        if (!label) {
            var anc = el.parentElement;
            var ancDepth = 0;
            while (anc && ancDepth < 3) {
                var ancText = '';
                try { ancText = (anc.innerText || '').trim(); } catch (eAnc) {}
                if (ancText && ancText.length <= 40) {
                    label = ancText;
                    break;
                }
                anc = anc.parentElement;
                ancDepth++;
            }
        }
        if (!label) {
            var sib = el.nextElementSibling || el.previousElementSibling;
            if (sib) {
                var sibText = '';
                try { sibText = (sib.innerText || sib.textContent || '').trim(); } catch (eSib) {}
                if (sibText && sibText.length <= 40) label = sibText;
            }
        }
        label = _afqaStripVolatileNumbers(_stripIconFontText(label || '')).trim();
        return label.slice(0, 40);
    }

    // nearest preceding heading/group title in the same container -
    // walks UP from el (checking each level's own preceding siblings,
    // and a fieldset's own <legend>) up to 6 levels, stopping the FIRST
    // time something heading-shaped is found. Empty (never guessed) when
    // nothing heading-shaped turns up within that bound.
    function _afqaComputeElementSection(el) {
        if (!el) return '';
        try {
            var node = el;
            var hops = 0;
            while (node && hops < 6) {
                var heading = null;
                var scan = node.previousElementSibling;
                while (scan) {
                    if (_afqaLooksLikeHeading(scan)) { heading = scan; break; }
                    scan = scan.previousElementSibling;
                }
                if (!heading && node.parentElement && node.parentElement.tagName === 'FIELDSET') {
                    heading = node.parentElement.querySelector('legend');
                }
                if (heading) {
                    return (heading.innerText || heading.textContent || '').trim().slice(0, 25);
                }
                node = node.parentElement;
                hops++;
            }
        } catch (eSection) {}
        return '';
    }

    function _afqaComputeElementLabelInfo(el) {
        return {
            element_label: _afqaComputeElementLabel(el),
            element_kind: _afqaClassifyElementKind(el),
            element_section: _afqaComputeElementSection(el),
        };
    }

    // FOLLOW-UP FIX (Part 4a, last bullet): a drag/multi-pick selects a
    // REPEATING GROUP, not one specific item - describing it by any ONE
    // member's own text would be misleading (which of the 50 cards' text
    // would even be "the" label?). Generic, structural naming only: the
    // member tag, then a shared stable class hinting at a common word
    // ("product-card" -> "cards"), "items" when nothing more specific
    // applies - never any one site's own class/text content.
    function _afqaGenericGroupLabel(memberTag, sampleEl) {
        var role = ((sampleEl && sampleEl.getAttribute && sampleEl.getAttribute('role')) || '').toLowerCase();
        if (role === 'listitem' || memberTag === 'li') return 'list items';
        if (memberTag === 'tr') return 'rows';
        if (memberTag === 'a') return 'links';
        if (memberTag === 'button') return 'buttons';
        if (memberTag === 'img') return 'images';
        if (memberTag === 'option') return 'options';
        if (sampleEl && typeof sampleEl.className === 'string' && sampleEl.className) {
            var cls = sampleEl.className.toLowerCase();
            if (/(^|[-_\s])card($|[-_\s])/.test(cls)) return 'cards';
            if (/(^|[-_\s])row($|[-_\s])/.test(cls)) return 'rows';
            if (/(^|[-_\s])item($|[-_\s])/.test(cls)) return 'items';
        }
        return 'items';
    }

    function xPath(el, labelText, excludeText) {
        // R2 (never anchor a locator on the value a fill action just
        // typed) - excludeText, when given, is that exact typed value.
        // CONFIRMED REAL BUG this fixes: session_20260921_081203's own
        // OTP fill step recorded //div[normalize-space(.)='1234']/input
        // - a wrapping div's rendered text happened to read "1234"
        // (an OTP widget's own visible per-digit boxes, kept in sync
        // with the real input) purely because that's what was just
        // typed, so a real OTP run - always different digits - can
        // never match it again. Declared once here, at the top of
        // xPath's own scope, so every nested tier below (attrTextTiers'
        // own text-candidate loop especially) sees it via closure
        // without threading it through as an extra argument everywhere.
        var _excludeText = (typeof excludeText === 'string') ? excludeText.trim() : '';
        // shape checks for an auto-generated/reused-per-render VALUE
        // (an id or a data-testid/data-test/data-cy alike) - moved
        // ahead of tier 0 so both it and tier 1 below can defer to
        // them, not just the parent-scoped attrTextTiers() walk further
        // down. LONG_DIGIT_RUN_RE catches both a purely-numeric value
        // AND a "word-digits" one with no clean separator; DYNAMIC_ID_RE
        // catches the specific "<word><-_>><digits>" shape precisely
        // enough to extract a stable PREFIX from it (e.g. "sizelabel-"
        // out of "sizelabel-116009189"), which is what actually lets a
        // starts-with() candidate be tried instead of just giving up.
        // CONFIRMED REAL, not hypothetical: a real recorded element
        // carried data-testid="sizelabel-116009189" - a real, unique
        // per-element attribute VALUE, but one that is certain to be a
        // DIFFERENT number on every other render of the same page (a
        // different product's size label, a re-fetch of the same
        // product), making an exact-match xpath built from it silently
        // stop matching anything at replay time on a live site.
        var DYNAMIC_ID_RE = /^([a-zA-Z]+[-_])[0-9]{3,}$/;
        var LONG_DIGIT_RUN_RE = /\d{5,}/;

        function looksAutoGenerated(value) {
            return LONG_DIGIT_RUN_RE.test(value) || DYNAMIC_ID_RE.test(value);
        }

        // tier 0 (NEW) - a stable, human/test-authored attribute on el
        // itself, checked BEFORE id - a data-testid/data-test/data-cy is
        // a much stronger, more intentional signal than a bare id, which
        // on many real sites (React apps especially) is often a
        // framework-internal, reused/non-semantic value (numeric ids
        // like "6", "7", reused across unrelated elements between
        // renders) rather than a real author-written identifier.
        // Confirmed real, not hypothetical: a real recorded element
        // carried BOTH id="116617349" and data-testid="sizelabel-
        // 116617349", yet its xpath was built from the bare id - tier 1
        // below used to run unconditionally, before this tier (or any
        // uniqueness check on the id at all) ever got a chance.
        // xpathLiteral/xpathIsUnique are defined further down as
        // function DECLARATIONS (hoisted to the top of this function's
        // scope in JS), so calling them here, before their own textual
        // definition, is safe.
        var TIER0_ID_ATTRS = ['data-testid', 'data-test', 'data-cy'];
        for (var t0 = 0; t0 < TIER0_ID_ATTRS.length; t0++) {
            var t0Val = null;
            try { t0Val = el.getAttribute(TIER0_ID_ATTRS[t0]); } catch (eT0) {}
            if (!t0Val) continue;
            // a long digit run anywhere in the value (a product id, a
            // hash) means this exact value is very unlikely to survive
            // to the next render of the same page - skip the exact-match
            // candidate entirely rather than build a locator that's
            // already known to be single-render-only.
            if (LONG_DIGIT_RUN_RE.test(t0Val)) {
                var t0Prefix = DYNAMIC_ID_RE.exec(t0Val);
                if (t0Prefix) {
                    var t0PrefixCandidate = '//*[starts-with(@' + TIER0_ID_ATTRS[t0] + ', ' + xpathLiteral(t0Prefix[1]) + ')]';
                    if (xpathIsUnique(t0PrefixCandidate)) return t0PrefixCandidate;
                }
                continue;
            }
            var t0Candidate = '//*[@' + TIER0_ID_ATTRS[t0] + '=' + xpathLiteral(t0Val) + ']';
            if (xpathIsUnique(t0Candidate)) return t0Candidate;
        }

        // tier 1 - unique id, EXCEPT a PURELY NUMERIC one or one that
        // otherwise looks auto-generated/reused-per-render (see the
        // looksAutoGenerated() note above) - a bare digit id ("6", "7",
        // ...) or a "sizelabel-116009189"-shaped one is exactly the
        // shape a framework's own internal/reused identifiers take, not
        // a real author-written id, and is what produced the fragile,
        // collision-prone locators this whole fix exists for. Skipped
        // here, this still gets a real shot via attrTextTiers(el) right
        // below (tier 2-5), whose own dynamic-id prefix matching (tier
        // 3) can turn "sizelabel-116009189" into
        // starts-with(@id, 'sizelabel-') - a real, non-numeric
        // author-written id (the overwhelmingly common case) is
        // completely unaffected - same as before this change.
        if (el.id && !looksAutoGenerated(el.id)) return "//*[@id='" + el.id + "']";

        // Builds a valid XPath 1.0 string literal for `value`. A plain
        // single- or double-quoted literal covers the common case; a
        // value that contains BOTH quote characters needs the standard
        // concat() workaround, since neither quote style alone can hold
        // it.
        function xpathLiteral(value) {
            value = String(value);
            if (value.indexOf("'") === -1) return "'" + value + "'";
            if (value.indexOf('"') === -1) return '"' + value + '"';
            var pieces = value.split("'");
            var exprParts = [];
            for (var i = 0; i < pieces.length; i++) {
                exprParts.push("'" + pieces[i] + "'");
                if (i < pieces.length - 1) exprParts.push('"\'"');
            }
            return 'concat(' + exprParts.join(', ') + ')';
        }

        // Confirms a candidate XPath resolves to exactly one live
        // element - never trust a candidate that matches 0 or more
        // than 1. Thin wrapper around the shared, top-level
        // xpathIsUniqueFor() (see its own docstring for the shadow-DOM/
        // iframe handling) - extracted there so buildXpathCandidates()
        // further down this file can reuse the EXACT same uniqueness
        // check without duplicating it.
        function xpathIsUnique(candidate) {
            return xpathIsUniqueFor(el, candidate);
        }

        // concatenation of `node`'s own direct text-node children only
        // (excludes descendant elements' text) - this is what an
        // XPath text() predicate actually tests against, so it's
        // tried before the more permissive full textContent
        function directTextOf(node) {
            var parts = [];
            var children = node.childNodes;
            for (var i = 0; i < children.length; i++) {
                if (children[i].nodeType === Node.TEXT_NODE) parts.push(children[i].nodeValue);
            }
            return parts.join('').trim().replace(/\s+/g, ' ');
        }

        // tier 2 attributes, tried in this order - the same "genuinely
        // stable, human/test-authored" signals STRONG_ATTRS favors
        // elsewhere in this file, just the subset the spec calls out
        // for xPath()
        var STABLE_ATTRS = ['name', 'data-testid', 'data-test', 'data-cy', 'aria-label', 'placeholder', 'href'];

        // generic SHAPE checks for auto-generated id/class values -
        // these describe naming CONVENTIONS whole libraries/build
        // tools use (CSS-in-JS hash classes, React Native Web's atomic
        // "r-" classes, a "<word>-<digits>" generated-id shape), never
        // any one site's actual class/id value. prefixLen is how much
        // of a matched class is the stable, non-random part.
        var DYNAMIC_CLASS_PATTERNS = [
            { re: /^r-[a-z0-9]+$/, prefixLen: 2 },
            { re: /^css-[a-z0-9]+$/, prefixLen: 4 }
        ];
        // DYNAMIC_ID_RE is already declared above (shared with tier 0/
        // tier 1's own looksAutoGenerated() check) - reused here as-is.
        var MAX_TEXT_LEN = 60;

        // Tiers 2-5: tries, in order, a stable attribute, a
        // dynamic-looking id/class matched by its stable prefix, the
        // element's own live text, then a combined
        // type+role+placeholder predicate - against `node`
        // specifically. Returns the first candidate that resolves to
        // exactly one element, or null if none of them do. Every
        // value used is read live off `node`; nothing here is a
        // fixed/site-specific string.
        function attrTextTiers(node, isLeafSelf) {
            if (!node || node.nodeType !== Node.ELEMENT_NODE) return null;
            var tag = node.tagName.toLowerCase();
            // CONFIRMED REAL REGRESSION, caught by this item's own
            // regression run: <html>/<body> never has a meaningful id/
            // data-testid, and its FULL textContent is the entire
            // page's text (always over MAX_TEXT_LEN, so the old
            // full-text candidate always skipped it) - but the new
            // first-line candidate below reads just the first line of
            // that same textContent, which is often short enough to
            // pass, producing a deceptively clean-looking
            // "//html[contains(., 'Page Title')]" for what was really
            // just a click that landed on empty page background. html/
            // body are never legitimate pick targets regardless of any
            // text they happen to contain - skip this whole tier for
            // them and let the walk fall through to the absolute tier 7
            // (a bare /html is at least honestly what it is), with the
            // large-container warning (see the pick-mode click handler)
            // separately telling the user to hover something smaller.
            if (tag === 'html' || tag === 'body') return null;

            // tier 2 - stable, human/test-authored attribute. For the
            // id-like subset (name/data-testid/data-test/data-cy - never
            // href/aria-label/placeholder, which are free text, not
            // generated identifiers) a long digit run means the exact
            // value is unlikely to survive to the next render (same
            // reasoning as tier 0/tier 1's own looksAutoGenerated()
            // check above) - skip the exact match and try a starts-with()
            // on its stable prefix instead, when the value has one.
            var ID_LIKE_STABLE_ATTRS = { 'name': 1, 'data-testid': 1, 'data-test': 1, 'data-cy': 1 };
            for (var i = 0; i < STABLE_ATTRS.length; i++) {
                var attr = STABLE_ATTRS[i];
                var val = null;
                try { val = node.getAttribute(attr); } catch (e) {}
                if (!val) continue;
                if (ID_LIKE_STABLE_ATTRS[attr] && LONG_DIGIT_RUN_RE.test(val)) {
                    var prefixMatch = DYNAMIC_ID_RE.exec(val);
                    if (prefixMatch) {
                        var prefixCandidate = '//' + tag + '[starts-with(@' + attr + ', ' + xpathLiteral(prefixMatch[1]) + ')]';
                        if (xpathIsUnique(prefixCandidate)) return prefixCandidate;
                    }
                    continue;
                }
                var attrCandidate = '//' + tag + '[@' + attr + '=' + xpathLiteral(val) + ']';
                if (xpathIsUnique(attrCandidate)) return attrCandidate;
            }

            // tier 3 - dynamic-looking id, matched by its stable prefix
            try {
                if (node.id && DYNAMIC_ID_RE.test(node.id)) {
                    var idPrefix = node.id.match(DYNAMIC_ID_RE)[1];
                    var idCandidate = '//' + tag + '[starts-with(@id, ' + xpathLiteral(idPrefix) + ')]';
                    if (xpathIsUnique(idCandidate)) return idCandidate;
                }
            } catch (e) {}

            // tier 3 - dynamic-looking class, matched by its stable prefix
            try {
                var classList = node.classList ? Array.prototype.slice.call(node.classList) : [];
                for (var c = 0; c < classList.length; c++) {
                    for (var p = 0; p < DYNAMIC_CLASS_PATTERNS.length; p++) {
                        if (DYNAMIC_CLASS_PATTERNS[p].re.test(classList[c])) {
                            var classPrefix = classList[c].slice(0, DYNAMIC_CLASS_PATTERNS[p].prefixLen);
                            var classCandidate = '//' + tag + '[contains(@class, ' + xpathLiteral(classPrefix) + ')]';
                            if (xpathIsUnique(classCandidate)) return classCandidate;
                        }
                    }
                }
            } catch (e) {}

            // tier 4 - the element's own live text (direct text() first,
            // the more permissive full-subtree string-value second).
            //
            // CONFIRMED REAL BUG (found via a live repro, not
            // hypothetical): the "full text" candidate used to ALSO
            // build its XPath with contains(text(), ...) - but XPath's
            // text() only ever tests a node's OWN direct text-node
            // children, never descendant text. A real "ADD TO BAG"-
            // style button almost always wraps its label in a nested
            // <span> (icon + label), so the button DIV's own text() is
            // EMPTY even though its full textContent is exactly "ADD TO
            // BAG" - contains(text(), 'ADD TO BAG') matches ZERO
            // elements there (verified: 0 matches), silently falling
            // through every tier below all the way to the absolute-path
            // last resort, while contains(., 'ADD TO BAG') - "." being
            // the whole subtree's string-value, the XPath equivalent of
            // .textContent - correctly matches. Each candidate below now
            // uses the axis that actually corresponds to how its own
            // text was read: text() for directTextOf's direct-children
            // reading, . for the full textContent reading.
            try {
                var textCandidates = [];
                // FIRST LINE of the subtree's raw text, tried before the
                // full concatenation below - a card/row-shaped element
                // (a product card: name, then sizes, then a price on
                // separate lines/child elements) collapses to one long,
                // PRICE-MIXED string once every line is joined with
                // spaces ("CAHOOT Sizes: M Rs. 679Rs. 1699(60% OFF)") -
                // the price/discount portion changes on every real
                // fetch of the same page, so an exact/contains() match
                // built from the WHOLE thing is fragile by construction.
                // Splitting on the RAW newlines in textContent (still
                // present here, before the whitespace-collapsing regex
                // below destroys them) and keeping just the first
                // non-empty one keeps only the stable name/label part.
                // Only ever tried as an EARLIER, more specific option -
                // the full text below still runs as a fallback if this
                // one doesn't resolve to exactly one element.
                var rawLines = (node.textContent || '').split('\n');
                var firstLine = '';
                for (var rl = 0; rl < rawLines.length; rl++) {
                    var candidateLine = rawLines[rl].trim().replace(/\s+/g, ' ');
                    if (candidateLine) { firstLine = candidateLine; break; }
                }
                var dText = directTextOf(node);
                var fText = (node.textContent || '').trim().replace(/\s+/g, ' ');
                // BUG 2 FIX: firstLine/fText are both read from node's FULL
                // textContent - every descendant's text concatenated
                // together, hidden ones included (textContent, unlike
                // innerText, doesn't respect display:none/visibility at
                // all). That's a fine, stable signal for a LEAF element's
                // own short label (a button/link's own visible text -
                // "may stay as it works today") but breaks by construction
                // when attrTextTiers() is called on an ANCESTOR instead
                // (tier 6 below, "nothing on el itself is distinguishing -
                // try its PARENT"): the parent's aggregated text mixes in
                // whatever ELSE lives under it - sibling status/loading
                // messages a script toggles via display:none but never
                // removes from the DOM, a price/badge that changes on
                // every fetch, anything - none of which is "this ancestor's
                // own label" at all. CONFIRMED REAL, not hypothetical: a
                // live repro (a disabled <input> inside a <form> that also
                // held a hidden, stale "Wait for it..." loading message
                // left over from an earlier toggle) produced
                // "//form[normalize-space(.)='DisableIt's enabled!Wait for
                // it...']/input" this exact way - a locator that only ever
                // matched that one transient DOM snapshot. directTextOf
                // (axis text()) is unaffected either way - it only ever
                // reads node's own DIRECT text-node children, never
                // descendant text, so it was never the aggregation problem
                // this guards against.
                if (isLeafSelf) {
                    if (firstLine && firstLine !== fText) textCandidates.push({ text: firstLine, axis: '.' });
                }
                if (dText) textCandidates.push({ text: dText, axis: 'text()' });
                if (isLeafSelf) {
                    if (fText && fText !== dText) textCandidates.push({ text: fText, axis: '.' });
                }
                for (var t = 0; t < textCandidates.length; t++) {
                    var txt = textCandidates[t].text;
                    var axis = textCandidates[t].axis;
                    if (txt.length === 0 || txt.length > MAX_TEXT_LEN) continue;
                    if (_excludeText && txt === _excludeText) continue;
                    // EXACT match tried first, before contains() - a
                    // short value ("M", "2", "L") is a substring of all
                    // kinds of unrelated real text ("Men", "Home",
                    // "2 items left", "Large") elsewhere on a real page;
                    // contains() would happily (and wrongly) match any
                    // of those. normalize-space() on the axis itself
                    // (not a separate function call target) matches
                    // el's committed text ignoring incidental
                    // leading/trailing/collapsed whitespace, without
                    // being a substring test at all. Only actually
                    // fires when it's unique on its own; contains()
                    // right below remains the fallback for genuinely
                    // partial-text cases (a longer sentence/description
                    // where only a distinctive fragment is worth
                    // matching).
                    // PHASE 1b: a volatile count baked into an exact
                    // normalize-space(axis)=X predicate would never match
                    // the live element again once the site's own count
                    // changes (X is now a strict equality against
                    // whatever text is really there) - and stripping the
                    // number out of X wouldn't help an EXACT match either
                    // (the live text still HAS the number, so it would
                    // never equal the stripped literal). Only a contains()
                    // built from the stable, number-stripped portion is
                    // ever usable once txt carries one; txt itself (and
                    // therefore the recorded locator_profile's own display
                    // text, built separately in buildLocatorProfile) is
                    // completely untouched either way.
                    var strippedTxt = _afqaStripVolatileNumbers(txt);
                    if (strippedTxt === txt) {
                        var exactCandidate = '//' + tag + '[normalize-space(' + axis + ')=' + xpathLiteral(txt) + ']';
                        if (xpathIsUnique(exactCandidate)) return exactCandidate;

                        var textCandidate = '//' + tag + '[contains(' + axis + ', ' + xpathLiteral(txt) + ')]';
                        if (xpathIsUnique(textCandidate)) return textCandidate;
                    } else if (strippedTxt) {
                        var strippedCandidate = '//' + tag + '[contains(' + axis + ', ' + xpathLiteral(strippedTxt) + ')]';
                        if (xpathIsUnique(strippedCandidate)) return strippedCandidate;
                    }
                }
            } catch (e) {}

            // tier 5 - combined type/role/placeholder
            try {
                var comboAttrs = ['type', 'role', 'placeholder'];
                var present = [];
                for (var a = 0; a < comboAttrs.length; a++) {
                    var cVal = null;
                    try { cVal = node.getAttribute(comboAttrs[a]); } catch (e2) {}
                    if (cVal) present.push([comboAttrs[a], cVal]);
                }
                if (present.length >= 2) {
                    var predicate = present.map(function (pair) {
                        return '@' + pair[0] + '=' + xpathLiteral(pair[1]);
                    }).join(' and ');
                    var comboCandidate = '//' + tag + '[' + predicate + ']';
                    if (xpathIsUnique(comboCandidate)) return comboCandidate;
                }
            } catch (e) {}

            return null;
        }

        // tier 1b (NEW) - svg/icon anchor from the nearest label text.
        // An svg (or one of its internal path/circle/rect/... children -
        // exactly what a real click on an icon most often actually
        // resolves to) almost never has any of its own stable
        // attributes or text - CONFIRMED REAL: a "Donate" checkbox's own
        // clickable target was a bare <svg><path/></svg> tick-mark icon
        // with nothing distinguishing on it at all, which fell all the
        // way through to the absolute-path tier 7 without this. Rather
        // than describe the icon itself, this anchors on the nearest
        // READABLE text near it (labelText - the same accessible-name
        // labelText tier 6b already relies on for custom checkboxes,
        // see its own comment) and descends to the nearest enclosing
        // <svg> from there - name()='svg' rather than a bare svg tag
        // test is deliberate: XPath 1.0's tag-name test against an
        // SVG element embedded in an HTML document is namespace-
        // sensitive in a way name() sidesteps entirely.
        try {
            var svgAncestor = (el.tagName && el.tagName.toLowerCase() === 'svg')
                ? el
                : (el.closest ? el.closest('svg') : null);
            if (svgAncestor && typeof labelText === 'string' && labelText.trim() !== '') {
                var svgLabelLiteral = xpathLiteral(labelText.trim());
                var svgCandidate = "//*[contains(normalize-space(.), " + svgLabelLiteral + ")]//*[name()='svg']";
                if (xpathIsUnique(svgCandidate)) return svgCandidate;
                // more than one svg under that label - scope further to
                // the SMALLEST containing element whose own text still
                // contains the label, same "climb from the label
                // upward until unique" approach tier 6b uses for a
                // plain (non-svg) checkbox
                var svgScopeAncestor = svgAncestor.parentElement;
                var svgScopeDepth = 0;
                while (svgScopeAncestor && svgScopeAncestor.nodeType === Node.ELEMENT_NODE && svgScopeDepth < 8) {
                    var scopedSvgCandidate = '//' + svgScopeAncestor.tagName.toLowerCase() +
                        "[contains(normalize-space(.), " + svgLabelLiteral + ")]//*[name()='svg']";
                    if (xpathIsUnique(scopedSvgCandidate)) return scopedSvgCandidate;
                    svgScopeAncestor = svgScopeAncestor.parentElement;
                    svgScopeDepth++;
                }
            }
        } catch (eSvg) {}

        // tiers 2-5 against the element itself
        var direct = attrTextTiers(el, true);
        if (direct) return direct;

        // tier 6 - nothing on the element itself is distinguishing;
        // try tiers 2-5 on its parent instead and descend from there.
        // A plain "/tag" step can still match more than one same-tag
        // sibling under that (unique) parent, so a live-computed
        // positional index is appended only if it's actually needed.
        try {
            var parent = el.parentElement;
            var parentCandidate = attrTextTiers(parent, false);
            if (parentCandidate) {
                var childTag = el.tagName.toLowerCase();
                var combined = parentCandidate + '/' + childTag;
                if (xpathIsUnique(combined)) return combined;

                var idx = 1;
                var sib = el.previousElementSibling;
                while (sib) {
                    if (sib.tagName === el.tagName) idx++;
                    sib = sib.previousElementSibling;
                }
                var indexed = combined + '[' + idx + ']';
                if (xpathIsUnique(indexed)) return indexed;
            }
        } catch (e) {}

        // NUMERIC ID - LAST-RESORT FALLBACK (NEW): a purely numeric id
        // was intentionally skipped back at tier 1 (see its own note),
        // deferring to every semantic-attribute/text/parent-based tier
        // above first. If NONE of those found anything unique either,
        // the numeric id is still tried here - a real, literally-correct
        // locator at record time, just a lower-confidence one than a
        // real author-written id or data-testid, so it only wins when
        // genuinely nothing better exists. Still requires uniqueness,
        // same as every other tier - a duplicate numeric id elsewhere on
        // the page correctly falls through past this too, on to tier 6a/
        // 6b below.
        if (el.id && /^[0-9]+$/.test(el.id)) {
            var numericIdCandidate = "//*[@id='" + el.id + "']";
            if (xpathIsUnique(numericIdCandidate)) return numericIdCandidate;
        }

        // tier 6-card - container anchored by a DIFFERENT descendant's
        // text (".//h4[contains(text(),'Shoulder Pop')]" identifying a
        // product card, say) then a relative path from THAT container
        // down to el - covers the real, common "product card" shape: el
        // itself (an "ADD TO BAG" link/button, a size chip, the card's
        // own outer link) has no useful text/id of its own, but a
        // SIBLING/COUSIN descendant of the same card (its title, most
        // often a heading tag) does. Different from tier 6/6b, which
        // both anchor on EL'S OWN text or an explicitly-supplied
        // labelText - this one looks at text that belongs to something
        // else entirely under the same container. Deliberately tried
        // BEFORE tier 6a-scoped just below: given a choice between
        // anchoring on a BROAD ancestor's id (tier 6a - e.g. the whole
        // product grid) and a NARROW container scoped to just this
        // card's own title (this tier), the narrower one is the more
        // specific, more change-resilient locator (surviving products
        // being reordered/added/removed elsewhere in the same grid),
        // so it gets first refusal. Confirmed via a real product-card
        // fixture: without this ordering, an "ADD TO BAG" button
        // resolved via the whole grid's id + a raw positional index
        // instead of via its own card's title. Bounded walk, same
        // real-world headroom as the other multi-level tiers.
        try {
            var HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
            var cardAncestor = el.parentElement;
            var cardDepth = 0;
            var CARD_MAX_DEPTH = 8;
            while (cardAncestor && cardAncestor.nodeType === Node.ELEMENT_NODE && cardDepth < CARD_MAX_DEPTH) {
                for (var ht = 0; ht < HEADING_TAGS.length; ht++) {
                    var headings = cardAncestor.getElementsByTagName(HEADING_TAGS[ht]);
                    for (var hi = 0; hi < headings.length; hi++) {
                        var headingText = (headings[hi].textContent || '').trim().replace(/\s+/g, ' ');
                        if (!headingText || headingText.length > MAX_TEXT_LEN) continue;
                        // PHASE 1b: a heading commonly carries its own
                        // volatile count too (a rating/review count, a
                        // "(1.2k sold)" badge) - stripped here for the
                        // SAME reason as tier 4 above; headingText itself
                        // (used only for this xpath predicate, never
                        // stored anywhere) is otherwise unaffected.
                        var strippedHeadingText = _afqaStripVolatileNumbers(headingText);
                        if (!strippedHeadingText) continue;
                        var containerCandidate = '//' + cardAncestor.tagName.toLowerCase() +
                            '[.//' + HEADING_TAGS[ht] + '[contains(text(), ' + xpathLiteral(strippedHeadingText) + ')]]';
                        if (!xpathIsUnique(containerCandidate)) continue; // ambiguous container - not a safe anchor
                        var steps = relativeStepsFrom(cardAncestor, el);
                        if (!steps) continue;
                        var cardFull = containerCandidate + '/' + steps;
                        if (xpathIsUnique(cardFull)) return cardFull;
                    }
                }
                cardAncestor = cardAncestor.parentElement;
                cardDepth++;
            }
        } catch (e) {}

        // tier 6a-scoped (NEW, additive - inserted before the existing
        // tier 6b below, never replacing it) - before ever falling to a
        // DOCUMENT-WIDE "contains(., text)" search (what tier 6b below
        // does), look for the closest ancestor that's independently,
        // stably identifiable on its own (id/data-testid/data-test/
        // data-cy/aria-label/role) - a dropdown/counter/popup panel's
        // own wrapper virtually always has ONE of these even when the
        // individual OPTIONS inside it (a quantity value, a size, a
        // color swatch) don't. Scoping the contains() search to just
        // that container's own subtree - both the uniqueness check AND
        // the position index if more than one match remains inside
        // it - means a page-wide shift in unrelated "contains this
        // text" content elsewhere (ad content, recommended products,
        // prices/ratings, pagination) can never change which element
        // this resolves to, since those live entirely outside the
        // scoped subtree. Confirmed real, not hypothetical: an XPath
        // shaped like "(//div[contains(., '2')])[63]//div" - a
        // document-wide text search pinned only by a raw document-
        // order index - is exactly what tier 6b below produces when no
        // scoped ancestor is tried first, and is exactly what THIS
        // tier exists to avoid whenever a stable ancestor is available
        // at all. Same bounded, real-world-headroom walk depth as tier
        // 6b (TIER6B_MAX_DEPTH, defined below and reused here since
        // this is the same kind of ancestor walk, just tried first).
        if (typeof labelText === 'string' && labelText.trim() !== '') {
            var STABLE_CONTAINER_ATTRS = ['id', 'data-testid', 'data-test', 'data-cy', 'aria-label'];
            var SCOPED_MAX_DEPTH = 8;
            try {
                var scopedTextLiteral = xpathLiteral(labelText.trim());
                var scopedAncestor = el.parentElement;
                var scopedDepth = 0;
                while (scopedAncestor && scopedAncestor.nodeType === Node.ELEMENT_NODE && scopedDepth < SCOPED_MAX_DEPTH) {
                    var containerXPath = null;
                    for (var sa = 0; sa < STABLE_CONTAINER_ATTRS.length; sa++) {
                        var attrName = STABLE_CONTAINER_ATTRS[sa];
                        var attrVal = null;
                        try { attrVal = scopedAncestor.getAttribute(attrName); } catch (eAttr) {}
                        if (attrVal) {
                            var candidateContainerXPath = '//*[@' + attrName + '=' + xpathLiteral(attrVal) + ']';
                            if (xpathIsUnique(candidateContainerXPath)) {
                                containerXPath = candidateContainerXPath;
                                break;
                            }
                        }
                    }
                    if (!containerXPath) {
                        var containerRole = null;
                        try { containerRole = scopedAncestor.getAttribute('role'); } catch (eRole) {}
                        if (containerRole) {
                            var roleContainerXPath = '//*[@role=' + xpathLiteral(containerRole) + ']';
                            if (xpathIsUnique(roleContainerXPath)) containerXPath = roleContainerXPath;
                        }
                    }

                    if (containerXPath) {
                        var scopedRole = null;
                        try { scopedRole = el.getAttribute ? el.getAttribute('role') : null; } catch (eR2) {}
                        var scopedDescendantSelector = scopedRole
                            ? '*[@role=' + xpathLiteral(scopedRole) + ']'
                            : el.tagName.toLowerCase();
                        var scopedRaw = containerXPath + '//' + scopedDescendantSelector +
                            '[contains(., ' + scopedTextLiteral + ')]';

                        if (xpathIsUnique(scopedRaw)) return scopedRaw;

                        // more than one match WITHIN just this scoped
                        // container - pin by position inside the
                        // container's own subtree only, never the
                        // whole document (see this tier's own comment
                        // block above)
                        try {
                            var scopedMatches = document.evaluate(
                                scopedRaw, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                            );
                            var scopedIdx = -1;
                            for (var sm = 0; sm < scopedMatches.snapshotLength; sm++) {
                                if (scopedMatches.snapshotItem(sm) === el) { scopedIdx = sm + 1; break; }
                            }
                            if (scopedIdx > 0) {
                                var scopedIndexed = '(' + scopedRaw + ')[' + scopedIdx + ']';
                                if (xpathIsUnique(scopedIndexed)) return scopedIndexed;
                            }
                        } catch (eScopedIdx) {}
                        // a stable container was found at this level but
                        // neither the bare nor the indexed scoped
                        // candidate panned out - stop climbing (a
                        // farther-out ancestor's own container would
                        // only be a WEAKER scope, never a better one)
                        // and let tier 6b below try its own, different
                        // (unscoped) approach instead
                        break;
                    }

                    scopedAncestor = scopedAncestor.parentElement;
                    scopedDepth++;
                }
            } catch (eScoped) {}
        }

        // tier 6b - multi-level ancestor + text-label anchor. Covers
        // the case tier 6 can't: a custom checkbox whose readable
        // label lives in a SIBLING, not inside el itself or its
        // descendants (buildProfile() fetches that label separately
        // via getCheckboxAccessibleName() and passes it in here as
        // labelText - tier 4's own text check never sees it, since
        // it only reads el's own text). Only attempted when a label
        // was actually supplied. Walks upward from the immediate
        // parent one ancestor at a time, bounded the same way
        // SEMANTIC_WALK_MAX_DEPTH bounds the interactive-ancestor
        // walk elsewhere in this file - real-world headroom, never an
        // unbounded walk to <body>.
        if (typeof labelText === 'string' && labelText.trim() !== '' && labelText.trim() !== _excludeText) {
            var TIER6B_MAX_DEPTH = 8;
            try {
                var textLiteral = xpathLiteral(labelText.trim());
                var ancestor = el.parentElement;
                var depth = 0;
                while (ancestor && ancestor.nodeType === Node.ELEMENT_NODE && depth < TIER6B_MAX_DEPTH) {
                    var ancestorTag = ancestor.tagName.toLowerCase();
                    var rawCandidate = '//' + ancestorTag + '[contains(., ' + textLiteral + ')]';

                    // rawCandidate searches the WHOLE document for any
                    // <ancestorTag> containing labelText as a
                    // substring - since text propagates upward through
                    // the DOM, every same-tag ancestor ABOVE this one
                    // (a wrapping list/container div, for example) also
                    // trivially contains it, so xpathIsUnique() on the
                    // bare candidate would almost always be false here.
                    // What actually identifies THIS level is this
                    // ancestor's own live position within that match
                    // set - found the same way tier 6b's own descendant
                    // step below (and tier 6 before it) already pins
                    // down a live position when a bare candidate isn't
                    // unique by itself: resolve the set, find `ancestor`
                    // in it by reference.
                    var ancestorIdx = -1;
                    try {
                        var ancestorMatches = document.evaluate(
                            rawCandidate, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                        );
                        for (var a = 0; a < ancestorMatches.snapshotLength; a++) {
                            if (ancestorMatches.snapshotItem(a) === ancestor) { ancestorIdx = a + 1; break; }
                        }
                    } catch (eAnc) {}

                    if (ancestorIdx > 0) {
                        // NOTE: a bare "rawCandidate[N]" would NOT mean
                        // "the Nth item of this match set" - //tag[N]
                        // binds position() to each node's own sibling
                        // rank under ITS OWN parent (the classic
                        // "//div[1] selects the first div child of
                        // EVERY parent" gotcha), not a flattened index
                        // across the whole document. Wrapping the
                        // already-filtered expression in parens first
                        // is what actually makes [N] index into this
                        // specific match set.
                        var ancestorCandidate = (ancestorMatches.snapshotLength === 1)
                            ? rawCandidate
                            : '(' + rawCandidate + ')[' + ancestorIdx + ']';

                        if (xpathIsUnique(ancestorCandidate)) {
                            // this is the nearest ancestor whose own
                            // text actually contains labelText - it's
                            // the anchor; stop climbing regardless of
                            // whether the descent below actually pans
                            // out
                            var role6b = null;
                            try { role6b = el.getAttribute ? el.getAttribute('role') : null; } catch (eR) {}
                            var descendantSelector = role6b
                                ? "*[@role=" + xpathLiteral(role6b) + ']'
                                : el.tagName.toLowerCase();
                            var combined6b = ancestorCandidate + '//' + descendantSelector;

                            if (xpathIsUnique(combined6b)) return combined6b;

                            // more than one matching descendant under
                            // this one anchor - find el's own live
                            // position among them (document order) and
                            // pin to it. A previousElementSibling-style
                            // walk (as tier 6 uses) only covers flat
                            // siblings under a SINGLE parent; matching
                            // descendants here can sit at different
                            // nesting depths under the ancestor, so
                            // their order has to come from resolving
                            // the same candidate set itself.
                            try {
                                var matches6b = document.evaluate(
                                    combined6b, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                                );
                                var idx6b = -1;
                                for (var m = 0; m < matches6b.snapshotLength; m++) {
                                    if (matches6b.snapshotItem(m) === el) { idx6b = m + 1; break; }
                                }
                                if (idx6b > 0) {
                                    // same parens-before-index rule as
                                    // the ancestor step above
                                    var indexed6b = '(' + combined6b + ')[' + idx6b + ']';
                                    if (xpathIsUnique(indexed6b)) return indexed6b;
                                }
                            } catch (eIdx) {}

                            break;
                        }
                    }

                    ancestor = ancestor.parentElement;
                    depth++;
                }
            } catch (e) {}
        }

        // Shared by the container-anchored-by-descendant-text tier and
        // tier 6c below - both need "the XPath steps from some ancestor
        // DOWN to el", expressed as plain tag/tag[N] segments (N only
        // when there's more than one same-tag sibling at that level).
        // Returns null if el isn't actually inside ancestor at all.
        function relativeStepsFrom(ancestor, node) {
            var relParts = [];
            var relNode = node;
            while (relNode && relNode !== ancestor) {
                if (relNode.nodeType !== Node.ELEMENT_NODE) return null;
                var relTag = relNode.tagName.toLowerCase();
                var relIdx = 1;
                var relSib = relNode.previousElementSibling;
                while (relSib) {
                    if (relSib.tagName === relNode.tagName) relIdx++;
                    relSib = relSib.previousElementSibling;
                }
                relParts.unshift(relIdx > 1 ? relTag + '[' + relIdx + ']' : relTag);
                relNode = relNode.parentElement;
            }
            return relNode === ancestor ? relParts.join('/') : null;
        }

        // tier 6c2 - a stable (human/author-written-looking) class name
        // on el itself - tried AFTER every semantic-attribute/text/
        // container tier above (a real id/data-testid/text signal always
        // wins when one exists), but BEFORE ever falling to a purely
        // positional path. Explicitly excludes anything matching the
        // SAME "looks generated" shapes DYNAMIC_CLASS_PATTERNS already
        // knows about (CSS-in-JS hashes, atomic-CSS classes) plus a
        // generic "long, no separators, mixed alnum" heuristic for
        // build-tool-generated hashes those two named patterns don't
        // happen to cover - a real class like "product-card" or
        // "add-to-bag-btn" passes both checks easily.
        try {
            var GENERIC_HASH_CLASS_RE = /^[a-z0-9]{8,}$/i;
            var elClassList = el.classList ? Array.prototype.slice.call(el.classList) : [];
            for (var ec = 0; ec < elClassList.length; ec++) {
                var candidateClass = elClassList[ec];
                var looksDynamic = GENERIC_HASH_CLASS_RE.test(candidateClass);
                for (var dp = 0; dp < DYNAMIC_CLASS_PATTERNS.length; dp++) {
                    if (DYNAMIC_CLASS_PATTERNS[dp].re.test(candidateClass)) looksDynamic = true;
                }
                if (looksDynamic) continue;
                var classCandidateFull = '//' + tag + "[contains(concat(' ', normalize-space(@class), ' '), " +
                    xpathLiteral(' ' + candidateClass + ' ') + ')]';
                if (xpathIsUnique(classCandidateFull)) return classCandidateFull;
            }
        } catch (e) {}

        // tier 6c - short relative path from the nearest ancestor that
        // has ANY id at all, numeric/generated included - this is
        // deliberately AFTER the numeric-id-on-el-itself and text-
        // anchored tiers above (a real, semantic signal always wins
        // when one exists), but BEFORE the absolute tier 7 below: any
        // id anywhere up the chain, however unremarkable, still makes a
        // SHORT, RELATIVE path ("//*[@id='mountRoot']/div/div/button")
        // - only the few steps between that ancestor and el, not the
        // whole document from <html> down - which is far more resilient
        // to unrelated page changes than an absolute path from the root
        // ever is. Bounded walk, same real-world headroom as the other
        // multi-level tiers above.
        try {
            var idAncestor = el.parentElement;
            var idAncestorDepth = 0;
            var ID_ANCESTOR_MAX_DEPTH = 15;
            while (idAncestor && idAncestor.nodeType === Node.ELEMENT_NODE && idAncestorDepth < ID_ANCESTOR_MAX_DEPTH) {
                if (idAncestor.id) {
                    var relSteps = relativeStepsFrom(idAncestor, el);
                    if (relSteps) {
                        var relCandidate = "//*[@id=" + xpathLiteral(idAncestor.id) + "]/" + relSteps;
                        if (xpathIsUnique(relCandidate)) return relCandidate;
                    }
                }
                idAncestor = idAncestor.parentElement;
                idAncestorDepth++;
            }
        } catch (e) {}

        // tier 7 - final fallback: existing absolute positional
        // algorithm, unchanged
        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let idx2 = 1;
            let sib2 = el.previousSibling;
            while (sib2) {
                if (sib2.nodeType === Node.ELEMENT_NODE && sib2.nodeName === el.nodeName) idx2++;
                sib2 = sib2.previousSibling;
            }
            parts.unshift(el.nodeName.toLowerCase() + '[' + idx2 + ']');
            el = el.parentElement;
        }
        return '/' + parts.join('/');
    }

    // Up to maxCount DISTINCT candidate XPaths for el, most-recommended
    // first - always includes xPath()'s own result (unchanged, still
    // the single source of truth for the "best" one) as the recommended
    // candidate, then fills in up to maxCount-1 more from independent,
    // narrower strategies (own id, own exact/contains text, own strong
    // attribute) tried directly here rather than by re-running the full
    // tier cascade a second time - each one only added if it's both
    // genuinely unique AND different from every candidate already
    // collected, so the list is never padded with near-duplicates of
    // the same locator. Exists so the Recording Editor can show a
    // choice instead of silently committing to whatever xPath() alone
    // decided was best - a real, if rare, wrong guess (an id that
    // looks stable but is actually per-render, say) is still easy for
    // a human to spot and override when they can see the alternatives.
    // Heuristic "stable" vs "weak" confidence tag for a finished xpath
    // STRING - deliberately independent of buildXpathCandidates()/xPath()
    // itself (never changes which candidate wins or what order they come
    // in, only how each one is LABELED for a human choosing between
    // them). "weak" means: an absolute /html path, or a bare positional
    // index ([3], not part of an @attr='...' predicate) with no stable
    // attribute anchored anywhere else in the same expression - a
    // starts-with(@id, ...) or @data-testid='...' condition alongside an
    // index makes the whole thing meaningfully more resilient than a
    // raw document-order guess, so that combination still counts as
    // "stable". Everything else (an id/data-testid/name/aria-label/
    // placeholder/href/role match, a text-anchored container, a class
    // name) is "stable".
    function classifyXpathConfidence(xpath) {
        if (!xpath) return 'weak';
        if (xpath.indexOf('/html') !== -1) return 'weak';
        var hasBareIndex = /\[\d+\]/.test(xpath);
        if (!hasBareIndex) return 'stable';
        var hasStableAnchor = /@(id|data-testid|data-test|data-cy|name|aria-label|placeholder|href|role)\s*=/.test(xpath) ||
            /starts-with\(@(id|data-testid|data-test|data-cy)/.test(xpath);
        return hasStableAnchor ? 'stable' : 'weak';
    }

    function buildXpathCandidates(el, labelText, maxCount) {
        maxCount = maxCount || 3;
        var out = [];

        function addIfNew(candidate) {
            if (!candidate) return;
            if (out.indexOf(candidate) !== -1) return;
            if (out.length >= maxCount) return;
            out.push(candidate);
        }

        addIfNew(xPath(el, labelText));

        try {
            if (el.id) {
                addIfNew("//*[@id=" + JSON.stringify(el.id).replace(/"/g, "'") + "]");
            }
        } catch (e) {}

        try {
            var tag = el.tagName.toLowerCase();
            var fText = (el.textContent || '').trim().replace(/\s+/g, ' ');
            if (fText && fText.length > 0 && fText.length <= 60) {
                var literal = "'" + fText.replace(/'/g, "\\'") + "'";
                // reuses xpathIsUniqueFor directly - this is a narrower,
                // independent probe, not another full tier walk
                var exactTextCandidate = '//' + tag + "[normalize-space(.)=" + literal + "]";
                if (xpathIsUniqueFor(el, exactTextCandidate)) addIfNew(exactTextCandidate);
            }
        } catch (e) {}

        try {
            var altAttrs = ['data-testid', 'data-test', 'data-cy', 'name', 'aria-label', 'placeholder'];
            for (var i = 0; i < altAttrs.length; i++) {
                var v = el.getAttribute ? el.getAttribute(altAttrs[i]) : null;
                if (!v) continue;
                var attrCandidate = '//*[@' + altAttrs[i] + "='" + v.replace(/'/g, "\\'") + "']";
                if (xpathIsUniqueFor(el, attrCandidate)) addIfNew(attrCandidate);
            }
        } catch (e) {}

        return out;
    }

    // the strongest, most stable attributes a test-automation-minded site
    // might expose - captured raw here, prioritized/tried in that order
    // during replay (see generator/script_generator.py resolve_and_act)
    var STRONG_ATTRS = ['data-testid', 'data-test', 'data-cy', 'name', 'aria-label',
        'placeholder', 'role', 'title', 'href', 'type'];

    // a physical click almost never lands exactly on the element that's
    // semantically "the thing the user interacted with" - it lands on
    // whatever's visually on top (an icon, a wrapping span, a product
    // image). Recording that literal DOM node produces a locator that's
    // only valid for that one specific render (an <img> at position 7 of
    // a product grid that reshuffles on every page load, for example).
    // Walking up to the nearest genuinely-interactive ancestor is what
    // makes the capture describe the actual control instead of whatever
    // pixel happened to be clicked - this is generic DOM/ARIA semantics,
    // not tied to any particular site's markup.
    var INTERACTIVE_TAGS = ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'OPTION'];
    var INTERACTIVE_ROLES = ['button', 'checkbox', 'radio', 'option', 'link', 'menuitem', 'tab', 'switch'];
    // real component libraries commonly wrap a card's actual link several
    // layers deeper than a hand-written page would (styling wrapper divs,
    // layout primitives, image/picture wrappers) - 8 was measured to be
    // one hop too shallow for a real product-card pattern (image -> picture
    // -> 5 layout divs -> the actual <a>, 9 hops from the click target),
    // which silently fell back to recording the raw <img> instead of the
    // real clickable link. 16 gives real-world nesting depth headroom
    // while still being a bounded stop, not an unbounded walk to <body>.
    var SEMANTIC_WALK_MAX_DEPTH = 16;

    function isInteractive(node) {
        var tag = node.tagName;
        if (INTERACTIVE_TAGS.indexOf(tag) !== -1) return true;
        if (tag === 'A' && node.hasAttribute('href')) return true;
        if (tag === 'LABEL') return true;
        var role = node.getAttribute && node.getAttribute('role');
        return !!(role && INTERACTIVE_ROLES.indexOf(role) !== -1);
    }

    // A menu / popover trigger is often an <img>, <svg> or <div> with no button role. Generic signals only:
    // aria-haspopup / aria-expanded / aria-controls, an onclick handler, tabindex >= 0, or the element that
    // declares cursor:pointer. Used only when the standard interactive walk below finds nothing.
    function afqaExtendedClickable(el) {
        try {
            var n = el, d = 0, ptr = null;
            while (n && n.nodeType === 1 && d < SEMANTIC_WALK_MAX_DEPTH) {
                var tg = n.tagName;
                if (tg === 'BODY' || tg === 'HTML' || tg === 'MAIN') break;      // never the whole page
                // STRONG signals: the element itself
                if (n.hasAttribute('aria-haspopup') || n.hasAttribute('aria-expanded') || n.hasAttribute('contenteditable') && n.getAttribute('contenteditable') !== 'false') return n;
                // never a container, and never walk past one
                if (afqaIsContainerLike(n)) break;
                // WEAK signals, accepted only on an element that is not container-like
                if (n.hasAttribute('aria-controls') || n.hasAttribute('onclick') || typeof n.onclick === 'function') return n;
                var ti = n.getAttribute('tabindex');
                if (ti !== null && parseInt(ti, 10) >= 0) return n;
                if (getComputedStyle(n).cursor === 'pointer') ptr = n;
                else if (ptr) break;
                n = n.parentElement; d++;
            }
            return ptr;
        } catch (eExtClickable) {}
        return null;
    }

    function resolveSemanticTarget(el) {
        if (!(el instanceof Element)) return el;
        var node = el;
        var depth = 0;
        while (node && node.nodeType === Node.ELEMENT_NODE && depth < SEMANTIC_WALK_MAX_DEPTH) {
            if (isInteractive(node)) {
                // a label's real target is the form control it's bound to
                // (nested or via for=) - the label wrapper itself isn't
                // what replay should click
                if (node.tagName === 'LABEL' && node.control) return node.control;
                return node;
            }
            node = node.parentElement;
            depth++;
        }
        // nothing semantic found within a reasonable distance - fall back
        // to the original physical target (some custom widgets genuinely
        // are a bare div/span with its own click handler)
        return afqaExtendedClickable(el) || el;
    }

    // RC1: identical walk to resolveSemanticTarget above, MINUS its
    // "LABEL -> node.control" substitution - CONFIRMED REAL BUG that
    // substitution causes: a real custom checkbox/radio/sort-option row
    // is near-universally a visible <label>...text...</label> wrapping
    // an invisible native <input> (kept for accessibility/form
    // semantics only) - jumping straight to that input is exactly
    // backwards for act_target, which needs to stay on the VISIBLE
    // element the user's pointer was actually on so replay can find and
    // click something that's actually on screen. Used ONLY for
    // act_target; every other resolveSemanticTarget() call site (the
    // mousedown snapshot and the click handler's own dedup comparisons)
    // is unchanged and must stay unchanged - those compare identity
    // across TWO physical click events for the SAME gesture (a label's
    // own click plus the browser's native forwarded click directly on
    // its control), which only agree in the first place because both
    // already resolve to the control.
    function _hasNoLayoutBox(node) {
        try {
            var r = node.getBoundingClientRect();
            return r.width === 0 && r.height === 0;
        } catch (e) {
            return false;
        }
    }

    function resolveSemanticActTarget(el) {
        if (!(el instanceof Element)) return el;
        var node = el;
        var depth = 0;
        while (node && node.nodeType === Node.ELEMENT_NODE && depth < SEMANTIC_WALK_MAX_DEPTH) {
            if (isInteractive(node)) {
                // a checkbox/radio <input> with NO layout box at all
                // (display:none, or an ancestor that is) can never
                // actually be the thing replay clicks - it structurally
                // isn't there to click, regardless of act_target's own
                // "stay visible" goal. Keep walking past it to the next
                // interactive ancestor (its wrapping label/row) instead
                // of stopping on something un-clickable. An input that's
                // merely opacity:0 (a real box, just invisible - the
                // other very common custom-checkbox technique) is left
                // alone: it genuinely IS where the click landed and
                // Playwright can interact with it directly at that same
                // screen position.
                if (
                    node.tagName === 'INPUT' &&
                    ['checkbox', 'radio'].indexOf((node.type || '').toLowerCase()) !== -1 &&
                    _hasNoLayoutBox(node)
                ) {
                    node = node.parentElement;
                    depth++;
                    continue;
                }
                return node;
            }
            node = node.parentElement;
            depth++;
        }
        return afqaExtendedClickable(el) || el;
    }

    // strips private-use-area icon-font codepoints (U+E000-U+F8FF) - a
    // FontAwesome/Material/etc icon font renders its glyphs at these
    // codepoints, so an element's rendered "text" can be a meaningless
    // PUA character (or, per a CONFIRMED real recording, a spinner glyph
    // that transiently replaces a button's real label - see the
    // _preClickSnapshot comment above) rather than anything a human or a
    // future replay run could recognize. Mirrors
    // generator/script_generator.py's own _strip_icon_font_text exactly,
    // so recording-time and replay-time agree on what counts as "real"
    // text. Never used to REJECT an element, only to keep its glyph out
    // of locator/label text; icon_class_hint (see iconClassHint below)
    // is the separate, additive fallback for icon-only elements.
    var _ICON_FONT_PUA_RE = /[-]/g;
    function _stripIconFontText(s) {
        if (!s) return '';
        return String(s).replace(_ICON_FONT_PUA_RE, '').trim();
    }

    // an <input>/<textarea>'s OWN .value is the right thing to read as
    // its "text" only when that value is an author-set static label
    // (type=submit/button/reset/image - the same handful of types where
    // the DOM itself treats .value as display text, not user data);
    // for every other type, .value is whatever the USER (or this very
    // action) just typed, which must never be baked into a locator -
    // CONFIRMED REAL: 081203's own OTP fill step recorded
    // //div[normalize-space(.)='1234']/input, anchored on the digits
    // just filled into that exact input, which cannot match any run
    // that ever fills a different value into the same field.
    function _isUserEditableValueField(el) {
        if (!el || !el.tagName) return false;
        if (el.tagName === 'TEXTAREA') return true;
        if (el.tagName === 'INPUT') {
            var t = (el.type || 'text').toLowerCase();
            return ['button', 'submit', 'reset', 'image', 'checkbox', 'radio'].indexOf(t) === -1;
        }
        return false;
    }

    // best-effort accessible name, checked in roughly the priority order
    // browsers/screen readers use - generic, no site knowledge required
    function accessibleName(el) {
        var ariaLabel = _stripIconFontText(el.getAttribute('aria-label'));
        if (ariaLabel) return ariaLabel;
        var labelledby = el.getAttribute('aria-labelledby');
        if (labelledby) {
            var txt = labelledby.split(/\s+/).map(function (id) {
                var ref = document.getElementById(id);
                return ref ? (ref.innerText || ref.textContent || '') : '';
            }).join(' ').trim();
            txt = _stripIconFontText(txt);
            if (txt) return txt;
        }
        if (el.tagName === 'IMG') {
            var alt = _stripIconFontText(el.alt);
            if (alt) return alt;
        }
        if ((el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el.placeholder) {
            var ph = _stripIconFontText(el.placeholder);
            if (ph) return ph;
        }
        var ownText = el.innerText || (_isUserEditableValueField(el) ? '' : el.value) || '';
        return _stripIconFontText(ownText.trim().slice(0, 80));
    }

    // CONFIRMED REAL BUG this fixes: a filter-chip trigger (a chevron/
    // arrow icon with no readable label of its own, sitting next to a
    // text label inside the same small chip container) has effectively
    // empty innerText - it slips under findCheckboxTarget's own "step
    // 0.5" ownText.length > 2 exclusion (a decorative single-glyph
    // arrow is length 1), which then lets the ancestor/descendant search
    // below run and grab the chip's own hover-revealed checkbox PANEL,
    // recording the click as a "check" on some checkbox inside it
    // instead of the actual chip click.
    //
    // An earlier version of this fix gated the whole descendant search
    // on "does rawEl have its own direct text" - that broke a real,
    // equally common widget shape: a plain, non-<label> row wrapping its
    // OWN readable text alongside a custom visual box and a native
    // (often visually hidden) checkbox as sibling children -
    // <div>Printed <span class="box"></span><input type="checkbox"
    // hidden></div> - which unconditionally lost its "check"
    // classification the same way the chip's chevron icon needed to.
    // The actual distinguishing signal was never "does rawEl have text"
    // - it's "is there exactly ONE checkbox candidate in the searched
    // container, or several": a row with its own single, unambiguous
    // checkbox is safe to search into regardless of whether rawEl
    // carries a label; a container with MULTIPLE checkboxes (a whole
    // filter panel with several options) can never be safely collapsed
    // to "the click meant THIS one" and is now treated as an ordinary
    // click instead of guessing which checkbox was meant.
    //
    // Deliberately NOT also gated on a plain display/visibility check -
    // a custom-styled checkbox very commonly hides its real native
    // <input> PERMANENTLY (the `hidden` attribute, opacity:0 - a design
    // choice, not a reveal-in-progress state) while a sibling element
    // provides the visible checked/unchecked box, and that reads
    // identically to "not revealed yet" from a pure display/visibility
    // check - there is no way to tell those apart by visibility alone.
    //
    // CONFIRMED REAL BUG uniqueness ALONE still missed: a chip whose
    // hover panel holds exactly ONE option ("Country of Origin" -> just
    // "India") makes the count check above trivially pass for ANY click
    // anywhere in the whole chip (its text, its arrow) - not just a
    // click genuinely on the India row. Two further, independent
    // conditions are required together with uniqueness, not instead of
    // it:
    //
    // (1) the click must have actually landed inside the candidate's
    //     OWN row - its nearest <label> ancestor (or its own immediate
    //     parent, when nothing wraps it in a label) - not merely
    //     somewhere inside a large shared container the checkbox
    //     happens to also be inside. Approximated via the ACTUAL
    //     clicked element's (clickOriginEl) own bounding-box center -
    //     that element is, by definition, exactly where the click
    //     landed.
    // (2) the candidate must NOT be something that only became visible
    //     because of the CURRENT hover - reuses _ambientVisiblePrev,
    //     the same pre-hover baseline snapshot already built for
    //     hover-chain detection (see its own docstring): a checkbox
    //     that wasn't part of that baseline was just revealed by
    //     hovering to reach this click, so the click was never for it.
    //
    // Together these three conditions correctly separate the real cases:
    // a single always-present, always-hidden-by-design checkbox in a
    // small custom row (uniqueness + click lands in its own row + it
    // was already there before any hover) is accepted; a single-item
    // hover panel (uniqueness alone would pass, but the click landed
    // outside the India row AND/OR India only just became visible) is
    // correctly rejected; a multi-item hover panel is already rejected
    // by uniqueness regardless of the other two.
    function _findRowContainerForCheckbox(cb) {
        var node = cb;
        var depth = 0;
        while (node && node.nodeType === Node.ELEMENT_NODE && depth < 4) {
            if (node.tagName === 'LABEL') return node;
            node = node.parentElement;
            depth++;
        }
        return cb.parentElement || cb;
    }

    function _findUniqueCheckboxDescendant(node, selector, clickOriginEl) {
        if (!node || !node.querySelectorAll) return null;
        var matches;
        try {
            matches = node.querySelectorAll(selector);
        } catch (e) {
            return null;
        }
        if (!matches || matches.length !== 1) return null;
        var cand = matches[0];

        if (clickOriginEl && clickOriginEl.getBoundingClientRect) {
            try {
                var originRect = clickOriginEl.getBoundingClientRect();
                var ox = originRect.left + originRect.width / 2;
                var oy = originRect.top + originRect.height / 2;
                var rowRect = _findRowContainerForCheckbox(cand).getBoundingClientRect();
                if (ox < rowRect.left || ox > rowRect.right || oy < rowRect.top || oy > rowRect.bottom) {
                    return null;
                }
            } catch (eRow) {
                return null;
            }
        }

        if (
            typeof _ambientVisiblePrev !== 'undefined' && _ambientVisiblePrev &&
            (Date.now() - _ambientVisiblePrev.time) < 500 &&
            !_ambientVisiblePrev.visibleSet.has(cand)
        ) {
            return null;
        }

        return cand;
    }

    // used by findCheckboxTarget's ancestor search below - a genuine
    // checkbox-plus-label/icon WIDGET is a small, local UI row, not a
    // large page section. Purely geometric (rendered width/height),
    // never a class/id/text check, so it works identically on any site.
    var MAX_CHECKBOX_WIDGET_WIDTH = 400;
    var MAX_CHECKBOX_WIDGET_HEIGHT = 150;

    function _isSmallEnoughForCheckboxWidget(node) {
        if (!node || !node.getBoundingClientRect) return false;
        try {
            var r = node.getBoundingClientRect();
            return r.width > 0 && r.height > 0 &&
                r.width <= MAX_CHECKBOX_WIDGET_WIDTH && r.height <= MAX_CHECKBOX_WIDGET_HEIGHT;
        } catch (e) {
            return false;
        }
    }

    function _isDirectCheckboxOrRadio(el) {
        if (!(el instanceof Element)) return false;
        if (el.tagName === 'INPUT') {
            var t = (el.getAttribute('type') || '').toLowerCase();
            if (t === 'checkbox' || t === 'radio') return true;
        }
        var r = el.getAttribute ? (el.getAttribute('role') || '') : '';
        return r === 'checkbox' || r === 'radio' || r === 'switch';
    }

    // Used only by the step-0.5 button/link exclusion above: true when
    // rawEl ITSELF (never a further-out ancestor) is unambiguously a
    // checkbox/radio/switch, or sits inside a <label> that wraps/points
    // at one - see that exclusion's own comment for why this matters
    // (a role="button" row that still contains a real radio input).
    function _isCheckboxOrRadioTargetItself(rawEl) {
        if (_isDirectCheckboxOrRadio(rawEl)) return true;
        var node = rawEl;
        var depth = 0;
        while (node && node.nodeType === Node.ELEMENT_NODE && depth < 6 && node.tagName !== 'BODY') {
            if (node.tagName === 'LABEL') {
                if (node.control && _isDirectCheckboxOrRadio(node.control)) return true;
                var forId = node.getAttribute('for');
                if (forId) {
                    var inputFor = document.getElementById(forId);
                    if (inputFor && _isDirectCheckboxOrRadio(inputFor)) return true;
                }
                if (node.querySelector('input[type="checkbox"], input[type="radio"], [role="checkbox"], [role="radio"], [role="switch"]')) {
                    return true;
                }
            }
            node = node.parentElement;
            depth++;
        }
        return false;
    }

    // FIX D: strict "does this actually expose checked/unchecked state"
    // check, used to gate the purely-geometric "small square" heuristics
    // (branches 5/6 below) - deliberately narrower than
    // isCheckboxCheckedState() further down (which also trusts class-
    // name/icon-presence heuristics for deciding CURRENT checked-ness
    // once something is ALREADY known to be a checkbox; those same
    // signals are too loose to decide whether it's a checkbox AT ALL -
    // almost any small icon button would match "contains an svg").
    function _exposesCheckedState(el) {
        if (!el) return false;
        if (el.tagName === 'INPUT') {
            var t = (el.getAttribute('type') || '').toLowerCase();
            if (t === 'checkbox' || t === 'radio') return true;
        }
        if (el.hasAttribute && (el.hasAttribute('aria-checked') || el.hasAttribute('data-checked'))) {
            return true;
        }
        if (el.querySelector) {
            var nested = el.querySelector('input[type="checkbox"], input[type="radio"], [aria-checked], [data-checked]');
            if (nested) return true;
        }
        return false;
    }

    // FIX D: action words that, when they appear in an icon-bearing
    // element's own accessible name/title/nearby text, mean this is an
    // ACTION button (add/remove/send/continue/verify/pick a person,
    // etc), never a checkbox/radio - purely a word list, no site-
    // specific selector. Checked as whole tokens (split on non-
    // alphanumeric, like the consent-overlay accept-word matching
    // elsewhere in this project) so e.g. "sender" doesn't false-match
    // "send", and "+"/"-" are checked as literal single-character
    // tokens since they're not alphanumeric words at all.
    var ACTION_WORDS = ['add', 'remove', 'send', 'continue', 'verify', 'pick'];
    var ACTION_SYMBOLS = ['+', '-'];

    function _looksLikeActionIcon(el) {
        if (!el || !el.querySelector) return false;
        var svg = el.querySelector('svg');
        if (!svg) return false;
        var pieces = [
            el.getAttribute ? (el.getAttribute('aria-label') || '') : '',
            el.getAttribute ? (el.getAttribute('title') || '') : '',
            svg.getAttribute ? (svg.getAttribute('aria-label') || '') : '',
            (el.innerText || el.textContent || ''),
        ];
        var combined = pieces.join(' ').trim();
        if (ACTION_SYMBOLS.indexOf(combined) !== -1) return true;
        var lower = combined.toLowerCase();
        var tokens = lower.split(/[^a-z0-9]+/).filter(Boolean);
        return ACTION_WORDS.some(function (w) { return tokens.indexOf(w) !== -1; });
    }

    // FIX D debug field ("classified_by"): set as a side effect by
    // findCheckboxTarget immediately before each of its own non-null
    // return points, naming which branch actually classified this click
    // as a checkbox/radio - read right after the call (see buildProfile
    // and the _snap.checkboxTarget capture site) and written into the
    // recorded action as a plain diagnostic field. findCheckboxTarget's
    // own signature/return value is completely unchanged (still just
    // element-or-null) - this is a parallel, additive side channel, not
    // a refactor of its callers.
    var lastCheckboxClassifiedBy = null;

    function findCheckboxTarget(rawEl) {
        lastCheckboxClassifiedBy = null;
        if (!(rawEl instanceof Element)) return null;

        // 0. Exclusion: Top navigation bars, headers, tabs, and links are NEVER checkboxes
        var checkNav = rawEl;
        var navDepth = 0;
        while (checkNav && checkNav.nodeType === Node.ELEMENT_NODE && navDepth < 6 && checkNav.tagName !== 'BODY') {
            var tag = checkNav.tagName;
            if (tag === 'NAV' || tag === 'HEADER') return null;
            var r = checkNav.getAttribute ? (checkNav.getAttribute('role') || '') : '';
            if (r === 'navigation' || r === 'tablist' || r === 'tab' || r === 'menu') return null;
            var c = (checkNav.className || '').toString().toLowerCase();
            if (c.indexOf('header') !== -1 || c.indexOf('navbar') !== -1 || c.indexOf('topbar') !== -1 || c.indexOf('nav-bar') !== -1) {
                return null;
            }
            checkNav = checkNav.parentElement;
            navDepth++;
        }

        // 0.5. Exclusion: an unambiguous button/link - or, per FIX D,
        // anything else that structurally behaves like an action control
        // rather than a toggle - is never a checkbox, no matter what any
        // of the heuristics below might otherwise find nearby (an
        // ancestor/descendant that merely LOOKS checkbox-shaped is
        // beside the point once the actual click target already has
        // real action semantics of its own). Never inferred from aria-
        // pressed or any DOM change after the click.
        //
        // Does NOT apply when the actual click target itself is
        // unambiguously a checkbox/radio/switch, or sits inside a <label>
        // that wraps/points at one - a whole row can legitimately carry
        // role="button" (or descriptive text, or an action-shaped icon)
        // for click-target convenience while still containing a real
        // radio/checkbox input (a settings row, a participant-picker
        // row, etc); only checked against rawEl itself (and a <label>
        // ancestor), never against a further-out ancestor - that's what
        // still lets a genuine button/link/action-icon elsewhere in that
        // same row be excluded normally.
        if (!_isCheckboxOrRadioTargetItself(rawEl)) {
            // (b) FIX D: rawEl's OWN visible text (not an aggregate of
            // ancestors, which would also pick up an unrelated sibling
            // label's text next to a genuine small-square checkbox and
            // wrongly exclude that legitimate case) - a real action
            // button/link almost always has its own short, readable
            // label; a bare toggle control usually has none.
            //
            // REFINED (real regression this fixes): that heuristic alone
            // wrongly excludes an equally common, legitimate widget - a
            // plain, non-<label> row that wraps its OWN readable text
            // alongside a custom visual box and a native (often visually
            // hidden) checkbox as sibling children, e.g. <div>Printed
            // <span class="box"></span><input type="checkbox"
            // hidden></div>. The same uniqueness principle
            // _findUniqueCheckboxDescendant already uses below (see its
            // own docstring) resolves the conflict: if rawEl - bounded to
            // plausibly BE a self-contained widget, not a large page
            // section - has EXACTLY ONE checkbox/radio/switch descendant
            // regardless of that descendant's own current visibility
            // (see that function's own reasoning for why visibility
            // can't distinguish "hidden by design" from "not revealed
            // yet"), this is unambiguous enough to skip the length-based
            // exclusion for. A container with SEVERAL such descendants
            // (a whole filter panel with multiple options) still finds
            // none here (matches.length !== 1) and is excluded exactly
            // as before.
            var ownText = (rawEl.innerText || rawEl.textContent || '').trim();
            // NOT bounded by _isSmallEnoughForCheckboxWidget here,
            // unlike step 4's ancestor walk below - this searches rawEl's
            // OWN subtree only (the exact thing that was actually
            // clicked), never an outer ancestor's, so a wide, full-width
            // flex row (a filter/settings row commonly stretches to fill
            // its container - a real, common layout, not a sign of
            // ambiguity) never wrongly loses this check just for being
            // visually wide. Uniqueness within rawEl's own subtree is
            // already the precise signal; the size bound exists for the
            // OUTWARD ancestor search, where growing container size
            // really can mean "now searching a shared section with other,
            // unrelated widgets in it."
            var _rawElOwnUniqueCheckbox = _findUniqueCheckboxDescendant(
                rawEl, 'input[type="checkbox"], [role="checkbox"], [role="menuitemcheckbox"], [role="switch"]', rawEl,
            );
            if (ownText.length > 2 && rawEl.tagName !== 'LABEL' && !_rawElOwnUniqueCheckbox) {
                return null;
            }

            var checkBtn = rawEl;
            var btnDepth = 0;
            while (checkBtn && checkBtn.nodeType === Node.ELEMENT_NODE && btnDepth < 6 && checkBtn.tagName !== 'BODY') {
                var btnTag = checkBtn.tagName;
                var btnRole = checkBtn.getAttribute ? (checkBtn.getAttribute('role') || '') : '';
                var btnType = (btnTag === 'INPUT' && checkBtn.getAttribute) ? (checkBtn.getAttribute('type') || '').toLowerCase() : '';
                if (
                    btnTag === 'BUTTON' || btnTag === 'A' || btnRole === 'button' ||
                    (btnTag === 'INPUT' && (btnType === 'submit' || btnType === 'button'))
                ) {
                    return null;
                }
                // (a) FIX D: an explicit onclick attribute, or a real
                // interactive affordance (tabindex="0" - the standard
                // way a non-native element opts into keyboard/focus
                // interactivity, a strong React/custom-component signal)
                // combined with a pointer cursor
                var hasOnclickAttr = checkBtn.hasAttribute && checkBtn.hasAttribute('onclick');
                var isFocusable = checkBtn.getAttribute && checkBtn.getAttribute('tabindex') === '0';
                var cursorPointer = false;
                try {
                    cursorPointer = getComputedStyle(checkBtn).cursor === 'pointer';
                } catch (eCursor) {}
                if (hasOnclickAttr || (isFocusable && cursorPointer)) {
                    return null;
                }
                // (c) FIX D: an icon (svg) whose own accessible name/
                // title/text suggests an action (+, -, add, remove,
                // send, continue, verify, pick) - never a toggle
                if (_looksLikeActionIcon(checkBtn)) {
                    return null;
                }
                checkBtn = checkBtn.parentElement;
                btnDepth++;
            }
        }

        // 1. Direct native input[type="checkbox"|"radio"] - radio added
        // alongside checkbox (previously handled only indirectly, if at
        // all, by the ancestor/descendant heuristics further below) since
        // a plain, unambiguous radio input is exactly as much a real
        // toggle control as a checkbox is; purely additive; a page target
        // this would ever have matched.
        if (rawEl.tagName === 'INPUT') {
            var directType = (rawEl.type || '').toLowerCase();
            if (directType === 'checkbox' || directType === 'radio') {
                lastCheckboxClassifiedBy = 'native-input-direct';
                return rawEl;
            }
        }

        // 2. Direct ARIA role="checkbox"|"radio"|"switch"|"menuitemcheckbox"
        var role = rawEl.getAttribute ? rawEl.getAttribute('role') : null;
        if (role === 'checkbox' || role === 'menuitemcheckbox' || role === 'switch' || role === 'radio') {
            lastCheckboxClassifiedBy = 'aria-role-direct';
            return rawEl;
        }

        // 3. Direct LABEL tag
        if (rawEl.tagName === 'LABEL') {
            // RC1: widened from checkbox-only to also recognize radio -
            // a real single-select filter/sort option (Myntra's own
            // "Price: Low to High" radio group, confirmed via a live
            // recording) is exactly as much a <label>-wraps-native-input
            // widget as a checkbox is; excluding radio here meant
            // state_target could never be populated for it at all, even
            // though act_target's own fix (resolveSemanticActTarget)
            // already handles the label side correctly on its own.
            if (
                rawEl.control && rawEl.control.tagName === 'INPUT' &&
                ['checkbox', 'radio'].indexOf((rawEl.control.type || '').toLowerCase()) !== -1
            ) {
                lastCheckboxClassifiedBy = 'label-control';
                return rawEl.control;
            }
            var forId = rawEl.getAttribute('for');
            if (forId) {
                var inputFor = document.getElementById(forId);
                if (inputFor && (inputFor.tagName === 'INPUT' || inputFor.getAttribute('role') === 'checkbox' || inputFor.getAttribute('role') === 'radio')) {
                    lastCheckboxClassifiedBy = 'label-for';
                    return inputFor;
                }
            }
            var inCb = _findUniqueCheckboxDescendant(
                rawEl, 'input[type="checkbox"], input[type="radio"], [role="checkbox"], [role="radio"]', rawEl,
            );
            if (inCb) {
                lastCheckboxClassifiedBy = 'label-descendant';
                return inCb;
            }
        }

        // 4. Ancestor search (up to 5 levels) for semantic input or ARIA checkbox control
        //
        // CONFIRMED REAL BUG, fixed here: every node.querySelector(...)
        // call below searches that ancestor's ENTIRE descendant subtree,
        // not just its immediate structural neighborhood. A genuine
        // checkbox-plus-label/icon WIDGET (what this search exists to
        // find - clicking an icon or label text a couple of DOM levels
        // above its own checkbox input) is a small, self-contained UI
        // row. But by the time this walk reaches a large shared
        // container a few levels up (a product page's main content div,
        // say), that same unbounded subtree search can just as easily
        // find a COMPLETELY UNRELATED checkbox living anywhere else
        // inside it (a filter toggle, a "select all", an unrelated
        // details-expander styled as a checkbox) - silently merging an
        // unrelated click into a "check" action on the wrong element
        // entirely, while the actually-clicked element's own click
        // never gets recorded as itself. _isSmallEnoughForCheckboxWidget
        // bounds every querySelector-based match below to the ancestor
        // it was found in being small enough to plausibly BE that
        // local widget - never a class name, id, or text check, purely
        // geometric, so this works identically on any site.
        //
        // SECOND CONFIRMED REAL BUG this also fixes: a filter-chip's own
        // chevron/toggle icon (own text short enough - even a single
        // decorative glyph - to slip under the step-0.5 exclusion above)
        // sits right next to the chip's own hover-revealed checkbox
        // PANEL in the same small container. _isSmallEnoughForCheckboxWidget
        // alone doesn't catch this: the panel is small (it's meant to
        // be), so the search still finds a real checkbox in it and
        // misrecords the click as a "check" instead of the actual chip
        // click. Every querySelector-based descendant search below now
        // uses _findUniqueCheckboxDescendant - see its own docstring for
        // why "exactly one candidate in the container" is the actual
        // safe/unsafe boundary. Ancestor NODE checks (its own tag/role)
        // are unaffected either way.
        var node = rawEl;
        var depth = 0;
        while (node && node.nodeType === Node.ELEMENT_NODE && depth < 5 && node.tagName !== 'BODY' && node.tagName !== 'HTML') {
            // rawEl's own subtree was already searched, unbounded by
            // size, in step 0.5 above (see _rawElOwnUniqueCheckbox's own
            // comment for why a wide/full-width row must not lose this
            // just for being visually wide) - reuse that same result
            // here on the very first iteration (node === rawEl) instead
            // of re-searching it a second time through the size-bounded
            // path below, which would otherwise reject a genuinely wide
            // row's own unique checkbox right back out again.
            if (node === rawEl && _rawElOwnUniqueCheckbox) {
                lastCheckboxClassifiedBy = 'own-unique-descendant';
                return _rawElOwnUniqueCheckbox;
            }
            if (node.tagName === 'LABEL') {
                if (node.control && node.control.tagName === 'INPUT' && (node.control.type || '').toLowerCase() === 'checkbox') {
                    lastCheckboxClassifiedBy = 'ancestor-label-control';
                    return node.control;
                }
                if (_isSmallEnoughForCheckboxWidget(node)) {
                    var childCb = _findUniqueCheckboxDescendant(node, 'input[type="checkbox"], [role="checkbox"]', rawEl);
                    if (childCb) {
                        lastCheckboxClassifiedBy = 'ancestor-label-descendant';
                        return childCb;
                    }
                }
            }
            var nodeRole = node.getAttribute ? node.getAttribute('role') : null;
            if (nodeRole === 'checkbox' || nodeRole === 'menuitemcheckbox' || nodeRole === 'switch') {
                lastCheckboxClassifiedBy = 'ancestor-aria-role';
                return node;
            }
            if (_isSmallEnoughForCheckboxWidget(node)) {
                var childCb2 = _findUniqueCheckboxDescendant(
                    node, 'input[type="checkbox"], [role="checkbox"], [role="menuitemcheckbox"], [role="switch"]', rawEl,
                );
                if (childCb2) {
                    lastCheckboxClassifiedBy = 'ancestor-widget-descendant';
                    return childCb2;
                }
            }
            var cls = (node.className || '').toString().toLowerCase();
            var dt = node.getAttribute ? (node.getAttribute('data-type') || node.getAttribute('data-testid') || '') : '';
            if (
                (cls.indexOf('checkbox') !== -1 || cls.indexOf('chk') !== -1 || dt.indexOf('checkbox') !== -1) &&
                _isSmallEnoughForCheckboxWidget(node)
            ) {
                var innerInput = _findUniqueCheckboxDescendant(node, 'input[type="checkbox"], [role="checkbox"]', rawEl);
                lastCheckboxClassifiedBy = innerInput ? 'ancestor-classname-descendant' : 'ancestor-classname-self';
                return innerInput || node;
            }
            node = node.parentElement;
            depth++;
        }

        // 5. Generic Custom Visual Checkbox Box (React Native for Web, Tailwind, custom div/span square boxes)
        if (rawEl.tagName === 'BUTTON' || rawEl.tagName === 'A' || rawEl.tagName === 'INPUT' || rawEl.tagName === 'TEXTAREA' || rawEl.tagName === 'SELECT') {
            return null;
        }

        var rect = rawEl.getBoundingClientRect ? rawEl.getBoundingClientRect() : null;
        if (rect && rect.y >= 65 && rect.width >= 10 && rect.width <= 40 && rect.height >= 10 && rect.height <= 40) {
            var aspect = rect.width / (rect.height || 1);
            if (aspect >= 0.5 && aspect <= 1.8) {
                var pNode = rawEl.parentElement;
                var pDepth = 0;
                while (pNode && pNode.nodeType === Node.ELEMENT_NODE && pDepth < 4 && pNode.tagName !== 'BODY') {
                    var pText = (pNode.innerText || pNode.textContent || '').trim();
                    var pCls = (pNode.className || '').toString().toLowerCase();
                    var pRole = pNode.getAttribute ? (pNode.getAttribute('role') || '') : '';
                    if (pText && pText.length > 0 && pText.length <= 150) {
                        if (pCls.indexOf('close') === -1 && pCls.indexOf('search') === -1 && pCls.indexOf('nav') === -1 && pRole !== 'button' && pRole !== 'link' && pRole !== 'tab') {
                            // 1. Prefer actual native input or explicit ARIA control inside the option row
                            var actualInPNode = pNode.querySelector ? pNode.querySelector('input[type="checkbox"], [role="checkbox"], [role="menuitemcheckbox"], [role="switch"]') : null;
                            if (actualInPNode) {
                                lastCheckboxClassifiedBy = 'geometric-square-widget-input';
                                return actualInPNode;
                            }
                            // 2. Check for associated label via for attribute
                            if (rawEl.id) {
                                try {
                                    var lFor = document.querySelector('label[for="' + CSS.escape(rawEl.id) + '"]');
                                    if (lFor) {
                                        lastCheckboxClassifiedBy = 'geometric-square-labeled';
                                        return rawEl;
                                    }
                                } catch (e) {}
                            }
                            // 3. FIX D: only return rawEl itself (the bare
                            // small visual square, purely on GEOMETRY) if
                            // it (or a hidden input inside it) actually
                            // exposes checked/aria-checked state - size and
                            // position alone are not enough; an action
                            // icon (a "+", a send arrow, ...) can easily be
                            // the same small square shape as a real
                            // checkbox.
                            if (_exposesCheckedState(rawEl)) {
                                lastCheckboxClassifiedBy = 'geometric-square-fallback';
                                return rawEl;
                            }
                        }
                    }
                    pNode = pNode.parentElement;
                    pDepth++;
                }
            }
        }

        // 6. Generic Text Label clicked directly next to a small square visual checkbox box
        if (rect && rect.y >= 65 && rawEl.parentElement && rawEl.parentElement.children) {
            var siblings = rawEl.parentElement.children;
            for (var i = 0; i < siblings.length; i++) {
                var sib = siblings[i];
                if (sib !== rawEl) {
                    var sRect = sib.getBoundingClientRect ? sib.getBoundingClientRect() : null;
                    if (sRect && sRect.width >= 10 && sRect.width <= 40 && sRect.height >= 10 && sRect.height <= 40) {
                        var sAspect = sRect.width / (sRect.height || 1);
                        if (sAspect >= 0.5 && sAspect <= 1.8) {
                            var actualInSib = sib.querySelector ? sib.querySelector('input[type="checkbox"], [role="checkbox"]') : null;
                            if (actualInSib) {
                                lastCheckboxClassifiedBy = 'geometric-sibling-input';
                                return actualInSib;
                            }
                            // FIX D: same _exposesCheckedState gate as
                            // branch 5's own bare-geometry fallback - the
                            // sibling "square" must actually expose
                            // checked state, not just be the right size.
                            if (_exposesCheckedState(sib)) {
                                lastCheckboxClassifiedBy = 'geometric-sibling-fallback';
                                return sib;
                            }
                        }
                    }
                }
            }
        }

        return null;
    }

    // stable-identity check reused from STRONG_ATTRS' own definition of
    // "stable" (id, plus the same data-testid/data-test/data-cy names
    // already treated as strong attributes elsewhere in this file) -
    // not a new, separate notion of what counts as stable
    function hasStrongIdentity(el) {
        if (!el || !el.getAttribute) return false;
        if (el.id) return true;
        if (el.getAttribute('data-testid')) return true;
        if (el.getAttribute('data-test')) return true;
        if (el.getAttribute('data-cy')) return true;
        return false;
    }

    // Additive, LOCATOR-ONLY refinement - findCheckboxTarget() above is
    // the checkbox DETECTION logic and is untouched: its result still
    // fully decides role/accessible_name/expected_state, exactly as
    // before. This separately decides which element's id/css_path/
    // xpath/tag get recorded for replay, preferring a genuine, more
    // stable control when one actually exists near the detected
    // checkbox - never a different SEMANTIC target, only a more
    // reliable one to point the locator at. Generic: no site-specific
    // selectors, IDs, class names, or labels anywhere in this search.
    //
    // Falls through to returning checkboxTarget itself, completely
    // unchanged, in every case where nothing more stable is actually
    // found - the existing, already-working locator is kept rather
    // than ever fabricating one.
    function resolveCheckboxLocatorElement(checkboxTarget) {
        if (!checkboxTarget) return checkboxTarget;

        // already a native control - already the most stable/semantic
        // thing a checkbox locator can point to
        if (checkboxTarget.tagName === 'INPUT') return checkboxTarget;

        // already carries a real id or a strong data-* attribute -
        // nothing more stable to look for
        if (hasStrongIdentity(checkboxTarget)) return checkboxTarget;

        // 1. a genuine native checkbox/radio control nested inside the
        // detected element - the single most reliable, generic signal
        // of "the actual control", common when a div/span is purely a
        // custom visual wrapper around a real (often visually hidden)
        // input kept for accessibility/form semantics
        var nested = checkboxTarget.querySelector
            ? checkboxTarget.querySelector('input[type="checkbox"], input[type="radio"]')
            : null;
        if (nested) return nested;

        // 2. a genuine native checkbox/radio control as an immediate
        // sibling - common when the visual box and the real input are
        // siblings rather than parent/child. Only trusted when there is
        // EXACTLY one such sibling, so a row of several checkboxes
        // under the same parent is never guessed at.
        var parent = checkboxTarget.parentElement;
        if (parent && parent.children) {
            var siblingInputs = [];
            for (var i = 0; i < parent.children.length; i++) {
                var sib = parent.children[i];
                if (sib !== checkboxTarget && sib.tagName === 'INPUT') {
                    var t = (sib.type || '').toLowerCase();
                    if (t === 'checkbox' || t === 'radio') siblingInputs.push(sib);
                }
            }
            if (siblingInputs.length === 1) return siblingInputs[0];
        }

        // nothing more stable found nearby - keep the existing,
        // already-working target exactly as resolved above
        return checkboxTarget;
    }

    function _nativeCheckboxRoleDefault(el) {
        // 'radio' or 'checkbox' when el is a genuine native input of that
        // type (radio has no explicit role="..." attribute in real HTML -
        // it's an implicit ARIA role - so this is the only reliable
        // source for it); null for anything else, letting the caller keep
        // its own generic fallback for a non-native styled target.
        if (el && el.tagName === 'INPUT') {
            var t = (el.type || '').toLowerCase();
            if (t === 'radio' || t === 'checkbox') return t;
        }
        return null;
    }

    function isCheckboxCheckedState(el) {
        if (!el) return false;
        if (
            el.tagName === 'INPUT' &&
            ['checkbox', 'radio'].indexOf((el.type || '').toLowerCase()) !== -1
        ) {
            return !!el.checked;
        }
        if (el.hasAttribute && el.hasAttribute('aria-checked')) {
            return el.getAttribute('aria-checked') === 'true';
        }
        if (el.hasAttribute && el.hasAttribute('data-checked')) {
            return el.getAttribute('data-checked') === 'true';
        }
        var cls = (el.className || '').toString().toLowerCase();
        if (cls.indexOf('checked') !== -1 || cls.indexOf('active') !== -1 || cls.indexOf('selected') !== -1) {
            return true;
        }
        if (el.querySelector && el.querySelector('svg, [class*="check"], [class*="tick"], [class*="icon"]')) {
            return true;
        }
        if (el.parentElement && el.parentElement.querySelector && el.parentElement.querySelector('svg, [class*="check"], [class*="tick"]')) {
            return true;
        }
        return false;
    }

    // RC1 (checked-state race - CONFIRMED via the hidden-radio-sort
    // fixture: a plain live read of checkboxTarget.checked here, taken
    // from the SAME click event that resolved to a label/wrapper as
    // rawEl, still shows the PRE-click value). A native <input
    // type=checkbox|radio> only actually flips its own .checked as part
    // of ITS OWN "pre-click activation steps" - which run before ANY
    // listener sees ITS OWN click event, but that's a SEPARATE, later
    // click event the browser dispatches only once the ORIGINAL click
    // (whatever rawEl actually was - typically a wrapping <label>)
    // finishes bubbling and its own post-click activation behavior
    // forwards a synthetic click() to the control. Our capture-phase
    // document listener processes that ORIGINAL event synchronously,
    // before that forwarding ever happens, so checkboxTarget.checked
    // read at that point is always stale whenever rawEl isn't
    // checkboxTarget itself. When rawEl IS checkboxTarget (the user's
    // pointer landed on the native input directly), there is no
    // forwarding involved at all and the live read is already correct
    // (that control's own pre-click activation steps already ran before
    // this same click event reached us) - only the forwarded-click case
    // needs the platform-defined result predicted instead of read.
    function _predictedCheckedState(checkboxTarget, rawEl) {
        if (!checkboxTarget) return null;
        if (rawEl === checkboxTarget) {
            return isCheckboxCheckedState(checkboxTarget);
        }
        var type = (checkboxTarget.tagName === 'INPUT') ? (checkboxTarget.type || '').toLowerCase() : '';
        if (type === 'radio') return true;
        if (type === 'checkbox') return !isCheckboxCheckedState(checkboxTarget);
        return isCheckboxCheckedState(checkboxTarget);
    }

    // RC4 (real DOM evidence for the future) - a compact snapshot of the
    // actual markup around act_target/state_target at record time, so a
    // later replay failure (or tests/fixture_from_snapshot.py) can show
    // "here is exactly what the site's DOM looked like" instead of only
    // a locator profile that no longer matches after a site redesign.
    // Deliberately capped (~8KB total) and best-effort throughout - a
    // huge/unusual subtree must never abort or slow down the actual
    // recorded action just to gather this extra evidence.
    var DOM_CONTEXT_MAX_BYTES = 8192;
    var DOM_CONTEXT_MAX_ANCESTORS = 6;

    function _domContextComputedStyle(el) {
        try {
            var cs = window.getComputedStyle(el);
            return { display: cs.display, visibility: cs.visibility, opacity: cs.opacity };
        } catch (e) {
            return null;
        }
    }

    function _domContextHtmlChain(el) {
        var chain = [];
        var node = el;
        var depth = 0;
        while (node && node.nodeType === Node.ELEMENT_NODE && depth <= DOM_CONTEXT_MAX_ANCESTORS) {
            try {
                chain.push(node.outerHTML || '');
            } catch (e) {
                chain.push('');
            }
            node = node.parentElement;
            depth++;
        }
        return chain;
    }

    function _domContextTrimChain(chain, budgetBytes) {
        if (!chain || !chain.length) return chain;
        var perItemBudget = Math.max(200, Math.floor(budgetBytes / chain.length));
        return chain.map(function (html) {
            return html.length > perItemBudget
                ? html.slice(0, perItemBudget) + '...[truncated]'
                : html;
        });
    }

    function buildDomContext(actEl, stateEl) {
        try {
            var hasState = stateEl && stateEl !== actEl;
            var actBudget = hasState ? Math.floor(DOM_CONTEXT_MAX_BYTES * 0.6) : DOM_CONTEXT_MAX_BYTES;
            var stateBudget = DOM_CONTEXT_MAX_BYTES - actBudget;
            return {
                act_target_html_chain: _domContextTrimChain(_domContextHtmlChain(actEl), actBudget),
                act_target_style: _domContextComputedStyle(actEl),
                state_target_html_chain: hasState
                    ? _domContextTrimChain(_domContextHtmlChain(stateEl), stateBudget)
                    : null,
                state_target_style: hasState ? _domContextComputedStyle(stateEl) : null,
            };
        } catch (e) {
            return null;
        }
    }

    function getCheckboxAccessibleName(checkboxEl, rawEl) {
        var target = checkboxEl || rawEl;
        if (!target) return '';

        var ariaLabel = target.getAttribute && target.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.trim()) return ariaLabel.trim();

        var labelledby = target.getAttribute && target.getAttribute('aria-labelledby');
        if (labelledby) {
            var txt = labelledby.split(/\s+/).map(function (id) {
                var ref = document.getElementById(id);
                return ref ? (ref.innerText || ref.textContent || '') : '';
            }).join(' ').trim();
            if (txt) return txt;
        }

        if (target.id) {
            try {
                var labelFor = document.querySelector('label[for="' + CSS.escape(target.id) + '"]');
                if (labelFor) {
                    var lTxt = (labelFor.innerText || labelFor.textContent || '').trim();
                    if (lTxt) return lTxt;
                }
            } catch (e) {}
        }

        var parentLabel = target.closest ? target.closest('label') : null;
        if (parentLabel) {
            var pTxt = (parentLabel.innerText || parentLabel.textContent || '').trim();
            if (pTxt) return pTxt;
        }

        var pNode = (rawEl && rawEl.parentElement) ? rawEl.parentElement : (target.parentElement ? target.parentElement : null);
        var pDepth = 0;
        while (pNode && pNode.nodeType === Node.ELEMENT_NODE && pDepth < 4 && pNode.tagName !== 'BODY') {
            var rowTxt = (pNode.innerText || pNode.textContent || '').trim();
            if (rowTxt && rowTxt.length > 0 && rowTxt.length <= 100) {
                var lines = rowTxt.split(/[\r\n]+/);
                var firstLine = lines[0].trim();
                if (firstLine) return firstLine;
            }
            pNode = pNode.parentElement;
            pDepth++;
        }

        return accessibleName(target) || accessibleName(rawEl) || '';
    }

    // SHARED locator-profile builder - the same rich field set (id, name,
    // role, aria_label, accessible_name, placeholder, title, href,
    // css_path, xpath, text, element_text, tag, attributes) every click/
    // fill/select/submit/press target already gets via buildProfile()
    // below, factored out so ANY action type - including scroll, which
    // used to hand-rolled its own bare {css_path, tag} pair - can record
    // the exact same fallback data. accNameOverride lets a caller that
    // already computed the accessible name a different way (buildProfile's
    // own checkbox handling, see getCheckboxAccessibleName) supply it
    // directly instead of recomputing via accessibleName(el); omitted
    // (undefined) means "compute it normally for this element".
    // valueToExclude (optional, R2): the exact value a fill action just
    // typed into el - passed through to xPath() so no text tier can
    // anchor a locator on it (see xPath's own comment on excludeText).
    // Never set for click-family/checkbox callers, which have no typed
    // value to exclude in the first place.
    // BUG 2 (product card label includes hover-only content): a card-
    // shaped container's own innerText commonly includes repeated badge
    // text ("NEW" appearing once per product tile in the same grid, all
    // captured together because the recorded target is an ANCESTOR
    // container, not just the single badge) and CSS ::hover-revealed
    // overlay text ("Sizes: XXL", a size-picker strip that only renders
    // while the pointer is actually over the card - genuinely
    // indistinguishable from "always there" text once the mouse has to
    // be over the card to click it in the first place, so there is no
    // real "before hover" DOM snapshot to take here). Cleans up after
    // the fact instead: collapses consecutive duplicate lines (10x
    // "NEW" -> one "NEW") and drops any line that's just a "Sizes:"-
    // style overlay label, rather than trying to prevent the browser's
    // own :hover state from ever being visible in innerText at all.
    function _cleanCardLabelText(text) {
        if (!text) return text;
        var lines = text.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
        var deduped = [];
        for (var i = 0; i < lines.length; i++) {
            if (deduped.length === 0 || deduped[deduped.length - 1] !== lines[i]) {
                deduped.push(lines[i]);
            }
        }
        deduped = deduped.filter(function (line) {
            return !/^sizes\s*:/i.test(line);
        });
        return deduped.join(' ').trim().slice(0, 80);
    }

    function buildLocatorProfile(el, accNameOverride, valueToExclude) {
        const attrs = {};
        for (const a of el.attributes || []) {
            if (STRONG_ATTRS.includes(a.name)) {
                attrs[a.name] = a.value;
            }
        }
        var accName = (accNameOverride !== undefined) ? accNameOverride : accessibleName(el);
        // an element that is only a fallback target (no strong interactive role) and is container-like has no
        // name of its own in its long text: its label is aria-label / title / alt (short), else nothing
        var afqaWrapperLike = false;
        try { afqaWrapperLike = !isInteractive(el) && afqaIsContainerLike(el); } catch (eWrapperLike) {}
        if (afqaWrapperLike) {
            accName = _stripIconFontText(el.getAttribute('aria-label') || '') || _stripIconFontText(el.getAttribute('title') || '') ||
                _stripIconFontText(el.getAttribute('alt') || '');
            accName = (accName || '').slice(0, AFQA_OWN_LABEL_MAX_CHARS);
        }
        // BUG 2: the click target for a product-grid card commonly
        // resolves to a DESCENDANT of the real <a href> card (an image,
        // a price span) rather than the anchor itself - widen href
        // capture (and the numeric product id inside it, when present)
        // to the nearest enclosing <a href>, not just el itself, so a
        // card click always gets a stable href-based locator regardless
        // of which inner element actually resolved.
        var _cardAnchor = (el.tagName === 'A' && el.hasAttribute('href'))
            ? el
            : (el.closest ? el.closest('a[href]') : null);
        var _cardHref = _cardAnchor ? _cardAnchor.getAttribute('href') : null;
        var _cardProductId = null;
        if (_cardHref) {
            // the id must come from the URL PATH only - a digit run inside
            // the query string is usually a random tracking/session token
            // (not an identifier of the linked item), and replay used it
            // to decide two different links were "the same product"
            var _pidPath = _cardHref.split('#')[0].split('?')[0];
            var _pidMatch = _pidPath.match(/(\d{4,})/);
            _cardProductId = _pidMatch ? _pidMatch[1] : null;
        }
        var elementText = afqaWrapperLike ? '' : _stripIconFontText(
            (el.innerText || (_isUserEditableValueField(el) ? '' : el.value) || '').trim().slice(0, 80)
        );
        if (_cardAnchor) {
            elementText = _cleanCardLabelText(elementText);
        }
        var finalText = accName || elementText;
        // BUG 2: a plain <a> with no aria-label gets an IMPLICIT
        // accessible name computed from its own (raw, uncleaned) text
        // content - accName can independently carry the exact same
        // repeated-badge/overlay noise elementText was just cleaned of,
        // and finalText prefers accName whenever it's non-empty. Clean
        // finalText too, once, right here, so whichever source actually
        // won still ends up card-cleaned.
        if (_cardAnchor) {
            finalText = _cleanCardLabelText(finalText);
        }
        // true for an element inside an open shadow root OR a same-
        // origin iframe (its ownerDocument differs from the top-level
        // document either way) - both are cases where a DOCUMENT-WIDE
        // xpath (evaluated from the top document) can't be trusted the
        // normal way (see xPath()'s own xpathIsUnique for exactly why),
        // even though css_path/id usually still resolve fine on replay
        // (Playwright's own CSS locator pierces shadow DOM natively;
        // generator/script_generator.py's _find_in_iframes() already
        // covers same-origin iframes as a fallback). Surfaced here
        // rather than silently pretending the xpath was actually
        // verified, so the Recording Editor can warn the user to prefer
        // the id/CSS selector for a pick like this.
        var crossBoundary = false;
        try {
            crossBoundary = (el.getRootNode() instanceof ShadowRoot) || (el.ownerDocument !== document);
        } catch (e) {}
        return {
            id: el.id ? '#' + el.id : null,
            name: el.getAttribute ? (el.getAttribute('name') || null) : null,
            role: el.getAttribute ? (el.getAttribute('role') || null) : null,
            aria_label: el.getAttribute ? (el.getAttribute('aria-label') || null) : null,
            accessible_name: accName,
            placeholder: el.getAttribute ? (el.getAttribute('placeholder') || null) : null,
            title: el.getAttribute ? (el.getAttribute('title') || null) : null,
            href: _cardHref,
            // BUG 2: numeric product id parsed out of the card's own
            // href (e.g. ".../buy/45954123" -> "45954123") - a stable
            // locator signal independent of the card's on-screen text,
            // which can legitimately change between recording and
            // replay (price, badges, stock). null whenever href itself
            // has no href or no numeric id segment.
            product_id: _cardProductId,
            css_path: cssPath(el),
            xpath: xPath(el, finalText, valueToExclude),
            text: finalText,
            element_text: elementText || accName,
            tag: el.tagName.toLowerCase(),
            attributes: attrs,
            cross_boundary: crossBoundary,
            // optional, additive - a readable last-resort name hint for
            // an icon-only element with no usable text (see
            // _strip_icon_font_text/_icon_class_hint on the Python side):
            // a class like "fa-user"/"icon-search"/"material-icons"
            // names WHAT the icon actually is, unlike the private-use
            // glyph its rendered text reads as. Checked on el itself
            // first, then its immediate parent (an icon is very
            // commonly one layer of <i>/<span> below the actual
            // clickable control) - never any deeper, to stay a cheap,
            // best-effort hint rather than another ancestor walk.
            icon_class_hint: iconClassHint(el) || (el.parentElement ? iconClassHint(el.parentElement) : null)
        };
    }

    // scans a className string for a recognizable icon-font class
    // naming convention - fa-<name>/fas fa-<name> (FontAwesome), icon-
    // <name>, glyphicon-<name> (Bootstrap 3), material-icons - generic
    // conventions, never any one site's specific class. Returns the
    // first match found, or null.
    var ICON_CLASS_PATTERNS = [
        /\bfa-[\w-]+\b/,
        /\bicon-[\w-]+\b/,
        /\bglyphicon-[\w-]+\b/,
        /\bmaterial-icons\w*\b/,
    ];
    function iconClassHint(el) {
        try {
            var cls = el && el.className ? String(el.className) : '';
            if (!cls) return null;
            for (var i = 0; i < ICON_CLASS_PATTERNS.length; i++) {
                var m = ICON_CLASS_PATTERNS[i].exec(cls);
                if (m) return m[0];
            }
        } catch (e) {}
        return null;
    }

    function buildProfile(rawEl, actionType, value) {
        // PRE-CLICK SNAPSHOT reuse (see its own comment above, next to
        // the mousedown listener that builds it) - only ever applies to
        // a real 'click' whose mousedown was captured on this EXACT raw
        // element; anything else (fill/select/no snapshot/a different
        // element) falls straight through to the original, unchanged
        // logic below.
        var _snap = (actionType === 'click' && _preClickSnapshot && _preClickSnapshot.rawTarget === rawEl)
            ? _preClickSnapshot : null;

        var checkboxTarget = _snap ? _snap.checkboxTarget : ((actionType === 'click') ? findCheckboxTarget(rawEl) : null);
        // FIX D debug field: whichever findCheckboxTarget call actually
        // produced checkboxTarget above - the snapshot's own value when
        // reused, or the fresh call's lastCheckboxClassifiedBy otherwise.
        // null whenever checkboxTarget itself is null (a plain click).
        var checkboxClassifiedBy = _snap ? _snap.checkboxClassifiedBy : lastCheckboxClassifiedBy;
        var effectiveActionType = checkboxTarget ? 'check' : actionType;

        // locator-only refinement (see resolveCheckboxLocatorElement) -
        // checkboxTarget itself, from the untouched detection logic
        // above, still fully drives role/accessible_name/expected_state
        // below; this only decides which element's id/css_path/xpath/
        // tag get recorded
        var checkboxLocatorTarget = checkboxTarget ? resolveCheckboxLocatorElement(checkboxTarget) : null;

        // RC1 (hidden native input as target - CONFIRMED REAL BUG via a
        // live Myntra recording: a filter radio's own recorded label was
        // "price_asc", its raw value attribute, not the visible "Price:
        // Low to High" text a person actually saw and clicked; replay
        // then requires that native <input> itself to be visible, which
        // it structurally never is - a real custom checkbox/radio/sort
        // option is near-universally a hidden <input> plus a visible
        // label/indicator). `el` used to be the underlying input itself
        // for a "check"-classified action (checkboxLocatorTarget,
        // deliberately preferred for its LOCATOR stability), which is
        // exactly backwards for what replay needs to actually CLICK -
        // act_target is now always the VISIBLE thing the user's pointer
        // was actually on (resolveSemanticTarget's own ancestor walk,
        // unchanged, run unconditionally now instead of only for a
        // plain, non-checkbox click); state_target - separate, new -
        // carries the underlying input's own locator + current state,
        // used for postcondition verification and as the PROXY source
        // if act_target ever fails to resolve live (see resolve_and_act
        // on the replay side). Both are the SAME element whenever the
        // user directly clicked the native input itself (act_target and
        // state_target simply end up pointing at the same thing) - nothing
        // changes for that already-fine case.
        var actTargetEl = resolveSemanticActTarget(rawEl);
        var stateTargetEl = checkboxLocatorTarget;
        var el = actTargetEl;

        const rect = el.getBoundingClientRect();
        // some real, visually-clickable elements measure as ZERO-size here
        // (an icon-wrapper div with no explicit width/height, absolutely-
        // positioned inner content that collapses its parent, a target
        // rendered entirely via a ::before/::after pseudo-element) - tagged
        // now, at record time, purely as informational metadata for replay
        // (which still re-checks the LIVE bounding box itself and works
        // correctly even without this tag; this just avoids re-discovering
        // the same fact the slow way on every replay run)
        const clickStrategy = (rect.width === 0 || rect.height === 0) ? 'force_click' : 'standard';
        var accName = checkboxTarget ? getCheckboxAccessibleName(checkboxTarget, rawEl) : accessibleName(el);
        try {
            if (!checkboxTarget && !isInteractive(el) && afqaIsContainerLike(el)) {
                accName = (_stripIconFontText(el.getAttribute('aria-label') || '') || _stripIconFontText(el.getAttribute('title') || '') ||
                    _stripIconFontText(el.getAttribute('alt') || '')).slice(0, AFQA_OWN_LABEL_MAX_CHARS);
            }
        } catch (eAccWrapper) {}
        // R2: a fill action's own just-typed value must never become its
        // own locator's anchor text (see buildLocatorProfile's/xPath's
        // own comments) - only ever passed for 'fill', never for
        // click/check/select/etc, which have no typed value at all.
        const valueToExclude = (effectiveActionType === 'fill' && typeof value === 'string') ? value : null;
        const locatorProfile = (_snap && _snap.semanticEl === el)
            ? _snap.locatorProfile
            : buildLocatorProfile(el, accName, valueToExclude);
        // checkbox-specific role default - an implicit checkbox (a styled
        // <div>/<span> with no real role attribute) still needs role=
        // 'checkbox' recorded so replay's own check-vs-click handling
        // recognizes it; a real role attribute (handled generically inside
        // buildLocatorProfile above) always wins over this default.
        //
        // BUG FOUND against a real Myntra recording (session_
        // 20260925_103118.json step 10): a native <input type="radio">
        // has NO explicit role="..." HTML attribute (radio is an IMPLICIT
        // ARIA role derived from tag+type, not a literal attribute), so
        // buildLocatorProfile's generic `el.getAttribute('role')` read
        // above always comes back null for it - which used to fall
        // through to this same unconditional 'checkbox' default even
        // though the live element is genuinely a radio. That wrong role
        // then fed replay's is-this-a-radio-group verification logic,
        // which never even considered treating it as one. Fixed: derive
        // the default from the element's own native type when it IS the
        // input (radio -> 'radio', checkbox -> 'checkbox'), keeping the
        // old blanket 'checkbox' default only for a genuinely non-native
        // target (a styled <div>/<span> with no type attribute at all).
        if (!locatorProfile.role && checkboxTarget) {
            locatorProfile.role = _nativeCheckboxRoleDefault(el) || 'checkbox';
        }

        // RC1: state_target - the underlying input's OWN locator profile
        // + its current checked state, separate from act_target/
        // locator_profile above (which is always the VISIBLE thing
        // actually clicked). Only ever built when checkboxTarget
        // resolved to something at all; null on a plain click. Reuses
        // the same buildLocatorProfile() + getCheckboxAccessibleName()
        // already used for the checkbox-classified case above, just
        // anchored on stateTargetEl specifically rather than el.
        var stateTargetProfile = null;
        if (stateTargetEl) {
            stateTargetProfile = (stateTargetEl === el)
                ? locatorProfile
                : buildLocatorProfile(stateTargetEl, getCheckboxAccessibleName(checkboxTarget, rawEl), null);
            if (!stateTargetProfile.role) {
                // same fix as locatorProfile's own default above -
                // state_target IS the underlying input itself, so its
                // native type (when present) is always the right source
                // of truth, never a blanket 'checkbox' guess.
                stateTargetProfile.role = _nativeCheckboxRoleDefault(stateTargetEl) || 'checkbox';
            }
        }

        var payload = {
            action_type: effectiveActionType,
            value: value || null,
            locator_profile: locatorProfile,
            act_target: locatorProfile,
            state_target: stateTargetProfile ? {
                locator_profile: stateTargetProfile,
                checked: checkboxTarget ? _predictedCheckedState(checkboxTarget, rawEl) : null,
            } : null,
            bounding_box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
            // BUG 3 (scroll leak across steps): bounding_box's x/y are
            // VIEWPORT-relative (getBoundingClientRect()) - meaningless
            // as a raw-coordinate replay fallback unless the page is
            // scrolled back to (roughly) this same position first. Every
            // action now carries the window scroll position it was
            // actually captured at, not just dedicated "scroll" actions,
            // so that fallback can restore it before trusting the
            // recorded coordinate.
            scroll_x: window.scrollX,
            scroll_y: window.scrollY,
            click_strategy: clickStrategy,
            page_url: window.location.href,
            timestamp: new Date().toISOString(),
            dom_context: buildDomContext(el, stateTargetEl),
        };

        if (effectiveActionType === 'check') {
            payload.expected_state = checkboxTarget
                ? _predictedCheckedState(checkboxTarget, rawEl)
                : isCheckboxCheckedState(el);
            // FIX D debug field: which findCheckboxTarget branch actually
            // classified this as a checkbox/radio - only meaningful (and
            // only ever set) for a "check" action; a plain click never
            // gets this field at all.
            payload.classified_by = checkboxClassifiedBy;
            // FIX 1.4 (postcondition) - same value as expected_state
            // above, just under the shared "expect" field's own
            // {type, ...} shape so replay's postcondition verification
            // (see resolve_and_act's "check" dispatch) can check for it
            // generically alongside a hover's own "reveal" expect,
            // without needing a per-action-type special case for this
            // one. expected_state itself is untouched, still read
            // directly by every existing consumer exactly as before.
            payload.expect = { type: 'toggle', final_checked: payload.expected_state };
        }

        // FIX 2 (locator stability, additive only): ~300ms after this
        // profile is captured, count how many live elements its primary
        // locators actually match right now - never inline/synchronous
        // with the click itself, so this never adds latency to the
        // capture path real-time recording depends on. See
        // _scheduleLocatorStabilityCheck's own docstring for what gets
        // reported back and how.
        _scheduleLocatorStabilityCheck(payload.timestamp, locatorProfile);

        // RESULT-BASED CHECKS (replay): was this step performed INSIDE a real modal? Only then does
        // replay require its target to be inside an active modal.
        try { payload.in_modal = _isInStrictModal(rawEl); } catch (eModal) {}
        try {
            var _sp = _sitePopupOf(rawEl);
            if (_sp) {
                payload.site_popup = _sp;
                if (!payload.popup_container) { var _spFp = _popupFingerprintOf(rawEl); if (_spFp) payload.popup_container = _spFp; }
            }
        } catch (eSitePopup) {}
        // a link / card's own name when it has no text of its own: the heading, image alt or title inside it
        try {
            if (payload.locator_profile && !payload.locator_profile.inner_label) {
                payload.locator_profile.inner_label = _innerLabel(rawEl);
            }
        } catch (eInner) {}
        // the item the control belongs to (the card / list item / row it repeats in): tells identical controls
        // ("Add to cart" in every card) apart on replay
        try {
            if (payload.locator_profile && !payload.locator_profile.item_context) {
                var _ictx = afqaItemContext(rawEl);
                if (_ictx) payload.locator_profile.item_context = _ictx;
            }
        } catch (eItemCtx) {}
        // a control with no name of its own (an icon drawn by an icon font): the short label next to it, so the
        // step can be called "icon button next to 'Free'" (naming only - never used to find the element)
        try {
            var _plp = payload.locator_profile;
            if (_plp && !_plp.nearby_label && !(_plp.text || _plp.aria_label || _plp.title || _plp.inner_label || _plp.accessible_name)) {
                var _nb = afqaNearbyLabel(rawEl);
                if (_nb) _plp.nearby_label = _nb;
            }
        } catch (eNearby) {}
        try {
            if (payload.locator_profile && !payload.locator_profile.near_text) {
                payload.locator_profile.near_text = _nearText(rawEl);
            }
        } catch (eNear) {}
        // an icon-only element: what tells it apart from the icon buttons next to it
        try {
            if (payload.locator_profile && payload.locator_profile.icon_signature === undefined) {
                var iconFp = afqaIconFingerprint(rawEl.closest ? (rawEl.closest('button, a, [role=button], input') || rawEl) : rawEl);
                if (iconFp) {
                    payload.locator_profile.icon_signature = iconFp.icon_signature;
                    payload.locator_profile.sibling_index = iconFp.sibling_index;
                    payload.locator_profile.sibling_total = iconFp.sibling_total;
                    payload.locator_profile.icon_container = { tag: iconFp.container_tag, class: iconFp.container_class };
                }
            }
        } catch (eIconFpSet) {}
        // what the element IS or CONTAINS, for a readable step name when it has no text of its own
        try {
            if (payload.locator_profile && !payload.locator_profile.content_hint) {
                payload.locator_profile.content_hint = _contentHint(rawEl);
            }
        } catch (eHint2) {}
        return payload;
    }

    // debug/test-only hook (RECORDER_DEBUG gated - see its own definition
    // above; never set on a real recording session) so an automated test
    // can call the exact same buildProfile() the real click listener
    // uses, instead of re-implementing its logic against a live page.
    if (RECORDER_DEBUG) {
        window.__RECORDER_DEBUG_BUILD_PROFILE__ = buildProfile;
    }

    // recording-time consistency check: after each captured action, a
    // lightweight scan of short, purely-numeric LEAF-element text (the
    // generic SHAPE of a counter/badge - a cart count, a notification
    // count - never any specific site's class name, id, or wording) is
    // kept as a snapshot. If a NEW click arrives and that snapshot would
    // now read higher than it did right after the last thing actually
    // captured, something on the page changed a counter with no
    // corresponding action recorded in between - exactly the signature
    // of a missed click. Purely diagnostic: this never changes what gets
    // captured, skipped, or how - it only prints a warning for whoever
    // is recording to notice and re-check.
    var MAX_BADGE_TEXT_LEN = 4;
    var MAX_BADGE_SCAN_ELEMENTS = 500;

    function scanNumericBadges() {
        var result = {};
        try {
            var candidates = document.querySelectorAll('span, sup, small, b, strong, a, button, i, div');
            var scanned = 0;
            for (var i = 0; i < candidates.length && scanned < MAX_BADGE_SCAN_ELEMENTS; i++) {
                var el = candidates[i];
                // leaf elements only (no element children) - a cheap
                // check that skips large container nodes and keeps this
                // scan fast even on a page with thousands of elements
                if (el.children && el.children.length > 0) continue;
                scanned++;
                var txt = (el.textContent || '').trim();
                if (txt && txt.length <= MAX_BADGE_TEXT_LEN && /^\d+$/.test(txt)) {
                    var key = cssPath(el);
                    if (key) result[key] = parseInt(txt, 10);
                }
            }
        } catch (e) {
            // best-effort only - never lets a scan failure affect real capture
        }
        return result;
    }

    var lastBadgeSnapshot = null;
    var actionsSinceLastBadgeSnapshot = 0;

    function checkForMissedClick() {
        if (!lastBadgeSnapshot) return;
        actionsSinceLastBadgeSnapshot++;
        var current = scanNumericBadges();
        for (var key in current) {
            if (
                Object.prototype.hasOwnProperty.call(lastBadgeSnapshot, key) &&
                current[key] > lastBadgeSnapshot[key]
            ) {
                send({
                    action_type: '__consistency_warning__',
                    value: null,
                    locator_profile: null,
                    bounding_box: null,
                    page_url: window.location.href,
                    timestamp: new Date().toISOString(),
                    message: (
                        'a counter/badge value changed (' + lastBadgeSnapshot[key] +
                        ' -> ' + current[key] + ') but no corresponding click was ' +
                        'captured in the last ' + actionsSinceLastBadgeSnapshot +
                        ' action(s) - a click may have been missed'
                    )
                });
                break; // one warning per check is enough - avoid spamming
            }
        }
    }

    // FIX 1 (recorder attaches too late): the recordAction binding is now
    // registered at the context level BEFORE page.goto() ever runs (see
    // record_session.py's install_context_capture), so in practice it is
    // already callable the instant this script's very first line runs -
    // this queue is defensive insurance for the remaining sliver of a
    // race (a binding call still in flight on the Playwright/CDP side)
    // rather than the primary fix. An event that fires while
    // window.recordAction genuinely isn't callable yet is queued, in
    // order, instead of being silently dropped - flushed the moment the
    // binding becomes available, and only ever drained oldest-first so
    // nothing is ever sent out of order or twice.
    var __afqaPendingQueue = [];
    var __afqaFlushTimer = null;
    // bounds the queue against a binding that never recovers (page stuck
    // in some broken state) - each queued entry is already the fully
    // serialized JSON payload, so its own "timestamp" field (set at the
    // moment send() was first called for it) never changes regardless of
    // how long it sits queued or when it's eventually flushed
    var __AFQA_QUEUE_CAP = 50;

    function __afqaEnqueue(serialized) {
        if (__afqaPendingQueue.length >= __AFQA_QUEUE_CAP) {
            // drop the OLDEST once genuinely full, never the newest - a
            // queue this deep means the binding has been unavailable for
            // a long time already; keeping the most recent activity is
            // more useful than an ever-growing backlog no one can act on
            __afqaPendingQueue.shift();
        }
        __afqaPendingQueue.push(serialized);
        if (!__afqaFlushTimer) {
            __afqaFlushTimer = setInterval(__afqaTryFlushQueue, 50);
        }
    }

    function __afqaTryFlushQueue() {
        if (!__afqaPendingQueue.length) {
            if (__afqaFlushTimer) { clearInterval(__afqaFlushTimer); __afqaFlushTimer = null; }
            return;
        }
        if (typeof window.recordAction !== 'function') return;
        var pending = __afqaPendingQueue;
        __afqaPendingQueue = [];
        for (var i = 0; i < pending.length; i++) {
            try {
                window.recordAction(pending[i]);
            } catch (err) {
                // binding disappeared again mid-flush (page unloading) - put
                // whatever's left back, oldest-first, and stop for now
                __afqaPendingQueue = pending.slice(i).concat(__afqaPendingQueue);
                break;
            }
        }
        if (!__afqaPendingQueue.length && __afqaFlushTimer) {
            clearInterval(__afqaFlushTimer);
            __afqaFlushTimer = null;
        }
    }

    // FIX 2 (locator stability, additive only): a locator that looks
    // unique at capture time can still turn out to match several
    // elements on the live page (a list of otherwise-identical rows, a
    // css_path that happens to also match a hidden duplicate elsewhere) -
    // this doesn't change what gets recorded as the action's own
    // locator_profile at all, it only ever ADDS a match_count/
    // disambiguation report replay can use as an EXTRA scoring signal
    // (see _score_candidates_and_pick's own use of it) alongside its
    // existing tiers, never a replacement for any of them.
    var LOCATOR_STABILITY_CHECK_DELAY_MS = 300;
    // NOTE on ordering: css_path/xpath are POSITIONAL (nth-of-type-based -
    // see buildLocatorProfile's own xPath()/cssPath() builders), so they
    // are essentially always unique AT CAPTURE TIME by construction, even
    // for one of several visually-identical elements - the count that
    // actually matters for "is this locator inherently ambiguous"
    // purposes is text+tag (content-based, the same signal
    // _score_candidates_and_pick's own recorded-text check and the real
    // resolve_and_act tier chain both use), checked BEFORE css_path/xpath
    // to match the real tier priority order.
    var LOCATOR_MATCH_PRIORITY = ['data-testid', 'data-test', 'data-cy', 'id', 'name', 'aria_label', 'text+tag', 'css_path', 'xpath'];

    function _countLocatorMatches(lp) {
        var counts = {};
        var attrs = lp.attributes || {};
        try {
            if (lp.id) counts.id = document.querySelectorAll(lp.id).length;
        } catch (e) {}
        ['data-testid', 'data-test', 'data-cy'].forEach(function (attr) {
            var val = attrs[attr];
            if (!val) return;
            try {
                counts[attr] = document.querySelectorAll('[' + attr + '="' + CSS.escape(val) + '"]').length;
            } catch (e) {}
        });
        try {
            if (lp.name) counts.name = document.getElementsByName(lp.name).length;
        } catch (e) {}
        try {
            if (lp.aria_label) counts.aria_label = document.querySelectorAll('[aria-label="' + CSS.escape(lp.aria_label) + '"]').length;
        } catch (e) {}
        try {
            var text = (lp.text || lp.element_text || '').trim();
            var tag = (lp.tag || '').toUpperCase();
            if (text && tag) {
                var sameTag = document.getElementsByTagName(tag);
                var textCount = 0;
                for (var t = 0; t < sameTag.length; t++) {
                    if ((sameTag[t].textContent || '').trim() === text) textCount++;
                }
                counts['text+tag'] = textCount;
            }
        } catch (e) {}
        try {
            if (lp.css_path) counts.css_path = document.querySelectorAll(lp.css_path).length;
        } catch (e) {}
        try {
            if (lp.xpath) {
                var xr = document.evaluate(lp.xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                counts.xpath = xr.snapshotLength;
            }
        } catch (e) {}
        return counts;
    }

    function _bestLocatorTier(counts) {
        for (var i = 0; i < LOCATOR_MATCH_PRIORITY.length; i++) {
            if (LOCATOR_MATCH_PRIORITY[i] in counts) return LOCATOR_MATCH_PRIORITY[i];
        }
        return null;
    }

    function _resolveForStabilityCheck(lp) {
        // best-effort representative element for the disambiguation
        // context below - same priority as the count above; when several
        // elements match, the first one found stands in for "the element
        // this action targeted" (good enough for a rough, additive
        // scoring signal - not meant to be exact)
        try {
            if (lp.id) {
                var byId = document.querySelector(lp.id);
                if (byId) return byId;
            }
        } catch (e) {}
        try {
            if (lp.css_path) {
                var byCss = document.querySelector(lp.css_path);
                if (byCss) return byCss;
            }
        } catch (e) {}
        try {
            if (lp.xpath) {
                var xr = document.evaluate(lp.xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                if (xr.singleNodeValue) return xr.singleNodeValue;
            }
        } catch (e) {}
        return null;
    }

    function _buildDisambiguationContext(el) {
        // container path: up to 3 ancestor levels, tag + id/class summary
        // - cheap, generic "where in the page structure is this" hint
        var containerPath = [];
        var node = el.parentElement;
        for (var i = 0; i < 3 && node; i++) {
            var desc = (node.tagName || '').toLowerCase();
            if (node.id) {
                desc += '#' + node.id;
            } else if (node.className && typeof node.className === 'string' && node.className.trim()) {
                desc += '.' + node.className.trim().split(/\s+/).join('.');
            }
            containerPath.push(desc);
            node = node.parentElement;
        }

        // same-text sibling index: this element's position among every
        // same-tag element (scoped to its own grandparent - one level
        // above its immediate wrapper, which for a typical item/row/list
        // structure lands on the shared list container everything else
        // being compared actually sits in; falls back to the whole
        // document when there's no grandparent at all) whose own trimmed
        // text content matches exactly - a purely structural/content
        // signal, never a site-specific selector
        var sameTextIndex = null, sameTextTotal = null;
        try {
            var scope = (el.parentElement && el.parentElement.parentElement) || document;
            var ownText = (el.textContent || '').trim();
            var candidates = Array.prototype.filter.call(
                scope.getElementsByTagName(el.tagName),
                function (c) { return (c.textContent || '').trim() === ownText; }
            );
            sameTextTotal = candidates.length;
            sameTextIndex = candidates.indexOf(el);
        } catch (e) {}

        // relative position: this element's own live bounding box, for
        // replay to compare against each candidate's box as a proximity
        // tiebreaker - the same kind of signal _score_candidates_and_pick
        // already uses via its own recorded_box, just sourced from here
        var boundingBox = null;
        try {
            var r = el.getBoundingClientRect();
            boundingBox = { x: r.x, y: r.y, width: r.width, height: r.height };
        } catch (e) {}

        return {
            container_path: containerPath,
            same_text_sibling_index: sameTextIndex,
            same_text_sibling_total: sameTextTotal,
            bounding_box: boundingBox,
        };
    }

    function _scheduleLocatorStabilityCheck(actionTimestamp, lp) {
        if (!lp || !actionTimestamp) return;
        setTimeout(function () {
            try {
                var counts = _countLocatorMatches(lp);
                var bestTier = _bestLocatorTier(counts);
                var patchPayload = {
                    action_type: '__locator_stability__',
                    target_timestamp: actionTimestamp,
                    match_count: counts,
                };
                if (bestTier && counts[bestTier] > 1) {
                    var el = _resolveForStabilityCheck(lp);
                    if (el) patchPayload.disambiguation = _buildDisambiguationContext(el);
                }
                send(patchPayload);
            } catch (e) {}
        }, LOCATOR_STABILITY_CHECK_DELAY_MS);
    }

    // ---- post-click result (metadata of the click step, NOT a step) --------
    // What the page DID in response to a click, captured after it settles:
    // the URL path before/after, the identity of the element holding focus,
    // and which form fields changed value because of the click (identity
    // only, never the text). Replay captures the same things after its own
    // click and compares them - this is how "replay behaved like manual" is
    // decided, instead of comparing the clicked element's name with
    // whatever happens to be focused afterwards. Sent as a follow-up
    // message (like the locator-stability patch), never as an action.
    var POST_CLICK_QUIET_MS = 500;
    var POST_CLICK_MIN_MS = 600;
    var POST_CLICK_MAX_MS = 4000;
    var _POST_CLICK_ACTIONABLE = 'a[href], button, [role=button], [role=link], [role=menuitem], [role=tab], [role=checkbox], [role=radio], [role=option], [onclick], input, select, textarea, summary, label';

    function _accessibleNameParts(el) {
        var a = (el && el.closest) ? (el.closest(_POST_CLICK_ACTIONABLE) || el) : el;
        var parts = [];
        if (!a || !a.getAttribute) return parts;
        var t = (a.innerText || a.textContent || '').trim();
        if (t) parts.push(t.slice(0, 120));
        var al = a.getAttribute('aria-label'); if (al) parts.push(al.slice(0, 120));
        var lb = a.getAttribute('aria-labelledby');
        if (lb) {
            lb.split(' ').forEach(function (id) {
                if (!id) return;
                var n = document.getElementById(id);
                if (n && n.textContent) parts.push(n.textContent.trim().slice(0, 120));
            });
        }
        var imgs = a.querySelectorAll ? a.querySelectorAll('img[alt]') : [];
        for (var i = 0; i < imgs.length && i < 3; i++) { var alt = imgs[i].getAttribute('alt'); if (alt) parts.push(alt); }
        var ti = a.getAttribute('title'); if (ti) parts.push(ti.slice(0, 120));
        var ph = a.getAttribute('placeholder'); if (ph) parts.push(ph.slice(0, 120));
        if (a.labels && a.labels.length) { var lt = (a.labels[0].textContent || '').trim(); if (lt) parts.push(lt.slice(0, 120)); }
        return parts;
    }

    function _snapshotFieldValues() {
        var map = new Map();
        var fields = document.querySelectorAll('input, textarea, select');
        for (var i = 0; i < fields.length; i++) map.set(fields[i], fields[i].value);
        return map;
    }
    // the input type of every field right now: a click that only changes a field's TYPE (and so its value text)
    // did not change what the user entered
    function afqaSnapshotFieldTypes() {
        var tmap = new Map();
        try {
            var fs = document.querySelectorAll('input, textarea, select');
            for (var i = 0; i < fs.length; i++) tmap.set(fs[i], fs[i].type || '');
        } catch (e) {}
        return tmap;
    }

    // a field a person can see and edit: visible, laid out, not hidden / aria-hidden / disabled /
    // read-only, not inside a hidden container (hidden inputs and internal state fields are not)
    function _isUserEditableField(f) {
        try {
            var type = (f.getAttribute('type') || '').toLowerCase();
            if (f.tagName === 'INPUT' && ['hidden', 'button', 'submit', 'image', 'reset'].indexOf(type) !== -1) return false;
            if (f.disabled || f.readOnly) return false;
            var r = f.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0) return false;
            var n = f;
            while (n && n.nodeType === 1) {
                var cs = getComputedStyle(n);
                if (cs.display === 'none' || cs.visibility === 'hidden' || n.hasAttribute('hidden') || n.getAttribute('aria-hidden') === 'true') return false;
                n = n.parentElement;
            }
            return true;
        } catch (e) { return false; }
    }

    // the text of a field (input / textarea value, or the text of a contenteditable box)
    function _fieldText(f) {
        try {
            if (f.tagName === 'INPUT' || f.tagName === 'TEXTAREA') return f.value || '';
            return f.innerText || f.textContent || '';
        } catch (e) { return ''; }
    }
    // visible, editable text boxes of the page (inputs, textareas, contenteditable / role=textbox)
    function _visibleTextFields() {
        var out = [];
        try {
            var q = document.querySelectorAll('input, textarea, [contenteditable=""], [contenteditable="true"], [contenteditable="plaintext-only"], [role=textbox]');
            for (var i = 0; i < q.length && out.length < 8; i++) {
                var f = q[i];
                if (f.tagName === 'INPUT') {
                    var ty = (f.getAttribute('type') || 'text').toLowerCase();
                    if (['text', 'search', 'email', 'url', 'tel', 'number'].indexOf(ty) === -1) continue;
                }
                if (!_isUserEditableField(f)) continue;
                out.push(f);
            }
        } catch (e) {}
        return out;
    }
    // is this element a "send / submit" control: a submit button, or a button that submits its form
    function _isSubmitLike(el) {
        try {
            var b = el && el.closest ? el.closest('button, input[type=submit], input[type=image], [role=button]') : null;
            if (!b) return false;
            var ty = (b.getAttribute('type') || '').toLowerCase();
            if (ty === 'submit' || ty === 'image') return true;
            if (b.tagName === 'BUTTON' && !ty && b.closest('form')) return true;
        } catch (e) {}
        return false;
    }
    // Conversation observation is limited to editors with strong structure or explicit
    // message/prompt semantics. Plain form inputs can also produce result text containing
    // their value, which is not evidence that a chat reply started.
    function _isConversationEditor(el) {
        try {
            if (!el) return false;
            var tag = (el.tagName || '').toLowerCase();
            var role = (el.getAttribute('role') || '').toLowerCase();
            var hasCe = el.hasAttribute('contenteditable');
            var ce = (el.getAttribute('contenteditable') || '').toLowerCase();
            if (tag === 'textarea' || role === 'textbox' || (hasCe && (ce === '' || ce === 'true' || ce === 'plaintext-only'))) return true;
            if (tag !== 'input' || (el.getAttribute('type') || 'text').toLowerCase() !== 'text') return false;
            var semantic = ['name', 'aria-label', 'placeholder', 'title'].map(function (key) {
                return el.getAttribute(key) || '';
            }).join(' ');
            return /\b(message|prompt|chat|ask)\b/i.test(semantic);
        } catch (e) { return false; }
    }
    // before an Enter / click: which text boxes hold text, and a count of new text-bearing nodes
    // that appear afterwards outside them. result() says: was a box cleared (or replaced), did
    // new content appear.
    function _submitSnapshot() {
        var fields = _visibleTextFields().filter(function (f) { return _fieldText(f).trim().length > 0; });
        var added = 0, obs = null;
        try {
            obs = new MutationObserver(function (muts) {
                for (var m = 0; m < muts.length; m++) {
                    var rec = muts[m];
                    if (rec.type !== 'childList') continue;
                    for (var k = 0; k < rec.addedNodes.length; k++) {
                        var nd = rec.addedNodes[k], inField = false;
                        for (var fi = 0; fi < fields.length; fi++) {
                            if (fields[fi] === nd || (fields[fi].contains && fields[fi].contains(nd))) { inField = true; break; }
                        }
                        if (inField) continue;
                        if (((nd.textContent || '').replace(/\s+/g, ' ').trim()).length >= 2) added++;
                    }
                }
            });
            obs.observe(document.documentElement, { childList: true, subtree: true });
        } catch (e) {}
        return {
            n: fields.length,
            fields: fields,
            result: function () {
                try { if (obs) obs.disconnect(); } catch (e) {}
                var cleared = false;
                for (var i = 0; i < fields.length; i++) {
                    if (!document.contains(fields[i]) || _fieldText(fields[i]).trim().length === 0) { cleared = true; break; }
                }
                return { fields_before: fields.length, field_cleared: cleared, content_added: added > 0 };
            }
        };
    }

    // ---- the chatbot's reply, saved on the step that sent the prompt --------------------------------------
    // "Idle fingerprint" of an input's container: the input editable / enabled, plus the accessible name, icon and
    // disabled state of the buttons next to it (a send button that turned into a stop button while the page is
    // replying, and back). Generic: nothing but what is on the page.
    function afqaChatFp(input) {
        try {
            if (!input || !input.isConnected) return null;
            var c = input;
            for (var i = 0; i < 5 && c.parentElement; i++) {
                c = c.parentElement;
                if (c.querySelector('button, [role=button], input[type=submit]')) break;
            }
            var btns = Array.prototype.slice.call(c.querySelectorAll('button, [role=button], input[type=submit]'), 0, 12).map(function (b) {
                var g = b.querySelector('svg');
                return [((b.getAttribute('aria-label') || b.getAttribute('title') || (b.innerText || '').trim()) + '').slice(0, 30),
                        g ? (g.getAttribute('class') || '') : '',
                        (b.disabled || b.getAttribute('aria-disabled') === 'true') ? 1 : 0];
            });
            var ed = (!input.disabled && !input.readOnly && input.getAttribute('aria-disabled') !== 'true') ? 1 : 0;
            return JSON.stringify([ed, btns]);
        } catch (e) { return null; }
    }
    function afqaBodyLines() {
        try {
            return ((document.body.innerText || '') + '').split(String.fromCharCode(10)).map(function (s) { return s.trim(); }).filter(Boolean);
        } catch (e) { return []; }
    }
    function afqaNormLine(s) {
        return String(s || '').toLowerCase().split('').filter(function (ch) { return /[a-z0-9\s]/.test(ch) || ch.charCodeAt(0) > 127 && /\S/.test(ch) && !/[\u2000-\u2BFF\uD800-\uDFFF]/.test(ch); }).join('').replace(/\s+/g, ' ').trim();
    }
    var AFQA_REPLY_SETTLE_MS = 2000;       // the page text has been still this long
    var AFQA_REPLY_MAX_MS = 180000;        // longest wait for a reply
    var AFQA_REPLY_NO_ACTIVITY_MS = 3000;  // nothing happened after the send: not a chat, nothing to save
    var afqaReplyFinishers = [];           // the reply watches still running (finished when recording stops)
    var afqaReplySpans = [];               // { start, end|null } of every reply watched: when the reply was being written
    function afqaDuringReply(ts) {
        try {
            var ms = ts ? Date.parse(ts) : Date.now();
            if (isNaN(ms)) ms = Date.now();
            for (var i = 0; i < afqaReplySpans.length; i++) {
                var s = afqaReplySpans[i];
                if (ms > s.start && (s.end === null || ms <= s.end)) return true;
            }
        } catch (e) {}
        return false;
    }
    // After a send: wait until the reply is finished (page text still for the settle time AND the input's container
    // back in its idle state), then save the text that is NEW on the page - not the input, not the echoed prompt.
    function afqaStartReplyWatch(payload, inputEl, typed) {
        try {
            if (!payload || !payload.timestamp || !inputEl || !document.body) return;
            var seen = {};
            afqaBodyLines().forEach(function (l) { seen[l] = true; });
            var idleFp = inputEl.__afqaIdleFp || null;
            var t0 = Date.now(), lastMut = 0, mutated = false, fpChanged = false, done = false, timer = null;
            var obs = new MutationObserver(function (muts) {
                for (var i = 0; i < muts.length; i++) {
                    var tg = muts[i].target;
                    if (tg === inputEl || (inputEl.contains && inputEl.contains(tg))) continue;
                    mutated = true; lastMut = Date.now(); break;
                }
            });
            obs.observe(document.body, { childList: true, subtree: true, characterData: true });
            // the time span during which this reply is still being written: an action made inside it is
            // saved with during_reply = true (see send()). It ends when the reply is really over - an action
            // of the user's own (e.g. a click on a stop control) ends the SAVING of the text, not the reply.
            var span = { start: Date.now(), end: null };
            afqaReplySpans.push(span);
            var lastPressAt = 0;                 // the last real mouse press made while this reply was written
            function over() {
                if (span.end === null) span.end = Date.now();
                try {
                    // the reply went quiet right after that press (it stopped growing within the settle time plus a
                    // little): that press stopped the reply - recorded as the outcome of its click
                    if (lastPressAt && lastMut && lastMut - lastPressAt <= 1500 && lastMut >= lastPressAt - 500) {
                        send({ action_type: '__reply_stop__', at: new Date(lastPressAt).toISOString(), timestamp: new Date().toISOString() });
                    }
                } catch (eStopNote) {}
                try { document.removeEventListener('mousedown', onPress, true); } catch (eRm) {}
                finish();
                try { obs.disconnect(); } catch (e) {}
                if (timer) clearInterval(timer);
            }
            afqaReplyFinishers.push(function () { try { over(); } catch (e) {} });
            var EVS = ['mousedown', 'keydown'];
            var onUser = function (ev) { if (ev.isTrusted) finish(); };
            // every real mouse press while the reply is being written (kept until the reply is over)
            var onPress = function (ev) { try { if (ev.isTrusted && span.end === null) lastPressAt = Date.now(); } catch (ePress) {} };
            document.addEventListener('mousedown', onPress, true);
            EVS.forEach(function (n) { document.addEventListener(n, onUser, true); });
            function finish() {
                if (done) return;
                done = true;
                EVS.forEach(function (n) { document.removeEventListener(n, onUser, true); });
                try {
                    if (!mutated) return;
                    var typedN = afqaNormLine(typed);
                    var newLines = afqaBodyLines().filter(function (l) { return !seen[l]; });
                    var out = newLines.filter(function (l) { return afqaNormLine(l) !== typedN; });
                    var text = out.join(' ').slice(0, 6000);
                    // FACTS of what this send did (never a guess): did the typed text show up on the page as a new
                    // entry (a conversation message), and is the message box still there afterwards (a conversation
                    // goes on in the same box; a login / form step replaces it)
                    var echoed = false, kept = false;
                    try {
                        echoed = !!typedN && newLines.some(function (l) {
                            var n = afqaNormLine(l);
                            return n === typedN || (typedN.length >= 3 && n.indexOf(typedN) !== -1);
                        });
                    } catch (eEcho) {}
                    try {
                        var ir = inputEl.getBoundingClientRect();
                        kept = !!inputEl.isConnected && ir.width > 1 && ir.height > 1 && getComputedStyle(inputEl).visibility !== 'hidden';
                    } catch (eKept) {}
                    var msg = { action_type: '__reply__', target_timestamp: payload.timestamp, message_echoed: echoed, input_kept: kept, timestamp: new Date().toISOString() };
                    if (text) msg.reply_text = text;
                    send(msg);
                } catch (eReply) {}
            }
            timer = setInterval(function () {
                try {
                    var now = Date.now();
                    if (now - t0 > AFQA_REPLY_MAX_MS) { over(); return; }
                    if (!mutated) { if (now - t0 > AFQA_REPLY_NO_ACTIVITY_MS) over(); return; }
                    var fp = afqaChatFp(inputEl);
                    if (idleFp && fp && fp !== idleFp) fpChanged = true;
                    var quiet = (now - lastMut) >= AFQA_REPLY_SETTLE_MS;
                    if (quiet && (!fpChanged || !idleFp || fp === idleFp || (now - lastMut) >= 3 * AFQA_REPLY_SETTLE_MS)) over();
                } catch (ePoll) {}
            }, 250);
        } catch (eStartReply) {}
    }

    // after a click's result was read: a navigation the click starts LATER (until the user's next mouse press /
    // key press, at most 15s) updates that click's recorded page-after - also when the browser is closed right
    // after it starts (the destination is known from the moment it starts). Never raises.
    var afqaStopLateNavWatch = null;
    function afqaWatchLateNavigation(targetTs, urlBefore) {
        try {
            var stopAt = Date.now() + 15000, stopped = false, lastSent = null, timer = null;
            var EV = ['mousedown', 'keydown'];
            var navApi = !!(window.navigation && window.navigation.addEventListener);
            var report = function (href) {
                try {
                    var u = new URL(href, location.href);
                    var key = u.origin + u.pathname;
                    if (key === urlBefore || key === lastSent) return;
                    lastSent = key;
                    send({ action_type: '__post_click__', target_timestamp: targetTs,
                           post_click: { url_path_after: key, navigated: true, late_navigation: true },
                           timestamp: new Date().toISOString() });
                } catch (eRep) {}
            };
            var onNav = function (ev) {
                try {
                    // Back / Forward / Reload are the user's OWN next action (pressed in the browser itself, outside
                    // the page): never the click's result - and the click's watch ends there
                    var nt = ev && ev.navigationType;
                    if (nt === 'traverse' || nt === 'reload') { stop(); return; }
                    if (ev && ev.destination && ev.destination.url) report(ev.destination.url);
                } catch (eNav) {}
            };
            var onUser = function (ev) { if (ev.isTrusted) stop(); };
            var onPop = function () { stop(); };
            var stop = function () {
                if (stopped) return;
                stopped = true;
                EV.forEach(function (n) { document.removeEventListener(n, onUser, true); });
                try { if (navApi) window.navigation.removeEventListener('navigate', onNav); } catch (eRm) {}
                try { window.removeEventListener('popstate', onPop, true); } catch (eRmPop) {}
                if (afqaStopLateNavWatch === stop) afqaStopLateNavWatch = null;
                if (timer) clearInterval(timer);
            };
            // a new watch replaces an older one; any next recorded action of the user also ends it (see send())
            try { if (afqaStopLateNavWatch) afqaStopLateNavWatch(); } catch (ePrev) {}
            afqaStopLateNavWatch = stop;
            window.addEventListener('popstate', onPop, true);
            EV.forEach(function (n) { document.addEventListener(n, onUser, true); });
            if (navApi) window.navigation.addEventListener('navigate', onNav);
            timer = setInterval(function () {
                if (stopped) return;
                if (Date.now() > stopAt) { stop(); return; }
                report(location.href);
            }, 250);
        } catch (eWatch) {}
    }

    function _schedulePostClickObservation(payload, opts) {
        try {
            if (!payload || !payload.timestamp) return;
            var before = _snapshotFieldValues();
            var beforeTypes = afqaSnapshotFieldTypes();
            var _sub = _submitSnapshot();
            try {
                // a text field held text when this was done: if the page now replies, save the reply on this step
                var replyInput = (opts && opts.inputEl) || lastFocusedTextField;
                if (!replyInput && _sub.n > 0) {
                    // a mouse press on a send button moves the focus to that button BEFORE the click, so the
                    // focused text box is gone by now: use the box the user was last in when it still holds
                    // the text, else the only box on the page that holds text
                    var lastBox = afqaLastTextBox;
                    if (lastBox && _sub.fields.indexOf(lastBox) !== -1) replyInput = lastBox;
                    else if (_sub.fields.length === 1) replyInput = _sub.fields[0];
                }
                if (_sub.n > 0 && replyInput && _isConversationEditor(replyInput)) {
                    afqaStartReplyWatch(payload, replyInput, _fieldText(replyInput));
                }
            } catch (eReplyStart) {}
            var urlBefore = location.origin + location.pathname;
            var startedAt = Date.now();
            var lastMutation = Date.now();
            var observer = new MutationObserver(function () { lastMutation = Date.now(); });
            observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, characterData: true });
            var done = false;
            var NEXT_EVENTS = ['mousedown', 'keydown', 'wheel', 'touchstart'];
            var endedByUser = false;
            var onNextInteraction = function (ev) {
                // the user's NEXT interaction ends the observation: whatever
                // it changes belongs to that next step, not to this click
                if (!ev.isTrusted) return;
                endedByUser = true;
                finish();
            };
            NEXT_EVENTS.forEach(function (n) { document.addEventListener(n, onNextInteraction, true); });
            var finish = function () {
                if (done) return;
                done = true;
                NEXT_EVENTS.forEach(function (n) { document.removeEventListener(n, onNextInteraction, true); });
                try {
                    observer.disconnect();
                    var active = document.activeElement;
                    var focus = null;
                    if (active && active !== document.body && active !== document.documentElement) {
                        focus = {
                            parts: _accessibleNameParts(active),
                            role: active.getAttribute('role') || null,
                            tag: active.tagName.toLowerCase()
                        };
                    }
                    var changed = [];
                    var fields = document.querySelectorAll('input, textarea, select');
                    for (var i = 0; i < fields.length; i++) {
                        var f = fields[i];
                        if (before.has(f) && before.get(f) !== f.value && _isUserEditableField(f)
                            && !(beforeTypes.has(f) && beforeTypes.get(f) !== (f.type || ''))) {
                            changed.push({ parts: _accessibleNameParts(f), tag: f.tagName.toLowerCase(), type: (f.getAttribute('type') || '').toLowerCase() || null });
                        }
                    }
                    send({
                        action_type: '__post_click__',
                        target_timestamp: payload.timestamp,
                        post_click: {
                            url_path_before: urlBefore,
                            url_path_after: location.origin + location.pathname,
                            focus: focus,
                            fields_changed: changed,
                            dialog_open: _isStrictDialogOpen(),
                            submit: (function () {
                                var r = _sub.result();
                                r.submit_like = !!(opts && opts.submitLike);
                                return r;
                            })(),
                            // this recording watches for a navigation the click starts later (see below)
                            nav_watch: true
                        },
                        timestamp: new Date().toISOString()
                    });
                    // a navigation the click starts only later (after a server check, say) still belongs to it
                    if (!endedByUser) afqaWatchLateNavigation(payload.timestamp, urlBefore);
                } catch (eFinish) {}
            };
            (function poll() {
                var now = Date.now();
                if (done) return;
                if ((now - lastMutation >= POST_CLICK_QUIET_MS && now - startedAt >= POST_CLICK_MIN_MS) ||
                    now - startedAt >= POST_CLICK_MAX_MS) {
                    finish();
                    return;
                }
                setTimeout(poll, 100);
            })();
        } catch (ePostClick) {}
    }

    function send(payload) {
        // an action made INSIDE an iframe says which <iframe> it is (the page side can read that for a
        // same-origin frame); the Python side must not ask Playwright from inside its binding callback
        // (that call can never return there and froze the recording)
        try {
            if (window.top !== window && payload && payload.action_type && payload.action_type.indexOf('__') !== 0) {
                var _fe = null;
                try { _fe = window.frameElement; } catch (eFe) {}
                payload.frame_hint = _fe
                    ? { src: _fe.getAttribute('src'), name: _fe.getAttribute('name') || _fe.getAttribute('id') || null, title: _fe.getAttribute('title') || null }
                    : { src: null, name: window.name || null, title: null };
            }
        } catch (eHint) {}
        // a value typed into a text field but not yet committed (no Enter,
        // no blur yet) has to land in the recording BEFORE whatever other
        // action is being recorded now, so step order stays correct - see
        // flushTypedFieldIfPending below (fill itself, and the internal
        // "__..." messages, never trigger it)
        if (payload && typeof payload.action_type === 'string' && payload.action_type !== 'fill' &&
            payload.action_type.indexOf('__') !== 0) {
            flushTypedFieldIfPending('next-action:' + payload.action_type, payload.timestamp);
            try {
                // the focus session of the field the user was typing in (see afqaCommitFieldSession)
                if (payload.action_type !== 'select') afqaCommitFieldSession(lastFocusedTextField, 'next-action:' + payload.action_type, payload.timestamp);
            } catch (eSessionFlush) {}
        }
        try {
            // the user's next recorded action ends the previous click's watch for a late navigation: a navigation
            // after this point is never that click's result
            if (payload && typeof payload.action_type === 'string' && payload.action_type.indexOf('__') !== 0 &&
                payload.action_type !== 'scroll' && payload.action_type !== 'hover' && afqaStopLateNavWatch) {
                afqaStopLateNavWatch();
            }
        } catch (eStopWatch) {}
        try {
            if (payload && typeof payload.action_type === 'string' && payload.action_type.indexOf('__') !== 0 && payload.during_reply === undefined) {
                payload.during_reply = afqaDuringReply(payload.timestamp);
            }
        } catch (eDuring) {}
        var serialized = JSON.stringify(payload);
        if (__afqaPendingQueue.length > 0) {
            // older events are still waiting to flush - queue this one too
            // instead of letting it jump the line ahead of them (calling
            // recordAction directly here, even though it might well be
            // callable again by now, would send THIS one before whatever
            // is still queued, violating capture order), then try to
            // drain everything, oldest-first, in one pass
            __afqaEnqueue(serialized);
            __afqaTryFlushQueue();
        } else {
            try {
                window.recordAction(serialized);
            } catch (err) {
                // recordAction not bound yet - queue it instead of dropping it
                __afqaEnqueue(serialized);
            }
        }
        // keep the badge snapshot in sync with whatever was actually
        // just captured, for the NEXT click's consistency check above -
        // the two internal message types are excluded since they aren't
        // real user actions and shouldn't reset the "since last action" window
        if (
            payload && payload.action_type !== '__consistency_warning__' &&
            payload.action_type !== '__page_visible__' &&
            payload.action_type !== '__locator_stability__'
        ) {
            lastBadgeSnapshot = scanNumericBadges();
            actionsSinceLastBadgeSnapshot = 0;
        }
    }

    // click vs dblclick: a real double-click always fires click, click,
    // dblclick (in that order, same target). We can't tell a click is
    // "final" the instant it happens, so we hold it briefly - if a second
    // click on the same element follows fast, it's a double-click and the
    // dblclick handler below records it instead; otherwise the held click
    // gets sent once the window passes. This is the standard way to tell
    // the two apart without ever recording both.
    var DBLCLICK_WINDOW_MS = 300;
    var pendingClick = null; // { target, payload, timer }

    function flushPendingClick(supersededByTarget) {
        if (!pendingClick) return;
        clearTimeout(pendingClick.timer);
        var payload = pendingClick.payload;
        var flushedTarget = pendingClick.target;
        pendingClick = null;
        send(payload);
        debugLog(
            'FLUSHED buffered click on', debugDescribeTarget(flushedTarget),
            '-> recorded as', payload.action_type,
            (supersededByTarget
                ? ('(superseded by new interaction on ' + debugDescribeTarget(supersededByTarget) + ')')
                : '')
        );
    }

    // a click that triggers a real page navigation can outrun its own
    // DBLCLICK_WINDOW_MS timer: the JS context (and the pending timer
    // with it) is torn down the moment the page actually unloads, so a
    // click held for double-click detection at that instant is lost
    // silently - never sent, no error, nothing in the recording. Firing
    // is deliberately the SAME flushPendingClick() the normal window-
    // expiry path already uses, so a click flushed this way is already
    // cleared from pendingClick (never double-sent, whether or not its
    // original timer still fires - clearTimeout above already prevents
    // that anyway) and travels through the exact same send() call as
    // every other click, unchanged.
    window.addEventListener('beforeunload', function () { flushPendingClick(); }, true);

    // clicking anywhere inside a <label> (or a custom widget whose
    // semantic ancestor is a <label>) makes the browser dispatch a SECOND,
    // separate native click directly on the label's bound form control,
    // synchronously, a moment after the one on whatever was actually
    // clicked. Both now resolve to the same semantic target (label ->
    // control), so without this the same user click would get recorded
    // twice. Scoped tightly (very short window + only when the raw event
    // targets genuinely differ) so it can never suppress a real second
    // click, including a real double-click on the same element.
    var LABEL_CASCADE_DEDUP_MS = 50;
    var lastSemanticClickEl = null;
    var lastSemanticClickRawTarget = null;
    var lastSemanticClickTime = 0;

    // pressing Enter in a form field makes the browser fire a REAL,
    // separate 'click' event on the form's implicit submit button AND a
    // 'submit' event on the form itself (per the HTML forms spec) a few ms
    // later - neither is a second user action, both are the same submit
    // already captured as 'press Enter', so they need to be swallowed
    // rather than recorded as redundant extra steps.
    // suppressAutoSubmitForm scopes that swallow to the SPECIFIC form the
    // Enter press happened in (null when no enclosing <form> exists) - a
    // timestamp alone isn't enough at higher action volume: two forms can
    // legitimately be submitted back-to-back well inside the 700ms window
    // below, and without this, the second form's own genuine submit would
    // be silently swallowed just for arriving too soon after the first.
    // SUBMITTER: after resolving a click on an inner child (span / icon / svg) to its closest button / input, the
    // element is a submitter when it is <button type="submit">, a <button> without a type attribute inside a
    // form (or linked with form=""), or <input type="submit"|"image">. Its form is element.form.
    // Returns { el, form } or null. Never raises.
    function afqaResolveSubmitter(rawEl) {
        try {
            var b = rawEl && rawEl.closest ? rawEl.closest('button, input') : null;
            if (!b || !b.form) return null;
            var tg = b.tagName.toLowerCase();
            var ty = (b.getAttribute('type') || '').toLowerCase();
            if (tg === 'input') return (ty === 'submit' || ty === 'image') ? { el: b, form: b.form } : null;
            if (ty === 'submit' || (!b.hasAttribute('type'))) return { el: b, form: b.form };
        } catch (eSubmitter) {}
        return null;
    }
    // the click on a submitter that was just made (it may still be waiting in the double-click window, so it
    // is not recorded yet when the browser fires the form's submit event right after it)
    var afqaLastSubmitterClick = null;

    // the previous recorded click (the possible opener of a menu the next click is inside)
    var afqaPrevClick = null;
    // The trigger that opened the popup / menu the element is inside, as a locator profile: the element with
    // aria-expanded="true" whose aria-controls names the popup, else the previous click when it was not inside
    // that popup itself. null when the element is not inside such a popup. Never raises.
    function afqaOpenedByTrigger(targetEl) {
        try {
            var popup = targetEl && targetEl.closest ? targetEl.closest('[role=menu], [role=listbox], [role=dialog], [role=menuitem]') : null;
            var trig = null;
            var exp = document.querySelectorAll('[aria-expanded="true"][aria-controls]');
            for (var i = 0; i < exp.length; i++) {
                var ctl = document.getElementById(exp[i].getAttribute('aria-controls'));
                if (ctl && ctl.contains(targetEl)) { trig = exp[i]; popup = popup || ctl; break; }
            }
            if (!popup) return null;
            var profile = null;
            if (trig && !trig.contains(targetEl)) {
                profile = buildLocatorProfile(trig);
            } else if (afqaPrevClick && afqaPrevClick.profile && afqaPrevClick.el !== targetEl && (Date.now() - afqaPrevClick.time) < 60000
                       && !popup.contains(afqaPrevClick.el)) {
                profile = afqaPrevClick.profile;
            }
            if (!profile) return null;
            return { profile: profile, name: profile.accessible_name || profile.text || profile.title || null };
        } catch (eOpenedByTrig) { return null; }
    }

    var suppressAutoSubmitUntil = 0;
    var suppressAutoSubmitForm = null;

    function isSubmitTrigger(el) {
        if (!el || !el.tagName) return false;
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute('type') || (tag === 'button' ? 'submit' : '')).toLowerCase();
        return (tag === 'button' || tag === 'input') && type === 'submit';
    }

    // true only for the specific form (if any) the suppression window was
    // opened for - a null suppressAutoSubmitForm means no enclosing <form>
    // could be identified for that Enter press, so this falls back to the
    // original time-only check for that one edge case, same as before this
    // fix; any IDENTIFIED form only ever suppresses its own submit.
    function isSameSuppressedForm(formEl) {
        if (!suppressAutoSubmitForm) return true;
        return formEl === suppressAutoSubmitForm;
    }

    // PRE-CLICK SNAPSHOT (fixes a CONFIRMED REAL BUG, not hypothetical):
    // an async button (Sportzia's own "Send OTP"/"Continue"/"Pick from
    // your saved people") replaces its own label with a spinner glyph
    // (a private-use icon-font codepoint) for roughly a second the
    // instant it's pressed. The click listener below builds its
    // locator profile from e.target at 'click' time - one native event
    // LATER than 'mousedown' - and a real screen recording plus a live
    // comparison against session_20260921_081203 (where this same
    // button correctly recorded action_type=click, text='Send OTP')
    // confirmed that on a real (human-paced, not synthetic-fast) click,
    // the app's own re-render can land in that gap: the broken
    // recording (session_20260921_095629) captured text='' (the
    // spinner glyph) and role='checkbox' for the exact same button -
    // findCheckboxTarget()'s own ancestor/descendant search picking up
    // whatever transient structure the spinner state introduces nearby,
    // something a live scan of the STABLE (non-spinner) DOM around this
    // button confirmed has no checkbox-role anywhere in its ancestor
    // chain at all. Capturing at 'mousedown', in the CAPTURE phase, on
    // document - before the event even reaches the target, let alone
    // before any bubble-phase app handler can react to it - means this
    // always sees the same pre-interaction DOM a real user's eye saw
    // right before pressing, regardless of how fast or slow the app's
    // own reaction is. Only ever used as a fallback by buildProfile()
    // below when it matches the SAME raw element the click ends up
    // firing on; never changes anything for the (overwhelming majority)
    // of clicks where mousedown-time and click-time DOM happen to
    // already agree.
    var _preClickSnapshot = null;

    // BUG 1 (hover-revealed menu not recorded): a hover-then-click
    // sequence (hover "MEN" -> a mega-menu opens -> click "Casual
    // Shirts") produces no recordable event of its own for the hover -
    // only the eventual click on the now-visible menu item. Replaying
    // just that click against a page where the menu was never opened
    // finds the target attached-but-hidden and has no idea a hover
    // needs to happen first. Tracked here so the click handler below
    // can emit an explicit "hover" step immediately before such a click,
    // but ONLY when there's real, structural evidence the hover is what
    // revealed it - never for an ordinary click with no menu involved.
    // RC2 (wrong/noisy hover steps - CONFIRMED via a live Myntra
    // recording: several hover steps targeted an "incidental mouse
    // pass" - the header search box, a product card, an unrelated
    // paragraph - that had nothing to do with the click that followed).
    // A first attempt tightened this all the way to 800ms on the theory
    // that a real "hover to reveal, then click" gesture happens close
    // together - CONFIRMED REAL REGRESSION that caused, via this file's
    // own hover-menu fixture test: a real person hovering a menu open
    // and then taking a MOMENT to find and click the revealed item
    // (well over 800ms is completely normal human pacing) lost its
    // hover step entirely. 2500ms keeps a real margin over that normal
    // pacing while still being meaningfully tighter than the original
    // 4000ms; the STRUCTURAL fix that actually eliminates the "Brands"-
    // header-style incidental pass (see hoverEl.contains(clickTarget)
    // below) doesn't depend on timing at all, so this window only needs
    // to bound "how long is a real hover-then-click gesture allowed to
    // take", not carry the whole burden of rejecting unrelated hovers.
    var HOVER_PENDING_MAX_AGE_MS = 2500;
    // hoverChain replaces the old single pendingHover slot: an ordered
    // array of { el, baselineSet, time }, OUTERMOST trigger first - built
    // live as the mouse moves (see the mouseover listener below), so a
    // NESTED reveal (hovering "Filters" opens a chip row, then hovering
    // the "Patterns" chip inside that row opens ITS OWN checkbox panel)
    // is captured as a real, ordered chain instead of only ever
    // recording the last, deepest hover (which would just equal the
    // eventual click target - the "nothing to report" case).
    var hoverChain = [];

    function _isHoverCandidateVisible(el) {
        if (!el || !el.getBoundingClientRect) return false;
        var r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) return false;
        var cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none') return false;
        if (parseFloat(cs.opacity) === 0) return false;
        return true;
    }

    // snapshot of which "revealed-content-shaped" descendants are
    // visible right now, near `el` - purely structural (bounded ancestor
    // walk, generic tag/role/leaf-text selection), never a site-specific
    // selector. Walked from a bounded ancestor (not el itself) since a
    // mega-menu's own revealed panel is typically a SIBLING of the
    // trigger under one shared wrapper, not a descendant of the trigger.
    //
    // A real dropdown/filter-chip/sort-menu panel's own items are just
    // as often plain <li>/<span>/<div>-shaped (a filter chip, a sort
    // option, a checkbox's own <label>) as they are semantic <a>/
    // <button> - matching ONLY semantic interactive tags (the original,
    // narrower version of this function) undercounts real UI badly
    // enough that hovering straight through an entire reveal can measure
    // as "nothing changed." Two generic signals, neither tied to any
    // site's own naming: (1) semantically interactive by tag/role/
    // tabindex/onclick, or (2) a LEAF element (no element children) that
    // has its own non-empty text - covers a chip label, a menu item, a
    // checkbox's label, without ever matching a bare structural wrapper
    // <div>/<span> that merely contains other things.
    var _INTERACTIVE_TAG_RE = /^(A|BUTTON|INPUT|SELECT|TEXTAREA|LABEL|LI|OPTION)$/;
    function _isRevealCandidateShaped(node) {
        if (_INTERACTIVE_TAG_RE.test(node.tagName)) return true;
        if (node.hasAttribute('role') || node.hasAttribute('tabindex') || node.hasAttribute('onclick')) return true;
        // has its own DIRECT text (a text node child, not just text that
        // belongs to some nested child ELEMENT) - covers a chip/menu-item
        // label that ALSO wraps its own dropdown panel as a child
        // element (very common real markup - a chip's label and its
        // panel share one wrapper), not just genuine no-children leaves.
        var kids = node.childNodes;
        for (var i = 0; i < kids.length; i++) {
            if (kids[i].nodeType === 3 && kids[i].textContent.trim().length > 0) return true;
        }
        return false;
    }
    function _visibleCandidatesNear(el) {
        var container = el;
        var depth = 0;
        while (container && container.parentElement && depth < 3) {
            container = container.parentElement;
            depth++;
        }
        var visibleSet = new Set();
        if (container && container.querySelectorAll) {
            var candidates = container.querySelectorAll('*');
            for (var i = 0; i < candidates.length; i++) {
                var node = candidates[i];
                if (!_isRevealCandidateShaped(node)) continue;
                if (_isHoverCandidateVisible(node)) {
                    visibleSet.add(node);
                }
            }
        }
        return visibleSet;
    }

    // CONFIRMED (empirically, not just in theory): a browser resolves
    // :hover synchronously with the mouse actually entering an element -
    // by the time a 'mouseover' handler for that element runs and reads
    // layout/style, CSS ":hover .submenu { display: block }" has already
    // taken effect. Snapshotting visibility INSIDE the mouseover handler
    // itself therefore always captures the POST-reveal state, never
    // "what was visible before this hover" - the exact comparison this
    // whole mechanism needs. The fix: maintain a rolling AMBIENT snapshot
    // via 'mousemove' (which fires repeatedly as the pointer approaches a
    // trigger, strictly BEFORE the boundary crossing that flips :hover),
    // and use the most recent one - captured just prior to this hover -
    // as pendingHover's baseline instead of recomputing fresh.
    // two generations, not just the latest: browsers dispatch mousemove
    // and mouseover essentially back-to-back for the SAME crossing event
    // (moving into a new element fires mousemove for that position, then
    // mouseover) - if mousemove's own handler runs first and overwrites
    // _ambientVisible right before mouseover reads it, the "ambient"
    // value would already reflect THIS SAME transition's post-reveal
    // state, not a genuinely prior one. Using the PREVIOUS generation
    // (one tick further back, ~80ms+ earlier) as the actual baseline
    // keeps a real safety margin ahead of that same-event race.
    var _ambientVisible = { visibleSet: new Set(), time: 0 };
    var _ambientVisiblePrev = { visibleSet: new Set(), time: 0 };
    var _lastAmbientSampleAt = 0;
    document.addEventListener('mousemove', function (e) {
        var now = Date.now();
        if (now - _lastAmbientSampleAt < 80) return; // throttle to ~12/sec
        _lastAmbientSampleAt = now;
        try {
            var atPoint = document.elementFromPoint(e.clientX, e.clientY);
            if (atPoint) {
                _ambientVisiblePrev = _ambientVisible;
                _ambientVisible = { visibleSet: _visibleCandidatesNear(atPoint), time: now };
            }
        } catch (eAmbient) {}
    }, true);

    // FIX 1 (deterministic reveal detection): a hover is recorded only when
    // it made content APPEAR, and the answer must not depend on how fast or
    // slowly the pointer moved. A rolling ring of "what is hidden right now"
    // snapshots (taken on a timer, independent of the pointer) gives a true
    // PRE-hover state; ~100ms after each mouseover, whatever was in the
    // newest snapshot older than the mouseover and is visible now is what
    // that hover revealed. The hovered element is attributed to the real
    // trigger (see _resolveRevealTrigger) and kept with the revealed nodes,
    // so a later click is attributed to it only when the click target is
    // inside what it revealed.
    var _hiddenRing = [];
    // the most recent real click (element + time): a reveal that followed a click on the
    // very trigger the pointer entered is that click's effect, not a hover's
    var _recentClick = null;
    var _recentClicks = [];   // the last few real clicks (a later click must not hide an earlier one)
    function _triggerClickedAround(trig, t0) {
        for (var i = _recentClicks.length - 1; i >= 0; i--) {
            var c = _recentClicks[i];
            if (c.time >= t0 - 1500 && c.el && (trig === c.el || (trig.contains && trig.contains(c.el)))) return true;
        }
        return false;
    }
    var _pendingRevealChecks = [];
    var HIDDEN_RING_MAX = 14;
    var HIDDEN_SAMPLE_MS = 150;
    var HIDDEN_NODE_CAP = 3000;
    function _sampleHiddenNodes() {
        try {
            if (document.visibilityState === 'hidden') return;
            var nodes = document.querySelectorAll('a,button,li,summary,label,option,[role],[tabindex],aside,nav,ul,ol,section,div,span');
            if (nodes.length > 12000) return;
            var hidden = [];
            // a menu parked OFF screen (left:-9999px, a clip, a transform) is hidden too - it only
            // counts while the page has not scrolled since (scrolling brings ordinary content into view)
            var off = [];
            var vw0 = window.innerWidth, vh0 = window.innerHeight;
            for (var i = 0; i < nodes.length && hidden.length < HIDDEN_NODE_CAP; i++) {
                var n = nodes[i];
                if (n.offsetParent === null && n.getClientRects().length === 0) {
                    hidden.push(n);
                } else if (n.matches && n.matches('a,button,li,summary,[role]')) {
                    var cs = getComputedStyle(n);
                    if (cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) hidden.push(n);
                    else {
                        var br = n.getBoundingClientRect();
                        if (br.width > 0 && br.height > 0 && (br.right <= 0 || br.left >= vw0) && off.length < HIDDEN_NODE_CAP) off.push(n);
                    }
                }
            }
            _hiddenRing.push({ time: Date.now(), hidden: hidden, off: off, sx: window.scrollX, sy: window.scrollY });
            if (_hiddenRing.length > HIDDEN_RING_MAX) _hiddenRing.shift();
        } catch (eSample) {}
    }
    setInterval(_sampleHiddenNodes, HIDDEN_SAMPLE_MS);
    _sampleHiddenNodes();

    document.addEventListener('mouseover', function (e) {
        try {
            var target = e.target;
            var t0 = Date.now();
            var pre = null;
            for (var ri = _hiddenRing.length - 1; ri >= 0; ri--) {
                if (_hiddenRing[ri].time < t0 - 30) { pre = _hiddenRing[ri]; break; }
            }
            if (!pre) return;
            var _done = false;
            var _check = function () {
                if (_done) return;
                _done = true;
                try {
                    var revealed = [];
                    for (var k = 0; k < pre.hidden.length && revealed.length < 600; k++) {
                        var n = pre.hidden[k];
                        if (n.isConnected && _isHoverCandidateVisible(n)) revealed.push(n);
                    }
                    if (pre.off && pre.sx === window.scrollX && pre.sy === window.scrollY) {
                        var vw1 = window.innerWidth;
                        for (var k2 = 0; k2 < pre.off.length && revealed.length < 600; k2++) {
                            var n2 = pre.off[k2];
                            if (!n2.isConnected) continue;
                            var r2 = n2.getBoundingClientRect();
                            if (r2.width > 0 && r2.height > 0 && r2.right > 0 && r2.left < vw1) revealed.push(n2);
                        }
                    }
                    if (!revealed.length) return;
                    var trig = _resolveRevealTrigger(target, null);
                    if (!trig) return;
                    // the revealed content has to belong to this trigger:
                    // inside it, inside its wrapper (<=3 levels up) or named
                    // by its aria-controls
                    var related = revealed.filter(function (r) {
                        return !trig.contains(r) ? _isSiblingTriggerOf(trig, r) : true;
                    });
                    if (!related.length) return;
                    for (var ci = 0; ci < hoverChain.length; ci++) {
                        if (hoverChain[ci].el === trig) return;
                    }
                    if (hoverChain.length >= 4) return;
                    var _viaClick = _triggerClickedAround(trig, t0);
                    hoverChain.push({ el: trig, baselineSet: new Set(), time: t0, revealed: related, clicked: _viaClick });
                } catch (eReveal) {}
            };
            _pendingRevealChecks.push(_check);
            setTimeout(_check, 100);
        } catch (eOver) {}
    }, true);

    // a click can land before the ~100ms checks above have run: they are run
    // right away so the click sees every reveal that already happened
    function _flushPendingRevealChecks() {
        var list = _pendingRevealChecks;
        _pendingRevealChecks = [];
        for (var i = 0; i < list.length; i++) {
            try { list[i](); } catch (e) {}
        }
    }

    // the not-yet-confirmed candidate for the NEXT chain link - exactly
    // the same role the old single-slot pendingHover played, just
    // rebased against the LAST CONFIRMED link's own freezeSize instead of
    // always against 0, so a second (or third) nested reveal can be
    // detected the same way the first one is.
    var _tentativeHover = null; // { el, baselineSet, time }

    document.addEventListener('mouseover', function (e) {
        try {
            var target = e.target;
            // the ambient snapshot is only trustworthy as a PRE-hover
            // baseline when it's fresh enough to plausibly predate this
            // exact hover transition (a real mousemove ~just before
            // entering); a stale/missing one (mouse warped via focus,
            // programmatic dispatch with no preceding mousemove, etc.)
            // falls back to a fresh read - loses the pre/post distinction
            // for that one hover, but never crashes or blocks recording.
            var baselineSet = (Date.now() - _ambientVisiblePrev.time < 500)
                ? _ambientVisiblePrev.visibleSet
                : _visibleCandidatesNear(target);
            // SELF-referential growth check (deliberately NOT compared
            // against a fixed/global reference point - the page's own
            // "ambient noise floor" for _visibleCandidatesNear is not
            // reliably 0; an ordinary, always-visible link elsewhere on
            // the page can easily be included in that scan, so "was
            // anything at all visible" is never a safe baseline).
            // Comparing each new mouseover's baseline against
            // _tentativeHover's OWN previously-recorded baseline is what
            // actually isolates a REAL reveal: mouseover fires (and
            // bubbles) for EVERY element the pointer transitions into,
            // including nested descendants - moving from a trigger down
            // INTO its own just-revealed submenu, then onto a link
            // inside it, fires three separate mouseover events for three
            // different elements. The FIRST of those to actually cause
            // new content to become visible (this baseline growing past
            // _tentativeHover's own) confirms _tentativeHover as a real
            // trigger - pushed onto hoverChain - and _tentativeHover is
            // then reset to null so the very NEXT mouseover bootstraps a
            // fresh comparison point from the page's NEW (already grown)
            // resting state, letting a SECOND, nested reveal (hovering a
            // chip inside an already-open row, opening ITS OWN panel) be
            // detected the exact same self-referential way, instead of
            // every subsequent mouseover just drifting a single old
            // pendingHover slot all the way down to the click target
            // itself (the "nothing to report" case this mechanism exists
            // to avoid).
            if (_tentativeHover && baselineSet.size > _tentativeHover.baselineSet.size) {
                if (target !== _tentativeHover.el
                    && !(target.contains && target.contains(_tentativeHover.el))
                    && hoverChain.length < 3) {
                    // bounded depth (3) - covers any realistic menu/
                    // panel nesting without letting a pathological page
                    // turn this into an unbounded chain
                    hoverChain.push({
                        el: _tentativeHover.el,
                        baselineSet: _tentativeHover.baselineSet,
                        time: _tentativeHover.time,
                    });
                }
                _tentativeHover = null;
                return;
            }
            _tentativeHover = { el: target, baselineSet: baselineSet, time: Date.now() };
        } catch (eHover) {
            // never let a hover-tracking failure break normal recording
        }
    }, true);

    // Consumed (and cleared) by the click handler below, at most once
    // per qualifying click - never re-emitted for a later, unrelated
    // click that merely happens to follow the same hover eventually.
    // Returns an ORDERED array of trigger elements (outermost first,
    // possibly empty) - see hoverChain's own docstring above.
    // FIX 1 (trigger attribution): the element a mouseover handler saw is
    // simply whatever was under the pointer at that instant - when the
    // pointer is moving fast or lingers inside already-open content that is
    // the revealed PANEL (or something inside it), never the trigger that
    // opened it. Maps such an element to the real trigger, generically:
    //   1. itself, when it is an interactive element (a/button/summary/
    //      role=menuitem|button|tab/aria-haspopup|expanded/tabindex)
    //   2. the owner named by aria-controls / aria-labelledby
    //   3. walking up, the nearest interactive SIBLING (same parent) of the
    //      branch that holds `el` - the usual "trigger + panel under one
    //      wrapper" shape
    //   4. the nearest interactive ancestor
    // Returns null when nothing qualifies (the link is then dropped - a
    // hover is never recorded on a big non-interactive container).
    var _TRIGGER_SEL = 'a, button, summary, [role=menuitem], [role=button], [role=tab], [role=menuitemcheckbox], [aria-haspopup], [aria-expanded], [tabindex]';
    function _isInteractiveTrigger(n) {
        try { return !!(n && n.matches && n.matches(_TRIGGER_SEL)); } catch (e) { return false; }
    }
    function _resolveRevealTrigger(el, avoid) {
        try {
            if (!el) return null;
            // A pointer target inside an active modal must not be attributed
            // to an interactive sibling behind that modal. The sibling walk
            // below is useful for ordinary trigger/panel pairs, but for a
            // page-blocking layer it can otherwise turn a modal close-button
            // mouseover into a hover action on an unrelated control beneath
            // the overlay. Keep inferred triggers in the same modal scope as
            // the actual element that received the pointer event.
            var sourceInModal = _isInStrictModal(el);
            var sameModalScope = function (candidate) {
                return !!candidate && _isInStrictModal(candidate) === sourceInModal;
            };
            if (_isInteractiveTrigger(el) && el.matches('a, button, summary, [role=menuitem], [role=button], [role=tab], [aria-haspopup], [aria-expanded]')) return el;
            // a wrapper that holds BOTH the trigger and its panel (the usual
            // <li>/<div> shape): its own direct interactive child that is not
            // the branch holding the click target is the trigger
            for (var ci0 = 0; ci0 < el.children.length; ci0++) {
                var kid = el.children[ci0];
                if (avoid && (kid === avoid || kid.contains(avoid))) continue;
                if (_isInteractiveTrigger(kid) && _isHoverCandidateVisible(kid) && sameModalScope(kid)) return kid;
            }
            var strictAnc = el.parentElement;
            while (strictAnc && strictAnc !== document.body) {
                if (strictAnc.matches('a, button, summary, [role=menuitem], [role=button], [role=tab], [aria-haspopup], [aria-expanded]') && _isHoverCandidateVisible(strictAnc) && sameModalScope(strictAnc)) return strictAnc;
                strictAnc = strictAnc.parentElement;
            }
            var node = el, depth = 0;
            while (node && node !== document.body && depth < 6) {
                if (node.id) {
                    var owners = document.querySelectorAll('[aria-controls]');
                    for (var oi = 0; oi < owners.length; oi++) {
                        if ((owners[oi].getAttribute('aria-controls') || '').split(/\s+/).indexOf(node.id) !== -1
                            && !owners[oi].contains(node) && _isHoverCandidateVisible(owners[oi]) && sameModalScope(owners[oi])) return owners[oi];
                    }
                }
                var labelled = node.getAttribute && node.getAttribute('aria-labelledby');
                if (labelled) {
                    var ow = document.getElementById(labelled.split(/\s+/)[0]);
                    if (ow && !ow.contains(node) && _isHoverCandidateVisible(ow) && sameModalScope(ow)) return ow;
                }
                var parent = node.parentElement;
                if (parent) {
                    for (var si = 0; si < parent.children.length; si++) {
                        var sib = parent.children[si];
                        if (sib === node || sib.contains(node)) continue;
                        if (_isInteractiveTrigger(sib) && _isHoverCandidateVisible(sib) && sameModalScope(sib)) return sib;
                    }
                }
                node = parent;
                depth++;
            }
            var anc = el.parentElement;
            while (anc && anc !== document.body) {
                if (_isInteractiveTrigger(anc) && _isHoverCandidateVisible(anc) && sameModalScope(anc)) return anc;
                anc = anc.parentElement;
            }
        } catch (eRes) {}
        return null;
    }

    // FIX 1: a trigger whose revealed panel is its SIBLING (trigger and
    // panel under one small wrapper), or that names the panel through
    // aria-controls - the shape a CSS/JS mega-menu most often has. Bounded
    // to 3 wrapper levels so "hovered something nearby" never qualifies.
    function _isSiblingTriggerOf(hoverEl, clickTarget) {
        try {
            if (!_isInteractiveTrigger(hoverEl)) return false;
            var ctl = hoverEl.getAttribute('aria-controls');
            if (ctl) {
                var ids = ctl.split(/\s+/);
                for (var i = 0; i < ids.length; i++) {
                    var panel = document.getElementById(ids[i]);
                    if (panel && panel.contains(clickTarget)) return true;
                }
            }
            var up = hoverEl.parentElement, lvl = 0;
            while (up && up !== document.body && lvl < 3) {
                if (up.contains(clickTarget)) return true;
                up = up.parentElement;
                lvl++;
            }
        } catch (e) {}
        return false;
    }

    // a REAL modal: a dialog / alertdialog / aria-modal / <dialog> ancestor, or a page-blocking
    // fixed/absolute layer covering at least half the viewport. A list, menu, tooltip, toast or
    // autocomplete suggestion box is never a modal.
    function _isStrictDialogOpen() {
        try {
            var ds = document.querySelectorAll('[role=dialog], [role=alertdialog], [aria-modal=true], dialog[open]');
            for (var i = 0; i < ds.length; i++) {
                var r = ds[i].getBoundingClientRect();
                if (r.width <= 0 || r.height <= 0) continue;
                var cs = getComputedStyle(ds[i]);
                if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
                return true;
            }
        } catch (e) {}
        return false;
    }
    var _NOT_MODAL_ROLES = ['listbox', 'menu', 'menubar', 'menuitem', 'option', 'tooltip', 'combobox', 'tree', 'grid', 'status', 'alert'];
    function _isInStrictModal(el) {
        try {
            var vw = window.innerWidth || 1, vh = window.innerHeight || 1;
            var n = el, depth = 0;
            while (n && n.nodeType === 1 && n !== document.body && depth < 40) {
                var role = (n.getAttribute('role') || '').toLowerCase();
                if (role === 'dialog' || role === 'alertdialog') return true;
                if ((n.getAttribute('aria-modal') || '').toLowerCase() === 'true') return true;
                if (n.tagName === 'DIALOG') return true;
                if (_NOT_MODAL_ROLES.indexOf(role) !== -1) return false;
                var cs = getComputedStyle(n);
                if (cs.position === 'fixed' || cs.position === 'absolute') {
                    var r = n.getBoundingClientRect();
                    if (r.width * r.height >= vw * vh * 0.5) return true;
                }
                n = n.parentElement; depth++;
            }
        } catch (e) {}
        return false;
    }

    // the visible text of the card / row an unnamed link or button sits in (its first line): what the
    // user saw next to it. Only small containers are read, never a whole page section.
    function _nearText(rawEl) {
        try {
            var el = (rawEl.closest && rawEl.closest('a, button, [role=button], [role=link]')) || rawEl;
            if (el === document.documentElement || el === document.body || (!isInteractive(el) && afqaIsContainerLike(el))) return null;
            var own = ((el.innerText || el.textContent || '') + '').trim();
            if (own) return null;                       // it has text of its own: that is its name
            var n = el.parentElement, depth = 0;
            while (n && n !== document.body && depth < 4) {
                var tx = ((n.innerText || '') + '').trim();
                if (tx.length >= 3 && tx.length <= 240) {
                    var lines = tx.split(String.fromCharCode(10));
                    for (var i = 0; i < lines.length; i++) {
                        var ln = lines[i].trim();
                        if (ln.length >= 3) return ln.slice(0, 80);
                    }
                }
                n = n.parentElement; depth++;
            }
        } catch (e) {}
        return null;
    }

    // An element with no text of its own (an icon-only button): a fingerprint made only of what already exists on it
    // - the class tokens / data-*icon* attributes / <use href> / title of its svg (or icon font element), and its
    // index among the interactive siblings of the same container - so replay can tell it from its neighbours.
    function afqaIconFingerprint(el) {
        try {
            if (!el || el.nodeType !== 1) return null;
            if (((el.innerText || el.textContent || '') + '').trim()) return null;      // it has text: not icon-only
            var parts = [];
            var gfx = el.querySelector ? (el.querySelector('svg') || el.querySelector('i, [class*=icon]')) : null;
            if (gfx) {
                var cls = (gfx.getAttribute('class') || '').split(' ').filter(Boolean);
                parts = parts.concat(cls);
                for (var ai = 0; ai < gfx.attributes.length; ai++) {
                    var an = gfx.attributes[ai].name;
                    if (an.indexOf('data-') === 0 && an.indexOf('icon') !== -1) parts.push(an + '=' + gfx.attributes[ai].value);
                }
                var use = gfx.querySelector ? gfx.querySelector('use') : null;
                if (use) { var uh = use.getAttribute('href') || use.getAttribute('xlink:href'); if (uh) parts.push('use=' + uh); }
                var ti = gfx.querySelector ? gfx.querySelector('title') : null;
                if (ti && (ti.textContent || '').trim()) parts.push('title=' + ti.textContent.trim());
            }
            var sibIndex = null, sibTotal = null;
            var par = el.parentElement;
            if (par) {
                var sibs = Array.prototype.filter.call(par.children, function (c) { return c.matches && c.matches(AFQA_STRONG_INTERACTIVE_SELECTOR); });
                sibTotal = sibs.length;
                sibIndex = sibs.indexOf(el);
                if (sibIndex < 0) { sibIndex = null; sibTotal = null; }
            }
            if (!parts.length && sibIndex === null) return null;
            var parClass = par && par.className && par.className.toString ? par.className.toString() : '';
            return { icon_signature: parts.join(' ').slice(0, 200) || null, sibling_index: sibIndex,
                sibling_total: sibTotal, container_tag: par ? par.tagName.toLowerCase() : null,
                container_class: parClass };
        } catch (eIconFp) { return null; }
    }

    // the main visible text of the nearest REPEATING container of the control (a list item / row / article, or
    // one of several sibling blocks of the same tag and class - a product card), other than the control's own
    // name: its heading, else its longest text line. { text, tag } or null. Never raises.
    function afqaItemContext(rawEl) {
        try {
            var ctl = (rawEl.closest && rawEl.closest('a, button, input, select, textarea, [role=button], [role=link], [role=checkbox], [role=menuitem], [role=tab], [role=option]')) || rawEl;
            var flat = function (s) { return ((s || '') + '').replace(/\s+/g, ' ').trim(); };
            var own = flat((ctl.innerText || '') + ' ' + (ctl.getAttribute('aria-label') || '')).toLowerCase();
            var clsOf = function (n) { return (n.className && n.className.toString) ? n.className.toString() : ''; };
            // a short cell repeated among identical siblings (a date, a time slot, a seat): its context is the
            // heading of the block it sits in (e.g. the calendar's month / year)
            try {
                var par = ctl.parentElement, sameCells = 0;
                if (par && own.length <= 8) {
                    for (var sc = par.firstElementChild; sc; sc = sc.nextElementSibling) {
                        if (sc.tagName === ctl.tagName && clsOf(sc) === clsOf(ctl)) sameCells++;
                    }
                }
                if (sameCells >= 3) {
                    var anc = ctl.parentElement;
                    for (var hd = 0; anc && anc !== document.body && hd < 6; hd++, anc = anc.parentElement) {
                        var arole = (anc.getAttribute('role') || '').toLowerCase();
                        var aal = flat(anc.getAttribute('aria-label'));
                        if (aal && aal.length <= 60 && (arole === 'grid' || arole === 'table' || arole === 'listbox' || arole === 'radiogroup')) {
                            return { text: aal.slice(0, 100), tag: anc.tagName.toLowerCase() };
                        }
                        var hel = anc.querySelector('h1, h2, h3, h4, h5, h6, [role=heading], caption, legend');
                        var htx = hel ? flat(hel.innerText || hel.textContent) : '';
                        if (htx && htx.length <= 60 && htx.toLowerCase() !== own) return { text: htx.slice(0, 100), tag: anc.tagName.toLowerCase() };
                    }
                }
            } catch (eCell) {}
            var node = ctl.parentElement;
            for (var d = 0; node && node !== document.body && d < 12; d++, node = node.parentElement) {
                var tg = node.tagName.toLowerCase(), role = (node.getAttribute('role') || '').toLowerCase();
                var repeating = tg === 'li' || tg === 'tr' || tg === 'article' || role === 'listitem' || role === 'row' || role === 'article';
                if (!repeating && node.parentElement) {
                    var same = 0, cls = clsOf(node);
                    for (var c = node.parentElement.firstElementChild; c; c = c.nextElementSibling) {
                        if (c.tagName === node.tagName && clsOf(c) === cls) same++;
                    }
                    repeating = same >= 2;
                }
                if (!repeating) continue;
                var r = node.getBoundingClientRect();
                if (r.height > (window.innerHeight || 800) * 1.5) return null;          // a page-sized section
                var h = node.querySelector('h1, h2, h3, h4, h5, h6, [role=heading]');
                var ht = h ? flat(h.innerText) : '';
                if (ht && ht.toLowerCase() !== own) return { text: ht.slice(0, 100), tag: tg };
                var best = '';
                (node.innerText || '').split('\n').forEach(function (l) {
                    l = flat(l);
                    if (l.length < 3 || l.length > 120 || l.toLowerCase() === own) return;
                    if (!/[A-Za-zÀ-￿]{3}/.test(l)) return;
                    if (l.length > best.length) best = l;
                });
                return best ? { text: best.slice(0, 100), tag: tg } : null;
            }
        } catch (e) {}
        return null;
    }

    // the short visible text of the smallest block around the element that has some (icon-font glyphs removed),
    // up to 4 levels up - "" when there is none. Never raises.
    function afqaNearbyLabel(rawEl) {
        try {
            var clean = function (s) {
                return ((s || '') + '').split('').filter(function (ch) {
                    var c = ch.charCodeAt(0);
                    return !(c >= 0xE000 && c <= 0xF8FF);
                }).join('').replace(/\s+/g, ' ').trim();
            };
            var n = rawEl && rawEl.parentElement;
            for (var d = 0; n && n !== document.body && d < 4; d++, n = n.parentElement) {
                var t = clean(n.innerText);
                if (t && t.length <= 40) return t;
                if (t.length > 40) break;
            }
        } catch (e) {}
        return '';
    }

    function _innerLabel(rawEl) {
        try {
            var el = (rawEl.closest && rawEl.closest('a, button, [role=button], [role=link]')) || rawEl;
            if (!el || !el.querySelector) return null;
            // a page-sized wrapper's headings are not the name of what was clicked
            if (el === document.documentElement || el === document.body || (!isInteractive(el) && afqaIsContainerLike(el))) return null;
            var h = el.querySelector('h1, h2, h3, h4, h5, h6, [role=heading]');
            var ht = h ? (h.innerText || h.textContent || '').trim() : '';
            if (ht) return ht.slice(0, 80);
            var im = el.querySelector('img[alt]');
            var alt = im ? (im.getAttribute('alt') || '').trim() : '';
            if (alt) return alt.slice(0, 80);
            var ti = el.querySelector('[title]');
            var tt = ti ? (ti.getAttribute('title') || '').trim() : '';
            if (tt) return tt.slice(0, 80);
        } catch (e) {}
        return null;
    }

    function _contentHint(rawEl) {
        try {
            var el = (rawEl.closest && rawEl.closest('button, a, [role=button], [role=link], [tabindex], input, select, textarea, iframe, video, audio, canvas, img')) || rawEl;
            var tag = el.tagName.toLowerCase();
            if (tag === 'iframe' || tag === 'frame') return 'frame';
            if (tag === 'video' || (el.querySelector && el.querySelector('video'))) return 'video';
            if (tag === 'audio' || (el.querySelector && el.querySelector('audio'))) return 'audio';
            if (tag === 'canvas') return 'canvas';
            if (tag === 'img' || tag === 'picture') return 'image';
            if (tag === 'input') return 'input:' + ((el.getAttribute('type') || 'text').toLowerCase());
            if (el.querySelector && (el.querySelector('svg') || el.querySelector('i[class*=icon], span[class*=icon], i[class^=fa]'))
                && !((el.innerText || '').trim())) return 'icon';
            if (el.querySelector && el.querySelector('img') && !((el.innerText || '').trim())) return 'image';
        } catch (e) {}
        return null;
    }

    // ---- popups the website opens by itself ----------------------------------------
    // A dialog that becomes visible with no user gesture shortly before it (no click, key, touch,
    // submit, or hover on a popup trigger) was opened by the site. Steps inside it are marked
    // (payload.site_popup) so replay can skip them when the site does not show it again.
    var _lastUserGestureTs = 0;
    var SITE_POPUP_GESTURE_WINDOW_MS = 3000;
    ['mousedown', 'keydown', 'touchstart', 'submit', 'change'].forEach(function (n) {
        document.addEventListener(n, function (ev) { if (ev.isTrusted) _lastUserGestureTs = Date.now(); }, true);
    });
    document.addEventListener('mouseover', function (ev) {
        if (!ev.isTrusted) return;
        try {
            if (ev.target && ev.target.closest && ev.target.closest('[aria-haspopup], [aria-expanded], [aria-controls]')) _lastUserGestureTs = Date.now();
        } catch (e) {}
    }, true);
    var _siteOpenedPopups = new WeakSet();
    var _popupWasShown = new WeakMap();
    function _scanForSitePopups() {
        try {
            var ds = document.querySelectorAll('[role=dialog], [role=alertdialog], [aria-modal=true], dialog[open]');
            for (var i = 0; i < ds.length; i++) {
                var d = ds[i];
                var r = d.getBoundingClientRect();
                var cs = getComputedStyle(d);
                var shown = r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0;
                var was = _popupWasShown.get(d) === true;
                _popupWasShown.set(d, shown);
                if (shown && !was && (Date.now() - _lastUserGestureTs) > SITE_POPUP_GESTURE_WINDOW_MS) _siteOpenedPopups.add(d);
                else if (shown && !was) _siteOpenedPopups.delete(d);
            }
        } catch (e) {}
    }
    function _installSitePopupWatch() {
        try {
            var _sitePopupTimer = null;
            new MutationObserver(function () {
                if (_sitePopupTimer) return;
                _sitePopupTimer = setTimeout(function () { _sitePopupTimer = null; _scanForSitePopups(); }, 80);
            }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ['open', 'style', 'class', 'hidden', 'aria-hidden'] });
            setTimeout(_scanForSitePopups, 50);
        } catch (eSitePopupObs) {}
    }
    // the script may run before the page has a root element
    if (document.documentElement) _installSitePopupWatch();
    else document.addEventListener('DOMContentLoaded', _installSitePopupWatch);
    // up to 4 pieces of content visible on screen right now, each { text, tag, x, y } (y = its top on screen):
    // the nearest element with a short text of its own at sample points across the window, each text only once.
    // Never raises.
    function afqaScrollAnchors() {
        var out = [];
        try {
            var vw = window.innerWidth || 0, vh = window.innerHeight || 0;
            if (!vw || !vh) return out;
            var seen = {};
            var xs = [0.25, 0.5, 0.75], ys = [0.2, 0.4, 0.6, 0.8];
            for (var yi = 0; yi < ys.length && out.length < 4; yi++) {
                for (var xi = 0; xi < xs.length && out.length < 4; xi++) {
                    var el = document.elementFromPoint(vw * xs[xi], vh * ys[yi]);
                    // content that stays put on screen whatever the scroll (a fixed / sticky header, side tab,
                    // floating banner, cookie bar) says nothing about where the page was scrolled to
                    var pinned = false;
                    for (var pn = el; pn && pn.nodeType === 1; pn = pn.parentElement) {
                        var pp = getComputedStyle(pn).position;
                        if (pp === 'fixed' || pp === 'sticky') { pinned = true; break; }
                    }
                    if (pinned) continue;
                    for (var d = 0; el && d < 6; d++, el = el.parentElement) {
                        if (el === document.body || el === document.documentElement) break;
                        var t = ((el.innerText || '') + '').replace(/\s+/g, ' ').trim();
                        if (!t) continue;
                        if (t.length < 3 || t.length > 80) { if (t.length > 80) break; continue; }
                        if (seen[t]) break;
                        var r = el.getBoundingClientRect();
                        if (r.width <= 1 || r.height <= 1 || r.top < 0 || r.bottom > vh) break;
                        seen[t] = true;
                        out.push({ text: t, tag: el.tagName.toLowerCase(), x: Math.round(r.left), y: Math.round(r.top) });
                        break;
                    }
                }
            }
        } catch (e) {}
        return out;
    }

    // can a person see this element on screen right now? Not when it is zero-size, entirely outside the
    // window (a skip-link parked at x=-9999), hidden (display / visibility), fully transparent through any
    // ancestor, or clipped away (the "visually hidden" pattern). Never raises (unknown = visible).
    function afqaVisiblyOnScreen(el) {
        try {
            if (!el || !el.getBoundingClientRect) return true;
            var r = el.getBoundingClientRect();
            if (r.width <= 1 || r.height <= 1) return false;
            var vw = window.innerWidth || document.documentElement.clientWidth || 0;
            var vh = window.innerHeight || document.documentElement.clientHeight || 0;
            if (r.right <= 0 || r.bottom <= 0 || (vw && r.left >= vw) || (vh && r.top >= vh)) return false;
            for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
                var cs = getComputedStyle(n);
                if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') return false;
                if (parseFloat(cs.opacity) === 0) return false;
                var clip = (cs.clip || '').replace(/\s+/g, '');
                if (clip === 'rect(0,0,0,0)' || clip === 'rect(0px,0px,0px,0px)' || clip === 'rect(1px,1px,1px,1px)') return false;
                if ((cs.clipPath || '').indexOf('inset(50%') === 0) return false;
            }
        } catch (eVis) {}
        return true;
    }

    function _sitePopupOf(el) {
        try {
            var n = el, depth = 0;
            while (n && n.nodeType === 1 && depth < 40) {
                if (_siteOpenedPopups.has(n)) {
                    var h = n.querySelector && n.querySelector('h1, h2, h3, [role=heading]');
                    var title = (n.getAttribute('aria-label') || (h && (h.innerText || h.textContent)) || (n.innerText || '').split('\n')[0] || '').replace(/\s+/g, ' ').trim().slice(0, 60);
                    return { title: title || null };
                }
                n = n.parentElement; depth++;
            }
        } catch (e) {}
        return null;
    }

    function _popupFingerprintOf(el) {
        try {
            var vw = window.innerWidth || 1, vh = window.innerHeight || 1;
            var n = el, depth = 0;
            while (n && n !== document.body && n !== document.documentElement && depth < 25) {
                if (n.nodeType === 1) {
                    var isDlg = !!(n.matches && n.matches('[role=dialog], [role=alertdialog], [aria-modal=true], dialog'));
                    var hi = false;
                    if (!isDlg) {
                        var cs = getComputedStyle(n);
                        var z = parseInt(cs.zIndex, 10);
                        if ((cs.position === 'fixed' || cs.position === 'absolute') && !isNaN(z) && z >= 10) {
                            var r = n.getBoundingClientRect();
                            hi = r.width * r.height >= vw * vh * 0.08;
                        }
                    }
                    if (isDlg || hi) {
                        return {
                            kind: isDlg ? 'dialog' : 'layer',
                            tag: n.tagName.toLowerCase(),
                            id: n.id || null,
                            role: n.getAttribute('role') || null,
                            aria_label: n.getAttribute('aria-label') || null,
                            css_path: cssPath(n),
                            text_hint: (n.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 60) || null
                        };
                    }
                }
                n = n.parentElement || ((n.getRootNode && n.getRootNode().host) || null);
                depth++;
            }
        } catch (e) {}
        return null;
    }

    var _clickedTriggersNow = [];
    function _consumeHoverChain(clickTarget) {
        _flushPendingRevealChecks();
        _clickedTriggersNow = [];
        var now = Date.now();
        var kept = [];
        var result = [];
        for (var i = 0; i < hoverChain.length; i++) {
            var link = hoverChain[i];
            var hoverEl = link.el;
            if (link.revealed) {
                // detected by what the hover made visible: it qualifies when
                // the click target is inside that revealed content
                if (now - link.time > 30000) continue;
                if (!hoverEl) continue;
                if (hoverEl === clickTarget || (clickTarget.contains && clickTarget.contains(hoverEl))) { link.clicked = true; kept.push(link); continue; }
                var covers = false;
                for (var rv = 0; rv < link.revealed.length; rv++) {
                    var rn = link.revealed[rv];
                    if (rn === clickTarget || (rn.contains && rn.contains(clickTarget))) { covers = true; break; }
                }
                if (covers && result.indexOf(hoverEl) === -1) {
                    result.push(hoverEl);
                    // ISSUE 1: the user also CLICKED this trigger - that click is
                    // its own step; no standalone hover step is saved for it
                    if (link.clicked) _clickedTriggersNow.push(hoverEl);
                }
                // clicking the trigger itself (a click-to-open menu) must not
                // forget it: the NEXT click inside what it opened needs it
                continue;
            }
            if (now - link.time > HOVER_PENDING_MAX_AGE_MS) continue;
            if (!hoverEl || hoverEl === clickTarget) continue;
            // hovering something INSIDE what you go on to click (the
            // reverse direction only) is completely ordinary - e.g.
            // hovering an icon then clicking the button that wraps it -
            // never a "hover revealed a separate menu" case.
            if (clickTarget.contains && clickTarget.contains(hoverEl)) continue;
            // RC2 (CONFIRMED via a live Amazon.in recording: a hover step
            // got recorded targeting the filter section's own "Brands"
            // header while the mouse merely passed near it on the way to
            // clicking an actual, always-visible "Allen Solly" filter
            // option several DOM levels away in a totally different
            // branch - no genuine :hover-driven reveal was involved at
            // all). A trigger whose hover genuinely reveals clickTarget
            // is - by how CSS :hover-based reveals actually work -
            // structurally an ANCESTOR of what it reveals (the DOM
            // shape every real mega-menu/dropdown/panel in this file's
            // own fixtures uses: trigger -> ... -> revealed item).
            // Requiring that here, strictly, is what rejects "just
            // happened to be hovered nearby" candidates that share only
            // some much higher, unrelated common ancestor (the whole
            // page, a shared layout wrapper) - a SIBLING-shaped trigger
            // (rarer) is still covered independently by the REPLAY-side
            // safety net (_reveal_via_ancestor_hover's own sibling walk,
            // used for every recording, old or new, regardless of
            // whether a hover_chain was ever recorded for this step at
            // all), so nothing is lost by not also recording it here.
            if (!(hoverEl.contains && hoverEl.contains(clickTarget)) && !_isSiblingTriggerOf(hoverEl, clickTarget)) continue;
            // was NOT visible before this link's own hover - the click
            // target must not already have been among the candidates
            // snapshotted as visible at that moment.
            if (link.baselineSet.has(clickTarget)) continue;
            // RC2 ("the trigger must be the SMALLEST element that caused
            // the reveal" - CONFIRMED via a live Myntra recording: the
            // hover step's own recorded text was the ENTIRE filter bar's
            // seven category names concatenated - "Bundles\nCountry of
            // Origin\nMaterials\n..." - not the one chip actually
            // hovered).
            //
            // An earlier version of this check compared hoverEl's own
            // AGGREGATE innerText (or its sibling count) against a
            // threshold - CONFIRMED REAL REGRESSION via this file's own
            // hover-menu fixture test: a genuine single trigger's
            // aggregate innerText NATURALLY includes its own revealed
            // submenu's text too (the submenu is a DESCENDANT of the
            // trigger being hovered), and a genuine trigger very
            // commonly sits alongside OTHER top-level nav items as
            // siblings (every ordinary navbar) - both signals fired on
            // the perfectly legitimate case, not just the "whole bar"
            // one. The signal that actually only fires for the bad case:
            // does hoverEl DIRECTLY contain (as its own immediate
            // children, not deep descendants) more than one element that
            // independently looks trigger-shaped? A real trigger's own
            // direct children are typically just its label text and/or
            // ONE wrapping element for its own revealed panel - the
            // "Bundles/Country of Origin/..." container, by contrast,
            // directly contains several sibling <li>/option elements,
            // each with its own label, as its own immediate children.
            var hoverDirectTriggerChildCount = 0;
            if (hoverEl.children) {
                for (var ci = 0; ci < hoverEl.children.length; ci++) {
                    if (_isRevealCandidateShaped(hoverEl.children[ci])) {
                        hoverDirectTriggerChildCount++;
                    }
                }
            }
            if (hoverDirectTriggerChildCount > 1) continue;
            // FIX 1: attribute to the real trigger, never the resting/
            // panel element - and never twice for the same trigger
            var realTrigger = _resolveRevealTrigger(hoverEl, clickTarget);
            if (!realTrigger || realTrigger === clickTarget) continue;
            if (clickTarget.contains && clickTarget.contains(realTrigger)) continue;
            if (result.indexOf(realTrigger) !== -1) continue;
            result.push(realTrigger);
            // the user also CLICKED this trigger around then: that click is its own step
            if (_triggerClickedAround(realTrigger, link.time)) {
                _clickedTriggersNow.push(realTrigger);
            }
        }
        hoverChain = kept;
        _tentativeHover = null;
        return result;
    }

    // FIX 1.1 (gesture id): one physical user gesture is everything from
    // a mousedown through whatever native events the browser generates
    // as a direct consequence of it - most commonly just its own click,
    // but for a <label> (wrapping a control, or associated via for=) the
    // browser ALSO dispatches a second, synthetic click directly on the
    // control, plus a change event, all for that SAME physical press.
    // _currentGestureId increments on every real mousedown (a NEW
    // physical press always starts a new gesture); _lastSentGestureId
    // records which gesture the most recently SENT click-family action
    // belonged to, so a second native click/change arriving for the
    // SAME still-current gesture is recognized generically (never a
    // site-specific label/for=/framework check) rather than relying only
    // on the semantic-element/timing heuristic below.
    var _gestureCounter = 0;
    var _currentGestureId = 0;
    var _lastSentGestureId = -1;

    window.addEventListener('mousedown', function (e) {
        try {
            _currentGestureId = ++_gestureCounter;
            var rawTarget = e.target;
            var semanticEl = resolveSemanticTarget(rawTarget);
            var _snapCheckboxTarget = findCheckboxTarget(rawTarget);
            _preClickSnapshot = {
                rawTarget: rawTarget,
                checkboxTarget: _snapCheckboxTarget,
                // FIX D debug field - snapshotted immediately alongside
                // checkboxTarget itself, from the SAME findCheckboxTarget
                // call, so a later findCheckboxTarget call elsewhere
                // (before this snapshot is actually consumed) can never
                // overwrite it out from under this one.
                checkboxClassifiedBy: lastCheckboxClassifiedBy,
                semanticEl: semanticEl,
                locatorProfile: buildLocatorProfile(semanticEl),
                gestureId: _currentGestureId,
            };
            // FIX 3 (drag detection): opened on EVERY mousedown, cleared
            // on mouseup whether or not it turned out to be a real drag
            // (see the mouseup listener below) - capturing sourceRect and
            // valueBefore NOW, before the page has any chance to react to
            // this press, is what keeps a slider's own "before" value
            // honest even if the site starts mutating the control the
            // instant it receives focus/mousedown (some custom sliders do).
            // the thing being dragged is the slider-like element (native
            // range input / role=slider / aria-valuenow) when the press
            // landed on it or on a decoration inside it (a touch-area or
            // tooltip child, whose css_path is ambiguous next to its
            // sibling children) - record THAT as the source, not the
            // decoration. Any other draggable is its own source.
            var _dragSrcEl = _closestSliderLikeElement(semanticEl) || semanticEl;
            var _dragSrcProfile = (_dragSrcEl === semanticEl)
                ? _preClickSnapshot.locatorProfile
                : buildLocatorProfile(_dragSrcEl);
            var _dragThumbInfo = _findSliderThumbInfo(_dragSrcEl);
            _dragState = {
                startX: e.clientX,
                startY: e.clientY,
                maxDist: 0,
                path: [{ x: e.clientX, y: e.clientY, t: 0 }],
                lastSampleAt: Date.now(),
                t0: Date.now(),
                gestureId: _currentGestureId,
                sourceRect: _dragSrcEl.getBoundingClientRect(),
                sourceEl: _dragSrcEl,
                sourceProfile: _dragSrcProfile,
                thumbInfo: _dragThumbInfo,
                // built NOW, before the drag: a slider handle's own text is
                // usually its current value, so a profile built at mouseup
                // would carry the AFTER text and later match some unrelated
                // element that happens to show that number (CONFIRMED: a
                // scale label "12" instead of the handle)
                thumbProfile: _dragThumbInfo ? buildLocatorProfile(_dragThumbInfo.thumbEl) : null,
                valueBefore: _captureDragValueSnapshot(_dragSrcEl, _dragThumbInfo),
                // the source's nearest ancestors and their boxes AS THEY
                // ARE NOW (before any drag movement) - see _findDragTrack
                ancestorRects: _snapshotAncestorRects(_dragSrcEl),
            };
        } catch (snapErr) {
            _preClickSnapshot = null;
            _dragState = null;
        }
    }, true);

    // ---- menu triggers: a press the page handles on pointerdown ---------------------------------
    // Many UI libraries open a menu on pointerdown and cancel the mouse events that follow (no mousedown), or
    // never let a click reach us. Without its own gesture id the click that does arrive looked like an echo of
    // the PREVIOUS click's mousedown and was dropped. Capture phase on window, like every other listener here.
    var afqaClickHandlerRef = null;     // the click listener below (set when it is registered)
    var afqaClickSeenAt = 0;            // when a click event last reached that listener
    var afqaPd = null;                  // the press waiting for its click
    var AFQA_PD_CLICK_WAIT_MS = 500;
    window.addEventListener('pointerdown', function (e) {
        try {
            if (!e.isTrusted || window.__afqaPickMode) return;
            if (typeof e.button === 'number' && e.button !== 0) return;
            _currentGestureId = ++_gestureCounter;                 // this press is its own gesture
            afqaLastPress = { target: afqaInnerEvent(e).target, x: e.clientX, y: e.clientY, t: Date.now() };
            if (afqaPd) afqaPd.cancelled = true;
            afqaPd = null;
            var pdTarget = afqaInnerEvent(e).target;
            var res = resolveSemanticTarget(pdTarget);
            if (!res || !(isInteractive(res) || afqaExtendedClickable(pdTarget) === res)) return;
            var pd = { target: pdTarget, x: e.clientX, y: e.clientY, t: Date.now(), cancelled: false };
            afqaPd = pd;
            setTimeout(function () { afqaPdFallback(pd); }, AFQA_PD_CLICK_WAIT_MS);
        } catch (ePdDown) {}
    }, true);
    window.addEventListener('pointerup', function (e) {
        try {
            if (afqaPd && (Math.abs(e.clientX - afqaPd.x) > 10 || Math.abs(e.clientY - afqaPd.y) > 10)) afqaPd.cancelled = true;
        } catch (ePdUp) {}
    }, true);
    window.addEventListener('pointercancel', function () { try { if (afqaPd) afqaPd.cancelled = true; } catch (ePdCancel) {} }, true);
    // no click for this press within the window: record it as a click anyway (the click listener's own
    // checks - gesture id, drag, duplicates - still apply, so a press that did produce a click or a drag
    // is never recorded twice)
    function afqaPdFallback(pd) {
        try {
            if (!pd || pd.cancelled || afqaClickSeenAt >= pd.t || !afqaClickHandlerRef) return;
            afqaClickHandlerRef({
                target: pd.target, isTrusted: true, clientX: pd.x, clientY: pd.y, button: 0,
                preventDefault: function () {}, stopPropagation: function () {}, stopImmediatePropagation: function () {}
            });
        } catch (ePdFallback) {}
    }

    // FIX 3 (new "drag" action - sliders, range inputs, drag-and-drop,
    // sortable lists): a pointerdown followed by movement beyond
    // DRAG_MOVE_THRESHOLD_PX and a pointerup is ONE "drag" action, sharing
    // the SAME gesture id _preClickSnapshot already assigns on mousedown -
    // sending it here and marking _lastSentGestureId (exactly like every
    // other click-family action does) makes the existing gesture-id dedup
    // at the top of the 'click' listener below suppress the trailing
    // click for free, with no separate mechanism needed. A plain click/
    // tap (no real movement) is completely unaffected - _dragState is
    // simply cleared with nothing sent.
    var DRAG_MOVE_THRESHOLD_PX = 5;
    var DRAG_MAX_PATH_POINTS = 20;
    var DRAG_PATH_SAMPLE_MS = 40;
    var DRAG_VALUE_SETTLE_TIMEOUT_MS = 500;
    var DRAG_VALUE_SETTLE_POLL_MS = 50;
    var _dragState = null;
    var _dragDropInfo = null; // set by dragstart/drop listeners below, consumed on mouseup

    function _closestSliderLikeElement(el) {
        // walks up a few ancestor levels looking for input[type=range],
        // [role="slider"], or an aria-valuenow-bearing element - generic,
        // no site-specific selector/class-name assumption
        var node = el;
        for (var i = 0; i < 4 && node; i++) {
            if (node.tagName === 'INPUT' && (node.type || '').toLowerCase() === 'range') return node;
            if (node.getAttribute && (node.getAttribute('role') === 'slider' || node.hasAttribute('aria-valuenow'))) return node;
            node = node.parentElement;
        }
        return null;
    }

    // multi-thumb sliders (a price-RANGE control with separate min/max
    // handles, say): dragging one thumb must never read/verify the OTHER
    // thumb's value just because they're both "the nearest slider-like
    // element" and happen to sit close together. Identifies which thumb
    // (by index among ALL of them, plus its own locator) the drag's own
    // source element actually is, generically - no site-specific
    // selector, just "how many sibling elements share the same native-
    // range/role=slider/aria-valuenow shape, within the nearest shared
    // container". Returns null for an ordinary single-thumb slider (or
    // no slider at all) - nothing extra to record in that case, the
    // existing _closestSliderLikeElement-based path is already unambiguous.
    // resolution-independent drag support: the "track" a dragged element
    // travels along (a slider rail, a scrollbar gutter, a sortable list's
    // container) is whichever of its nearest ancestors is clearly larger
    // than it along the drag's own axis AND contains both the drag's start
    // and end along that axis. Recording the drag as fractions of THAT
    // extent (replay re-applies them to the live track) makes it land on
    // the same logical position when the track is wider/narrower/moved at
    // replay time, instead of replaying raw pixels. Generic - no class
    // names, ids or site knowledge; absent when no such ancestor exists.
    var DRAG_TRACK_MAX_LEVELS = 4;
    function _snapshotAncestorRects(el) {
        var out = [];
        var node = el && el.parentElement;
        for (var i = 0; i < DRAG_TRACK_MAX_LEVELS && node; i++) {
            try {
                var r = node.getBoundingClientRect();
                out.push({ el: node, rect: { x: r.x, y: r.y, width: r.width, height: r.height } });
            } catch (e) {}
            node = node.parentElement;
        }
        return out;
    }

    function _findDragTrack(state, sourceRect, endX, endY) {
        var dx = endX - state.startX, dy = endY - state.startY;
        var axis = Math.abs(dx) >= Math.abs(dy) ? 'x' : 'y';
        var startC = axis === 'x' ? state.startX : state.startY;
        var endC = axis === 'x' ? endX : endY;
        var srcLen = axis === 'x' ? sourceRect.width : sourceRect.height;
        var cands = state.ancestorRects || [];
        for (var i = 0; i < cands.length; i++) {
            var r = cands[i].rect;
            var lo = axis === 'x' ? r.x : r.y;
            var len = axis === 'x' ? r.width : r.height;
            if (!(len > 0) || len < 2 * Math.max(srcLen, 1)) continue;
            var tol = Math.max(srcLen, 2);
            if (startC < lo - tol || startC > lo + len + tol) continue;
            if (endC < lo - tol || endC > lo + len + tol) continue;
            // a real track stays put while its thumb moves; an ancestor
            // whose own box moved/resized during the drag (a slider's
            // "origin" element, translated by the handle's value) is part
            // of the moving control, not the rail it travels along
            try {
                var r2 = cands[i].el.getBoundingClientRect();
                if (Math.abs(r2.x - r.x) > 1.5 || Math.abs(r2.y - r.y) > 1.5 ||
                    Math.abs(r2.width - r.width) > 1.5 || Math.abs(r2.height - r.height) > 1.5) continue;
            } catch (e) {}
            return {
                axis: axis,
                locator_profile: buildLocatorProfile(cands[i].el),
                rect_at_down: { x: r.x, y: r.y, width: r.width, height: r.height },
            };
        }
        return null;
    }

    function _findSliderThumbInfo(el) {
        var thumbEl = null;
        if (el.tagName === 'INPUT' && (el.type || '').toLowerCase() === 'range') {
            thumbEl = el;
        } else if (el.getAttribute && (el.getAttribute('role') === 'slider' || el.hasAttribute('aria-valuenow'))) {
            thumbEl = el;
        } else if (el.querySelector) {
            try {
                thumbEl = el.querySelector('input[type="range"], [role="slider"], [aria-valuenow]');
            } catch (e) {}
        }
        if (!thumbEl) return null;

        var selector = (thumbEl.tagName === 'INPUT' && (thumbEl.type || '').toLowerCase() === 'range')
            ? 'input[type="range"]'
            : '[role="slider"], [aria-valuenow]';
        var container = thumbEl.parentElement;
        var thumbs = [];
        for (var i = 0; i < 4 && container; i++) {
            try {
                thumbs = Array.prototype.slice.call(container.querySelectorAll(selector));
            } catch (e) {
                thumbs = [];
            }
            if (thumbs.length > 1) break;
            container = container.parentElement;
        }
        if (thumbs.length <= 1) return null; // single-thumb (or no) slider - nothing extra to record
        var idx = thumbs.indexOf(thumbEl);
        if (idx === -1) return null;
        return { thumbEl: thumbEl, index: idx, total: thumbs.length };
    }

    function _captureDragValueSnapshot(sourceEl, thumbInfo) {
        // best-effort, generic "what value does this control show right
        // now" - a real native range input's own .value, else aria-
        // valuenow/valuetext off the nearest slider-role ancestor, else
        // (last resort, for a fully custom-styled slider with no ARIA at
        // all - exactly the Myntra price-range case) nearby text that
        // looks numeric/currency, climbing a few container levels.
        // Returns null (not a slider at all) rather than guessing when
        // none of these signals exist. thumbInfo (optional, see
        // _findSliderThumbInfo) pins this to a SPECIFIC thumb on a multi-
        // thumb slider instead of whichever slider-like element happens
        // to be nearest.
        try {
            var slider = (thumbInfo && thumbInfo.thumbEl) || _closestSliderLikeElement(sourceEl);
            if (slider) {
                if (slider.tagName === 'INPUT') {
                    return { kind: 'range_value', value: slider.value };
                }
                return {
                    kind: 'aria_value',
                    value: slider.getAttribute('aria-valuenow'),
                    text: slider.getAttribute('aria-valuetext'),
                };
            }
            var container = (sourceEl.closest && sourceEl.closest('[class]')) || sourceEl.parentElement;
            for (var j = 0; j < 3 && container; j++) {
                var txt = (container.innerText || '').trim();
                if (txt && txt.length < 200 && /\d/.test(txt)) {
                    return { kind: 'nearby_text', value: txt };
                }
                container = container.parentElement;
            }
        } catch (e) {}
        return null;
    }

    document.addEventListener('mousemove', function (e) {
        if (!_dragState) return;
        var dx = e.clientX - _dragState.startX;
        var dy = e.clientY - _dragState.startY;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > _dragState.maxDist) _dragState.maxDist = dist;
        var now = Date.now();
        if (now - _dragState.lastSampleAt >= DRAG_PATH_SAMPLE_MS && _dragState.path.length < DRAG_MAX_PATH_POINTS) {
            _dragState.path.push({ x: e.clientX, y: e.clientY, t: now - _dragState.t0 });
            _dragState.lastSampleAt = now;
        }
    }, true);

    // HTML5 drag-and-drop (draggable="true" elements, sortable lists that
    // use the native DnD API rather than plain pointer tracking): the
    // browser dispatches dragstart/drop instead of a plain mousedown-move-
    // mouseup sequence landing cleanly on the same target throughout, so
    // this is recorded as a SEPARATE signal and merged into whichever
    // gesture is currently open (or, if none is (some browsers suppress
    // the plain mouse sequence entirely for a real native drag), used on
    // its own in _finishDragGesture's dragstart/drop-only fallback path).
    document.addEventListener('dragstart', function (e) {
        try {
            _dragDropInfo = { html5: true, sourceEl: resolveSemanticTarget(e.target), dropEl: null };
        } catch (err) {}
    }, true);
    document.addEventListener('drop', function (e) {
        if (!_dragDropInfo) return;
        try {
            _dragDropInfo.dropEl = resolveSemanticTarget(e.target);
        } catch (err) {}
    }, true);

    function _finishDragGesture(state, upEvent) {
        // claimed and timestamped NOW, at mouseup - not when the (possibly
        // deferred, see the value-settle poll below) payload finally goes
        // out. The browser's own trailing 'click' fires in this same tick;
        // if the gesture were only marked as sent later, that click would
        // be recorded as a separate action ahead of the drag (CONFIRMED on
        // a native two-thumb range slider whose value didn't change on the
        // first poll), and the drag would be stamped after whatever the
        // user did next.
        _lastSentGestureId = state.gestureId;
        var dragTimestamp = new Date().toISOString();
        var dragPageUrl = window.location.href;
        var sourceEl = state.sourceEl || ((_preClickSnapshot && _preClickSnapshot.gestureId === state.gestureId)
            ? _preClickSnapshot.semanticEl
            : resolveSemanticTarget(upEvent.target));
        var sourceProfile = state.sourceProfile || ((_preClickSnapshot && _preClickSnapshot.gestureId === state.gestureId)
            ? _preClickSnapshot.locatorProfile
            : buildLocatorProfile(sourceEl));
        var sourceRect = state.sourceRect || sourceEl.getBoundingClientRect();
        var containerEl = sourceEl.parentElement || sourceEl;
        var containerRect = containerEl.getBoundingClientRect();

        var endX = upEvent.clientX, endY = upEvent.clientY;
        var dropEl = document.elementFromPoint(endX, endY);
        var dropSemanticEl = dropEl ? resolveSemanticTarget(dropEl) : null;
        var dropProfile = null;
        if (_dragDropInfo && _dragDropInfo.dropEl && _dragDropInfo.dropEl !== sourceEl) {
            dropProfile = buildLocatorProfile(_dragDropInfo.dropEl);
        } else if (dropSemanticEl && dropSemanticEl !== sourceEl && !sourceEl.contains(dropSemanticEl)) {
            dropProfile = buildLocatorProfile(dropSemanticEl);
        }

        var pathPoints = state.path.map(function (p) {
            return { dx: p.x - sourceRect.left, dy: p.y - sourceRect.top, t: p.t };
        });

        var valueBefore = state.valueBefore;
        var gestureIdForDrag = state.gestureId;
        var html5 = !!(_dragDropInfo && _dragDropInfo.html5);
        _dragDropInfo = null;

        // FIX 3 continuation (multi-thumb sliders): recorded once, at
        // mousedown, from the SAME element _findSliderThumbInfo identified
        // then (see its own docstring) - re-deriving it here from the
        // post-drag DOM would risk landing on a DIFFERENT thumb if the
        // drag itself reordered them (a sortable multi-handle range, say).
        var thumbInfo = state.thumbInfo;
        var thumbProfile = state.thumbProfile || null;
        var dragTrack = null;
        try { dragTrack = _findDragTrack(state, sourceRect, endX, endY); } catch (trackErr) {}

        function sendDragPayload(valueAfter) {
            var payload = {
                action_type: 'drag',
                html5: html5,
                source_target: sourceProfile,
                locator_profile: sourceProfile,
                drop_target: dropProfile,
                start_offset: { x: state.startX - sourceRect.left, y: state.startY - sourceRect.top },
                end_delta: { dx: endX - state.startX, dy: endY - state.startY },
                end_relative_to_container: { x: endX - containerRect.left, y: endY - containerRect.top },
                path: pathPoints,
                value_before: valueBefore || null,
                value_after: valueAfter || null,
                // multi-thumb sliders only - both null for a single-thumb
                // slider/plain drag, so replay's own thumb-specific
                // handling (see resolve_and_act's "drag" branch) is a
                // no-op for every recording made before this existed too.
                thumb_index: thumbInfo ? thumbInfo.index : null,
                thumb_total: thumbInfo ? thumbInfo.total : null,
                thumb_locator_profile: thumbProfile,
                // resolution-independent drag (see _findDragTrack) - null
                // when the source has no track-like ancestor
                track: dragTrack,
                expect: (valueBefore || valueAfter)
                    ? { type: 'value_change', before: valueBefore, after: valueAfter }
                    : { type: 'move', drop_target: !!dropProfile },
                bounding_box: { x: sourceRect.x, y: sourceRect.y, width: sourceRect.width, height: sourceRect.height },
                page_url: dragPageUrl,
                timestamp: dragTimestamp,
            };
            send(payload);
            _lastSentGestureId = gestureIdForDrag;
        }

        // give the site's own drop-handling a brief, bounded chance to
        // settle before capturing the AFTER value - mirrors this file's
        // other bounded-poll settle waits (never open-ended); a control
        // with no detectable value at all (valueBefore === null) skips
        // straight to sending, since there's nothing to wait for.
        if (!valueBefore) {
            sendDragPayload(null);
            return;
        }
        var pollDeadline = Date.now() + DRAG_VALUE_SETTLE_TIMEOUT_MS;
        (function pollForSettledValue() {
            var current = _captureDragValueSnapshot(sourceEl, thumbInfo);
            var changed = current && JSON.stringify(current) !== JSON.stringify(valueBefore);
            if (changed || Date.now() >= pollDeadline) {
                sendDragPayload(current);
            } else {
                setTimeout(pollForSettledValue, DRAG_VALUE_SETTLE_POLL_MS);
            }
        })();
    }

    window.addEventListener('mouseup', function (e) {
        var state = _dragState;
        _dragState = null;
        if (!state || state.maxDist <= DRAG_MOVE_THRESHOLD_PX || !e.isTrusted) return;
        try {
            _finishDragGesture(state, e);
        } catch (dragErr) {
            debugLog('drag gesture failed to record', dragErr && dragErr.message);
        }
    }, true);

    window.addEventListener('click', afqaClickHandlerRef = function (afqaRawEvt) {
        var e = afqaInnerEvent(afqaRawEvt);          // the innermost real target (shadow DOM included)
        afqaClickSeenAt = Date.now();
        // PICK ELEMENT MODE - a completely separate feature (Recording
        // Editor's "Pick Element" button) from normal recording, riding
        // on this SAME injected script since it needs the exact same
        // buildLocatorProfile() this file already has, unchanged. Only
        // ever active when recorder/pick_element.py's own init script
        // explicitly set window.__afqaPickMode = true on this page - for
        // every normal recording session that flag is simply never set,
        // so this branch never runs and everything below (dedup, label-
        // cascade, submit-suppression, buildProfile, send()) behaves
        // exactly as it always has. Reports the clicked element's own
        // locator profile back to Python via window.pickResult (exposed
        // by pick_element.py, not recordAction) and prevents the click
        // from actually activating whatever was clicked - the user is
        // choosing a locator, not performing the recorded flow.
        //
        // CAPTURE-ONLY GUARANTEE: this whole listener is registered with
        // useCapture=true (see the closing "}, true)" this function ends
        // with, far below) - the ONLY 'click' listener this file ever
        // adds to document. Capture-phase listeners on document fire
        // FIRST in the entire dispatch sequence, before the event even
        // reaches the clicked element, which is before ANY bubble-phase
        // listener the site's own JS could have attached (React/Vue
        // event delegation, an inline onclick, a directly-bound
        // handler - all bubble by default, the overwhelming common
        // case). This script itself is also guaranteed to be the first
        // script that runs on the page at all (injected via Playwright's
        // add_init_script, which always executes before the page's own
        // bundle), so even a site that registers its OWN capture-phase
        // document listener can't win a same-node registration-order
        // race against this one. preventDefault() suppresses the
        // browser's own default action (navigation, form submit,
        // checkbox toggle, ...); stopImmediatePropagation() (stronger
        // than stopPropagation() - also blocks any OTHER listener on
        // this SAME node/phase, not just ones on other elements) is the
        // deliberate belt-and-braces on top of that, so nothing else -
        // not even another capture-phase document listener - gets a
        // chance to react to this click while pick mode is on.
        if (window.__afqaPickMode) {
            e.preventDefault();
            e.stopImmediatePropagation();
            // DRAG-SELECT: a real drag was just handled entirely by the
            // mouseup listener above (single xpath for the whole group
            // already sent) - the 'click' the browser fires right after
            // that same mouseup must be swallowed here, not run through
            // the single-element pick logic below a second time.
            if (window.__afqaJustDragSelected) {
                window.__afqaJustDragSelected = false;
                return;
            }
            // already locked onto an earlier click (or drag-select) - a
            // further plain click (not a double click) while locked is
            // just noise (a stray click, or the first half of what turns
            // out to be a double click below) and must NOT silently
            // re-lock onto something else out from under the user; only
            // the dblclick handler further down this file is allowed to
            // release it.
            if ((window.__afqaPickIsLocked && window.__afqaPickIsLocked()) ||
                (window.__afqaPickIsMultiLocked && window.__afqaPickIsMultiLocked())) {
                return;
            }
            try {
                // e.target here is the OVERLAY itself (it's the topmost
                // element at every point on screen while picking, by
                // design - see _afqaSetupPickOverlay's own comment) - the
                // real element the user meant to click is, in order:
                // (1) whatever the hover highlight is CURRENTLY showing
                //     (__afqaPickLastHovered, kept live by the overlay's
                //     own mousemove handler above) - the exact element the
                //     user visually confirmed before clicking;
                // (2) a fresh elementsFromPoint() read at this exact click
                //     position, for the rare case a click fires with no
                //     preceding hover move at all (e.g. a synthetic/
                //     assistive-tech click);
                // (3) e.target itself, only as the final fallback.
                // Never trusts e.target directly as anything but that
                // last resort.
                var realEl = window.__afqaPickLastHovered ||
                    (window.__afqaPickRealElementAt && window.__afqaPickRealElementAt(e.clientX, e.clientY)) ||
                    e.target;
                // LARGE-CONTAINER WARNING: a picked element taller than
                // the viewport is almost always a wrapper the user meant
                // to hover THROUGH to something smaller inside it, not
                // the actual intended target - locking onto it anyway
                // (a whole page-length product-listing container, say)
                // produces a technically-valid but practically useless
                // locator. Purely advisory: still locks and reports the
                // real profile below (a genuinely large container IS
                // occasionally the real intent - a "the whole results
                // grid is visible" check, for instance), just flags it
                // so the modal can steer the user toward a smaller
                // element instead of silently accepting it.
                var largeContainer = false;
                try {
                    var lcRect = realEl.getBoundingClientRect();
                    largeContainer = lcRect.height > window.innerHeight * 1.5;
                } catch (eLc) {}
                // CONFIRMED REAL BUG (found via this item's own isolated
                // svg test, not hypothetical): normal recording's own
                // buildProfile() passes getCheckboxAccessibleName()'s
                // nearby-label-climbing result as accNameOverride for a
                // checkbox-style target, which is exactly what lets
                // xPath()'s new svg/icon tier (and tier 6b's existing
                // label-anchored tiers) find something to anchor an
                // icon-only element (a bare <svg><path/></svg> tick mark,
                // with no text/aria-label of its own) on at all. Pick
                // mode's own click handler used to just call
                // buildLocatorProfile(realEl) with no override, so
                // accessibleName(realEl) alone (empty for a bare svg/
                // path) was all xPath() ever saw here - the label-
                // anchored tiers never even got a chance to try,
                // regardless of how good they are. getCheckboxAccessible
                // Name()'s own label-finding logic isn't actually
                // checkbox-specific (label/parent-label/nearby-row-text
                // climbing generalizes to any element), so reusing it
                // here - always, not just for actual checkboxes, since
                // pick mode doesn't know in advance what kind of control
                // was clicked - costs nothing when accessibleName(realEl)
                // already found something real (that's tried FIRST) and
                // fixes exactly this gap when it didn't.
                var pickAccName = accessibleName(realEl) || getCheckboxAccessibleName(realEl, realEl);
                var profile = buildLocatorProfile(realEl, pickAccName);
                // FOLLOW-UP FIX (Part 4a): added to this SAME payload, no
                // new channel - see _afqaComputeElementLabelInfo's own
                // docstring for the confirmed real bug this fixes.
                try {
                    var _labelInfo = _afqaComputeElementLabelInfo(realEl);
                    profile.element_label = _labelInfo.element_label;
                    profile.element_kind = _labelInfo.element_kind;
                    profile.element_section = _labelInfo.element_section;
                } catch (eLabelInfo) {
                    profile.element_label = '';
                    profile.element_kind = 'element';
                    profile.element_section = '';
                }
                if (largeContainer) {
                    profile.large_container = true;
                    profile.large_container_message = 'You picked a large container, hover a smaller element';
                }
                // match-count feedback (Katalon Object Spy-style "Found:
                // N of N") - evaluated HERE, against the live page,
                // right while the xpath is still fresh, rather than a
                // separate round-trip later. -1 (not 0) signals "this
                // xpath itself couldn't even be evaluated" (a malformed
                // expression), distinct from a genuine zero-match result.
                //
                // Same cross-boundary gap as xpathIsUnique() inside
                // xPath() (see its own comment): a shadow-DOM element's
                // xpath can never be verified via document.evaluate() at
                // all, and an iframe-internal element needs evaluating
                // against ITS OWN document, not the top one, or this
                // always reads as zero matches regardless of whether the
                // xpath is actually correct. Mirrors that same fix here,
                // since this is a separate document.evaluate() call, not
                // a shared helper.
                try {
                    if (realEl.getRootNode() instanceof ShadowRoot) {
                        // unverifiable via XPath at all - id presence is
                        // the best honest signal available (see
                        // cross_boundary on the profile itself for the
                        // UI-facing warning)
                        profile.match_count = profile.id ? 1 : -1;
                    } else {
                        var evalDoc = realEl.ownerDocument || document;
                        var xpathResult = evalDoc.evaluate(
                            profile.xpath, evalDoc, null,
                            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                        );
                        profile.match_count = xpathResult.snapshotLength;
                    }
                } catch (xpathErr) {
                    profile.match_count = -1;
                }
                // PICK-MODE ONLY - buildXpathCandidates() runs a few
                // extra document.evaluate() probes on top of xPath()'s
                // own, deliberately NOT folded into buildLocatorProfile()
                // itself (that function also builds the profile for
                // every ORDINARY recorded click/fill/etc - adding this
                // extra work there would slow down normal recording for
                // a feature only Pick Element needs). Lets the Recording
                // Editor show a choice instead of silently committing to
                // whichever one xPath() alone decided was best.
                try {
                    profile.xpath_candidates = buildXpathCandidates(realEl, profile.text, 3);
                } catch (candErr) {
                    profile.xpath_candidates = [profile.xpath];
                }
                // stable/weak tag per candidate, same order as
                // xpath_candidates above - a NEW, OPTIONAL field
                // (recording_editor.html falls back to no tag at all if
                // it's ever missing), never changes xpath_candidates
                // itself or which one is pre-selected.
                try {
                    profile.xpath_candidates_confidence = profile.xpath_candidates.map(classifyXpathConfidence);
                } catch (confErr) {
                    profile.xpath_candidates_confidence = [];
                }
                if (window.__afqaPickLock) window.__afqaPickLock(realEl);
                // LATENCY INSTRUMENTATION (always on - see pick_element.py's
                // matching [pick-timing] lines): timestamps the exact
                // moment of the lock and the exact moment the binding call
                // is dispatched, so a real run's end-to-end timeline
                // (lock -> Python receives it -> dashboard shows it) can be
                // reconstructed from the two logs together.
                console.log('[pick-timing] locked_js t=' + Date.now());
                window.pickResult(JSON.stringify(profile));
                console.log('[pick-timing] pickResult_dispatched t=' + Date.now());
            } catch (err) {
                // pickResult binding not ready yet, or buildLocatorProfile
                // threw on an unusual element - nothing more to do here,
                // the Python side's own timeout covers this
            }
            return;
        }
        // isTrusted is false for any event dispatched by page JS itself
        // (el.click(), a framework's own synthetic event, etc.) - only
        // genuine OS-level user input should ever become a recorded
        // action, never something the website's own code triggered
        if (!e.isTrusted) {
            debugLog('DISCARDED click on', debugDescribeTarget(e.target), '- reason: not trusted (isTrusted=false)');
            return;
        }
        _recentClick = { el: e.target, time: Date.now() };
        _recentClicks.push(_recentClick); if (_recentClicks.length > 8) _recentClicks.shift();
        if (
            suppressAutoSubmitUntil && Date.now() <= suppressAutoSubmitUntil &&
            isSubmitTrigger(e.target) &&
            isSameSuppressedForm(e.target.closest ? e.target.closest('form') : null)
        ) {
            debugLog('DISCARDED click on', debugDescribeTarget(e.target), '- reason: suppressed as an Enter-triggered submit echo');
            return;
        }

        // everything below reads a real, trusted click's own DOM shape
        // (resolveSemanticTarget's ancestor walk, buildProfile's
        // attribute/text/cssPath/xPath inspection) - an unusual element
        // structure on any given site can make ANY of that throw, and an
        // uncaught exception here would silently abort the WHOLE
        // listener with no trace: the click never gets buffered, never
        // gets sent, and never shows up as an error anywhere a person
        // recording would see it. That is a strictly worse failure mode
        // than a slightly-less-precise fallback capture, so this is
        // wrapped end to end - a genuine trusted click can no longer
        // vanish from the recording without a trace, regardless of what
        // site-specific DOM quirk triggered the failure.
        try {
            flushFocusedFieldIfNeeded();

            var semanticEl = resolveSemanticTarget(e.target);

            // FIX 1.1 (gesture id) - a second native click firing for the
            // SAME physical mousedown (a <label> forwarding to its
            // control, whether wrapped or associated via for=, or an
            // equivalent framework pattern) is recognized purely by
            // gesture id here, with no dependency on DOM containment or
            // semantic-target resolution agreeing between the two events
            // at all - a broader, more principled net than the
            // semantic-element check just below, which stays as a
            // second, independent guard for a genuine same-gesture
            // cascade this one might not otherwise structurally expect
            // (see its own comment).
            if (_currentGestureId === _lastSentGestureId) {
                debugLog(
                    'DISCARDED click on', debugDescribeTarget(e.target),
                    '- reason: gesture-id dedup, another click-family action',
                    'already sent for this same physical mousedown (gesture',
                    _currentGestureId + ')'
                );
                return;
            }

            if (
                semanticEl === lastSemanticClickEl &&
                e.target !== lastSemanticClickRawTarget &&
                (Date.now() - lastSemanticClickTime) < LABEL_CASCADE_DEDUP_MS
            ) {
                debugLog(
                    'DISCARDED click on', debugDescribeTarget(e.target),
                    '- reason: label-cascade dedup, same semantic element',
                    debugDescribeTarget(semanticEl),
                    'as a click', (Date.now() - lastSemanticClickTime) + 'ms ago',
                    '(window=' + LABEL_CASCADE_DEDUP_MS + 'ms)'
                );
                return;
            }

            if (pendingClick && pendingClick.target === e.target) {
                // second click of a double-click - let the dblclick handler
                // below record the real action, this pair doesn't get its own
                debugLog(
                    'DISCARDED click on', debugDescribeTarget(e.target),
                    '- reason: treated as the second click of a double-click,',
                    'deferring to the dblclick handler instead'
                );
                clearTimeout(pendingClick.timer);
                pendingClick = null;
                return;
            }
            // a pending click on a DIFFERENT element wasn't part of a double
            // click after all - it was just a normal single click, send it now
            flushPendingClick(e.target);

            // compares against the badge snapshot taken right after
            // whatever was captured last (see send() above) - placed
            // here, after flushPendingClick() has already run, so a
            // click that's about to be correctly flushed/sent right now
            // is never mistaken for one that was missed
            checkForMissedClick();

            lastSemanticClickEl = semanticEl;
            lastSemanticClickRawTarget = e.target;
            lastSemanticClickTime = Date.now();
            _lastSentGestureId = _currentGestureId;

            // BUG 1 / hover chain: emit an explicit hover step for EACH
            // trigger in the chain that revealed this click's target (see
            // _consumeHoverChain's own docstring for exactly when a link
            // qualifies), outermost first, immediately before the click's
            // own payload. Sent immediately, unbuffered (never held for
            // the double-click window the click itself gets) - each
            // one's own earlier timestamp is what keeps them ordered
            // before the click once Python-side sorts by timestamp
            // (Recorder.stop()), regardless of send order.
            var hoverTriggerChain = _consumeHoverChain(e.target);
            var hoverChainLocatorProfiles = [];
            // FIX 1.4 (postcondition): what this hover was actually FOR -
            // the eventual click target's own locator profile - recorded
            // once and attached to every link's own "expect" field, so
            // replay can verify each hover step's own reveal actually
            // happened (see resolve_and_act's hover dispatch) instead of
            // just trusting that .hover() not raising means it worked.
            var _revealExpectLp = null;
            try {
                _revealExpectLp = buildLocatorProfile(e.target);
            } catch (eExpectLp) {}
            for (var _hci = 0; _hci < hoverTriggerChain.length; _hci++) {
                var _hoverTrigger = hoverTriggerChain[_hci];
                try {
                    // the user cannot have hovered something that is not visible on screen: no hover step,
                    // and not part of the chain replay hovers
                    if (!afqaVisiblyOnScreen(_hoverTrigger)) {
                        debugLog('hover step NOT saved (trigger not visible on screen):', debugDescribeTarget(_hoverTrigger));
                        continue;
                    }
                    var _hoverLp = buildLocatorProfile(_hoverTrigger);
                    hoverChainLocatorProfiles.push(_hoverLp);
                    if (_clickedTriggersNow.indexOf(_hoverTrigger) !== -1) {
                        debugLog('hover step NOT saved (trigger was clicked, that click is its own step):', debugDescribeTarget(_hoverTrigger));
                        continue;
                    }
                    if (_sitePopupOf(_hoverTrigger)) {
                        debugLog('hover step NOT saved (inside a popup the site opened by itself):', debugDescribeTarget(_hoverTrigger));
                        continue;
                    }
                    var hoverRect = _hoverTrigger.getBoundingClientRect();
                    send({
                        action_type: 'hover',
                        value: null,
                        locator_profile: _hoverLp,
                        bounding_box: { x: hoverRect.x, y: hoverRect.y, width: hoverRect.width, height: hoverRect.height },
                        page_url: window.location.href,
                        timestamp: new Date().toISOString(),
                        expect: _revealExpectLp ? { type: 'reveal', revealed_locator_profile: _revealExpectLp } : null,
                    });
                    debugLog('EMITTED hover step for', debugDescribeTarget(_hoverTrigger), '- revealed', debugDescribeTarget(e.target));
                } catch (eHoverEmit) {
                    // never let hover-step emission break the click it precedes
                }
            }

            var payload = buildProfile(e.target, 'click', null);
            try {
                // a click inside an opened menu / popup: remember what opened it (replay opens it again if the
                // item is missing); then remember this click as the possible opener of the next one
                var ob = afqaOpenedByTrigger(e.target);
                if (ob) { payload.opened_by = ob.profile; payload.opened_by_name = ob.name; }
                afqaPrevClick = { el: e.target, profile: payload.locator_profile, time: Date.now() };
            } catch (eOpenedBy) {}
            try {
                // where inside the saved element the user clicked (replay clicks the same relative spot)
                var offEl = resolveSemanticActTarget(e.target);
                var offR = offEl && offEl.getBoundingClientRect ? offEl.getBoundingClientRect() : null;
                if (offR && offR.width > 0 && offR.height > 0 && typeof e.clientX === 'number' && typeof e.clientY === 'number') {
                    var xr = (e.clientX - offR.left) / offR.width, yr = (e.clientY - offR.top) / offR.height;
                    if (xr >= 0 && xr <= 1 && yr >= 0 && yr <= 1) payload.click_offset = { x_ratio: Math.round(xr * 1000) / 1000, y_ratio: Math.round(yr * 1000) / 1000 };
                }
            } catch (eClickOffset) {}
            try {
                // a click on a submitter: its form is submitted by this click (replay must not submit it again)
                var sbmt = afqaResolveSubmitter(e.target);
                if (sbmt) {
                    payload.submits_form = true;
                    payload.form_selector = cssPath(sbmt.form);
                    afqaLastSubmitterClick = { el: sbmt.el, form: sbmt.form, time: Date.now() };
                }
            } catch (eSubmitsForm) {}
            // FIX 1: a click on an element that only OPENS something (an
            // href="#"/javascript: link, or one declaring aria-haspopup/
            // aria-expanded/aria-controls) is a reveal trigger, not a
            // navigation - flagged so the saved recording treats it exactly
            // like hovering the same trigger (see repository.
            // normalize_reveal_steps).
            try {
                var _opEl = semanticEl || e.target;
                var _opA = _opEl.closest ? (_opEl.closest('a, button, [role=button], [role=menuitem]') || _opEl) : _opEl;
                var _opHref = _opA.tagName === 'A' ? (_opA.getAttribute('href') || '') : null;
                var _isFragOpen = _opHref !== null && (_opHref === '' || _opHref === '#' || /^javascript:/i.test(_opHref));
                var _declOpen = _opA.hasAttribute && (_opA.hasAttribute('aria-haspopup') || _opA.hasAttribute('aria-expanded') || _opA.hasAttribute('aria-controls'));
                if (_isFragOpen || _declOpen) payload.opener = true;
            } catch (eOpener) {}
            // ISSUE 2: optional fingerprint of the popup this click was made
            // inside (nearest dialog / aria-modal / <dialog> / large fixed or
            // absolute high-z-index ancestor). Replay uses it so a close step
            // is judged against THAT popup only, never "any overlay". Absent
            // when the click was not inside a popup.
            try {
                var _popFp = _popupFingerprintOf(semanticEl || e.target);
                if (_popFp) payload.popup_container = _popFp;
            } catch (ePop) {}
            // FIX 2.a/2.b (replay preconditions/resolve): the full chain
            // also travels WITH the click's own payload (not just as
            // separate hover steps) so replay can re-establish it
            // directly from this one action even if something upstream
            // ever strips/reorders the standalone hover steps - never
            // required to be non-empty; absent/empty means "no hover
            // chain was involved in reaching this click" exactly as
            // before.
            if (hoverChainLocatorProfiles.length) {
                payload.hover_chain = hoverChainLocatorProfiles;
            }
            debugLog(
                'BUFFERED click on', debugDescribeTarget(e.target),
                '(semantic target', debugDescribeTarget(semanticEl) + ')',
                '- will send in', DBLCLICK_WINDOW_MS + 'ms unless a dblclick follows'
            );
            _schedulePostClickObservation(payload, { submitLike: _isSubmitLike(e.target) });
            pendingClick = {
                target: e.target,
                payload: payload,
                timer: setTimeout(function () {
                    pendingClick = null;
                    send(payload);
                    debugLog(
                        'FLUSHED buffered click on', debugDescribeTarget(e.target),
                        '-> recorded as', payload.action_type,
                        '(normal', DBLCLICK_WINDOW_MS + 'ms timeout, no dblclick followed)'
                    );
                }, DBLCLICK_WINDOW_MS)
            };
        } catch (captureErr) {
            debugLog(
                'EXCEPTION building profile for click on', debugDescribeTarget(e.target),
                '- falling back to a minimal/coordinate-only capture:', String(captureErr)
            );
            // best-effort fallback: a raw coordinate is still real
            // evidence of where a genuine trusted click landed, even
            // when nothing above could be safely inspected. Sent
            // immediately (not buffered through pendingClick) since the
            // richer double-click disambiguation this function is built
            // around isn't available for a payload built this way anyway.
            //
            // whatever threw above almost certainly did so reading a JS
            // PROPERTY (.id, .className, a custom getter, a framework
            // proxy) - getAttribute() is a more fundamental, far less
            // likely to be intercepted DOM method, so it's tried here,
            // independently guarded, as a second chance at a real
            // locator instead of falling straight to coordinate-only
            var fallbackTag = null, fallbackId = null, fallbackCssPath = null;
            try {
                fallbackTag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : null;
            } catch (e1) { /* even tagName isn't safe to assume here */ }
            try {
                var rawId = (e.target && e.target.getAttribute) ? e.target.getAttribute('id') : null;
                if (rawId) {
                    fallbackId = '#' + rawId;
                    fallbackCssPath = (fallbackTag || '*') + '#' + rawId;
                }
            } catch (e2) { /* fall through with whatever we already have */ }

            try {
                send({
                    action_type: 'click',
                    value: null,
                    locator_profile: (fallbackId || fallbackTag) ? {
                        id: fallbackId,
                        css_path: fallbackCssPath,
                        tag: fallbackTag,
                        attributes: {}
                    } : null,
                    // a truly 0x0 box is deliberately SKIPPED by the
                    // replay engine's own bounding_box fallback tier
                    // ("occupies no space, nothing to click") - a 1x1
                    // placeholder centered on the real click point keeps
                    // this fallback capture genuinely replayable instead
                    // of silently unusable
                    bounding_box: (typeof e.clientX === 'number')
                        ? { x: e.clientX - 0.5, y: e.clientY - 0.5, width: 1, height: 1 }
                        : null,
                    click_strategy: 'force_click',
                    page_url: window.location.href,
                    timestamp: new Date().toISOString(),
                    capture_error: String((captureErr && captureErr.message) || captureErr)
                });
            } catch (sendErr) {
                // truly nothing more this listener can do
            }
        }
    }, true);

    window.addEventListener('dblclick', function (e) {
        // PICK ELEMENT MODE - releases a locked selection (see the
        // click handler's own pick-mode branch above for how it gets
        // locked in the first place) and resumes hover mode, so the
        // user can pick a different element after realizing the first
        // one was wrong. Only meaningful while something IS actually
        // locked - a double click with nothing locked yet has no lock
        // to release, and just falls through as a no-op here (the
        // single-click handler already dealt with both of its own
        // constituent clicks by the time this fires).
        if (window.__afqaPickMode) {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (window.__afqaPickIsLocked && window.__afqaPickIsLocked()) {
                window.__afqaPickRelease();
                try {
                    window.pickReleased && window.pickReleased();
                } catch (err) {
                    // pickReleased binding not ready - nothing more to do,
                    // the highlight has already visually released either way
                }
            } else if (window.__afqaPickIsMultiLocked && window.__afqaPickIsMultiLocked()) {
                // DRAG-SELECT: same release gesture, for a multi-pick
                // result instead of a single element - clears the green
                // outline boxes and resumes hover mode.
                window.__afqaReleaseMulti();
                try {
                    window.pickReleased && window.pickReleased();
                } catch (err) {
                    // pickReleased binding not ready - nothing more to do
                }
            }
            return;
        }
        if (!e.isTrusted) return;
        flushFocusedFieldIfNeeded();
        if (pendingClick) {
            clearTimeout(pendingClick.timer);
            pendingClick = null;
        }
        send(buildProfile(e.target, 'dblclick', null));
        debugLog('RESOLVED as dblclick on', debugDescribeTarget(e.target));
    }, true);

    // right-click: the browser only fires 'contextmenu' for the secondary
    // button, never 'click', so there's no disambiguation needed here
    window.addEventListener('contextmenu', function (e) {
        if (!e.isTrusted) return;
        flushFocusedFieldIfNeeded();
        flushPendingClick(e.target);
        send(buildProfile(e.target, 'right_click', null));
    }, true);

    // change fires once on blur/commit, not per keystroke - that's what
    // keeps typing from generating a huge pile of actions. But "type into
    // a search box then press Enter" often submits/navigates WITHOUT the
    // field ever blurring, so change never fires and the typed text gets
    // lost. sendFillIfChanged() is also called directly from keydown below
    // to flush the current value before that can happen; the dedup check
    // here (against the last value we actually sent) keeps both paths
    // from ever producing two fill actions for the same committed value.
    // WHO produced this field's current value: "user" when it is exactly
    // what the user's own trusted editing (keystrokes, paste, drop, IME
    // composition - each ends in a trusted input event, see the listeners
    // below) last left in the box, "page" when the value is something else
    // - set by the page itself after a click, programmatically, or by an
    // animation that types into the box. A page-generated value must be
    // saved as an EXPECTATION of what the page puts there, never as a Fill
    // replay would have to type on top of the page doing it too.
    function valueSourceOf(el) {
        var current = el.value;
        if (el.__afqaUserValue !== undefined && el.__afqaUserValue === current) return 'user';
        return 'page';
    }

    // A value the PAGE put in the box (an animation typing a prompt, a
    // click that fills a field) is never recorded as ANY step: not a Fill
    // (replay would type on top of the page doing it too), and not a
    // validation - the recorder only ever records what the user did, and a
    // validation exists only when the user adds one deliberately. Replay
    // handles such a field on its own (it waits for the page to finish
    // changing it before any Fill, and never types into it meanwhile).
    function buildFieldValueAction(el, current) {
        var payload = buildProfile(el, 'fill', current);
        payload.value_source = 'user';
        try {
            el.__afqaFilledSinceFocus = true;
            el.__afqaRecordedValue = current;       // a Fill with this value exists for this focus session
            if (el.tagName === 'INPUT') {
                payload.input_type = (el.type || '').toLowerCase();                      // the type NOW
                payload.focus_type = (el.__afqaFocusType || '').toLowerCase() || null;   // the type when it gained focus
            }
        } catch (eDt) {}
        return payload;
    }

    // ---- native date / time inputs, and a generic "value changed while focused" safety net ----
    // A native date / time box keeps value "" until the date is complete, and then holds the ISO form
    // (never the text shown on screen). One Fill per field per focus, with the final value.
    var DATETIME_INPUT_TYPES = ['date', 'datetime-local', 'month', 'week', 'time'];
    function isDateTimeInput(el) {
        try { return !!el && el.tagName === 'INPUT' && DATETIME_INPUT_TYPES.indexOf((el.type || '').toLowerCase()) !== -1; } catch (e) { return false; }
    }

    function sendFillIfChanged(el) {
        // single authoritative guard for every call site below (change,
        // the Enter/Tab flush, and the blur/focus-based fallback further
        // down) - a submit/button-style <input> (or any other non-text-
        // entry control) must never become a 'fill' just because it's
        // still, technically, an <input> element - see isTextLikeField.
        if (!isTextLikeField(el)) return;
        const current = el.value;
        if (el.__afqaLastSentValue === current) return;
        el.__afqaLastSentValue = current;
        // (a native date / time box the user edited holds the browser's own value, never a page-generated one)
        // (a field the user edited - trusted typing during this focus - holds the user's value, whatever the page did to it)
        if (valueSourceOf(el) === 'page' && !el.__afqaUserTouched) return;   // page-generated: no step at all
        send(buildFieldValueAction(el, current));
    }

    // autofill (browser-saved credentials, password managers, a site's own
    // "remember me" restore) and some non-standard value-setting paths
    // frequently don't fire the input/change events the listeners above
    // rely on - the field ends up with a real value on screen (and the
    // page's own logic sees it fine, since most such flows read el.value
    // directly rather than depending on the event) but no fill action ever
    // gets recorded, because nothing here was ever told it happened. This
    // catches that value the same way change already does - by reading
    // el.value - just triggered by a different, more reliable signal that
    // doesn't depend on any particular DOM event having fired for it: the
    // field losing focus. sendFillIfChanged's own dedup (against
    // __afqaLastSentValue) means this is a genuine no-op whenever change
    // already captured the same value, so a normal fill never gets
    // recorded twice - this only ever adds the ONE fill that would
    // otherwise have been silently missing.
    // input types that are never genuine text entry, even though they're
    // still <input> elements - a submit/button/reset/image control is a
    // trigger the user clicks (already correctly recorded as its own
    // 'click' action by the click listener below, on any site), not
    // something typed into; checkbox/radio/file/color/range are likewise
    // non-textual controls already handled elsewhere. Anything NOT in
    // this list (text, search, email, tel, url, password, number, date,
    // etc.) is genuine text entry and still gets treated as fill-worthy.
    var NON_TEXT_ENTRY_INPUT_TYPES = [
        'checkbox', 'radio', 'submit', 'button', 'reset', 'image', 'file', 'color', 'range',
    ];

    function isTextLikeField(el) {
        if (!el || !el.tagName) return false;
        const tag = el.tagName.toLowerCase();
        if (tag !== 'input' && tag !== 'textarea') return false;
        const inputType = (el.getAttribute('type') || 'text').toLowerCase();
        return NON_TEXT_ENTRY_INPUT_TYPES.indexOf(inputType) === -1;
    }

    var lastFocusedTextField = null;
    var afqaLastTextBox = null;

    // [DIAG-REC] one line per form-field event, only when the recorder diagnostics flag is on
    // (AUTOFLOW_DEBUG=1 or DEBUG_RECORDER=1 when the recorder starts); never raises, never changes a result
    function afqaRecLog(evtName, el, action) {
        try {
            if (!window.__AFQA_REC_DIAG__) return;
            var d = new Date();
            var ts = d.toTimeString().slice(0, 8) + '.' + ('00' + d.getMilliseconds()).slice(-3);
            console.log('[DIAG-REC] ' + ts + ' ' + evtName + ' type=' + (el && el.type) + ' value=' + (el && el.value) +
                ' userEdited=' + (!!(el && el.__afqaUserTouched)) + ' action=' + action);
        } catch (eRecLog) {}
    }

    // a field the user can type into: input / textarea except checkbox, radio, button, submit, file ...
    function afqaIsSessionField(el) {
        try { return !!el && el.tagName && isTextLikeField(el); } catch (e) { return false; }
    }

    // FOCUS SESSION: when a field gains focus, remember its value and type; it is "user-edited" once a trusted
    // key press that edits, input, change, paste or drop happens on it - whatever its type is at that moment.
    // ONE Fill is committed with the CURRENT value and type (and the type at focus) when the field loses focus,
    // when the next action is about to be recorded, or when the page goes away - never an intermediate value.
    document.addEventListener('focusin', function (e) {
        lastFocusedTextField = isTextLikeField(e.target) ? e.target : null;
        try {
            // the last text box the user was in - kept when the focus moves on to a button (see the reply watch)
            if (lastFocusedTextField || (e.target && (e.target.isContentEditable || (e.target.getAttribute && e.target.getAttribute('role') === 'textbox')))) {
                afqaLastTextBox = e.target;
            }
        } catch (eLastBox) {}
        try {
            var f0 = e.target;
            if (f0 && f0.tagName && (isTextLikeField(f0) || f0.tagName.toLowerCase() === 'select')) {
                f0.__afqaFocusValue = f0.value;
                f0.__afqaFocusType = f0.type || '';
                try { f0.__afqaIdleFp = afqaChatFp(f0); } catch (eIdleFp) {}
                f0.__afqaFilledSinceFocus = false;
                f0.__afqaRecordedValue = undefined;
                f0.__afqaUserTouched = false;
                f0.__afqaTypedLatest = undefined;
                afqaRecLog('focusin', f0, 'none (focus session started)');
            }
        } catch (eFocusIn) {}
    }, true);

    // keys that edit a field's value (a character, Backspace, Delete); Enter / Tab / arrows / Escape do not
    function afqaIsEditingKey(ev) {
        try { return !!ev && typeof ev.key === 'string' && (ev.key.length === 1 || ev.key === 'Backspace' || ev.key === 'Delete'); } catch (e) { return false; }
    }
    ['keydown', 'input', 'change', 'paste', 'drop'].forEach(function (evtName) {
        document.addEventListener(evtName, function (e) {
            try {
                if (!e.isTrusted || !e.target || !e.target.tagName) return;
                if (evtName === 'keydown' && !afqaIsEditingKey(e)) return;
                e.target.__afqaUserTouched = true;
                if ((evtName === 'input' || evtName === 'change') && (afqaIsSessionField(e.target) || e.target.tagName.toLowerCase() === 'select')) {
                    afqaRecLog(evtName, e.target, 'none (edit noted)');
                }
            } catch (eTouch) {}
        }, true);
    });

    // COMMIT the focus session of one field. Conditions: user-edited, a non-empty value that differs from the
    // value at focus, and no Fill with this same final value already recorded in this session. A value committed
    // here is never dropped by the page-generated check: the user's own typing produced it.
    function afqaCommitFieldSession(el, reason, beforeTimestamp) {
        var outcome = 'skipped: not a field';
        try {
            if (!el || !el.tagName || !el.isConnected) { outcome = 'skipped: field gone'; return false; }
            var isSelect = el.tagName.toLowerCase() === 'select';
            if (!isSelect && !afqaIsSessionField(el)) { return false; }
            if (!el.__afqaUserTouched) { outcome = 'skipped: not edited by the user'; return false; }
            var cur = el.value;
            // the site emptied the box right after the prompt was sent: the user's last typed value is what counts
            if ((cur === undefined || cur === null || cur === '') && el.__afqaTypedLatest) cur = el.__afqaTypedLatest;
            if (cur === undefined || cur === null || cur === '') { outcome = 'skipped: empty value'; return false; }
            if (cur === el.__afqaFocusValue) { outcome = 'skipped: same as at focus'; return false; }
            if (el.__afqaRecordedValue === cur || (isSelect && el.__afqaFilledSinceFocus)) { outcome = 'skipped: already recorded'; return false; }
            var beforeMs = beforeTimestamp ? Date.parse(beforeTimestamp) : NaN;
            // an action that happened before the last keystroke has nothing to do with the typed value
            if (!isNaN(beforeMs) && el.__afqaLastInputMs > beforeMs) { outcome = 'skipped: action precedes the typing'; return false; }
            if (isSelect) {
                el.__afqaFilledSinceFocus = true;
                outcome = 'committed Select (' + reason + ')';
                send(buildProfile(el, 'select', cur));
                return true;
            }
            el.__afqaLastSentValue = cur;
            var payload = buildFieldValueAction(el, cur);
            if (!isNaN(beforeMs)) payload.timestamp = new Date(beforeMs - 1).toISOString();
            outcome = 'committed Fill (' + reason + ')';
            send(payload);
            return true;
        } catch (eCommit) {
            outcome = 'skipped: error ' + eCommit;
            return false;
        } finally {
            afqaRecLog('commit:' + reason, el, outcome);
        }
    }

    // the field loses focus
    document.addEventListener('focusout', function (e) {
        try {
            afqaRecLog('focusout', e.target, 'checking commit');
            afqaCommitFieldSession(e.target, 'focusout');
        } catch (eFocusOut) {}
    }, true);

    // a pointer press elsewhere comes BEFORE the field's blur: commit first, so the Fill is saved before the click
    ['pointerdown', 'mousedown'].forEach(function (evtName) {
        document.addEventListener(evtName, function (e) {
            try {
                if (!e.isTrusted) return;
                var f1 = lastFocusedTextField || lastTypedField;
                if (!f1 || f1 === e.target || (f1.contains && f1.contains(e.target))) return;
                afqaCommitFieldSession(f1, evtName);
            } catch (ePress) {}
        }, true);
    });

    // blur doesn't bubble, but a capture-phase listener on document still
    // sees every blur on its way down to the actual target - same pattern
    // every other listener in this file already uses
    document.addEventListener('blur', function (e) {
        if (!isTextLikeField(e.target)) return;
        if (!e.target.value) return;
        sendFillIfChanged(e.target);
    }, true);

    // defense-in-depth for widgets that manage their own visual "focus"
    // state without a real native blur ever firing on the underlying
    // field (some component libraries render the actual editable element
    // detached from where focus visually appears to be) - right before
    // ANY click is recorded, flush whatever field this page last put
    // focus into if it still has an uncaptured value. This is exactly the
    // "about to click Sign in/submit with a filled-but-uncaptured field"
    // case, but written generically: it runs before every click, not a
    // detected "submit-style" one, since a click that turns out to
    // navigate/submit can't be told apart from any other click in
    // advance, and a plain click on an unrelated element makes this a
    // harmless no-op (sendFillIfChanged's own dedup already covers a
    // field that blur already flushed normally).
    function flushFocusedFieldIfNeeded() {
        var el = lastFocusedTextField;
        if (el && el.isConnected && el.value) {
            sendFillIfChanged(el);
        }
    }

    // ---- typed-but-uncommitted value: extra flush triggers -----------------
    // Enter/Tab, change, blur and "right before a click" already commit a
    // typed value (above). What was still missing: paths where none of
    // those happens before the page or the recording goes away - the page
    // navigating/unloading, the tab being closed, Stop Recording - and any
    // other kind of action being recorded while the field still holds
    // typed text (see send()). Only a value the user actually TYPED counts
    // (a trusted input event on that field), so a field that was merely
    // clicked, or that holds a pre-filled value nobody touched, never gets
    // a Fill step from these triggers; and the same dedup as every other
    // path (__afqaLastSentValue) means a value Enter/blur already
    // committed is never recorded a second time.
    var lastTypedField = null;
    var __afqaFlushingFill = false;

    document.addEventListener('input', function (e) {
        if (!e.isTrusted || !isTextLikeField(e.target)) return;
        e.target.__afqaUserTyped = true;
        e.target.__afqaLastInputMs = Date.now();
        // what the user's own edit just left in the box - compared against
        // the value at send time to tell user input from page-set input
        e.target.__afqaUserValue = e.target.value;
        e.target.__afqaTypedLatest = e.target.value;      // what the user's own typing left in the box (a site clearing it does not change this)
        lastTypedField = e.target;
    }, true);

    // the user-driven edit paths (keystroke, paste, drop, IME composition):
    // each ends in a trusted 'input' event handled above; a late
    // compositionend also re-reads the value, since some IMEs commit the
    // final text there. Programmatic changes dispatch none of these.
    ['compositionend', 'paste', 'drop'].forEach(function (evtType) {
        document.addEventListener(evtType, function (e) {
            if (!e.isTrusted || !isTextLikeField(e.target)) return;
            var target = e.target;
            setTimeout(function () {
                if (target.isConnected) target.__afqaUserValue = target.value;
            }, 0);
        }, true);
    });

    function flushTypedFieldIfPending(trigger, beforeTimestamp) {
        var el = lastTypedField;
        if (__afqaFlushingFill || !el || !el.isConnected || !el.__afqaUserTyped) return false;
        var current = el.value;
        if (!current && el.__afqaTypedLatest) current = el.__afqaTypedLatest;   // the site cleared the box after the send
        if (!current || el.__afqaLastSentValue === current) return false;
        var beforeMs = beforeTimestamp ? Date.parse(beforeTimestamp) : NaN;
        // an action that HAPPENED before the last keystroke (e.g. the click
        // that focused this field, which is only sent after its
        // double-click window) has nothing to do with this typed value
        if (!isNaN(beforeMs) && el.__afqaLastInputMs > beforeMs) return false;
        __afqaFlushingFill = true;
        try {
            el.__afqaLastSentValue = current;
            if (valueSourceOf(el) === 'page' && !el.__afqaUserTouched) return false;   // page-generated: no step at all
            var payload = buildFieldValueAction(el, current);
            // ordered strictly before the action whose recording triggered
            // this flush (the saved recording is sorted on timestamp)
            if (!isNaN(beforeMs)) payload.timestamp = new Date(beforeMs - 1).toISOString();
            send(payload);
        } finally {
            __afqaFlushingFill = false;
        }
        return true;
    }

    // page navigating away / unloading / tab closing
    window.addEventListener('pagehide', function () {
        flushTypedFieldIfPending('navigate-away:pagehide');
        try { afqaCommitFieldSession(lastFocusedTextField, 'pagehide'); } catch (ePh) {}
    }, true);
    window.addEventListener('beforeunload', function () {
        flushTypedFieldIfPending('navigate-away:beforeunload');
        try { afqaCommitFieldSession(lastFocusedTextField, 'beforeunload'); } catch (eBu) {}
    }, true);

    // Stop Recording (record_session.py's stop() calls this in every open
    // page/frame before it switches recording off)
    window.__afqaFlushPendingFill = function (trigger) {
        var flushedTyped = flushTypedFieldIfPending(trigger || 'stop-recording');
        try {
            // a reply still being watched is saved as it is now
            var pendingWatches = afqaReplyFinishers.splice(0);
            pendingWatches.forEach(function (f) { f(); });
            if (pendingWatches.length) flushedTyped = true;
        } catch (eFinishReplies) {}
        try { if (afqaCommitFieldSession(lastFocusedTextField, trigger || 'stop-recording')) return true; } catch (eStopCommit) {}
        return flushedTyped;
    };

    document.addEventListener('change', function (e) {
        if (!e.isTrusted) return;
        const tag = e.target.tagName.toLowerCase();
        if (tag === 'select') {
            // dropdowns are their own action type, not a "fill" - replay
            // needs page.select_option(), not page.fill()
            try { e.target.__afqaFilledSinceFocus = true; } catch (eSel) {}
            send(buildProfile(e.target, 'select', e.target.value));
            return;
        }
        // a native date / time box fires change on every valid edit while the date is still being typed:
        // the Fill is sent once, with the final value, when it loses focus (or the next action is recorded)
        if (isDateTimeInput(e.target)) {
            try {
                e.target.__afqaUserTouched = true;
                e.target.__afqaUserTyped = true;
                lastTypedField = e.target;
            } catch (eDtChange) {}
            return;
        }
        if (tag === 'input' || tag === 'textarea') {
            // checkboxes/radios/submit-or-button-style inputs already get
            // recorded as a plain 'click' above (that's the correct
            // replay action for them too, on any site) - only genuine
            // text-entry inputs need their committed value captured;
            // sendFillIfChanged itself also guards this (see
            // isTextLikeField), this pre-check just avoids the call
            // entirely for the common case.
            sendFillIfChanged(e.target);
        }
    }, true);

    document.addEventListener('submit', function (e) {
        if (!e.isTrusted) return;
        // e.target on a 'submit' event IS the <form> itself
        if (suppressAutoSubmitUntil && Date.now() <= suppressAutoSubmitUntil && isSameSuppressedForm(e.target)) {
            return;
        }
        try {
            // the form was submitted by a click on its submit button that was just recorded: that click
            // already stands for the submit - no separate step. Enter in a field, a script's submit() or any
            // submit without such a click is recorded as before.
            var lsc = afqaLastSubmitterClick;
            if (e.submitter && lsc && lsc.form === e.target && lsc.el === e.submitter && (Date.now() - lsc.time) < 2000) {
                afqaLastSubmitterClick = null;
                return;
            }
            // the same echo when the site submits the form ITSELF a moment after the click (it cancels the
            // native submit and calls requestSubmit() later, so e.submitter is empty, or it re-renders the
            // button so the node differs): the latest real click - still held in the double-click window or
            // just sent - was on a control inside this form (not a text field, whose Enter is handled above).
            var rc = _recentClick, nowMs = Date.now();
            var clickInForm = function (el) {
                try { return !!el && (e.target.contains(el) || (el.form && el.form === e.target)); } catch (eIn) { return false; }
            };
            var lscEcho = lsc && (nowMs - lsc.time) < 2000 && (!rc || rc.time <= lsc.time) &&
                          (lsc.form === e.target || clickInForm(lsc.el));
            var rcEcho = rc && (nowMs - rc.time) < 2000 && clickInForm(rc.el) && !isTextLikeField(rc.el);
            if (lscEcho || rcEcho) {
                afqaLastSubmitterClick = null;
                try {
                    // the click that caused it now carries the submit (replay must not submit the form again)
                    var heldClick = pendingClick && rc && pendingClick.target === rc.el ? pendingClick.payload : null;
                    if (heldClick && !heldClick.submits_form) {
                        heldClick.submits_form = true;
                        heldClick.form_selector = cssPath(e.target);
                    }
                } catch (eHeld) {}
                return;
            }
        } catch (eSubmitEcho) {}
        send(buildProfile(e.target, 'submit', null));
    }, true);

    // ---- browser history navigation: Back / Forward -------------------------------------
    // EVERY traversal of the session history is reported as its own message (never merged with
    // another, never dropped because it lands on a page seen before): a document loaded by a
    // traversal (navigation type back_forward), a same-document traversal (single-page app), and a
    // back-forward-cache restore (pageshow persisted). The direction comes from the position of the
    // history entry (Navigation API) compared with the position remembered for this tab.
    (function () {
        if (window.top !== window) return;
        var KEY = '__afqa_nav_idx';
        var lastUrl = null, lastAt = 0;
        function entryIndex() {
            try { return (window.navigation && window.navigation.currentEntry) ? window.navigation.currentEntry.index : null; } catch (e) { return null; }
        }
        function stored() {
            try { var v = sessionStorage.getItem(KEY); return v === null ? null : parseInt(v, 10); } catch (e) { return null; }
        }
        function remember(i) {
            try { if (i !== null && i !== undefined) sessionStorage.setItem(KEY, String(i)); } catch (e) {}
        }
        function directionFrom(prevIdx, idx) {
            if (prevIdx === null || prevIdx === undefined || idx === null || idx === undefined || isNaN(prevIdx)) return null;
            return idx < prevIdx ? 'back' : (idx > prevIdx ? 'forward' : null);
        }
        function report(direction) {
            var now = Date.now();
            if (lastUrl === location.href && now - lastAt < 400) return;      // the same traversal seen twice
            lastUrl = location.href; lastAt = now;
            try { window.__afqaLastHistory = { url: location.href, at: now, direction: direction }; } catch (e) {}
            send({ action_type: '__history__', direction: direction, url: location.href, title: document.title || null, timestamp: new Date().toISOString() });
        }
        var prevIdx = stored(), idx0 = entryIndex();
        try {
            var nv = performance.getEntriesByType('navigation')[0];
            if (nv && nv.type === 'back_forward') report(directionFrom(prevIdx, idx0));
        } catch (eNav) {}
        remember(idx0);
        if (window.navigation && window.navigation.addEventListener) {
            window.navigation.addEventListener('currententrychange', function (ev) {
                var idx = entryIndex();
                if (ev && ev.navigationType === 'traverse') {
                    var from = (ev.from && typeof ev.from.index === 'number') ? ev.from.index : stored();
                    report(directionFrom(from, idx));
                }
                remember(idx);
            });
        } else {
            window.addEventListener('popstate', function () { report(null); });
        }
        window.addEventListener('pageshow', function (ev) {
            if (ev && ev.persisted) { var idx = entryIndex(); report(directionFrom(stored(), idx)); remember(idx); }
        });
        // the page title, for a readable step name ("Open - <page title>")
        function sendTitle() {
            try { send({ action_type: '__title__', url: location.href, title: (document.title || '').trim() || null, timestamp: new Date().toISOString() }); } catch (e) {}
        }
        window.addEventListener('load', function () { setTimeout(sendTitle, 300); });
    })();

    // only a few keys are worth recording as their own step - everything
    // else (regular typing) is already captured by the change event above
    var MEANINGFUL_KEYS = ['Enter', 'Tab', 'Escape', 'Backspace'];
    document.addEventListener('keydown', function (e) {
        if (!e.isTrusted) return;
        if (MEANINGFUL_KEYS.indexOf(e.key) === -1) return;
        const el = e.target;
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        const editingText = tag === 'input' || tag === 'textarea' || el.isContentEditable;
        // backspace while editing text is just a correction mid-typing -
        // the eventual change event already captures the corrected value,
        // recording every backspace on top of that would be noise
        if (e.key === 'Backspace' && editingText) return;

        // Enter/Tab can trigger a form submit or navigation before blur
        // ever fires (blur is what normally commits the fill via change,
        // above) - flush the current value now, synchronously, while the
        // field still definitely has it, so a search box's typed text
        // never gets lost to a same-tick Enter-submits-the-form flow
        if ((tag === 'input' || tag === 'textarea') && (e.key === 'Enter' || e.key === 'Tab')) {
            // sendFillIfChanged itself guards non-text-entry inputs (see
            // isTextLikeField) - no need to re-check the type here too
            sendFillIfChanged(el);
            if (e.key === 'Enter') {
                // how long after Enter the browser's own synthetic submit
                // click/submit events show up varies a lot by site - ~11ms
                // on Amazon, ~530ms on eBay (likely autocomplete/typeahead
                // teardown running first) - 700ms covers both with room to
                // spare, while still being far shorter than a human
                // deliberately clicking a different submit button next
                suppressAutoSubmitUntil = Date.now() + 700;
                suppressAutoSubmitForm = el.closest ? el.closest('form') : null;
            }
        }

        var _pressPayload = buildProfile(el, 'press', e.key);
        if (e.key === 'Enter' && editingText) {
            try { _schedulePostClickObservation(_pressPayload, { submitLike: true, inputEl: el }); } catch (ePressObs) {}
        }
        send(_pressPayload);
    }, true);

    // scroll: fires directly on whatever element's scroll position
    // ACTUALLY changed, however that happened - mouse wheel, a scrollbar
    // thumb dragged with the mouse, keyboard (Page Down/Up, arrows,
    // Space), touch, or a page's own programmatic scrollTo()/scrollTop
    // assignment. Deliberately reworked from an earlier, wheel-event-
    // based approach: 'wheel' only observes the INPUT device gesture,
    // not the result, so it stays silent for every one of those other
    // scroll mechanisms, AND can straightforwardly misreport the result
    // even for an ordinary mouse-wheel gesture if a page's own JS
    // intercepts the wheel event to drive some custom scroll behavior
    // that doesn't move scrollTop the way the browser's native response
    // would have - confirmed missing entirely on a real product-listing/
    // search-results grid page, where scrolling still visibly happened
    // (confirmed on video) but zero scroll actions ever reached the
    // saved recording. Listening for the actual 'scroll' event instead
    // means this only ever reacts to a REAL, already-applied position
    // change, on any site, however it was driven.
    //
    // 'scroll' does not bubble past its own target (only the window's
    // own scroll, which targets `document`, propagates to window
    // listeners) - a nested scrollable container's own scroll event
    // never reaches a bubble-phase listener on an ancestor at all. The
    // CAPTURE phase is the only propagation phase that visits every
    // ancestor top-down regardless of bubbling, so registering here in
    // the capture phase on document is what makes one listener see a
    // scroll fired on ANY element on the page, nested or not - not just
    // stylistic, load-bearing for the same reason capture:true was for
    // the previous wheel-based listener.
    var SCROLL_SETTLE_MS = 250;
    // per-element (not one global) debounce timer/start-position - a page
    // can legitimately have the user scroll the window, then a nested
    // panel, then the window again, and each needs its own independent
    // settle-cycle and "before" baseline rather than borrowing whatever
    // the last-scrolled element's value was
    var scrollSettleTimers = new WeakMap();
    var scrollGestureStart = new WeakMap();
    var lastSettledScrollTop = new WeakMap();
    var lastSettledScrollLeft = new WeakMap();
    // a permanent, DOM-independent sentinel used as the WeakMap key for
    // window/document-level scrolling - deliberately NOT document.
    // scrollingElement/documentElement, which don't exist yet at the
    // exact moment this script runs (add_init_script executes at the
    // very start of a fresh document's lifecycle, before the parser has
    // created ANY node) and would make an initial "seed this at 0, right
    // now, before the user could possibly have scrolled anything" seed
    // either throw (WeakMap keys must be objects) or - if merely
    // skipped - silently miss its only genuinely race-free opportunity,
    // leaving the real element to be seeded much later, by which point
    // Chromium's own compositor-thread fast-path scrolling (which
    // doesn't wait for a passive listener like this one, since passive
    // means it's guaranteed not to call preventDefault) may already have
    // applied the scroll before this script ever observes it. A plain
    // object literal has no such dependency and is always available.
    var WINDOW_SCROLL_KEY = {};
    // seeded immediately, unconditionally, at script-injection time -
    // window.scrollY/X are always valid, ordinary numbers (0 by
    // definition for a document that hasn't rendered anything yet) with
    // no DOM-readiness dependency at all, unlike an element reference
    lastSettledScrollTop.set(WINDOW_SCROLL_KEY, window.scrollY);
    lastSettledScrollLeft.set(WINDOW_SCROLL_KEY, window.scrollX);

    // the REAL scrollingElement, needed only for reading its
    // scrollHeight/clientHeight when building a payload - by the time
    // any of that happens (well after a real scroll settled), the DOM
    // genuinely exists, so this is always safe to call there, just not
    // safe to rely on for anything at true script-top-level.
    function windowScrollFallback() {
        return document.scrollingElement || document.documentElement;
    }

    function scrollEventTarget(e) {
        // the window/document's own scroll fires with target === document
        // (or, in older engines, target === window) - normalized here to
        // the same permanent sentinel every other window-scroll code path
        // in this file already keys off of, so lastSettledScrollTop/Left
        // above always index it consistently
        var t = e.target;
        if (t === document || t === window || (t && t.nodeType === Node.DOCUMENT_NODE)) {
            return WINDOW_SCROLL_KEY;
        }
        return t;
    }

    // seeds lastSettledScrollTop/Left for a candidate NESTED element (and
    // every ancestor up to body) BEFORE any resulting scroll happens -
    // solves a real gap the 'scroll' event alone can't: unlike the
    // wheel-driven approach this replaced, 'scroll' only ever fires
    // AFTER a position change already happened, so the very first time
    // this listener ever sees a given element, it has no way to know
    // what its position was just before that - and simply falling back
    // to "whatever it reads right now" would read the ALREADY-CHANGED
    // value, making before/after look identical and silently dropping
    // the very first scroll recorded on any element. This is a purely
    // passive cache - it never records or sends anything, and never
    // overwrites a value that's already known, so a genuine settled
    // position from an earlier gesture is never clobbered. Walking the
    // whole ancestor chain (not just one guessed container) means this
    // doesn't need to know ahead of time which element will actually
    // turn out to be the one that scrolls - whichever one does is
    // already seeded by the time it does.
    //
    // Window/document scrolling is deliberately handled separately (see
    // WINDOW_SCROLL_KEY above), not here - a NATIVELY-scrollable target
    // (the window itself, or a nested overflow:auto/scroll container)
    // can still race ahead of even a capture-phase 'wheel'/'mousedown'
    // seed exactly like it does the 'scroll' event itself (Chromium's
    // compositor-thread fast-path scrolling doesn't wait for a passive
    // listener), so seeding from a gesture-start event here is only
    // reliable for a target that ISN'T natively scrolled by the browser
    // on its own - a nested container is the common real case (its
    // scrollTop only ever changes via explicit script/user-driven
    // scrolling this listener also observes), while the window's own
    // baseline is instead seeded exactly once, unconditionally, at true
    // script-injection time above, before any scrolling could possibly
    // have happened yet.
    //
    // scrollSettleTimers.has(node) is just as important a guard here as
    // lastSettledScrollTop.has(node) - confirmed real, not hypothetical:
    // a single logical scroll gesture routinely produces MULTIPLE raw
    // 'wheel'/'mousedown' ticks before its own debounce ever settles
    // (lastSettledScrollTop is deliberately only written AT settle time,
    // see the 'scroll' listener below), and without this second guard, a
    // later tick within that SAME still-in-progress gesture would see
    // lastSettledScrollTop still empty and re-seed it with whatever the
    // position has ALREADY moved to mid-gesture - silently corrupting
    // the correct "before" value scrollGestureStart captured at the
    // gesture's true start into a near-zero, no-op-looking delta.
    function seedScrollBaseline(el) {
        var node = el;
        while (node && node.nodeType === Node.ELEMENT_NODE) {
            if (!lastSettledScrollTop.has(node) && !scrollSettleTimers.has(node)) {
                lastSettledScrollTop.set(node, node.scrollTop);
                lastSettledScrollLeft.set(node, node.scrollLeft);
            }
            node = node.parentElement;
        }
    }
    // any of these commonly precede a real scroll actually happening
    // (mouse wheel, a scrollbar thumb grabbed with the mouse, keyboard
    // Page Down/arrows/Space, a touch drag) - capture phase so this sees
    // the gesture starting on any element, nested or not, the same
    // reasoning as the 'scroll' listener itself below.
    //
    // 'mouseover' is ALSO in this list, and that one is not like the
    // others - it doesn't precede a scroll gesture the way a wheel/
    // mousedown/keydown/touchstart tick does, it precedes the CURSOR
    // arriving somewhere, which usually happens earlier still. That gap
    // matters: Chromium's compositor-thread fast-path scrolling (see the
    // WINDOW_SCROLL_KEY comment above for the window's own version of
    // this same problem) can apply a NESTED container's scroll before
    // even a capture-phase 'wheel' listener runs - confirmed via a real
    // debug-instrumented repro (DEBUG_RECORDER=1): a single fast wheel
    // gesture over a nested scrollable div showed the container's own
    // scrollTop already at its POST-scroll value (e.g. 50, on the very
    // first debounce tick of a 0->300 gesture) by the time seedScrollBaseline
    // ran from 'wheel', undercounting the recorded delta by however much
    // the compositor won the race by - up to the ENTIRE gesture for one
    // large, fast jump, which silently drops the scroll from the
    // recording altogether. seedScrollBaseline's own .has() guard already
    // makes it a no-op once a real pre-gesture value is cached, so adding
    // 'mouseover' here costs nothing on top of the existing listeners -
    // it just gives the SAME idempotent seed an earlier, race-free chance
    // to run at the moment the cursor first arrives over a scrollable
    // element, strictly before any wheel/keydown/touchstart tick (and
    // therefore before the compositor has any scroll to race ahead of).
    ['wheel', 'mousedown', 'keydown', 'touchstart', 'mouseover'].forEach(function (evtType) {
        document.addEventListener(evtType, function (e) {
            if (e.target && e.target.nodeType === Node.ELEMENT_NODE) {
                seedScrollBaseline(e.target);
            }
        }, { passive: true, capture: true });
    });

    document.addEventListener('scroll', function (e) {
        var el = scrollEventTarget(e);
        if (!el) return;
        var isWindowScroll = (el === WINDOW_SCROLL_KEY);
        // the REAL element to read DOM properties (scrollTop/Height,
        // clientHeight, tag, css_path) from - el itself for a nested
        // container, but the actual scrollingElement for the window
        // case, since el there is WINDOW_SCROLL_KEY, a plain object with
        // no such properties at all (see WINDOW_SCROLL_KEY's own comment
        // for why the WeakMap key and the real element can't just be the
        // same reference)
        var realEl = isWindowScroll ? windowScrollFallback() : el;
        var curTop = isWindowScroll ? window.scrollY : el.scrollTop;
        var curLeft = isWindowScroll ? window.scrollX : el.scrollLeft;

        debugLog(
            'scroll event on', debugDescribeTarget(realEl),
            '(event target=' + debugDescribeTarget(e.target) + ')',
            'scrollTop=' + curTop,
            'scrollHeight=' + (realEl ? realEl.scrollHeight : null),
            'isWindowScroll=' + isWindowScroll
        );

        if (!scrollSettleTimers.has(el)) {
            // first event of a new settle-cycle for this element - lock
            // in its pre-gesture position now, before any further
            // movement in this same burst happens. Same "previous
            // gesture's own settled value, not a mid-gesture sample" idea
            // the old wheel-based approach used - a fast, rapid-fire
            // burst of scroll events can already reflect a position well
            // past where this specific burst started by the time this
            // handler runs.
            var beforeTop = lastSettledScrollTop.has(el) ? lastSettledScrollTop.get(el) : curTop;
            var beforeLeft = lastSettledScrollLeft.has(el) ? lastSettledScrollLeft.get(el) : curLeft;
            scrollGestureStart.set(el, { top: beforeTop, left: beforeLeft });
        } else {
            clearTimeout(scrollSettleTimers.get(el));
        }

        var timer = setTimeout(function () {
            scrollSettleTimers.delete(el);
            var start = scrollGestureStart.get(el) || { top: curTop, left: curLeft };
            scrollGestureStart.delete(el);

            var yBefore = start.top;
            var xBefore = start.left;
            var yAfter = isWindowScroll ? window.scrollY : el.scrollTop;
            var xAfter = isWindowScroll ? window.scrollX : el.scrollLeft;
            lastSettledScrollTop.set(el, yAfter);
            lastSettledScrollLeft.set(el, xAfter);

            var dy = Math.round(yAfter - yBefore);
            var dx = Math.round(xAfter - xBefore);
            if (dx === 0 && dy === 0) {
                // settled back exactly where this burst started (a
                // momentum overshoot that fully reversed, or an already-
                // at-boundary no-op) - not a real position change,
                // nothing to record
                return;
            }

            var payload = {
                action_type: 'scroll',
                value: null,
                delta_x: dx,
                delta_y: dy,
                scroll_y_before: yBefore,
                scroll_y_after: yAfter,
                viewport_height: isWindowScroll ? window.innerHeight : realEl.clientHeight,
                document_height: realEl.scrollHeight,
                // only a nested container needs a locator to re-find at
                // replay time - plain window scrolling has none. Same
                // buildLocatorProfile() every click/fill/select/submit/
                // press target already goes through (see its own comment)
                // - a scroll target used to get only {css_path, tag}, with
                // no id/aria-label/xpath/text/attributes to fall back to
                // if css_path's nth-of-type-based path drifts between
                // record and replay time, unlike every other action type.
                locator_profile: isWindowScroll ? null : buildLocatorProfile(realEl),
                bounding_box: null,
                page_url: window.location.href,
                timestamp: new Date().toISOString()
            };
            try {
                // what was on screen after the scroll: a few short texts and where they sat, so replay can bring
                // the SAME content into view (a banner of another height must not shift it)
                if (isWindowScroll) {
                    var anchors = afqaScrollAnchors();
                    if (anchors.length) payload.scroll_anchors = anchors;
                }
            } catch (eAnchors) {}
            debugLog(
                'scroll captured on', debugDescribeTarget(realEl),
                'dx=' + dx, 'dy=' + dy,
                'before=' + yBefore, 'after=' + yAfter
            );
            send(payload);
        }, SCROLL_SETTLE_MS);
        scrollSettleTimers.set(el, timer);
    }, { passive: true, capture: true });

    // Page Visibility API - the only generic, DOM-standard way to detect
    // that the user switched TO this tab from page-level JS (browser
    // tab-strip clicks happen outside any page's DOM, so there's no click/
    // focus event for them). Every visible transition is forwarded; the
    // Python side (Recorder._handle_visibility) decides whether it's a
    // genuine switch back to an already-open tab or just this page's own
    // first-ever activation (initial load / just-opened new tab), and
    // only the former becomes a recorded tab_switch action. Note this can
    // also fire from OS-level app-switching (alt-tab away and back), a
    // known limitation of this API - there's no way to distinguish that
    // from a real browser tab switch at this layer.
    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState !== 'visible') return;
        send({
            action_type: '__page_visible__',
            value: null,
            locator_profile: null,
            bounding_box: null,
            page_url: window.location.href,
            timestamp: new Date().toISOString()
        });
    });
})();
