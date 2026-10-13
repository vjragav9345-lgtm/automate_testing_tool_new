p = 'generator/script_generator.py'
lines = open(p, encoding='utf-8').read().split('\n')


def find(marker, start=0):
    for i in range(start, len(lines)):
        if lines[i].strip() == marker:
            return i
    raise ValueError(marker)


s = find('elif action_type == "validate_element":', 5000)
_vt = find('elif action_type == "validate_text":', 5000)
e = None
for i in range(s, _vt):
    if lines[i].strip() == 'strategy, found, ok, err = None, False, False, str(ve)':
        e = i + 1
        break
assert e is not None

new_block = r'''                    elif action_type == "validate_element":
                        # Checks whether a specific element on the page
                        # is disabled (check: "disabled") or enabled
                        # (check: "enabled"). Does NOT alter the page.
                        # success=True when the check matches reality.
                        #
                        # CONFIRMED REAL BUG this fixes: read el.is_disabled()
                        # exactly ONCE, right after a single resolve - a real
                        # site whose own JS re-enables/disables the target a
                        # couple of seconds AFTER the preceding click (a
                        # loading state, on any site) was read mid-transition
                        # and failed, even though the state the recording
                        # actually expects arrives moments later. Uses the
                        # SAME shared poll_until_expected every other
                        # validator now uses - never a second, separate
                        # polling implementation - with its OWN existing
                        # locator chain (text/role/css_path/xpath) passed in
                        # as resolve_fn, so switching this onto the shared
                        # poll never also changes WHICH element it resolves,
                        # only that it's now polled rather than checked once.
                        lp = step.get("locator_profile") or {}
                        check_mode = (step.get("check") or "disabled").strip().lower()
                        _settle(page)

                        def _ve_resolve(_page, _lp):
                            for selector_fn in [
                                lambda: _page.get_by_text(_lp["text"], exact=False).first if _lp.get("text") else None,
                                lambda: _page.get_by_role(_lp["role"]).first if _lp.get("role") else None,
                                lambda: _page.locator(_lp["css_path"]).first if _lp.get("css_path") else None,
                                lambda: _page.locator(_lp["xpath"]).first if _lp.get("xpath") else None,
                            ]:
                                try:
                                    candidate = selector_fn()
                                    if candidate and candidate.count() > 0:
                                        return candidate
                                except Exception:
                                    pass
                            return None

                        try:
                            el, _ve_info, _ve_elapsed = poll_until_expected(
                                page, lp,
                                resolve_fn=_ve_resolve,
                                read_fn=lambda e: {"is_disabled": e.is_disabled()},
                                is_expected=lambda info: info["is_disabled"] == (check_mode == "disabled"),
                            )
                            if el is None:
                                strategy, found, ok, err = None, False, False, "Element not found for validate_element"
                            else:
                                is_disabled = (_ve_info or {}).get("is_disabled", False)
                                if check_mode == "disabled":
                                    ok = is_disabled
                                    result_msg = "disabled" if is_disabled else "enabled (expected disabled)"
                                elif check_mode == "enabled":
                                    ok = not is_disabled
                                    result_msg = "enabled" if not is_disabled else "disabled (expected enabled)"
                                else:
                                    ok, result_msg = False, f"unknown check mode: {check_mode!r}"
                                strategy, found = None, True
                                if not ok:
                                    err = f"validate_element failed: element is {result_msg} - checked for {_ve_elapsed:.1f}s"
                                    print(f"[validate_element] Element is {'disabled' if is_disabled else 'enabled'} → check '{check_mode}': FAIL ({result_msg}) after {_ve_elapsed:.1f}s")
                                else:
                                    err = None
                                    print(f"[validate_element] Element is {'disabled' if is_disabled else 'enabled'} → check '{check_mode}': PASS - passed after {_ve_elapsed:.1f}s")
                        except Exception as ve:
                            strategy, found, ok, err = None, False, False, str(ve)
'''
new_lines = new_block.split('\n')
if new_lines[-1] == '':
    new_lines.pop()

lines[s:e] = new_lines
open(p, 'w', encoding='utf-8').write('\n'.join(lines))
print('patched validate_element OK')
