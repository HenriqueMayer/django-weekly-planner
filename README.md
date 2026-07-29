# django-weekly-planner
A modular, time-blocking weekly planner template built with Python, Django, and CSS Grid. Organize your routine like a spreadsheet.

## Development

### Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- No Node.js / npm required — CSS is built with the Tailwind **standalone CLI** binary (PRD risk R4).

### Backend

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

### TailwindCSS build pipeline

This project uses **Tailwind CSS v4** with its CSS-first configuration — there is no `tailwind.config.js`. Dark mode and template source paths are declared directly in `static/css/input.css`:

```css
@import 'tailwindcss';
@custom-variant dark (&:where(.dark, .dark *));
@source '../../templates';
@source '../../apps';
```

> **Deviation from PRD §13 task 1.3:** the PRD describes a v3-style workflow (`@tailwind` directives, `tailwind.config.js`, `darkMode: 'class'`). Tailwind is now v4 and configures itself in CSS instead of JavaScript, so those concepts map onto `@import`, `@custom-variant dark`, and `@source` as shown above. There is intentionally no `tailwind.config.js` in this repository.

The CLI itself is a self-contained executable (no npm project, nothing in `package.json`) and is **not committed** to the repository (~100 MB binary) — download it once per machine into `bin/`, which is git-ignored:

```sh
# Linux x86_64 (this project's dev environment)
mkdir -p bin
curl -sL -o bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x bin/tailwindcss
```

For other platforms, swap the asset name (`tailwindcss-macos-arm64`, `tailwindcss-macos-x64`, `tailwindcss-windows-x64.exe`, ...) — see the [release page](https://github.com/tailwindlabs/tailwindcss/releases/latest).

Build the compiled stylesheet (`static/css/app.css`, which **is** committed — PRD risk R4):

```sh
./bin/tailwindcss -i static/css/input.css -o static/css/app.css
```

Watch for changes while developing templates:

```sh
./bin/tailwindcss -i static/css/input.css -o static/css/app.css --watch
```

Minify for a production build:

```sh
./bin/tailwindcss -i static/css/input.css -o static/css/app.css --minify
```

**Whenever you add or change a Tailwind utility class in any template, rebuild `app.css` before judging the page — an unbuilt stylesheet is not a design bug.**

### Running tests

```sh
uv run python manage.py test
```

Runs the full suite (models, views, and the pure-Python grid builder) against Django's own throwaway test database — nothing here depends on `db.sqlite3` or any seeded data, so this passes clean from a fresh clone right after `uv sync` + `migrate`.
