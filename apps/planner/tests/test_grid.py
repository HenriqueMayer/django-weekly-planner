"""Grid builder tests for the planner app (PRD 8.3.1).

`build_week_grid()` is pure Python (no database query), so these tests
construct `PlannerSettings`/`TimeBlock` instances directly, unsaved, and
never touch the database -- `SimpleTestCase` enforces that. `TimeBlock`
instances here are only ever passed to `build_week_grid()`, never
`.full_clean()`-ed or `.save()`-d, so leaving `user` unset is safe (the
overlap-validation codepath that needs `user` is not exercised here at
all -- see `test_models.py` for that).
"""

from datetime import time

from django.test import SimpleTestCase

from apps.planner.grid import build_week_grid
from apps.planner.models import PlannerSettings, TimeBlock


def _settings(slot_interval=60, day_start=time(6, 0), day_end=time(0, 0), time_format='24h'):
    """Build an unsaved `PlannerSettings` instance for `build_week_grid()`."""
    return PlannerSettings(
        slot_interval=slot_interval,
        day_start=day_start,
        day_end=day_end,
        time_format=time_format,
    )


def _block(label, day_of_week, start_time, end_time):
    """Build an unsaved `TimeBlock` instance for `build_week_grid()`."""
    return TimeBlock(
        label=label, day_of_week=day_of_week, start_time=start_time, end_time=end_time,
    )


def _first_non_empty_cells(week_grid, day):
    """Return `[(row_index, cell), ...]` for every non-'empty' cell in
    `day`'s column, in row order -- a compact way to assert a whole
    day's placement without a nested per-row `if` in every test."""
    return [
        (index, row.cells[day])
        for index, row in enumerate(week_grid.rows)
        if row.cells[day].kind != 'empty'
    ]


class EmptyGridTests(SimpleTestCase):
    def test_empty_grid_has_all_cells_empty(self):
        week_grid = build_week_grid(_settings(), [])

        self.assertEqual(len(week_grid.rows), 18)  # (24:00 - 06:00) / 60
        self.assertEqual(len(week_grid.day_headers), 7)
        for row in week_grid.rows:
            self.assertEqual(len(row.cells), 7)
            for cell in row.cells:
                self.assertEqual(cell.kind, 'empty')


class SingleBlockRowspanTests(SimpleTestCase):
    """A single 90-minute block, checked at both 30 and 60-minute
    intervals (PRD 8.3.1's explicit "same scenario, both intervals" case)."""

    def _block(self):
        return _block('Deep work', 0, time(7, 0), time(8, 30))

    def test_at_sixty_minute_interval(self):
        week_grid = build_week_grid(_settings(slot_interval=60), [self._block()])

        placed = _first_non_empty_cells(week_grid, day=0)
        self.assertEqual(len(placed), 2)
        (start_index, start_cell), (occupied_index, occupied_cell) = placed

        self.assertEqual(start_index, 1)  # 07:00 is the 2nd row after 06:00
        self.assertEqual(start_cell.kind, 'block-start')
        self.assertEqual(start_cell.rowspan, 2)
        self.assertEqual(occupied_index, 2)
        self.assertEqual(occupied_cell.kind, 'occupied')
        self.assertEqual(len(week_grid.rows), 18)

    def test_at_thirty_minute_interval(self):
        week_grid = build_week_grid(_settings(slot_interval=30), [self._block()])

        # 90 minutes / 30-minute interval = exactly 3 rows (no rounding
        # needed here -- the round-half-up nuance is covered by the
        # 60-minute case above and by TimeBlockRowspanTests).
        placed = _first_non_empty_cells(week_grid, day=0)
        self.assertEqual(len(placed), 3)
        start_index, start_cell = placed[0]

        self.assertEqual(start_index, 2)  # 07:00 is the 3rd 30-min row after 06:00
        self.assertEqual(start_cell.kind, 'block-start')
        self.assertEqual(start_cell.rowspan, 3)
        self.assertTrue(all(cell.kind == 'occupied' for _, cell in placed[1:]))
        self.assertEqual(len(week_grid.rows), 36)


class StackedBlocksTests(SimpleTestCase):
    """Two sequential, touching blocks in the same day column (PRD 8.3.1)."""

    def test_two_sequential_blocks_each_get_their_own_cells(self):
        blocks = [
            _block('Gym', 0, time(7, 0), time(8, 0)),
            _block('Study', 0, time(8, 0), time(9, 0)),
        ]
        week_grid = build_week_grid(_settings(slot_interval=60), blocks)

        placed = _first_non_empty_cells(week_grid, day=0)
        self.assertEqual(len(placed), 2)
        (first_index, first_cell), (second_index, second_cell) = placed

        self.assertEqual(first_index, 1)
        self.assertEqual(first_cell.kind, 'block-start')
        self.assertEqual(first_cell.block.label, 'Gym')
        self.assertEqual(first_cell.rowspan, 1)

        self.assertEqual(second_index, 2)
        self.assertEqual(second_cell.kind, 'block-start')
        self.assertEqual(second_cell.block.label, 'Study')
        self.assertEqual(second_cell.rowspan, 1)

    def test_row_collision_re_anchors_the_second_block_forward(self):
        """Documented in ARCHITECTURE.md's Grid Rendering section: two
        legally non-overlapping, exactly-touching blocks (09:00-09:20,
        09:20-09:40) both snap to the same row at a coarse 60-minute
        interval. The second one must be re-anchored to the next free
        row, flagged `clamped`, and never silently dropped."""
        blocks = [
            _block('First', 0, time(9, 0), time(9, 20)),
            _block('Second', 0, time(9, 20), time(9, 40)),
        ]
        week_grid = build_week_grid(_settings(slot_interval=60), blocks)

        placed = _first_non_empty_cells(week_grid, day=0)
        self.assertEqual(len(placed), 2)
        (first_index, first_cell), (second_index, second_cell) = placed

        self.assertEqual(first_cell.block.label, 'First')
        self.assertFalse(first_cell.clamped)

        self.assertEqual(second_cell.block.label, 'Second')
        self.assertGreater(second_index, first_index)
        self.assertTrue(second_cell.clamped)
        self.assertEqual(week_grid.unplaced_blocks, [])


class OutOfRangeBlockTests(SimpleTestCase):
    def test_block_entirely_outside_day_range_is_flagged_not_placed(self):
        settings_obj = _settings(day_start=time(8, 0), day_end=time(18, 0))
        early_block = _block('Sleep', 0, time(6, 0), time(7, 0))

        week_grid = build_week_grid(settings_obj, [early_block])

        self.assertEqual(week_grid.out_of_range_blocks, [early_block])
        self.assertEqual(week_grid.unplaced_blocks, [])
        self.assertTrue(all(row.cells[0].kind == 'empty' for row in week_grid.rows))


class TimeFormatLabelTests(SimpleTestCase):
    def test_twelve_hour_labels_have_no_leading_zero(self):
        week_grid = build_week_grid(_settings(time_format='12h'), [])

        labels = [row.label for row in week_grid.rows]
        self.assertEqual(labels[0], '6:00 AM')  # 06:00, first row
        self.assertEqual(labels[8], '2:00 PM')  # 14:00

    def test_twenty_four_hour_labels_keep_the_leading_zero(self):
        week_grid = build_week_grid(_settings(time_format='24h'), [])

        labels = [row.label for row in week_grid.rows]
        self.assertEqual(labels[0], '06:00')
        self.assertEqual(labels[8], '14:00')
