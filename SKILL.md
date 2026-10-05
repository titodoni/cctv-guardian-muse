---
name: cctv-guardian
description: Control EZVIZ cloud cameras from chat (snapshot, PTZ move, video record) and run a scheduled motion-alert guardian. Trigger on "check my camera", "take a snapshot", "move the camera left", "record the terrace", "surveille la caméra", "prends une capture", "cek cctv", or when setting up camera monitoring.
---

# CCTV Guardian for Muse

Control EZVIZ cloud cameras and get automatic motion alerts — all from chat.
No local network needed: everything goes through the EZVIZ cloud API.

## Requirements

- An EZVIZ account with at least one camera already added in the EZVIZ app.
- Python 3.9+ with `pip install -r requirements.txt` (`pyezvizapi`, `requests`).
- For the guardian: a way to run `scripts/guardian_check.py` on a schedule
  (a Muse agent cron, system cron, or systemd timer).

**New here?** Do the guided setup first: read `ONBOARDING.md` and follow it
conversationally with the user. It collects credentials securely, registers
cameras, tests a snapshot, and installs the guardian schedule.

## Tooling

All scripts read config from `$CCTV_GUARDIAN_HOME` (default `~/.cctv-guardian`):
`.env` (credentials), `cameras.json` (alias → serial), `ezviz_session.json`
(cached login), `state/` (guardian watermarks).

```bash
S=scripts  # path to this build's scripts/

# Snapshot — prints the image path. ALWAYS show the image to the user.
python3 $S/snapshot.py <camera-alias> [output.jpg]

# PTZ — move a PTZ camera, then auto-snapshots (prints MEDIA:<path>)
python3 $S/ptz.py <left|right|up|down|zoom_in|zoom_out> [seconds] [camera-alias]

# Record — prints SUCCESS:<path>
python3 $S/record.py <camera-alias> [seconds] [output.mp4]

# List cameras on the account (onboarding helper)
python3 $S/list_cameras.py

# Guardian — one alarm-check pass (meant for a scheduler, not by hand)
python3 $S/guardian_check.py
```

## Auth

- Credentials live in `$CCTV_GUARDIAN_HOME/.env` (`EZVIZ_EMAIL`, `EZVIZ_PASSWORD`,
  `EZVIZ_REGION`), file mode 600. Never hardcode them, never print them,
  never commit them.
- Collect the password through the agent platform's secure credential flow —
  never ask for it in plain chat.
- The login session is cached in `ezviz_session.json` and refreshed automatically.
- If EZVIZ demands verification, it emails a 6-digit code: ask the user for it,
  re-run once with `EZVIZ_MFA=<code>`, then discard the code.

## Guardian (motion alerts)

`guardian_check.py` is built for a scheduler: each run fetches recent motion
alarms per camera and, for every new alarm, downloads the alarm image (or takes
a fresh snapshot), optionally describes it with a vision model
(`VISION_API_URL` / `VISION_API_KEY` / `VISION_MODEL`, OpenAI-compatible), and
POSTs a notification to `NOTIFY_WEBHOOK`. Without a webhook it prints to
stdout so the scheduler log captures it.

- Dedup: `state/guardian_state.json` stores the last alarm id per camera.
- Spam guard: `GUARDIAN_MAX_ALERTS` (default 3) caps alerts per camera per run.
- Recommended schedule: every 10 minutes. More frequent than ~5 minutes risks
  EZVIZ rate limits.

## Operating rules

1. After every snapshot/PTZ/record, show the resulting image or video to the
   user — never a text-only "done".
2. Keep the site's camera names: use the `name` from `cameras.json` when
   talking about a camera.
3. If a command fails with an auth error, try once more (the session may have
   just expired); if it asks for MFA, follow the Auth section above.
4. If the camera is offline, say so plainly and suggest checking power/network —
   do not retry in a loop.
5. PTZ on a fixed-lens camera exits with code 2 and a clear note — relay that
   note instead of retrying.
6. Never invent camera aliases, serials, or install steps. If `cameras.json`
   is missing, run the onboarding.

## Troubleshooting

- `MFA required` → get the 6-digit code from the user's email, `EZVIZ_MFA=<code>`.
- `unknown camera` → run `list_cameras.py` and update `cameras.json`.
- Wrong region (`EZVIZ_REGION`) is the most common login failure — the serial's
  region must match the account's (see `.env.example`).
- Guardian sends nothing → check the scheduler log; verify `NOTIFY_WEBHOOK`
  and that alarms exist in the EZVIZ app for the period.
