# agent-ready-repo

**A starting point for a repository that AI coding agents can work in safely.**
Copy the files, fill in the placeholders, and the agent gets instructions it can
actually use, a hook that keeps it out of your secrets, review skills for the
mistakes static checks miss, and CI that holds it to the same bar as a person.

This is the generalised version of the setup I use on a production multi-tenant
platform where about nine in ten of my commits are written with Claude Code.
[How that works, with the numbers and what went wrong](https://ajeer.website/how-i-work).

## What is in it

| File | What it does | Why |
|---|---|---|
| `AGENTS.md` | The agent's entry point: what the system is, the rules that never bend, and a map of the docs | An index the agent can read in one go, not a manual it skims |
| `CLAUDE.md` | One line pointing Claude Code at `AGENTS.md` | One source of truth for every agent tool |
| `.claude/hooks/block-secret-reads.py` | Blocks any tool call that would read the contents of a secret file | The leak that actually happens is an accident, not an attack |
| `.claude/settings.json` | Wires up that hook, runs bouncer-gates after every edit, and sets a small permission policy | The agent hears about a mistake in the same turn it made it |
| `.claude/skills/tenant-check` | Reviews database changes for cross-tenant leaks a static check cannot see | Transactions, built filters and stale exceptions |
| `.claude/skills/ship-check` | Checks a change works before "done": test counts, a clean-state run, real output, the live system | Agent mistakes arrive looking finished |
| `.mcp.json` | Serves the same checks over MCP | Any MCP client can call them |
| `.github/workflows/ci.yml` | Runs the checks and the hook's tests on every push | Nothing fixed in the editor comes back through a merge |
| `docs/LEDGER.md` | A dated log the agent reads first and appends to last | Continuity between sessions |
| `docs/AGENT_SAFETY.md` | The rules behind the setup | So the next person knows why |

## Quick start

1. Copy everything except `README.md` and `LICENSE` into your repository.
2. Fill in every `<placeholder>` in `AGENTS.md`, then delete the comment block.
3. Generate the tenant config from your Prisma schema, or fill in
   `bouncer-gates.config.json` by hand:
   ```bash
   npx bouncer-gates --init
   ```
4. Run the checks once and record any existing problems so only new ones block:
   ```bash
   npx bouncer-gates
   npx bouncer-gates --baseline-write   # only if there is existing debt
   ```
5. Run the hook's tests:
   ```bash
   python -m unittest discover -s .claude/hooks -p "test_*.py"
   ```
6. Commit it all. Everyone who opens the repository in Claude Code gets the same setup.

**On Windows**, change `python3` to `python` in `.claude/settings.json` if
`python3` is not on your path.

## The idea in one table

Put each rule in the cheapest place that can actually hold it.

| Kind of rule | Where it belongs |
|---|---|
| Formatting, naming | The formatter |
| Types, null safety | The compiler |
| Context, intent, "prefer this" | `AGENTS.md` |
| Anything expensive to get wrong | A check that blocks CI, and runs in the editor too |

The usual first move is a long instructions file. It helps, but an agent follows
written rules most of the time, not all of the time, and the expensive mistakes
live in the gap.

## Honest limits

- **The secret-read hook catches accidents, nothing more.** It is not a wall. Anything running as your user can read what you can read. Keep
  production credentials off the development machine.
- **The checks match patterns; they do not understand your code.** That is why
  the `tenant-check` skill exists for what they cannot see, and why a person
  still reads every change that touches money, tenancy, authentication or the
  schema.
- **The permission policy is an example.** Tighten it for your project. A short
  list you understand beats a long one that grew by accident.

## Related

- [bouncer-gates](https://github.com/ajeermahmood/bouncer-gates): the checks this
  template runs, as a CLI, GitHub Action, MCP server and editor hook.
- [Making a codebase safe for AI coding agents](https://ajeer.website/blog/coding-agents-in-production-repositories)
- [What my coding agents got wrong, and what caught it](https://ajeer.website/blog/what-my-coding-agents-got-wrong)

## Licence

MIT.
