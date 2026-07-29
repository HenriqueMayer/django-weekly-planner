"""Domain models for the planner app (PRD FR-06, FR-12, FR-13, FR-15, §8.2).

Fat-models philosophy (PRD R6): duration math, the midnight-crossing rule,
and overlap validation all live here so Sprint 8's model tests are cheap to
write and templates/views stay free of layout or business logic.
"""

from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import TimestampedModel

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Enter a valid hex color code, e.g. #FF5733.',
)

MIDNIGHT = time(0, 0)
MINUTES_PER_DAY = 24 * 60


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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='time_blocks',
    )
    label = models.CharField(max_length=200)
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
        ordering = ('day_of_week', 'start_time')

    def __str__(self):
        return f'{self.label} ({self.get_day_of_week_display()} {self.start_time}-{self.end_time})'

    def get_duration_minutes(self):
        """Return the block's duration in minutes.

        `end_time == 00:00` is treated as 24:00 (midnight-crossing), via the
        shared `minutes_since_midnight()` helper.
        """
        start_minutes = minutes_since_midnight(self.start_time)
        end_minutes = minutes_since_midnight(self.end_time, treat_midnight_as_end_of_day=True)
        return end_minutes - start_minutes

    def get_rowspan(self, interval):
        """Return how many `interval`-minute slots this block spans."""
        return self.get_duration_minutes() // interval

    def clean(self):
        super().clean()
        if self.start_time is None or self.end_time is None or self.day_of_week is None:
            # Required-field errors are already reported by clean_fields();
            # nothing sensible to validate here yet.
            return

        if self.get_duration_minutes() <= 0:
            raise ValidationError('End time must be after start time.')

        for other in self._same_day_queryset():
            if self._overlaps(other):
                raise ValidationError(
                    f'This block overlaps with "{other.label}" '
                    f'({other.start_time}-{other.end_time}).'
                )

    def _same_day_queryset(self):
        """Return the user's other blocks on the same day (excludes self)."""
        return TimeBlock.objects.filter(
            user=self.user,
            day_of_week=self.day_of_week,
        ).exclude(pk=self.pk)

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
        self.full_clean()
        super().save(*args, **kwargs)
