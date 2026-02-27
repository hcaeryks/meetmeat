from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from .db import get_connection


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_id(length: int = 10) -> str:
    return secrets.token_urlsafe(length)


def _format_utc_millis(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _parse_utc_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hhmm(minutes: int) -> str:
    hh = minutes // 60
    mm = minutes % 60
    return f"{hh:02d}:{mm:02d}"


def _clock_to_minutes(clock: str) -> int | None:
    parts = clock.split(":")
    if len(parts) != 2:
        return None
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except Exception:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return hh * 60 + mm


def _iter_interval_slot_keys(
    start_utc: str, end_utc: str, slot_minutes: int
) -> list[str]:
    try:
        start = _parse_utc_iso(start_utc)
        end = _parse_utc_iso(end_utc)
    except Exception:
        return []
    if end <= start:
        return []

    step = timedelta(minutes=max(1, slot_minutes))
    keys: list[str] = []
    current = start
    while current < end:
        next_dt = min(current + step, end)
        keys.append(f"{_format_utc_millis(current)}|{_format_utc_millis(next_dt)}")
        current = next_dt
    return keys


def _iter_weekly_slot_keys(
    dow: int, start_clock: str, end_clock: str, slot_minutes: int
) -> list[str]:
    start_min = _clock_to_minutes(start_clock)
    end_min = _clock_to_minutes(end_clock)
    if start_min is None or end_min is None or end_min <= start_min:
        return []
    step = max(1, slot_minutes)
    keys: list[str] = []
    current = start_min
    while current < end_min:
        next_min = min(current + step, end_min)
        keys.append(f"{dow}|{_hhmm(current)}|{_hhmm(next_min)}")
        current = next_min
    return keys


# ── Plans ──────────────────────────────────────────────────────


def create_plan(
    title: str,
    mode: str,
    anchor_timezone: str,
    slot_minutes: int,
    require_password: bool,
    config: dict[str, Any],
) -> str:
    conn = get_connection()
    try:
        for _ in range(10):
            plan_id = _generate_id()
            try:
                conn.execute(
                    """INSERT INTO plans
                       (plan_id, title, mode, created_at_utc, anchor_timezone,
                        slot_minutes, require_password, config_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        plan_id,
                        title,
                        mode,
                        _now_utc(),
                        anchor_timezone,
                        slot_minutes,
                        1 if require_password else 0,
                        json.dumps(config),
                    ),
                )
                conn.commit()
                return plan_id
            except Exception:
                continue
        raise RuntimeError("Failed to generate unique plan_id")
    finally:
        conn.close()


def get_plan(plan_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["config_json"] = json.loads(d["config_json"])
        return d
    finally:
        conn.close()


def set_plan_password(plan_id: str, password_hash: str) -> bool:
    """Set password. Returns False if already set."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """UPDATE plans SET password_hash = ?, password_created_at_utc = ?
               WHERE plan_id = ? AND password_hash IS NULL""",
            (password_hash, _now_utc(), plan_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Participants ───────────────────────────────────────────────


def get_participant_by_name(plan_id: str, display_name: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM participants WHERE plan_id = ? AND display_name = ?",
            (plan_id, display_name),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_participant_by_id(participant_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM participants WHERE participant_id = ?",
            (participant_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_or_get_participant(
    plan_id: str, display_name: str, tz: str, password_hash: str | None = None
) -> dict[str, Any]:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM participants WHERE plan_id = ? AND display_name = ?",
            (plan_id, display_name),
        ).fetchone()
        if existing:
            d = dict(existing)
            if d["timezone"] != tz:
                conn.execute(
                    "UPDATE participants SET timezone = ? WHERE participant_id = ?",
                    (tz, d["participant_id"]),
                )
                conn.commit()
                d["timezone"] = tz
            return d
        pid = _generate_id()
        conn.execute(
            """INSERT INTO participants
               (participant_id, plan_id, display_name, timezone, created_at_utc, password_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pid, plan_id, display_name, tz, _now_utc(), password_hash),
        )
        conn.commit()
        return {
            "participant_id": pid,
            "plan_id": plan_id,
            "display_name": display_name,
            "timezone": tz,
            "created_at_utc": _now_utc(),
            "password_hash": password_hash,
        }
    finally:
        conn.close()


def get_participants_count(plan_id: str) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM participants WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


# ── Submissions ────────────────────────────────────────────────


def upsert_submission(
    plan_id: str, participant_id: str, availability: dict[str, Any]
) -> str:
    conn = get_connection()
    now = _now_utc()
    try:
        existing = conn.execute(
            "SELECT submission_id FROM submissions WHERE plan_id = ? AND participant_id = ?",
            (plan_id, participant_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE submissions SET availability_json = ?, updated_at_utc = ? WHERE submission_id = ?",
                (json.dumps(availability), now, existing["submission_id"]),
            )
        else:
            sid = _generate_id()
            conn.execute(
                """INSERT INTO submissions
                   (submission_id, plan_id, participant_id, availability_json, updated_at_utc)
                   VALUES (?, ?, ?, ?, ?)""",
                (sid, plan_id, participant_id, json.dumps(availability), now),
            )
        conn.commit()
        return now
    finally:
        conn.close()


def get_submission(plan_id: str, participant_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM submissions WHERE plan_id = ? AND participant_id = ?",
            (plan_id, participant_id),
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["availability_json"] = json.loads(d["availability_json"])
        return d
    finally:
        conn.close()


def get_all_submissions(plan_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM submissions WHERE plan_id = ?", (plan_id,)
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["availability_json"] = json.loads(d["availability_json"])
            result.append(d)
        return result
    finally:
        conn.close()


def get_all_participants(plan_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM participants WHERE plan_id = ?", (plan_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Aggregation ────────────────────────────────────────────────


def compute_aggregate(plan_id: str) -> dict[str, Any]:
    plan = get_plan(plan_id)
    if not plan:
        return {}
    mode = plan["mode"]
    submissions = get_all_submissions(plan_id)
    participants_count = get_participants_count(plan_id)
    all_participants = get_all_participants(plan_id)
    config = plan["config_json"]
    slot_minutes = plan["slot_minutes"]

    if mode == "WEEKLY_GRID":
        return _aggregate_grid(
            submissions, participants_count, all_participants, slot_minutes
        )
    elif mode == "DATES_ONLY":
        return _aggregate_dates(submissions, participants_count, all_participants)
    elif mode == "DATE_TIME_WINDOWS":
        return _aggregate_grid(
            submissions, participants_count, all_participants, slot_minutes
        )
    elif mode == "OPTIONS_POLL":
        return _aggregate_options(submissions, participants_count, config, all_participants)
    elif mode == "DURATION_FINDER":
        return _aggregate_duration(submissions, participants_count, config, all_participants)
    return {}


def _aggregate_grid(
    submissions: list[dict[str, Any]],
    participants_count: int,
    all_participants: list[dict[str, Any]] | None = None,
    slot_minutes: int = 15,
) -> dict[str, Any]:
    """Aggregate for interval-based modes. Returns per-slot counts and participant names."""
    pid_to_name: dict[str, str] = {}
    participant_ids: set[str] = set()
    if all_participants:
        for p in all_participants:
            pid = p["participant_id"]
            participant_ids.add(pid)
            pid_to_name[pid] = p["display_name"]

    slot_counts: dict[str, dict[str, int]] = {}
    slot_ideal: dict[str, set[str]] = {}
    slot_ok: dict[str, set[str]] = {}

    def ensure_slot(key: str) -> None:
        if key not in slot_counts:
            slot_counts[key] = {"IDEAL": 0, "OK": 0}
            slot_ideal[key] = set()
            slot_ok[key] = set()

    for sub in submissions:
        avail = sub["availability_json"]
        pid = sub["participant_id"]
        participant_ids.add(pid)

        intervals = avail.get("intervals_utc", [])
        for interval in intervals:
            start, end, value = interval[0], interval[1], interval[2]
            keys = _iter_interval_slot_keys(start, end, slot_minutes)
            if not keys:
                keys = [f"{start}|{end}"]
            for key in keys:
                ensure_slot(key)
                if value in ("IDEAL", "OK"):
                    slot_counts[key][value] += 1
                    if value == "IDEAL":
                        slot_ideal[key].add(pid)
                    else:
                        slot_ok[key].add(pid)

        weekly = avail.get("weekly", [])
        for entry in weekly:
            keys = _iter_weekly_slot_keys(
                entry["dow"], entry["start"], entry["end"], slot_minutes
            )
            if not keys:
                keys = [f"{entry['dow']}|{entry['start']}|{entry['end']}"]
            value = entry.get("value", "UNSET")
            for key in keys:
                ensure_slot(key)
                if value in ("IDEAL", "OK"):
                    slot_counts[key][value] += 1
                    if value == "IDEAL":
                        slot_ideal[key].add(pid)
                    else:
                        slot_ok[key].add(pid)

    slot_participants: dict[str, dict[str, list[str]]] = {}
    for key in slot_counts:
        ideal_pids = slot_ideal.get(key, set())
        ok_pids = slot_ok.get(key, set())
        unset_pids = participant_ids - ideal_pids - ok_pids
        slot_participants[key] = {
            "IDEAL": sorted(pid_to_name.get(p, p) for p in ideal_pids),
            "OK": sorted(pid_to_name.get(p, p) for p in ok_pids),
            "UNSET": sorted(pid_to_name.get(p, p) for p in unset_pids),
        }

    return {
        "participants_count": participants_count,
        "slot_counts": slot_counts,
        "slot_participants": slot_participants,
    }


def _aggregate_dates(
    submissions: list[dict[str, Any]],
    participants_count: int,
    all_participants: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pid_to_name: dict[str, str] = {}
    participant_ids: set[str] = set()
    if all_participants:
        for p in all_participants:
            pid = p["participant_id"]
            participant_ids.add(pid)
            pid_to_name[pid] = p["display_name"]

    date_counts: dict[str, dict[str, int]] = {}
    date_ideal: dict[str, set[str]] = {}
    date_ok: dict[str, set[str]] = {}

    for sub in submissions:
        avail = sub["availability_json"]
        pid = sub["participant_id"]
        participant_ids.add(pid)

        for d in avail.get("dates", []):
            date_str = d["date"]
            value = d.get("value", "UNSET")
            if date_str not in date_counts:
                date_counts[date_str] = {"IDEAL": 0, "OK": 0}
                date_ideal[date_str] = set()
                date_ok[date_str] = set()
            if value in ("IDEAL", "OK"):
                date_counts[date_str][value] += 1
                if value == "IDEAL":
                    date_ideal[date_str].add(pid)
                else:
                    date_ok[date_str].add(pid)

    date_participants: dict[str, dict[str, list[str]]] = {}
    for date_str in date_counts:
        ideal_pids = date_ideal.get(date_str, set())
        ok_pids = date_ok.get(date_str, set())
        unset_pids = participant_ids - ideal_pids - ok_pids
        date_participants[date_str] = {
            "IDEAL": sorted(pid_to_name.get(p, p) for p in ideal_pids),
            "OK": sorted(pid_to_name.get(p, p) for p in ok_pids),
            "UNSET": sorted(pid_to_name.get(p, p) for p in unset_pids),
        }

    return {
        "participants_count": participants_count,
        "date_counts": date_counts,
        "date_participants": date_participants,
    }


def _aggregate_options(
    submissions: list[dict[str, Any]],
    participants_count: int,
    config: dict[str, Any],
    all_participants: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pid_to_name: dict[str, str] = {}
    participant_ids: set[str] = set()
    if all_participants:
        for p in all_participants:
            pid = p["participant_id"]
            participant_ids.add(pid)
            pid_to_name[pid] = p["display_name"]

    options = config.get("options", [])
    option_counts: dict[str, dict[str, int]] = {}
    option_ideal: dict[str, set[str]] = {}
    option_ok: dict[str, set[str]] = {}
    for opt in options:
        option_counts[opt["option_id"]] = {"IDEAL": 0, "OK": 0}
        option_ideal[opt["option_id"]] = set()
        option_ok[opt["option_id"]] = set()
    for sub in submissions:
        avail = sub["availability_json"]
        pid = sub["participant_id"]
        participant_ids.add(pid)
        for vote in avail.get("votes", []):
            oid = vote["option_id"]
            val = vote.get("value", "UNSET")
            if oid not in option_counts:
                option_counts[oid] = {"IDEAL": 0, "OK": 0}
                option_ideal[oid] = set()
                option_ok[oid] = set()
            if val in ("IDEAL", "OK"):
                option_counts[oid][val] += 1
                if val == "IDEAL":
                    option_ideal[oid].add(pid)
                else:
                    option_ok[oid].add(pid)

    option_participants: dict[str, dict[str, list[str]]] = {}
    for oid in option_counts:
        ideal_pids = option_ideal.get(oid, set())
        ok_pids = option_ok.get(oid, set())
        unset_pids = participant_ids - ideal_pids - ok_pids
        option_participants[oid] = {
            "IDEAL": sorted(pid_to_name.get(p, p) for p in ideal_pids),
            "OK": sorted(pid_to_name.get(p, p) for p in ok_pids),
            "UNSET": sorted(pid_to_name.get(p, p) for p in unset_pids),
        }
    return {
        "participants_count": participants_count,
        "option_counts": option_counts,
        "option_participants": option_participants,
    }


def _aggregate_duration(
    submissions: list[dict[str, Any]],
    participants_count: int,
    config: dict[str, Any],
    all_participants: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    duration_minutes = config.get("duration_minutes", 60)
    slot_minutes = config.get("slot_minutes", 15)
    min_attendees = config.get("min_attendees", 1)
    slots_needed = max(1, duration_minutes // slot_minutes)

    pid_to_name: dict[str, str] = {}
    if all_participants:
        for p in all_participants:
            pid_to_name[p["participant_id"]] = p["display_name"]

    all_submitted_pids: set[str] = set()
    all_intervals: list[tuple[str, str, str, str]] = []
    for sub in submissions:
        avail = sub["availability_json"]
        pid = sub["participant_id"]
        all_submitted_pids.add(pid)
        for interval in avail.get("intervals_utc", []):
            all_intervals.append((interval[0], interval[1], interval[2], pid))

    all_intervals.sort(key=lambda x: x[0])

    slot_set: dict[str, set[str]] = {}
    ideal_set: dict[str, set[str]] = {}
    ok_set: dict[str, set[str]] = {}
    for start_str, end_str, value, pid in all_intervals:
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except Exception:
            continue
        current = start_dt
        while current < end_dt:
            key = current.isoformat()
            if key not in slot_set:
                slot_set[key] = set()
                ideal_set[key] = set()
                ok_set[key] = set()
            slot_set[key].add(pid)
            if value == "IDEAL":
                ideal_set[key].add(pid)
            elif value == "OK":
                ok_set[key].add(pid)
            current += timedelta(minutes=slot_minutes)

    slot_counts: dict[str, dict[str, int]] = {}
    slot_participants: dict[str, dict[str, list[str]]] = {}
    for key in slot_set:
        ideal_pids = ideal_set.get(key, set())
        ok_pids = ok_set.get(key, set())
        unset_pids = all_submitted_pids - ideal_pids - ok_pids
        slot_counts[key] = {"IDEAL": len(ideal_pids), "OK": len(ok_pids)}
        slot_participants[key] = {
            "IDEAL": sorted(pid_to_name.get(p, p) for p in ideal_pids),
            "OK": sorted(pid_to_name.get(p, p) for p in ok_pids),
            "UNSET": sorted(pid_to_name.get(p, p) for p in unset_pids),
        }

    sorted_slots = sorted(slot_set.keys())
    top_slots: list[dict[str, Any]] = []

    for i in range(len(sorted_slots) - slots_needed + 1):
        window_slots = sorted_slots[i : i + slots_needed]
        common = slot_set.get(window_slots[0], set()).copy()
        ideal_common = ideal_set.get(window_slots[0], set()).copy()
        for s in window_slots[1:]:
            common &= slot_set.get(s, set())
            ideal_common &= ideal_set.get(s, set())
        if len(common) >= min_attendees:
            try:
                end_dt = datetime.fromisoformat(
                    window_slots[-1].replace("Z", "+00:00")
                ) + timedelta(minutes=slot_minutes)
            except Exception:
                continue
            top_slots.append(
                {
                    "start_utc": window_slots[0],
                    "end_utc": end_dt.isoformat(),
                    "total": len(common),
                    "ideal": len(ideal_common),
                }
            )

    top_slots.sort(key=lambda x: (-x["ideal"], -x["total"]))
    top_slots = top_slots[:10]

    return {
        "participants_count": participants_count,
        "slot_counts": slot_counts,
        "slot_participants": slot_participants,
        "top_slots": top_slots,
    }
