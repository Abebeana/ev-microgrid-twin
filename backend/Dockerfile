FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock .python-version /app/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-default-groups
COPY backend /app/backend
COPY config /app/config
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
