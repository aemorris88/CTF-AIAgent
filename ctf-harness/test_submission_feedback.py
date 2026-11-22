
import unittest

from harness.platform.browser_ctf import (
    classify_submission_feedback,
)


class SubmissionFeedbackTests(unittest.TestCase):

    def test_new_point_award(self):
        before = (
            "Base Case\n"
            "Time spent solving challenge: 00:02\n"
            "Number of attempts made: 0"
        )

        after = (
            "ACCESS GRANTED\n"
            "+100 pts\n"
            "Base Case\n"
            "Time spent solving challenge: 00:03\n"
            "Number of attempts made: 1"
        )

        self.assertEqual(
            classify_submission_feedback(before, after),
            "accepted"
        )

    def test_rejected_flag(self):
        before = "Base Case\nNumber of attempts made: 0"
        after = (
            "Base Case\n"
            "Incorrect flag. Try again.\n"
            "Number of attempts made: 1"
        )

        self.assertEqual(
            classify_submission_feedback(before, after),
            "rejected"
        )

    def test_unknown_feedback(self):
        before = "Base Case\nTime spent solving: 00:02"
        after = "Base Case\nTime spent solving: 00:03"

        self.assertEqual(
            classify_submission_feedback(before, after),
            "unknown"
        )

    def test_old_point_award(self):
        before = "ACCESS GRANTED\n+100 pts\nBase Case"
        after = (
            "ACCESS GRANTED\n+100 pts\n"
            "Base Case\nTime spent solving: 00:05"
        )

        self.assertEqual(
            classify_submission_feedback(before, after),
            "unknown"
        )


if __name__ == "__main__":
    unittest.main()
