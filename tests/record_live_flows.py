"""TEST-ONLY: records a real flow on a live site by driving the browser with
Playwright's own (trusted) input, through the real Recorder, and saves it as
a normal recording - used to re-record the ChatGPT / Amazon flows after the
recorder changes.

    python tests/record_live_flows.py chatgpt
    python tests/record_live_flows.py amazon
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from storage import repository

which = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    rec = Recorder(pg)
    rec.install_context_capture(ctx)
    if which == "chatgpt":
        pg.goto("https://www.chatgpt.com", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        rec.start(launch_url=pg.url)
        pg.get_by_role("link", name="Images").first.click()
        pg.wait_for_timeout(5000)
        pg.mouse.wheel(0, 300)
        pg.wait_for_timeout(1200)
        pg.get_by_role("button", name="Sketch").first.click()   # a card: the page then fills the prompt box
        pg.wait_for_timeout(9000)                                 # the page types the prompt itself
        pg.mouse.wheel(0, 200)
        pg.wait_for_timeout(1200)
        name = "live_chatgpt_pin"
    elif which == "doc360":
        pg.goto("https://document360.com", wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        rec.start(launch_url=pg.url)
        pg.locator("header a", has_text="Features").first.hover()
        pg.wait_for_timeout(900)
        pg.locator('a[href$="/knowledgebase-portal/analytics/"]:visible').first.click()
        pg.wait_for_timeout(6000)
        try:
            pg.get_by_role("button", name="Allow All").first.click(timeout=4000)
            pg.wait_for_timeout(800)
        except Exception:
            pass
        pg.locator("a#d360_intro-play").first.click()
        pg.wait_for_timeout(3500)
        pg.locator('button[title="Close"]:visible').first.click()
        pg.wait_for_timeout(1200)
        pg.get_by_text("EN", exact=True).locator("visible=true").first.click()
        pg.wait_for_timeout(900)
        pg.locator('a[href="https://document360.com/es/"]:visible').first.click()
        pg.wait_for_timeout(6000)
        name = "live_doc360"
    elif which == "wiki":
        pg.goto("http://wikipedia.org", wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
        rec.start(launch_url=pg.url)
        pg.locator("#js-link-box-en").click()
        pg.wait_for_timeout(5000)
        pg.mouse.wheel(0, 400)
        pg.wait_for_timeout(1000)
        name = "live_wiki"
    elif which == "react":
        pg.goto("https://react.dev", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        rec.start(launch_url=pg.url)
        pg.get_by_role("link", name="Learn", exact=True).first.click()
        pg.wait_for_timeout(4000)
        pg.get_by_role("link", name="Reference", exact=True).first.click()
        pg.wait_for_timeout(4000)
        name = "live_react"
    elif which == "vue":
        pg.goto("https://vuejs.org", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        rec.start(launch_url=pg.url)
        pg.get_by_role("link", name="Get Started").first.click()
        pg.wait_for_timeout(4000)
        pg.get_by_role("link", name="Examples").first.click()
        pg.wait_for_timeout(4000)
        name = "live_vue"
    elif which == "bbc":
        pg.goto("http://bbc.com", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        rec.start(launch_url=pg.url)
        pg.locator('a[href="/news"]:visible').first.click()
        pg.wait_for_timeout(5000)
        name = "live_bbc"
    elif which == "github":
        pg.goto("https://github.com", wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        rec.start(launch_url=pg.url)
        pg.locator("header").get_by_text("Product", exact=True).first.hover()
        pg.wait_for_timeout(900)
        pg.locator('a[href$="/features/actions"]:visible').first.click()
        pg.wait_for_timeout(5000)
        name = "live_github"
    else:
        pg.goto("https://www.amazon.com", wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        rec.start(launch_url=pg.url)
        tile = pg.locator('a[aria-label="Jewelry"]').first
        tile.scroll_into_view_if_needed()
        pg.wait_for_timeout(800)
        tile.click()
        pg.wait_for_timeout(6000)
        pg.mouse.wheel(0, 500)
        pg.wait_for_timeout(1500)
        name = "live_amazon_jewelry"
    tc = rec.stop(name=name, stop_reason="terminal_enter")
    drafts = (rec._draft_path, rec._draft_jsonl_path)
    b.close()
for d in drafts:
    if d:
        Path(d).unlink(missing_ok=True)
path = repository.save_recording(tc)
print("SAVED", path)
print([(a["action_type"], bool(a.get("post_click"))) for a in tc["actions"]])
for a in tc["actions"]:
    if a.get("post_click"):
        print(a["action_type"], (a.get("locator_profile") or {}).get("text"), "->", a["post_click"])
