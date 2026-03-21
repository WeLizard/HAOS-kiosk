# Changelog

## v1.3.2-welizard.91 - March 2026

- **Switch to Debian Bookworm (glibc) base image.**
  Alpine's musl libc is fundamentally incompatible with Chromium 146's
  WebGL/WASM renderer — the renderer process crashes with SIGILL on
  any page using WebAssembly (e.g. Live2D Cubism Core) or complex
  WebGL shaders. No combination of Chromium flags fixes this.
  Debian/glibc eliminates the issue entirely.
- Clean Chromium flags — no GL overrides, no WASM workarounds.
- Debian compatibility: auto-detect udevd path, non-fatal tty0 hack,
  column command fallback.
- Clear GPU/shader caches on every addon restart.

## v1.3.2-welizard.88 - March 2026

- Keep the default Chromium launch path close to a normal X11 kiosk browser:
  remove the forced `--use-gl=angle --use-angle=swiftshader` +
  `--enable-unsafe-swiftshader` override from the main runtime path.
- Align `run.sh` fallback defaults with the current add-on config defaults:
  `browser_refresh=0`, `screen_timeout=0`, `onscreen_keyboard=true`.
- Track the launched Chromium PID directly instead of relying on a
  `chromium-browser` process-name grep that falsely expired after 10 seconds
  even while Chromium was still alive.

## v1.3.2-welizard.84 - March 2026

- **Clean restart from upstream.** Reset Dockerfile and run.sh to
  upstream puterboy/HAOS-kiosk baseline (Alpine, no build.yaml).
- Add Chromium + WebGL support with minimal additions:
  `chromium`, `chromium-swiftshader`, `mesa-vulkan-swrast`,
  `vulkan-loader`, `mesa-gl` — only software Vulkan (lavapipe),
  no hardware GPU drivers.
- Add `browser_engine` option (chromium/luakit, default: chromium).
- Chromium launched with minimal kiosk flags + `--enable-unsafe-swiftshader`
  + `--ignore-gpu-blocklist`. No forced GL/ANGLE backend — ANGLE
  auto-detects lavapipe for software WebGL.
- Make `ha_username`/`ha_password` optional (Chromium can use existing
  HA sessions without credentials).
- Support absolute URLs in `ha_dashboard` (e.g. `http://host:port/scene/`).

## v1.3.2-welizard.80 - March 2026

- **Switch base image from Alpine to Debian bookworm (glibc).**
  Alpine's musl libc causes Chromium renderer crashes (SIGILL) on
  WebGL/WASM workloads. Chromium is built and tested against glibc;
  Debian eliminates this entire class of bugs.
- Rewrite Dockerfile for Debian packages (`apt-get` instead of `apk`).
- Use Chromium 146 from Debian bookworm repos (glibc-compiled).
- `intel_hwaccel` profile: ANGLE + auto-detect backend with
  `--ignore-gpu-blocklist`. On Intel N150, ANGLE selects ANV (Intel
  Vulkan) for hardware-accelerated WebGL.
- `swiftshader_scene` profile: modernize to SwANGLE (`--use-angle=swiftshader`)
  for pure software WebGL fallback.
- Replace `pip install aiohttp` with `python3-aiohttp` Debian package.
- Limit arch to amd64 + aarch64 (Debian HA base images).

## v1.3.2-welizard.79 - March 2026

- (build failed — luakit version pin incompatible with Alpine 3.22 repos)

## v1.3.2-welizard.78 - March 2026

- Pin base image to Alpine 3.21 via `build.yaml`. HAOS 17.1 defaults
  to Alpine 3.23 which ships Chromium 146 — this version crashes the
  renderer with SIGILL on musl when any WebGL/WASM content runs.
  Alpine 3.21 ships Chromium 136 which was confirmed working in .53.
- Revert `intel_hwaccel` profile to clean auto/default (same as the
  working .53 `minimal` profile). Remove all Chromium 146-specific
  workarounds (Vulkan feature disable, Skia Graphite disable, etc.).

## v1.3.2-welizard.77 - March 2026

- Switch `intel_hwaccel` profile from ANGLE Vulkan (Intel ANV) to ANGLE
  SwiftShader. Chromium 146 on Alpine/musl crashes the renderer with
  SIGILL when any WebGL/WASM workload runs, regardless of GPU backend.
  The crash is in the renderer, not the GPU process. SwiftShader ANGLE
  is the proven working approach on Alpine (Grafana chromium-swiftshader-alpine).
  Requires `chromium-swiftshader` package (added in .75).
- Fix `--enable-unsafe-swiftshader` gate: accept both `swiftshader` and
  `swiftshader-webgl` ANGLE backends (was only `swiftshader-webgl`).
- Remove Intel ANV ICD forcing (VK_ICD_FILENAMES) — SwiftShader uses
  its own built-in Vulkan implementation.

## v1.3.2-welizard.76 - March 2026

- Remove invalid `--js-flags=--no-avx --no-avx2` (V8 does not recognize
  these flags). The SIGILL fix was from .73 profile changes (disable GPU
  rasterization, compositing, OOP rasterization), not V8 JIT.

## v1.3.2-welizard.75 - March 2026

- Fix renderer SIGILL: add `--js-flags=--no-avx --no-avx2` to
  `intel_hwaccel` profile. V8 JIT detects AVX2 on Intel N150 and emits
  instructions that crash under Alpine musl. Force SSE4.2 baseline.
- Add `chromium-swiftshader` package to Dockerfile. Chromium 137+ removed
  the automatic SwiftShader WebGL fallback — without this package the
  renderer has no software GL path and may crash on fallback init.

## v1.3.2-welizard.74 - March 2026

- Fix fallback defaults: `CHROMIUM_PROFILE` → `intel_hwaccel` (was
  `swiftshader_scene`), `SCREEN_TIMEOUT` → `0` (was `600`),
  `ONSCREEN_KEYBOARD` → `true` (was `false`). These now match
  `config.yaml` defaults.
- Fix `rest_bearer_token` translation key (was `rest_authorization_token`
  causing the option to not render in HA UI).
- Fix Lua-style regex `[%w%.%-]` in `chromium_watchdog.py` — replaced
  with proper Python regex `[\w.\-]`.
- Remove dead `CHROMIUM_ENABLE_WATCHDOG` variable (watchdog runs
  unconditionally since .69).
- Mark `SwiftShader Scene` profile as broken on Chromium 146 in UI.
- Update `chromium_profile` description: default is now Intel GPU.

## v1.3.2-welizard.73 - March 2026

- Disable GPU rasterization, GPU compositing, and OOP rasterization in
  `intel_hwaccel` profile. The renderer process on Alpine musl crashes
  with SIGILL when it uses GPU-accelerated Skia paths. Now only WebGL
  goes through the GPU process via ANGLE/Vulkan — all renderer-side
  compositing and rasterization stays in software.

## v1.3.2-welizard.72 - March 2026

- Fix SIGILL in renderer: `--enable-features=Vulkan` caused Skia compositor
  in the renderer process to initialize Vulkan directly on Alpine musl,
  triggering SIGILL. Removed Vulkan feature flag — ANGLE uses Vulkan via
  `--use-angle=vulkan` alone (GPU process only). Also disable Skia Graphite
  to prevent renderer-side Vulkan initialization.

## v1.3.2-welizard.71 - March 2026

- Add `intel_hwaccel` to translations so it appears in the HA UI dropdown.
- Change default profile from `swiftshader_scene` to `intel_hwaccel`.

## v1.3.2-welizard.70 - March 2026

- Add `intel_hwaccel` Chromium profile: hardware-accelerated WebGL via
  ANGLE Vulkan backend on Intel GPU (ANV driver). This replaces both
  the `swiftshader_scene` profile (broken on Chromium 146 — SwANGLE
  lacks VK_KHR_surface for windowed contexts) and `minimal` profile
  (SIGILL in iris GL JIT on Alpine musl).
- Add `mesa-vulkan-intel` to Dockerfile for Intel ANV Vulkan driver.
- `intel_hwaccel` profile auto-selects Intel Vulkan ICD via
  VK_ICD_FILENAMES, enables `Vulkan` + `VulkanFromANGLE` features,
  GPU rasterization, and ignores GPU blocklist.
- Add GPU diagnostics at startup: DRI render nodes, Vulkan ICDs
  installed, active VK_ICD_FILENAMES.

## v1.3.2-welizard.69 - March 2026

- Re-enable Chromium watchdog unconditionally. The watchdog monitors via
  DevTools and auto-reloads to the target URL when the renderer crashes
  (e.g. after display wake from DPMS sleep). Removes the CHROMIUM_ENABLE_WATCHDOG
  flag — watchdog now always runs alongside Chromium.

## v1.3.2-welizard.68 - March 2026

- Clear Chromium GPU/shader cache on startup for ALL profiles, not just
  `recovery_baseline`. Corrupted GPU cache from prior deep-sleep experiments
  (`e2f9af7`, `3895d2a`) persists in HA addon_config storage across updates
  and is a likely cause of the persistent black screen after the `.65` rollback.
- Restore `mesa-vulkan-swrast` + `vulkan-loader` in Dockerfile. These were
  added in `.53` to enable SwANGLE/Lavapipe WebGL but were lost during the
  `.65` revert to `.52` baseline.
- Fix DPMS handling when `screen_timeout: 0`: properly run `xset s off` +
  `xset -dpms` instead of enabling DPMS with zero timeouts.

## v1.3.2-welizard.67 - March 2026

- Add a narrow Chromium startup diagnostics pass for the real HDMI box.
- The add-on now logs timed snapshots of Chromium processes, X11 window
  discovery, `xset`/`xrandr` display state, and DevTools `/json/version` /
  `/json/list` availability during startup.
- Save one startup screenshot to `/media/screenshots` so the X server output
  can be compared with the physical black screen.

## v1.3.2-welizard.66 - March 2026

- Stop auto-starting `chromium_watchdog.py` in the main Chromium path for a
  narrow HDMI isolation pass.
- Chromium still launches directly to `HA_TARGET_URL`, but the add-on no longer
  depends on the DevTools watchdog loop during startup.
- This release exists only to answer one question cleanly on the real box:
  does the black-screen path remain when the watchdog is removed from startup?

## v1.3.2-welizard.65 - March 2026

- Roll back the add-on runtime files to the exact `.52` source baseline after
  later display-path lines regressed into black-screen behavior on the target
  HDMI box.
- Restore the `.52` Chromium defaults (`SwiftShader Scene`) and remove the
  post-`.52` wake/display experiments from the main user path.
- Keep this release intentionally narrow: runtime sources match `.52`; only
  the installable version/changelog metadata are newer so Home Assistant can
  pull the rollback as an update.

## v1.3.2-welizard.52 - March 2026

- Keep `SwiftShader Scene` as the default profile, but explicitly disable
  Chromium `Vulkan` and `Skia Graphite` for that profile.
- Live `.51` logs on the target HDMI box showed the scene loading while the
  avatar fell back after `ANGLE Display::initialize` failed on missing Vulkan
  extensions (`VK_KHR_surface`, `VK_KHR_xcb_surface`) and the GPU process
  exited during initialization.
- `.52` is a narrow follow-up to force the `.40`-style SwiftShader WebGL path
  away from the broken Vulkan route on Chromium 144 Alpine.

## v1.3.2-welizard.51 - March 2026

- Stop using `Recovery Baseline` as the default profile because it regressed
  the physical HDMI path back to a black screen on the current box.
- Add `SwiftShader Scene` as the new default Chromium profile.
- This reproduces the last confirmed HDMI-visible `.40` runtime:
  `UseSkiaRenderer` off, `--disable-gpu-compositing`,
  `--disable-oop-rasterization`, and Chromium's official
  `--use-gl=angle --use-angle=swiftshader-webgl --enable-unsafe-swiftshader`
  fallback for the avatar path.

## v1.3.2-welizard.50 - March 2026

- Add a `Recovery Baseline` Chromium profile and make it the default profile
  for the next HDMI verification pass.
- This restores the early `c6378e1` Chromium launcher behavior while keeping
  the current shared `target_url.py` path for direct `Kiosk Scene` URLs such
  as `localhost:48123/scene/`.
- Bring back the old Chromium runtime cache reset, seeded profile preferences,
  prompt suppression, and hard manual reload path for this profile only.

## v1.3.2-welizard.49 - March 2026

- Fix Chromium profile configuration so HA UI options are actually honored.
- `run.sh` had pre-initialized `CHROMIUM_PROFILE`, `CHROMIUM_USE_GL`, and
  `CHROMIUM_ANGLE_BACKEND` before reading add-on config, which forced the
  runtime back onto `legacy_neiri` even when the UI showed `desktop_glx`.

## v1.3.2-welizard.48 - March 2026

- Add a dedicated `Desktop GLX` Chromium profile and make it the default
  experiment for the HDMI path.
- This bypasses ANGLE entirely and forces Chromium onto native X11 desktop
  OpenGL (`--use-gl=desktop`) without the legacy GPU overrides.
- Keep `Legacy Neiri` intact so the last restored ANGLE+GL profile is still
  available for comparison.

## v1.3.2-welizard.47 - March 2026

- Restore `mesa-gl` in the add-on image. The last known working Chromium
  baseline (`c6378e1`) installed it, but the current image no longer did.
- Keep `.46` runtime flags unchanged; this is a pure build-layer follow-up to
  test the missing Mesa GL userspace on the HDMI Chromium path.

## v1.3.2-welizard.46 - March 2026

- Keep the `.45` `Legacy Neiri` ANGLE+GL profile, but explicitly disable
  Chromium's Vulkan feature path and `Skia Graphite` for that profile.
- This is a narrow follow-up to `.45`: same restored legacy launch profile,
  with only anti-Vulkan/anti-Graphite hardening added for the current
  `texStorage2D -> SharedImage -> GPU process exited` crash chain.

## v1.3.2-welizard.45 - March 2026

- Tighten the `Legacy Neiri` preset to use `ANGLE + OpenGL` explicitly
  instead of `ANGLE + default`.
- Keep the rest of the restored legacy launch profile unchanged so this
  remains a narrow GPU-path experiment.

## v1.3.2-welizard.44 - March 2026

- Add a single `Legacy Neiri` Chromium profile that restores the older
  hardcoded working launch flags without requiring manual toggle hunting.
- Keep `Minimal X11` and `Custom` profiles available for narrower HDMI
  debugging when the legacy profile is not desired.

## v1.3.2-welizard.43 - March 2026

- Add explicit advanced toggles for the two Chromium flags that were part of
  the older working Neiri profile:
  - `Enable GPU Rasterization`
  - `Ignore GPU Blocklist`
- Keep both off by default so `.43` stays on the clean `.42` baseline unless
  the old profile is deliberately reproduced from the HA UI.

## v1.3.2-welizard.42 - March 2026

- Expose Chromium graphics overrides in the add-on configuration instead of
  hardcoding them in `run.sh`.
- Added advanced settings for:
  - `Chromium GL Mode`
  - `Chromium ANGLE Backend`
  - `Disable Skia Renderer`
  - `Disable GPU Compositing`
  - `Disable OOP Rasterization`
  - `Enable Unsafe SwiftShader`
- Safe defaults remain on the minimal `.41` X11 Chromium profile. The new
  settings exist so HDMI experiments can be compared from HA UI without
  rewriting the add-on each time.

## v1.3.2-welizard.41 - March 2026

- Drop the `.40` `swiftshader-webgl` fallback and all temporary Chromium GPU
  overrides from the main display path.
- Run Chromium on the simplest X11 kiosk profile again:
  no `UseSkiaRenderer` disable, no `--disable-gpu-compositing`, no
  `--disable-oop-rasterization`, and no forced `ANGLE`/`SwiftShader` flags.
- This is the first clean verification step after confirming the scene itself
  already renders on HDMI and the remaining problem is the avatar WebGL path.

## v1.3.2-welizard.40 - March 2026

- Replace the temporary `.39` `--disable-webgl` phase with Chromium's official
  opt-in software WebGL fallback:
  `--use-gl=angle --use-angle=swiftshader-webgl --enable-unsafe-swiftshader`.
- Keep the host-only `.38` compositor guards (`UseSkiaRenderer` off,
  `--disable-gpu-compositing`, `--disable-oop-rasterization`) so the HDMI host
  path stays on the already-restored stable scene output while only the avatar
  WebGL path is pushed onto SwiftShader.

## v1.3.2-welizard.39 - March 2026

- Keep the `.38` host compositor fixes, but disable WebGL in Chromium with
  `--disable-webgl`.
- This is a deliberate phase-step: the HDMI host path now paints simple pages
  again, while `/scene/` still crashes specifically inside Chromium's WebGL
  path (`GL_INVALID_FRAMEBUFFER_OPERATION`, `GL_CONTEXT_LOST_KHR`). For this
  phase the avatar is intentionally ignored so the rest of the scene can be
  validated on the real display without touching Kiosk Scene itself.

## v1.3.2-welizard.38 - March 2026

- Keep the `.37` Linux non-Skia path, but also disable GPU compositing with
  `--disable-gpu-compositing`.
- This is the next narrow host-only step after confirming that even a simple
  `http://localhost:48123/` landing page still crashes in Chromium's
  compositor path (`texStorage2D -> SharedImage -> GPU process exited`) before
  Kiosk Scene-specific rendering is involved.

## v1.3.2-welizard.37 - March 2026

- Keep the minimal Chromium profile from `.36`, but disable `UseSkiaRenderer`
  so Linux falls back to Chromium's older GL renderer path instead of the
  current `SkiaRenderer` + `SharedImage` compositor path that is crashing on
  the live Intel HDMI box.
- Keep `--disable-oop-rasterization` in place; do not reintroduce ANGLE, EGL,
  or GPU blocklist overrides.

## v1.3.2-welizard.36 - March 2026

- Keep the cleaned Chromium default profile from `.35`, but disable OOP
  rasterization with `--disable-oop-rasterization`.
- Live HDMI logs still crash inside Chromium's `SharedImage` and
  `RasterDecoder` path on Alpine, so this release forces the older raster path
  without bringing back the previous ANGLE/EGL/blocklist hacks.

## v1.3.2-welizard.35 - March 2026

- Remove forced `--enable-gpu-rasterization` and `--ignore-gpu-blocklist`
  from the default Chromium launch profile so the HDMI runtime stays on the
  browser's normal GPU path by default.
- Unify default launch URL resolution around `HA_TARGET_URL` across `run.sh`,
  REST handlers, gesture handlers, and browser control.
- Align Chromium refresh defaults to `0` consistently between add-on config and
  watchdog runtime.
- Log the effective Chromium package/version and launch flags at startup so
  live HDMI runs can be compared against the actual browser build.

## v1.3.2-welizard.34 - March 2026

- Keep the rollback baseline from `.33`, but stop forcing `--use-gl=egl`.
- On the current amd64 Chromium package the only allowed implementation is
  `egl-angle/default`, so hard-forcing EGL prevents the GPU process from
  initializing at all and leaves the HDMI path black.

## v1.3.2-welizard.33 - March 2026

- Roll back the Chromium runtime to the first stable Welizard baseline instead
  of the later GL/ANGLE experimentation path.
- Keep only the minimum follow-up fixes on top of that baseline:
  browser engine selector, Chromium touch events, and optional HA auto-login.
- Preserve support for absolute display target URLs so `Kiosk Scene` can still
  publish a direct scene URL for the kiosk host.
- Disable periodic browser refresh by default (`0`) to avoid unnecessary reload
  churn on the HDMI display.

## v1.3.2-welizard.7 - March 2026

- Make `ha_username` and `ha_password` optional in add-on schema so the
  manifest remains valid even without credentials.
- Remove hard startup failure when HA credentials are empty.
- Add explicit `HA_AUTO_LOGIN` runtime mode:
  - enabled only when both username and password are configured
  - disabled otherwise (kiosk still starts and can use existing HA session)
- Update option descriptions to reflect optional auto-login behavior.

## v1.3.2-welizard.6 - March 2026

- Fix add-on manifest validation in Home Assistant Supervisor by adding
  default `options` entries for required schema fields `ha_username` and
  `ha_password`.
- This removes `Invalid config: Missing option 'ha_username' in root`
  when adding/updating the repository.

## v1.3.2-welizard.5 - March 2026

- Fix ingress/REST port drift by aligning runtime fallback `INGRESS_PORT` with
  add-on metadata `ingress_port` (`8080`), so Home Assistant ingress does not
  break with `502 Bad Gateway` when `rest_port` is customized.
- Add configurable `ingress_runtime_port` option so ingress target can be
  corrected from add-on settings without editing `run.sh`.

## v1.3.2-welizard.3 - March 2026

- Fix ingress editor API path resolution by using a URL relative to current page
  (works both for direct `http://host:port/` and `/api/hassio_ingress/...`).
- Set add-on metadata `ingress_port` to `8080` so default ingress routing matches
  the default REST/UI server port out of the box.

## v1.3.2-welizard.2 - March 2026

- Expose the add-on ingress UI as a proper sidebar panel (`panel_title` + `panel_icon`)
  so the scene editor is discoverable from Home Assistant UI.
- Allow `/editor/config` reads/writes through ingress-authenticated requests even when
  `REST_BEARER_TOKEN` is enabled, removing the extra token prompt for normal HA usage.
- Add scene-editing convenience actions in the editor (`Форматировать`, `+ Страница`,
  `Шаблон`) to make carousel customization possible without manual JSON scaffolding.

## v1.3.2-welizard.1 - March 2026

- Fix supervisor update detection by bumping to a clear semver successor after 1.3.1-welizard.8.
- Keep ingress enabled on a stable fixed port (ingress_port: 8099) so Web UI editor does not return 502 due random port drift.

## v1.3.1-welizard.10 - March 2026

- Explicitly set ingress_port: 8099 in add-on metadata so Home Assistant ingress
  always targets the editor server port used by the runtime
- Prevent stale ingress mappings that can surface as 502 Bad Gateway when
  opening the add-on Web UI

## v1.3.1-welizard.9 - March 2026

- Fix Home Assistant ingress 502 by starting a dedicated ingress-compatible
  REST/UI listener on fixed port `8099`
- Keep automation REST endpoint compatible on user-configured `rest_port`
  (default `8080`) while ingress remains stable

## v1.3.1-welizard.8 - March 2026

- Launch Neiri directly by URL instead of relying on the intermediate
  `dashboard-display/0` container path for kiosk runtime
- Suppress Chromium translate and password-save UI so fullscreen display
  sessions stay clean on HDMI screens

## v1.3.1-welizard.7 - March 2026

- Add a first-party ingress editor for kiosk display page configuration
- Store page definitions in `/config/display-pages.json` instead of treating
  Lovelace itself as the page editor

## v1.3.1-welizard.6 - March 2026

- Fix `touch_debug_level` schema so Home Assistant Supervisor can index the
  add-on in the store instead of dropping it as invalid
- Point repository metadata and installation docs to the canonical
  `WeLizard/HAOS-kiosk` repository
## v1.3.1-welizard.5 - March 2026

- Add a clear `Browser Engine` selector to the add-on configuration UI
- Keep Chromium/Luakit switching exposed next to the other browser settings

## v1.3.1-welizard.4 - March 2026

- Add configurable `touch_debug_level` so touch and gesture parsing can be
  diagnosed on real hardware like the Mellow FlyHDMI7 without rebuilding the
  container for each test
## v1.3.1-welizard.3 - March 2026

- Explicitly enable Chromium touch events for kiosk sessions
- Improve compatibility with touchscreens such as the Mellow FlyHDMI7
  when pages rely on pointer/touch gestures like tap and pinch

## v1.3.0 - February 2026

- Added more key bindings for opening/closing/rotating tabs and windows
- Add x11vnc server to facilitate remote viewing or debugging of kiosk
- Added 'screenshot' function to REST_API and gesture action commands
- Added `enable_inputs` and `disable_inputs` functions to REST_API to allow
  locking down (and unlocking) inputs by disabling keyboard, mouse and
  touch functions
- Added `mute_audio`, `unmute_audio` and `toggle_audio` functions to
  REST_API to change audio state (`toggle_audio` can also be used in
  gesture action commands)
- Converted default gestures in `config.yaml` to use internal
  `kiosk.<function>` handlers rather than calling shell functions
- Added short list of built-in keyboard shortcuts
- Revamped `ultrasonic-trigger.py` example and added new functionality to
  enable/disable inputs, mute/unmute audio, and rotate through a list of
  URLs
- Added INSTRUCTIONS section to README.md (thanks: @cvroque)
- Added more details to README.

## v1.2.0 - January 2026

- Added ability to set HA theme in config.yaml
- Added USB audio (`audio: true` and `usb: true` in config.yaml) Added
  corresponding config option `audio_sink` which can be: auto, hdmi, usb,
  or none.
- Increased ulimit (in config.yaml) to reduce crashes from heavy usage
- Improved browser refresh logic and stability by:
  - Changing browser refresh from JS injection to native luakit view:reload
  - Forcing hard reload (including cache) every HARD_RELOAD_FREQ reloads
    (refreshes)
  - Killing and restarting luakit if ang page fails to reload more than
    MAX_LOAD_FAILURES in a row
- Improved logging of browser refresh
- Added luakit memory process logging after every page load
- Added JS injections to protect against browser errors & crashes
- Improved robustness and debug output for associating udevadm paths with
  libinput list devices
- Changed run.sh exit logic so that quits if no luakit process for at least
  10 seconds (even if original luakit process has exited)
- Removed config.yaml parameter `allow_user_command` and replaced with
  `command_whitelist` regex. Also added internal whitelist, blacklist, and
  dangerous shell tokens list along with path restrictions (see README.md)
  for details on how behavior has changed.
- Wrote complete Python 'xinput2' parser to detect broad range of mouse and
  touch gestures and execute gesture-specific commands. Replaces prior very
  limited tkinter implementation. See 'mouse_touch_inputs.py' and
  'gesture_commmands.json'
- Added corresponding 'gestures' list option to config.yaml
- Added 'Option "GrabDevice" "true"' to keyboard InputClass section in
  xorg.conf
- Added mouse buttons (left/right/middle/drag) to default Onboard keyboard
  layout
- Refactored and rewrote `rest_server.py`
- Added `REST_IP` to options to allow users to set the listening IP address
- Changed onscreen_keyboard option default to `true`
- README edits

## v1.1.1 - September 2025

- Auto-detect drm video card used and set 'kmsdev' accordingly in xorg.conf
- Added more system & display logging
- Minor bug fixes and tweaks

## v1.1.0 - September 2025

- Added REST API to allow remote launching of new urls, display on/off,
  browser refresh, and execution of one or more shell commands
- Added onscreen keyboard for touch screens (Thanks GuntherSchulz01)
- Added 'toogle_keyboard.py' to create 1x1 pixel at extreme top-right to
  toggle keyboard visibility
- Save DBUS_SESSION_BUS_ADDRESS to ~/.profile for use in other (login)
  shells
- Code now potentially supports xfwm4 window manager as well as Openbox
  (but xfwm4 commented out for now)
- Revamped 'Xorg.conf.default' to use more modern & generalized structure
- Prevent luakit from automatically restoring old sessions
- Patched luakit unique_instance.lua to open remote url's in existing tab
- Force (modified) passthrough mode in luakit with every page load to
  maximize kiosk-like behavior and hide potentially conflicting command
  mode
- Removed auto refresh on display wake (not necessary)

## v1.0.1 - August 2025

- Simplified and generalzed libinput discovery tagging and merged resulting
  code into 'run.sh' (Thanks to GuntherSchulz01 and tacher4000)
- Added "CURSOR_TIMEOUT" to hide cursor (Thanks tacher4000)
- Set LANG consistent with keyboard layout (Thanks tacher4000)
- Added additional logging to help debug any future screen or input (touch
  or mouse) issues
- Substituted luakit browser-level Dark Mode preference for HA-specific
  theme preference (Thanks tacher4000)

## v1.0.0 - July 2025

- Switched from (legacy) framebuffer-based video (fbdev) to OpenGL/DRI
  video
- Switched from (legacy) evdev input handling to libinput input handling
- Switched from "HDMI PORT" to "OUTPUT NUMBER" to determine which physical
  port is displayed
- Added 'rotation' config to rotate display
- Added boolean config to determine whether touch inputs are mapped to the
  display output (in particular, this will rotate them in sync)
- Modified 'xorg.conf' for consistency with 'OpenGL/DRI' and 'libinput'
- Attempted to maximize compatibility across RPi and x86
- Added ability to append to or replace default 'xorg.conf'
- Added ability to set keyboard layout. (default: 'us')
- Updated & improved userconf.lua code
- Extensive changes and improvements to 'run.sh' code
- Added back (local) DBUS to allow for inter-process luakit communication
  (e.g., to allow use of unique instance)

## v0.9.9 - July 2025

- Removed remounting of /dev/ ro (which caused HAOS updates to fail)
- Added 'debug' config that stops add-on before launching luakit
- Cleaned up/improved code in run.sh and userconf.lua
- Reverted to luakit=2.3.6-r0 since luakit=2.4.0-r0 crashes (temporary fix)

## v0.9.8 – June 2025

- Added ability to set browser theme and sidebar behavior
- Added <Control-r> binding to reload browser screen
- Reload browser screen automatically when returning from screen blank
- Improved input validation and error handling
- Removed host dbus dependency
- Added: ingress: true
- Tightened up code
- Updated documentation

## v0.9.7 – April 2025

- Initial public release
- Added Zoom capability

## 0.9.6 – March 2025

- Initial private release
