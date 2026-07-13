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


if __name__ == "__main__":
    unittest.main()
