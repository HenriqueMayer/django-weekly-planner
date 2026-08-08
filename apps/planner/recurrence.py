"""Creation and materialization helpers for weekly recurrence rules."""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.planner.models import RecurrenceSeries, TimeBlock


@transaction.atomic
def materialize_series(series, from_date=None, to_date=None):
    """Create missing, non-exception occurrences in an inclusive date range."""
    start = max(from_date or series.starts_on, series.starts_on)
    end = to_date or series.ends_on
    if series.ends_on:
        end = min(end or series.ends_on, series.ends_on)
    if end is None or end < start:
        return []

    exception_dates = set(
        series.exceptions.filter(
            occurrence_date__gte=start,
            occurrence_date__lte=end,
        ).values_list('occurrence_date', flat=True)
    )
    existing_dates = set(
        series.occurrences.filter(
            scheduled_date__gte=start,
            scheduled_date__lte=end,
        ).values_list('scheduled_date', flat=True)
    )
    created = []
    current = start
    while current <= end:
        if current.weekday() in series.weekdays and current not in exception_dates:
            if current not in existing_dates:
                occurrence = TimeBlock(
                    user=series.user,
                    label=series.label,
                    description=series.description,
                    status=series.status,
                    start_time=series.start_time,
                    end_time=series.end_time,
                    color=series.color,
                    scheduled_date=current,
                    day_of_week=current.weekday(),
                    recurrence_series=series,
                )
                try:
                    occurrence.save()
                except ValidationError:
                    pass
                else:
                    created.append(occurrence)
        current += timedelta(days=1)
    return created


@transaction.atomic
def create_weekly_series(*, user, label, start_time, end_time, starts_on, weekdays,
                         ends_on=None, description='', status='planned', color=None):
    """Create a rule and its initial materialized occurrences."""
    series = RecurrenceSeries.objects.create(
        user=user,
        label=label,
        description=description,
        status=status,
        start_time=start_time,
        end_time=end_time,
        color=color,
        starts_on=starts_on,
        ends_on=ends_on,
        weekdays=weekdays,
    )
    materialize_series(series)
    return series


@transaction.atomic
def update_weekly_series(series, effective_from=None):
    """Apply the changed rule to future, non-skipped occurrences."""
    effective_from = max(effective_from or date.today(), series.starts_on)
    series.occurrences.filter(
        scheduled_date__gte=effective_from,
        skipped=False,
    ).delete()
    return materialize_series(series, from_date=effective_from)
