"""Unit tests for ISO-week navigation and calendar data."""

from datetime import date

from django.test import SimpleTestCase

from apps.planner.dates import month_calendar, normalize_week_start, parse_week_start, week_label


class PlannerDateTests(SimpleTestCase):
    def test_week_start_is_always_monday(self):
        self.assertEqual(normalize_week_start(date(2026, 8, 8)), date(2026, 8, 3))

    def test_parser_normalizes_non_monday_and_rejects_invalid_input(self):
        self.assertEqual(parse_week_start('2026-08-05'), date(2026, 8, 3))
        self.assertEqual(parse_week_start('not-a-date').weekday(), 0)

    def test_week_label_contains_iso_week_and_date_range(self):
        self.assertEqual(
            week_label(date(2026, 8, 3)),
            'Week 32 - 2026 · 03–09 Aug 2026',
        )

    def test_calendar_marks_only_the_selected_week_start(self):
        rows = month_calendar(date(2026, 8, 1), date(2026, 8, 3))
        selected_days = [day for row in rows for day in row['days'] if day['is_selected']]
        self.assertEqual([day['date'] for day in selected_days], [date(2026, 8, 3)])

    def test_calendar_uses_natural_month_rows_and_starts_on_sunday(self):
        rows = month_calendar(date(2026, 2, 1), date(2026, 2, 2))

        self.assertEqual(len(rows), 4)
        self.assertEqual(
            [day['date'].weekday() for day in rows[0]['days']],
            [6, 0, 1, 2, 3, 4, 5],
        )
        self.assertTrue(rows[0]['days'][0]['is_weekend'])
