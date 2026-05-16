# SmartyTask Rebuild Spec

**Source:** Production DB dump pulled 2026-05-15 (`_dl_b8d2e1a9c7f4.sql.gz`, MySQL 5.5, Django 1.1.x).
**Purpose:** Field-level documentation of the relevant tables so the v2 Django app can be built from a spec rather than spelunking the dump again.
**Scope:** GTD core (8 tables) + auth/identity (1) + profile (1) + comingsoon (1) + billing (2). Blog, static-page CMS, django admin log, content-type, permissions, session, site tables are intentionally excluded — they're either Django built-ins we get for free or features (blog, CMS) that the v2 product won't carry.

---

## Production usage (actual row counts from the dump)

| Table | Rows | Notes |
|---|---:|---|
| `auth_user` | 1,584 | Total accounts ever created |
| `membership_profile` | 1,577 | ~99% of users completed profile setup |
| `spreedly_subscriber` | 1,577 | 1-to-1 with profiles |
| `spreedly_plan` | 2 | $9.99/mo and $99/yr |
| `comingsoon_email` | 493 | Pre-existing coming-soon list — already close to the "first 500 founders" goalpost |
| `smarty_action` | **236,001** | Lifetime task volume — the load-bearing table |
| `smarty_project` | 24,981 | |
| `smarty_context` | 16,071 | Includes child contexts (parent_id) |
| `smarty_altitude` | 8,966 | MPTT-managed tree |
| `smarty_smartcontext` | 2,729 | Saved filters (e.g., "Low Effort") |
| `smarty_smartcontextrule` | 2,577 | Rule definitions for smart contexts |
| `smarty_smartcontextrule_contexts` | 1,708 | M2M between rules and contexts |
| `smarty_somedaycategory` | 2,556 | "Someday/maybe" buckets |

Useful for relaunch positioning: the system has handled 236K actions across 1,584 users. That's not vaporware — it's a real, battle-tested workflow.

---

## Table-by-table spec

Notation: `→ FK` means foreign key reference; `(idx)` means indexed; `(unique)` means unique constraint; `[v2]` means a note about how this should change in the rebuild.

### `auth_user` — Django 1.1 built-in user table

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | auto-increment |
| username | varchar(30) | no | unique |
| first_name | varchar(30) | no | |
| last_name | varchar(30) | no | |
| email | varchar(75) | no | NOT unique in old schema |
| password | varchar(128) | no | sha1$salt$hash format |
| is_staff | bool | no | |
| is_active | bool | no | |
| is_superuser | bool | no | |
| last_login | datetime | no | |
| date_joined | datetime | no | |

**Sample:** `(1,'bryan','Bryan','Chow','bryan@veryfresh.com','sha1$094c6$...',1,1,1,'2017-04-20','2009-05-23')`

[v2] Switch to a custom User model from day one (Django docs strongly recommend this even if you don't customize). Use Argon2 (Django default since 1.10). Make email unique and the login identifier (drop username, or keep as optional handle). Drop sha1 hashes — force a password reset on migration if we ever import these users.

---

### `membership_profile` — Per-user app settings (1:1 with auth_user)

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id, unique (1:1) |
| hide_empty_contexts | bool | no | UI preference |
| enable_smartcontexts | bool | no | feature toggle |
| hide_empty_smartcontexts | bool | no | UI preference |
| default_page | int | yes | which page to land on after login |
| number_actions_for_contexts | bool | no | show count badges on contexts? |
| number_actions_for_projects | bool | no | show count badges on projects? |
| reminder_email | varchar(75) | yes | where the daily digest gets sent |
| reminder_time | time | no | what time of day to send digest |
| reminder_tickler_behavior | int | no | how ticklers appear in the digest (enum) |
| reminder_action_behavior | int | no | how actions appear in the digest (enum) |
| use_stars | bool | no | star-prioritization feature toggle |
| tz_offset | int | no | minutes from UTC (480 = -08:00 = Pacific) |
| use_dst | bool | no | observe DST? |
| inbox_email | varchar(60) | yes | email-to-inbox handle, e.g., 'bryan' → bryan@inbox.smartytask.com |
| options | text | yes | manual JSON blob with extra prefs (e.g., `{"confirmDelete": 1}`) |
| created | datetime | no | |
| modified | datetime | no | |

**Sample:** `(1,1,0,1,0,NULL,1,1,'bryan@fullfactor.com','00:30:00',3,2,1,480,1,'bryan','{...}','2009-09-04','2016-10-12')`

[v2] Replace `tz_offset` + `use_dst` with a single TZ string (`America/Los_Angeles`) — Python's `zoneinfo` handles DST natively. Move `options` to a proper `JSONField`. Move email-to-inbox config to its own model when we get to the inbox feature.

---

### `comingsoon_email` — The pre-existing email list

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| email | varchar(75) | no | |
| created | datetime | no | |

[v2] This table is a goldmine for the relaunch — 493 people who once wanted SmartyTask. **Do not migrate blindly** — these emails are 10-15+ years old, mostly cold/bouncy/spam-trap territory. Plan: run them through a list verification service (NeverBounce, ZeroBounce) before any send, then a careful re-engagement sequence with explicit re-opt-in. The "first 500 founders" wedge writes itself if even 50 of these convert.

---

### `smarty_context` — GTD contexts (the @home, @phone, @errands list)

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id (idx) |
| title | varchar(256) | no | "@Home", "Calls / Emails", etc. |
| parent_id | int | yes | self-FK for ONE level of nesting (idx) |
| active | bool | no | inactive = hidden but not deleted |
| ordering | int | no | manual sort order |
| created | datetime | no | |
| modified | datetime | no | |

**Sample:** `(1, 1, 'Home', NULL, 0, 30, ...)`, `(38, 6, 'Office', NULL, 1, 1, ...)`, `(41, 6, 'Bryan', NULL, 0, 50, ...)`

[v2] Keep the self-FK for nesting but enforce parent depth at the model level. Order via a `position` integer; the legacy `ordering` field is fine as-is.

---

### `smarty_project` — GTD projects (multi-step outcomes)

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id (idx) |
| title | varchar(256) | no | |
| notes | longtext | no | HTML rich text |
| completed | datetime | yes | timestamp of completion (NULL = open) |
| due_date | date | yes | |
| separator | bool | no | flag = visual separator row, not a real project |
| collapsed | bool | no | UI state: section folded in the list |
| ordering | int | no | manual sort |
| created | datetime | no | |
| modified | datetime | no | |
| deleted | datetime | yes | soft delete |

[v2] Soft-delete pattern stays (use `django-safedelete` or just `deleted_at`). Store `notes` as Markdown in v2, not HTML — modern editors round-trip Markdown cleanly and it's safer. Drop the `separator` field — that's a UI-affordance hack; do separators in the frontend.

---

### `smarty_action` — Actions / tasks / ticklers (the load-bearing table)

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id (idx) |
| context_id | int | yes | → smarty_context.id (idx) |
| project_id | int | yes | → smarty_project.id (idx) |
| someday_category_id | int | yes | → smarty_somedaycategory.id (idx) |
| is_tickler | bool | no | distinguishes ticklers from regular actions |
| title | varchar(256) | no | |
| notes | longtext | no | HTML rich text (often empty `<p><br /></p>\n`) |
| starred | bool | no | priority flag |
| completed | datetime | yes | completion timestamp |
| minutes_required | int | yes | estimated time |
| effort | int | yes | enum: 1=low, 2=medium, 3=high |
| due_date | date | yes | |
| reminded | datetime | yes | last time a reminder was sent |
| inbox_ordering | int | no | sort position in inbox view |
| context_ordering | int | no | sort position within context view |
| project_ordering | int | no | sort position within project view |
| someday_ordering | int | no | sort position within someday view |
| options | text | yes | JSON blob for ad-hoc settings |
| created | datetime | no | |
| modified | datetime | no | |
| deleted | datetime | yes | soft delete |

**Sample:** `(1, 2, NULL, NULL, NULL, 0, 'This is another "Personal" action.', '<ul>...', 0, '2009-10-16', NULL, 1, NULL, NULL, 0, 55, 0, 0, NULL, '2009-09-04', '2009-10-16', NULL)`

**Critical index:** `i_user_deleted_completed_tickler (user_id, deleted, completed, is_tickler)` — this powers the "inbox / next actions / tickler" filters and is the reason the app stays fast at 236K rows.

[v2] Several changes:
- **One ordering field, not four.** The four parallel ordering columns are a relic of the SPA pre-rendering every view. With server-driven HTMX, sort within a view query — manual reordering can be a single nullable `position` integer.
- **Status as enum,** not implicit-from-fields. The old model derives status from `(deleted, completed, is_tickler)` combinations; v2 should have an explicit `status` field with `TextChoices` (inbox, next, scheduled, waiting, someday, tickler, completed, deleted) and let queries filter on it cleanly.
- **Effort and minutes_required:** keep both. They're different data — `effort` is energy/focus, `minutes_required` is time. Use `IntegerChoices` for effort.
- **Notes:** Markdown, not HTML.
- **`options` → JSONField.**

---

### `smarty_altitude` — David Allen's altitude hierarchy (MPTT tree)

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id (idx) |
| title | varchar(2000) | yes | yes, 2000-char titles — Allen-style "horizon" descriptions |
| parent_id | int | yes | self-FK (idx) |
| collapsed | bool | no | UI state |
| ordering | int | no | |
| created | datetime | no | |
| modified | datetime | no | |
| lft, rght, tree_id, level | int | no | django-mptt internals (all indexed) |

[v2] Switch to `django-treebeard` — actively maintained, more modern than `mptt`. Decision point flagged in old memory: **expand the altitude model from 3 levels (5yr/1yr/90day) to Allen's full 5 (Runway/10K/20K/30K/40K/50K) or rename to be clearer.** The data already supports arbitrary depth; only the UI hardcoded 3 levels. This is a relaunch story point: "the only GTD app that implements Allen's full altitude model."

---

### `smarty_smartcontext` — Saved filters (named queries over actions)

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id (idx) |
| title | varchar(256) | no | "Low Effort", "Starred", "On The Gas!" |
| feed_slug | varchar(50) | yes | URL slug for RSS feed of the filter |
| ordering | int | no | |
| created | datetime | no | |
| modified | datetime | no | |

[v2] Rename to `SavedView` or `SmartList` — `smartcontext` is confusing terminology. Keep RSS feed (`feed_slug`) — power-user feature, niche but loved. Add iCal export while we're at it.

---

### `smarty_smartcontextrule` — Filter criteria for a SmartContext

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| smartcontext_id | int | no | → smarty_smartcontext.id (idx) |
| use_context | bool | no | apply context-list constraint? (toggle for the M2M below) |
| time_low/medium/high | bool | yes | match actions with minutes_required = X? |
| effort_low/medium/high | bool | yes | match actions with effort = X? |
| created_before | int | yes | days |
| created_after | int | yes | days |
| due_before | int | yes | days |
| due_after | int | yes | days |
| starred | bool | yes | tri-state: NULL = ignore, 0 = unstarred only, 1 = starred only |
| ordering | int | no | multiple rules per smartcontext, ordered |
| created, modified | datetime | no | |

[v2] The wide tri-state-bool-per-criterion pattern is dated. Modernize as a `JSONField` describing the rule, OR a small DSL: `{"effort": ["low"], "starred": true, "context_in": [1,2,5]}`. Either way, write a single evaluator that takes the rule + a queryset and returns the filtered queryset. Don't replicate the old field-by-field structure.

---

### `smarty_smartcontextrule_contexts` — M2M between rules and contexts

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| smartcontextrule_id | int | no | → smarty_smartcontextrule.id |
| context_id | int | no | → smarty_context.id (idx) |
| | | | unique (smartcontextrule_id, context_id) |

[v2] Implicit through Django's `ManyToManyField`. Drops out if rules become a JSON DSL.

---

### `smarty_somedaycategory` — Buckets for "someday/maybe" items

| Field | Type | Null | Notes |
|---|---|---|---|
| id | int PK | no | |
| user_id | int | no | → auth_user.id (idx) |
| title | varchar(256) | no | "Books to read", "Trips to take", "Code" |
| ordering | int | no | |
| created, modified | datetime | no | |

[v2] Trivial port. Maybe rename to `SomedayList` for clarity.

---

### `spreedly_plan` and `spreedly_subscriber` — Legacy billing

Replaced wholesale by Stripe in v2. Don't port these tables; document the historical pricing for reference:
- $9.99/month
- $99/year
- 7-day free trial
- Subscriber 1:1 with user

The `data` longtext blobs hold the raw Spreedly API responses — not useful for v2.

---

## What's NOT being ported (and why)

| Old table | Why drop |
|---|---|
| `auth_message` | Django <1.4 messaging — gone since 2012, replaced by `django.contrib.messages` |
| `auth_group*`, `auth_permission*` | Django built-ins; we get fresh schema |
| `django_admin_log`, `django_content_type`, `django_site`, `django_session` | Django built-ins |
| `blog_*` | The blog feature doesn't survive the cut — run content on the marketing site, not inside the app |
| `static_page`, `static_redirect` | The in-app CMS for help docs doesn't survive — use a real docs site or a Markdown folder in the repo |
| `spreedly_*` | Stripe replaces this entirely |

---

## Migration considerations (when/if we ever import old data)

Greenfield rebuild means no automatic import. But IF Donny ever wants to recover his own historical data (he uses the system himself), here's the path:

1. **Don't try to live-migrate** — stand up the new app empty, develop on it, then write a one-shot import script that reads the old MySQL dump (via `pymysql`) and creates v2 records.
2. **Password reset required** — sha1 hashes don't survive the move to Argon2. Email users a reset link if we bring any of them along.
3. **Notes field needs HTML → Markdown conversion.** `html2text` does this reasonably well; budget some manual cleanup time for edge cases.
4. **Datetimes are tz-naive in the old schema** — need to localize to each user's `tz_offset` before importing. Easier: import everything as UTC-naive, accept some drift, and let users adjust.
5. **The old `options` JSON-in-text fields** use single-quoted Python repr in some places (spreedly), valid JSON in others (smarty_action, membership_profile). Parser must be tolerant.

---

## Open questions for v2 model design

1. **Inbox model:** keep email-to-inbox or simplify to just-a-form-on-the-page? **Recommendation: keep it as a headline feature.** It's the actual differentiator.
2. **Multi-tenant or single-user-per-DB?** Single shared DB with `user_id` on every row, same as the old app.
3. **API-first or HTMX-first?** **HTMX-first for the v1 launch.** Add DRF later if/when we want a mobile app.
4. **Mobile: PWA or native?** **PWA via responsive HTMX** for v1.
5. **Search:** old app had none visible. v2 should ship with PostgreSQL full-text search on action titles + notes from day one.

---

End of spec. Next deliverable: `REBUILD_MODELS.md` — concrete Django 5 model definitions derived from this spec.
