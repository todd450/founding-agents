"""The propose workflow ends in one queue item: each role's recommendation and the team's, the options and how to decide."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

GO = {"repo": "o/site", "issue": 7, "recommend": "go", "reason": "two founders asked for it", "overruled": False,
      "screens": True, "decisions": []}
NO_GO = {**GO, "recommend": "no-go", "reason": "no evidence anyone wants it yet"}


def option(letter, stars):
    base = f"mockups/issue-7/{letter.lower()}"
    return {"letter": letter, "name": f"Option {letter}", "stars": stars, "what": f"{letter} at the key moment.",
            "cost": f"{stars} days", "html": f"{base}.html", "phone": f"{base}-phone.png",
            "desktop": f"{base}-desktop.png"}


def spec(letter, stars):
    return {"letter": letter, "name": f"Option {letter}", "stars": stars, "what": f"{letter} at the key moment.",
            "distinct": f"{letter} is the {stars}-star one.", "cost": f"{stars} days"}


def files(*letters):
    paths = ["mockups/issue-7/storyboard.md"]
    for letter in letters:
        o = option(letter, 0)
        paths += [o["html"], o["phone"], o["desktop"]]
    return {"files": paths}


DESIGN = {"stopped_because": "", "recommended": "B", "why": "B shows the whole journey.",
          "options": [spec("A", 3), spec("B", 6)]}
PUSHED = {"stopped_because": ""}
POSTED = {"comment_url": "https://github.com/o/site/issues/7#issuecomment-1"}


DOOR = {"decision": "How the site deploys", "options": ["GitHub Pages", "Netlify"], "recommend": "GitHub Pages",
        "why": "It already serves the site.", "reverse": "an hour while it is one page"}
BUILT = {**GO, "screens": False, "decisions": [DOOR]}


def view(recommend="go", option="", why="It is a day's work.", decisions=()):
    return {"recommend": recommend, "option": option, "why": why, "decisions": list(decisions)}


VOICES = ["researcher", "architect", "builder", "qa", "code reviewer", "security reviewer", "integrator"]
TEAM = view(option="B", why="Everyone agrees B is worth its six days.")


def replies(lead=GO, design=DESIGN, views=None, team=TEAM, built=None, branch=None):
    views = views or {}
    out = {"product lead": [lead], "team": [team], "queue": [POSTED]}
    out.update({voice: [views.get(voice, view(option="B" if design else ""))] for voice in VOICES})
    if design:
        letters = [o["letter"] for o in design["options"]]
        built = built or {}
        out["storyboard"] = [design]
        out.update({f"option {letter}": [built.get(letter, PUSHED)] for letter in letters})
        out["design check"] = [branch or files(*[l for l in letters if not built.get(l, PUSHED)["stopped_because"]])]
    return out


@unittest.skipUnless(HAVE_NODE, "needs node")
class ProposeWorkflowTest(unittest.TestCase):
    def call(self, run, label):
        [call] = [call for call in run["calls"] if call["label"] == label]
        return call

    def queue_item(self, run):
        return self.call(run, "queue item")["prompt"]

    def labels(self, run):
        return [call["label"] for call in run["calls"]]

    def test_an_issue_number_is_shaped_in_place(self):
        run = run_workflow("propose", replies(), 7)
        self.assertIn("Shape issue #7", run["calls"][0]["prompt"])
        self.assertEqual(run["result"]["queue_item"], POSTED["comment_url"])

    def test_an_idea_in_words_becomes_a_new_issue(self):
        run = run_workflow("propose", replies(), "a pricing page")
        prompt = run["calls"][0]["prompt"]
        self.assertIn("open it as a new issue", prompt)
        self.assertIn("a pricing page", prompt)

    def test_each_role_runs_as_its_plugin_agent_and_each_designer_in_a_worktree(self):
        run = run_workflow("propose", replies(), 7)
        lead = self.call(run, "product lead")
        self.assertEqual((lead["agentType"], lead["model"]), ("founding-agents:product-lead", "opus"))
        for label in ["storyboard", "option A", "option B"]:
            designer = self.call(run, label)
            self.assertEqual((designer["agentType"], designer["isolation"], designer["model"]),
                             ("founding-agents:designer", "worktree", "opus"))
        self.assertEqual(self.call(run, "design check")["model"], "haiku")
        for voice in VOICES:
            self.assertEqual((self.call(run, voice)["agentType"], self.call(run, voice)["model"]),
                             (f"founding-agents:{voice.replace(' ', '-')}", "sonnet"))
        self.assertEqual(self.call(run, "team")["model"], "opus")
        self.assertEqual(self.call(run, "queue item")["model"], "haiku")

    def test_the_queue_item_gives_the_teams_recommendation_then_each_roles_with_why(self):
        views = {"builder": view(option="A", why="A is two days less work."),
                 "qa": view(option="B", why="B is easier to check on a phone."),
                 "integrator": view(option="B", why="Neither changes how the site goes live.")}
        team = view(option="B", why="B shows the whole journey; the builder prefers A to save two days.")
        item = self.queue_item(run_workflow("propose", replies(views=views, team=team), 7))
        self.assertIn("### What the team recommends", item)
        self.assertIn("**The team: go, option B.** B shows the whole journey; the builder prefers A to save two days.", item)
        self.assertIn("- **Product lead:** go. two founders asked for it", item)
        self.assertIn("- **Designer:** option B. B shows the whole journey.", item)
        self.assertIn("- **Builder:** go, option A. A is two days less work.", item)
        self.assertIn("- **QA:** go, option B. B is easier to check on a phone.", item)
        self.assertIn("- **Integrator:** go, option B. Neither changes how the site goes live.", item)
        self.assertLess(item.index("**The team:"), item.index("**Product lead:**"))

    def test_each_role_forms_its_own_view_and_the_team_weighs_them_all(self):
        run = run_workflow("propose", replies(), 7)
        builder = self.call(run, "builder")["prompt"]
        self.assertIn("A. Option A, 3 stars", builder)
        self.assertIn("plain English", builder)
        self.assertIn("Read only", builder)
        self.assertNotIn("two founders asked for it", builder)
        self.assertNotIn("B shows the whole journey", builder)
        team = self.call(run, "team")["prompt"]
        self.assertIn("- Product lead: go. two founders asked for it", team)
        self.assertIn("- Designer: option B. B shows the whole journey.", team)
        self.assertIn("- Integrator: go, option B.", team)
        self.assertIn("do not count votes", team)

    def test_the_queue_item_shows_every_option_with_screenshots_cost_and_the_teams_pick(self):
        item = self.queue_item(run_workflow("propose", replies(team={**TEAM, "option": "A"}), 7))
        self.assertIn("### A. Option A (recommended): 3 stars", item)
        self.assertIn("### B. Option B: 6 stars", item)
        self.assertIn("https://github.com/o/site/blob/propose/issue-7/mockups/issue-7/b-phone.png?raw=true", item)
        self.assertIn("**Cost:** 6 days", item)
        self.assertIn("add the `decided` label", item)
        self.assertIn("/founding-agents:plan 7", item)

    def test_a_role_or_team_that_returns_nothing_still_leaves_a_queue_item(self):
        r = replies()
        r["qa"], r["team"] = [None], [None]
        run = run_workflow("propose", r, 7)
        item = self.queue_item(run)
        self.assertIn("**The team** gave no overall recommendation", item)
        self.assertNotIn("**QA:**", item)
        self.assertIn("- **Builder:** go, option B.", item)
        self.assertIn("### B. Option B (recommended)", item)
        self.assertEqual(run["result"]["team"], "")

    def test_a_no_go_skips_the_designer_and_still_reaches_the_founder_with_every_view(self):
        run = run_workflow("propose", replies(lead=NO_GO, design=None, team=view("no-go", why="Nobody has asked yet.")), 7)
        self.assertEqual(self.labels(run), ["product lead", *VOICES, "team", "queue item", "tidy worktrees", "run report"])
        item = self.queue_item(run)
        self.assertIn("**The team: no-go.** Nobody has asked yet.", item)
        self.assertIn("- **Product lead:** no-go. no evidence anyone wants it yet", item)
        self.assertNotIn("**Designer:**", item)
        self.assertIn("close the issue", item)
        self.assertEqual(run["result"]["options"], [])

    def test_an_overruled_no_go_gets_mockups_and_keeps_the_honest_recommendation(self):
        run = run_workflow("propose", replies(lead={**NO_GO, "overruled": True}), 7)
        self.assertEqual(self.labels(run),
                         ["product lead", "storyboard", "option A", "option B", "design check", *VOICES, "team", "queue item",
                          "tidy worktrees", "run report"])
        item = self.queue_item(run)
        self.assertIn("- **Product lead:** no-go.", item)
        self.assertIn("You overruled the no-go", item)
        self.assertIn("### B. Option B (recommended)", item)

    def test_a_designer_that_stops_posts_no_queue_item(self):
        stopped = {**DESIGN, "stopped_because": "Chrome is missing", "options": []}
        run = run_workflow("propose", replies(design=stopped), 7)
        self.assertEqual(run["result"]["status"], "stopped in design")
        self.assertEqual(run["result"]["reason"], "Chrome is missing")
        self.assertNotIn("queue item", self.labels(run))
        self.assertNotIn("team", self.labels(run))
        self.assertNotIn("option A", self.labels(run))

    def test_the_options_are_built_at_the_same_time_after_the_storyboard(self):
        run = run_workflow("propose", replies(), 7, slow={"option": 200})
        events = run["events"]
        self.assertLess(events.index("end storyboard"), events.index("start option A"))
        self.assertLess(events.index("start option B"), events.index("end option A"))
        self.assertLess(max(events.index("end option A"), events.index("end option B")), events.index("start design check"))

    def test_the_storyboard_commits_only_itself_and_each_option_only_its_own_files(self):
        run = run_workflow("propose", replies(), 7)
        storyboard = self.call(run, "storyboard")["prompt"]
        self.assertIn("`mockups/issue-7/storyboard.md`", storyboard)
        self.assertIn("Do not build the pages", storyboard)
        self.assertIn("screenshots can be taken", storyboard)
        self.assertIn("removing anything an earlier run left in `mockups/issue-7`", storyboard)
        a = self.call(run, "option A")["prompt"]
        self.assertIn("`mockups/issue-7/a.html`", a)
        self.assertIn("What sets it apart: A is the 3-star one.", a)
        self.assertIn("B. Option B, 6 stars", a)
        self.assertIn("git switch --detach FETCH_HEAD", a)
        self.assertIn("git push origin HEAD:propose/issue-7", a)
        self.assertIn("git pull --rebase origin propose/issue-7", a)
        self.assertNotIn("b.html", a)

    def test_the_queue_item_takes_its_paths_from_the_branch_and_links_the_storyboard(self):
        item = self.queue_item(run_workflow("propose", replies(), 7))
        self.assertIn("https://github.com/o/site/blob/propose/issue-7/mockups/issue-7/storyboard.md", item)
        self.assertIn("https://github.com/o/site/blob/propose/issue-7/mockups/issue-7/a-desktop.png?raw=true", item)
        self.assertNotIn("not built", item)

    def test_an_option_that_was_not_built_is_left_out_while_two_remain(self):
        three = {**DESIGN, "options": [spec("A", 3), spec("B", 6), spec("C", 9)]}
        run = run_workflow("propose", replies(design=three, built={"C": {"stopped_because": "the push never landed"}}), 7)
        item = self.queue_item(run)
        self.assertIn("### B. Option B (recommended): 6 stars", item)
        self.assertNotIn("### C.", item)
        self.assertIn("not offered: option C: the push never landed.", item)
        self.assertNotIn("C. Option C", self.call(run, "builder")["prompt"])
        self.assertEqual(run["result"]["options"], ["A", "B"])

    def test_an_option_missing_from_the_branch_is_left_out_whatever_its_designer_said(self):
        three = {**DESIGN, "options": [spec("A", 3), spec("B", 6), spec("C", 9)]}
        item = self.queue_item(run_workflow("propose", replies(design=three, branch=files("A", "B")), 7))
        self.assertNotIn("### C.", item)
        self.assertIn("option C: it is not on the branch", item)

    def test_an_option_that_stopped_is_left_out_even_with_an_earlier_runs_page_on_the_branch(self):
        three = {**DESIGN, "options": [spec("A", 3), spec("B", 6), spec("C", 9)]}
        r = replies(design=three, built={"C": {"stopped_because": "a blank screenshot"}}, branch=files("A", "B", "C"))
        self.assertNotIn("### C.", self.queue_item(run_workflow("propose", r, 7)))

    def test_fewer_than_two_options_built_stops_in_design_with_the_reasons(self):
        run = run_workflow("propose", replies(built={"A": {"stopped_because": "Chrome is missing"}}), 7)
        self.assertEqual(run["result"]["status"], "stopped in design")
        self.assertIn("fewer than two options; option A: Chrome is missing", run["result"]["reason"])
        self.assertNotIn("queue item", self.labels(run))

    def test_a_pick_that_was_not_built_stops_in_design(self):
        three = {**DESIGN, "options": [spec("A", 3), spec("B", 6), spec("C", 9)]}
        run = run_workflow("propose", replies(design=three, built={"B": {"stopped_because": "a blank screenshot"}}), 7)
        self.assertEqual(run["result"]["status"], "stopped in design")
        self.assertIn("the designer's pick was not built; option B: a blank screenshot", run["result"]["reason"])

    def test_a_branch_with_more_than_mockups_stops_in_design(self):
        branch = files("A", "B")
        branch["files"].append("src/index.html")
        run = run_workflow("propose", replies(branch=branch), 7)
        self.assertEqual(run["result"]["status"], "stopped in design")
        self.assertEqual(run["result"]["reason"], "the branch holds more than mockups: src/index.html")

    def test_the_report_goes_on_the_issue_the_product_lead_shaped(self):
        run = run_workflow("propose", replies(), "a pricing page")
        self.assertIn("--workflow propose --issue 7 --budget 5 --post", run["calls"][-1]["prompt"])

    def test_each_technical_decision_shows_the_teams_choice_and_each_roles(self):
        door = {"decision": "How the site is built", "options": ["plain HTML", "a static site generator"],
                "recommend": "plain HTML", "why": "One page needs nothing more.", "reverse": "half a day while it is one page"}
        builder = view(option="B", decisions=[{"id": "D1", "choice": "a static site generator", "why": "Pages will repeat."}])
        team = {**TEAM, "decisions": [{"id": "D1", "choice": "plain HTML", "why": "It is one page for now."}]}
        run = run_workflow("propose", replies(lead={**GO, "decisions": [door]}, views={"builder": builder}, team=team), 7)
        item = self.queue_item(run)
        self.assertIn("### Technical decisions", item)
        self.assertIn("- **D1. How the site is built:** plain HTML / a static site generator. "
                      "Reversing it later: half a day while it is one page", item)
        self.assertIn("  - **The team: plain HTML.** It is one page for now.", item)
        self.assertIn("  - Product lead: plain HTML. One page needs nothing more.", item)
        self.assertIn("  - Builder: a static site generator. Pages will repeat.", item)
        self.assertIn("your choice for each technical decision (D1)", item)
        self.assertIn("D1. How the site is built: plain HTML / a static site generator", self.call(run, "builder")["prompt"])

    def test_a_brief_that_settles_no_technical_decision_says_so(self):
        item = self.queue_item(run_workflow("propose", replies(), 7))
        self.assertIn("**Technical decisions:** none.", item)
        self.assertNotIn("each technical decision", item)

    def test_the_product_lead_is_asked_to_name_decisions_including_ones_taken_for_granted(self):
        prompt = run_workflow("propose", replies(lead=NO_GO, design=None), 7)["calls"][0]["prompt"]
        self.assertIn('"Technical decisions"', prompt)
        self.assertIn('"a static site"', prompt)

    def test_a_brief_with_nothing_on_screen_skips_the_designer_and_asks_only_the_decisions(self):
        run = run_workflow("propose", replies(lead=BUILT, design=None), 7)
        self.assertEqual(self.labels(run), ["product lead", *VOICES, "team", "queue item", "tidy worktrees", "run report"])
        self.assertNotIn("one option", self.call(run, "builder")["prompt"])
        item = self.queue_item(run)
        self.assertIn("**D1. How the site deploys:** GitHub Pages / Netlify", item)
        self.assertIn("reply with your choice for each technical decision (D1) and any notes, then add the `decided` label", item)
        self.assertNotIn("which option", item)
        self.assertNotIn("again for mockups", item)

    def test_an_overruled_no_go_with_nothing_on_screen_is_decided_without_mockups(self):
        run = run_workflow("propose", replies(lead={**BUILT, "recommend": "no-go", "overruled": True}, design=None), 7)
        self.assertNotIn("designer", self.labels(run))
        item = self.queue_item(run)
        self.assertIn("say so in a reply with your choice for each technical decision (D1), then add the `decided` label", item)

    def test_the_queue_item_adds_the_needs_founder_label(self):
        item = self.queue_item(run_workflow("propose", replies(lead=NO_GO, design=None), 7))
        self.assertIn("--add-label needs-founder", item)

    def test_nothing_to_propose_is_an_error(self):
        self.assertIn("Name an issue", run_workflow("propose", {}, None)["error"])


if __name__ == "__main__":
    unittest.main()
