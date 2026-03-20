#!/usr/bin/env python3
"""One-shot Chromium startup diagnostics for the HDMI kiosk path."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: [%(filename)s:%(funcName)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DISPLAY = os.getenv("DISPLAY", ":0")
DEVTOOLS_HOST = os.getenv("CHROMIUM_DEVTOOLS_HOST", "127.0.0.1")
DEVTOOLS_PORT = os.getenv("CHROMIUM_DEVTOOLS_PORT", "9222")
SCREENSHOT_DIR = Path(os.getenv("HAOS_SCREENSHOT_DIR", "/media/screenshots"))
SNAPSHOT_DELAYS = (2, 5, 10, 15, 30)


def _run(cmd: list[str], *, timeout: int = 5) -> dict[str, Any]:
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return {"success": False, "error": str(exc)}
    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
    }


def _http_json(path: str) -> dict[str, Any]:
    url = f"http://{DEVTOOLS_HOST}:{DEVTOOLS_PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as exc:
        return {"success": False, "error": str(exc.reason), "url": url}
    except Exception as exc:  # pylint: disable=broad-except
        return {"success": False, "error": str(exc), "url": url}
    return {"success": True, "url": url, "payload": payload}


def _find_windows() -> list[str]:
    candidates = [
        ["xdotool", "search", "--onlyvisible", "--class", "chromium"],
        ["xdotool", "search", "--onlyvisible", "--class", "chromium-browser"],
        ["xdotool", "search", "--onlyvisible", "--name", "Chromium"],
    ]
    window_ids: list[str] = []
    seen: set[str] = set()
    for cmd in candidates:
        result = _run(cmd)
        if not result["success"]:
            continue
        for line in result["stdout"].splitlines():
            window_id = line.strip()
            if window_id and window_id not in seen:
                seen.add(window_id)
                window_ids.append(window_id)
    return window_ids


def _log_window_state() -> None:
    window_ids = _find_windows()
    if not window_ids:
        logger.info("X11 windows: none found for Chromium")
        return

    logger.info("X11 windows: found %d Chromium window(s)", len(window_ids))
    for window_id in window_ids[:3]:
        name = _run(["xdotool", "getwindowname", window_id])
        pid = _run(["xdotool", "getwindowpid", window_id])
        geometry = _run(["xdotool", "getwindowgeometry", "--shell", window_id])
        logger.info(
            "X11 window id=%s pid=%s name=%s geometry=%s",
            window_id,
            pid.get("stdout", ""),
            name.get("stdout", ""),
            geometry.get("stdout", "").replace("\n", " "),
        )


def _log_devtools_state() -> None:
    version = _http_json("/json/version")
    if version["success"]:
        payload = version["payload"]
        logger.info(
            "DevTools version: browser=%s protocol=%s ws=%s",
            payload.get("Browser", ""),
            payload.get("Protocol-Version", ""),
            payload.get("webSocketDebuggerUrl", ""),
        )
    else:
        logger.info("DevTools version probe failed: %s", version["error"])

    targets = _http_json("/json/list")
    if targets["success"]:
        payload = targets["payload"]
        urls = [
            str(item.get("url", ""))
            for item in payload
            if isinstance(item, dict) and item.get("type") == "page"
        ]
        logger.info("DevTools targets: count=%d urls=%s", len(urls), urls)
    else:
        logger.info("DevTools target probe failed: %s", targets["error"])


def _log_display_state() -> None:
    xset_result = _run(["xset", "-q"])
    if xset_result["success"]:
        state = "unknown"
        if "Monitor is On" in xset_result["stdout"]:
            state = "on"
        elif "Monitor is Off" in xset_result["stdout"]:
            state = "off"
        logger.info("xset state: monitor=%s", state)
    else:
        logger.info("xset probe failed: %s", xset_result.get("stderr") or xset_result.get("error"))

    xrandr_result = _run(["xrandr", "--listactivemonitors"])
    if xrandr_result["success"]:
        logger.info("xrandr active monitors: %s", xrandr_result["stdout"].replace("\n", " | "))
    else:
        logger.info("xrandr probe failed: %s", xrandr_result.get("stderr") or xrandr_result.get("error"))


def _log_process_state() -> None:
    pgrep_result = _run(["pgrep", "-af", "chromium"])
    if pgrep_result["success"]:
        logger.info("Chromium processes: %s", pgrep_result["stdout"].replace("\n", " | "))
    else:
        logger.info("Chromium process probe failed: %s", pgrep_result.get("stderr") or pgrep_result.get("error"))


def _take_screenshot() -> None:
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # pylint: disable=broad-except
        logger.info("Screenshot directory setup failed: %s", exc)
        return

    filename = SCREENSHOT_DIR / f"haoskiosk-startup-diag-{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    result = _run(["scrot", str(filename), "-q", "90"], timeout=10)
    if result["success"]:
        logger.info("Startup screenshot saved: %s", filename)
    else:
        logger.info("Startup screenshot failed: %s", result.get("stderr") or result.get("error"))


def main() -> None:
    logger.info(
        "Chromium startup diagnostics enabled: display=%s devtools=%s:%s",
        DISPLAY,
        DEVTOOLS_HOST,
        DEVTOOLS_PORT,
    )
    start = time.monotonic()
    last_mark = 0
    screenshot_done = False

    for mark in SNAPSHOT_DELAYS:
        time.sleep(max(0, mark - last_mark))
        elapsed = int(time.monotonic() - start)
        logger.info("Startup snapshot +%ss", elapsed)
        _log_process_state()
        _log_display_state()
        _log_devtools_state()
        _log_window_state()
        if not screenshot_done and elapsed >= 15:
            _take_screenshot()
            screenshot_done = True
        last_mark = mark


if __name__ == "__main__":
    main()
