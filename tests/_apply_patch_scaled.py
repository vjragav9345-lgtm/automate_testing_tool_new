"""One-off patch applier (TEST-SIDE helper): drag pointer mapping = grab the thumb where it IS (live element
position) and scale only the DISPLACEMENT by the live/recorded track size; absolute track-fraction and recorded
absolute mappings stay as candidates (chosen by where they land, for sliders exposing a value)."""
p = 'generator/script_generator.py'
s = open(p, encoding='utf-8').read()


def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


sub('''def _drag_point_mappers(page, step, live_box):''', '''def _drag_point_mappers(page, step, live_box, off_x, off_y):''')

sub('''      "track"    - when the recording carries `track` (the rail/track the
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
    lands (see the drag branch)."""''', '''      "scaled"   - the pointer GRABS the control where it is now (the live
                   box of the resolved element plus the recorded grab
                   offset - a 12px thumb must be hit where it currently
                   sits, and it moves when the site's data changes the
                   slider's domain), and only the DISPLACEMENT is
                   resolution-independent: scaled by live-track-extent /
                   recorded-track-extent along the drag axis, so a rail
                   that is wider/narrower at replay still moves the same
                   fraction of its length. Needs a recorded `track`
                   (action_capture.js's _findDragTrack) measurable live;
      "relative" - the same grab point with the recorded displacement
                   unscaled (what replay always did before);
      "track"    - absolute: both axes taken from the live track (a
                   fraction of its extent along it, the recorded offset
                   from its edge across it) - right when the resolved
                   element is only a stand-in and cannot be trusted for
                   position;
      "recorded" - the recorded absolute viewport coordinates.
    Which one is right depends on things only the page knows, so the caller
    picks by testing where each lands whenever the control exposes a value
    (see the drag branch), and otherwise takes the first."""''')

sub('''                out.append(("track", mapped))
    except Exception:
        pass

    out.append(("relative", lambda dx, dy: (live_box["x"] + dx, live_box["y"] + dy)))
''', '''                sx = (tb["width"] / rt["width"]) if axis == "x" else 1.0
                sy = (tb["height"] / rt["height"]) if axis == "y" else 1.0
                out.append(("scaled", lambda dx, dy: (
                    live_box["x"] + off_x + (dx - off_x) * sx,
                    live_box["y"] + off_y + (dy - off_y) * sy,
                )))
                out.append(("track", mapped))
    except Exception:
        pass

    out.insert(1 if out else 0, ("relative", lambda dx, dy: (live_box["x"] + dx, live_box["y"] + dy)))
''')

sub('''                        _mappers = _drag_point_mappers(page, step, _box)''', '''                        _mappers = _drag_point_mappers(page, step, _box, _off_x, _off_y)''')
open(p, 'w', encoding='utf-8').write(s)
print('patched OK')
