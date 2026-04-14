# backend/Dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic.ini .
COPY alembic/ alembic/

# API server
FROM base AS api
CMD ["uvicorn", "src.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Worker
FROM base AS worker
CMD ["python", "-m", "src.workers.main"]
