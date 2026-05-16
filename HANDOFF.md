# HANDOFF — SmartyTask v2 scaffold

Last updated: 2026-05-16 (Session 3)

## What just happened

Session 3 took the project from "marketing site stuck on design" to "modern Django foundation scaffolded." Two deliverables landed:

1. **`REBUILD_SPEC.md`** — field-level documentation of every relevant table in the production DB dump, with real row counts (236K actions across 1,584 users) and explicit `[v2]` annotations for what changes in the rebuild.
2. **`REBUILD_MODELS.md`** — concrete Django 5 model design distilled from the spec. Four apps: `accounts`, `tasks`, `inbox`, `billing`.
3. **The actual scaffolded project** — `pyproject.toml`, settings split (base/dev/prod), four installed apps with models + admin + migration stubs, base HTMX/Tailwind template, smoke tests, Makefile, pre-commit, ruff config. The whole thing should `make install && make migrate && make dev` cleanly once Postgres is up.

## What's NOT done yet

- **The project has never been run.** It was written from the spec. First time Donny (or Claude in the next session) tries `make install + make migrate`, expect a couple of small fixes — typos, version pins, etc. The smoke tests exist to catch the obvious things.
- **No `uv.lock`** — `make install` generates it on first run.
- **No initial migrations** — `make makemigrations` creates them; deliberately not pre-committed so the first migration captures whatever final field tweaks happen.
- **No GitHub repo yet.** This scaffold lives only on Donny's iMac in `~/Documents/Claude/Projects/Smarty Task/smartytask-v2/`. Task #5 covers pushing it to a new `RichIdiot/smartytask-v2` repo.
- **No views, URLs, or templates beyond a healthz endpoint and a base template.** Coming in subsequent tasks (#16 HTMX UI).

## How to push this to GitHub when ready

The bindfs-in-iCloud-Documents limitation from Session 2 still applies — git can't write `.git/index.lock` from the sandbox into the Documents folder reliably. Two options:

**Option A — Donny does it via GitHub Desktop (recommended):**
1. Create the new repo on github.com: `RichIdiot/smartytask-v2`, **private**, no README/gitignore/license (we have our own).
2. Open GitHub Desktop → File → Add Local Repository → point at `~/Documents/Claude/Projects/Smarty Task/smartytask-v2/`.
3. GitHub Desktop offers to publish; click it, point at the new repo. Done.

**Option B — Claude does it via the /tmp workaround:**
1. Donny creates the GitHub repo (same as A.1).
2. Donny generates a one-time PAT with `repo` scope.
3. Claude rsyncs the v2 folder to `/tmp/smartytask-v2-build`, inits git there, commits, pushes with the PAT.
4. Donny revokes the PAT.

## Open decisions still pending (carried forward)

- Launchlist design — Donny is iterating in another tool. PARKED until he brings a winner back.
- Founder pricing exact $ — needs launchlist to settle first.
- Domain strategy — launchlist on cPanel subdomain vs. replacing root; v2 app likely on a separate `app.smartytask.com` subdomain on its own hosting.

## Next session

If marketing is still parked:
- **Task #5** — push v2 scaffold to GitHub (whichever option above).
- **Task #6** — run `make install && make makemigrations && make migrate` for real, fix anything that breaks, commit the initial migrations.
- **Task #16** — start the actual HTMX UI: auth pages (login, signup, password reset), Inbox view, Next Actions view, Add Action form. This is the first "you can use it" milestone.

If marketing is unstuck:
- Pivot back to Task #11 (copy in Donny's voice) and Task #12 (build/deploy on cPanel subdomain).
