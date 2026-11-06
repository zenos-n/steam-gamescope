"""Keep a loading view inside Gamescope until Steam presents its own window."""
import os
import signal
import subprocess
import sys
import time

from Xlib import X, Xatom, display
from Xlib.error import BadDrawable, BadWindow


def steam_visible(connection):
    for window in connection.screen().root.query_tree().children:
        try:
            classes = window.get_wm_class() or ()
            if not any(name.lower().startswith("steam") for name in classes):
                continue
            geometry = window.get_geometry()
            if (window.get_attributes().map_state == X.IsViewable
                    and geometry.width >= 160 and geometry.height >= 100):
                return True
        except (BadWindow, BadDrawable):
            continue
    return False


def loading_window():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("GdkX11", "3.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf, GdkX11, Gtk

    window = Gtk.Window(title="Starting Steam")
    window.set_wmclass("zenos-steam-loading", "ZenosSteamLoading")
    window.set_decorated(False)
    screen = window.get_screen()
    window.set_default_size(screen.get_width(), screen.get_height())
    window.fullscreen()
    window.set_name("steam-loading")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.CENTER)
    if Gtk.IconTheme.get_default().has_icon("steam"):
        icon = Gtk.Image.new_from_icon_name("steam", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(112)
    else:
        icon = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.environ["STEAM_GAMESCOPE_ICON"], 112, 112, True))
    box.add(icon)
    label = Gtk.Label(label="Starting Steam…")
    box.add(label)
    spinner = Gtk.Spinner()
    spinner.set_size_request(28, 28)
    spinner.set_halign(Gtk.Align.CENTER)
    spinner.start()
    box.add(spinner)
    window.add(box)
    css = Gtk.CssProvider()
    css.load_from_data(b"""
        #steam-loading { background: #101822; color: #f3f6fa; }
        #steam-loading label { font-family: "DejaVu Sans", sans-serif; font-size: 22px; font-weight: 500; }
        #steam-loading spinner { color: #8bb9e8; min-width: 28px; min-height: 28px; }
    """)
    Gtk.StyleContext.add_provider_for_screen(screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return window


def run(command):
    # Force X11 only for this view, never for Steam or its games.
    steam_environment = os.environ.copy()
    os.environ["GDK_BACKEND"] = "x11"
    try:
        window = loading_window()
        from gi.repository import GLib, Gtk
        connection = display.Display()
    except Exception as error:
        print(f"Steam loading view unavailable: {error}", file=sys.stderr)
        os.execvpe(command[0], command, steam_environment)

    process = None
    result = 0
    started_at = time.monotonic()
    visible = True

    def hide():
        nonlocal visible
        if visible:
            visible = False
            window.destroy()

    def start(clock):
        nonlocal process, result
        clock.disconnect(paint_handler)
        try:
            process = subprocess.Popen(command, env=steam_environment)
        except OSError as error:
            print(f"Could not start Steam: {error}", file=sys.stderr)
            result = 1
            Gtk.main_quit()

    def poll():
        nonlocal result
        if process is not None and process.poll() is not None:
            result = process.returncode
            Gtk.main_quit()
            return GLib.SOURCE_REMOVE
        if visible:
            try:
                # Never let a broken readiness probe cover Steam indefinitely.
                if steam_visible(connection) or time.monotonic() - started_at > 120:
                    hide()
            except Exception as error:
                print(f"Steam window detection unavailable: {error}", file=sys.stderr)
                hide()
        return GLib.SOURCE_CONTINUE

    def stop(_signum, _frame):
        nonlocal result
        result = 128 + _signum
        if process is not None and process.poll() is None:
            process.terminate()
        Gtk.main_quit()

    def cancel(*_args):
        stop(signal.SIGTERM, None)
        return True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    window.connect("delete-event", cancel)
    window.realize()
    xid = window.get_window().get_xid()
    # Gamescope treats app ID 769 as its Steam UI, not as a running game.
    connection.create_resource_object("window", xid).change_property(
        connection.intern_atom("STEAM_GAME"), Xatom.CARDINAL, 32, [769])
    connection.flush()
    paint_handler = window.get_frame_clock().connect("after-paint", start)
    window.show_all()
    GLib.timeout_add(100, poll)
    try:
        Gtk.main()
    finally:
        hide()
        connection.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    return result


if __name__ == "__main__":
    raise SystemExit(run(["steam", "-gamepadui"]))
