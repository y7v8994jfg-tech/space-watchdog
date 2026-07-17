#!/usr/bin/env python3
"""
HF Space Watchdog - runs on GitHub Actions.
Checks Space health and auto-restarts if squeezed out.

Triggers: GitHub Actions cron every 15 minutes, 24/7.
Completely decoupled from local machine.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

REPO = os.environ.get("SPACE_REPO", "avvnire/agent-data")
SPACE_URL = os.environ.get("SPACE_URL", f"https://{REPO.replace('/', '-')}.hf.space")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
# GitHub Actions runs in US, can access huggingface.co directly
HF_API = "https://huggingface.co/api/spaces"

# Beijing time
BJ = timezone(timedelta(hours=8))
now_str = datetime.now(BJ).strftime("%Y-%m-%d %H:%M:%S")


def check_runtime(token):
    """Check Space runtime status via HF API."""
    try:
        r = requests.get(
            f"{HF_API}/{REPO}/runtime",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if r.status_code != 200:
            return f"API_ERROR_{r.status_code}", None, None
        data = r.json()
        stage = data.get("stage", "unknown")
        hw = data.get("hardware", {})
        hw_current = hw.get("current") if hw else None
        err = data.get("errorMessage")
        return stage, err, hw_current
    except Exception as e:
        return f"API_FAIL: {e}", None, None


def check_page():
    """Check if Space serves HTTP."""
    try:
        r = requests.get(SPACE_URL, timeout=30, allow_redirects=True)
        return r.status_code
    except:
        return -1


def restart_space(token):
    """Restart the Space via HF API."""
    try:
        r = requests.post(
            f"{HF_API}/{REPO}/restart",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        return r.status_code, r.text[:200] if r.text else ""
    except Exception as e:
        return -1, str(e)


def main():
    if not HF_TOKEN:
        print(f"[{now_str}] ❌ No HF_TOKEN set, aborting.")
        sys.exit(1)

    print(f"[{now_str}] Checking {REPO}...")

    stage, err, hw_current = check_runtime(HF_TOKEN)
    page_status = check_page()

    print(f"  Runtime stage: {stage}")
    print(f"  Hardware: {hw_current}")
    if err:
        print(f"  Error: {err}")
    print(f"  Page HTTP: {page_status}")

    needs_restart = False
    reason = ""

    # Condition 1: Runtime error / paused / build error
    if stage in ("RUNTIME_ERROR", "PAUSED", "BUILD_ERROR"):
        needs_restart = True
        reason = f"stage={stage}"

    # Condition 2: No hardware allocated (squeezed out)
    elif hw_current is None and stage not in ("BUILDING",):
        needs_restart = True
        reason = f"hardware=None (squeezed out), stage={stage}"

    # Condition 3: 503 from the Space page
    elif page_status == 503:
        needs_restart = True
        reason = f"page=503, stage={stage}"

    # Condition 4: Page unreachable AND not building/starting
    elif page_status == -1 and stage not in ("BUILDING", "APP_STARTING", "RUNNING_APP"):
        needs_restart = True
        reason = f"page=unreachable, stage={stage}"

    if needs_restart:
        print(f"
⚠️ Space unhealthy: {reason}")
        print(f"   Triggering restart...")
        status, body = restart_space(HF_TOKEN)
        if status == 200:
            print(f"✅ Restart triggered successfully (HTTP {status})")
        else:
            print(f"❌ Restart failed (HTTP {status}): {body}")
            # If restart API fails, try factory reboot as fallback
            try:
                r = requests.post(
                    f"{HF_API}/{REPO}/restart",
                    headers={"Authorization": f"Bearer {HF_TOKEN}"},
                    params={"factory": "true"},
                    timeout=15
                )
                print(f"   Factory reboot attempt: HTTP {r.status_code}")
            except:
                pass
    else:
        print(f"✅ Space healthy (stage={stage}, page={page_status}). All good.")


if __name__ == "__main__":
    main()
