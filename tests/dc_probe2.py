from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    pg.goto("https://the-internet.herokuapp.com/dynamic_controls", wait_until="domcontentloaded")
    pg.wait_for_timeout(500)
    print(pg.content()[:3000])
    b.close()
