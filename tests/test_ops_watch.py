"""Ops watch's site check finds a failed deploy and broken links, and keeps one red issue."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent.parent / "skills" / "setup"
sys.path.insert(0, str(SETUP))
sys.path.insert(0, str(SETUP / "ops_watch"))
from check_site import TITLE, Response, broken_links, deploy_problems, report_issue, site_problems  # noqa: E402
from install_kit import KITS, install, plan  # noqa: E402

ROOT = "https://owner.github.io/site/"


def page(html, url):
    return Response(200, "text/html", html.encode(), url, None)


class FakeWeb:
    """Answers from a dict of url -> Response; a list answers in turn, for a link that recovers."""

    def __init__(self, answers):
        self.answers = answers
        self.fetched = []

    def __call__(self, url):
        self.fetched.append(url)
        answer = self.answers.get(url, Response(404, None, b"", url, None))
        return answer.pop(0) if isinstance(answer, list) else answer


class FakeGh:
    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def __call__(self, *args, input=None):
        self.calls.append((args, input))
        for prefix, answer in self.answers.items():
            if args[: len(prefix)] == prefix:
                return answer
        return 0, "", ""

    def ran(self, *prefix):
        return [call for call in self.calls if call[0][: len(prefix)] == prefix]


class BrokenLinksTest(unittest.TestCase):
    def check(self, answers):
        return broken_links(ROOT, fetch=FakeWeb(answers), sleep=lambda seconds: None)

    def test_a_site_whose_links_all_resolve_is_green(self):
        answers = {
            ROOT: page('<a href="about.html">About</a> <a href="https://example.com/">x</a>', ROOT),
            ROOT + "about.html": page('<a href="./">Home</a> <img src="logo.png">', ROOT + "about.html"),
            ROOT + "logo.png": Response(200, "image/png", b"", ROOT + "logo.png", None),
            "https://example.com/": Response(200, "text/html", b"", "https://example.com/", None),
        }
        self.assertEqual(self.check(answers), [])

    def test_reports_a_broken_link_and_the_page_it_is_on(self):
        answers = {ROOT: page('<a href="missing.html">gone</a>', ROOT)}
        [problem] = self.check(answers)
        self.assertIn(ROOT + "missing.html answers HTTP 404", problem)
        self.assertIn(f"linked from {ROOT}", problem)

    def test_a_site_that_is_down_is_red(self):
        answers = {ROOT: Response(None, None, b"", ROOT, "Name or service not known")}
        [problem] = self.check(answers)
        self.assertIn("Name or service not known", problem)

    def test_a_link_that_fails_once_and_then_answers_is_not_red(self):
        flaky = "https://example.com/slow"
        answers = {
            ROOT: page(f'<a href="{flaky}">slow</a>', ROOT),
            flaky: [Response(503, None, b"", flaky, None), Response(200, None, b"", flaky, None)],
        }
        self.assertEqual(self.check(answers), [])

    def test_skips_fragments_mail_links_and_connection_hints(self):
        web = FakeWeb({ROOT: page(
            '<a href="#top">top</a> <a href="mailto:a@b.c">mail</a> '
            '<link rel="preconnect" href="https://fonts.gstatic.com">', ROOT)})
        self.assertEqual(broken_links(ROOT, fetch=web, sleep=lambda seconds: None), [])
        self.assertEqual(web.fetched, [ROOT])

    def test_checks_other_sites_links_without_crawling_them(self):
        other = "https://example.com/"
        web = FakeWeb({
            ROOT: page(f'<a href="{other}">other</a>', ROOT),
            other: page('<a href="https://example.com/never">deeper</a>', other),
        })
        broken_links(ROOT, fetch=web, sleep=lambda seconds: None)
        self.assertNotIn("https://example.com/never", web.fetched)


class DeployTest(unittest.TestCase):
    def test_pages_turned_off_is_red(self):
        url, problems = deploy_problems("o/r", gh=FakeGh({("api", "repos/o/r/pages"): (1, "", "Not Found")}))
        self.assertIsNone(url)
        self.assertIn("GitHub Pages is not on", problems[0])

    def test_a_failed_branch_build_is_red(self):
        gh = FakeGh({
            ("api", "repos/o/r/pages/builds/latest"): (0, json.dumps(
                {"status": "errored", "error": {"message": "Liquid syntax error"}}), ""),
            ("api", "repos/o/r/pages"): (0, json.dumps({"html_url": ROOT, "build_type": "legacy"}), ""),
        })
        url, problems = deploy_problems("o/r", gh=gh)
        self.assertEqual(url, ROOT)
        self.assertEqual(problems, ["The latest Pages build failed: Liquid syntax error"])

    def test_a_successful_workflow_deploy_is_green(self):
        gh = FakeGh({
            ("api", "repos/o/r/deployments/7/statuses?per_page=1"): (0, json.dumps([{"state": "success"}]), ""),
            ("api", "repos/o/r/deployments?environment=github-pages&per_page=1"): (0, json.dumps([{"id": 7}]), ""),
            ("api", "repos/o/r/pages"): (0, json.dumps({"html_url": ROOT, "build_type": "workflow"}), ""),
        })
        self.assertEqual(deploy_problems("o/r", gh=gh), (ROOT, []))


class RedIssueTest(unittest.TestCase):
    def open_issues(self, *issues):
        return {("issue", "list"): (0, json.dumps(list(issues)), "")}

    def test_red_with_no_open_issue_opens_one(self):
        gh = FakeGh(self.open_issues())
        self.assertTrue(report_issue("o/r", ["site down"], "run 1", gh=gh))
        [(args, body)] = gh.ran("issue", "create")
        self.assertIn("red", args)
        self.assertIn("- site down", body)

    def test_red_again_updates_the_open_issue_instead_of_opening_another(self):
        gh = FakeGh(self.open_issues({"number": 5, "title": TITLE}))
        report_issue("o/r", ["site down"], "run 2", gh=gh)
        self.assertEqual(gh.ran("issue", "create"), [])
        self.assertEqual(gh.ran("issue", "edit")[0][0][2], "5")

    def test_green_closes_the_open_issue(self):
        gh = FakeGh(self.open_issues({"number": 5, "title": TITLE}))
        self.assertTrue(report_issue("o/r", [], "run 3", gh=gh))
        self.assertEqual(gh.ran("issue", "close")[0][0][2], "5")

    def test_green_leaves_other_red_issues_alone(self):
        gh = FakeGh(self.open_issues({"number": 6, "title": "Backup did not land"}))
        self.assertTrue(report_issue("o/r", [], "run 4", gh=gh))
        self.assertEqual(gh.ran("issue", "close"), [])

    def test_a_refused_change_fails_the_run(self):
        gh = FakeGh({**self.open_issues(), ("issue", "create"): (1, "", "HTTP 403")})
        self.assertFalse(report_issue("o/r", ["site down"], "run 5", gh=gh))


class LiveAddressTest(unittest.TestCase):
    """A product served off GitHub Pages, such as the website on Vercel, names its live address."""

    def test_a_named_address_is_crawled_and_the_pages_api_is_not_asked(self):
        asked = []
        url, problems = site_problems("o/site", "https://site.vercel.app/",
                                      deploy=lambda repo: asked.append(repo) or ("", []),
                                      crawl=lambda url: [f"{url} answers HTTP 503"])
        self.assertEqual(asked, [])
        self.assertEqual((url, problems), ("https://site.vercel.app/", ["https://site.vercel.app/ answers HTTP 503"]))

    def test_without_an_address_the_pages_deploy_is_checked_then_crawled(self):
        url, problems = site_problems("o/site", None,
                                      deploy=lambda repo: (ROOT, ["the latest Pages build failed"]),
                                      crawl=lambda url: [f"{url}x answers HTTP 404"])
        self.assertEqual(url, ROOT)
        self.assertEqual(problems, ["the latest Pages build failed", f"{ROOT}x answers HTTP 404"])

    def test_the_address_comes_from_the_repository_variable_the_workflow_passes(self):
        workflow = (SETUP / "ops_watch" / "ops-watch.yml").read_text()
        self.assertIn("OPS_WATCH_URL: ${{ vars.OPS_WATCH_URL }}", workflow)
        source = (SETUP / "ops_watch" / "check_site.py").read_text()
        self.assertIn('os.environ.get("OPS_WATCH_URL") or None', source)


class InstallTest(unittest.TestCase):
    def test_writes_the_workflow_and_the_check_then_finds_them_up_to_date(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual({state for _, _, state in plan(root, "ops-watch")}, {"new"})
            install(root, plan(root, "ops-watch"))
            for _, target, _ in KITS["ops-watch"]:
                self.assertTrue((root / target).exists())
            self.assertEqual({state for _, _, state in plan(root, "ops-watch")}, {"already up to date"})

    def test_ci_writes_the_workflow_and_a_starter_check_script_that_can_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            install(root, plan(root, "ci"))
            self.assertIn("sh ./check.sh", (root / ".github/workflows/ci.yml").read_text())
            self.assertTrue((root / "check.sh").stat().st_mode & 0o111)

    def test_ci_never_replaces_the_products_own_check_script(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "check.sh").write_text("npx html-validate index.html\n")
            install(root, plan(root, "ci"))
            self.assertEqual((root / "check.sh").read_text(), "npx html-validate index.html\n")
            self.assertIn((Path("check.sh"), "kept: the product's own"),
                          [(target, state) for _, target, state in plan(root, "ci")])

    def test_ci_replaces_an_outdated_copy_of_its_own_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/ci.yml").write_text("name: old\n")
            install(root, plan(root, "ci"))
            self.assertIn("name: ci", (root / ".github/workflows/ci.yml").read_text())


if __name__ == "__main__":
    unittest.main()
