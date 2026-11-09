"""Every workflow and the sweeps define a technical one-way door in the same words, so they judge the same way."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / "workflows"


def one_way(name):
    match = re.search(r"^const ONE_WAY = '(.+)'$", (WORKFLOWS / name).read_text(), re.M)
    return match.group(1) if match else None


class OneWayDoorTest(unittest.TestCase):
    def test_every_workflow_uses_the_same_definition(self):
        self.assertIsNotNone(one_way("build.js"))
        self.assertEqual(one_way("build.js"), one_way("propose.js"))

    def test_the_sweeps_use_the_same_definition(self):
        rules = " ".join((ROOT / "skills/sweep/kinds/every-sweep.md").read_text().split())
        self.assertIn(one_way("build.js"), rules)


if __name__ == "__main__":
    unittest.main()
