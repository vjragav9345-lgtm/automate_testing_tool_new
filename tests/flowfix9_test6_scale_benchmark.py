"""FIX 5 (scale) - measures the actual per-step overhead and on-disk sizes
for a synthetic 250-action recording (generated synthetically, per the
task's own instruction - no live site needed for this measurement), before
vs after the incremental-JSONL-sidecar change to Recorder._flush_draft.

"Before" is reconstructed analytically from the OLD, unconditional
"rewrite the whole JSON (all actions so far) on every action" behavior
(the exact code this replaced - see the .bak_flowfix9 backup) using the
same synthetic action sizes, since re-instrumenting the removed code path
directly isn't meaningful once it's gone; the arithmetic is the same
either way (sum of a linearly-growing per-call write size).
"""
import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from recorder.record_session import Recorder  # noqa: E402

N_ACTIONS = 250


def make_synthetic_action(i):
    # sized to resemble a real recorded action with RC4 dom_context (see
    # action_capture.js's DOM_CONTEXT_MAX_BYTES=8192 cap) - this is what
    # makes the OLD full-rewrite-per-action behavior's cost actually
    # matter in practice, not just in theory
    return {
        "action_type": "click",
        "value": None,
        "locator_profile": {"id": f"#el{i}", "text": f"Button {i}", "css_path": f"div#el{i}", "attributes": {}},
        "act_target": {"id": f"#el{i}", "text": f"Button {i}"},
        "state_target": None,
        "dom_context": {
            "act_target_html_chain": [f"<button id='el{i}'>Button {i}</button>" * 20][:2000],
            "act_target_style": {"display": "block", "visibility": "visible", "opacity": "1"},
        },
        "bounding_box": {"x": 10, "y": 20 + i, "width": 100, "height": 30},
        "page_url": f"https://example.test/page?step={i}",
        "timestamp": f"2026-01-01T00:00:{i % 60:02d}.000Z",
        "page_id": 0,
    }


def main():
    # bypasses start() (which needs a real, attached Playwright page just
    # to record step 1's own navigate) and sets up exactly the same
    # draft/JSONL/consolidation state it would - _record()/_flush_draft()
    # themselves (the code under actual measurement here) are completely
    # unmodified real code, not stubs
    from datetime import datetime
    from storage.repository import RECORDINGS_DIR

    rec = Recorder(page=None)
    rec.actions = []
    rec.session_id = "flowfix9_benchmark"
    rec._draft_path = RECORDINGS_DIR / f"flowfix9_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    rec._draft_jsonl_path = rec._draft_path.with_suffix(".draft.jsonl")
    rec._draft_actions_since_consolidate = 0
    rec._draft_last_consolidate_at = time.monotonic()
    draft_path = rec._draft_path
    jsonl_path = rec._draft_jsonl_path

    BATCH = 25
    batch_times = []
    t_total_start = time.perf_counter()
    for i in range(N_ACTIONS):
        action = make_synthetic_action(i)
        if i % BATCH == 0:
            t_batch_start = time.perf_counter()
        rec._record(action)
        if i % BATCH == BATCH - 1:
            batch_times.append(time.perf_counter() - t_batch_start)
    t_total = time.perf_counter() - t_total_start

    rec._consolidate_draft()  # final flush, same as a real stop() triggers indirectly

    jsonl_size = jsonl_path.stat().st_size if jsonl_path.exists() else 0
    json_size = draft_path.stat().st_size if draft_path.exists() else 0

    first_batch_avg = batch_times[0] / BATCH
    last_batch_avg = batch_times[-1] / BATCH

    print(f"=== FIX 5 synthetic benchmark: {N_ACTIONS} actions ===")
    print(f"total time for all {N_ACTIONS} _record() calls: {t_total*1000:.1f}ms")
    print(f"avg per-action time, first batch (actions 0-{BATCH-1}):    {first_batch_avg*1000:.4f}ms")
    print(f"avg per-action time, last batch (actions {N_ACTIONS-BATCH}-{N_ACTIONS-1}): {last_batch_avg*1000:.4f}ms")
    print(f"  (NEW behavior: flat O(1) per action via JSONL append - "
          f"first/last batch should be close to each other)")
    print(f"final JSONL sidecar size: {jsonl_size:,} bytes")
    print(f"final consolidated JSON size: {json_size:,} bytes")

    # analytical reconstruction of the OLD per-action cost (full JSON
    # rewrite of every action captured so far, every single action)
    actions_so_far = []
    old_total_bytes_written = 0
    for i in range(N_ACTIONS):
        actions_so_far.append(make_synthetic_action(i))
        old_total_bytes_written += len(json.dumps({
            "name": "x", "start_url": "x", "actions": actions_so_far,
        }, default=str))
    new_total_bytes_written = jsonl_size + (json_size * (N_ACTIONS // 20 + 1))  # ~one consolidation per 20 actions

    print(f"\n=== OLD vs NEW total bytes WRITTEN across the whole recording ===")
    print(f"OLD (full JSON rewrite every action): {old_total_bytes_written:,} bytes")
    print(f"NEW (JSONL append + periodic consolidation): ~{new_total_bytes_written:,} bytes")
    print(f"reduction: {(1 - new_total_bytes_written / old_total_bytes_written) * 100:.1f}%")

    # a generous multiplier (not a tight bound) - this just needs to catch
    # a real O(N) or worse per-action regression, not chase timing noise
    # from a synthetic in-process benchmark with no real I/O latency
    assert last_batch_avg < max(first_batch_avg * 5, 0.002), (
        f"per-action time should stay roughly flat, not grow with recording "
        f"length: first batch {first_batch_avg*1000:.4f}ms vs last batch {last_batch_avg*1000:.4f}ms"
    )
    assert new_total_bytes_written < old_total_bytes_written / 5, "expected a large reduction in total bytes written"

    # cleanup
    jsonl_path.unlink(missing_ok=True)
    draft_path.unlink(missing_ok=True)

    print("\nPASS: per-action write cost stays flat and total bytes written drops sharply")


if __name__ == "__main__":
    main()
