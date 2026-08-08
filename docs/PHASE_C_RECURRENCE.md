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
- Added card-panel editing for weekly days and the inclusive end date.
- Recurrence edits can now apply label, description, status, times, color, days,
  and end date to future non-skipped occurrences.
- Added a per-occurrence skip action that persists an exception and hides the
  occurrence from the grid without deleting its activity history.
- Added explicit per-occurrence overrides that survive later series edits.
- Added restore actions for skipped and overridden occurrences.
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

Individual generated occurrence edits are marked as overrides and are kept
when the series rule is later rebuilt. The panel can restore an override to the
current series values.

## Verification

- Full Django test suite: 122 tests.
- `python manage.py check`.
- `python manage.py makemigrations --check --dry-run`.
- `ruff check apps static`.
- `git diff --check`.

All user-facing strings introduced by this phase are in English.
