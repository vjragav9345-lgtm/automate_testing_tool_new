"""Item 2 (crash recovery): a recording session that ends abnormally
(process killed, crash, power loss) leaves behind its append-only JSONL
sidecar (recorder/record_session.py's Recorder._flush_draft) with every
action it ever captured, even ones the periodic full-JSON consolidation
never got to. storage.repository.recover_orphaned_drafts() must rebuild a
complete, saved recording from that sidecar, and only remove the sidecar
once that save has actually succeeded.

Simulates a crash directly (writes a .draft.jsonl by hand, exactly the
shape Recorder._flush_draft produces, with NO corresponding .json at all -
the worst case, a crash before the first periodic consolidation ever
ran) rather than actually killing a process, since the thing under test is
the recovery logic itself, not process-management.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from storage import repository  # noqa: E402
from storage.repository import RECORDINGS_DIR  # noqa: E402


def main():
    name = "flowfix10_crash_test_session"
    jsonl_path = RECORDINGS_DIR / f"{name}.draft.jsonl"
    json_path = RECORDINGS_DIR / f"{name}.json"

    # make sure we start clean
    jsonl_path.unlink(missing_ok=True)
    json_path.unlink(missing_ok=True)

    actions = [
        {"action_type": "navigate", "value": None, "locator_profile": None, "page_url": "https://example.test/", "timestamp": "2026-01-01T00:00:00.000Z", "page_id": 0},
        {"action_type": "click", "value": None, "locator_profile": {"id": "#a"}, "page_url": "https://example.test/", "timestamp": "2026-01-01T00:00:01.000Z", "page_id": 0},
        {"action_type": "click", "value": None, "locator_profile": {"id": "#b"}, "page_url": "https://example.test/", "timestamp": "2026-01-01T00:00:02.000Z", "page_id": 0},
    ]
    with open(jsonl_path, "a", encoding="utf-8") as f:
        for a in actions:
            f.write(json.dumps(a) + "\n")
        # simulate a crash mid-write on a 4th action - a truncated final line
        f.write('{"action_type": "click", "value": null, "locator_pr')

    assert not json_path.exists(), "test setup: no consolidated json should exist yet (worst case)"

    recovered = repository.recover_orphaned_drafts()
    print("recovered paths:", recovered)

    assert not jsonl_path.exists(), "sidecar must be removed after a successful recovery save"
    assert json_path.exists(), "a full recording must now exist"

    data = json.loads(json_path.read_text(encoding="utf-8"))
    print("recovered actions:", len(data["actions"]))
    print("recovered flag:", data.get("recovered"))
    print("recovered_note:", data.get("recovered_note"))

    assert len(data["actions"]) == 3, "the truncated 4th line must be dropped, not crash recovery"
    assert data.get("recovered") is True
    assert data.get("name") == name
    assert data.get("start_url") == "https://example.test/"

    # idempotency: calling again with no sidecar left must be a no-op
    recovered2 = repository.recover_orphaned_drafts()
    assert recovered2 == [], f"expected no further recovery, got {recovered2}"

    # cleanup
    json_path.unlink(missing_ok=True)

    print("\nPASS: crash recovery rebuilds the full recording from the JSONL sidecar, "
          "drops only the truncated final line, and cleans up only after a successful save")


if __name__ == "__main__":
    main()
