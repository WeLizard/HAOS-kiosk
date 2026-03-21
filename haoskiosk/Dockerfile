################################################################################
# Add-on: HAOS Kiosk Display (haoskiosk)
# File: Dockerfile
# Version: 1.3.2-welizard.80
# Copyright Jeff Kosowsky
# Date: February 2026
#
# Debian bookworm (glibc) base — eliminates musl-specific Chromium crashes
# (SIGILL on WebGL/WASM) that affect Alpine builds.
################################################################################

ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION
ENV ADDON_VERSION=${BUILD_VERSION}

#===============================================================================
##### Install X, Browser and all necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
## Xserver and graphics
     xserver-xorg-core \
     libgl1-mesa-dri \
     libegl1 \
     libgles2 \
     libgl1 \
     mesa-vulkan-drivers \
     libvulkan1 \
     libdrm2 \
### X utils
     xdotool \
     xinput \
     x11-xserver-utils \
     libxkbcommon0 \
     x11-xkb-utils \
### Input, udev
     xserver-xorg-input-libinput \
     udev \
     libevdev2 \
     evtest \
### Window, mouse, keyboard management
     openbox \
     onboard \
     dconf-cli \
     unclutter-xfixes \
     fonts-dejavu \
### Linux utils
     util-linux \
     procps \
     psmisc \
     patch \
     scrot \
### Python libraries
     python3-pip \
     python3-xlib \
     python3-aiohttp \
### Sound
     pulseaudio-utils \
### VNC (for debugging) - run: x11vnc -display :0 -forever &
     x11vnc \
### Browser
     chromium \
     fonts-noto \
     fonts-noto-color-emoji \
     luakit \
   && rm -rf /var/lib/apt/lists/*

#===============================================================================

##### Set the display variable
ENV DISPLAY=:0

##### Copy over 'xorg.conf.default' and lua 'userconf.lua' file
COPY xorg.conf.default /etc/X11/
COPY userconf.lua /root/.config/luakit/
COPY translations/*.yaml /translations/

COPY run.sh /
RUN chmod a+x /run.sh

COPY mouse_touch_inputs.py gesture_commands.json /
COPY rest_server.py /
COPY browser_ctl.py chromium_watchdog.py chromium_startup_diag.py target_url.py /

#### Patches
# Need to patch 'unique_instance.lua' so that new instance urls overwrite active url rather than add new tab
COPY unique_instance.patch /usr/share/luakit/lib
RUN patch -p2 /usr/share/luakit/lib/unique_instance.lua < /usr/share/luakit/lib/unique_instance.patch

CMD ["/run.sh"]
