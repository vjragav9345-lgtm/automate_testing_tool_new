"""TEST-ONLY diagnostic probe for the drag/scroll replay investigation.

Replays a recording through the REAL, unmodified generator + run(), while
wrapping Playwright's public API in-process (same technique as
tests/otp_real_run_wrapper.py) to log, per step:
  - every mouse down/move/up (drag path actually dispatched)
  - the drag source's live bounding box and the slider label text at
    mouse-down and after mouse-up
  - window.scrollY at every step boundary, plus every scroll event the page
    fired during the step (with the Playwright API call that was in flight)

Nothing here is imported by production code.

    venv/Scripts/python.exe tests/dragscroll_probe.py <recording.json> [--headless] [--no-stop] [--out result.json] [--max-steps N]
"""
import argparse
import builtins
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import BrowserContext, Locator, Mouse, Page  # noqa: E402

from generator.script_generator import generate_script  # noqa: E402
import importlib.machinery  # noqa: E402
import importlib.util as _ilu  # noqa: E402


def _load_generate_script(path):
    """generate_script from an arbitrary generator file (e.g. a backups/ copy) - lets the SAME probe
    replay a recording with the ORIGINAL (pre-fix) code for before/after comparisons."""
    loader = importlib.machinery.SourceFileLoader("gen_alt", str(path))
    spec = _ilu.spec_from_loader("gen_alt", loader)
    m = _ilu.module_from_spec(spec)
    loader.exec_module(m)
    return m.generate_script

_STEP_RE = re.compile(r"^\[(\d+)/(\d+)\]$")

STATE = {
    "step": 0,
    "page": None,
    "ctx": None,
    "step_pages": {},      # step -> [{url, scrollY, ...}, ...] for EVERY open page at the END of that step
    "events": [],          # chronological probe events
    "step_scroll": {},     # step -> scrollY at the START of the next step boundary (i.e. end of step)
    "drag": [],
    "cur_api": None,
}

SCROLL_INIT_JS = """
(() => {
  if (window.__probeScrollLog) return;
  window.__probeScrollLog = [];
  window.addEventListener('scroll', () => {
    window.__probeScrollLog.push([Math.round(performance.now()), window.scrollY]);
    if (window.__probeScrollLog.length > 400) window.__probeScrollLog.shift();
  }, {capture: true, passive: true});
})();
"""


def ev(kind, **kw):
    STATE["events"].append({"t": round(time.time(), 3), "step": STATE["step"], "kind": kind, **kw})


def read_scroll(page):
    try:
        return page.evaluate("() => [window.scrollX, window.scrollY, document.scrollingElement ? document.scrollingElement.scrollHeight : null, window.innerHeight]")
    except Exception:
        return None


def drain_scroll_log(page):
    try:
        return page.evaluate("() => { const l = window.__probeScrollLog || []; window.__probeScrollLog = []; return l; }")
    except Exception:
        return []


def slider_snapshot(page):
    """Generic-ish diagnostic: bbox of any element whose id contains 'Thumb'
    or 'Rail' plus text of the nearest container that shows a numeric range."""
    try:
        return page.evaluate("""() => {
          const out = {};
          for (const el of document.querySelectorAll('[id*="Thumb"],[id*="Rail"],[role="slider"],input[type=range]')) {
            const r = el.getBoundingClientRect();
            out[el.id || el.getAttribute('role') || el.tagName] = {x: r.x, y: r.y, w: r.width, h: r.height};
          }
          const t = document.querySelector('[id*="Thumb"]');
          let txt = null;
          if (t) { let n = t; for (let i=0;i<6 && n;i++){ const s=(n.innerText||'').trim(); if (s && /\\d/.test(s) && s.length<120){ txt=s; break;} n=n.parentElement; } }
          return {boxes: out, text: txt, scrollY: window.scrollY, vw: window.innerWidth, vh: window.innerHeight};
        }""")
    except Exception as e:
        return {"error": str(e)}


def install_patches():
    orig_new_page = BrowserContext.new_page

    def new_page(self, *a, **k):
        try:
            self.add_init_script(SCROLL_INIT_JS)
        except Exception:
            pass
        p = orig_new_page(self, *a, **k)
        STATE["page"] = p
        STATE["ctx"] = self
        try:
            self.on("page", lambda np: np.add_init_script(SCROLL_INIT_JS))
        except Exception:
            pass
        return p

    BrowserContext.new_page = new_page

    o_down, o_move, o_up, o_wheel = Mouse.down, Mouse.move, Mouse.up, Mouse.wheel

    def down(self, *a, **k):
        pg = STATE["page"]
        snap = slider_snapshot(pg) if pg else None
        STATE["drag"].append({"step": STATE["step"], "phase": "down", "snap": snap, "moves": []})
        ev("mouse.down", snap=snap)
        return o_down(self, *a, **k)

    def move(self, x, y, *a, **k):
        if STATE["drag"] and STATE["drag"][-1]["phase"] == "down":
            STATE["drag"][-1]["moves"].append({"x": x, "y": y, "steps": k.get("steps", 1)})
        return o_move(self, x, y, *a, **k)

    def up(self, *a, **k):
        r = o_up(self, *a, **k)
        pg = STATE["page"]
        if STATE["drag"] and STATE["drag"][-1]["phase"] == "down":
            d = STATE["drag"][-1]
            d["phase"] = "up"
            time.sleep(0.8)
            d["after_snap"] = slider_snapshot(pg) if pg else None
            ev("mouse.up", after=d["after_snap"])
        return r

    def wheel(self, dx, dy):
        ev("mouse.wheel", dx=dx, dy=dy)
        return o_wheel(self, dx, dy)

    Mouse.down, Mouse.move, Mouse.up, Mouse.wheel = down, move, up, wheel

    for name in ("click", "hover", "check", "uncheck", "fill", "scroll_into_view_if_needed", "drag_to", "dblclick", "press", "press_sequentially"):
        orig = getattr(Locator, name)

        def make(orig, name):
            def wrapped(self, *a, **k):
                pg = STATE["page"]
                before = read_scroll(pg) if pg else None
                try:
                    return orig(self, *a, **k)
                finally:
                    after = read_scroll(pg) if pg else None
                    if before and after and abs((after[1] or 0) - (before[1] or 0)) > 0.5:
                        ev("api-scrolled", api=f"Locator.{name}", before_y=before[1], after_y=after[1])
            return wrapped
        setattr(Locator, name, make(orig, name))

    o_eval = Page.evaluate

    def peval(self, expression, *a, **k):
        if isinstance(expression, str) and "scroll" in expression.lower() and "__probeScrollLog" not in expression and "scrollY" not in expression.replace("window.scrollTo", ""):
            ev("page.evaluate(scroll)", expr=expression[:80])
        elif isinstance(expression, str) and "scrollTo" in expression:
            ev("page.evaluate(scrollTo)", expr=expression[:80], arg=a[0] if a else None)
        return o_eval(self, expression, *a, **k)

    Page.evaluate = peval


def sample_all_pages():
    out = []
    ctx = STATE.get("ctx")
    if ctx is None:
        return out
    try:
        pages = list(ctx.pages)
    except Exception:
        return out
    for i, pg in enumerate(pages):
        try:
            if pg.is_closed():
                continue
            out.append({"i": i, "url": pg.url, "pos": read_scroll(pg), "events": len(drain_scroll_log(pg))})
        except Exception:
            pass
    return out


def install_print_hook():
    real_print = builtins.print

    def hooked(*args, **kwargs):
        real_print(*args, **kwargs)
        if len(args) == 1 and isinstance(args[0], str):
            m = _STEP_RE.match(args[0].strip())
            if m:
                prev = STATE["step"]
                pg = STATE["page"]
                if prev:
                    STATE["step_pages"][prev] = sample_all_pages()
                if pg is not None and prev:
                    pos = read_scroll(pg)
                    STATE["step_scroll"][prev] = {"pos": pos, "scroll_events": drain_scroll_log(pg)}
                STATE["step"] = int(m.group(1))
    builtins.print = hooked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recording")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--no-stop", action="store_true", help="AUTOFLOW_STOP_ON_FAILURE=0 (diagnostic only)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--generator", default=None, help="path to an alternative script_generator.py (e.g. the backup)")
    args = ap.parse_args()

    if args.no_stop:
        os.environ["AUTOFLOW_STOP_ON_FAILURE"] = "0"

    rec = json.loads(Path(args.recording).read_text(encoding="utf-8"))
    actions = rec["actions"]
    if args.max_steps:
        actions = actions[: args.max_steps]
    start_url = rec["start_url"]
    if actions[0].get("action_type") != "navigate":
        actions = [{"action_type": "navigate", "page_url": start_url, "page_id": 0}] + list(actions)
    tc = dict(rec)
    tc["actions"] = actions

    scratch = Path(tempfile.mkdtemp(prefix="dragscroll_probe_"))
    gen = _load_generate_script(args.generator) if args.generator else generate_script
    script_path = gen(tc, out_name="dragscroll_probe_script.py", output_dir=scratch)
    spec = importlib.util.spec_from_file_location("dragscroll_probe_script", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    install_patches()
    install_print_hook()

    out_json = scratch / "report.json"
    result = mod.run(start_url, output_json_path=out_json, screenshot_dir=scratch / "shots", headless=args.headless)
    # final step boundary
    pg = STATE["page"]
    if STATE["step"]:
        try:
            STATE["step_pages"][STATE["step"]] = sample_all_pages()
        except Exception:
            pass
    if pg is not None and STATE["step"]:
        try:
            STATE["step_scroll"][STATE["step"]] = {"pos": read_scroll(pg), "scroll_events": drain_scroll_log(pg)}
        except Exception:
            pass

    summary = {
        "status": result.get("status"),
        "steps": [
            {k: s.get(k) for k in ("index", "action_type", "success", "error", "not_run")}
            for s in result.get("steps", [])
        ],
        "drag": STATE["drag"],
        "step_scroll": STATE["step_scroll"],
        "step_pages": STATE["step_pages"],
        "events": STATE["events"],
    }
    outp = Path(args.out) if args.out else scratch / "probe_result.json"
    outp.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    builtins.__dict__["print"] = builtins.print
    sys.stdout.write(f"\nPROBE RESULT WRITTEN: {outp}\n")


if __name__ == "__main__":
    main()
