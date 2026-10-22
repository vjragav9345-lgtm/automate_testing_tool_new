"""Utility helpers for URL normalization and Playwright dialog handling."""

import os
from urllib.parse import urlsplit, urlunsplit

# Render sets the RENDER environment variable automatically on its servers
ON_RENDER = os.environ.get("RENDER") is not None
_RENDER_BROWSER_ARGS = ("--no-sandbox", "--disable-dev-shm-usage")


def server_safe_launch_kwargs(**kwargs):
    """Playwright launch options, unchanged everywhere except on Render: there the browser is headless and the
    Render-required args are merged into any existing args (no duplicates, no other option touched)."""
    if not ON_RENDER:
        return kwargs
    kw = dict(kwargs)
    kw["headless"] = True
    args = list(kw.get("args") or [])
    for a in _RENDER_BROWSER_ARGS:
        if a not in args:
            args.append(a)
    kw["args"] = args
    return kw


def normalize_url(url: str) -> str:
    """Ensures a URL string has a valid http:// or https:// scheme."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def attach_dialog_handler(page):
    """Automatically dismisses native browser alert/confirm/prompt dialogs."""
    try:
        page.on("dialog", lambda dialog: dialog.dismiss())
    except Exception:
        pass
