/*
 * tty0_override.c — LD_PRELOAD library to fake /dev/tty0 VT management
 *
 * Problem: Xorg on Debian requires /dev/tty0 for VT management, but HAOS
 * Docker containers don't allow access to it (EPERM from device cgroup).
 *
 * Solution: Intercept open("/dev/tty0") and redirect to /dev/null, then
 * fake VT ioctl responses so Xorg thinks VT management succeeded.
 * The real display output uses DRM/KMS via /dev/dri/card0 — unaffected.
 *
 * Usage: LD_PRELOAD=/usr/lib/tty0_override.so Xorg ...
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <stdarg.h>
#include <fcntl.h>
#include <linux/vt.h>
#include <linux/kd.h>
#include <sys/ioctl.h>

static int fake_tty_fd = -1;

/* Intercept open() — redirect /dev/tty0 and /dev/ttyN to /dev/null */
int open(const char *pathname, int flags, ...) {
    int (*real_open)(const char *, int, ...) =
        (int (*)(const char *, int, ...))dlsym(RTLD_NEXT, "open");

    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }

    /* Redirect /dev/tty0 and /dev/ttyN opens to /dev/null */
    if (pathname && strncmp(pathname, "/dev/tty", 8) == 0) {
        char c = pathname[8];
        if (c >= '0' && c <= '9') {
            int fd = real_open("/dev/null", flags, mode);
            if (fd >= 0) fake_tty_fd = fd;
            return fd;
        }
    }
    return real_open(pathname, flags, mode);
}

/* Also intercept open64 (used by some glibc builds) */
int open64(const char *pathname, int flags, ...) {
    int (*real_open64)(const char *, int, ...) =
        (int (*)(const char *, int, ...))dlsym(RTLD_NEXT, "open64");

    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }

    if (pathname && strncmp(pathname, "/dev/tty", 8) == 0) {
        char c = pathname[8];
        if (c >= '0' && c <= '9') {
            int fd = real_open64("/dev/null", flags, mode);
            if (fd >= 0) fake_tty_fd = fd;
            return fd;
        }
    }
    return real_open64(pathname, flags, mode);
}

/* Intercept ioctl() — fake VT management responses */
int ioctl(int fd, unsigned long request, ...) {
    int (*real_ioctl)(int, unsigned long, ...) =
        (int (*)(int, unsigned long, ...))dlsym(RTLD_NEXT, "ioctl");

    va_list ap;
    va_start(ap, request);
    void *arg = va_arg(ap, void *);
    va_end(ap);

    /* Only intercept ioctls on our fake tty fd */
    if (fd >= 0 && fd == fake_tty_fd) {
        switch (request) {
            case VT_GETSTATE: {
                struct vt_stat *vt = (struct vt_stat *)arg;
                if (vt) {
                    vt->v_active = 1;
                    vt->v_signal = 0;
                    vt->v_state = 0x2;
                }
                return 0;
            }
            case VT_OPENQRY: {
                int *vtno = (int *)arg;
                if (vtno) *vtno = 7;
                return 0;
            }
            case VT_ACTIVATE:
            case VT_WAITACTIVE:
            case VT_RELDISP:
            case VT_SETMODE:
            case VT_GETMODE:
                return 0;
            case KDSETMODE:
            case KDGETMODE:
                if (request == KDGETMODE && arg) {
                    *(int *)arg = KD_GRAPHICS;
                }
                return 0;
            case KDGKBMODE:
                if (arg) *(int *)arg = K_OFF;
                return 0;
            case KDSKBMODE:
                return 0;
        }
    }
    return real_ioctl(fd, request, arg);
}
