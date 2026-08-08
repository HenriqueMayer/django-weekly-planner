# Phase A — Week Foundation

**Status:** complete

## Delivered

- Added `TimeBlock.scheduled_date` as the real calendar date for a block.
- Added a data migration that assigns pre-existing blocks to the current ISO week without deleting them.
- Added indexes for user/date and user/day lookups.
- Added centralized helpers for Monday normalization, ISO week parsing, week labels, month movement, and calendar rows.
- Updated the dashboard and standalone planner to read one selected week from `?week=YYYY-MM-DD`.
- Added previous-week, next-week, and Today navigation.
- Added a compact month calendar popover with ISO week numbers and direct week selection.
- Added keyboard navigation with Left Arrow, Right Arrow, and Home when focus is not inside an editable control.
- Updated block creation, HTMX responses, and exports to preserve the selected week.
- Kept a temporary null-date compatibility path for legacy programmatic blocks; application forms always write `scheduled_date`.

## ISO week rules

- The URL stores a real Monday date, not a week number.
- The displayed week number is derived from ISO 8601 (`date.isocalendar()`).
- A value such as `2026-08-12` is normalized to `2026-08-10`.
- Invalid week values fall back to the current Monday instead of raising an exception.

## Recurrence decision

Recurring weekly cards were intentionally not materialized in this phase. The date foundation is
now used by Phase C's recurrence series and occurrence exceptions without storing week numbers as
persistent data or creating a second planner data source.

## Verification

- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- Full Django test suite, including the new ISO-week and selected-week tests.

All user-facing strings introduced by this phase are in English.
