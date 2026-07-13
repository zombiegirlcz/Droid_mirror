import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from droid.core.adb_wrapper import extract_logcat_priority, filter_logcat_line


SAMPLE = "07-13 19:14:01.234  1234  1234 E TagName: something broke"
SAMPLE_I = "07-13 19:14:02.000  1234  1234 I OtherTag: info message here"


class FilterTest(unittest.TestCase):
    def test_extract_priority(self):
        self.assertEqual(extract_logcat_priority(SAMPLE), "E")
        self.assertEqual(extract_logcat_priority(SAMPLE_I), "I")
        self.assertIsNone(extract_logcat_priority("malformed line"))

    def test_filter_by_priority_keeps_higher(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {"priority": "W"}))
        self.assertFalse(filter_logcat_line(SAMPLE_I, {"priority": "W"}))
        # V pustí vše
        self.assertTrue(filter_logcat_line(SAMPLE_I, {"priority": "V"}))

    def test_filter_by_tag(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {"tag": "tagname"}))
        self.assertFalse(filter_logcat_line(SAMPLE, {"tag": "nomatch"}))

    def test_filter_by_keyword(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {"keyword": "broke"}))
        self.assertFalse(filter_logcat_line(SAMPLE, {"keyword": "zzz"}))

    def test_combined_filters(self):
        f = {"priority": "W", "tag": "tagname", "keyword": "broke"}
        self.assertTrue(filter_logcat_line(SAMPLE, f))
        f2 = {"priority": "W", "tag": "tagname", "keyword": "zzz"}
        self.assertFalse(filter_logcat_line(SAMPLE, f2))

    def test_empty_filters_keep_everything(self):
        self.assertTrue(filter_logcat_line(SAMPLE, {}))


if __name__ == "__main__":
    unittest.main()
