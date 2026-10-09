# <Project name>: agent entry point

> Read this file first, then open **only** the doc your task needs. This file is
> an index, not a manual. Keep it short enough to read in one sitting.

<!--
  HOW TO USE THIS TEMPLATE
  Replace every <angle-bracket> placeholder and delete these comments.
  The rule for what belongs here: knowledge that is NOT visible from reading the
  code. Style belongs in the formatter. Types belong in the compiler. Anything
  you would be upset to find broken in production belongs in CI, and is only
  repeated here so the agent knows why the check exists.
-->

## What this is

<One paragraph. What the system does, who uses it, the stack, and the one thing
about it that a capable newcomer would get wrong. For a multi-tenant app that is
usually: "every tenant-owned table is scoped by tenantId".>

## Start here every session

1. Read [docs/LEDGER.md](docs/LEDGER.md): the live worklist and the most recent
   entries. Older history is in [docs/ledger/](docs/ledger/). Search it, never
   read it whole.
2. Open only the doc your task needs from the map below.
3. When you finish, append one entry to the ledger in the format at its top.

## Non-negotiable rules

Every rule here is also a check. The check is what holds; this list is what
explains it.

1. **Tenant isolation.** Every tenant-owned query is scoped by `<tenantId>`. Go
   through `<the scoped client>`, never around it. Check: `npx bouncer-gates --only scope`.
   Before committing any database change, run the `tenant-check` skill.
2. **Money is integer minor units.** Never a float, never a hardcoded `* 100`.
   Check: `npx bouncer-gates --only money`.
3. **Migrations are backward-compatible.** The previous release must survive the
   new schema during a deploy. Check: `npx bouncer-gates --only migration-safety`.
4. **No secret is ever a literal, and you never read one.** Reference variables
   by name; the list of names is in `.env.example`. A hook blocks reading secret
   files, so do not try to work around it.
5. **Production is reached through one door.** `<your committed deploy / ops
   command>`. Never write a throwaway script with credentials in it.

## Ask before you

- Change anything in payments, authentication, or a migration.
- Add a dependency.
- Touch `<generated or vendored paths>`.

## Doc map

| If your task touches | Read |
|---|---|
| What happened and what is next | [docs/LEDGER.md](docs/LEDGER.md) |
| Why the safety rules exist | [docs/AGENT_SAFETY.md](docs/AGENT_SAFETY.md) |
| <System design, tenancy, request flow> | `<docs/ARCHITECTURE.md>` |
| <Data model> | `<docs/DATA_MODEL.md>` |
| <Deploying> | `<docs/DEPLOY.md>` |

## Before you say you are done

Run the `ship-check` skill. "Tests pass" is not the same as "the change works".
