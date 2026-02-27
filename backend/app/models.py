from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


PlanMode = Literal[
    "WEEKLY_GRID",
    "DATES_ONLY",
    "DATE_TIME_WINDOWS",
    "OPTIONS_POLL",
    "DURATION_FINDER",
]

CellValue = Literal["IDEAL", "OK", "UNSET"]


# ── Plan creation ──────────────────────────────────────────────


class CreatePlanRequest(BaseModel):
    title: str
    mode: PlanMode
    anchor_timezone: str
    slot_minutes: int = 15
    require_password: bool = False
    config: dict[str, Any]


class CreatePlanResponse(BaseModel):
    plan_id: str
    url_path: str


# ── Plan retrieval ─────────────────────────────────────────────


class PlanResponse(BaseModel):
    plan_id: str
    title: str
    mode: PlanMode
    created_at_utc: str
    anchor_timezone: str
    slot_minutes: int
    require_password: bool
    password_hash_exists: bool
    config: dict[str, Any]
    participants_count: int


# ── Password ───────────────────────────────────────────────────


class SetPasswordRequest(BaseModel):
    password: str


class SetPasswordResponse(BaseModel):
    ok: bool


# ── Participants ───────────────────────────────────────────────


class CreateParticipantRequest(BaseModel):
    display_name: str
    timezone: str
    password: str | None = None


class ParticipantResponse(BaseModel):
    participant_id: str
    display_name: str
    timezone: str
    has_password: bool = False


# ── Submissions ────────────────────────────────────────────────


class SubmitAvailabilityRequest(BaseModel):
    availability: dict[str, Any]


class SubmitAvailabilityResponse(BaseModel):
    ok: bool
    updated_at_utc: str


class GetSubmissionResponse(BaseModel):
    participant_id: str
    updated_at_utc: str | None = None
    availability: dict[str, Any]


# ── Aggregate ──────────────────────────────────────────────────


class AggregateResponse(BaseModel):
    mode: PlanMode
    participants_count: int
    data: dict[str, Any]


# ── Export ─────────────────────────────────────────────────────


class ExportResponse(BaseModel):
    plan: dict[str, Any]
    participants: list[dict[str, Any]]
    submissions: list[dict[str, Any]]
