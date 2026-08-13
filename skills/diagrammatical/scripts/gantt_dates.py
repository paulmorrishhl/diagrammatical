#!/usr/bin/env python3
"""Small deterministic calculations for inclusive-date Gantt diagrams."""

from __future__ import annotations

from datetime import date, timedelta


def parse_iso_date(value: str) -> date:
    """Parse a strict ISO calendar date."""

    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid ISO date '{value}'; expected YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"invalid ISO date '{value}'; expected YYYY-MM-DD")
    return parsed


def inclusive_duration(start: str | date, end: str | date) -> int:
    """Return inclusive calendar-day duration; reject reversed ranges."""

    start_date = parse_iso_date(start) if isinstance(start, str) else start
    end_date = parse_iso_date(end) if isinstance(end, str) else end
    days = (end_date - start_date).days + 1
    if days < 1:
        raise ValueError("end date must be on or after start date")
    return days


def resolve_end(start: str | date, duration_days: int) -> date:
    """Resolve an inclusive end date from a positive duration."""

    start_date = parse_iso_date(start) if isinstance(start, str) else start
    if not isinstance(duration_days, int) or isinstance(duration_days, bool) or duration_days < 1:
        raise ValueError("durationDays must be a positive integer")
    return start_date + timedelta(days=duration_days - 1)


def select_scale(plan_start: str | date, plan_end: str | date) -> str:
    """Select a readable week, month, or quarter scale from inclusive span."""

    days = inclusive_duration(plan_start, plan_end)
    if days <= 70:
        return "week"
    if days <= 550:
        return "month"
    return "quarter"


def date_to_x(
    value: str | date,
    plan_start: str | date,
    plan_end: str | date,
    x_min: float,
    x_max: float,
) -> float:
    """Map a date to a bounded coordinate using inclusive day cells."""

    current = parse_iso_date(value) if isinstance(value, str) else value
    start = parse_iso_date(plan_start) if isinstance(plan_start, str) else plan_start
    end = parse_iso_date(plan_end) if isinstance(plan_end, str) else plan_end
    if end < start:
        raise ValueError("plan end date must be on or after plan start date")
    if current < start or current > end:
        raise ValueError("date falls outside the declared plan range")
    if x_max <= x_min:
        raise ValueError("timeline coordinate bounds must increase")
    total_cells = inclusive_duration(start, end)
    return x_min + ((current - start).days / total_cells) * (x_max - x_min)


def task_span(
    start: str | date,
    end: str | date,
    plan_start: str | date,
    plan_end: str | date,
    x_min: float,
    x_max: float,
) -> tuple[float, float]:
    """Return the x coordinate and width for an inclusive task bar."""

    start_x = date_to_x(start, plan_start, plan_end, x_min, x_max)
    end_date = parse_iso_date(end) if isinstance(end, str) else end
    plan_end_date = parse_iso_date(plan_end) if isinstance(plan_end, str) else plan_end
    cell_width = (x_max - x_min) / inclusive_duration(plan_start, plan_end)
    if end_date == plan_end_date:
        end_x = x_max
    else:
        end_x = date_to_x(end_date + timedelta(days=1), plan_start, plan_end, x_min, x_max)
    return start_x, end_x - start_x if end_x > start_x else cell_width
