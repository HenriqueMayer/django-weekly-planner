# Development Guide

## Setup

Requirements: Python 3.12+, `uv`, and Git.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The default development database is `db.sqlite3`. It is not used by automated tests.

## Required Checks

Run these before opening or merging a change:

```bash
uv run python manage.py test
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check apps config
git diff --check
```

The project currently has no CI workflow, so these checks are local responsibilities.

## Tailwind CSS

Tailwind v4 is configured in `static/css/input.css` through `@source` and `@custom-variant`. There is no JavaScript configuration file or Node package.

Download the standalone CLI into the ignored `bin/` directory:

```bash
mkdir -p bin
curl -sL -o bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x bin/tailwindcss
```

Build or watch the stylesheet:

```bash
./bin/tailwindcss -i static/css/input.css -o static/css/app.css
./bin/tailwindcss -i static/css/input.css -o static/css/app.css --watch
```

Commit `static/css/app.css` whenever its source or template utility classes change.

## Code Conventions

- Application code, templates, identifiers, and documentation are written in English.
- Python targets 3.12, uses single quotes, and follows the Ruff configuration in `pyproject.toml`.
- Models inherit `apps.core.models.TimestampedModel` unless there is a documented reason not to.
- Keep business rules in models or small pure-Python services, not templates.
- Prefer Django class-based views where they reduce duplication.
- Scope all user-owned querysets to `request.user`.
- Never trust client-provided owner IDs, dates, or schedule values without server validation.
- Add migrations and tests with every model change.

## Planner Conventions

- Carry the selected week through links, forms, HTMX requests, and mutation responses.
- Normalize selected dates through `apps.planner.dates` rather than duplicating date math.
- Reuse `build_week_grid()` for dashboard, planner, and visual exports.
- A card mutation may return the full `#grid-table`; do not patch individual occupied cells unless the complete `rowspan` effect is handled.
- Card modal mutations target `#card-panel` and may include an out-of-band grid refresh.
- HTMX request branching may inspect `HX-Request` and `HX-Target`; full requests must still return a valid page.
- Event handlers for swapped content should use delegation rather than one-time element binding.

## Tests

- Use `SimpleTestCase` for pure date/grid/export logic that does not need a database.
- Use `TestCase` for models, authentication, ownership, views, uploads, and recurrence.
- Assert database state and response contracts such as `HX-Retarget`, `HX-Reswap`, and out-of-band fragments.
- Use temporary media storage in attachment tests and delete created files.
- Add ownership tests for every endpoint accepting a model identifier.

Browser behavior such as drag resizing, modal visibility, theme switching, PNG capture, and print still requires manual smoke testing because no end-to-end browser suite exists.

## Database Changes

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py makemigrations --check --dry-run
```

Review generated migrations before committing them. Do not edit existing migrations that may already have been applied.
