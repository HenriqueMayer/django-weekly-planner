"""Server-side weekly grid computation (PRD FR-05, FR-06, R2, R3).

This module is the single place where the weekly time-blocking grid's
row/column/rowspan matrix is computed. Nothing here touches the database,
templates, or HTTP -- `build_week_grid()` is a pure function of a
`PlannerSettings` instance and an iterable of `TimeBlock` instances, so it
stays trivially unit-testable (Sprint 8, PRD 8.3.1) and keeps all
layout-sensitive logic out of Django Template Language, per risk R2
("compute the grid matrix server-side ... templates only iterate -- no
logic-heavy DTL").

Shape of the result
--------------------
`build_week_grid()` returns a `WeekGrid`::

    WeekGrid(
        day_headers=['Monday', 'Tuesday', ..., 'Sunday'],  # 7 labels, Mon..Sun
        rows=[
            GridRow(label='06:00', start_time=time(6, 0), cells=[...7 cells...]),
            ...
        ],
        slot_interval=60,
        time_format='24h',
        out_of_range_blocks=[...TimeBlock...],
        unplaced_blocks=[...TimeBlock...],
    )

Each `GridRow.cells` list has exactly 7 entries, index 0 = Monday through
index 6 = Sunday (matching `TimeBlock.DAY_CHOICES` and `day_headers`, so a
template can zip/iterate them positionally without any extra lookup).
Each entry is a `GridCell` tagged by `kind`:

- `'empty'` -- a clickable, unoccupied slot. Carries `day` and the slot's
  `slot_start`/`slot_end` `time` objects, so Sprint 6 can build
  `hx-get`/`data-*` attributes straight from them without any
  template-side computation.
- `'block-start'` -- the top-left cell of a rendered block. Carries the
  `TimeBlock` instance itself (`cell.block`) and `rowspan` (how many
  `<tr>` rows the `<td rowspan="...">` should span). `clamped` is `True`
  when the block's rendered position/extent does not exactly match its
  stored start/end -- either because the stored range extends beyond the
  current visible day range and had to be visually cut off (PRD R3), or
  because it had to be re-anchored/shrunk to fit the grid's row count
  after interval-snapping (see `unplaced_blocks` below). The stored
  `TimeBlock` row is never mutated. Note: no template currently reads or
  surfaces this flag in the UI yet -- that is deferred to a later polish
  sprint, not an oversight.
- `'occupied'` -- a row covered by a `'block-start'` cell above it via
  `rowspan`. Templates must render nothing for this cell (no `<td>` at
  all) rather than an empty one, since the HTML `rowspan` already
  accounts for it.

`WeekGrid.out_of_range_blocks` holds blocks whose entire time range falls
outside the current `[day_start, day_end)` window (e.g. the day range was
narrowed after the block was created), so they cannot appear as a cell at
all -- this list is where PRD R3's "flag, don't delete" guidance surfaces
for them. Nothing consumes this list yet (a later sprint's polish pass
can); it exists purely so the information is not silently lost.

`WeekGrid.unplaced_blocks` holds blocks that fall *inside* the visible day
range but, after snapping to the current `slot_interval`, could not be
placed anywhere in their day's column -- every row from their snapped
start to the bottom of the grid is already claimed by other blocks (a
genuinely pathological case, e.g. the day is already completely packed).
This is distinct from `out_of_range_blocks` (which is about *time range*,
not row availability): a block only ever lands here as a last resort,
after `build_week_grid()` has already tried re-anchoring it at the next
free row in its column. Nothing consumes this list yet either; it exists
for the same "flag, don't silently drop" reason.

Nothing in this module performs a database query -- callers are expected
to pass an already-evaluated/filtered `TimeBlock` iterable (ideally with
`.select_related('color')` to avoid per-cell queries, per NFR-03).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import time
from math import ceil

from apps.planner.models import TimeBlock, minutes_since_midnight, round_half_up, time_from_minutes


@dataclass
class GridCell:
    """One cell of the rendered week grid.

    `kind` is one of `'empty'`, `'block-start'`, or `'occupied'` -- see
    the module docstring for what each means to the template layer.
    """

    kind: str
    day: int
    slot_start: time
    slot_end: time
    block: TimeBlock | None = None
    rowspan: int = 1
    clamped: bool = False


@dataclass
class GridRow:
    """One row of the grid: a time-slot label plus its 7 day cells."""

    label: str
    start_time: time
    cells: list[GridCell]


@dataclass
class WeekGrid:
    """The full computed weekly grid, ready for a template to iterate."""

    day_headers: list[str]
    rows: list[GridRow]
    slot_interval: int
    time_format: str
    out_of_range_blocks: list[TimeBlock] = field(default_factory=list)
    unplaced_blocks: list[TimeBlock] = field(default_factory=list)


class _CellState:
    """Internal, pre-`GridCell` bookkeeping for one (day, row) matrix slot.

    Kept separate from `GridCell` so the public dataclass never carries a
    `None`-means-undecided placeholder -- by the time a `GridCell` is
    built below, its `slot_start`/`slot_end` are always known.
    """

    __slots__ = ('kind', 'block', 'rowspan', 'clamped')

    def __init__(self, kind, block=None, rowspan=1, clamped=False):
        self.kind = kind
        self.block = block
        self.rowspan = rowspan
        self.clamped = clamped


def _format_time_label(value, time_format):
    """Format a `time` object per `PlannerSettings.time_format` (5.1.2).

    `'24h'` -> `'14:00'`. `'12h'` -> `'2:00 PM'`, built from the portable
    `%I:%M %p` (avoiding the platform-specific `%-I`) with the leading
    zero stripped by hand.
    """
    if time_format == '12h':
        formatted = value.strftime('%I:%M %p')
        return formatted[1:] if formatted.startswith('0') else formatted
    return value.strftime('%H:%M')


def build_week_grid(planner_settings, blocks):
    """Build the full week grid matrix for one user.

    Args:
        planner_settings: a `PlannerSettings` instance (`slot_interval`,
            `day_start`, `day_end`, `time_format`).
        blocks: an iterable of the user's `TimeBlock` instances, e.g.
            `TimeBlock.objects.filter(user=...).select_related('color')`.
            No query is issued here -- pass an already-filtered queryset
            or list; this function never touches the database.

    Returns:
        A `WeekGrid` instance. See the module docstring for its shape.
    """
    interval = planner_settings.slot_interval
    time_format = planner_settings.time_format

    range_start = minutes_since_midnight(planner_settings.day_start)
    range_end = minutes_since_midnight(planner_settings.day_end, treat_midnight_as_end_of_day=True)
    total_minutes = range_end - range_start
    # Round up, not down: a day range that isn't an exact multiple of
    # `interval` (e.g. 06:00-23:45 at a 60-minute interval) must still be
    # fully representable as rows, even if the trailing row only covers a
    # partial slot -- otherwise the configured range's tail silently
    # disappears from the grid entirely (PRD R3's "clamp/flag, don't
    # delete" applies just as much to the range itself as to blocks).
    slots_count = ceil(total_minutes / interval) if total_minutes > 0 else 0

    # matrix[day][row] holds a `_CellState` once a block claims that
    # slot, or `None` while still unclaimed (filled in as 'empty' below).
    matrix = [[None] * slots_count for _ in range(7)]
    out_of_range_blocks = []
    unplaced_blocks = []

    blocks_by_day = defaultdict(list)
    for block in blocks:
        blocks_by_day[block.day_of_week].append(block)

    for day, day_blocks in blocks_by_day.items():
        if not (0 <= day <= 6):
            continue
        for block in sorted(day_blocks, key=lambda b: b.start_time):
            block_start = minutes_since_midnight(block.start_time)
            block_end = minutes_since_midnight(block.end_time, treat_midnight_as_end_of_day=True)

            if slots_count == 0 or block_end <= range_start or block_start >= range_end:
                # Entirely outside the current visible day range (PRD R3):
                # flag it, do not render it, and never touch the stored row.
                out_of_range_blocks.append(block)
                continue

            clamped_start = max(block_start, range_start)
            clamped_end = min(block_end, range_end)
            is_clamped = clamped_start != block_start or clamped_end != block_end

            relative_start = clamped_start - range_start
            relative_end = clamped_end - range_start

            raw_start_row = round_half_up(relative_start / interval)
            raw_end_row = round_half_up(relative_end / interval)
            if raw_end_row <= raw_start_row:
                raw_end_row = raw_start_row + 1

            start_row = max(0, min(raw_start_row, slots_count - 1))
            end_row = max(start_row + 1, min(raw_end_row, slots_count))

            # A second, independent clamping mechanism alongside the
            # day-range boundary clamp above: pulling `raw_start_row`/
            # `raw_end_row` back inside `[0, slots_count]` also cuts the
            # block's rendered extent short of what its (already
            # range-clamped) stored times would otherwise snap to. Both
            # mechanisms must agree on setting the flag (PRD R3) --
            # `clamped` must never read `False` for a block that was
            # visibly cut off by either one.
            if start_row != raw_start_row or end_row != raw_end_row:
                is_clamped = True

            if matrix[day][start_row] is not None:
                # Snapping to the current `slot_interval` collided with an
                # already-placed block on the same day. This is reachable
                # through entirely valid, non-overlapping blocks (per
                # `TimeBlock.clean()`) -- e.g. two short blocks that touch
                # exactly (09:00-09:20 then 09:20-09:40) both round to the
                # same row at a coarse interval, or blocks created at a
                # fine interval before the user later coarsens
                # `slot_interval`. Never silently drop the block: search
                # forward in this day's column for the next free row,
                # re-anchor it there, and flag it as clamped since its
                # rendered position no longer matches its stored time.
                rowspan = end_row - start_row
                candidate = start_row
                while candidate < slots_count and matrix[day][candidate] is not None:
                    candidate += 1

                if candidate >= slots_count:
                    # No free row anywhere below `start_row` in this
                    # day's column for the rest of the visible range --
                    # a genuinely pathological, fully packed day. Flag it
                    # distinctly from an out-of-range block rather than
                    # silently dropping it.
                    unplaced_blocks.append(block)
                    continue

                # Shrink the rowspan to the longest contiguous run of
                # free rows available from `candidate`, so re-anchoring
                # never overruns another block or the bottom of the grid.
                span = 1
                while (
                    span < rowspan
                    and candidate + span < slots_count
                    and matrix[day][candidate + span] is None
                ):
                    span += 1

                start_row = candidate
                end_row = candidate + span
                is_clamped = True

            matrix[day][start_row] = _CellState(
                kind='block-start',
                block=block,
                rowspan=end_row - start_row,
                clamped=is_clamped,
            )
            for row in range(start_row + 1, end_row):
                if matrix[day][row] is None:
                    matrix[day][row] = _CellState(kind='occupied', block=block)

    rows = []
    for row_index in range(slots_count):
        slot_start_minutes = range_start + row_index * interval
        slot_end_minutes = slot_start_minutes + interval
        slot_start_time = time_from_minutes(slot_start_minutes)
        slot_end_time = time_from_minutes(slot_end_minutes)

        cells = []
        for day in range(7):
            state = matrix[day][row_index] or _CellState(kind='empty')
            cells.append(GridCell(
                kind=state.kind,
                day=day,
                slot_start=slot_start_time,
                slot_end=slot_end_time,
                block=state.block,
                rowspan=state.rowspan,
                clamped=state.clamped,
            ))

        rows.append(GridRow(
            label=_format_time_label(slot_start_time, time_format),
            start_time=slot_start_time,
            cells=cells,
        ))

    day_headers = [label for _, label in TimeBlock.DAY_CHOICES]

    return WeekGrid(
        day_headers=day_headers,
        rows=rows,
        slot_interval=interval,
        time_format=time_format,
        out_of_range_blocks=out_of_range_blocks,
        unplaced_blocks=unplaced_blocks,
    )
