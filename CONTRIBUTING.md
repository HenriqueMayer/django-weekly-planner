# Contributing

This is a template project: the goal is that anyone can clone it, understand it quickly, and
adapt it to their own use case. Read `docs/ProductRequirementDocument.md` for the full spec and
`docs/ARCHITECTURE.md` for how the codebase actually turned out (including every deliberate
deviation from the spec, and why) before making structural changes.

## Ground rules

- English-only: code, comments, identifiers, templates, docs.
- PEP 8, single quotes. Run `uv run ruff check .` before committing — it's the enforced dev tool
  (`[tool.ruff]` in `pyproject.toml`); `ruff format` is deliberately not run wholesale across the
  repo (see `docs/ARCHITECTURE.md`'s Sprint 7 quality-pass notes for why).
- Class-Based Views over function views wherever Django's generic CBVs fit the job.
- Every model inherits `apps.core.models.TimestampedModel` (`created_at`/`updated_at`).
- Signals live only in each app's `signals.py`, registered from that app's `AppConfig.ready()`.
- Keep it lean (NFR-01): no SPA framework, no DRF, no Celery, no extra ORM. If you're reaching for
  one of those, the answer is probably "don't" for this template.
- Run `uv run python manage.py test` before opening a PR — it must stay clean from a fresh clone
  with no test-ordering dependency (verified in this repo under `--shuffle`/`--reverse`/`--parallel`).

## How to add a new Django app

1. `mkdir -p apps/<name>` and build it out like the existing apps (`apps/core`, `apps/accounts`,
   `apps/planner`) — a `apps.py` with `AppConfig.name = 'apps.<name>'`, `models.py`, `views.py`,
   `urls.py` with its own `app_name = '<name>'`.
2. Add `'apps.<name>'` to `INSTALLED_APPS` in `config/settings.py`.
3. `include()` its `urls.py` from `config/urls.py` under whatever path prefix makes sense.
4. If it needs its own signals, put them in `apps/<name>/signals.py` and register them from a
   deferred import inside `AppConfig.ready()` — see `apps/planner/apps.py` for the pattern this
   project already uses (Django's own documented approach, avoids circular imports).
5. Write tests under `apps/<name>/tests.py` (or a `tests/` package once the app's test surface
   covers more than one genuinely distinct concern — see `apps/planner/tests/` for when and why
   that split happened).

## How to swap the color palette / design tokens

- The design-token table (colors, gradients, component class strings) is documented in
  `docs/ProductRequirementDocument.md` §9 and mirrored as a comment header in
  `static/css/input.css`. Change the Tailwind utility classes directly in the shared partials
  (`templates/partials/buttons/*.html`, `templates/partials/form_field.html`,
  `apps/planner/templates/planner/partials/*.html`) — because those are already extracted into
  single call sites (see `docs/ARCHITECTURE.md`'s "Design system" section), a token change is a
  one-file edit, not a project-wide find-and-replace.
- After changing any Tailwind class anywhere, rebuild the compiled stylesheet:
  `./bin/tailwindcss -i static/css/input.css -o static/css/app.css` (see the README's Tailwind
  section for the one-time CLI download). An unbuilt stylesheet is not a design bug.
- This is unrelated to the **per-user** color palette feature (`BlockColor` model, name + hex,
  managed by each signed-in user through the dashboard's Palette panel) — that's runtime data, not
  a design-system token, and needs no code change to use.

## How to change grid defaults

Default values for a brand-new user's grid live on `apps.planner.models.PlannerSettings`
(`apps/planner/models.py`):

| Field | Default | Choices |
|---|---|---|
| `slot_interval` | `60` (minutes) | `30` or `60` |
| `day_start` | `06:00` | any `time` |
| `day_end` | `00:00` (midnight) | any `time`; `00:00` is treated as end-of-day, not zero-duration |
| `time_format` | `'24h'` | `'24h'` or `'12h'` |

Change the `default=` on the relevant field, then `manage.py makemigrations planner` +
`manage.py migrate` — this only changes the default for *new* `PlannerSettings` rows (created by
the `post_save` signal in `apps/planner/signals.py` the moment a user signs up); it does not touch
existing users' saved settings.

The actual grid matrix (rows/columns/rowspans) is computed once, in one place:
`apps/planner/grid.py`'s `build_week_grid()`. It's pure Python with no database access — if you
need to change how the grid is laid out (e.g. a different week-start day), that function and its
tests (`apps/planner/tests/test_grid.py`) are the only things you should need to touch.

## SQLite limits and switching databases

SQLite is the only database this template ships with (PRD §8.1) — it's a single file
(`db.sqlite3` locally, or a Docker volume in the containerized setup), which is genuinely
sufficient for a personal, single-tenant planner but does not handle high write concurrency well
(PRD risk R7). If you outgrow it:

1. Change `DATABASES['default']` in `config/settings.py` to point at your engine of choice (e.g.
   `django.db.backends.postgresql`), following Django's own
   [database settings docs](https://docs.djangoproject.com/en/6.0/ref/settings/#databases).
2. Add the matching DB driver (e.g. `psycopg`) via `uv add <package>`.
3. Re-run `manage.py migrate` against the new database — no application code depends on SQLite
   specifically; every query goes through the ORM.

Nothing else in this codebase assumes SQLite.
