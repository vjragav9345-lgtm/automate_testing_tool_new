"""Shared harness for the Phase 4 (Myntra hover/card/scroll/tab bug-fix)
offline fixture tests - generates a real replay script from a test_case
dict via the REAL, unmodified generator.script_generator, runs it, and
captures stdout so a test can assert on both the structured report and
the printed [hover-reveal]/[href-tier]/[tab-open-recovery]/etc log lines.
"""
import importlib.util
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from generator.script_generator import generate_script  # noqa: E402


def run_test_case(test_case, label, headless=True):
    """Generates + runs test_case, returns (result_dict, captured_stdout)."""
    scratch_dir = Path(tempfile.mkdtemp(prefix=f"phase4_{label}_"))
    script_path = generate_script(test_case, out_name=f"phase4_{label}_script.py", output_dir=scratch_dir)
    spec = importlib.util.spec_from_file_location(f"phase4_{label}_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output_json = scratch_dir / "report.json"
    screenshot_dir = scratch_dir / "screenshots"
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = module.run(
            test_case["start_url"], output_json_path=output_json,
            screenshot_dir=screenshot_dir, headless=headless,
        )
    captured = buf.getvalue()
    print(captured)  # still show it live in this process's own output
    return result, captured


def step_lp(id_=None, text=None, element_text=None, href=None, product_id=None,
            css_path=None, xpath=None, tag="a", role=None, attributes=None, aria_label=None):
    return {
        "id": id_, "name": None, "role": role, "aria_label": aria_label,
        "accessible_name": text, "placeholder": None, "title": None,
        "href": href, "product_id": product_id, "css_path": css_path, "xpath": xpath,
        "text": text, "element_text": element_text or text, "tag": tag,
        "attributes": attributes or {}, "cross_boundary": False,
        "icon_class_hint": None,
    }
