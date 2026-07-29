"""Server-side export builders for the weekly grid (Sprint 10, new feature).

This is not part of the original PRD sprint plan (Sprints 1-9): it is a
user-requested, zero-new-runtime-dependency addition on top of the
existing planner. PNG is drawn client-side on an HTML5 canvas from the
live DOM, and PDF uses the browser's native print-to-PDF -- neither of
those is this module's concern. This module owns exactly two
server-side formats: Markdown and SVG.

Both builders follow the same PRD-R2 philosophy `apps.planner.grid`
already established -- "compute everything server-side, templates only
iterate, no logic-heavy DTL":

- `render_week_markdown()` is a pure function of an already-filtered
  iterable of `TimeBlock` instances plus a `time_format` string. It
  never queries the database itself -- same contract as
  `apps.planner.grid.build_week_grid()` -- so the caller (a view) is
  always the one responsible for scoping the queryset to
  `request.user` (NFR-07).
- `build_svg_export()` takes an already-built `WeekGrid` (the exact
  same matrix the on-screen `<table>` is rendered from, via
  `apps.planner.grid.build_week_grid()`) and turns it into a flat list
  of pixel-positioned drawable primitives (`SvgRect`/`SvgText`). Reusing
  `WeekGrid` here -- rather than re-deriving positions from raw blocks
  -- guarantees the exported SVG visually matches what the user sees on
  screen, including the same collision re-anchoring and out-of-range
  clamping `build_week_grid()` already resolved. The template that
  iterates the resulting `SvgExport` (`django-frontend`'s
  `planner/partials/grid_export.svg`, not this module's concern) does
  no layout math of its own -- it only loops over `rects`/`texts`.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from apps.planner.models import TimeBlock, format_time_label

# Tailwind's `slate-50`, matching the on-screen grid header background
# (`bg-slate-50`, see `grid_table.html`) so the SVG export draws from the
# same design tokens rather than an invented color.
HEADER_BACKGROUND = '#f8fafc'

# Tailwind's `slate-500`, matching `block_cell.html`'s neutral fallback
# for a block whose `color` is null (`bg-slate-500`).
BLOCK_FALLBACK_FILL = '#64748b'

# White text on every block rect. `block_cell.html`'s own default is
# `text-white`, with `static/js/contrast.js` only overriding it to a dark
# color client-side, per custom hex background, after the DOM has
# painted. A static export has no such JS pass available, and adding a
# relative-luminance contrast computation here would be scope creep this
# feature does not need (NFR-01) -- white is the same pre-JS default
# `block_cell.html` itself falls back to.
BLOCK_LABEL_FILL = '#ffffff'

TIME_COLUMN_WIDTH = 64
DAY_COLUMN_WIDTH = 110
HEADER_HEIGHT = 32
ROW_HEIGHT = 28

# Small inset so text never touches a rect's own border.
TEXT_PADDING_X = 6


def render_week_markdown(blocks, time_format):
    """Render one user's week as a Markdown document.

    Args:
        blocks: an iterable of `TimeBlock` instances, already filtered by
            the caller to one user (same contract as
            `apps.planner.grid.build_week_grid()` -- this function never
            queries the database itself).
        time_format: `'24h'` or `'12h'`, passed straight through to
            `format_time_label()` for every block's start/end time.

    Returns:
        A `str`: a `# My Week` title followed by one `## <Day name>`
        heading per day, Monday through Sunday (via `TimeBlock.
        DAY_CHOICES`, not queryset/dict ordering, so every day gets its
        own heading even with zero blocks) -- each listing its blocks,
        sorted by `start_time`, as `- <start>-<end> <label>` bullets, or
        `_No blocks._` when the day has none.
    """
    blocks_by_day = defaultdict(list)
    for block in blocks:
        blocks_by_day[block.day_of_week].append(block)

    lines = ['# My Week', '']
    for day_value, day_name in TimeBlock.DAY_CHOICES:
        lines.append(f'## {day_name}')
        lines.append('')

        day_blocks = sorted(blocks_by_day.get(day_value, []), key=lambda b: b.start_time)
        if day_blocks:
            for block in day_blocks:
                start_label = format_time_label(block.start_time, time_format)
                end_label = format_time_label(block.end_time, time_format)
                # A label is free text (no newline validator at the model
                # or form layer -- and none is warranted there, since a
                # normal <input type="text"> can't produce one by keystroke
                # anyway). A crafted label containing an embedded newline
                # would otherwise start a new Markdown line mid-bullet,
                # letting it masquerade as a heading/bullet of its own and
                # land under the wrong day's section. Collapsing embedded
                # newlines to spaces keeps this function's output exactly
                # one line per block, always, regardless of what a label
                # contains.
                safe_label = ' '.join(block.label.split())
                lines.append(f'- {start_label}–{end_label} {safe_label}')
        else:
            lines.append('_No blocks._')
        lines.append('')

    return '\n'.join(lines).rstrip('\n') + '\n'


@dataclass
class SvgRect:
    """One drawable `<rect>`, fully pixel-positioned -- a template only
    needs to interpolate these fields into attributes, no arithmetic."""

    x: int
    y: int
    width: int
    height: int
    fill: str
    stroke: str = '#e2e8f0'


@dataclass
class SvgText:
    """One drawable `<text>`, fully pixel-positioned."""

    x: int
    y: int
    content: str
    fill: str = '#0f172a'
    font_size: int = 12
    font_weight: str = 'normal'


@dataclass
class SvgExport:
    """The full computed SVG drawing, ready for a template to iterate."""

    width: int
    height: int
    rects: list[SvgRect] = field(default_factory=list)
    texts: list[SvgText] = field(default_factory=list)


def _row_top(row_index):
    """Return the y-coordinate of the top of `row_index` (0-based),
    below the header row."""
    return HEADER_HEIGHT + row_index * ROW_HEIGHT


def build_svg_export(week_grid):
    """Turn a `WeekGrid` (see `apps.planner.grid`) into an `SvgExport`.

    No database access and no layout decisions of its own: every
    position/size here is derived directly from `week_grid`'s already-
    resolved matrix (day headers, row labels, and each day's
    `'block-start'`/`rowspan` cells), plus the fixed pixel constants
    defined in this module. `'empty'`/`'occupied'` cells are skipped
    entirely -- no rect is drawn for an empty slot, and `'occupied'`
    cells never need one since the `'block-start'` rect above them
    already covers that vertical span (mirrors `grid_table.html`'s own
    contract that `'occupied'` renders nothing).
    """
    row_count = len(week_grid.rows)
    width = TIME_COLUMN_WIDTH + 7 * DAY_COLUMN_WIDTH
    height = HEADER_HEIGHT + row_count * ROW_HEIGHT

    rects = []
    texts = []

    for day_index, day_name in enumerate(week_grid.day_headers):
        header_x = TIME_COLUMN_WIDTH + day_index * DAY_COLUMN_WIDTH
        rects.append(SvgRect(
            x=header_x, y=0, width=DAY_COLUMN_WIDTH, height=HEADER_HEIGHT,
            fill=HEADER_BACKGROUND,
        ))
        texts.append(SvgText(
            x=header_x + TEXT_PADDING_X,
            y=HEADER_HEIGHT // 2 + 4,
            content=day_name,
            font_weight='bold',
        ))

    for row_index, row in enumerate(week_grid.rows):
        row_top = _row_top(row_index)
        texts.append(SvgText(
            x=TEXT_PADDING_X,
            y=row_top + ROW_HEIGHT // 2 + 4,
            content=row.label,
        ))

        for day_index, cell in enumerate(row.cells):
            if cell.kind != 'block-start':
                continue

            block = cell.block
            fill = block.color.hex_code if block.color else BLOCK_FALLBACK_FILL
            rect_x = TIME_COLUMN_WIDTH + day_index * DAY_COLUMN_WIDTH
            rect_height = cell.rowspan * ROW_HEIGHT
            rects.append(SvgRect(
                x=rect_x, y=row_top, width=DAY_COLUMN_WIDTH, height=rect_height,
                fill=fill,
            ))
            texts.append(SvgText(
                x=rect_x + TEXT_PADDING_X,
                y=row_top + 16,
                # `<text>` is one line -- a label carrying an embedded
                # newline (see the identical normalization in
                # render_week_markdown() above) would otherwise place its
                # tail past this rect's own bounds instead of stacking as
                # a second visual line, since SVG text never wraps on its
                # own. Same fix, same reason, both call sites.
                content=' '.join(block.label.split()),
                fill=BLOCK_LABEL_FILL,
                font_size=11,
            ))

    return SvgExport(width=width, height=height, rects=rects, texts=texts)
