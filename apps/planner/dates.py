"""Date and ISO-week helpers shared by planner views and templates."""

import calendar
from datetime import date, timedelta


def normalize_week_start(value=None):
    """Return the Monday belonging to ``value`` (or today when omitted)."""
    value = value or date.today()
    return value - timedelta(days=value.weekday())


def parse_week_start(value):
    """Parse a YYYY-MM-DD week value and normalize it to Monday.

    Invalid user input deliberately falls back to the current week so a bad
    shared URL cannot produce a server error or an unbounded query.
    """
    try:
        return normalize_week_start(date.fromisoformat(value))
    except (TypeError, ValueError):
        return normalize_week_start()


def week_end(week_start):
    return week_start + timedelta(days=6)


def week_label(week_start):
    """Return the compact English label used by the planner header."""
    end = week_end(week_start)
    if week_start.year == end.year and week_start.month == end.month:
        dates = f'{week_start.day:02d}–{end.day:02d} {end.strftime("%b")} {end.year}'
    elif week_start.year == end.year:
        dates = (
            f'{week_start.day:02d} {week_start.strftime("%b")}–'
            f'{end.day:02d} {end.strftime("%b")} {end.year}'
        )
    else:
        dates = (
            f'{week_start.day:02d} {week_start.strftime("%b")} {week_start.year}–'
            f'{end.day:02d} {end.strftime("%b")} {end.year}'
        )
    return f'Week {week_start.isocalendar().week} - {week_start.isocalendar().year} · {dates}'


def month_calendar(month_start, selected_week):
    """Build a compact Sunday-first month matrix for the date picker."""
    month_start = month_start.replace(day=1)
    rows = []
    for week in calendar.Calendar(firstweekday=calendar.SUNDAY).monthdatescalendar(
        month_start.year,
        month_start.month,
    ):
        days = []
        for current in week:
            days.append({
                'date': current,
                'day': current.day,
                'in_month': current.month == month_start.month,
                'is_weekend': current.weekday() >= 5,
                'is_today': current == date.today(),
                'is_selected': current == selected_week,
                'week_start': normalize_week_start(current),
            })
        rows.append({'days': days})
    return rows


def shift_month(month_start, amount):
    """Move a month by ``amount`` without relying on month-length arithmetic."""
    index = month_start.year * 12 + month_start.month - 1 + amount
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


def navigation_context(week_start, month_value=None):
    """Return the serializable context used by both planner page views."""
    try:
        month_start = (
            date.fromisoformat(f'{month_value}-01')
            if month_value else week_start.replace(day=1)
        )
    except (TypeError, ValueError):
        month_start = week_start.replace(day=1)
    current_week = normalize_week_start()
    return {
        'selected_week_start': week_start,
        'selected_week_value': week_start.isoformat(),
        'selected_week_end': week_end(week_start),
        'week_label': week_label(week_start),
        'is_current_week': week_start == current_week,
        'previous_week': week_start - timedelta(days=7),
        'next_week': week_start + timedelta(days=7),
        'today_week_start': current_week,
        'calendar_month': month_start,
        'calendar_today': date.today(),
        'calendar_day_headers': ('S', 'M', 'T', 'W', 'T', 'F', 'S'),
        'calendar_rows': month_calendar(month_start, week_start),
        'previous_month': shift_month(month_start, -1),
        'next_month': shift_month(month_start, 1),
    }
