---
name: ship-check
description: Verify a change actually works before calling it done, beyond "the tests are green". Compares test counts, runs from a clean state, reads real output instead of checking it exists, and checks the live system after a deploy. Use before saying a task is finished, and before every release.
---

# Ship check

Every step here exists because skipping it once let a real mistake through. An
agent's mistakes arrive looking finished, and the worst ones fail nothing.

## 1. Compare the test count, not just the colour

Run the full suite and read the **count**, against the last known count.

- Fewer tests than before, with no tests deleted on purpose, means a file stopped
  loading. A test file that fails to parse is not reported as failing; it is
  simply absent, and a filtered summary line will still say "passed".
- Never filter test output down to one line to save space. Read the file-level
  summary too.

## 2. Run once from a clean state

Caches, state directories and first-run code paths hide bugs. Before a release:

- Delete local state the tool keeps between runs, and run it again.
- Install the built package into an empty directory and use it from there, rather
  than running it from source.

## 3. Read the output, do not just check it arrived

A command that exits 0 can still be wrong. Look at the actual values:

- Does `--version`, a handshake, or a report show the version you just set?
- Did a find-and-replace actually match anything? A replacement that matches
  nothing exits successfully.

## 4. Look for a second source of truth

If a value lives in two places, one of them is already stale or soon will be.
Read it from one place, and add a test that asserts they agree.

## 5. Check the live system after a deploy

A successful deploy says the upload worked, not that the feature does.

- Exercise the most common real input against the live deployment.
- For anything public facing, check what a first-time visitor would actually do.

## 6. Check provenance before installing anything

Do not install or run a package from its name alone, especially one that asks
for credentials. Read its maintainer, repository and description first. A
package with exactly the right name can belong to someone else.

## Report

List each step as done, skipped with a reason, or not applicable. Never report
a step as done that was not run.
