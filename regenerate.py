"""CLI tool to manually regenerate Python test scripts from recording JSON files.

Usage:
    python regenerate.py storage/recordings/session_20260903_151100.json
    python regenerate.py  (regenerates all recordings in storage/recordings/)
"""

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from generator.script_generator import generate_script


def main():
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        recordings_dir = BASE_DIR / "storage" / "recordings"
        paths = list(recordings_dir.glob("*.json"))

    if not paths:
        print("No recording JSON files specified or found.")
        sys.exit(1)

    for json_path in paths:
        if not json_path.is_absolute():
            json_path = BASE_DIR / json_path

        if not json_path.exists():
            print(f"File not found: {json_path}")
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            script_path = generate_script(data)
            print(f"[SUCCESS] Regenerated script for {json_path.name} -> {script_path}")
        except Exception as e:
            print(f"[ERROR] Could not regenerate script for {json_path.name}: {e}")


if __name__ == "__main__":
    main()
