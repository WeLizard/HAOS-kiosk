# Chromium Migration Notes

Current direction for this fork:

- Keep `Xorg + Openbox + REST/touch` from the existing add-on.
- Replace `Luakit` as the primary browser runtime with `Chromium`.
- Preserve `launch_url`, `refresh_browser`, `back`, `forward`, and display power control.
- Keep `luakit` only as a temporary fallback engine until Chromium is fully validated on target hardware.

What changed in this pass:

- Added `browser_engine` option to `config.yaml` with `chromium` as the primary target.
- Added `browser_ctl.py`:
  - `luakit` mode keeps legacy `xdotool` / `luakit -n`
  - `chromium` mode uses local DevTools instead of synthetic keystrokes
- Added `chromium_watchdog.py` for HA-specific browser behavior:
  - HA login form automation
  - browser_mod id injection
  - HA sidebar and theme localStorage setup
  - timed browser reloads
- Updated `run.sh` so Chromium can be launched with persistent profile and DevTools enabled.
- Switched default Chromium GL launch path to `--use-gl=angle --use-angle=default`
  because the target HAOS hardware advertises `egl-angle` as the allowed
  implementation while `--use-gl=egl` caused the GPU process to exit during
  startup.

Known remaining gaps:

- Chromium restart-on-consecutive-load-failure is not implemented yet.
- README still documents Luakit-first behavior and needs a Chromium pass.
- Multi-window DevTools target selection is still "first page target wins".
- We still need on-device validation for:
  - WebGL on the real HAOS hardware
  - emoji rendering with the added font packages
  - kiosk input gestures under Chromium

Target end-state:

- Remove Luakit entirely.
- Keep Chromium as the only browser engine.
- Move all browser control to DevTools/API-driven actions instead of xdotool where possible.
