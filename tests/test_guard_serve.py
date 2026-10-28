"""The serve guard blocks a local preview that listens beyond this machine or serves a secret."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "hooks" / "guard_serve.py"


class ServeGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "site").mkdir()
        (self.repo / "site" / "index.html").write_text("<h1>Hi</h1>")

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, command, agent="founding-agents:qa"):
        event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(self.repo), "agent_type": agent}
        result = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event), capture_output=True, text=True)
        return result.returncode, result.stderr

    def test_an_unbound_server_is_blocked_with_the_command_to_use(self):
        # The command Half Badger's issues gave, and the plugin's own agents used, before 27 Oct 2026.
        for command in ("cd site && python3 -m http.server", "python3 -m http.server 0", "python -m http.server 8000 &",
                        "nohup python3 -m http.server 8823 --directory site > /dev/null 2>&1 &",
                        "python3 -m http.server 8000 --bind 0.0.0.0"):
            code, message = self.check(command)
            self.assertEqual(code, 2, command)
            self.assertIn("python3 -m http.server 0 --bind 127.0.0.1", message)

    def test_a_server_bound_to_this_machine_passes(self):
        for command in ("cd site && python3 -m http.server 0 --bind 127.0.0.1",
                        "python3 -m http.server 8823 -b localhost --directory site",
                        "(cd site && python3 -m http.server --bind=::1 0) &"):
            self.assertEqual(self.check(command)[0], 0, command)

    def test_a_folder_holding_a_secret_is_not_served_even_when_bound(self):
        # Half Badger kept a Vercel token in site/, the folder its issues served.
        (self.repo / "site" / ".env.local").write_text("VERCEL_TOKEN=x")
        code, message = self.check("cd site && python3 -m http.server 0 --bind 127.0.0.1")
        self.assertEqual(code, 2)
        self.assertIn(".env.local", message)
        self.assertIn("--directory", message)

    def test_a_secret_a_level_down_or_in_a_vercel_folder_counts_too(self):
        (self.repo / "site" / "assets" / ".vercel").mkdir(parents=True)
        self.assertEqual(self.check("python3 -m http.server 0 --bind 127.0.0.1 --directory site")[0], 2)

    def test_a_secret_outside_the_served_folder_does_not_block(self):
        (self.repo / ".env").write_text("TOKEN=x")
        (self.repo / "site" / ".env.example").write_text("TOKEN=")
        self.assertEqual(self.check("python3 -m http.server 0 --bind 127.0.0.1 --directory site")[0], 0)
        self.assertEqual(self.check("python3 -m http.server 0 --bind 127.0.0.1")[0], 2)

    def test_it_holds_for_every_session_and_ignores_other_commands(self):
        self.assertEqual(self.check("python3 -m http.server", agent=None)[0], 2)
        self.assertEqual(self.check("grep -rn http.server docs/")[0], 0)
        self.assertEqual(self.check("python3 -m pytest")[0], 0)


if __name__ == "__main__":
    unittest.main()
