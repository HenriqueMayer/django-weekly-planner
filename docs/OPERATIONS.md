# Operations Guide

The included Docker setup is suitable for local evaluation and small private deployments. It is not a complete production platform.

## Configuration

| Variable | Default when unset | Requirement |
|---|---|---|
| `SECRET_KEY` | Insecure development key | Set a unique secret outside local development |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | Empty list | Set allowed hostnames before deployment |

Docker also sets these internal values:

- `SQLITE_DB_PATH=/app/data/db.sqlite3`
- `DJANGO_USE_WHITENOISE=True`

Create local environment configuration with:

```bash
cp .env.example .env
```

## Docker Lifecycle

```bash
docker compose build
docker compose up -d
docker compose logs -f web
docker compose down
```

Compose publishes container port 8000 as host port 2000. Container startup runs database migrations before starting Gunicorn.

Static assets are collected during image build. `static/css/app.css` must already be compiled and committed before building the image.

## Persistence

The `sqlite_data` volume persists `/app/data/db.sqlite3` across container recreation. Back up this volume before schema or infrastructure changes.

Uploaded attachments are stored under `/app/media`. The current Compose file does not mount that path, so attachments are lost when the container is replaced. A deployment that enables attachments must add persistent media storage and back it up with the database.

## Static and Media Files

- WhiteNoise serves collected static files from the application image.
- WhiteNoise does not serve uploaded media.
- Django serves media URLs only in development when `DEBUG=True`.
- With `DEBUG=False`, configure a reverse proxy, object storage, or another media-serving solution.

## Production Checklist

- Set a unique `SECRET_KEY` outside source control.
- Set `DEBUG=False` and explicit `ALLOWED_HOSTS`.
- Configure HTTPS and secure proxy headers at the ingress layer.
- Persist and serve `/app/media`, or replace filesystem media storage.
- Define database and media backup/restore procedures.
- Add health checks, monitoring, and centralized logs.
- Review Gunicorn worker and timeout settings for the target host.
- Run Django's deployment check: `python manage.py check --deploy`.
- Run the complete test and migration checks before building.
- Consider PostgreSQL before supporting concurrent multi-user workloads.
- Run the container as a non-root user in hardened environments; the current image does not set `USER`.

## Known Operational Limits

- SQLite serializes writes and is not intended for high concurrency.
- The application timezone is UTC and is not user-configurable.
- There is no reverse proxy, TLS, health check, worker queue, cache, monitoring, or CI/CD configuration in this repository.
- Migrations run at every container start; coordinate startup if multiple replicas are introduced.
