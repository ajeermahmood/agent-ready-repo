# Keeping this repository safe for people and agents

The short version, for an agent:

- Never read or print a secret value. Reference variables by name.
- Reach production only through the one committed command named in `AGENTS.md`.
- Never write a command shaped like an attack, even one that would work.
- Run the `ship-check` skill before saying you are done.

## Why "shaped like an attack" matters

Each of these is sometimes legitimate. Together, written fresh into a session,
they are indistinguishable from an intrusion, and sessions doing them get
refused, escalated or cut short:

| Shape | Do instead |
|---|---|
| A credential inline in a command or a generated script | A committed tool that loads credentials itself |
| Decoding an encoded blob into a remote path and running it | A committed script, transferred and run by name |
| Piping a download straight into a shell | Download, check, then run |
| Auto-accepting an SSH host key | Pin the host key once, and verify it |
| Switching off certificate checks so a request goes through | Find out why the certificate fails, and fix that |
| A background process whose output goes nowhere | Write its output to a log file you can name |

`npx bouncer-gates --only secrets` flags most of these in CI and in the editor.

## Where each rule lives

| Kind of rule | Where | Why |
|---|---|---|
| Formatting, import order | Formatter | Deterministic, already solved |
| Types, nulls | Compiler, strict mode | Free, and it runs in the editor |
| Context, intent, taste | `AGENTS.md` | A machine cannot check taste |
| Being wrong is expensive | A check that blocks CI | The only place a rule actually holds |

Written rules get followed most of the time. For anything in the last row, most
of the time is a polite way of saying it will eventually ship broken. If you would
be upset to find a rule broken in production, give it a check.

## What the secret-read hook is not

It catches accidents. It is not a wall: any program running as you can read your
files in ways the hook never sees. For real containment, keep
production credentials off the development machine entirely.
