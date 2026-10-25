"""Setup's branch protection requires a PR and the checks, and binds admins too."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "setup"))
from protect_branch import build_protection  # noqa: E402


class ProtectionTest(unittest.TestCase):
    def test_requires_a_pull_request_and_binds_admins(self):
        protection = build_protection([])
        self.assertTrue(protection["enforce_admins"])
        self.assertEqual(protection["required_pull_request_reviews"]["required_approving_review_count"], 0)
        self.assertFalse(protection["allow_force_pushes"])
        self.assertFalse(protection["allow_deletions"])

    def test_requires_checks_on_an_up_to_date_branch(self):
        checks = build_protection(["test", "lint"])["required_status_checks"]
        self.assertTrue(checks["strict"])
        self.assertEqual(checks["checks"], [{"context": "test"}, {"context": "lint"}])

    def test_without_ci_requires_no_checks(self):
        self.assertIsNone(build_protection([])["required_status_checks"])


if __name__ == "__main__":
    unittest.main()
