from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import crud
from .availability_validation import validate_and_normalize_availability
from .auth import hash_password, verify_password
from .db import init_db
from .models import (
    AggregateResponse,
    CreateParticipantRequest,
    CreatePlanRequest,
    CreatePlanResponse,
    GetSubmissionResponse,
    ParticipantResponse,
    PlanResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    SubmitAvailabilityRequest,
    SubmitAvailabilityResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="meet me at API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _verify_plan_password(
    plan: dict[str, Any], password: str | None
) -> None:
    if not plan["require_password"]:
        return
    if plan["password_hash"] is None:
        return
    if not password:
        raise HTTPException(status_code=401, detail="Password required")
    if not verify_password(password, plan["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid password")


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_plan_tz(dt: datetime, tz_name: str) -> datetime:
    try:
        return dt.astimezone(ZoneInfo(tz_name))
    except Exception:
        return dt.astimezone(timezone.utc)


def _time_label(dt: datetime) -> str:
    hour12 = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour12}:{dt.minute:02d} {ampm}"


def _date_label(dt: datetime) -> str:
    return f"{dt.strftime('%a %b')} {dt.day}"


def _datetime_label(dt: datetime) -> str:
    return f"{_date_label(dt)} {_time_label(dt)}"


def _interval_label(start_utc: str, end_utc: str, tz_name: str) -> str:
    try:
        start = _to_plan_tz(_parse_utc(start_utc), tz_name)
        end = _to_plan_tz(_parse_utc(end_utc), tz_name)
    except Exception:
        return f"{start_utc} to {end_utc}"
    if start.date() == end.date():
        return f"{_date_label(start)} {_time_label(start)}-{_time_label(end)}"
    return f"{_datetime_label(start)} to {_datetime_label(end)}"


def _clock_label(clock: str) -> str:
    parts = clock.split(":")
    if len(parts) != 2:
        return clock
    try:
        hh = int(parts[0])
        mm = int(parts[1])
    except Exception:
        return clock
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return clock
    hour12 = hh % 12 or 12
    ampm = "AM" if hh < 12 else "PM"
    return f"{hour12}:{mm:02d} {ampm}"


def _weekly_label(entry: dict[str, Any]) -> str:
    dow_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    dow = entry.get("dow")
    start = str(entry.get("start", ""))
    end = str(entry.get("end", ""))
    day = f"DOW {dow}"
    if isinstance(dow, int) and 0 <= dow <= 6:
        day = dow_labels[dow]
    return f"{day} {_clock_label(start)}-{_clock_label(end)}"


def _date_value_label(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(f"{date_str}T00:00:00")
        return _date_label(dt)
    except Exception:
        return date_str


def _join_human(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _option_label(
    option: dict[str, Any] | None, fallback_id: str, tz_name: str
) -> str:
    if not option:
        return fallback_id
    start = option.get("start_utc")
    duration = option.get("duration_minutes")
    if not isinstance(start, str) or not start:
        return fallback_id
    try:
        start_dt = _to_plan_tz(_parse_utc(start), tz_name)
        base = _datetime_label(start_dt)
    except Exception:
        base = start
    if isinstance(duration, (int, float)) and duration > 0:
        return f"{base} ({int(duration)} min)"
    return base


def _extract_mode_buckets(
    plan: dict[str, Any], availability: dict[str, Any] | None
) -> tuple[list[str], list[str]]:
    mode = plan["mode"]
    config = plan["config_json"]
    anchor_tz = plan["anchor_timezone"]
    ideal: list[str] = []
    ok: list[str] = []
    if not isinstance(availability, dict):
        return ideal, ok

    if mode == "WEEKLY_GRID":
        scope = availability.get("scope", config.get("scope", "ANY_WEEK"))
        if scope == "ANY_WEEK":
            for entry in availability.get("weekly", []):
                if not isinstance(entry, dict):
                    continue
                value = entry.get("value")
                label = _weekly_label(entry)
                if value == "IDEAL":
                    _append_unique(ideal, label)
                elif value == "OK":
                    _append_unique(ok, label)
        else:
            for interval in availability.get("intervals_utc", []):
                if not isinstance(interval, list | tuple) or len(interval) < 3:
                    continue
                label = _interval_label(str(interval[0]), str(interval[1]), anchor_tz)
                if interval[2] == "IDEAL":
                    _append_unique(ideal, label)
                elif interval[2] == "OK":
                    _append_unique(ok, label)

    elif mode in {"DATE_TIME_WINDOWS", "DURATION_FINDER"}:
        for interval in availability.get("intervals_utc", []):
            if not isinstance(interval, list | tuple) or len(interval) < 3:
                continue
            label = _interval_label(str(interval[0]), str(interval[1]), anchor_tz)
            if interval[2] == "IDEAL":
                _append_unique(ideal, label)
            elif interval[2] == "OK":
                _append_unique(ok, label)

    elif mode == "DATES_ONLY":
        for item in availability.get("dates", []):
            if not isinstance(item, dict):
                continue
            date_str = item.get("date")
            if not isinstance(date_str, str):
                continue
            label = _date_value_label(date_str)
            if item.get("value") == "IDEAL":
                _append_unique(ideal, label)
            elif item.get("value") == "OK":
                _append_unique(ok, label)

    elif mode == "OPTIONS_POLL":
        options = config.get("options", [])
        by_id: dict[str, dict[str, Any]] = {}
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict) and isinstance(option.get("option_id"), str):
                    by_id[option["option_id"]] = option
        for vote in availability.get("votes", []):
            if not isinstance(vote, dict):
                continue
            option_id = vote.get("option_id")
            if not isinstance(option_id, str):
                continue
            label = _option_label(by_id.get(option_id), option_id, anchor_tz)
            if vote.get("value") == "IDEAL":
                _append_unique(ideal, label)
            elif vote.get("value") == "OK":
                _append_unique(ok, label)

    return ideal, ok


def _participant_availability_sentence(
    name: str, plan: dict[str, Any], submission: dict[str, Any] | None
) -> str:
    if not submission:
        return f"{name} has not submitted availability yet."
    ideal, ok = _extract_mode_buckets(plan, submission.get("availability_json"))
    if ideal and ok:
        return (
            f"{name} is ideally available for {_join_human(ideal)}. "
            f"{name} could be available for {_join_human(ok)}. "
            f"{name} is not available for any other time."
        )
    if ideal:
        return (
            f"{name} is ideally available for {_join_human(ideal)}. "
            f"{name} is not available for any other time."
        )
    if ok:
        return (
            f"{name} could be available for {_join_human(ok)}. "
            f"{name} is not available for any other time."
        )
    return f"{name} is not available for any listed time."


# ── 1. Create plan ─────────────────────────────────────────────


@app.post("/api/plans", response_model=CreatePlanResponse)
async def create_plan(req: CreatePlanRequest):
    plan_id = crud.create_plan(
        title=req.title,
        mode=req.mode,
        anchor_timezone=req.anchor_timezone,
        slot_minutes=req.slot_minutes,
        require_password=req.require_password,
        config=req.config,
    )
    return CreatePlanResponse(plan_id=plan_id, url_path=f"/{plan_id}")


# ── 2. Get plan ────────────────────────────────────────────────


@app.get("/api/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    count = crud.get_participants_count(plan_id)
    return PlanResponse(
        plan_id=plan["plan_id"],
        title=plan["title"],
        mode=plan["mode"],
        created_at_utc=plan["created_at_utc"],
        anchor_timezone=plan["anchor_timezone"],
        slot_minutes=plan["slot_minutes"],
        require_password=bool(plan["require_password"]),
        password_hash_exists=plan["password_hash"] is not None,
        config=plan["config_json"],
        participants_count=count,
    )


# ── 3. Set password ────────────────────────────────────────────


@app.post("/api/plans/{plan_id}/password", response_model=SetPasswordResponse)
async def set_password(plan_id: str, req: SetPasswordRequest):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan["require_password"]:
        raise HTTPException(status_code=400, detail="Plan does not require password")
    hashed = hash_password(req.password)
    ok = crud.set_plan_password(plan_id, hashed)
    if not ok:
        raise HTTPException(status_code=409, detail="Password already set")
    return SetPasswordResponse(ok=True)


# ── 4. Create / get participant ────────────────────────────────


@app.post("/api/plans/{plan_id}/participants", response_model=ParticipantResponse)
async def create_participant(
    plan_id: str,
    req: CreateParticipantRequest,
    x_plan_password: str | None = Header(None),
):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    _verify_plan_password(plan, x_plan_password)

    existing = crud.get_participant_by_name(plan_id, req.display_name)
    if existing:
        if existing.get("password_hash"):
            if not req.password:
                raise HTTPException(status_code=401, detail="Participant password required")
            if not verify_password(req.password, existing["password_hash"]):
                raise HTTPException(status_code=401, detail="Invalid participant password")
        return ParticipantResponse(
            participant_id=existing["participant_id"],
            display_name=existing["display_name"],
            timezone=existing["timezone"],
            has_password=existing.get("password_hash") is not None,
        )

    pw_hash = hash_password(req.password) if req.password else None
    p = crud.create_or_get_participant(plan_id, req.display_name, req.timezone, pw_hash)
    return ParticipantResponse(
        participant_id=p["participant_id"],
        display_name=p["display_name"],
        timezone=p["timezone"],
        has_password=p.get("password_hash") is not None,
    )


# ── 5. Submit availability ─────────────────────────────────────


@app.put(
    "/api/plans/{plan_id}/submissions/{participant_id}",
    response_model=SubmitAvailabilityResponse,
)
async def submit_availability(
    plan_id: str,
    participant_id: str,
    req: SubmitAvailabilityRequest,
    x_plan_password: str | None = Header(None),
    x_participant_password: str | None = Header(None),
):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    _verify_plan_password(plan, x_plan_password)

    participant = crud.get_participant_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    if participant["plan_id"] != plan_id:
        raise HTTPException(status_code=404, detail="Participant not found in this plan")
    if participant.get("password_hash"):
        if not x_participant_password:
            raise HTTPException(status_code=401, detail="Participant password required")
        if not verify_password(x_participant_password, participant["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid participant password")

    try:
        normalized = validate_and_normalize_availability(
            mode=plan["mode"],
            config=plan["config_json"],
            anchor_timezone=plan["anchor_timezone"],
            availability=req.availability,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    updated = crud.upsert_submission(plan_id, participant_id, normalized)
    return SubmitAvailabilityResponse(ok=True, updated_at_utc=updated)


# ── 6. Get participant submission ──────────────────────────────


@app.get(
    "/api/plans/{plan_id}/submissions/{participant_id}",
    response_model=GetSubmissionResponse,
)
async def get_submission(
    plan_id: str,
    participant_id: str,
    x_plan_password: str | None = Header(None),
    x_participant_password: str | None = Header(None),
):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    _verify_plan_password(plan, x_plan_password)

    participant = crud.get_participant_by_id(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    if participant["plan_id"] != plan_id:
        raise HTTPException(status_code=404, detail="Participant not found in this plan")
    if participant.get("password_hash"):
        if not x_participant_password:
            raise HTTPException(status_code=401, detail="Participant password required")
        if not verify_password(x_participant_password, participant["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid participant password")

    sub = crud.get_submission(plan_id, participant_id)
    return GetSubmissionResponse(
        participant_id=participant_id,
        updated_at_utc=sub["updated_at_utc"] if sub else None,
        availability=sub["availability_json"] if sub else {},
    )


# ── 7. Aggregate ───────────────────────────────────────────────


@app.get("/api/plans/{plan_id}/aggregate", response_model=AggregateResponse)
async def get_aggregate(plan_id: str):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    data = crud.compute_aggregate(plan_id)
    return AggregateResponse(
        mode=plan["mode"],
        participants_count=data.get("participants_count", 0),
        data=data,
    )


# ── 8. Export ──────────────────────────────────────────────────


@app.get("/api/plans/{plan_id}/export")
async def export_plan(
    plan_id: str,
    format: str = Query("json", pattern="^(json|ai)$"),
    x_plan_password: str | None = Header(None),
):
    plan = crud.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    _verify_plan_password(plan, x_plan_password)

    participants = crud.get_all_participants(plan_id)
    submissions = crud.get_all_submissions(plan_id)

    safe_plan = {k: v for k, v in plan.items() if k != "password_hash"}

    if format == "json":
        return {
            "plan": safe_plan,
            "participants": participants,
            "submissions": submissions,
        }

    submissions_by_pid = {
        sub["participant_id"]: sub for sub in submissions
    }
    sorted_participants = sorted(
        participants, key=lambda p: str(p.get("display_name", "")).lower()
    )

    mode_label = str(plan["mode"]).replace("_", " ").title()
    lines = [
        f"Plan: {plan['title']}",
        f"Mode: {mode_label}",
        f"Anchor timezone: {plan['anchor_timezone']}",
        f"Slot size: {plan['slot_minutes']} minutes",
        f"Participants: {len(participants)}",
        "",
        "Participant availability:",
    ]
    for participant in sorted_participants:
        name = str(participant.get("display_name", "Participant"))
        sub = submissions_by_pid.get(str(participant.get("participant_id", "")))
        lines.append(
            f"- {_participant_availability_sentence(name, plan, sub)}"
        )

    return {"text": "\n".join(lines)}
