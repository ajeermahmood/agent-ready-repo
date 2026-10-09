#!/usr/bin/env python3
"""PreToolUse hook: stop a coding agent reading secret files by accident.

Claude Code runs this before every Bash, PowerShell, Read, Edit, Write, Grep and
Glob call, passing the tool input as JSON on stdin. Exit 2 blocks the call and
hands the message on stderr back to the model. Exit 0 allows it.

WHAT THIS IS FOR
    The accident: an agent running `cat .env`, grepping the repo for a variable
    and catching its value, or piping a secret into a command whose output lands
    in the transcript. That is the leak that actually happens.

WHAT THIS IS NOT
    A security boundary. A shell is a universal interpreter: base64, a one-line
    script, an editor, a renamed copy. Anything running as your user can read
    what you can read. Treat this as a guardrail against mistakes, not as
    containment of a hostile agent.

FALSE POSITIVES MATTER
    A guardrail that fires on innocent commands gets switched off, and a hook
    that is switched off protects nothing. So this checks whether a protected
    file is the OPERAND OF A COMMAND THAT PRINTS CONTENTS, not whether the
    command text mentions it. `ls -la .env`, `git check-ignore .env` and a
    script that writes the word `.env` are all allowed. `cat .env` is not.

TO ADAPT
    Add your own secret files to EXTRA_PROTECTED below. Keep the list short.
"""

import json
import re
import shlex
import sys

# Your project's own secret files, as regex fragments. Examples:
#   r"secrets\.json", r"credentials\.yml", r"service-account\.json"
EXTRA_PROTECTED: list[str] = []

_BASE = [
    r"\.env(\.[A-Za-z0-9_.-]+)?",  # .env, .env.local, .env.production
    r"id_rsa",
    r"id_ed25519",
    r"[A-Za-z0-9_.-]*\.(pem|key|p12|pfx)",
]
_ALTERNATION = "|".join(_BASE + EXTRA_PROTECTED)

# Files whose CONTENTS are secret. Reading the name is fine; reading inside is not.
PROTECTED = re.compile(
    r"(^|[\s/\\'\"=(,;|&])(" + _ALTERNATION + r")($|[^A-Za-z0-9_.-])",
    re.IGNORECASE,
)

# A token that IS a path to a protected file, as opposed to a pattern that merely
# mentions one. `.env` and `config/.env` match; a grep pattern like `\.env` does not.
PROTECTED_PATH = re.compile(r"^[A-Za-z0-9_./\\~:-]*?(" + _ALTERNATION + r")$", re.IGNORECASE)

# Templates that hold variable NAMES with placeholder values. Always fine to read.
ALLOWED = re.compile(r"\.env\.(example|sample|template)", re.IGNORECASE)

# "This is a regex, not a filename." A backslash before a dot is the giveaway:
# `grep -rn "\.env" src/` is a search, not a read.
REGEX_METACHARS = re.compile(r"[|*+?()\[\]{}^$]|\\\.")

# Commands that emit file CONTENTS. Anything else (ls, stat, git, rm, mv, find,
# test, ...) only touches names or metadata, so it passes.
READERS = {
    "cat", "bat", "head", "tail", "less", "more", "nl", "od", "xxd", "hexdump",
    "strings", "sed", "awk", "grep", "egrep", "fgrep", "rg", "ack", "cut", "tr",
    "sort", "uniq", "wc", "base64", "tee", "source", ".", "cp", "copy", "scp",
    "rsync", "get-content", "gc", "select-string", "type",
}

# Interpreters can hide a read inside inline code, so for these the mere mention
# of a protected file in the same segment is enough.
INTERPRETERS = {"python", "python3", "py", "node", "deno", "bun", "perl", "ruby", "php"}

# Shell noise to skip when finding a segment's real command word.
PREFIXES = {"sudo", "command", "env", "nohup", "time", "exec", "builtin", "\\"}

HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)

MESSAGE = (
    "Blocked: that would read the contents of a secret file.\n"
    "\n"
    "Do not read or print secret values. Reference the variable by NAME instead,\n"
    "and read .env.example for the list of names. If a command needs a secret,\n"
    "let the program load it from the environment at runtime.\n"
)


def strip_heredocs(command: str) -> str:
    """Writing a script that mentions `.env` is not reading `.env`."""
    return HEREDOC.sub(" HEREDOC_BODY_ELIDED ", command)


def command_word(segment: str) -> str:
    """The command a pipeline segment actually runs, past `sudo` and `VAR=x`."""
    for token in segment.strip().split():
        token = token.strip("(){}")
        if not token:
            continue
        if "=" in token and not token.startswith("-") and "/" not in token:
            continue  # VAR=value prefix
        if token.lower() in PREFIXES:
            continue
        return token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    return ""


def is_path_like(token: str) -> bool:
    return bool(PROTECTED_PATH.match(token)) and not REGEX_METACHARS.search(token)


def tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def reads_secret(command: str) -> bool:
    """True when some pipeline segment reads a protected file.

    Deliberately narrow, so ordinary work is not blocked:
      1. an argument of a reading command is a path to a protected file, or
      2. the command is an interpreter and the segment mentions one at all.
    """
    command = strip_heredocs(command)
    for segment in re.split(r"\|\||&&|[|;\n]", command):
        # Remove template names FIRST, so `cat .env.example .env` is still judged
        # on the real file rather than excused by the template beside it.
        probe = ALLOWED.sub(" ", segment)
        if not PROTECTED.search(probe):
            continue
        word = command_word(segment)
        if word in INTERPRETERS:
            return True
        if word in READERS:
            for token in tokens(segment)[1:]:
                if is_path_like(token) and not ALLOWED.search(token):
                    return True
    return False


def blocked(payload: dict) -> bool:
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool in ("Bash", "PowerShell"):
        return reads_secret(str(tool_input.get("command", "")))

    targets = []
    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        targets.append(str(tool_input.get("file_path", "")))
    elif tool in ("Grep", "Glob"):
        targets.append(str(tool_input.get("path", "")))
        targets.append(str(tool_input.get("glob", "")))

    return any(t and PROTECTED.search(t) and not ALLOWED.search(t) for t in targets)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0  # never break a session on a malformed payload
    if blocked(payload):
        sys.stderr.write(MESSAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
