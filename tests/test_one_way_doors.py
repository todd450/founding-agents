"""Both workflows define a technical one-way door in the same words, so they judge the same way."""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"


def one_way(name):
    match = re.search(r"^const ONE_WAY = '(.+)'$", (WORKFLOWS / name).read_text(), re.M)
    return match.group(1) if match else None


class OneWayDoorTest(unittest.TestCase):
    def test_build_and_propose_use_the_same_definition(self):
        self.assertIsNotNone(one_way("build.js"))
        self.assertEqual(one_way("build.js"), one_way("propose.js"))


if __name__ == "__main__":
    unittest.main()
