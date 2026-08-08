# Phase C — Weekly Recurrence

**Status:** complete

## Delivered

- Added `RecurrenceSeries` for a user's weekly rule, date range, time range,
  label, status, description, and color.
- Added `RecurrenceException` for dates intentionally omitted from a series.
- Kept materialized occurrences as ordinary `TimeBlock` rows, so the existing
  grid, exports, overlap validation, ownership rules, and activity history all
  continue to use the same planner data source.
- Added transactional `create_weekly_series()` and `materialize_series()` helpers.
- Added weekly recurrence controls to the inline block creation form.
- Added overlap-tolerant materialization: a conflicting occurrence is skipped,
  while later dates in the same series are still created.
- Registered recurrence models in Django admin.

## Rules

- The recurrence start is the selected week's real Monday date.
- Weekdays are stored as ISO-compatible values from `0` (Monday) through `6`
  (Sunday), not as localized names or week numbers.
- The end date is inclusive.
- Materialization is idempotent: existing occurrence dates are not duplicated.
- Exceptions are checked before materializing a date.
- All series and occurrence queries remain user-scoped through the owning user.

## Deliberate scope boundary

Editing a recurrence rule from the card panel and a user-facing "skip this
occurrence" action are reserved for a follow-up interaction pass. The domain
model and service layer already support both without changing the grid source.

## Verification

- Full Django test suite: 116 tests.
- `python manage.py check`.
- `python manage.py makemigrations --check --dry-run`.
- `ruff check apps static`.
- `git diff --check`.

All user-facing strings introduced by this phase are in English.
