"""FIX 1 (Validate Value Range rewrite): pytest regression suite.

Runs entirely against local, static HTML via Playwright's page.set_content()
- no live sites. Exercises the shared analysis/resolution helpers
(_AFQA_ELEMENT_ANALYSIS_JS, _afqa_resolve_element_value,
_afqa_check_value_range) through a REAL generated replay script - the
exact same module a real replay run imports - not a reimplementation.

Run with: venv/Scripts/python.exe -m pytest tests/test_fix1_value_range.py -v
"""
import importlib.util
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from generator.script_generator import generate_script  # noqa: E402

REGRESSION_HTML = """
<!DOCTYPE html><html><body>
<div id="card">
  <span>4.1 stars</span>
  <span>(128 ratings)</span>
  <span>Rs. <!-- -->1520</span><span style="text-decoration:line-through">Rs. 2999</span><span>(49% OFF)</span>
</div>
<div id="superscript">61,896<sup>66</sup></div>
<div id="indian">Rs.&nbsp;1,00,000</div>
<div id="rsvariant">Rs. 1,520</div>
<div id="percentOnly">(49% OFF)</div>
<div id="noNumber">In stock, ships tomorrow</div>
<div id="justBoundaryMin">Rs. 1000</div>
<div id="justBoundaryMax">Rs. 10000</div>
</body></html>
"""


@pytest.fixture(scope="module")
def gen_module(tmp_path_factory):
    """Generates a real replay script (same path production code takes)
    and imports it as a module, so tests call the ACTUAL functions a
    replay run uses - _afqa_resolve_element_value, _afqa_check_value_range,
    _AFQA_ELEMENT_ANALYSIS_JS - never a second, parallel copy of the logic."""
    tc = {
        "name": "zz_pytest_fix1",
        "start_url": "http://example.com",
        "actions": [{
            "action_type": "navigate", "page_url": "http://example.com", "page_id": 0,
            "value": None, "locator_profile": None, "bounding_box": None,
            "timestamp": "2026-01-01T00:00:00Z",
        }],
    }
    out_dir = tmp_path_factory.mktemp("gen")
    path = generate_script(tc, out_name="zz_pytest_fix1", output_dir=out_dir)
    spec = importlib.util.spec_from_file_location("zz_pytest_fix1_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def card_page(page):
    page.set_content(REGRESSION_HTML)
    return page


# ---------------------------------------------------------------------
# Number-token boundary regex (FOLLOW-UP: strict lookahead/lookbehind
# restored, with an explicit currency-token alternative rather than a
# blanket "any uppercase letter" exception - the earlier, broader
# version wrongly let "16GB" through since G/B are uppercase but not a
# currency token)
# ---------------------------------------------------------------------

def _num_tokens(gen_module, text):
    return [
        (m.group(0), gen_module._afqa_parse_numeric_token(m.group(1), m.group(2)))
        for m in gen_module._AFQA_NUM_TOKEN_RE.finditer(text)
    ]


def test_spec_number_is_not_a_price_candidate(gen_module):
    """A dimension/spec number immediately followed by a unit word (no
    currency token) must not be extracted at all - from either side."""
    assert _num_tokens(gen_module, "16GB DDR5") == []


def test_adjacent_prices_no_separator(gen_module):
    """Two currency amounts with zero separating whitespace (adjacent
    <span>s in the markup) - both extracted, each keeping its OWN
    currency prefix (so each is correctly tagged role=price/struck, not
    just the first)."""
    tokens = _num_tokens(gen_module, "Rs. 1520Rs. 2999")
    assert [v for _, v in tokens] == [1520.0, 2999.0]
    assert tokens[0][0] == "Rs. 1520"
    assert tokens[1][0] == "Rs. 2999"


def test_spec_number_before_real_price(gen_module):
    tokens = _num_tokens(gen_module, "512GB SSD ₹61,896")
    assert [v for _, v in tokens] == [61896.0]


# ---------------------------------------------------------------------
# Number extraction / role tagging
# ---------------------------------------------------------------------

def test_dropped_price_regression(gen_module, card_page):
    """The exact HTML shape from the bug report: the discounted price
    (1520) must appear as a 'price' candidate, not be dropped."""
    el = card_page.locator("#card")
    analysis = el.evaluate(gen_module._AFQA_ELEMENT_ANALYSIS_JS)
    roles = {t["raw"]: t["role"] for t in analysis["tokens"]}
    assert any(v == 1520 for t in analysis["tokens"] for v in [t["value"]] if t["role"] == "price")
    struck_vals = [t["value"] for t in analysis["tokens"] if t["role"] == "struck"]
    assert 2999 in struck_vals
    percent_vals = [t["value"] for t in analysis["tokens"] if t["role"] == "percent"]
    assert 49 in percent_vals


def test_superscript_fraction_join(gen_module, card_page):
    el = card_page.locator("#superscript")
    analysis = el.evaluate(gen_module._AFQA_ELEMENT_ANALYSIS_JS)
    values = [t["value"] for t in analysis["tokens"]]
    assert values == [61896.66]


def test_indian_thousands_with_nbsp(gen_module, card_page):
    el = card_page.locator("#indian")
    val, reason, detail = gen_module._afqa_resolve_element_value(el)
    assert reason is None
    assert val == 100000


def test_rs_variant(gen_module, card_page):
    el = card_page.locator("#rsvariant")
    val, reason, detail = gen_module._afqa_resolve_element_value(el)
    assert val == 1520
    assert reason is None


def test_percent_alone_is_no_number_by_default(gen_module, card_page):
    el = card_page.locator("#percentOnly")
    val, reason, detail = gen_module._afqa_resolve_element_value(el)
    assert val is None
    assert detail["resolution"] == "no_number"


def test_percent_alone_with_hint(gen_module, card_page):
    el = card_page.locator("#percentOnly")
    val, reason, detail = gen_module._afqa_resolve_element_value(el, value_hint="percent")
    assert val == 49
    assert reason is None


def test_no_number_element(gen_module, card_page):
    el = card_page.locator("#noNumber")
    val, reason, detail = gen_module._afqa_resolve_element_value(el)
    assert val is None
    assert detail["resolution"] == "no_number"


# ---------------------------------------------------------------------
# Resolution rules (auto_price / value_hint)
# ---------------------------------------------------------------------

def test_auto_price_resolution(gen_module, card_page):
    """Whole card, no hint -> auto_price 1520 (the one non-struck price)."""
    el = card_page.locator("#card")
    val, reason, detail = gen_module._afqa_resolve_element_value(el)
    assert val == 1520
    assert reason is None
    assert detail["resolution"] == "auto_price"


def test_value_hint_mrp(gen_module, card_page):
    """Whole card, value_hint=mrp -> 2999 (the struck-through reference price)."""
    el = card_page.locator("#card")
    val, reason, detail = gen_module._afqa_resolve_element_value(el, value_hint="mrp")
    assert val == 2999
    assert reason is None


def test_value_hint_rating(gen_module, card_page):
    el = card_page.locator("#card")
    val, reason, detail = gen_module._afqa_resolve_element_value(el, value_hint="rating")
    assert val == 4.1


def test_value_hint_count(gen_module, card_page):
    el = card_page.locator("#card")
    val, reason, detail = gen_module._afqa_resolve_element_value(el, value_hint="count")
    assert val == 128


def test_legacy_recording_without_value_hint_unchanged(gen_module, card_page):
    """value_hint=None (the key absent entirely, as on any recording saved
    before this feature existed) behaves exactly like the auto-resolution
    default - never a different code path."""
    el = card_page.locator("#card")
    with_none, _, _ = gen_module._afqa_resolve_element_value(el, value_hint=None)
    without_arg, _, _ = gen_module._afqa_resolve_element_value(el)
    assert with_none == without_arg == 1520


# ---------------------------------------------------------------------
# Range check: inclusive bounds, tolerance, below/above
# ---------------------------------------------------------------------

@pytest.mark.parametrize("value,min_v,max_v,expect_ok,expect_reason", [
    (1520, 1000, 10000, True, None),
    (1491, 1000, 10000, True, None),
    (912, 1000, 10000, False, "below_min"),
    (809, 1000, 10000, False, "below_min"),
    (1000, 1000, 10000, True, None),       # inclusive lower boundary
    (10000, 1000, 10000, True, None),      # inclusive upper boundary
    (999.99, 1000, 10000, False, "below_min"),
    (10000.01, 1000, 10000, False, "above_max"),
    (100000, 1000, 10000, False, "above_max"),  # "₹1,00,000" -> 100000
    (500, 1000, None, False, "below_min"),      # min only
    (500, None, 1000, True, None),              # max only
])
def test_range_boundaries(gen_module, value, min_v, max_v, expect_ok, expect_reason):
    ok, reason = gen_module._afqa_check_value_range(value, min_v, max_v)
    assert ok == expect_ok
    assert reason == expect_reason


def test_boundary_uses_tolerance_not_strict_equality(gen_module):
    """1e-9 tolerance: a value that's boundary-equal but for float noise
    still passes."""
    ok, reason = gen_module._afqa_check_value_range(1000.0000000001, 1000, 10000)
    assert ok is True


# ---------------------------------------------------------------------
# Ambiguous element_not_found handled by the full validate_value_range
# step (integration-level - exercised via ui_verify_fix1_value_range.py's
# real-app/real-browser run, which showed element_not_found -> FAILED,
# replay continues, and the full multi-item PASS/FAIL/summary line; not
# duplicated here to keep this suite fast and dependency-free).
# ---------------------------------------------------------------------
