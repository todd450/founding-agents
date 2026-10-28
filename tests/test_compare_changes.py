"""The comparison groups PRs by label or build branch, prices them from run reports, and finds fixes."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "compare-changes"))
from compare import change, follow_ups, group, hours_to_merge, report, run_costs  # noqa: E402

NOW = datetime(2026, 11, 30, tzinfo=timezone.utc)


def pr(number, merged, title="A change", labels=(), branch="feat/x", paths=("index.html",),
       first=None, issues=()):
    return {"number": number, "title": title, "labels": [{"name": n} for n in labels],
            "headRefName": branch, "createdAt": merged, "mergedAt": merged,
            "files": [{"path": p} for p in paths],
            "commits": [{"authoredDate": first}] if first else [],
            "closingIssuesReferences": [{"number": n} for n in issues]}


class GroupTest(unittest.TestCase):
    def test_a_build_branch_counts_as_with_the_plugin_without_a_label(self):
        self.assertEqual(group(pr(1, "2026-10-01T00:00:00Z", branch="build/issue-12")), "with")

    def test_labels_decide_the_rest(self):
        self.assertEqual(group(pr(1, "2026-10-01T00:00:00Z", labels=["without-plugin"])), "without")
        self.assertEqual(group(pr(1, "2026-10-01T00:00:00Z", labels=["with-plugin"])), "with")

    def test_a_pr_with_neither_is_left_out(self):
        self.assertIsNone(group(pr(1, "2026-10-01T00:00:00Z", branch="build/notes")))


class FollowUpTest(unittest.TestCase):
    def setUp(self):
        self.change = pr(1, "2026-10-01T00:00:00Z", paths=["index.html", "README.md"])

    def test_a_later_fix_to_the_same_file_within_two_weeks_counts(self):
        fix = pr(2, "2026-10-10T00:00:00Z", title="Fix the status band", paths=["index.html"])
        self.assertEqual(follow_ups(self.change, [self.change, fix]), [2])

    def test_a_bug_label_or_a_revert_counts_as_a_fix(self):
        labelled = pr(2, "2026-10-05T00:00:00Z", title="Tidy the band", labels=["bug"])
        revert = pr(3, "2026-10-06T00:00:00Z", title='Revert "Site 2 of 3"')
        self.assertEqual(follow_ups(self.change, [labelled, revert]), [2, 3])

    def test_other_files_later_merges_and_non_fixes_do_not_count(self):
        others = [pr(2, "2026-10-05T00:00:00Z", title="Fix CI", paths=["ci.yml"]),
                  pr(3, "2026-10-20T00:00:00Z", title="Fix the band"),
                  pr(4, "2026-09-30T00:00:00Z", title="Fix the band"),
                  pr(5, "2026-10-05T00:00:00Z", title="Add a prefix to the heading")]
        self.assertEqual(follow_ups(self.change, others), [])


class CostAndTimeTest(unittest.TestCase):
    def test_reads_the_total_from_each_run_report(self):
        bodies = ["**Run report** · `propose` #6 · 12 min · $1.50 at API prices\n\n| Role |",
                  "Looks good", "**Run report** · `build` #6 · 29 min · $6.19 at API prices"]
        self.assertEqual(run_costs(bodies), [1.50, 6.19])

    def test_time_to_merge_runs_from_the_first_commit(self):
        self.assertEqual(hours_to_merge(pr(1, "2026-10-01T03:00:00Z", first="2026-10-01T01:30:00Z")), 1.5)

    def test_a_change_counts_the_reports_on_its_pr_and_the_issues_it_closes(self):
        built = pr(9, "2026-10-26T19:54:40Z", branch="build/issue-6", issues=[6])
        posted = {6: ["**Run report** · `build` #6 · 70 min · $9.00 at API prices"],
                  9: ["**Run report** · s1 · 3 min · $0.50 at API prices"]}
        row = change(built, [built], lambda n: posted.get(n, []), NOW)
        self.assertAlmostEqual(row["cost"], 9.50)

    def test_a_change_without_a_report_has_no_cost_rather_than_zero(self):
        plain = pr(3, "2026-10-26T00:00:00Z", labels=["without-plugin"])
        self.assertIsNone(change(plain, [plain], lambda n: [], NOW)["cost"])


class ReportTest(unittest.TestCase):
    def test_counts_changes_still_inside_two_weeks_apart(self):
        old = pr(1, "2026-10-01T00:00:00Z", branch="build/issue-1")
        recent = pr(2, "2026-11-25T00:00:00Z", branch="build/issue-2")
        fix = pr(3, "2026-10-03T00:00:00Z", title="Fix the band")
        rows = [change(p, [old, recent, fix], lambda n: [], NOW) for p in (old, recent)]
        text = report(rows, "todd450/site")
        self.assertIn("| With the plugin | 2 | none reported |", text)
        self.assertIn("1 of 1 (1 merged under two weeks ago)", text)
        self.assertIn("| Without it | 0 |", text)
        self.assertIn("| #1 A change | with | not reported | 0 min | #3 |", text)


if __name__ == "__main__":
    unittest.main()
