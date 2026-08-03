# Routine Organizer

A time-blocking weekly planner built with Django — click any empty cell, type a label, optionally pick a color, and drag an edge to resize. Server-rendered with HTMX-driven interactions and a PyCharm-inspired Darcula dark theme. No JavaScript build step.

![Routine Organizer — the weekly grid with colored time blocks](assets/ForTheReadme/MainPageLight.png)

## Features

- **Free-form time blocks.** Click any empty cell and type anything — no fixed categories, no mandatory event fields.
- **Drag to resize.** Pull a block's edge to span consecutive time slots, with a +/- keyboard/click fallback.
- **Repeat across days.** Copy one block to other days in a single request; overlapping copies are skipped and reported, never silently dropped.
- **Personal color palette.** Manage your own named hex colors; deleting one leaves affected blocks with a neutral fallback instead of breaking anything.
- **Export anywhere.** Grab your week as Markdown, SVG, or PNG, or print a clean PDF — all generated from your real data, zero extra dependencies.
- **Zero full-page reloads.** Every block, color, and settings operation is an HTMX partial swap.
- **Light/dark theme** with a Darcula-inspired dark palette, persisted per browser.
- **Configurable grid.** 30 or 60-minute slots, any day-start/day-end range (including midnight-crossing), 24h or 12h AM/PM display.
- **Native Django auth.** No extra auth package.

## Stack

| | |
|---|---|
| Backend | Python 3.12 · Django 6.0 |
| Frontend | Django Template Language · TailwindCSS v4 (standalone CLI) · HTMX |
| Database | SQLite (single file) |
| Auth | `django.contrib.auth` (native) |
| Tooling | [`uv`](https://docs.astral.sh/uv/) |
| Deployment | Docker / Docker Compose · gunicorn · WhiteNoise |

## Quick start

Requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/> and sign up from the landing page — your account is ready to use immediately.

### Docker

Requires Docker with the Compose plugin.

```bash
cp .env.example .env        # optional — the app boots with dev-safe defaults without it
docker compose build
docker compose up -d
```

The container runs `migrate` on start and serves the app at <http://localhost:2000/> (host port 8000 is left free for a local `runserver`; change it in `docker-compose.yml` if you'd like it elsewhere). Data persists in the `sqlite_data` named volume across restarts; `docker compose down -v` wipes it.

> **Dev-only defaults.** Without a `.env` file the container runs with `DEBUG=True` and an empty `ALLOWED_HOSTS` — fine for a quick local look. Before exposing it beyond `localhost`, set `DEBUG=False`, a real `ALLOWED_HOSTS`, and a fresh `SECRET_KEY` in `.env`.

## Project layout

```
config/          # Project configuration (settings, urls, wsgi, asgi)
apps/
  core/          # Landing page, dashboard shell, TimestampedModel
  accounts/      # Sign up, login, logout (native auth)
  planner/       # TimeBlock / BlockColor / PlannerSettings models, grid builder, export, HTMX views
templates/       # Project-level templates + shared partials
static/          # CSS (Tailwind source + compiled output) and JS
```

## Configuration reference

Every variable in `.env.example` maps directly to `config/settings.py`:

| Variable | Purpose | Default if unset |
|---|---|---|
| `SECRET_KEY` | Django's cryptographic signing key | insecure development fallback — **required in production** |
| `DEBUG` | `True` / `False` | `True` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `localhost,127.0.0.1` |

Two container-only settings, `SQLITE_DB_PATH` and `DJANGO_USE_WHITENOISE`, are set in the Dockerfile and are not meant to be edited locally.

## Development

### TailwindCSS build

Tailwind v4 is configured in `static/css/input.css` — there is no `tailwind.config.js`. The standalone CLI is not committed (~100 MB); download it once into `bin/` (gitignored):

```bash
mkdir -p bin
curl -sL -o bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x bin/tailwindcss
```

For other platforms, swap the asset name (see the [release page](https://github.com/tailwindlabs/tailwindcss/releases/latest)).

Build the compiled stylesheet (committed as `static/css/app.css`):

```bash
./bin/tailwindcss -i static/css/input.css -o static/css/app.css
```

Use `--watch` while developing templates and `--minify` for a production build. Rebuild `app.css` whenever you change a utility class — an unbuilt stylesheet is not a design bug.

### Tests

```bash
uv run python manage.py test
```

Runs the full suite (models, views, and the pure-Python grid/export builders) against Django's throwaway test database — nothing depends on `db.sqlite3`, so it passes clean from a fresh clone.

## Documentation

- [`ProductRequirementDocument.md`](docs/ProductRequirementDocument.md) — full product specification, requirements, and design system
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the codebase is organized, sprint by sprint

## License

Copyright (c) 2026 Henrique Mayer

Licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0). Personal, noncommercial use is permitted — studying it, running it for yourself, adapting it for a hobby project. Selling this software, or using it for any commercial purpose, is not. See [LICENSE](LICENSE) for the full terms.
