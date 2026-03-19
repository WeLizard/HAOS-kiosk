#!/usr/bin/env python3
"""Chromium kiosk watchdog.

Handles the HA-specific browser behavior previously implemented in Luakit:
auto-login, persistent kiosk browser id, HA theme/sidebar storage, and timed
reloads. This keeps the Chromium runtime thin while preserving the HA-focused
workflow expected by the add-on.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any

from browser_ctl import ChromiumController


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: [%(filename)s:%(funcName)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

HA_URL = (os.getenv("HA_URL") or "http://localhost:8123").rstrip("/")
HA_URL_BASE = re.match(r"^(https?://[%w%.%-]+(?::\d+)?)", HA_URL)
HA_URL_BASE = HA_URL_BASE.group(1).rstrip("/") if HA_URL_BASE else HA_URL
HA_USERNAME = os.getenv("HA_USERNAME") or ""
HA_PASSWORD = os.getenv("HA_PASSWORD") or ""
RAW_AUTO_LOGIN = (os.getenv("HA_AUTO_LOGIN") or "").strip().lower()
if RAW_AUTO_LOGIN in {"1", "true", "yes", "on"}:
    HA_AUTO_LOGIN = True
elif RAW_AUTO_LOGIN in {"0", "false", "no", "off"}:
    HA_AUTO_LOGIN = False
else:
    HA_AUTO_LOGIN = bool(HA_USERNAME and HA_PASSWORD)
LOGIN_DELAY_MS = int(float(os.getenv("LOGIN_DELAY") or "1") * 1000)
BROWSER_REFRESH = max(0, int(os.getenv("BROWSER_REFRESH") or "0"))
DARK_MODE = (os.getenv("DARK_MODE") or "true").strip().lower() == "true"
RAW_SIDEBAR = (os.getenv("HA_SIDEBAR") or "").strip().lower()
RAW_THEME = (os.getenv("HA_THEME") or "").strip()
POLL_INTERVAL = 5.0
POLL_INTERVAL_IDLE = 15.0
POLL_INTERVAL_DISPLAY_OFF = 30.0  # slower when display off, but keep Chromium alive
HARD_RELOAD_FREQ = 10
DISPLAY_STATE_FILE = "/tmp/haoskiosk-display-state"

SIDEBAR_MAP = {
    "full": "",
    "none": '"always_hidden"',
    "narrow": '"auto"',
    "": "",
}


def normalize_sidebar(raw_sidebar: str) -> str:
    """Return the HA localStorage representation for dockedSidebar."""
    return SIDEBAR_MAP.get(raw_sidebar, "")


def normalize_theme(raw_theme: str, dark_mode: bool) -> str:
    """Return the HA localStorage representation for selectedTheme."""
    theme = raw_theme.strip()
    if theme in {"", "{}", "Home Assistant"}:
        return '{"dark":true}' if dark_mode else '{"dark":false}'
    if theme[0] not in {'"', "'", "{"}:
        return json.dumps(theme)
    return theme


def build_auto_login_script() -> str:
    """Return JS that fills HA auth fields and submits the form."""
    return f"""
(() => {{
  const username = {json.dumps(HA_USERNAME)};
  const password = {json.dumps(HA_PASSWORD)};
  const delayMs = {LOGIN_DELAY_MS};
  window.setTimeout(() => {{
    try {{
      const usernameField = document.querySelector('input[autocomplete="username"]');
      const passwordField = document.querySelector('input[autocomplete="current-password"]');
      const checkbox = document.querySelector('ha-checkbox');
      const submitButton = document.querySelector('ha-button, mwc-button');
      if (!usernameField || !passwordField || !submitButton) {{
        return {{ ok: false, reason: 'missing-elements' }};
      }}
      usernameField.value = username;
      usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
      passwordField.value = password;
      passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
      if (checkbox) {{
        checkbox.setAttribute('checked', '');
        checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }}
      submitButton.click();
      return {{ ok: true }};
    }} catch (error) {{
      return {{ ok: false, reason: String(error) }};
    }}
  }}, delayMs);
}})();
"""


def build_settings_script(sidebar: str, theme: str) -> str:
    """Return JS that applies HA localStorage settings."""
    return f"""
(() => {{
  try {{
    let changed = false;
    localStorage.setItem('browser_mod-browser-id', 'haos_kiosk');

    const sidebar = {json.dumps(sidebar)};
    const currentSidebar = localStorage.getItem('dockedSidebar') || '';
    if (sidebar !== currentSidebar) {{
      if (sidebar) {{
        localStorage.setItem('dockedSidebar', sidebar);
      }} else {{
        localStorage.removeItem('dockedSidebar');
      }}
      changed = true;
    }}

    const theme = {json.dumps(theme)};
    const currentTheme = localStorage.getItem('selectedTheme') || '';
    if (theme !== currentTheme) {{
      if (theme) {{
        localStorage.setItem('selectedTheme', theme);
      }} else {{
        localStorage.removeItem('selectedTheme');
      }}
      changed = true;
    }}

    return {{
      ok: true,
      changed,
      sidebar: localStorage.getItem('dockedSidebar') || '',
      theme: localStorage.getItem('selectedTheme') || '',
    }};
  }} catch (error) {{
    return {{ ok: false, changed: false, error: String(error) }};
  }}
}})();
"""


WEBGL_DIAG_SCRIPT = """
(() => {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
    const webgl = !!gl;
    let renderer = 'none';
    let vendor = 'none';
    if (gl) {
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      if (ext) {
        renderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || 'unknown';
        vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) || 'unknown';
      }
    }
    // Try to reach into the avatar iframe for Live2D state
    let avatarState = null;
    try {
      const iframes = document.querySelectorAll('iframe');
      for (const iframe of iframes) {
        const src = iframe.src || '';
        if (src.includes('avatar')) {
          const doc = iframe.contentDocument || (iframe.contentWindow && iframe.contentWindow.document);
          if (doc) {
            const liveCanvas = doc.querySelector('canvas');
            const fallback = doc.getElementById('fallback-portrait');
            const frame = doc.getElementById('frame');
            const status = doc.getElementById('status');
            avatarState = {
              iframeSrc: src.substring(0, 120),
              hasLiveCanvas: !!liveCanvas,
              canvasSize: liveCanvas ? liveCanvas.width + 'x' + liveCanvas.height : 'none',
              fallbackHidden: fallback ? fallback.classList.contains('hidden') : null,
              frameReady: frame ? frame.classList.contains('is-ready') : null,
              statusText: status ? status.textContent : null,
              bodyLoading: doc.body ? doc.body.classList.contains('is-loading') : null,
            };
            break;
          }
        }
      }
      if (!avatarState) {
        // List all iframes for debugging
        avatarState = {
          iframeCount: iframes.length,
          iframeSrcs: Array.from(iframes).map(f => (f.src || '').substring(0, 100)),
        };
      }
    } catch (iframeErr) {
      avatarState = { iframeError: String(iframeErr) };
    }
    // Also check main document for avatar elements (non-iframe case)
    const mainCanvas = document.querySelector('canvas');
    const mainFallback = document.getElementById('fallback-portrait');
    const mainFrame = document.getElementById('frame');
    const mainStatus = document.getElementById('status');
    return {
      webgl,
      renderer,
      vendor,
      mainDoc: {
        hasCanvas: !!mainCanvas,
        fallbackHidden: mainFallback ? mainFallback.classList.contains('hidden') : null,
        frameReady: mainFrame ? mainFrame.classList.contains('is-ready') : null,
        statusText: mainStatus ? mainStatus.textContent : null,
      },
      avatar: avatarState,
    };
  } catch (e) {
    return { error: String(e) };
  }
})();
"""


def is_auth_page(url: str) -> bool:
    """Return True if URL looks like HA auth page."""
    return bool(re.match(rf"^{re.escape(HA_URL_BASE)}/auth/authorize\?response_type=code", url))


def is_ha_page(url: str) -> bool:
    """Return True if URL belongs to the current HA instance."""
    return bool(url and (url + "/").startswith(HA_URL_BASE + "/"))



def is_display_off() -> bool:
    """Check if display is off by reading the state file written by rest_server."""
    try:
        with open(DISPLAY_STATE_FILE) as f:
            return f.read().strip() == "off"
    except (FileNotFoundError, OSError):
        return False


def extract_evaluate_value(result: dict[str, Any]) -> Any:
    """Unwrap Runtime.evaluate returnByValue payload."""
    runtime_result = result.get("result")
    if isinstance(runtime_result, dict) and "value" in runtime_result:
        return runtime_result["value"]
    return runtime_result


async def main() -> None:
    """Start watchdog loop."""
    controller = ChromiumController()
    sidebar = normalize_sidebar(RAW_SIDEBAR)
    theme = normalize_theme(RAW_THEME, DARK_MODE)
    auto_login_script = build_auto_login_script()
    settings_script = build_settings_script(sidebar, theme)

    logger.info(
        "Chromium watchdog started: HA_URL=%s LOGIN_DELAY=%.1fs REFRESH=%ss SIDEBAR=%s THEME=%s AUTO_LOGIN=%s",
        HA_URL,
        LOGIN_DELAY_MS / 1000,
        BROWSER_REFRESH,
        sidebar,
        theme,
        HA_AUTO_LOGIN,
    )

    last_url = ""
    last_auth_url = ""
    last_settings_url = ""
    last_reload_at = time.monotonic()
    reload_count = 0
    webgl_diagnosed = False
    stable_ticks = 0  # counts consecutive ticks with no URL change or action

    while True:
        try:
            target = await controller.get_page_target()
            url = str(target.get("url") or "")
            action_taken = False

            if url and url != last_url:
                logger.info("URL: %s", url)
                last_url = url
                stable_ticks = 0
                action_taken = True

            if HA_AUTO_LOGIN and url and is_auth_page(url) and url != last_auth_url:
                await controller.evaluate(auto_login_script)
                last_auth_url = url
                logger.info("Triggered HA auto-login for %s", url)
                action_taken = True

            if url and is_ha_page(url) and not is_auth_page(url) and url != last_settings_url:
                result = extract_evaluate_value(await controller.evaluate(settings_script))
                if isinstance(result, dict) and result.get("ok"):
                    logger.info(
                        "Applied HA settings: sidebar=%s theme=%s changed=%s",
                        result.get("sidebar"),
                        result.get("theme"),
                        result.get("changed"),
                    )
                    if result.get("changed"):
                        await controller.reload(ignore_cache=False)
                        last_reload_at = time.monotonic()
                        logger.info("Reloaded page to apply updated HA localStorage")
                else:
                    logger.warning("Failed to apply HA settings: %s", result)
                last_settings_url = url
                action_taken = True

            # One-time WebGL diagnostic after scene-runtime loads
            if not webgl_diagnosed and url and "scene-runtime" in url:
                await asyncio.sleep(12)  # give Live2D time to init
                try:
                    diag = extract_evaluate_value(await controller.evaluate(WEBGL_DIAG_SCRIPT))
                    logger.info("WebGL diagnostic: %s", json.dumps(diag, ensure_ascii=False))
                except Exception as diag_exc:
                    logger.warning("WebGL diagnostic failed: %s", diag_exc)
                webgl_diagnosed = True

            if BROWSER_REFRESH > 0 and url and url != "about:blank":
                now = time.monotonic()
                if now - last_reload_at >= BROWSER_REFRESH:
                    reload_count += 1
                    ignore_cache = reload_count % HARD_RELOAD_FREQ == 0
                    await controller.reload(ignore_cache=ignore_cache)
                    last_reload_at = now
                    logger.info("Reloading%s: %s", " [HARD]" if ignore_cache else "", url)
                    action_taken = True

            if not action_taken:
                stable_ticks += 1

        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Watchdog loop error: %s", exc)
            stable_ticks = 0

        # Adaptive polling: fast during setup, slow when idle, slowest when display off
        if is_display_off():
            interval = POLL_INTERVAL_DISPLAY_OFF
        elif stable_ticks < 6:
            interval = POLL_INTERVAL
        else:
            interval = POLL_INTERVAL_IDLE
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
