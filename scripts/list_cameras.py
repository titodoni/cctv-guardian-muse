#!/usr/bin/env python3
"""List EZVIZ devices on the account.

Used during onboarding so the user can pick friendly names for each camera.
Usage: python3 list_cameras.py
Prints one line per device: serial | name | model | online
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ezviz_client import get_client


def main():
    client = get_client()
    try:
        devices = client.get_device_infos()
    except Exception as e:
        print(f"Error listing devices: {e}", file=sys.stderr)
        sys.exit(1)

    if not devices:
        print("No devices found on this EZVIZ account.", file=sys.stderr)
        sys.exit(1)

    for d in devices:
        serial = d.get("deviceSerial", "?")
        name = d.get("deviceName", d.get("deviceType", "?"))
        model = d.get("deviceType", "?")
        status = d.get("status", "?")
        print(f"{serial} | {name} | {model} | status={status}")


if __name__ == "__main__":
    main()
