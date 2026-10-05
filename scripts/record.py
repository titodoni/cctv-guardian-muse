#!/usr/bin/env python3
"""EZVIZ cloud video recorder.
Usage: python3 record.py <camera-alias> [duration_sec] [output.mp4]
Prints SUCCESS:<path> on success. Exit 1 on failure.

Note: cloud recordings may be encrypted. The script fetches and caches the
camera media key automatically (first run may require EZVIZ_MFA).
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ezviz_client import get_client, load_cameras, resolve_camera, home_dir, load_dotenv


def media_key_path() -> Path:
    return home_dir() / "ezviz_media_key.json"


def get_media_key(client, serial, smscode=None):
    kp = media_key_path()
    if kp.exists():
        try:
            keys = json.loads(kp.read_text())
            if serial in keys:
                return keys[serial]
        except Exception:
            pass
    try:
        result = client.get_cam_key(serial, smscode=smscode)
        key = result.get("encryptkey")
        if key:
            keys = json.loads(kp.read_text()) if kp.exists() else {}
            keys[serial] = key
            kp.write_text(json.dumps(keys, indent=2))
            try:
                os.chmod(kp, 0o600)
            except OSError:
                pass
            return key
    except Exception as e:
        if "20002" in str(e) or "MFA" in str(e):
            print(f"MFA required to fetch the media key for {serial}.", file=sys.stderr)
            print("Re-run with EZVIZ_MFA=<code> (one-time).", file=sys.stderr)
        raise
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: record.py <camera-alias> [duration_sec] [output.mp4]", file=sys.stderr)
        sys.exit(1)

    alias = sys.argv[1].lower()
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    cameras = load_cameras()
    cam = resolve_camera(cameras, alias)
    serial = cam["serial"]
    channel = int(cam.get("channel", 1))

    if len(sys.argv) > 3:
        output = Path(sys.argv[3])
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"/tmp/cctv_{alias}_{ts}.mp4")

    load_dotenv()
    print(f"Recording {cam.get('name', alias)} ({serial}) for {duration}s...")

    client = get_client()
    media_key = None
    try:
        media_key = get_media_key(client, serial)
    except Exception as e:
        print(f"Warning: no media key ({e}); recording may not be playable.", file=sys.stderr)

    kwargs = {"duration_seconds": duration, "channel": channel}
    if media_key:
        kwargs["decrypt_video"] = True
        kwargs["media_key"] = media_key

    try:
        result = client.save_clip(serial, str(output), source="cloud", **kwargs)
    except Exception as e:
        print(f"Cloud recording failed: {e}", file=sys.stderr)
        sys.exit(1)

    if result.get("ok") and output.exists():
        print(f"SUCCESS:{output}")
    else:
        print(f"FAILED: {result}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
