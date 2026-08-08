"""Recurrence rule and materialization tests for Phase C."""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import ActivityEvent, RecurrenceException, RecurrenceSeries, TimeBlock
from apps.planner.recurrence import create_weekly_series, materialize_series, update_weekly_series

User = get_user_model()


class RecurrenceSeriesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')

    def test_materializes_selected_weekdays_until_end_date(self):
        series = create_weekly_series(
            user=self.user,
            label='Training',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0, 2],
            ends_on=date(2026, 8, 24),
        )

        self.assertEqual(
            list(series.occurrences.values_list('scheduled_date', flat=True)),
            [
                date(2026, 8, 3), date(2026, 8, 5),
                date(2026, 8, 10), date(2026, 8, 12),
                date(2026, 8, 17), date(2026, 8, 19),
                date(2026, 8, 24),
            ],
        )

    def test_exception_prevents_later_materialization(self):
        series = RecurrenceSeries.objects.create(
            user=self.user,
            label='Focus',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            ends_on=date(2026, 8, 17),
            weekdays=[0],
        )
        RecurrenceException.objects.create(
            series=series,
            occurrence_date=date(2026, 8, 10),
        )

        materialize_series(series)

        self.assertEqual(
            list(series.occurrences.values_list('scheduled_date', flat=True)),
            [date(2026, 8, 3), date(2026, 8, 17)],
        )

    def test_overlapping_occurrence_is_skipped_without_aborting_series(self):
        TimeBlock.objects.create(
            user=self.user,
            label='Existing',
            scheduled_date=date(2026, 8, 10),
            day_of_week=0,
            start_time=time(9),
            end_time=time(10),
        )

        series = create_weekly_series(
            user=self.user,
            label='Focus',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 17),
        )

        self.assertEqual(
            list(series.occurrences.values_list('scheduled_date', flat=True)),
            [date(2026, 8, 3), date(2026, 8, 17)],
        )

    def test_invalid_weekday_is_rejected(self):
        with self.assertRaises(ValidationError):
            RecurrenceSeries.objects.create(
                user=self.user,
                label='Invalid',
                start_time=time(9),
                end_time=time(10),
                starts_on=date(2026, 8, 3),
                weekdays=[7],
            )

    def test_updating_rule_rebuilds_future_non_skipped_occurrences(self):
        series = create_weekly_series(
            user=self.user,
            label='Focus',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 24),
        )
        series.weekdays = [2]
        series.save()
        update_weekly_series(series, effective_from=date(2026, 8, 10))

        self.assertEqual(
            list(series.occurrences.values_list('scheduled_date', flat=True)),
            [date(2026, 8, 3), date(2026, 8, 12), date(2026, 8, 19)],
        )

    def test_future_occurrences_use_updated_series_properties(self):
        series = create_weekly_series(
            user=self.user,
            label='Old label',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 17),
        )
        series.label = 'New label'
        series.start_time = time(11)
        series.end_time = time(12)
        series.save()
        update_weekly_series(series, effective_from=date(2026, 8, 10))

        historical = series.occurrences.get(scheduled_date=date(2026, 8, 3))
        future = series.occurrences.get(scheduled_date=date(2026, 8, 10))
        self.assertEqual(historical.label, 'Old label')
        self.assertEqual(future.label, 'New label')
        self.assertEqual(future.start_time, time(11))

    def test_bulk_update_preserves_an_overridden_future_occurrence(self):
        series = create_weekly_series(
            user=self.user,
            label='Series label',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 17),
        )
        overridden = series.occurrences.get(scheduled_date=date(2026, 8, 10))
        overridden.label = 'Personal label'
        overridden.overridden = True
        overridden.save()
        series.label = 'Updated series label'
        series.save()
        update_weekly_series(series, effective_from=date(2026, 8, 10))

        overridden.refresh_from_db()
        self.assertEqual(overridden.label, 'Personal label')
        self.assertTrue(overridden.overridden)


class RecurrenceCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_create_form_creates_series_occurrences_and_activity(self):
        response = self.client.post(reverse('planner:block-create'), {
            'week': '2026-08-03',
            'label': 'Weekly review',
            'day_of_week': '0',
            'start_time': '09:00',
            'end_time': '10:00',
            'recurrence_weekly': 'on',
            'recurrence_weekdays': ['0', '4'],
            'recurrence_until': '2026-08-28',
        })

        self.assertEqual(response.status_code, 200)
        series = RecurrenceSeries.objects.get(user=self.user)
        self.assertEqual(series.occurrences.count(), 8)
        self.assertEqual(ActivityEvent.objects.filter(event_type='recurrence_created').count(), 1)

    def test_skip_occurrence_hides_it_and_creates_exception(self):
        series = create_weekly_series(
            user=self.user,
            label='Weekly review',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 17),
        )
        occurrence = series.occurrences.get(scheduled_date=date(2026, 8, 10))

        response = self.client.post(reverse('planner:occurrence-skip', args=[occurrence.pk]))

        self.assertEqual(response.status_code, 200)
        occurrence.refresh_from_db()
        self.assertTrue(occurrence.skipped)
        self.assertTrue(series.exceptions.filter(occurrence_date=date(2026, 8, 10)).exists())
        self.assertTrue(occurrence.activity_events.filter(event_type='occurrence_skipped').exists())

        response = self.client.post(reverse('planner:occurrence-restore', args=[occurrence.pk]))

        self.assertEqual(response.status_code, 200)
        occurrence.refresh_from_db()
        self.assertFalse(occurrence.skipped)
        self.assertFalse(series.exceptions.filter(occurrence_date=date(2026, 8, 10)).exists())
        self.assertTrue(occurrence.activity_events.filter(event_type='occurrence_restored').exists())

    def test_recurrence_update_is_ownership_scoped(self):
        other = User.objects.create_user(username='bob', password='pass12345')
        series = create_weekly_series(
            user=other,
            label='Private',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 17),
        )
        occurrence = series.occurrences.first()

        response = self.client.post(
            reverse('planner:recurrence-update', args=[occurrence.pk]),
            {'weekdays': ['1'], 'ends_on': '2026-08-24'},
        )

        self.assertEqual(response.status_code, 404)

    def test_recurrence_update_applies_properties_to_future_occurrences(self):
        series = create_weekly_series(
            user=self.user,
            label='Old label',
            start_time=time(9),
            end_time=time(10),
            starts_on=date(2026, 8, 3),
            weekdays=[0],
            ends_on=date(2026, 8, 17),
        )
        occurrence = series.occurrences.first()

        response = self.client.post(
            reverse('planner:recurrence-update', args=[occurrence.pk]),
            {
                'label': 'New label',
                'description': 'Updated description',
                'status': 'in_progress',
                'start_time': '11:00',
                'end_time': '12:00',
                'color': '',
                'weekdays': ['0'],
                'ends_on': '2026-08-17',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            TimeBlock.objects.get(scheduled_date=date(2026, 8, 3)).label,
            'Old label',
        )
        future = TimeBlock.objects.get(scheduled_date=date(2026, 8, 10))
        self.assertEqual(future.label, 'New label')
        self.assertEqual(future.start_time, time(11))
