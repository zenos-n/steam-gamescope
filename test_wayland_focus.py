"""Exercise the actual upstream patch's focus policy without a GPU/session."""
import pathlib
import subprocess
import tempfile
import unittest


class WaylandFocusTests(unittest.TestCase):
    def test_upstream_focus_policy(self):
        patch = (pathlib.Path(__file__).parent / "patches/wayland-unfocused-refresh.patch").read_text()
        added = "\n".join(line[1:] for line in patch.splitlines()
                          if line.startswith("+") and not line.startswith("+++"))
        policy = added[added.index("    static bool s_bSeenActivated"):added.index("\t    else")]
        source = "#include <cassert>\nint g_nNestedRefresh, g_nNestedUnfocusedRefresh;\n" + policy + r'''
int main() {
    g_nNestedRefresh = 240000;
    g_nNestedUnfocusedRefresh = 15000;
    // Hosts that omit the optional active state must not get stuck throttled.
    UpdateNestedRefreshForActivation(false);
    assert(g_nNestedRefresh == 240000);
    for (int rate : {60000, 144000, 240000, 0}) {
        g_nNestedRefresh = rate;
        UpdateNestedRefreshForActivation(true);
        UpdateNestedRefreshForActivation(false);
        assert(g_nNestedRefresh == 15000);
        UpdateNestedRefreshForActivation(false); // repeated resize/configure
        assert(g_nNestedRefresh == 15000);
        UpdateNestedRefreshForActivation(true);
        assert(g_nNestedRefresh == rate);
        UpdateNestedRefreshForActivation(true);
        assert(g_nNestedRefresh == rate);
    }
    g_nNestedRefresh = 240000;
    g_nNestedUnfocusedRefresh = 0;
    UpdateNestedRefreshForActivation(false);
    assert(g_nNestedRefresh == 240000);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / "focus.cpp").write_text("#include <initializer_list>\n" + source)
            subprocess.run(["c++", "-std=c++17", "-Wall", "-Werror", str(path / "focus.cpp"),
                            "-o", str(path / "focus")], check=True)
            subprocess.run([str(path / "focus")], check=True)
