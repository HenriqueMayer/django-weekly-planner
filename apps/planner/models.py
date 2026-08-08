"""Domain models for the planner app (PRD FR-06, FR-12, FR-13, FR-15, §8.2).

Fat-models philosophy (PRD R6): duration math, the midnight-crossing rule,
and overlap validation all live here so Sprint 8's model tests are cheap to
write and templates/views stay free of layout or business logic.
"""

import math
from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TimestampedModel

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Enter a valid hex color code, e.g. #FF5733.',
)

MIDNIGHT = time(0, 0)
MINUTES_PER_DAY = 24 * 60
STATUS_CHOICES = (
    ('planned', 'Planned'),
    ('in_progress', 'In progress'),
    ('partial', 'Partial'),
    ('completed', 'Completed'),
    ('incomplete', 'Incomplete'),
    ('abandoned', 'Abandoned'),
    ('transferred', 'Transferred'),
)


def minutes_since_midnight(value, treat_midnight_as_end_of_day=False):
    """Return the number of minutes between 00:00 and `value`.

    This is the single, centralized implementation of the midnight-crossing
    rule (PRD R3): when `treat_midnight_as_end_of_day` is True, a `value` of
    `00:00` is treated as 24:00 (1440 minutes) instead of 0. It backs both
    `TimeBlock`'s duration/overlap validation and `PlannerSettingsForm`'s
    day-range validation, so the rule is never re-implemented elsewhere.
    """
    if treat_midnight_as_end_of_day and value == MIDNIGHT:
        return MINUTES_PER_DAY
    return value.hour * 60 + value.minute


def round_half_up(value):
    """Round a non-negative float to the nearest integer, ties rounding up.

    Python's built-in `round()` uses banker's rounding (ties to even),
    which can silently produce a different result than "snap to the
    nearest slot boundary" expects when a value falls exactly halfway
    between two integers (PRD 5.1.3). Round-half-up is the more
    predictable, template-obvious behavior for this.

    This is the single, centralized implementation shared by
    `TimeBlock.get_rowspan()` and `apps.planner.grid.build_week_grid()`, so
    both agree on how a block's duration snaps to slot rows.
    """
    return math.floor(value + 0.5)


def time_from_minutes(total_minutes):
    """Convert a minutes-since-midnight count back into a `time` object.

    The inverse of `minutes_since_midnight()`: wraps at 1440 so a value of
    exactly `MINUTES_PER_DAY` (e.g. the end of a midnight-crossing block,
    or the last row of a 06:00-00:00 day) renders as `00:00` instead of
    raising `ValueError` on the invalid `time(24, 0)`.

    This is the single, centralized implementation shared by
    `apps.planner.grid.build_week_grid()` and every resize code path in
    `apps.planner.views`, so the minutes-to-time direction is never
    re-implemented elsewhere -- mirroring `minutes_since_midnight()` above
    for the reverse direction.
    """
    total_minutes %= MINUTES_PER_DAY
    hour, minute = divmod(total_minutes, 60)
    return time(hour, minute)


def format_time_label(value, time_format):
    """Format a `time` object per `PlannerSettings.time_format` (5.1.2).

    `'24h'` -> `'14:00'`. `'12h'` -> `'2:00 PM'`, built from the portable
    `%I:%M %p` (avoiding the platform-specific `%-I`) with the leading
    zero stripped by hand.

    Promoted here (Sprint 10) from what used to be a private
    `apps.planner.grid._format_time_label()`, following the same
    precedent already set for `time_from_minutes()` (Sprint 6,
    ARCHITECTURE.md): this is the single, centralized implementation
    shared by `apps.planner.grid.build_week_grid()` (on-screen row
    labels) and `apps.planner.export.render_week_markdown()` (the
    Markdown export), so both agree on how a `time` renders in either
    format.
    """
    if time_format == '12h':
        formatted = value.strftime('%I:%M %p')
        return formatted[1:] if formatted.startswith('0') else formatted
    return value.strftime('%H:%M')


class BlockColor(TimestampedModel):
    """A single entry in a user's personal color palette (PRD FR-13)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='block_colors',
    )
    name = models.CharField(max_length=50)
    hex_code = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_block_color_name_per_user',
            ),
        ]

    def __str__(self):
        return self.name


class PlannerSettings(TimestampedModel):
    """Per-user weekly grid display preferences (PRD FR-06, §8.2).

    Auto-created for every new user via a `post_save` signal on the user
    model (see `apps/planner/signals.py`, registered in
    `PlannerConfig.ready()`).
    """

    SLOT_INTERVAL_CHOICES = (
        (30, '30 minutes'),
        (60, '60 minutes'),
    )
    TIME_FORMAT_CHOICES = (
        ('24h', '24-hour'),
        ('12h', '12-hour AM/PM'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    slot_interval = models.IntegerField(choices=SLOT_INTERVAL_CHOICES, default=60)
    day_start = models.TimeField(default=time(6, 0))
    day_end = models.TimeField(default=time(0, 0))
    time_format = models.CharField(max_length=3, choices=TIME_FORMAT_CHOICES, default='24h')

    def __str__(self):
        return f'Planner settings for {self.user}'


class RecurrenceSeries(TimestampedModel):
    """Weekly recurrence rule whose materialized rows are `TimeBlock`s."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurrence_series',
    )
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    start_time = models.TimeField()
    end_time = models.TimeField()
    color = models.ForeignKey(
        BlockColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurrence_series',
    )
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    weekdays = models.JSONField(default=list)

    class Meta:
        ordering = ('starts_on', 'start_time')

    def __str__(self):
        return f'{self.label} ({self.starts_on})'

    def clean(self):
        super().clean()
        valid_days = {day for day, _ in TimeBlock.DAY_CHOICES}
        if not self.weekdays or any(day not in valid_days for day in self.weekdays):
            raise ValidationError('Choose at least one valid recurrence day.')
        if self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError('Recurrence end date must be on or after its start date.')
        if self.start_time == self.end_time and self.start_time != MIDNIGHT:
            raise ValidationError('End time must be after start time.')
        if self.start_time and self.end_time:
            duration = minutes_since_midnight(
                self.end_time, treat_midnight_as_end_of_day=True,
            ) - minutes_since_midnight(self.start_time)
            if duration <= 0:
                raise ValidationError('End time must be after start time.')

    def save(self, *args, **kwargs):
        self.weekdays = sorted({int(day) for day in self.weekdays})
        self.full_clean()
        super().save(*args, **kwargs)


class RecurrenceException(TimestampedModel):
    """A date intentionally omitted from a recurrence series."""

    series = models.ForeignKey(
        RecurrenceSeries,
        on_delete=models.CASCADE,
        related_name='exceptions',
    )
    occurrence_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['series', 'occurrence_date'],
                name='unique_recurrence_exception_date',
            ),
        ]


class TimeBlock(TimestampedModel):
    """A single scheduled block on one day of a user's week (PRD §8.2)."""

    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    STATUS_PLANNED = 'planned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PARTIAL = 'partial'
    STATUS_COMPLETED = 'completed'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_ABANDONED = 'abandoned'
    STATUS_TRANSFERRED = 'transferred'
    STATUS_CHOICES = STATUS_CHOICES

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='time_blocks',
    )
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    due_at = models.DateTimeField(null=True, blank=True)
    skipped = models.BooleanField(default=False)
    overridden = models.BooleanField(default=False)
    recurrence_series = models.ForeignKey(
        RecurrenceSeries,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='occurrences',
    )
    # Nullable during the transition so old programmatic callers can still
    # save a day-only block; planner forms always populate this field.
    scheduled_date = models.DateField(null=True, blank=True)
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    color = models.ForeignKey(
        BlockColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_blocks',
    )

    class Meta:
        ordering = ('scheduled_date', 'start_time')
        indexes = [
            models.Index(fields=['user', 'scheduled_date']),
            models.Index(fields=['user', 'day_of_week']),
        ]

    def __str__(self):
        day = self.scheduled_date or self.get_day_of_week_display()
        return f'{self.label} ({day} {self.start_time}-{self.end_time})'

    def get_duration_minutes(self):
        """Return the block's duration in minutes.

        `end_time == 00:00` is treated as 24:00 (midnight-crossing), via the
        shared `minutes_since_midnight()` helper.
        """
        start_minutes = minutes_since_midnight(self.start_time)
        end_minutes = minutes_since_midnight(self.end_time, treat_midnight_as_end_of_day=True)
        return end_minutes - start_minutes

    def get_rowspan(self, interval):
        """Return how many `interval`-minute slots this block spans.

        Uses round-half-up (via the shared `round_half_up()` helper), not
        floor division, so this agrees with `apps.planner.grid`'s own
        rowspan computation for the same block (PRD 5.1.3's "snap display
        to nearest slot boundary") -- e.g. a 90-minute block at a 60-minute
        interval spans 2 rows, not 1.
        """
        return round_half_up(self.get_duration_minutes() / interval)

    def clean(self):
        super().clean()
        if self.start_time is None or self.end_time is None or self.day_of_week is None:
            # Required-field errors are already reported by clean_fields();
            # nothing sensible to validate here yet.
            return

        if self.get_duration_minutes() <= 0:
            raise ValidationError('End time must be after start time.')

        if self.scheduled_date is not None:
            self.day_of_week = self.scheduled_date.weekday()

        for other in self._same_day_queryset():
            if self._overlaps(other):
                raise ValidationError(
                    f'This block overlaps with "{other.label}" '
                    f'({other.start_time}-{other.end_time}).'
                )

    def _same_day_queryset(self):
        """Return the user's other blocks on the same day (excludes self)."""
        queryset = TimeBlock.objects.filter(user=self.user, skipped=False)
        if self.scheduled_date is not None:
            queryset = queryset.filter(
                Q(scheduled_date=self.scheduled_date)
                | Q(scheduled_date__isnull=True, day_of_week=self.day_of_week),
            )
        else:
            queryset = queryset.filter(day_of_week=self.day_of_week, scheduled_date__isnull=True)
        return queryset.exclude(pk=self.pk)

    def _overlaps(self, other):
        """Return True if this block's time range overlaps `other`'s.

        Blocks that merely touch (`a.end == b.start`) are legal, not
        overlapping (PRD 8.1.2).
        """
        self_start = minutes_since_midnight(self.start_time)
        self_end = self_start + self.get_duration_minutes()
        other_start = minutes_since_midnight(other.start_time)
        other_end = other_start + other.get_duration_minutes()
        return self_start < other_end and other_start < self_end

    def save(self, *args, **kwargs):
        """Enforce `clean()` on every `.save()` call, matching NFR-08's
        authoritative server-side validation. Note this does not protect
        bulk `QuerySet.update()` calls, which bypass `save()`/`clean()`
        entirely -- a standard Django limitation, not specific to this
        model."""
        if self.scheduled_date is not None:
            self.day_of_week = self.scheduled_date.weekday()
        self.full_clean()
        super().save(*args, **kwargs)


class ActivityEvent(TimestampedModel):
    """Immutable user-visible history for a planner card."""

    time_block = models.ForeignKey(
        TimeBlock,
        on_delete=models.CASCADE,
        related_name='activity_events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='planner_activity_events',
    )
    event_type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ('-created_at', '-pk')
        indexes = [
            models.Index(fields=['time_block', '-created_at']),
        ]


class ChecklistItem(TimestampedModel):
    """An ordered, ownership-scoped checklist item on a planner card."""

    time_block = models.ForeignKey(
        TimeBlock,
        on_delete=models.CASCADE,
        related_name='checklist_items',
    )
    text = models.CharField(max_length=300)
    is_completed = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('position', 'created_at', 'pk')
        indexes = [
            models.Index(fields=['time_block', 'position']),
        ]

    def __str__(self):
        return self.text
