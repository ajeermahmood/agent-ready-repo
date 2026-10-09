# Ledger

The dated project log. Agents read the top of this file at the start of every
session and append one entry when they finish.

Keep this file small. When it passes about 50 KB, move older entries into
`docs/ledger/<year>-<month>.md` and leave a one-line pointer here. An entry
point that tells every session to read a huge file is the fastest way to waste
a session before any work starts.

## Entry format

```
### YYYY-MM-DD: <one-line summary>
- What changed, in a sentence or two.
- What was verified, and how.
- What is left, if anything.
```

## Worklist

- <the next thing to do>

## Entries

### <YYYY-MM-DD>: Adopted the agent-ready setup
- Added AGENTS.md, the secret-read hook, the tenant-check and ship-check skills, and bouncer-gates in the editor and CI.
- Verified: hook tests pass, `npx bouncer-gates` runs clean.
