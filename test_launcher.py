import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from loading import steam_visible
from steam_gamescope import primary_mode, display_index, command


def state(transform=0, scale=1.0):
    other = ("HDMI-A-1", "other", "display", "one")
    chosen = ("DP-2", "chosen", "display", "two")
    return (1, [(other, [("1080p", 1920, 1080, 120.0, 1.0, [], {"is-current": True})], {}),
                (chosen, [("old", 1024, 768, 60.0, 1.0, [], {}),
                          ("current", 2560, 1440, 143.91, 1.0, [], {"is-current": True})], {})],
            [(0, 0, 1.0, 0, False, [other], {}), (1920, 0, scale, transform, True, [chosen], {})], {})


class LauncherTests(unittest.TestCase):
    def test_primary_active_mode_is_selected_instead_of_first_or_preferred(self):
        mode = primary_mode(state())
        self.assertEqual((mode["connector"], mode["width"], mode["height"], mode["refresh_hz"]), ("DP-2", 2560, 1440, 143.91))

    def test_fractional_scale_preserves_physical_game_resolution(self):
        mode = primary_mode(state(scale=1.5))
        self.assertEqual((mode["width"], mode["height"]), (2560, 1440))

    def test_rotated_primary_swaps_pixel_dimensions(self):
        mode = primary_mode(state(transform=1))
        self.assertEqual((mode["width"], mode["height"]), (1440, 2560))

    def test_sdl_display_order_does_not_select_the_wrong_monitor(self):
        mode = primary_mode(state())
        displays = [{"index": 0, "name": "HDMI-A-1", "x": 0, "y": 0},
                    {"index": 1, "name": "DP-2", "x": 1920, "y": 0}]
        self.assertEqual(display_index(mode, displays), 1)
        with self.assertRaises(ValueError):
            display_index(mode, displays[:1])

    def test_detected_refresh_and_dimensions_are_passed_at_startup(self):
        argv = command(primary_mode(state()), 1)
        self.assertEqual(argv[argv.index("-r")+1], "144")
        self.assertEqual(argv[argv.index("-W")+1], "2560")
        self.assertEqual(argv[argv.index("-H")+1], "1440")
        self.assertEqual(argv[-1], "steam-gamescope-session")
        self.assertIn("--mangoapp", argv)

    def test_fractional_refresh_rounds_to_gamescope_whole_hz(self):
        mode = primary_mode(state())
        mode["refresh_hz"] = 59.94
        argv = command(mode, 1)
        self.assertEqual(argv[argv.index("-r")+1], "60")

    def test_host_sdl_driver_does_not_leak_into_nested_games(self):
        mode = primary_mode(state())
        argv = command(mode, 0)
        client = argv[argv.index("--")+1:]
        self.assertEqual(client[:5], ["env", "-u", "SDL_VIDEODRIVER", "-u", "SDL_VIDEO_WAYLAND_WMCLASS"])
        restored = command(mode, 0, {"SDL_VIDEODRIVER": "x11"})
        self.assertIn("SDL_VIDEODRIVER=x11", restored)

    def test_loading_only_yields_to_a_visible_meaningful_steam_window(self):
        def window(classes, mapped, width=1280, height=720):
            item = Mock()
            item.get_wm_class.return_value = classes
            item.get_attributes.return_value = SimpleNamespace(map_state=mapped)
            item.get_geometry.return_value = SimpleNamespace(width=width, height=height)
            return item
        connection = Mock()
        hidden = window(("steam", "Steam"), 0)
        tiny = window(("steam", "Steam"), 2, 1, 1)
        loading = window(("zenos-steam-loading", "ZenosSteamLoading"), 2)
        connection.screen().root.query_tree.return_value.children = [hidden, tiny, loading]
        self.assertFalse(steam_visible(connection))
        connection.screen().root.query_tree.return_value.children.append(window(("steam", "Steam"), 2))
        self.assertTrue(steam_visible(connection))


if __name__ == "__main__":
    unittest.main()
