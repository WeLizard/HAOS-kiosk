################################################################################
# Add-on: HAOS Kiosk Display (haoskiosk)
# File: Dockerfile
# Base: Debian Bookworm (glibc) — required for Chromium WebGL/WASM stability
# Copyright Jeff Kosowsky / Welizard Chromium fork
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
     xserver-xorg-video-all \
     libgl1-mesa-dri \
     libegl-mesa0 \
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
     libinput10 \
     libinput-tools \
     udev \
     libevdev2 \
     evtest \
### Window, mouse, keyboard management
     openbox \
     onboard \
     unclutter-xfixes \
     fonts-dejavu-core \
### Linux utils
     bash \
     util-linux \
     patch \
     scrot \
     procps \
### Python libraries
     python3-pip \
     python3-xlib \
### Sound
     pulseaudio-utils \
### VNC (for debugging)
     x11vnc \
## Browsers
     chromium \
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
COPY browser_ctl.py target_url.py /
RUN pip install --no-cache-dir --break-system-packages aiohttp

#### Patches
# Need to patch 'unique_instance.lua' so that new instance urls overwrite active url rather than add new tab
COPY unique_instance.patch /usr/share/luakit/lib/
RUN patch -p2 /usr/share/luakit/lib/unique_instance.lua < /usr/share/luakit/lib/unique_instance.patch || true

CMD ["/run.sh"]
