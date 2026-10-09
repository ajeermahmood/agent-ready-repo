"""Tests for block-secret-reads.py.

Half of these assert the hook stays QUIET. That is the half that matters: a
guardrail that blocks ordinary work gets switched off, and then it blocks nothing.

Run: python -m unittest discover -s .claude/hooks -p "test_*.py"
"""

import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("hook", HERE / "block-secret-reads.py")
hook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hook)


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class BlocksRealReads(unittest.TestCase):
    def test_printing_the_env_file(self):
        self.assertTrue(hook.blocked(bash("cat .env")))
        self.assertTrue(hook.blocked(bash("head -n 5 config/.env.production")))

    def test_a_template_beside_the_real_file_does_not_excuse_it(self):
        self.assertTrue(hook.blocked(bash("cat .env.example .env")))

    def test_inside_a_pipeline(self):
        self.assertTrue(hook.blocked(bash("ls && cat .env | grep DB")))

    def test_an_interpreter_naming_the_file(self):
        self.assertTrue(hook.blocked(bash("python -c \"print(open('.env').read())\"")))
        self.assertTrue(hook.blocked(bash("node -e \"require('fs').readFileSync('.env')\"")))

    def test_powershell(self):
        self.assertTrue(hook.blocked({"tool_name": "PowerShell", "tool_input": {"command": "Get-Content .env"}}))

    def test_private_keys(self):
        self.assertTrue(hook.blocked(bash("cat ~/.ssh/id_ed25519")))
        self.assertTrue(hook.blocked(bash("base64 deploy.pem")))

    def test_file_tools(self):
        self.assertTrue(hook.blocked({"tool_name": "Read", "tool_input": {"file_path": "/repo/.env"}}))
        self.assertTrue(hook.blocked({"tool_name": "Grep", "tool_input": {"path": ".env.local"}}))


class StaysQuietOnOrdinaryWork(unittest.TestCase):
    def test_names_and_metadata_are_not_contents(self):
        for command in ("ls -la .env", "git check-ignore .env", "stat .env", "rm .env.bak", "test -f .env"):
            self.assertFalse(hook.blocked(bash(command)), command)

    def test_templates_are_readable(self):
        self.assertFalse(hook.blocked(bash("cat .env.example")))
        self.assertFalse(hook.blocked({"tool_name": "Read", "tool_input": {"file_path": ".env.example"}}))

    def test_searching_for_the_pattern_is_not_reading_the_file(self):
        self.assertFalse(hook.blocked(bash('grep -rn "\\.env" src/')))
        self.assertFalse(hook.blocked(bash('git ls-files | grep "\\.env"')))

    def test_writing_a_script_that_mentions_env(self):
        command = "cat > setup.sh <<'EOF'\necho 'copy .env.example to .env'\ncat .env\nEOF"
        self.assertFalse(hook.blocked(bash(command)))

    def test_unrelated_commands(self):
        for command in ("npm test", "git status", "cat README.md", "grep -rn TODO src"):
            self.assertFalse(hook.blocked(bash(command)), command)


class ProcessContract(unittest.TestCase):
    """The exit codes Claude Code reads: 2 blocks and returns stderr, 0 allows."""

    def run_hook(self, stdin: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(HERE / "block-secret-reads.py")],
            input=stdin, capture_output=True, text=True, timeout=20,
        )

    def test_block_exits_2_with_a_reason(self):
        r = self.run_hook(json.dumps(bash("cat .env")))
        self.assertEqual(r.returncode, 2)
        self.assertIn("Blocked", r.stderr)

    def test_allow_exits_0_silently(self):
        r = self.run_hook(json.dumps(bash("npm test")))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, "")

    def test_a_malformed_payload_never_breaks_the_session(self):
        self.assertEqual(self.run_hook("not json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
