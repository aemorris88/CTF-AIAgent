"""Current browser-mode regression: the multi-challenge test covers JSON isolation."""
import unittest
from test_multichallenge_browser import MultiBrowserTests

class BrowserModeTest(unittest.TestCase):
    def test_browser_mode_bypasses_json_adapter(self):
        # Exercise the new dashboard-to-per-challenge workflow, not the
        # retired one-session browser runner.
        MultiBrowserTests().test_distinct_csv_rows_without_json_adapter()

if __name__ == '__main__':
    unittest.main()
