# Changelog

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
