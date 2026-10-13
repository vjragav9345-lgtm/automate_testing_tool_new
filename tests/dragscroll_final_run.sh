#!/bin/bash
# TEST-ONLY: the whole final validation sequence for the drag/scroll fix (run from the repo root).
#   bash tests/dragscroll_final_run.sh
# Writes tests/_probe_out/final_*.{json,log} and finally tests/_probe_out/final_all_done.flag
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
PY=./venv/Scripts/python.exe
OUT=tests/_probe_out
BK=$(cat $OUT/backup_dir.txt)
rm -f $OUT/final_all_done.flag

echo "[1/8] re-record noUiSlider (~200 actions, headless) with the FINAL recorder"
$PY tests/dragscroll_scenario_record.py nouislider --target 200 --headless > $OUT/final_noui_rec.log 2>&1

echo "[2/8] noUiSlider: ORIGINAL code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_nouislider_large.json --headless --generator $BK/generator/script_generator.py --out $OUT/final_noui_before.json > $OUT/final_noui_before.log 2>&1
echo "[3/8] noUiSlider: FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_nouislider_large.json --headless --out $OUT/final_noui_after.json > $OUT/final_noui_after.log 2>&1
echo "[4/8] noUiSlider recorded by the OLD recorder: FIXED code (replay-side robustness)"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_nouislider_large_oldrec.json --headless --out $OUT/final_noui_old_after.json > $OUT/final_noui_old_after.log 2>&1

echo "[5/8] Amazon: FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_amazon_small.json --headless --out $OUT/final_amz_after.json > $OUT/final_amz_after.log 2>&1

echo "[6/8] Myntra 83 actions: FIXED code"
$PY tests/dragscroll_probe.py storage/recordings/dragscroll_myntra_medium.json --out $OUT/final_myn_after.json > $OUT/final_myn_after.log 2>&1

echo "[7/8] evidence recording session_20260928_100946 x3: FIXED code, default cascade"
for i in 1 2 3; do
  $PY tests/dragscroll_probe.py storage/recordings/session_20260928_100946.json --out $OUT/final2_ev_run$i.json > $OUT/final2_ev_run$i.log 2>&1
done

echo "[8/8] cascade-unchanged check + drag/nudge fixture tests"
$PY tests/dragscroll_cascade_check.py > $OUT/final_cascade.log 2>&1
$PY tests/dragscroll_nudge_check.py > $OUT/final_nudge.log 2>&1
$PY tests/flowfix9_test3_drag_replay.py > $OUT/final_fix9t3.log 2>&1
$PY tests/flowfix10_test3_multithumb_drag.py > $OUT/final_fix10t3.log 2>&1

echo done > $OUT/final_all_done.flag
