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


class DeviceSelectionTest(unittest.TestCase):
    def setUp(self):
        aw.set_device_serial(None)

    def tearDown(self):
        aw.set_device_serial(None)

    def test_parse_devices_empty(self):
        self.assertEqual(aw.parse_devices(""), [])
        self.assertEqual(aw.parse_devices("List of devices attached\n\n"), [])

    def test_parse_devices_single(self):
        raw = "List of devices attached\nABC123\tdevice\n"
        devs = aw.parse_devices(raw)
        self.assertEqual(len(devs), 1)
        self.assertEqual(devs[0]["serial"], "ABC123")
        self.assertEqual(devs[0]["state"], "device")

    def test_parse_devices_multiple_with_extra(self):
        raw = (
            "List of devices attached\n"
            "ABC123\tdevice\tproduct:phone model:X\n"
            "emulator-5554\toffline\n"
        )
        devs = aw.parse_devices(raw)
        self.assertEqual(len(devs), 2)
        self.assertEqual(devs[0]["serial"], "ABC123")
        self.assertEqual(devs[0]["extra"], "product:phone model:X")
        self.assertEqual(devs[1]["state"], "offline")

    def test_adb_run_injects_serial(self):
        aw.set_device_serial("ABC123")
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            fr = mock.Mock()
            fr.returncode = 0
            fr.stdout = "out"
            fr.stderr = ""
            return fr

        with mock.patch.object(aw.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(aw, "_ADB_PATH", "adb"):
            out = aw.adb_run(["shell", "getprop"])
        self.assertEqual(out, "out")
        # -s <serial> musí být hned za adb, před vlastním příkazem
        self.assertEqual(captured["cmd"][:4], ["adb", "-s", "ABC123", "shell"])

    def test_adb_run_no_serial_for_devices(self):
        aw.set_device_serial("ABC123")
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            fr = mock.Mock()
            fr.returncode = 0
            fr.stdout = ""
            fr.stderr = ""
            return fr

        with mock.patch.object(aw.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(aw, "_ADB_PATH", "adb"):
            aw.adb_run(["devices", "-l"])
        # devices je globální příkaz -> bez -s
        self.assertEqual(captured["cmd"], ["adb", "devices", "-l"])

    def test_logcat_stream_passes_serial(self):
        import io
        bad = b"07-13 19:14:01.234  1234  1234 E Tag: ok\n"
        fake_proc = mock.Mock()
        fake_proc.stdout = io.TextIOWrapper(
            io.BytesIO(bad), encoding="utf-8", errors="replace"
        )
        fake_proc.terminate = mock.Mock()
        fake_proc.wait = mock.Mock()
        with mock.patch.object(aw.subprocess, "Popen", return_value=fake_proc) as m, \
             mock.patch.object(aw.platform, "system", return_value="Windows"), \
             mock.patch.object(aw, "_ADB_PATH", "adb"), \
             mock.patch("builtins.print"):
            aw.adb_logcat_stream({"priority": "V"}, serial="ABC123")
        # Popen musí dostat -s <serial> před logcat
        self.assertEqual(m.call_args.args[0][:4], ["adb", "-s", "ABC123", "logcat"])


if __name__ == "__main__":
    unittest.main()
