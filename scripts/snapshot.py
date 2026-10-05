#!/usr/bin/env python3
"""EZVIZ cloud snapshot.
Usage: python3 snapshot.py <camera-alias> [output.jpg]
Prints the output path on success. Exit 1 on failure.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ezviz_client import get_client, load_cameras, resolve_camera


def main():
    if len(sys.argv) < 2:
        print("Usage: snapshot.py <camera-alias> [output.jpg]", file=sys.stderr)
        sys.exit(1)

    alias = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    cameras = load_cameras()
    cam = resolve_camera(cameras, alias)
    client = get_client()

    ts = time.strftime("%Y%m%d_%H%M%S")
    outfile = output or f"/tmp/ezviz_{alias.lower()}_{ts}.jpg"

    try:
        result = client.save_image(cam["serial"], outfile, channel=int(cam.get("channel", 1)))
        if result.get("ok") and os.path.isfile(outfile) and os.path.getsize(outfile) > 0:
            print(outfile)
        else:
            print(f"Error: failed to capture {cam.get('name', alias)}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {cam.get('name', alias)} - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
