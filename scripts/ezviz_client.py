#!/usr/bin/env python3
"""Shared EZVIZ client bootstrap for the cctv-guardian skill.

All configuration lives under CCTV_GUARDIAN_HOME (default ~/.cctv-guardian):
  .env                  EZVIZ_EMAIL, EZVIZ_PASSWORD, EZVIZ_REGION, ...
  cameras.json          {"alias": {"serial": ..., "name": ..., "channel": 1, "ptz": bool}}
  ezviz_session.json    cached login session (chmod 600)
  state/                runtime state files

Import this module instead of re-implementing login in every script.
"""
import json
import os
import sys
from pathlib import Path


def home_dir() -> Path:
    return Path(os.environ.get("CCTV_GUARDIAN_HOME", str(Path.home() / ".cctv-guardian")))


def load_dotenv() -> None:
    env_file = home_dir() / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def session_path() -> Path:
    return home_dir() / "ezviz_session.json"


def cameras_path() -> Path:
    return home_dir() / "cameras.json"


def load_cameras() -> dict:
    p = cameras_path()
    if not p.exists():
        print(f"Error: cameras.json not found at {p}.", file=sys.stderr)
        print("Run the onboarding first (ONBOARDING.md) to register your cameras.", file=sys.stderr)
        sys.exit(1)
    try:
        cams = json.loads(p.read_text())
    except Exception as e:
        print(f"Error: cannot parse {p}: {e}", file=sys.stderr)
        sys.exit(1)
    if not cams:
        print(f"Error: no cameras defined in {p}.", file=sys.stderr)
        sys.exit(1)
    return cams


def resolve_camera(cameras: dict, alias: str) -> dict:
    cam = cameras.get(alias.lower())
    if not cam:
        print(f"Error: unknown camera '{alias}'. Available: {', '.join(sorted(cameras))}", file=sys.stderr)
        sys.exit(1)
    return cam


def get_client():
    """Return an authenticated EzvizClient (cached session, auto re-login)."""
    try:
        from pyezvizapi import EzvizClient
    except ImportError:
        print("Error: the 'pyezvizapi' package is not installed.", file=sys.stderr)
        print("Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    load_dotenv()
    email = os.environ.get("EZVIZ_EMAIL", "")
    password = os.environ.get("EZVIZ_PASSWORD", "")
    region = os.environ.get("EZVIZ_REGION", "apiisgp.ezvizlife.com")
    mfa = os.environ.get("EZVIZ_MFA", "")

    if not email or not password:
        print("Error: EZVIZ_EMAIL and EZVIZ_PASSWORD are required.", file=sys.stderr)
        print("See .env.example and ONBOARDING.md for setup.", file=sys.stderr)
        sys.exit(1)

    sp = session_path()
    if sp.exists():
        try:
            cached = json.loads(sp.read_text())
            if cached.get("session_id"):
                client = EzvizClient(account=email, password=password, url=region, token=cached)
                client.get_user_id()  # raises if the session is dead
                return client
        except Exception:
            pass  # fall through to fresh login

    print("Logging in to EZVIZ cloud...", file=sys.stderr)
    client = EzvizClient(account=email, password=password, url=region)
    try:
        if mfa:
            client.login(sms_code=int(mfa))
        else:
            client.login()
    except Exception as e:
        msg = str(e)
        if "MFA" in msg or "verification" in msg.lower() or "20002" in msg:
            print("MFA required: EZVIZ emailed you a 6-digit code.", file=sys.stderr)
            print("Re-run with EZVIZ_MFA=<code> set (one-time, do not store it).", file=sys.stderr)
            sys.exit(2)
        raise

    token = getattr(client, "_token", None)
    if token:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(token))
        try:
            os.chmod(sp, 0o600)
        except OSError:
            pass
    return client
