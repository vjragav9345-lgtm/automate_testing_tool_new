"""TEST-ONLY: inspect the real dynamic_controls page's DOM/text around the input, at each stage."""
from playwright.sync_api import sync_playwright

JS = """() => {
    const forms = Array.from(document.querySelectorAll('form'));
    return forms.map(f => ({
        html: f.innerHTML.slice(0, 400),
        textContent: (f.textContent || '').trim(),
        innerText: (f.innerText || '').trim(),
    }));
}"""

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    pg.goto("https://the-internet.herokuapp.com/dynamic_controls", wait_until="domcontentloaded")
    pg.wait_for_timeout(1000)

    def dump(label):
        info = pg.evaluate(JS)
        print(f"--- {label} ---")
        for i, f in enumerate(info):
            print(f"form[{i}] textContent={f['textContent']!r}")
            print(f"form[{i}] innerText  ={f['innerText']!r}")
        print()

    dump("initial (before Enable click)")
    pg.click("text=Enable")
    pg.wait_for_timeout(300)
    dump("300ms after Enable click (loading)")
    pg.wait_for_timeout(3000)
    dump("still loading (~3.3s)")
    pg.wait_for_timeout(2000)
    dump("after enabled (~5.3s)")
    inp = pg.locator("#input-example input")
    print("input disabled?", inp.is_disabled())
    inp.fill("hello")
    pg.wait_for_timeout(200)
    dump("after fill")
    pg.click("text=Disable")
    pg.wait_for_timeout(300)
    dump("300ms after Disable click (loading)")
    b.close()
