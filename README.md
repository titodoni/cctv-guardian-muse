# CCTV Guardian for Muse

Give your Muse agent eyes: control your EZVIZ cloud cameras from chat —
snapshots, PTZ moves, video recordings — plus a scheduled guardian that
watches for motion and sends you alerts automatically.

No local network needed. Everything goes through the EZVIZ cloud API.

## Quick start (about 10 minutes)

1. Clone and install:
   ```bash
   git clone https://github.com/titodoni/cctv-guardian-muse.git
   cd cctv-guardian-muse
   pip install -r requirements.txt
   ```
2. Give `ONBOARDING.md` to your Muse agent (or say "run the CCTV Guardian
   onboarding"). It walks you through setup conversationally:
   - secure EZVIZ credential entry (never typed in chat)
   - automatic camera discovery
   - live test snapshot from your own camera
   - optional notifications (your webhook) and AI image descriptions
   - optional guardian schedule (motion checks every N minutes)

No config files to hand-edit.

## What's inside

- `SKILL.md` — the agent skill (trigger phrases, operating rules)
- `ONBOARDING.md` — the conversational setup prompt for your agent
- `scripts/snapshot.py` — still image from any camera
- `scripts/ptz.py` — pan / tilt / zoom a PTZ camera
- `scripts/record.py` — short video clip
- `scripts/list_cameras.py` — list cameras on your EZVIZ account
- `scripts/guardian_check.py` — one motion-alarm check pass (for schedulers)
- `scripts/ezviz_client.py` — shared login, session cache, MFA handling

## Requirements

- An EZVIZ account with at least one camera added in the EZVIZ app
- Python 3.9+
- A Muse agent that can run scripts (and schedule them, for the guardian)

## Security

- Credentials live only in `$CCTV_GUARDIAN_HOME/.env` (mode 600) on your machine.
- Login sessions are cached with mode 600 and refreshed automatically.
- If EZVIZ asks for email verification, the onboarding handles the one-time code.
- This repo contains no credentials — ever. If you fork it, keep it that way.

## License

All rights reserved. Purchase includes personal use on your own devices.
