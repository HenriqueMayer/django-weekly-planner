# Phase F — Card Labels

**Status:** complete

## Delivered

- Added reusable user-owned `CardLabel` definitions with a color.
- Added many-to-many label associations on `TimeBlock`.
- Added card-panel label creation, association, and removal via HTMX.
- Added ownership checks for both cards and label definitions.
- Added `label_added` and `label_removed` activity events.
- Registered labels in Django admin.

## Rules

- A label name is unique per user, not globally.
- Removing a label only removes the card association.
- Labels remain reusable on other cards after removal.
- Label color is validated as a six-digit hex value.

## Verification

- Full Django test suite: 133 tests.
- `python manage.py check`.
- `python manage.py makemigrations --check --dry-run`.
- `ruff check apps static`.
- `git diff --check`.
