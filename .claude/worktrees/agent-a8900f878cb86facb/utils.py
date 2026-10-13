"""Small helpers shared across app.py, executor, and search."""
import logging

logger = logging.getLogger(__name__)


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return raw
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw


def attach_dialog_handler(page):
    """Auto-dismiss cookie banners/alerts/confirms so they don't hang a run."""
    def _on_dialog(dialog):
        logger.info("dialog appeared (%s): %s - dismissing", dialog.type, dialog.message)
        try:
            dialog.dismiss()
        except Exception as e:
            logger.warning("couldn't dismiss dialog: %s", e)

    page.on("dialog", _on_dialog)
