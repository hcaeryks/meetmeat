# meet me at

A group scheduling web app where a plan owner creates a scheduling plan, shares a link, and participants mark their availability. The system supports 5 scheduling modes and normalizes all cell values into 3 types: **IDEAL**, **OK**, **UNSET**.

## Scheduling Modes

| Mode | Description |
|---|---|
| **WEEKLY_GRID** | 7-day time grid (Sun–Sat), 24h rows with configurable slot size. Supports "Any Week" (recurring) and "Specific Week" scopes. |
| **DATES_ONLY** | Calendar date picker. Click dates to mark as Ideal / OK. |
| **DATE_TIME_WINDOWS** | Pick dates in a range, then paint time slots within each day. |
| **OPTIONS_POLL** | Vote Yes / Maybe / No on a list of specific datetime options. Maps to IDEAL / OK / UNSET. |
| **DURATION_FINDER** | Paint availability like DATE_TIME_WINDOWS; the system finds the best overlapping windows of a given duration. |

## Tech Stack

- **Backend**: FastAPI (Python 3.12+), SQLite, managed with `uv`
- **Frontend**: SvelteKit, Tailwind CSS v4, `date-fns` + `date-fns-tz`
- **Deployment**: Docker Compose

## Local Development

### Backend

```bash
cd backend
uv sync
uv run fastapi dev
```

The API runs at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The app runs at `http://localhost:5173`. The Vite dev server proxies `/api` requests to the backend at `localhost:8000`.

## Docker

### Production

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- SQLite database persists at `./data/app.db`

### Development (with hot reload)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend dev server: `http://localhost:3000` (Vite HMR)
- Backend API: `http://localhost:8000` (uvicorn `--reload`)
- Source files are mounted into containers — edits to `backend/app/` and `frontend/src/` trigger automatic reloads

## API Endpoints

All endpoints are under `/api`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/plans` | Create a new plan |
| GET | `/api/plans/{plan_id}` | Get plan details (password-gated) |
| POST | `/api/plans/{plan_id}/password` | Set password (first visitor) |
| POST | `/api/plans/{plan_id}/participants` | Create or get participant |
| PUT | `/api/plans/{plan_id}/submissions/{participant_id}` | Save availability |
| GET | `/api/plans/{plan_id}/aggregate` | Get aggregated results |
| GET | `/api/plans/{plan_id}/export?format=json\|ai` | Export plan data |

### Password Flow

1. Creator enables "Require password" during plan creation.
2. First visitor to the plan sets the password.
3. Subsequent visitors must enter the password (sent via `X-Plan-Password` header).

## Data Formats

### Plan Config JSON (`plans.config_json`)

**WEEKLY_GRID:**
```json
{ "scope": "ANY_WEEK", "slot_minutes": 15 }
{ "scope": "SPECIFIC_WEEK", "week_start_local_date": "2026-03-01", "slot_minutes": 15 }
```

**DATES_ONLY:**
```json
{ "date_start_local": "2026-03-01", "date_end_local": "2026-03-31" }
```

**DATE_TIME_WINDOWS:**
```json
{ "date_start_local": "2026-03-01", "date_end_local": "2026-03-07", "slot_minutes": 15 }
```

**OPTIONS_POLL:**
```json
{ "options": [{ "option_id": "o1", "start_utc": "2026-03-01T14:00:00Z", "duration_minutes": 120 }] }
```

**DURATION_FINDER:**
```json
{ "date_start_local": "2026-03-01", "date_end_local": "2026-03-07", "slot_minutes": 15, "duration_minutes": 120, "min_attendees": 3 }
```

### Participant Availability JSON (`submissions.availability_json`)

**WEEKLY_GRID (ANY_WEEK):**
```json
{ "type": "WEEKLY_GRID", "scope": "ANY_WEEK", "anchor_timezone": "America/Sao_Paulo", "weekly": [{ "dow": 1, "start": "09:00", "end": "12:00", "value": "IDEAL" }] }
```

**WEEKLY_GRID (SPECIFIC_WEEK):**
```json
{ "type": "WEEKLY_GRID", "scope": "SPECIFIC_WEEK", "intervals_utc": [["2026-03-01T12:00:00Z", "2026-03-01T15:00:00Z", "IDEAL"]] }
```

**DATES_ONLY:**
```json
{ "type": "DATES_ONLY", "anchor_timezone": "America/Sao_Paulo", "dates": [{ "date": "2026-03-01", "value": "IDEAL" }] }
```

**DATE_TIME_WINDOWS / DURATION_FINDER:**
```json
{ "type": "DATE_TIME_WINDOWS", "intervals_utc": [["2026-03-01T12:00:00Z", "2026-03-01T15:00:00Z", "IDEAL"]] }
```

**OPTIONS_POLL:**
```json
{ "type": "OPTIONS_POLL", "votes": [{ "option_id": "o1", "value": "IDEAL" }] }
```

## Timezone Handling

- All concrete timestamps are stored in UTC.
- Each plan has an `anchor_timezone` (IANA string) used as the reference for local-time constructs.
- **ANY_WEEK** patterns and **DATES_ONLY** dates are stored in the anchor timezone to avoid DST shifting.
- Each participant selects their timezone; the UI converts between viewer timezone and UTC/anchor timezone for display.

## Theme

The app supports dark and light themes. Toggle via the sun/moon icon in the header. Preference is stored in `localStorage`.
