#!/usr/bin/env python3
"""EZVIZ cloud PTZ control.
Usage: python3 ptz.py <direction> [duration_sec] [camera-alias] [--speed 1-10] [--no-snapshot]
Prints status, and MEDIA:<path> when a post-move snapshot is taken.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ezviz_client import get_client, load_cameras, resolve_camera

DIRECTION_MAP = {
    # English
    "left": "LEFT", "right": "RIGHT", "up": "UP", "down": "DOWN",
    "zoom_in": "ZOOM_IN", "zoomin": "ZOOM_IN", "zoom-in": "ZOOM_IN",
    "zoom_out": "ZOOM_OUT", "zoomout": "ZOOM_OUT", "zoom-out": "ZOOM_OUT",
    # French
    "gauche": "LEFT", "droite": "RIGHT", "haut": "UP", "bas": "DOWN",
    # Indonesian
    "kiri": "LEFT", "kanan": "RIGHT", "atas": "UP", "bawah": "DOWN",
}


def move_camera(direction: str, duration: float, alias: str, speed: int, take_snapshot: bool):
    cameras = load_cameras()
    cam = resolve_camera(cameras, alias)

    if not cam.get("ptz", False):
        print(f"Note: camera '{cam.get('name', alias)}' is a fixed lens and does not support PTZ movement.",
              file=sys.stderr)
        sys.exit(2)

    dir_cmd = DIRECTION_MAP.get(direction.lower())
    if not dir_cmd:
        print(f"Error: invalid direction '{direction}'.", file=sys.stderr)
        print(f"Valid: left, right, up, down, zoom_in, zoom_out (also: gauche/droite/haut/bas, kiri/kanan/atas/bawah)",
              file=sys.stderr)
        sys.exit(1)

    speed = max(1, min(10, speed))
    duration = max(0.2, min(5.0, duration))

    client = get_client()
    serial = cam["serial"]
    client.ptz_control(command=dir_cmd, serial=serial, action="START", speed=speed)
    time.sleep(duration)
    client.ptz_control(command=dir_cmd, serial=serial, action="STOP", speed=speed)
    print(f"OK: moved {cam.get('name', alias)} {dir_cmd} for {duration}s (speed {speed})")

    if take_snapshot:
        time.sleep(0.5)
        outfile = Path("/tmp") / f"cctv_{alias.lower()}_latest.jpg"
        snap = Path(__file__).resolve().parent / "snapshot.py"
        res = subprocess.run([sys.executable, str(snap), alias, str(outfile)],
                             capture_output=True, text=True)
        if res.returncode == 0 and outfile.exists():
            print(f"MEDIA:{outfile}")


def main():
    parser = argparse.ArgumentParser(description="EZVIZ PTZ control")
    parser.add_argument("direction", help="left/right/up/down/zoom_in/zoom_out")
    parser.add_argument("duration", nargs="?", type=float, default=0.8, help="seconds (default 0.8)")
    parser.add_argument("camera", nargs="?", default=None, help="camera alias (default: first PTZ camera)")
    parser.add_argument("--speed", type=int, default=5, help="1-10 (default 5)")
    parser.add_argument("--no-snapshot", action="store_true", help="skip post-move snapshot")
    args = parser.parse_args()

    cameras = load_cameras()
    alias = args.camera
    if alias is None:
        ptz_cams = [a for a, c in cameras.items() if c.get("ptz")]
        if not ptz_cams:
            print("Error: no PTZ-capable camera configured.", file=sys.stderr)
            sys.exit(1)
        alias = ptz_cams[0]

    try:
        move_camera(args.direction, args.duration, alias, args.speed, not args.no_snapshot)
    except Exception as e:
        print(f"Error moving PTZ: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
