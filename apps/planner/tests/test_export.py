"""Export builder tests for the planner app (Sprint 10, new feature).

Both `render_week_markdown()` and `build_svg_export()` are pure Python
(no database query) -- exactly like `apps.planner.grid.build_week_grid()`,
which `test_grid.py` already established the pattern for. These tests
construct `PlannerSettings`/`TimeBlock`/`BlockColor` instances directly,
unsaved, and never touch the database -- `SimpleTestCase` enforces that.
"""

from datetime import time

from django.test import SimpleTestCase

from apps.planner.export import (
    BLOCK_FALLBACK_FILL,
    HEADER_BACKGROUND,
    ROW_HEIGHT,
    build_svg_export,
    render_week_markdown,
)
from apps.planner.grid import build_week_grid
from apps.planner.models import BlockColor, PlannerSettings, TimeBlock


def _settings(slot_interval=60, day_start=time(6, 0), day_end=time(0, 0), time_format='24h'):
    """Build an unsaved `PlannerSettings` instance."""
    return PlannerSettings(
        slot_interval=slot_interval,
        day_start=day_start,
        day_end=day_end,
        time_format=time_format,
    )


def _block(label, day_of_week, start_time, end_time, color=None):
    """Build an unsaved `TimeBlock` instance."""
    return TimeBlock(
        label=label, day_of_week=day_of_week,
        start_time=start_time, end_time=end_time, color=color,
    )


class RenderWeekMarkdownTests(SimpleTestCase):
    """PRD-analog coverage for `render_week_markdown()` (Sprint 10)."""

    def test_empty_week_shows_no_blocks_for_every_day(self):
        content = render_week_markdown([], '24h')

        for _, day_name in TimeBlock.DAY_CHOICES:
            self.assertIn(f'## {day_name}', content)
        self.assertEqual(content.count('_No blocks._'), 7)
        self.assertTrue(content.startswith('# My Week'))

    def test_block_appears_with_correctly_formatted_times_in_24h(self):
        blocks = [_block('Gym', 0, time(9, 0), time(10, 0))]

        content = render_week_markdown(blocks, '24h')

        self.assertIn('- 09:00–10:00 Gym', content)

    def test_block_appears_with_correctly_formatted_times_in_12h(self):
        blocks = [_block('Deep work', 0, time(14, 0), time(15, 30))]

        content = render_week_markdown(blocks, '12h')

        self.assertIn('- 2:00 PM–3:30 PM Deep work', content)

    def test_multiple_blocks_on_one_day_are_listed_in_start_time_order(self):
        """Passed out of chronological order on purpose -- the function
        must sort defensively itself, not rely on caller ordering."""
        blocks = [
            _block('Afternoon', 0, time(14, 0), time(15, 0)),
            _block('Morning', 0, time(9, 0), time(10, 0)),
        ]

        content = render_week_markdown(blocks, '24h')

        morning_index = content.index('09:00–10:00 Morning')
        afternoon_index = content.index('14:00–15:00 Afternoon')
        self.assertLess(morning_index, afternoon_index)

    def test_day_with_zero_blocks_still_gets_its_own_heading(self):
        """A day with no blocks must not be silently omitted -- it still
        gets a heading, just with `_No blocks._` under it."""
        blocks = [_block('Gym', 0, time(9, 0), time(10, 0))]

        content = render_week_markdown(blocks, '24h')

        tuesday_heading = content.index('## Tuesday')
        wednesday_heading = content.index('## Wednesday')
        tuesday_section = content[tuesday_heading:wednesday_heading]
        self.assertIn('_No blocks._', tuesday_section)

    def test_embedded_newlines_in_a_label_cannot_inject_a_fake_heading_or_bullet(self):
        """A label carrying an embedded newline (unreachable via a normal
        <input type="text"> keystroke, but not rejected by the model or
        form either) must not be able to fabricate a Markdown heading or
        bullet of its own -- the whole block must stay on its one bullet
        line, under its real day."""
        blocks = [_block('Evil\n## Sunday\n- 00:00-00:01 Injected', 0, time(9, 0), time(10, 0))]

        content = render_week_markdown(blocks, '24h')
        lines = content.splitlines()

        # Exactly one *line* is the real Sunday heading -- the injected
        # "## Sunday" text survives only as inert words in the middle of
        # Monday's bullet line, never as a heading line of its own.
        self.assertEqual(lines.count('## Sunday'), 1)
        self.assertIn('- 09:00–10:00 Evil ## Sunday - 00:00-00:01 Injected', lines)


class BuildSvgExportTests(SimpleTestCase):
    """Coverage for `build_svg_export()` (Sprint 10)."""

    def test_empty_week_grid_produces_day_header_texts_and_no_block_rects(self):
        week_grid = build_week_grid(_settings(), [])

        svg_export = build_svg_export(week_grid)

        # Exactly one header background rect per day, no block rects.
        self.assertEqual(len(svg_export.rects), 7)
        for rect in svg_export.rects:
            self.assertEqual(rect.fill, HEADER_BACKGROUND)

        header_texts = [text.content for text in svg_export.texts]
        for _, day_name in TimeBlock.DAY_CHOICES:
            self.assertIn(day_name, header_texts)

    def test_single_block_produces_exactly_one_rect_with_its_color(self):
        color = BlockColor(hex_code='#4f46e5')
        blocks = [_block('Gym', 0, time(9, 0), time(10, 0), color=color)]
        week_grid = build_week_grid(_settings(), blocks)

        svg_export = build_svg_export(week_grid)

        colored_rects = [rect for rect in svg_export.rects if rect.fill == '#4f46e5']
        self.assertEqual(len(colored_rects), 1)
        self.assertEqual(len(svg_export.rects), 8)  # 7 header rects + this one block rect

    def test_colorless_block_falls_back_to_the_neutral_fill(self):
        blocks = [_block('Gym', 0, time(9, 0), time(10, 0), color=None)]
        week_grid = build_week_grid(_settings(), blocks)

        svg_export = build_svg_export(week_grid)

        fallback_rects = [rect for rect in svg_export.rects if rect.fill == BLOCK_FALLBACK_FILL]
        self.assertEqual(len(fallback_rects), 1)

    def test_multi_row_spanning_block_rect_height_matches_rowspan_times_row_height(self):
        blocks = [_block('Deep work', 0, time(9, 0), time(12, 0))]  # 3 hours, 60-min interval
        week_grid = build_week_grid(_settings(slot_interval=60), blocks)

        svg_export = build_svg_export(week_grid)

        block_rects = [rect for rect in svg_export.rects if rect.fill != HEADER_BACKGROUND]
        self.assertEqual(len(block_rects), 1)
        self.assertEqual(block_rects[0].height, 3 * ROW_HEIGHT)

    def test_embedded_newlines_in_a_label_stay_on_one_line(self):
        """Same normalization, same reason, as
        RenderWeekMarkdownTests.test_embedded_newlines_in_a_label_cannot_inject_a_fake_heading_or_bullet
        -- SVG `<text>` never wraps on its own, so an embedded newline
        must not survive into `SvgText.content`."""
        blocks = [_block('Evil\nmulti\nline', 0, time(9, 0), time(10, 0))]
        week_grid = build_week_grid(_settings(), blocks)

        svg_export = build_svg_export(week_grid)

        block_texts = [text.content for text in svg_export.texts if 'Evil' in text.content]
        self.assertEqual(block_texts, ['Evil multi line'])
