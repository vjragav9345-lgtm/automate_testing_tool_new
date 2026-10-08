"""FIX 5 (scale) - DOM snapshot mechanism: a real document load must get a
snapshot; a client-side pushState/history navigation (an SPA filter/sort
change - exactly what inflated a real Myntra recording to 16 near-
duplicate ~1.2MB snapshots for 57 actions) must NOT. Also verifies the new
gzip compression and identical-content dedup skip, directly against
record_session.py's own (unmodified) helper functions and a real
Playwright page - no mocking of the detection logic itself.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402
from recorder.record_session import (  # noqa: E402
    _is_hard_navigation, _mark_navigation_counted, _capture_dom_snapshot, _SnapshotBudget,
)
from tests.phase4_fixture_server import FixtureServer  # noqa: E402


def main():
    with FixtureServer() as srv, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1) real hard navigation -> True
        page.goto(srv.url("flowfix9_multistep.html"))
        hard = _is_hard_navigation(page)
        _mark_navigation_counted(page)
        print("hard navigation detected:", hard)
        assert hard is True, "a real page.goto() must be detected as a hard navigation"

        # 2) pushState (no reload) -> False
        page.evaluate("() => history.pushState({}, '', '?f=Color:Blue')")
        soft = _is_hard_navigation(page)
        _mark_navigation_counted(page)
        print("pushState detected as hard nav:", soft)
        assert soft is False, "a pushState-only URL change must NOT be treated as a hard navigation"

        # 3) another real navigation -> True again
        page.goto(srv.url("flowfix9_radio_race.html"))
        hard2 = _is_hard_navigation(page)
        _mark_navigation_counted(page)
        assert hard2 is True

        # 4) snapshot capture: gzip, budget tracking, identical-content dedup
        budget = _SnapshotBudget()
        session_id = "flowfix9_scale_test_session"
        path1 = _capture_dom_snapshot(page, session_id, "2026-01-01T00-00-00-000Z", budget)
        assert path1 is not None and path1.endswith(".html.gz"), path1
        assert budget.total_bytes > 0

        # same content, no navigation in between -> skipped as a duplicate
        path2 = _capture_dom_snapshot(page, session_id, "2026-01-01T00-00-01-000Z", budget)
        assert path2 is None, f"expected duplicate content to be skipped, got {path2}"

        # verify the saved file really is gzip and decompresses to real HTML
        import gzip
        saved = BASE_DIR / path1
        raw = gzip.decompress(saved.read_bytes()).decode("utf-8")
        assert "<html" in raw.lower()
        print(f"snapshot saved+verified: {saved} ({saved.stat().st_size} bytes compressed)")

        # cleanup
        import shutil
        shutil.rmtree(saved.parent, ignore_errors=True)

        browser.close()

    print("\nPASS: FIX 5 correctly skips snapshots for pushState-only navigations, "
          "compresses real ones, and dedupes identical content")


if __name__ == "__main__":
    main()
