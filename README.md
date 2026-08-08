# Routine Organizer

A date-aware weekly planner built with Django, HTMX, Tailwind CSS, and vanilla JavaScript. It combines a time-blocking grid with Trello-style card details while remaining server-rendered and dependency-lean.

![Routine Organizer landing page](assets/MainPageLight.png)

## Features

- Monday-to-Sunday planner with 30 or 60-minute slots and configurable visible hours.
- Fast card creation from an empty time slot, overlap validation, editing, deletion, and drag resizing.
- Week navigation with browser history and a compact monthly date picker.
- Card details with description, status, due date, labels, attachments, checklists, comments, replies, and activity.
- Weekly recurrence with materialized occurrences, exceptions, overrides, skip, and restore actions.
- Kanban view grouped by card status.
- `@username` mentions and persisted notifications.
- Card ownership transfer with overlap protection and an audit record.
- Personal color palette and persistent light/dark themes.
- Markdown, SVG, PNG, print, and browser PDF export for the selected week.
- Per-user data isolation with Django session authentication and CSRF protection.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+ and Django 6.0.7+ |
| Frontend | Django templates, HTMX 2, Tailwind CSS 4, vanilla JavaScript |
| Database | SQLite |
| Tooling | `uv`, Ruff, Tailwind standalone CLI |
| Deployment | Docker Compose, Gunicorn, WhiteNoise |

## Quick Start

Install Python 3.12+ and [`uv`](https://docs.astral.sh/uv/getting-started/installation/), then run:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/>, create an account, and use the dashboard.

## Docker

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

The application is available at <http://localhost:2000/>. The container runs migrations when it starts and stores SQLite data in the `sqlite_data` named volume.

The default configuration is for local evaluation. Before exposing the service, set a unique `SECRET_KEY`, set `DEBUG=False`, configure `ALLOWED_HOSTS`, and provide production media storage. Uploaded attachments under `/app/media` are not persisted by the current Compose file and are not served by WhiteNoise.

See [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for deployment constraints.

## Project Layout

```text
apps/
  accounts/          Native signup, login, and logout
  core/              Landing page and dashboard
  planner/           Scheduling domain, views, services, templates, and tests
config/              Django settings, root URLs, WSGI, and ASGI
docs/                Product, architecture, development, and operations docs
static/              Tailwind source/output and browser JavaScript
templates/           Base template and shared project partials
```

## Development

Run the complete test suite and static checks:

```bash
uv run python manage.py test
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check apps config
```

Tailwind CSS is configured in `static/css/input.css`. Download the standalone CLI once into the ignored `bin/` directory:

```bash
mkdir -p bin
curl -sL -o bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x bin/tailwindcss
./bin/tailwindcss -i static/css/input.css -o static/css/app.css
```

The compiled `static/css/app.css` is committed. Rebuild it whenever template utility classes or `input.css` change.

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for contribution conventions.

## Documentation

- [`ProductRequirementDocument.md`](docs/ProductRequirementDocument.md): current product scope and behavior.
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md): current system structure and technical decisions.
- [`DEVELOPMENT.md`](docs/DEVELOPMENT.md): local workflow and implementation conventions.
- [`OPERATIONS.md`](docs/OPERATIONS.md): configuration, Docker, persistence, and production gaps.

## License

Copyright (c) 2026 Henrique Mayer.

Licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). The source may be studied, run, and adapted for noncommercial use; it is not OSI open-source software and may not be used commercially under this license.
