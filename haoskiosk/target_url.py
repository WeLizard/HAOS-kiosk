#!/usr/bin/env python3
"""Shared helpers for kiosk display target URL resolution."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urljoin


HOST_LIKE_URL_RE = re.compile(
    r"^(?:"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}(?:\.\d{1,3}){3}"
    r")"
    r"(?::\d{1,5})?"
    r"(?:/?|[/?#][^\s]*)?$",
    re.IGNORECASE,
)

VALID_URL_REGEX = re.compile(
    r"^(https?://)?"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}(?:\.\d{1,3}){3})"
    r"(?::\d{1,5})?"
    r"(?:/?|[/?#][^\s]*)?$",
    re.IGNORECASE,
)


def compose_target_url(ha_url: str | None, ha_dashboard: str | None) -> str:
    """Compose the configured kiosk target URL.

    `ha_dashboard` may be:
    - empty -> use `ha_url`
    - a full absolute URL -> use as-is
    - `about:blank`
    - a host-like value (`localhost:48123/scene/`) -> returned as-is for later normalization
    - a path relative to `ha_url`
    """

    base_url = (ha_url or "about:blank").strip() or "about:blank"
    dashboard = (ha_dashboard or "").strip()
    if not dashboard:
        return base_url
    if dashboard == "about:blank" or dashboard.startswith(("http://", "https://")):
        return dashboard
    if HOST_LIKE_URL_RE.fullmatch(dashboard):
        return dashboard
    if base_url == "about:blank":
        return dashboard
    return urljoin(base_url.rstrip("/") + "/", dashboard)


def is_valid_url(url: str) -> bool:
    """Validate a URL or host-like browser target."""
    return bool(url == "about:blank" or VALID_URL_REGEX.fullmatch(url.strip()))


def normalize_url(url: str | None, fallback: str | None = None) -> str:
    """Return a browser-safe URL with scheme when needed."""
    candidate = (url or fallback or "about:blank").strip()
    if not candidate:
        candidate = (fallback or "about:blank").strip() or "about:blank"
    if candidate != "about:blank" and not candidate.startswith(("http://", "https://")):
        candidate = "http://" + candidate
    if not is_valid_url(candidate):
        raise ValueError(f"Invalid URL format: {candidate}")
    return candidate


def resolve_default_launch_url() -> str:
    """Resolve the configured default launch URL from environment."""
    candidate = (
        (os.getenv("HA_TARGET_URL") or "").strip()
        or compose_target_url(os.getenv("HA_URL"), os.getenv("HA_DASHBOARD"))
        or "about:blank"
    )
    return normalize_url(candidate, "about:blank")


def main(argv: list[str] | None = None) -> int:
    """CLI for shell scripts inside the add-on image."""
    args = argv or sys.argv[1:]
    if not args or args[0] == "default":
        print(resolve_default_launch_url())
        return 0

    command = args[0]
    if command == "compose":
        print(compose_target_url(args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else None))
        return 0
    if command == "normalize":
        print(normalize_url(args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else None))
        return 0

    print(
        "Usage: target_url.py [default|compose <ha_url> <ha_dashboard>|normalize <url> [fallback]]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
