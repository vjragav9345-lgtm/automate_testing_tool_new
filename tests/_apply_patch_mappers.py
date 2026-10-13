"""One-off patch applier (TEST-SIDE helper, not part of the product): applies the drag tier-order and
candidate-mapper changes to generator/script_generator.py. Kept only so the exact change is reviewable."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()

# ---- (1) tier order for drag sources
old = '''    element_found = False
    last_err = None
    position_fallback_info = {}'''
new = '''    if action_type == "drag":
        # A drag source is one specific control (a slider thumb), not a
        # repeating list item: its literal recorded structural path
        # identifies it, whereas position_fallback guesses "the Nth of the
        # similar siblings" from the path's nth-of-type numbers - which is
        # off by one whenever a non-item sibling precedes the items (a
        # slider's connects bar precedes its handles) and lands on the
        # wrong handle. Try css_path/xpath first for drags only; every
        # other action type keeps the order above exactly.
        _structural_tiers = [t for t in tiers if t[0] in ("css_path", "xpath")]
        tiers = [t for t in tiers if t[0] not in ("css_path", "xpath")]
        _pf_at = next(i for i, t in enumerate(tiers) if t[0] == "position_fallback")
        tiers[_pf_at:_pf_at] = _structural_tiers

    element_found = False
    last_err = None
    position_fallback_info = {}'''
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)

# ---- (2) candidate mappers replace the single mapper
i0 = s.index('def _drag_point_mapper(page, step, live_box):')
i1 = s.index('def _drag_verify_held(')
new_mapper = '''def _drag_point_mappers(page, step, live_box):
    """Candidate mappings from a point recorded as an offset (dx, dy) from
    the source's top-left AT MOUSEDOWN to a live viewport coordinate, most
    trusted first: [(name, f), ...].
      "track"    - when the recording carries `track` (the rail/track the
                   source travels along, see action_capture.js's
                   _findDragTrack) and it can be measured live: BOTH axes
                   come from the live track (a fraction of its extent along
                   it, the recorded offset from its edge across it), so a
                   rail that is wider/narrower/moved at replay still lands
                   on the same logical value;
      "relative" - translation from the live box of the element the tier
                   chain resolved (what replay always did before);
      "recorded" - the recorded absolute viewport coordinates (the page is
                   normally in exactly the recorded scroll/layout state).
    Which one is right depends on things only the page knows - a stand-in
    resolved element poisons "relative", a moving element mistaken for a
    track poisons "track" - so the caller picks by testing where each one
    lands (see the drag branch)."""
    rec_src = step.get("bounding_box") or {}
    track = step.get("track") or {}
    out = []

    try:
        axis = track.get("axis")
        rt = track.get("rect_at_down") or {}
        lp = track.get("locator_profile")
        if axis in ("x", "y") and lp and rt.get("width" if axis == "x" else "height") and rec_src.get("x") is not None:
            t_el = _resolve_element(page, lp)
            tb = t_el.bounding_box() if t_el is not None else None
            if tb and tb.get("width" if axis == "x" else "height"):
                def mapped(dx, dy):
                    if axis == "x":
                        frac = ((rec_src["x"] + dx) - rt["x"]) / rt["width"]
                        return tb["x"] + frac * tb["width"], tb["y"] + ((rec_src["y"] + dy) - rt["y"])
                    frac = ((rec_src["y"] + dy) - rt["y"]) / rt["height"]
                    return tb["x"] + ((rec_src["x"] + dx) - rt["x"]), tb["y"] + frac * tb["height"]
                out.append(("track", mapped))
    except Exception:
        pass

    out.append(("relative", lambda dx, dy: (live_box["x"] + dx, live_box["y"] + dy)))

    if rec_src.get("x") is not None and rec_src.get("y") is not None:
        out.append(("recorded", lambda dx, dy: (rec_src["x"] + dx, rec_src["y"] + dy)))
    return out


'''
s = s[:i0] + new_mapper + s[i1:]

# ---- use in the drag branch
old = '''                        _map_pt, _used_track = _drag_point_mapper(page, step, _box)
                        _start_x, _start_y = _map_pt(
                            _start_off.get("x", _box["width"] / 2), _start_off.get("y", _box["height"] / 2),
                        )
                        _end_x, _end_y = _map_pt(
                            _start_off.get("x", _box["width"] / 2) + _delta.get("dx", 0),
                            _start_off.get("y", _box["height"] / 2) + _delta.get("dy", 0),
                        )
                        if _used_track:
                            print(f"[drag] mapped along the live track (axis={(step.get('track') or {}).get('axis')})")
                        page.mouse.move(_start_x, _start_y)
                        _under = _drag_slider_under_pointer(page, _start_x, _start_y) if _value_after else None
                        if _under is not None:'''
new = '''                        _off_x = _start_off.get("x", _box["width"] / 2)
                        _off_y = _start_off.get("y", _box["height"] / 2)
                        _mappers = _drag_point_mappers(page, step, _box)
                        _map_name, _map_pt = _mappers[0]
                        _under = None
                        if _value_after and len(_mappers) > 1:
                            # pick the mapping whose start point lands on a
                            # slider that currently shows the RECORDED
                            # before-value (the handle the user grabbed);
                            # failing that, on any slider; failing that,
                            # keep the most trusted mapping
                            _any_hit = None
                            for _cand_name, _cand_f in _mappers:
                                _cx, _cy = _cand_f(_off_x, _off_y)
                                _cu = _drag_slider_under_pointer(page, _cx, _cy)
                                if _cu is None:
                                    continue
                                if _any_hit is None:
                                    _any_hit = (_cand_name, _cand_f, _cu)
                                if _drag_values_equal(
                                    _captureDragValueSnapshot_py(_cu), step.get("value_before")
                                ):
                                    _map_name, _map_pt, _under = _cand_name, _cand_f, _cu
                                    break
                            else:
                                if _any_hit is not None:
                                    _map_name, _map_pt, _under = _any_hit
                        _start_x, _start_y = _map_pt(_off_x, _off_y)
                        _end_x, _end_y = _map_pt(
                            _off_x + _delta.get("dx", 0), _off_y + _delta.get("dy", 0),
                        )
                        print(f"[drag] pointer positions from the '{_map_name}' mapping")
                        page.mouse.move(_start_x, _start_y)
                        if _under is None and _value_after:
                            _under = _drag_slider_under_pointer(page, _start_x, _start_y)
                        if _under is not None:'''
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('patched OK')
