"""Launch the curated Steam client in Gamescope on GNOME's primary monitor."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


APP_ID = "com.neg-zero.SteamGamescope"


def primary_mode(state):
    _, monitors, logical_monitors, _ = state
    primary = next((m for m in logical_monitors if m[4]), None)
    if primary is None or not primary[5]:
        raise ValueError("GNOME has no active primary monitor")
    spec = primary[5][0]
    monitor = next((m for m in monitors if tuple(m[0]) == tuple(spec)), None)
    if monitor is None:
        raise ValueError("primary monitor is absent from the display configuration")
    mode = next((m for m in monitor[1] if m[6].get("is-current")), None)
    if mode is None:
        raise ValueError("primary monitor has no active display mode")
    width, height = mode[1:3]
    if primary[3] in (1, 3, 5, 7):
        width, height = height, width
    if width <= 0 or height <= 0 or mode[3] <= 0:
        raise ValueError("invalid active display mode")
    return {"connector": spec[0], "x": primary[0], "y": primary[1],
            "width": width, "height": height, "refresh_hz": mode[3]}


def current_state():
    from gi.repository import Gio
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    result = bus.call_sync("org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig",
                          "org.gnome.Mutter.DisplayConfig", "GetCurrentState", None, None,
                          Gio.DBusCallFlags.NONE, 5000, None)
    return result.unpack()


def sdl_displays():
    sdl = ctypes.CDLL(os.environ["STEAM_GAMESCOPE_SDL_LIBRARY"])
    class Rect(ctypes.Structure):
        _fields_ = [(name, ctypes.c_int) for name in ("x", "y", "w", "h")]
    sdl.SDL_Init.argtypes = [ctypes.c_uint32]
    sdl.SDL_GetError.restype = ctypes.c_char_p
    sdl.SDL_GetDisplayName.argtypes = [ctypes.c_int]
    sdl.SDL_GetDisplayName.restype = ctypes.c_char_p
    sdl.SDL_GetDisplayBounds.argtypes = [ctypes.c_int, ctypes.POINTER(Rect)]
    # Initialize video enumeration only; create no window or rendering context.
    if sdl.SDL_Init(0x20):
        raise RuntimeError(sdl.SDL_GetError().decode(errors="replace"))
    try:
        displays = []
        for index in range(sdl.SDL_GetNumVideoDisplays()):
            bounds = Rect()
            if sdl.SDL_GetDisplayBounds(index, ctypes.byref(bounds)):
                continue
            name = sdl.SDL_GetDisplayName(index)
            displays.append({"index": index, "name": name.decode() if name else "",
                             "x": bounds.x, "y": bounds.y})
        return displays
    finally:
        sdl.SDL_Quit()


def display_index(mode, displays):
    candidates = [d for d in displays if (d["x"], d["y"]) == (mode["x"], mode["y"])]
    if not candidates:
        raise ValueError("SDL cannot locate GNOME's primary monitor")
    return next((d["index"] for d in candidates if d["name"] == mode["connector"]), candidates[0]["index"])


def command(mode, index, previous=None):
    # Gamescope's CLI takes integer Hz; seed the virtual display before it starts.
    refresh = max(1, int(mode["refresh_hz"] + 0.5))
    previous = previous or {}
    client = ["env"]
    for key in ("SDL_VIDEODRIVER", "SDL_VIDEO_WAYLAND_WMCLASS"):
        if previous.get(key) is None:
            client.extend(["-u", key])
    client.extend(f"{key}={value}" for key, value in previous.items() if value is not None)
    client.extend(["steam", "-gamepadui"])
    return ["gamescope", "--backend", "sdl", "--display-index", str(index),
            "-f", "-e", "--xwayland-count", "2",
            "-W", str(mode["width"]), "-H", str(mode["height"]),
            "-w", str(mode["width"]), "-h", str(mode["height"]),
            "-r", str(refresh),
            "--", *client]


def steam_running():
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if entry.stat().st_uid == os.getuid() and (entry / "comm").read_text().strip() == "steam":
                return True
        except OSError:
            continue
    return False


def fail(message):
    print(f"Steam (Gamescope): {message}", file=sys.stderr)
    notify = shutil.which("notify-send")
    if notify:
        subprocess.run([notify, "--app-name=Steam (Gamescope)", "--icon=steam",
                        "Steam (Gamescope)", message], check=False)
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true", help="show the detected mode and command without opening Steam")
    args = parser.parse_args()
    if not args.print_plan and steam_running():
        return fail("Quit Steam completely, then open Steam (Gamescope) again.")
    if not os.environ.get("WAYLAND_DISPLAY"):
        return fail("This launcher requires a GNOME Wayland session.")
    previous = {key: os.environ.get(key) for key in ("SDL_VIDEODRIVER", "SDL_VIDEO_WAYLAND_WMCLASS")}
    os.environ["SDL_VIDEODRIVER"] = "wayland"
    os.environ["SDL_VIDEO_WAYLAND_WMCLASS"] = APP_ID
    try:
        mode = primary_mode(current_state())
        index = display_index(mode, sdl_displays())
        argv = command(mode, index, previous)
    except Exception as error:
        return fail(f"Could not detect the primary display: {error}")
    if args.print_plan:
        print(json.dumps({"monitor": mode, "display_index": index, "argv": argv}, indent=2))
        return 0
    print(f'Steam (Gamescope): {mode["connector"]}, {mode["width"]}×{mode["height"]}, {mode["refresh_hz"]:.3f} Hz', flush=True)
    try:
        os.execvp(argv[0], argv)
    except OSError as error:
        return fail(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
