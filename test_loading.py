"""Exercise the real loading view on an isolated X server, never real Steam."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.environ["STEAM_LOADING_MODULE_DIR"])


def windows(connection, prefix):
    result = []
    for item in connection.screen().root.query_tree().children:
        try:
            if any(name.lower().startswith(prefix) for name in (item.get_wm_class() or ())):
                result.append(item)
        except Exception:
            pass
    return result


if len(sys.argv) > 1 and sys.argv[1] == "fixture":
    assert os.environ["GDK_BACKEND"] == "wayland", "Loading backend leaked into Steam"
    os.environ["GDK_BACKEND"] = "x11"
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk
    window = Gtk.Window(title="Steam fixture")
    window.set_wmclass("steam", "Steam")
    window.set_default_size(800, 600)
    GLib.timeout_add(1500, lambda: (window.show_all(), False)[1])
    GLib.timeout_add(2200, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    raise SystemExit(0)

if len(sys.argv) > 1 and sys.argv[1] == "session":
    from loading import run
    raise SystemExit(run(sys.argv[2:]))

from Xlib import Xatom, display
connection = display.Display()
environment = os.environ | {"GDK_BACKEND": "wayland"}
script = str(Path(__file__).resolve())


def wait_until(predicate, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.03)
    raise AssertionError("Timed out waiting for loading lifecycle")


def session(command):
    return subprocess.Popen([sys.executable, script, "session", *command], env=environment)


with tempfile.TemporaryDirectory() as directory:
    process = session([sys.executable, script, "fixture"])
    try:
        splash = wait_until(lambda: windows(connection, "zenos-steam-loading"))[0]
        assert splash.get_full_property(connection.intern_atom("STEAM_GAME"), Xatom.CARDINAL).value[0] == 769
        assert splash.get_geometry().width == 1280
        assert splash.get_geometry().height == 720
        screenshot = os.environ.get("STEAM_LOADING_SCREENSHOT")
        if screenshot:
            os.environ["GDK_BACKEND"] = "x11"
            import gi
            gi.require_version("Gdk", "3.0")
            from gi.repository import Gdk
            time.sleep(.15)
            Gdk.init([])
            Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(), 0, 0, 1280, 720).savev(screenshot, "png", [], [])
        wait_until(lambda: windows(connection, "steam"))
        wait_until(lambda: not windows(connection, "zenos-steam-loading"))
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
    assert not windows(connection, "zenos-steam-loading")
    failed = session([sys.executable, "-c", "raise SystemExit(7)"])
    assert failed.wait(timeout=10) == 7
    assert not windows(connection, "zenos-steam-loading")
    missing = session([str(Path(directory) / "missing-steam")])
    assert missing.wait(timeout=10) == 1
    assert not windows(connection, "zenos-steam-loading")
connection.close()
print("Loading UI: fullscreen, Steam UI app ID, real-window handoff, environment isolation and failed launch cleanup passed")
