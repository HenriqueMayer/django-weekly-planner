"""Model tests for the planner app (PRD 8.1.1-8.1.4).

Covers `TimeBlock` duration/rowspan math, `clean()`'s start/end rule
(including the documented midnight-crossing and full-day edge cases),
same-user overlap validation, `BlockColor`'s hex validator and per-user
uniqueness, the `SET_NULL` behavior on color deletion, and the
`PlannerSettings` auto-creation signal.
"""

from datetime import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.planner.models import BlockColor, PlannerSettings, TimeBlock

User = get_user_model()


class TimeBlockDurationTests(TestCase):
    """PRD 8.1.1: `get_duration_minutes()`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')

    def test_normal_case(self):
        block = TimeBlock(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 30),
        )
        self.assertEqual(block.get_duration_minutes(), 90)

    def test_midnight_crossing_end_case(self):
        """`end_time == 00:00` is treated as 24:00 (PRD R3)."""
        block = TimeBlock(
            user=self.user, label='Sleep', day_of_week=0,
            start_time=time(22, 0), end_time=time(0, 0),
        )
        self.assertEqual(block.get_duration_minutes(), 120)

    def test_start_and_end_both_midnight_is_a_full_day(self):
        """Documented edge case (ARCHITECTURE.md, Sprint 4): because the
        midnight exception only inspects `end_time`, `00:00`-to-`00:00`
        reads as a full 1440-minute day, not a zero-duration error."""
        block = TimeBlock(
            user=self.user, label='All day', day_of_week=0,
            start_time=time(0, 0), end_time=time(0, 0),
        )
        self.assertEqual(block.get_duration_minutes(), 1440)


class TimeBlockRowspanTests(TestCase):
    """PRD 8.1.1: `get_rowspan(interval)`, round-half-up not floor."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')

    def test_exact_multiple_of_interval(self):
        block = TimeBlock(
            user=self.user, label='Work', day_of_week=0,
            start_time=time(9, 0), end_time=time(11, 0),
        )
        self.assertEqual(block.get_rowspan(60), 2)

    def test_ninety_minutes_at_sixty_interval_rounds_up_to_two(self):
        """The round-half-up case explicitly called out in PRD 8.1.1: a
        90-minute block at a 60-minute interval must span 2 rows, not 1
        (floor division would wrongly give 1)."""
        block = TimeBlock(
            user=self.user, label='Study', day_of_week=0,
            start_time=time(9, 30), end_time=time(11, 0),
        )
        self.assertEqual(block.get_duration_minutes(), 90)
        self.assertEqual(block.get_rowspan(60), 2)

    def test_ninety_minutes_at_thirty_interval(self):
        block = TimeBlock(
            user=self.user, label='Study', day_of_week=0,
            start_time=time(9, 30), end_time=time(11, 0),
        )
        self.assertEqual(block.get_rowspan(30), 3)

    def test_full_day_rowspan_at_sixty_interval(self):
        block = TimeBlock(
            user=self.user, label='All day', day_of_week=0,
            start_time=time(0, 0), end_time=time(0, 0),
        )
        self.assertEqual(block.get_rowspan(60), 24)


class TimeBlockCleanTests(TestCase):
    """PRD 8.1.1: `clean()`'s start/end rule."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')

    def test_rejects_start_after_end(self):
        block = TimeBlock(
            user=self.user, label='Bad', day_of_week=0,
            start_time=time(11, 0), end_time=time(9, 0),
        )
        with self.assertRaises(ValidationError):
            block.full_clean()

    def test_rejects_zero_duration_non_midnight(self):
        """`start == end` at a non-midnight time is zero duration, not the
        full-day exception, and must be rejected."""
        block = TimeBlock(
            user=self.user, label='Bad', day_of_week=0,
            start_time=time(9, 0), end_time=time(9, 0),
        )
        with self.assertRaises(ValidationError):
            block.full_clean()

    def test_accepts_midnight_crossing_block(self):
        block = TimeBlock(
            user=self.user, label='Night shift', day_of_week=0,
            start_time=time(22, 0), end_time=time(0, 0),
        )
        block.full_clean()  # Must not raise.

    def test_accepts_full_day_midnight_to_midnight_block(self):
        """Documented edge case (not a bug, per ARCHITECTURE.md): validates
        successfully as a 24h block."""
        block = TimeBlock(
            user=self.user, label='All day', day_of_week=0,
            start_time=time(0, 0), end_time=time(0, 0),
        )
        block.full_clean()  # Must not raise.


class TimeBlockOverlapTests(TestCase):
    """PRD 8.1.2: overlap rejection, touching blocks allowed, self
    exclusion on update, and per-day/per-user scoping."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')
        cls.other_user = User.objects.create_user(username='bob', password='pass12345')

    def test_same_day_overlap_rejected(self):
        TimeBlock.objects.create(
            user=self.user, label='Work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        overlapping = TimeBlock(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 30), end_time=time(10, 30),
        )
        with self.assertRaises(ValidationError):
            overlapping.full_clean()

    def test_touching_blocks_are_allowed(self):
        """A block ending exactly when another starts is legal, not
        overlapping (the classic off-by-one)."""
        TimeBlock.objects.create(
            user=self.user, label='Work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        touching = TimeBlock(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(10, 0), end_time=time(11, 0),
        )
        touching.full_clean()  # Must not raise.
        touching.save()
        self.assertEqual(TimeBlock.objects.filter(user=self.user).count(), 2)

    def test_updating_unchanged_block_does_not_self_collide(self):
        """`self.pk` must be excluded from the overlap query, so re-saving
        an unchanged block never raises against itself."""
        block = TimeBlock.objects.create(
            user=self.user, label='Work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        block.label = 'Deep work'
        block.full_clean()  # Must not raise.
        block.save()
        block.refresh_from_db()
        self.assertEqual(block.label, 'Deep work')

    def test_overlap_on_different_day_is_allowed(self):
        TimeBlock.objects.create(
            user=self.user, label='Work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        other_day = TimeBlock(
            user=self.user, label='Gym', day_of_week=1,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        other_day.full_clean()  # Must not raise.

    def test_overlap_for_different_user_is_allowed(self):
        """Same day/time overlap is only checked within one user's own
        blocks (also an ownership-isolation guarantee)."""
        TimeBlock.objects.create(
            user=self.user, label='Work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        other_users_block = TimeBlock(
            user=self.other_user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        other_users_block.full_clean()  # Must not raise.


class BlockColorHexValidatorTests(TestCase):
    """PRD 8.1.3: `HEX_COLOR_VALIDATOR` regex."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')

    def test_rejects_missing_hash(self):
        color = BlockColor(user=self.user, name='Work', hex_code='FF5733')
        with self.assertRaises(ValidationError):
            color.full_clean()

    def test_rejects_wrong_length(self):
        color = BlockColor(user=self.user, name='Work', hex_code='#FF57')
        with self.assertRaises(ValidationError):
            color.full_clean()

    def test_rejects_non_hex_characters(self):
        color = BlockColor(user=self.user, name='Work', hex_code='#GGHHII')
        with self.assertRaises(ValidationError):
            color.full_clean()

    def test_accepts_uppercase_hex(self):
        color = BlockColor(user=self.user, name='Work', hex_code='#FF5733')
        color.full_clean()  # Must not raise.

    def test_accepts_lowercase_hex(self):
        color = BlockColor(user=self.user, name='Work', hex_code='#ff5733')
        color.full_clean()  # Must not raise.


class BlockColorUniqueConstraintTests(TestCase):
    """PRD 8.1.3: `UniqueConstraint(fields=['user', 'name'])`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='alice', password='pass12345')
        cls.other_user = User.objects.create_user(username='bob', password='pass12345')

    def test_rejects_duplicate_name_for_same_user(self):
        BlockColor.objects.create(user=self.user, name='Work', hex_code='#FF5733')
        duplicate = BlockColor(user=self.user, name='Work', hex_code='#000000')
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_allows_same_name_for_different_users(self):
        BlockColor.objects.create(user=self.user, name='Work', hex_code='#FF5733')
        other_users_color = BlockColor(user=self.other_user, name='Work', hex_code='#123456')
        other_users_color.full_clean()  # Must not raise.


class BlockColorSetNullTests(TestCase):
    """PRD 8.1.3: deleting a referenced `BlockColor` sets `TimeBlock.color`
    to `None` (`SET_NULL`) rather than deleting the block."""

    def test_deleting_color_nulls_referencing_block_without_deleting_it(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        color = BlockColor.objects.create(user=user, name='Work', hex_code='#FF5733')
        block = TimeBlock.objects.create(
            user=user, label='Deep work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0), color=color,
        )

        color.delete()

        block.refresh_from_db()
        self.assertIsNone(block.color)
        self.assertTrue(TimeBlock.objects.filter(pk=block.pk).exists())


class PlannerSettingsSignalTests(TestCase):
    """PRD 8.1.4: `post_save` on the user model auto-creates
    `PlannerSettings` with the documented defaults, exactly once."""

    def test_creates_planner_settings_with_documented_defaults(self):
        user = User.objects.create_user(username='alice', password='pass12345')

        self.assertEqual(PlannerSettings.objects.filter(user=user).count(), 1)
        settings_obj = PlannerSettings.objects.get(user=user)
        self.assertEqual(settings_obj.slot_interval, 60)
        self.assertEqual(settings_obj.day_start, time(6, 0))
        self.assertEqual(settings_obj.day_end, time(0, 0))
        self.assertEqual(settings_obj.time_format, '24h')

    def test_saving_existing_user_again_does_not_create_a_second_row(self):
        user = User.objects.create_user(username='alice', password='pass12345')
        self.assertEqual(PlannerSettings.objects.filter(user=user).count(), 1)

        user.first_name = 'Alice'
        user.save()

        self.assertEqual(PlannerSettings.objects.filter(user=user).count(), 1)
