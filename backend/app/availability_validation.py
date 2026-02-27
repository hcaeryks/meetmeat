from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any


CELL_VALUES = {"IDEAL", "OK", "UNSET"}
WEEKLY_VALUES = {"IDEAL", "OK"}
CLOCK_RE = re.compile(r"^\d{2}:\d{2}$")


def _coerce_str(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _normalize_cell(value: Any, field: str, allowed: set[str] | None = None) -> str:
    v = _coerce_str(value, field)
    if v not in CELL_VALUES:
        raise ValueError(f"{field} must be one of IDEAL/OK/UNSET")
    if allowed is not None and v not in allowed:
        allowed_text = "/".join(sorted(allowed))
        raise ValueError(f"{field} must be one of {allowed_text}")
    return v


def _parse_utc_iso(value: Any, field: str) -> datetime:
    raw = _coerce_str(value, field)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO datetime") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{field} must include timezone info")
    return dt.astimezone(timezone.utc)


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _parse_clock(value: Any, field: str) -> tuple[int, int]:
    clock = _coerce_str(value, field)
    if not CLOCK_RE.match(clock):
        raise ValueError(f"{field} must be HH:MM")
    hh = int(clock[0:2])
    mm = int(clock[3:5])
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        raise ValueError(f"{field} must be HH:MM")
    return hh, mm


def _clock_to_minutes(value: Any, field: str) -> int:
    hh, mm = _parse_clock(value, field)
    return hh * 60 + mm


def _normalize_weekly_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("weekly entries must be objects")
    dow_raw = entry.get("dow")
    try:
        dow = int(dow_raw)
    except Exception as exc:
        raise ValueError("weekly.dow must be an integer from 0 to 6") from exc
    if dow < 0 or dow > 6:
        raise ValueError("weekly.dow must be an integer from 0 to 6")

    start = _coerce_str(entry.get("start"), "weekly.start")
    end = _coerce_str(entry.get("end"), "weekly.end")
    start_min = _clock_to_minutes(start, "weekly.start")
    end_min = _clock_to_minutes(end, "weekly.end")
    if end_min <= start_min:
        raise ValueError("weekly.end must be later than weekly.start")

    value = _normalize_cell(entry.get("value"), "weekly.value", WEEKLY_VALUES)
    return {
        "dow": dow,
        "start": start,
        "end": end,
        "value": value,
    }


def _normalize_intervals(intervals: Any, field: str) -> list[list[str]]:
    if not isinstance(intervals, list):
        raise ValueError(f"{field} must be a list")
    out: list[list[str]] = []
    for i, item in enumerate(intervals):
        if not isinstance(item, list | tuple) or len(item) < 3:
            raise ValueError(f"{field}[{i}] must be [start_utc, end_utc, value]")
        start = _parse_utc_iso(item[0], f"{field}[{i}].start_utc")
        end = _parse_utc_iso(item[1], f"{field}[{i}].end_utc")
        if end <= start:
            raise ValueError(f"{field}[{i}] end must be after start")
        value = _normalize_cell(item[2], f"{field}[{i}].value", WEEKLY_VALUES)
        out.append([_format_utc(start), _format_utc(end), value])
    return out


def _normalize_dates_entries(dates: Any) -> list[dict[str, str]]:
    if not isinstance(dates, list):
        raise ValueError("dates must be a list")
    out: list[dict[str, str]] = []
    for i, item in enumerate(dates):
        if not isinstance(item, dict):
            raise ValueError(f"dates[{i}] must be an object")
        date_str = _coerce_str(item.get("date"), f"dates[{i}].date")
        try:
            date.fromisoformat(date_str)
        except ValueError as exc:
            raise ValueError(f"dates[{i}].date must be YYYY-MM-DD") from exc
        value = _normalize_cell(item.get("value"), f"dates[{i}].value")
        out.append({"date": date_str, "value": value})
    return out


def _normalize_votes(votes: Any) -> list[dict[str, str]]:
    if not isinstance(votes, list):
        raise ValueError("votes must be a list")
    out: list[dict[str, str]] = []
    for i, item in enumerate(votes):
        if not isinstance(item, dict):
            raise ValueError(f"votes[{i}] must be an object")
        option_id = _coerce_str(item.get("option_id"), f"votes[{i}].option_id")
        value = _normalize_cell(item.get("value"), f"votes[{i}].value")
        out.append({"option_id": option_id, "value": value})
    return out


def validate_and_normalize_availability(
    mode: str,
    config: dict[str, Any],
    anchor_timezone: str,
    availability: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(availability, dict):
        raise ValueError("availability must be an object")

    if mode == "WEEKLY_GRID":
        scope = config.get("scope", "ANY_WEEK")
        submitted_scope = availability.get("scope", scope)
        if submitted_scope not in {"ANY_WEEK", "SPECIFIC_WEEK"}:
            raise ValueError("WEEKLY_GRID scope must be ANY_WEEK or SPECIFIC_WEEK")

        normalized: dict[str, Any] = {
            "type": "WEEKLY_GRID",
            "scope": submitted_scope,
        }
        if submitted_scope == "ANY_WEEK":
            weekly = availability.get("weekly", [])
            normalized["anchor_timezone"] = _coerce_str(
                availability.get("anchor_timezone", anchor_timezone), "anchor_timezone"
            )
            normalized["weekly"] = [_normalize_weekly_entry(entry) for entry in weekly]
        else:
            normalized["intervals_utc"] = _normalize_intervals(
                availability.get("intervals_utc", []), "intervals_utc"
            )
        return normalized

    if mode == "DATES_ONLY":
        return {
            "type": "DATES_ONLY",
            "anchor_timezone": _coerce_str(
                availability.get("anchor_timezone", anchor_timezone), "anchor_timezone"
            ),
            "dates": _normalize_dates_entries(availability.get("dates", [])),
        }

    if mode in {"DATE_TIME_WINDOWS", "DURATION_FINDER"}:
        return {
            "type": "DATE_TIME_WINDOWS",
            "intervals_utc": _normalize_intervals(
                availability.get("intervals_utc", []), "intervals_utc"
            ),
        }

    if mode == "OPTIONS_POLL":
        return {
            "type": "OPTIONS_POLL",
            "votes": _normalize_votes(availability.get("votes", [])),
        }

    raise ValueError(f"Unsupported mode: {mode}")
