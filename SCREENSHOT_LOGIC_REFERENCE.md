<!--
READ-ONLY REFERENCE COPY - FOR REVIEW/DOCUMENTATION ONLY.

This file is a verbatim snapshot of the replay-time screenshot-capture code
that actually lives in generator/script_generator.py (with one companion
piece in executor/run_execution.py). It is NOT imported, NOT executed, and
NOT part of the running application - it exists purely so this logic can be
reviewed in one place without opening the full generator file and hunting
through it.

The real, live code is untouched and stays exactly where it is. If the two
ever disagree, generator/script_generator.py (and executor/run_execution.py)
are the source of truth - this file should be regenerated from them, not the
other way around.

Line numbers below refer to generator/script_generator.py unless otherwise
noted, and were accurate as of the snapshot this file was generated from.
-->

# Screenshot-Capture Logic Reference

## 1. Per-run folder path

### `run()` header — decides `shot_dir` — `generator/script_generator.py:1621-1648`

```python
def run(qa_url, output_json_path=None, screenshot_dir=None, headless=True, product_name=None):
    _verify_fill_select_retry_intact()
    print("Starting replay...")
    result = {
        "status": "FAIL",
        "message": "",
        "qa_url": qa_url,
        "steps": [],
        "final_url": None,
        "final_screenshot": None,
        "final_text": None,
        "product_validation": None,
    }

    # an explicit screenshot_dir (the dashboard flows always pass one -
    # see execute_test in executor/run_execution.py) is already a fresh,
    # unique-per-run folder, used as-is. The fallback here only kicks in
    # when the script is run directly with no screenshot_dir arg -
    # without a per-run subfolder of its own, every such run would write
    # into the SAME shared "screenshots" folder and different runs'
    # same-numbered images would collide/interleave with no way to tell
    # which run a given file came from.
    if screenshot_dir:
        shot_dir = Path(screenshot_dir)
    else:
        run_id = f"{_slug(SOURCE_NAME) or 'run'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shot_dir = Path(__file__).resolve().parent / "screenshoots" / run_id
    shot_dir.mkdir(parents=True, exist_ok=True)
```

### Shared counters set up immediately after — `generator/script_generator.py:1650-1662`

```python
    # one shared, run-wide counter so EVERY screenshot this run takes -
    # the initial load, every per-step capture, the final state, and any
    # product-validation capture - lands in one strictly sequential
    # img1.png, img2.png, ... series, in the exact order they were
    # actually taken. A single-element list so _validate_product (a
    # separate function, called later) can advance the SAME sequence
    # rather than starting its own.
    img_counter = [0]
    # tracks the state fingerprint of the last screenshot actually SAVED
    # this run (see _capture_screenshot/_page_state_key) - also a single-
    # element list so it's shared/mutable across every capture call site,
    # including _validate_product's own.
    last_state = [None]
```

### Companion path for dashboard-triggered runs — `executor/run_execution.py:104-117`

```python
def execute_test(qa_url, script_path, expected_content=None, expected_screenshot=None, product_to_verify=None, recording_name=None):
    qa_url = normalize_url(qa_url)
    script_path = Path(script_path)
    # one dedicated folder for EVERYTHING this run produces - the
    # sequential img1.png, img2.png, ... screenshots (including product-
    # validation's own capture) and the report data below - instead of
    # each kind of output picking its own top-level location. Single
    # generated_scripts/screenshoots/<name>_<timestamp>/ folder, same
    # naming convention (and same parent as the generated scripts
    # themselves) the generated script's own run() uses for its
    # script-relative fallback when executed directly.
    run_id = f"{_slug(recording_name or script_path.stem) or 'run'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = BASE_DIR / "generated_scripts" / "screenshoots" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_json = run_dir / "report.json"
```

---

## 2. Milestone detection / dedup — helper functions

### `_next_shot_path` — `generator/script_generator.py:168-174`

```python
def _next_shot_path(shot_dir, counter):
    """Returns the path for the NEXT screenshot in this run's sequence -
    img1.png, img2.png, ... - advancing the shared counter every call so
    every screenshot the whole run takes (initial load, per-step,
    final, product validation) lands in one strictly ordered series."""
    counter[0] += 1
    return Path(shot_dir) / f"img{counter[0]}.png"
```

### `_page_state_key` — `generator/script_generator.py:177-207`

```python
def _page_state_key(page):
    """A cheap, generic fingerprint of the page's CURRENT rendered state -
    URL, a hash of the full DOM markup (not just visible text, so a
    purely visual/structural change - a button gaining disabled/aria-
    busy, a class toggling on for a spinner, an error banner being
    inserted - still counts as a real change even when no visible text
    changed), plus every input/textarea/select's current VALUE. That
    last part matters generically on any site: page.content() serializes
    static HTML attributes only - typing into a field changes its live
    DOM property, not its HTML attribute, so content() alone never
    reflects what a user actually typed/selected. Returns None if the
    page can't be read right now (e.g. mid-navigation, closed) - callers
    should treat that as "can't compare, don't suppress."
    """
    try:
        content = page.content()
    except Exception:
        return None
    try:
        url = page.url
    except Exception:
        url = ""
    try:
        field_values = page.eval_on_selector_all(
            "input, textarea, select",
            "els => els.map(el => el.value).join('\\u0001')",
        )
    except Exception:
        field_values = ""
    fingerprint = f"{content}{field_values}"
    return url + "|" + hashlib.md5(fingerprint.encode("utf-8", "ignore")).hexdigest()
```

---

## 3. The actual screenshot-taking call

### `_capture_screenshot` — `generator/script_generator.py:210-235`

```python
def _capture_screenshot(page, shot_dir, img_counter, last_state, full_page=False):
    """Takes the next screenshot in this run's sequence, but SKIPS saving
    it (and does not advance the image counter) if the page's current
    state is a near-duplicate of the last screenshot actually saved this
    run - several near-identical captures of the same still-settling
    state (e.g. a field mid-retry, a click whose transition was too fast
    to render anything different) collapse into the one that shows an
    actually new state, while a real change (a field's final value, a
    loading indicator appearing, an error banner, a new page) always
    still gets its own image. Best-effort throughout: a failure to read
    state or to take the screenshot just means this capture is skipped,
    never a reason to fail the action it's attached to.

    Returns the saved path as a string, or None if skipped/failed.
    """
    state_key = _page_state_key(page)
    if state_key is not None and state_key == last_state[0]:
        return None
    try:
        shot_path = _next_shot_path(shot_dir, img_counter)
        page.screenshot(path=str(shot_path), full_page=full_page)
    except Exception:
        return None
    if state_key is not None:
        last_state[0] = state_key
    return str(shot_path)
```

---

## 4. Every call site that triggers a capture during replay

### Initial page load (img1) — `generator/script_generator.py:1707-1726`

```python
        # same standard as every other navigate action below: don't treat
        # the initial page load as genuinely ready just because
        # domcontentloaded/networkidle fired - confirm action #1's own
        # target can actually be found first, using the exact same
        # lookahead used for every subsequent navigate action, so the
        # homepage is truly rendered (not just loaded) before anything
        # is clicked on it
        first_step = STEPS[0] if STEPS else None
        first_lp = (first_step or {}).get("locator_profile") or {}
        if first_lp:
            print("[navigate-ready] waiting for step 1's target to become findable (up to 9.0s)...")
            ready_start = time.monotonic()
            if _wait_for_next_step_ready(page, first_step):
                print(f"[navigate-ready] found at t={time.monotonic() - ready_start:.1f}s - initial page is ready")
            else:
                print("[navigate-ready] step 1's target never appeared within the wait window")

        # img1: the settled result of the very first page load, before
        # any recorded action has run
        _capture_screenshot(page, shot_dir, img_counter, last_state)
```

### Explicit `navigate` steps — readiness check before that step's shared capture — `generator/script_generator.py:1918-1941`

```python
                        if ok:
                            # the URL and networkidle checks above can both
                            # be satisfied while the SPA is still rendering
                            # the previous view underneath - the strongest,
                            # most directly relevant signal that the
                            # destination is actually usable is whether the
                            # NEXT recorded step's own target can be found
                            # there, so check that directly instead of a
                            # generic content-diff/timing heuristic.
                            next_step = STEPS[i] if i < len(STEPS) else None
                            next_lp = (next_step or {}).get("locator_profile") or {}
                            if next_lp:
                                print(f"[navigate-ready] waiting for next step's target to become findable (up to 9.0s)...")
                                ready_start = time.monotonic()
                                if _wait_for_next_step_ready(page, next_step):
                                    print(f"[navigate-ready] found at t={time.monotonic() - ready_start:.1f}s - destination page is ready")
                                else:
                                    print(f"[navigate-ready] next step's target never appeared within the wait window")
                                    readiness_note = (
                                        "next recorded step's target never appeared on this "
                                        "page within the wait window - destination may not have "
                                        "actually finished loading/rendering"
                                    )
                                    nav_warning = f"{nav_warning}; {readiness_note}" if nav_warning else readiness_note
```

### Click/dblclick/right_click/submit/press that succeed (`NAV_CAUSING_ACTIONS`) — `generator/script_generator.py:2005-2078`

```python
                    else:
                        try:
                            strategy, found, ok, err = _resolve_and_act_with_retry(page, step)
                        except Exception as e:
                            # one bad step shouldn't blank out the rest of the run
                            strategy, found, ok, err = None, False, False, str(e)
                            logger.error("step %d raised unexpectedly: %s", i, e)

                        if ok and action_type in NAV_CAUSING_ACTIONS:
                            # captured BEFORE settling, so a visible
                            # transitional state (a submit button going
                            # into a loading/disabled state, etc.) has a
                            # chance to be caught in its own image - the
                            # dedup check in _capture_screenshot means a
                            # transition too fast to render anything
                            # different here just gets skipped, and the
                            # step's own post-settle screenshot below
                            # ends up being the only (and correct) one
                            _capture_screenshot(page, shot_dir, img_counter, last_state)
                            _settle(page)
                            # _settle() only waits for network activity to
                            # quiet down - a result the app renders purely
                            # client-side (a validation/error message, a
                            # success state) with no accompanying network
                            # request wouldn't be waited for at all
                            # otherwise, so the step's screenshot below
                            # could still catch a pre-result frame. Same
                            # short, generic wait used elsewhere in this
                            # file for exactly this kind of DOM-settling
                            # purpose (see _validate_product's scroll
                            # loop) - not tied to any specific site or
                            # outcome.
                            try:
                                page.wait_for_timeout(300)
                            except Exception:
                                pass

                            # networkidle+300ms is a generic timing proxy,
                            # not proof the destination actually finished
                            # rendering - an SPA route change this click
                            # triggered can still be waiting on its own
                            # data fetch (an events listing, a form
                            # template) well after the network itself goes
                            # quiet. This does NOT affect the click's own
                            # success/failure (ok/strategy/err above are
                            # already decided) - it only delays the
                            # milestone screenshot below until the next
                            # recorded step's target is actually findable,
                            # the same readiness signal the navigate branch
                            # already relies on, so a milestone image never
                            # captures a still-loading page just because
                            # this wasn't a recorded "navigate" step.
                            #
                            # Gated on the URL actually having changed:
                            # most clicks in a real flow (a checkbox, an
                            # expanding dropdown, a size/gender picker)
                            # interact with the SAME page and never
                            # navigate anywhere - for those the "next
                            # step's target" often isn't meant to appear
                            # from THIS click at all (it may need a
                            # further click first), so waiting the full
                            # window here would just burn up to 9s per
                            # such click for no benefit. A real navigation
                            # is cheaply, generically detectable first: a
                            # different URL after settling.
                            try:
                                url_changed = page.url != url_before
                            except Exception:
                                url_changed = False
                            if url_changed:
                                next_step_for_shot = STEPS[i] if i < len(STEPS) else None
                                next_lp_for_shot = (next_step_for_shot or {}).get("locator_profile") or {}
                                if next_lp_for_shot:
                                    _wait_for_next_step_ready(page, next_step_for_shot)
```

### Unconditional per-step capture (every action type — dedup does the real filtering) — `generator/script_generator.py:2092-2102`

```python
                # every recorded action still gets its own screenshot
                # ATTEMPT here, no exceptions, positioned after any
                # settling the action-type-specific handling above did -
                # _capture_screenshot skips the SAVE (leaving shot_str
                # None, same as a failed capture) only when this state is
                # a near-duplicate of the last screenshot actually saved,
                # e.g. a fill whose value didn't visibly change from the
                # prior step's already-typed state, or a click whose
                # transitional capture above already caught this same
                # settled state
                shot_str = _capture_screenshot(page, shot_dir, img_counter, last_state)
```

### End of run (final state, full page) — `generator/script_generator.py:2197`

```python
            final_shot = _capture_screenshot(final_page, shot_dir, img_counter, last_state, full_page=True)
```

---

## Index

| Piece | File | Lines |
|---|---|---|
| `_next_shot_path` | `generator/script_generator.py` | 168–174 |
| `_page_state_key` | `generator/script_generator.py` | 177–207 |
| `_capture_screenshot` | `generator/script_generator.py` | 210–235 |
| Folder-path decision (`run()` header) | `generator/script_generator.py` | 1621–1648 |
| Counter setup | `generator/script_generator.py` | 1650–1662 |
| Initial page-load capture | `generator/script_generator.py` | 1707–1726 |
| `navigate`-step readiness check | `generator/script_generator.py` | 1918–1941 |
| `NAV_CAUSING_ACTIONS` block | `generator/script_generator.py` | 2005–2078 |
| Unconditional per-step capture | `generator/script_generator.py` | 2092–2102 |
| Final-state capture | `generator/script_generator.py` | 2197 |
| Dashboard-run folder path | `executor/run_execution.py` | 104–117 |

Note: the recorder (`recorder/record_session.py`, `recorder/action_capture.js`) contains no screenshot logic at all — nothing to reference here.
