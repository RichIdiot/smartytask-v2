# SmartyTask v2

Greenfield rebuild of [SmartyTask](https://smartytask.com), a Getting Things Done web app originally written in 2009 on Django 1.1. This is the modern Django 5 / Python 3.12 / Postgres / Stripe / HTMX rebuild driven by the spec in `REBUILD_SPEC.md` (extracted from the production DB) and the model design in `REBUILD_MODELS.md`.

## Stack

- Python 3.12+
- Django 5.1 LTS
- Postgres 16 (via `psycopg[binary]`)
- `uv` for dependency management
- `django-treebeard` for the Altitude hierarchy (David Allen's full 5-level horizon model)
- HTMX + Tailwind for the UI (server-driven, no SPA)
- Argon2 password hashing
- Stripe for billing
- Brevo SMTP for transactional email
- Postfix → webhook for email-to-inbox
- ruff + pytest-django + pre-commit + mypy

## Project layout

```
smartytask-v2/
├── pyproject.toml          uv-driven deps; ruff + pytest + mypy config
├── manage.py
├── Makefile                make dev / migrate / test / lint / format
├── .env.example            copy to .env for local dev
├── REBUILD_SPEC.md         field-level documentation of the old DB
├── REBUILD_MODELS.md       v2 model design notes
├── src/
│   ├── smartytask/         project package (settings, urls, wsgi/asgi)
│   │   └── settings/       base.py, dev.py, prod.py split
│   ├── accounts/           custom User + Preferences
│   ├── tasks/              Context, Project, Action, SomedayList, Altitude, SavedView
│   ├── inbox/              email-to-inbox handles + message log
│   ├── billing/            Stripe-driven Plan + Subscription + StripeEvent
│   └── templates/          base.html (HTMX + Tailwind via CDN for dev)
└── tests/                  pytest-django smoke + unit tests
```

## Quick start

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all deps (incl. dev)
make install

# Create local Postgres DB
createdb smartytask
psql -c "CREATE USER smartytask WITH PASSWORD 'smartytask'; GRANT ALL PRIVILEGES ON DATABASE smartytask TO smartytask;"

# Copy env template
cp .env.example .env

# First migrations
make makemigrations
make migrate
make superuser

# Run dev server
make dev
# → http://localhost:8000/admin/
```

## What's NOT in this repo (yet)

- Views / URL routes for the actual GTD app — coming in Task #16 (HTMX UI).
- DRF API layer — deferred until v1.5 / mobile.
- Stripe checkout / webhook handlers — coming in Task #18.
- Email-to-inbox webhook — coming in Task #19.
- The old SmartyTask Django 1.1 source (which lives in the parent `RichIdiot/Smartytask` repo as the historical spec).
- The production DB dump (gitignored; lives only on Donny's iMac).

## Sibling repos

- `RichIdiot/Smartytask` — the original 2009 Django 1.1 codebase. Read-only reference.
- `RichIdiot/smartytask-v2` — this repo. The modernized rebuild.

## License

Proprietary. Donny Farmer, 2026.
