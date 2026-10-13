p = 'generator/script_generator.py'
lines = open(p, encoding='utf-8').read().split('\n')
start = None
for i, l in enumerate(lines):
    if l.strip() == 'elif action_type == "validate_checked":':
        start = i
        break
assert start is not None
end = None
for i in range(start + 1, len(lines)):
    if 'elif action_type == "count_elements":' in lines[i]:
        end = i
        break
assert end is not None

new_block = r'''                    elif action_type == "validate_checked":
                        # Read-only: reads state via _resolve_checkbox_state
                        # (see its own docstring for the a-f priority order)
                        # instead of trusting whatever element the recording's
                        # locator happens to resolve to - a real site's custom
                        # checkbox is very often a hidden native <input> plus
                        # a separate, visible styled <div>/<span> as the tick
                        # box (CONFIRMED live: Pick Element saved that visible
                        # div, which has no checked property of its own -
                        # reading it directly always read as "unchecked",
                        # regardless of the real, hidden input's actual
                        # state). Never clicks/focuses/changes anything -
                        # existing locator resolution/fallback strategies
                        # (_resolve_with_timeout) are unchanged; only the
                        # "read checked state" part is replaced.
                        #
                        # Polls (re-locating AND re-running the helper each
                        # time, never a fixed sleep) until the state matches
                        # what's expected or the deadline runs out - the
                        # existing recorded action's target is unaffected,
                        # this only guards against a site that re-renders the
                        # list after a filter click hasn't finished doing so
                        # yet. STEP_TIME_BUDGET_S (this project's existing,
                        # already-configurable per-step timeout - there is no
                        # separate per-step timeout field in the recording
                        # itself) is reused as the deadline rather than
                        # inventing a second, parallel timeout knob.
                        lp = step.get("locator_profile") or {}
                        expected_state = (step.get("expected_state") or "checked").strip().lower()
                        expected_value = expected_state
                        _vc_deadline = time.monotonic() + STEP_TIME_BUDGET_S
                        _vc_state_info = None
                        el = None
                        while True:
                            el, strategy, _attempt = _resolve_with_timeout(page, lp)
                            if el is not None:
                                _vc_state_info = _resolve_checkbox_state(el)
                                if _vc_state_info.get("state") == expected_state:
                                    break
                                # a genuinely-not-a-checkbox target (or an
                                # ambiguous one) is a structural fact about
                                # the picked element, not a timing issue - it
                                # will never resolve differently by polling
                                # again, so stop immediately rather than
                                # burning the whole timeout on a re-render
                                # that will never happen.
                                if _vc_state_info.get("state") == "not_a_checkbox":
                                    break
                            if time.monotonic() >= _vc_deadline:
                                break
                            try:
                                page.wait_for_timeout(200)
                            except Exception:
                                break

                        if el is None:
                            found, ok, err = False, False, "validate_checked: element not found"
                        else:
                            found = True
                            validate_shot_override = _draw_validation_highlight(page, el, "Validate Checked", shot_dir=shot_dir)
                            actual_value = (_vc_state_info or {}).get("state")
                            _vc_how = (_vc_state_info or {}).get("resolvedHow")
                            _vc_tag = (_vc_state_info or {}).get("resolvedTag")
                            _vc_ambiguous = (_vc_state_info or {}).get("ambiguousCount")
                            # only worth mentioning when the resolved control
                            # ISN'T simply the element the recording already
                            # pointed at (a plain native checkbox picked
                            # directly, or a role="checkbox" element read via
                            # aria-checked on itself) - those two read exactly
                            # what was picked, nothing to explain.
                            _resolved_note = (
                                f" (resolved via {_vc_how} from <{_vc_tag}>)"
                                if _vc_how in ("label.control", "descendant", "ancestor") and _vc_tag
                                else ""
                            )
                            if actual_value == "not_a_checkbox":
                                ok = False
                                if _vc_how == "ambiguous":
                                    err = f"validate_checked: ambiguous: {_vc_ambiguous} checkboxes near the picked element"
                                else:
                                    err = (
                                        f"validate_checked: picked element is a <{_vc_tag}>, not a checkbox, "
                                        f"and no single associated checkbox was found"
                                    )
                                print(f"[validate_checked] {err}")
                            else:
                                ok = (actual_value == expected_state)
                                err = None if ok else f"validate_checked: checkbox is {actual_value}, expected {expected_state}{_resolved_note}"
                                print(
                                    f"[validate_checked] expected={expected_state} actual={actual_value}: "
                                    f"{'PASS' if ok else 'FAIL'}{_resolved_note}"
                                )
                                _label = (
                                    lp.get("accessible_name") or _strip_icon_font_text(lp.get("text") or "") or
                                    lp.get("aria_label") or lp.get("placeholder") or lp.get("tag") or "checkbox"
                                )
                                _label = " ".join(str(_label).split())[:40]
                                print(
                                    f"Validation: checkbox [{_label}] is {expected_state} -> "
                                    f"{'PASSED' if ok else 'FAILED'} (expected {expected_state}, actual {actual_value}){_resolved_note}"
                                )
'''.split('\n')
if new_block[-1] == '':
    new_block.pop()

lines[start:end] = new_block
open(p, 'w', encoding='utf-8').write('\n'.join(lines))
print('patched. new total lines:', len(lines))
