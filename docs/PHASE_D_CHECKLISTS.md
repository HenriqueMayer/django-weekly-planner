# Phase D — Card Checklists

**Status:** complete

## Delivered

- Added ordered `ChecklistItem` rows owned through `TimeBlock`.
- Added checklist display inside the card detail panel.
- Added HTMX item creation, completion toggle, and deletion.
- Added ownership-scoped endpoints for every checklist mutation.
- Added activity events for item creation, completion changes, and deletion.
- Registered checklist items in Django admin.

## Rules

- Checklist text is required and limited to 300 characters.
- New items receive the next position on their card.
- Completion changes do not alter card geometry or recurrence rules.
- Deleting a card cascades to its checklist items.
- An item can only be accessed through a card owned by the authenticated user.

## Deliberate scope boundary

Drag reordering, nested checklist items, and checklist editing are reserved for
a later interaction pass. The current ordered model supports reordering without
changing the card or recurrence data model.

## Verification

- Full Django test suite: 125 tests.
- `python manage.py check`.
- `python manage.py makemigrations --check --dry-run`.
- `ruff check apps static`.
- `git diff --check`.

All user-facing strings introduced by this phase are in English.
