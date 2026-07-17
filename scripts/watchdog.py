#!/usr/bin/env python3
"""
HF Space Watchdog - runs on GitHub Actions.
Checks Space health and auto-restarts if squeezed out.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

REPO = os.environ.get("SPACE_REPO", "avvnire/agent-data")
SPACE_URL = os.environ.get("SPACE_URL", "https://avvnire-agent-data.hf.space")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_API = "https://huggingface.co/api/spaces"

BJ = timezone(timedelta(hours=8))
now_str = datetime.now(BJ).strftime("%Y-%m-%d %H:%M:%S")


def check_runtime(token):
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
    try:
        r = requests.get(SPACE_URL, timeout=30, allow_redirects=True)
        return r.status_code
    except:
        return -1


def restart_space(token):
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
    print(f"[DEBUG] HF_TOKEN length={len(HF_TOKEN)}, starts={HF_TOKEN[:8]}, ends={HF_TOKEN[-6:]}" if HF_TOKEN else "[DEBUG] HF_TOKEN is EMPTY")
    if not HF_TOKEN:
        print(f"[{now_str}] No HF_TOKEN, aborting.")
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

    if stage in ("RUNTIME_ERROR", "PAUSED", "BUILD_ERROR"):
        needs_restart = True
        reason = f"stage={stage}"
    elif hw_current is None and stage not in ("BUILDING",):
        needs_restart = True
        reason = f"hardware=None (squeezed out), stage={stage}"
    elif page_status == 503:
        needs_restart = True
        reason = f"page=503, stage={stage}"
    elif page_status == -1 and stage not in ("BUILDING", "APP_STARTING", "RUNNING_APP"):
        needs_restart = True
        reason = f"page=unreachable, stage={stage}"

    if needs_restart:
        print(f"  [ALERT] Space unhealthy: {reason}")
        print(f"  Triggering restart...")
        status, body = restart_space(HF_TOKEN)
        if status == 200:
            print(f"  [OK] Restart triggered (HTTP {status})")
        else:
            print(f"  [FAIL] Restart failed (HTTP {status}): {body}")
            try:
                r = requests.post(
                    f"{HF_API}/{REPO}/restart",
                    headers={"Authorization": f"Bearer {HF_TOKEN}"},
                    params={"factory": "true"},
                    timeout=15
                )
                print(f"  Factory reboot: HTTP {r.status_code}")
            except:
                pass
    else:
        print(f"  [OK] Space healthy (stage={stage}, page={page_status})")


if __name__ == "__main__":
    main()
