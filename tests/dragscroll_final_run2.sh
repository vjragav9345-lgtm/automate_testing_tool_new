#!/bin/bash
# TEST-ONLY: second final validation pass - same recordings, patched replay (tier order for drags +
# candidate pointer mappings). Writes tests/_probe_out/final3_*.{json,log}; finishes with final3_all_done.flag
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
PY=./venv/Scripts/python.exe
OUT=tests/_probe_out
BK=$(cat $OUT/backup_dir.txt)
rm -f $OUT/final3_all_done.flag

echo "[1/7] noUiSlider 202 actions (final recorder): FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_nouislider_large.json --headless --out $OUT/final3_noui_after.json > $OUT/final3_noui_after.log 2>&1
echo "[2/7] noUiSlider 202 actions recorded by the OLD recorder: FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_nouislider_large_oldrec.json --headless --out $OUT/final3_noui_old_after.json > $OUT/final3_noui_old_after.log 2>&1
echo "[3/7] Amazon 21 actions: FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_amazon_small.json --headless --out $OUT/final3_amz_after.json > $OUT/final3_amz_after.log 2>&1
echo "[4/7] Myntra 83 actions: FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_myntra_medium.json --out $OUT/final3_myn_after.json > $OUT/final3_myn_after.log 2>&1
echo "[5/7] evidence recording x3: FIXED code, default cascade"
for i in 1 2 3; do
  $PY tests/dragscroll_probe.py storage/recordings/session_20260928_100946.json --out $OUT/final3_ev_run$i.json > $OUT/final3_ev_run$i.log 2>&1
done
echo "[6/7] cascade-unchanged check + nudge fixture"
$PY tests/dragscroll_cascade_check.py > $OUT/final3_cascade.log 2>&1
$PY tests/dragscroll_nudge_check.py > $OUT/final3_nudge.log 2>&1
echo "[7/7] earlier drag fixture tests + phase4 regression suite"
$PY tests/flowfix9_test2_drag_capture.py > $OUT/final3_fix9t2.log 2>&1
$PY tests/flowfix9_test3_drag_replay.py > $OUT/final3_fix9t3.log 2>&1
$PY tests/flowfix10_test3_multithumb_drag.py > $OUT/final3_fix10t3.log 2>&1
$PY tests/flowfix10_test2_locator_stability.py > $OUT/final3_fix10t2.log 2>&1
$PY tests/flowfix9_test1_toggle_verify.py > $OUT/final3_fix9t1.log 2>&1
for t in phase4_test_bug1_hover phase4_test_bug2_card phase4_test_bug3_scroll phase4_test_multi_candidate; do
  $PY -m tests.$t > $OUT/final3_$t.log 2>&1
  echo "exit $?" >> $OUT/final3_$t.log
done
echo done > $OUT/final3_all_done.flag
