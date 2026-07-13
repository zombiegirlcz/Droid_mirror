import os
import sys
import io
import unittest

# zajistí import droid i bez editable install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import droid.ui.style as style


class _TTY(io.StringIO):
    def isatty(self):
        return True


class StyleTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("NO_COLOR", None)
        self._old = sys.stdout
        sys.stdout = _TTY()

    def tearDown(self):
        sys.stdout = self._old

    def test_colors_enabled_contain_ansi(self):
        out = style.green("hi")
        self.assertIn("\x1b[", out)
        self.assertIn("hi", out)
        self.assertIn(style.RESET, out)

    def test_no_color_env_returns_plain(self):
        os.environ["NO_COLOR"] = "1"
        self.assertEqual(style.green("hi"), "hi")
        self.assertEqual(style.red("x"), "x")
        del os.environ["NO_COLOR"]

    def test_no_tty_returns_plain(self):
        sys.stdout = io.StringIO()  # isatty() -> False
        self.assertEqual(style.green("hi"), "hi")

    def test_android_green_is_correct_rgb(self):
        self.assertEqual(style.ANDROID_GREEN, "\x1b[38;2;61;220;132m")

    def test_box_contains_title_and_body(self):
        out = style.box("devices -l", "abc\ndef")
        self.assertIn("devices -l", out)
        self.assertIn("abc", out)
        self.assertIn("def", out)

    def test_box_empty_body_shows_placeholder(self):
        out = style.box("x", "")
        self.assertIn("žádný výstup", out)

    def test_box_alignment(self):
        import re
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        out = style.box("ls -la /sbin/", "(žádný výstup)")
        # měříme VIDITELNOU šířku (bez ANSI escape kódů)
        lines = [ansi.sub("", l) for l in out.split("\n")]
        widths = [len(l) for l in lines]
        self.assertEqual(len(set(widths)), 1, f"box lines not aligned: {widths}")
        self.assertTrue(lines[0].startswith("┌"))
        self.assertTrue(lines[-1].startswith("└"))

    def test_logcat_color_priority_codes(self):
        e = style.logcat_color("E", "boom")
        self.assertIn("\x1b[", e)
        self.assertIn("boom", e)
        # neznámá priorita -> plain (obsahuje RESET jen pokud obarveno)
        self.assertIn("weird", style.logcat_color("Z", "weird"))

    def test_logcat_color_no_tty_plain(self):
        sys.stdout = io.StringIO()
        self.assertEqual(style.logcat_color("E", "boom"), "boom")


if __name__ == "__main__":
    unittest.main()
