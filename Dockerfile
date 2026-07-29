# syntax=docker/dockerfile:1

# python:3.12-slim matches this project's `requires-python = ">=3.12"`
# (pyproject.toml). uv is installed by copying its prebuilt binary from the
# official distroless image — the Context7-confirmed current approach
# (astral-sh/uv docs > guides/integration/docker.md), pinned to the version
# used to develop this project for reproducible builds.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_USE_WHITENOISE=True \
    SQLITE_DB_PATH=/app/data/db.sqlite3

WORKDIR /app

# Install dependencies before copying the rest of the app so this layer is
# cached across code-only changes. Installs the main `dependencies` (just
# Django) plus the Docker-only `docker` group (gunicorn, whitenoise) and
# explicitly excludes the `dev` group (ruff) — confirmed via Context7
# (astral-sh/uv docs > concepts/projects/sync.md and dependencies.md):
# `--no-dev` disables the `dev` group specifically, `--group docker` adds
# the docker-only group on top of the main dependencies, and `--locked`
# requires uv.lock to already be up to date with pyproject.toml (fails the
# build instead of silently re-resolving).
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --group docker --no-install-project

# Now copy the application and finish the sync (installs the project itself
# in addition to its dependencies).
COPY . .
RUN uv sync --locked --no-dev --group docker

# Dedicated directory for the SQLite file (see SQLITE_DB_PATH above and
# `config/settings.py`). A *directory* is volume-mounted here at runtime,
# not the db.sqlite3 file itself — named volumes mounted directly onto a
# single file path were tested against this environment's Docker daemon
# and fail outright ("<path> is not directory" on first creation, reproduced
# even with a trivial one-file test image), so persistence is achieved by
# mounting this directory instead, which is Docker's well-supported case.
RUN mkdir -p /app/data

# Static files are baked into the image at build time; only /app/data (the
# SQLite file's directory) is expected to live on a runtime volume (see
# docker-compose.yml) — nothing else under /app should be volume-mounted,
# or it would shadow this image's own code and virtual environment on every
# restart.
#
# `--ignore=input.css` excludes the raw, uncompiled Tailwind v4 source (it
# contains a bare `@import 'tailwindcss'` resolved only by the Tailwind CLI,
# not a real relative file path) from collectstatic's post-processing —
# only the already-committed, already-compiled `static/css/app.css` is
# actually served (see the brief: no Tailwind build step in this image).
RUN python manage.py collectstatic --noinput --ignore=input.css

EXPOSE 8000

# `migrate` must run at container *start*, not build time, since it depends
# on the runtime-mounted /app/data volume (holding db.sqlite3), which may
# not exist yet on a first run. A one-line inline shell entrypoint is
# enough here (NFR-01) — no separate entrypoint.sh script for a single `&&`.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
