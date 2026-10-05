# CCTV Guardian — Onboarding Prompt (for Muse agents)

> **How to use this file:** when the user wants to set up the CCTV Guardian
> skill, follow this runbook conversationally, one phase at a time. Do not
> dump all questions at once. Confirm each phase works before moving on.
> Speak the user's language.

## What this sets up

1. Secure EZVIZ cloud credentials (never in chat, never in the repo).
2. The user's cameras registered with friendly names.
3. A tested snapshot, so the user sees their own camera image before we finish.
4. Optional: motion-alert notifications (webhook) and AI image descriptions.
5. Optional: the guardian schedule (recurring alarm checks).

**Before you start, tell the user in one short paragraph** what the skill does
and what you will need from them: their EZVIZ account email, access to the
email inbox for a possible verification code, and the EZVIZ app open (to read
camera serials if auto-detection fails).

---

## Phase 1 — Credentials (secure)

1. Ask for the EZVIZ account **email** and **region**:
   - "What email do you use for your EZVIZ account?"
   - "Which region is your account on? (Asia-Pacific / Europe / Americas — 
     default Asia-Pacific. If unsure, pick the default; we can change it.)"
   - Map: Asia-Pacific → `apiisgp.ezvizlife.com`, Europe → `apiieu.ezvizlife.com`,
     Americas → `apius.ezvizlife.com`.
2. For the **password**: NEVER ask for it in plain chat. Use your platform's
   secure credential capture. Tell the user: "I'll open a secure form for your
   EZVIZ password — it goes straight to encrypted storage, I never see it in chat."
3. Write `$CCTV_GUARDIAN_HOME/.env` (default `~/.cctv-guardian/.env`):
   ```
   EZVIZ_EMAIL=<email>
   EZVIZ_PASSWORD=<from secure storage>
   EZVIZ_REGION=<endpoint>
   ```
   Then `chmod 600` the file. Verify the file exists and is not world-readable.

**If the user hesitates:** explain the password only ever lives in that one
600-permission file on their machine and is only sent to EZVIZ's own login API.

## Phase 2 — Test login and discover cameras

1. Run: `python3 scripts/list_cameras.py`
2. **If it prints devices:** show the list (serial, name, model) and go to Phase 3.
3. **If it exits 2 (MFA):** say "EZVIZ just emailed you a 6-digit verification
   code." Ask the user to read it from their inbox, then re-run with
   `EZVIZ_MFA=<code> python3 scripts/list_cameras.py`. The code is one-time —
   never write it into `.env`.
4. **If login fails:** the most common cause is the wrong region. Ask which
   country the EZVIZ account was registered in and try the matching endpoint.
   After two failures, stop and ask the user to confirm the email/password.

## Phase 3 — Name the cameras

For each device from Phase 2, ask: "What should I call this camera?
(e.g. `carport`, `terrace`, `garage` — one word, no spaces.)"
Also ask whether it can pan/tilt/zoom (PTZ) — if the user is unsure, default
`false` for fixed cameras; the skill will tell them if a PTZ command is
rejected.

Write `$CCTV_GUARDIAN_HOME/cameras.json`:
```json
{
  "carport": {"serial": "<serial>", "name": "Carport", "channel": 1, "ptz": false},
  "terrace": {"serial": "<serial>", "name": "Terrace", "channel": 1, "ptz": true}
}
```

## Phase 4 — Test snapshot (the proof)

1. Run: `python3 scripts/snapshot.py <first-alias>`
2. **Show the image to the user, large.** Ask: "Is this the right camera?"
3. If yes → continue. If the image is wrong/black → try the next alias, or
   re-check the serial in the EZVIZ app (device Settings > Device Information).
4. If the user has a PTZ camera, offer one demo move:
   `python3 scripts/ptz.py left 0.8 <alias>` then show the new snapshot.

Do not proceed until the user confirms at least one camera shows the correct image.

## Phase 5 — Notifications (optional but recommended)

Explain: "When motion is detected, the guardian can notify you automatically.
It sends a small JSON message to a webhook URL — your own bot, a WhatsApp
bridge, Telegram bot, n8n, etc. The message looks like this:"

```json
{"text": "🚨 CCTV Guardian — motion detected\n📷 Terrace (terrace) · 2026-10-05 21:40:12\n👁️ A courier passing by with a package.",
 "camera": "terrace", "camera_name": "Terrace",
 "alarm_time": "2026-10-05 21:40:12", "is_night": true, "image_path": "/tmp/cctv_alarm_....jpg"}
```

- If the user provides a URL → append `NOTIFY_WEBHOOK=<url>` to `.env`,
  then send a test: temporarily run a tiny POST with `{"text":"CCTV Guardian test — notifications working."}`
  and ask the user to confirm receipt.
- If the user skips → note that alerts will only appear in the scheduler log,
  and they can add a webhook later.

## Phase 6 — AI descriptions (optional)

Explain: "Alerts can include a one-sentence AI description of what the camera
saw ('A courier passing by with a package.'). This needs any OpenAI-compatible
vision API."

- If the user provides API URL + key + model → append to `.env`:
  `VISION_API_URL`, `VISION_API_KEY` (via secure capture, never in chat),
  `VISION_MODEL`, and `VISION_LANG` (`en`/`id`/`fr` — match the user's language).
- If skipped → alerts say "Motion detected." They can enable it later.

## Phase 7 — Guardian schedule (optional)

Explain: "The guardian checks EZVIZ for new motion alarms on a schedule and
notifies you. Recommended: every 10 minutes. Faster than ~5 minutes risks
EZVIZ rate limits."

1. Ask: "How often should it check? (default: every 10 minutes)" and
   "Which cameras should it watch? (default: all)".
   - If a subset: you can run one scheduled job per camera or filter later —
     keep it simple: all cameras, one job, unless the user insists.
2. Dry-run first: `python3 scripts/guardian_check.py` — show the user the
   output. Note: the first run may report the most recent alarms as a self-test;
   afterwards only new alarms trigger.
3. Create the recurring job on your agent platform (e.g. a Muse cron) that runs:
   `python3 /full/path/to/scripts/guardian_check.py`
   every N minutes. Confirm the job was created and show its schedule.

## Phase 8 — Done

Summarize in a short message:
- Which cameras are registered (alias → name).
- What was configured: notifications (yes/no), AI descriptions (yes/no + language),
  guardian schedule (interval).
- How to use it: "check the <alias>", "move <alias> left", "record <alias> 10 seconds".
- Where config lives (`$CCTV_GUARDIAN_HOME`) and that `.env` holds secrets.

---

## Hard rules (never break these)

1. **Passwords and API keys via secure capture only.** Never in chat, never in
   logs you quote back, never in the repo, never in `cameras.json`.
2. **`.env` is chmod 600.** Verify after writing.
3. **MFA codes are one-time.** Pass via env var for a single run; never store.
4. **Show every snapshot/image to the user.** A text-only "done" is a failure.
5. **Never invent serials, aliases, or install steps.** If `list_cameras.py`
   finds nothing, ask the user to read the serial from the EZVIZ app.
6. One phase at a time. If a phase fails twice, stop and explain — don't loop.
