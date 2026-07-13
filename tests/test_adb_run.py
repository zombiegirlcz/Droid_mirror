import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import droid.core.adb_wrapper as aw


class AdbRunTest(unittest.TestCase):
    def _fake(self, returncode, stdout, stderr):
        fake = mock.Mock()
        fake.returncode = returncode
        fake.stdout = stdout
        fake.stderr = stderr
        return fake

    def test_returns_stdout_on_success(self):
        fake = self._fake(0, "file1\nfile2\n", "")
        with mock.patch.object(aw.subprocess, "run", return_value=fake), \
             mock.patch.object(aw, "_ADB_PATH", "adb"):
            out = aw.adb_run(["shell", "ls"])
        self.assertEqual(out, "file1\nfile2\n")

    def test_returns_stderr_when_stdout_empty_and_error(self):
        fake = self._fake(1, "", "ls: /sbin/: No such file or directory")
        with mock.patch.object(aw.subprocess, "run", return_value=fake), \
             mock.patch.object(aw, "_ADB_PATH", "adb"):
            out = aw.adb_run(["shell", "ls", "/sbin/"])
        self.assertEqual(out, "ls: /sbin/: No such file or directory")

    def test_returns_stdout_when_both_present(self):
        fake = self._fake(0, "result\n", "warning on stderr\n")
        with mock.patch.object(aw.subprocess, "run", return_value=fake), \
             mock.patch.object(aw, "_ADB_PATH", "adb"):
            out = aw.adb_run(["shell", "ls"])
        self.assertEqual(out, "result\n")

    def test_logcat_stream_handles_invalid_utf8(self):
        import io
        bad = (
            b"07-13 19:14:01.234  1234  1234 E Tag: ok line\n"
            b"07-13 19:14:02.000  1234  1234 E Tag: bad \xc0 byte here\n"
        )
        fake_proc = mock.Mock()
        fake_proc.stdout = io.TextIOWrapper(
            io.BytesIO(bad), encoding="utf-8", errors="replace"
        )
        fake_proc.terminate = mock.Mock()
        fake_proc.wait = mock.Mock()

        captured = []
        with mock.patch.object(aw.subprocess, "Popen", return_value=fake_proc) as m, \
             mock.patch.object(aw.platform, "system", return_value="Windows"), \
             mock.patch.object(aw, "_ADB_PATH", "adb"), \
             mock.patch("builtins.print", side_effect=lambda *a, **k: captured.append(a)):
            aw.adb_logcat_stream({"priority": "V"})

        # Popen musí dostat errors="replace", jinak by neplatné UTF-8 pádlo
        self.assertEqual(m.call_args.kwargs.get("errors"), "replace")
        # stream nezpůsobil výjimku a propustil obě řádky (priority V)
        self.assertTrue(any("bad" in str(c) for c in captured))


if __name__ == "__main__":
    unittest.main()
