# Release safety

The Checks workflow must pass before merging or publishing. It includes dependency audits, linting, unit tests, migration/restore regression tests, browser smoke tests, and both container builds and scans.

## Repository settings

In Settings > Rules > Rulesets (or Branches > Branch protection), protect main:
- Require a pull request before merging.
- Require the Checks / tests status check, and require the branch to be up to date.
- Require CodeQL analysis checks for Python and JavaScript after their first successful run.
- Block force pushes and deletion.
- Do not allow bypassing checks for routine changes.

These settings are repository-side and cannot be enforced by this document.

## Upgrade safety

Use a disposable backup when validating a new version. Never use a production portfolio in CI. Existing migration and restore tests cover historical schemas, failed migrations, transaction rollback and preservation of users. Run the full Python suite before every release.
