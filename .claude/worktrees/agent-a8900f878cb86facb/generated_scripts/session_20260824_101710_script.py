"""
Auto-generated from recording: session_20260824_101710
Generated at: 2026-08-24T10:17:10.340734
Original recorded (production) URL: https://sportzia-preprod.kovaionplay.com/feed

Resolution order per step: data-testid -> data-test -> data-cy -> id -> name
-> aria-label -> placeholder -> role -> css_path -> xpath -> text+tag ->
bounding box click. Dropdowns use page.select_option(), form submits use
form.requestSubmit(), meaningful keypresses (Enter/Tab/Escape) use el.press(),
double/right clicks use el.dblclick()/el.click(button="right"), scrolling
uses page.mouse.wheel().

Prints simple progress/result messages only - no internal strategy/step
logs. Set AUTOFLOW_DEBUG=1 to also see which locator strategy was used for
every step.

Run directly with: python session_20260824_101710_script.py [qa_url] [output_json_path] [screenshot_dir] [headless] [product_name]
qa_url defaults to the recorded starting URL if omitted. Running the file
directly launches a VISIBLE (headed) browser so you can watch the replay;
pass "1" as the 4th argument to run headless instead. An optional 5th
argument validates that a product appears on whatever page the recorded
actions end on - no separate search, no re-opening the site.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urljoin

from playwright.sync_api import sync_playwright

# quiet unless AUTOFLOW_DEBUG=1 - this is a replay script, not a report, so
# by default it should just perform the recorded actions and stay silent
# unless something actually fails
_DEBUG = os.environ.get("AUTOFLOW_DEBUG") == "1"
logging.basicConfig(level=logging.DEBUG if _DEBUG else logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# recorded element text can contain characters a terminal's codec can't
# encode (icon-font glyphs, emoji, non-Latin scripts) - on Windows this is
# cp1252/cp437 by default, and an unencodable character reaching a bare
# print() raises UnicodeEncodeError right out of the replay loop, aborting
# every action after it. Reconfiguring stdout/stderr to UTF-8 with a
# replace fallback means a print can never crash the run over encoding.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

STEPS = [   {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Sign in',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div:nth-of-type(2) > div > '
                                           'div > div > div:nth-of-type(3) > div > div > '
                                           'div:nth-of-type(2)',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/div[2]',
                               'text': 'Sign in',
                               'element_text': 'Sign in',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {'x': 1226.125, 'y': 45.5, 'width': 38.875, 'height': 15.199999809265137},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/feed',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:37.664Z',
        'delay_before_ms': 0,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Enter your email or phone number',
                               'placeholder': 'Enter your email or phone number',
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(3) > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[3]/div[1]/input[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'input',
                               'attributes': {   'placeholder': 'Enter your email or phone number',
                                                 'type': 'email'}},
        'bounding_box': {   'x': 442.8000183105469,
                            'y': 346.8000183105469,
                            'width': 426.3999938964844,
                            'height': 43.20000076293945},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/login',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:39.785Z',
        'delay_before_ms': 2121,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/login',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:42.384Z',
        'delay_before_ms': 2599,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Accept',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div:nth-of-type(2) > div > '
                                           'div:nth-of-type(2)',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]',
                               'text': 'Accept',
                               'element_text': 'Accept',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {   'x': 1140,
                            'y': 667.2000122070312,
                            'width': 100,
                            'height': 36.79999923706055},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/login',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:45.766Z',
        'delay_before_ms': 3382,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Enter your email or phone number',
                               'placeholder': 'Enter your email or phone number',
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(3) > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[3]/div[1]/input[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'input',
                               'attributes': {   'placeholder': 'Enter your email or phone number',
                                                 'type': 'email'}},
        'bounding_box': {   'x': 442.8000183105469,
                            'y': 346.8000183105469,
                            'width': 426.3999938964844,
                            'height': 43.20000076293945},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/login',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:47.251Z',
        'delay_before_ms': 1485,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Create an Account',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(6) > div > span',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[6]/div[1]/span[1]',
                               'text': 'Create an Account',
                               'element_text': 'Create an Account',
                               'tag': 'span',
                               'attributes': {}},
        'bounding_box': {   'x': 624.7750244140625,
                            'y': 552,
                            'width': 123.2249984741211,
                            'height': 16.80000114440918},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/login',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:58.259Z',
        'delay_before_ms': 11008,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Enter your full name',
                               'placeholder': 'Enter your full name',
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(3) > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[3]/div[1]/input[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'input',
                               'attributes': {'placeholder': 'Enter your full name'}},
        'bounding_box': {   'x': 442.8000183105469,
                            'y': 341,
                            'width': 426.3999938964844,
                            'height': 42.400001525878906},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:45:59.427Z',
        'delay_before_ms': 1168,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:03.070Z',
        'delay_before_ms': 3643,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'fill',
        'value': 'vijay',
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Enter your full name',
                               'placeholder': 'Enter your full name',
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(3) > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[3]/div[1]/input[1]',
                               'text': 'vijay',
                               'element_text': 'vijay',
                               'tag': 'input',
                               'attributes': {'placeholder': 'Enter your full name'}},
        'bounding_box': {   'x': 442.8000183105469,
                            'y': 341,
                            'width': 426.3999938964844,
                            'height': 42.400001525878906},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:04.074Z',
        'delay_before_ms': 1004,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Enter your email or phone number',
                               'placeholder': 'Enter your email or phone number',
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(4) > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[4]/div[1]/input[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'input',
                               'attributes': {'placeholder': 'Enter your email or phone number'}},
        'bounding_box': {   'x': 442.8000183105469,
                            'y': 405,
                            'width': 426.3999938964844,
                            'height': 42.400001525878906},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:04.299Z',
        'delay_before_ms': 225,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'fill',
        'value': 'vijay@12.co',
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Enter your email or phone number',
                               'placeholder': 'Enter your email or phone number',
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(4) > div > input',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[4]/div[1]/input[1]',
                               'text': 'vijay@12.co',
                               'element_text': 'vijay@12.co',
                               'tag': 'input',
                               'attributes': {'placeholder': 'Enter your email or phone number'}},
        'bounding_box': {   'x': 442.8000183105469,
                            'y': 405,
                            'width': 426.3999938964844,
                            'height': 42.400001525878906},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:19.238Z',
        'delay_before_ms': 14939,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': 'Choose date',
                               'accessible_name': 'Choose date',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(5) > div > div > '
                                           'div > div:nth-of-type(2) > button',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[5]/div[1]/div[1]/div[1]/div[2]/button[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'button',
                               'attributes': {'type': 'button', 'aria-label': 'Choose date'}},
        'bounding_box': {'x': 820, 'y': 467.9750061035156, 'width': 40, 'height': 40},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:19.456Z',
        'delay_before_ms': 218,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#«re»-grid-label',
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'August 2026',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#«re»-grid-label',
                               'xpath': "//*[@id='«re»-grid-label']",
                               'text': 'August 2026',
                               'element_text': 'August 2026',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {'x': 434, 'y': 150, 'width': 92.9625015258789, 'height': 24},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:21.851Z',
        'delay_before_ms': 2395,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': 'radio',
                               'aria_label': None,
                               'accessible_name': '2004',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'body > div:nth-of-type(3) > div:nth-of-type(2) > div > '
                                           'div > div > div:nth-of-type(2) > div > div > '
                                           'div:nth-of-type(105) > button',
                               'xpath': '/html[1]/body[1]/div[3]/div[2]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[105]/button[1]',
                               'text': '2004',
                               'element_text': '2004',
                               'tag': 'button',
                               'attributes': {'type': 'button', 'role': 'radio'}},
        'bounding_box': {'x': 414.8999938964844, 'y': 183, 'width': 72, 'height': 36},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:24.121Z',
        'delay_before_ms': 2270,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': 'gridcell',
                               'aria_label': None,
                               'accessible_name': '23',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'body > div:nth-of-type(3) > div:nth-of-type(2) > div > '
                                           'div > div > div:nth-of-type(2) > div > div > '
                                           'div:nth-of-type(2) > div > div:nth-of-type(4) > '
                                           'button:nth-of-type(2)',
                               'xpath': '/html[1]/body[1]/div[3]/div[2]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div[4]/button[2]',
                               'text': '23',
                               'element_text': '23',
                               'tag': 'button',
                               'attributes': {'type': 'button', 'role': 'gridcell'}},
        'bounding_box': {'x': 472, 'y': 341, 'width': 36, 'height': 36},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:25.548Z',
        'delay_before_ms': 1427,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': '',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(6) > div > div > '
                                           'div',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[6]/div[1]/div[1]/div[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {'x': 410, 'y': 536.5625, 'width': 20, 'height': 20},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:27.548Z',
        'delay_before_ms': 2000,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Sign up',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#3 > div > div > div > div > div > div > div > '
                                           'div:nth-of-type(2) > div:nth-of-type(7)',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[7]',
                               'text': 'Sign up',
                               'element_text': 'Sign up',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {   'x': 410,
                            'y': 578.3624877929688,
                            'width': 460,
                            'height': 49.20000076293945},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:46:28.985Z',
        'delay_before_ms': 1437,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None},
    {   'action_type': 'tab_close',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://sportzia-preprod.kovaionplay.com/signup',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-24T04:47:10.287Z',
        'delay_before_ms': 41302,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None,
        'remaining_page_id': None}]
PROD_URL = "https://sportzia-preprod.kovaionplay.com/feed"
SOURCE_NAME = "session_20260824_101710"
SOURCE_TYPE = "ORIGINAL"

# how long (seconds) to keep the browser open, fully idle, after the last
# action/screenshot/report data is captured - purely so a human watching a
# headed run gets to actually see the final page before it vanishes. Does
# not affect action timing/order, only the moment right before close().
DEFAULT_CLOSE_DELAY = 5

# replay waits BETWEEN actions to roughly match how the actions were
# originally paced when recorded, instead of firing every Playwright call
# back-to-back - a recording is a real user's workflow, and a replay that
# teleports through it isn't a believable rehearsal of that workflow.
# Capped both ways: never less than MIN (even if two actions were
# recorded milliseconds apart) and never more than MAX (a user reading
# the page for 30 seconds mid-recording shouldn't make every replay of
# this test take 30 seconds too).
REPLAY_TIMING_ENABLED = True
MIN_ACTION_DELAY = 0
MAX_ACTION_DELAY = 4


def _parse_timestamp(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _replay_delay(prev_ts, cur_ts):
    """Seconds to wait before replaying cur_ts's action, based on how far
    apart the two actions were actually recorded - not a fixed sleep."""
    if not REPLAY_TIMING_ENABLED:
        return 0
    prev = _parse_timestamp(prev_ts)
    cur = _parse_timestamp(cur_ts)
    if prev is None or cur is None:
        return 0
    delta = (cur - prev).total_seconds()
    if delta <= 0:
        return 0
    return max(MIN_ACTION_DELAY, min(MAX_ACTION_DELAY, delta))


def _step_delay(step, prev_ts, cur_ts):
    """Prefers the recorder's own delay_before_ms (the user's actual
    pacing between normalized actions, captured once at recording time)
    when present, falling back to a timestamp diff for older recordings
    made before that field existed. Either way this is purely recorded
    HUMAN pacing - it's layered on top of, never a substitute for, the
    Playwright waits (_settle, scroll_into_view_if_needed, etc.) that
    handle actual page/element readiness elsewhere in this loop."""
    if not REPLAY_TIMING_ENABLED:
        return 0
    delay_ms = step.get("delay_before_ms")
    if delay_ms is not None:
        return max(MIN_ACTION_DELAY, min(MAX_ACTION_DELAY, delay_ms / 1000))
    return _replay_delay(prev_ts, cur_ts)


def _slug(text, max_len=20):
    """Sanitizes recorded element text into a short, filesystem-safe
    fragment for screenshot filenames, e.g. "Add to Cart" -> "add_to_cart".
    Returns "" when there's nothing usable (caller falls back to just the
    action type)."""
    if not text:
        return ""
    safe = "".join(c if c.isalnum() else "_" for c in text.strip().lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_")[:max_len]


def _screenshot_name(i, step):
    action_type = step.get("action_type")
    label = None
    if action_type not in ("navigate", "scroll"):
        label, _ = _describe_step(step)
        if label == "(element)":
            label = None
    elif action_type == "navigate":
        label = step.get("page_url")
    slug = _slug(label)
    base = f"{i:03d}_{action_type}" + (f"_{slug}" if slug else "")
    return base


def _describe_step(step):
    """Best-effort human label + locator string for the per-action
    terminal log - mirrors the recorder's own [RECORDED] line style so
    replay output reads like a continuation of the recording's."""
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    text = (lp.get("element_text") or lp.get("text") or "").strip()
    value = step.get("value")
    # a click-type action with no recorded locator text falls back to
    # Value as its target text at replay time too (see resolve_and_act's
    # tier 11b) - describe it the same way here for an accurate log
    value_as_text = (
        value
        if step.get("action_type") in ("click", "dblclick", "right_click") and value
        else None
    )
    label = (
        text
        or value_as_text
        or lp.get("accessible_name")
        or lp.get("aria_label") or attrs.get("aria-label")
        or lp.get("placeholder") or attrs.get("placeholder")
        or lp.get("id")
        or lp.get("tag")
        or "(element)"
    )
    locator_display = (
        lp.get("id")
        or (f'a[href="{lp["href"]}"]' if lp.get("href") else None)
        or lp.get("css_path")
        or lp.get("xpath")
        or "(no stable locator found - will fall back to screen position)"
    )
    return label, locator_display


def _locator_attempts(step):
    """Numbered list of every locator tier resolve_and_act() would try for
    this step, in the same priority order, for failure diagnostics - shows
    what was actually available to try, not just the one that "won"."""
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    action_type = step.get("action_type")
    value = step.get("value")
    tiers = [
        ("data-testid", attrs.get("data-testid")),
        ("data-test", attrs.get("data-test")),
        ("data-cy", attrs.get("data-cy")),
        ("id", lp.get("id")),
        ("name", attrs.get("name") or lp.get("name")),
        ("aria-label", attrs.get("aria-label") or lp.get("aria_label")),
        ("placeholder", attrs.get("placeholder") or lp.get("placeholder")),
        ("title", attrs.get("title") or lp.get("title")),
        ("role", attrs.get("role") or lp.get("role")),
        ("href", lp.get("href")),
        ("text", lp.get("element_text") or lp.get("text")),
        ("css_path", lp.get("css_path")),
        ("xpath", lp.get("xpath")),
    ]
    if action_type in ("click", "dblclick", "right_click") and not lp.get("text") and value:
        tiers.append(("text (from value)", value))
    box = step.get("bounding_box")
    if action_type in ("click", "dblclick", "right_click") and box and box.get("width") and box.get("height"):
        tiers.append(("bounding_box", f"x={box.get('x')}, y={box.get('y')}"))

    present = [(k, v) for k, v in tiers if v]
    if not present:
        return ["(no locator information recorded for this action)"]
    return [f"{i}. {k}={v}" for i, (k, v) in enumerate(present, start=1)]


def _print_step_header(i, total, step):
    action_type = step.get("action_type")
    page_id = step.get("page_id", 0)
    print("=" * 50)
    print(f"[{i}/{total}]")
    print(f"ACTION: {action_type}")
    if page_id:
        print(f"PAGE: {page_id}")
    if action_type == "navigate":
        print(f"URL: {step.get('page_url')}")
        if step.get("new_tab"):
            print("(new tab/page - replay switches to it for subsequent actions)")
    elif action_type == "scroll":
        print(f"Delta: ({step.get('delta_x')}, {step.get('delta_y')})")
    elif action_type == "press":
        print(f"Key: {step.get('value')}")
    elif action_type == "tab_switch":
        print(f"Switch: page {step.get('from_page_id')} -> page {step.get('to_page_id')}")
    elif action_type == "tab_open":
        print(f"URL: {step.get('page_url')}")
        print(f"(new tab/page opened from page {step.get('from_page_id')} - replay switches to it for subsequent actions)")
    elif action_type == "tab_close":
        print(f"Closing page {step.get('page_id')} -> remaining page {step.get('remaining_page_id')}")
    elif action_type in ("click", "dblclick", "right_click", "submit", "fill", "select"):
        label, locator_display = _describe_step(step)
        print(f"Element: {label}")
        print(f"Locator: {locator_display}")
        if action_type in ("fill", "select"):
            print(f"Value: {step.get('value')}")
    print()


def to_qa_url(recorded_url, qa_base):
    """Map a URL recorded against production onto the QA host, keeping the
    path/query intact. Relative URLs and third-party domains pass through
    mostly unchanged - only the domain we actually recorded against gets
    swapped for the QA one.
    """
    if not recorded_url:
        return qa_base
    qa = urlsplit(qa_base)
    rec = urlsplit(recorded_url)
    if not rec.netloc:
        # already a relative/path-only URL - just point it at the QA host
        return urlunsplit((qa.scheme, qa.netloc, rec.path, rec.query, rec.fragment))
    prod = urlsplit(PROD_URL) if PROD_URL else None
    if prod and rec.netloc == prod.netloc:
        return urlunsplit((qa.scheme, qa.netloc, rec.path, rec.query, rec.fragment))
    # different domain than what we recorded against (e.g. a third-party
    # link) - leave it alone rather than guessing
    return recorded_url


def _by_attr(page, attr, value):
    """Locate by a raw HTML attribute value, e.g. [data-testid="submit"]."""
    if not value:
        return None
    try:
        safe = value.replace('"', '\"')
        c = page.locator(f'[{attr}="{safe}"]')
        if c.count() > 0:
            return c.first
    except Exception:
        pass
    return None


def _find_by_id(page, lp):
    if not lp.get("id"):
        return None
    try:
        c = page.locator(lp["id"])
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _find_by_role(page, lp, attrs):
    role = attrs.get("role") or lp.get("role")
    if not role:
        return None
    try:
        name = lp.get("accessible_name") or lp.get("text") or None
        c = page.get_by_role(role, name=name)
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _normalize_href_for_match(href, base_url, keep_query):
    """Resolves href to a comparable (scheme, host, path[, query]) key for
    deciding whether it points at the SAME target as another href - not a
    fuzzy/similarity match, an equivalence check: two hrefs that represent
    the same resource (one absolute, one relative; with/without a
    trailing slash; differing only in tracking-style query params) must
    normalize to the same key, but any genuine path difference still
    means "different target", full stop.

    keep_query is decided ONCE by the caller from the RECORDED href alone
    (see _find_by_href) and applied identically to both sides being
    compared - a live element's .href is always a fully-resolved absolute
    URL and so always has a path, so deciding "keep the query" per-href
    independently would make the two sides permanently disagree whenever
    the recorded reference itself was query-only.
    """
    if not href:
        return None
    try:
        parts = urlsplit(urljoin(base_url, href))
    except Exception:
        return None
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return (parts.scheme, parts.netloc, path, parts.query if keep_query else "")


def _find_by_href(page, lp):
    if not lp.get("href"):
        return None
    recorded_href = lp["href"]
    # a recorded reference with no path component of its own (a query-
    # only or fragment-only reference like "?tab=reviews") means the
    # query IS what distinguishes the target - otherwise the query
    # string/fragment are ignored (tracking params, session ids, etc.
    # commonly vary without representing a different target)
    try:
        keep_query = not urlsplit(recorded_href).path
    except Exception:
        keep_query = False
    recorded_key = _normalize_href_for_match(recorded_href, page.url, keep_query)
    if recorded_key is None:
        return None
    try:
        anchors = page.locator("a[href]")
        live_hrefs = anchors.evaluate_all("els => els.map(el => el.href)")
    except Exception:
        return None
    for i, live_href in enumerate(live_hrefs):
        if _normalize_href_for_match(live_href, page.url, keep_query) == recorded_key:
            try:
                return anchors.nth(i)
            except Exception:
                return None
    return None


def _find_by_text_tag(page, lp):
    # exact, whole-trimmed-text match against each candidate's own text -
    # Playwright's has_text (substring match anywhere in the subtree) is
    # too permissive for short/generic labels ("8", "1", "OK") common to
    # pagination, quantity/size pickers, star ratings, etc. on any site,
    # and can silently grab the wrong element that merely CONTAINS the
    # recorded text rather than the one that IS that text.
    if not (lp.get("text") and lp.get("tag")):
        return None
    text = lp["text"].strip()
    if not text:
        return None
    try:
        loc = page.locator(lp["tag"])
        texts = loc.all_inner_texts()
    except Exception:
        return None

    exact_idx = [i for i, t in enumerate(texts) if t.strip() == text]
    if not exact_idx:
        lowered = text.lower()
        exact_idx = [i for i, t in enumerate(texts) if t.strip().lower() == lowered]
    if not exact_idx:
        return None

    # very short or purely numeric text is an inherently weak signal on
    # any site (it's exactly the kind of label pagination/size/quantity/
    # rating controls use) - only trust it when it's genuinely
    # unambiguous on this page; with multiple exact matches there's no
    # reliable way to know which one the user meant, so this tier is
    # skipped entirely (falls through to css_path/xpath) rather than
    # blindly taking the first match
    is_weak_text = len(text) <= 2 or text.isdigit()
    if is_weak_text and len(exact_idx) != 1:
        return None

    try:
        return loc.nth(exact_idx[0])
    except Exception:
        return None


def _find_by_value_text(page, lp, value, action_type):
    # a click-type action with no recorded locator text at all (e.g.
    # manually added in the Recording Editor) still has its Value, which
    # for a click is normally the visible text of the link/button to
    # click - never treated as the ONLY locator source when real
    # locator_profile.text exists (that's tried first, above)
    if lp.get("text") or not value or action_type not in ("click", "dblclick", "right_click"):
        return None
    try:
        c = page.get_by_text(value, exact=True)
        if c.count() == 0:
            c = page.get_by_text(value)
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _find_by_css(page, lp):
    if not lp.get("css_path"):
        return None
    try:
        c = page.locator(lp["css_path"])
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _find_by_xpath(page, lp):
    if not lp.get("xpath"):
        return None
    try:
        c = page.locator("xpath=" + lp["xpath"])
        return c.first if c.count() > 0 else None
    except Exception:
        return None


def _parse_nth_of_type(segment):
    """Returns (tag, position) if this single css_path segment carries an
    explicit :nth-of-type(N) suffix (exactly how cssPath() in
    action_capture.js writes a non-unique sibling), else None. Plain
    string parsing, not regex - the format is simple and fixed enough
    that a dependency isn't worth adding for it.
    """
    marker = ":nth-of-type("
    idx = segment.find(marker)
    if idx == -1 or not segment.endswith(")"):
        return None
    tag = segment[:idx]
    num_str = segment[idx + len(marker):-1]
    if not (tag and num_str.isdigit()):
        return None
    return tag, int(num_str)


def _find_by_position(page, lp, info=None):
    """Fallback for when the recorded href/text no longer identifies an
    element anywhere on the page - the underlying content genuinely
    changed since recording (a different item now occupies that slot in
    a product grid, article feed, search results list, etc, on any
    site, static or dynamic). Re-derives "the Nth <tag> among its
    siblings under this container" from the recorded css_path's own
    :nth-of-type segment (css_path already encodes this - no new
    recorded field needed) and finds whatever CURRENTLY occupies that
    same structural position in the live DOM, rather than trying to
    relocate the specific recorded item by content.

    This is deliberately looser than the css_path tier itself, which
    applies the whole recorded path fairly literally and is fragile to
    any structural drift above the repeating element - here, only the
    repeating element's own tag and position among its immediate
    siblings matters, wherever its container now is. Position among
    structurally-similar siblings is the ONLY signal used - no text/
    content similarity, no scoring, nothing fuzzy.

    info, when given a dict, is populated with the position/tag actually
    used so the caller can report that a position fallback (not an exact
    match) is what resolved this step.

    Returns the resolved element, or None if the recorded css_path has
    no positional information to fall back on, or nothing currently
    occupies that position.
    """
    css_path = lp.get("css_path")
    if not css_path:
        return None

    segments = [s.strip() for s in css_path.split(">")]

    repeat_idx = None
    tag = None
    position = None
    for i in range(len(segments) - 1, -1, -1):
        parsed = _parse_nth_of_type(segments[i])
        if parsed:
            repeat_idx = i
            tag, position = parsed
            break

    if repeat_idx is None:
        return None

    container_selector = " > ".join(segments[:repeat_idx])
    remainder_selector = " > ".join(segments[repeat_idx + 1:])

    try:
        siblings = page.locator(f"{container_selector} > {tag}") if container_selector else page.locator(tag)
        if siblings.count() < position:
            return None
        target = siblings.nth(position - 1)
        if remainder_selector:
            descendant = target.locator(remainder_selector)
            if descendant.count() == 0:
                return None
            target = descendant.first
        if info is not None:
            info["tag"] = tag
            info["position"] = position
        return target
    except Exception:
        return None


def _try_dismiss_overlay(page):
    """Best-effort, generic recovery from an unexpected overlay/modal/
    dialog blocking a click - Escape, then a generically-matched close
    button (aria-label containing "close", anywhere, optionally inside a
    role=dialog element). No assumptions about any particular site's
    modal/lightbox/gallery markup; failures here are swallowed since this
    is purely a recovery attempt, not the action itself.
    """
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        close_btn = page.locator(
            '[role="dialog"] [aria-label*="close" i], [aria-label*="close" i]'
        ).first
        if close_btn.count() > 0:
            close_btn.click(timeout=1000)
    except Exception:
        pass


def _do_fill(el, value):
    """Fill el with value; if the direct value-set doesn't stick (some
    fields only react to real keystrokes - input masks, auto-advancing
    multi-box PIN/OTP inputs, etc.), retry by typing the characters
    instead, which fires the same key/input events a real user's typing
    would. Generic recovery for ANY fill whose direct-set didn't take
    effect, not specific to any particular kind of field.
    """
    filled_ok = False
    try:
        el.fill(value, timeout=5000)
        filled_ok = el.input_value(timeout=1000) == value
    except Exception:
        filled_ok = False
    if not filled_ok:
        try:
            el.clear(timeout=2000)
        except Exception:
            pass
        el.press_sequentially(value, timeout=5000)


def resolve_and_act(page, step):
    """Try each locator strategy in priority order, then perform the step's
    action. Strongest/most stable signals first (test-automation attributes,
    id, other stable attributes), generic/fragile ones last.

    Unlike a simple "first tier that finds anything wins" search, EVERY
    tier that finds an element gets an actual attempt at the action before
    moving on - a tier can locate the right element in the DOM while that
    element is temporarily not visible/actionable (mid-animation, behind
    an overlay, hidden at the current viewport), and only the interaction
    itself reveals that. Falling through to the next tier in that case
    (rather than declaring the step failed) is what "use fallback locators
    if the primary locator fails" means in practice, not just "if the
    primary locator finds nothing."

    Returns (strategy_used, element_found, success, error_message).
    element_found is True for any real locator hit (everything except the
    bounding-box fallback, which still lets the step succeed but does NOT
    count as "found" for UI element validation purposes.
    """
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    action_type = step.get("action_type")
    value = step.get("value")

    # an action type this executor has no handler for must never be
    # silently treated as a no-op success just because a locator happened
    # to resolve - fail it outright, clearly labeled, before spending any
    # time searching for an element to act on
    SUPPORTED_ACTIONS = ("click", "dblclick", "right_click", "fill", "select", "submit", "press")
    if action_type not in SUPPORTED_ACTIONS:
        return None, False, False, f"UNSUPPORTED action_type: {action_type!r}"

    # same priority as before: test-automation attributes, id, other
    # stable/human-meaningful attributes, role+accessible-name, href,
    # visible text, value-as-text, then the positional/structural
    # fallbacks - just tried as attempt-then-fall-through instead of
    # find-then-commit
    tiers = [
        ("data-testid", lambda: _by_attr(page, "data-testid", attrs.get("data-testid"))),
        ("data-test", lambda: _by_attr(page, "data-test", attrs.get("data-test"))),
        ("data-cy", lambda: _by_attr(page, "data-cy", attrs.get("data-cy"))),
        ("id", lambda: _find_by_id(page, lp)),
        ("name", lambda: _by_attr(page, "name", attrs.get("name"))),
        ("aria-label", lambda: _by_attr(page, "aria-label", attrs.get("aria-label"))),
        ("placeholder", lambda: _by_attr(page, "placeholder", attrs.get("placeholder"))),
        ("title", lambda: _by_attr(page, "title", attrs.get("title"))),
        ("role", lambda: _find_by_role(page, lp, attrs)),
        ("href", lambda: _find_by_href(page, lp)),
        ("text+tag", lambda: _find_by_text_tag(page, lp)),
        ("text+tag", lambda: _find_by_value_text(page, lp, value, action_type)),
        # only reached once every exact-content signal above (href, text)
        # has found NOTHING at all - the recorded item's identity can no
        # longer be verified on the live page (content genuinely changed
        # since recording, on any site). Position among structurally-
        # similar siblings, derived from the recorded css_path itself, is
        # the sole fallback signal - never text/content similarity.
        # Placed before css_path/xpath since those apply the recorded
        # path fairly literally (fragile to any structural drift above
        # the repeating element) while this is deliberately looser.
        ("position_fallback", lambda: _find_by_position(page, lp, position_fallback_info)),
        ("css_path", lambda: _find_by_css(page, lp)),
        ("xpath", lambda: _find_by_xpath(page, lp)),
    ]

    element_found = False
    last_err = None
    position_fallback_info = {}

    for strategy, finder in tiers:
        try:
            el = finder()
        except Exception:
            el = None
        if el is None:
            continue
        element_found = True
        # position_fallback means the recorded item's identity couldn't
        # be verified at all (content genuinely changed since recording)
        # - a successful click here is still a real success, but it must
        # never look indistinguishable from an exact-content match in
        # the step's own result, or a silently-wrong-item click could
        # pass as if nothing were amiss
        success_note = None
        if strategy == "position_fallback":
            success_note = (
                f"recorded target not found - used same position "
                f"(#{position_fallback_info.get('position')}) instead, "
                f"content may differ from recording"
            )
        try:
            el.scroll_into_view_if_needed(timeout=5000)
            if action_type == "click":
                el.click(timeout=5000)
            elif action_type == "dblclick":
                el.dblclick(timeout=5000)
            elif action_type == "right_click":
                el.click(timeout=5000, button="right")
            elif action_type == "fill" and value is not None:
                _do_fill(el, value)
            elif action_type == "select" and value is not None:
                el.select_option(value, timeout=5000)
            elif action_type == "submit":
                el.evaluate("f => f.requestSubmit ? f.requestSubmit() : f.submit()")
            elif action_type == "press" and value:
                el.press(value, timeout=5000)
            # which tier actually won - only visible with AUTOFLOW_DEBUG=1
            # (same gate as the failure logging below), useful for
            # diagnosing a future "resolved to the wrong element" report
            # on any site the same way this one was diagnosed
            logger.debug("step resolved via strategy=%s", strategy)
            if success_note:
                print(success_note)
            return strategy, element_found, True, success_note
        except Exception as e:
            # this tier found a real element but the interaction itself
            # failed (not visible/not stable/obscured, most commonly).
            # For click-type actions specifically, this is also exactly
            # what an unexpected overlay/modal/dialog blocking the real
            # target looks like - one generic, site-agnostic recovery
            # attempt (Escape / a generically-matched close button) plus
            # a single retry on this SAME element before giving up on
            # this tier, since the recovery may well have been all that
            # was needed.
            if action_type in ("click", "dblclick", "right_click"):
                _try_dismiss_overlay(page)
                try:
                    if action_type == "click":
                        el.click(timeout=3000)
                    elif action_type == "dblclick":
                        el.dblclick(timeout=3000)
                    else:
                        el.click(timeout=3000, button="right")
                    logger.debug("step resolved via strategy=%s (after overlay recovery)", strategy)
                    if success_note:
                        print(success_note)
                    return strategy, element_found, True, success_note
                except Exception as e2:
                    e = e2
            # a DIFFERENT tier might resolve to a different, actually-
            # interactable element (or the same one in a different
            # state by the time it's tried), so keep going rather than
            # give up here - Playwright's own exception text includes a
            # full multi-line retry trace that's only useful for
            # debugging, not for a "did my replay work" run
            logger.debug("resolved via %s but action failed: %s", strategy, e)
            last_err = str(e)
            continue

    if not element_found:
        last_err = "none of the locator strategies (data-testid/data-test/data-cy/id/name/aria-label/placeholder/title/role/href/text+tag/css_path/xpath) matched an element"

        # last resort for fill/select ONLY, and only once every named
        # locator has come up completely empty: some frameworks swap or
        # restructure an input's DOM the moment it receives focus
        # (floating-label / animated fields - the unfocused node the
        # recorder saw no longer exists once focused), so a fresh locator
        # query for the ORIGINAL attributes can genuinely match nothing
        # even though the right field is right there, already focused, by
        # the immediately-preceding click. Whatever the page currently has
        # focused is a reliable, framework-agnostic signal of intent for
        # exactly this click-then-type pattern - not a guess about page
        # content, since it only fires once every real locator has failed.
        if action_type in ("fill", "select") and value is not None:
            try:
                focused_tag = page.evaluate(
                    "document.activeElement && document.activeElement.tagName"
                )
            except Exception:
                focused_tag = None
            if focused_tag in ("INPUT", "TEXTAREA", "SELECT"):
                try:
                    el = page.locator(":focus")
                    el.scroll_into_view_if_needed(timeout=5000)
                    if action_type == "fill":
                        _do_fill(el, value)
                    else:
                        el.select_option(value, timeout=5000)
                    logger.debug("step resolved via strategy=focused_element_fallback")
                    return "focused_element_fallback", True, True, None
                except Exception as e:
                    last_err = str(e)

    # bounding box is a last resort for click-type actions only - selects/
    # submits/keypresses need a real element to act on, a blind coordinate
    # click would just do the wrong thing. Only one dimension needs to be
    # non-zero, not both: some real, genuinely-clickable elements report
    # zero WIDTH (or height) in their own computed box (icon/badge header
    # links using overflow-visible children are a common real-world case)
    # - Playwright's own el.click() already refused these as "not visible"
    # above, but a raw pixel click doesn't require that same check and can
    # still land on real rendered content at that coordinate. A box where
    # BOTH dimensions are zero occupies no space at all and is skipped.
    box = step.get("bounding_box")
    if action_type in ("click", "dblclick", "right_click") and box and (box.get("width") or box.get("height")):
        try:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            if action_type == "dblclick":
                page.mouse.dblclick(x, y)
            elif action_type == "right_click":
                page.mouse.click(x, y, button="right")
            else:
                page.mouse.click(x, y)
            return "bounding_box", element_found, True, None
        except Exception as e:
            return "bounding_box", element_found, False, f"coordinate click failed: {e}"

    return None, element_found, False, last_err


def _resolve_and_act_with_retry(page, step, retry_budget_s=4.5, retry_interval_s=0.35):
    """fill/select actions are the ones exposed to a different failure mode
    than click-type actions: the target can genuinely not exist in the DOM
    yet at the single instant resolve_and_act tries it - an async page
    transition still loading (a form submit that triggers a backend call
    before the next screen renders), or a framework that rebuilds an
    input's DOM node on focus and hasn't settled yet. In both cases every
    locator tier - including the focused-element fallback, since nothing
    may be focused/existing yet either - correctly finds nothing, because
    there is genuinely nothing there YET, not because the wrong thing was
    searched for.

    This is a different problem from what Playwright's own per-element
    actionability retrying already covers (that only helps once a locator
    has found *a* matching element and is waiting for it to become
    interactable) - here nothing matches at all, so the fix is to retry
    the entire search-and-act attempt, fresh, for a bounded window, not to
    wait longer on a single found element.

    Click/dblclick/right_click/submit/press are unaffected - only
    fill/select get this treatment, and only because they're the ones
    actually exposed to this timing gap.
    """
    if step.get("action_type") not in ("fill", "select"):
        return resolve_and_act(page, step)

    deadline = time.monotonic() + retry_budget_s
    result = resolve_and_act(page, step)
    while not result[2] and time.monotonic() < deadline:
        page.wait_for_timeout(int(retry_interval_s * 1000))
        result = resolve_and_act(page, step)
    return result


def _dismiss_dialog(dialog):
    logger.debug("dialog appeared (%s): %s - dismissing", dialog.type, dialog.message)
    dialog.dismiss()


def _get_valid_open_page(pages, preferred=None):
    """Returns any still-open Page from the runtime registry, or None if
    every page has closed. `preferred` (typically the loop's last-used
    page) is tried first - after a recorded tab_close, that variable can
    be pointing at an already-closed Page, and calling ANY Playwright
    method on a closed Page raises TargetClosedError, so nothing past the
    main action loop (final state capture, the close-delay pause) may
    touch a page without going through this first.
    """
    candidates = ([preferred] if preferred is not None else []) + list(pages.values())
    for pg in candidates:
        if pg is None:
            continue
        try:
            if not pg.is_closed():
                return pg
        except Exception:
            continue
    return None


def _resolve_target_page(pages, target_page_id, anchor_page, fallback_url=None, wait_seconds=5):
    """Returns (page_or_None, reason) for the page a step with this
    page_id should execute against. reason is None on success, or a
    concrete explanation of why resolution failed - callers must surface
    it rather than let a page-mismatch fail silently with no clue why.

    The common case (page already known - almost always page_id 0)
    returns immediately with no waiting at all. A page_id that hasn't
    appeared yet is given a short window to show up via the context's
    "page" event (it's usually mid-flight from the click that immediately
    preceded this step) before falling back to opening it directly at the
    recorded URL, so a popup that doesn't fire identically on this run
    still doesn't stall or silently misdirect the action to the wrong page.
    """
    if target_page_id in pages:
        existing = pages[target_page_id]
        try:
            closed = existing.is_closed()
        except Exception:
            closed = True
        if not closed:
            return existing, None
        return None, (
            f"page_id={target_page_id} was already closed (a recorded tab_close closed "
            f"it earlier in this replay) and cannot be used for this action"
        )

    # anchor_page (typically the loop's last-used page) may itself already
    # be closed here - e.g. the immediately preceding step was a
    # tab_close on exactly this page, and this step needs a page_id that
    # hasn't appeared yet. Any Playwright call on a closed Page raises
    # TargetClosedError, so the poll below (and the fallback context
    # access further down) must use a genuinely open page, not
    # necessarily anchor_page itself.
    safe_anchor = _get_valid_open_page(pages, preferred=anchor_page)
    if safe_anchor is None:
        return None, (
            f"page_id={target_page_id} has not appeared and no open page remains "
            f"to wait on or open a fallback page from (every registered page is closed)"
        )

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if target_page_id in pages:
            return pages[target_page_id], None
        safe_anchor.wait_for_timeout(100)

    if not fallback_url:
        return None, (
            f"waited {wait_seconds}s for page_id={target_page_id} to appear as a new "
            f"tab/page (context 'page' event) but it never did, and this step has no "
            f"recorded URL to fall back to opening it directly"
        )

    try:
        new_page = safe_anchor.context.new_page()
        new_page.set_default_timeout(8000)
        new_page.on("dialog", _dismiss_dialog)
        new_page.goto(fallback_url, wait_until="domcontentloaded", timeout=30000)
        pages[target_page_id] = new_page
        return new_page, None
    except Exception as e:
        return None, (
            f"waited {wait_seconds}s for page_id={target_page_id} to appear as a new "
            f"tab/page but it never did; fallback attempt to open {fallback_url!r} "
            f"directly also failed: {e}"
        )


def _settle(page):
    """domcontentloaded fires before JS-heavy sites (Amazon's search box,
    for one) finish rendering the elements a step is about to look for -
    without this, the very next action can find nothing there yet and skip.
    Best-effort only: sites that never go network-idle just get the full
    timeout and move on rather than hanging the replay.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def _replay_scroll(page, dx, dy, scroll_y_after=None, element=None):
    """Replay a recorded scroll gradually instead of one instant jump - a
    single page.mouse.wheel(dx, dy) call for a large accumulated delta
    would teleport the page instead of scrolling it the way the original
    action looked. Breaking it into smaller hops with brief pauses gets
    much closer to the real thing without needing to match its timing
    exactly.

    scroll_y_after is the absolute vertical position the page actually
    ended up at when this action was recorded. The incremental hops above
    still provide the visual motion, but afterwards the vertical position
    is snapped to that exact recorded value - the live page's document
    height can differ slightly from record time (ads, lazy-loaded
    content, a different viewport), so replaying the recorded delta alone
    can drift short of or past where the user actually ended up. There's
    no recorded absolute value for horizontal movement, so delta_x is
    always replayed as-is. Older recordings made before scroll_y_after
    existed simply omit it, leaving this as pure delta replay like before.

    element, when provided, is the resolved locator for the SPECIFIC
    scrollable container this action was recorded on (a nested panel, not
    the window) - scrolling happens on that element directly via
    scrollLeft/scrollTop rather than page.mouse.wheel(), since replay
    can't rely on the mouse already being positioned over that container
    the way it naturally was when the action was recorded. When element
    is None (plain window scrolling, or an older recording with no
    container locator), behavior is exactly as before this parameter
    existed: page.mouse.wheel() + window.scrollTo().
    """
    total = max(abs(dx), abs(dy))
    steps = max(1, min(20, int(total / 120)))
    step_dx = dx / steps
    step_dy = dy / steps

    if element is not None:
        for _ in range(steps):
            try:
                element.evaluate(
                    "(el, d) => { el.scrollLeft += d[0]; el.scrollTop += d[1]; }",
                    [step_dx, step_dy],
                )
            except Exception:
                pass
            page.wait_for_timeout(40)
        if scroll_y_after is not None:
            try:
                element.evaluate("(el, y) => { el.scrollTop = y; }", scroll_y_after)
            except Exception:
                pass
        return

    for _ in range(steps):
        page.mouse.wheel(step_dx, step_dy)
        page.wait_for_timeout(40)
    if scroll_y_after is not None:
        try:
            # the options-object form only changes what's actually
            # specified - omitting "left" leaves whatever horizontal
            # position the delta_x hops above already produced alone,
            # only snapping the vertical position to the recorded value
            page.evaluate("y => window.scrollTo({top: y})", scroll_y_after)
        except Exception:
            pass


# --- Product search validation (optional Phase 6 addition) --------------
# Runs against the SAME page the recorded workflow already produced -
# never re-opens the site or re-runs a search of its own. Whatever page
# the recorded/replayed actions ended up on is what gets scanned. Generic
# on purpose: just scans <a> elements for plausible product-title-length
# text, no site-specific selectors, so it works the same on Amazon,
# Flipkart, or anywhere else.
PRODUCT_MIN_TITLE_LEN = 15
PRODUCT_MAX_TITLE_LEN = 300
PRODUCT_MAX_SCROLLS = 15
PRODUCT_SCROLL_STEP_PX = 1800


def _normalize_product_text(text):
    return " ".join((text or "").split()).strip().lower()


def _scan_product_candidates(page, target_norm, seen, position, similar_matches):
    """One pass over the currently-rendered links. Mutates seen/similar_matches
    in place, returns (exact_match_or_None, updated_position). position only
    advances for genuinely new (not-yet-seen) candidates, so a result that's
    already on screen from a previous scroll pass never gets counted twice.
    """
    try:
        links = page.locator("a")
        count = links.count()
    except Exception:
        return None, position

    for i in range(count):
        el = links.nth(i)
        try:
            text = (el.inner_text(timeout=1000) or "").strip()
        except Exception:
            continue

        if len(text) < PRODUCT_MIN_TITLE_LEN or len(text) > PRODUCT_MAX_TITLE_LEN:
            continue
        norm = _normalize_product_text(text)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        position += 1

        if norm == target_norm:
            href = None
            try:
                href = el.get_attribute("href")
            except Exception:
                pass
            return {"position": position, "title": text, "url": href}, position

        if len(similar_matches) < 5 and (target_norm in norm or norm in target_norm):
            similar_matches.append({"position": position, "title": text})

    return None, position


def _validate_product(page, product_name, shot_dir):
    """Scans the CURRENT page - wherever replay left it - for an exact
    match of product_name, scrolling to reveal more results as needed.
    Stops once the page stops growing for two rounds in a row (reached the
    end of the results) so it can't loop forever on an endless feed.
    """
    target_norm = _normalize_product_text(product_name)
    seen = set()
    similar_matches = []
    position = 0

    match, position = _scan_product_candidates(page, target_norm, seen, position, similar_matches)

    if not match:
        stable_rounds = 0
        last_height = None
        for _ in range(PRODUCT_MAX_SCROLLS):
            try:
                height_before = page.evaluate("document.body.scrollHeight")
            except Exception:
                height_before = last_height
            try:
                page.mouse.wheel(0, PRODUCT_SCROLL_STEP_PX)
            except Exception:
                break
            page.wait_for_timeout(700)
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass

            match, position = _scan_product_candidates(page, target_norm, seen, position, similar_matches)
            if match:
                break

            try:
                height_after = page.evaluate("document.body.scrollHeight")
            except Exception:
                height_after = height_before
            if height_before is not None and height_after is not None and height_after <= height_before:
                stable_rounds += 1
                if stable_rounds >= 2:
                    break
            else:
                stable_rounds = 0
            last_height = height_after

    screenshot = None
    try:
        shot_path = Path(shot_dir) / "product_validation.png"
        page.screenshot(path=str(shot_path))
        screenshot = str(shot_path)
    except Exception:
        pass

    try:
        current_url = page.url
    except Exception:
        current_url = None

    if match:
        return {
            "status": "PASS",
            "product": product_name,
            "found": True,
            "match_type": "exact",
            "position": match["position"],
            "page": 1,
            "title": match["title"],
            "url": match["url"],
            "screenshot": screenshot,
            "reason": None,
            "checked_count": position,
            "search_url": current_url,
        }

    if similar_matches:
        best = similar_matches[0]
        reason = (
            "Exact product not found after checking all available results - "
            f'a similar result was seen at position #{best["position"]}: "{best["title"]}"'
        )
        match_type = "similar"
    else:
        reason = "Product not found after checking all available results"
        match_type = None

    return {
        "status": "FAIL",
        "product": product_name,
        "found": False,
        "match_type": match_type,
        "position": None,
        "page": 1,
        "title": None,
        "url": None,
        "screenshot": screenshot,
        "reason": reason,
        "checked_count": position,
        "search_url": current_url,
    }


def run(qa_url, output_json_path=None, screenshot_dir=None, headless=True, product_name=None):
    print("Starting replay...")
    result = {
        "status": "FAIL",
        "message": "",
        "qa_url": qa_url,
        "steps": [],
        "final_url": None,
        "final_screenshot": None,
        "final_text": None,
        "product_validation": None,
    }

    shot_dir = Path(screenshot_dir) if screenshot_dir else Path(__file__).resolve().parent / "run_screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless)
        except Exception as e:
            # a headed launch can fail on a machine with no display (e.g. a
            # bare server) - headless still lets the replay actually run
            if not headless:
                logger.warning("headed launch failed (%s), falling back to headless", e)
                browser = p.chromium.launch(headless=True)
            else:
                raise
        print("Browser launched.")
        # an explicit context (not the browser.new_page() shorthand) -
        # that shorthand creates a context that only ever supports the one
        # page it made, and raises "Please use browser.new_context()" the
        # moment anything (like the multi-page fallback below) tries to
        # open a second page on it. An explicit context matches how
        # recording already works (see app.py) and actually supports the
        # multi-page workflows recordings can contain.
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(8000)
        # cookie banners/alerts shouldn't be able to hang an unattended run
        page.on("dialog", _dismiss_dialog)

        try:
            page.goto(qa_url, wait_until="domcontentloaded", timeout=30000)
            _settle(page)
        except Exception as e:
            print(f"Replay failed - could not open {qa_url}:\n{e}")
            result["message"] = f"could not open QA URL: {e}"
            browser.close()
            _write_result(result, output_json_path)
            return result

        print("REPLAY SOURCE:", SOURCE_NAME)
        print("ACTION COUNT:", len(STEPS))
        print("SOURCE TYPE:", SOURCE_TYPE)
        print()

        # page_id 0 is always the page we just opened above. Recorded
        # actions on any tab/page that opened DURING recording carry a
        # higher page_id (1, 2, ...), assigned in the order those pages
        # appeared - context.on("page") mirrors that same assignment here
        # so a click that (like it did when recording) pops open a new
        # tab gets that tab registered under the matching id automatically.
        # Actions without a page_id (recordings made before this existed)
        # default to 0 via step.get("page_id", 0) below, so single-page
        # recordings replay exactly as before.
        pages = {0: page}
        _next_replay_page_id = [1]

        def _on_replay_new_page(new_page):
            pid = _next_replay_page_id[0]
            _next_replay_page_id[0] += 1
            pages[pid] = new_page
            try:
                new_page.set_default_timeout(8000)
                new_page.on("dialog", _dismiss_dialog)
            except Exception:
                pass
            print(f"(new page/tab appeared during replay - assigned page_id={pid}, url={new_page.url})")

        page.context.on("page", _on_replay_new_page)

        print("Executing recorded actions...")
        print()

        total_steps = len(STEPS)
        prev_timestamp = None
        # these are the action types that can plausibly trigger real
        # navigation (a link, a submit button, Enter in a form) - after
        # one of these succeeds, give any resulting page load a moment to
        # settle before the screenshot/next action, so both see the
        # RESULTING page rather than a mid-navigation snapshot. A click
        # that didn't navigate is already idle, so this resolves almost
        # immediately and doesn't add a meaningful delay to those.
        NAV_CAUSING_ACTIONS = ("click", "dblclick", "right_click", "submit", "press")

        # tracks whether any step since the last successful "navigate" has
        # failed - a navigate is often recorded because an earlier action
        # (form submit, payment step, etc.) succeeded and the app itself
        # redirected there. If what came before it this run actually
        # failed, blindly loading that same URL can LOOK like progress
        # while replaying to a destination that never really earned it.
        failed_since_last_navigate = False

        for i, step in enumerate(STEPS, start=1):
            action_type = step.get("action_type")
            cur_timestamp = step.get("timestamp")
            nav_warning = None
            if action_type == "navigate" and failed_since_last_navigate:
                nav_warning = (
                    "prior step(s) since the last successful navigation "
                    "failed - this navigate may be replaying to a URL that "
                    "depended on their success, so the destination may not "
                    "reflect a real transaction"
                )

            # Everything for this one step lives inside this try/except.
            # Every individual action type already catches its OWN
            # execution errors below (a normal "element not found" keeps
            # the loop going, as before) - this outer layer is a safety
            # net for anything else that could throw (the page dying
            # mid-replay, the pacing wait itself failing, etc.) so THAT
            # can never silently truncate the remaining actions without a
            # trace. If it fires, this step is recorded as failed and the
            # loop stops - the backfill after the loop then explicitly
            # marks every action that never got a chance to run, so the
            # result can never look like a complete run when it wasn't.
            try:
                _print_step_header(i, total_steps, step)
                print("STATUS: STARTED")

                # recorded delay_before_ms is history/diagnostic data
                # about how the user actually paced the recording - it is
                # deliberately NOT replayed as a sleep. Replay waits only
                # for real technical conditions (element/page readiness,
                # popups, navigation) via the Playwright waits already
                # used throughout this loop (_settle, scroll_into_view,
                # the popup wait in _resolve_target_page, etc.), so replay
                # stays materially faster than the original recording.
                prev_timestamp = cur_timestamp

                # every recorded action names which page/tab it belongs to
                # (page_id 0 = the original page; higher ids = tabs that
                # opened during recording) - resolve that page BEFORE
                # acting, since a page that opened mid-recording may not
                # exist yet on this run at exactly the same moment. The
                # fallback URL comes from THIS step's own recorded
                # page_url (not just steps flagged new_tab) so that once
                # the first action for a page_id is recovered, it's
                # registered in `pages` and every later action on that
                # same page_id hits the instant fast-path above instead
                # of repeating the wait.
                target_page_id = step.get("page_id", 0)
                if target_page_id not in pages:
                    fallback_url = to_qa_url(step.get("page_url"), qa_url) if step.get("page_url") else None
                    resolved_page, resolve_err = _resolve_target_page(pages, target_page_id, page, fallback_url=fallback_url)
                else:
                    resolved_page, resolve_err = pages[target_page_id], None

                print("Executing...")

                if resolved_page is None:
                    strategy, found, ok, err = None, False, False, (
                        f"page_id={target_page_id} could not be resolved - {resolve_err}"
                    )
                    step_start = time.monotonic()
                    try:
                        url_before = page.url
                    except Exception:
                        url_before = None
                else:
                    page = resolved_page

                    try:
                        url_before = page.url
                    except Exception:
                        url_before = None

                    step_start = time.monotonic()

                    if action_type == "navigate":
                        target = to_qa_url(step.get("page_url"), qa_url)

                        def _same_route(url, _target=target):
                            try:
                                cu, tu = urlsplit(url), urlsplit(_target)
                            except Exception:
                                return url == _target
                            return (
                                cu.scheme, cu.netloc, cu.path.rstrip("/") or "/", cu.query
                            ) == (
                                tu.scheme, tu.netloc, tu.path.rstrip("/") or "/", tu.query
                            )

                        try:
                            if _same_route(page.url):
                                # a preceding action (already executed above,
                                # this step's own click/submit/etc.) already
                                # triggered the app's own client-side
                                # transition to this exact URL - this
                                # recorded navigate is just confirming where
                                # that landed. Nothing to do: forcing a
                                # reload here would discard whatever
                                # client-side state (cart, form progress,
                                # session data) the app built up getting
                                # here for real.
                                _settle(page)
                                strategy, found, ok, err = None, True, True, None
                            else:
                                # give the app a short window to arrive here
                                # on its own first - covers the common SPA
                                # case where the PRECEDING step is what
                                # actually triggers a client-side route
                                # change, and this navigate only confirms
                                # the destination rather than something that
                                # should force a fresh document load
                                try:
                                    page.wait_for_url(_same_route, timeout=3500)
                                    _settle(page)
                                    strategy, found, ok, err = None, True, True, None
                                except Exception:
                                    # the natural client-side transition
                                    # never happened (most likely the
                                    # preceding action didn't actually
                                    # succeed/trigger it) - force the URL
                                    # directly as a recovery, but flag it
                                    # clearly: a hard-loaded page here may be
                                    # missing state a real transition would
                                    # have carried over
                                    page.goto(target, wait_until="domcontentloaded", timeout=30000)
                                    _settle(page)
                                    strategy, found, ok, err = None, True, True, None
                                    fallback_note = (
                                        "forced hard-navigation fallback - preceding action "
                                        "may not have triggered the app's own client-side "
                                        "transition, destination page may be missing state "
                                        "it would normally have"
                                    )
                                    nav_warning = f"{nav_warning}; {fallback_note}" if nav_warning else fallback_note
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "scroll":
                        # a scroll recorded against a nested scrollable
                        # container (not the window) carries a css_path
                        # locator for it - resolved here via the same
                        # _find_by_css tier resolve_and_act itself uses,
                        # so that container gets scrolled directly instead
                        # of the page as a whole. No locator (the common
                        # case, or an older recording predating this
                        # field) means plain window scrolling, unchanged.
                        # scroll_y_after (absolute recorded position) is
                        # passed through when present so the final
                        # position gets corrected for any drift.
                        try:
                            scroll_lp = step.get("locator_profile") or {}
                            scroll_el = _find_by_css(page, scroll_lp) if scroll_lp.get("css_path") else None
                            _replay_scroll(
                                page,
                                step.get("delta_x") or 0,
                                step.get("delta_y") or 0,
                                step.get("scroll_y_after"),
                                scroll_el,
                            )
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "tab_switch":
                        # the page-resolution step above already switched
                        # `page` to the recorded to_page_id (every step
                        # resolves its target page before acting, tab_switch
                        # is no different) - bring_to_front() just makes
                        # that switch visually real in a headed run too,
                        # matching what the user actually did
                        try:
                            page.bring_to_front()
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "tab_open":
                        # the page-resolution step above already found (a
                        # real popup, if one happened) or created (the
                        # fallback in _resolve_target_page) the runtime
                        # page for this recorded page_id - no separate
                        # goto here: the page is already at the right URL,
                        # and re-navigating an already-loaded new tab
                        # could re-trigger side effects the original
                        # tab-open never had. Just let it settle.
                        try:
                            _settle(page)
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "tab_close":
                        # closes the runtime page for the recorded page_id
                        # this step names (already resolved to `page`
                        # above) - later steps resolve their OWN page_id
                        # fresh via the same mechanism, so this doesn't
                        # need to do anything beyond the close itself
                        try:
                            if not page.is_closed():
                                page.close()
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    else:
                        try:
                            strategy, found, ok, err = _resolve_and_act_with_retry(page, step)
                        except Exception as e:
                            # one bad step shouldn't blank out the rest of the run
                            strategy, found, ok, err = None, False, False, str(e)
                            logger.error("step %d raised unexpectedly: %s", i, e)

                        if ok and action_type in NAV_CAUSING_ACTIONS:
                            _settle(page)

                duration = time.monotonic() - step_start

                if action_type == "navigate":
                    failed_since_last_navigate = not ok
                elif not ok:
                    failed_since_last_navigate = True

                try:
                    url_after = page.url
                except Exception:
                    url_after = None

                # zero-padded index + action type + short readable slug of
                # the target (+ _FAILED when it didn't succeed) -
                # traceable to exactly which step produced it, unlike a
                # bare "step3.png"
                suffix = "" if ok else "_FAILED"
                shot_path = shot_dir / f"{_screenshot_name(i, step)}{suffix}.png"
                try:
                    page.screenshot(path=str(shot_path))
                    shot_str = str(shot_path)
                except Exception:
                    shot_str = None

                logger.debug("step %d (%s): strategy=%s found=%s success=%s", i, action_type, strategy, found, ok)
                if ok:
                    print("STATUS: SUCCESS")
                    print(f"Done ({duration:.2f}s).")
                else:
                    # the plain print() is the real user-facing failure
                    # message (see AUTOFLOW_DEBUG for the fuller
                    # strategy/step trace)
                    logger.debug("step %d (%s) failed: %s", i, action_type, err)
                    print("STATUS: FAILED")
                    print(f"Reason: {err}")
                    print(f"Current URL: {url_after or url_before}")
                    if action_type not in ("navigate", "scroll"):
                        print("Locator attempts:")
                        for line in _locator_attempts(step):
                            print(f"  {line}")
                    if shot_str:
                        print(f"Screenshot: {shot_str}")
                if nav_warning:
                    print(f"WARNING: {nav_warning}")
                print()

                result["steps"].append({
                    "index": i,
                    "action_type": action_type,
                    "strategy_used": strategy,
                    "element_found": found,
                    "success": ok,
                    "error": err,
                    "warning": nav_warning,
                    "screenshot": shot_str,
                    "url_before": url_before,
                    "url_after": url_after,
                    "duration": round(duration, 3),
                })

            except Exception as fatal_e:
                logger.error("step %d crashed the replay loop: %s", i, fatal_e)
                print("STATUS: FAILED")
                print(f"Reason: replay could not continue - {fatal_e}")
                print()
                result["steps"].append({
                    "index": i,
                    "action_type": action_type,
                    "strategy_used": None,
                    "element_found": False,
                    "success": False,
                    "error": f"replay could not continue: {fatal_e}",
                    "warning": None,
                    "screenshot": None,
                    "url_before": None,
                    "url_after": None,
                    "duration": 0,
                })
                break

        # guarantee exactly one result entry per recorded action - if the
        # loop above broke early (the page/browser died), every action
        # after that point is explicitly recorded as NOT EXECUTED rather
        # than just missing, so a truncated run can never be mistaken for
        # a complete one just because everything THAT DID RUN succeeded
        executed_indexes = {s["index"] for s in result["steps"]}
        for i, step in enumerate(STEPS, start=1):
            if i not in executed_indexes:
                result["steps"].append({
                    "index": i,
                    "action_type": step.get("action_type"),
                    "strategy_used": None,
                    "element_found": False,
                    "success": False,
                    "error": "not executed - replay stopped before reaching this action",
                    "warning": None,
                    "screenshot": None,
                    "url_before": None,
                    "url_after": None,
                    "duration": 0,
                })
        result["steps"].sort(key=lambda s: s["index"])

        # the loop's own `page` variable can be pointing at an already-
        # closed Page here (e.g. the last recorded action was a tab_close
        # that closed exactly that page) - resolve a genuinely open page
        # from the runtime registry before touching anything else, rather
        # than assume `page` is still usable
        final_page = _get_valid_open_page(pages, preferred=page)

        if final_page is not None:
            try:
                result["final_url"] = final_page.url
                result["final_text"] = final_page.inner_text("body")
            except Exception as e:
                logger.warning("couldn't read final page state: %s", e)

            final_shot = shot_dir / "final.png"
            try:
                final_page.screenshot(path=str(final_shot), full_page=True)
                result["final_screenshot"] = str(final_shot)
            except Exception as e:
                logger.warning("couldn't capture final screenshot: %s", e)
        else:
            logger.info("no open page remained at replay end - skipping final URL/screenshot capture")

        page = final_page

        if product_name and product_name.strip() and page is not None:
            pname = product_name.strip()
            print("PRODUCT SEARCH VALIDATION")
            print("")
            print("Requested Product:")
            print(pname)
            print("")
            try:
                pv = _validate_product(page, pname, shot_dir)
            except Exception as e:
                logger.error("product validation crashed: %s", e)
                try:
                    cur_url = page.url
                except Exception:
                    cur_url = None
                pv = {
                    "status": "FAIL", "product": pname, "found": False,
                    "match_type": None, "position": None, "page": 1,
                    "title": None, "url": None, "screenshot": None,
                    "reason": f"product validation crashed: {e}",
                    "checked_count": 0, "search_url": cur_url,
                }
            result["product_validation"] = pv
            if pv.get("found"):
                print("PASS")
                print("Product is found")
                print(f"Position: Result {pv.get('position')}")
            else:
                print("FAIL")
                print("Product is not found")
                print("Checked complete available results")
        elif product_name and product_name.strip():
            result["product_validation"] = {
                "status": "FAIL", "product": product_name.strip(), "found": False,
                "match_type": None, "position": None, "page": None,
                "title": None, "url": None, "screenshot": None,
                "reason": "no open page remained at replay end - could not validate",
                "checked_count": 0, "search_url": None,
            }

        # status/message/report are all finalized and written BEFORE the
        # close delay and browser.close() below - nothing about the
        # result depends on the browser still being open past this point.
        # result["steps"] is guaranteed (by the backfill above) to have
        # exactly one entry per recorded action, so these counts can never
        # under-report a run that was cut short.
        NOT_EXECUTED_MSG = "not executed - replay stopped before reaching this action"
        recorded_count = total_steps
        not_executed_steps = [s for s in result["steps"] if s["error"] == NOT_EXECUTED_MSG]
        attempted_count = recorded_count - len(not_executed_steps)
        successful_actions = sum(1 for s in result["steps"] if s["success"])
        failed_actions = attempted_count - successful_actions
        not_executed_count = len(not_executed_steps)

        # PASS requires every single recorded action to have both been
        # attempted AND succeeded - a truncated run (anything left
        # NOT EXECUTED) or any individual failure both force FAIL
        steps_ok = not_executed_count == 0 and failed_actions == 0
        result["status"] = "PASS" if steps_ok else "FAIL"
        if not_executed_count:
            result["message"] = f"replay stopped early - {not_executed_count} action(s) never executed"
        elif failed_actions:
            result["message"] = "one or more steps failed"
        else:
            result["message"] = "all steps resolved"

        _write_result(result, output_json_path)

        print("=" * 50)
        print("REPLAY COMPLETED")
        print("=" * 50)
        print()
        print(f"Recorded: {recorded_count}")
        print(f"JSON: {recorded_count}")
        print(f"Generated: {recorded_count}")
        print(f"Executed: {attempted_count}")
        print(f"Successful: {successful_actions}")
        print(f"Failed: {failed_actions}")
        if not_executed_count:
            first_missed = not_executed_steps[0]["index"]
            last_missed = not_executed_steps[-1]["index"]
            print(f"Not executed: {first_missed}-{last_missed} ({not_executed_count} action(s))")
        else:
            print("Not executed: 0")
        print()
        print(f"RESULT: {result['status']}")
        print()
        print("Final URL:")
        print(result.get("final_url"))
        print()
        print("Screenshots:")
        print(str(shot_dir))
        print()
        print("Generated Script:")
        print(str(Path(__file__).resolve()))
        print()
        # everything that needs the page/browser (final_url, final
        # screenshot, product validation, report) is already captured and
        # written above - this is purely a "let it sit on screen for a
        # moment" pause before the ONE close() call below, not a
        # per-action delay. `page` may already be closed at this point (a
        # recorded tab_close, possibly the very last action, can close
        # exactly the page this variable was last pointing at) - calling
        # wait_for_timeout (or anything else) on a closed Page raises
        # TargetClosedError, so re-check for a genuinely open page rather
        # than trust `page`/`final_page` are still valid this much later.
        close_delay_page = _get_valid_open_page(pages, preferred=page)

        if close_delay_page is not None:
            print(f"Browser will remain open for {DEFAULT_CLOSE_DELAY} seconds...")
            try:
                close_delay_page.wait_for_timeout(DEFAULT_CLOSE_DELAY * 1000)
            except Exception as e:
                logger.info("close-delay wait skipped - page became unavailable: %s", e)
        else:
            print("No open page remained - skipping the close delay.")

        try:
            if browser.is_connected():
                browser.close()
                print("Browser closed successfully.")
            else:
                print("Browser was already closed.")
        except Exception as e:
            logger.info("browser.close() raised (already closing/closed): %s", e)
            print("Browser was already closed.")
        print("=" * 50)

    return result


def _write_result(result, output_json_path):
    if output_json_path:
        Path(output_json_path).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else PROD_URL
    if target and not target.startswith(("http://", "https://")):
        target = "https://" + target
    out_json = sys.argv[2] if len(sys.argv) > 2 else None
    out_shots = sys.argv[3] if len(sys.argv) > 3 else None
    # headed (visible) by default when you run this file yourself, so you
    # can actually watch the replay - pass "1" as a 4th argument to run it
    # headless instead (that's what the dashboard's automated QA runs use)
    headless_arg = sys.argv[4] if len(sys.argv) > 4 else "0"
    product_arg = sys.argv[5] if len(sys.argv) > 5 else ""
    run(target, out_json, out_shots, headless=(headless_arg == "1"), product_name=product_arg)
