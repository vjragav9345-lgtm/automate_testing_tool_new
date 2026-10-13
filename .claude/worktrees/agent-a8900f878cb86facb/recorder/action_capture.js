// Injected once per page load. Always listens and always forwards to
// Python via window.recordAction - whether an event actually gets kept as
// a recorded step is decided on the Python side (Recorder.recording), not
// here. Keeping the on/off switch out of page JS means it can't survive a
// navigation and silently start capturing again after a recording ends.
(function () {
    if (window.__afqaListenersAttached) return;
    window.__afqaListenersAttached = true;

    function cssPath(el) {
        if (!(el instanceof Element)) return '';
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

    function xPath(el) {
        if (el.id) return "//*[@id='" + el.id + "']";
        const parts = [];
        while (el && el.nodeType === Node.ELEMENT_NODE) {
            let idx = 1;
            let sib = el.previousSibling;
            while (sib) {
                if (sib.nodeType === Node.ELEMENT_NODE && sib.nodeName === el.nodeName) idx++;
                sib = sib.previousSibling;
            }
            parts.unshift(el.nodeName.toLowerCase() + '[' + idx + ']');
            el = el.parentElement;
        }
        return '/' + parts.join('/');
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
        return el;
    }

    // best-effort accessible name, checked in roughly the priority order
    // browsers/screen readers use - generic, no site knowledge required
    function accessibleName(el) {
        var ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.trim()) return ariaLabel.trim();
        var labelledby = el.getAttribute('aria-labelledby');
        if (labelledby) {
            var txt = labelledby.split(/\s+/).map(function (id) {
                var ref = document.getElementById(id);
                return ref ? (ref.innerText || ref.textContent || '') : '';
            }).join(' ').trim();
            if (txt) return txt;
        }
        if (el.tagName === 'IMG' && el.alt && el.alt.trim()) return el.alt.trim();
        if ((el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el.placeholder) return el.placeholder.trim();
        return (el.innerText || el.value || '').trim().slice(0, 80);
    }

    function buildProfile(rawEl, actionType, value) {
        // only click-type interactions benefit from walking to a semantic
        // ancestor - fill/select/press already fire on the real form
        // control (that's what "target" means for those event types)
        var el = (actionType === 'click' || actionType === 'dblclick' || actionType === 'right_click')
            ? resolveSemanticTarget(rawEl)
            : rawEl;
        const rect = el.getBoundingClientRect();
        const attrs = {};
        for (const a of el.attributes) {
            if (STRONG_ATTRS.includes(a.name)) {
                attrs[a.name] = a.value;
            }
        }
        const elementText = (el.innerText || el.value || '').trim().slice(0, 80);
        return {
            action_type: actionType,
            value: value || null,
            locator_profile: {
                id: el.id ? '#' + el.id : null,
                name: el.getAttribute('name') || null,
                role: el.getAttribute('role') || null,
                aria_label: el.getAttribute('aria-label') || null,
                accessible_name: accessibleName(el),
                placeholder: el.getAttribute('placeholder') || null,
                title: el.getAttribute('title') || null,
                href: (el.tagName === 'A' && el.hasAttribute('href')) ? el.getAttribute('href') : null,
                css_path: cssPath(el),
                xpath: xPath(el),
                text: elementText,
                element_text: elementText,
                tag: el.tagName.toLowerCase(),
                attributes: attrs
            },
            bounding_box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
            page_url: window.location.href,
            timestamp: new Date().toISOString()
        };
    }

    function send(payload) {
        try {
            window.recordAction(JSON.stringify(payload));
        } catch (err) {
            // recordAction not bound yet (recording never started on this page), ignore
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

    function flushPendingClick() {
        if (!pendingClick) return;
        clearTimeout(pendingClick.timer);
        var payload = pendingClick.payload;
        pendingClick = null;
        send(payload);
    }

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
    // rather than recorded as redundant extra steps
    var suppressAutoSubmitUntil = 0;

    function isSubmitTrigger(el) {
        if (!el || !el.tagName) return false;
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute('type') || (tag === 'button' ? 'submit' : '')).toLowerCase();
        return (tag === 'button' || tag === 'input') && type === 'submit';
    }

    document.addEventListener('click', function (e) {
        // isTrusted is false for any event dispatched by page JS itself
        // (el.click(), a framework's own synthetic event, etc.) - only
        // genuine OS-level user input should ever become a recorded
        // action, never something the website's own code triggered
        if (!e.isTrusted) return;
        if (suppressAutoSubmitUntil && Date.now() <= suppressAutoSubmitUntil && isSubmitTrigger(e.target)) {
            return;
        }

        flushFocusedFieldIfNeeded();

        var semanticEl = resolveSemanticTarget(e.target);

        if (
            semanticEl === lastSemanticClickEl &&
            e.target !== lastSemanticClickRawTarget &&
            (Date.now() - lastSemanticClickTime) < LABEL_CASCADE_DEDUP_MS
        ) {
            return;
        }

        if (pendingClick && pendingClick.target === e.target) {
            // second click of a double-click - let the dblclick handler
            // below record the real action, this pair doesn't get its own
            clearTimeout(pendingClick.timer);
            pendingClick = null;
            return;
        }
        // a pending click on a DIFFERENT element wasn't part of a double
        // click after all - it was just a normal single click, send it now
        flushPendingClick();

        lastSemanticClickEl = semanticEl;
        lastSemanticClickRawTarget = e.target;
        lastSemanticClickTime = Date.now();

        var payload = buildProfile(e.target, 'click', null);
        pendingClick = {
            target: e.target,
            payload: payload,
            timer: setTimeout(function () {
                pendingClick = null;
                send(payload);
            }, DBLCLICK_WINDOW_MS)
        };
    }, true);

    document.addEventListener('dblclick', function (e) {
        if (!e.isTrusted) return;
        flushFocusedFieldIfNeeded();
        if (pendingClick) {
            clearTimeout(pendingClick.timer);
            pendingClick = null;
        }
        send(buildProfile(e.target, 'dblclick', null));
    }, true);

    // right-click: the browser only fires 'contextmenu' for the secondary
    // button, never 'click', so there's no disambiguation needed here
    document.addEventListener('contextmenu', function (e) {
        if (!e.isTrusted) return;
        flushFocusedFieldIfNeeded();
        flushPendingClick();
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
    function sendFillIfChanged(el) {
        const current = el.value;
        if (el.__afqaLastSentValue === current) return;
        el.__afqaLastSentValue = current;
        send(buildProfile(el, 'fill', current));
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
    function isTextLikeField(el) {
        if (!el || !el.tagName) return false;
        const tag = el.tagName.toLowerCase();
        if (tag !== 'input' && tag !== 'textarea') return false;
        const inputType = (el.getAttribute('type') || 'text').toLowerCase();
        return inputType !== 'checkbox' && inputType !== 'radio';
    }

    var lastFocusedTextField = null;

    document.addEventListener('focusin', function (e) {
        lastFocusedTextField = isTextLikeField(e.target) ? e.target : null;
    }, true);

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

    document.addEventListener('change', function (e) {
        if (!e.isTrusted) return;
        const tag = e.target.tagName.toLowerCase();
        if (tag === 'select') {
            // dropdowns are their own action type, not a "fill" - replay
            // needs page.select_option(), not page.fill()
            send(buildProfile(e.target, 'select', e.target.value));
            return;
        }
        if (tag === 'input' || tag === 'textarea') {
            // checkboxes/radios already get recorded as a plain 'click'
            // above (that's the correct replay action for them too) -
            // only text-like inputs need their committed value captured
            const inputType = (e.target.getAttribute('type') || 'text').toLowerCase();
            if (inputType === 'checkbox' || inputType === 'radio') return;
            sendFillIfChanged(e.target);
        }
    }, true);

    document.addEventListener('submit', function (e) {
        if (!e.isTrusted) return;
        if (suppressAutoSubmitUntil && Date.now() <= suppressAutoSubmitUntil) {
            return;
        }
        send(buildProfile(e.target, 'submit', null));
    }, true);

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
            const inputType = (el.getAttribute('type') || 'text').toLowerCase();
            if (inputType !== 'checkbox' && inputType !== 'radio') {
                sendFillIfChanged(el);
            }
            if (e.key === 'Enter') {
                // how long after Enter the browser's own synthetic submit
                // click/submit events show up varies a lot by site - ~11ms
                // on Amazon, ~530ms on eBay (likely autocomplete/typeahead
                // teardown running first) - 700ms covers both with room to
                // spare, while still being far shorter than a human
                // deliberately clicking a different submit button next
                suppressAutoSubmitUntil = Date.now() + 700;
            }
        }

        send(buildProfile(el, 'press', e.key));
    }, true);

    // scroll wheel: fires many times per second during a single scroll
    // gesture, so the deltas are accumulated and sent once as ONE action
    // after the user pauses, the same "commit on settle" idea as change.
    // scroll_y_before is the position where THAT SAME scrolling element's
    // PREVIOUS gesture (or the page load, for the first one) actually
    // settled - not sampled mid-gesture, since a synthetic/fast wheel
    // event can already reflect the post-scroll position by the time a
    // handler runs, which would make "before" and "after" read as the
    // same value despite a real change.
    var SCROLL_SETTLE_MS = 250;
    var scrollTimer = null;
    var scrollDx = 0;
    var scrollDy = 0;
    var scrollTargetEl = null;
    var scrollYBeforeForGesture = null;
    // per-element (not one global) last-settled scrollTop - a page can
    // legitimately have the user scroll the window, then a nested panel,
    // then the window again, and each needs its own "before" baseline
    // rather than borrowing whatever the last-scrolled element's value was
    var lastSettledScrollTop = new WeakMap();
    var windowScrollFallback = document.scrollingElement || document.documentElement;

    // walks up from the wheel event's actual target to the nearest
    // ancestor that is genuinely a scrollable container (has real
    // overflow content AND a non-default computed overflow-y) - product
    // pages, split-panel layouts, dashboards, or any other page where a
    // nested region scrolls independently of the window all hit this.
    // Falls back to the window's own scrolling element when no such
    // ancestor exists, which is identical to the previous behavior for
    // ordinary whole-page scrolling - this is purely structural
    // (scrollHeight/clientHeight/computed overflow), no site knowledge.
    function findScrollableAncestor(el) {
        var node = (el && el.nodeType === Node.ELEMENT_NODE) ? el : (el && el.parentElement);
        while (node) {
            if (node.scrollHeight > node.clientHeight) {
                var overflowY = window.getComputedStyle(node).overflowY;
                if (overflowY === 'scroll' || overflowY === 'auto') {
                    return node;
                }
            }
            node = node.parentElement;
        }
        return windowScrollFallback;
    }

    document.addEventListener('wheel', function (e) {
        if (!e.isTrusted) return;
        if (scrollTimer === null && scrollDx === 0 && scrollDy === 0) {
            // first wheel tick of a new gesture - lock in which element
            // is actually scrolling and its pre-gesture position now,
            // before any of this gesture's own movement happens
            scrollTargetEl = findScrollableAncestor(e.target);
            scrollYBeforeForGesture = lastSettledScrollTop.has(scrollTargetEl)
                ? lastSettledScrollTop.get(scrollTargetEl)
                : scrollTargetEl.scrollTop;
        }
        scrollDx += e.deltaX;
        scrollDy += e.deltaY;
        if (scrollTimer) clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function () {
            var dx = Math.round(scrollDx);
            var dy = Math.round(scrollDy);
            var el = scrollTargetEl;
            var yBefore = scrollYBeforeForGesture;
            var yAfter = el.scrollTop;
            lastSettledScrollTop.set(el, yAfter);
            scrollDx = 0;
            scrollDy = 0;
            scrollTimer = null;
            scrollTargetEl = null;
            scrollYBeforeForGesture = null;
            if (dx === 0 && dy === 0) {
                // opposing wheel ticks that fully cancelled out within
                // this gesture - not a real scroll attempt, nothing to
                // record. A non-zero delta that still didn't move the
                // page (e.g. already at a boundary, or a nested scroll
                // container) is NOT filtered here - that's still real
                // signal, just not this exact no-op case.
                return;
            }
            var isWindowScroll = (el === windowScrollFallback);
            var payload = {
                action_type: 'scroll',
                value: null,
                delta_x: dx,
                delta_y: dy,
                scroll_y_before: yBefore,
                scroll_y_after: yAfter,
                viewport_height: isWindowScroll ? window.innerHeight : el.clientHeight,
                document_height: el.scrollHeight,
                // only a nested container needs a locator to re-find at
                // replay time - plain window scrolling has none, exactly
                // as before this change
                locator_profile: isWindowScroll ? null : { css_path: cssPath(el), tag: el.tagName.toLowerCase() },
                bounding_box: null,
                page_url: window.location.href,
                timestamp: new Date().toISOString()
            };
            send(payload);
        }, SCROLL_SETTLE_MS);
    }, { passive: true });

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
