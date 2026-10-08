"""TEST-ONLY: unit checks for the drag value comparison helpers (_drag_reached / _drag_start_matches),
loaded from a freshly generated script (the helpers only exist inside the generator's template)."""
import importlib.util
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from generator.script_generator import generate_script  # noqa: E402

tc = {"name": "reached_check", "start_url": "http://x/", "actions": [
    {"action_type": "navigate", "value": None, "locator_profile": {}, "page_url": "http://x/"}]}
sp = generate_script(tc, out_name="reached_check.py", output_dir=Path(tempfile.mkdtemp()))
spec = importlib.util.spec_from_file_location("reached_check_mod", sp)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def v(text):
    return {"kind": "nearby_text", "value": text}


before, target = v("₹300 - ₹5,300+"), v("₹1,400 - ₹5,300+")   # drag changed only the FIRST number
cases = [
    ("exact match", v("₹1,400 - ₹5,300+"), True),
    ("other number (domain max) drifted, dragged number exact", v("₹1,400 - ₹4,300+"), True),
    ("dragged number wrong", v("₹1,200 - ₹4,300+"), False),
    ("dragged number wrong, other exact", v("₹1,200 - ₹5,300+"), False),
    ("different shape (one number)", v("₹1,400"), False),
    ("no reading", None, False),
]
for label, cur, want in cases:
    got = m._drag_reached(cur, target, before)
    print(f"{'ok ' if got == want else 'BAD'} _drag_reached: {label}: {got}")
    assert got == want, label

# nothing changed (before == target): must be exact equality
same = v("₹100 - ₹2,900")
assert m._drag_reached(v("₹100 - ₹2,900"), same, same) is True
assert m._drag_reached(v("₹100 - ₹2,800"), same, same) is False
# single-number aria value
assert m._drag_reached({"kind": "aria_value", "value": "20.0", "text": "20.00"}, {"kind": "aria_value", "value": "20.0", "text": "20.00"}, None)
assert not m._drag_reached({"kind": "aria_value", "value": "10.0", "text": "10.00"}, {"kind": "aria_value", "value": "20.0", "text": "20.00"}, {"kind": "aria_value", "value": "0.0", "text": "0.00"})
# start-state test used to choose the pointer mapping
assert m._drag_start_matches(v("₹300 - ₹4,300+"), before, target)          # start state equal in the changed number
assert not m._drag_start_matches(v("₹800 - ₹5,300+"), before, target)
print("\nPASS: drag value comparison looks at the numbers the drag changed, else exact equality")
