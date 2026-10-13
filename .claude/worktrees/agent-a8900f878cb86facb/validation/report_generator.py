"""Builds the self-contained HTML report for a test run.

Screenshots get inlined as base64 data URIs so the report is a single
file someone can email around without also having to hand over the
screenshots folder.
"""
import base64
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from storage.repository import BASE_DIR

logger = logging.getLogger(__name__)

TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _to_data_uri(rel_path):
    if not rel_path:
        return None
    full = BASE_DIR / rel_path
    if not full.exists():
        return None
    try:
        data = base64.b64encode(full.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except OSError as e:
        logger.warning("couldn't embed screenshot %s: %s", rel_path, e)
        return None


def generate_report(execution_result: dict, output_dir: Path = None) -> Path:
    template = _env.get_template("report.html")

    steps = []
    for s in execution_result.get("steps", []):
        steps.append({**s, "screenshot_data": _to_data_uri(s.get("screenshot"))})

    ui_elements = execution_result.get("ui_elements", [])
    execution_summary = {
        "total": len(steps),
        "passed": sum(1 for s in steps if s.get("success")),
        "failed": sum(1 for s in steps if not s.get("success")),
        "first_failed": next((s for s in steps if not s.get("success")), None),
    }
    ui_summary = {
        "total": len(ui_elements),
        "found": sum(1 for e in ui_elements if e.get("element_found")),
        "missing": sum(1 for e in ui_elements if not e.get("element_found")),
        "status": execution_result.get("ui_elements_status"),
    }

    product_validation = execution_result.get("product_validation")
    if product_validation:
        product_validation = {**product_validation, "screenshot_data": _to_data_uri(product_validation.get("screenshot"))}

    html = template.render(
        result=execution_result,
        steps=steps,
        ui_elements=ui_elements,
        ui_summary=ui_summary,
        execution_summary=execution_summary,
        product_validation=product_validation,
        final_screenshot_data=_to_data_uri(execution_result.get("final_screenshot")),
        generated_at=datetime.now().isoformat(),
    )

    # a caller with a per-run output folder already (the dashboard's Run
    # Test flow - see execute_test in executor/run_execution.py) passes
    # it here so the HTML report lands alongside that same run's
    # screenshots and report.json instead of its own separate top-level
    # location. Falls back to the old shared REPORTS_DIR only for a
    # caller that doesn't have a per-run folder to give it.
    if output_dir:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / "report.html"
    else:
        run_id = execution_result.get("run_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"report_{run_id}.html"
    path.write_text(html, encoding="utf-8")
    logger.info("wrote report to %s", path)
    return path
