FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

FROM python:3.12-alpine

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/

ENV DATABASE_PATH=/data/app.db

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
