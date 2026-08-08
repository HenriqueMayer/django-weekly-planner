# Phase B — Card Details

**Status:** complete

## Delivered

- Added card status choices: Planned, In progress, Partial, Completed, Incomplete, Abandoned, and Transferred.
- Added optional description and due date fields to `TimeBlock`.
- Added `ActivityEvent` with actor, event type, payload, and ownership through the card relationship.
- Added a shared `record_activity()` service wrapped in a transaction.
- Added the responsive card detail panel loaded through HTMX.
- Added card property editing for title, description, status, and due date.
- Added activity display ordered from newest to oldest, limited to the latest 20 events.
- Added status and due-date indicators to Planner cards.
- Added focus restoration and `Escape` closing for the card panel.
- Added activity events for card creation, schedule edits, and detail edits.
- Added server-side status validation and ownership-scoped detail endpoints.
- Preserved the existing inline form for day/time/color edits so grid geometry remains stable.

## Transaction and ownership rules

- Detail updates are atomic with their activity event.
- Every card detail query filters by `request.user` before resolving the primary key.
- The grid is refreshed as an HTMX out-of-band fragment after a detail update.
- Invalid status values are rejected by Django's model form and create no activity event.

## Deliberate scope boundary

Checklists, labels, comments, attachments, transfers, and Kanban are not part of this phase.
The activity model is intentionally generic so those later phases can add event types without
creating a second history system.

## Verification

- Full Django test suite: 111 tests.
- `python manage.py check`.
- `python manage.py makemigrations --check --dry-run`.
- `ruff check apps static`.
- `git diff --check`.

All user-facing strings introduced by this phase are in English.
