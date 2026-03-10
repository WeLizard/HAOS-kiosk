#!/usr/bin/env python3
"""Browser control helpers for HAOS Kiosk.

Provides a single control surface for both Luakit and Chromium. Luakit keeps the
legacy xdotool/`luakit -n` behaviour. Chromium uses the local DevTools protocol
so navigation and reload actions work on the active page target without UI
keystroke emulation.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import ClientSession, ClientTimeout, WSMsgType  # type: ignore[import-not-found]


BROWSER_ENGINE = (os.getenv("BROWSER_ENGINE") or "chromium").strip().lower()
CHROMIUM_DEVTOOLS_PORT = int(os.getenv("CHROMIUM_DEVTOOLS_PORT", "9222"))
CHROMIUM_DEVTOOLS_HOST = os.getenv("CHROMIUM_DEVTOOLS_HOST", "127.0.0.1")
CLIENT_TIMEOUT = ClientTimeout(total=5)

VALID_URL_REGEX = re.compile(
    r"^(https?://)?"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}(?:\.\d{1,3}){3})"
    r"(?::\d{1,5})?"
    r"(?:/?|[/?][^\s]*)?$",
    re.IGNORECASE,
)

def compose_target_url(ha_url: str | None, ha_dashboard: str | None) -> str:
    """Compose the default launch URL from HA base URL and dashboard option."""
    base_url = (ha_url or "about:blank").strip()
    dashboard = (ha_dashboard or "").strip()
    if dashboard.startswith(("http://", "https://")):
        return dashboard
    if not dashboard:
        return base_url or "about:blank"
    return f"{base_url.rstrip('/')}/{dashboard.lstrip('/')}"


DEFAULT_LAUNCH_URL = (
    os.getenv("HA_TARGET_URL")
    or compose_target_url(os.getenv("HA_URL"), os.getenv("HA_DASHBOARD"))
    or "about:blank"
)
BROWSER_STATE_DIR = os.getenv("BROWSER_STATE_DIR", "/run/haos-kiosk")
BROWSER_STATE_FILE = os.path.join(BROWSER_STATE_DIR, "browser_state.json")
DISPLAY_SLEEP_URL = (os.getenv("DISPLAY_SLEEP_URL") or "about:blank").strip() or "about:blank"


def is_valid_url(url: str) -> bool:
    """Validate URL format (allows http://, https://, bare domain/IP, path, query, fragment)."""
    return bool(url == "about:blank" or VALID_URL_REGEX.fullmatch(url.strip()))


def normalize_url(url: str | None) -> str:
    """Return a browser-safe URL."""
    candidate = (url or DEFAULT_LAUNCH_URL or "about:blank").strip()
    if not candidate:
        candidate = DEFAULT_LAUNCH_URL or "about:blank"
    if candidate != "about:blank" and not candidate.startswith(("http://", "https://")):
        candidate = "http://" + candidate
    if not is_valid_url(candidate):
        raise ValueError(f"Invalid URL format: {candidate}")
    return candidate


def get_sleep_url() -> str:
    """Return the URL used while the display is sleeping."""
    return normalize_url(DISPLAY_SLEEP_URL)


def load_browser_state() -> dict[str, Any]:
    """Return persisted browser runtime state."""
    try:
        with open(BROWSER_STATE_FILE, encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_browser_state(state: dict[str, Any]) -> dict[str, Any]:
    """Persist browser runtime state atomically."""
    os.makedirs(BROWSER_STATE_DIR, exist_ok=True)
    payload = dict(state)
    payload["updated_at"] = int(time.time())
    temp_path = BROWSER_STATE_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
    os.replace(temp_path, BROWSER_STATE_FILE)
    return payload


def update_browser_state(**changes: Any) -> dict[str, Any]:
    """Merge state updates into persisted browser runtime state."""
    state = load_browser_state()
    state.update(changes)
    return save_browser_state(state)


def is_browser_sleeping() -> bool:
    """Return True when browser work should stay suspended."""
    return bool(load_browser_state().get("display_sleeping"))


def get_saved_browser_url(fallback: str | None = None) -> str:
    """Return the last active browser URL, falling back to the configured default."""
    state = load_browser_state()
    candidate = state.get("saved_url")
    if isinstance(candidate, str) and candidate.strip():
        return normalize_url(candidate)
    return normalize_url(fallback or DEFAULT_LAUNCH_URL)


def remember_active_url(url: str) -> dict[str, Any]:
    """Persist the currently active URL as the next wake target."""
    normalized = normalize_url(url)
    return update_browser_state(
        current_url=normalized,
        saved_url=normalized,
        display_sleeping=False,
    )


def _run_luakit_command(args: list[str]) -> None:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(stderr or f"Command failed with exit={result.returncode}: {args}")


class ChromiumPageSession:
    """Small CDP client bound to a single page target."""

    def __init__(self, websocket: Any) -> None:
        self._websocket = websocket
        self._next_id = 0

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a single CDP command and wait for the matching response."""
        self._next_id += 1
        command_id = self._next_id
        await self._websocket.send_json(
            {"id": command_id, "method": method, "params": params or {}}
        )

        while True:
            message = await self._websocket.receive()
            if message.type is WSMsgType.TEXT:
                payload = json.loads(message.data)
                if payload.get("id") != command_id:
                    continue
                if "error" in payload:
                    error = payload["error"]
                    raise RuntimeError(
                        f"CDP {method} failed: {error.get('message', error)}"
                    )
                return payload.get("result", {})
            if message.type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                raise RuntimeError(f"DevTools websocket closed while calling {method}")


class ChromiumController:
    """One-shot Chromium DevTools controller."""

    def __init__(
        self,
        *,
        host: str = CHROMIUM_DEVTOOLS_HOST,
        port: int = CHROMIUM_DEVTOOLS_PORT,
    ) -> None:
        self._json_list_url = f"http://{host}:{port}/json/list"
        self._timeout = CLIENT_TIMEOUT

    async def list_targets(self) -> list[dict[str, Any]]:
        """Return the current DevTools targets."""
        async with ClientSession(timeout=self._timeout) as session:
            async with session.get(self._json_list_url) as response:
                response.raise_for_status()
                targets = await response.json()
        if not isinstance(targets, list):
            raise RuntimeError("DevTools /json/list returned unexpected payload")
        return [target for target in targets if isinstance(target, dict)]

    async def get_page_target(self) -> dict[str, Any]:
        """Return the best current page target."""
        targets = await self.list_targets()
        page_targets = [
            target
            for target in targets
            if target.get("type") == "page" and target.get("webSocketDebuggerUrl")
        ]
        if not page_targets:
            raise RuntimeError("No Chromium page target found")
        page_targets.sort(
            key=lambda target: (
                target.get("url") in {"", "about:blank"},
                target.get("id", ""),
            )
        )
        return page_targets[0]

    async def _with_page(
        self,
        worker: Callable[[ChromiumPageSession, dict[str, Any]], Awaitable[Any]],
    ) -> Any:
        async with ClientSession(timeout=self._timeout) as session:
            async with session.get(self._json_list_url) as response:
                response.raise_for_status()
                targets = await response.json()
            if not isinstance(targets, list):
                raise RuntimeError("DevTools /json/list returned unexpected payload")
            page_targets = [
                target
                for target in targets
                if isinstance(target, dict)
                and target.get("type") == "page"
                and target.get("webSocketDebuggerUrl")
            ]
            if not page_targets:
                raise RuntimeError("No Chromium page target found")
            page_targets.sort(
                key=lambda target: (
                    target.get("url") in {"", "about:blank"},
                    target.get("id", ""),
                )
            )
            target = page_targets[0]
            async with session.ws_connect(
                target["webSocketDebuggerUrl"], heartbeat=10
            ) as websocket:
                page = ChromiumPageSession(websocket)
                await page.call("Page.enable")
                await page.call("Runtime.enable")
                return await worker(page, target)

    async def navigate(self, url: str) -> dict[str, Any]:
        """Navigate active page to the provided URL."""
        normalized = normalize_url(url)

        async def worker(page: ChromiumPageSession, _: dict[str, Any]) -> dict[str, Any]:
            return await page.call("Page.navigate", {"url": normalized})

        return await self._with_page(worker)

    async def reload(self, *, ignore_cache: bool = False) -> dict[str, Any]:
        """Reload the active page."""

        async def worker(page: ChromiumPageSession, _: dict[str, Any]) -> dict[str, Any]:
            return await page.call("Page.reload", {"ignoreCache": ignore_cache})

        return await self._with_page(worker)

    async def go_back(self) -> dict[str, Any]:
        """Move one step back in navigation history."""

        async def worker(page: ChromiumPageSession, _: dict[str, Any]) -> dict[str, Any]:
            history = await page.call("Page.getNavigationHistory")
            current_index = int(history.get("currentIndex", 0))
            entries = history.get("entries", [])
            if current_index <= 0 or not isinstance(entries, list):
                raise RuntimeError("No previous history entry")
            entry_id = entries[current_index - 1]["id"]
            return await page.call("Page.navigateToHistoryEntry", {"entryId": entry_id})

        return await self._with_page(worker)

    async def go_forward(self) -> dict[str, Any]:
        """Move one step forward in navigation history."""

        async def worker(page: ChromiumPageSession, _: dict[str, Any]) -> dict[str, Any]:
            history = await page.call("Page.getNavigationHistory")
            current_index = int(history.get("currentIndex", 0))
            entries = history.get("entries", [])
            if not isinstance(entries, list) or current_index >= len(entries) - 1:
                raise RuntimeError("No forward history entry")
            entry_id = entries[current_index + 1]["id"]
            return await page.call("Page.navigateToHistoryEntry", {"entryId": entry_id})

        return await self._with_page(worker)

    async def evaluate(
        self,
        expression: str,
        *,
        await_promise: bool = False,
        return_by_value: bool = True,
    ) -> dict[str, Any]:
        """Evaluate JavaScript on the active page."""

        async def worker(page: ChromiumPageSession, _: dict[str, Any]) -> dict[str, Any]:
            return await page.call(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "awaitPromise": await_promise,
                    "returnByValue": return_by_value,
                },
            )

        return await self._with_page(worker)

    async def sleep(self, *, sleep_url: str | None = None) -> dict[str, Any]:
        """Navigate Chromium to a cheap sleep URL and persist the wake target."""
        normalized_sleep_url = normalize_url(sleep_url or get_sleep_url())
        target = await self.get_page_target()
        current_url = str(target.get("url") or "")
        state = load_browser_state()

        saved_url = state.get("saved_url")
        if current_url and current_url not in {"about:blank", normalized_sleep_url}:
            saved_url = normalize_url(current_url)
        if not isinstance(saved_url, str) or not saved_url.strip():
            saved_url = normalize_url(DEFAULT_LAUNCH_URL)

        update_browser_state(
            current_url=normalized_sleep_url,
            saved_url=saved_url,
            display_sleeping=True,
        )

        if current_url == normalized_sleep_url:
            return {
                "success": True,
                "sleeping": True,
                "already_sleeping": True,
                "saved_url": saved_url,
                "sleep_url": normalized_sleep_url,
            }

        result = await self.navigate(normalized_sleep_url)
        return {
            "success": True,
            "sleeping": True,
            "saved_url": saved_url,
            "sleep_url": normalized_sleep_url,
            "result": result,
        }

    async def wake(self, *, target_url: str | None = None) -> dict[str, Any]:
        """Restore Chromium from the sleep URL back to the last active URL."""
        normalized_target_url = normalize_url(target_url or get_saved_browser_url(DEFAULT_LAUNCH_URL))
        target = await self.get_page_target()
        current_url = str(target.get("url") or "")

        update_browser_state(
            current_url=normalized_target_url,
            saved_url=normalized_target_url,
            display_sleeping=False,
        )

        if current_url == normalized_target_url:
            return {
                "success": True,
                "sleeping": False,
                "already_awake": True,
                "url": normalized_target_url,
            }

        result = await self.navigate(normalized_target_url)
        return {
            "success": True,
            "sleeping": False,
            "url": normalized_target_url,
            "result": result,
        }


async def run_browser_action(action: str, url: str | None = None) -> dict[str, Any]:
    """Dispatch browser control action based on configured engine."""
    if BROWSER_ENGINE == "luakit":
        normalized = normalize_url(url) if action == "launch_url" else None
        if action == "launch_url":
            _run_luakit_command(["luakit", "-n", normalized or DEFAULT_LAUNCH_URL])
        elif action == "refresh_browser":
            _run_luakit_command(["xdotool", "key", "--clearmodifiers", "ctrl+r"])
        elif action == "back":
            _run_luakit_command(["xdotool", "key", "--clearmodifiers", "ctrl+Left"])
        elif action == "forward":
            _run_luakit_command(["xdotool", "key", "--clearmodifiers", "ctrl+Right"])
        else:
            raise RuntimeError(f"Unsupported luakit action: {action}")
        return {"success": True, "engine": "luakit", "action": action}

    controller = ChromiumController()
    if action == "launch_url":
        normalized = normalize_url(url or DEFAULT_LAUNCH_URL)
        if is_browser_sleeping():
            update_browser_state(saved_url=normalized)
            return {
                "success": True,
                "engine": "chromium",
                "action": action,
                "sleeping": True,
                "deferred": True,
                "url": normalized,
            }
        result = await controller.navigate(normalized)
        remember_active_url(normalized)
        return result
    if action == "refresh_browser":
        if is_browser_sleeping():
            return {"success": True, "sleeping": True, "skipped": True}
        return await controller.reload(ignore_cache=True)
    if action == "back":
        if is_browser_sleeping():
            return {"success": True, "sleeping": True, "skipped": True}
        return await controller.go_back()
    if action == "forward":
        if is_browser_sleeping():
            return {"success": True, "sleeping": True, "skipped": True}
        return await controller.go_forward()
    if action == "page_info":
        return await controller.get_page_target()
    if action == "sleep_display":
        return await controller.sleep()
    if action == "wake_display":
        return await controller.wake(target_url=url)
    raise RuntimeError(f"Unknown browser action: {action}")


async def _main_async(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: browser_ctl.py <launch_url|refresh_browser|back|forward|page_info|sleep_display|wake_display> [url]",
            file=sys.stderr,
        )
        return 2

    action = argv[1].strip().lower()
    url = argv[2] if len(argv) > 2 else None
    try:
        result = await run_browser_action(action, url)
    except Exception as exc:  # pylint: disable=broad-except
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


def main() -> int:
    """CLI entrypoint."""
    return asyncio.run(_main_async(sys.argv))


if __name__ == "__main__":
    raise SystemExit(main())
