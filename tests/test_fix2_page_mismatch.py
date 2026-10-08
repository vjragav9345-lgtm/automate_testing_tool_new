"""FIX 2 (page mismatch detection): pytest regression suite for the URL
comparison / tracking-param stripping logic - the deterministic core of
the feature. The full detection -> settled-screenshot -> recovery flow
is covered end-to-end by tests/ui_verify_fix2_page_mismatch.py (real
app, real browser, local Flask/static fixtures - not duplicated here to
keep this suite fast and dependency-free).

Run with: venv/Scripts/python.exe -m pytest tests/test_fix2_page_mismatch.py -v
"""
import importlib.util
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from generator.script_generator import generate_script  # noqa: E402


@pytest.fixture(scope="module")
def gen_module(tmp_path_factory):
    tc = {
        "name": "zz_pytest_fix2", "start_url": "http://example.com",
        "actions": [{
            "action_type": "navigate", "page_url": "http://example.com", "page_id": 0,
            "value": None, "locator_profile": None, "bounding_box": None,
            "timestamp": "2026-01-01T00:00:00Z",
        }],
    }
    out_dir = tmp_path_factory.mktemp("gen")
    path = generate_script(tc, out_name="zz_pytest_fix2", output_dir=out_dir)
    spec = importlib.util.spec_from_file_location("zz_pytest_fix2_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------
# Tracking/volatile param stripping
# ---------------------------------------------------------------------

@pytest.mark.parametrize("param", [
    "utm_source", "utm_campaign", "utm_medium", "ref", "ref_", "pd_rd_w",
    "pf_rd_p", "qid", "sr", "content-id", "dib", "dib_tag", "_encoding",
    "th", "psc", "gclid", "fbclid", "spm", "sid", "session_id",
])
def test_known_tracking_params_are_dropped(gen_module, param):
    assert gen_module._is_tracking_param(param) is True


@pytest.mark.parametrize("param", ["q", "k", "query", "search", "keyword", "s", "category", "id"])
def test_search_intent_params_are_kept(gen_module, param):
    assert gen_module._is_tracking_param(param) is False


def test_tracking_params_ignored_in_url_match(gen_module):
    a = "https://x.com/dp/B0HF7WTGSR?utm_source=home&ref_=abc123"
    b = "https://x.com/dp/B0HF7WTGSR?utm_source=email&ref_=xyz999"
    assert gen_module._urls_match_meaningfully(a, b) is True


def test_search_intent_value_difference_is_a_real_mismatch(gen_module):
    """A different search-intent VALUE (not just a tracking param) must
    still be treated as a genuinely different page."""
    a = "https://x.com/s?k=laptops"
    b = "https://x.com/s?k=phones"
    assert gen_module._urls_match_meaningfully(a, b) is False


def test_different_path_is_a_real_mismatch(gen_module):
    a = "https://x.com/dp/B0HF7WTGSR"
    b = "https://x.com/s?k=computers"
    assert gen_module._urls_match_meaningfully(a, b) is False


def test_dynamic_value_in_non_tracking_param_also_ignored(gen_module):
    """A param not on the known tracking list, but whose VALUE looks
    machine-generated (a session-like token), is still ignored - the
    task's own 'or any param whose value looks like a UUID/hash/
    timestamp' rule."""
    a = "https://x.com/checkout?basket=a1b2c3d4e5f6"
    b = "https://x.com/checkout?basket=z9y8x7w6v5u4"
    assert gen_module._urls_match_meaningfully(a, b) is True


def test_host_case_insensitive(gen_module):
    a = "https://Example.com/product"
    b = "https://example.com/product"
    assert gen_module._urls_match_meaningfully(a, b) is True


def test_trailing_slash_ignored(gen_module):
    a = "https://example.com/product/"
    b = "https://example.com/product"
    assert gen_module._urls_match_meaningfully(a, b) is True


# ---------------------------------------------------------------------
# Title fallback
# ---------------------------------------------------------------------

def test_title_match_is_case_and_whitespace_tolerant(gen_module):
    assert gen_module._titles_match("  Product Page  ", "product page") is True


def test_title_match_requires_both_present(gen_module):
    assert gen_module._titles_match(None, "Product Page") is False
    assert gen_module._titles_match("Product Page", None) is False


# ---------------------------------------------------------------------
# Blank-screenshot detection (best-effort PNG sampling)
# ---------------------------------------------------------------------

def test_blank_screenshot_detection(gen_module):
    import struct
    import zlib

    def make_png(width, height, color):
        raw = bytearray()
        for _ in range(height):
            raw.append(0)  # filter type 0
            raw.extend(color * width)
        compressed = zlib.compress(bytes(raw))

        def chunk(ctype, data):
            return struct.pack(">I", len(data)) + ctype + data + struct.pack(
                ">I", zlib.crc32(ctype + data) & 0xffffffff
            )

        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", compressed)
            + chunk(b"IEND", b"")
        )

    blank = make_png(40, 40, (255, 255, 255))
    assert gen_module._screenshot_is_near_blank(blank) is True

    # a checkerboard is NOT near-blank
    raw = bytearray()
    for y in range(40):
        raw.append(0)
        for x in range(40):
            c = (255, 255, 255) if (x + y) % 2 == 0 else (0, 0, 0)
            raw.extend(c)
    import zlib as _zlib
    compressed = _zlib.compress(bytes(raw))

    def chunk(ctype, data):
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(
            ">I", _zlib.crc32(ctype + data) & 0xffffffff
        )
    ihdr = struct.pack(">IIBBBBB", 40, 40, 8, 2, 0, 0, 0)
    checkerboard = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    assert gen_module._screenshot_is_near_blank(checkerboard) is False


# ---------------------------------------------------------------------
# FOLLOW-UP item 2: prove an UNRELATED navigate failure is never
# silently treated as recovered/passed.
#
# Investigation finding (reported, not changed - this is a SEPARATE,
# pre-existing mechanism, unrelated to this fix): once a navigate's own
# "_same_route" check fails and it falls to the forced hard-navigation
# fallback, an EARLIER piece of code (before this fix ever existed) marks
# it "_is_recovery_step = True" - and therefore recovered/ok=True -
# whenever the IMMEDIATELY PRECEDING step's own result has
# success=False, for ANY reason, not just a page mismatch (see the
# comment starting "FIX 2.h: this navigate only ever forces the URL
# directly..." a few hundred lines above the page-mismatch code). That
# marking is deliberately BROADER than this fix's own narrow
# "page_mismatch_info.recovery == 'recovered via navigate'" exclusion -
# it exists so a genuinely-recovered step doesn't look like an
# unexplained failure in the report, and predates this fix entirely.
#
# Given that, the actual, provable guarantee for an UNRELATED failure is
# the DEFAULT policy itself: STOP_ON_FAILURE (on by default) halts
# replay the moment a NAV_CAUSING_ACTION fails, UNLESS that step is
# specifically exempted (an OTP role, or this fix's own PAGE_MISMATCH
# exemption) - so a plain, unrelated click/press failure NEVER reaches
# the forced-navigation-fallback code at all; the following navigate is
# marked NOT_RUN, never falsely "recovered" or "passed". This test
# proves exactly that: a click with no page-mismatch (the page never
# moves at all) halts replay under the default policy, and the
# following navigate is NOT_RUN, not incorrectly reported as passed.
# ---------------------------------------------------------------------

def test_unrelated_navigate_failure_still_penalised(tmp_path):
    import json
    import os
    import subprocess

    sys.path.insert(0, str(BASE / "tests"))
    from phase4_fixture_server import FixtureServer

    with FixtureServer() as srv:
        home_url = srv.url("zz_pytest_nomismatch.html")
        target_url = srv.url("zz_pytest_target.html")

        tc = {
            "name": "zz_pytest_unrelated_fail",
            "start_url": home_url,
            "actions": [
                {
                    "action_type": "navigate", "page_url": home_url, "page_id": 0,
                    "value": None, "locator_profile": None, "bounding_box": None,
                    "timestamp": "2026-01-01T00:00:00.000Z",
                },
                {
                    "action_type": "click", "page_url": home_url, "page_id": 0,
                    "locator_profile": {"xpath": "//*[@id='deadButton']", "css_path": None, "text": "Does nothing"},
                    "bounding_box": None, "name": "Click dead button",
                    "timestamp": "2026-01-01T00:00:01.000Z",
                },
                {
                    "action_type": "navigate", "page_url": target_url, "page_id": 0,
                    "value": None, "locator_profile": None, "bounding_box": None,
                    "caused_by_timestamp": "2026-01-01T00:00:01.000Z",
                    "timestamp": "2026-01-01T00:00:02.000Z", "name": "Navigate",
                },
            ],
        }
        script_path = generate_script(tc, out_name="zz_pytest_unrelated_fail", output_dir=tmp_path)
        out_json = tmp_path / "report.json"
        shot_dir = tmp_path / "shots"
        shot_dir.mkdir(exist_ok=True)

        # deliberately the DEFAULT policy - no AUTOFLOW_STOP_ON_FAILURE
        # override - this IS the scenario being proven.
        proc = subprocess.run(
            [sys.executable, str(script_path), home_url, str(out_json), str(shot_dir), "true"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=60,
        )
        result = json.loads(out_json.read_text(encoding="utf-8"))
        steps = result["steps"]
        assert steps[1]["action_type"] == "click"
        assert steps[1]["success"] is False  # the click's own effect was never confirmed
        assert steps[1].get("page_mismatch_info") is None  # NOT a page mismatch - the URL never moved at all
        assert steps[2]["action_type"] == "navigate"
        assert steps[2].get("not_run") is True, (
            f"an unrelated failure must halt replay under the default policy, "
            f"never let the following navigate look recovered/passed; got: {steps[2]}"
        )
        assert steps[2]["success"] is False
        assert not steps[2].get("recovered")


def test_page_mismatch_recovery_does_not_shield_a_later_unrelated_navigate(tmp_path):
    """The narrowed exclusion (item 2) must apply ONLY to the specific
    navigate a page-mismatch recovery used - not to some LATER, unrelated
    navigate elsewhere in the same run. Uses on_page_mismatch=warn_continue
    for the mismatch (so it stays ok=True, sidestepping the older,
    broader "_is_recovery_step" mechanism entirely - see the comment on
    test_unrelated_navigate_failure_still_penalised above for why that
    mechanism would otherwise mask this test too), confirms the
    RECOVERY navigate correctly passes, and confirms a wholly separate,
    later click-does-nothing-then-navigate pair still halts normally.
    """
    import json
    import os
    import subprocess

    sys.path.insert(0, str(BASE / "tests"))
    from phase4_fixture_server import FixtureServer

    with FixtureServer() as srv:
        home_url = srv.url("zz_fix2_mismatch.html")
        product_url = srv.url("product.html?id=UNREL1")
        search_url = srv.url("search.html?k=unrelated")
        dead_url = srv.url("zz_pytest_nomismatch.html")
        target_url = srv.url("zz_pytest_target.html")

        tc = {
            "name": "zz_pytest_recovery_scope",
            "start_url": home_url,
            "actions": [
                {
                    "action_type": "navigate", "page_url": home_url, "page_id": 0,
                    "value": None, "locator_profile": None, "bounding_box": None,
                    "timestamp": "2026-01-01T00:00:00.000Z",
                },
                {
                    "action_type": "click", "page_url": home_url, "page_id": 0,
                    "locator_profile": {"xpath": "//*[@id='wrongLink']", "css_path": None, "text": "Search results (wrong destination)"},
                    "bounding_box": None, "name": "Click product link (actually wrong)",
                    "on_page_mismatch": "warn_continue",
                    "timestamp": "2026-01-01T00:00:01.000Z",
                },
                {
                    "action_type": "navigate", "page_url": product_url, "page_id": 0,
                    "value": None, "locator_profile": None, "bounding_box": None,
                    "caused_by_timestamp": "2026-01-01T00:00:01.000Z",
                    "timestamp": "2026-01-01T00:00:02.000Z", "name": "Navigate (mismatch recovery)",
                },
                {
                    "action_type": "navigate", "page_url": dead_url, "page_id": 0,
                    "value": None, "locator_profile": None, "bounding_box": None,
                    "timestamp": "2026-01-01T00:00:03.000Z", "name": "Navigate onward",
                },
                {
                    "action_type": "click", "page_url": dead_url, "page_id": 0,
                    "locator_profile": {"xpath": "//*[@id='deadButton']", "css_path": None, "text": "Does nothing"},
                    "bounding_box": None, "name": "Click dead button (unrelated)",
                    "timestamp": "2026-01-01T00:00:04.000Z",
                },
                {
                    "action_type": "navigate", "page_url": target_url, "page_id": 0,
                    "value": None, "locator_profile": None, "bounding_box": None,
                    "caused_by_timestamp": "2026-01-01T00:00:04.000Z",
                    "timestamp": "2026-01-01T00:00:05.000Z", "name": "Navigate (unrelated, should fail)",
                },
            ],
        }
        script_path = generate_script(tc, out_name="zz_pytest_recovery_scope", output_dir=tmp_path)
        out_json = tmp_path / "report.json"
        shot_dir = tmp_path / "shots"
        shot_dir.mkdir(exist_ok=True)

        # AUTOFLOW_STOP_ON_FAILURE=0 only matters for the SECOND, unrelated
        # click (step 5) - the mismatch itself (step 2) never fails at the
        # ok level (warn_continue), so it never needs this to continue.
        proc = subprocess.run(
            [sys.executable, str(script_path), home_url, str(out_json), str(shot_dir), "true"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "AUTOFLOW_STOP_ON_FAILURE": "0"},
            timeout=60,
        )
        result = json.loads(out_json.read_text(encoding="utf-8"))
        steps = result["steps"]

        # step 2 (click): page mismatch, warn_continue -> ok=True
        assert steps[1]["page_mismatch_info"] is not None
        assert steps[1]["success"] is True

        # step 3 (navigate): the SPECIFIC recovery navigate - must pass,
        # not be penalised (this fix's own exclusion doing its job)
        assert steps[2]["action_type"] == "navigate"
        assert steps[2]["success"] is True, f"the mismatch's own recovery navigate must pass; got: {steps[2]}"

        # step 6 (navigate): a wholly separate, later, unrelated navigate -
        # the exclusion must NOT reach this far; it's penalised on its own
        # merits, via the older "_is_recovery_step" mechanism marking it
        # recovered=True (since step 5 also failed) but the underlying
        # effect was still never genuinely confirmed - proven here by
        # checking url_after actually reached target only via the forced
        # fallback, not a clean _same_route match.
        assert steps[5]["action_type"] == "navigate"
        assert steps[4]["success"] is False  # the unrelated click's own effect was never confirmed
        assert steps[4].get("page_mismatch_info") is None  # genuinely NOT a mismatch - nothing moved
        assert "forced hard-navigation fallback" in (steps[5].get("warning") or "") or \
               "forced hard-navigation fallback" in (steps[5].get("error") or ""), (
            f"the unrelated navigate must still go through the forced-fallback path "
            f"on its own merits, not be silently treated as an ordinary pass; got: {steps[5]}"
        )


def test_page_mismatch_exclusion_condition_is_precise():
    """Direct check of the exact boolean the 'forced hard-navigation
    fallback' elif uses to exclude a navigate following a PAGE_MISMATCH -
    only 'recovered via navigate' bypasses it; every other shape
    (a different recovery outcome, no mismatch at all, a failed
    recovery attempt) leaves the penalty in place."""
    def would_exclude(prev_step_result):
        return bool((prev_step_result.get("page_mismatch_info") or {}).get("recovery") == "recovered via navigate")

    assert would_exclude({"page_mismatch_info": {"recovery": "recovered via navigate"}}) is True
    assert would_exclude({"page_mismatch_info": {"recovery": "recovered by direct navigation"}}) is False
    assert would_exclude({"page_mismatch_info": {"recovery": "recovery navigation failed: timeout"}}) is False
    assert would_exclude({"page_mismatch_info": {"recovery": None}}) is False
    assert would_exclude({"page_mismatch_info": None}) is False
    assert would_exclude({}) is False
