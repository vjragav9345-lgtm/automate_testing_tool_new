"""TEST-ONLY comparison run (item 8: Myntra regression check) - runs the
SAME Myntra recording through the OLD (script_generator.py.bak_otp_fix3,
pre-Phase-1-fix) and NEW (current) resolver, back to back, and diffs the
per-step results. Reports any step that passed under OLD and is now
rejected under NEW (the stricter target-verification gate), with the
rejection reason. Never touches the Sportzia site or its Send OTP budget.

    venv/Scripts/python.exe tests/myntra_compare_old_new.py
"""
import importlib.machinery
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def _load_generator_module(path, mod_name):
    # explicit SourceFileLoader: the .bak_otp_fix3 backup's extension isn't
    # .py, so spec_from_file_location can't auto-detect a loader for it
    loader = importlib.machinery.SourceFileLoader(mod_name, str(path))
    spec = importlib.util.spec_from_loader(mod_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def run_with_generator(generator_module, recording, label):
    actions = recording["actions"]
    start_url = recording["start_url"]
    if not actions or actions[0].get("action_type") != "navigate":
        actions = [{"action_type": "navigate", "page_url": start_url, "page_id": 0}] + list(actions)

    test_case = {"name": f"myntra_compare_{label}", "start_url": start_url, "actions": actions}
    scratch_dir = Path(tempfile.mkdtemp(prefix=f"myntra_compare_{label}_"))
    script_path = generator_module.generate_script(
        test_case, out_name=f"myntra_compare_{label}_script.py", output_dir=scratch_dir
    )
    spec = importlib.util.spec_from_file_location(f"myntra_compare_{label}_script", script_path)
    run_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_module)

    output_json = scratch_dir / "report.json"
    screenshot_dir = scratch_dir / "screenshots"
    result = run_module.run(
        start_url, output_json_path=output_json, screenshot_dir=screenshot_dir, headless=True,
    )
    return result


def main():
    recording_path = BASE_DIR / "storage" / "recordings" / "edited" / "myntra_men_tshirt_full_flow_edited.json"
    with open(recording_path, "r", encoding="utf-8") as f:
        recording = json.load(f)

    old_path = BASE_DIR / "generator" / "script_generator.py.bak_otp_fix3"
    new_path = BASE_DIR / "generator" / "script_generator.py"

    print("===== running OLD (pre-Phase-1-fix) =====", flush=True)
    old_module = _load_generator_module(old_path, "script_generator_old")
    old_result = run_with_generator(old_module, recording, "old")

    print("\n===== running NEW (current) =====", flush=True)
    new_module = _load_generator_module(new_path, "script_generator_new")
    new_result = run_with_generator(new_module, recording, "new")

    old_steps = {s["index"]: s for s in old_result.get("steps", [])}
    new_steps = {s["index"]: s for s in new_result.get("steps", [])}

    print("\n\n===== COMPARISON =====")
    regressions = []
    for idx in sorted(set(old_steps) | set(new_steps)):
        o = old_steps.get(idx, {})
        n = new_steps.get(idx, {})
        o_ok = o.get("success")
        n_ok = n.get("success")
        flag = ""
        if o_ok and not n_ok:
            flag = " <== REGRESSION (passed under OLD, rejected under NEW)"
            regressions.append({
                "index": idx, "action_type": n.get("action_type"),
                "old_strategy": (o.get("locator_report") or {}).get("strategy"),
                "new_error": n.get("error"),
            })
        elif (not o_ok) and n_ok:
            flag = " (improvement: failed under OLD, passes under NEW)"
        print(
            f"step {idx} [{n.get('action_type') or o.get('action_type')}]: "
            f"OLD success={o_ok} strategy={(o.get('locator_report') or {}).get('strategy')} | "
            f"NEW success={n_ok} strategy={(n.get('locator_report') or {}).get('strategy')} "
            f"err={n.get('error')!r}{flag}"
        )

    print(f"\nOLD status: {old_result.get('status')}, NEW status: {new_result.get('status')}")
    if regressions:
        print("\n===== REGRESSIONS =====")
        for r in regressions:
            print(json.dumps(r, indent=2))
    else:
        print("\nNO REGRESSIONS - every step that passed under OLD still passes under NEW")

    out_path = BASE_DIR / "tests" / "myntra_compare_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"old": old_result, "new": new_result, "regressions": regressions}, f, indent=2, default=str)
    print(f"\nfull comparison saved to {out_path}")


if __name__ == "__main__":
    main()
