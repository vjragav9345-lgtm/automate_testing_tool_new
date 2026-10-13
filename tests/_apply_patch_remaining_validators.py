p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()


def sub(old, new, count=1):
    global s
    got = s.count(old)
    assert got == count, (got, old[:90])
    s = s.replace(old, new, count)


# ---- validate_text ----
sub(
r'''                    elif action_type == "validate_text":
                        lp = step.get("locator_profile") or {}
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "contains").strip().lower()
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_text: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Text", shot_dir=shot_dir)
                            try:
                                actual_value = _extract_element_value(el) or ""
                                if not actual_value:
                                    actual_value = " ".join((el.inner_text(timeout=1000) or "").split())
                            except Exception:
                                actual_value = ""
                            if match_mode == "exact":
                                ok = actual_value.strip() == expected_value.strip()
                            else:
                                ok = expected_value.strip().lower() in actual_value.lower()
                            err = None if ok else (
                                f"validate_text: expected {'exactly ' if match_mode == 'exact' else ''}"
                                f"{expected_value!r}, got {actual_value!r}"
                            )
                            print(f"[validate_text] expected={expected_value!r} actual={actual_value!r} mode={match_mode}: {'PASS' if ok else 'FAIL'}")''',
r'''                    elif action_type == "validate_text":
                        lp = step.get("locator_profile") or {}
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "contains").strip().lower()

                        def _vt_read(e):
                            try:
                                v = _extract_element_value(e) or ""
                                if not v:
                                    v = " ".join((e.inner_text(timeout=1000) or "").split())
                            except Exception:
                                v = ""
                            return {"text": v}

                        def _vt_expected(info):
                            v = info["text"]
                            return v.strip() == expected_value.strip() if match_mode == "exact" else expected_value.strip().lower() in v.lower()

                        el, _vt_info, _vt_elapsed = poll_until_expected(
                            page, lp, read_fn=_vt_read, is_expected=_vt_expected,
                        )
                        if el is None:
                            found, ok, err = False, False, "validate_text: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Text", shot_dir=shot_dir)
                            actual_value = (_vt_info or {}).get("text", "")
                            ok = _vt_expected(_vt_info) if _vt_info else False
                            if ok:
                                err = None
                                print(f"[validate_text] expected={expected_value!r} actual={actual_value!r} mode={match_mode}: PASS - passed after {_vt_elapsed:.1f}s")
                            else:
                                err = (
                                    f"validate_text: expected {'exactly ' if match_mode == 'exact' else ''}"
                                    f"{expected_value!r}, got {actual_value!r} - checked for {_vt_elapsed:.1f}s"
                                )
                                print(f"[validate_text] {err}")''',
)

# ---- validate_visible ----
sub(
r'''                    elif action_type == "validate_visible":
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "visible").strip().lower()
                        expected_value = expected_state
                        # a step validating "hidden" must not fail just
                        # because the element hasn't rendered YET - a
                        # short bounded poll either way, same centralized
                        # timeout as every other new validation action
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            is_visible = False
                            found = False
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Visible", shot_dir=shot_dir)
                            try:
                                is_visible = el.is_visible()
                            except Exception:
                                is_visible = False
                        actual_value = "visible" if is_visible else "hidden"
                        if expected_state == "hidden":
                            ok = not is_visible
                        else:
                            ok = is_visible
                        err = None if ok else f"validate_visible: element is {actual_value}, expected {expected_state}"
                        print(f"[validate_visible] expected={expected_state} actual={actual_value}: {'PASS' if ok else 'FAIL'}")''',
r'''                    elif action_type == "validate_visible":
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "visible").strip().lower()
                        expected_value = expected_state
                        # a step validating "hidden" must not fail just
                        # because the element hasn't rendered YET (or has
                        # already been removed) - "not found" is itself a
                        # valid, stable "hidden" reading, unchanged from
                        # before. _VV_NOT_FOUND is a sentinel (never None) so
                        # poll_until_expected still calls read_fn/is_expected
                        # on this attempt instead of treating it as "nothing
                        # resolved yet, keep trying" - a genuinely-never-
                        # appearing element with expected_state="hidden"
                        # must PASS promptly, not wait out the full timeout.
                        _VV_NOT_FOUND = object()

                        def _vv_resolve(_page, _lp):
                            _el, _s, _a = _resolve_with_timeout(_page, _lp)
                            return _el if _el is not None else _VV_NOT_FOUND

                        def _vv_read(e):
                            if e is _VV_NOT_FOUND:
                                return {"found": False, "is_visible": False}
                            try:
                                v = e.is_visible()
                            except Exception:
                                v = False
                            return {"found": True, "is_visible": v}

                        def _vv_expected(info):
                            return (not info["is_visible"]) if expected_state == "hidden" else info["is_visible"]

                        _el_raw, _vv_info, _vv_elapsed = poll_until_expected(
                            page, lp, resolve_fn=_vv_resolve, read_fn=_vv_read, is_expected=_vv_expected,
                        )
                        found = bool((_vv_info or {}).get("found"))
                        el = _el_raw if found else None
                        is_visible = bool((_vv_info or {}).get("is_visible"))
                        if found:
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Visible", shot_dir=shot_dir)
                        actual_value = "visible" if is_visible else "hidden"
                        ok = _vv_expected(_vv_info) if _vv_info else (expected_state == "hidden")
                        if ok:
                            err = None
                            print(f"[validate_visible] expected={expected_state} actual={actual_value}: PASS - passed after {_vv_elapsed:.1f}s")
                        else:
                            err = f"validate_visible: element is {actual_value}, expected {expected_state} - checked for {_vv_elapsed:.1f}s"
                            print(f"[validate_visible] {err}")''',
)

# ---- validate_value ----
sub(
r'''                    elif action_type == "validate_value":
                        lp = step.get("locator_profile") or {}
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "exact").strip().lower()
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_value: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Value", shot_dir=shot_dir)
                            try:
                                actual_value = _extract_element_value(el) or ""
                            except Exception:
                                actual_value = ""
                            if match_mode == "contains":
                                ok = expected_value.strip().lower() in actual_value.lower()
                            else:
                                ok = actual_value.strip() == expected_value.strip()
                            err = None if ok else f"validate_value: expected {expected_value!r}, got {actual_value!r}"
                            print(f"[validate_value] expected={expected_value!r} actual={actual_value!r} mode={match_mode}: {'PASS' if ok else 'FAIL'}")''',
r'''                    elif action_type == "validate_value":
                        lp = step.get("locator_profile") or {}
                        expected_value = step.get("value") or ""
                        match_mode = (step.get("match_mode") or "exact").strip().lower()

                        def _vval_read(e):
                            try:
                                v = _extract_element_value(e) or ""
                            except Exception:
                                v = ""
                            return {"value": v}

                        def _vval_expected(info):
                            v = info["value"]
                            return expected_value.strip().lower() in v.lower() if match_mode == "contains" else v.strip() == expected_value.strip()

                        el, _vval_info, _vval_elapsed = poll_until_expected(
                            page, lp, read_fn=_vval_read, is_expected=_vval_expected,
                        )
                        if el is None:
                            found, ok, err = False, False, "validate_value: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Value", shot_dir=shot_dir)
                            actual_value = (_vval_info or {}).get("value", "")
                            ok = _vval_expected(_vval_info) if _vval_info else False
                            if ok:
                                err = None
                                print(f"[validate_value] expected={expected_value!r} actual={actual_value!r} mode={match_mode}: PASS - passed after {_vval_elapsed:.1f}s")
                            else:
                                err = f"validate_value: expected {expected_value!r}, got {actual_value!r} - checked for {_vval_elapsed:.1f}s"
                                print(f"[validate_value] {err}")''',
)

# ---- validate_enabled ----
sub(
r'''                    elif action_type == "validate_enabled":
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "enabled").strip().lower()
                        expected_value = expected_state
                        el, strategy, _attempt = _resolve_with_timeout(page, lp)
                        if el is None:
                            found, ok, err = False, False, "validate_enabled: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Enabled", shot_dir=shot_dir)
                            try:
                                is_disabled = el.is_disabled()
                            except Exception:
                                is_disabled = False
                            actual_value = "disabled" if is_disabled else "enabled"
                            ok = (actual_value == expected_state)
                            err = None if ok else f"validate_enabled: element is {actual_value}, expected {expected_state}"
                            print(f"[validate_enabled] expected={expected_state} actual={actual_value}: {'PASS' if ok else 'FAIL'}")''',
r'''                    elif action_type == "validate_enabled":
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "enabled").strip().lower()
                        expected_value = expected_state

                        def _vena_read(e):
                            try:
                                d = e.is_disabled()
                            except Exception:
                                d = False
                            return {"is_disabled": d}

                        def _vena_expected(info):
                            return ("disabled" if info["is_disabled"] else "enabled") == expected_state

                        el, _vena_info, _vena_elapsed = poll_until_expected(
                            page, lp, read_fn=_vena_read, is_expected=_vena_expected,
                        )
                        if el is None:
                            found, ok, err = False, False, "validate_enabled: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Enabled", shot_dir=shot_dir)
                            actual_value = "disabled" if (_vena_info or {}).get("is_disabled") else "enabled"
                            ok = (actual_value == expected_state)
                            if ok:
                                err = None
                                print(f"[validate_enabled] expected={expected_state} actual={actual_value}: PASS - passed after {_vena_elapsed:.1f}s")
                            else:
                                err = f"validate_enabled: element is {actual_value}, expected {expected_state} - checked for {_vena_elapsed:.1f}s"
                                print(f"[validate_enabled] {err}")''',
)

open(p, 'w', encoding='utf-8').write(s)
print('patched OK')
