# Phase E — Card Comments

**Status:** complete

## Delivered

- Added authored `CardComment` records attached to planner cards.
- Added chronological comment display in the card detail panel.
- Added HTMX comment creation with server-side validation.
- Added ownership-scoped comment access through the card owner.
- Added `comment_added` activity events.
- Added author-only comment editing and deletion.
- Registered comments in Django admin.

## Rules

- Comments are limited to 2,000 characters and require a body.
- The authenticated user is always the author; client input cannot choose one.
- Comments cascade when their card is deleted.
- Comments and immutable activity events remain separate data concepts.

## Deliberate scope boundary

Mentions and threaded replies are reserved for a later collaboration pass.

## Verification

- Full Django test suite: 130 tests.
- `python manage.py check`.
- `python manage.py makemigrations --check --dry-run`.
- `ruff check apps static`.
- `git diff --check`.

All user-facing strings introduced by this phase are in English.
