# Steam (Gamescope)

A GNOME Wayland desktop launcher for Steam Big Picture inside Gamescope.
It reads GNOME's user-selected primary monitor and its **active physical mode**
at each launch. SDR uses the SDL2 backend; HDR uses Gamescope’s native
Wayland backend for color management. Fractional scaling and rotated displays are accounted for. No screen
size, refresh rate, or connector is hardcoded.

Rendering, output and the virtual game display start at the detected native pixel
dimensions and active refresh. Gamescope's `-r` CLI accepts whole Hz, so fractional
rates are rounded to the nearest Hz; the host compositor still controls actual
presentation timing. Relaunch after changing the primary monitor or its mode.

Install through ZenPkgs as `com.neg-zero.SteamGamescope` or
`apps.gaming.steam-gamescope`. The package consumes the curated Steam package,
including its existing private-home setup and Proton GE. It provides
`steam-gamescope` and `com.neg-zero.SteamGamescope.desktop`, using the theme's
Steam icon. Ordinary Steam and its URL associations are unchanged.

A dark loading screen with the themed Steam icon and spinner appears **inside**
Gamescope while Steam starts. It disappears when Steam presents a visible window,
including an updater or login window. Hidden helper windows do not dismiss it.
Launch failure/exit closes it; a failed window probe never permanently covers Steam.

Games keep their own refresh/VSync/frame-limit settings: a detected
120 Hz display does not override a game's saved 60 Hz mode or VSync choice.

Quit any existing Steam client first. Steam is a singleton; otherwise it forwards
the launch request to the existing client outside Gamescope. This launcher reports
that situation and never closes Steam or running games automatically.

`steam-gamescope --print-plan` queries display metadata without opening a window,
initializing a renderer, or launching Steam. This requires GNOME Wayland and the
package's SDL2 library; no compositor extensions or screen-capture grants are used.

Primary sources:

- [Mutter DisplayConfig API](https://gitlab.gnome.org/GNOME/mutter/-/blob/main/data/dbus-interfaces/org.gnome.Mutter.DisplayConfig.xml)
- [Gamescope 3.16.23 SDL backend](https://github.com/ValveSoftware/gamescope/blob/3.16.23/src/Backends/SDLBackend.cpp)
- [Gamescope refresh selection](https://github.com/ValveSoftware/gamescope/blob/3.16.23/src/steamcompmgr.cpp)

The launcher is MIT licensed; Steam and Gamescope retain their own licenses.

Keyboard layouts, their variants and XKB options are copied from GNOME input
sources at launch, rather than using Gamescope's default keyboard map. The
selected source is placed first. Restart this launcher after changing sources
or options; existing sessions do not dynamically follow input-source changes.
IBus input methods cannot be represented by Gamescope's XKB configuration and
produce an explicit error instead of silently selecting a US keyboard.
`--print-plan` includes the keyboard environment for diagnosis.

HDR follows GNOME’s primary monitor color mode. HDR launches use `--hdr-enabled`,
the matching Gamescope WSI layer and `DXVK_HDR=1`; no debug force flags are used.
The packaged Gamescope patch accepts Mutter’s HDR10 PQ capability subset, skips
unsupported mastering metadata and Windows scRGB requests, and composites scRGB
clients to PQ when needed. Upstream interoperability report:
https://github.com/ValveSoftware/gamescope/issues/2249
The patch is derived from Gamescope 3.16.23, BSD-2-Clause; it is maintained here
alongside the launcher that requires it. Optional metadata is omitted on hosts
that cannot accept it. Actual HDR appearance/calibration still requires game testing.

Adaptive sync follows the active GNOME display mode: select Variable Refresh Rate
in GNOME Display Settings to enable FreeSync/VRR, then relaunch. Gamescope cannot
enable host-compositor VRR with a command-line flag alone. HDR fullscreen placement
is controlled by GNOME’s native Wayland window placement; SDL’s display-index
option does not apply to that backend.

At launch, Xcursor gets GNOME’s current theme and cursor size multiplied by the
primary monitor scale, since Gamescope’s virtual X display uses physical pixels.
Application-defined game cursors can choose their own size.

When the host Gamescope window loses keyboard focus (including minimization),
the launcher limits its nested refresh to 15 FPS. Focus restores the refresh
selected at launch; the monitor mode, HDR, VRR and individual game settings stay
unchanged. SDR uses the existing SDL implementation. HDR includes the native
Wayland fix from [Gamescope PR 2556](https://github.com/ValveSoftware/gamescope/pull/2556)
by Brandon Falk (BSD-2-Clause, original patch attribution retained).
Hosts that never report the optional activated state keep the foreground rate;
the Wayland implementation starts throttling after the first reported activation.
An already-running Gamescope process needs a natural quit/relaunch to use an update.
