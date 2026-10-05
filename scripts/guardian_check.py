#!/usr/bin/env python3
"""CCTV Guardian — motion alarm check (cron-friendly).

Designed to run once per invocation from a scheduled job (e.g. a Muse agent
cron every 5-15 minutes). For every configured camera it fetches recent EZVIZ
motion alarms; for each alarm newer than the last seen one it:
  1. downloads the alarm image (or takes a fresh snapshot as fallback),
  2. optionally describes it with a vision model (OpenAI-compatible API),
  3. sends a notification to NOTIFY_WEBHOOK (or prints it when unset).

State: <CCTV_GUARDIAN_HOME>/state/guardian_state.json  {alias: last_alarm_id}

Exit codes: 0 = ok (or nothing new), 1 = config error, 2 = auth/MFA error.
"""
import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ezviz_client import get_client, load_cameras, home_dir, load_dotenv

load_dotenv()

STATE_FILE = home_dir() / "state" / "guardian_state.json"
WEBHOOK = os.environ.get("NOTIFY_WEBHOOK", "").strip()
VISION_URL = os.environ.get("VISION_API_URL", "").strip().rstrip("/")
VISION_KEY = os.environ.get("VISION_API_KEY", "").strip()
VISION_MODEL = os.environ.get("VISION_MODEL", "").strip()
VISION_LANG = os.environ.get("VISION_LANG", "en").strip().lower()
MAX_ALERTS = int(os.environ.get("GUARDIAN_MAX_ALERTS", "3"))

VISION_PROMPTS = {
    "en": ("You are a CCTV motion detector. Output ONLY one casual sentence, "
           "max 12 words, describing what is visible. No reasoning, no prefix. "
           "Example: 'Courier passing by with a package.'"),
    "id": ("Kamu detektor gerakan CCTV. Output HANYA 1 kalimat kasual, max 12 kata, "
           "menjelaskan yang terlihat. Tanpa reasoning, tanpa prefix. "
           "Contoh: 'Ada kurir lewat bawa paket.'"),
    "fr": ("Tu es un détecteur de mouvement pour vidéosurveillance. Réponds UNIQUEMENT "
           "par une phrase décontractée, 12 mots maximum, décrivant ce qui est visible. "
           "Sans raisonnement, sans préfixe. Exemple : 'Un livreur passe avec un colis.'"),
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def download_image(url: str) -> str | None:
    try:
        import requests
    except ImportError:
        print("Error: the 'requests' package is not installed. Run: pip install -r requirements.txt",
              file=sys.stderr)
        return None
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and r.content:
            p = Path("/tmp") / f"cctv_alarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            p.write_bytes(r.content)
            return str(p)
    except Exception as e:
        print(f"  alarm image download failed: {e}", file=sys.stderr)
    return None


def take_snapshot(alias: str) -> str | None:
    snap = Path(__file__).resolve().parent / "snapshot.py"
    try:
        res = subprocess.run([sys.executable, str(snap), alias],
                             capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            out = res.stdout.strip().splitlines()
            if out and Path(out[-1]).exists():
                return out[-1]
    except Exception as e:
        print(f"  fallback snapshot failed: {e}", file=sys.stderr)
    return None


def describe_image(image_path: str) -> str | None:
    """Describe the image with the configured vision model. None when disabled/failing."""
    if not (VISION_URL and VISION_KEY and VISION_MODEL):
        return None
    import requests
    try:
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
        prompt = VISION_PROMPTS.get(VISION_LANG, VISION_PROMPTS["en"])
        r = requests.post(
            f"{VISION_URL}/chat/completions",
            headers={"Authorization": f"Bearer {VISION_KEY}", "Content-Type": "application/json"},
            json={
                "model": VISION_MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Describe in one short sentence."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ]},
                ],
                "max_tokens": 60,
                "temperature": 0.3,
            },
            timeout=30,
        )
        if r.status_code == 200:
            content = (r.json()["choices"][0]["message"].get("content") or "").strip()
            content = content.split("\n")[0].strip()  # first line only, no reasoning spill
            words = content.split()
            if len(words) > 12:
                content = " ".join(words[:12])
            if len(content) >= 5:
                return content
    except Exception as e:
        print(f"  vision describe failed: {e}", file=sys.stderr)
    return None


def notify(payload: dict) -> None:
    if WEBHOOK:
        import requests
        try:
            r = requests.post(WEBHOOK, json=payload, timeout=10)
            print(f"  notified via webhook (HTTP {r.status_code})")
            return
        except Exception as e:
            print(f"  webhook failed: {e}", file=sys.stderr)
    # No webhook configured (or it failed): print so the cron log captures it.
    print("  [no webhook] " + json.dumps(payload, ensure_ascii=False))


def main() -> int:
    cameras = load_cameras()
    state = load_state()
    client = get_client()  # exits 1/2 on config/auth problems

    total_alerts = 0
    for alias, cam in cameras.items():
        name = cam.get("name", alias)
        try:
            result = client.get_alarminfo(serial=cam["serial"], limit=5)
        except Exception as e:
            print(f"[{alias}] alarm fetch failed: {e}", file=sys.stderr)
            continue

        alarms = result.get("alarms", []) or []
        last_id = state.get(alias)
        fresh = []
        for a in alarms:  # newest first
            aid = a.get("alarmId")
            if not aid or aid == last_id:
                break
            fresh.append(a)
        fresh.reverse()  # oldest first
        fresh = fresh[:MAX_ALERTS]

        for a in fresh:
            aid = a.get("alarmId")
            atime = a.get("alarmStartTimeStr", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print(f"[{alias}] new alarm {aid} @ {atime}")

            image = download_image(a.get("picUrl") or "") or take_snapshot(alias)
            desc = describe_image(image) if image else None

            hour = datetime.now().hour
            payload = {
                "text": f"\U0001f6a8 CCTV Guardian — motion detected\n"
                        f"\U0001f4f7 {name} ({alias}) · {atime}\n"
                        f"\U0001f441️ {desc or 'Motion detected.'}",
                "camera": alias,
                "camera_name": name,
                "alarm_time": atime,
                "is_night": hour >= 18 or hour < 6,
                "image_path": image,
            }
            notify(payload)
            state[alias] = aid
            total_alerts += 1

    save_state(state)
    print(f"done: {total_alerts} alert(s) sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
