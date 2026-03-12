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

## Upstream vs Welizard Fork Findings (March 12, 2026)

After comparing `upstream/main` with the Welizard fork and reviewing the
official Chromium/ANGLE docs, the main lessons are:

- The fork started from a reasonable split: keep `Xorg + Openbox + touch + REST`
  and swap the browser engine from `luakit` to `chromium`.
- The first Chromium commit (`7b1fd4a`) already forced a risky GPU profile on
  Alpine Chromium:
  - `--enable-gpu-rasterization`
  - `--ignore-gpu-blocklist`
  - `--use-gl=egl`
- Later commits layered more backend forcing (`ANGLE`, `swiftshader`,
  compositor overrides, `full_access`) and turned GPU debugging knobs into the
  default runtime path.
- Official Chromium guidance treats these switches as backend/debug controls,
  not as a stable "always-on" production profile. In particular:
  - `--ignore-gpu-blocklist` explicitly bypasses Chromium's own safety checks
  - SwiftShader WebGL fallback requires explicit unsafe opt-in and is no longer
    something Chromium wants enabled implicitly
  - ANGLE backends should be selected intentionally for debugging/porting, not
    blindly forced on every box
- Rebuild drift matters here: the Dockerfile installs `chromium` without a
  pinned package version, so "same code" can end up running a different browser
  build after a later add-on rebuild.

## Current Safe Direction

- Keep the Chromium fork minimal on top of upstream:
  - browser engine selector
  - Chromium DevTools watchdog/control
  - touch support
  - absolute target URL support
- Keep the default Chromium launch profile close to a normal X11 kiosk browser:
  - `--ozone-platform=x11`
  - `--touch-events=enabled`
  - no forced GL backend
  - no forced GPU rasterization
  - no forced GPU blocklist bypass
- Treat any GL/ANGLE/SwiftShader override as explicit troubleshooting, not the
  normal user path.
- Log the exact Chromium version at startup so live behavior can be correlated
  with the actual browser build.
- Pin or otherwise control the Chromium package version before trusting any
  "it worked before" conclusion across rebuilds.
