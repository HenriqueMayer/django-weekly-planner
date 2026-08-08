"""View tests for the planner app (PRD 8.2.1-8.2.4).

Uses `django.test.Client`/`TestCase` throughout -- no raw scripts. Covers
auth protection, per-user ownership isolation (404, never 403, on a
cross-user pk), the block/color CRUD + resize HTMX-fragment contracts
(success is 200, not a redirect; validation failure is 200 with
`HX-Retarget`/`HX-Reswap`, never a persisted row), the `repeat_days`
feature, the `grid_oob` out-of-band mechanism, and the settings-update
view.
"""

import re
import xml.etree.ElementTree as ET
from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.planner.models import BlockColor, PlannerSettings, TimeBlock

User = get_user_model()

# Matches the opening `<div id="grid-table" ...>` tag only -- not the
# `#grid-toast` div, which unconditionally carries its own
# `hx-swap-oob="true"` regardless of `grid_oob` (see grid_table.html's
# docstring), so a plain substring search for "hx-swap-oob" anywhere in
# the response body would not actually prove anything about this tag.
GRID_TABLE_TAG_RE = re.compile(r'<div\s+id="grid-table"[^>]*>')


def _grid_table_tag(content):
    match = GRID_TABLE_TAG_RE.search(content)
    assert match is not None, 'response did not contain a #grid-table element'
    return match.group(0)


class AuthProtectionTests(TestCase):
    """PRD 8.2.1: every planner/dashboard route redirects an anonymous
    client to login -- never a 200, never a 500."""

    # (url_name, http_method, url_kwargs). A dummy pk of 999999 is safe for
    # every pk-taking view here: `LoginRequiredMixin` redirects in
    # `dispatch()`, before any queryset/`get_object()` lookup ever runs.
    PROTECTED_URLS = [
        ('core:dashboard', 'get', {}),
        ('planner:grid', 'get', {}),
        ('planner:settings', 'get', {}),
        ('planner:block-create', 'get', {}),
        ('planner:block-edit', 'get', {'pk': 999999}),
        ('planner:block-delete', 'post', {'pk': 999999}),
        ('planner:block-resize', 'post', {'pk': 999999}),
        ('planner:block-cancel', 'get', {'pk': 999999}),
        ('planner:cell-cancel', 'get', {}),
        ('planner:palette', 'get', {}),
        ('planner:color-create', 'get', {}),
        ('planner:color-edit', 'get', {'pk': 999999}),
        ('planner:color-cancel', 'get', {'pk': 999999}),
        ('planner:color-delete', 'post', {'pk': 999999}),
        ('planner:export-markdown', 'get', {}),
        ('planner:export-svg', 'get', {}),
    ]

    def test_anonymous_client_is_redirected_to_login(self):
        for url_name, method, kwargs in self.PROTECTED_URLS:
            with self.subTest(url_name=url_name, method=method):
                url = reverse(url_name, kwargs=kwargs)
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/accounts/login/'))


class OwnershipIsolationTests(TestCase):
    """PRD 8.2.2: user A gets 404, never 403, on user B's block/color pk,
    on every endpoint that takes one -- and the underlying row is
    untouched by the attempt."""

    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create_user(username='alice', password='pass12345')
        cls.user_b = User.objects.create_user(username='bob', password='pass12345')
        cls.color_b = BlockColor.objects.create(user=cls.user_b, name='Focus', hex_code='#4f46e5')
        cls.block_b = TimeBlock.objects.create(
            user=cls.user_b, label='Deep work', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0), color=cls.color_b,
        )

    def setUp(self):
        self.client.force_login(self.user_a)

    def test_block_edit_get_returns_404(self):
        response = self.client.get(reverse('planner:block-edit', args=[self.block_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_block_edit_post_returns_404_and_does_not_modify_block(self):
        response = self.client.post(
            reverse('planner:block-edit', args=[self.block_b.pk]),
            {'label': 'Hijacked', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00'},
        )
        self.assertEqual(response.status_code, 404)
        self.block_b.refresh_from_db()
        self.assertEqual(self.block_b.label, 'Deep work')

    def test_block_delete_returns_404_and_block_survives(self):
        response = self.client.post(reverse('planner:block-delete', args=[self.block_b.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(TimeBlock.objects.filter(pk=self.block_b.pk).exists())

    def test_block_resize_returns_404_and_block_unchanged(self):
        response = self.client.post(
            reverse('planner:block-resize', args=[self.block_b.pk]),
            {'start_time': '11:00', 'end_time': '12:00'},
        )
        self.assertEqual(response.status_code, 404)
        self.block_b.refresh_from_db()
        self.assertEqual(self.block_b.start_time, time(9, 0))
        self.assertEqual(self.block_b.end_time, time(10, 0))

    def test_block_cancel_returns_404(self):
        response = self.client.get(reverse('planner:block-cancel', args=[self.block_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_color_edit_get_returns_404(self):
        response = self.client.get(reverse('planner:color-edit', args=[self.color_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_color_edit_post_returns_404_and_does_not_modify_color(self):
        response = self.client.post(
            reverse('planner:color-edit', args=[self.color_b.pk]),
            {'name': 'Hijacked', 'hex_code': '#000000'},
        )
        self.assertEqual(response.status_code, 404)
        self.color_b.refresh_from_db()
        self.assertEqual(self.color_b.name, 'Focus')

    def test_color_cancel_returns_404(self):
        response = self.client.get(reverse('planner:color-cancel', args=[self.color_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_color_delete_returns_404_and_color_survives(self):
        response = self.client.post(reverse('planner:color-delete', args=[self.color_b.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(BlockColor.objects.filter(pk=self.color_b.pk).exists())


class BlockCrudViewTests(TestCase):
    """PRD 8.2.3: block create/edit/delete/resize contracts."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_create_success_returns_200_and_persists(self):
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Gym', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        block = TimeBlock.objects.get(user=self.user, label='Gym')
        self.assertEqual(block.start_time, time(9, 0))
        self.assertIn(b'grid-table', response.content)

    def test_create_missing_label_returns_200_with_retarget_and_does_not_persist(self):
        response = self.client.post(reverse('planner:block-create'), {
            'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], '#block-form')
        self.assertEqual(response['HX-Reswap'], 'outerHTML')
        self.assertEqual(TimeBlock.objects.filter(user=self.user).count(), 0)

    def test_create_zero_duration_returns_200_with_retarget_and_does_not_persist(self):
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Bad', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '09:00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], '#block-form')
        self.assertIn('after start time', response.content.decode().lower())
        self.assertEqual(TimeBlock.objects.filter(user=self.user).count(), 0)

    def test_create_overlap_returns_200_with_retarget_and_grid_left_unchanged(self):
        """FR-12: a rejected create must leave the grid unchanged -- no
        phantom block persisted."""
        TimeBlock.objects.create(
            user=self.user, label='Existing', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Overlap', 'day_of_week': 0, 'start_time': '09:30', 'end_time': '10:30',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], '#block-form')
        self.assertIn('overlap', response.content.decode().lower())
        self.assertEqual(TimeBlock.objects.filter(user=self.user).count(), 1)

    def test_create_touching_block_is_allowed(self):
        """The classic off-by-one: one block ending 09:00, the next
        starting 09:00, must both be accepted."""
        TimeBlock.objects.create(
            user=self.user, label='Existing', day_of_week=0,
            start_time=time(8, 0), end_time=time(9, 0),
        )
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Touching', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('HX-Retarget', response)
        self.assertEqual(TimeBlock.objects.filter(user=self.user).count(), 2)

    def test_edit_success_returns_200_and_persists(self):
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-edit', args=[block.pk]), {
            'label': 'Gym (renamed)', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.label, 'Gym (renamed)')

    def test_edit_invalid_returns_200_with_retarget_and_does_not_persist_change(self):
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-edit', args=[block.pk]), {
            'label': '', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], '#block-form')
        block.refresh_from_db()
        self.assertEqual(block.label, 'Gym')

    def test_edit_moving_block_to_another_day_updates_day_of_week(self):
        """PRD FR-08: moving a block to another day must update both the
        old and new day columns -- verified here at the data/context
        level (the actual response is a full grid re-render, see the
        module docstring in apps/planner/views.py for why)."""
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-edit', args=[block.pk]), {
            'label': 'Gym', 'day_of_week': 2, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.day_of_week, 2)

        week_grid = response.context['week_grid']
        monday_cells = [row.cells[0] for row in week_grid.rows]
        wednesday_cells = [row.cells[2] for row in week_grid.rows]
        self.assertTrue(all(cell.kind == 'empty' for cell in monday_cells))
        self.assertTrue(any(cell.kind == 'block-start' for cell in wednesday_cells))

    def test_delete_success_returns_200_and_removes_row(self):
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-delete', args=[block.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TimeBlock.objects.filter(pk=block.pk).exists())

    def test_resize_success_returns_200_and_persists(self):
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-resize', args=[block.pk]), {
            'start_time': '09:00', 'end_time': '11:00',
        })
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.end_time, time(11, 0))

    def test_resize_touching_an_adjacent_block_is_allowed(self):
        TimeBlock.objects.create(
            user=self.user, label='Later', day_of_week=0,
            start_time=time(10, 0), end_time=time(11, 0),
        )
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(8, 0), end_time=time(9, 0),
        )
        response = self.client.post(reverse('planner:block-resize', args=[block.pk]), {
            'start_time': '08:00', 'end_time': '10:00',
        })
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.end_time, time(10, 0))

    def test_resize_overlap_is_rejected_and_leaves_block_unchanged(self):
        TimeBlock.objects.create(
            user=self.user, label='Later', day_of_week=0,
            start_time=time(10, 0), end_time=time(11, 0),
        )
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(8, 0), end_time=time(9, 0),
        )
        response = self.client.post(reverse('planner:block-resize', args=[block.pk]), {
            'start_time': '08:00', 'end_time': '10:30',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('overlap', response.content.decode().lower())
        block.refresh_from_db()
        self.assertEqual(block.start_time, time(8, 0))
        self.assertEqual(block.end_time, time(9, 0))

    def test_resize_outside_configured_day_range_is_rejected_with_error_toast(self):
        """A resize clamped to the user's `[day_start, day_end)` range down
        to zero/negative duration is rejected outright, block unchanged,
        with an error toast rendered in the response body."""
        settings_obj = PlannerSettings.objects.get(user=self.user)
        self.assertEqual(settings_obj.day_start, time(6, 0))  # sanity: default range

        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(reverse('planner:block-resize', args=[block.pk]), {
            'start_time': '05:00', 'end_time': '05:30',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('rejected', content.lower())
        self.assertIn(response.context['toast_message'], content)
        self.assertEqual(response.context['toast_level'], 'error')
        block.refresh_from_db()
        self.assertEqual(block.start_time, time(9, 0))
        self.assertEqual(block.end_time, time(10, 0))

    def test_block_mutation_response_grid_table_is_not_out_of_band(self):
        """Regression check: a normal Sprint-6 block-mutation response's
        `#grid-table` must NOT carry `hx-swap-oob` -- that flag is
        exclusively for the Sprint-7 palette-response path
        (`_render_palette_response()`, see `GridOobRegressionTests`
        below)."""
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Gym', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertNotIn('hx-swap-oob', _grid_table_tag(response.content.decode()))

    def test_edit_extend_action_extends_block_by_one_slot(self):
        """PRD 6.3.4 keyboard/click '+/-' fallback, folded into
        `BlockUpdateView.post()`."""
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        response = self.client.post(
            reverse('planner:block-edit', args=[block.pk]), {'action': 'extend'},
        )
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.end_time, time(11, 0))  # +1 slot at the default 60-min interval

    def test_edit_extend_action_rejected_outside_range_leaves_block_unchanged(self):
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(23, 0), end_time=time(0, 0),
        )
        response = self.client.post(
            reverse('planner:block-edit', args=[block.pk]), {'action': 'extend'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('rejected', response.content.decode().lower())
        block.refresh_from_db()
        self.assertEqual(block.start_time, time(23, 0))
        self.assertEqual(block.end_time, time(0, 0))


class ColorCrudViewTests(TestCase):
    """PRD 8.2.3-analog for the palette (color) CRUD endpoints, plus the
    `grid_oob` out-of-band mechanism (Sprint 7)."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_create_success_returns_200_and_persists(self):
        response = self.client.post(reverse('planner:color-create'), {
            'name': 'Focus', 'hex_code': '#4f46e5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(BlockColor.objects.filter(user=self.user, name='Focus').exists())

    def test_create_success_response_carries_palette_and_oob_grid_fragment(self):
        response = self.client.post(reverse('planner:color-create'), {
            'name': 'Focus', 'hex_code': '#4f46e5',
        })
        content = response.content.decode()
        self.assertIn('id="palette-panel"', content)
        self.assertIn('hx-swap-oob="true"', _grid_table_tag(content))

    def test_create_duplicate_name_returns_200_with_retarget_and_does_not_persist(self):
        BlockColor.objects.create(user=self.user, name='Focus', hex_code='#4f46e5')
        response = self.client.post(reverse('planner:color-create'), {
            'name': 'Focus', 'hex_code': '#000000',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], '#color-form-row')
        self.assertEqual(BlockColor.objects.filter(user=self.user, name='Focus').count(), 1)

    def test_create_invalid_hex_returns_200_with_retarget_and_does_not_persist(self):
        response = self.client.post(reverse('planner:color-create'), {
            'name': 'Bad', 'hex_code': 'not-a-hex',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], '#color-form-row')
        self.assertFalse(BlockColor.objects.filter(user=self.user, name='Bad').exists())

    def test_edit_success_returns_200_and_persists(self):
        color = BlockColor.objects.create(user=self.user, name='Focus', hex_code='#4f46e5')
        response = self.client.post(reverse('planner:color-edit', args=[color.pk]), {
            'name': 'Deep focus', 'hex_code': '#4f46e5',
        })
        self.assertEqual(response.status_code, 200)
        color.refresh_from_db()
        self.assertEqual(color.name, 'Deep focus')

    def test_edit_invalid_retargets_to_this_colors_own_row_id(self):
        other = BlockColor.objects.create(user=self.user, name='Taken', hex_code='#000000')
        color = BlockColor.objects.create(user=self.user, name='Focus', hex_code='#4f46e5')
        response = self.client.post(reverse('planner:color-edit', args=[color.pk]), {
            'name': other.name, 'hex_code': '#4f46e5',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['HX-Retarget'], f'#color-row-{color.pk}')
        color.refresh_from_db()
        self.assertEqual(color.name, 'Focus')

    def test_delete_success_sets_referencing_block_color_null(self):
        color = BlockColor.objects.create(user=self.user, name='Focus', hex_code='#4f46e5')
        block = TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0), color=color,
        )
        response = self.client.post(reverse('planner:color-delete', args=[color.pk]))
        self.assertEqual(response.status_code, 200)
        block.refresh_from_db()
        self.assertIsNone(block.color)
        self.assertTrue(TimeBlock.objects.filter(pk=block.pk).exists())
        self.assertIn('hx-swap-oob="true"', _grid_table_tag(response.content.decode()))


class RepeatDaysTests(TestCase):
    """PRD 6.4.1/6.4.2: `BlockCreateView.form_valid()`'s repeat-across-days
    step."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_repeat_days_creates_copies_on_the_selected_days(self):
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Gym', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
            'repeat_days': ['1', '2'],
        })
        self.assertEqual(response.status_code, 200)
        copies = TimeBlock.objects.filter(user=self.user, label='Gym').order_by('day_of_week')
        self.assertEqual(list(copies.values_list('day_of_week', flat=True)), [0, 1, 2])
        for copy in copies:
            self.assertEqual(copy.start_time, time(9, 0))
            self.assertEqual(copy.end_time, time(10, 0))

    def test_repeat_day_that_would_overlap_is_skipped_without_aborting_primary(self):
        TimeBlock.objects.create(
            user=self.user, label='Existing', day_of_week=1,
            start_time=time(9, 30), end_time=time(10, 30),
        )
        response = self.client.post(reverse('planner:block-create'), {
            'label': 'Gym', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
            'repeat_days': ['1'],
        })
        self.assertEqual(response.status_code, 200)
        # Primary block still saved despite the skipped copy.
        self.assertTrue(
            TimeBlock.objects.filter(user=self.user, label='Gym', day_of_week=0).exists(),
        )
        # No copy created on the overlapping day -- 'Existing' is untouched.
        self.assertEqual(
            TimeBlock.objects.filter(user=self.user, day_of_week=1).count(), 1,
        )
        content = response.content.decode()
        self.assertIn('Skipped', content)
        self.assertIn('overlap', content.lower())


class SettingsUpdateViewTests(TestCase):
    """PRD 8.2.4: settings update redirects, and a subsequent grid fetch
    reflects the new interval/format."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_update_success_redirects_to_dashboard(self):
        response = self.client.post(reverse('planner:settings'), {
            'slot_interval': 30, 'day_start': '06:00', 'day_end': '00:00', 'time_format': '24h',
        })
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_update_changes_slot_interval_reflected_in_grid_row_count(self):
        grid_before = self.client.get(reverse('planner:grid'))
        rows_before = len(grid_before.context['week_grid'].rows)

        self.client.post(reverse('planner:settings'), {
            'slot_interval': 30, 'day_start': '06:00', 'day_end': '00:00', 'time_format': '24h',
        })

        grid_after = self.client.get(reverse('planner:grid'))
        rows_after = len(grid_after.context['week_grid'].rows)
        self.assertEqual(rows_before, 18)
        self.assertEqual(rows_after, 36)

    def test_update_time_format_reflected_in_grid_labels(self):
        self.client.post(reverse('planner:settings'), {
            'slot_interval': 60, 'day_start': '06:00', 'day_end': '00:00', 'time_format': '12h',
        })

        grid_after = self.client.get(reverse('planner:grid'))
        labels = [row.label for row in grid_after.context['week_grid'].rows]
        self.assertIn('6:00 AM', labels)
        self.assertNotIn('06:00', labels)


class WeekNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_dashboard_uses_requested_week_and_iso_label(self):
        TimeBlock.objects.create(
            user=self.user,
            label='Future work',
            scheduled_date=date(2026, 8, 10),
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        response = self.client.get(reverse('core:dashboard'), {'week': '2026-08-12'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_week_start'], date(2026, 8, 10))
        self.assertIn('Week 33 - 2026', response.content.decode())
        self.assertIn('Future work', response.content.decode())

    def test_requested_week_does_not_render_other_week_blocks(self):
        TimeBlock.objects.create(
            user=self.user,
            label='Other week',
            scheduled_date=date(2026, 8, 17),
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:grid'), {'week': '2026-08-03'})

        self.assertNotIn('Other week', response.content.decode())

    def test_create_preserves_requested_week(self):
        response = self.client.post(
            reverse('planner:block-create') + '?week=2026-08-10',
            {
                'label': 'Planned later',
                'day_of_week': 2,
                'start_time': '09:00',
                'end_time': '10:00',
                'week': '2026-08-10',
            },
        )

        self.assertEqual(response.status_code, 200)
        block = TimeBlock.objects.get(user=self.user, label='Planned later')
        self.assertEqual(block.scheduled_date, date(2026, 8, 12))


class MixedOperationSequenceTests(TestCase):
    """PRD 6.5.3: create -> resize -> move -> delete -> create again must
    leave the grid in a consistent state throughout."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_mixed_sequence_stays_consistent(self):
        create_response = self.client.post(reverse('planner:block-create'), {
            'label': 'Gym', 'day_of_week': 0, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(create_response.status_code, 200)
        block = TimeBlock.objects.get(user=self.user, label='Gym')

        resize_response = self.client.post(reverse('planner:block-resize', args=[block.pk]), {
            'start_time': '09:00', 'end_time': '11:00',
        })
        self.assertEqual(resize_response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.end_time, time(11, 0))

        move_response = self.client.post(reverse('planner:block-edit', args=[block.pk]), {
            'label': 'Gym', 'day_of_week': 3, 'start_time': '09:00', 'end_time': '11:00',
        })
        self.assertEqual(move_response.status_code, 200)
        block.refresh_from_db()
        self.assertEqual(block.day_of_week, 3)

        delete_response = self.client.post(reverse('planner:block-delete', args=[block.pk]))
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(TimeBlock.objects.filter(pk=block.pk).exists())

        second_create_response = self.client.post(reverse('planner:block-create'), {
            'label': 'Study', 'day_of_week': 3, 'start_time': '09:00', 'end_time': '10:00',
        })
        self.assertEqual(second_create_response.status_code, 200)
        self.assertEqual(TimeBlock.objects.filter(user=self.user).count(), 1)

        week_grid = second_create_response.context['week_grid']
        thursday_cells = [row.cells[3] for row in week_grid.rows]
        block_start_cells = [cell for cell in thursday_cells if cell.kind == 'block-start']
        self.assertEqual(len(block_start_cells), 1)
        self.assertEqual(block_start_cells[0].block.label, 'Study')


class ExportMarkdownViewTests(TestCase):
    """Sprint 10 (new feature): `ExportMarkdownView`'s HTTP contract."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_success_returns_200_with_markdown_headers(self):
        response = self.client.get(reverse('planner:export-markdown'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/markdown; charset=utf-8')
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename="weekly-planner.md"',
        )

    def test_content_contains_expected_day_headings_and_block_line(self):
        TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:export-markdown'))
        content = response.content.decode()

        self.assertIn('## Monday', content)
        self.assertIn('## Sunday', content)
        self.assertIn('- 09:00–10:00 Gym', content)
        self.assertIn('_No blocks._', content)  # every other day

    def test_export_is_scoped_to_request_user(self):
        """NFR-07: another user's blocks must never appear in this
        user's exported document."""
        other_user = User.objects.create_user(username='bob', password='pass12345')
        TimeBlock.objects.create(
            user=other_user, label="Bob's secret", day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )
        TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:export-markdown'))
        content = response.content.decode()

        self.assertIn('Gym', content)
        self.assertNotIn("Bob's secret", content)

    def test_respects_the_users_time_format_setting(self):
        settings_obj = PlannerSettings.objects.get(user=self.user)
        settings_obj.time_format = '12h'
        settings_obj.save()
        TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:export-markdown'))
        content = response.content.decode()

        self.assertIn('- 9:00 AM–10:00 AM Gym', content)


class ExportSVGViewTests(TestCase):
    """Sprint 10 (new feature): `ExportSVGView`'s HTTP contract.

    Exercises the real `planner/partials/grid_export.svg` template (no
    stand-in -- an earlier draft of this test used an in-memory locmem
    template while the real file didn't exist yet; now that
    `django-frontend` has shipped it, these tests hit it directly, since
    testing a fake stand-in forever would verify nothing real).
    """

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.client.force_login(self.user)

    def test_success_returns_200_with_svg_headers(self):
        response = self.client.get(reverse('planner:export-svg'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename="weekly-planner.svg"',
        )

    def test_content_contains_expected_rect_count_for_a_known_scenario(self):
        """Default settings (60-min interval, 06:00-00:00) plus a single
        one-hour block: 1 whole-document background rect + 7 day-header
        rects + 1 block rect = 9 (see `grid_export.svg`'s own background
        `<rect>`, drawn before the loop over `svg_export.rects`)."""
        TimeBlock.objects.create(
            user=self.user, label='Gym', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:export-svg'))
        content = response.content.decode()

        self.assertEqual(content.count('<rect'), 9)
        self.assertIn('<text', content)
        self.assertIn('<svg', content)

    def test_export_is_scoped_to_request_user(self):
        """NFR-07: another user's block label must never appear in this
        user's exported SVG."""
        other_user = User.objects.create_user(username='bob', password='pass12345')
        TimeBlock.objects.create(
            user=other_user, label="Bob's secret", day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:export-svg'))
        content = response.content.decode()

        self.assertNotIn("Bob's secret", content)
        self.assertEqual(content.count('<rect'), 8)  # background + 7 header rects only

    def test_content_is_well_formed_xml(self):
        """The real template's output must actually parse as XML, not
        just contain the right substrings -- guards against the exact
        class of bug this feature hit while it was being built (a stray
        leading newline before `<?xml ...?>` breaks every XML parser)."""
        TimeBlock.objects.create(
            user=self.user, label='Q&A <review> "quoted"', day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        )

        response = self.client.get(reverse('planner:export-svg'))

        root = ET.fromstring(response.content)
        self.assertTrue(root.tag.endswith('svg'))
