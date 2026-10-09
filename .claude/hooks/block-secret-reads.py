#!/usr/bin/env python3
"""Claude Code PreToolUse hook that keeps an agent from printing secret files.

How Claude Code uses it
    Before a tool runs, Claude Code sends the tool name and its input to this
    script as JSON on stdin. Exiting with 2 cancels the tool call, and whatever
    is on stderr is shown to the model as the reason. Exiting with 0 lets the
    call go ahead.

What it guards against
    Mistakes. An agent that wants to know which database URL is configured will
    happily run `cat .env`, and the value then sits in the conversation log.
    This script cancels that kind of call and tells the agent what to do instead.

What it does not guard against
    A determined process. Any program running as you can read your files in
    countless ways this script will never see. Keep production credentials off
    the machine if you need real isolation.

Why it is picky
    If it fired every time a command mentioned `.env`, people would turn it off
    within a day. So it only fires when a secret file is actually handed to a
    command that prints file contents. Listing the file, checking whether git
    ignores it, or writing a script that talks about it all pass.

Adapting it
    Add your own secret file patterns to MORE_SECRET_FILES.
"""

import json
import re
import shlex
import sys

# Extra secret files for your project, as regular-expression fragments,
# for example r"credentials\.json" or r"service-account\.json".
MORE_SECRET_FILES: list[str] = []

SECRET_FILE_PATTERNS = [
    r"\.env(\.[A-Za-z0-9_.-]+)?",       # .env and its variants
    r"id_(rsa|ed25519)",                # SSH private keys
    r"[A-Za-z0-9_.-]*\.(pem|key|p12|pfx)",  # certificates and key stores
] + MORE_SECRET_FILES

_ANY_SECRET = "|".join(SECRET_FILE_PATTERNS)

# A secret file name appearing anywhere, bounded so `.envrc-tools` does not count.
MENTIONS_SECRET = re.compile(r"(?:^|[\s/\\'\"=(,;|&])(?:" + _ANY_SECRET + r")(?:$|[^A-Za-z0-9_.-])", re.I)

# A single argument that is itself a path ending in a secret file.
IS_SECRET_PATH = re.compile(r"^[\w./\\~:-]*?(?:" + _ANY_SECRET + r")$", re.I)

# Example files list variable names with dummy values, so they are always safe.
EXAMPLE_FILE = re.compile(r"\.env\.(?:example|sample|template)", re.I)

# Characters that only appear in a search pattern, never in a real file name.
# `grep "\.env" src/` is searching for the text, not opening the file.
LOOKS_LIKE_PATTERN = re.compile(r"[|*+?()\[\]{}^$]|\\\.")

# Commands whose job is to show, copy or transform what is inside a file.
PRINTING_COMMANDS = {
    ".", "ack", "awk", "base64", "bat", "cat", "copy", "cp", "cut", "egrep",
    "fgrep", "gc", "get-content", "grep", "head", "hexdump", "less", "more",
    "nl", "od", "rg", "rsync", "scp", "sed", "select-string", "sort",
    "source", "strings", "tail", "tee", "tr", "type", "uniq", "wc", "xxd",
}

# Commands that run code, where the file could be opened from inside a string.
SCRIPT_RUNNERS = {"bun", "deno", "node", "perl", "php", "py", "python", "python3", "ruby"}

# Words that come before the real command and should be skipped over.
LEADING_WORDS = {"\\", "builtin", "command", "env", "exec", "nohup", "sudo", "time"}

HEREDOC_BODY = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)

REFUSAL = (
    "Blocked: that would read the contents of a secret file.\n"
    "\n"
    "Do not read or print secret values. Refer to the variable by NAME, and\n"
    "read .env.example to see which names exist. If a program needs a secret,\n"
    "let it load the value from the environment when it runs.\n"
)


def drop_heredoc_bodies(command: str) -> str:
    """Text inside a heredoc is being written, not read, so ignore it."""
    return HEREDOC_BODY.sub(" ", command)


def first_command(segment: str) -> str:
    """The program a pipeline segment runs, ignoring `sudo` and `NAME=value`."""
    for word in segment.split():
        word = word.strip("(){}")
        if not word or word.lower() in LEADING_WORDS:
            continue
        if "=" in word and not word.startswith("-") and "/" not in word:
            continue
        return re.split(r"[/\\]", word)[-1].lower()
    return ""


def split_words(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:  # unbalanced quotes; fall back to plain splitting
        return segment.split()


def prints_a_secret(command: str) -> bool:
    """True if any part of a shell command prints a secret file's contents."""
    for segment in re.split(r"\|\||&&|[|;\n]", drop_heredoc_bodies(command)):
        # Ignore example files before deciding, so that naming one beside a real
        # secret, as in `cat .env.example .env`, does not excuse the real one.
        if not MENTIONS_SECRET.search(EXAMPLE_FILE.sub(" ", segment)):
            continue
        program = first_command(segment)
        if program in SCRIPT_RUNNERS:
            return True
        if program in PRINTING_COMMANDS:
            arguments = split_words(segment)[1:]
            if any(
                IS_SECRET_PATH.match(arg)
                and not LOOKS_LIKE_PATTERN.search(arg)
                and not EXAMPLE_FILE.search(arg)
                for arg in arguments
            ):
                return True
    return False


def touches_a_secret(path: str) -> bool:
    return bool(path) and bool(MENTIONS_SECRET.search(path)) and not EXAMPLE_FILE.search(path)


def blocked(event: dict) -> bool:
    """Decide for one PreToolUse event whether to cancel the tool call."""
    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}

    if tool in {"Bash", "PowerShell"}:
        return prints_a_secret(str(args.get("command", "")))
    if tool in {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit"}:
        return touches_a_secret(str(args.get("file_path", "")))
    if tool in {"Grep", "Glob"}:
        return touches_a_secret(str(args.get("path", ""))) or touches_a_secret(str(args.get("glob", "")))
    return False


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0  # a malformed event should never stop the session
    if blocked(event):
        sys.stderr.write(REFUSAL)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
