################################################################################
# Add-on: HAOS Kiosk Display (haoskiosk)
# File: Dockerfile
# Base: Alpine (default HAOS base image)
# Copyright Jeff Kosowsky / Welizard Chromium fork
################################################################################

ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION
ENV ADDON_VERSION=${BUILD_VERSION}

#===============================================================================
##### Install X, Browser and all necessary dependencies
RUN apk update && apk add --no-cache \
## Xserver and graphics
     xorg-server \
     xf86-video-modesetting \
     mesa-dri-gallium \
     mesa-egl \
     mesa-gles \
     libdrm \
### Vulkan (required for Chromium ANGLE/SwANGLE WebGL)
     mesa-vulkan-swrast \
     vulkan-loader \
### X utils
     xdotool \
     xinput \
     xrandr \
     xset \
     libxkbcommon \
     setxkbmap \
### Input, udev
     xf86-input-libinput \
     libinput \
     udev \
     libinput-udev \
     libevdev \
     evtest \
### Window, mouse, keyboard management
     openbox \
     onboard \
     unclutter-xfixes \
     ttf-dejavu \
### Linux utils
     bash \
     util-linux \
     patch \
     scrot \
### Full Timezone info
     icu-data-full \
### Python libraries
    py3-pip \
    py3-xlib \
### Sound
     pulseaudio-utils \
### VNC (for debugging)
      x11vnc \
## Browsers
     chromium \
   && apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/v3.21/community luakit=2.3.6-r0 \
   && rm -rf /var/cache/apk/*

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
COPY unique_instance.patch /usr/share/luakit/lib
RUN patch -p2 /usr/share/luakit/lib/unique_instance.lua < /usr/share/luakit/lib/unique_instance.patch

CMD ["/run.sh"]
