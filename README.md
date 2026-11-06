# Steam (Gamescope)

A GNOME Wayland desktop launcher for Steam Big Picture inside Gamescope.
It reads GNOME's user-selected primary monitor and its **active physical mode**
at each launch, then maps that monitor to the same SDL2 Wayland backend used by
Gamescope. Fractional scaling and rotated displays are accounted for. No screen
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

The launcher includes and starts MangoApp, the performance-overlay component
selected by Steam's Gamescope integration. Steam retains control of its overlay
settings. Games keep their own refresh/VSync/frame-limit settings: a detected
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
