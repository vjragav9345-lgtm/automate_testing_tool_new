"""Utility helpers for URL normalization and Playwright dialog handling."""

from urllib.parse import urlsplit, urlunsplit


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
