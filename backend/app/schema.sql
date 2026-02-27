CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('WEEKLY_GRID','DATES_ONLY','DATE_TIME_WINDOWS','OPTIONS_POLL','DURATION_FINDER')),
    created_at_utc TEXT NOT NULL,
    anchor_timezone TEXT NOT NULL,
    slot_minutes INTEGER NOT NULL DEFAULT 15,
    require_password INTEGER NOT NULL DEFAULT 0 CHECK(require_password IN (0,1)),
    password_hash TEXT NULL,
    password_created_at_utc TEXT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    timezone TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    password_hash TEXT NULL,
    UNIQUE(plan_id, display_name)
);

CREATE TABLE IF NOT EXISTS submissions (
    submission_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    participant_id TEXT NOT NULL REFERENCES participants(participant_id) ON DELETE CASCADE,
    availability_json TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE(plan_id, participant_id)
);
