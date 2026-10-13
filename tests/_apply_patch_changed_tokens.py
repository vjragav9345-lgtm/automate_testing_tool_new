"""One-off patch applier (TEST-SIDE helper, not part of the product): makes the drag value comparison look
only at the numbers the drag actually CHANGED (recorded before -> recorded after)."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()


def sub(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:70])
    s = s.replace(old, new)


# helpers, right after _drag_numbers
sub('''def _drag_point_mappers(page, step, live_box):''', '''def _drag_changed_indices(before, target):
    """Positions (in the numeric tokens of a drag value) that the recorded
    drag CHANGED, i.e. where `before` and `target` differ - None when that
    can't be told (no numbers, different shapes, nothing changed)."""
    bn, tn = _drag_numbers(before), _drag_numbers(target)
    if bn and len(bn) == len(tn):
        idx = [i for i in range(len(tn)) if bn[i] != tn[i]]
        if idx:
            return idx
    return None


def _drag_reached(cur, target, before):
    """Does `cur` show the recorded value? Exactly equal, or - when the
    label carries several numbers and the recorded drag changed only some
    of them - equal in the numbers the drag changed. The others (the
    other thumb, a domain maximum that follows live inventory data, a
    running total) are not part of "did THIS drag land" and legitimately
    differ between record time and replay time: CONFIRMED on a real
    price-range filter whose label "1,400 - 5,300+" carried a domain
    maximum that read 4,300+ an hour later, while the dragged number was
    exact."""
    if cur is None or target is None:
        return False
    if _drag_values_equal(cur, target):
        return True
    idx = _drag_changed_indices(before, target)
    if not idx:
        return False
    cn, tn = _drag_numbers(cur), _drag_numbers(target)
    return len(cn) == len(tn) and all(cn[i] == tn[i] for i in idx)


def _drag_start_matches(live, before, target):
    """Is `live` (read from the slider under the candidate start point) the
    state the recording started from? Equal to the recorded before-value, or
    equal to it in the numbers the drag changed."""
    if live is None or before is None:
        return False
    if _drag_values_equal(live, before):
        return True
    idx = _drag_changed_indices(before, target)
    if not idx:
        return False
    ln, bn = _drag_numbers(live), _drag_numbers(before)
    return len(ln) == len(bn) and all(ln[i] == bn[i] for i in idx)


def _drag_point_mappers(page, step, live_box):''')

# _drag_verify_held
sub('''    while not _drag_values_equal(cur, target) and time.monotonic() < deadline:
        page.wait_for_timeout(60)
        cur = read()
    if _drag_values_equal(cur, target):
        return True, cur, 0''', '''    while not _drag_reached(cur, target, recorded_before) and time.monotonic() < deadline:
        page.wait_for_timeout(60)
        cur = read()
    if _drag_reached(cur, target, recorded_before):
        return True, cur, 0''')
sub('''        idxs = [i for i in range(len(tn)) if cn[i] != tn[i]]
        if not idxs:
            break
        idx = idxs[0]''', '''        # steer by the number(s) the drag changed, not by whichever number
        # happens to differ first (see _drag_reached)
        idxs = [i for i in (_drag_changed_indices(recorded_before, target) or range(len(tn))) if cn[i] != tn[i]]
        if not idxs:
            break
        idx = idxs[0]''')
sub('''        cur = new
        if _drag_values_equal(cur, target):
            return True, cur, nudges''', '''        cur = new
        if _drag_reached(cur, target, recorded_before):
            return True, cur, nudges''')

# _drag_poll_for_value
sub('''def _drag_poll_for_value(page, thumb_el, target, budget_s):''', '''def _drag_poll_for_value(page, thumb_el, target, budget_s, before=None):''')
sub('''    while not _drag_values_equal(cur, target) and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        cur = _captureDragValueSnapshot_py(thumb_el)
    return _drag_values_equal(cur, target), cur''', '''    while not _drag_reached(cur, target, before) and time.monotonic() < deadline:
        page.wait_for_timeout(100)
        cur = _captureDragValueSnapshot_py(thumb_el)
    return _drag_reached(cur, target, before), cur''')

# drag branch: start-candidate test, post-release poll, final compare
sub('''                                if _drag_values_equal(
                                    _captureDragValueSnapshot_py(_cu), step.get("value_before")
                                ):''', '''                                if _drag_start_matches(
                                    _captureDragValueSnapshot_py(_cu), step.get("value_before"), _value_after,
                                ):''')
sub('''                        _drag_release_ok, _drag_held_val = _drag_poll_for_value(
                            page, _drag_src, _value_after, DRAG_RELEASE_POLL_BUDGET_S,
                        )''', '''                        _drag_release_ok, _drag_held_val = _drag_poll_for_value(
                            page, _drag_src, _value_after, DRAG_RELEASE_POLL_BUDGET_S,
                            before=step.get("value_before"),
                        )''')
sub('''                            if _drag_values_equal(_cur_final, _value_after):''', '''                            if _drag_reached(_cur_final, _value_after, step.get("value_before")):''')

open(p, 'w', encoding='utf-8').write(s)
print('patched OK')
