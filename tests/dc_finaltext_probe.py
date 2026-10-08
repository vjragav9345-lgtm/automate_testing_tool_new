from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    pg.goto("https://the-internet.herokuapp.com/dynamic_controls", wait_until="domcontentloaded")
    pg.wait_for_timeout(800)
    pg.click("#input-example button")
    pg.wait_for_timeout(3500)
    info = pg.evaluate("""() => {
        const el = document.querySelector('#input-example input');
        return {
            innerText: el.innerText,
            value: el.value,
            placeholder: el.placeholder,
            ariaLabel: el.getAttribute('aria-label'),
            outerHTML: el.outerHTML,
            parentOuterHTML: el.parentElement.outerHTML.slice(0,500),
        };
    }""")
    for k, v in info.items(): print(k, '=', repr(v))
    b.close()
