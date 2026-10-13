"""
Auto-generated from recording: session_20260819_123848
Generated at: 2026-08-19T12:38:48.881604
Original recorded (production) URL: https://www.nykaa.com/skin/masks/c/8399?search_redirection=True

Resolution order per step: data-testid -> data-test -> data-cy -> id -> name
-> aria-label -> placeholder -> role -> css_path -> xpath -> text+tag ->
bounding box click. Dropdowns use page.select_option(), form submits use
form.requestSubmit(), meaningful keypresses (Enter/Tab/Escape) use el.press(),
double/right clicks use el.dblclick()/el.click(button="right"), scrolling
uses page.mouse.wheel().

Prints simple progress/result messages only - no internal strategy/step
logs. Set AUTOFLOW_DEBUG=1 to also see which locator strategy was used for
every step.

Run directly with: python session_20260819_123848_script.py [qa_url] [output_json_path] [screenshot_dir] [headless] [product_name]
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
from urllib.parse import urlsplit, urlunsplit

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

STEPS = [   {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': -25,
        'delta_y': 3467,
        'scroll_y_before': 668,
        'scroll_y_after': 3442.39990234375,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:07:54.907Z',
        'delay_before_ms': 0,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': 0,
        'delta_y': 82,
        'scroll_y_before': 3442.39990234375,
        'scroll_y_after': 3508,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:07:55.530Z',
        'delay_before_ms': 623,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': 0,
        'delta_y': -725,
        'scroll_y_before': 3508,
        'scroll_y_after': 2928,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:07:56.625Z',
        'delay_before_ms': 1095,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': 0,
        'delta_y': -874,
        'scroll_y_before': 2927.199951171875,
        'scroll_y_after': 2228.800048828125,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:08:02.069Z',
        'delay_before_ms': 5444,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Sanfe Instant Glow Rose Facial Mask, 100% Fruit '
                                                  'Extracts, Ko...\n'
                                                  'Price ₹49.\n'
                                                  '₹49\n'
                                                  '(',
                               'placeholder': None,
                               'title': None,
                               'href': '/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
                               'css_path': 'div#product-list-wrap > div:nth-of-type(13) > div > '
                                           'div > a',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[4]/div[2]/div[1]/div[13]/div[1]/div[1]/a[1]',
                               'text': 'Sanfe Instant Glow Rose Facial Mask, 100% Fruit Extracts, '
                                       'Ko...\n'
                                       'Price ₹49.\n'
                                       '₹49\n'
                                       '(',
                               'element_text': 'Sanfe Instant Glow Rose Facial Mask, 100% Fruit '
                                               'Extracts, Ko...\n'
                                               'Price ₹49.\n'
                                               '₹49\n'
                                               '(',
                               'tag': 'a',
                               'attributes': {   'href': '/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13'}},
        'bounding_box': {   'x': 370.07501220703125,
                            'y': 319,
                            'width': 219.6750030517578,
                            'height': 337},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:02.999Z',
        'delay_before_ms': 930,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:06.251Z',
        'delay_before_ms': 3252,
        'new_tab': True,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': 0,
        'delta_y': 315,
        'scroll_y_before': 291.20001220703125,
        'scroll_y_after': 534.4000244140625,
        'viewport_height': 720,
        'document_height': 2578,
        'timestamp': '2026-08-19T07:08:06.811Z',
        'delay_before_ms': 560,
        'new_tab': None,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': 'Add to bag undefined',
                               'accessible_name': 'Add to bag undefined',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#app > div > div:nth-of-type(2) > div > '
                                           'div:nth-of-type(2) > div > div > div:nth-of-type(6) > '
                                           'div > div > button',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[6]/div[1]/div[1]/button[1]',
                               'text': 'Add to Bag',
                               'element_text': 'Add to Bag',
                               'tag': 'button',
                               'attributes': {   'type': 'button',
                                                 'aria-label': 'Add to bag undefined'}},
        'bounding_box': {'x': 547.0625, 'y': 481.4375, 'width': 222, 'height': 48},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:08.241Z',
        'delay_before_ms': 1430,
        'new_tab': None,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#header-bag-icon',
                               'name': None,
                               'role': None,
                               'aria_label': 'Shopping Bag, 1 item',
                               'accessible_name': 'Shopping Bag, 1 item',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'button#header-bag-icon',
                               'xpath': "//*[@id='header-bag-icon']",
                               'text': '1',
                               'element_text': '1',
                               'tag': 'button',
                               'attributes': {   'type': 'button',
                                                 'aria-label': 'Shopping Bag, 1 item'}},
        'bounding_box': {   'x': 1174.5250244140625,
                            'y': 61.35000228881836,
                            'width': 24,
                            'height': 27.30000114440918},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:12.045Z',
        'delay_before_ms': 3804,
        'new_tab': None,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': 'Delete Sanfe Instant Glow Rose Facial Mask, 100% '
                                             'Fruit Extracts, Korean Mask',
                               'accessible_name': 'Delete Sanfe Instant Glow Rose Facial Mask, '
                                                  '100% Fruit Extracts, Korean Mask',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'li#16334484 > div > button',
                               'xpath': '/html[1]/body[1]/div[2]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[1]/div[1]/button[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'button',
                               'attributes': {   'aria-label': 'Delete Sanfe Instant Glow Rose '
                                                               'Facial Mask, 100% Fruit Extracts, '
                                                               'Korean Mask'}},
        'bounding_box': {   'x': 1226.4000244140625,
                            'y': 162.8000030517578,
                            'width': 30,
                            'height': 30},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:21.053Z',
        'delay_before_ms': 9008,
        'new_tab': None,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Yes',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'li#16334484 > div > div > div:nth-of-type(2) > div > '
                                           'button',
                               'xpath': '/html[1]/body[1]/div[2]/div[1]/div[1]/div[1]/div[3]/ul[1]/li[1]/div[1]/div[1]/div[2]/div[1]/button[1]',
                               'text': 'Yes',
                               'element_text': 'Yes',
                               'tag': 'button',
                               'attributes': {}},
        'bounding_box': {   'x': 931.6000366210938,
                            'y': 220.8000030517578,
                            'width': 148.40000915527344,
                            'height': 41.60000228881836},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:23.254Z',
        'delay_before_ms': 2201,
        'new_tab': None,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': 'button',
                               'aria_label': 'Back Button',
                               'accessible_name': 'Back Button',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#portal-root > div > div > div > div > div > div > '
                                           'div',
                               'xpath': '/html[1]/body[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]',
                               'text': '',
                               'element_text': '',
                               'tag': 'div',
                               'attributes': {'role': 'button', 'aria-label': 'Back Button'}},
        'bounding_box': {'x': 912.7999877929688, 'y': 16.80000114440918, 'width': 44, 'height': 24},
        'page_url': 'https://www.nykaa.com/sanfe-instant-glow-rose-facial-mask/p/16334484?productId=16334484&pps=13',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:25.966Z',
        'delay_before_ms': 2712,
        'new_tab': None,
        'page_id': 1,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': 0,
        'delta_y': -3371,
        'scroll_y_before': 2227.199951171875,
        'scroll_y_after': 0,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:08:32.680Z',
        'delay_before_ms': 6714,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': 'Sign in',
                               'accessible_name': 'Sign in',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#header_id > div:nth-of-type(2) > div > '
                                           'div:nth-of-type(2) > div > div > button',
                               'xpath': '/html[1]/body[1]/div[1]/header[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/button[1]',
                               'text': 'Sign in',
                               'element_text': 'Sign in',
                               'tag': 'button',
                               'attributes': {'aria-label': 'Sign in'}},
        'bounding_box': {'x': 1049.5250244140625, 'y': 55, 'width': 78.4000015258789, 'height': 40},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:34.887Z',
        'delay_before_ms': 2207,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': 0,
        'delta_y': 1222,
        'scroll_y_before': 6.400000095367432,
        'scroll_y_after': 978.4000244140625,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:08:39.879Z',
        'delay_before_ms': 4992,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': None,
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'Concern',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'div#filters-strip > div > div > div:nth-of-type(4) > '
                                           'div',
                               'xpath': '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/div[4]/div[1]/div[1]/div[2]/div[1]/div[1]/div[4]/div[1]',
                               'text': 'Concern',
                               'element_text': 'Concern',
                               'tag': 'div',
                               'attributes': {}},
        'bounding_box': {   'x': 54.400001525878906,
                            'y': 119.20000457763672,
                            'width': 253,
                            'height': 52},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:40.548Z',
        'delay_before_ms': 669,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'click',
        'value': None,
        'locator_profile': {   'id': '#checkbox_Blackheads & Whiteheads_181575',
                               'name': None,
                               'role': None,
                               'aria_label': None,
                               'accessible_name': 'on',
                               'placeholder': None,
                               'title': None,
                               'href': None,
                               'css_path': 'input#checkbox_Blackheads & Whiteheads_181575',
                               'xpath': "//*[@id='checkbox_Blackheads & Whiteheads_181575']",
                               'text': 'on',
                               'element_text': 'on',
                               'tag': 'input',
                               'attributes': {'type': 'checkbox'}},
        'bounding_box': {   'x': 54.400001525878906,
                            'y': 142.6999969482422,
                            'width': 13,
                            'height': 13},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?search_redirection=True',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:42.276Z',
        'delay_before_ms': 1728,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'scroll',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?page_no=1&sort=popularity&search_redirection=True&concern_filter=181575',
        'delta_x': 0,
        'delta_y': 2290,
        'scroll_y_before': 366.3999938964844,
        'scroll_y_after': 2197.60009765625,
        'viewport_height': 720,
        'document_height': 7705,
        'timestamp': '2026-08-19T07:08:46.846Z',
        'delay_before_ms': 4570,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None},
    {   'action_type': 'navigate',
        'value': None,
        'locator_profile': {},
        'bounding_box': {},
        'page_url': 'https://www.nykaa.com/skin/masks/c/8399?page_no=1&sort=popularity&search_redirection=True&concern_filter=181575',
        'delta_x': None,
        'delta_y': None,
        'scroll_y_before': None,
        'scroll_y_after': None,
        'viewport_height': None,
        'document_height': None,
        'timestamp': '2026-08-19T07:08:47.626Z',
        'delay_before_ms': 780,
        'new_tab': None,
        'page_id': 0,
        'from_page_id': None,
        'to_page_id': None,
        'from_url': None,
        'to_url': None}]
PROD_URL = "https://www.nykaa.com/skin/masks/c/8399?search_redirection=True"
SOURCE_NAME = "session_20260819_123848"
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


def resolve_and_act(page, step):
    """Try each locator strategy in priority order, then perform the step's
    action. Strongest/most stable signals first (test-automation attributes,
    id, other stable attributes), generic/fragile ones last.

    Returns (strategy_used, element_found, success, error_message).
    element_found is True for any real locator hit (everything except the
    bounding-box fallback, which still lets the step succeed but does NOT
    count as "found" for UI element validation purposes.
    """
    lp = step.get("locator_profile") or {}
    attrs = lp.get("attributes") or {}
    action_type = step.get("action_type")
    value = step.get("value")
    el = None
    strategy = None

    # an action type this executor has no handler for must never be
    # silently treated as a no-op success just because a locator happened
    # to resolve - fail it outright, clearly labeled, before spending any
    # time searching for an element to act on
    SUPPORTED_ACTIONS = ("click", "dblclick", "right_click", "fill", "select", "submit", "press")
    if action_type not in SUPPORTED_ACTIONS:
        return None, False, False, f"UNSUPPORTED action_type: {action_type!r}"

    # 1-3: test-automation attributes - purpose-built to be stable locators
    for attr in ("data-testid", "data-test", "data-cy"):
        if el is None:
            el = _by_attr(page, attr, attrs.get(attr))
            if el is not None:
                strategy = attr

    # 4: unique id
    if el is None and lp.get("id"):
        try:
            c = page.locator(lp["id"])
            if c.count() > 0:
                el, strategy = c.first, "id"
        except Exception:
            pass

    # 5-8: other attributes that are usually stable and human-meaningful.
    # aria-label/title are tried both as raw attributes (5-6, matches any
    # element) and, for aria-label, the dedicated locator_profile.aria_label
    # field is equivalent - attrs already carries it when present.
    for attr in ("name", "aria-label", "placeholder", "title"):
        if el is None:
            el = _by_attr(page, attr, attrs.get(attr))
            if el is not None:
                strategy = attr

    # 9: accessibility role + accessible name - accessible_name (computed
    # the same way a screen reader would: aria-label, aria-labelledby, alt,
    # placeholder, then visible text) is a better discriminator than raw
    # visible text alone, but falls back to it for older recordings that
    # predate this field
    if el is None and (attrs.get("role") or lp.get("role")):
        try:
            role = attrs.get("role") or lp.get("role")
            name = lp.get("accessible_name") or lp.get("text") or None
            c = page.get_by_role(role, name=name)
            if c.count() > 0:
                el, strategy = c.first, "role"
        except Exception:
            pass

    # 10: stable href - links are common navigation targets and a full
    # href is normally far more stable across a dynamic page's re-renders
    # than a position-dependent CSS path ever is
    if el is None and lp.get("href"):
        try:
            safe = lp["href"].replace('"', '\"')
            c = page.locator(f'a[href="{safe}"]')
            if c.count() > 0:
                el, strategy = c.first, "href"
        except Exception:
            pass

    # 11: visible text + tag - promoted above css_path/xpath because a
    # positional selector (nth-of-type chains especially) silently points
    # at the wrong element the moment a dynamic page's layout/ordering
    # shifts even slightly, while matching on an element's own stable
    # visible text does not
    if el is None and lp.get("text") and lp.get("tag"):
        try:
            c = page.locator(lp["tag"], has_text=lp["text"])
            if c.count() > 0:
                el, strategy = c.first, "text+tag"
        except Exception:
            pass

    # 11b: text only, no tag - a click-type action that has no recorded/
    # edited locator_profile at all (e.g. manually added in the Recording
    # Editor, or edited without touching Locator) still has its Value,
    # which for a click is normally the visible text of the link/button to
    # click. Value is never treated as the ONLY locator source when a real
    # locator_profile.text exists (that's tried first, above) - this only
    # kicks in when there's nothing else to go on.
    if (
        el is None
        and not lp.get("text")
        and value
        and action_type in ("click", "dblclick", "right_click")
    ):
        try:
            c = page.get_by_text(value, exact=True)
            if c.count() == 0:
                c = page.get_by_text(value)
            if c.count() > 0:
                el, strategy = c.first, "text+tag"
        except Exception:
            pass

    # 12: css path / xpath - kept as a fallback rather than removed: still
    # useful when an element genuinely has no id/role/href/stable text
    # (a bare styled div/span acting as a custom control), just no longer
    # preferred over the more resilient signals above
    if el is None and lp.get("css_path"):
        try:
            c = page.locator(lp["css_path"])
            if c.count() > 0:
                el, strategy = c.first, "css_path"
        except Exception:
            pass

    if el is None and lp.get("xpath"):
        try:
            c = page.locator("xpath=" + lp["xpath"])
            if c.count() > 0:
                el, strategy = c.first, "xpath"
        except Exception:
            pass

    element_found = el is not None
    last_err = None

    if el is not None:
        try:
            el.scroll_into_view_if_needed(timeout=5000)
            if action_type == "click":
                el.click(timeout=5000)
            elif action_type == "dblclick":
                el.dblclick(timeout=5000)
            elif action_type == "right_click":
                el.click(timeout=5000, button="right")
            elif action_type == "fill" and value is not None:
                el.fill(value, timeout=5000)
            elif action_type == "select" and value is not None:
                el.select_option(value, timeout=5000)
            elif action_type == "submit":
                el.evaluate("f => f.requestSubmit ? f.requestSubmit() : f.submit()")
            elif action_type == "press" and value:
                el.press(value, timeout=5000)
            return strategy, element_found, True, None
        except Exception as e:
            # a recoverable hiccup, not a final failure yet - the bounding
            # box fallback below still gets a chance, and Playwright's own
            # exception text includes a full multi-line retry trace that's
            # only useful for debugging, not for a "did my replay work" run
            logger.debug("resolved via %s but action failed: %s", strategy, e)
            last_err = str(e)
    else:
        last_err = "none of the locator strategies (data-testid/data-test/data-cy/id/name/aria-label/placeholder/role/css_path/xpath/text+tag) matched an element"

    # bounding box is a last resort for click-type actions only - selects/
    # submits/keypresses need a real element to act on, a blind coordinate
    # click would just do the wrong thing
    box = step.get("bounding_box")
    if action_type in ("click", "dblclick", "right_click") and box and box.get("width") and box.get("height"):
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

    return strategy, element_found, False, last_err


def _dismiss_dialog(dialog):
    logger.debug("dialog appeared (%s): %s - dismissing", dialog.type, dialog.message)
    dialog.dismiss()


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
        return pages[target_page_id], None

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if target_page_id in pages:
            return pages[target_page_id], None
        anchor_page.wait_for_timeout(100)

    if not fallback_url:
        return None, (
            f"waited {wait_seconds}s for page_id={target_page_id} to appear as a new "
            f"tab/page (context 'page' event) but it never did, and this step has no "
            f"recorded URL to fall back to opening it directly"
        )

    try:
        new_page = anchor_page.context.new_page()
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


def _replay_scroll(page, dx, dy):
    """Replay a recorded scroll gradually instead of one instant jump - a
    single page.mouse.wheel(dx, dy) call for a large accumulated delta
    would teleport the page instead of scrolling it the way the original
    action looked. Breaking it into smaller hops with brief pauses gets
    much closer to the real thing without needing to match its timing
    exactly.
    """
    total = max(abs(dx), abs(dy))
    steps = max(1, min(20, int(total / 120)))
    step_dx = dx / steps
    step_dy = dy / steps
    for _ in range(steps):
        page.mouse.wheel(step_dx, step_dy)
        page.wait_for_timeout(40)


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

        for i, step in enumerate(STEPS, start=1):
            action_type = step.get("action_type")
            cur_timestamp = step.get("timestamp")

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

                if i > 1:
                    delay = _step_delay(step, prev_timestamp, cur_timestamp)
                    if delay > 0:
                        print(f"(waiting {delay:.1f}s to match recorded pacing)")
                        page.wait_for_timeout(delay * 1000)

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
                        try:
                            page.goto(target, wait_until="domcontentloaded", timeout=30000)
                            _settle(page)
                            strategy, found, ok, err = None, True, True, None
                        except Exception as e:
                            strategy, found, ok, err = None, True, False, str(e)
                    elif action_type == "scroll":
                        # no element involved - just replay the same mouse
                        # wheel movement that was recorded, on the page as a
                        # whole
                        try:
                            _replay_scroll(page, step.get("delta_x") or 0, step.get("delta_y") or 0)
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
                    else:
                        try:
                            strategy, found, ok, err = resolve_and_act(page, step)
                        except Exception as e:
                            # one bad step shouldn't blank out the rest of the run
                            strategy, found, ok, err = None, False, False, str(e)
                            logger.error("step %d raised unexpectedly: %s", i, e)

                        if ok and action_type in NAV_CAUSING_ACTIONS:
                            _settle(page)

                duration = time.monotonic() - step_start

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
                print()

                result["steps"].append({
                    "index": i,
                    "action_type": action_type,
                    "strategy_used": strategy,
                    "element_found": found,
                    "success": ok,
                    "error": err,
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
                    "screenshot": None,
                    "url_before": None,
                    "url_after": None,
                    "duration": 0,
                })
        result["steps"].sort(key=lambda s: s["index"])

        try:
            result["final_url"] = page.url
            result["final_text"] = page.inner_text("body")
        except Exception as e:
            logger.warning("couldn't read final page state: %s", e)

        final_shot = shot_dir / "final.png"
        try:
            page.screenshot(path=str(final_shot), full_page=True)
            result["final_screenshot"] = str(final_shot)
        except Exception as e:
            logger.warning("couldn't capture final screenshot: %s", e)

        if product_name and product_name.strip():
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
        print(f"Browser will remain open for {DEFAULT_CLOSE_DELAY} seconds...")

        # everything that needs the page/browser (final_url, final
        # screenshot, product validation, report) is already captured and
        # written above - this is purely a "let it sit on screen for a
        # moment" pause before the ONE close() call below, not a
        # per-action delay
        page.wait_for_timeout(DEFAULT_CLOSE_DELAY * 1000)

        browser.close()
        print("Browser closed successfully.")
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
