import json
import subprocess
from pathlib import Path
from datetime import datetime

# ==========================================================
# Configuration
# ==========================================================

TIMELINE_DIR = Path(r"C:\Games\Steam\userdata\userid\gamerecordings\timelines")
VIDEO_DIR = Path(r"C:\Games\Steam\userdata\userid\gamerecordings\video")
OUTPUT_DIR = Path(r"D:\Recordings\Achievements")

SECONDS_BEFORE = 30
SECONDS_AFTER = 30

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# Build recording index
# ==========================================================

recordings = {}

for folder in VIDEO_DIR.iterdir():

    if not folder.is_dir():
        continue

    name = folder.name

    if not name.startswith("bg_"):
        continue

    try:
        # bg_3723430_20260630_181739
        _, appid, date, time = name.split("_")

        dt = datetime.strptime(date + time, "%Y%m%d%H%M%S")

        recordings.setdefault(appid, []).append({
            "folder": folder,
            "datetime": dt
        })

    except Exception:
        continue

# ==========================================================

print("=" * 60)
print("Steam Achievement Clip Exporter")
print("=" * 60)
print()

timeline_files = sorted(TIMELINE_DIR.glob("timeline_*.json"))

print(f"Found {len(timeline_files)} timeline files.\n")

for timeline_file in timeline_files:

    try:
        with open(timeline_file, "r", encoding="utf-8") as f:
            timeline = json.load(f)
    except Exception as e:
        print(f"[!] Couldn't read {timeline_file.name}")
        print(e)
        continue

    stem = timeline_file.stem
    remainder = stem[len("timeline_"):]

    datetime_part = remainder[-15:]
    appid = remainder[:-15]

    try:
        timeline_dt = datetime.strptime(
            datetime_part.replace("_", ""),
            "%Y%m%d%H%M%S"
        )
    except Exception:
        print(f"[!] Bad filename: {timeline_file.name}")
        continue

    if appid not in recordings:
        print(f"[!] No recordings found for app {appid}")
        print()
        continue

    # ------------------------------------------------------
    # Find closest recording
    # ------------------------------------------------------

    closest = None
    smallest_diff = None

    for recording in recordings[appid]:

        diff = abs(
            (recording["datetime"] - timeline_dt).total_seconds()
        )

        if smallest_diff is None or diff < smallest_diff:
            smallest_diff = diff
            closest = recording

    session_folder = closest["folder"]
    mpd_file = session_folder / "session.mpd"

    if not mpd_file.exists():
        print(f"[!] session.mpd missing:")
        print(session_folder)
        print()
        continue

    print(f"[Timeline] {timeline_file.name}")
    print(f"   -> {session_folder.name}")
    print(f"   Difference: {int(smallest_diff)} seconds")

    entries = timeline.get("entries", [])

    for entry in entries:

        if entry.get("type") != "achievement":
            continue

        achievement = entry.get(
            "achievement_name",
            "Unknown Achievement"
        )

        # sanitize filename
        for c in '<>:"/\\|?*':
            achievement = achievement.replace(c, "_")

        try:
            achievement_time = int(entry["time"]) / 1000.0
        except Exception:
            continue

        clip_start = max(0, achievement_time - SECONDS_BEFORE)
        clip_duration = SECONDS_BEFORE + SECONDS_AFTER

        recording_stamp = session_folder.name.split("_", 2)[2]

        output_file = (
            OUTPUT_DIR /
            f"{appid} - {recording_stamp} - {achievement}.mkv"
        )

        if output_file.exists():
            print(f"      [✓] {output_file.name}")
            continue

        print(f"      [>] {achievement}")

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(clip_start),
                "-i",
                str(mpd_file),
                "-t",
                str(clip_duration),
                "-c",
                "copy",
                str(output_file)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            print("          ✓ Success")
        else:
            print("          ✗ Failed")
            print(result.stderr)

    print()

print("=" * 60)
print("Finished.")
print("=" * 60)
