"""Drives the requested Townscript flow live, through the REAL Recorder
(record_session.py) with FIX 1/2/6 active, capturing everything exactly
as a human recording session would - no hardcoded selectors, only
generic text/placeholder/role-based interactions. Stops before any real
payment is ever submitted (closes the tab right after reaching/clicking
"Proceed" toward payment, per explicit instruction not to force a real
transaction). Saves the resulting recording via the same repository the
real app uses, then hands back for replay validation.

    venv/Scripts/python.exe tests/townscript_record_live.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright  # noqa: E402

from recorder.record_session import Recorder  # noqa: E402
from storage import repository  # noqa: E402

LAUNCH_URL = "https://www.townscript.com/in/india"


def shot(page, name):
    path = BASE_DIR / "tests" / f"townscript_{name}.png"
    try:
        page.screenshot(path=str(path))
        print(f"[driver] screenshot: {path}")
    except Exception as e:
        print(f"[driver] screenshot failed ({name}): {e}")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        recorder = Recorder(page)
        recorder.install_context_capture(context)

        page.goto(LAUNCH_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        recorder.start(launch_url=LAUNCH_URL)

        # scroll up and down (per the requested flow)
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(400)
        page.mouse.wheel(0, -600)
        page.wait_for_timeout(400)

        # the "Select Your City" modal's own search caused a full page
        # navigation that closed the page entirely (observed live) -
        # dismiss the modal instead and use the header's own generic
        # search bar, which behaves like an ordinary in-page search.
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            page.mouse.click(5, 5)
            page.wait_for_timeout(300)
        except Exception:
            pass
        search_box = page.get_by_placeholder("Search for events, interests or activities")
        search_box.click()
        search_box.fill("coimbatore")
        search_box.press("Enter")
        page.wait_for_timeout(2000)
        shot(page, "01_search_coimbatore")

        page.mouse.wheel(0, 400)
        page.wait_for_timeout(400)
        page.mouse.wheel(0, -400)
        page.wait_for_timeout(400)

        target = page.get_by_text("Entrepreneurs Meetup", exact=False).first
        target.scroll_into_view_if_needed()
        shot(page, "02_before_select_event")
        with context.expect_page(timeout=8000) as new_page_info:
            target.click()
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded", timeout=15000)
        recorder.record_new_tab(new_page)
        page = new_page
        page.wait_for_timeout(1500)
        shot(page, "03_event_page")

        page.mouse.wheel(0, 600)
        page.wait_for_timeout(400)
        page.mouse.wheel(0, -600)
        page.wait_for_timeout(400)

        add_btn = page.get_by_text("+ Add", exact=False).first
        if add_btn.count() == 0:
            add_btn = page.locator("text=/\\+\\s*Add/i").first
        add_btn.scroll_into_view_if_needed()
        shot(page, "04_before_add")
        add_btn.click()
        page.wait_for_timeout(800)
        shot(page, "05_after_add")

        proceed_btn = page.get_by_text("Proceed", exact=False).first
        proceed_btn.scroll_into_view_if_needed()
        proceed_btn.click()
        page.wait_for_timeout(1200)
        shot(page, "06_after_proceed")

        recorder_actions_so_far = len(recorder.actions)
        print(f"[driver] captured {recorder_actions_so_far} actions so far")

        try:
            name_field = page.get_by_placeholder("Name", exact=False).first
            if name_field.count() == 0:
                name_field = page.locator("input[name*='name' i]").first
            name_field.click()
            name_field.fill("vijay")
        except Exception as e:
            print(f"[driver] name field: {e}")
        shot(page, "07_after_name")

        try:
            email_field = page.get_by_placeholder("Email", exact=False).first
            if email_field.count() == 0:
                email_field = page.locator("input[type='email']").first
            email_field.click()
            email_field.fill("vijayaragavanv18@gmail.com")
        except Exception as e:
            print(f"[driver] email field: {e}")
        shot(page, "08_after_email")

        try:
            email_fields = page.get_by_placeholder("Email", exact=False)
            if email_fields.count() >= 2:
                confirm_email = email_fields.nth(1)
            else:
                confirm_email = page.get_by_placeholder("Confirm", exact=False).first
            confirm_email.click()
            confirm_email.fill("vijayaragavanv18@gmail.com")
        except Exception as e:
            print(f"[driver] confirm email field: {e}")
        shot(page, "09_after_confirm_email")

        try:
            phone_field = page.get_by_placeholder("Phone", exact=False).first
            if phone_field.count() == 0:
                phone_field = page.locator("input[type='tel']").first
            phone_field.click()
            phone_field.fill("9345691852")
        except Exception as e:
            print(f"[driver] phone field: {e}")
        shot(page, "10_after_phone")

        try:
            save_btn = page.get_by_text("Save", exact=False).first
            save_btn.click()
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"[driver] save button: {e}")
        shot(page, "11_after_save")

        try:
            proceed_btn2 = page.get_by_text("Proceed", exact=False).first
            proceed_btn2.click()
            page.wait_for_timeout(1500)
        except Exception as e:
            print(f"[driver] second proceed: {e}")
        shot(page, "12_after_final_proceed")

        # STOP HERE - explicit instruction not to force a real payment.
        # Close the tab immediately, exactly as the requested flow's own
        # last step says, without ever touching a payment form.
        test_case = recorder.stop(stop_reason="terminal_enter")
        path = repository.save_recording(test_case)
        print(f"[driver] recording saved to {path}")
        print(f"[driver] total actions captured: {len(test_case['actions'])}")

        try:
            page.close()
        except Exception:
            pass
        browser.close()

        return path


if __name__ == "__main__":
    saved_path = main()
    print(f"\nSAVED_RECORDING_PATH={saved_path}")
