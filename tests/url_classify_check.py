"""TEST-ONLY (I1-e): the normalised URL classification."""
import importlib.util, sys, json
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script
d = BASE / "tests" / "_probe_out" / "url_classify"; d.mkdir(parents=True, exist_ok=True)
sp = generate_script({"name": "u", "start_url": "http://x/", "actions": [{"action_type": "navigate", "page_url": "http://x/", "locator_profile": {}}]}, out_name="u.py", output_dir=d)
spec = importlib.util.spec_from_file_location("u", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
C = m._classify_url
cases = [
    # (actual, expected, chain, want)
    ("https://www.Example.com/a/b/", "http://example.com/a/b", None, "match"),                       # scheme/www/case/trailing slash
    ("https://example.com:443/a/b", "https://example.com/a/b", None, "match"),                       # default port
    ("https://example.com/a/b#frag", "https://example.com/a/b", None, "match"),                      # fragment
    ("https://example.com/a?utm_source=x&gclid=1&fbclid=2&msclkid=3&_ga=4&_gl=5", "https://example.com/a", None, "match"),  # tracking
    ("https://example.com/a?b=2&a=1", "https://example.com/a?a=1&b=2", None, "match"),               # order
    ("https://example.com/item/12345/view", "https://example.com/item/99887/view", None, "match"),   # numeric dynamic segment
    ("https://example.com/p/3f2b8c1e-1111-2222-3333-444455556666", "https://example.com/p/aaaaaaaa-1111-2222-3333-444455556666", None, "match"),  # uuid
    ("https://example.com/es/pricing/", "https://example.com/pricing/", None, "mismatch"),           # locale prefix kept
    ("https://example.com/features/", "https://example.com/pricing/", None, "mismatch"),             # different path
    ("https://example.com/a?sort=price", "https://example.com/a?sort=name", None, "query"),          # same path, query differs -> warning
    ("https://example.org/a", "https://example.com/a", None, "mismatch"),                            # host
    ("https://example.com/final", "https://example.com/start", ["https://example.com/hop", "https://example.com/final"], "match"),  # redirect chain
    ("https://example.com/#/route/two", "https://example.com/#/route/one", None, "mismatch"),        # hash routing kept
]
bad = 0
for actual, expected, chain, want in cases:
    got = C(actual, expected, chain)
    ok = got == want
    bad += (not ok)
    print(("ok  " if ok else "FAIL"), got, "<-", actual, "vs", expected)
assert bad == 0, f"{bad} case(s) wrong"
print("URL CLASSIFY CHECKS PASS")
